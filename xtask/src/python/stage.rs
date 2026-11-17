//! The prefix, driver command, and completion marker every Python stage shares.

use crate::TaskError;
use crate::deps::{self, TARGET, Toolchain};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// The triple every driver receives as `--target-triple`. The drivers
/// branch on it (the macOS deployment target, the musl checks), so it
/// lives beside `driver` in a file every Python stage keys on rather than in
/// the unkeyed `deps/mod.rs`. On Linux it is `TARGET`, which the prefix path
/// already carries.
const DRIVER_TARGET: &str = if cfg!(target_os = "macos") {
    if cfg!(target_arch = "aarch64") {
        "aarch64-macos"
    } else {
        "x86_64-macos"
    }
} else if cfg!(windows) {
    "x86_64-windows-msvc"
} else {
    TARGET
};

/// The content-addressed prefix of a Python stage. Its inventory in
/// `deps::inputs` names the code and drivers that build it, so the key adds
/// only the toolchain digest and the stage's own `extra` inputs.
pub(super) fn stage_prefix(
    root: &Path,
    label: &str,
    tools: &Toolchain,
    extra: &[&[u8]],
) -> Result<PathBuf, TaskError> {
    let mut inputs: Vec<&[u8]> = vec![tools.digest.as_bytes()];
    inputs.extend_from_slice(extra);
    let digest = deps::digest(root, label, &inputs)?;
    Ok(deps::store(root)
        .join("deps")
        .join(TARGET)
        .join(format!("{label}-{digest}")))
}

/// The scratch directory of the Python stage `label`, under the checkout's
/// `target/deps/<TARGET>/work` rather than its prefix.
///
/// Each stage keeps one stable directory, so a new key starts from the
/// previous key's tree. A stage whose driver cannot tell another key's
/// scratch from its own claims it with `claim_work`.
pub(super) fn stage_work(root: &Path, label: &str) -> PathBuf {
    deps::work_dir(root, TARGET, label)
}

/// The scratch directory of the Python stage `label` in PGO mode `pgo`. The
/// two modes keep apart, so alternating builds neither replace each other's
/// scratch nor wait on it.
pub(super) fn pgo_work(root: &Path, label: &str, pgo: bool) -> PathBuf {
    stage_work(root, label).join(if pgo { "pgo" } else { "no-pgo" })
}

pub(super) fn driver(root: &Path, name: &str, tools: &Toolchain) -> Command {
    // The isolated driver must retain the caller's network settings for pip.
    // Each script applies tool_environ() to compiler and interpreter children,
    // and adds network_environ() only to its hash-pinned package downloads.
    let mut command = Command::new(if cfg!(windows) { "python" } else { "python3" });
    command
        .current_dir(root)
        .args(["-E", "-s", "-B"])
        .arg(root.join("deps/scripts").join(name))
        .arg("--target-triple")
        .arg(DRIVER_TARGET)
        .arg("--cc")
        .arg(&tools.cc)
        .arg("--ar")
        .arg(&tools.ar)
        .arg("--ranlib")
        .arg(&tools.ranlib);
    if let Some(sdk) = &tools.sdk {
        command.arg("--sdk-path").arg(sdk);
    }
    if let Some((_, file)) = &tools.msvc {
        command.arg("--msvc-environ").arg(file);
    }
    command
}

pub(super) fn complete(prefix: &Path, outputs: &[&str]) -> bool {
    prefix.join(".complete").is_file() && outputs.iter().all(|output| prefix.join(output).is_file())
}

pub(super) fn finish(prefix: &Path, outputs: &[&str]) -> Result<(), TaskError> {
    for output in outputs {
        if !prefix.join(output).is_file() {
            return Err(TaskError::Message(format!(
                "dependency build omitted {}",
                prefix.join(output).display()
            )));
        }
    }
    fs::write(prefix.join(".complete"), "ok\n")?;
    Ok(())
}
