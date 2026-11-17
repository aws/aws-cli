//! What botocore's `create_credential_resolver` reads for its fetcher and
//! how the fetcher picks its base URL (`IMDSFetcher._select_base_url`).
//!
//! botocore reads the settings, and refuses the ones it cannot use, as it
//! builds its chain: before any provider is asked, and whichever provider
//! then answers. The CLI has it build the chain as its session starts, so
//! a refusal fails every command ([`InstanceMetadataSettings::refusal`]).
//!
//! The values a person writes are read as botocore reads them: a number
//! of ASCII digits with a sign and whitespace around it, a mode, an
//! endpoint. What else CPython's `int()` reads, digits outside ASCII and
//! underscores among them, is refused here with its error. A variable
//! whose value is not Unicode is refused, by name, where its text is
//! needed, and is not `true` where it is a switch. A key whose value is a
//! nested block is refused, by name, the same way.
//!
//! A configured endpoint is not an AWS product. Its URL is read as far as
//! [`super::Location`] reads one, a user and a password in it are dropped
//! and never shown, and a form that is not read fails the fetch that would
//! use it.
use super::DISABLED;
use crate::LoadError;
use crate::process::parse_failure;
use awscli_config::{Entries, ParsedFiles};
use cli_core::EnvMap;
use std::borrow::Cow;
use std::fmt;
use std::net::Ipv6Addr;
use std::time::Duration;

const ENDPOINT_MODE: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE";
const USE_IPV6: &str = "AWS_IMDS_USE_IPV6";
const ENDPOINT: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT";
const V1_DISABLED: &str = "AWS_EC2_METADATA_V1_DISABLED";
const TIMEOUT: &str = "AWS_METADATA_SERVICE_TIMEOUT";
const NUM_ATTEMPTS: &str = "AWS_METADATA_SERVICE_NUM_ATTEMPTS";
/// Every variable the provider and its settings read.
pub(crate) const VARIABLES: [&str; 7] = [
    DISABLED,
    ENDPOINT_MODE,
    USE_IPV6,
    ENDPOINT,
    V1_DISABLED,
    TIMEOUT,
    NUM_ATTEMPTS,
];
/// botocore's `METADATA_BASE_URL` and `METADATA_BASE_URL_IPv6`.
const BASE_URL: &str = "http://169.254.169.254/";
const BASE_URL_IPV6: &str = "http://[fd00:ec2::254]/";
/// The longest a request waits to connect, and for each part of a
/// response: what CPython's socket waits at most on Linux, the
/// milliseconds `poll` counts in an `int` (socketmodule.c
/// `internal_select`). A longer timeout is this one.
const WAIT_MAX: Duration = Duration::from_millis(2_147_483_647);
/// What every refusal of an endpoint this crate does not read says.
const UNSUPPORTED_ENDPOINT: &str = "cannot ask the instance metadata service for credentials: \
    this form of ec2_metadata_service_endpoint is not supported";

/// How botocore's fetcher asks the service.
#[derive(Clone, PartialEq, Eq)]
pub struct InstanceMetadataSettings {
    /// The service's base URL, botocore's `_select_base_url`: a configured
    /// endpoint, else the service's own address in the configured family.
    /// A configured endpoint is held without the user and password its URL
    /// may name.
    pub base_url: String,
    /// `metadata_service_timeout`.
    pub timeout: Timeout,
    /// `metadata_service_num_attempts`: how often each request is tried.
    /// Less than one sends nothing. A number past what an `i64` holds is
    /// the nearest it holds, which no fetch outlasts.
    pub num_attempts: i64,
    /// Whether a fetch without a token is refused, where it would
    /// otherwise go on without one (`IMDSFetcher._assert_v1_enabled`).
    pub v1_disabled: bool,
}

/// Shows the base URL without the user and password an endpoint may name.
impl fmt::Debug for InstanceMetadataSettings {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("InstanceMetadataSettings")
            .field("base_url", &masked(&self.base_url))
            .field("timeout", &self.timeout)
            .field("num_attempts", &self.num_attempts)
            .field("v1_disabled", &self.v1_disabled)
            .finish()
    }
}

/// `metadata_service_timeout` as botocore's HTTP session meets it when the
/// fetcher sends its first request.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Timeout {
    /// What the service has to accept a connection, and again to send each
    /// part of a response.
    Within(Duration),
    /// A number urllib3 refuses before anything is sent, with the text of
    /// the exception, which botocore raises as an `HTTPClientError`
    /// (`URLLib3Session.send`).
    Refused(String),
}

impl Timeout {
    /// urllib3 refuses a timeout that is not positive when it creates its
    /// pool (util/timeout.py `_validate_timeout`), and any other is
    /// at most [`WAIT_MAX`].
    fn of(seconds: i64) -> Self {
        match u64::try_from(seconds) {
            Ok(seconds) if seconds > 0 => Self::Within(Duration::from_secs(seconds).min(WAIT_MAX)),
            _ => Self::Refused(format!(
                "Attempted to set connect timeout to {seconds}, but the timeout cannot be set \
                 to a value less than or equal to 0."
            )),
        }
    }
}

/// `url` with the user and password of its authority replaced.
pub(crate) fn masked(url: &str) -> Cow<'_, str> {
    match around_credentials(url) {
        Some((start, host)) => Cow::Owned(format!("{start}***@{host}")),
        None => Cow::Borrowed(url),
    }
}

/// `url` without the user and password of its authority.
fn without_credentials(url: &str) -> String {
    match around_credentials(url) {
        Some((start, host)) => format!("{start}{host}"),
        None => url.to_owned(),
    }
}

/// What stands on either side of the user and password in `url`'s
/// authority: the URL through its `//`, and from its host on. The two are
/// everything from the `//` to the last `@` before the path. `None` for a
/// URL without them.
fn around_credentials(url: &str) -> Option<(&str, &str)> {
    let start = url.find("//")? + 2;
    let rest = &url[start..];
    let end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
    let at = rest[..end].rfind('@')?;
    Some((&url[..start], &rest[at + 1..]))
}

/// A setting as botocore's session has it.
#[derive(Clone, Copy)]
enum Setting<'a> {
    /// A variable's value, or a key's.
    Text(&'a str),
    /// A variable's value that is not Unicode.
    NotUnicode,
    /// A key with a nested block for its value.
    Block,
}

/// botocore's `ensure_boolean`: only text is ever `true`.
fn enabled(value: Option<Setting<'_>>) -> bool {
    matches!(value, Some(Setting::Text(value)) if value.eq_ignore_ascii_case("true"))
}

impl InstanceMetadataSettings {
    /// Reads each setting from its variable in `env`, else from `profile`
    /// in the shared files, as botocore's session does
    /// (`BOTOCORE_DEFAUT_SESSION_VARIABLES`).
    ///
    /// # Errors
    /// Shared files that did not parse; a variable that is not Unicode, or
    /// a key that is a nested block, where the setting is text; a timeout
    /// or a number of attempts that `int()` refuses; an endpoint mode that
    /// is neither `ipv4` nor `ipv6`; and an endpoint that is not a URL with
    /// a host (`IMDSFetcher._select_base_url`).
    pub fn resolve(
        env: &impl EnvMap,
        files: &ParsedFiles,
        profile: &str,
    ) -> Result<Self, LoadError> {
        let Some(profiles) = &files.profiles else {
            return Err(parse_failure(files));
        };
        let entries = profiles.get(profile);
        let setting = |variable, key| setting(env, entries, variable, key);
        let text = |variable, key| match setting(variable, key) {
            Some(Setting::Text(text)) => Ok(Some(text)),
            Some(Setting::NotUnicode) => Err(LoadError::InstanceMetadataNotUnicode { variable }),
            Some(Setting::Block) => Err(LoadError::InstanceMetadataBlock { key }),
            None => Ok(None),
        };
        let timeout = integer(text(TIMEOUT, "metadata_service_timeout")?)?;
        let num_attempts = integer(text(NUM_ATTEMPTS, "metadata_service_num_attempts")?)?;
        let endpoint = text(ENDPOINT, "ec2_metadata_service_endpoint")?;
        // botocore's `resolve_imds_endpoint_mode`.
        let ipv6 = match text(ENDPOINT_MODE, "ec2_metadata_service_endpoint_mode")? {
            Some(mode) if mode.eq_ignore_ascii_case("ipv6") => true,
            Some(mode) if mode.eq_ignore_ascii_case("ipv4") => false,
            Some(mode) => {
                let mode = mode.to_owned();
                return Err(LoadError::InstanceMetadataEndpointMode { mode });
            }
            None => enabled(setting(USE_IPV6, "imds_use_ipv6")),
        };
        let v1_disabled = enabled(setting(V1_DISABLED, "ec2_metadata_v1_disabled"));
        let base_url = match endpoint {
            // An empty endpoint is none (`IMDSFetcher._select_base_url`).
            Some("") | None => default_url(ipv6),
            Some(endpoint) => configured(endpoint)?,
        };
        Ok(Self {
            base_url,
            timeout: Timeout::of(timeout),
            num_attempts,
            v1_disabled,
        })
    }

    /// What botocore raises for the settings as it builds its chain, which
    /// the CLI has it do when its session starts: for every command,
    /// before the command reads its own arguments, and whichever provider
    /// would answer (awscli's `inject_assume_role_provider_cache` and
    /// botocore's `create_credential_resolver`). `None` when it raises
    /// nothing, and for shared files that did not parse, which botocore
    /// refuses earlier.
    pub fn refusal(env: &impl EnvMap, files: &ParsedFiles, profile: &str) -> Option<LoadError> {
        files.profiles.as_ref()?;
        Self::resolve(env, files, profile).err()
    }

    /// Why no request goes to the base URL, for one in a form
    /// [`Form::Unsupported`] names: the text of the `HTTPClientError` the
    /// fetch fails with. botocore accepts such a URL as it builds its
    /// chain, so only a fetch meets it.
    pub(super) fn unsendable(&self) -> Option<String> {
        (form(&self.base_url) == Form::Unsupported).then(|| UNSUPPORTED_ENDPOINT.to_owned())
    }
}

/// The base URL for a configured endpoint.
///
/// # Errors
/// botocore's `InvalidIMDSEndpointError`, for an endpoint that is not a URL
/// with a host (`IMDSFetcher._select_base_url`).
fn configured(endpoint: &str) -> Result<String, LoadError> {
    if form(endpoint) == Form::Invalid {
        let endpoint = masked(endpoint).into_owned();
        return Err(LoadError::InstanceMetadataEndpoint { endpoint });
    }
    Ok(without_credentials(endpoint))
}

/// The service's own address in the configured family.
fn default_url(ipv6: bool) -> String {
    if ipv6 { BASE_URL_IPV6 } else { BASE_URL }.to_owned()
}

/// A setting as its first source has it: the variable, Unicode or not, else
/// the profile's key, empty or not (`ChainProvider.resolve`,
/// `EnvironmentProvider.provide`).
fn setting<'a>(
    env: &'a impl EnvMap,
    entries: Option<&'a Entries>,
    variable: &str,
    key: &str,
) -> Option<Setting<'a>> {
    if let Some(value) = env.var_os(variable) {
        return Some(value.to_str().map_or(Setting::NotUnicode, Setting::Text));
    }
    let value = &entries?.get(key)?.value;
    Some(value.as_str().map_or(Setting::Block, Setting::Text))
}

/// A setting botocore converts with `int`; one that is absent is 1. The
/// literal is ASCII digits, with a sign and the whitespace `int()` strips
/// around them, and one past what an `i64` holds is the nearest it holds.
///
/// # Errors
/// CPython's `ValueError` for anything else.
fn integer(value: Option<&str>) -> Result<i64, LoadError> {
    let Some(text) = value else {
        return Ok(1);
    };
    let literal = text.trim_matches([' ', '\t', '\n', '\r', '\x0b', '\x0c']);
    let (negative, digits) = match literal.as_bytes() {
        [b'-', digits @ ..] => (true, digits),
        [b'+', digits @ ..] => (false, digits),
        digits => (false, digits),
    };
    if digits.is_empty() || !digits.iter().all(u8::is_ascii_digit) {
        return Err(LoadError::InstanceMetadataInteger {
            value: text.to_owned(),
        });
    }
    // Only a number past an `i64` fails to parse now.
    Ok(literal
        .parse()
        .unwrap_or(if negative { i64::MIN } else { i64::MAX }))
}

/// What becomes of a configured endpoint.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Form {
    /// botocore's `is_valid_uri` is true, and the requests for it are ones
    /// [`super::Location`] reads.
    Valid,
    /// `is_valid_uri` is false, so botocore raises
    /// `InvalidIMDSEndpointError` as it builds its chain.
    Invalid,
    /// What botocore makes of it depends on rules of `urlsplit` and
    /// urllib3 that are not ported: a space or a control character at its
    /// start, one of those or a character past ASCII in its authority, and
    /// brackets around anything but an IPv6 address without a zone. A fetch
    /// that would use it fails and says so.
    Unsupported,
}

fn form(endpoint: &str) -> Form {
    // `is_valid_ipv6_endpoint_url` and `is_valid_endpoint_url` both refuse
    // these first.
    if endpoint.contains(['\t', '\r', '\n']) {
        return Form::Invalid;
    }
    // `urlsplit` strips spaces and control characters from the start.
    if endpoint.starts_with(|first: char| first <= ' ') {
        return Form::Unsupported;
    }
    // `is_valid_endpoint_url`: no host at all.
    let Some(netloc) = netloc(endpoint) else {
        return Form::Invalid;
    };
    // `urlsplit` normalizes what is not ASCII before it looks for a host.
    if !netloc.bytes().all(|byte| byte.is_ascii_graphic()) {
        return Form::Unsupported;
    }
    let host = netloc.rsplit_once('@').map_or(netloc, |(_, host)| host);
    if netloc.contains(['[', ']']) {
        return if is_bracketed_address(host) {
            Form::Valid
        } else {
            Form::Unsupported
        };
    }
    let hostname = host.split_once(':').map_or(host, |(name, _)| name);
    if is_host_name(hostname) {
        Form::Valid
    } else {
        Form::Invalid
    }
}

/// `urlsplit`'s `netloc` (urllib/parse.py `_urlsplit`): what follows `//`,
/// after a scheme if the text before the first colon is one, up to the
/// path, the query or the fragment. `None` without the two slashes.
fn netloc(url: &str) -> Option<&str> {
    let rest = match url.split_once(':') {
        Some((scheme, rest)) if is_scheme(scheme) => rest,
        _ => url,
    };
    let rest = rest.strip_prefix("//")?;
    let end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
    Some(&rest[..end])
}

fn is_scheme(text: &str) -> bool {
    text.bytes()
        .next()
        .is_some_and(|first| first.is_ascii_alphabetic())
        && text
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'+' | b'-' | b'.'))
}

/// Whether a host in brackets is an IPv6 address, which botocore accepts
/// (`is_valid_ipv6_endpoint_url`). `urlsplit` raises for brackets around
/// anything else, and botocore's pattern admits a zone, which is not read
/// here.
fn is_bracketed_address(host: &str) -> bool {
    host.strip_prefix('[')
        .and_then(|rest| rest.split_once(']'))
        .filter(|(_, port)| port.is_empty() || port.starts_with(':'))
        .is_some_and(|(address, _)| address.parse::<Ipv6Addr>().is_ok())
}

/// botocore's pattern for a host name (`is_valid_endpoint_url`): at most
/// 255 characters, and, a final dot aside, labels of one to 63 letters,
/// digits and hyphens that neither start nor end with a hyphen.
fn is_host_name(hostname: &str) -> bool {
    if hostname.is_empty() || hostname.len() > 255 {
        return false;
    }
    let hostname = hostname.strip_suffix('.').unwrap_or(hostname);
    hostname.split('.').all(|label| {
        (1..=63).contains(&label.len())
            && label
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
            && !label.starts_with('-')
            && !label.ends_with('-')
    })
}

#[cfg(test)]
mod tests;
