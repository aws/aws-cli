//! botocore's credential providers and chain resolver, with no CRT dependency.
//!
//! A [`Provider`] is one source of credentials and a [`Resolver`] asks an
//! ordered list of them, as botocore's `CredentialResolver` does. The
//! crate reads only the environment and the parsed shared files it is
//! given, and runs nothing but a profile's credential process, so every
//! rule here runs without the CRT or a network. The container and instance
//! metadata providers ask their services with botocore's own requests
//! ([`ContainerFetcher`], [`Fetcher`]), which they send through a
//! [`Transport`] the caller supplies.
//!
//! The chain is walked once. What it returns is a [`Loaded`]: credentials
//! that never change, or a [`Refreshable`] that carries the refresh
//! operation of the one provider that found it. A refresh calls that
//! operation and nothing else, so no other provider is asked again and the
//! chain's order is not evaluated again, as in botocore, whose resolver is
//! out of the picture once `load_credentials` returns.
#![forbid(unsafe_code)]

mod container;
mod env;
mod expiry;
mod imds;
mod process;
mod profile;
mod refresh;

#[doc(inline)]
pub use container::{
    ContainerEndpoint, ContainerError, ContainerFetch, ContainerFetcher, ContainerProvider,
};
#[doc(inline)]
pub use env::EnvProvider;
#[doc(inline)]
pub use imds::{
    Fetcher, InstanceMetadataProvider, InstanceMetadataSettings, Location, Request, Response,
    RoleCredentials, RoleFetcher, Timeout, Transport, TransportError,
};
#[doc(inline)]
pub use process::{ProcessOutput, ProcessProvider, Runner};
#[doc(inline)]
pub use profile::{ConfigProvider, SharedCredentialsProvider};
#[doc(inline)]
pub use refresh::{Clock, RefreshError, Refreshable};

use awscli_config::ParsedFiles;
use cli_core::{EnvMap, SnapshotEnv};
use std::fmt;
use std::time::SystemTime;

/// One immutable set of AWS credentials, botocore's `ReadOnlyCredentials`
/// with the `method` of its `Credentials` and the expiry of its
/// `RefreshableCredentials`.
#[derive(Clone, PartialEq, Eq)]
pub struct Credentials {
    access_key_id: String,
    secret_access_key: String,
    session_token: Option<String>,
    account_id: Option<String>,
    expiry: Option<SystemTime>,
    method: &'static str,
}

impl Credentials {
    /// Long-term credentials that the provider named `method` found.
    pub fn new(
        method: &'static str,
        access_key_id: impl Into<String>,
        secret_access_key: impl Into<String>,
    ) -> Self {
        Self {
            access_key_id: access_key_id.into(),
            secret_access_key: secret_access_key.into(),
            session_token: None,
            account_id: None,
            expiry: None,
            method,
        }
    }
    /// An empty token is no token. botocore keeps one a provider hands it
    /// and leaves the header out when it signs, as it does for every
    /// token Python counts as false.
    #[must_use]
    pub fn with_session_token(mut self, session_token: Option<String>) -> Self {
        self.session_token = session_token.filter(|token| !token.is_empty());
        self
    }
    #[must_use]
    pub fn with_account_id(mut self, account_id: Option<String>) -> Self {
        self.account_id = account_id;
        self
    }
    /// When the credentials stop being valid; `None` for ones that never do.
    #[must_use]
    pub fn with_expiry(mut self, expiry: Option<SystemTime>) -> Self {
        self.expiry = expiry;
        self
    }
    pub fn access_key_id(&self) -> &str {
        &self.access_key_id
    }
    pub fn secret_access_key(&self) -> &str {
        &self.secret_access_key
    }
    pub fn session_token(&self) -> Option<&str> {
        self.session_token.as_deref()
    }
    pub fn account_id(&self) -> Option<&str> {
        self.account_id.as_deref()
    }
    pub fn expiry(&self) -> Option<SystemTime> {
        self.expiry
    }
    /// botocore's `METHOD` of the provider that found these credentials.
    pub fn method(&self) -> &'static str {
        self.method
    }
}

/// Names the access key and the source, never the secret or the token.
impl fmt::Debug for Credentials {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Credentials")
            .field("access_key_id", &self.access_key_id)
            .field(
                "session_token",
                &self.session_token.as_ref().map(|_| "<redacted>"),
            )
            .field("account_id", &self.account_id)
            .field("expiry", &self.expiry)
            .field("method", &self.method)
            .finish_non_exhaustive()
    }
}

/// A source that is configured wrongly or that failed, which stops the
/// chain when it loads and fails a refresh when it refreshes.
///
/// Most of the messages are botocore's (exceptions.py), because the CLI
/// prints them, and [`LoadError::InstanceMetadataInteger`]'s is CPython's.
/// [`LoadError::Expiry`], [`LoadError::Metadata`],
/// [`LoadError::CredentialProcess`],
/// [`LoadError::InstanceMetadataNotUnicode`] and
/// [`LoadError::InstanceMetadataBlock`] stand where botocore lets an
/// exception of Python's or dateutil's through, or reads what this crate
/// does not, so their text is this crate's own. [`ContainerError`] says whose its texts are.
///
/// A refresh sorts them by where botocore raises. A provider that fails
/// raises inside the refresh callable, which the advisory window forgives
/// (`RefreshableCredentials._protected_refresh`).
/// [`LoadError::EmptyRefresh`], [`LoadError::Expiry`] and
/// [`LoadError::Metadata`] are faults in what a provider returned, which
/// botocore meets after the callable has returned, where nothing forgives
/// them (`RefreshableCredentials._set_from_data`).
#[derive(Clone, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum LoadError {
    /// botocore's `PartialCredentialsError`: the source has an access key
    /// but lacks `cred_var`.
    PartialCredentials {
        provider: &'static str,
        cred_var: &'static str,
    },
    /// botocore's `ConfigParseError`: the shared file at `path` did not parse.
    ConfigParse { path: String },
    /// botocore's `CredentialRetrievalError`.
    CredentialRetrieval {
        provider: &'static str,
        error_msg: String,
    },
    /// botocore's `CredentialRetrievalError` for a refresh that returned
    /// nothing (`RefreshableCredentials._set_from_data`).
    EmptyRefresh { provider: &'static str },
    /// botocore's `InvalidIMDSEndpointModeError`.
    InstanceMetadataEndpointMode { mode: String },
    /// botocore's `InvalidIMDSEndpointError`: the
    /// configured endpoint, or a URL made from it, is not one a request
    /// can be sent to.
    InstanceMetadataEndpoint { endpoint: String },
    /// CPython's `ValueError` for a timeout or a number of attempts that
    /// `int()` refuses, which botocore lets through. Its text has the
    /// value's `repr`, exact while the value is ASCII.
    InstanceMetadataInteger { value: String },
    /// An instance metadata setting's `variable` whose value is not
    /// Unicode, where the setting is text. The value is never shown: an
    /// endpoint's may hold a password.
    InstanceMetadataNotUnicode { variable: &'static str },
    /// An instance metadata setting's `key` whose value in the profile is a
    /// nested block, where the setting is text.
    InstanceMetadataBlock { key: &'static str },
    /// botocore's `MetadataRetrievalError`.
    MetadataRetrieval { error_msg: String },
    /// botocore's `ProxyConnectionError`.
    ProxyConnection { proxy_url: String },
    /// botocore's `SSLError`.
    Ssl { endpoint_url: String, error: String },
    /// botocore's `HTTPClientError`.
    HttpClient { error: String },
    /// The source's expiry is not a timestamp [`Refreshable`] can compare
    /// with the clock. botocore parses it once the provider has returned
    /// (`RefreshableCredentials._set_from_data`).
    Expiry {
        provider: &'static str,
        value: String,
    },
    /// The source's `key` is there but is not text, so [`Credentials`]
    /// cannot hold it. botocore takes the value unchecked
    /// (`RefreshableCredentials._set_from_data`) and fails when it signs
    /// with it.
    Metadata {
        provider: &'static str,
        key: &'static str,
    },
    /// The credential process could not be run, or what it printed could
    /// not be read.
    CredentialProcess { reason: String },
    /// The container provider's settings or answer are refused.
    Container(ContainerError),
}

impl fmt::Display for LoadError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::PartialCredentials { provider, cred_var } => {
                write!(
                    f,
                    "Partial credentials found in {provider}, missing: {cred_var}"
                )
            }
            Self::ConfigParse { path } => write!(f, "Unable to parse config file: {path}"),
            Self::CredentialRetrieval {
                provider,
                error_msg,
            } => write!(
                f,
                "Error when retrieving credentials from {provider}: {error_msg}"
            ),
            Self::EmptyRefresh { provider } => write!(
                f,
                "Error when retrieving credentials from {provider}: Credential refresh failed, \
                 response did not contain: access_key, secret_key, token, expiry_time"
            ),
            Self::InstanceMetadataEndpointMode { mode } => write!(
                f,
                "Invalid EC2 Instance Metadata endpoint mode: {mode} \
                 Valid endpoint modes (case-insensitive): ('ipv4', 'ipv6')."
            ),
            Self::InstanceMetadataEndpoint { endpoint } => write!(
                f,
                "Invalid endpoint EC2 Instance Metadata endpoint: {endpoint}"
            ),
            Self::InstanceMetadataInteger { value } => write!(
                f,
                "invalid literal for int() with base 10: {}",
                imds::repr_text(value)
            ),
            Self::InstanceMetadataNotUnicode { variable } => {
                write!(f, "the value of {variable} is not valid Unicode")
            }
            Self::InstanceMetadataBlock { key } => {
                write!(f, "{key} must be a value, not a nested block")
            }
            Self::MetadataRetrieval { error_msg } => {
                write!(f, "Error retrieving metadata: {error_msg}")
            }
            Self::ProxyConnection { proxy_url } => {
                write!(f, "Failed to connect to proxy URL: \"{proxy_url}\"")
            }
            Self::Ssl {
                endpoint_url,
                error,
            } => write!(f, "SSL validation failed for {endpoint_url} {error}"),
            Self::HttpClient { error } => {
                write!(f, "An HTTP Client raised an unhandled exception: {error}")
            }
            Self::Expiry { provider, value } => write!(
                f,
                "credential expiry from {provider} is not an ISO 8601 time with a zone: {value}"
            ),
            Self::Metadata { provider, key } => {
                write!(f, "{key} from {provider} is not a string")
            }
            Self::CredentialProcess { reason } => {
                write!(f, "credential process failed: {reason}")
            }
            Self::Container(error) => error.fmt(f),
        }
    }
}

impl std::error::Error for LoadError {}

impl LoadError {
    /// Whether the provider answered and the answer is at fault, which a
    /// refresh raises in either window.
    pub(crate) fn is_metadata(&self) -> bool {
        matches!(
            self,
            Self::EmptyRefresh { .. } | Self::Expiry { .. } | Self::Metadata { .. }
        )
    }
}

/// What one provider found: the two things botocore's `load` returns, a
/// `Credentials` or a `RefreshableCredentials`.
///
/// It outlives the chain that found it, and holds nothing of the chain but
/// the finding provider's own refresh operation.
#[derive(Debug)]
#[non_exhaustive]
pub enum Loaded {
    /// Credentials with no expiry, which every request is signed with.
    Static(Credentials),
    /// Credentials their provider replaces as they near their expiry.
    Refreshable(Refreshable),
}

impl Loaded {
    /// botocore's `method` of the provider that found the credentials.
    pub fn method(&self) -> &'static str {
        match self {
            Self::Static(credentials) => credentials.method(),
            Self::Refreshable(refreshable) => refreshable.method(),
        }
    }
    /// The credentials to sign one request with; see
    /// [`Refreshable::frozen`], which may block.
    ///
    /// # Errors
    /// A refresh that botocore raises to the caller.
    pub fn frozen(&self) -> Result<Credentials, RefreshError> {
        match self {
            Self::Static(credentials) => Ok(credentials.clone()),
            Self::Refreshable(refreshable) => refreshable.frozen(),
        }
    }
    /// The credentials to sign one request with, for a caller that waited
    /// behind another's refresh; see [`Refreshable::frozen_after_waiting`],
    /// which may block.
    ///
    /// # Errors
    /// A refresh that botocore raises to the caller.
    pub fn frozen_after_waiting(&self) -> Result<Credentials, RefreshError> {
        match self {
            Self::Static(credentials) => Ok(credentials.clone()),
            Self::Refreshable(refreshable) => refreshable.frozen_after_waiting(),
        }
    }
    /// The credentials while no refresh is due; see
    /// [`Refreshable::outside_advisory`], which never blocks. Credentials
    /// without an expiry are never due.
    pub fn outside_advisory(&self) -> Option<Credentials> {
        match self {
            Self::Static(credentials) => Some(credentials.clone()),
            Self::Refreshable(refreshable) => refreshable.outside_advisory(),
        }
    }
    /// The credentials while they need not wait for a refresh that is
    /// under way; see [`Refreshable::outside_mandatory`], which never
    /// blocks.
    pub fn outside_mandatory(&self) -> Option<Credentials> {
        match self {
            Self::Static(credentials) => Some(credentials.clone()),
            Self::Refreshable(refreshable) => refreshable.outside_mandatory(),
        }
    }
    /// Reads the time from `clock` in place of the system's.
    #[must_use]
    pub fn with_clock(self, clock: Clock) -> Self {
        match self {
            Self::Static(credentials) => Self::Static(credentials),
            Self::Refreshable(refreshable) => Self::Refreshable(refreshable.with_clock(clock)),
        }
    }
}

impl From<Credentials> for Loaded {
    fn from(credentials: Credentials) -> Self {
        Self::Static(credentials)
    }
}

impl From<Refreshable> for Loaded {
    fn from(refreshable: Refreshable) -> Self {
        Self::Refreshable(refreshable)
    }
}

/// One source in the chain, botocore's `CredentialProvider`.
pub trait Provider: fmt::Debug {
    /// botocore's `METHOD`, which names the provider in errors and logs.
    fn method(&self) -> &'static str;
    /// Reads the source once.
    ///
    /// `Ok(None)` means the source has no credentials, so the chain asks the
    /// next provider. A provider whose credentials expire returns a
    /// [`Refreshable`] bound to an operation that reads this source again;
    /// the operation owns what it reads, because it outlives the provider.
    ///
    /// # Errors
    /// The source is configured wrongly. The chain stops and reports the
    /// error; it does not ask the next provider.
    fn load(&self) -> Result<Option<Loaded>, LoadError>;
}

/// An ordered chain of providers, botocore's `CredentialResolver`.
#[derive(Debug)]
pub struct Resolver<'a> {
    providers: Vec<Box<dyn Provider + 'a>>,
}

impl<'a> Resolver<'a> {
    pub fn new(providers: Vec<Box<dyn Provider + 'a>>) -> Self {
        Self { providers }
    }
    /// The providers' methods, in the order the chain asks them.
    pub fn methods(&self) -> impl Iterator<Item = &'static str> {
        self.providers.iter().map(|provider| provider.method())
    }
    /// botocore's `load_credentials`: the first
    /// provider with credentials wins. `Ok(None)` is botocore's
    /// `NoCredentialsError` case.
    ///
    /// Call it once. The result refreshes itself through the provider that
    /// won, so asking the chain again is never part of a refresh.
    ///
    /// # Errors
    /// The first provider that fails stops the chain with its error.
    pub fn load_credentials(&self) -> Result<Option<Loaded>, LoadError> {
        for provider in &self.providers {
            if let Some(credentials) = provider.load()? {
                return Ok(Some(credentials));
            }
        }
        Ok(None)
    }
}

/// The profile the chain reads, and how the invocation selected it.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Profile<'a> {
    /// `--profile` named it. botocore then drops the environment provider
    /// (`create_credential_resolver`).
    Explicit(&'a str),
    /// `AWS_PROFILE` named it, or nothing did and it is `default`.
    Ambient(&'a str),
}

/// The environment variables [`default_resolver`]'s providers and
/// [`InstanceMetadataSettings::resolve`] read.
pub fn variables() -> impl Iterator<Item = &'static str> {
    text_variables()
        .chain(container::VARIABLES)
        .chain(imds::VARIABLES)
}

/// The [`variables`] that are read as text alone, where botocore reads a
/// value that is not Unicode with its surrogate escapes. The instance
/// metadata service's are not among them: its settings read such a value as
/// botocore does, and its provider's one variable disables the service
/// only when it is `true`. Nor are the container provider's, which fails
/// on such a value.
pub fn text_variables() -> impl Iterator<Item = &'static str> {
    env::VARIABLES.into_iter()
}

/// The [`variables`] of `env`, copied.
///
/// A provider whose credentials expire keeps the environment for its
/// refresh, which outlives the command's borrow of its own. The providers
/// read each variable as text, so to them a value that is not Unicode is
/// absent, and the container provider fails on one; botocore reads such a
/// value with its surrogate escapes, as
/// [`InstanceMetadataSettings::resolve`] does from the environment itself.
pub fn environment(env: &impl EnvMap) -> SnapshotEnv {
    SnapshotEnv::from_pairs(
        variables().filter_map(|name| Some((name, env.var_os(name)?.to_owned()))),
    )
}

/// Whether the chain reads `expiry`, the value of
/// `AWS_CREDENTIAL_EXPIRATION` or of a credential process's `Expiration`,
/// as an instant. botocore reads more forms than the chain does, through
/// `dateutil.parser.parse`.
pub fn reads_expiry(expiry: &str) -> bool {
    expiry::parse("", expiry).is_ok()
}

/// The chain botocore's `create_credential_resolver` builds, limited to
/// the providers this crate has.
///
/// botocore's full order is env, assume-role, web identity, SSO, shared
/// credentials file, login, process, config file, EC2 credentials file, boto
/// config, container, instance metadata (`create_credential_resolver`,
/// `ProfileProviderBuilder.providers`).
///
/// A profile's `credential_process` runs through [`Runner::system`], the
/// container's endpoint is asked through `container`, which a
/// [`ContainerFetcher`] is, and the instance metadata service through
/// `instance_metadata`, which a [`Fetcher`] is.
pub fn default_resolver<'a, E>(
    env: &'a E,
    files: &'a ParsedFiles,
    profile: Profile<'a>,
    container: ContainerFetch<'a>,
    instance_metadata: RoleFetcher,
) -> Resolver<'a>
where
    E: EnvMap + Clone + Send + Sync + 'static,
{
    let mut providers: Vec<Box<dyn Provider + 'a>> = Vec::new();
    let name = match profile {
        Profile::Explicit(name) => name,
        Profile::Ambient(name) => {
            providers.push(Box::new(EnvProvider::new(env)));
            name
        }
    };
    providers.push(Box::new(SharedCredentialsProvider::new(files, name)));
    providers.push(Box::new(ProcessProvider::new(files, name)));
    providers.push(Box::new(ConfigProvider::new(files, name)));
    providers.push(Box::new(ContainerProvider::new(env, container)));
    providers.push(Box::new(InstanceMetadataProvider::new(
        env,
        instance_metadata,
    )));
    Resolver::new(providers)
}

#[cfg(test)]
mod tests;
