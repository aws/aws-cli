//! The compiler-rt profile runtime of a Linux PGO build and the tools that use it.

use super::stage::{complete, driver, finish, stage_prefix, stage_work};
use crate::deps::{self, Pins, Roots, Toolchain};
use crate::{TaskError, process};
use std::fs;
use std::path::{Path, PathBuf};

/// The profile merger and instrumentation runtime of a Linux PGO interpreter
/// build.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfileTools {
    pub llvm_profdata: PathBuf,
    pub profile_runtime: PathBuf,
}

impl ProfileTools {
    /// The toolchain's merger and the compiler-rt runtime built by `profile`.
    pub fn managed(root: &Path, pins: &Pins, tools: &Toolchain) -> Result<Self, TaskError> {
        Ok(Self {
            llvm_profdata: tools.llvm_profdata.clone(),
            profile_runtime: profile(root, pins, tools)?,
        })
    }
}

/// The stage label, which names the prefix and the work directory.
const LABEL: &str = "profile";

/// The prefix `profile` builds for `tools`, keyed without building it.
fn prefix(root: &Path, tools: &Toolchain) -> Result<PathBuf, TaskError> {
    stage_prefix(root, LABEL, tools, &[])
}

/// The profile stage's prefix and scratch directory for `tools`.
pub(super) fn roots(root: &Path, tools: &Toolchain) -> Result<Roots, TaskError> {
    let mut roots = Roots::default();
    roots.insert(LABEL, prefix(root, tools)?);
    roots.insert_work(root, stage_work(root, LABEL));
    Ok(roots)
}

/// Build compiler-rt's native musl profile runtime for the toolchain self-test.
pub fn profile(root: &Path, pins: &Pins, tools: &Toolchain) -> Result<PathBuf, TaskError> {
    let prefix = prefix(root, tools)?;
    let _lock = deps::lock_stage(&prefix)?;
    let output = "lib/libclang_rt.profile-musl.a";
    if !complete(&prefix, &[output]) {
        let source = deps::source(root, pins, "compiler_rt_source")?;
        fs::create_dir_all(&prefix)?;
        // The driver's stamp names `cc --version`, not the wrapper's sysroot
        // and flags, so a toolchain key that keeps the LLVM pin would reuse
        // an archive built against the old musl: another key's scratch is
        // emptied instead.
        let work = stage_work(root, LABEL);
        let _work_lock = deps::claim_work(&work, &prefix)?;
        process::run(
            driver(root, "build_pgo_tools.py", tools)
                .arg("--llvm-profdata")
                .arg(&tools.llvm_profdata)
                .arg("--llvm-version")
                .arg(&tools.version)
                .arg("--compiler-rt-source")
                .arg(source)
                .arg("--cache-dir")
                .arg(&work)
                .arg("--profile-runtime-output")
                .arg(prefix.join(output)),
        )?;
        finish(&prefix, &[output])?;
    }
    Ok(prefix.join(output))
}
