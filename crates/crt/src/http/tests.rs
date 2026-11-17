//! The client against stand-in servers on loopback. Every timeout here is
//! short, and every wait on a server is bounded.
use super::{Error, Request, Response, Signing};
use crate::credentials::{Delegate, Query, Source, View};
use crate::s3::NO_CREDENTIALS_ERROR_CODE;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::Arc;
use std::sync::mpsc::{Receiver, Sender, channel};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

type TestResult = Result<(), Box<dyn std::error::Error>>;

/// Long enough for loopback on a loaded machine, and short for a test.
const TIMEOUT: Duration = Duration::from_millis(300);
/// How long a test lets a server or a client take before it fails.
const PATIENCE: Duration = Duration::from_secs(20);

/// Answers every query from another thread, or fails it.
#[derive(Debug)]
struct Fixed {
    fail: bool,
}

impl Delegate for Fixed {
    fn credentials(&self, query: Query) {
        if self.fail {
            return query.fail();
        }
        std::thread::spawn(move || {
            query.complete(View {
                access_key_id: "AKIDDELEGATE",
                secret_access_key: "delegate-secret",
                session_token: Some("delegate-token"),
                account_id: None,
                expiration: None,
            });
        });
    }
}

fn runtime(fail: bool) -> Result<crate::Runtime, Box<crate::s3::TransferResult>> {
    crate::Runtime::new(crate::RuntimeOptions {
        // The S3 client is built but unused: the request goes around it.
        endpoint_url: "http://127.0.0.1:9".into(),
        credentials: Source::Delegate(Arc::new(Fixed { fail })),
        event_loop_count: 1,
        ..crate::RuntimeOptions::default()
    })
}

/// What a stand-in server does with the one connection it accepts, once
/// it has read the request's head.
#[derive(Clone, Copy)]
enum Script {
    /// Writes these bytes and closes.
    Answer(&'static [u8]),
    /// Writes nothing, and holds the connection until the test is done.
    Silent,
    /// Writes these bytes, then holds the connection until the test is
    /// done.
    Stall(&'static [u8]),
    /// Closes without a byte.
    Drop,
    /// Writes these bytes before it reads any, then reads until the
    /// client closes.
    Unasked(&'static [u8]),
}

/// A stand-in server for one connection. `done` releases a connection it
/// holds; the thread returns the request's head.
struct Server {
    port: u16,
    done: Sender<()>,
    thread: JoinHandle<std::io::Result<String>>,
}

impl Server {
    fn start(script: Script) -> std::io::Result<Self> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let port = listener.local_addr()?.port();
        let (done, held) = channel();
        let thread = std::thread::spawn(move || serve(&listener, script, &held));
        Ok(Self { port, done, thread })
    }
    /// The request's head, once the server has let go of its connection.
    fn finish(self) -> Result<String, Box<dyn std::error::Error>> {
        // The server may already be gone.
        let _ = self.done.send(());
        Ok(self.thread.join().map_err(|_| "the server panicked")??)
    }
}

fn serve(listener: &TcpListener, script: Script, held: &Receiver<()>) -> std::io::Result<String> {
    let (mut stream, _) = listener.accept()?;
    stream.set_read_timeout(Some(PATIENCE))?;
    if let Script::Unasked(bytes) = script {
        stream.write_all(bytes)?;
    }
    let head = read_head(&mut stream)?;
    match script {
        Script::Answer(bytes) => stream.write_all(bytes)?,
        Script::Silent => hold(held),
        Script::Stall(bytes) => {
            stream.write_all(bytes)?;
            stream.flush()?;
            hold(held);
        }
        Script::Drop | Script::Unasked(_) => {}
    }
    Ok(head)
}

/// Keeps the connection open until the test lets go, or gives up.
fn hold(held: &Receiver<()>) {
    // A test that failed dropped its sender, which also ends the wait.
    let _ = held.recv_timeout(PATIENCE);
}

fn read_head(stream: &mut TcpStream) -> std::io::Result<String> {
    let mut request = Vec::new();
    let mut chunk = [0; 1024];
    while !request.windows(4).any(|window| window == b"\r\n\r\n") {
        let count = stream.read(&mut chunk)?;
        if count == 0 {
            break;
        }
        request.extend_from_slice(&chunk[..count]);
    }
    Ok(String::from_utf8_lossy(&request).into_owned())
}

const OK: &[u8] = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}";

fn request<'a>(port: u16, headers: &'a [(&'a str, &'a str)]) -> Request<'a> {
    Request {
        host: "127.0.0.1",
        port,
        tls: false,
        method: "GET",
        target: "/2015-03-31/functions/my-fn/configuration",
        headers,
        signing: None,
        connect_timeout: TIMEOUT,
        read_timeout: TIMEOUT,
    }
}

#[test]
fn a_delegate_signs_a_request_outside_the_s3_client() -> TestResult {
    let server = Server::start(Script::Answer(OK))?;
    let runtime = runtime(false)?;
    let host = format!("127.0.0.1:{}", server.port);
    let headers = [("Host", host.as_str())];
    let signed = Request {
        signing: Some(Signing {
            region: "us-west-2",
            service: "lambda",
        }),
        ..request(server.port, &headers)
    };
    let response = runtime.http_client().send(&signed);
    assert_eq!(
        response,
        Ok(Response {
            status: 200,
            body: b"{}".to_vec()
        })
    );
    drop(runtime);
    let sent = server.finish()?;
    assert!(
        sent.starts_with("GET /2015-03-31/functions/my-fn/configuration HTTP/1.1\r\n"),
        "{sent}"
    );
    let lower = sent.to_ascii_lowercase();
    assert!(
        lower.contains("authorization: aws4-hmac-sha256 credential=akiddelegate/"),
        "{sent}"
    );
    assert!(lower.contains("/us-west-2/lambda/aws4_request"), "{sent}");
    assert!(lower.contains("x-amz-security-token: delegate-token\r\n"));
    Ok(())
}

#[test]
fn a_failed_query_fails_the_request_before_it_connects() -> TestResult {
    let runtime = runtime(true)?;
    let signed = Request {
        signing: Some(Signing {
            region: "us-west-2",
            service: "lambda",
        }),
        ..request(9, &[])
    };
    assert_eq!(
        runtime.http_client().send(&signed),
        Err(Error::Connect(NO_CREDENTIALS_ERROR_CODE))
    );
    Ok(())
}

/// The request goes out as it was given: unsigned, its headers in order,
/// an empty one among them, and nothing added.
#[test]
fn an_unsigned_request_is_sent_as_given_and_its_body_is_read() -> TestResult {
    let server = Server::start(Script::Answer(
        b"HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n\r\nnot there",
    ))?;
    let runtime = runtime(true)?;
    let headers = [
        ("Host", "metadata.example"),
        ("Accept-Encoding", "identity"),
        ("x-aws-ec2-metadata-token", ""),
        ("User-Agent", "aws-cli/2.0.0"),
        ("Content-Length", "0"),
    ];
    let put = Request {
        method: "PUT",
        target: "http://metadata.example/latest/api/token",
        ..request(server.port, &headers)
    };
    assert_eq!(
        runtime.http_client().send(&put),
        Ok(Response {
            status: 404,
            body: b"not there".to_vec()
        })
    );
    drop(runtime);
    assert_eq!(
        server.finish()?,
        "PUT http://metadata.example/latest/api/token HTTP/1.1\r\n\
         Host: metadata.example\r\n\
         Accept-Encoding: identity\r\n\
         x-aws-ec2-metadata-token: \r\n\
         User-Agent: aws-cli/2.0.0\r\n\
         Content-Length: 0\r\n\r\n"
    );
    Ok(())
}

#[test]
fn a_chunked_body_is_read_whole() -> TestResult {
    let server = Server::start(Script::Answer(
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n\
          4\r\nrole\r\n5\r\n-name\r\n0\r\n\r\n",
    ))?;
    let runtime = runtime(true)?;
    let response = runtime.http_client().send(&request(server.port, &[]))?;
    assert_eq!(response.body, b"role-name");
    drop(runtime);
    server.finish()?;
    Ok(())
}

/// Nothing listens on the port once the listener is gone. Windows refuses
/// a loopback connect only after it has sent the SYN again, about two
/// seconds on, so the connect timeout is the long one.
#[test]
fn a_refused_connection_is_a_connect_error() -> TestResult {
    let port = TcpListener::bind("127.0.0.1:0")?.local_addr()?.port();
    let runtime = runtime(true)?;
    let refused = runtime.http_client().send(&Request {
        connect_timeout: PATIENCE,
        ..request(port, &[])
    });
    assert_eq!(
        refused,
        Err(Error::Connect(crt_sys::AWS_IO_SOCKET_CONNECTION_REFUSED))
    );
    Ok(())
}

/// A listener whose backlog is full leaves a connect unanswered, and the
/// CRT gives it up at the connect timeout.
#[test]
#[cfg(target_os = "linux")]
fn a_connect_that_is_not_answered_ends_at_the_connect_timeout() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    // Never accepted, these fill the queue of completed connections.
    let mut filling = Vec::new();
    for _ in 0..512 {
        let pending = TcpStream::connect_timeout(&address, Duration::from_millis(100));
        match pending {
            Ok(stream) => filling.push(stream),
            Err(_) => break,
        }
    }
    let runtime = runtime(true)?;
    let started = Instant::now();
    let unanswered = runtime.http_client().send(&request(address.port(), &[]));
    assert_eq!(
        unanswered,
        Err(Error::Connect(super::SOCKET_TIMEOUT_ERROR_CODE))
    );
    assert!(started.elapsed() < PATIENCE);
    Ok(())
}

/// The server never answers: the wait ends at the read timeout while the
/// server still holds the connection.
#[test]
fn a_response_that_never_starts_ends_at_the_read_timeout() -> TestResult {
    let server = Server::start(Script::Silent)?;
    let runtime = runtime(true)?;
    let started = Instant::now();
    let silent = runtime.http_client().send(&request(server.port, &[]));
    let waited = started.elapsed();
    assert_eq!(silent, Err(Error::ReadTimeout));
    assert!(waited >= TIMEOUT && waited < PATIENCE, "{waited:?}");
    drop(runtime);
    server.finish()?;
    Ok(())
}

/// The server sends its headers and part of the body, then stalls: the
/// call is abandoned at the read timeout, and the runtime's drop does not
/// wait for the server, which still holds the connection.
#[test]
fn a_stalled_body_is_abandoned_and_the_runtime_drops() -> TestResult {
    let server = Server::start(Script::Stall(
        b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\npartial",
    ))?;
    let runtime = runtime(true)?;
    let started = Instant::now();
    let stalled = runtime.http_client().send(&request(server.port, &[]));
    assert_eq!(stalled, Err(Error::ReadTimeout));
    drop(runtime);
    assert!(started.elapsed() < PATIENCE);
    server.finish()?;
    Ok(())
}

/// The server takes the connection and never answers the ClientHello.
/// The CRT gives the handshake up after the connect timeout, which bounds
/// it as well, while the server still holds the connection; the read
/// timeout, far longer here, has not begun.
#[test]
fn a_tls_handshake_that_stalls_ends_at_the_connect_timeout() -> TestResult {
    let server = Server::start(Script::Silent)?;
    let runtime = runtime(true)?;
    let started = Instant::now();
    let stalled = runtime.http_client().send(&Request {
        tls: true,
        read_timeout: PATIENCE,
        ..request(server.port, &[])
    });
    let waited = started.elapsed();
    assert_eq!(stalled, Err(Error::Connect(super::TLS_TIMEOUT_ERROR_CODE)));
    assert!(waited >= TIMEOUT && waited < PATIENCE, "{waited:?}");
    drop(runtime);
    assert!(started.elapsed() < PATIENCE);
    server.finish()?;
    Ok(())
}

/// A handshake that fails, here on the server's fatal alert, is a connect
/// error at once, not at the handshake's timeout, and no request is sent.
#[test]
fn a_tls_handshake_that_fails_is_a_connect_error() -> TestResult {
    // One TLS 1.2 alert record: fatal, handshake_failure.
    const ALERT: &[u8] = b"\x15\x03\x03\x00\x02\x02\x28";
    let server = Server::start(Script::Unasked(ALERT))?;
    let runtime = runtime(true)?;
    let failed = runtime.http_client().send(&Request {
        tls: true,
        connect_timeout: Duration::from_secs(5),
        ..request(server.port, &[])
    });
    assert_eq!(
        failed,
        Err(Error::Connect(
            crt_sys::AWS_IO_TLS_ERROR_NEGOTIATION_FAILURE
        ))
    );
    drop(runtime);
    assert!(!server.finish()?.contains("GET "));
    Ok(())
}

#[test]
fn a_connection_closed_without_a_response_is_a_response_error() -> TestResult {
    let server = Server::start(Script::Drop)?;
    let runtime = runtime(true)?;
    let dropped = runtime.http_client().send(&request(server.port, &[]));
    assert!(matches!(dropped, Err(Error::Response(_))), "{dropped:?}");
    drop(runtime);
    server.finish()?;
    Ok(())
}

/// A runtime dropped while a request waits closes the request's
/// connection, so neither the drop nor the request waits out the read
/// timeout, which here is longer than the test allows.
#[test]
fn a_runtime_drop_ends_a_request_in_flight() -> TestResult {
    let server = Server::start(Script::Silent)?;
    let runtime = runtime(true)?;
    let client = runtime.http_client();
    let port = server.port;
    let (sent, outcome) = channel();
    let sender = std::thread::spawn(move || {
        let slow = Request {
            read_timeout: PATIENCE * 10,
            ..request(port, &[])
        };
        // The receiver is there until the test has the outcome.
        let _ = sent.send(client.send(&slow));
    });
    // The request is in flight once the server has read it.
    let started = Instant::now();
    std::thread::sleep(TIMEOUT);
    drop(runtime);
    let ended = outcome.recv_timeout(PATIENCE)?;
    assert!(matches!(ended, Err(Error::Response(_))), "{ended:?}");
    assert!(started.elapsed() < PATIENCE);
    sender.join().map_err(|_| "the sender panicked")?;
    server.finish()?;
    Ok(())
}

/// aws-c-http will not send a header value that holds a control character,
/// and says so once the connection is up: nothing reaches the server.
#[test]
fn a_request_aws_c_http_refuses_is_not_sent() -> TestResult {
    let server = Server::start(Script::Drop)?;
    let runtime = runtime(true)?;
    let headers = [("x-aws-ec2-metadata-token", "to\u{1}ken")];
    let refused = runtime.http_client().send(&request(server.port, &headers));
    assert!(
        matches!(refused, Err(Error::Connect(code)) if super::is_refusal(code)),
        "{refused:?}"
    );
    drop(runtime);
    assert_eq!(server.finish()?, "");
    Ok(())
}

#[test]
fn a_client_that_outlives_its_runtime_is_closed() -> TestResult {
    let runtime = runtime(true)?;
    let client = runtime.http_client();
    drop(runtime);
    assert_eq!(client.send(&request(9, &[])), Err(Error::Closed));
    Ok(())
}

/// A header's value may be a session token and a target may name
/// credentials, so neither is in what a request shows of itself.
#[test]
fn a_request_s_debug_form_leaves_out_header_values_and_the_target() {
    let headers = [("x-aws-ec2-metadata-token", "MARKER-token")];
    let request = Request {
        target: "http://user:MARKER-password@metadata.example/latest/api/token",
        ..request(80, &headers)
    };
    let debug = format!("{request:?}");
    assert!(!debug.contains("MARKER"), "{debug}");
    assert!(debug.contains("x-aws-ec2-metadata-token"), "{debug}");
    assert!(
        debug.contains("127.0.0.1") && debug.contains("GET"),
        "{debug}"
    );
}

/// A body may be a session token or a document of credentials.
#[test]
fn a_response_s_debug_form_leaves_out_the_body() {
    let response = Response {
        status: 200,
        body: br#"{"SecretAccessKey": "MARKER-secret"}"#.to_vec(),
    };
    let debug = format!("{response:?}");
    assert!(!debug.contains("MARKER"), "{debug}");
    assert!(debug.contains("200") && debug.contains("36"), "{debug}");
}
