//! Native host build driver for the `aws` executable.

#![forbid(unsafe_code)]

mod argparse;
mod blackbox;
mod ci;
mod coverage;
mod deps;
mod file_lock;
mod fuzzing;
mod harness;
mod integ;
mod lint;
mod packaging;
mod process;
mod product;
mod python;
mod sanitizers;
mod verification;

#[cfg(test)]
mod tests;

use std::fmt;
use std::io::{self, Write};
use std::path::Path;
use std::process::ExitCode;

#[derive(Debug)]
pub enum TaskError {
    Io(io::Error),
    Message(String),
}

impl fmt::Display for TaskError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(error) => error.fmt(f),
            Self::Message(message) => f.write_str(message),
        }
    }
}

impl std::error::Error for TaskError {}

impl From<io::Error> for TaskError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

fn main() -> ExitCode {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent();
    let result = match root {
        Some(root) => dispatch(root, &args),
        None => Err(TaskError::Message("workspace root is absent".into())),
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let _ = writeln!(io::stderr().lock(), "xtask: {error}");
            ExitCode::FAILURE
        }
    }
}

fn dispatch(root: &Path, args: &[String]) -> Result<(), TaskError> {
    let (command, rest) = args
        .split_first()
        .ok_or_else(|| TaskError::Message(format!("expected one of: {}", COMMANDS.join(", "))))?;
    // Held until the command returns, after every build and test it runs
    // exits, so `deps reset` never removes a dependency a command still reads.
    let _store = if deps::resets_store(command, rest) {
        None
    } else {
        Some(deps::hold_store(root)?)
    };
    if let Some(args) = system_crt_args(command, rest) {
        return product::system_crt(root, args);
    }
    match command.as_str() {
        "build" => product::build(root, rest),
        "run" => product::run(root, rest),
        "package" => packaging::run(root, rest),
        "ci" => ci::run(root, rest),
        "fuzz" => fuzzing::run(root, rest),
        "integ" => integ::run(root, rest),
        "lint" => lint::run(root),
        "test" => verification::run(root, rest),
        "blackbox" => blackbox::run(root, rest),
        "harness-test" => harness::self_test(root, rest),
        "dump-arg-tables" | "check-argparse" | "fuzz-argparse" => {
            argparse::run(root, command, rest)
        }
        "fetch" | "check-pins" | "deps" => deps::run(root, command, rest),
        _ => Err(TaskError::Message(format!(
            "unknown command {command}; expected one of: {}",
            COMMANDS.join(", ")
        ))),
    }
}

/// The options of `deps system-crt`, which `dispatch` sends to the product's
/// system-mode preparation before `deps::run`: the system CRT is an input of
/// system builds alone, so it takes the system-mode host check, any native
/// Linux/glibc architecture, rather than the static host list `deps::run`
/// applies to every dependency stage.
fn system_crt_args<'a>(command: &str, rest: &'a [String]) -> Option<&'a [String]> {
    match rest {
        [stage, args @ ..] if command == "deps" && stage == "system-crt" => Some(args),
        _ => None,
    }
}

const COMMANDS: &[&str] = &[
    "build",
    "run",
    "package",
    "ci",
    "fuzz",
    "integ",
    "lint",
    "test",
    "blackbox",
    "harness-test",
    "dump-arg-tables",
    "check-argparse",
    "fuzz-argparse",
    "fetch",
    "check-pins",
    "deps",
];
