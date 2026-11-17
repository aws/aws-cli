//! Checked child process execution.

use crate::TaskError;
use crate::file_lock::FileLock;
use std::fs;
use std::io::{self, Write};
use std::path::Path;
use std::process::{Child, Command, Output};

/// Serialize CLI suites whose Python oracle contends for CRT's auto-selection lock.
pub fn cli_test_guard(root: &Path) -> Result<FileLock, TaskError> {
    let directory = root.join("target");
    fs::create_dir_all(&directory)?;
    let path = directory.join("cli-tests.lock");
    match FileLock::try_lock(&path) {
        Ok(lock) => Ok(lock),
        Err(std::fs::TryLockError::WouldBlock) => {
            writeln!(io::stderr(), "waiting for the other local CLI test suite")?;
            Ok(FileLock::lock(&path)?)
        }
        Err(std::fs::TryLockError::Error(error)) => Err(error.into()),
    }
}

/// Starts a checked child whose nonzero outcome or cancellation the caller owns.
pub fn spawn(command: &mut Command) -> Result<Child, TaskError> {
    validate(command)?;
    Ok(command.spawn()?)
}

pub fn run(command: &mut Command) -> Result<(), TaskError> {
    validate(command)?;
    let status = command.status()?;
    if !status.success() {
        return Err(TaskError::Message(format!(
            "command {:?} failed with {status}",
            command.get_program()
        )));
    }
    Ok(())
}

pub fn output(command: &mut Command) -> Result<Output, TaskError> {
    validate(command)?;
    let output = command.output()?;
    if !output.status.success() {
        return Err(TaskError::Message(format!(
            "command {:?} failed: {}",
            command.get_program(),
            String::from_utf8_lossy(&output.stderr)
        )));
    }
    Ok(output)
}

fn validate(command: &Command) -> Result<(), TaskError> {
    for (name, value) in command.get_envs() {
        if name == "HOME" {
            return Err(TaskError::Message(format!(
                "child commands must preserve HOME (requested {value:?})"
            )));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests;
