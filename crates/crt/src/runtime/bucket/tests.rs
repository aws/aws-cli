use super::*;
use crate::redirect::{ResolveError, ResolvedEndpoint};
use crt_sys::native as c;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::time::Duration;

type TestResult = Result<(), Box<dyn std::error::Error>>;

#[derive(Debug)]
struct FixedResolver(String);
impl Resolver for FixedResolver {
    fn bucket(&self) -> &str {
        "bucket"
    }
    fn client_region(&self) -> &str {
        "us-east-1"
    }
    fn resolve(&self, _region: &str) -> Result<ResolvedEndpoint, ResolveError> {
        Ok(ResolvedEndpoint {
            url: self.0.clone(),
            signing_region: None,
        })
    }
}

fn options(endpoint_url: String) -> RuntimeOptions {
    RuntimeOptions {
        region: "fips-us-east-1".into(),
        endpoint_url,
        event_loop_count: 1,
        no_sign_request: true,
        user_agent: "redirect-test-agent".into(),
        ..RuntimeOptions::default()
    }
}

fn redirect_failure(region: Option<&str>) -> TransferResult {
    let mut failure = TransferResult {
        error_code: 1,
        response_status: 301,
        ..TransferResult::default()
    };
    failure.request_region.set(b"us-east-1");
    failure.service_error.operation.set(b"GetObject");
    if let Some(region) = region {
        failure.service_error.region_header.set(region.as_bytes());
    }
    failure
}

fn signing_region(runtime: &Runtime) -> Vec<u8> {
    let mut snapshot = std::mem::MaybeUninit::<c::SigningSnapshot>::uninit();
    // SAFETY: the shim fills every field; the runtime outlives the copied cursor.
    let snapshot = unsafe {
        c::zaws_runtime_signing_snapshot(runtime.pointer(), snapshot.as_mut_ptr());
        snapshot.assume_init()
    };
    assert!(snapshot.anonymous && snapshot.same_credentials);
    if snapshot.region.len == 0 {
        return Vec::new();
    }
    // SAFETY: the cursor borrows the live runtime's signing region.
    unsafe { std::slice::from_raw_parts(snapshot.region.ptr, snapshot.region.len).to_vec() }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test checks every setting the published client keeps"
)]
fn published_client_preserves_anonymous_signing_and_the_original_proxy_bypass() -> TestResult {
    let interrupted = State::new();
    let runtime = BucketRuntime::new(
        options("http://127.0.0.1:1/base/bucket".into()),
        Some(Arc::new(FixedResolver(
            "http://127.0.0.1:9/base/bucket".into(),
        ))),
        None,
    )?;
    assert_eq!(runtime.original().client_region(), "us-east-1");
    assert!(Arc::ptr_eq(runtime.selected(), runtime.original()));
    let mut failure = redirect_failure(Some("us-west-2"));
    assert_eq!(
        runtime.recover_region(&failure, true, &interrupted),
        Outcome::Ready
    );
    let selected = Arc::clone(runtime.selected());
    assert!(!Arc::ptr_eq(&selected, runtime.original()));
    assert_eq!(selected.client_region(), "us-west-2");
    assert_eq!(
        selected.options().endpoint_url,
        "http://127.0.0.1:9/base/bucket"
    );
    assert_eq!(selected.options().user_agent, "redirect-test-agent");
    assert!(selected.options().no_sign_request);
    assert_eq!(signing_region(&selected), b"us-west-2");
    assert_eq!(selected.options().proxy_url, None);
    let stale = redirect_failure(Some("eu-west-1"));
    assert_eq!(
        runtime.recover_region(&stale, true, &interrupted),
        Outcome::Ready
    );
    assert!(Arc::ptr_eq(runtime.selected(), &selected));
    failure.request_region.set(b"us-west-2");
    assert_eq!(
        runtime.recover_region(&failure, true, &interrupted),
        Outcome::Unavailable
    );
    assert_eq!(
        runtime.recover_region(&failure, false, &interrupted),
        Outcome::Ready
    );
    interrupted.request();
    assert_eq!(
        runtime.recover_region(&failure, false, &interrupted),
        Outcome::Canceled
    );
    Ok(())
}

#[test]
fn runtimes_without_a_recipe_or_with_ineligible_failures_never_recover() -> TestResult {
    let interrupted = State::new();
    let plain = BucketRuntime::new(options("http://127.0.0.1:1/bucket".into()), None, None)?;
    assert_eq!(plain.original().client_region(), "fips-us-east-1");
    let failure = redirect_failure(Some("us-west-2"));
    assert_eq!(
        plain.recover_region(&failure, true, &interrupted),
        Outcome::Unavailable
    );
    let runtime = BucketRuntime::new(
        options("http://127.0.0.1:1/bucket".into()),
        Some(Arc::new(FixedResolver("http://127.0.0.1:9/bucket".into()))),
        None,
    )?;
    let same = redirect_failure(Some("us-east-1"));
    assert_eq!(
        runtime.recover_region(&same, true, &interrupted),
        Outcome::Unavailable
    );
    let invalid = redirect_failure(Some("bad/region"));
    assert_eq!(
        runtime.recover_region(&invalid, false, &interrupted),
        Outcome::Unavailable
    );
    assert!(Arc::ptr_eq(runtime.selected(), runtime.original()));
    interrupted.request();
    assert_eq!(
        runtime.recover_region(&failure, true, &interrupted),
        Outcome::Canceled
    );
    assert!(Arc::ptr_eq(runtime.selected(), runtime.original()));
    Ok(())
}

fn serve(listener: TcpListener, responses: Vec<&'static [u8]>) -> std::io::Result<Vec<String>> {
    let mut requests = Vec::new();
    for response in responses {
        let (mut stream, _) = listener.accept()?;
        stream.set_read_timeout(Some(Duration::from_secs(15)))?;
        let mut request = Vec::new();
        let mut chunk = [0; 1024];
        while !request.windows(4).any(|w| w == b"\r\n\r\n") {
            let count = stream.read(&mut chunk)?;
            if count == 0 {
                break;
            }
            request.extend_from_slice(&chunk[..count]);
        }
        requests.push(String::from_utf8_lossy(&request).into_owned());
        stream.write_all(response)?;
    }
    Ok(requests)
}

#[test]
fn missing_metadata_discovers_through_one_uncached_head_bucket() -> TestResult {
    for (base, request_line) in [("/base/bucket", "HEAD /base/bucket "), ("", "HEAD / ")] {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let server = std::thread::spawn(move || {
            serve(
                listener,
                vec![
                    b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
                    b"HTTP/1.1 403 Forbidden\r\nx-amz-bucket-region: us-west-2\r\nContent-L\
                      ength: 0\r\nConnection: close\r\n\r\n",
                ],
            )
        });
        let interrupted = State::new();
        let runtime = BucketRuntime::new(
            options(format!("http://{address}{base}")),
            Some(Arc::new(FixedResolver("http://127.0.0.1:9/bucket".into()))),
            None,
        )?;
        let failure = redirect_failure(None);
        assert_eq!(
            runtime.recover_region(&failure, true, &interrupted),
            Outcome::Unavailable
        );
        assert!(Arc::ptr_eq(runtime.selected(), runtime.original()));
        assert_eq!(
            runtime.recover_region(&failure, true, &interrupted),
            Outcome::Ready
        );
        assert_eq!(runtime.selected().client_region(), "us-west-2");
        drop(runtime);
        let requests = server.join().map_err(|_| "server panic")??;
        assert_eq!(requests.len(), 2);
        assert!(
            requests
                .iter()
                .all(|request| request.starts_with(request_line)),
            "{requests:?}"
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "one test follows both requests through the redirect and the regional replay"
)]
fn head_and_listing_replay_once_on_the_regional_client() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let redirect: &'static [u8] =
        b"HTTP/1.1 301 Moved Permanently\r\nx-amz-bucket-region: us-west-2\r\n\
        Content-Length: 0\r\nConnection: close\r\n\r\n";
    let page: &'static [u8] =
        b"HTTP/1.1 200 OK\r\nContent-Length: 116\r\nConnection: close\r\n\r\n\
        <ListBucketResult><IsTruncated>false</IsTruncated><Contents><Key>a</Key><Size>1</Size>\
        </Contents></ListBucketResult>";
    let server = std::thread::spawn(move || {
        serve(
            listener,
            vec![
                redirect,
                b"HTTP/1.1 200 OK\r\nContent-Length: 17\r\nConnection: close\r\n\r\n",
                redirect,
                page,
            ],
        )
    });
    let interrupted = State::new();
    let resolver = Arc::new(FixedResolver(format!("http://{address}/regional/bucket")));
    let head_runtime = BucketRuntime::new(
        options(format!("http://{address}/bucket")),
        Some(Arc::clone(&resolver) as Arc<dyn Resolver>),
        None,
    )?;
    let head = head_runtime.head_object(
        crate::s3::HeadObject {
            key: b"key",
            request_payer: None,
            headers: &[],
        },
        &interrupted,
    )?;
    assert_eq!(head.transfer.error_code, 0);
    assert_eq!(head.content_length, Some(17));
    assert_eq!(head.transfer.request_region.as_bytes(), b"us-west-2");
    assert_eq!(
        head.transfer.endpoint_url.as_bytes(),
        format!("http://{address}/regional/bucket").as_bytes()
    );
    let list_runtime = BucketRuntime::new(
        options(format!("http://{address}/bucket")),
        Some(resolver),
        None,
    )?;
    let mut names = Vec::new();
    let listed = list_runtime.list_objects(
        crate::s3::ListOptions {
            object_conditions: false,
            bucket: b"bucket",
            prefix: b"",
            request_payer: b"",
            recursive: true,
            page_size: 0,
            prefetch: false,
            user_agent: None,
        },
        None,
        &mut |entry| {
            names.push(entry.name);
            0
        },
        &interrupted,
    );
    assert_eq!(listed.transfer.error_code, 0, "{}", listed.transfer);
    assert_eq!(names, [b"a".to_vec()]);
    drop((head_runtime, list_runtime));
    let requests = server.join().map_err(|_| "server panic")??;
    assert!(requests[0].starts_with("HEAD /bucket/key "), "{requests:?}");
    assert!(requests[1].starts_with("HEAD /regional/bucket/key "));
    assert!(requests[2].starts_with("GET /bucket?list-type=2"));
    assert!(requests[3].starts_with("GET /regional/bucket?list-type=2"));
    Ok(())
}

#[test]
fn a_throttled_head_or_delete_is_sent_again_while_its_attempts_last() -> TestResult {
    let throttled: &'static [u8] =
        b"HTTP/1.1 429 Too Many Requests\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let server = std::thread::spawn(move || {
        serve(
            listener,
            vec![
                throttled,
                b"HTTP/1.1 200 OK\r\nContent-Length: 17\r\nConnection: close\r\n\r\n",
                throttled,
                b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n",
                throttled,
                throttled,
            ],
        )
    });
    let interrupted = State::new();
    let runtime = BucketRuntime::new(
        RuntimeOptions {
            botocore_attempts: 2,
            ..options(format!("http://{address}/bucket"))
        },
        None,
        None,
    )?;
    let head = HeadObject {
        key: b"key",
        request_payer: None,
        headers: &[],
    };
    let headed = runtime.head_object(head, &interrupted)?;
    assert_eq!(headed.transfer.error_code, 0, "{}", headed.transfer);
    assert_eq!(headed.content_length, Some(17));
    let delete = RequestOptions {
        kind: RequestKind::Delete,
        key: b"key",
        filepath: None,
        object_size_hint: None,
        if_none_match: false,
        content_type: None,
        condition: None,
        check_object_size: false,
        request_payer: None,
        user_agent: None,
        headers: &[],
        checksum_algorithm: None,
        validate_checksum: false,
    };
    let deleted = runtime.send(delete, &interrupted)?;
    assert_eq!(deleted.error_code, 0, "{deleted}");
    let failed = runtime.head_object(head, &interrupted)?.transfer;
    assert_eq!(failed.response_status, 429);
    assert_eq!(failed.retries_exhausted, Some(1));
    drop(runtime);
    let requests = server.join().map_err(|_| "server panic")??;
    let methods: Vec<_> = requests
        .iter()
        .map(|request| request.split(' ').next().unwrap_or(""))
        .collect();
    assert_eq!(
        methods,
        ["HEAD", "HEAD", "DELETE", "DELETE", "HEAD", "HEAD"],
        "{requests:?}"
    );
    Ok(())
}
