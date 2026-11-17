//! AWS region resolution: command line beats AWS_REGION beats
//! AWS_DEFAULT_REGION beats the selected profile's region in the shared
//! config and credentials files, which beats the CRT default region.
#![forbid(unsafe_code)]
use crate::{EnvMap, aws_profile, shared_config};
use awscli_config::ParsedFiles;
/// CRT's baseline region when every configured source is absent or empty.
pub const DEFAULT_REGION: &str = "us-east-1";
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum RegionError {
    EmptyRegion,
}
impl std::fmt::Display for RegionError {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.write_str("empty region")
    }
}
impl std::error::Error for RegionError {}
/// The region for one invocation, borrowed from its source: the
/// [`configured_region`], else the CRT default.
///
/// # Errors
/// An explicit empty `--region` is [`RegionError::EmptyRegion`].
pub fn resolve_region<'a>(
    env: &'a impl EnvMap,
    files: &'a ParsedFiles,
    cli_region: Option<&'a str>,
    cli_profile: Option<&str>,
) -> Result<&'a str, RegionError> {
    Ok(configured_region(env, files, cli_region, cli_profile)?.unwrap_or(DEFAULT_REGION))
}

/// The region a setting names, borrowed from its source, or none when none
/// does and the CRT default applies; botocore then builds its clients for no
/// region at all. An empty environment variable or profile setting is
/// skipped as unset, as is a variable that is not Unicode and the profile's
/// setting when either shared file failed to parse. The profile is
/// [`aws_profile::select`]'s.
///
/// # Errors
/// An explicit empty `--region` is [`RegionError::EmptyRegion`].
pub fn configured_region<'a>(
    env: &'a impl EnvMap,
    files: &'a ParsedFiles,
    cli_region: Option<&'a str>,
    cli_profile: Option<&str>,
) -> Result<Option<&'a str>, RegionError> {
    if let Some(region) = cli_region {
        return if region.is_empty() {
            Err(RegionError::EmptyRegion)
        } else {
            Ok(Some(region))
        };
    }
    Ok([
        env.var("AWS_REGION"),
        env.var("AWS_DEFAULT_REGION"),
        shared_config::profile_property(
            files,
            aws_profile::select_or_default(env, cli_profile),
            "region",
        ),
    ]
    .into_iter()
    .flatten()
    .find(|region| !region.is_empty()))
}

/// The region botocore's chain resolves, borrowed from its source, or none
/// when no source holds one: `--region`, then the first of `AWS_REGION` and
/// `AWS_DEFAULT_REGION` that is present, then the profile's `region`
/// (`_construct_cli_region_chain`). Unlike
/// [`configured_region`], an empty value is returned rather than skipped;
/// botocore builds no valid endpoint for it. A variable that is not Unicode
/// is present too, and keeps its replacement characters.
pub fn session_region<'a>(
    env: &'a impl EnvMap,
    files: &'a ParsedFiles,
    cli_region: Option<&'a str>,
    cli_profile: Option<&str>,
) -> Option<std::borrow::Cow<'a, str>> {
    cli_region
        .map(std::borrow::Cow::Borrowed)
        .or_else(|| {
            env.var_os("AWS_REGION")
                .map(std::ffi::OsStr::to_string_lossy)
        })
        .or_else(|| {
            env.var_os("AWS_DEFAULT_REGION")
                .map(std::ffi::OsStr::to_string_lossy)
        })
        .or_else(|| {
            shared_config::profile_property(
                files,
                aws_profile::select_or_default(env, cli_profile),
                "region",
            )
            .map(std::borrow::Cow::Borrowed)
        })
}

/// Whether a setting names the region, which decides the client botocore
/// builds: one for no region at all otherwise. An explicit empty `--region`
/// names one, which [`resolve_region`] rejects.
pub fn is_configured(
    env: &impl EnvMap,
    files: &ParsedFiles,
    cli_region: Option<&str>,
    cli_profile: Option<&str>,
) -> bool {
    configured_region(env, files, cli_region, cli_profile).map_or(true, |value| value.is_some())
}

/// botocore's `validate_region_name`, which its session raises
/// InvalidRegionError for when it creates any client: `re.match` of
/// `^(?![0-9]+$)(?!-)[a-zA-Z0-9-]{,63}(?<!-)$`, whose `$` also matches
/// before one final newline.
pub fn is_valid_name(region: &str) -> bool {
    let label = region.strip_suffix('\n').unwrap_or(region);
    label.len() <= 63
        && !label.starts_with('-')
        && !label.ends_with('-')
        && label
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'-')
        && (label.is_empty() || !label.bytes().all(|c| c.is_ascii_digit()))
}
