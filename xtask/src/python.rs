//! Build the static interpreter, support libraries, profile runtime, and payload.
//!
//! Each stage's build code lives in its own module, so a stage keys only on
//! the code that builds it (see `deps::inputs::stage_files`): `stage` holds
//! what every Python stage runs through, `profile`, `support`, and
//! `interpreter` build the stages they are named for, and `fallback` packs the
//! payload. This file only sequences them, so no stage keys on it.

use crate::TaskError;
use crate::deps::{CpythonLibraries, Pins, Roots, Toolchain};
use std::path::{Path, PathBuf};

mod fallback;
mod interpreter;
mod profile;
mod stage;
mod support;

pub use self::fallback::{FallbackInputs, fallback};
#[cfg(test)]
pub(crate) use self::interpreter::interpreter_key;
pub use self::interpreter::{PYTHON_ABI, interpreter};
pub use self::profile::{ProfileTools, profile};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PythonOutputs {
    pub cpython: PathBuf,
    pub fallback: PathBuf,
}

/// Build every Python dependency and return the prefixes consumed by the
/// link: the interpreter against the managed OpenSSL and zlib/xz, and the
/// fallback against the interpreter and the `crt`'s headers.
pub fn build(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    crt: &Path,
    pgo: bool,
) -> Result<PythonOutputs, TaskError> {
    let libraries = CpythonLibraries::managed(root, tools)?;
    let cpython = interpreter(root, pins, tools, &libraries, pgo, None)?;
    let fallback = fallback(
        root,
        pins,
        tools,
        &FallbackInputs {
            crt,
            cpython: &cpython,
            runtime_source: &runtime_source(root),
            pgo,
        },
    )?;
    Ok(PythonOutputs { cpython, fallback })
}

/// The runtime bootstrap the product's fallback compiles.
fn runtime_source(root: &Path) -> PathBuf {
    root.join("crates/python-fallback/python/runtime.py")
}

/// Every root of the Python stages `build` used for `outputs`: the support,
/// interpreter, and fallback prefixes and the scratch directories of `pgo`.
///
/// The keys are recomputed, never built: each is named by the toolchain
/// digest, the stage's own inputs, and the prefix paths of the stages it
/// follows.
pub fn roots(
    root: &Path,
    tools: &Toolchain,
    crt: &Path,
    pgo: bool,
    outputs: &PythonOutputs,
) -> Result<Roots, TaskError> {
    let mut roots = support::roots(root, tools)?;
    roots.extend(interpreter::roots(root, &outputs.cpython, pgo));
    roots.extend(fallback::roots(
        root,
        tools,
        &FallbackInputs {
            crt,
            cpython: &outputs.cpython,
            runtime_source: &runtime_source(root),
            pgo,
        },
    )?);
    Ok(roots)
}

/// The profile stage's roots. The Linux toolchain's self-test builds the
/// stage, so they belong to the toolchain whether or not CPython uses PGO.
pub fn profile_roots(root: &Path, tools: &Toolchain) -> Result<Roots, TaskError> {
    profile::roots(root, tools)
}

#[cfg(test)]
mod tests;
