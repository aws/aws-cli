//! Environment, shared files and a credential process, through the chain,
//! onto the wire, before and after a refresh.
use super::{Chain, Resolved};
use ::credentials::{
    Clock, ContainerFetch, Credentials, LoadError, Loaded, ProcessOutput, ProcessProvider, Profile,
    RefreshError, Refreshable, Resolver, RoleFetcher, Runner, default_resolver,
};
use awscli_config::{Contents, Inputs, ParsedFiles};
use cli_core::SnapshotEnv;
use crt::credentials::{Delegate, Query, Source};
use crt::s3::{ListOptions, NO_CREDENTIALS_ERROR_CODE};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, mpsc};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

type TestResult = Result<(), Box<dyn std::error::Error>>;

/// Answers `count` requests, one connection each, with a single-page
/// listing, and returns the requests' heads in order.
fn serve(listener: TcpListener, count: usize) -> std::io::Result<Vec<String>> {
    let mut requests = Vec::new();
    for _ in 0..count {
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
        let body = b"<ListBucketResult><IsTruncated>false</IsTruncated></ListBucketResult>";
        write!(
            stream,
            "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        )?;
        stream.write_all(body)?;
        requests.push(String::from_utf8_lossy(&request).into_owned());
    }
    Ok(requests)
}

/// The access key in a request's `Authorization` credential scope.
fn access_key(request: &str) -> Option<&str> {
    request.split("Credential=").nth(1)?.split('/').next()
}

/// One listing through the S3 client; the CRT's error code, zero for none.
fn list(runtime: &crt::Runtime) -> i32 {
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
        &mut |_| 0,
    );
    result.transfer.error_code
}

fn parse(config: &[u8], credentials: &[u8]) -> ParsedFiles {
    ParsedFiles::parse(Inputs {
        config: Some(Contents {
            bytes: config,
            source: "config",
        }),
        credentials: Some(Contents {
            bytes: credentials,
            source: "credentials",
        }),
        aliases: None,
    })
}

/// The access key that signs one listing with what the chain finds.
fn signed_access_key(
    env: &SnapshotEnv,
    files: &ParsedFiles,
    profile: Profile<'_>,
) -> Result<String, Box<dyn std::error::Error>> {
    let no_role = RoleFetcher::new(|| Ok(None));
    let no_container = ContainerFetch::new(|_| Ok(None));
    let resolver = default_resolver(env, files, profile, no_container, no_role);
    let resolved = Resolved::load(&resolver)?;
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let server = std::thread::spawn(move || serve(listener, 1));
    let runtime = crt::Runtime::new(crt::RuntimeOptions {
        endpoint_url: format!("http://{address}/bucket"),
        credentials: resolved.source(),
        event_loop_count: 1,
        ..crt::RuntimeOptions::default()
    })?;
    assert_eq!(list(&runtime), 0);
    drop(runtime);
    let requests = server.join().map_err(|_| "loopback server panicked")??;
    let request = requests.first().ok_or("the server saw no request")?;
    Ok(access_key(request)
        .ok_or("the request is unsigned")?
        .to_owned())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn the_chains_credentials_sign_a_native_listing() -> TestResult {
    let files = parse(
        b"[profile dev]\naws_access_key_id = AKIDCONFIGDEV\n\
          aws_secret_access_key = config-secret\n",
        b"[default]\naws_access_key_id = AKIDSHARED\n\
          aws_secret_access_key = shared-secret\n",
    );
    let keys = SnapshotEnv::from_pairs([
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
    ]);
    let empty = SnapshotEnv::default();
    for (env, profile, access_key) in [
        (&keys, Profile::Ambient("default"), "AKIDENV"),
        (&empty, Profile::Ambient("default"), "AKIDSHARED"),
        (&keys, Profile::Explicit("dev"), "AKIDCONFIGDEV"),
    ] {
        assert_eq!(signed_access_key(env, &files, profile)?, access_key);
    }
    Ok(())
}

/// 2037-10-21T07:00:00Z, where the tests' clocks start.
const SEVEN: u64 = 2_139_721_200;
const MINUTE: u64 = 60;

/// The refusal is `str()` of what botocore raises as the CLI's session
/// starts. The literal `int()` refuses is its `repr`.
#[test]
fn a_settings_refusal_is_the_text_python_prints() {
    const INTEGER: &str = "invalid literal for int() with base 10: ";
    let files = parse(b"[default]\nmetadata_service_num_attempts = many\n", b"");
    let refusal = |timeout: &str, profile| {
        let env = SnapshotEnv::from_pairs([("AWS_METADATA_SERVICE_TIMEOUT", timeout)]);
        super::settings_refusal(&env, &files, profile)
    };
    for (timeout, literal) in [("soon", "'soon'"), ("it's", "\"it's\"")] {
        assert_eq!(
            refusal(timeout, "default"),
            Some(format!("{INTEGER}{literal}")),
            "{timeout:?}"
        );
    }
    // The profile's own setting is the next one botocore reads.
    assert_eq!(refusal("1", "default"), Some(format!("{INTEGER}'many'")));
    assert_eq!(refusal("1", "other"), None);
}

/// A clock the test moves, and the seconds since the epoch it reads.
fn clock() -> (Clock, Arc<AtomicU64>) {
    let seconds = Arc::new(AtomicU64::new(SEVEN));
    let read = Arc::clone(&seconds);
    let clock = Clock::new(move || UNIX_EPOCH + Duration::from_secs(read.load(Ordering::SeqCst)));
    (clock, seconds)
}

/// A stand-in credential process. Its first run prints credentials that
/// expire at eight, its second a different key, secret and token that
/// expire at nine, and later runs fail.
fn rotating() -> (Runner, Arc<AtomicUsize>) {
    let runs = Arc::new(AtomicUsize::new(0));
    let count = Arc::clone(&runs);
    let runner = Runner::new(move |_| {
        let run = count.fetch_add(1, Ordering::SeqCst);
        if run >= 2 {
            return Ok(ProcessOutput {
                stderr: b"the token has expired".to_vec(),
                ..ProcessOutput::default()
            });
        }
        let stdout = format!(
            r#"{{"Version": 1, "AccessKeyId": "AKIDRUN{run}", "SecretAccessKey": "secret-{run}",
                "SessionToken": "token-{run}", "Expiration": "2037-10-21T{:02}:00:00Z"}}"#,
            8 + run
        );
        Ok(ProcessOutput {
            success: true,
            stdout: stdout.into_bytes(),
            stderr: Vec::new(),
        })
    });
    (runner, runs)
}

/// What the CRT's signer was handed for one request: the access key, the
/// secret key and the token, or `None` for a failure.
type Handed = Option<(String, String, Option<String>)>;

/// The credentials the stand-in process prints on its run numbered `run`.
fn printed(run: usize) -> Handed {
    Some((
        format!("AKIDRUN{run}"),
        format!("secret-{run}"),
        Some(format!("token-{run}")),
    ))
}

/// Passes the CRT's queries on to the resolved credentials, and records
/// each answer on its way back to the CRT. The wire shows the access key
/// and the token; the secret key a request is signed with shows only here.
#[derive(Debug)]
struct Recording {
    resolved: Resolved,
    handed: Arc<Mutex<Vec<Handed>>>,
}

impl Delegate for Recording {
    fn credentials(&self, query: Query) {
        let handed = Arc::clone(&self.handed);
        self.resolved.credentials(Query::new(move |view| {
            super::lock(&handed).push(view.as_ref().map(|view| {
                (
                    view.access_key_id.to_owned(),
                    view.secret_access_key.to_owned(),
                    view.session_token.map(str::to_owned),
                )
            }));
            match view {
                Some(view) => query.complete(view),
                None => query.fail(),
            }
        }));
    }
}

/// One runtime and one walk of the chain. Credentials that come due
/// between two requests are replaced by the provider that found them, and
/// the CRT signs the second request with the new ones, through the S3
/// client and through a request sent around it.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "one test follows one runtime through a refresh and a failed refresh"
)]
fn refreshed_credentials_sign_the_next_request() -> TestResult {
    let (runner, runs) = rotating();
    let (clock, seconds) = clock();
    let files = parse(b"[default]\ncredential_process = fetch-credentials\n", b"");
    let resolver = Resolver::new(vec![Box::new(ProcessProvider::new_with_runner(
        &files, "default", runner,
    ))]);
    let found = resolver.load_credentials()?;
    drop(resolver);
    let resolved = Resolved::new(found.map(|found| found.with_clock(clock)));
    assert_eq!(resolved.method(), Some("custom-process"));

    let handed = Arc::new(Mutex::new(Vec::new()));
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let server = std::thread::spawn(move || serve(listener, 4));
    let runtime = crt::Runtime::new(crt::RuntimeOptions {
        endpoint_url: format!("http://{address}/bucket"),
        credentials: Source::Delegate(Arc::new(Recording {
            resolved: resolved.clone(),
            handed: Arc::clone(&handed),
        })),
        event_loop_count: 1,
        ..crt::RuntimeOptions::default()
    })?;
    let host = address.to_string();
    let headers = [("Host", host.as_str())];
    let request = crt::http::Request {
        host: "127.0.0.1",
        port: address.port(),
        tls: false,
        method: "GET",
        target: "/2015-03-31/functions",
        headers: &headers,
        signing: Some(crt::http::Signing {
            region: "us-west-2",
            service: "lambda",
        }),
        connect_timeout: Duration::from_secs(10),
        read_timeout: Duration::from_secs(10),
    };
    let client = runtime.http_client();
    let status = || client.send(&request).map(|response| response.status);

    // An hour left: no refresh.
    assert_eq!(list(&runtime), 0);
    assert_eq!(status(), Ok(200));
    assert_eq!(runs.load(Ordering::SeqCst), 1);
    // Five minutes left, the mandatory window: the next request waits for
    // a refresh, and the one after it finds the new credentials.
    seconds.fetch_add(55 * MINUTE, Ordering::SeqCst);
    assert_eq!(list(&runtime), 0);
    assert_eq!(status(), Ok(200));
    assert_eq!(runs.load(Ordering::SeqCst), 2);
    assert_eq!(resolved.refresh_error(), None);
    // Nine minutes left on the second key, and the process now fails: the
    // request fails rather than go out under credentials about to expire.
    seconds.fetch_add(56 * MINUTE, Ordering::SeqCst);
    assert_eq!(list(&runtime), NO_CREDENTIALS_ERROR_CODE);
    assert_eq!(
        resolved.refresh_error().map(|error| error.to_string()),
        Some("Error when retrieving credentials from custom-process: the token has expired".into())
    );
    assert_eq!(
        status(),
        Err(crt::http::Error::Connect(NO_CREDENTIALS_ERROR_CODE))
    );
    drop(runtime);

    let requests = server.join().map_err(|_| "loopback server panicked")??;
    let keys: Vec<_> = requests.iter().map(|request| access_key(request)).collect();
    assert_eq!(
        keys,
        ["AKIDRUN0", "AKIDRUN0", "AKIDRUN1", "AKIDRUN1"].map(Some)
    );
    let tokens: Vec<_> = requests
        .iter()
        .map(|request| {
            let request = request.to_ascii_lowercase();
            ["token-0", "token-1"]
                .map(|token| request.contains(&format!("x-amz-security-token: {token}\r\n")))
        })
        .collect();
    let (old, new) = ([true, false], [false, true]);
    assert_eq!(tokens, [old, old, new, new]);
    // The secret key rotated with the access key, and each request was
    // signed with the one that belongs to its access key.
    assert_eq!(
        *super::lock(&handed),
        [printed(0), printed(0), printed(1), printed(1), None, None]
    );
    Ok(())
}

fn at(seconds: u64) -> SystemTime {
    UNIX_EPOCH + Duration::from_secs(seconds)
}

fn failed() -> LoadError {
    LoadError::CredentialRetrieval {
        provider: "test",
        error_msg: "the source is down".into(),
    }
}

/// How long a test waits for a refresh or an answer before it fails.
const PATIENCE: Duration = Duration::from_secs(10);

/// A delegate over credentials whose refreshes the test holds back.
struct Gated {
    resolved: Resolved,
    /// Receives once per refresh, as the refresh starts.
    entered: mpsc::Receiver<()>,
    /// Lets one refresh finish per message.
    release: mpsc::Sender<()>,
    refreshes: Arc<AtomicUsize>,
    /// Each query's answer as it arrives: the access key and expiry the
    /// signer was given, or `None` for a failure.
    answers: mpsc::Receiver<Option<(String, Option<SystemTime>)>>,
    answered: mpsc::Sender<Option<(String, Option<SystemTime>)>>,
}

impl Gated {
    /// Credentials `AKIDA` with `lifetime` seconds left, whose refreshes
    /// return `results` in order.
    fn new(lifetime: u64, results: Vec<Result<Credentials, LoadError>>) -> Self {
        let (clock, _) = clock();
        let (enter, entered) = mpsc::channel();
        let (release, released) = mpsc::channel::<()>();
        let released = Mutex::new(released);
        let results = Mutex::new(results.into_iter());
        let refreshes = Arc::new(AtomicUsize::new(0));
        let count = Arc::clone(&refreshes);
        let initial =
            Credentials::new("test", "AKIDA", "secret-a").with_expiry(Some(at(SEVEN + lifetime)));
        let refreshable = Refreshable::new(initial, move || {
            count.fetch_add(1, Ordering::SeqCst);
            // A test that has stopped listening fails on its own
            // assertions.
            let _ = enter.send(());
            let _ = super::lock(&released).recv_timeout(PATIENCE);
            super::lock(&results).next().unwrap_or(Err(failed()))
        });
        let (answered, answers) = mpsc::channel();
        Self {
            resolved: Resolved::new(Some(Loaded::from(refreshable.with_clock(clock)))),
            entered,
            release,
            refreshes,
            answers,
            answered,
        }
    }
    /// Asks as the CRT's signer does. It returns without an answer when
    /// the query is parked.
    fn ask(&self) {
        let answered = self.answered.clone();
        self.resolved.credentials(Query::new(move |view| {
            let _ =
                answered.send(view.map(|view| (view.access_key_id.to_owned(), view.expiration)));
        }));
    }
    fn answer(&self) -> Result<Option<String>, mpsc::RecvTimeoutError> {
        let answer = self.answers.recv_timeout(PATIENCE)?;
        Ok(answer.map(|(access_key, _)| access_key))
    }
    /// Waits for the refresh thread to stop, which it does a moment after
    /// its last answer, so that the next query finds no refresh under way.
    fn idle(&self) -> TestResult {
        let live = self.resolved.0.as_ref().ok_or("no credentials")?;
        let deadline = Instant::now() + PATIENCE;
        while super::lock(&live.waiting).served {
            if Instant::now() > deadline {
                return Err("the refresh thread did not stop".into());
            }
            std::thread::yield_now();
        }
        Ok(())
    }
}

fn refreshed() -> Credentials {
    refreshed_until(SEVEN + 120 * MINUTE)
}

fn refreshed_until(expiry: u64) -> Credentials {
    Credentials::new("test", "AKIDB", "secret-b").with_expiry(Some(at(expiry)))
}

#[test]
fn requests_that_wait_for_a_mandatory_refresh_share_it() -> TestResult {
    let gated = Gated::new(5 * MINUTE, vec![Ok(refreshed())]);
    // None of these blocks, though the refresh they need has not finished.
    for _ in 0..5 {
        gated.ask();
    }
    gated.entered.recv_timeout(PATIENCE)?;
    // No signer was handed the key that is about to expire.
    assert!(gated.answers.try_recv().is_err());
    gated.release.send(())?;
    for _ in 0..5 {
        assert_eq!(
            gated.answers.recv_timeout(PATIENCE)?,
            Some(("AKIDB".into(), Some(at(SEVEN + 120 * MINUTE))))
        );
    }
    assert_eq!(gated.refreshes.load(Ordering::SeqCst), 1);
    assert_eq!(gated.resolved.refresh_error(), None);
    Ok(())
}

/// botocore's callers that wait for a refresh recheck the mandatory window
/// alone (`RefreshableCredentials._refresh`), so a refresh that leaves twelve
/// minutes serves them all. Only a request that arrives once the refresh thread
/// has stopped, and so finds no refresh under way, tries an advisory one.
#[test]
fn requests_that_waited_take_credentials_inside_the_advisory_window() -> TestResult {
    let twelve_minutes = SEVEN + 12 * MINUTE;
    let gated = Gated::new(5 * MINUTE, vec![Ok(refreshed_until(twelve_minutes))]);
    for _ in 0..5 {
        gated.ask();
    }
    // Every refresh that starts may finish, so a request that began one of
    // its own would show in the count.
    for _ in 0..5 {
        gated.release.send(())?;
    }
    for _ in 0..5 {
        assert_eq!(
            gated.answers.recv_timeout(PATIENCE)?,
            Some(("AKIDB".into(), Some(at(twelve_minutes))))
        );
    }
    assert_eq!(gated.refreshes.load(Ordering::SeqCst), 1);
    // The later request's advisory refresh fails, which is forgiven.
    gated.idle()?;
    gated.ask();
    assert_eq!(gated.answer()?, Some("AKIDB".into()));
    assert_eq!(gated.refreshes.load(Ordering::SeqCst), 2);
    assert_eq!(gated.resolved.refresh_error(), None);
    Ok(())
}

/// A request waits for whichever refresh is under way when it arrives
/// (`RefreshableCredentials._refresh`), a waiter's own included: one that
/// arrives during the second refresh below is signed with what that refresh
/// left, and does not go on to an advisory refresh, which here would fail it.
#[test]
fn a_request_that_arrives_during_a_waiters_refresh_waits_for_it() -> TestResult {
    let twelve_minutes = SEVEN + 12 * MINUTE;
    let unreadable = LoadError::Expiry {
        provider: "test",
        value: "soon".into(),
    };
    let gated = Gated::new(
        5 * MINUTE,
        vec![
            Err(failed()),
            Ok(refreshed_until(twelve_minutes)),
            Err(unreadable),
        ],
    );
    // The first request refreshes, and the second waits for it.
    gated.ask();
    gated.entered.recv_timeout(PATIENCE)?;
    gated.ask();
    // That refresh fails, so the request that waited refreshes itself.
    gated.release.send(())?;
    assert_eq!(gated.answer()?, None);
    gated.entered.recv_timeout(PATIENCE)?;
    // The third request arrives while the second one's refresh runs.
    gated.ask();
    // Every refresh that starts may finish, so one more would show.
    for _ in 0..3 {
        gated.release.send(())?;
    }
    let refreshed = Some(("AKIDB".into(), Some(at(twelve_minutes))));
    assert_eq!(gated.answers.recv_timeout(PATIENCE)?, refreshed);
    assert_eq!(gated.answers.recv_timeout(PATIENCE)?, refreshed);
    gated.idle()?;
    assert_eq!(gated.refreshes.load(Ordering::SeqCst), 2);
    // Only the first request's failure was raised.
    assert_eq!(
        gated.resolved.refresh_error(),
        Some(RefreshError::Provider(failed()))
    );
    Ok(())
}

#[test]
fn a_request_in_the_advisory_window_does_not_wait_for_a_refresh_under_way() -> TestResult {
    let gated = Gated::new(14 * MINUTE, vec![Ok(refreshed())]);
    // The first request takes the refresh on and waits for it.
    gated.ask();
    gated.entered.recv_timeout(PATIENCE)?;
    // The second is signed at once with the current credentials.
    gated.ask();
    assert_eq!(gated.answer()?, Some("AKIDA".into()));
    gated.release.send(())?;
    assert_eq!(gated.answer()?, Some("AKIDB".into()));
    assert_eq!(gated.refreshes.load(Ordering::SeqCst), 1);
    Ok(())
}

#[test]
fn a_failed_mandatory_refresh_fails_each_request_that_waited() -> TestResult {
    let gated = Gated::new(5 * MINUTE, vec![Err(failed()), Err(failed())]);
    gated.ask();
    gated.ask();
    gated.release.send(())?;
    gated.release.send(())?;
    assert_eq!(gated.answer()?, None);
    assert_eq!(gated.answer()?, None);
    // As in botocore, the request that waited tries the provider itself.
    assert_eq!(gated.refreshes.load(Ordering::SeqCst), 2);
    assert_eq!(
        gated.resolved.refresh_error(),
        Some(RefreshError::Provider(failed()))
    );
    Ok(())
}

#[test]
fn a_chain_that_found_nothing_fails_every_query() -> TestResult {
    let resolved = Resolved::new(None);
    let (answered, answers) = mpsc::channel();
    resolved.credentials(Query::new(move |view| {
        let _ = answered.send(view.is_some());
    }));
    assert!(!answers.recv_timeout(PATIENCE)?);
    assert_eq!((resolved.method(), resolved.refresh_error()), (None, None));
    Ok(())
}

/// The command's walk: the first provider with credentials answers every
/// query, and a provider that fails stops the walk with botocore's error.
#[test]
fn a_walk_answers_with_the_first_provider_that_has_credentials() -> TestResult {
    let files = parse(
        b"[profile work]\naws_access_key_id = AKIDCONFIG\naws_secret_access_key = c\n",
        b"",
    );
    let env = SnapshotEnv::from_pairs([
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
        ("AWS_EC2_METADATA_DISABLED", "true"),
    ]);
    for (profile, method, key) in [
        (Profile::Ambient("work"), "env", "AKIDENV"),
        (Profile::Explicit("work"), "config-file", "AKIDCONFIG"),
    ] {
        let chain = Chain::walk(&env, &files, profile)?;
        assert_eq!(chain.method(), Some(method));
        let (answered, answers) = mpsc::channel();
        chain.credentials(Query::new(move |view| {
            let _ = answered.send(view.map(|view| view.access_key_id.to_owned()));
        }));
        assert_eq!(answers.recv_timeout(PATIENCE)?, Some(key.into()));
    }
    let partial = SnapshotEnv::from_pairs([("AWS_ACCESS_KEY_ID", "AKIDENV")]);
    let error = Chain::walk(&partial, &files, Profile::Ambient("work")).err();
    assert_eq!(
        error.map(|error| error.to_string()),
        Some("Partial credentials found in env, missing: AWS_SECRET_ACCESS_KEY".into())
    );
    Ok(())
}

/// A walk that ends with nothing, its instance metadata provider disabled,
/// fails every query and never waits for a runtime.
#[test]
fn a_walk_that_found_nothing_fails_every_query() -> TestResult {
    let env = SnapshotEnv::from_pairs([("AWS_EC2_METADATA_DISABLED", "TRUE")]);
    let chain = Chain::walk(&env, &parse(b"", b""), Profile::Ambient("default"))?;
    let (answered, answers) = mpsc::channel();
    chain.credentials(Query::new(move |view| {
        let _ = answered.send(view.is_some());
    }));
    assert!(!answers.recv_timeout(PATIENCE)?);
    assert_eq!((chain.method(), chain.refresh_error()), (None, None));
    Ok(())
}

mod container;
mod instance_metadata;
