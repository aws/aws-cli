//! Opt-in upstream integration runner; collection is the only offline mode.

use std::path::Path;
use std::process::Command;

use crate::{TaskError, deps, harness, process};

pub fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    let (artifact_args, forwarded) = arguments(args);
    // Only the default artifact takes the static host check (`harness::binary`).
    let binary = harness::binary(root, artifact_args)?;
    let pins = deps::Pins::load(root)?;
    deps::check_pins(root, &pins)?;
    let source = deps::aws_cli_source(root)?;
    process::run(&mut command(root, &binary, &source, forwarded))
}

fn arguments(args: &[String]) -> (&[String], &[String]) {
    args.iter()
        .position(|argument| argument == "--")
        .map_or((args, &[]), |index| (&args[..index], &args[index + 1..]))
}

fn command(root: &Path, binary: &Path, source: &Path, args: &[String]) -> Command {
    let mut command = Command::new("python3");
    // `-B` keeps the runner's imports from writing bytecode under `tests/`;
    // the runner sends the pytest child's bytecode under the cache.
    command
        .current_dir(root)
        .arg("-B")
        .arg(root.join("tests/integ/run_integ_tests.py"))
        .arg("--aws-binary")
        .arg(binary)
        .arg("--aws-cli-source")
        .arg(source)
        .arg("--cache-dir")
        .arg(root.join("target/integ-test"))
        .args(args);
    command
}

#[cfg(test)]
mod tests;
