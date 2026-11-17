//! The static support libraries CPython's extension modules link.

use super::stage::{complete, driver, finish, stage_prefix, stage_work};
use crate::deps::{self, Pins, Roots, Toolchain};
use crate::{TaskError, process};
use std::fs;
use std::path::{Path, PathBuf};

/// The stage label, which names the prefix and the work directory.
const LABEL: &str = "python-support";

/// The prefix `support` builds for `tools`, keyed without building it.
fn prefix(root: &Path, tools: &Toolchain) -> Result<PathBuf, TaskError> {
    stage_prefix(root, LABEL, tools, &[])
}

/// The support stage's prefix and scratch directory for `tools`.
///
/// They are roots even where a cached interpreter was reused without them,
/// so the next interpreter key, after a CRT bump, finds them built.
pub(super) fn roots(root: &Path, tools: &Toolchain) -> Result<Roots, TaskError> {
    let mut roots = Roots::default();
    roots.insert(LABEL, prefix(root, tools)?);
    roots.insert_work(root, stage_work(root, LABEL));
    Ok(roots)
}

/// Build the support archives into their own prefix, which the interpreter
/// stage builds against and then merges into its own.
pub(super) fn support(root: &Path, pins: &Pins, tools: &Toolchain) -> Result<PathBuf, TaskError> {
    let prefix = prefix(root, tools)?;
    let outputs = [
        "lib/libsqlite3.a",
        "lib/libbz2.a",
        "lib/libffi.a",
        "lib/libzstd.a",
    ];
    let _lock = deps::lock_stage(&prefix)?;
    if !complete(&prefix, &outputs) {
        fs::create_dir_all(&prefix)?;
        // The driver builds each library in a fresh copy of its source, so
        // another key's scratch is never reused.
        let work = stage_work(root, LABEL);
        let mut command = driver(root, "build_python_deps.py", tools);
        command
            .arg("--prefix")
            .arg(&prefix)
            .arg("--cache-dir")
            .arg(&work)
            .arg("--stamp")
            .arg(prefix.join(".support-stamp"));
        for name in ["sqlite", "bzip2", "libffi", "zstd"] {
            command
                .arg(format!("--{name}-source"))
                .arg(deps::source(root, pins, name)?);
        }
        let _work_lock = deps::lock_stage(&work)?;
        process::run(&mut command)?;
        finish(&prefix, &outputs)?;
    }
    Ok(prefix)
}
