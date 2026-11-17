//! The static CPython interpreter, built against OpenSSL, zlib, xz, and the
//! support archives.

use super::profile::ProfileTools;
use super::stage::{complete, driver, finish, pgo_work, stage_prefix};
use super::support::support;
use crate::deps::{self, CpythonLibraries, Pins, Roots, Toolchain};
use crate::{TaskError, process};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// The embedded CPython's ABI name: "python" and the major.minor of
/// deps/pins.toml `python_version`, which `cargo xtask check-pins` requires it
/// to name. A macro so the interpreter outputs below stay constants.
macro_rules! python_abi {
    () => {
        "python3.14"
    };
}

/// The embedded CPython's ABI name, such as "python3.14": its include
/// directory, library and executable.
pub const PYTHON_ABI: &str = python_abi!();

/// Whether an interpreter build trains on the AWS CLI. Only Linux PGO does,
/// with the managed profile tools; macOS PGO keeps CPython's own workload
/// until it has native measurements.
fn trains_on_cli(pgo: bool) -> bool {
    pgo && cfg!(target_os = "linux")
}

/// Build the managed interpreter and support archives independently of a
/// payload, against `libraries`, which are built first only if the
/// interpreter must be. `profile_tools` replaces the managed merger and
/// profile runtime of a Linux PGO build and then also keys the stage; `None`
/// keeps the managed tools.
pub fn interpreter(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    libraries: &CpythonLibraries,
    pgo: bool,
    profile_tools: Option<&ProfileTools>,
) -> Result<PathBuf, TaskError> {
    let cli_trained = trains_on_cli(pgo);
    // The tools apply only to a build that trains on the CLI.
    let profile_tools = profile_tools.filter(|_| cli_trained);
    let key = interpreter_key(
        pgo,
        [libraries.openssl(), libraries.zlib_xz()],
        profile_tools,
    );
    let prefix = stage_prefix(root, "cpython", tools, &key)?;
    let _lock = deps::lock_stage(&prefix)?;
    if !interpreter_complete(&prefix) {
        libraries.build(root, pins, tools)?;
        let support = support(root, pins, tools)?;
        let source = deps::source(root, pins, "cpython")?;
        fs::create_dir_all(&prefix)?;
        // The driver empties its build tree on every build and maps the
        // directory to a logical path, so neither another key's tree nor the
        // location reaches the interpreter.
        let work = scratch(root, pgo);
        let mut command = driver(root, "build_cpython.py", tools);
        command
            .arg("--ld")
            .arg(&tools.ld_lld)
            .arg("--python-version")
            .arg(pins.version("python_version")?)
            .arg("--prefix")
            .arg(&prefix)
            .arg("--openssl-prefix")
            .arg(libraries.openssl())
            .arg("--zlib-xz-prefix")
            .arg(libraries.zlib_xz())
            .arg("--deps-prefix")
            .arg(&support)
            .arg("--cache-dir")
            .arg(&work)
            .arg("--source-dir")
            .arg(source)
            .arg(if pgo { "--pgo" } else { "--no-pgo" });
        // Only Linux PGO receives the profile tools and the training source.
        if cli_trained {
            train_on_cli(&mut command, root, pins, tools, profile_tools)?;
        }
        // Taken once the library, support, and profile stages are built, so
        // no other stage's lock is awaited while the scratch is held.
        let _work_lock = deps::lock_stage(&work)?;
        process::run(&mut command)?;
        // Consumers expect support archives beside libpython, so the support
        // stage's `include` and `lib` trees are merged into this prefix.
        for directory in ["include", "lib"] {
            deps::copy_tree(
                &support.join(directory),
                &prefix.join(directory),
                deps::CopyMode::Merge,
            )?;
        }
        finish_interpreter(&prefix)?;
    }
    Ok(prefix)
}

/// The interpreter's scratch directory in PGO mode `pgo`.
fn scratch(root: &Path, pgo: bool) -> PathBuf {
    pgo_work(root, "cpython", pgo)
}

/// The interpreter `prefix` built in PGO mode `pgo`, and that mode's
/// scratch directory.
pub(super) fn roots(root: &Path, prefix: &Path, pgo: bool) -> Roots {
    let mut roots = Roots::default();
    roots.insert("cpython", prefix.to_owned());
    roots.insert_work(root, scratch(root, pgo));
    roots
}

/// The interpreter stage's extra key: the PGO mode, the prefixes it reads
/// OpenSSL and then zlib and xz from, then the paths of any selected profile
/// tools, so the managed tools keep their key unchanged.
///
/// Each library prefix carries its stage's key into this one. The CRT's own
/// prefix keys no interpreter, so an AWS C library bump, which changes only
/// the CRT, reuses it.
pub(crate) fn interpreter_key<'a>(
    pgo: bool,
    libraries: [&'a Path; 2],
    profile_tools: Option<&'a ProfileTools>,
) -> Vec<&'a [u8]> {
    let mut key: Vec<&[u8]> = vec![if pgo { b"pgo" } else { b"no-pgo" }];
    key.extend(
        libraries
            .iter()
            .map(|prefix| prefix.as_os_str().as_encoded_bytes()),
    );
    if let Some(selected) = profile_tools {
        key.push(selected.llvm_profdata.as_os_str().as_encoded_bytes());
        key.push(selected.profile_runtime.as_os_str().as_encoded_bytes());
    }
    key
}

/// Add a Linux PGO build's profile tools, `selected` or else the managed
/// ones, and the AWS CLI source its training workload runs.
fn train_on_cli(
    command: &mut Command,
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    selected: Option<&ProfileTools>,
) -> Result<(), TaskError> {
    let managed;
    let selected = match selected {
        Some(selected) => selected,
        None => {
            managed = ProfileTools::managed(root, pins, tools)?;
            &managed
        }
    };
    command
        .arg("--llvm-profdata")
        .arg(&selected.llvm_profdata)
        .arg("--profile-runtime")
        .arg(&selected.profile_runtime)
        .arg("--aws-cli-source")
        .arg(deps::aws_cli_source(root)?);
    Ok(())
}

const CPYTHON_OUTPUTS: &[&str] = &[
    if cfg!(windows) {
        concat!("bin/", python_abi!(), ".exe")
    } else {
        concat!("bin/", python_abi!())
    },
    concat!("lib/lib", python_abi!(), ".a"),
    concat!("include/", python_abi!(), "/pyconfig.h"),
    concat!("lib/", python_abi!(), "-inittab.c"),
    "lib/libsqlite3.a",
    "lib/libbz2.a",
    "lib/libffi.a",
    "lib/libzstd.a",
];

/// The normalized sysconfig copies only the payload packs. The packer rejects
/// a prefix without them, so a prefix missing them is never reused.
const PAYLOAD_SYSCONFIG: &str = "lib/payload-sysconfig";

fn interpreter_complete(prefix: &Path) -> bool {
    complete(prefix, CPYTHON_OUTPUTS) && prefix.join(PAYLOAD_SYSCONFIG).is_dir()
}

fn finish_interpreter(prefix: &Path) -> Result<(), TaskError> {
    if !prefix.join(PAYLOAD_SYSCONFIG).is_dir() {
        return Err(TaskError::Message(format!(
            "dependency build omitted {}",
            prefix.join(PAYLOAD_SYSCONFIG).display()
        )));
    }
    finish(prefix, CPYTHON_OUTPUTS)
}

#[cfg(test)]
mod tests;
