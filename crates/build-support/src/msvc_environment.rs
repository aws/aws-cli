use std::{io, process::Command};

#[cfg(any(windows, test))]
use std::{
    collections::BTreeMap,
    fs::File,
    io::{Read, Write},
    path::Path,
};

#[cfg(any(windows, test))]
const VARIABLE: &str = "AWS_NATIVE_MSVC_ENV_FILE";
#[cfg(any(windows, test))]
const CAPTURE_BYTES_MAX: usize = 1024 * 1024;
#[cfg(any(windows, test))]
const CAPTURE_VARIABLES_MAX: usize = 512;

/// Applies the explicitly captured MSVC environment to a build-script child.
///
/// Windows consumers require `AWS_NATIVE_MSVC_ENV_FILE`, emitted by the native
/// dependency driver. Call this after sanitizing inherited tool variables and
/// before setting stage-specific compiler options. `HOME` remains inherited.
/// Cargo receives both environment and file dependencies. Other hosts do nothing.
///
/// # Errors
/// On Windows, returns missing-path, file-read, oversized-capture, invalid-map,
/// invalid-variable, or Cargo-output errors before the child can be launched.
///
/// # Examples
/// ```
/// let mut compiler = std::process::Command::new("clang");
/// # if cfg!(windows) && std::env::var_os("AWS_NATIVE_MSVC_ENV_FILE").is_some() {
/// build_support::apply_captured_msvc_environment(
///     &mut compiler, &mut std::io::stdout().lock(),
/// )?;
/// # }
/// # Ok::<(), std::io::Error>(())
/// ```
pub fn apply_captured_msvc_environment(
    command: &mut Command,
    cargo_output: &mut impl io::Write,
) -> io::Result<()> {
    #[cfg(windows)]
    {
        let path = std::env::var_os(VARIABLE).ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::NotFound,
                "AWS_NATIVE_MSVC_ENV_FILE is missing; use the native dependency driver",
            )
        })?;
        apply_file(command, cargo_output, Path::new(&path))
    }
    #[cfg(not(windows))]
    {
        let _ = (command, cargo_output);
        Ok(())
    }
}

#[cfg(any(windows, test))]
fn apply_file(command: &mut Command, cargo_output: &mut impl Write, path: &Path) -> io::Result<()> {
    writeln!(cargo_output, "cargo:rerun-if-env-changed={VARIABLE}")?;
    let tracked_path = path
        .to_str()
        .filter(|path| !path.contains(['\n', '\r']))
        .ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::InvalidInput,
                "MSVC capture path cannot be tracked by Cargo",
            )
        })?;
    writeln!(cargo_output, "cargo:rerun-if-changed={tracked_path}")?;
    let variables = read_variables(File::open(path)?)?;
    command.envs(variables);
    Ok(())
}

#[cfg(any(windows, test))]
fn read_variables(input: impl Read) -> io::Result<BTreeMap<String, String>> {
    let mut bytes = Vec::new();
    input
        .take(CAPTURE_BYTES_MAX as u64 + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() > CAPTURE_BYTES_MAX {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "MSVC capture exceeds 1 MiB",
        ));
    }
    let variables: BTreeMap<String, String> = serde_json::from_slice(&bytes)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    if variables.len() > CAPTURE_VARIABLES_MAX {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "MSVC capture exceeds 512 variables",
        ));
    }
    let mut normalized = BTreeMap::new();
    for (name, value) in variables {
        if name.is_empty() || name.contains(['=', '\0']) || value.contains('\0') {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "invalid MSVC environment variable",
            ));
        }
        let name = name.to_ascii_uppercase();
        if name == "HOME" {
            continue;
        }
        if normalized.insert(name, value).is_some() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "duplicate MSVC environment variable",
            ));
        }
    }
    Ok(normalized)
}

#[cfg(test)]
mod tests;
