use super::*;
use crate::tests::{TestResult, Time};
use crate::{Loaded, RoleFetcher};
use std::collections::VecDeque;
use std::sync::Mutex;
use std::time::UNIX_EPOCH;

type Answer = Result<Response, TransportError>;
/// A request's method, its path under the default base URL, and its token
/// header.
type Seen = (&'static str, String, Option<String>);
type Fetched = Result<Option<RoleCredentials>, LoadError>;

/// A stand-in transport that gives its answers in order and records what
/// it was sent. A request it has no answer for fails as no test expects.
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
    fn requests(&self) -> Vec<Request> {
        let sent = self.sent.lock().unwrap_or_else(|lock| lock.into_inner());
        sent.iter().map(|(request, _)| request.clone()).collect()
    }
    fn seen(&self) -> Vec<Seen> {
        let token = |request: &Request| {
            let header = request
                .headers
                .iter()
                .find(|(name, _)| *name == TOKEN_HEADER);
            header.map(|(_, value)| value.clone())
        };
        let path = |request: &Request| request.url.replacen(BASE, "", 1);
        let requests = self.requests();
        let seen = requests.iter();
        seen.map(|request| (request.method, path(request), token(request)))
            .collect()
    }
}

const BASE: &str = "http://169.254.169.254/";
const ROLE: &str = "latest/meta-data/iam/security-credentials/";
const DOCUMENT: &str = r#"{"Code": "Success", "AccessKeyId": "AKIDIMDS",
    "SecretAccessKey": "imds-secret", "Token": "imds-token",
    "Expiration": "2037-10-21T07:28:00Z"}"#;
/// 2037-10-21T07:28:00Z.
const EXPIRY: u64 = 2_139_722_880;

fn answer(status: u16, body: &str) -> Answer {
    Ok(Response {
        status,
        body: body.into(),
    })
}

fn ok(body: &str) -> Answer {
    answer(200, body)
}

fn settings(num_attempts: i64) -> InstanceMetadataSettings {
    InstanceMetadataSettings {
        base_url: BASE.into(),
        timeout: Timeout::Within(Duration::from_secs(1)),
        num_attempts,
        v1_disabled: false,
    }
}

/// A fetcher whose clock reads a day before [`EXPIRY`].
fn fetcher(settings: InstanceMetadataSettings, script: &Arc<Script>) -> Fetcher {
    let transport: Arc<dyn Transport> = Arc::clone(script) as _;
    Fetcher::new(settings, None, transport)
        .with_clock(Clock::new(|| {
            UNIX_EPOCH + Duration::from_secs(EXPIRY - 86_400)
        }))
        .with_jitter(|| 0)
}

/// What a fetch with `num_attempts` gets from `answers`, and the requests
/// it sent.
fn fetch(num_attempts: i64, answers: impl IntoIterator<Item = Answer>) -> (Fetched, Vec<Seen>) {
    let script = Script::new(answers);
    let found = fetcher(settings(num_attempts), &script).retrieve();
    (found, script.seen())
}

fn put() -> Seen {
    ("PUT", TOKEN_PATH.into(), None)
}

fn get(path: &str, token: Option<&str>) -> Seen {
    ("GET", path.into(), token.map(str::to_owned))
}

/// The three requests of one fetch whose GETs carry `token`.
fn round(token: Option<&str>) -> Vec<Seen> {
    let credentials = format!("{ROLE}test-role");
    vec![put(), get(ROLE, token), get(&credentials, token)]
}

fn message(found: Fetched) -> Option<String> {
    found.err().map(|error| error.to_string())
}

#[test]
fn a_fetch_is_a_token_the_roles_name_and_its_credentials() -> TestResult {
    let script = Script::new([ok("imds-token"), ok("test-role"), ok(DOCUMENT)]);
    let transport: Arc<dyn Transport> = Arc::clone(&script) as _;
    let mut configured = settings(1);
    configured.timeout = Timeout::Within(Duration::from_secs(7));
    let fetcher = Fetcher::new(configured, Some("aws-cli/2.0.0".into()), transport)
        .with_clock(Clock::new(|| UNIX_EPOCH));
    let found = fetcher.retrieve()?.ok_or("no credentials")?;
    assert_eq!(
        found,
        RoleCredentials {
            access_key: "AKIDIMDS".into(),
            secret_key: "imds-secret".into(),
            token: "imds-token".into(),
            expiry: UNIX_EPOCH + Duration::from_secs(EXPIRY),
        }
    );
    // The headers are botocore's, in its order.
    let agent = (USER_AGENT_HEADER, "aws-cli/2.0.0".to_owned());
    let token = (TOKEN_HEADER, "imds-token".to_owned());
    let request = |method, path: &str, first| Request {
        method,
        url: format!("{BASE}{path}"),
        headers: vec![first, agent.clone()],
    };
    assert_eq!(
        script.requests(),
        [
            request("PUT", TOKEN_PATH, (TTL_HEADER, "21600".to_owned())),
            request("GET", ROLE, token.clone()),
            request("GET", &format!("{ROLE}test-role"), token.clone()),
        ]
    );
    let sent = script.sent.lock().map_err(|_| "poisoned")?;
    assert!(
        sent.iter()
            .all(|(_, timeout)| *timeout == Duration::from_secs(7))
    );
    Ok(())
}

/// `_fetch_metadata_token`: 403, 404 and 405 are a service without tokens,
/// 400 ends the fetch, and any other status is tried again.
#[test]
fn a_token_request_ends_as_its_status_says() -> TestResult {
    for status in [403, 404, 405] {
        let (found, seen) = fetch(2, [answer(status, "no"), ok("test-role"), ok(DOCUMENT)]);
        assert_eq!(
            found?.map(|found| found.access_key),
            Some("AKIDIMDS".into())
        );
        assert_eq!(seen, round(None), "{status}");
    }
    let (found, seen) = fetch(2, [answer(400, "bad"), ok("test-role"), ok(DOCUMENT)]);
    assert_eq!((found?, seen), (None, vec![put()]));
    for status in [500, 201, 204, 301] {
        let failed = || answer(status, "error");
        let (found, seen) = fetch(2, [failed(), failed(), ok("test-role"), ok(DOCUMENT)]);
        assert!(found?.is_some());
        assert_eq!(seen, [vec![put()], round(None)].concat(), "{status}");
        let (found, seen) = fetch(2, [failed(), ok("t"), ok("test-role"), ok(DOCUMENT)]);
        assert!(found?.is_some());
        assert_eq!(seen, [vec![put()], round(Some("t"))].concat(), "{status}");
    }
    Ok(())
}

/// `_fetch_metadata_token`: a read timeout is a service without tokens at
/// once, and the other three are tried again.
#[test]
fn a_token_request_that_fails_is_retried_unless_it_timed_out_reading() -> TestResult {
    let timed_out = Err(TransportError::ReadTimeout);
    let (found, seen) = fetch(2, [timed_out, ok("test-role"), ok(DOCUMENT)]);
    assert!(found?.is_some());
    assert_eq!(seen, round(None));
    for error in [
        TransportError::ConnectTimeout,
        TransportError::Connect,
        TransportError::ConnectionClosed,
    ] {
        let failed = || Err(error.clone());
        let (found, seen) = fetch(2, [failed(), failed(), ok("test-role"), ok(DOCUMENT)]);
        assert!(found?.is_some());
        assert_eq!(seen, [vec![put()], round(None)].concat(), "{error:?}");
        let (found, seen) = fetch(2, [failed(), ok("t"), ok("test-role"), ok(DOCUMENT)]);
        assert!(found?.is_some());
        assert_eq!(seen, [vec![put()], round(Some("t"))].concat(), "{error:?}");
    }
    Ok(())
}

/// The errors botocore does not retry reach the caller, in its words.
#[test]
fn an_error_botocore_lets_through_is_raised_with_its_message() {
    let token_url = format!("{BASE}{TOKEN_PATH}");
    let role_url = format!("{BASE}{ROLE}");
    let proxy = || TransportError::Proxy {
        url: "http://127.0.0.1:1".into(),
    };
    let tls = || TransportError::Tls {
        reason: "certificate verify failed".into(),
    };
    let client = || TransportError::Client {
        reason: "boom".into(),
    };
    let rows = [
        (
            TransportError::InvalidUrl,
            format!("Invalid endpoint EC2 Instance Metadata endpoint: {token_url}"),
            format!("An HTTP Client raised an unhandled exception: Failed to parse: {role_url}"),
        ),
        (
            proxy(),
            "Failed to connect to proxy URL: \"http://127.0.0.1:1\"".into(),
            "Failed to connect to proxy URL: \"http://127.0.0.1:1\"".into(),
        ),
        (
            tls(),
            format!("SSL validation failed for {token_url} certificate verify failed"),
            format!("SSL validation failed for {role_url} certificate verify failed"),
        ),
        (
            client(),
            "An HTTP Client raised an unhandled exception: boom".into(),
            "An HTTP Client raised an unhandled exception: boom".into(),
        ),
    ];
    for (error, from_token, from_get) in rows {
        // Attempts are left, and none is made.
        let (found, seen) = fetch(3, [Err(error.clone())]);
        assert_eq!((message(found), seen), (Some(from_token), vec![put()]));
        let (found, seen) = fetch(3, [ok("t"), Err(error)]);
        assert_eq!(message(found), Some(from_get));
        assert_eq!(seen, [put(), get(ROLE, Some("t"))]);
    }
}

/// `IMDSFetcher._get_request` and `_needs_retry_for_credentials`.
#[test]
fn a_get_is_retried_for_a_bad_answer_and_for_every_retryable_error() -> TestResult {
    let credentials = format!("{ROLE}test-role");
    let role_again: [Answer; 6] = [
        answer(500, "error"),
        answer(404, "nf"),
        ok(""),
        Err(TransportError::ReadTimeout),
        Err(TransportError::ConnectTimeout),
        Err(TransportError::ConnectionClosed),
    ];
    for bad in role_again {
        let (found, seen) = fetch(2, [ok("t"), bad, ok("test-role"), ok(DOCUMENT)]);
        assert!(found?.is_some());
        let again = [put(), get(ROLE, Some("t"))];
        assert_eq!(seen, [&again[..], &round(Some("t"))[1..]].concat());
    }
    let credentials_again: [Answer; 5] = [
        answer(500, DOCUMENT),
        ok(""),
        ok("not json"),
        ok("{\"AccessKeyId\": "),
        Err(TransportError::Connect),
    ];
    for bad in credentials_again {
        let (found, seen) = fetch(2, [ok("t"), ok("test-role"), bad, ok(DOCUMENT)]);
        assert!(found?.is_some());
        let again = [get(&credentials, Some("t"))];
        assert_eq!(seen, [&round(Some("t"))[..], &again[..]].concat());
    }
    Ok(())
}

/// `retrieve_iam_role_credentials`: a request out of attempts is a fetch
/// without credentials, not an error.
#[test]
fn a_get_out_of_attempts_ends_the_fetch_without_credentials() -> TestResult {
    let (found, seen) = fetch(1, [ok("t"), answer(404, "nf")]);
    assert_eq!((found?, seen), (None, round(Some("t"))[..2].to_vec()));
    let (found, seen) = fetch(2, [ok("t"), ok(""), Err(TransportError::Connect)]);
    assert_eq!(found?, None);
    assert_eq!(seen, [put(), get(ROLE, Some("t")), get(ROLE, Some("t"))]);
    let (found, seen) = fetch(1, [ok("t"), ok("test-role"), ok("not json")]);
    assert_eq!((found?, seen), (None, round(Some("t"))));
    Ok(())
}

/// A transport with no way to the service ends each request at its first
/// attempt, as running out of attempts that fail to connect ends it: no
/// token, then no role, or the refusal of a fetch without a token.
#[test]
fn a_transport_with_no_route_ends_the_fetch_without_its_attempts() -> TestResult {
    let unreachable = || Err(TransportError::NoRoute);
    let (found, seen) = fetch(3, [unreachable(), unreachable()]);
    assert_eq!((found?, seen), (None, vec![put(), get(ROLE, None)]));
    let (found, seen) = fetch(3, [ok("t"), unreachable()]);
    assert_eq!((found?, seen), (None, vec![put(), get(ROLE, Some("t"))]));
    let script = Script::new([unreachable()]);
    let mut disabled = settings(3);
    disabled.v1_disabled = true;
    let found = fetcher(disabled, &script).retrieve();
    assert_eq!(
        message(found),
        Some(format!("Error retrieving metadata: {V1_DISABLED}"))
    );
    assert_eq!(script.seen(), [put()]);
    Ok(())
}

/// `range` of a count below one is empty.
#[test]
fn no_attempts_send_nothing() -> TestResult {
    for num_attempts in [0, -1, i64::MIN] {
        let (found, seen) = fetch(num_attempts, [ok("t")]);
        assert_eq!((found?, seen), (None, vec![]), "{num_attempts}");
    }
    // The fetch still has no token, which is refused before the attempts
    // are counted.
    let script = Script::new([]);
    let mut disabled = settings(0);
    disabled.v1_disabled = true;
    let found = fetcher(disabled, &script).retrieve();
    assert_eq!(
        message(found),
        Some(format!("Error retrieving metadata: {V1_DISABLED}"))
    );
    assert_eq!(script.seen(), []);
    Ok(())
}

/// `_assert_v1_enabled`: without a token the fetch is refused, and an
/// empty token is none. A token request the service calls bad still ends
/// the fetch first.
#[test]
fn a_fetch_without_a_token_is_refused_when_v1_is_disabled() -> TestResult {
    let disabled = |answers: Vec<Answer>| {
        let script = Script::new(answers);
        let mut configured = settings(2);
        configured.v1_disabled = true;
        (fetcher(configured, &script).retrieve(), script.seen())
    };
    let refusal = Some(format!("Error retrieving metadata: {V1_DISABLED}"));
    let (found, seen) = disabled(vec![answer(404, "nf"), ok("test-role"), ok(DOCUMENT)]);
    assert_eq!((message(found), seen), (refusal.clone(), vec![put()]));
    let (found, seen) = disabled(vec![ok(""), ok("test-role"), ok(DOCUMENT)]);
    assert_eq!((message(found), seen), (refusal.clone(), vec![put()]));
    let exhausted = vec![answer(500, "error"), Err(TransportError::Connect)];
    let (found, seen) = disabled(exhausted);
    assert_eq!((message(found), seen), (refusal, vec![put(), put()]));
    let (found, seen) = disabled(vec![answer(400, "bad")]);
    assert_eq!((found?, seen), (None, vec![put()]));
    let (found, seen) = disabled(vec![ok("t"), ok("test-role"), ok(DOCUMENT)]);
    assert!(found?.is_some());
    assert_eq!(seen, round(Some("t")));
    Ok(())
}

/// `token is not None`, so the header is sent empty.
#[test]
fn an_empty_token_is_sent_as_an_empty_header() -> TestResult {
    let (found, seen) = fetch(1, [ok(""), ok("test-role"), ok(DOCUMENT)]);
    assert!(found?.is_some());
    assert_eq!(seen, round(Some("")));
    Ok(())
}

/// urllib3 refuses the timeout as it opens its pool, before anything is
/// sent, and botocore does not retry what it wraps that in.
#[test]
fn a_timeout_that_is_refused_fails_the_first_request() -> TestResult {
    let script = Script::new([ok("t")]);
    let mut configured = settings(2);
    configured.timeout = Timeout::Refused("not positive".into());
    let found = fetcher(configured.clone(), &script).retrieve();
    assert_eq!(
        message(found).as_deref(),
        Some("An HTTP Client raised an unhandled exception: not positive")
    );
    assert_eq!(script.seen(), []);
    // No attempt is no request to refuse.
    configured.num_attempts = 0;
    assert_eq!(fetcher(configured, &script).retrieve()?, None);
    Ok(())
}

/// A base URL in a form this crate does not read fails the first request
/// the same way.
#[test]
fn an_endpoint_that_cannot_be_sent_to_fails_the_first_request() {
    let script = Script::new([ok("t")]);
    let mut configured = settings(2);
    configured.base_url = "http://[fe80::1%eth0]/".into();
    let found = fetcher(configured, &script).retrieve();
    assert_eq!(
        message(found).as_deref(),
        Some(
            "An HTTP Client raised an unhandled exception: cannot ask the instance metadata \
             service for credentials: this form of ec2_metadata_service_endpoint is not supported"
        )
    );
    assert_eq!(script.seen(), []);
}

/// `IMDSFetcher._construct_url`.
#[test]
fn a_url_joins_the_base_and_the_path_with_one_slash() -> TestResult {
    for (base, token_url) in [
        (
            "http://imds.invalid",
            "http://imds.invalid/latest/api/token",
        ),
        (
            "http://imds.invalid/",
            "http://imds.invalid/latest/api/token",
        ),
        (
            "http://imds.invalid/p",
            "http://imds.invalid/p/latest/api/token",
        ),
        (
            "http://[fd00:ec2::254]/",
            "http://[fd00:ec2::254]/latest/api/token",
        ),
    ] {
        let script = Script::new([answer(400, "bad")]);
        let mut configured = settings(1);
        configured.base_url = base.into();
        assert_eq!(fetcher(configured, &script).retrieve()?, None);
        let urls: Vec<String> = script.requests().into_iter().map(|r| r.url).collect();
        assert_eq!(urls, [token_url]);
    }
    Ok(())
}

/// What the fetch makes of a credentials document.
fn document(body: &str) -> Fetched {
    fetch(1, [ok("t"), ok("test-role"), ok(body)]).0
}

/// `_contains_all_credential_fields`: a document without all four members
/// is a fetch without credentials, and nothing else in it is looked at.
#[test]
fn a_document_needs_the_four_members_and_nothing_more() -> TestResult {
    for missing in ["AccessKeyId", "SecretAccessKey", "Token", "Expiration"] {
        let body = DOCUMENT.replace(missing, "Other");
        assert_eq!(document(&body)?, None, "{missing}");
    }
    let denied = r#"{"Code": "AssumeRoleUnauthorizedAccess", "Message": "x"}"#;
    assert_eq!(document(denied)?, None);
    // Nor is JSON that is no object.
    for body in ["[1]", "[]", "\"abc\"", "{}", "5", "null"] {
        assert_eq!(document(body)?, None, "{body}");
    }
    let failure = DOCUMENT.replace("Success", "Failure");
    assert_eq!(
        document(&failure)?.map(|found| found.access_key),
        Some("AKIDIMDS".into())
    );
    Ok(())
}

/// botocore stores the values unchecked, and signs with a token only when
/// it is not empty.
#[test]
fn a_documents_values_must_be_ones_credentials_can_hold() -> TestResult {
    let with = |member: &str, value: &str| {
        let mut parsed: Value = serde_json::from_str(DOCUMENT)?;
        parsed[member] = serde_json::from_str(value)?;
        Ok::<_, serde_json::Error>(document(&parsed.to_string()))
    };
    for key in ["AccessKeyId", "SecretAccessKey", "Token"] {
        let provider = "iam-role";
        assert_eq!(with(key, "5")?, Err(LoadError::Metadata { provider, key }));
    }
    let found = with("Token", "\"\"")?;
    assert_eq!(found?.map(|found| found.token), Some(String::new()));
    for (value, text) in [("null", "null"), ("5", "5"), ("\"soon\"", "soon")] {
        assert_eq!(
            with("Expiration", value)?,
            Err(LoadError::Expiry {
                provider: "iam-role",
                value: text.into()
            })
        );
    }
    Ok(())
}

/// The fetcher's clock reads a day before the service's expiry until a
/// test moves it.
#[test]
fn an_expiry_near_the_clock_is_moved_only_in_the_services_form() -> TestResult {
    let time = Time::new(EXPIRY - 17 * 60);
    let expiry = |text: &str, jitter: u64| {
        let body = DOCUMENT.replace("2037-10-21T07:28:00Z", text);
        let script = Script::new([ok("t"), ok("test-role"), ok(&body)]);
        let fetcher = fetcher(settings(1), &script)
            .with_clock(time.clock())
            .with_jitter(move || jitter);
        let found = fetcher.retrieve()?.ok_or("no credentials")?;
        Ok::<_, Box<dyn std::error::Error>>(found.expiry.duration_since(UNIX_EPOCH)?.as_secs())
    };
    // Seventeen minutes are left, and botocore keeps seventeen to
    // twenty-five ahead: its window, two minutes and the jitter. One
    // second more is outside the least of them. An expiry in the past
    // moves as well, and one in another form never does.
    for (text, jitter, expected) in [
        ("2037-10-21T07:28:00Z", 0, EXPIRY),
        ("2037-10-21T07:28:00Z", 480, EXPIRY + 480),
        ("2037-10-21T07:28:00Z", 481, EXPIRY),
        ("2037-10-21T07:28:00Z", 1, EXPIRY + 1),
        ("2037-10-21t07:28:00z", 1, EXPIRY),
        ("2037-10-21T07:28:01Z", 0, EXPIRY + 1),
        ("2000-01-01T00:00:00Z", 0, EXPIRY),
        ("2000-01-01T00:00:00.000Z", 0, 946_684_800),
        ("2037-10-21T07:28:00.000Z", 480, EXPIRY),
        ("2037-10-21T07:28:00+00:00", 480, EXPIRY),
    ] {
        assert_eq!(expiry(text, jitter)?, expected, "{text} {jitter}");
    }
    Ok(())
}

#[test]
fn a_token_or_a_name_that_is_not_utf8_is_refused() {
    let bytes = |body: &[u8]| {
        Ok(Response {
            status: 200,
            body: body.to_vec(),
        })
    };
    let refused = |key| {
        Err(LoadError::Metadata {
            provider: "iam-role",
            key,
        })
    };
    let (found, seen) = fetch(1, [bytes(b"t\xff"), ok("test-role")]);
    assert_eq!((found, seen), (refused("the session token"), vec![put()]));
    let (found, seen) = fetch(1, [ok("t"), bytes(b"r\xff"), ok(DOCUMENT)]);
    assert_eq!(found, refused("the role's name"));
    assert_eq!(seen, round(Some("t"))[..2]);
}

/// A fetcher is the provider's [`RoleFetcher`]: the chain's walk and each
/// refresh are one fetch.
#[test]
fn the_provider_fetches_as_it_loads_and_again_as_it_refreshes() -> TestResult {
    let later = DOCUMENT
        .replace("AKIDIMDS", "AKIDLATER")
        .replace("07:28:00Z", "09:28:00Z");
    let script = Script::new([
        ok("t"),
        ok("test-role"),
        ok(DOCUMENT),
        ok("u"),
        ok("test-role"),
        ok(&later),
    ]);
    let time = Time::new(EXPIRY - 3600);
    let fetcher = fetcher(settings(1), &script).with_clock(time.clock());
    let found = RoleFetcher::from(fetcher).load()?.ok_or("no credentials")?;
    let Loaded::Refreshable(found) = found.with_clock(time.clock()) else {
        return Err("the credentials do not refresh".into());
    };
    assert_eq!(found.frozen()?.access_key_id(), "AKIDIMDS");
    assert_eq!(script.seen(), round(Some("t")));
    // Fourteen minutes are left: a refresh is due.
    time.advance(46 * 60);
    assert_eq!(found.frozen()?.access_key_id(), "AKIDLATER");
    assert_eq!(script.seen(), [round(Some("t")), round(Some("u"))].concat());
    Ok(())
}

#[test]
fn debug_output_never_shows_a_token_or_a_secret() {
    let script = Script::new([ok("imds-token"), ok("test-role"), ok(DOCUMENT)]);
    let fetcher = fetcher(settings(1), &script);
    let found = fetcher.retrieve();
    let debug = format!("{fetcher:?} {found:?} {:?}", script.sent);
    let response = format!("{:?}", ok(DOCUMENT));
    for secret in ["imds-token", "imds-secret"] {
        assert!(!debug.contains(secret), "{debug}");
        assert!(!response.contains(secret), "{response}");
    }
    assert!(debug.contains(TOKEN_HEADER) && debug.contains("AKIDIMDS"));
}

/// An endpoint botocore accepts may name a user and a password, which the
/// fetcher's requests then carry in their URLs.
#[test]
fn debug_output_never_shows_an_endpoint_s_user_or_password() {
    let request = Request {
        method: "GET",
        url: "http://MARKER-user:MARKER-password@imds.invalid/latest/api/token".into(),
        headers: vec![(TOKEN_HEADER, "MARKER-token".into())],
    };
    let debug = format!("{request:?}");
    assert!(!debug.contains("MARKER"), "{debug}");
    assert!(
        debug.contains("http://***@imds.invalid/latest/api/token"),
        "{debug}"
    );
}
