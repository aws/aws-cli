//! A delegate's credentials sign the S3 client's requests on the wire.
use crate::credentials::native::{Pinned, data, on_query};
use crate::credentials::{Delegate, Query, Source, Unavailable, View};
use crate::s3::{ListOptions, NO_CREDENTIALS_ERROR_CODE};
use std::ffi::{c_int, c_void};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, UNIX_EPOCH};

unsafe extern "C" {
    fn aws_credentials_get_access_key_id(
        credentials: *const crt_sys::AwsCredentials,
    ) -> crt_sys::AwsByteCursor;
    fn aws_credentials_get_secret_access_key(
        credentials: *const crt_sys::AwsCredentials,
    ) -> crt_sys::AwsByteCursor;
    fn aws_credentials_get_session_token(
        credentials: *const crt_sys::AwsCredentials,
    ) -> crt_sys::AwsByteCursor;
    fn aws_credentials_get_account_id(
        credentials: *const crt_sys::AwsCredentials,
    ) -> crt_sys::AwsByteCursor;
    fn aws_credentials_get_expiration_timepoint_seconds(
        credentials: *const crt_sys::AwsCredentials,
    ) -> u64;
}

/// How a test delegate answers each query.
#[derive(Debug, Clone, Copy)]
enum Answer {
    /// During the CRT's call, on the CRT's thread.
    Inline,
    /// After the call returns, from a thread the delegate owns, as a
    /// refresh that must not block an event loop would.
    OtherThread,
    Fail,
}

#[derive(Debug)]
struct Fixed {
    answer: Answer,
    queries: AtomicUsize,
    /// Queries that arrived on the thread that built the delegate, which
    /// is the thread that submits the requests.
    on_submitting_thread: AtomicUsize,
    submitter: std::thread::ThreadId,
}

impl Fixed {
    fn new(answer: Answer) -> Arc<Self> {
        Arc::new(Self {
            answer,
            queries: AtomicUsize::new(0),
            on_submitting_thread: AtomicUsize::new(0),
            submitter: std::thread::current().id(),
        })
    }
}

const VIEW: View<'static> = View {
    access_key_id: "AKIDDELEGATE",
    secret_access_key: "delegate-secret",
    session_token: Some("delegate-token"),
    account_id: None,
    expiration: None,
};

impl Delegate for Fixed {
    fn credentials(&self, query: Query) {
        self.queries.fetch_add(1, Ordering::SeqCst);
        if std::thread::current().id() == self.submitter {
            self.on_submitting_thread.fetch_add(1, Ordering::SeqCst);
        }
        match self.answer {
            Answer::Inline => query.complete(VIEW),
            Answer::OtherThread => {
                std::thread::spawn(move || {
                    std::thread::sleep(Duration::from_millis(20));
                    query.complete(VIEW);
                });
            }
            Answer::Fail => query.fail(),
        }
    }
}

/// Serves one single-page listing and returns the request's head.
fn serve(listener: TcpListener) -> std::io::Result<String> {
    let (mut stream, _) = listener.accept()?;
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
    let body = b"<ListBucketResult><IsTruncated>false</IsTruncated><Contents><Key>a</Key>\
        <Size>1</Size></Contents></ListBucketResult>";
    write!(
        stream,
        "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    )?;
    stream.write_all(body)?;
    Ok(String::from_utf8_lossy(&request).into_owned())
}

fn list(runtime: &crate::Runtime) -> (crate::s3::ListResult, usize) {
    let mut entries = 0;
    let result = runtime.list_objects(
        ListOptions {
            bucket: b"bucket",
            prefix: b"",
            request_payer: b"",
            recursive: false,
            page_size: 1000,
            prefetch: true,
            user_agent: None,
            object_conditions: false,
        },
        None,
        &mut |_| {
            entries += 1;
            0
        },
    );
    (result, entries)
}

fn runtime(
    endpoint_url: String,
    delegate: &Arc<Fixed>,
) -> Result<crate::Runtime, Box<crate::s3::TransferResult>> {
    crate::Runtime::new(crate::RuntimeOptions {
        endpoint_url,
        region: "us-west-2".into(),
        credentials: Source::Delegate(Arc::clone(delegate) as Arc<dyn Delegate>),
        event_loop_count: 1,
        ..crate::RuntimeOptions::default()
    })
}

#[test]
fn a_delegate_signs_the_s3_clients_requests() -> Result<(), Box<dyn std::error::Error>> {
    for answer in [Answer::Inline, Answer::OtherThread] {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let server = std::thread::spawn(move || serve(listener));
        let delegate = Fixed::new(answer);
        let runtime = runtime(format!("http://{address}/bucket"), &delegate)?;
        let (result, entries) = list(&runtime);
        assert_eq!((result.transfer.error_code, entries), (0, 1), "{answer:?}");
        drop(runtime);
        let request = server.join().map_err(|_| "loopback server panicked")??;
        let lower = request.to_ascii_lowercase();
        assert!(
            lower.contains("authorization: aws4-hmac-sha256 credential=akiddelegate/"),
            "{request}"
        );
        assert!(lower.contains("/us-west-2/s3/aws4_request"), "{request}");
        assert!(lower.contains("x-amz-security-token: delegate-token\r\n"));
        assert!(!request.contains("delegate-secret"));
        // The CRT asked once for the one request it signed, and cached
        // nothing. It asked on one of its own threads, which a blocking
        // answer would stall.
        assert_eq!(delegate.queries.load(Ordering::SeqCst), 1);
        assert_eq!(delegate.on_submitting_thread.load(Ordering::SeqCst), 0);
    }
    Ok(())
}

#[test]
fn a_failed_query_is_the_signers_no_credentials_error() -> Result<(), Box<dyn std::error::Error>> {
    let delegate = Fixed::new(Answer::Fail);
    // Nothing listens: signing fails before the client connects.
    let runtime = runtime("http://127.0.0.1:9/bucket".into(), &delegate)?;
    let (result, entries) = list(&runtime);
    assert_eq!(
        (result.transfer.error_code, entries),
        (NO_CREDENTIALS_ERROR_CODE, 0)
    );
    Ok(())
}

/// Answers every query with the view it holds.
#[derive(Debug)]
struct Answering(View<'static>);

impl Delegate for Answering {
    fn credentials(&self, query: Query) {
        query.complete(View { ..self.0 });
    }
}

/// What the CRT's credentials object holds, read back through aws-c-auth's
/// own getters. A member the credentials lack reads as empty.
#[derive(Debug, PartialEq, Eq)]
struct Held {
    access_key_id: String,
    secret_access_key: String,
    session_token: String,
    account_id: String,
    expiration: u64,
}

/// A signer's callback that records the credentials it is given in the
/// `Option<Held>` its data points at.
unsafe extern "C" fn record(
    credentials: *mut crt_sys::AwsCredentials,
    error_code: c_int,
    data: *mut c_void,
) {
    if error_code != 0 || credentials.is_null() {
        return;
    }
    let text = |cursor: crt_sys::AwsByteCursor| {
        if cursor.len == 0 {
            return String::new();
        }
        // SAFETY: a cursor that is not empty points at `len` bytes the
        // credentials own, which are live for this call.
        let bytes = unsafe { std::slice::from_raw_parts(cursor.ptr, cursor.len) };
        String::from_utf8_lossy(bytes).into_owned()
    };
    // SAFETY: the credentials are live for the call, and the test passes a
    // live `Option<Held>` that nothing else touches during it.
    unsafe {
        *data.cast::<Option<Held>>() = Some(Held {
            access_key_id: text(aws_credentials_get_access_key_id(credentials)),
            secret_access_key: text(aws_credentials_get_secret_access_key(credentials)),
            session_token: text(aws_credentials_get_session_token(credentials)),
            account_id: text(aws_credentials_get_account_id(credentials)),
            expiration: aws_credentials_get_expiration_timepoint_seconds(credentials),
        });
    }
}

/// The wire shows the access key and the token. The secret key only signs
/// and the signer never reads the expiry, so the wire cannot show that
/// either reached the CRT; the credentials object the signer is handed can.
#[test]
fn the_crts_credentials_hold_what_the_delegate_answered() {
    let _library = crate::runtime::Library::acquire();
    let expiry = 2_139_722_880;
    let whole = View {
        account_id: Some("123456789012"),
        expiration: Some(UNIX_EPOCH + Duration::from_secs(expiry)),
        ..VIEW
    };
    let bare = View {
        session_token: None,
        ..VIEW
    };
    for (view, session_token, account_id, expiration) in [
        (whole, "delegate-token", "123456789012", expiry),
        (bare, "", "", u64::MAX),
    ] {
        let delegate: Pinned = Box::new(Arc::new(Answering(view)));
        let mut seen: Option<Held> = None;
        // SAFETY: the delegate outlives the call, and it answers during
        // the call, while `seen` is live and unshared.
        let status = unsafe {
            on_query(
                data(&delegate),
                Some(record),
                std::ptr::from_mut(&mut seen).cast(),
            )
        };
        let held = Held {
            access_key_id: "AKIDDELEGATE".into(),
            secret_access_key: "delegate-secret".into(),
            session_token: session_token.into(),
            account_id: account_id.into(),
            expiration,
        };
        assert_eq!((status, seen), (0, Some(held)));
    }
}

/// Notes the runtimes handed to it: the thread each arrived on, and
/// whether the runtime could already serve the delegate.
#[derive(Debug, Default)]
struct Attached(std::sync::Mutex<Vec<(std::thread::ThreadId, bool)>>);

impl Delegate for Attached {
    fn credentials(&self, query: Query) {
        query.fail();
    }
    fn attach(&self, runtime: &crate::Runtime) -> Result<(), Unavailable> {
        // Nothing listens on the discard port, so the answer is a refusal
        // that the runtime's own threads deliver.
        let refused = runtime.http_client().send(&crate::http::Request {
            host: "127.0.0.1",
            port: 9,
            tls: false,
            method: "GET",
            target: "/",
            headers: &[("Host", "127.0.0.1:9")],
            signing: None,
            connect_timeout: std::time::Duration::from_secs(5),
            read_timeout: std::time::Duration::from_secs(5),
        });
        let usable = matches!(refused, Err(crate::http::Error::Connect(_)));
        crate::signal::lock(&self.0).push((std::thread::current().id(), usable));
        Ok(())
    }
}

/// A delegate whose credentials come from a service the runtime reaches
/// asks it here: on the thread that builds the runtime, once for each
/// runtime, with the runtime already able to build what the delegate needs.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_delegate_is_handed_each_runtime_as_it_is_built() -> Result<(), Box<dyn std::error::Error>> {
    let delegate = Arc::new(Attached::default());
    let options = crate::RuntimeOptions {
        endpoint_url: "http://127.0.0.1:9/bucket".into(),
        credentials: Source::Delegate(Arc::clone(&delegate) as Arc<dyn Delegate>),
        event_loop_count: 1,
        ..crate::RuntimeOptions::default()
    };
    let first = crate::Runtime::new(options.clone())?;
    let second = crate::Runtime::new(options)?;
    let here = std::thread::current().id();
    assert_eq!(*crate::signal::lock(&delegate.0), [(here, true); 2]);
    drop((first, second));
    Ok(())
}
