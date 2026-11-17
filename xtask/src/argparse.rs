//! Argument-parser parity gates against a noninstalled embedded Python oracle.
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::{TaskError, deps, process, product};

#[derive(Debug, Default, PartialEq, Eq)]
struct Options {
    capture_binary: Option<PathBuf>,
    native_parser: Option<PathBuf>,
    fuzz: Option<String>,
    seed: Option<String>,
    forwarded: Vec<String>,
}

pub fn run(root: &Path, command: &str, args: &[String]) -> Result<(), TaskError> {
    deps::native_host()?;
    let options = options(args)?;
    let parser = match &options.native_parser {
        Some(path) => absolute(root, path),
        None => build_tool(root)?,
    };
    let tables = process::output(Command::new(&parser).arg("dump-tables"))?;
    if command == "dump-arg-tables" {
        io::stdout().lock().write_all(&tables.stdout)?;
        return Ok(());
    }
    let directory = root.join("target/argparse");
    fs::create_dir_all(&directory)?;
    let table_file = directory.join("tables.json");
    fs::write(&table_file, tables.stdout)?;
    let source = deps::aws_cli_source(root)?;
    let capture = match &options.capture_binary {
        Some(path) => absolute(root, path),
        None => product::build_capture(root)?,
    };
    if !capture.is_file() {
        return Err(TaskError::Message(format!(
            "capture binary is absent: {}",
            capture.display()
        )));
    }
    let mut oracle = oracle_command(root, &parser, &capture, &source, &table_file, &directory);
    configure_mode(&mut oracle, command, &options)?;
    if command != "check-argparse" {
        return process::run(&mut oracle);
    }
    // The drift check and the corpus replay both run, and both report, so a
    // drifted table does not hide replay divergences.
    combine([
        check_tables(root, &source, &table_file)
            .map_err(|error| deps::error(format!("argument table drift: {error}"))),
        process::run(&mut oracle).map_err(|error| deps::error(format!("corpus replay: {error}"))),
    ])
}

/// Fail with every failed check's message, in order; a lone failure is kept as is.
fn combine(results: [Result<(), TaskError>; 2]) -> Result<(), TaskError> {
    let mut failures = results.into_iter().filter_map(Result::err);
    let Some(first) = failures.next() else {
        return Ok(());
    };
    match failures.next() {
        None => Err(first),
        Some(second) => Err(deps::error(format!("{first}\n{second}"))),
    }
}

fn configure_mode(oracle: &mut Command, command: &str, options: &Options) -> Result<(), TaskError> {
    match command {
        "check-argparse" if options.forwarded.is_empty() => {
            oracle.arg("--check");
        }
        "check-argparse" => {}
        "fuzz-argparse" => {
            oracle.args(["--fuzz", options.fuzz.as_deref().unwrap_or("3000")]);
        }
        _ => return Err(deps::error(format!("unknown argparse command: {command}"))),
    }
    if let Some(seed) = &options.seed {
        oracle.args(["--seed", seed]);
    }
    oracle.args(&options.forwarded);
    Ok(())
}

fn check_tables(root: &Path, source: &Path, tables: &Path) -> Result<(), TaskError> {
    process::run(&mut table_check_command(root, source, tables))
}

fn table_check_command(root: &Path, source: &Path, tables: &Path) -> Command {
    let mut command = Command::new("python3");
    // A venv of its own keeps another harness from replacing the interpreter
    // the checker is using. `-B` keeps the checker's imports from writing
    // bytecode under `tests/`.
    command
        .current_dir(root)
        .arg("-B")
        .arg(root.join("tests/argparse/argtables.py"))
        .arg("--aws-cli-source")
        .arg(source)
        .arg("--cache-dir")
        .arg(root.join("target/argtables"))
        .arg("--native-tables")
        .arg(tables);
    command
}

fn build_tool(root: &Path) -> Result<PathBuf, TaskError> {
    process::run(Command::new("cargo").current_dir(root).args([
        "build",
        "--locked",
        "--package",
        "awscli-argparse",
        "--bin",
        "argparse-tool",
    ]))?;
    Ok(root
        .join("target/debug/argparse-tool")
        .with_extension(std::env::consts::EXE_EXTENSION))
}

fn oracle_command(
    root: &Path,
    parser: &Path,
    capture: &Path,
    source: &Path,
    tables: &Path,
    directory: &Path,
) -> Command {
    let mut command = Command::new("python3");
    command
        .current_dir(root)
        .arg("-B")
        .arg(root.join("tests/argparse/parse_oracle.py"))
        .arg("--capture-binary")
        .arg(capture)
        .arg("--native-parser")
        .arg(parser)
        .arg("--aws-cli-source")
        .arg(source)
        .arg("--native-tables")
        .arg(tables)
        .arg("--ledger")
        .arg(directory.join("divergences.jsonl"));
    command
}

fn absolute(root: &Path, path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_owned()
    } else {
        root.join(path)
    }
}

fn options(args: &[String]) -> Result<Options, TaskError> {
    let mut result = Options::default();
    let mut args = args.iter();
    while let Some(option) = args.next() {
        if option == "--" {
            result.forwarded.extend(args.cloned());
            break;
        }
        let value = args
            .next()
            .ok_or_else(|| TaskError::Message(format!("{option} requires a value")))?;
        match option.as_str() {
            "--capture-binary" => result.capture_binary = Some(value.into()),
            "--native-parser" => result.native_parser = Some(value.into()),
            "--fuzz" => {
                positive_integer(value)?;
                result.fuzz = Some(value.clone());
            }
            "--seed" => {
                value.parse::<u64>().map_err(|_| {
                    TaskError::Message("--seed requires a decimal unsigned integer".into())
                })?;
                result.seed = Some(value.clone());
            }
            _ => {
                return Err(TaskError::Message(format!(
                    "unknown argparse option: {option}"
                )));
            }
        }
    }
    Ok(result)
}

fn positive_integer(value: &str) -> Result<(), TaskError> {
    if value.parse::<u32>().is_ok_and(|number| number > 0) {
        Ok(())
    } else {
        Err(TaskError::Message(
            "--fuzz requires a positive integer".into(),
        ))
    }
}

#[cfg(test)]
mod tests;
