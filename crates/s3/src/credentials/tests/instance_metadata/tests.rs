//! The chain's last provider, answered by the CRT from a stand-in metadata
//! service on loopback, onto the wire and through a refresh.
use super::super::{MINUTE, TestResult, access_key, clock, list, parse, serve};
use crate::credentials::Chain;
use ::credentials::{InstanceMetadataSettings, Profile, Transport, TransportError};
use cli_core::proxy::{Forward, ForwardProxy};
use cli_core::{EnvMap, SnapshotEnv};
use crt::s3::NO_CREDENTIALS_ERROR_CODE;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::JoinHandle;
use std::time::Duration;

const ROLE_PATH: &str = "/latest/meta-data/iam/security-credentials/";
const LOOPBACK: &str = "http://127.0.0.1:";
/// The service's default base URL, without its last slash
/// (`METADATA_BASE_URL`).
const INSTANCE: &str = "http://169.254.169.254";

/// The document the service holds on the `turn`th fetch: a key, secret and
/// token of that turn, which expire `turn` hours after eight.
fn document(turn: usize) -> String {
    format!(
        r#"{{"Code": "Success", "Type": "AWS-HMAC", "AccessKeyId": "AKIDIMDS{turn}",
            "SecretAccessKey": "imds-secret-{turn}", "Token": "imds-token-{turn}",
            "Expiration": "2037-10-21T{:02}:00:00Z"}}"#,
        8 + turn
    )
}

/// A stand-in metadata service, which also stands for a proxy in front of
/// one. It issues a token, names one role, and answers each request for
/// that role's credentials with the next of its documents, then with 404.
struct Service {
    address: SocketAddr,
    stop: Arc<AtomicBool>,
    thread: JoinHandle<std::io::Result<Vec<String>>>,
}

impl Service {
    fn start(documents: Vec<String>) -> std::io::Result<Self> {
        Self::start_with_token(documents, true)
    }
    /// A service that has no token to issue when `token` is false, as one
    /// that speaks only the first version of its protocol.
    fn start_with_token(documents: Vec<String>, token: bool) -> std::io::Result<Self> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let stop = Arc::new(AtomicBool::new(false));
        let stopped = Arc::clone(&stop);
        let thread = std::thread::spawn(move || answer(&listener, documents, token, &stopped));
        Ok(Self {
            address,
            stop,
            thread,
        })
    }
    /// An environment that names this service as the instance's.
    fn env(&self, more: &[(&str, &str)]) -> SnapshotEnv {
        let endpoint = format!("http://{}", self.address);
        let named = [("AWS_EC2_METADATA_SERVICE_ENDPOINT", endpoint.as_str())];
        SnapshotEnv::from_pairs(named.into_iter().chain(more.iter().copied()))
    }
    /// An environment whose proxy for the instance's own address is this
    /// service.
    fn proxy_env(&self) -> SnapshotEnv {
        let proxy = format!("http://{}", self.address);
        SnapshotEnv::from_pairs([("HTTP_PROXY", proxy.as_str())])
    }
    /// Stops the service and returns the method and target of each request
    /// it answered.
    fn finish(self) -> Result<Vec<String>, Box<dyn std::error::Error>> {
        self.stop.store(true, Ordering::SeqCst);
        // Wakes the accept the thread waits in.
        drop(TcpStream::connect(self.address)?);
        Ok(self.thread.join().map_err(|_| "the service panicked")??)
    }
}

fn answer(
    listener: &TcpListener,
    documents: Vec<String>,
    token: bool,
    stop: &AtomicBool,
) -> std::io::Result<Vec<String>> {
    let mut documents = documents.into_iter();
    let mut answered = Vec::new();
    loop {
        let (mut stream, _) = listener.accept()?;
        if stop.load(Ordering::SeqCst) {
            return Ok(answered);
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
        let request = String::from_utf8_lossy(&request).into_owned();
        let line = request.lines().next().unwrap_or_default();
        let line = line.trim_end_matches(" HTTP/1.1");
        // A proxy is sent the service's whole URL.
        let path = line.replacen(INSTANCE, "", 1);
        let body = match path.as_str() {
            "PUT /latest/api/token" => token.then(|| "metadata-token".to_owned()),
            _ if path == format!("GET {ROLE_PATH}") => Some("example-role".to_owned()),
            _ if path == format!("GET {ROLE_PATH}example-role") => documents.next(),
            _ => None,
        };
        let status = if body.is_some() {
            "200 OK"
        } else {
            "404 Not Found"
        };
        let body = body.unwrap_or_default();
        write!(
            stream,
            "HTTP/1.1 {status}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
            body.len()
        )?;
        answered.push(line.to_owned());
    }
}

/// The requests of `fetches` fetches, each to the service at `base`: a
/// token, the role's name, and the role's credentials
/// (`retrieve_iam_role_credentials`).
fn fetched_from(base: &str, fetches: usize) -> Vec<String> {
    let round = [
        format!("PUT {base}/latest/api/token"),
        format!("GET {base}{ROLE_PATH}"),
        format!("GET {base}{ROLE_PATH}example-role"),
    ];
    std::iter::repeat_n(round, fetches).flatten().collect()
}

/// [`fetched_from`] the service itself.
fn fetched(fetches: usize) -> Vec<String> {
    fetched_from("", fetches)
}

/// A runtime that signs with what the default chain finds in `env`, whose
/// last provider asks the service `env` names.
struct Signed {
    runtime: crt::Runtime,
    resolved: Chain,
    /// The clock the credentials are compared with, in seconds since the
    /// epoch; it starts at seven.
    seconds: Arc<AtomicU64>,
    /// The S3 endpoint, which stops after the listings it was started for.
    server: JoinHandle<std::io::Result<Vec<String>>>,
}

impl Signed {
    /// The chain is walked before the runtime exists, as a command walks
    /// it, and the runtime it then signs for asks the service.
    fn start(env: &SnapshotEnv, listings: usize) -> Result<Self, Box<dyn std::error::Error>> {
        let files = parse(b"", b"");
        let settings = InstanceMetadataSettings::resolve(env, &files, "default")?;
        // Never the instance's own address, unless a loopback proxy stands
        // in front of it.
        let proxied = env
            .var("HTTP_PROXY")
            .is_some_and(|proxy| proxy.starts_with(LOOPBACK));
        let direct = settings.base_url.replacen("https://", "http://", 1);
        assert!(direct.starts_with(LOOPBACK) || proxied);
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let server = std::thread::spawn(move || serve(listener, listings));
        let (clock, seconds) = clock();
        let profile = Profile::Ambient("default");
        let resolved = Chain::walk_with_clock(env, &files, profile, Some(clock))?;
        let runtime = crt::Runtime::new(crt::RuntimeOptions {
            endpoint_url: format!("http://{address}/bucket"),
            credentials: resolved.source(),
            event_loop_count: 1,
            ..crt::RuntimeOptions::default()
        })?;
        Ok(Self {
            runtime,
            resolved,
            seconds,
            server,
        })
    }
    /// Drops the runtime and returns the listings the S3 endpoint saw.
    fn finish(self) -> Result<Vec<String>, Box<dyn std::error::Error>> {
        drop(self.runtime);
        Ok(self
            .server
            .join()
            .map_err(|_| "the S3 endpoint panicked")??)
    }
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn the_instance_roles_credentials_sign_a_request_through_the_delegate() -> TestResult {
    let service = Service::start(vec![document(0)])?;
    let signed = Signed::start(&service.env(&[]), 1)?;
    assert_eq!(signed.resolved.method(), Some("iam-role"));
    assert_eq!(list(&signed.runtime), 0);
    // The chain holds the role's credentials and the way to the service,
    // and shows neither the secret nor either token.
    let debug = format!("{:?}", signed.resolved);
    for secret in ["imds-secret-0", "imds-token-0", "metadata-token"] {
        assert!(!debug.contains(secret), "{debug}");
    }
    assert!(debug.contains("AKIDIMDS0"), "{debug}");
    let listings = signed.finish()?;
    let listing = listings.first().ok_or("the S3 endpoint saw no request")?;
    assert_eq!(access_key(listing), Some("AKIDIMDS0"));
    let lower = listing.to_ascii_lowercase();
    assert!(
        lower.contains("x-amz-security-token: imds-token-0\r\n"),
        "{listing}"
    );
    assert!(!listing.contains("imds-secret-0"));
    assert_eq!(service.finish()?, fetched(1));
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_chain_that_resolves_earlier_never_contacts_the_service() -> TestResult {
    let service = Service::start(vec![document(0)])?;
    let keys = [
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
    ];
    let signed = Signed::start(&service.env(&keys), 1)?;
    assert_eq!(signed.resolved.method(), Some("env"));
    assert_eq!(list(&signed.runtime), 0);
    let listings = signed.finish()?;
    assert_eq!(
        listings.first().and_then(|l| access_key(l)),
        Some("AKIDENV")
    );
    assert_eq!(service.finish()?, Vec::<String>::new());
    Ok(())
}

/// A refresh asks the service again, token and all, and only inside
/// botocore's windows.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn credentials_that_come_due_are_fetched_again_from_the_service() -> TestResult {
    let service = Service::start(vec![document(0), document(1)])?;
    let signed = Signed::start(&service.env(&[]), 3)?;
    // An hour left, then sixteen minutes: no refresh.
    assert_eq!(list(&signed.runtime), 0);
    signed.seconds.fetch_add(44 * MINUTE, Ordering::SeqCst);
    assert_eq!(list(&signed.runtime), 0);
    // Fourteen minutes left, the advisory window: this request waits for
    // the refresh it starts and is signed with what that returns.
    signed.seconds.fetch_add(2 * MINUTE, Ordering::SeqCst);
    assert_eq!(list(&signed.runtime), 0);
    assert_eq!(signed.resolved.refresh_error(), None);
    // Fourteen minutes left on the second set, and the service has no
    // third. botocore's fetcher returns nothing for that, which fails the
    // request in the advisory window too
    // (`RefreshableCredentials._protected_refresh`).
    signed.seconds.fetch_add(60 * MINUTE, Ordering::SeqCst);
    assert_eq!(list(&signed.runtime), NO_CREDENTIALS_ERROR_CODE);
    assert_eq!(
        signed
            .resolved
            .refresh_error()
            .map(|error| error.to_string()),
        Some(
            "Error when retrieving credentials from iam-role: Credential refresh failed, \
             response did not contain: access_key, secret_key, token, expiry_time"
                .into()
        )
    );
    let listings = signed.finish()?;
    let keys: Vec<_> = listings.iter().map(|listing| access_key(listing)).collect();
    assert_eq!(keys, ["AKIDIMDS0", "AKIDIMDS0", "AKIDIMDS1"].map(Some));
    let lower = listings.last().map(|listing| listing.to_ascii_lowercase());
    assert!(lower.is_some_and(|l| l.contains("x-amz-security-token: imds-token-1\r\n")));
    assert_eq!(service.finish()?, fetched(3));
    Ok(())
}

/// botocore's provider passes for a service that is disabled, cannot be
/// reached or has no credentials (`InstanceMetadataProvider.load`), and its
/// chain then raises `NoCredentialsError`, which each request here fails with.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_service_with_nothing_to_give_leaves_the_chain_with_nothing() -> TestResult {
    let disabled = [("AWS_EC2_METADATA_DISABLED", "true")];
    for (documents, more, requests) in [
        // The role has no credentials: the fetcher asks for them, gets 404,
        // and has no attempt left.
        (vec![], &[][..], fetched(1)),
        // The service has them and is never asked.
        (vec![document(0)], &disabled[..], vec![]),
    ] {
        let service = Service::start(documents)?;
        let signed = Signed::start(&service.env(more), 0)?;
        assert_eq!(signed.resolved.method(), None);
        assert_eq!(list(&signed.runtime), NO_CREDENTIALS_ERROR_CODE);
        assert_eq!(signed.resolved.refresh_error(), None);
        signed.finish()?;
        assert_eq!(service.finish()?, requests);
    }
    // Nothing listens where the service should be.
    let gone = Service::start(vec![])?;
    let env = gone.env(&[]);
    gone.finish()?;
    let signed = Signed::start(&env, 0)?;
    assert_eq!(signed.resolved.method(), None);
    assert_eq!(list(&signed.runtime), NO_CREDENTIALS_ERROR_CODE);
    signed.finish()?;
    Ok(())
}

/// A command may build a client only to validate it, and then the client
/// that sends its requests. The first asks the service, and a refresh asks
/// through the one that is left.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_refresh_asks_through_the_runtime_that_is_still_there() -> TestResult {
    let service = Service::start(vec![document(0), document(1)])?;
    let (clock, seconds) = clock();
    let profile = Profile::Ambient("default");
    let chain = Chain::walk_with_clock(&service.env(&[]), &parse(b"", b""), profile, Some(clock))?;
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let server = std::thread::spawn(move || serve(listener, 1));
    let options = || crt::RuntimeOptions {
        endpoint_url: format!("http://{address}/bucket"),
        credentials: chain.source(),
        event_loop_count: 1,
        ..crt::RuntimeOptions::default()
    };
    drop(crt::Runtime::new(options())?);
    assert_eq!(chain.method(), Some("iam-role"));
    let runtime = crt::Runtime::new(options())?;
    // Fourteen minutes left: the request waits for a refresh.
    seconds.fetch_add(46 * MINUTE, Ordering::SeqCst);
    assert_eq!(list(&runtime), 0);
    assert_eq!(chain.refresh_error(), None);
    drop(runtime);
    let listings = server.join().map_err(|_| "the S3 endpoint panicked")??;
    assert_eq!(
        listings.first().and_then(|l| access_key(l)),
        Some("AKIDIMDS1")
    );
    assert_eq!(service.finish()?, fetched(2));
    Ok(())
}

/// botocore's fetcher takes the environment's proxy for its own URL
/// (`IMDSFetcher.__init__`), and a forwarding proxy is sent that URL whole.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn the_service_is_asked_through_the_environment_s_proxy() -> TestResult {
    let proxy = Service::start(vec![document(0)])?;
    let signed = Signed::start(&proxy.proxy_env(), 1)?;
    assert_eq!(signed.resolved.method(), Some("iam-role"));
    assert_eq!(list(&signed.runtime), 0);
    let listings = signed.finish()?;
    assert_eq!(
        listings.first().and_then(|l| access_key(l)),
        Some("AKIDIMDS0")
    );
    assert_eq!(proxy.finish()?, fetched_from(INSTANCE, 1));
    Ok(())
}

/// An error botocore's fetcher raises stops the chain as the client is
/// created (`Session.create_client`): the runtime is not built, and the chain
/// keeps botocore's error for the command to print.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_fetch_that_raises_fails_the_runtime_with_botocore_s_error() -> TestResult {
    let service = Service::start_with_token(vec![document(0)], false)?;
    let env = service.env(&[("AWS_EC2_METADATA_V1_DISABLED", "true")]);
    let chain = Chain::walk(&env, &parse(b"", b""), Profile::Ambient("default"))?;
    let source = chain.source();
    assert_eq!(source.failure(), None);
    let options = || crt::RuntimeOptions {
        endpoint_url: "http://127.0.0.1:9/bucket".into(),
        credentials: source.clone(),
        event_loop_count: 1,
        ..crt::RuntimeOptions::default()
    };
    // A second client of the same command fails the same way, unasked.
    for _ in 0..2 {
        let refused = crt::Runtime::new(options()).map(drop);
        assert_eq!(
            refused.map_err(|failure| failure.error_code),
            Err(NO_CREDENTIALS_ERROR_CODE)
        );
    }
    assert_eq!(
        source.failure().as_deref(),
        Some(
            "Error retrieving metadata: Unable to retrieve token for use in IMDSv2 call and \
             IMDSv1 has been disabled"
        )
    );
    assert_eq!(chain.method(), None);
    assert_eq!(service.finish()?, ["PUT /latest/api/token"]);
    Ok(())
}

/// A stand-in that finishes no TLS handshake. It answers each connection
/// with a fatal alert, or with nothing, and holds it until the client
/// closes.
struct Handshakes {
    address: SocketAddr,
    stop: Arc<AtomicBool>,
    thread: JoinHandle<std::io::Result<usize>>,
}

impl Handshakes {
    fn start(alert: bool) -> std::io::Result<Self> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let stop = Arc::new(AtomicBool::new(false));
        let stopped = Arc::clone(&stop);
        let thread = std::thread::spawn(move || refuse(&listener, alert, &stopped));
        Ok(Self {
            address,
            stop,
            thread,
        })
    }
    /// Stops the stand-in and returns how many connections it took.
    fn finish(self) -> Result<usize, Box<dyn std::error::Error>> {
        self.stop.store(true, Ordering::SeqCst);
        // Wakes the accept the thread waits in.
        drop(TcpStream::connect(self.address)?);
        Ok(self.thread.join().map_err(|_| "the stand-in panicked")??)
    }
}

fn refuse(listener: &TcpListener, alert: bool, stop: &AtomicBool) -> std::io::Result<usize> {
    let mut taken = 0;
    loop {
        let (mut stream, _) = listener.accept()?;
        if stop.load(Ordering::SeqCst) {
            return Ok(taken);
        }
        taken += 1;
        stream.set_read_timeout(Some(Duration::from_secs(10)))?;
        if alert {
            // One TLS 1.2 alert record: fatal, handshake_failure.
            stream.write_all(b"\x15\x03\x03\x00\x02\x02\x28")?;
        }
        // Until the client gives the handshake up and closes.
        let mut sink = [0; 1024];
        while matches!(stream.read(&mut sink), Ok(count) if count != 0) {}
    }
}

/// An `https` endpoint is verified with the runtime's trust, and one whose
/// handshake fails, as it does for a certificate that trust does not
/// verify, is a service that cannot be reached: botocore's fetcher tries
/// each request as often as its settings say (`IMDSFetcher._get_request`), and
/// the chain is left with nothing.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn an_https_service_whose_handshake_fails_leaves_the_chain_with_nothing() -> TestResult {
    let endpoint = Handshakes::start(true)?;
    let url = format!("https://{}", endpoint.address);
    let env = SnapshotEnv::from_pairs([
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", url.as_str()),
        ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "2"),
    ]);
    let signed = Signed::start(&env, 0)?;
    assert_eq!(signed.resolved.method(), None);
    assert_eq!(list(&signed.runtime), NO_CREDENTIALS_ERROR_CODE);
    signed.finish()?;
    // The token, then the role's name without one, twice each.
    assert_eq!(endpoint.finish()?, 4);
    Ok(())
}

/// What the transport answers for an `https` URL, with a timeout far
/// shorter than a setting can name: a handshake that fails is a
/// connection that could not be made, one that stalls ends at the timeout
/// as a connect that timed out, and a proxy for such a URL, which would be
/// a tunnel, is not asked.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn the_transport_names_a_handshake_that_fails_or_stalls_as_a_connection_s() -> TestResult {
    const TIMEOUT: Duration = Duration::from_millis(200);
    let runtime = crt::Runtime::new(crt::RuntimeOptions {
        endpoint_url: "http://127.0.0.1:9/bucket".into(),
        event_loop_count: 1,
        ..crt::RuntimeOptions::default()
    })?;
    let session = |forward| crate::credentials::Service {
        forward,
        clients: Mutex::new(vec![runtime.http_client()]),
    };
    let token = |address: SocketAddr| ::credentials::Request {
        method: "PUT",
        url: format!("https://{address}/latest/api/token"),
        headers: Vec::new(),
    };
    for (alert, error) in [
        (true, TransportError::Connect),
        (false, TransportError::ConnectTimeout),
    ] {
        let endpoint = Handshakes::start(alert)?;
        let started = std::time::Instant::now();
        let answer = session(Forward::Direct).send(&token(endpoint.address), TIMEOUT);
        let waited = started.elapsed();
        assert_eq!(answer.map(drop), Err(error));
        assert!(alert || waited >= TIMEOUT, "{waited:?}");
        assert!(waited < Duration::from_secs(5), "{waited:?}");
        assert_eq!(endpoint.finish()?, 1);
    }
    let endpoint = Handshakes::start(true)?;
    let proxy = ForwardProxy::parse(&format!("http://{}", endpoint.address));
    let proxy = proxy.ok_or("the proxy's URL does not parse")?;
    let tunnelled = session(Forward::Proxy(proxy)).send(&token(endpoint.address), TIMEOUT);
    assert!(
        matches!(tunnelled, Err(TransportError::Client { .. })),
        "{tunnelled:?}"
    );
    assert_eq!(endpoint.finish()?, 0);
    Ok(())
}

/// A header value with a line end, which only a token the service sent
/// could hold, is one aws-c-http refuses to send. The error names its
/// reason, never the value.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_header_value_with_a_line_end_is_refused_without_being_shown() -> TestResult {
    // Takes the connection; the request is refused before it is written.
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let runtime = crt::Runtime::new(crt::RuntimeOptions {
        endpoint_url: "http://127.0.0.1:9/bucket".into(),
        event_loop_count: 1,
        ..crt::RuntimeOptions::default()
    })?;
    let session = crate::credentials::Service {
        forward: Forward::Direct,
        clients: Mutex::new(vec![runtime.http_client()]),
    };
    let request = ::credentials::Request {
        method: "GET",
        url: format!("http://{}{ROLE_PATH}", listener.local_addr()?),
        headers: vec![("x-aws-ec2-metadata-token", "MARKER-token\n".to_owned())],
    };
    let answer = session.send(&request, Duration::from_secs(2));
    let Err(TransportError::Client { reason }) = answer else {
        return Err(format!("{answer:?}").into());
    };
    assert!(!reason.is_empty() && !reason.contains("MARKER"), "{reason}");
    Ok(())
}

/// A proxy for the service that the transport does not use leaves the
/// service unasked. The fetch ends at once, whatever attempts are
/// configured, as it does for a service that cannot be reached: the chain
/// is left with nothing, or, without IMDSv1, with botocore's error for a
/// fetch that has no token. A proxy the transport would use in front of an
/// `https` endpoint is a tunnel, and that fetch fails with an error that
/// says so. Nothing is sent to the proxy either way, and no error names any
/// part of its URL.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_proxy_the_transport_does_not_use_leaves_the_service_unasked() -> TestResult {
    const V1_DISABLED: &str = "Error retrieving metadata: Unable to retrieve token for use in \
        IMDSv2 call and IMDSv1 has been disabled";
    const TUNNEL: &str = "An HTTP Client raised an unhandled exception: cannot ask the instance \
        metadata service for credentials: an https endpoint is not supported through a proxy";
    const ENDPOINT: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT";
    const CLEARTEXT: (&str, &str) = (ENDPOINT, "http://127.0.0.1:9");
    const SECURE: (&str, &str) = (ENDPOINT, "https://127.0.0.1:9");
    const NO_V1: (&str, &str) = ("AWS_EC2_METADATA_V1_DISABLED", "true");
    let proxy = Handshakes::start(false)?;
    let port = proxy.address.port();
    let login = format!("http://user:secret@127.0.0.1:{port}");
    let secure = format!("https://127.0.0.1:{port}");
    let plain = format!("http://127.0.0.1:{port}");
    let environment = |pairs: &[(&'static str, &str)]| {
        let attempts = ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "3");
        SnapshotEnv::from_pairs(pairs.iter().copied().chain([attempts]))
    };
    for pairs in [
        [CLEARTEXT, ("HTTP_PROXY", login.as_str())],
        [CLEARTEXT, ("HTTP_PROXY", secure.as_str())],
        [SECURE, ("HTTPS_PROXY", login.as_str())],
    ] {
        let signed = Signed::start(&environment(&pairs), 0)?;
        assert_eq!(signed.resolved.method(), None, "{pairs:?}");
        assert_eq!(signed.resolved.load_error(), None, "{pairs:?}");
        assert_eq!(list(&signed.runtime), NO_CREDENTIALS_ERROR_CODE);
        signed.finish()?;
    }
    for (pairs, message) in [
        (
            &[CLEARTEXT, ("HTTP_PROXY", login.as_str()), NO_V1][..],
            V1_DISABLED,
        ),
        (&[SECURE, ("HTTPS_PROXY", plain.as_str())], TUNNEL),
    ] {
        let chain = Chain::walk(
            &environment(pairs),
            &parse(b"", b""),
            Profile::Ambient("default"),
        )?;
        let source = chain.source();
        let refused = crt::Runtime::new(crt::RuntimeOptions {
            endpoint_url: "http://127.0.0.1:9/bucket".into(),
            credentials: source.clone(),
            event_loop_count: 1,
            ..crt::RuntimeOptions::default()
        });
        assert_eq!(
            refused.map(drop).map_err(|failure| failure.error_code),
            Err(NO_CREDENTIALS_ERROR_CODE),
            "{pairs:?}"
        );
        assert_eq!(source.failure().as_deref(), Some(message), "{pairs:?}");
        assert_eq!(chain.method(), None);
    }
    assert_eq!(proxy.finish()?, 0);
    Ok(())
}
