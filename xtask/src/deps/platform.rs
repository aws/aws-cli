//! Pure host and tool policy; discovery and execution still require the native host.

use super::{Result, error};

pub(super) fn supported_host(os: &str, arch: &str, linux_only: bool) -> bool {
    match (os, arch) {
        ("linux", "x86_64" | "aarch64") => true,
        ("macos", "x86_64" | "aarch64") | ("windows", "x86_64") => !linux_only,
        _ => false,
    }
}

pub(super) fn target(os: &str, arch: &str, system: bool) -> Result<String> {
    if !supported_host(os, arch, false) || (system && os != "linux") {
        return Err(error("unsupported native host/build mode"));
    }
    let suffix = match (os, system) {
        ("linux", false) => "unknown-linux-musl",
        ("linux", true) => "unknown-linux-gnu",
        ("macos", _) => "apple-darwin",
        ("windows", _) => "pc-windows-msvc",
        _ => return Err(error("unsupported native ABI")),
    };
    Ok(format!("{arch}-{suffix}"))
}

pub(super) fn openssl_target(triple: &str) -> Option<&'static str> {
    let triple = triple.replace("-unknown-", "-").replace("-pc-", "-");
    match triple.as_str() {
        "x86_64-linux-musl" => Some("linux-x86_64"),
        "aarch64-linux-musl" => Some("linux-aarch64"),
        "x86_64-windows-msvc" => Some("VC-WIN64A"),
        target if target.starts_with("aarch64-macos") || target == "aarch64-apple-darwin" => {
            Some("darwin64-arm64-cc")
        }
        target if target.starts_with("x86_64-macos") || target == "x86_64-apple-darwin" => {
            Some("darwin64-x86_64-cc")
        }
        _ => None,
    }
}

pub(super) fn uses_nmake(configure_target: &str) -> bool {
    configure_target.starts_with("VC-")
}

pub(super) fn includes_library(os: &str, library: &str) -> bool {
    os != "windows" || library != "s2n"
}

pub(super) fn archive_name(os: &str, library: &str) -> String {
    if os == "windows" {
        format!("{library}.lib")
    } else {
        format!("lib{library}.a")
    }
}

#[cfg(test)]
mod tests;
