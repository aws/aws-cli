//! Literal shared-file lookup after environment-based location selection.
#![forbid(unsafe_code)]
use crate::{EnvMap, Fs};
use awscli_config::{ParsedFiles, Paths, ReadError, Status};
use std::borrow::Cow;
use std::ffi::{OsStr, OsString};
use std::path::PathBuf;
/// Loads configuration, credentials, and runtime aliases from the injected inputs.
///
/// # Errors
/// Propagates cancellation and filesystem resource exhaustion.
pub fn load(fs: &impl Fs, env: &impl EnvMap) -> Result<ParsedFiles, ReadError> {
    let config = locate(env, "AWS_CONFIG_FILE", "config");
    let credentials = locate(env, "AWS_SHARED_CREDENTIALS_FILE", "credentials");
    let aliases = home_directory(env).map(|home| home.join(".aws/cli/alias"));
    ParsedFiles::load(
        fs,
        Paths {
            config: config.as_deref(),
            credentials: credentials.as_deref(),
            aliases: aliases.as_deref(),
        },
    )
}
/// The selected `profile`'s top-level `key`. A profile name need not be
/// Unicode; one that is not names no profile, as the shared files are UTF-8.
pub fn profile_property<'a>(
    files: &'a ParsedFiles,
    profile: impl AsRef<OsStr>,
    key: &str,
) -> Option<&'a str> {
    files
        .profiles
        .as_ref()?
        .get(profile.as_ref().to_str()?)?
        .get(key)?
        .value
        .as_str()
}
pub fn profile_nested_property<'a>(
    files: &'a ParsedFiles,
    profile: impl AsRef<OsStr>,
    key: &str,
    nested_key: &str,
) -> Option<&'a str> {
    files
        .profiles
        .as_ref()?
        .get(profile.as_ref().to_str()?)?
        .get(key)?
        .value
        .as_nested()?
        .get(nested_key)
        .map(String::as_str)
}
/// Expands only a leading `~` segment; an empty override omits the file.
pub fn locate(env: &impl EnvMap, variable: &str, name: &str) -> Option<PathBuf> {
    match env.var_os(variable) {
        Some(value) => expand_home(env, value),
        None => home_directory(env).map(|home| home.join(".aws").join(name)),
    }
}

fn expand_home(env: &impl EnvMap, value: &OsStr) -> Option<PathBuf> {
    if value.is_empty() {
        return None;
    }
    if let Some(suffix) = home_relative_suffix(value) {
        return home_directory(env).map(|home| join_home(home, &suffix));
    }
    Some(PathBuf::from(value))
}

fn join_home(home: PathBuf, suffix: &OsStr) -> PathBuf {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::{OsStrExt, OsStringExt};
        let mut joined = home.into_os_string().into_vec();
        join_units(&mut joined, suffix.as_bytes(), |unit| unit == b'/', b'/');
        PathBuf::from(OsString::from_vec(joined))
    }
    #[cfg(windows)]
    {
        use std::os::windows::ffi::{OsStrExt, OsStringExt};
        let mut joined = home.into_os_string().encode_wide().collect::<Vec<_>>();
        let suffix = suffix.encode_wide().collect::<Vec<_>>();
        let separator = |unit| unit == u16::from(b'/') || unit == u16::from(b'\\');
        join_units(&mut joined, &suffix, separator, u16::from(b'\\'));
        PathBuf::from(OsString::from_wide(&joined))
    }
}

fn join_units<T: Copy>(
    joined: &mut Vec<T>,
    suffix: &[T],
    is_separator: impl Fn(T) -> bool,
    separator: T,
) {
    let Some(&first) = suffix.first() else {
        return;
    };
    let ends = joined.last().is_some_and(|&unit| is_separator(unit));
    match (ends, is_separator(first)) {
        (true, true) => joined.extend_from_slice(&suffix[1..]),
        (false, false) => {
            joined.push(separator);
            joined.extend_from_slice(suffix);
        }
        _ => joined.extend_from_slice(suffix),
    }
}

const BOTO_CONFIG_DEFAULTS: [&str; 2] = ["/etc/boto.cfg", "~/.boto"];

/// Whether a boto config file botocore's `BotoProvider` reads would supply
/// credentials, a `[Credentials]` section with `aws_access_key_id`, or fails
/// to parse, which botocore raises. It reads `BOTO_CONFIG` when present, else
/// each default file in turn. A missing file supplies nothing, and neither
/// does an unreadable one, which configparser skips.
///
/// # Errors
/// Propagates cancellation and filesystem resource exhaustion.
pub fn boto_config_supplies_credentials(
    fs: &impl Fs,
    env: &impl EnvMap,
) -> Result<bool, ReadError> {
    if let Some(path) = env.var_os("BOTO_CONFIG") {
        return boto_file_supplies_credentials(fs, env, path);
    }
    for path in BOTO_CONFIG_DEFAULTS {
        if boto_file_supplies_credentials(fs, env, OsStr::new(path))? {
            return Ok(true);
        }
    }
    Ok(false)
}

fn boto_file_supplies_credentials(
    fs: &impl Fs,
    env: &impl EnvMap,
    path: &OsStr,
) -> Result<bool, ReadError> {
    let Some(path) = expand_home(env, path) else {
        return Ok(false);
    };
    let parsed = ParsedFiles::load(
        fs,
        Paths {
            credentials: Some(&path),
            ..Paths::default()
        },
    )?;
    Ok(match parsed.credentials.status {
        Status::Loaded => parsed
            .credentials
            .sections
            .get("Credentials")
            .is_some_and(|section| section.contains_key("aws_access_key_id")),
        Status::ParseFailure(_) | Status::ResourceLimit => true,
        Status::Omitted | Status::Missing | Status::Directory | Status::Unreadable(_) => false,
    })
}

/// The path following a leading `~` home-directory reference, or none when
/// `value` is not home-relative. A bare `~` yields an empty suffix, which
/// `join_home` leaves off, so it resolves to the home directory itself.
///
/// The separator after the `~` is `/` on Unix and `/` or `\` on Windows. That
/// matches `posixpath.expanduser` and `ntpath.expanduser` respectively, and it
/// matches aws-c-sdkutils, which rewrites every directory separator to the
/// platform separator before it looks for a leading `~` segment. So
/// `AWS_CONFIG_FILE=~\alternate`, the natural Windows spelling, expands on
/// Windows and stays a literal relative path anywhere else.
pub fn home_relative_suffix(value: &OsStr) -> Option<Cow<'_, OsStr>> {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        match value.as_bytes() {
            [b'~'] => Some(Cow::Borrowed(OsStr::new(""))),
            [b'~', b'/', suffix @ ..] => Some(Cow::Borrowed(OsStr::from_bytes(suffix))),
            _ => None,
        }
    }
    #[cfg(windows)]
    {
        use std::os::windows::ffi::{OsStrExt, OsStringExt};
        let tilde = u16::from(b'~');
        let is_separator = |unit: u16| unit == u16::from(b'/') || unit == u16::from(b'\\');
        let units = value.encode_wide().collect::<Vec<_>>();
        match units.as_slice() {
            [first] if *first == tilde => Some(Cow::Borrowed(OsStr::new(""))),
            [first, separator, suffix @ ..] if *first == tilde && is_separator(*separator) => {
                Some(Cow::Owned(OsString::from_wide(suffix)))
            }
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum HomeSource {
    Variable(&'static str),
    Pair(&'static str, &'static str),
}

pub(crate) const POSIX_HOME_SOURCES: &[HomeSource] = &[HomeSource::Variable("HOME")];

pub(crate) const WINDOWS_HOME_SOURCES: &[HomeSource] = &[
    HomeSource::Variable("USERPROFILE"),
    HomeSource::Pair("HOMEDRIVE", "HOMEPATH"),
    HomeSource::Variable("HOME"),
];

const HOME_SOURCES: &[HomeSource] = if cfg!(windows) {
    WINDOWS_HOME_SOURCES
} else {
    POSIX_HOME_SOURCES
};

pub(crate) type HomeFallback = fn() -> Option<PathBuf>;

#[cfg(unix)]
const HOME_FALLBACK: Option<HomeFallback> = Some(crate::passwd::home_directory);
#[cfg(not(unix))]
const HOME_FALLBACK: Option<HomeFallback> = None;

/// The home directory the environment names, or the fallback's when it sets
/// none of the source variables. An empty variable counts as absent, since it
/// cannot name a directory, but it is still set, so an empty `HOME` yields
/// none rather than the passwd entry: neither reference consults the passwd
/// database while `HOME` is set.
pub fn home_directory(env: &impl EnvMap) -> Option<PathBuf> {
    home_directory_from(env, HOME_SOURCES, HOME_FALLBACK)
}

pub(crate) fn home_directory_from(
    env: &impl EnvMap,
    sources: &[HomeSource],
    fallback_when_unset: Option<HomeFallback>,
) -> Option<PathBuf> {
    if let Some(resolve) = fallback_when_unset
        && !any_source_set(env, sources)
    {
        return resolve().filter(|home| !home.as_os_str().is_empty());
    }
    let non_empty = |name| env.var_os(name).filter(|value| !value.is_empty());
    sources.iter().find_map(|source| match *source {
        HomeSource::Variable(name) => non_empty(name).map(PathBuf::from),
        HomeSource::Pair(first, second) => {
            let mut home = non_empty(first)?.to_os_string();
            home.push(non_empty(second)?);
            Some(home.into())
        }
    })
}

fn any_source_set(env: &impl EnvMap, sources: &[HomeSource]) -> bool {
    sources.iter().any(|source| match *source {
        HomeSource::Variable(name) => env.var_os(name).is_some(),
        HomeSource::Pair(first, second) => {
            env.var_os(first).is_some() || env.var_os(second).is_some()
        }
    })
}

pub fn profile_property_is_block(
    files: &ParsedFiles,
    profile: impl AsRef<OsStr>,
    key: &str,
) -> bool {
    files
        .profiles
        .as_ref()
        .zip(profile.as_ref().to_str())
        .and_then(|(profiles, profile)| profiles.get(profile))
        .and_then(|entries| entries.get(key))
        .is_some_and(|entry| entry.value.as_nested().is_some())
}

#[cfg(test)]
mod tests;
