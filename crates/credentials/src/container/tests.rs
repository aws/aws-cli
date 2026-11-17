use super::*;
use crate::tests::{TestResult, Time, env, files, no_container};
use crate::{Profile, RoleFetcher, default_resolver};
use std::collections::VecDeque;
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};

type Answer = Result<Response, TransportError>;
/// A request's URL and its headers.
type Seen = (String, Vec<(&'static str, String)>);

/// A stand-in transport that gives its answers in order and records what
/// it was sent.
#[derive(Debug, Default)]
struct Script {
    answers: Mutex<VecDeque<Answer>>,
    sent: Mutex<Vec<(Request, Duration)>>,
}

impl Transport for Script {
    fn send(&self, request: &Request, timeout: Duration) -> Answer {
        let mut sent = self.sent.lock().unwrap_or_else(|lock| lock.into_inner());
        sent.push((request.clone(), timeout));
        let mut answers = self.answers.lock().unwrap_or_else(|lock| lock.into_inner());
        answers.pop_front().unwrap_or(Err(TransportError::Client {
            reason: "the test scripted no answer".into(),
        }))
    }
}

impl Script {
    fn new(answers: impl IntoIterator<Item = Answer>) -> Arc<Self> {
        Arc::new(Self {
            answers: Mutex::new(answers.into_iter().collect()),
            sent: Mutex::default(),
        })
    }
    fn seen(&self) -> Vec<Seen> {
        let sent = self.sent.lock().unwrap_or_else(|lock| lock.into_inner());
        sent.iter()
            .map(|(request, timeout)| {
                assert_eq!((request.method, *timeout), ("GET", TIMEOUT));
                (request.url.clone(), request.headers.clone())
            })
            .collect()
    }
}

fn document(turn: usize, expiration: &str) -> String {
    format!(
        r#"{{"AccessKeyId": "AKIDCONTAINER{turn}", "SecretAccessKey": "container-secret",
            "Token": "container-token", "Expiration": "{expiration}",
            "AccountId": "123456789012"}}"#
    )
}

const EXPIRATION: &str = "2037-10-21T07:28:00Z";

fn ok(body: &str) -> Answer {
    status(200, body)
}

fn status(status: u16, body: &str) -> Answer {
    Ok(Response {
        status,
        body: body.into(),
    })
}

/// A fetcher over `script`, and the waits it would have made.
fn fetcher(script: &Arc<Script>) -> (ContainerFetcher, Arc<Mutex<Vec<Duration>>>) {
    let slept = Arc::new(Mutex::new(Vec::new()));
    let noted = Arc::clone(&slept);
    let transport: Arc<dyn Transport> = Arc::clone(script) as _;
    let fetcher = ContainerFetcher::new(transport).with_sleep(move |wait| {
        noted
            .lock()
            .unwrap_or_else(|lock| lock.into_inner())
            .push(wait);
    });
    (fetcher, slept)
}

fn slept(waits: &Mutex<Vec<Duration>>) -> Vec<Duration> {
    waits
        .lock()
        .unwrap_or_else(|lock| lock.into_inner())
        .clone()
}

fn endpoint(pairs: &[(&str, &str)]) -> Result<ContainerEndpoint, Box<dyn std::error::Error>> {
    Ok(ContainerEndpoint::from_env(&env(pairs))?.ok_or("no endpoint")?)
}

fn accept() -> (&'static str, String) {
    ("Accept", "application/json".to_owned())
}

fn authorization(token: &str) -> (&'static str, String) {
    ("Authorization", token.to_owned())
}

/// A file of this test's own that holds `token`.
fn token_file(name: &str, token: &str) -> std::io::Result<std::path::PathBuf> {
    let path = std::env::temp_dir().join(format!("{name}-{}", std::process::id()));
    std::fs::write(&path, token)?;
    Ok(path)
}

/// ECS and CodeBuild: a relative URI is a path on the ECS agent, and it
/// wins over a full URI (`ContainerProvider._retrieve_or_fail`).
#[test]
fn a_relative_uri_asks_the_ecs_agent_and_wins_over_a_full_uri() -> TestResult {
    let script = Script::new([ok(&document(0, EXPIRATION))]);
    let (fetcher, waits) = fetcher(&script);
    let found = fetcher.load(endpoint(&[
        (RELATIVE_URI, "/v2/credentials/task-id"),
        (FULL_URI, "http://127.0.0.1:1/full"),
    ])?)?;
    assert_eq!(found.method(), "container-role");
    let found = found.outside_advisory().ok_or("no credentials")?;
    assert_eq!(found.access_key_id(), "AKIDCONTAINER0");
    assert_eq!(found.secret_access_key(), "container-secret");
    assert_eq!(found.session_token(), Some("container-token"));
    assert_eq!(found.account_id(), Some("123456789012"));
    assert_eq!(found.expiry(), Some(expiry::parse("", EXPIRATION)?));
    assert_eq!(
        script.seen(),
        [(
            "http://169.254.170.2/v2/credentials/task-id".to_owned(),
            vec![accept()]
        )]
    );
    assert!(slept(&waits).is_empty());
    Ok(())
}

/// EKS Pod Identity reads its token from a file, which wins over the
/// variable; a local agent on loopback may take the variable
/// (`ContainerProvider._build_headers`).
#[test]
fn a_full_uri_sends_the_token_its_file_or_variable_holds() -> TestResult {
    let path = token_file("container-token", "eks-token")?;
    let file = path.to_str().ok_or("temporary path is not Unicode")?;
    let cases = [
        (
            "http://169.254.170.23/v1/credentials",
            &[(AUTH_TOKEN_FILE, file), (AUTH_TOKEN, "Basic env")][..],
            Some("eks-token"),
        ),
        (
            "http://[fd00:ec2::23]/v1/credentials",
            &[(AUTH_TOKEN_FILE, file)][..],
            Some("eks-token"),
        ),
        (
            "http://127.0.0.1:8080/creds?task=1",
            &[(AUTH_TOKEN, "Basic local")][..],
            Some("Basic local"),
        ),
        ("http://[::1]:8080/creds", &[][..], None),
        (
            "http://localhost:8080/creds",
            &[(AUTH_TOKEN, "")][..],
            Some(""),
        ),
    ];
    for (url, tokens, token) in cases {
        let script = Script::new([ok(&document(0, EXPIRATION))]);
        let (fetcher, _) = fetcher(&script);
        let mut pairs = vec![(FULL_URI, url)];
        pairs.extend_from_slice(tokens);
        fetcher.load(endpoint(&pairs)?)?;
        let mut headers = vec![accept()];
        headers.extend(token.map(authorization));
        assert_eq!(script.seen(), [(url.to_owned(), headers)], "{url}");
    }
    std::fs::remove_file(&path)?;
    Ok(())
}

#[test]
fn an_endpoint_botocore_refuses_fails_before_a_request() {
    let refused = |pairs: &[(&str, &str)]| endpoint(pairs).map_err(|error| error.to_string());
    assert_eq!(
        refused(&[(FULL_URI, "http://169.254.169.254/creds")]).err(),
        Some(
            "Unsupported host '169.254.169.254'.  Can only retrieve metadata from a loopback \
             address or one of these hosts: 169.254.170.2, 169.254.170.23, fd00:ec2::23, \
             localhost"
                .to_owned()
        )
    );
    assert_eq!(
        refused(&[(FULL_URI, "http://127.0.0.1/"), (AUTH_TOKEN, "Bearer a\nb")]).err(),
        Some("Auth token value is not a legal header value".to_owned())
    );
    // Any https URL skips the allowlist (`_validate_allowed_url`).
    assert!(refused(&[(FULL_URI, "https://credentials.example/creds")]).is_ok());
}

/// A URL [`Location`] cannot read, here for its empty port.
#[test]
fn an_unreadable_url_fails_without_its_user_and_password() {
    let url = "http://container-user:container-password@127.0.0.1:/creds";
    let shown = endpoint(&[(FULL_URI, url)])
        .err()
        .map(|error| error.to_string())
        .unwrap_or_default();
    assert!(shown.contains("Failed to parse"), "{shown}");
    assert!(!shown.contains("container-user"), "{shown}");
    assert!(!shown.contains("container-password"), "{shown}");
}

#[test]
fn without_an_endpoint_variable_the_provider_passes_unasked() -> TestResult {
    let asked = AtomicUsize::new(0);
    let fetch = || {
        ContainerFetch::new(|_| {
            asked.fetch_add(1, Ordering::SeqCst);
            Ok(None)
        })
    };
    let tokens = env(&[(AUTH_TOKEN, "token"), (AUTH_TOKEN_FILE, "/missing")]);
    assert!(ContainerProvider::new(&tokens, fetch()).load()?.is_none());
    assert_eq!(asked.load(Ordering::SeqCst), 0);
    // Set but empty still turns the provider on (`ContainerProvider.load`).
    let empty = env(&[(RELATIVE_URI, "")]);
    assert!(ContainerProvider::new(&empty, fetch()).load()?.is_none());
    assert_eq!(asked.load(Ordering::SeqCst), 1);
    Ok(())
}

const RETRIEVAL: &str = "Error when retrieving credentials from container-role: Error retrieving \
                         metadata: ";

/// Three attempts, with a second's wait after each that fails, the last
/// included, and the last attempt's error (`_retrieve_credentials`).
#[test]
fn a_failing_endpoint_is_asked_three_times() -> TestResult {
    const URL: &str = "http://127.0.0.1:1/creds";
    let cases = [
        (
            status(404, "not found"),
            "Received non 200 response 404 from container metadata: not found".to_owned(),
        ),
        (
            ok("<html>"),
            "Unable to parse JSON returned from container metadata services".to_owned(),
        ),
        (
            Err(TransportError::Connect),
            format!(
                "Received error when attempting to retrieve container metadata: Could not \
                 connect to the endpoint URL: \"{URL}\""
            ),
        ),
        (
            Err(TransportError::ReadTimeout),
            format!(
                "Received error when attempting to retrieve container metadata: Read timeout \
                 on endpoint URL: \"{URL}\""
            ),
        ),
    ];
    for (answer, message) in cases {
        let script = Script::new(std::iter::repeat_n(answer, ATTEMPTS));
        let (fetcher, waits) = fetcher(&script);
        let failed = fetcher.load(endpoint(&[(FULL_URI, URL)])?);
        assert_eq!(
            failed.map(drop).map_err(|error| error.to_string()),
            Err(format!("{RETRIEVAL}{message}"))
        );
        assert_eq!(script.seen().len(), ATTEMPTS, "{message}");
        assert_eq!(slept(&waits), [SLEEP; ATTEMPTS], "{message}");
    }
    Ok(())
}

#[test]
fn a_later_attempt_s_credentials_are_taken() -> TestResult {
    let script = Script::new([
        status(500, "busy"),
        Err(TransportError::ConnectionClosed),
        ok(&document(0, EXPIRATION)),
    ]);
    let (fetcher, waits) = fetcher(&script);
    fetcher.load(endpoint(&[(FULL_URI, "http://127.0.0.1:1/creds")])?)?;
    assert_eq!(script.seen().len(), 3);
    assert_eq!(slept(&waits), [SLEEP; 2]);
    Ok(())
}

/// What botocore lets through ends the fetch at once: an error it does not
/// try again (`_get_response`) and a member the answer lacks
/// (`fetch_creds`). A null token is no token.
#[test]
fn errors_botocore_does_not_retry_end_the_fetch_at_once() -> TestResult {
    let no_token = r#"{"AccessKeyId": "AKID", "SecretAccessKey": "secret",
        "Expiration": "2037-10-21T07:28:00Z"}"#;
    let cases = [
        (
            Err(TransportError::Tls {
                reason: "bad certificate".into(),
            }),
            "SSL validation failed for http://127.0.0.1:1/creds bad certificate",
        ),
        (ok(no_token), "'Token'"),
    ];
    for (answer, message) in cases {
        let script = Script::new([answer]);
        let (fetcher, waits) = fetcher(&script);
        let failed = fetcher.load(endpoint(&[(FULL_URI, "http://127.0.0.1:1/creds")])?);
        assert_eq!(
            failed.map(drop).map_err(|error| error.to_string()),
            Err(message.to_owned())
        );
        assert_eq!((script.seen().len(), slept(&waits)), (1, vec![]));
    }
    let null = no_token.replace("\"Expiration\"", "\"Token\": null, \"Expiration\"");
    let script = Script::new([ok(&null)]);
    let (fetcher, _) = fetcher(&script);
    let found = fetcher.load(endpoint(&[(FULL_URI, "http://127.0.0.1:1/creds")])?)?;
    let found = found.outside_advisory().ok_or("no credentials")?;
    assert_eq!(found.session_token(), None);
    Ok(())
}

/// A refresh asks the same URL with the same token, read once
/// (`ContainerProvider._retrieve_or_fail`).
#[test]
fn a_refresh_asks_the_same_endpoint_again() -> TestResult {
    let later = "2037-10-21T09:28:00Z";
    let script = Script::new([ok(&document(0, EXPIRATION)), ok(&document(1, later))]);
    let (fetcher, _) = fetcher(&script);
    let time = Time::at("2037-10-21T06:28:00Z")?;
    let url = "http://169.254.170.23/v1/credentials";
    let found = fetcher
        .load(endpoint(&[(FULL_URI, url), (AUTH_TOKEN, "pod-token")])?)?
        .with_clock(time.clock());
    assert_eq!(found.frozen()?.access_key_id(), "AKIDCONTAINER0");
    // Fourteen minutes left: inside the advisory window.
    time.advance(46 * 60);
    let refreshed = found.frozen()?;
    assert_eq!(refreshed.access_key_id(), "AKIDCONTAINER1");
    assert_eq!(refreshed.expiry(), Some(expiry::parse("", later)?));
    let request = (url.to_owned(), vec![accept(), authorization("pod-token")]);
    assert_eq!(script.seen(), [request.clone(), request]);
    Ok(())
}

/// botocore's order: the container after the config file and before the
/// instance (`create_credential_resolver`). An earlier provider's credentials
/// win and the endpoint is never asked; with the endpoint set, the
/// instance never is.
#[test]
fn the_chain_asks_the_container_after_the_profiles_and_before_the_instance() -> TestResult {
    let ambient = Profile::Ambient("default");
    let container = [(FULL_URI, "http://127.0.0.1:1/creds")];
    let keys = [
        (FULL_URI, "http://127.0.0.1:1/creds"),
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
    ];
    let profile = "[default]\naws_access_key_id = AKIDCONFIG\naws_secret_access_key = secret\n";
    for (variables, config, method, requests) in [
        (&keys[..], "", "env", 0),
        (&container[..], profile, "config-file", 0),
        (&container[..], "", "container-role", 1),
    ] {
        let script = Script::new([ok(&document(0, EXPIRATION))]);
        let (fetcher, _) = fetcher(&script);
        let instance = Arc::new(AtomicUsize::new(0));
        let counted = RoleFetcher::new({
            let instance = Arc::clone(&instance);
            move || {
                instance.fetch_add(1, Ordering::SeqCst);
                Ok(None)
            }
        });
        let (variables, parsed) = (env(variables), files(config, ""));
        let resolver = default_resolver(&variables, &parsed, ambient, fetcher.into(), counted);
        let found = resolver.load_credentials()?.ok_or("no credentials")?;
        assert_eq!((found.method(), script.seen().len()), (method, requests));
        assert_eq!(instance.load(Ordering::SeqCst), 0);
    }
    let empty = env(&[]);
    let parsed = files("", "");
    let no_role = RoleFetcher::new(|| Ok(None));
    let resolver = default_resolver(&empty, &parsed, ambient, no_container(), no_role);
    let methods: Vec<_> = resolver.methods().collect();
    assert_eq!(methods[methods.len() - 2..], ["container-role", "iam-role"]);
    Ok(())
}

#[test]
fn nothing_shows_the_token() -> TestResult {
    let script = Script::new([ok(&document(0, EXPIRATION))]);
    let (fetcher, _) = fetcher(&script);
    let found = endpoint(&[
        (FULL_URI, "http://127.0.0.1:1/c"),
        (AUTH_TOKEN, "s3cr3t-token"),
    ])?;
    let shown = format!("{found:?} {fetcher:?} {:?}", fetcher.load(found.clone())?);
    let sent = script.sent.lock().unwrap_or_else(|lock| lock.into_inner());
    let shown = format!("{shown} {sent:?}");
    assert!(!shown.contains("s3cr3t-token"), "{shown}");
    assert!(!shown.contains("container-secret"), "{shown}");
    Ok(())
}
