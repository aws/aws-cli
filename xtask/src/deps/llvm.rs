//! Unpack and check the pinned official LLVM release.

use std::path::{Path, PathBuf};

use super::{Pins, Result, error, source, tool_command};
use crate::process;

const TOOLS: &[&str] = &[
    "clang",
    "clang++",
    "ld.lld",
    "llvm-ar",
    "llvm-ranlib",
    "llvm-nm",
    "llvm-objdump",
    "llvm-profdata",
];
/// The parts of an official release archive the managed toolchain uses: the
/// `TOOLS` programs, the files their links point to, and clang's resource
/// directory. The release's other programs and libraries take about 10 GB
/// unpacked.
pub(super) const RELEASE_MEMBERS: &[&str] = &[
    "bin/clang",
    "bin/clang++",
    "bin/clang-21",
    "bin/ld.lld",
    "bin/lld",
    "bin/llvm-ar",
    "bin/llvm-ranlib",
    "bin/llvm-nm",
    "bin/llvm-objdump",
    "bin/llvm-profdata",
    "lib/clang/21",
];

/// The members `source` unpacks from the archive `name`; an empty list
/// unpacks every member.
pub(super) fn archive_members(name: &str) -> &'static [&'static str] {
    match name {
        "llvm_binary" | "llvm_binary_aarch64" => RELEASE_MEMBERS,
        _ => &[],
    }
}

/// Unpack the host architecture's pinned LLVM release and return its
/// directory once every one of `TOOLS` runs and reports `llvm_version`.
///
/// There is no fallback: a host the release cannot run on, such as one whose
/// glibc is older than the release links against, fails here with the
/// tool's error.
pub fn release(root: &Path, pins: &Pins) -> Result<PathBuf> {
    let name = if cfg!(target_arch = "aarch64") {
        "llvm_binary_aarch64"
    } else {
        "llvm_binary"
    };
    let prefix = source(root, pins, name)?;
    check(root, &prefix, pins.version("llvm_version")?)?;
    Ok(prefix)
}

fn check(root: &Path, prefix: &Path, version: &str) -> Result<()> {
    for name in TOOLS {
        let output =
            process::output(tool_command(root, prefix.join("bin").join(name))?.arg("--version"))?;
        if !String::from_utf8_lossy(&output.stdout).contains(version) {
            return Err(error(format!("{name} must report exact version {version}")));
        }
    }
    Ok(())
}

pub(super) fn check_runtime_path(prefix: &Path, runtime: &Path) -> Result<()> {
    if !runtime.is_absolute() || !runtime.is_file() {
        return Err(error(format!(
            "LLVM native musl runtime is missing: {}",
            runtime.display()
        )));
    }
    if !runtime.canonicalize()?.starts_with(prefix.canonicalize()?) {
        return Err(error(format!(
            "LLVM native musl runtime escapes the managed toolchain: {}",
            runtime.display()
        )));
    }
    Ok(())
}

#[cfg(test)]
mod tests;
