//! Static zlib and xz, built as their own stage before the CPython and CRT
//! that link them.
//!
//! CPython's `zlib` and `_lzma` modules link them, and the CRT publishes
//! them for the product's link, but no AWS C library builds against them.
//! The stage keys only on their pins, this builder, the CMake driver, the
//! toolchain digest, and CMake, so an AWS C library bump rebuilds the CRT
//! against the cached prefix, and CPython, which keys on this prefix and
//! OpenSSL's rather than the CRT's, is reused.

use std::fs;
use std::path::{Path, PathBuf};

use super::super::{
    Pins, Result, Roots, TARGET, Toolchain, claim_work, digest, error, files, guard, lock_stage,
    platform, source, work_dir,
};
use super::cmake::{Build, MARKERS, Project, installed_marker, mark_installed};

/// The stage label, which names the prefix, the work directory, and the
/// builder guard.
const LABEL: &str = "zlib-xz";

/// The directories of the prefix the CRT links into its own: the archives
/// and headers, and their pkg-config and CMake package files.
pub(super) const OUTPUTS: &[&str] = &["include", "lib", "share"];

/// xz's configure arguments: only the static library, without the tools,
/// their documentation, or translations.
const XZ_ARGUMENTS: &[&str] = &[
    "-DXZ_NLS=OFF",
    "-DXZ_DOC=OFF",
    "-DXZ_TOOL_XZ=OFF",
    "-DXZ_TOOL_XZDEC=OFF",
    "-DXZ_TOOL_LZMADEC=OFF",
    "-DXZ_TOOL_LZMAINFO=OFF",
    "-DXZ_TOOL_SCRIPTS=OFF",
];

/// The zlib/xz stage's key and the prefix that key names.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Stage {
    pub(super) prefix: PathBuf,
    pub(super) key: String,
}

impl Stage {
    /// Key the stage for `tools` without building it, so a cached CRT or
    /// interpreter can key on this prefix even where the prefix itself is
    /// gone.
    pub(super) fn new(root: &Path, tools: &Toolchain) -> Result<Self> {
        let key = digest(root, LABEL, &[tools.digest.as_bytes()])?;
        let prefix = super::super::store(root)
            .join("deps")
            .join(TARGET)
            .join(format!("{LABEL}-{key}"));
        Ok(Self { prefix, key })
    }

    /// Build the prefix unless it is complete, resuming after the projects
    /// an interrupted build installed.
    ///
    /// Callers may hold the CRT's or the interpreter's stage lock, and
    /// OpenSSL's: zlib/xz's is taken after them, and no stage takes them in
    /// another order.
    pub(super) fn build(&self, root: &Path, pins: &Pins, tools: &Toolchain) -> Result<()> {
        let prefix = &self.prefix;
        let _lock = lock_stage(prefix)?;
        if cached(prefix)? {
            return Ok(());
        }
        guard(LABEL)?;
        fs::create_dir_all(prefix)?;
        {
            // As the CRT's: the CMake trees stay out of the published
            // prefix, and since every command line names this prefix,
            // another key's trees are emptied, not reused.
            let work = scratch(root);
            let _work_lock = claim_work(&work, prefix)?;
            let build = Build {
                prefix,
                work: &work,
            };
            zlib(root, pins, tools, &build)?;
            xz(root, pins, tools, &build)?;
        }
        validate(prefix)?;
        fs::write(prefix.join(".complete"), &self.key)?;
        Ok(())
    }
}

/// The stage's scratch directory, which holds the CMake trees of one key.
fn scratch(root: &Path) -> PathBuf {
    work_dir(root, TARGET, LABEL)
}

/// The zlib/xz `prefix` and the stage's scratch directory.
pub(super) fn roots(root: &Path, prefix: &Path) -> Roots {
    let mut roots = Roots::default();
    roots.insert(LABEL, prefix.to_owned());
    roots.insert_work(root, scratch(root));
    roots
}

/// Whether `prefix` is a complete build, validated for reuse.
fn cached(prefix: &Path) -> Result<bool> {
    if !prefix.join(".complete").is_file() {
        return Ok(false);
    }
    validate(prefix)?;
    Ok(true)
}

/// Build zlib's static archive into the stage unless it is installed.
fn zlib(root: &Path, pins: &Pins, tools: &Toolchain, build: &Build<'_>) -> Result<()> {
    let name = "zlib";
    if installed_marker(build.prefix, name).exists() {
        return Ok(());
    }
    guard(&format!("{LABEL}-cmake-{name}"))?;
    let input = source(root, pins, name)?;
    let project = Project {
        name,
        source: &input,
        target: "zlibstatic",
    };
    let tree = build.run(root, tools, &project, &["-DZLIB_BUILD_EXAMPLES=OFF"])?;
    install_zlib(&input, &tree, build.prefix)?;
    mark_installed(build.prefix, name)
}

/// zlib builds only its static target, which has no install rule: copy the
/// archive, headers and pkg-config file into the prefix by hand.
fn install_zlib(input: &Path, build: &Path, prefix: &Path) -> Result<()> {
    // Only scratch artifacts are pruned. Shared files in the installed
    // prefix still fail validation, including files from another project.
    files::prune_matching(build, "libz.so*")?;
    files::prune_matching(build, "libz*.dylib")?;
    for (source, relative) in [
        (
            // zlib 1.3.2 names its Windows static archive `zs.lib`, while
            // the linker looks for `z.lib`, so it is installed as `z.lib`.
            build.join(if cfg!(windows) { "zs.lib" } else { "libz.a" }),
            if cfg!(windows) {
                "lib/z.lib"
            } else {
                "lib/libz.a"
            },
        ),
        (input.join("zlib.h"), "include/zlib.h"),
        (build.join("zconf.h"), "include/zconf.h"),
        (build.join("zlib.pc"), "share/pkgconfig/zlib.pc"),
    ] {
        let destination = prefix.join(relative);
        if let Some(parent) = destination.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::copy(source, destination)?;
    }
    Ok(())
}

/// Build and install liblzma into the stage unless it is installed.
fn xz(root: &Path, pins: &Pins, tools: &Toolchain, build: &Build<'_>) -> Result<()> {
    let name = "xz";
    if installed_marker(build.prefix, name).exists() {
        return Ok(());
    }
    guard(&format!("{LABEL}-cmake-{name}"))?;
    let input = source(root, pins, name)?;
    let project = Project {
        name,
        source: &input,
        target: "install",
    };
    build.run(root, tools, &project, XZ_ARGUMENTS)?;
    if cfg!(windows) {
        // As zlib's archive, the linker looks for `lzma.lib`.
        let input = build.prefix.join("lib/liblzma.lib");
        if input.is_file() {
            fs::rename(input, build.prefix.join("lib/lzma.lib"))?;
        }
    }
    mark_installed(build.prefix, name)
}

/// Require the archives and headers CPython and the CRT read, and nothing
/// outside `OUTPUTS`, the only trees the CRT links, but the stage's markers:
/// whatever else an install added would silently be missing from the CRT
/// prefix.
fn validate(prefix: &Path) -> Result<()> {
    for entry in fs::read_dir(prefix)? {
        let name = entry?.file_name();
        if name != ".complete" && name != MARKERS && !OUTPUTS.iter().any(|output| name == *output) {
            return Err(error(format!(
                "zlib/xz prefix {} has {}, which the CRT does not publish",
                prefix.display(),
                name.to_string_lossy()
            )));
        }
    }
    let mut required = vec![prefix.join("include/zlib.h"), prefix.join("include/lzma.h")];
    for name in ["z", "lzma"] {
        required.push(
            prefix
                .join("lib")
                .join(platform::archive_name(std::env::consts::OS, name)),
        );
    }
    for path in required {
        if !path.is_file() {
            return Err(error(format!("zlib/xz prefix lacks {}", path.display())));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests;
