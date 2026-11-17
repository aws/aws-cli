//! Native glibc static CRT for distro builds with shared system OpenSSL.

use super::{Pins, Result, error, guard, source, tool_command};
use crate::process;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

const PROJECTS: &[(&str, &str)] = &[
    ("s2n-tls", "s2n_tls"),
    ("aws-c-common", "aws_c_common"),
    ("aws-checksums", "aws_checksums"),
    ("aws-c-cal", "aws_c_cal"),
    ("aws-c-io", "aws_c_io"),
    ("aws-c-compression", "aws_c_compression"),
    ("aws-c-event-stream", "aws_c_event_stream"),
    ("aws-c-http", "aws_c_http"),
    ("aws-c-mqtt", "aws_c_mqtt"),
    ("aws-c-sdkutils", "aws_c_sdkutils"),
    ("aws-c-auth", "aws_c_auth"),
    ("aws-c-s3", "aws_c_s3"),
];

/// Build, or reuse, the CRT prefix for the native glibc triple. It is a
/// system-mode input, so any architecture `product::system_target` accepts
/// may build it, under the triple rustc spells (`riscv64gc`, where
/// `consts::ARCH` is `riscv64`).
pub fn build(root: &Path, pins: &Pins) -> Result<PathBuf> {
    if !cfg!(target_os = "linux") {
        return Err(error("system CRT requires native Linux/glibc"));
    }
    let target = crate::product::system_target()?;
    let cc = std::env::var_os("CC").unwrap_or_else(|| "clang".into());
    let compiler = process::output(Command::new(&cc).arg("--version"))?;
    let openssl = process::output(Command::new("pkg-config").args(["--modversion", "openssl"]))?;
    let mut digest = Sha256::new();
    for name in [
        "deps/pins.toml",
        "xtask/src/deps/system_crt.rs",
        "xtask/src/deps/crt.rs",
    ] {
        digest.update(fs::read(root.join(name))?);
    }
    digest.update(&compiler.stdout);
    digest.update(&openssl.stdout);
    digest.update(&target);
    let digest = format!("{:x}", digest.finalize());
    let prefix = super::store(root)
        .join("deps")
        .join(&target)
        .join(format!("crt-{digest}"));
    let _lock = super::lock_stage(&prefix)?;
    if prefix.join(".complete").is_file() {
        validate(&prefix)?;
        return Ok(prefix);
    }
    guard("system-crt")?;
    fs::create_dir_all(&prefix)?;
    {
        // The CMake trees stay out of the published prefix, as in the static
        // CRT, and another key's trees, configured from other sources and
        // for another prefix, are emptied rather than reused.
        let work = super::work_dir(root, &target, "crt");
        let _work_lock = super::claim_work(&work, &prefix)?;
        build_projects(root, pins, &prefix, &work, &cc)?;
    }
    validate(&prefix)?;
    fs::write(prefix.join(".complete"), digest)?;
    Ok(prefix)
}

fn build_projects(
    root: &Path,
    pins: &Pins,
    prefix: &Path,
    scratch: &Path,
    cc: &std::ffi::OsStr,
) -> Result<()> {
    let ninja = super::ninja_program()?;
    for &(name, pin) in PROJECTS {
        let work = scratch.join(name);
        // The marker records an install into this prefix, so it lives there
        // rather than in the scratch tree another key may claim.
        if super::crt::installed_marker(prefix, name).is_file() {
            continue;
        }
        let input = source(root, pins, pin)?;
        process::run(
            tool_command(root, "cmake")?
                .arg("-S")
                .arg(input)
                .arg("-B")
                .arg(&work)
                .args([
                    "-G",
                    "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DCMAKE_INSTALL_LIBDIR=lib",
                    "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                    "-DBUILD_SHARED_LIBS=OFF",
                    "-DBUILD_TESTING=OFF",
                    "-DUSE_OPENSSL=ON",
                    "-DUNSAFE_TREAT_WARNINGS_AS_ERRORS=OFF",
                    "-DCMAKE_C_FLAGS=-fno-omit-frame-pointer",
                    "-DCMAKE_FIND_USE_PACKAGE_REGISTRY=FALSE",
                ])
                .arg(format!("-DCMAKE_C_COMPILER={}", cc.to_string_lossy()))
                .arg(format!("-DCMAKE_MAKE_PROGRAM={}", ninja.display()))
                .arg(format!("-DCMAKE_INSTALL_PREFIX={}", prefix.display()))
                .arg(format!("-DCMAKE_PREFIX_PATH={}", prefix.display())),
        )?;
        process::run(
            tool_command(root, "cmake")?
                .arg("--build")
                .arg(&work)
                .args(["--target", "install", "--parallel"])
                .arg(super::toolchain::jobs()?.to_string()),
        )?;
        super::crt::mark_installed(prefix, name)?;
    }
    Ok(())
}

fn validate(prefix: &Path) -> Result<()> {
    for &(name, _) in PROJECTS {
        let name = if name == "s2n-tls" { "s2n" } else { name };
        if !prefix.join("lib").join(format!("lib{name}.a")).is_file() {
            return Err(error(format!("prepared system CRT missing {name}")));
        }
    }
    for name in ["crypto", "ssl"] {
        if prefix.join("lib").join(format!("lib{name}.a")).exists() {
            return Err(error("distro CRT prefix must leave OpenSSL shared"));
        }
    }
    Ok(())
}
