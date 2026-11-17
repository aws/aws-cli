//! Static OpenSSL, built as its own stage before the CPython and CRT that
//! link it.
//!
//! OpenSSL keys only on its own pin, this builder, the toolchain digest, and
//! the perl that generates its Makefile, configuration headers, and perlasm
//! assembly. A bump of an AWS C library, zlib, or xz rebuilds the CRT against
//! the cached OpenSSL prefix rather than OpenSSL itself.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use super::super::toolchain::jobs;
use super::super::{CopyMode, copy_tree, files, platform, write_executable};
use super::super::{
    Pins, Result, Roots, TARGET, Toolchain, claim_work, digest, error, guard, lock_stage, source,
    work_dir,
};
use super::source_paths;
use crate::process;

/// The stage label, which names the prefix, the work directory, the
/// builder guard, and the deps/pins.toml source.
const LABEL: &str = "openssl";

/// A fixed reproducibility epoch (2000-01-01 UTC), not a wall-clock build date.
/// Positive because OpenSSL's Windows resource generator treats zero as unset.
const SOURCE_DATE_EPOCH: &str = "946684800";

/// The directories of the prefix the CRT links into its own: OpenSSL's
/// `install_dev` installs only headers, archives, and their pkg-config and
/// CMake package files.
pub(super) const OUTPUTS: &[&str] = &["include", "lib"];

/// The OpenSSL stage's key and the prefix that key names.
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

    /// Build the prefix unless it is complete.
    ///
    /// Callers may hold the CRT's or the interpreter's stage lock: OpenSSL's
    /// is taken after either, and before zlib/xz's, and no stage takes them
    /// in another order.
    pub(super) fn build(&self, root: &Path, pins: &Pins, tools: &Toolchain) -> Result<()> {
        let prefix = &self.prefix;
        let _lock = lock_stage(prefix)?;
        if cached(prefix)? {
            return Ok(());
        }
        guard(LABEL)?;
        reset(prefix)?;
        {
            // The make tree stays out of the published prefix, and since its
            // objects are bound to this key's sources and flags, another key's
            // tree is emptied.
            let work = scratch(root);
            let _work_lock = claim_work(&work, prefix)?;
            build(root, pins, tools, prefix, &work)?;
        }
        validate(prefix)?;
        fs::write(prefix.join(".complete"), &self.key)?;
        Ok(())
    }
}

/// OpenSSL's scratch directory, which holds the make tree of one key.
fn scratch(root: &Path) -> PathBuf {
    work_dir(root, TARGET, LABEL)
}

/// The OpenSSL `prefix` and OpenSSL's scratch directory.
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

/// Empty `prefix` for a build: an interrupted install leaves files the
/// next one must not merge with.
fn reset(prefix: &Path) -> Result<()> {
    if fs::symlink_metadata(prefix).is_ok() {
        fs::remove_dir_all(prefix)?;
    }
    fs::create_dir_all(prefix)?;
    Ok(())
}

/// Require the archives and headers every OpenSSL consumer reads, and
/// nothing outside `OUTPUTS`, the only trees the CRT links: whatever else
/// an install added would silently be missing from the CRT prefix.
fn validate(prefix: &Path) -> Result<()> {
    for entry in fs::read_dir(prefix)? {
        let name = entry?.file_name();
        if name != ".complete" && !OUTPUTS.iter().any(|output| name == *output) {
            return Err(error(format!(
                "OpenSSL prefix {} has {}, which the CRT does not publish",
                prefix.display(),
                name.to_string_lossy()
            )));
        }
    }
    let mut required = vec![prefix.join("include/openssl/ssl.h")];
    for name in ["ssl", "crypto"] {
        required.push(
            prefix
                .join("lib")
                .join(platform::archive_name(std::env::consts::OS, name)),
        );
    }
    for path in required {
        if !path.is_file() {
            return Err(error(format!("OpenSSL prefix lacks {}", path.display())));
        }
    }
    Ok(())
}

/// Configure, build, and install OpenSSL into `prefix` from the scratch
/// tree `scratch`, which keeps the layout the CRT's work directory had, so
/// the source maps record the same logical paths.
fn build(root: &Path, pins: &Pins, tools: &Toolchain, prefix: &Path, scratch: &Path) -> Result<()> {
    let input = source(root, pins, LABEL)?;
    let work = scratch.join(LABEL);
    let build = work.join("source");
    copy_tree(&input, &build, CopyMode::Replace)?;
    let roots = source_paths::Roots {
        name: LABEL,
        source: &build,
        build: &work,
        work: scratch,
        install: prefix,
    };
    let maps = if cfg!(windows) {
        source_paths::clang_cl_flags(&roots)?
    } else {
        let maps = source_paths::flags(&roots)?;
        write_executable(
            &build.join("native-cc"),
            &source_paths::wrapper(&tools.cc, &maps)?,
        )?;
        maps
    };
    let configure_target =
        platform::openssl_target(TARGET).ok_or_else(|| error("unsupported native OpenSSL host"))?;
    let paths = openssl_runtime_paths(configure_target);
    openssl_configure(root, tools, &build, configure_target, &paths, &maps)?;
    let make = if platform::uses_nmake(configure_target) {
        "nmake"
    } else {
        "make"
    };
    let mut libraries = tools.command(root, make)?;
    openssl_environment(&mut libraries, tools, &maps)?;
    if !cfg!(windows) {
        libraries.arg(format!("-j{}", jobs()?));
    }
    process::run(libraries.current_dir(&build).arg("build_libs"))?;
    let compilers = [&tools.cc, &tools.clang].map(|tool| tool.parent().unwrap_or(tool));
    verify_openssl_build_information(&build, &[prefix, scratch, compilers[0], compilers[1]])?;
    // A static Windows install_dev copies the `ossl_static.pdb` that cl
    // writes for `/Zi /Fd`. clang-cl keeps that debug information in the
    // objects and ignores `/Fd`, so an empty stand-in lets the install run,
    // and the installed copy, which nothing reads, is removed again.
    let pdb = build.join(WINDOWS_OPENSSL_PDB);
    if cfg!(windows) && !pdb.exists() {
        fs::write(&pdb, b"")?;
    }
    openssl_install(root, tools, make, &work, prefix, &paths, &maps)?;
    if cfg!(windows) {
        // A static nmake install_dev still creates the `bin` directory a
        // shared build installs its DLLs into, and leaves it empty.
        let bin = prefix.join("bin");
        if fs::read_dir(&bin).is_ok_and(|mut entries| entries.next().is_none()) {
            fs::remove_dir(bin)?;
        }
        let installed = prefix.join("lib").join(WINDOWS_OPENSSL_PDB);
        if fs::metadata(&installed).is_ok_and(|metadata| metadata.len() == 0) {
            fs::remove_file(installed)?;
        }
        for name in ["ssl", "crypto"] {
            let input = prefix.join("lib").join(format!("lib{name}.lib"));
            let output = prefix.join("lib").join(format!("{name}.lib"));
            fs::rename(input, output)?;
        }
    }
    Ok(())
}

fn openssl_configure(
    root: &Path,
    tools: &Toolchain,
    build: &Path,
    configure_target: &str,
    paths: &OpenSslRuntimePaths,
    maps: &[String],
) -> Result<()> {
    let mut configure = tools.command(root, tools.perl.as_deref().unwrap_or(Path::new("perl")))?;
    openssl_environment(&mut configure, tools, maps)?;
    configure.arg("./Configure").arg(configure_target);
    if cfg!(windows) {
        configure.args(["no-asm", "/MT"]);
    }
    configure
        .current_dir(build)
        .args([
            "no-shared",
            "no-tests",
            "no-docs",
            "no-apps",
            "no-engine",
            "no-legacy",
            "--libdir=lib",
        ])
        .arg(format!("--prefix={}", paths.prefix))
        .arg(format!("--openssldir={}", paths.openssldir));
    process::run(&mut configure)
}

/// Install through INSTALL.md's packaging interface, then merge into the prefix.
///
/// DESTDIR stages the logical prefix: POSIX prepends it, Windows replaces the
/// drive. Overriding the install location instead would leak into compiler
/// definitions that expand the makefile's installation variables.
fn openssl_install(
    root: &Path,
    tools: &Toolchain,
    make: &str,
    work: &Path,
    prefix: &Path,
    paths: &OpenSslRuntimePaths,
    maps: &[String],
) -> Result<()> {
    let destdir = work.join("install");
    if destdir.exists() {
        fs::remove_dir_all(&destdir)?;
    }
    let mut install = tools.command(root, make)?;
    openssl_environment(&mut install, tools, maps)?;
    process::run(
        install
            .current_dir(work.join("source"))
            .arg(format!("DESTDIR={}", destdir.display()))
            .arg("install_dev"),
    )?;
    let staged = destdir.join(if cfg!(windows) {
        &paths.prefix[3..]
    } else {
        &paths.prefix[1..]
    });
    files::install_staged(&staged, prefix)
}

/// Logical, project-owned OpenSSL defaults, never the physical build prefix.
///
/// OpenSSL derives modules and engines from the prefix and its X509 and
/// configuration paths from openssldir. `SSL_CERT_FILE`, `SSL_CERT_DIR`, and
/// `OPENSSL_CONF` still override them at run time.
struct OpenSslRuntimePaths {
    prefix: &'static str,
    openssldir: &'static str,
}

fn openssl_runtime_paths(configure_target: &str) -> OpenSslRuntimePaths {
    if platform::uses_nmake(configure_target) {
        OpenSslRuntimePaths {
            prefix: "C:\\Program Files\\aws-cli-native",
            openssldir: "C:\\ProgramData\\aws-cli-native\\ssl",
        }
    } else if configure_target.starts_with("darwin") {
        OpenSslRuntimePaths {
            prefix: "/usr/local/lib/aws-cli-native",
            openssldir: "/Library/Application Support/aws-cli-native/ssl",
        }
    } else {
        OpenSslRuntimePaths {
            prefix: "/usr/local/lib/aws-cli-native",
            openssldir: "/etc/aws-cli-native/ssl",
        }
    }
}

/// The compiler environment for OpenSSL's configure and make steps.
fn openssl_environment(command: &mut Command, tools: &Toolchain, maps: &[String]) -> Result<()> {
    tools.apply_build_tools(command);
    apply_openssl_compiler(command, &tools.clang, maps, cfg!(windows))
}

/// Name OpenSSL's compiler without recording where the toolchain lives.
///
/// OpenSSL embeds CC and its flags in its build information. On POSIX the
/// source maps sit inside a wrapper named by a relative path. On Windows
/// clang-cl is named through PATH and takes the maps from `_CL_`, and the
/// makefile archives with lib's options, so AR and RANLIB are left to its
/// own `lib`.
fn apply_openssl_compiler(
    command: &mut Command,
    clang: &Path,
    maps: &[String],
    windows: bool,
) -> Result<()> {
    command.env("SOURCE_DATE_EPOCH", SOURCE_DATE_EPOCH);
    if !windows {
        command.env("CC", "./native-cc");
        return Ok(());
    }
    let directory = clang
        .parent()
        .ok_or_else(|| error("the selected clang has no directory"))?;
    let existing = search_path(command);
    let entries = std::iter::once(directory.to_owned())
        .chain(existing.iter().flat_map(std::env::split_paths));
    let path = std::env::join_paths(entries)
        .map_err(|failure| error(format!("cannot form the OpenSSL compiler path: {failure}")))?;
    command
        .env("CC", WINDOWS_OPENSSL_CC)
        .env("PATH", path)
        .env("_CL_", source_paths::clang_cl_variable(maps))
        .env_remove("AR")
        .env_remove("RANLIB");
    Ok(())
}

/// The compiler name OpenSSL's Windows build records, independent of where
/// the toolchain is installed.
const WINDOWS_OPENSSL_CC: &str = "clang-cl";

/// The program database a static Windows OpenSSL build installs.
const WINDOWS_OPENSSL_PDB: &str = "ossl_static.pdb";

/// Reject OpenSSL build information that names a physical build path.
///
/// `OPENSSL_CFLAGS` reports the compiler and flags recorded in
/// `crypto/buildinf.h`; none of the given build directories, such as the
/// OpenSSL prefix or a compiler's directory, may appear there as given or
/// in either separator spelling.
fn verify_openssl_build_information(build: &Path, directories: &[&Path]) -> Result<()> {
    let recorded = recorded_compiler_flags(&fs::read_to_string(build.join("crypto/buildinf.h"))?)?;
    for directory in directories {
        let directory = directory.to_string_lossy();
        if directory.is_empty() {
            continue;
        }
        let spellings = [
            directory.to_string(),
            directory.replace('\\', "/"),
            directory.replace('/', "\\"),
        ];
        for spelling in spellings {
            if recorded.contains(&spelling) {
                return Err(error(format!(
                    "OpenSSL recorded the build path {spelling} in its compiler flags"
                )));
            }
        }
    }
    Ok(())
}

/// Decode the character array `util/mkbuildinf.pl` writes for the compiler
/// flags. It doubles each backslash, then escapes backslashes and quotes in
/// single-character literals, and ends the array with `'\0'`.
fn recorded_compiler_flags(buildinf: &str) -> Result<String> {
    let start = buildinf
        .find("compiler_flags[] = {")
        .ok_or_else(|| error("OpenSSL build information has no compiler flags"))?;
    let mut characters = buildinf[start..].chars();
    let mut escaped = String::new();
    while let Some(character) = characters.next() {
        if character != '\'' {
            continue;
        }
        let value = match characters.next() {
            Some('\\') => match characters.next() {
                Some('0') => return Ok(escaped.replace("\\\\", "\\")),
                Some(value) => value,
                None => break,
            },
            Some(value) => value,
            None => break,
        };
        escaped.push(value);
        if characters.next() != Some('\'') {
            break;
        }
    }
    Err(error(
        "OpenSSL build information has malformed compiler flags",
    ))
}

/// The search path a command will run with: its own setting, else the caller's.
fn search_path(command: &Command) -> Option<std::ffi::OsString> {
    let configured = command.get_envs().find(|(name, _)| {
        name.to_str()
            .is_some_and(|name| name.eq_ignore_ascii_case("PATH"))
    });
    match configured {
        Some((_, value)) => value.map(ToOwned::to_owned),
        None => std::env::var_os("PATH"),
    }
}

#[cfg(test)]
mod tests;
