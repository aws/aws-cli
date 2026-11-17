use super::super::*;
use crate::runtime::{ChecksumMode, RuntimeOptions};
use cli_core::interrupt::State;
use std::{
    io::{Read, Write},
    net::{TcpListener, TcpStream},
    sync::atomic::Ordering,
    time::Duration,
};

type TestResult = Result<(), Box<dyn std::error::Error>>;
fn read_headers(stream: &mut TcpStream) -> std::io::Result<String> {
    stream.set_read_timeout(Some(Duration::from_secs(5)))?;
    let mut request = Vec::new();
    while !request.ends_with(b"\r\n\r\n") {
        let mut byte = [0];
        stream.read_exact(&mut byte)?;
        request.push(byte[0]);
    }
    Ok(String::from_utf8_lossy(&request).into_owned())
}
fn options() -> RequestOptions<'static> {
    RequestOptions {
        kind: RequestKind::Get,
        key: b"object",
        filepath: None,
        object_size_hint: Some(4),
        if_none_match: false,
        content_type: None,
        condition: None,
        check_object_size: false,
        request_payer: None,
        user_agent: None,
        headers: &[],
        checksum_algorithm: None,
        validate_checksum: false,
    }
}
#[test]
fn unsigned_unranged_get_lends_its_body_and_reports_progress() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let runtime = Arc::new(Runtime::new(RuntimeOptions {
        endpoint_url: format!("http://{}/bucket", listener.local_addr()?),
        no_sign_request: true,
        event_loop_count: 1,
        single_request_threshold: Some(4),
        response_checksum_validation: ChecksumMode::WhenSupported,
        user_agent: "native-option-capture".into(),
        ..RuntimeOptions::default()
    })?);
    let server = std::thread::spawn(move || -> std::io::Result<String> {
        let (mut stream, _) = listener.accept()?;
        let request = read_headers(&mut stream)?;
        stream
            .write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\nConnection: close\r\n\r\ndata")?;
        Ok(request)
    });
    let lent = Arc::new(Mutex::new(Vec::new()));
    let bodies = Arc::clone(&lent);
    let body: CallbackBodyFn = Box::new(move |body| {
        match body {
            CallbackBody::Transient { bytes, range_start } => {
                lock(&bodies).push((bytes.to_vec(), range_start));
            }
            CallbackBody::Ticketed(_) | CallbackBody::Missing => {
                return Err(INVALID_ARGUMENT_ERROR_CODE);
            }
        }
        Ok(())
    });
    let (completion, request) = Completion::submit(&runtime, options(), body)?;
    let result = completion.wait(&runtime, request)?;
    assert_eq!(result.error_code, 0, "{result}");
    assert!(result.body_delivered);
    assert_eq!(result.bytes_transferred, 4);
    let request = server
        .join()
        .map_err(|_| "loopback server panicked")??
        .to_ascii_lowercase();
    assert!(request.starts_with("get /bucket/object http/1.1\r\n"));
    assert!(!request.contains("authorization:") && !request.contains("range:"));
    assert!(request.contains("x-amz-checksum-mode: enabled\r\n"));
    assert!(request.contains("user-agent: native-option-capture"));
    assert_eq!(*lock(&lent), [(b"data".to_vec(), 0)]);
    assert_eq!(completion.progress.load(Ordering::Relaxed), 4);
    Ok(())
}
#[test]
fn a_get_above_the_threshold_is_conditioned_on_its_etag() -> TestResult {
    for (size, conditioned) in [(3, false), (4, false), (5, true)] {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let runtime = Arc::new(Runtime::new(RuntimeOptions {
            endpoint_url: format!("http://{}/bucket", listener.local_addr()?),
            no_sign_request: true,
            event_loop_count: 1,
            single_request_threshold: Some(4),
            ..RuntimeOptions::default()
        })?);
        let server = std::thread::spawn(move || -> std::io::Result<String> {
            let (mut stream, _) = listener.accept()?;
            let request = read_headers(&mut stream)?;
            stream.write_all(
                b"HTTP/1.1 206 Partial Content\r\nContent-Length: 4\r\n\
                  Content-Range: bytes 0-3/4\r\nETag: \"original\"\r\n\
                  Connection: close\r\n\r\ndata",
            )?;
            Ok(request)
        });
        let options = RequestOptions {
            object_size_hint: Some(size),
            condition: Some(DownloadCondition {
                etag: b"\"original\"",
                full_object_checksum: &FullObjectChecksum::Unknown,
            }),
            ..options()
        };
        let result = transfer(&runtime, options, Box::new(|_| Ok(())))?;
        assert_eq!(result.error_code, 0, "{result}");
        let request = server
            .join()
            .map_err(|_| "loopback server panicked")??
            .to_ascii_lowercase();
        assert_eq!(
            request.contains("\r\nif-match: \"original\"\r\n"),
            conditioned,
            "{size}"
        );
    }
    Ok(())
}
#[test]
fn head_archive_headers_preserve_restore_completion() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let runtime = Runtime::new(RuntimeOptions {
        endpoint_url: format!("http://{}/bucket", listener.local_addr()?),
        no_sign_request: true,
        event_loop_count: 1,
        ..RuntimeOptions::default()
    })?;
    let server = std::thread::spawn(move || -> std::io::Result<()> {
        let (mut stream, _) = listener.accept()?;
        read_headers(&mut stream)?;
        stream.write_all(
            b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\nx-amz-storage-class: GLAC\
            IER\r\nx-amz-restore: ongoing-request=\"false\", expiry-date=\"Fr\
            i, 21 Dec 2012 00:00:00 GMT\"\r\nConnection: close\r\n\r\n",
        )
    });
    let result = runtime.head_object(
        HeadObject {
            key: b"object",
            request_payer: None,
            headers: &[],
        },
        &State::new(),
    )?;
    assert_eq!(result.content_length, Some(4));
    assert_eq!(
        result.archive,
        ArchiveState {
            archived: true,
            restored: true
        }
    );
    server.join().map_err(|_| "loopback server panicked")??;
    Ok(())
}
#[test]
fn configured_retry_attempts_bound_service_retries() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let runtime = Arc::new(Runtime::new(RuntimeOptions {
        endpoint_url: format!("http://{}/bucket", listener.local_addr()?),
        no_sign_request: true,
        event_loop_count: 1,
        max_attempts: Some(2),
        single_request_threshold: Some(4),
        ..RuntimeOptions::default()
    })?);
    let server = std::thread::spawn(move || -> std::io::Result<usize> {
        let mut count = 0;
        for _ in 0..2 {
            let (mut stream, _) = listener.accept()?;
            read_headers(&mut stream)?;
            stream.write_all(
                b"HTTP/1.1 503 Slow Down\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
            )?;
            count += 1;
        }
        Ok(count)
    });
    let result = transfer(&runtime, options(), Box::new(|_| Ok(())))?;
    assert_ne!(result.error_code, 0);
    assert_eq!(server.join().map_err(|_| "loopback server panicked")??, 2);
    Ok(())
}
#[test]
fn upload_content_type_conditional_and_checksum_modes_reach_http() -> TestResult {
    let path = std::env::temp_dir().join(format!("crt-upload-options-{}", std::process::id()));
    std::fs::write(&path, b"data")?;
    for mode in [ChecksumMode::WhenSupported, ChecksumMode::WhenRequired] {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let runtime = Runtime::new(RuntimeOptions {
            endpoint_url: format!("http://{}/bucket", listener.local_addr()?),
            no_sign_request: true,
            event_loop_count: 1,
            request_checksum_calculation: mode,
            ..RuntimeOptions::default()
        })?;
        let server = std::thread::spawn(move || -> std::io::Result<String> {
            let (mut stream, _) = listener.accept()?;
            let headers = read_headers(&mut stream)?;
            let length = headers
                .lines()
                .find_map(|line| {
                    let (name, value) = line.split_once(':')?;
                    name.eq_ignore_ascii_case("content-length")
                        .then(|| value.trim().parse::<usize>().ok())
                        .flatten()
                })
                .unwrap_or(0);
            let mut body = vec![0; length];
            stream.read_exact(&mut body)?;
            stream.write_all(
                b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nETag: \"tag\"\r\nConnecti\
                on: close\r\n\r\n",
            )?;
            Ok(headers)
        });
        let result = runtime
            .submit(
                RequestOptions {
                    kind: RequestKind::Put,
                    key: b"object",
                    filepath: Some(&path),
                    object_size_hint: None,
                    if_none_match: true,
                    content_type: Some(b"text/example"),
                    condition: None,
                    check_object_size: false,
                    request_payer: None,
                    user_agent: None,
                    headers: &[],
                    checksum_algorithm: None,
                    validate_checksum: false,
                },
                &State::new(),
            )?
            .wait();
        assert_eq!(result.transfer.error_code, 0, "{}", result.transfer);
        let request = server
            .join()
            .map_err(|_| "loopback server panicked")??
            .to_ascii_lowercase();
        assert!(request.contains("content-type: text/example\r\n"));
        assert!(request.contains("if-none-match: *\r\n"));
        assert_eq!(
            request.contains("x-amz-trailer: x-amz-checksum-crc64nvme"),
            mode == ChecksumMode::WhenSupported
        );
    }
    std::fs::remove_file(path)?;
    Ok(())
}
