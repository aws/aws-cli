use super::super::{ListOptions, ListStats};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};
use std::time::Duration;

fn serve(
    listener: TcpListener,
    second_status: u16,
    emitted: Option<Arc<AtomicBool>>,
) -> std::io::Result<Vec<String>> {
    let mut requests = Vec::new();
    for index in 0..2 {
        let (mut stream, _) = listener.accept()?;
        if index == 1
            && let Some(emitted) = &emitted
        {
            assert!(emitted.load(Ordering::SeqCst));
        }
        stream.set_read_timeout(Some(Duration::from_secs(10)))?;
        let mut request = Vec::new();
        let mut chunk = [0; 1024];
        while !request.windows(4).any(|window| window == b"\r\n\r\n") {
            let count = stream.read(&mut chunk)?;
            if count == 0 {
                break;
            }
            request.extend_from_slice(&chunk[..count]);
        }
        requests.push(String::from_utf8_lossy(&request).into_owned());
        let body: &[u8] = if index == 0 {
            b"<ListBucketResult><EncodingType>url</EncodingType><IsTruncated>tr\
                ue</IsTruncated><NextContinuationToken>t/+=</NextContinuationToke\
                n><Contents><Key>a%2Bb</Key><Size>1</Size></Contents></ListBucket\
                Result>"
                .as_slice()
        } else if second_status == 200 {
            b"<ListBucketResult><EncodingType>url</EncodingType><IsTruncated>fa\
                lse</IsTruncated><CommonPrefixes><Prefix>dir%2F</Prefix></CommonP\
                refixes></ListBucketResult>"
        } else {
            b"<Error><Code>AccessDenied</Code><Message>denied &amp; blocked</Message></Error>"
        };
        let status = if index == 0 { 200 } else { second_status };
        write!(
            stream,
            "HTTP/1.1 {status} status\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        )?;
        stream.write_all(body)?;
    }
    Ok(requests)
}
#[test]
fn real_pagination_headers_and_failed_page_context() -> Result<(), Box<dyn std::error::Error>> {
    for (status, prefetch) in [(200, true), (403, true), (200, false)] {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let emitted = Arc::new(AtomicBool::new(false));
        let server_emitted = (!prefetch).then(|| Arc::clone(&emitted));
        let server = std::thread::spawn(move || serve(listener, status, server_emitted));
        let runtime = crate::Runtime::new(crate::RuntimeOptions {
            endpoint_url: format!("http://{address}/bucket"),
            no_sign_request: true,
            event_loop_count: 1,
            max_attempts: None,
            user_agent: "listing-regression".into(),
            ..crate::RuntimeOptions::default()
        })?;
        let mut entries = Vec::new();
        let mut stats = ListStats::default();
        let result = runtime.list_objects(
            ListOptions {
                object_conditions: false,
                bucket: b"bucket",
                prefix: b"a b",
                request_payer: b"requester",
                recursive: false,
                page_size: 1,
                prefetch,
                user_agent: None,
            },
            Some(&mut stats),
            &mut |entry| {
                entries.push(entry);
                emitted.store(true, Ordering::SeqCst);
                0
            },
        );
        assert_result(status, &result, &stats, &entries);
        drop(runtime);
        let requests = server.join().map_err(|_| "loopback server panicked")??;
        assert_requests(&requests);
    }
    Ok(())
}

fn assert_result(
    status: u16,
    result: &crate::s3::ListResult,
    stats: &ListStats,
    entries: &[super::super::ListEntry],
) {
    assert_eq!(entries[0].name, b"a+b");
    if status == 200 {
        assert_eq!(result.transfer.error_code, 0);
        assert_eq!(entries[1].name, b"dir/");
        assert_eq!(stats.pages, 2);
        assert_eq!(stats.shutdown_wait.count, 2);
    } else {
        assert_failure(result);
    }
}
fn header_names(request: &str) -> Vec<String> {
    request
        .split("\r\n")
        .skip(1)
        .take_while(|line| !line.is_empty())
        .filter_map(|line| line.split_once(':'))
        .map(|(name, _)| name.to_ascii_lowercase())
        .collect()
}
fn assert_requests(requests: &[String]) {
    for request in requests {
        let lower = request.to_ascii_lowercase();
        assert!(lower.contains("accept: application/xml\r\n"));
        assert!(lower.contains("x-amz-request-payer: requester\r\n"));
        assert!(lower.contains("user-agent: listing-regression"));
        assert!(!lower.contains("authorization:"));
        assert_eq!(
            header_names(request),
            ["host", "accept", "x-amz-request-payer", "user-agent"]
        );
    }
    assert!(requests[0].starts_with(
        "GET /bucket?list-type=2&prefix=a%20b&delimiter=%2F&max-keys=1&encoding-type=url "
    ));
    assert!(requests[1].starts_with(
        "GET /bucket?list-type=2&prefix=a%20b&delimiter=%2F&max-keys=1&con\
        tinuation-token=t%2F%2B%3D&encoding-type=url "
    ));
}

fn assert_failure(result: &crate::s3::ListResult) {
    assert_eq!(result.transfer.response_status, 403);
    assert_eq!(
        result.transfer.service_error.code.as_bytes(),
        b"AccessDenied"
    );
    assert_eq!(result.transfer.service_error.message, b"denied & blocked");
    assert_eq!(
        result.transfer.service_error.operation.as_bytes(),
        b"ListObjectsV2"
    );
    assert_eq!(
        result.request_path.as_slice(),
        b"/bucket?list-type=2&prefix=a%20b&delimiter=%2F&max-keys=1&continu\
        ation-token=t%2F%2B%3D&encoding-type=url"
    );
}

fn serve_rejected(listener: TcpListener, count: usize) -> std::io::Result<Vec<String>> {
    let body = b"<html>oops";
    let mut lines = Vec::new();
    for _ in 0..count {
        let (mut stream, _) = listener.accept()?;
        stream.set_read_timeout(Some(Duration::from_secs(10)))?;
        let mut request = Vec::new();
        let mut chunk = [0; 1024];
        while !request.windows(4).any(|window| window == b"\r\n\r\n") {
            let read = stream.read(&mut chunk)?;
            if read == 0 {
                break;
            }
            request.extend_from_slice(&chunk[..read]);
        }
        let request = String::from_utf8_lossy(&request).into_owned();
        lines.push(request.lines().next().unwrap_or_default().to_owned());
        write!(
            stream,
            "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        )?;
        stream.write_all(body)?;
    }
    Ok(lines)
}
#[test]
fn a_listing_takes_its_page_attempts_from_the_runtime() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let server = std::thread::spawn(move || serve_rejected(listener, 2));
    let runtime = crate::Runtime::new(crate::RuntimeOptions {
        endpoint_url: format!("http://{address}/bucket"),
        no_sign_request: true,
        event_loop_count: 1,
        botocore_attempts: 2,
        user_agent: "listing-regression".into(),
        ..crate::RuntimeOptions::default()
    })?;
    let result = runtime.list_objects(
        ListOptions {
            object_conditions: false,
            bucket: b"bucket",
            prefix: b"",
            request_payer: b"",
            recursive: true,
            page_size: 0,
            prefetch: true,
            user_agent: None,
        },
        None,
        &mut |_| 0,
    );
    drop(runtime);
    let requests = server.join().map_err(|_| "loopback server panicked")??;
    assert_eq!(requests.len(), 2);
    assert_eq!(requests[0], requests[1]);
    assert_eq!(result.local_error, None);
    assert_eq!(
        (
            result.transfer.response_status,
            result.transfer.retries_exhausted
        ),
        (500, Some(1))
    );
    assert_eq!(
        result.transfer.service_error.operation.as_bytes(),
        b"ListObjectsV2"
    );
    Ok(())
}
