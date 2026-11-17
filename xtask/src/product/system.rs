//! Prepare native glibc system-Python payloads and explicit link inputs.

use super::options::{Options, PythonPayload};
use crate::{TaskError, deps, process};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

const INPUTS: &[&str] = &[
    "xtask/src/product/system.rs",
    "xtask/src/product/options.rs",
    "deps/scripts/probe_system_python.py",
    "deps/scripts/validate_bytecode_metadata.py",
    "deps/scripts/prepare_system_python.py",
    "deps/scripts/prepare_python_fallback.py",
    "deps/scripts/pack.py",
    "deps/scripts/gen_ac_index.py",
    "deps/scripts/build_environ.py",
    "deps/scripts/build_guard.py",
    "deps/scripts/native_target.py",
    "deps/scripts/tool_environ.txt",
];

struct Inputs {
    cc: std::ffi::OsString,
    ar: std::ffi::OsString,
    crt: PathBuf,
    crt_include: PathBuf,
    crt_lib: PathBuf,
    mode: &'static str,
    runtime: &'static str,
    awscrt_version: String,
    cli_digest: String,
    facts: BTreeMap<String, String>,
}

pub fn build(root: &Path, options: &Options) -> Result<(), TaskError> {
    let inputs = inputs(root, options)?;
    let prefix = prefix(root, options, &inputs)?;
    let lock = deps::lock_stage(&prefix)?;
    prepare(root, options, &inputs, &prefix)?;
    validate_bytecode(root, options, &prefix, fact(&inputs.facts, "magic")?)?;
    // Cargo only reads the prefix, which this command's hold on the store
    // keeps, so another checkout's build of the same payload need not wait.
    drop(lock);
    link(root, options, &inputs, &prefix)
}

/// Prepare the system CRT under the system-mode host check. `deps::run`
/// gates every stage on the static host list, which belongs to static
/// builds only, so `main.rs` sends `deps system-crt` here instead.
pub(super) fn crt(root: &Path, args: &[String]) -> Result<(), TaskError> {
    super::options::system_target()?;
    if std::env::var_os("AWS_NATIVE_DEPS_OVERRIDE").is_some() {
        return Err(error("dependency gates reject AWS_NATIVE_DEPS_OVERRIDE"));
    }
    let pins = deps::Pins::load(root)?;
    deps::check_pins(root, &pins)?;
    let print_roots = crt_options(args)?;
    let prefix = deps::system_crt(root, &pins)?;
    if print_roots {
        let roots = BTreeMap::from([("crt", prefix)]);
        serde_json::to_writer(io::stdout().lock(), &roots)
            .map_err(|error| TaskError::Message(error.to_string()))?;
    }
    Ok(())
}

/// Whether `deps system-crt` prints its roots; `--print-roots` is its only
/// option.
pub(super) fn crt_options(args: &[String]) -> Result<bool, TaskError> {
    if args.iter().any(|argument| argument != "--print-roots") {
        return Err(error("system-crt accepts only --print-roots"));
    }
    Ok(!args.is_empty())
}

fn inputs(root: &Path, options: &Options) -> Result<Inputs, TaskError> {
    let pins = deps::Pins::load(root)?;
    deps::check_pins(root, &pins)?;
    for path in [&options.crt_static_prefix, &options.awscrt_source]
        .into_iter()
        .flatten()
    {
        deps::register_input(root, path)?;
    }
    let embedded = options.python_payload == PythonPayload::Embedded;
    let mode = if embedded { "embedded" } else { "system" };
    let awscrt_version = pins
        .versions
        .get("awscrt_version")
        .ok_or_else(|| error("missing awscrt version"))?
        .clone();
    let crt = options
        .crt_static_prefix
        .clone()
        .unwrap_or_else(|| PathBuf::from("/usr"));
    let crt_include = crt.join("include");
    if !crt_include.join("aws/s3/s3_client.h").is_file() {
        return Err(error(format!(
            "system CRT headers missing from {}; install declared CRT development packages \
             or supply --crt-static-prefix",
            crt_include.display()
        )));
    }
    let crt_lib = crt_library_dir(&crt, &options.target, options.crt_static_prefix.is_some())?;
    let facts = probe(root, options, mode, &awscrt_version)?;
    if fact(&facts, "libdir_is_loader_path")? != "true" {
        return Err(error(
            "system Python library must be on the loader's native path; \
             package builds must not add RPATH/RUNPATH",
        ));
    }
    Ok(Inputs {
        cc: std::env::var_os("CC").unwrap_or_else(|| "clang".into()),
        ar: std::env::var_os("AR").unwrap_or_else(|| "ar".into()),
        crt,
        crt_include,
        crt_lib,
        mode,
        awscrt_version,
        facts,
        runtime: if embedded {
            "crates/python-fallback/python/runtime.py"
        } else {
            "crates/python-fallback/python/runtime_system.py"
        },
        cli_digest: deps::aws_cli_digest(root)?,
    })
}

fn probe(
    root: &Path,
    options: &Options,
    mode: &str,
    awscrt_version: &str,
) -> Result<BTreeMap<String, String>, TaskError> {
    let probe = python_output(
        &options.python_exe,
        Command::new(&options.python_exe)
            .current_dir(root)
            .arg("-I")
            .arg(root.join("deps/scripts/probe_system_python.py"))
            .args([
                "--payload-mode",
                mode,
                "--expected-awscrt-version",
                awscrt_version,
                "--awscrt",
                if options.awscrt_source.is_some() {
                    "bundled"
                } else {
                    "platlib"
                },
            ]),
    )?;
    let facts = parse_probe(&probe.stdout)?;
    validate_probe(&facts)?;
    Ok(facts)
}

/// Run the selected interpreter, naming it when it cannot be started:
/// `selected CPython executable ... was not found`.
fn python_output(python_exe: &Path, command: &mut Command) -> Result<Output, TaskError> {
    process::output(command).map_err(|failure| missing_python(python_exe, failure))
}

fn python_run(python_exe: &Path, command: &mut Command) -> Result<(), TaskError> {
    process::run(command).map_err(|failure| missing_python(python_exe, failure))
}

fn missing_python(python_exe: &Path, failure: TaskError) -> TaskError {
    match failure {
        TaskError::Io(spawn) if spawn.kind() == io::ErrorKind::NotFound => error(format!(
            "selected CPython executable {} was not found",
            python_exe.display()
        )),
        failure => failure,
    }
}

fn prefix(root: &Path, options: &Options, inputs: &Inputs) -> Result<PathBuf, TaskError> {
    let mut digest = Sha256::new();
    for name in INPUTS.iter().copied().chain([inputs.runtime]) {
        digest.update(fs::read(root.join(name))?);
    }
    digest.update(inputs.cli_digest.as_bytes());
    for (name, value) in &inputs.facts {
        digest.update(format!("{name}={value}\n"));
    }
    // Only the options the payload driver reads key it: the optimize profile,
    // strip, CPU, and frame pointers shape only the link.
    digest.update(format!(
        "{:?}:{:?}:{:?}:{:?}:{}:{:?}:{:?}",
        options.python_payload,
        options.python_exe,
        options.awscrt_source,
        options.crt_static_prefix,
        options.target,
        inputs.cc,
        inputs.ar,
    ));
    // The bundled awscrt objects are compiled with `CC`, so its identity, not
    // only its name, keys them.
    if options.awscrt_source.is_some() {
        digest.update(Command::new(&inputs.cc).arg("--version").output()?.stdout);
    }
    digest.update(fs::read(
        Path::new(fact(&inputs.facts, "libdir")?).join(fact(&inputs.facts, "ldlibrary")?),
    )?);
    digest.update(deps::tree_digest(&inputs.crt_include.join("aws"))?.as_bytes());
    if let Some(source) = &options.awscrt_source {
        for directory in ["source", "awscrt"] {
            digest.update(deps::tree_digest(&source.join(directory))?.as_bytes());
        }
    }
    Ok(deps::store(root)
        .join("deps")
        .join(&options.target)
        .join(format!("system-{:x}", digest.finalize())))
}

const OUTPUTS: &[(&str, &str)] = &[
    ("inittab", "inittab.c"),
    ("blob", "awscli-v2.blob"),
    ("runtime-bytecode", "runtime.pyc"),
    ("metadata", "python-bytecode-metadata.json"),
    ("python-config", "python_config.rs"),
];

fn prepare(
    root: &Path,
    options: &Options,
    inputs: &Inputs,
    prefix: &Path,
) -> Result<(), TaskError> {
    if prefix.join(".complete").is_file()
        && OUTPUTS.iter().all(|(_, name)| prefix.join(name).is_file())
        && (options.awscrt_source.is_none() || prefix.join("python-fallback.a").is_file())
    {
        return Ok(());
    }
    deps::guard("system-python")?;
    fs::create_dir_all(prefix)?;
    fs::write(prefix.join("aws-cli.digest"), &inputs.cli_digest)?;
    // The venv's marker records the requirements and the interpreter it was
    // built from, so it outlives any one payload key, such as each AWS CLI
    // edit, and the driver rewrites the rest of its scratch on every run.
    let work = payload_work(root, &options.target, inputs.mode);
    let _work_lock = deps::lock_stage(&work)?;
    python_run(
        &options.python_exe,
        &mut payload_command(root, options, inputs, prefix, &work)?,
    )?;
    validate_bytecode(root, options, prefix, fact(&inputs.facts, "magic")?)?;
    fs::write(prefix.join(".complete"), "ok\n")?;
    Ok(())
}

/// The `prepare_system_python.py` invocation that writes the payload outputs
/// into `prefix`, with its scratch under `work`.
fn payload_command(
    root: &Path,
    options: &Options,
    inputs: &Inputs,
    prefix: &Path,
    work: &Path,
) -> Result<Command, TaskError> {
    let mut command = Command::new(&options.python_exe);
    command
        .current_dir(root)
        .args(["-E", "-s", "-B"])
        .arg(root.join("deps/scripts/prepare_system_python.py"))
        .args(["--payload-mode", inputs.mode])
        .arg("--cache-dir")
        .arg(work)
        .arg("--aws-cli-digest")
        .arg(prefix.join("aws-cli.digest"))
        .arg("--aws-cli-source")
        .arg(deps::aws_cli_source(root)?)
        .arg("--pack-tool")
        .arg(root.join("deps/scripts/pack.py"))
        .arg("--requirements")
        .arg(deps::aws_cli_runtime_lock(root)?)
        .arg("--runtime-source")
        .arg(root.join(inputs.runtime))
        .args([
            "--expected-magic",
            fact(&inputs.facts, "magic")?,
            "--platlib",
            fact(&inputs.facts, "platlib")?,
        ])
        .args(["--native-service", "s3", "--target-triple", &options.target])
        .arg("--cc")
        .arg(&inputs.cc)
        .arg("--ar")
        .arg(&inputs.ar)
        .arg("--crt-include")
        .arg(&inputs.crt_include)
        .arg("--object-file")
        .arg(prefix.join("python-fallback.a"));
    for (flag, output) in OUTPUTS {
        command.arg(format!("--{flag}")).arg(prefix.join(output));
    }
    if options.python_payload == PythonPayload::Embedded {
        command
            .arg("--gen-ac-index")
            .arg(root.join("deps/scripts/gen_ac_index.py"));
    }
    if let Some(source) = &options.awscrt_source {
        command
            .arg("--awscrt-source")
            .arg(source)
            .args(["--awscrt-version", &inputs.awscrt_version]);
    }
    Ok(command)
}

/// The system payload's scratch directory for `target`, split by payload
/// `mode`.
fn payload_work(root: &Path, target: &str, mode: &str) -> PathBuf {
    deps::work_dir(root, target, "system-payload").join(mode)
}

fn link(root: &Path, options: &Options, inputs: &Inputs, prefix: &Path) -> Result<(), TaskError> {
    let mut command = Command::new("cargo");
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
        .args(["--target", &options.target, "--profile", &options.profile]);
    apply_environment(&mut command, options, inputs, prefix)?;
    process::run(&mut command)
}

fn apply_environment(
    command: &mut Command,
    options: &Options,
    inputs: &Inputs,
    prefix: &Path,
) -> Result<(), TaskError> {
    command
        .env("AWS_NATIVE_LINK_MODE", "system")
        .env(
            "AWS_NATIVE_CRT_STATIC",
            options.crt_static_prefix.is_some().to_string(),
        )
        .env("AWS_NATIVE_CRT_PREFIX", &inputs.crt)
        .env("AWS_NATIVE_CRT_INCLUDE", &inputs.crt_include)
        .env("AWS_NATIVE_CRT_LIBRARY_DIR", &inputs.crt_lib)
        .env("AWS_NATIVE_FALLBACK_PREFIX", prefix)
        .env("AWS_NATIVE_PYTHON_LINK", "dynamic")
        .env("AWS_NATIVE_PYTHON_PAYLOAD", inputs.mode)
        .env("AWS_NATIVE_PYTHON_INCLUDE", fact(&inputs.facts, "include")?)
        .env(
            "AWS_NATIVE_PYTHON_LIBRARY_DIR",
            fact(&inputs.facts, "libdir")?,
        )
        .env("AWS_NATIVE_PYTHON_LIBRARY", fact(&inputs.facts, "abi")?)
        .env(
            "AWS_NATIVE_PYTHON_LIBRARIES",
            fact(&inputs.facts, "link_libraries")?,
        )
        .env(
            "AWS_NATIVE_AWSCRT_BUNDLED",
            options.awscrt_source.is_some().to_string(),
        )
        .env("CC", &inputs.cc)
        .env("AR", &inputs.ar);
    super::apply_codegen(command, options);
    Ok(())
}

fn error(message: impl Into<String>) -> TaskError {
    TaskError::Message(message.into())
}

fn crt_library_dir(prefix: &Path, target: &str, is_static: bool) -> Result<PathBuf, TaskError> {
    let name = if is_static {
        "libaws-c-s3.a"
    } else {
        "libaws-c-s3.so"
    };
    for relative in [multiarch_library_dir(target), "lib64".into(), "lib".into()] {
        let candidate = prefix.join(relative);
        if candidate.join(name).is_file() {
            return Ok(candidate);
        }
    }
    Err(error(format!(
        "system CRT library {name} is missing under {}",
        prefix.display()
    )))
}

/// Debian's multiarch library directory for a rustc glibc triple, whose
/// architecture spelling differs from the GNU one for riscv64 among the
/// architectures a system build admits.
fn multiarch_library_dir(target: &str) -> String {
    let arch = match target.split('-').next().unwrap_or_default() {
        "riscv64gc" => "riscv64",
        arch => arch,
    };
    format!("lib/{arch}-linux-gnu")
}

fn parse_probe(output: &[u8]) -> Result<BTreeMap<String, String>, TaskError> {
    let text =
        std::str::from_utf8(output).map_err(|error| TaskError::Message(error.to_string()))?;
    let mut facts = BTreeMap::new();
    for line in text.trim().lines() {
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        if key == "libdir_is_loader_path" && !matches!(value, "true" | "false") {
            return Err(error("invalid system Python loader-path flag"));
        }
        if key == "link_libraries" {
            let libraries = facts.entry(key.into()).or_insert_with(String::new);
            for name in value.split(',').filter(|name| !name.is_empty()) {
                if !libraries.is_empty() {
                    libraries.push(',');
                }
                libraries.push_str(name);
            }
        } else {
            facts.insert(key.into(), value.into());
        }
    }
    Ok(facts)
}

fn validate_probe(facts: &BTreeMap<String, String>) -> Result<(), TaskError> {
    for name in [
        "abi",
        "include",
        "platlib",
        "libdir",
        "libdir_is_loader_path",
        "ldlibrary",
        "magic",
        "link_libraries",
    ] {
        let _ = fact(facts, name)?;
    }
    Ok(())
}

fn fact<'a>(facts: &'a BTreeMap<String, String>, key: &str) -> Result<&'a str, TaskError> {
    facts
        .get(key)
        .map(String::as_str)
        .ok_or_else(|| error(format!("system Python probe omitted {key}")))
}

fn validate_bytecode(
    root: &Path,
    options: &Options,
    prefix: &Path,
    magic: &str,
) -> Result<(), TaskError> {
    python_run(
        &options.python_exe,
        Command::new(&options.python_exe)
            .current_dir(root)
            .args(["-E", "-s", "-B"])
            .arg(root.join("deps/scripts/validate_bytecode_metadata.py"))
            .arg("--payload")
            .arg(prefix.join("awscli-v2.blob"))
            .arg("--runtime")
            .arg(prefix.join("runtime.pyc"))
            .arg("--metadata")
            .arg(prefix.join("python-bytecode-metadata.json"))
            .args(["--expected-magic", magic])
            .arg("--stamp")
            .arg(prefix.join("python-bytecode-validated.stamp")),
    )
}

#[cfg(test)]
mod tests;
