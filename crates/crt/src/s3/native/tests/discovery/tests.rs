use super::super::*;
use crate::RuntimeOptions;
use cli_core::interrupt::State;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::time::{Duration, Instant};

type TestResult = Result<(), Box<dyn std::error::Error>>;
const TEST_NAME: &str =
    "s3::native::tests::discovery::tests::part_number_discovery_handles_failed_requests";

#[test]
fn part_number_discovery_handles_failed_requests() -> TestResult {
    if std::env::var_os("ZAWS_DISCOVERY_CHILD").is_some() {
        cancel_before_headers()?;
        reject_discovery()?;
        return stale_size_hint();
    }
    let mut child = Command::new(std::env::current_exe()?)
        .args(["--exact", TEST_NAME, "--nocapture"])
        .env("ZAWS_DISCOVERY_CHILD", "1")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    let deadline = Instant::now() + Duration::from_secs(20);
    while child.try_wait()?.is_none() {
        if Instant::now() > deadline {
            child.kill()?;
            let output = child.wait_with_output()?;
            return Err(format!(
                "discovery test timed out: {}",
                String::from_utf8_lossy(&output.stderr)
            )
            .into());
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    let output = child.wait_with_output()?;
    assert!(
        output.status.success(),
        "status={} stdout={} stderr={}",
        output.status,
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    Ok(())
}

fn runtime(listener: &TcpListener) -> Result<Runtime, Box<TransferResult>> {
    Runtime::new(RuntimeOptions {
        endpoint_url: format!(
            "http://{}/bucket",
            listener
                .local_addr()
                .map_err(|_| TransferResult::invalid_argument())?
        ),
        region: "us-east-1".into(),
        credentials: crate::credentials::Source::Delegate(std::sync::Arc::new(Loopback)),
        event_loop_count: 1,
        ..RuntimeOptions::default()
    })
}

/// Answers every query with keys that sign only loopback requests.
#[derive(Debug)]
struct Loopback;

impl crate::credentials::Delegate for Loopback {
    fn credentials(&self, query: crate::credentials::Query) {
        query.complete(crate::credentials::View {
            access_key_id: "loopback-only",
            secret_access_key: "loopback-only",
            session_token: None,
            account_id: None,
            expiration: None,
        });
    }
}

fn options() -> RequestOptions<'static> {
    RequestOptions {
        kind: RequestKind::Get,
        key: b"object",
        filepath: None,
        object_size_hint: Some(1),
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

fn read_request(stream: &mut TcpStream) -> Result<String, std::io::Error> {
    stream.set_read_timeout(Some(Duration::from_secs(5)))?;
    let mut request = Vec::new();
    while !request.ends_with(b"\r\n\r\n") {
        let mut byte = [0];
        stream.read_exact(&mut byte)?;
        request.push(byte[0]);
    }
    Ok(String::from_utf8_lossy(&request).into_owned())
}

fn empty_object_discovery(listener: &TcpListener) -> Result<TcpStream, std::io::Error> {
    let (mut initial, _) = listener.accept()?;
    let request = read_request(&mut initial)?;
    assert!(request.starts_with("GET /bucket/object "));
    assert!(request.to_ascii_lowercase().contains("range: bytes=0-"));
    let body = concat!(
        "<Error><Code>InvalidRange</Code>",
        "<ActualObjectSize>0</ActualObjectSize></Error>",
    );
    write!(
        initial,
        "HTTP/1.1 416 Range Not Satisfiable\r\nContent-Type: application/x\
            ml\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )?;
    drop(initial);
    let (mut discovery, _) = listener.accept()?;
    let request = read_request(&mut discovery)?;
    assert!(request.starts_with("GET /bucket/object?partNumber=1 "));
    Ok(discovery)
}

fn cancel_before_headers() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let runtime = runtime(&listener)?;
    let (seen, observed) = mpsc::channel();
    let (release, held) = mpsc::channel();
    let server = std::thread::spawn(move || -> Result<(), std::io::Error> {
        let stream = empty_object_discovery(&listener)?;
        let _ = seen.send(());
        let _ = held.recv_timeout(Duration::from_secs(10));
        drop(stream);
        Ok(())
    });
    let interrupt = State::new();
    let request = runtime.submit(options(), &interrupt)?;
    observed.recv_timeout(Duration::from_secs(5))?;
    interrupt.request();
    let result = request.wait().transfer;
    let _ = release.send(());
    server.join().map_err(|_| "server panicked")??;
    assert_eq!(result.error_code, CANCELED_ERROR_CODE);
    assert!(result.canceled_by_interrupt);
    Ok(())
}

fn reject_discovery() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let runtime = Arc::new(runtime(&listener)?);
    let server = std::thread::spawn(move || -> Result<(), std::io::Error> {
        let mut stream = empty_object_discovery(&listener)?;
        let body = "<Error><Code>AccessDenied</Code><Message>denied</Message></Error>";
        write!(
            stream,
            "HTTP/1.1 403 Forbidden\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
            body.len()
        )
    });
    let options = RequestOptions {
        object_size_hint: Some(1024),
        ..options()
    };
    let result = transfer(&runtime, options, Box::new(|_| Ok(())))?;
    server.join().map_err(|_| "server panicked")??;
    assert_ne!(result.error_code, 0);
    assert_eq!(result.response_status, 403);
    assert_eq!(result.service_error.code.as_bytes(), b"AccessDenied");
    Ok(())
}

fn stale_size_hint() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let runtime = Arc::new(runtime(&listener)?);
    let server = std::thread::spawn(move || -> Result<(), std::io::Error> {
        for _ in 0..1 {
            let (mut stream, _) = listener.accept()?;
            let request = read_request(&mut stream)?;
            assert!(!request.contains("partNumber=1"));
            write!(
                stream,
                concat!(
                    "HTTP/1.1 206 Partial Content\r\nContent-Length: 4\r\n",
                    "Content-Range: bytes 0-3/4\r\nETag: \"test\"\r\n",
                    "Connection: close\r\n\r\ndata",
                )
            )?;
        }
        Ok(())
    });
    let received = Arc::new(Mutex::new(Vec::new()));
    let result = transfer(&runtime, options(), collect(Arc::clone(&received)))?;
    server.join().map_err(|_| "server panicked")??;
    assert_eq!(result.error_code, 0);
    assert_eq!(&*lock(&received), b"data");
    Ok(())
}
