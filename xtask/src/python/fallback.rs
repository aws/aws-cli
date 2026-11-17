//! Pack the embedded payload: the interpreter archive, the AWS CLI blob, and the runtime.

use super::PYTHON_ABI;
use super::stage::{complete, driver, finish, pgo_work, stage_prefix};
use crate::deps::{self, Pins, Roots, Toolchain};
use crate::{TaskError, process};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// The interpreter registration sources and the archive of interpreter and
/// awscrt objects, which no AWS CLI or runtime bootstrap edit changes.
const ARCHIVE_OUTPUTS: &[&str] = &["inittab.c", "frozen_bootstrap.c", "python-fallback.a"];

/// The packed AWS CLI payload.
const PAYLOAD_BLOB: &str = "awscli-v2.blob";

/// The compiled runtime bootstrap and the configuration checked against the payload.
const RUNTIME_OUTPUTS: &[&str] = &[
    "runtime.pyc",
    "python-bytecode-metadata.json",
    "python_config.rs",
];

/// Prepared dependencies and application bootstrap selected by a payload consumer.
pub struct FallbackInputs<'a> {
    pub crt: &'a Path,
    pub cpython: &'a Path,
    pub runtime_source: &'a Path,
    pub pgo: bool,
}

/// Pack a bootstrap against prepared managed interpreter and CRT outputs.
///
/// The archive, payload, and runtime are separate stages, each keyed on its
/// own inputs: an AWS CLI edit repacks only the payload and recompiles the
/// runtime against it, and a runtime bootstrap edit reuses both the archive
/// and the payload. The returned prefix links every output into the one
/// directory the consumers read.
pub fn fallback(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    inputs: &FallbackInputs<'_>,
) -> Result<PathBuf, TaskError> {
    let Prefixes {
        archive,
        payload,
        runtime,
        published: prefix,
    } = Prefixes::new(root, tools, inputs)?;
    fallback_archive(root, pins, tools, inputs, &archive)?;
    fallback_payload(root, pins, tools, inputs, &payload)?;
    fallback_runtime(root, tools, inputs, &payload, &runtime)?;
    let outputs = fallback_outputs();
    let _lock = deps::lock_stage(&prefix)?;
    if !complete(&prefix, &outputs) {
        fs::create_dir_all(&prefix)?;
        for (stage, names) in [
            (&archive, ARCHIVE_OUTPUTS),
            (&payload, &[PAYLOAD_BLOB]),
            (&runtime, RUNTIME_OUTPUTS),
        ] {
            for name in names {
                link_output(&stage.join(name), &prefix.join(name))?;
            }
        }
        finish(&prefix, &outputs)?;
    }
    Ok(prefix)
}

/// The prefixes of the fallback stages for one set of inputs.
struct Prefixes {
    archive: PathBuf,
    payload: PathBuf,
    runtime: PathBuf,
    published: PathBuf,
}

impl Prefixes {
    /// Key every fallback stage for `inputs` without building any: each key
    /// names only the inputs and the prefix paths of the stages before it.
    fn new(root: &Path, tools: &Toolchain, inputs: &FallbackInputs<'_>) -> Result<Self, TaskError> {
        let archive = stage_prefix(root, "fallback-archive", tools, &archive_key(inputs))?;
        let payload = stage_prefix(root, "fallback-payload", tools, &fallback_key(inputs))?;
        let runtime_source = fs::read(inputs.runtime_source)?;
        let key = runtime_key(inputs, &payload, &runtime_source);
        let runtime = stage_prefix(root, "fallback-runtime", tools, &key)?;
        let published = stage_prefix(
            root,
            "fallback",
            tools,
            &[
                archive.as_os_str().as_encoded_bytes(),
                payload.as_os_str().as_encoded_bytes(),
                runtime.as_os_str().as_encoded_bytes(),
            ],
        )?;
        Ok(Self {
            archive,
            payload,
            runtime,
            published,
        })
    }
}

/// Every fallback stage's prefix for `inputs`, and the scratch directories
/// of the archive and payload in its PGO mode. The runtime and the
/// published prefix build in no scratch.
pub(super) fn roots(
    root: &Path,
    tools: &Toolchain,
    inputs: &FallbackInputs<'_>,
) -> Result<Roots, TaskError> {
    let prefixes = Prefixes::new(root, tools, inputs)?;
    let mut roots = Roots::default();
    roots.insert("fallback-archive", prefixes.archive);
    roots.insert_work(root, archive_scratch(root, inputs.pgo));
    roots.insert("fallback-payload", prefixes.payload);
    roots.insert_work(root, payload_scratch(root, inputs.pgo));
    roots.insert("fallback-runtime", prefixes.runtime);
    roots.insert("fallback", prefixes.published);
    Ok(roots)
}

/// The archive's scratch directory in PGO mode `pgo`.
fn archive_scratch(root: &Path, pgo: bool) -> PathBuf {
    pgo_work(root, "fallback-archive", pgo)
}

/// The payload's scratch directory in PGO mode `pgo`.
fn payload_scratch(root: &Path, pgo: bool) -> PathBuf {
    pgo_work(root, "fallback-payload", pgo)
}

/// Every output of the published fallback prefix.
fn fallback_outputs() -> Vec<&'static str> {
    let mut outputs = ARCHIVE_OUTPUTS.to_vec();
    outputs.push(PAYLOAD_BLOB);
    outputs.extend_from_slice(RUNTIME_OUTPUTS);
    outputs
}

/// The extra key every fallback stage shares: the PGO mode and the
/// interpreter prefix every phase runs.
fn fallback_key<'a>(inputs: &'a FallbackInputs<'_>) -> Vec<&'a [u8]> {
    vec![
        if inputs.pgo { b"pgo" } else { b"no-pgo" },
        inputs.cpython.as_os_str().as_encoded_bytes(),
    ]
}

/// The archive's extra key: the shared key and the CRT prefix, whose headers
/// compile the awscrt objects. Only the archive reads the CRT, so the payload
/// and runtime keep their keys across a CRT rebuild that leaves the
/// interpreter prefix unchanged.
fn archive_key<'a>(inputs: &'a FallbackInputs<'_>) -> Vec<&'a [u8]> {
    let mut key = fallback_key(inputs);
    key.push(inputs.crt.as_os_str().as_encoded_bytes());
    key
}

/// Generate the registration sources and archive the interpreter and
/// awscrt objects into `prefix`.
fn fallback_archive(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    inputs: &FallbackInputs<'_>,
    prefix: &Path,
) -> Result<(), TaskError> {
    let _lock = deps::lock_stage(prefix)?;
    if !complete(prefix, ARCHIVE_OUTPUTS) {
        // The driver regenerates its object lists and recompiles every
        // awscrt object it archives, so another key's scratch is never read.
        let work = archive_scratch(root, inputs.pgo);
        let _work_lock = deps::lock_stage(&work)?;
        fs::create_dir_all(prefix)?;
        let mut command = fallback_driver(root, tools, inputs, "archive");
        command
            .arg("--cache-dir")
            .arg(&work)
            .arg("--awscrt-version")
            .arg(pins.version("awscrt_version")?)
            .arg("--awscrt-source")
            .arg(deps::source(root, pins, "awscrt")?)
            .arg("--crt-include-dir")
            .arg(inputs.crt.join("include"));
        for (flag, script) in [
            ("gen-inittab", "gen_inittab.py"),
            ("gen-frozen-bootstrap", "gen_frozen_bootstrap.py"),
        ] {
            command
                .arg(format!("--{flag}"))
                .arg(root.join("deps/scripts").join(script));
        }
        for (flag, output) in [
            ("inittab", "inittab.c"),
            ("frozen-bootstrap", "frozen_bootstrap.c"),
            ("object-file", "python-fallback.a"),
        ] {
            command.arg(format!("--{flag}")).arg(prefix.join(output));
        }
        process::run(&mut command)?;
        finish(prefix, ARCHIVE_OUTPUTS)?;
    }
    Ok(())
}

/// Pack the AWS CLI, its runtime dependencies, and the autocomplete index
/// into `prefix`.
fn fallback_payload(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    inputs: &FallbackInputs<'_>,
    prefix: &Path,
) -> Result<(), TaskError> {
    let _lock = deps::lock_stage(prefix)?;
    if !complete(prefix, &[PAYLOAD_BLOB]) {
        // The packing venv depends only on the runtime lock and interpreter,
        // which its own marker records, so it outlives any one payload key.
        let work = payload_scratch(root, inputs.pgo);
        let _work_lock = deps::lock_stage(&work)?;
        fs::create_dir_all(prefix)?;
        let mut command = fallback_driver(root, tools, inputs, "payload");
        command
            .arg("--cache-dir")
            .arg(&work)
            .arg("--awscrt-version")
            .arg(pins.version("awscrt_version")?)
            .arg("--awscrt-source")
            .arg(deps::source(root, pins, "awscrt")?)
            .arg("--aws-cli-version")
            .arg(deps::aws_cli_version(root)?)
            .arg("--aws-cli-source")
            .arg(deps::aws_cli_source(root)?)
            .arg("--requirements")
            .arg(deps::aws_cli_runtime_lock(root)?);
        for (flag, script) in [
            ("pack-tool", "pack.py"),
            ("gen-ac-index", "gen_ac_index.py"),
        ] {
            command
                .arg(format!("--{flag}"))
                .arg(root.join("deps/scripts").join(script));
        }
        command.arg("--blob").arg(prefix.join(PAYLOAD_BLOB));
        process::run(&mut command)?;
        finish(prefix, &[PAYLOAD_BLOB])?;
    }
    Ok(())
}

/// The runtime's extra key: the shared key, the payload prefix it checks
/// the configuration against, and the bootstrap source the caller selected.
fn runtime_key<'a>(
    inputs: &'a FallbackInputs<'_>,
    payload: &'a Path,
    runtime_source: &'a [u8],
) -> Vec<&'a [u8]> {
    let mut key = fallback_key(inputs);
    key.push(payload.as_os_str().as_encoded_bytes());
    key.push(runtime_source);
    key
}

/// Compile the runtime bootstrap into `prefix` and record the configuration
/// checked against `payload`.
fn fallback_runtime(
    root: &Path,
    tools: &Toolchain,
    inputs: &FallbackInputs<'_>,
    payload: &Path,
    prefix: &Path,
) -> Result<(), TaskError> {
    let blob = payload.join(PAYLOAD_BLOB);
    let _lock = deps::lock_stage(prefix)?;
    if !complete(prefix, RUNTIME_OUTPUTS) {
        fs::create_dir_all(prefix)?;
        let mut command = fallback_driver(root, tools, inputs, "runtime");
        command
            .arg("--blob")
            .arg(&blob)
            .arg("--runtime-source")
            .arg(inputs.runtime_source);
        for (flag, output) in [
            ("runtime-bytecode", "runtime.pyc"),
            ("metadata", "python-bytecode-metadata.json"),
            ("python-config", "python_config.rs"),
        ] {
            command.arg(format!("--{flag}")).arg(prefix.join(output));
        }
        process::run(&mut command)?;
        finish(prefix, RUNTIME_OUTPUTS)?;
    }
    Ok(())
}

/// The packing driver's command for `phase`, after the options every phase reads.
fn fallback_driver(
    root: &Path,
    tools: &Toolchain,
    inputs: &FallbackInputs<'_>,
    phase: &str,
) -> Command {
    let mut command = driver(root, "prepare_python_fallback.py", tools);
    command
        .arg("--python-root")
        .arg(inputs.cpython)
        .args(["--python-abi", PYTHON_ABI, phase]);
    command
}

/// Place a stage `output` at `destination`: a hard link, as both sit in the
/// dependency store, or a copy where the filesystem refuses one.
fn link_output(output: &Path, destination: &Path) -> Result<(), TaskError> {
    if destination.exists() {
        fs::remove_file(destination)?;
    }
    if fs::hard_link(output, destination).is_err() {
        fs::copy(output, destination)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests;
