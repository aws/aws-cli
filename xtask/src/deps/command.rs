//! The commands every dependency build runs its tools through: a sanitized
//! environment, the Ninja on PATH, and the executable wrappers it writes.
//!
//! Each stage that builds through these keys on this file (see
//! `inputs::stage_files`). The orchestration in `deps/mod.rs` keys no stage,
//! so the code here stays apart from it.

use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

use super::{Result, error, files};

/// The allowlist in `deps/scripts/tool_environ.txt`: the variables a tool
/// may inherit from the caller.
pub fn tool_allowlist(root: &Path) -> Result<String> {
    Ok(fs::read_to_string(
        root.join("deps/scripts/tool_environ.txt"),
    )?)
}

pub fn tool_command(root: &Path, program: impl AsRef<std::ffi::OsStr>) -> Result<Command> {
    let mut command = Command::new(program);
    let allowlist = tool_allowlist(root)?;
    let parent: BTreeMap<_, _> = std::env::vars_os().collect();
    let sanitized = files::tool_environment(parent.clone(), &allowlist);
    for name in parent.keys() {
        if name != "HOME" && !sanitized.contains_key(name) {
            command.env_remove(name);
        }
    }
    command.env("LC_ALL", "C");
    Ok(command)
}

pub(super) fn ninja_program() -> Result<PathBuf> {
    let search = std::env::var_os("PATH").ok_or_else(|| error("PATH is unset"))?;
    files::find_executable(&search, &["ninja-build", "ninja", "samu"])?
        .ok_or_else(|| error("no executable Ninja builder found on PATH"))
}

pub fn write_executable(path: &Path, content: &str) -> Result<()> {
    #[cfg(unix)]
    use std::os::unix::fs::PermissionsExt;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut file = File::create(path)?;
    file.write_all(content.as_bytes())?;
    #[cfg(unix)]
    fs::set_permissions(path, fs::Permissions::from_mode(0o755))?;
    Ok(())
}

pub fn shell_quote(path: &Path) -> Result<String> {
    let path = path
        .to_str()
        .ok_or_else(|| error("tool paths must be UTF-8"))?;
    Ok(format!("'{}'", path.replace('\'', "'\\''")))
}
