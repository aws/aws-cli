//! Endpoint settings for one service in the AWS CLI's precedence order: the
//! command line, then `AWS_ENDPOINT_URL_<SERVICE>` and `AWS_ENDPOINT_URL`,
//! then the selected profile's services section, then its `endpoint_url`.
//! Profile settings come from the parsed shared config and credentials files.
//! FIPS and dual-stack flags follow the environment, then the profile, and any
//! explicit endpoint clears both, as botocore's ConfiguredEndpointProvider does.
#![forbid(unsafe_code)]
use crate::{EnvMap, aws_profile, shared_config};
use awscli_config::ParsedFiles;
use std::ffi::OsStr;
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Values {
    pub endpoint: Option<String>,
    pub use_fips: bool,
    pub use_dual_stack: bool,
    pub ignore_configured: bool,
}
/// botocore's S3 addressing styles: `auto`, the default, and `virtual` let the
/// endpoint rules place the bucket, and `path` keeps it in the path.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum AddressingStyle {
    #[default]
    Auto,
    Virtual,
    Path,
}
/// The selected profile's `s3` block endpoint rule inputs, as botocore's S3
/// client reads them: the addressing style, and the accelerate and dual-stack
/// switches after `ensure_boolean`. `ClientConfig` resolves and validates them;
/// the S3 endpoint resolver combines them with the settings `resolve` reads.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct S3Block {
    /// `addressing_style`.
    pub addressing_style: AddressingStyle,
    /// `use_accelerate_endpoint`.
    pub use_accelerate_endpoint: bool,
    /// `use_dualstack_endpoint`, which turns dual-stack on whatever the
    /// top-level setting says, and never off (`ClientEndpointBridge`).
    pub use_dualstack_endpoint: bool,
}
#[derive(Clone, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum EndpointError {
    InvalidServiceName,
    MissingServicesSection(String),
}
impl std::fmt::Display for EndpointError {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidServiceName => out.write_str("invalid service name"),
            Self::MissingServicesSection(name) => write!(out, "missing services section: {name}"),
        }
    }
}
impl std::error::Error for EndpointError {}
/// The endpoint settings for `service`. Profile settings come from the
/// profile [`aws_profile::select`] names, else `default`.
///
/// # Errors
/// [`EndpointError::InvalidServiceName`] when `service` holds a byte other
/// than an ASCII letter, digit, or hyphen, and
/// [`EndpointError::MissingServicesSection`] when the lookup reaches a
/// services section the config file lacks or leaves empty.
pub fn resolve(
    env: &impl EnvMap,
    files: &ParsedFiles,
    service: &str,
    cli_endpoint: Option<&str>,
    cli_profile: Option<&str>,
) -> Result<Values, EndpointError> {
    let profile = aws_profile::select_or_default(env, cli_profile);
    let property = |key| shared_config::profile_property(files, profile, key);
    let mut values = Values {
        ignore_configured: switch(
            env,
            "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS",
            property("ignore_configured_endpoint_urls"),
        ),
        use_fips: switch(env, "AWS_USE_FIPS_ENDPOINT", property("use_fips_endpoint")),
        use_dual_stack: switch(
            env,
            "AWS_USE_DUALSTACK_ENDPOINT",
            property("use_dualstack_endpoint"),
        ),
        endpoint: cli_endpoint.map(str::to_owned),
    };
    if values.endpoint.is_none() && !values.ignore_configured {
        let variable = service_endpoint_environment_name(service)?;
        let raw = |name: &str| env.var_os(name).filter(|value| !value.is_empty());
        let selected = raw(&variable).or_else(|| raw("AWS_ENDPOINT_URL"));
        values.endpoint = if let Some(value) = selected {
            Some(value.to_string_lossy().into_owned())
        } else {
            service_endpoint(files, property("services"), service)?
                .filter(|value| !value.is_empty())
                .or_else(|| property("endpoint_url").filter(|value| !value.is_empty()))
                .map(str::to_owned)
        };
    }
    if values.endpoint.is_some() {
        values.use_fips = false;
        values.use_dual_stack = false;
    }
    Ok(values)
}
/// Whether a setting is on: present and `true` in any case, as botocore's
/// `ensure_boolean` reads a string.
pub fn bool_value(value: Option<&str>) -> bool {
    value.is_some_and(|value| value.eq_ignore_ascii_case("true"))
}
fn switch(env: &impl EnvMap, variable: &str, setting: Option<&str>) -> bool {
    match env.var_os(variable) {
        Some(value) => bool_value(value.to_str()),
        None => bool_value(setting),
    }
}
/// Whether every endpoint URL the settings could select for `service`
/// holds only ASCII bytes: the command line's, `AWS_ENDPOINT_URL_<SERVICE>`,
/// `AWS_ENDPOINT_URL`, the selected profile's services entry, and its
/// `endpoint_url`, whichever one wins. It reads before the endpoint is
/// resolved; a services section the file lacks holds no URL, and resolution
/// reports it later. False for a service name
/// `service_endpoint_environment_name` rejects.
pub fn configured_endpoints_ascii(
    env: &impl EnvMap,
    files: &ParsedFiles,
    service: &str,
    cli_endpoint: Option<&str>,
    cli_profile: Option<&str>,
) -> bool {
    let profile = aws_profile::select_or_default(env, cli_profile);
    let property = |key| shared_config::profile_property(files, profile, key);
    let variable = match service_endpoint_environment_name(service) {
        Ok(v) => v,
        Err(_) => return false,
    };
    let environment = [env.var_os(&variable), env.var_os("AWS_ENDPOINT_URL")];
    [
        cli_endpoint,
        service_endpoint(files, property("services"), service)
            .ok()
            .flatten(),
        property("endpoint_url"),
    ]
    .into_iter()
    .flatten()
    .map(str::as_bytes)
    .chain(
        environment
            .into_iter()
            .flatten()
            .map(OsStr::as_encoded_bytes),
    )
    .all(<[u8]>::is_ascii)
}
/// Whether the settings name an endpoint URL for `service`, as [`resolve`]
/// selects one: the command line's, else, unless configured endpoints are
/// ignored, the first nonempty of `AWS_ENDPOINT_URL_<SERVICE>`,
/// `AWS_ENDPOINT_URL`, the selected profile's services entry, and its
/// `endpoint_url`. botocore reports that as the `ENDPOINT_OVERRIDE` feature. A
/// services section the file lacks names none here, and resolution reports it
/// later.
pub fn endpoint_configured(
    env: &impl EnvMap,
    files: &ParsedFiles,
    service: &str,
    cli_endpoint: Option<&str>,
    cli_profile: Option<&str>,
) -> bool {
    if cli_endpoint.is_some() {
        return true;
    }
    let profile = aws_profile::select_or_default(env, cli_profile);
    let property = |key| shared_config::profile_property(files, profile, key);
    if switch(
        env,
        "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS",
        property("ignore_configured_endpoint_urls"),
    ) {
        return false;
    }
    let variable = match service_endpoint_environment_name(service) {
        Ok(v) => v,
        Err(_) => return false,
    };
    let nonempty = |name: &str| env.var_os(name).is_some_and(|value| !value.is_empty());
    nonempty(&variable)
        || nonempty("AWS_ENDPOINT_URL")
        || [
            service_endpoint(files, property("services"), service)
                .ok()
                .flatten(),
            property("endpoint_url"),
        ]
        .into_iter()
        .flatten()
        .any(|value| !value.is_empty())
}
/// Whether the native resolver reads the endpoint URL the settings select for
/// `service`, as [`resolve`] selects one, as botocore's endpoint rules do, or
/// no URL is selected (`parses_alike`). A services section the file lacks
/// selects none here, and resolution reports it later. A value that is not
/// Unicode, which [`configured_endpoint_fails`] sends to Python first, is no
/// URL the native resolver reads.
pub fn selected_endpoint_resolves_natively(
    env: &impl EnvMap,
    files: &ParsedFiles,
    service: &str,
    cli_endpoint: Option<&str>,
    cli_profile: Option<&str>,
) -> bool {
    if let Some(url) = cli_endpoint {
        return parses_alike(url);
    }
    let profile = aws_profile::select_or_default(env, cli_profile);
    let property = |key| shared_config::profile_property(files, profile, key);
    if switch(
        env,
        "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS",
        property("ignore_configured_endpoint_urls"),
    ) {
        return true;
    }
    let Ok(variable) = service_endpoint_environment_name(service) else {
        return true;
    };
    let raw = |name: &str| env.var_os(name).filter(|value| !value.is_empty());
    if let Some(url) = raw(&variable).or_else(|| raw("AWS_ENDPOINT_URL")) {
        return url.to_str().is_some_and(parses_alike);
    }
    let entry = service_endpoint(files, property("services"), service)
        .ok()
        .flatten();
    non_empty(entry)
        .or_else(|| non_empty(property("endpoint_url")))
        .is_none_or(parses_alike)
}

/// Whether the CRT's `parseURL` reads `url` as botocore's `parse_url` does.
/// Their schemes and ports must agree ([`scheme_and_port_alike`]), and so must
/// their authorities ([`authority_alike`]). botocore drops a fragment, which
/// the CRT keeps in the path; both refuse a query, with different errors; and
/// botocore's path is `quote(normalize_url_path(path))`, where the CRT only
/// brackets the path with slashes. `quote` keeps ASCII letters, digits, and
/// `-._~/` alone and escapes every other byte, an existing escape's `%`
/// included, and `urlparse` ends the last segment at a `;`.
fn parses_alike(url: &str) -> bool {
    if !scheme_and_port_alike(url) || !authority_alike(url) || url.contains('#') {
        return false;
    }
    // An empty query is none to either parser.
    if url.find('?').is_some_and(|index| index + 1 != url.len()) {
        return false;
    }
    let path = url_path(url);
    path.bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || b"-._~/".contains(&byte))
        && is_normal_path(path)
}

/// Whether `url`'s authority holds at most one literal `@`, no empty port,
/// and no port naming its scheme's default. The CRT ends userinfo at the
/// first `@` (uri.c), where `urlsplit` ends it at the last, so with more they
/// read different hosts and ports; an escaped `%40` is no separator to
/// either. Native sends the authority as spelled for the Host header. An
/// empty port, a bare `:` after the host, is none to `urlsplit`, so
/// botocore's Host header has no colon, and `http.client` leaves out a port
/// equal to the scheme's default, 80 for `http` or 443 for `https`, however
/// many zeros pad it, on a direct or tunneled request.
fn authority_alike(url: &str) -> bool {
    let Some(authority) = url_authority(url) else {
        return true;
    };
    if authority.find('@') != authority.rfind('@') {
        return false;
    }
    let Some(host_port) = url_host_port(url) else {
        return true;
    };
    if &host_port[authority_host(host_port).len()..] == ":" {
        return false;
    }
    let Some(Ok(port)) = url_port(url).map(str::parse::<u16>) else {
        return true;
    };
    let default_port = if url.starts_with("https://") { 443 } else { 80 };
    port != default_port
}

/// Whether `url` starts with the scheme `http` or `https` as spelled, which
/// is all the CRT takes, and names no port or one `urlparse` reads. botocore
/// strips leading spaces and controls and lowercases the scheme first, and
/// both refuse any other scheme, with different errors. `urlparse` refuses a
/// port that is not ASCII digits naming at most 65535, where the CRT takes
/// any number up to 2^32 - 1.
fn scheme_and_port_alike(url: &str) -> bool {
    (url.starts_with("http://") || url.starts_with("https://")) && url_port(url).is_none_or(is_port)
}

/// Whether `normalize_url_path` keeps `path`: it removes empty, `.`, and `..`
/// segments and keeps only a leading and a trailing slash. It makes an empty
/// path `/`, as the CRT does too.
fn is_normal_path(path: &str) -> bool {
    let inner = path.strip_prefix('/').unwrap_or(path);
    if inner.is_empty() {
        return true;
    }
    inner
        .strip_suffix('/')
        .unwrap_or(inner)
        .split('/')
        .all(|segment| !matches!(segment, "" | "." | ".."))
}

/// Whether botocore fails before any request on the endpoint the settings
/// select for `service`, as [`resolve`] selects one: the lookup [`resolve`]
/// mirrors reaches a services section the config file lacks or leaves empty
/// (`_get_services_config`), which a command-line URL skips, or selects a URL
/// whose host `is_valid_endpoint_url` rejects, or one that is not Unicode.
/// Python reads such a command-line or environment value with surrogate
/// escapes, which the endpoint rules' `parseURL` cannot encode; the config
/// files are UTF-8 already.
pub fn configured_endpoint_fails(
    env: &impl EnvMap,
    files: &ParsedFiles,
    service: &str,
    cli_endpoint: Option<&OsStr>,
    cli_profile: Option<&str>,
) -> bool {
    if let Some(url) = cli_endpoint {
        return url.to_str().is_none_or(|url| !is_valid_endpoint_url(url));
    }
    let profile = aws_profile::select_or_default(env, cli_profile);
    let property = |key| shared_config::profile_property(files, profile, key);
    if switch(
        env,
        "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS",
        property("ignore_configured_endpoint_urls"),
    ) {
        return false;
    }
    let Ok(variable) = service_endpoint_environment_name(service) else {
        return false;
    };
    let raw = |name: &str| env.var_os(name).filter(|value| !value.is_empty());
    if let Some(url) = raw(&variable).or_else(|| raw("AWS_ENDPOINT_URL")) {
        return url.to_str().is_none_or(|url| !is_valid_endpoint_url(url));
    }
    match service_endpoint(files, property("services"), service) {
        Err(_) => true,
        Ok(entry) => non_empty(entry)
            .or_else(|| non_empty(property("endpoint_url")))
            .is_some_and(|url| !is_valid_endpoint_url(url)),
    }
}

/// botocore's `is_valid_endpoint_url` on the host `urlsplit` finds: no tab or
/// line break anywhere, then dot-separated labels of 1 to 63 ASCII letters,
/// digits, and hyphens, no label starting or ending with a hyphen, at most 255
/// bytes, one trailing dot allowed. A bracketed host is an IPv6 literal, which
/// `is_valid_ipv6_endpoint_url` judges instead; it is left to resolution.
/// Unbalanced brackets make `urlsplit` raise, which is a failure too.
pub(crate) fn is_valid_endpoint_url(url: &str) -> bool {
    if url.contains(['\t', '\r', '\n']) {
        return false;
    }
    let Some(host) = url_host(url) else {
        return false;
    };
    if host.contains(['[', ']']) {
        return host.len() >= 2 && host.starts_with('[') && host.ends_with(']');
    }
    if host.len() > 255 {
        return false;
    }
    let name = host.strip_suffix('.').unwrap_or(host);
    name.split('.').all(is_host_label)
}

/// `(?!-)[A-Z\d-]{1,63}(?<!-)` under `re.IGNORECASE`.
fn is_host_label(label: &str) -> bool {
    (1..=63).contains(&label.len())
        && !label.starts_with('-')
        && !label.ends_with('-')
        && label
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
}

fn url_host(url: &str) -> Option<&str> {
    let host = authority_host(url_host_port(url)?);
    (!host.is_empty()).then_some(host)
}

pub(crate) fn url_port(url: &str) -> Option<&str> {
    let host_port = url_host_port(url)?;
    let (_, port) = host_port[authority_host(host_port).len()..].split_once(':')?;
    (!port.is_empty()).then_some(port)
}

fn url_authority(url: &str) -> Option<&str> {
    let rest = url_past_scheme(url).strip_prefix("//")?;
    Some(&rest[..rest.find(['/', '?', '#']).unwrap_or(rest.len())])
}

fn url_host_port(url: &str) -> Option<&str> {
    let authority = url_authority(url)?;
    Some(
        authority
            .rsplit_once('@')
            .map_or(authority, |(_, host_port)| host_port),
    )
}

/// Whether `urlsplit`'s `port` reads `text`: ASCII digits naming at most 65535.
pub(crate) fn is_port(text: &str) -> bool {
    text.bytes().all(|byte| byte.is_ascii_digit()) && text.parse::<u16>().is_ok()
}

pub(crate) fn url_path(url: &str) -> &str {
    let mut rest = url_past_scheme(url);
    if let Some(authority_rest) = rest.strip_prefix("//") {
        let authority_end = authority_rest
            .find(['/', '?', '#'])
            .unwrap_or(authority_rest.len());
        rest = &authority_rest[authority_end..];
    }
    &rest[..rest.find(['?', '#']).unwrap_or(rest.len())]
}

/// `url` past the leading C0 controls and spaces `urlsplit` strips first,
/// and past a scheme it takes.
fn url_past_scheme(url: &str) -> &str {
    let rest = url.trim_start_matches(|c: char| c <= ' ');
    match rest.split_once(':') {
        Some((scheme, after)) if is_url_scheme(scheme) => after,
        _ => rest,
    }
}

fn authority_host(host_port: &str) -> &str {
    if host_port.starts_with('[') {
        host_port
            .find(']')
            .map_or(host_port, |close| &host_port[..=close])
    } else {
        &host_port[..host_port.find(':').unwrap_or(host_port.len())]
    }
}

fn is_url_scheme(prefix: &str) -> bool {
    prefix.starts_with(|c: char| c.is_ascii_alphabetic())
        && prefix
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"+-.".contains(&byte))
}

fn non_empty(value: Option<&str>) -> Option<&str> {
    value.filter(|value| !value.is_empty())
}
/// `AWS_ENDPOINT_URL_` and `service` in uppercase with each hyphen spelled
/// `_`, the variable botocore's ConfiguredEndpointProvider reads for one service.
/// [`EndpointError::InvalidServiceName`] when `service` holds any other byte
/// than an ASCII letter, digit, or hyphen.
fn service_endpoint_environment_name(service: &str) -> Result<String, EndpointError> {
    let mut result = String::from("AWS_ENDPOINT_URL_");
    for byte in service.bytes() {
        if byte.is_ascii_alphanumeric() {
            result.push(char::from(byte.to_ascii_uppercase()));
        } else if byte == b'-' {
            result.push('_');
        } else {
            return Err(EndpointError::InvalidServiceName);
        }
    }
    Ok(result)
}
/// The `endpoint_url` nested under the service's entry in the services section
/// `services` selects, as botocore reads `services[name][service].endpoint_url`.
/// The service is a top-level option of its section, so its name folded to
/// lowercase; the nested key kept its case. None when the profile selects no
/// section or the section has no nested entry with an `endpoint_url` for the
/// service. [`EndpointError::MissingServicesSection`] when the config file has
/// no section by that name, or an empty one.
fn service_endpoint<'a>(
    files: &'a ParsedFiles,
    services: Option<&str>,
    service: &str,
) -> Result<Option<&'a str>, EndpointError> {
    let Some(name) = services.filter(|name| !name.is_empty()) else {
        return Ok(None);
    };
    // botocore tests the section's truth, so an empty one is missing too.
    let section = files
        .organized
        .services
        .get(name)
        .filter(|section| !section.is_empty())
        .ok_or_else(|| EndpointError::MissingServicesSection(name.to_owned()))?;
    Ok(section
        .get(service)
        .and_then(|entry| entry.value.as_nested())
        .and_then(|nested| nested.get("endpoint_url"))
        .map(String::as_str))
}
