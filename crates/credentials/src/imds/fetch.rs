//! botocore's `IMDSFetcher` and `InstanceMetadataFetcher`.
//!
//! One fetch is three requests: a PUT for a session token, a GET for the
//! name of the instance's role, and a GET for that role's credentials.
//! Which answers end the fetch, which are tried again and which errors
//! botocore lets through are its rules, kept here as they are. Nothing
//! waits between two attempts.
//!
//! The requests go through a [`Transport`], which stands for botocore's
//! `URLLib3Session.send` and reports what that raises as a
//! [`TransportError`].
//!
//! Where this differs from botocore:
//!
//! * The token and the role's name are sent back as the bytes the service
//!   sent. botocore decodes them by the response's `Content-Type` and
//!   encodes the token again as Latin-1, which gives the same bytes for a
//!   `text/plain` response and for any ASCII one. Bytes that are not UTF-8
//!   are refused here.
//! * A header value with a line end in it, which only a token the service
//!   sent could hold, is refused by the transport, in its own words.
//! * A document of credentials that is JSON and not an object has no
//!   credentials. A `Token` that is not a string cannot be signed with.
//! * A transport with no way to the service ([`TransportError::NoRoute`])
//!   ends the fetch as attempts that all failed to connect would, without
//!   making them.
//! * A configured endpoint whose URL is in a form this crate does not send
//!   to fails the fetch before anything is sent, in this crate's own words
//!   ([`InstanceMetadataSettings`]). botocore reads more forms.
use super::settings::masked;
use super::{InstanceMetadataSettings, METHOD, RoleCredentials, Timeout, expiration};
use crate::{Clock, LoadError};
use serde_json::{Map, Value};
use std::fmt;
use std::hash::{BuildHasher, RandomState};
use std::sync::Arc;
use std::time::Duration;

/// `IMDSFetcher`'s `_TOKEN_PATH` and `_TOKEN_TTL`.
const TOKEN_PATH: &str = "latest/api/token";
const TOKEN_TTL: &str = "21600";
const TTL_HEADER: &str = "x-aws-ec2-metadata-token-ttl-seconds";
const TOKEN_HEADER: &str = "x-aws-ec2-metadata-token";
const USER_AGENT_HEADER: &str = "User-Agent";
/// `InstanceMetadataFetcher._URL_PATH`.
const ROLE_PATH: &str = "latest/meta-data/iam/security-credentials/";
/// The error `IMDSFetcher._assert_v1_enabled` raises.
const V1_DISABLED: &str =
    "Unable to retrieve token for use in IMDSv2 call and IMDSv1 has been disabled";

/// One request of the fetcher's, botocore's `AWSRequest` without a body.
#[derive(Clone, PartialEq, Eq)]
pub struct Request {
    /// `PUT` or `GET`.
    pub method: &'static str,
    /// The URL as botocore builds it (`IMDSFetcher._construct_url`);
    /// [`super::Location`] reads it for a transport.
    pub url: String,
    /// The headers the fetcher sets, in its order. The HTTP client adds
    /// its own to them: `Host`, `Accept-Encoding: identity` and, for a
    /// PUT, `Content-Length: 0`.
    pub headers: Vec<(&'static str, String)>,
}

/// Names the headers and omits their values, the session token among
/// them, and the user and password an endpoint's URL may name.
impl fmt::Debug for Request {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let names: Vec<&str> = self.headers.iter().map(|(name, _)| *name).collect();
        f.debug_struct("Request")
            .field("method", &self.method)
            .field("url", &masked(&self.url))
            .field("headers", &names)
            .finish()
    }
}

/// A response, read whole.
#[derive(Clone, Default, PartialEq, Eq)]
pub struct Response {
    pub status: u16,
    pub body: Vec<u8>,
}

/// Omits the body, which holds the session token or the secret key.
impl fmt::Debug for Response {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Response")
            .field("status", &self.status)
            .finish_non_exhaustive()
    }
}

/// Why a request has no response: what botocore's `URLLib3Session.send`
/// raises.
#[derive(Clone, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum TransportError {
    /// `ConnectTimeoutError`: the connection did not come up in time.
    ConnectTimeout,
    /// `EndpointConnectionError`: the connection was refused, or the host
    /// has no address.
    Connect,
    /// `ReadTimeoutError`: the response stayed silent for too long.
    ReadTimeout,
    /// `ConnectionClosedError`: the connection ended before a response
    /// did.
    ConnectionClosed,
    /// `ProxyConnectionError`: no connection to the proxy at `url`, which
    /// the transport gives as botocore prints it, with a scheme and with
    /// its credentials masked.
    Proxy { url: String },
    /// `SSLError`.
    Tls { reason: String },
    /// `HTTPClientError`, for anything else the client raises.
    Client { reason: String },
    /// urllib3's `LocationParseError`: the URL cannot be read.
    InvalidUrl,
    /// Nothing botocore raises: the transport has no way to the service,
    /// so no attempt at any request can get a response.
    NoRoute,
}

impl TransportError {
    /// Whether the error is one of botocore's `RETRYABLE_HTTP_ERRORS`.
    fn is_retryable(&self) -> bool {
        matches!(
            self,
            Self::ConnectTimeout | Self::Connect | Self::ReadTimeout | Self::ConnectionClosed
        )
    }
}

/// How the fetcher's requests are sent, botocore's `URLLib3Session.send`.
pub trait Transport: Send + Sync + fmt::Debug {
    /// Sends `request` once and reads its response whole. The service has
    /// `timeout` to accept a connection, and again for each part of the
    /// response (`IMDSFetcher.__init__`).
    ///
    /// # Errors
    /// A request that got no response.
    fn send(&self, request: &Request, timeout: Duration) -> Result<Response, TransportError>;
}

/// How a fetch ends without credentials.
enum Stop {
    /// botocore's `_RetriesExceededError` and `BadIMDSRequestError`, which
    /// its fetcher answers with nothing (`retrieve_iam_role_credentials`).
    Empty,
    /// An exception it lets through.
    Raised(LoadError),
}

impl From<LoadError> for Stop {
    fn from(error: LoadError) -> Self {
        Self::Raised(error)
    }
}

/// Which GET a response answers, and so which of botocore's tests decide
/// whether it is tried again.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Get {
    RoleName,
    Credentials,
}

/// botocore's `InstanceMetadataFetcher`.
#[derive(Clone)]
pub struct Fetcher {
    settings: InstanceMetadataSettings,
    user_agent: Option<String>,
    transport: Arc<dyn Transport>,
    clock: Clock,
    jitter: Arc<dyn Fn() -> u64 + Send + Sync>,
}

impl fmt::Debug for Fetcher {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Fetcher")
            .field("settings", &self.settings)
            .field("user_agent", &self.user_agent)
            .field("transport", &self.transport)
            .finish_non_exhaustive()
    }
}

impl Fetcher {
    /// A fetcher that asks the service `settings` describe through
    /// `transport`, naming itself `user_agent` when there is one
    /// (`IMDSFetcher._add_user_agent`).
    pub fn new(
        settings: InstanceMetadataSettings,
        user_agent: Option<String>,
        transport: Arc<dyn Transport>,
    ) -> Self {
        Self {
            settings,
            user_agent,
            transport,
            clock: Clock::system(),
            // A fresh hasher's keys are the randomness the standard
            // library has.
            jitter: Arc::new(|| RandomState::new().hash_one(0)),
        }
    }
    /// Reads the time of a fetch from `clock` in place of the system's.
    #[must_use]
    pub fn with_clock(mut self, clock: Clock) -> Self {
        self.clock = clock;
        self
    }
    /// Draws from `jitter` what botocore draws with `random.randint`
    /// (`_evaluate_expiration`): any number, of which the fetcher takes
    /// the remainder it needs.
    #[must_use]
    pub fn with_jitter(mut self, jitter: impl Fn() -> u64 + Send + Sync + 'static) -> Self {
        self.jitter = Arc::new(jitter);
        self
    }
    /// botocore's `retrieve_iam_role_credentials`.
    /// `Ok(None)` is its empty answer: a request that ran out of attempts,
    /// a token request the service called bad, or a document without all
    /// of the credentials' members.
    ///
    /// # Errors
    /// What botocore lets through: a fetch without a token when
    /// `ec2_metadata_v1_disabled` is set, a proxy that cannot be reached,
    /// a failure of TLS or of the HTTP client, a URL that cannot be read,
    /// and credentials or an expiry that cannot be held.
    pub fn retrieve(&self) -> Result<Option<RoleCredentials>, LoadError> {
        match self.exchange() {
            Ok(found) => Ok(found),
            Err(Stop::Empty) => Ok(None),
            Err(Stop::Raised(error)) => Err(error),
        }
    }

    fn exchange(&self) -> Result<Option<RoleCredentials>, Stop> {
        let token = self.token()?;
        let token = token.as_deref();
        let role = self.get(ROLE_PATH, token, Get::RoleName)?;
        let role = text(role.body, "the role's name")?;
        let document = self.get(&format!("{ROLE_PATH}{role}"), token, Get::Credentials)?;
        // `_get_credentials` parses the body again, as the retry test
        // parsed it.
        let document = serde_json::from_slice(&document.body).map_err(|_| Stop::Empty)?;
        Ok(self.credentials(&document)?)
    }

    /// botocore's `_fetch_metadata_token`: `None` is a
    /// service that has no token to give.
    fn token(&self) -> Result<Option<String>, Stop> {
        let request = self.request("PUT", TOKEN_PATH, vec![(TTL_HEADER, TOKEN_TTL.to_owned())]);
        for _ in 0..self.settings.num_attempts {
            match self.send(&request) {
                Ok(response) => match response.status {
                    200 => return Ok(Some(text(response.body, "the session token")?)),
                    403..=405 => return Ok(None),
                    400 => return Err(Stop::Empty),
                    _ => {}
                },
                // Not tried again, unlike a GET's.
                Err(TransportError::ReadTimeout) => return Ok(None),
                // What attempts that all fail to connect leave.
                Err(TransportError::NoRoute) => return Ok(None),
                Err(error) if error.is_retryable() => {}
                // `_fetch_metadata_token`'s `InvalidIMDSEndpointError`.
                Err(TransportError::InvalidUrl) => {
                    return Err(LoadError::InstanceMetadataEndpoint {
                        endpoint: request.url,
                    }
                    .into());
                }
                Err(error) => return Err(raised(error, &request.url).into()),
            }
        }
        Ok(None)
    }

    /// botocore's `_get_request`.
    fn get(&self, path: &str, token: Option<&str>, get: Get) -> Result<Response, Stop> {
        // `_assert_v1_enabled`: an empty token is no token here.
        if token.is_none_or(str::is_empty) && self.settings.v1_disabled {
            return Err(LoadError::MetadataRetrieval {
                error_msg: V1_DISABLED.to_owned(),
            }
            .into());
        }
        // An empty token is still sent.
        let headers = token.map(|token| (TOKEN_HEADER, token.to_owned()));
        let request = self.request("GET", path, headers.into_iter().collect());
        for _ in 0..self.settings.num_attempts {
            match self.send(&request) {
                Ok(response) if !needs_retry(&response, get) => return Ok(response),
                Ok(_) => {}
                // Out of attempts, however many there are.
                Err(TransportError::NoRoute) => break,
                Err(error) if error.is_retryable() => {}
                Err(error) => return Err(raised(error, &request.url).into()),
            }
        }
        Err(Stop::Empty)
    }

    /// A request for `path` under the base URL (`_construct_url`), with
    /// `headers` and then the user agent (`_add_user_agent`).
    fn request(
        &self,
        method: &'static str,
        path: &str,
        mut headers: Vec<(&'static str, String)>,
    ) -> Request {
        let base = &self.settings.base_url;
        let separator = if base.is_empty() || base.ends_with('/') {
            ""
        } else {
            "/"
        };
        if let Some(user_agent) = &self.user_agent {
            headers.push((USER_AGENT_HEADER, user_agent.clone()));
        }
        Request {
            method,
            url: format!("{base}{separator}{path}"),
            headers,
        }
    }

    /// Sends `request` unless urllib3 would refuse it before anything is
    /// sent: a timeout it refuses ([`Timeout::Refused`]), which botocore
    /// wraps in `HTTPClientError` (`URLLib3Session.send`). So is an
    /// endpoint in a form this crate does not send to.
    fn send(&self, request: &Request) -> Result<Response, TransportError> {
        if let Some(reason) = self.settings.unsendable() {
            return Err(TransportError::Client { reason });
        }
        let timeout = match &self.settings.timeout {
            Timeout::Within(timeout) => *timeout,
            Timeout::Refused(reason) => {
                return Err(TransportError::Client {
                    reason: reason.clone(),
                });
            }
        };
        self.transport.send(request, timeout)
    }

    /// What botocore's fetcher returns for the service's document
    /// (`retrieve_iam_role_credentials`), and its provider then holds
    /// (`RefreshableCredentials.create_from_metadata`).
    fn credentials(&self, document: &Value) -> Result<Option<RoleCredentials>, LoadError> {
        const FIELDS: [&str; 4] = ["AccessKeyId", "SecretAccessKey", "Token", "Expiration"];
        // `_contains_all_credential_fields`: a document without all four
        // has none.
        let Value::Object(members) = document else {
            return Ok(None);
        };
        if !FIELDS.iter().all(|field| members.contains_key(*field)) {
            return Ok(None);
        }
        // The expiry is the first value botocore reads; the rest it
        // stores unchecked and fails to sign with.
        let expiry = match members.get("Expiration") {
            Some(Value::String(text)) => {
                let offset = expiration::offset((self.jitter)());
                expiration::evaluate(text, self.clock.now(), offset)?
            }
            // `strptime` and dateutil raise `TypeError` for anything else.
            other => {
                return Err(LoadError::Expiry {
                    provider: METHOD,
                    value: other.map(Value::to_string).unwrap_or_default(),
                });
            }
        };
        Ok(Some(RoleCredentials {
            access_key: string(members, "AccessKeyId")?.to_owned(),
            secret_key: string(members, "SecretAccessKey")?.to_owned(),
            // An empty token leaves the header out
            // (`SigV4Auth._modify_request_before_signing`).
            token: string(members, "Token")?.to_owned(),
            expiry,
        }))
    }
}

/// botocore's `_needs_retry_for_role_name` and
/// `_needs_retry_for_credentials`.
fn needs_retry(response: &Response, get: Get) -> bool {
    response.status != 200
        || response.body.is_empty()
        || (get == Get::Credentials && serde_json::from_slice::<Value>(&response.body).is_err())
}

/// The exception botocore lets through for an error it does not retry,
/// from a request for `url`.
pub(crate) fn raised(error: TransportError, url: &str) -> LoadError {
    match error {
        TransportError::Proxy { url } => LoadError::ProxyConnection { proxy_url: url },
        TransportError::Tls { reason } => LoadError::Ssl {
            endpoint_url: url.to_owned(),
            error: reason,
        },
        TransportError::Client { reason } => LoadError::HttpClient { error: reason },
        // A GET's `LocationParseError` stays the `HTTPClientError` urllib3's
        // message is wrapped in (`URLLib3Session.send`), without the user
        // and password botocore shows.
        TransportError::InvalidUrl => LoadError::HttpClient {
            error: format!("Failed to parse: {}", masked(url)),
        },
        // Tried again or ended on, so never let through; named for
        // completeness.
        TransportError::ConnectTimeout
        | TransportError::Connect
        | TransportError::ReadTimeout
        | TransportError::ConnectionClosed
        | TransportError::NoRoute => LoadError::HttpClient {
            error: format!("no response from {url}"),
        },
    }
}

/// A body botocore uses as text (awsrequest.py `AWSResponse.text`).
fn text(body: Vec<u8>, key: &'static str) -> Result<String, LoadError> {
    String::from_utf8(body).map_err(|_| LoadError::Metadata {
        provider: METHOD,
        key,
    })
}

/// A value botocore stores unchecked
/// (`RefreshableCredentials._set_from_data`) and cannot sign with unless
/// it is a string.
fn string<'a>(members: &'a Map<String, Value>, key: &'static str) -> Result<&'a str, LoadError> {
    members
        .get(key)
        .and_then(Value::as_str)
        .ok_or(LoadError::Metadata {
            provider: METHOD,
            key,
        })
}

#[cfg(test)]
mod tests;
