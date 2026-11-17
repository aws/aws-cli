//! Native Visual Studio discovery with an isolated, explicitly captured environment.

use std::collections::BTreeMap;
use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use sha2::{Digest, Sha256};

use super::{Result, error, files, tool_command};

mod capture;

const MARKER: &str = "__msvc_env__";
const VCVARS_VARIABLE: &str = "AWSCLI_NATIVE_VCVARS";
const DUMP_BYTES_MAX: usize = 1024 * 1024;
const DUMP_LINES_MAX: usize = 512;
const DRIVER_CONTENTS: &str = concat!(
    "@echo off\r\n",
    "chcp 65001 >nul\r\n",
    "call \"%AWSCLI_NATIVE_VCVARS%\" >nul || exit /b 1\r\n",
    "set AWSCLI_NATIVE_VCVARS=\r\n",
    "echo __msvc_env__\r\n",
    "set\r\n",
);

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Environment {
    variables: BTreeMap<String, String>,
    tools_version: String,
    sdk_version: String,
}

impl Environment {
    fn value(&self, name: &str) -> Option<&str> {
        self.variables
            .iter()
            .find_map(|(key, value)| key.eq_ignore_ascii_case(name).then_some(value.as_str()))
    }

    pub fn apply(&self, command: &mut Command) {
        for name in ["INCLUDE", "LIB", "LIBPATH", "CL", "_CL_"] {
            command.env_remove(name);
        }
        command.envs(
            self.variables
                .iter()
                .filter(|(name, _)| !name.eq_ignore_ascii_case("HOME")),
        );
    }

    pub fn find_tool(&self, name: &str) -> Result<PathBuf> {
        self.find_tools(&[name])
    }

    pub fn find_tools(&self, names: &[&str]) -> Result<PathBuf> {
        let path = self.value("PATH").unwrap_or("");
        files::find_executable(OsStr::new(path), names)?.ok_or_else(|| {
            error(format!(
                "none of {names:?} is present in the captured MSVC environment"
            ))
        })
    }

    pub fn identity(&self) -> Result<Vec<u8>> {
        let values = ["INCLUDE", "LIB", "LIBPATH"].map(|name| self.value(name).unwrap_or(""));
        serde_json::to_vec(&(&self.tools_version, &self.sdk_version, values))
            .map_err(|failure| error(failure.to_string()))
    }

    /// Save the environment for the drivers and build scripts that read it,
    /// in a file in `directory` named by its contents, and return the file.
    ///
    /// A file is never rewritten, and is written under a temporary name
    /// first, so concurrent commands never read one partly written.
    pub fn save(&self, directory: &Path) -> Result<PathBuf> {
        // HOME stays inherited, even when the captured developer prompt reports it.
        let variables: BTreeMap<_, _> = self
            .variables
            .iter()
            .filter(|(name, _)| !name.eq_ignore_ascii_case("HOME"))
            .collect();
        let contents =
            serde_json::to_vec(&variables).map_err(|failure| error(failure.to_string()))?;
        let digest = format!("{:x}", Sha256::digest(&contents));
        let path = directory.join(format!("{digest}.json"));
        if !path.is_file() {
            fs::create_dir_all(directory)?;
            let temporary = directory.join(format!("{digest}.{}.part", std::process::id()));
            fs::write(&temporary, &contents)?;
            // A concurrent command may have saved the same file first.
            if let Err(failure) = fs::rename(&temporary, &path) {
                let _ = fs::remove_file(&temporary);
                if !path.is_file() {
                    return Err(failure.into());
                }
            }
        }
        Ok(path)
    }
}

pub fn discover(root: &Path) -> Result<Environment> {
    if !cfg!(windows) {
        return Err(error(
            "Visual Studio discovery requires a native Windows host",
        ));
    }
    let installation = installation(root)?;
    let vcvars = installation.join("VC/Auxiliary/Build/vcvars64.bat");
    validate_vcvars(&vcvars)?;
    let scratch = root.join("target/msvc-discovery");
    let _lock = super::lock_stage(&scratch)?;
    fs::create_dir_all(&scratch)?;
    let driver = scratch.join("dump-msvc-env.bat");
    fs::write(&driver, DRIVER_CONTENTS)?;
    let comspec = std::env::var_os("ComSpec").unwrap_or_else(|| "cmd.exe".into());
    let mut command = tool_command(root, comspec)?;
    command
        .args(["/d", "/c"])
        .arg(driver)
        .env(VCVARS_VARIABLE, vcvars);
    let dump = capture::output(&mut command, DUMP_BYTES_MAX)?;
    let variables =
        parse_dump(&dump)?.ok_or_else(|| error("vcvars64.bat reported no environment"))?;
    let version = |name| {
        variables
            .iter()
            .find_map(|(key, value)| key.eq_ignore_ascii_case(name).then(|| value.clone()))
            .ok_or_else(|| error(format!("vcvars64.bat did not export {name}")))
    };
    Ok(Environment {
        tools_version: version("VCToolsVersion")?,
        sdk_version: version("WindowsSDKVersion")?,
        variables,
    })
}

fn validate_vcvars(path: &Path) -> Result<()> {
    if !path.is_file() {
        return Err(error(format!(
            "vcvars64.bat was not found at {}",
            path.display()
        )));
    }
    if path
        .as_os_str()
        .as_encoded_bytes()
        .iter()
        .any(|byte| b"%^".contains(byte))
    {
        return Err(error(
            "the Visual Studio path contains % or ^, which cmd.exe consumes; \
             use an installation or directory junction whose path contains neither",
        ));
    }
    Ok(())
}

fn installation(root: &Path) -> Result<PathBuf> {
    let program_files = std::env::var_os("ProgramFiles(x86)")
        .map_or_else(|| PathBuf::from("C:/Program Files (x86)"), PathBuf::from);
    let vswhere = program_files.join("Microsoft Visual Studio/Installer/vswhere.exe");
    let mut command = tool_command(root, vswhere)?;
    command.args([
        "-latest",
        "-products",
        "*",
        "-requires",
        "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-property",
        "installationPath",
        "-utf8",
    ]);
    let output = capture::output(&mut command, DUMP_BYTES_MAX)?;
    let path = output.trim();
    if path.is_empty() {
        return Err(error(
            "vswhere found no installation with the x64 C++ build tools",
        ));
    }
    Ok(PathBuf::from(path))
}

pub fn native_perl(root: &Path, environment: &Environment) -> Result<PathBuf> {
    let mut candidates = Vec::new();
    if let Some(path) = std::env::var_os("AWSCLI_NATIVE_PERL") {
        candidates.push(PathBuf::from(path));
    }
    candidates.push(PathBuf::from("C:/Strawberry/perl/bin/perl.exe"));
    if let Ok(path) = environment.find_tool("perl") {
        candidates.push(path);
    }
    for candidate in candidates {
        if !candidate.is_file() {
            continue;
        }
        let mut command = tool_command(root, &candidate)?;
        environment.apply(&mut command);
        command.args(["-e", "print $^O"]);
        if capture::probe(&mut command, 64).is_some_and(|output| output.trim() == "MSWin32") {
            return Ok(candidate);
        }
    }
    Err(error(
        "OpenSSL needs native Windows Perl; install Strawberry Perl or set \
         AWSCLI_NATIVE_PERL to its executable (MSYS and Cygwin Perl are unsupported)",
    ))
}

fn parse_dump(dump: &str) -> Result<Option<BTreeMap<String, String>>> {
    if dump.len() > DUMP_BYTES_MAX {
        return Err(error("MSVC environment dump exceeds the byte limit"));
    }
    let mut found_marker = false;
    let mut variables = BTreeMap::new();
    for (index, raw) in dump.split('\n').enumerate() {
        if index + 1 >= DUMP_LINES_MAX {
            return Err(error("MSVC environment dump exceeds the line limit"));
        }
        let line = raw.trim_end_matches('\r');
        if !found_marker {
            found_marker = line == MARKER;
        } else if let Some((name, value)) = line.split_once('=')
            && !name.is_empty()
        {
            variables.insert(name.into(), value.into());
        }
    }
    Ok(found_marker.then_some(variables))
}

#[cfg(test)]
mod tests;
