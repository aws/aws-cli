//! Publish the CLI's resolved shared-file paths for Windows CRT readers.
use cli_core::EnvMap;
use std::io;

#[cfg(any(windows, test))]
use std::{ffi::OsStr, path::Path};

#[cfg(any(windows, test))]
mod publication;

#[cfg(windows)]
static PUBLICATION: publication::Publication = publication::Publication::new();

/// The two variables aws-c-sdkutils consults before it resolves a shared file
/// itself. `s_get_raw_file_path` in aws_profile.c reads them ahead of its
/// `~/.aws/...` default, so naming them redirects every consumer that goes
/// through `aws_get_config_file_path` / `aws_get_credentials_file_path`: the
/// profile and STS web-identity providers that
/// `aws_credentials_provider_new_chain_default` builds, and the
/// `credential_process` provider the profile provider constructs when the
/// selected profile declares one.
///
/// It does not reach the SSO and login token caches: `aws_construct_sso_token_path`
/// and `aws_login_token_construct_token_path` call `aws_get_home_directory`
/// directly, and this CRT exposes no variable that overrides it, so a cached
/// token is still looked for under the home directory the CRT picks. That is
/// moot for the default chain in this pinned version, which builds no SSO
/// provider at all, but it is the one path this export cannot repair.
pub const CONFIG_FILE_VARIABLE: &str = "AWS_CONFIG_FILE";
/// The credentials counterpart to [`CONFIG_FILE_VARIABLE`].
pub const CREDENTIALS_FILE_VARIABLE: &str = "AWS_SHARED_CREDENTIALS_FILE";

/// Publishes Windows shared-file paths once before credential providers start.
///
/// Failed attempts remain retryable; successful publication is reused.
///
/// # Errors
/// Returns an error if a path contains a NUL or the C environment rejects it.
///
/// # Panics
/// Panics if an earlier Windows publisher panicked while holding its state lock.
///
/// # Safety
/// Call before any CRT reader or worker thread starts. The environment must be
/// the same snapshot used to resolve the invocation's shared configuration.
pub unsafe fn prepare_process(environment: &impl EnvMap) -> io::Result<()> {
    #[cfg(windows)]
    {
        PUBLICATION.run(|| {
            for (variable, name) in [
                (CONFIG_FILE_VARIABLE, "config"),
                (CREDENTIALS_FILE_VARIABLE, "credentials"),
            ] {
                let resolved = cli_core::shared_config::locate(environment, variable, name);
                if let Some(path) = export_value(environment.var_os(variable), resolved.as_deref())
                {
                    // SAFETY: the caller guarantees publication precedes every reader.
                    unsafe { set_variable(variable, path)? };
                }
            }
            Ok(())
        })
    }
    #[cfg(not(windows))]
    {
        let _ = environment;
        Ok(())
    }
}

#[cfg(any(windows, test))]
fn export_value<'a>(existing: Option<&OsStr>, resolved: Option<&'a Path>) -> Option<&'a Path> {
    if let Some(existing) = existing
        && cli_core::shared_config::home_relative_suffix(existing).is_none()
    {
        return None;
    }
    resolved
}

#[cfg(windows)]
fn encode_value(value: &OsStr) -> io::Result<Vec<u16>> {
    use std::os::windows::ffi::OsStrExt;
    let mut value: Vec<u16> = value.encode_wide().collect();
    if value.contains(&0) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "shared-file path contains NUL",
        ));
    }
    value.push(0);
    Ok(value)
}

#[cfg(windows)]
unsafe fn set_variable(name: &str, value: &Path) -> io::Result<()> {
    unsafe extern "C" {
        fn _wputenv_s(name: *const u16, value: *const u16) -> std::ffi::c_int;
    }
    let name: Vec<u16> = name.encode_utf16().chain([0]).collect();
    let value = encode_value(value.as_os_str())?;
    // SAFETY: both strings are terminated and remain live for this copying call;
    // the caller guarantees no CRT readers or workers have started.
    let status = unsafe { _wputenv_s(name.as_ptr(), value.as_ptr()) };
    publication_result(status)
}

#[cfg(any(windows, test))]
fn publication_result(status: i32) -> io::Result<()> {
    if status == 0 {
        Ok(())
    } else {
        // _wputenv_s returns errno_t, not a Win32 GetLastError code.
        Err(io::Error::other(format!(
            "shared-file publication failed (C runtime error {status})"
        )))
    }
}

#[cfg(test)]
mod tests;
