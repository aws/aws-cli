//! Self-contained native CLI builds using finished dependency prefixes.

pub(crate) mod options;
mod system;

use crate::{TaskError, deps, process, python};
pub(crate) use options::system_target;
use options::{LinkMode, Options};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// `cargo xtask deps system-crt [--print-roots]`: prepare the static glibc
/// CRT that a `--crt-static-prefix` system build links.
pub fn system_crt(root: &Path, args: &[String]) -> Result<(), TaskError> {
    system::crt(root, args)
}

pub fn build(root: &Path, args: &[String]) -> Result<(), TaskError> {
    // The host gate depends on the link mode: system builds accept any native
    // Linux/glibc architecture, so options come first.
    let options = options::parse(args)?;
    reject_dependency_override()?;
    if options.link_mode == LinkMode::System {
        return system::build(root, &options);
    }
    deps::native_host()?;
    let (mut command, _) = static_command(root, &options)?;
    process::run(&mut command)
}

/// Build the noninstalled parser-capture executable and return its path.
///
/// It reuses the static product's interpreter and payload, but its bootstrap
/// ends in capture source fixed at build time instead of CLIDriver dispatch.
/// A separate target directory keeps it from replacing an installable binary.
pub fn build_capture(root: &Path) -> Result<PathBuf, TaskError> {
    deps::native_host()?;
    reject_dependency_override()?;
    let options = options::parse(&["--profile".into(), "dev".into()])?;
    let (mut command, python) = static_command(root, &options)?;
    let directory = root.join(CAPTURE_TARGET_DIR);
    let bytecode = capture_bytecode(root, &python.cpython, &directory)?;
    command
        .arg("--target-dir")
        .arg(&directory)
        .env("AWS_NATIVE_RUNTIME_BYTECODE", bytecode);
    process::run(&mut command)?;
    Ok(capture_executable(root, &options))
}

const CAPTURE_TARGET_DIR: &str = "target/argparse/capture";

fn capture_executable(root: &Path, options: &Options) -> PathBuf {
    root.join(CAPTURE_TARGET_DIR)
        .join(&options.target)
        .join(options.cargo_profile())
        .join(format!("aws{}", std::env::consts::EXE_SUFFIX))
}

/// Compile the capture bootstrap with the interpreter the executable embeds.
///
/// The output is replaced only when its bytes change, so an unchanged
/// interpreter and bootstrap do not relink the capture executable.
fn capture_bytecode(root: &Path, cpython: &Path, directory: &Path) -> Result<PathBuf, TaskError> {
    fs::create_dir_all(directory)?;
    let output = directory.join("parse-capture.pyc");
    let candidate = directory.join("parse-capture.pyc.new");
    let interpreter = cpython.join("bin").join(format!(
        "{}{}",
        python::PYTHON_ABI,
        std::env::consts::EXE_SUFFIX
    ));
    process::run(
        Command::new(interpreter)
            .current_dir(root)
            .arg("-I")
            .arg(root.join("tests/argparse/build_capture.py"))
            .arg(root.join("crates/python-fallback/python/runtime.py"))
            .arg(root.join("tests/argparse/parse_capture.py"))
            .arg(&candidate),
    )?;
    if fs::read(&output).ok() == Some(fs::read(&candidate)?) {
        fs::remove_file(&candidate)?;
    } else {
        fs::rename(&candidate, &output)?;
    }
    Ok(output)
}

fn reject_dependency_override() -> Result<(), TaskError> {
    if std::env::var_os("AWS_NATIVE_DEPS_OVERRIDE").is_some() {
        return Err(TaskError::Message(
            "the link gate rejects dependency overrides".into(),
        ));
    }
    Ok(())
}

fn static_command(
    root: &Path,
    options: &Options,
) -> Result<(Command, python::PythonOutputs), TaskError> {
    let pins = deps::Pins::load(root)?;
    deps::check_pins(root, &pins)?;
    let tools = deps::toolchain(root, &pins)?;
    let crt = deps::crt(root, &pins, &tools)?;
    let python = python::build(root, &pins, &tools, &crt, options.python_pgo)?;
    let mut command = Command::new("cargo");
    tools.apply_environment(&mut command);
    command
        .current_dir(root)
        .args(["build", "--locked", "-p", "aws-cli"])
        .args(
            options
                .features()
                .map(|features| ["--features", features])
                .iter()
                .flatten(),
        )
        .args(["--target", &options.target])
        .args(["--profile", &options.profile])
        .env("AWS_NATIVE_LINK_MODE", "static")
        .env("AWS_NATIVE_PYTHON_LINK", "static")
        .env("AWS_NATIVE_PYTHON_PAYLOAD", "embedded")
        .env("AWS_NATIVE_CRT_PREFIX", crt)
        .env("AWS_NATIVE_CPYTHON_PREFIX", &python.cpython)
        .env("AWS_NATIVE_FALLBACK_PREFIX", &python.fallback);
    tools.apply_c_tools(&mut command);
    apply_codegen(&mut command, options);
    tools.apply_link(&mut command);
    Ok((command, python))
}

#[cfg(test)]
mod tests;

fn apply_codegen(command: &mut Command, options: &Options) {
    // Cargo profile overrides retain profile-specific optimization while allowing
    // the public strip switch to affect only the final artifact.
    if let Some(strip) = options.strip {
        let profile = options.profile.replace('-', "_").to_uppercase();
        command.env(
            format!("CARGO_PROFILE_{profile}_STRIP"),
            if strip { "symbols" } else { "none" },
        );
        // An unstripped binary keeps full DWARF; the release profiles carry
        // none, and dev already has it.
        if !strip && options.profile != "dev" {
            command.env(format!("CARGO_PROFILE_{profile}_DEBUG"), "full");
        }
    }
    let mut flags = std::env::var("CARGO_ENCODED_RUSTFLAGS").unwrap_or_else(|_| {
        std::env::var("RUSTFLAGS")
            .unwrap_or_default()
            .split_whitespace()
            .collect::<Vec<_>>()
            .join("\x1f")
    });
    for flag in [
        Some(format!(
            "-Cforce-frame-pointers={}",
            if options.frame_pointers { "yes" } else { "no" }
        )),
        options.cpu.as_ref().map(|cpu| {
            let cpu = if cpu == "baseline" {
                if cfg!(target_arch = "x86_64") {
                    "x86-64"
                } else {
                    "generic"
                }
            } else {
                cpu.as_str()
            };
            format!("-Ctarget-cpu={cpu}")
        }),
    ]
    .into_iter()
    .flatten()
    {
        if !flags.is_empty() {
            flags.push('\x1f');
        }
        flags.push_str(&flag);
    }
    if cfg!(windows) {
        flags.push_str("\x1f-Ctarget-feature=+crt-static");
    }
    command.env("CARGO_ENCODED_RUSTFLAGS", flags);
}

pub fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    let (build_args, aws_args) = split_run_args(args);
    let options = options::parse(build_args)?;
    build(root, build_args)?;
    let executable = root
        .join("target")
        .join(&options.target)
        .join(options.cargo_profile())
        .join(if cfg!(windows) { "aws.exe" } else { "aws" });
    process::run(Command::new(executable).current_dir(root).args(aws_args))
}

/// Split `[BUILD OPTIONS] [-- ARGS]` at the first `--`. Without one, every
/// argument is a build option and aws runs with none.
fn split_run_args(args: &[String]) -> (&[String], &[String]) {
    match args.iter().position(|argument| argument == "--") {
        Some(separator) => (&args[..separator], &args[separator + 1..]),
        None => (args, &[]),
    }
}
