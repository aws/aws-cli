//! botocore's `ContainerProvider` and `ContainerMetadataFetcher`.
//!
//! This is the provider of ECS tasks, CodeBuild and EKS Pod Identity.
//! Either endpoint variable, even empty, turns it on, and from then on it
//! answers or fails, so the chain never asks past it
//! (`ContainerProvider.load`). Its credentials are refreshable, and a
//! refresh asks the same URL with the same headers again
//! (`ContainerProvider._retrieve_or_fail`).
//!
//! The requests go through a [`Transport`] and never through a proxy:
//! botocore builds the fetcher's session without one.
//!
//! Where this differs from botocore, for values no container sets:
//!
//! * A variable that is not Unicode, a token file that cannot be read as
//!   UTF-8, and credentials that are JSON but not an object fail in this
//!   crate's own words.
//! * The allowlist reads the URL's host as [`Location`] does, and a URL
//!   it cannot read fails as one urllib3 cannot.
//! * A body that is not UTF-8 is read lossily, where botocore fails to
//!   decode it.
use crate::imds::{Location, Request, Response, Transport, TransportError, masked, raised};
use crate::{Credentials, LoadError, Loaded, Provider, Refreshable, expiry};
use cli_core::EnvMap;
use serde_json::Value;
use std::fmt;
use std::net::IpAddr;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;

const METHOD: &str = "container-role";
const RELATIVE_URI: &str = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI";
const FULL_URI: &str = "AWS_CONTAINER_CREDENTIALS_FULL_URI";
const AUTH_TOKEN: &str = "AWS_CONTAINER_AUTHORIZATION_TOKEN";
const AUTH_TOKEN_FILE: &str = "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE";
/// The variables the provider reads.
pub(crate) const VARIABLES: [&str; 4] = [RELATIVE_URI, FULL_URI, AUTH_TOKEN, AUTH_TOKEN_FILE];

/// The ECS agent, which a relative URI is a path on
/// (`ContainerMetadataFetcher.full_url`).
const RELATIVE_HOST: &str = "169.254.170.2";
/// The hosts an `http` URL may name besides a loopback address, in
/// botocore's order, which its error lists.
const ALLOWED_HOSTS: [&str; 4] = [RELATIVE_HOST, "169.254.170.23", "fd00:ec2::23", "localhost"];
/// `ContainerMetadataFetcher`'s defaults: one timeout for the connect and
/// for each read, the attempts, and the wait after each attempt that
/// fails, the last one too.
const TIMEOUT: Duration = Duration::from_secs(2);
const ATTEMPTS: usize = 3;
const SLEEP: Duration = Duration::from_secs(1);

/// Why the container provider stops the chain or fails a refresh.
///
/// The texts of [`ContainerError::Host`] and [`ContainerError::Token`] are
/// botocore's and [`ContainerError::MissingKey`]'s is CPython's, because
/// the CLI prints them. [`ContainerError::Unreadable`] stands for values
/// no container sets, so its text is this crate's own.
#[derive(Clone, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum ContainerError {
    /// botocore's `ValueError` for an `http` URL whose host is neither a
    /// loopback address nor an allowed one (`_validate_allowed_url`).
    Host { host: String },
    /// botocore's `ValueError` for an authorization token with a line
    /// break in it (`ContainerProvider._validate_auth_token`).
    Token,
    /// CPython's `KeyError` for a member the credentials lack, which
    /// botocore lets through (`ContainerProvider._create_fetcher`).
    MissingKey { key: &'static str },
    /// A variable, the token file or the answer cannot be read.
    Unreadable { reason: String },
}

impl fmt::Display for ContainerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Host { host } => write!(
                f,
                "Unsupported host '{host}'.  Can only retrieve metadata from a loopback address \
                 or one of these hosts: {}",
                ALLOWED_HOSTS.join(", ")
            ),
            Self::Token => f.write_str("Auth token value is not a legal header value"),
            // `str()` of a `KeyError` is the key's `repr`.
            Self::MissingKey { key } => write!(f, "'{key}'"),
            Self::Unreadable { reason } => f.write_str(reason),
        }
    }
}

impl std::error::Error for ContainerError {}

impl From<ContainerError> for LoadError {
    fn from(error: ContainerError) -> Self {
        Self::Container(error)
    }
}

/// The URL the provider asks and the `Authorization` header it sends, as
/// botocore's provider builds them once for every fetch.
#[derive(Clone, PartialEq, Eq)]
pub struct ContainerEndpoint {
    url: String,
    authorization: Option<String>,
}

impl ContainerEndpoint {
    /// The endpoint `env` names, or `None` when neither endpoint variable
    /// is set. The relative URI wins, and the token file wins over the
    /// token.
    ///
    /// # Errors
    /// botocore's for a token with a line break and for an `http` URL
    /// outside the allowlist, and this crate's own for a variable that is
    /// not Unicode and a token file that cannot be read.
    pub fn from_env(env: &impl EnvMap) -> Result<Option<Self>, LoadError> {
        let url = if env.var_os(RELATIVE_URI).is_some() {
            format!("http://{RELATIVE_HOST}{}", text(env, RELATIVE_URI)?)
        } else if env.var_os(FULL_URI).is_some() {
            text(env, FULL_URI)?.to_owned()
        } else {
            return Ok(None);
        };
        let authorization = if let Some(path) = env.var_os(AUTH_TOKEN_FILE) {
            Some(read_token(Path::new(path))?)
        } else if env.var_os(AUTH_TOKEN).is_some() {
            Some(text(env, AUTH_TOKEN)?.to_owned())
        } else {
            None
        };
        if authorization
            .as_deref()
            .is_some_and(|token| token.contains(['\r', '\n']))
        {
            return Err(ContainerError::Token.into());
        }
        allow(&url)?;
        Ok(Some(Self { url, authorization }))
    }
}

/// Omits the URL and the token.
impl fmt::Debug for ContainerEndpoint {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ContainerEndpoint").finish_non_exhaustive()
    }
}

fn text<'a>(env: &'a impl EnvMap, name: &'static str) -> Result<&'a str, LoadError> {
    let reason = || format!("{name} is not valid Unicode");
    env.var(name)
        .ok_or_else(|| ContainerError::Unreadable { reason: reason() }.into())
}

/// The whole file, as botocore reads it
/// (`ContainerProvider._build_headers`).
fn read_token(path: &Path) -> Result<String, LoadError> {
    std::fs::read_to_string(path).map_err(|error| {
        let reason = format!(
            "cannot read the authorization token file {}: {error}",
            path.display()
        );
        ContainerError::Unreadable { reason }.into()
    })
}

/// botocore's `_validate_allowed_url`.
fn allow(url: &str) -> Result<(), LoadError> {
    let location =
        Location::parse(url, false).ok_or_else(|| raised(TransportError::InvalidUrl, url))?;
    let loopback = location
        .host
        .parse::<IpAddr>()
        .is_ok_and(|address| address.is_loopback());
    if location.tls || loopback || ALLOWED_HOSTS.contains(&location.host.as_str()) {
        return Ok(());
    }
    Err(ContainerError::Host {
        host: location.host,
    }
    .into())
}

/// botocore's `ContainerMetadataFetcher` with its provider's fetch
/// (`ContainerProvider._create_fetcher`).
#[derive(Clone)]
pub struct ContainerFetcher {
    transport: Arc<dyn Transport>,
    sleep: Arc<dyn Fn(Duration) + Send + Sync>,
}

impl fmt::Debug for ContainerFetcher {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ContainerFetcher")
            .field("transport", &self.transport)
            .finish_non_exhaustive()
    }
}

impl ContainerFetcher {
    /// A fetcher that sends through `transport` and waits between attempts
    /// on the thread it runs on.
    pub fn new(transport: Arc<dyn Transport>) -> Self {
        Self {
            transport,
            sleep: Arc::new(std::thread::sleep),
        }
    }
    /// Waits through `sleep` in place of the thread's own.
    #[must_use]
    pub fn with_sleep(mut self, sleep: impl Fn(Duration) + Send + Sync + 'static) -> Self {
        self.sleep = Arc::new(sleep);
        self
    }
    /// What botocore's provider returns for `endpoint`: credentials that a
    /// refresh asks the same endpoint for again
    /// (`ContainerProvider._retrieve_or_fail`).
    ///
    /// # Errors
    /// botocore's `CredentialRetrievalError` once every attempt failed, and
    /// what it lets through: a transport error it does not try again, a
    /// member the credentials lack, and an expiry that cannot be read.
    pub fn load(&self, endpoint: ContainerEndpoint) -> Result<Loaded, LoadError> {
        let found = self.retrieve(&endpoint)?;
        let fetcher = self.clone();
        Ok(Refreshable::new(found, move || fetcher.retrieve(&endpoint)).into())
    }

    /// The provider's `fetch_creds`.
    fn retrieve(&self, endpoint: &ContainerEndpoint) -> Result<Credentials, LoadError> {
        credentials(self.document(endpoint)?)
    }

    /// botocore's `_retrieve_credentials`.
    fn document(&self, endpoint: &ContainerEndpoint) -> Result<Value, LoadError> {
        let mut headers = vec![("Accept", "application/json".to_owned())];
        headers.extend(
            endpoint
                .authorization
                .clone()
                .map(|token| ("Authorization", token)),
        );
        let request = Request {
            method: "GET",
            url: endpoint.url.clone(),
            headers,
        };
        let mut failure = String::new();
        for _ in 0..ATTEMPTS {
            failure = match self.transport.send(&request, TIMEOUT) {
                Ok(response) => match document(response) {
                    Ok(document) => return Ok(document),
                    Err(failure) => failure,
                },
                Err(error) => {
                    retried(&error, &request.url).ok_or_else(|| raised(error, &request.url))?
                }
            };
            (self.sleep)(SLEEP);
        }
        // `fetch_creds` wraps the fetcher's last error.
        Err(LoadError::CredentialRetrieval {
            provider: METHOD,
            error_msg: LoadError::MetadataRetrieval { error_msg: failure }.to_string(),
        })
    }
}

/// botocore's `_get_response` for a response: the
/// document, or why the attempt failed.
fn document(response: Response) -> Result<Value, String> {
    if response.status != 200 {
        let body = String::from_utf8_lossy(&response.body);
        return Err(format!(
            "Received non 200 response {} from container metadata: {body}",
            response.status
        ));
    }
    serde_json::from_slice(&response.body)
        .map_err(|_| "Unable to parse JSON returned from container metadata services".to_owned())
}

/// The text of the error for a request that failed as `error` says, when
/// it is one of botocore's `RETRYABLE_HTTP_ERRORS`. The URL is shown
/// without its user and password.
fn retried(error: &TransportError, url: &str) -> Option<String> {
    let url = masked(url);
    let text = match error {
        // `NoRoute` is no error of botocore's; a container's transport has
        // a route.
        TransportError::Connect | TransportError::NoRoute => {
            format!("Could not connect to the endpoint URL: \"{url}\"")
        }
        TransportError::ConnectTimeout => format!("Connect timeout on endpoint URL: \"{url}\""),
        TransportError::ReadTimeout => format!("Read timeout on endpoint URL: \"{url}\""),
        TransportError::ConnectionClosed => format!(
            "Connection was closed before we received a valid response from endpoint URL: \
             \"{url}\"."
        ),
        _ => return None,
    };
    Some(format!(
        "Received error when attempting to retrieve container metadata: {text}"
    ))
}

/// The credentials botocore's fetch reads from the document, in its order
/// (`fetch_creds`), as its provider holds them.
fn credentials(document: Value) -> Result<Credentials, LoadError> {
    let Value::Object(members) = document else {
        let reason = "the credentials from the container metadata service are not a JSON object";
        return Err(ContainerError::Unreadable {
            reason: reason.to_owned(),
        }
        .into());
    };
    let member = |key: &'static str| members.get(key).ok_or(ContainerError::MissingKey { key });
    let access_key = member("AccessKeyId")?;
    let secret_key = member("SecretAccessKey")?;
    let token = member("Token")?;
    let expiration = member("Expiration")?;
    // The expiry is the first value botocore reads once the fetch has
    // returned; the rest it stores unchecked and fails to sign with.
    let expiry = match expiration {
        Value::String(text) => expiry::parse(METHOD, text)?,
        other => {
            return Err(LoadError::Expiry {
                provider: METHOD,
                value: other.to_string(),
            });
        }
    };
    let token = match token {
        Value::Null => None,
        other => Some(string(other, "Token")?.to_owned()),
    };
    let account_id = members.get("AccountId").and_then(Value::as_str);
    Ok(Credentials::new(
        METHOD,
        string(access_key, "AccessKeyId")?,
        string(secret_key, "SecretAccessKey")?,
    )
    .with_session_token(token)
    .with_account_id(account_id.map(str::to_owned))
    .with_expiry(Some(expiry)))
}

fn string<'a>(value: &'a Value, key: &'static str) -> Result<&'a str, LoadError> {
    value.as_str().ok_or(LoadError::Metadata {
        provider: METHOD,
        key,
    })
}

type Fetch<'a> = dyn Fn(ContainerEndpoint) -> Result<Option<Loaded>, LoadError> + 'a;

/// How the provider asks its endpoint: [`ContainerFetcher::load`], or a
/// stand-in for a caller that asks later itself. Only a stand-in answers
/// `Ok(None)`, which passes the chain on as botocore's provider never does.
pub struct ContainerFetch<'a>(Box<Fetch<'a>>);

impl<'a> ContainerFetch<'a> {
    pub fn new(
        fetch: impl Fn(ContainerEndpoint) -> Result<Option<Loaded>, LoadError> + 'a,
    ) -> Self {
        Self(Box::new(fetch))
    }
}

impl From<ContainerFetcher> for ContainerFetch<'_> {
    fn from(fetcher: ContainerFetcher) -> Self {
        Self::new(move |endpoint| fetcher.load(endpoint).map(Some))
    }
}

impl fmt::Debug for ContainerFetch<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ContainerFetch").finish_non_exhaustive()
    }
}

/// Credentials from the container's endpoint.
pub struct ContainerProvider<'a, E> {
    env: &'a E,
    fetch: ContainerFetch<'a>,
}

impl<'a, E: EnvMap> ContainerProvider<'a, E> {
    pub fn new(env: &'a E, fetch: ContainerFetch<'a>) -> Self {
        Self { env, fetch }
    }
}

/// Omits the environment, which holds the token.
impl<E> fmt::Debug for ContainerProvider<'_, E> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ContainerProvider").finish_non_exhaustive()
    }
}

impl<E: EnvMap> Provider for ContainerProvider<'_, E> {
    fn method(&self) -> &'static str {
        METHOD
    }
    fn load(&self) -> Result<Option<Loaded>, LoadError> {
        match ContainerEndpoint::from_env(self.env)? {
            Some(endpoint) => (self.fetch.0)(endpoint),
            None => Ok(None),
        }
    }
}

#[cfg(test)]
mod tests;
