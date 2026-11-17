//! Upstream and repository blackbox tests against one AWS CLI through the local TLS stub.
//!
//! The blackbox harness, `tests/blackbox/run.py`, runs upstream's tests and
//! the repository's in two pytest sessions against one binary, in its default
//! configuration. The built binary runs with its ledger of known native gaps;
//! an `--external-binary`, such as the public AWS CLI of the in-tree version,
//! runs with only the upstream issues that ledger holds and skips the tests
//! marked `native_only`. `--suite upstream` or `--suite repo` runs that
//! session alone. Every run applies the upstream failures, and pytest
//! selection follows `--`. A system build says so with the options
//! `cargo xtask build` made it with (`--link-mode system`, `--crt-link`,
//! `--python-payload`, `--python-exe`), so its executable and payload tests
//! check the system build's contract instead of the static build's, as
//! smoke's did. The caller's environment, including `HOME`,
//! reaches the runner unchanged but for the router variable, which reaches
//! no command unless `--env` sets it. Each `--env NAME=VALUE` sets `NAME` in
//! the environment of every command of the binary, over the environment the
//! test gives it, and in no other process.

mod options;

use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::product::options::{LinkMode, PythonPayload};
use crate::python::PYTHON_ABI;
use crate::{TaskError, deps, harness, process};

use options::{Binary, Build, CrtLink, Options};

pub fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    let options = options::parse(args)?;
    let artifact = options.artifact_args();
    // Only the default artifact takes its mode's host check (`harness::binary`).
    let binary = match (&options.binary, options.build.link_mode) {
        (Binary::External(path), _) => external_binary(root, path)?,
        (_, LinkMode::Static) => harness::binary(root, &artifact)?,
        (_, LinkMode::System) => harness::system_binary(root, &artifact)?,
    };
    let build = build_args(root, &options.build)?;
    let _cli_test_guard = process::cli_test_guard(root)?;
    let pins = deps::Pins::load(root)?;
    deps::check_pins(root, &pins)?;
    let source = deps::aws_cli_source(root)?;
    let name = options.binary.report_name();
    let reports = reports(root, &options);
    fs::create_dir_all(junit_dir(root, &options.binary))?;
    for (_, report) in &reports {
        match fs::remove_file(report) {
            Ok(()) => {}
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.into()),
        }
    }
    writeln!(
        io::stdout(),
        "blackbox tests: {name} binary {}",
        binary.display()
    )?;
    let mut failures = Vec::new();
    if let Err(error) = process::run(&mut command(root, &binary, &source, &options, &build)) {
        failures.push(error.to_string());
    }
    // run.py's exit status alone does not pass a run: a run that should have
    // run tests must also report some, so an empty selection fails.
    if runs_tests(&options.forwarded)
        && let Err(error) = harness::verify_sessions(&reports, &format!("blackbox {name}"))
    {
        failures.push(error.to_string());
    }
    if failures.is_empty() {
        Ok(())
    } else {
        Err(deps::error(failures.join("\n")))
    }
}

/// Whether pytest runs tests with these forwarded arguments: collection,
/// fixture, marker, help and version listings exit without running any.
fn runs_tests(forwarded: &[String]) -> bool {
    !forwarded.iter().any(|argument| {
        matches!(
            argument.as_str(),
            "--collect-only"
                | "--co"
                | "--fixtures"
                | "--funcargs"
                | "--fixtures-per-test"
                | "--markers"
                | "--help"
                | "-h"
                | "--version"
                | "-V"
        )
    })
}

/// The AWS CLI at `path`, which, like an explicit artifact, takes no host
/// check.
fn external_binary(root: &Path, path: &str) -> Result<PathBuf, TaskError> {
    let binary = root.join(path);
    if !binary.is_file() {
        return Err(deps::error(format!(
            "external AWS CLI is absent: {}",
            binary.display()
        )));
    }
    Ok(binary)
}

/// The run.py options that describe `build`: none for the static build,
/// which run.py assumes, and every fact a system build's tests check
/// otherwise, its Python's ABI included.
fn build_args(root: &Path, build: &Build) -> Result<Vec<String>, TaskError> {
    if build.link_mode == LinkMode::Static {
        return Ok(Vec::new());
    }
    let crt_link = match build.crt_link {
        CrtLink::Static => "static",
        CrtLink::Shared => "shared",
    };
    let payload = match build.payload {
        PythonPayload::Embedded => "embedded",
        PythonPayload::System => "system",
    };
    Ok(vec![
        "--link-mode".to_owned(),
        "system".to_owned(),
        "--crt-link".to_owned(),
        crt_link.to_owned(),
        "--python-payload".to_owned(),
        payload.to_owned(),
        "--python-abi".to_owned(),
        python_abi(root, build.python_exe.as_deref())?,
    ])
}

/// The `abi` fact the system-Python discovery reports for `python_exe`,
/// spelled as `deps/scripts/probe_system_python.py` spells it. Without an
/// interpreter it is the pinned `PYTHON_ABI`, which the build's default
/// interpreter, `/usr/bin/<PYTHON_ABI>`, also reports. The interpreter runs
/// from `root`, as the build's discovery runs it, so a relative
/// `--python-exe` names the interpreter the build used wherever xtask runs.
fn python_abi(root: &Path, python_exe: Option<&Path>) -> Result<String, TaskError> {
    let Some(python_exe) = python_exe else {
        return Ok(PYTHON_ABI.to_owned());
    };
    let output = process::output(Command::new(python_exe).current_dir(root).args([
        "-I",
        "-c",
        "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')",
    ]))?;
    let abi = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    if abi.is_empty() {
        return Err(deps::error(format!(
            "system Python {} reported no ABI",
            python_exe.display()
        )));
    }
    Ok(abi)
}

/// The directory run.py writes the binary's session reports into.
fn junit_dir(root: &Path, binary: &Binary) -> PathBuf {
    root.join("target/blackbox/junit")
        .join(binary.report_name())
}

/// Each selected session's name and the JUnit report run.py writes for it.
fn reports(root: &Path, options: &Options) -> Vec<(&'static str, PathBuf)> {
    let directory = junit_dir(root, &options.binary);
    options
        .suite
        .sessions()
        .iter()
        .map(|&session| (session, directory.join(format!("{session}.xml"))))
        .collect()
}

fn command(
    root: &Path,
    binary: &Path,
    source: &Path,
    options: &Options,
    build: &[String],
) -> Command {
    let mut command = Command::new("python3");
    // `-B` keeps the runner's own imports from writing bytecode under
    // `tests/`; run.py sends the pytest child's bytecode under the cache.
    command
        .current_dir(root)
        .arg("-B")
        .arg(root.join("tests/blackbox/run.py"))
        .arg("--aws-binary")
        .arg(binary)
        .arg("--binary-kind")
        .arg(options.binary.report_name())
        .args(build);
    // Only this repository's binary has known native gaps; another AWS CLI
    // gets the upstream issues of the same ledger from run.py.
    if options.binary.is_built() {
        command
            .arg("--known-gaps")
            .arg(root.join("tests/blackbox/failures.txt"));
    }
    command
        .arg("--upstream-failures")
        .arg(root.join("tests/blackbox/upstream-failures.txt"))
        .arg("--aws-cli-source")
        .arg(source)
        .arg("--cache-dir")
        .arg(root.join("target/blackbox"));
    if let Some(suite) = options.suite.runner_arg() {
        command.arg("--suite").arg(suite);
    }
    if options.run_all {
        command.arg("--run-all");
    }
    // Each test builds its commands' environment from scratch, so run.py
    // hands these to the plugin that launches every command.
    for (name, value) in &options.env {
        command.arg("--env").arg(format!("{name}={value}"));
    }
    command
        .arg("--junit-dir")
        .arg(junit_dir(root, &options.binary));
    // The binary runs in its default configuration unless `--env` says
    // otherwise, so a router variable the caller exported reaches no command.
    command
        .args(&options.forwarded)
        .env_remove("AWS_CLI_NATIVE_ROUTER");
    command
}

#[cfg(test)]
mod tests;
