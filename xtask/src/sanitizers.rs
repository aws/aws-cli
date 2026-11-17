//! Project-owned C instrumentation of the native test binaries.

mod runtime;

use crate::{TaskError, deps, process, python};
use serde::Serialize;
use std::collections::BTreeMap;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CMode {
    Trap,
    Full,
}
impl CMode {
    fn name(self) -> &'static str {
        match self {
            Self::Trap => "trap",
            Self::Full => "full",
        }
    }
}

/// Prepare the pinned native musl runtime during the dependency-building phase.
pub fn prepare(root: &Path) -> Result<PathBuf, TaskError> {
    deps::native_host()?;
    let pins = deps::Pins::load(root)?;
    let tools = deps::toolchain(root, &pins)?;
    runtime::build(root, &pins, &tools)
}

/// The prefix of the runtime archive `prepare` returns, which `runtime::build`
/// keeps in the prefix's `lib` directory.
pub fn runtime_prefix(archive: &Path) -> Result<PathBuf, TaskError> {
    archive
        .parent()
        .and_then(Path::parent)
        .map(Path::to_owned)
        .ok_or_else(|| deps::error(format!("{} has no prefix", archive.display())))
}

/// Build the instrumented tests, then run each binary from its package
/// directory, as `cargo test` does, with `filter`, if any, as its first
/// argument.
pub fn c(root: &Path, mode: CMode, profile: &str, filter: Option<&str>) -> Result<(), TaskError> {
    let mut command = native_tests(root, &format!("ubsan-{}", mode.name()), profile)?;
    command
        .arg("--workspace")
        .env("AWS_NATIVE_SANITIZE_C", mode.name());
    if mode == CMode::Full {
        command.env("AWS_NATIVE_UBSAN_RUNTIME", prepare(root)?);
    }
    let binaries = executables(&process::output(&mut command)?.stdout)?;
    execute(
        root,
        &format!("ubsan-{}", mode.name()),
        &binaries,
        &command,
        filter,
    )
}

fn native_tests(root: &Path, label: &str, profile: &str) -> Result<Command, TaskError> {
    deps::native_host()?;
    if !matches!(
        profile,
        "dev" | "release" | "release-safe" | "release-small"
    ) {
        return Err(deps::error(format!(
            "unsupported sanitizer test profile: {profile}"
        )));
    }
    let pins = deps::Pins::load(root)?;
    let tools = deps::toolchain(root, &pins)?;
    let crt = deps::crt(root, &pins, &tools)?;
    let payload = python::build(root, &pins, &tools, &crt, !cfg!(windows))?;
    let mut command = Command::new("cargo");
    tools.apply_environment(&mut command);
    command.current_dir(root).args([
        "test",
        "--locked",
        "--no-run",
        "--message-format=json-render-diagnostics",
        "--target",
        deps::TARGET,
        "--profile",
        profile,
    ]);
    command
        .env("AWS_NATIVE_CRT_PREFIX", crt)
        .env("AWS_NATIVE_CPYTHON_PREFIX", payload.cpython)
        .env("AWS_NATIVE_FALLBACK_PREFIX", payload.fallback)
        // Compiler probes in the test suites use the managed toolchain.
        .env("AWS_NATIVE_TEST_CC", &tools.cc)
        .env("AWS_NATIVE_TEST_CLANG", &tools.clang)
        .env("CARGO_TARGET_DIR", root.join("target/analysis").join(label));
    tools.apply_c_tools(&mut command);
    if cfg!(target_arch = "x86_64") {
        command.env("RUSTFLAGS", "-Ctarget-cpu=x86-64");
    }
    tools.apply_link(&mut command);
    Ok(command)
}

/// A test executable and the package directory its tests resolve fixture
/// paths against.
#[derive(Debug, Eq, PartialEq)]
struct TestBinary {
    path: PathBuf,
    package: PathBuf,
}

fn executables(output: &[u8]) -> Result<Vec<TestBinary>, TaskError> {
    let mut result = BTreeMap::new();
    for line in output
        .split(|byte| *byte == b'\n')
        .filter(|line| !line.is_empty())
    {
        let value: serde_json::Value = serde_json::from_slice(line)
            .map_err(|failure| deps::error(format!("invalid Cargo artifact message: {failure}")))?;
        if value["reason"] == "compiler-artifact"
            && value["profile"]["test"] == true
            && let Some(path) = value["executable"].as_str()
        {
            let package = value["manifest_path"]
                .as_str()
                .and_then(|manifest| Path::new(manifest).parent())
                .ok_or_else(|| deps::error(format!("test executable {path} has no package")))?;
            result.insert(PathBuf::from(path), package.to_owned());
        }
    }
    if result.is_empty() {
        return Err(deps::error("Cargo produced no test executables"));
    }
    Ok(result
        .into_iter()
        .map(|(path, package)| TestBinary { path, package })
        .collect())
}

#[derive(Serialize)]
struct Outcome {
    binary: PathBuf,
    success: bool,
    status: String,
}
fn execute(
    root: &Path,
    label: &str,
    binaries: &[TestBinary],
    build: &Command,
    filter: Option<&str>,
) -> Result<(), TaskError> {
    let mut outcomes = Vec::new();
    for binary in binaries {
        writeln!(io::stdout(), "{label}: {}", binary.path.display())?;
        let mut command = Command::new(&binary.path);
        command
            .args(filter)
            .current_dir(&binary.package)
            .envs(
                build
                    .get_envs()
                    .filter_map(|(key, value)| value.map(|value| (key, value))),
            )
            .env("UBSAN_OPTIONS", "halt_on_error=1:print_stacktrace=1");
        let status = process::spawn(&mut command)?.wait()?;
        outcomes.push(Outcome {
            binary: binary.path.clone(),
            success: status.success(),
            status: status.to_string(),
        });
    }
    write_report(root, label, &outcomes)
}

fn write_report(root: &Path, label: &str, outcomes: &[Outcome]) -> Result<(), TaskError> {
    let report = root
        .join("target/analysis")
        .join(label)
        .join("results.json");
    fs::create_dir_all(
        report
            .parent()
            .ok_or_else(|| deps::error("missing report parent"))?,
    )?;
    fs::write(
        report,
        serde_json::to_vec_pretty(outcomes).map_err(|failure| {
            deps::error(format!("cannot encode sanitizer results: {failure}"))
        })?,
    )?;
    let failed = outcomes.iter().filter(|outcome| !outcome.success).count();
    writeln!(
        io::stdout(),
        "{label}: {} test binaries, {failed} failed",
        outcomes.len()
    )?;
    if failed == 0 {
        Ok(())
    } else {
        Err(deps::error(format!(
            "{label}: {failed} test binaries failed"
        )))
    }
}

#[cfg(test)]
mod tests;
