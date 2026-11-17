//! Static CRT prefix built with the verified native wrappers.

use std::fs;
use std::path::{Path, PathBuf};

use super::files;
use super::{
    Pins, Result, Roots, TARGET, Toolchain, claim_work, digest, error, guard, source, work_dir,
};

use self::cmake::{Build, Project};
pub(super) use self::cmake::{installed_marker, mark_installed};

mod cmake;
mod openssl;
mod source_paths;
mod zlib_xz;

const PROJECTS: &[(&str, &str)] = &[
    ("s2n-tls", "s2n_tls"),
    ("aws-c-common", "aws_c_common"),
    ("aws-checksums", "aws_checksums"),
    ("aws-c-cal", "aws_c_cal"),
    ("aws-c-io", "aws_c_io"),
    ("aws-c-compression", "aws_c_compression"),
    ("aws-c-event-stream", "aws_c_event_stream"),
    ("aws-c-http", "aws_c_http"),
    ("aws-c-mqtt", "aws_c_mqtt"),
    ("aws-c-sdkutils", "aws_c_sdkutils"),
    ("aws-c-auth", "aws_c_auth"),
    ("aws-c-s3", "aws_c_s3"),
];

/// Build, or reuse, the static CRT prefix: the AWS C libraries, built
/// against OpenSSL and published with OpenSSL, zlib, and xz.
///
/// OpenSSL and zlib/xz are their own stages, so an AWS C library bump
/// reuses them, and CPython, which links them rather than the CRT, keeps its
/// key. The CRT keys on both stages' keys, as `crt_key` describes, and builds
/// them only when the CRT itself must be built: a cached CRT is reused even
/// where their prefixes have since been removed.
pub fn crt(root: &Path, pins: &Pins, tools: &Toolchain) -> Result<PathBuf> {
    let openssl = openssl::Stage::new(root, tools)?;
    let zlib_xz = zlib_xz::Stage::new(root, tools)?;
    let hash = digest(
        root,
        "crt",
        &crt_key(&tools.digest, &openssl.key, &zlib_xz.key),
    )?;
    let prefix = super::store(root)
        .join("deps")
        .join(TARGET)
        .join(format!("crt-{hash}"));
    let _lock = super::lock_stage(&prefix)?;
    if prefix.join(".complete").is_file() {
        validate(root, &prefix)?;
        return Ok(prefix);
    }
    guard("crt")?;
    openssl.build(root, pins, tools)?;
    zlib_xz.build(root, pins, tools)?;
    fs::create_dir_all(&prefix)?;
    // Consumers such as crt-sys, python-fallback, and the crt-libraries.txt
    // check read OpenSSL, zlib, and xz from the CRT prefix, and the AWS C
    // libraries find OpenSSL there through the hints in `arguments`. As the
    // fallback stage publishes its phases, the prefix links the stages'
    // outputs rather than copying them; no CRT project installs a file of
    // the same name, so none writes through a link into their prefixes.
    for (stage, outputs) in [
        (&openssl.prefix, openssl::OUTPUTS),
        (&zlib_xz.prefix, zlib_xz::OUTPUTS),
    ] {
        for output in outputs {
            files::link_tree(&stage.join(output), &prefix.join(output))?;
        }
    }
    {
        // The CMake trees stay out of the published prefix, and since every
        // command line names this prefix, another key's trees are emptied,
        // not reused.
        let work = scratch(root);
        let _work_lock = claim_work(&work, &prefix)?;
        let build = Build {
            prefix: &prefix,
            work: &work,
        };
        for &(name, source_name) in PROJECTS {
            if cfg!(windows) && name == "s2n-tls" {
                continue;
            }
            project(root, pins, tools, &build, name, source_name)?;
        }
    }
    validate(root, &prefix)?;
    fs::write(prefix.join(".complete"), hash)?;
    Ok(prefix)
}

/// The CRT's scratch directory, which holds the CMake trees of one key.
fn scratch(root: &Path) -> PathBuf {
    work_dir(root, TARGET, "crt")
}

/// The roots of the CRT at `prefix`: its prefix, the OpenSSL and zlib/xz
/// prefixes it was keyed on, and the scratch directories of all three.
///
/// The OpenSSL and zlib/xz prefixes are roots even where a cached CRT was
/// reused without them, so the next CRT key, after an AWS C library bump,
/// finds them built.
pub(super) fn roots(root: &Path, tools: &Toolchain, prefix: &Path) -> Result<Roots> {
    let openssl = openssl::Stage::new(root, tools)?;
    let zlib_xz = zlib_xz::Stage::new(root, tools)?;
    Ok(stage_roots(root, &openssl.prefix, &zlib_xz.prefix, prefix))
}

/// The roots of the CRT at `prefix` keyed on the OpenSSL at `openssl` and
/// the zlib/xz at `zlib_xz`.
fn stage_roots(root: &Path, openssl: &Path, zlib_xz: &Path, prefix: &Path) -> Roots {
    let mut roots = openssl::roots(root, openssl);
    roots.extend(zlib_xz::roots(root, zlib_xz));
    roots.insert("crt", prefix.to_owned());
    roots.insert_work(root, scratch(root));
    roots
}

/// The CRT's key beyond its own files, pins, and tools: the toolchain
/// digest and the keys of the OpenSSL and zlib/xz stages it links and
/// publishes.
///
/// Their keys, not their prefix paths, so the CRT's key stays independent
/// of where the checkout lives, as its source maps keep its output: the CRT
/// is always built against the prefixes of its own tree, and each prefix is
/// named by its key alone.
pub(super) fn crt_key<'a>(toolchain: &'a str, openssl: &'a str, zlib_xz: &'a str) -> [&'a [u8]; 3] {
    [toolchain.as_bytes(), openssl.as_bytes(), zlib_xz.as_bytes()]
}

/// The OpenSSL, zlib, and xz CPython links: the managed stages the CRT
/// publishes them from, or a prepared CRT prefix that carries all three.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CpythonLibraries(Libraries);

#[derive(Clone, Debug, PartialEq, Eq)]
enum Libraries {
    Managed(openssl::Stage, zlib_xz::Stage),
    Prepared(PathBuf),
}

impl CpythonLibraries {
    /// The managed OpenSSL and zlib/xz stages for `tools`, keyed without
    /// being built.
    ///
    /// # Errors
    /// Reports a stage whose key cannot be computed.
    pub fn managed(root: &Path, tools: &Toolchain) -> Result<Self> {
        Ok(Self(Libraries::Managed(
            openssl::Stage::new(root, tools)?,
            zlib_xz::Stage::new(root, tools)?,
        )))
    }

    /// The libraries of the prepared CRT prefix `crt`, which carries them.
    pub fn prepared(crt: &Path) -> Self {
        Self(Libraries::Prepared(crt.to_owned()))
    }

    /// The prefix CPython reads OpenSSL from.
    pub fn openssl(&self) -> &Path {
        match &self.0 {
            Libraries::Managed(openssl, _) => &openssl.prefix,
            Libraries::Prepared(crt) => crt,
        }
    }

    /// The prefix CPython reads zlib and xz from.
    pub fn zlib_xz(&self) -> &Path {
        match &self.0 {
            Libraries::Managed(_, zlib_xz) => &zlib_xz.prefix,
            Libraries::Prepared(crt) => crt,
        }
    }

    /// Build the managed stages unless they are complete. A prepared prefix
    /// is already built.
    ///
    /// # Errors
    /// Reports a stage that fails to build or to validate.
    pub fn build(&self, root: &Path, pins: &Pins, tools: &Toolchain) -> Result<()> {
        if let Libraries::Managed(openssl, zlib_xz) = &self.0 {
            openssl.build(root, pins, tools)?;
            zlib_xz.build(root, pins, tools)?;
        }
        Ok(())
    }
}

/// Build the CRT project `name` from the pinned source `source_name` into
/// the stage unless it is installed.
fn project(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    build: &Build<'_>,
    name: &str,
    source_name: &str,
) -> Result<()> {
    if installed_marker(build.prefix, name).exists() {
        return Ok(());
    }
    guard(&format!("crt-cmake-{name}"))?;
    let input = source(root, pins, source_name)?;
    let project = Project {
        name,
        source: &input,
        target: "install",
    };
    build.run(root, tools, &project, &arguments(build.prefix, name))?;
    mark_installed(build.prefix, name)
}

/// The CRT project `name`'s own configure arguments for the CRT `prefix`.
fn arguments(prefix: &Path, name: &str) -> Vec<String> {
    let mut arguments = Vec::new();
    if !cfg!(windows)
        && matches!(
            name,
            "s2n-tls" | "aws-c-cal" | "aws-c-io" | "aws-c-http" | "aws-c-auth"
        )
    {
        arguments.extend([
            "-DUSE_OPENSSL=ON".to_owned(),
            format!("-DOPENSSL_ROOT_DIR={}", prefix.display()),
            format!("-DOPENSSL_INCLUDE_DIR={}/include", prefix.display()),
            format!(
                "-DOPENSSL_CRYPTO_LIBRARY={}/lib/libcrypto.a",
                prefix.display()
            ),
            format!("-DOPENSSL_SSL_LIBRARY={}/lib/libssl.a", prefix.display()),
        ]);
    }
    if cfg!(target_os = "macos") && name == "aws-c-io" {
        // Keep macOS on kqueue/POSIX sockets instead of Network.framework's
        // dispatch queue backend, whose symbols would remain in the archive.
        arguments.push("-DNETWORK_LIB=FALSE".to_owned());
    }
    if name == "s2n-tls" {
        arguments.push("-DUNSAFE_TREAT_WARNINGS_AS_ERRORS=OFF".to_owned());
    }
    arguments
}

fn inventory(text: &str) -> Vec<&str> {
    text.lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .collect()
}

fn validate(root: &Path, prefix: &Path) -> Result<()> {
    archives(root, prefix)?;
    shared_library_check(&prefix.join("lib"))?;
    Ok(())
}

/// The static archives a CRT prefix provides for this host, named from
/// deps/crt-libraries.txt. Each must be a file inside the prefix.
pub(crate) fn archives(root: &Path, prefix: &Path) -> Result<Vec<PathBuf>> {
    let canonical = fs::canonicalize(prefix)?;
    let libraries = fs::read_to_string(root.join("deps/crt-libraries.txt"))?;
    let mut archives = Vec::new();
    for name in inventory(&libraries) {
        if !super::platform::includes_library(std::env::consts::OS, name) {
            continue;
        }
        let archive = prefix
            .join("lib")
            .join(super::platform::archive_name(std::env::consts::OS, name));
        let resolved = fs::canonicalize(&archive).map_err(|failure| {
            error(format!(
                "missing CRT archive {}: {failure}",
                archive.display()
            ))
        })?;
        if !resolved.starts_with(&canonical) || !resolved.is_file() {
            return Err(error(format!(
                "CRT archive escapes prefix: {}",
                archive.display()
            )));
        }
        archives.push(archive);
    }
    Ok(archives)
}

fn shared_library_check(directory: &Path) -> Result<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if name.ends_with(".so")
            || name.contains(".so.")
            || name.ends_with(".dylib")
            || name.ends_with(".dll")
        {
            return Err(error(format!(
                "shared library in static CRT prefix: {}",
                entry.path().display()
            )));
        }
        if entry.file_type()?.is_dir() {
            shared_library_check(&entry.path())?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests;
