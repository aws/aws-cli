//! AWS shared-profile selection: which profile an invocation reads its
//! settings from, and whether a selected profile exists. Every native
//! consumer of the shared files selects through [`select`], so the order the
//! AWS CLI applies is defined once.
#![forbid(unsafe_code)]
use crate::EnvMap;
use awscli_config::ParsedFiles;
use std::ffi::OsStr;
/// The profile the AWS CLI selects before it reads any setting: a nonempty
/// `--profile`, else `AWS_PROFILE`, else `AWS_DEFAULT_PROFILE`, in the
/// order of botocore's `profile` chain. None when nothing selects one, in
/// which case consumers read `default` without requiring it to exist. An
/// empty `--profile` selects nothing because `_handle_top_level_args`
/// applies the flag only when it is truthy; an empty environment value
/// selects the profile named "", which botocore reports as missing like any
/// other absent one.
///
/// The name is an `OsStr` because the environment's need not be Unicode. A
/// present variable selects even when its value is not Unicode; such a name
/// shadows the variables after it and names no profile.
pub fn select<'a>(env: &'a impl EnvMap, cli_profile: Option<&'a str>) -> Option<&'a OsStr> {
    cli_profile
        .filter(|profile| !profile.is_empty())
        .map(OsStr::new)
        .or_else(|| env.var_os("AWS_PROFILE"))
        .or_else(|| env.var_os("AWS_DEFAULT_PROFILE"))
}
/// The section a setting is read from: the [`select`]ed profile, else
/// `default`.
pub fn select_or_default<'a>(env: &'a impl EnvMap, cli_profile: Option<&'a str>) -> &'a OsStr {
    select(env, cli_profile).unwrap_or(OsStr::new("default"))
}
/// Whether `--profile` selected the profile. botocore drops the environment
/// credentials provider from its chain only in that case, never for a
/// profile the environment named (`create_credential_resolver`).
pub fn is_explicit(cli_profile: Option<&str>) -> bool {
    cli_profile.is_some_and(|profile| !profile.is_empty())
}
/// Whether the named profile has a section in the shared config file or
/// the shared credentials file, which is what botocore's scoped config
/// requires of a selected profile, `default` included. A shared file that
/// failed to parse defines no profiles. The files are UTF-8, so a name that
/// is not Unicode has none.
pub fn explicit_profile_exists(files: &ParsedFiles, profile: impl AsRef<OsStr>) -> bool {
    let Some(profile) = profile.as_ref().to_str() else {
        return false;
    };
    files
        .profiles
        .as_ref()
        .is_some_and(|profiles| profiles.contains_key(profile))
}
