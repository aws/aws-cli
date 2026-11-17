//! Native compiler, archive and interpreter conventions for package consumers.

use std::path::{Path, PathBuf};
use std::process::Command;

/// Flags for every compilation, including a source built to its own object.
pub(super) fn compile_flags(command: &mut Command) {
    if cfg!(windows) {
        command.args([
            "--driver-mode=gcc",
            "-fms-runtime-lib=static",
            "-DPy_NO_ENABLE_SHARED=1",
            "-gcodeview",
        ]);
    }
}

/// Flags only the link of a consumer executable takes.
pub(super) fn link_flags(command: &mut Command) {
    if cfg!(target_os = "linux") {
        command.arg("-static");
    } else if cfg!(windows) {
        command.arg("-fuse-ld=lld");
    }
}

pub(super) fn archives_begin(command: &mut Command) {
    if cfg!(target_os = "linux") {
        command.args(["-Wl,--gc-sections", "-Wl,--start-group"]);
    } else if cfg!(target_os = "macos") {
        command.arg("-Wl,-dead_strip");
    } else if cfg!(windows) {
        command.args(["-Xlinker", "/OPT:REF"]);
    }
}

pub(super) fn archives_end(command: &mut Command) {
    if cfg!(target_os = "linux") {
        command.args(["-Wl,--end-group", "-pthread", "-ldl", "-lm"]);
    } else if cfg!(target_os = "macos") {
        for framework in ["CoreFoundation", "Security", "SystemConfiguration"] {
            command.args(["-framework", framework]);
        }
    } else if cfg!(windows) {
        for library in [
            "advapi32", "bcrypt", "crypt32", "iphlpapi", "ncrypt", "secur32", "ws2_32", "userenv",
            "ole32", "oleaut32", "oldnames", "pathcch", "rpcrt4", "shlwapi", "user32", "version",
        ] {
            command.arg(format!("-l{library}"));
        }
    }
}

pub(super) fn interpreter(prefix: &Path) -> PathBuf {
    prefix.join("bin").join(format!(
        "{}{}",
        crate::python::PYTHON_ABI,
        std::env::consts::EXE_SUFFIX
    ))
}

pub(super) fn archive(name: &str) -> String {
    if cfg!(windows) {
        format!("{name}.lib")
    } else {
        format!("lib{name}.a")
    }
}
