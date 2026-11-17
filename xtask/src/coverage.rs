//! Native Rust line coverage collected with the matching LLVM tools component.

mod report;

use crate::{TaskError, deps, process, python};
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Collect line coverage from the product tests. `filter`, the test
/// command's `--filter`, selects the tests whose hits are collected; the
/// application baseline stays the whole `aws` binary.
pub fn run(root: &Path, packages: &[String], filter: Option<&str>) -> Result<(), TaskError> {
    deps::native_host()?;
    if !packages.is_empty() {
        return Err(deps::error(
            "coverage reports all product crates; omit --package",
        ));
    }
    let llvm = llvm_tools(root)?;
    let directory = root.join("target/coverage");
    let profiles = directory.join("profiles");
    if profiles.exists() {
        fs::remove_dir_all(&profiles)?;
    }
    fs::create_dir_all(&profiles)?;
    let mut command = native_command(root, &directory)?;
    command.args([
        "test",
        "--locked",
        "--workspace",
        "--exclude",
        "xtask",
        "--target",
        deps::TARGET,
        "--no-run",
        "--message-format=json",
    ]);
    let output = process::output(&mut command)?;
    let mut artifacts = test_artifacts(&output.stdout)?;
    let profile = profiles.join("%p-%m.profraw");
    for artifact in &artifacts {
        process::run(&mut test_command(
            root, artifact, &command, &profile, filter,
        ))?;
    }
    let binary = build_cli(root, &directory)?;
    process::run(
        Command::new(&binary)
            .arg("--version")
            .env("LLVM_PROFILE_FILE", &profile),
    )?;
    let merged = merge(&llvm, &profiles, &directory)?;
    // The shipped binary alone names the application's executable lines;
    // every test executable and it together supply the hits.
    let application = export(&llvm, &merged, std::slice::from_ref(&binary))?;
    artifacts.push(binary);
    let union = export(&llvm, &merged, &artifacts)?;
    fs::write(directory.join("application.lcov"), &application)?;
    fs::write(directory.join("union.lcov"), &union)?;
    let table = report::summary(root, &application, &union)?;
    fs::write(directory.join("lines.txt"), &table)?;
    io::stdout().write_all(table.as_bytes())?;
    Ok(())
}

/// One test executable's run under the build's environment, writing raw
/// profiles to `profile`, with the libtest `filter`, if any, as its first
/// argument, as `--sanitize-c` passes it. The `harness = false`
/// interpreter tests (python-fallback `finder`, `exit_status`) ignore it and
/// run in full, as they do under `cargo test -- FILTER`.
fn test_command(
    root: &Path,
    artifact: &Path,
    build: &Command,
    profile: &Path,
    filter: Option<&str>,
) -> Command {
    let mut command = Command::new(artifact);
    command
        .args(filter)
        .current_dir(root)
        .envs(
            build
                .get_envs()
                .filter_map(|(key, value)| value.map(|value| (key, value))),
        )
        .env("LLVM_PROFILE_FILE", profile);
    command
}

/// The lcov export of the merged profile over `objects`.
fn export(llvm: &Path, merged: &Path, objects: &[PathBuf]) -> Result<Vec<u8>, TaskError> {
    let mut command = Command::new(llvm_tool(llvm, "llvm-cov"));
    command
        .args(["export", "--format=lcov"])
        .arg(format!("--instr-profile={}", merged.display()));
    for object in objects {
        command.arg("--object").arg(object);
    }
    Ok(process::output(&mut command)?.stdout)
}

fn native_command(root: &Path, directory: &Path) -> Result<Command, TaskError> {
    let pins = deps::Pins::load(root)?;
    let tools = deps::toolchain(root, &pins)?;
    let crt = deps::crt(root, &pins, &tools)?;
    let payload = python::build(root, &pins, &tools, &crt, !cfg!(windows))?;
    let mut command = Command::new("cargo");
    tools.apply_environment(&mut command);
    command
        .current_dir(root)
        .env("CARGO_TARGET_DIR", directory.join("build"))
        .env("RUSTFLAGS", "-C instrument-coverage")
        .env("AWS_NATIVE_CRT_PREFIX", crt)
        .env("AWS_NATIVE_CPYTHON_PREFIX", payload.cpython)
        .env("AWS_NATIVE_FALLBACK_PREFIX", payload.fallback);
    tools.apply_c_tools(&mut command);
    tools.apply_link(&mut command);
    Ok(command)
}

fn build_cli(root: &Path, directory: &Path) -> Result<PathBuf, TaskError> {
    let mut command = native_command(root, directory)?;
    command.args([
        "build",
        "--locked",
        "-p",
        "aws-cli",
        "--bin",
        "aws",
        "--target",
        deps::TARGET,
    ]);
    process::run(&mut command)?;
    Ok(directory
        .join("build")
        .join(deps::TARGET)
        .join("debug/aws")
        .with_extension(std::env::consts::EXE_EXTENSION))
}

fn llvm_tools(root: &Path) -> Result<PathBuf, TaskError> {
    let sysroot = process::output(
        Command::new("rustc")
            .current_dir(root)
            .args(["--print", "sysroot"]),
    )?;
    let version = process::output(Command::new("rustc").current_dir(root).arg("-vV"))?;
    let version = String::from_utf8_lossy(&version.stdout);
    let host = version
        .lines()
        .find_map(|line| line.strip_prefix("host: "))
        .ok_or_else(|| deps::error("rustc host missing"))?;
    let directory = PathBuf::from(String::from_utf8_lossy(&sysroot.stdout).trim())
        .join("lib/rustlib")
        .join(host)
        .join("bin");
    if !llvm_tool(&directory, "llvm-cov").is_file()
        || !llvm_tool(&directory, "llvm-profdata").is_file()
    {
        return Err(deps::error(
            "coverage requires rustup component add llvm-tools-preview",
        ));
    }
    Ok(directory)
}

fn llvm_tool(directory: &Path, name: &str) -> PathBuf {
    directory
        .join(name)
        .with_extension(std::env::consts::EXE_EXTENSION)
}

fn test_artifacts(output: &[u8]) -> Result<Vec<PathBuf>, TaskError> {
    let mut artifacts = Vec::new();
    for line in output
        .split(|byte| *byte == b'\n')
        .filter(|line| !line.is_empty())
    {
        let value: serde_json::Value = serde_json::from_slice(line)
            .map_err(|error| deps::error(format!("invalid Cargo artifact JSON: {error}")))?;
        if value["reason"] == "compiler-artifact"
            && value["profile"]["test"] == true
            && let Some(path) = value["executable"].as_str()
        {
            artifacts.push(PathBuf::from(path));
        }
    }
    artifacts.sort();
    artifacts.dedup();
    if artifacts.is_empty() {
        return Err(deps::error("coverage build emitted no test executables"));
    }
    Ok(artifacts)
}

fn merge(llvm: &Path, profiles: &Path, directory: &Path) -> Result<PathBuf, TaskError> {
    let mut inputs = Vec::new();
    for entry in fs::read_dir(profiles)? {
        let path = entry?.path();
        if path
            .extension()
            .is_some_and(|extension| extension == "profraw")
        {
            inputs.push(path);
        }
    }
    inputs.sort();
    if inputs.is_empty() {
        return Err(deps::error("coverage run emitted no raw profiles"));
    }
    let merged = directory.join("merged.profdata");
    process::run(
        Command::new(llvm_tool(llvm, "llvm-profdata"))
            .args(["merge", "--sparse"])
            .args(inputs)
            .arg("--output")
            .arg(&merged),
    )?;
    Ok(merged)
}

#[cfg(test)]
mod tests;
