//! S3-specific endpoint parameters evaluated by the shared CRT rules engine.
//! The endpoint settings `endpoint_config` reads and the `s3` block's inputs
//! the record resolved become the rules' parameters as botocore's S3 client
//! computes them (`compute_endpoint_resolver_builtin_defaults`,
//! `ClientEndpointBridge`), and a rule error the request's parameters reach
//! becomes the error botocore raises for it at request time
//! (`EndpointRulesetResolver.construct_endpoint`).
use awscli_argparse::json::{self, JsonValue};
use cli_core::endpoint_config::{AddressingStyle, S3Block};
#[doc(inline)]
pub use cli_core::proxy::netloc;
use crt::redirect::ResolveError;
/// The region botocore's S3 client resolves to when none is configured: the
/// partition endpoint its legacy resolver names, which the rules map to the
/// global endpoint.
pub const GLOBAL_REGION: &str = "aws-global";
/// botocore's `S3_ACCELERATE_WHITELIST`: the one label that may sit between
/// `s3-accelerate` and `amazonaws.com` in an accelerate endpoint.
const ACCELERATE_FEATURE_LABEL: &str = "dualstack";
/// The client whose endpoint netloc `resolve` also returns: botocore tests a
/// proxy bypass list against it once per client
/// (`EndpointCreator.create_endpoint`, `should_bypass_proxies`). botocore
/// resolves that endpoint with its legacy resolver
/// (`ClientArgsCreator.get_client_args`), which agrees with the rules for a
/// bucketless request in the common regions, dual-stack included, and never
/// moves to the accelerate host, which botocore picks per request. Differences
/// handled here include no region, FIPS pseudo-regions, and `s3-external-1`.
/// The rest, for some exotic regions and variants, are a residual only a bypass
/// entry naming the exact host can observe.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum ClientNetloc {
    /// No bypass list is in force.
    #[default]
    None,
    /// The client of the region a setting names.
    ConfiguredRegion,
    /// botocore's client when no setting names a region: the `aws-global`
    /// endpoint, `s3.amazonaws.com`, whatever region the request defaults to.
    DefaultRegion,
}
impl ClientNetloc {
    /// The netloc a client needs: none without a bypass list.
    pub fn select(bypass_list: bool, region_configured: bool) -> Self {
        if !bypass_list {
            return Self::None;
        }
        if region_configured {
            Self::ConfiguredRegion
        } else {
            Self::DefaultRegion
        }
    }
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Options<'a> {
    pub endpoint: Option<&'a str>,
    pub use_fips: bool,
    pub use_dual_stack: bool,
    /// The `s3` block's addressing style, which decides the rules'
    /// ForcePathStyle with the endpoint and `accelerate`.
    pub addressing_style: AddressingStyle,
    /// The `s3` block's `use_accelerate_endpoint`.
    pub accelerate: bool,
    /// Which client's netloc `Endpoint::client_netloc` holds, if any; without
    /// a configured endpoint that costs a second evaluation of the rules.
    pub client_netloc: ClientNetloc,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Endpoint {
    pub url: Vec<u8>,
    pub properties: Vec<u8>,
    pub signing_region: Option<String>,
    /// `urlparse(endpoint_url).netloc` of the client botocore builds: the
    /// configured endpoint, or the rules' endpoint for no bucket in the
    /// client's region (`ClientNetloc`). botocore tests the proxy bypass list
    /// against it once per client. None unless requested.
    pub client_netloc: Option<String>,
    /// Owned inputs for re-resolving this bucket after a region redirect;
    /// absent without a bucket the redirect policy supports.
    pub recipe: Option<Recipe>,
}
/// Keeps the original override, not the bucket-expanded request URL, and
/// the command's loaded rules, so re-resolution never re-reads configuration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Recipe {
    bucket: String,
    client_region: String,
    endpoint: Option<String>,
    use_fips: bool,
    use_dual_stack: bool,
    addressing_style: AddressingStyle,
    accelerate: bool,
    rules: crate::endpoint_rules::Rules,
}
impl crt::redirect::Resolver for Recipe {
    fn bucket(&self) -> &str {
        &self.bucket
    }
    fn client_region(&self) -> &str {
        &self.client_region
    }
    /// Evaluates the rules directly: the discovered region gets no name check
    /// or FIPS normalization, and the original proxy decision is untouched.
    fn resolve(&self, region: &str) -> Result<crt::redirect::ResolvedEndpoint, ResolveError> {
        let options = Options {
            endpoint: self.endpoint.as_deref(),
            use_fips: self.use_fips,
            use_dual_stack: self.use_dual_stack,
            addressing_style: self.addressing_style,
            accelerate: self.accelerate,
            client_netloc: ClientNetloc::None,
        };
        let endpoint = match resolve_rules(&self.rules, region, Some(&self.bucket), options) {
            Ok(Resolved::Endpoint(endpoint)) => endpoint,
            Ok(Resolved::RuleError(_)) | Err(EndpointError::InvalidEndpoint) => {
                return Err(ResolveError::InvalidEndpoint);
            }
            Err(_) => return Err(ResolveError::RulesUnavailable),
        };
        Ok(crt::redirect::ResolvedEndpoint {
            url: String::from_utf8(endpoint.url).map_err(|_| ResolveError::RulesUnavailable)?,
            signing_region: endpoint.signing_region,
        })
    }
}
#[derive(Debug)]
#[non_exhaustive]
pub enum EndpointError {
    InvalidProperties,
    InvalidEndpoint,
    UserVisibleFailure,
    Configuration(cli_core::endpoint_config::EndpointError),
    Rules(crate::endpoint_rules::RulesError),
    Io(std::io::Error),
}
impl std::fmt::Display for EndpointError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidProperties => f.write_str("invalid endpoint properties"),
            Self::InvalidEndpoint => f.write_str("invalid endpoint"),
            Self::UserVisibleFailure => f.write_str("endpoint configuration failed"),
            Self::Configuration(error) => error.fmt(f),
            Self::Rules(error) => error.fmt(f),
            Self::Io(error) => error.fmt(f),
        }
    }
}
impl std::error::Error for EndpointError {}
/// The error botocore raises at request time for a rule error of the
/// ruleset: `str()` of the exception, which the handlers render in each
/// command's shape.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleError {
    /// The message, after botocore's translation of some rule messages into
    /// its older exception types.
    pub message: String,
    /// The client's URL, independent of the refused request's bucket and
    /// variants. Filled by `resolve` so transfers can still validate their
    /// CRT client setup.
    pub client_url: Option<String>,
}
/// What resolving a request's endpoint produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Resolved {
    /// The request's endpoint.
    Endpoint(Endpoint),
    /// The rule error the request's parameters reach, which botocore raises
    /// when it resolves the request's endpoint, before sending it.
    RuleError(RuleError),
}
/// Validates every auth scheme and returns only the first scheme's region.
pub fn parse_signing_region(properties: &[u8]) -> Result<Option<String>, EndpointError> {
    let value = json::parse(properties).map_err(|_| EndpointError::InvalidProperties)?;
    let JsonValue::Object(object) = value else {
        return Err(EndpointError::InvalidProperties);
    };
    let Some(schemes) = object.get("authSchemes") else {
        return Ok(None);
    };
    let JsonValue::Array(schemes) = schemes else {
        return Err(EndpointError::InvalidProperties);
    };
    let regions = schemes
        .iter()
        .map(scheme_region)
        .collect::<Result<Vec<_>, _>>()?;
    Ok(regions.first().copied().flatten().map(str::to_owned))
}
fn scheme_region(scheme: &JsonValue) -> Result<Option<&str>, EndpointError> {
    let JsonValue::Object(scheme) = scheme else {
        return Err(EndpointError::InvalidProperties);
    };
    match scheme.get("signingRegion") {
        None | Some(JsonValue::Null) => Ok(None),
        Some(JsonValue::String(region)) => Ok(Some(region)),
        _ => Err(EndpointError::InvalidProperties),
    }
}
/// Configures only the S3 rule parameters [`crt::endpoints::Parameters`]
/// carries; the rule set's others stay unset.
pub fn parameters<'a>(
    region: &'a str,
    bucket: Option<&'a str>,
    options: Options<'a>,
) -> crt::endpoints::Parameters<'a> {
    crt::endpoints::Parameters {
        region,
        bucket,
        use_fips: options.use_fips,
        use_dual_stack: options.use_dual_stack,
        endpoint: options.endpoint,
        force_path_style: Some(force_path_style(
            options.addressing_style,
            options.accelerate,
            options.endpoint,
        )),
        accelerate: Some(options.accelerate),
        use_global_endpoint: Some(false),
        disable_multi_region_access_points: Some(false),
        use_arn_region: None,
    }
}
/// The endpoint of `bucket` in `region`, or the rule error its parameters
/// reach, with the client netloc when `options.client_netloc` asks for it.
/// A FIPS pseudo-region is the region it wraps with FIPS on, for the
/// request as for the client, as botocore's client creation normalizes it
/// (`ClientCreator._normalize_fips_region`); a configured endpoint drops that
/// FIPS as it drops the setting's
/// (`compute_endpoint_resolver_builtin_defaults`).
/// `EndpointError::InvalidEndpoint` is a region or an endpoint botocore's
/// client creation refuses, or a rule error native does not render as
/// botocore's request-time error (`rule_error`).
pub fn resolve(
    view: pyload::View<'_>,
    region: &str,
    bucket: Option<&str>,
    mut options: Options<'_>,
) -> Result<Resolved, EndpointError> {
    // botocore validates the region as configured, before it normalizes it
    // (`Session._resolve_region_name`).
    if !cli_core::region::is_valid_name(region) {
        return Err(EndpointError::InvalidEndpoint);
    }
    let normalized = fips_pseudo_region(region);
    let region = normalized.as_deref().unwrap_or(region);
    if normalized.is_some() && options.endpoint.is_none() {
        options.use_fips = true;
    }
    let rules = crate::endpoint_rules::Rules::load(view, "s3").map_err(EndpointError::Rules)?;
    let mut endpoint = match resolve_rules(&rules, region, bucket, options)? {
        Resolved::Endpoint(endpoint) => endpoint,
        Resolved::RuleError(mut rule_error) => {
            require_client_endpoint_if_accelerated(&rules, region, bucket, options)?;
            rule_error.client_url = Some(resolve_client_url(&rules, region, options)?);
            return Ok(Resolved::RuleError(rule_error));
        }
    };
    if options.client_netloc != ClientNetloc::None {
        endpoint.client_netloc = Some(resolve_client_netloc(&rules, region, options)?);
    }
    endpoint.recipe = bucket
        .filter(|bucket| crt::redirect::supports_bucket(bucket))
        .map(|bucket| Recipe {
            bucket: bucket.to_owned(),
            client_region: region.to_owned(),
            endpoint: options.endpoint.map(str::to_owned),
            use_fips: options.use_fips,
            use_dual_stack: options.use_dual_stack,
            addressing_style: options.addressing_style,
            accelerate: options.accelerate,
            rules,
        });
    Ok(Resolved::Endpoint(endpoint))
}
fn require_client_endpoint_if_accelerated(
    rules: &crate::endpoint_rules::Rules,
    region: &str,
    bucket: Option<&str>,
    options: Options<'_>,
) -> Result<(), EndpointError> {
    if !options.accelerate {
        return Ok(());
    }
    let client = Options {
        accelerate: false,
        client_netloc: ClientNetloc::None,
        ..options
    };
    resolve_rules(rules, region, bucket, client).map(drop)
}
fn resolve_rules(
    rules: &crate::endpoint_rules::Rules,
    region: &str,
    bucket: Option<&str>,
    options: Options<'_>,
) -> Result<Resolved, EndpointError> {
    let resolved = rules
        .resolve(parameters(region, bucket, options))
        .map_err(EndpointError::Rules)?;
    match resolved {
        crt::endpoints::Resolved::Endpoint { url, properties } => {
            let signing_region = parse_signing_region(&properties)?;
            Ok(Resolved::Endpoint(Endpoint {
                url,
                properties,
                signing_region,
                client_netloc: None,
                recipe: None,
            }))
        }
        crt::endpoints::Resolved::RuleError(message) => Ok(Resolved::RuleError(rule_error(
            &String::from_utf8_lossy(&message),
        )?)),
    }
}
/// Resolves configuration while preserving the missing-services diagnostic bytes.
pub fn configured_values(
    environment: &impl cli_core::EnvMap,
    files: &awscli_config::ParsedFiles,
    cli_endpoint: Option<&str>,
    profile: Option<&str>,
    mut stderr: impl std::io::Write,
) -> Result<cli_core::endpoint_config::Values, EndpointError> {
    match cli_core::endpoint_config::resolve(environment, files, "s3", cli_endpoint, profile) {
        Ok(values) => Ok(values),
        Err(cli_core::endpoint_config::EndpointError::MissingServicesSection(section)) => {
            writeln!(
                stderr,
                "The profile is configured to use the services section but the \"{\
            section}\" services configuration does not exist."
            )
            .map_err(EndpointError::Io)?;
            stderr.flush().map_err(EndpointError::Io)?;
            Err(EndpointError::UserVisibleFailure)
        }
        Err(error) => Err(EndpointError::Configuration(error)),
    }
}
/// The S3 endpoint after applying the configured endpoint settings from the
/// command line, the environment, and the selected profile in the parsed
/// shared files and the `s3` block's inputs, with the client netloc when
/// `cli.client_netloc` asks for it. A profile that selects a missing services
/// section is reported on `stderr` as `EndpointError::UserVisibleFailure`.
pub fn resolve_configured(
    view: pyload::View<'_>,
    environment: &impl cli_core::EnvMap,
    files: &awscli_config::ParsedFiles,
    region: &str,
    bucket: Option<&str>,
    cli: ConfiguredInput<'_>,
    stderr: impl std::io::Write,
) -> Result<Resolved, EndpointError> {
    let values = configured_values(environment, files, cli.endpoint, cli.profile, stderr)?;
    // A configured endpoint drops dual-stack whatever enables it; otherwise
    // the block's switch turns it on over the top-level setting
    // (`compute_endpoint_resolver_builtin_defaults`, `ClientEndpointBridge`).
    let block = cli.s3_block;
    let dual_stack =
        values.endpoint.is_none() && (values.use_dual_stack || block.use_dualstack_endpoint);
    // botocore's S3 client hands the rules the name of its legacy endpoint as
    // the region (`ClientArgsCreator._build_endpoint_resolver`), a configured
    // endpoint's included (`_set_region_if_custom_s3_endpoint`). With no region
    // configured that is the partition endpoint, `aws-global`, unless
    // dual-stack names us-east-1 (`EndpointResolver.construct_endpoint`). A
    // configured endpoint drops dual-stack before this, which changes neither
    // its URL nor its signing region.
    let region = if cli.region_configured || dual_stack {
        region
    } else {
        GLOBAL_REGION
    };
    resolve(
        view,
        region,
        bucket,
        Options {
            endpoint: values.endpoint.as_deref(),
            use_fips: values.use_fips,
            use_dual_stack: dual_stack,
            addressing_style: block.addressing_style,
            accelerate: block.use_accelerate_endpoint,
            client_netloc: cli.client_netloc,
        },
    )
}
#[derive(Debug, Clone, Copy, Default)]
pub struct ConfiguredInput<'a> {
    pub endpoint: Option<&'a str>,
    /// Whether a setting names the request's region, rather than the default
    /// supplying it.
    pub region_configured: bool,
    pub profile: Option<&'a str>,
    /// The selected profile's `s3` block endpoint rule inputs.
    pub s3_block: S3Block,
    pub client_netloc: ClientNetloc,
}

/// botocore's `AWS::S3::ForcePathStyle` builtin: accelerate always takes the
/// bucket out of the path; with a configured endpoint that is no accelerate
/// endpoint, anything but `virtual` keeps it in the path; otherwise only `path`
/// does. The rules still fall back to path style when the bucket cannot be a
/// host label.
pub fn force_path_style(style: AddressingStyle, accelerate: bool, endpoint: Option<&str>) -> bool {
    if accelerate {
        return false;
    }
    if endpoint.is_some_and(|url| !is_s3_accelerate_url(url)) {
        return style != AddressingStyle::Virtual;
    }
    style == AddressingStyle::Path
}
/// botocore's `is_s3_accelerate_url`: an `http` or `https` URL whose netloc, as
/// `urlsplit` returns it and compared with case, ends with `amazonaws.com`,
/// starts with the label `s3-accelerate`, and has at most the one `dualstack`
/// label between those two parts.
pub fn is_s3_accelerate_url(url: &str) -> bool {
    let Some((scheme, _)) = url.split_once(':') else {
        return false;
    };
    if !scheme.eq_ignore_ascii_case("http") && !scheme.eq_ignore_ascii_case("https") {
        return false;
    }
    let host = cli_core::proxy::netloc(url);
    if !host.ends_with("amazonaws.com") {
        return false;
    }
    // `parts[1:-2]` are the labels between the first and the last two.
    let labels = host.split('.').collect::<Vec<_>>();
    labels.first() == Some(&"s3-accelerate")
        && (labels.len() <= 3 || (labels.len() == 4 && labels[1] == ACCELERATE_FEATURE_LABEL))
}
/// The region a FIPS pseudo-region names, which botocore's client resolves
/// with `use_fips_endpoint` on (`ClientCreator._normalize_fips_region`): every
/// `fips-`, then every `-fips`, removed. None when there is none to remove.
pub fn fips_pseudo_region(region: &str) -> Option<String> {
    let normalized = region.replace("fips-", "").replace("-fips", "");
    (normalized != region).then_some(normalized)
}
/// The rule messages botocore translates into its older exception types
/// (`EndpointRulesetResolver.ruleset_error_to_botocore_exception`), each with
/// the `str()` prefix of the exception's `fmt`. An exact entry precedes the
/// prefix entry that would also match it.
const RULE_TRANSLATIONS: [RuleTranslation; 8] = [
    RuleTranslation::exact(
        "S3 Object Lambda does not support S3 Accelerate",
        UNSUPPORTED_S3,
    ),
    RuleTranslation::exact("Accelerate cannot be used with FIPS", UNSUPPORTED_S3),
    RuleTranslation::prefix("S3 Outposts does not support", UNSUPPORTED_ACCESS_POINTS),
    RuleTranslation::prefix("S3 MRAP does not support", UNSUPPORTED_ACCESS_POINTS),
    RuleTranslation::prefix(
        "S3 Object Lambda does not support",
        UNSUPPORTED_ACCESS_POINTS,
    ),
    RuleTranslation::prefix("Access Points do not support", UNSUPPORTED_ACCESS_POINTS),
    RuleTranslation::prefix("Invalid configuration:", UNSUPPORTED_ACCESS_POINTS),
    RuleTranslation::prefix(
        "Client was configured for partition",
        UNSUPPORTED_ACCESS_POINTS,
    ),
];
/// `UnsupportedS3ConfigurationError`'s format before the message.
const UNSUPPORTED_S3: &str = "Unsupported configuration when using S3: ";
/// `UnsupportedS3AccesspointConfigurationError`'s format before the message.
const UNSUPPORTED_ACCESS_POINTS: &str = "Unsupported configuration when using S3 access-points: ";
#[derive(Debug, Clone, Copy)]
struct RuleTranslation {
    whole: bool,
    text: &'static str,
    format_prefix: &'static str,
}
impl RuleTranslation {
    const fn exact(text: &'static str, format_prefix: &'static str) -> Self {
        Self {
            whole: true,
            text,
            format_prefix,
        }
    }
    const fn prefix(text: &'static str, format_prefix: &'static str) -> Self {
        Self {
            whole: false,
            text,
            format_prefix,
        }
    }
    fn matches(&self, message: &str) -> bool {
        if self.whole {
            return message == self.text;
        }
        message.starts_with(self.text)
    }
}
/// botocore's request-time error for the rule error `message`: the message,
/// or the older exception botocore translates it into
/// (`ruleset_error_to_botocore_exception`). `EndpointError::InvalidEndpoint`
/// for a rule upstream never reaches at request time, which native keeps
/// reporting as an unresolvable endpoint: a custom endpoint that is no URL,
/// which botocore's client creation rejects first
/// (`EndpointCreator.create_endpoint`), a missing region, which native always
/// resolves, and the ARN errors, which only the ARN buckets native routes to
/// Python reach.
pub fn rule_error(message: &str) -> Result<RuleError, EndpointError> {
    if is_preempted_rule(message) {
        return Err(EndpointError::InvalidEndpoint);
    }
    let prefix = RULE_TRANSLATIONS
        .iter()
        .find(|translation| translation.matches(message))
        .map_or("", |translation| translation.format_prefix);
    Ok(RuleError {
        message: format!("{prefix}{message}"),
        client_url: None,
    })
}
fn is_preempted_rule(message: &str) -> bool {
    message == "A region must be set when sending requests to S3."
        || message.starts_with("Custom endpoint `")
        || message.starts_with("Invalid region in ARN: ")
        || message.to_ascii_lowercase().starts_with("invalid arn:")
}
fn resolve_client_url(
    rules: &crate::endpoint_rules::Rules,
    region: &str,
    options: Options<'_>,
) -> Result<String, EndpointError> {
    if let Some(configured) = options.endpoint {
        return Ok(configured.to_owned());
    }
    let resolved = resolve_bucketless(rules, region, Options::default())?
        .ok_or(EndpointError::InvalidEndpoint)?;
    String::from_utf8(resolved.url).map_err(|_| EndpointError::InvalidEndpoint)
}
fn resolve_client_netloc(
    rules: &crate::endpoint_rules::Rules,
    region: &str,
    options: Options<'_>,
) -> Result<String, EndpointError> {
    debug_assert!(options.client_netloc != ClientNetloc::None);
    if let Some(configured) = options.endpoint {
        return Ok(cli_core::proxy::netloc(configured).to_owned());
    }
    let client = Options {
        accelerate: false,
        client_netloc: ClientNetloc::None,
        ..options
    };
    let client_region = client_region(region, options);
    // Legacy endpoints.json gives this region a hostname override. Variants
    // use their own templates instead; request rules never use the override.
    if client_region == "s3-external-1" && !client.use_fips && !client.use_dual_stack {
        return Ok("s3-external-1.amazonaws.com".to_owned());
    }
    let resolved = match resolve_bucketless(rules, client_region, client)? {
        Some(resolved) => resolved,
        None => resolve_bucketless(rules, region, client)?.ok_or(EndpointError::InvalidEndpoint)?,
    };
    let url = std::str::from_utf8(&resolved.url).map_err(|_| EndpointError::InvalidEndpoint)?;
    Ok(cli_core::proxy::netloc(url).to_owned())
}
fn resolve_bucketless(
    rules: &crate::endpoint_rules::Rules,
    region: &str,
    options: Options<'_>,
) -> Result<Option<Endpoint>, EndpointError> {
    match resolve_rules(rules, region, None, options) {
        Ok(Resolved::Endpoint(endpoint)) => Ok(Some(endpoint)),
        Ok(Resolved::RuleError(_)) | Err(EndpointError::InvalidEndpoint) => Ok(None),
        Err(error) => Err(error),
    }
}
fn client_region<'a>(region: &'a str, options: Options<'_>) -> &'a str {
    if options.client_netloc == ClientNetloc::DefaultRegion
        && !options.use_fips
        && !options.use_dual_stack
    {
        return GLOBAL_REGION;
    }
    region
}
#[cfg(test)]
mod tests;
