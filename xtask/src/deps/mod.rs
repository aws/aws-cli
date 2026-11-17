//! Verified source downloads and native, content-addressed dependency builds.

mod command;
mod crt;
mod files;
pub mod inputs;
mod llvm;
mod msvc;
mod platform;
mod roots;
mod store;
mod system_crt;
mod toolchain;

use std::collections::BTreeMap;
use std::fs::{self, File, TryLockError};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::SystemTime;

use serde::Deserialize;
use sha2::{Digest, Sha256};

use self::command::ninja_program;
pub use self::command::{shell_quote, tool_command, write_executable};
pub(crate) use self::crt::archives as crt_archives;
pub use self::crt::{CpythonLibraries, crt};
pub use self::files::{CopyMode, copy_tree};
pub use self::roots::{ROOTS_FILE, Roots};
pub use self::system_crt::build as system_crt;
pub use self::toolchain::{Toolchain, toolchain};
use crate::file_lock::FileLock;
use crate::{TaskError, process};

pub const TARGET: &str = if cfg!(target_os = "linux") {
    if cfg!(target_arch = "aarch64") {
        "aarch64-unknown-linux-musl"
    } else {
        "x86_64-unknown-linux-musl"
    }
} else if cfg!(target_os = "macos") {
    if cfg!(target_arch = "aarch64") {
        "aarch64-apple-darwin"
    } else {
        "x86_64-apple-darwin"
    }
} else {
    "x86_64-pc-windows-msvc"
};

type Result<T> = std::result::Result<T, TaskError>;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NativeEnvironment {
    crt: PathBuf,
    cpython: PathBuf,
    fallback: PathBuf,
    cc: PathBuf,
    clang: PathBuf,
    ar: PathBuf,
    ranlib: PathBuf,
    mimalloc: Option<PathBuf>,
    msvc: Option<(msvc::Environment, PathBuf)>,
    /// The toolchain's musl link driver, `Toolchain::link`.
    link: Option<PathBuf>,
}

impl NativeEnvironment {
    pub fn apply(&self, command: &mut Command) {
        if let Some((environment, path)) = &self.msvc {
            environment.apply(command);
            command.env("AWS_NATIVE_MSVC_ENV_FILE", path);
        }
        command
            .env("AWS_NATIVE_LINK_MODE", "static")
            .env("AWS_NATIVE_PYTHON_LINK", "static")
            .env("AWS_NATIVE_PYTHON_PAYLOAD", "embedded")
            .env("AWS_NATIVE_CRT_PREFIX", &self.crt)
            .env("AWS_NATIVE_CPYTHON_PREFIX", &self.cpython)
            .env("AWS_NATIVE_FALLBACK_PREFIX", &self.fallback)
            .env("CC", &self.cc)
            .env("AR", &self.ar)
            .env("RANLIB", &self.ranlib);
        if let Some(source) = &self.mimalloc {
            command.env("AWS_NATIVE_MIMALLOC_SOURCE", source);
        }
    }

    /// Names the managed compilers that the test suites' compiler probes run.
    pub fn apply_test_tools(&self, command: &mut Command) {
        command
            .env("AWS_NATIVE_TEST_CC", &self.cc)
            .env("AWS_NATIVE_TEST_CLANG", &self.clang);
    }

    /// Link the command's musl executables through the toolchain's driver,
    /// as `Toolchain::apply_link` does, after it sets its own flags.
    pub fn apply_link(&self, command: &mut Command) {
        toolchain::link_through(self.link.as_deref(), command);
    }
}

#[derive(Debug, Deserialize)]
pub struct Pins {
    pub versions: BTreeMap<String, String>,
    pub sources: BTreeMap<String, Source>,
}

#[derive(Debug, Deserialize)]
pub struct Source {
    pub url: String,
    pub sha256: String,
    pub original_url: Option<String>,
    #[serde(default = "default_strip_components")]
    pub strip_components: u8,
}

fn default_strip_components() -> u8 {
    1
}

impl Pins {
    pub fn load(root: &Path) -> Result<Self> {
        let pins: Self = toml::from_str(&fs::read_to_string(root.join("deps/pins.toml"))?)
            .map_err(|error| TaskError::Message(format!("invalid deps/pins.toml: {error}")))?;
        for (name, pin) in &pins.sources {
            if pin.sha256.len() != 64 || !pin.sha256.bytes().all(|byte| byte.is_ascii_hexdigit()) {
                return Err(error(format!("{name}: expected a 64-digit SHA-256")));
            }
            if !pin.url.starts_with("https://") {
                return Err(error(format!("{name}: source URL must use HTTPS")));
            }
        }
        Ok(pins)
    }

    /// The canonical version pinned under `name`.
    pub fn version(&self, name: &str) -> Result<&str> {
        self.versions
            .get(name)
            .map(String::as_str)
            .ok_or_else(|| error(format!("missing version {name}")))
    }
}

/// The dependency commands: `check-pins`, `fetch [SOURCE...]`, and `deps`.
///
/// `cargo xtask deps [toolchain|crt|python|python-fallback|all]
/// [--python-pgo=true|false] [--print-roots]` builds the stage and those
/// before it; `--print-roots` then prints, as one JSON object, every stage
/// prefix and scratch directory they own (see `Roots`). The stages live in
/// the store every checkout of the user shares (see `store`).
/// `cargo xtask deps gc [--days=N] [--dry-run]` removes the store's entries
/// unused for N days, and `cargo xtask deps reset PATH...|--all` removes
/// entries, or the whole store, while no other command runs. `cargo xtask
/// deps prune --roots=FILE... [--sources] [--dry-run]` removes every entry
/// of a local store's `target/deps/<TARGET>` those printed roots do not
/// keep, builds nothing, and with `--sources` also removes the unpacked
/// sources and archives no pin names (see `roots::prune`). `deps
/// system-crt` is dispatched to the system-mode product before this.
pub fn run(root: &Path, command: &str, args: &[String]) -> Result<()> {
    let pins = Pins::load(root)?;
    match command {
        "check-pins" => check_pins(root, &pins),
        "fetch" => {
            check_pins(root, &pins)?;
            for name in pins.sources.keys() {
                if args.is_empty() || args.contains(name) {
                    let _ = download(root, &pins, name)?;
                }
            }
            for name in args {
                if !pins.sources.contains_key(name) {
                    return Err(error(format!("unknown source {name}")));
                }
            }
            Ok(())
        }
        "deps" => run_deps(root, &pins, args),
        _ => Err(error(format!("unknown dependency command {command}"))),
    }
}

fn run_deps(root: &Path, pins: &Pins, args: &[String]) -> Result<()> {
    // Cleanup builds nothing, so it precedes the static host gate: a system
    // build host, which the gate rejects, fills the store too.
    if let Some((command, options)) = args.split_first() {
        match command.as_str() {
            "gc" => return store::gc(root, options),
            "reset" => return store::reset(root, options),
            _ => {}
        }
    }
    gate(root, pins)?;
    if args
        .first()
        .is_some_and(|argument| argument == "system-crt")
    {
        if args
            .iter()
            .skip(1)
            .any(|argument| argument != "--print-roots")
        {
            return Err(error("system-crt accepts only --print-roots"));
        }
        let prefix = system_crt::build(root, pins)?;
        if args.iter().any(|argument| argument == "--print-roots") {
            let roots = BTreeMap::from([("crt", prefix)]);
            serde_json::to_writer(std::io::stdout().lock(), &roots)
                .map_err(|error| TaskError::Message(error.to_string()))?;
        }
        return Ok(());
    }
    if let Some((command, options)) = args.split_first()
        && command == "prune"
    {
        return roots::prune(root, pins, options);
    }
    let (stage, pgo, print_roots) = dependency_options(args)?;
    let roots = prepare(root, pins, stage, pgo)?;
    if print_roots {
        roots.write(&mut std::io::stdout().lock())?;
    }
    Ok(())
}

/// The checks every `deps` command makes before it builds or prunes.
fn gate(root: &Path, pins: &Pins) -> Result<()> {
    native_host()?;
    if std::env::var_os("AWS_NATIVE_DEPS_OVERRIDE").is_some() {
        return Err(error("dependency gates reject AWS_NATIVE_DEPS_OVERRIDE"));
    }
    check_pins(root, pins)
}

/// Build what `cargo xtask deps <args>` builds and return its roots.
pub fn dependency_roots(root: &Path, args: &[String]) -> Result<Roots> {
    let pins = Pins::load(root)?;
    gate(root, &pins)?;
    let (stage, pgo, _) = dependency_options(args)?;
    prepare(root, &pins, stage, pgo)
}

/// Build `stage` and the stages before it, then return every root they own:
/// each stage's prefix, and the scratch directory it builds in for `pgo`.
///
/// The roots name the generation the current inputs select, including the
/// stages a cached downstream stage skipped, such as OpenSSL under a cached
/// CRT, so the next key that needs them finds them built.
fn prepare(root: &Path, pins: &Pins, stage: &str, pgo: bool) -> Result<Roots> {
    let tools = toolchain(root, pins)?;
    let mut roots = toolchain_roots(root, &tools)?;
    if stage != "toolchain" {
        let prefix = crt(root, pins, &tools)?;
        roots.extend(crt::roots(root, &tools, &prefix)?);
        if stage != "crt" {
            let python = crate::python::build(root, pins, &tools, &prefix, pgo)?;
            roots.extend(crate::python::roots(root, &tools, &prefix, pgo, &python)?);
        }
    }
    Ok(roots)
}

/// The roots of the toolchain `tools`: its prefix and, on Linux, the
/// scratch it builds in and the profile stage its self-test builds.
fn toolchain_roots(root: &Path, tools: &Toolchain) -> Result<Roots> {
    let mut roots = Roots::default();
    roots.insert("toolchain", tools.prefix.clone());
    if cfg!(target_os = "linux") {
        // Only the Linux toolchain builds; the others discover the host's.
        roots.insert_work(root, toolchain::scratch(root));
        roots.extend(crate::python::profile_roots(root, tools)?);
    }
    Ok(roots)
}

/// A toolchain that only keys stages: none of its tools is run.
#[cfg(test)]
pub(crate) fn keying_toolchain() -> Toolchain {
    let path = PathBuf::from("/unused");
    Toolchain {
        prefix: path.clone(),
        cc: path.clone(),
        ar: path.clone(),
        ranlib: path.clone(),
        clang: path.clone(),
        llvm_ar: path.clone(),
        ld_lld: path.clone(),
        llvm_profdata: path.clone(),
        sysroot: path,
        link: None,
        digest: "toolchain".to_owned(),
        version: "21.1.0".to_owned(),
        sdk: None,
        msvc: None,
        perl: None,
        mimalloc: None,
    }
}

fn dependency_options(args: &[String]) -> Result<(&str, bool, bool)> {
    let (mut stage, mut pgo, mut print_roots) = (None, !cfg!(windows), false);
    for arg in args {
        match arg.as_str() {
            "--print-roots" => print_roots = true,
            "--python-pgo=false" => pgo = false,
            "--python-pgo=true" => pgo = true,
            "toolchain" | "crt" | "python" | "python-fallback" | "all" if stage.is_none() => {
                stage = Some(arg.as_str());
            }
            _ => {
                return Err(error(format!(
                    "unknown or duplicate dependency argument {arg}"
                )));
            }
        }
    }
    if cfg!(windows) && pgo {
        return Err(error("CPython PGO is unsupported on Windows"));
    }
    Ok((stage.unwrap_or("all"), pgo, print_roots))
}

pub fn native_host() -> Result<()> {
    if !platform::supported_host(std::env::consts::OS, std::env::consts::ARCH, false) {
        return Err(error(
            "unsupported native host; cross-compilation is forbidden",
        ));
    }
    Ok(())
}

pub fn native_target(system: bool) -> Result<String> {
    platform::target(std::env::consts::OS, std::env::consts::ARCH, system)
}

pub fn native_environment(root: &Path, python_pgo: bool) -> Result<NativeEnvironment> {
    native_host()?;
    if std::env::var_os("AWS_NATIVE_DEPS_OVERRIDE").is_some() {
        return Err(error(
            "native dependency consumers reject AWS_NATIVE_DEPS_OVERRIDE",
        ));
    }
    let pins = Pins::load(root)?;
    check_pins(root, &pins)?;
    let tools = toolchain(root, &pins)?;
    let crt = crt(root, &pins, &tools)?;
    let python = crate::python::build(root, &pins, &tools, &crt, python_pgo)?;
    Ok(NativeEnvironment {
        crt,
        cpython: python.cpython,
        fallback: python.fallback,
        cc: tools.cc,
        clang: tools.clang,
        ar: tools.ar,
        ranlib: tools.ranlib,
        mimalloc: tools.mimalloc,
        msvc: tools.msvc,
        link: tools.link,
    })
}

pub fn error(message: impl Into<String>) -> TaskError {
    TaskError::Message(message.into())
}

/// The directory of the checkout's managed dependency builds: the user's
/// shared store, or with `AWS_NATIVE_CACHE=local` the checkout's `target`
/// (see `store`). It holds `downloads`, `download-locks`, `sources`,
/// `toolchain`, and `deps/<target>`, as `target` always did.
pub fn store(root: &Path) -> PathBuf {
    store::resolve(root).directory
}

/// Hold the dependency store of `root` shared until the guard drops, as
/// every command but `deps reset` does for as long as it runs.
///
/// # Errors
/// Rejects an invalid `AWS_NATIVE_CACHE` or `AWS_NATIVE_CACHE_DIR`, and
/// reports a store that cannot be created or locked.
pub fn hold_store(root: &Path) -> Result<FileLock> {
    store::hold(root)
}

/// Record a use of `path`, an input a caller supplied such as a
/// `--crt-prefix`, if it lies in an entry of the store of `root`, so
/// `deps gc` keeps that entry as it keeps a stage a build resolves.
///
/// The entry's lock is awaited first, so a `deps gc` removing the entry
/// finishes before this returns.
///
/// # Errors
/// Reports an entry `deps gc` removed while this awaited its lock.
pub fn register_input(root: &Path, path: &Path) -> Result<()> {
    let Some(entry) = store::entry(root, path)? else {
        return Ok(());
    };
    let _lock = lock_stage(&entry)?;
    if fs::symlink_metadata(&entry).is_err() {
        return Err(error(format!(
            "{} was removed from the dependency store",
            entry.display()
        )));
    }
    Ok(())
}

/// Whether `cargo xtask <command> <args>` is `deps reset`, the one command
/// that does not hold the store shared: it takes the store exclusively, and
/// only while no other command holds it.
pub fn resets_store(command: &str, args: &[String]) -> bool {
    command == "deps" && args.first().is_some_and(|argument| argument == "reset")
}

/// Hold an exclusive native file lock until the stage's completed marker is visible.
/// The lock sits beside the stage so replacing scratch contents cannot unlink it.
///
/// A lock another build holds is announced on stderr before it is awaited.
/// Once acquired, the lock file's modification time records this use of the
/// entry, which `deps gc` reads.
pub fn lock_stage(prefix: &Path) -> Result<FileLock> {
    let path = lock_path(prefix);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let lock = match FileLock::try_lock(&path) {
        Ok(lock) => lock,
        Err(TryLockError::WouldBlock) => {
            writeln!(
                io::stderr().lock(),
                "xtask: waiting for {} (another build holds its lock)",
                prefix.display()
            )?;
            FileLock::lock(&path)?
        }
        Err(TryLockError::Error(failure)) => return Err(failure.into()),
    };
    lock.touch()?;
    Ok(lock)
}

/// Record a use of the entry `prefix` without taking its lock, as
/// `lock_stage` records one.
fn touch_stage(prefix: &Path) -> Result<()> {
    let path = lock_path(prefix);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    File::options()
        .write(true)
        .create(true)
        .truncate(false)
        .open(path)?
        .set_modified(SystemTime::now())?;
    Ok(())
}

/// The lock file `lock_stage` takes for `prefix`: its `.lock` sibling.
fn lock_path(prefix: &Path) -> PathBuf {
    let mut name = prefix.as_os_str().to_owned();
    name.push(".lock");
    PathBuf::from(name)
}

/// The scratch directory of `stage` for `target`, outside every prefix.
///
/// Keeping `target/deps/<target>/work/<stage>` apart from the
/// content-addressed outputs means a published prefix, and the CI snapshot
/// of it, holds only what consumers read, and a stage keeps one scratch tree
/// rather than one per key. The CRT, CPython, and awscrt builds map the
/// directory to a logical path; the toolchain's compiler-rt builtins
/// still record it through `__FILE__`, as they recorded `<prefix>/work`.
/// Callers hold `lock_stage` on the directory, or `claim_work`, after their
/// stage lock and while they acquire no other stage's.
///
/// The directory stays in the checkout's `target` when the prefixes are in
/// the shared store: it is named per stage, not per key, so checkouts that
/// shared it would empty each other's, and the payload's packing venv kept
/// across keys would be reinstalled.
pub fn work_dir(root: &Path, target: &str, stage: &str) -> PathBuf {
    root.join("target/deps")
        .join(target)
        .join("work")
        .join(stage)
}

/// The marker naming the prefix whose scratch a claimed work directory holds.
const WORK_KEY: &str = ".key";

/// Lock the scratch directory `work` for a build of the stage at `prefix`,
/// first emptying it unless it last held that prefix's scratch.
///
/// The CMake and make trees the Rust builders keep are reused only for the
/// prefix that configured them: CMake refuses a tree configured from another
/// source directory, and make keeps objects compiled with another key's
/// flags. The prefix's name carries the stage key, and its location the
/// store whose sources the tree was configured from. Within one prefix an
/// interrupted build resumes in its own tree. Drivers that validate or wipe
/// their own scratch take `lock_stage` alone.
pub fn claim_work(work: &Path, prefix: &Path) -> Result<FileLock> {
    let lock = lock_stage(work)?;
    let marker = work.join(WORK_KEY);
    let owner = prefix.as_os_str().as_encoded_bytes();
    if fs::read(&marker).ok().as_deref() != Some(owner) {
        if fs::symlink_metadata(work).is_ok() {
            fs::remove_dir_all(work)?;
        }
        fs::create_dir_all(work)?;
        fs::write(&marker, owner)?;
    }
    Ok(lock)
}

pub fn guard(name: &str) -> Result<()> {
    guard_controls(
        name,
        std::env::var_os("AWSCLI_FORBID_EXPENSIVE_BUILDS").as_deref(),
        std::env::var_os("AWSCLI_BUILDER_MARKER_DIR").as_deref(),
    )
}

pub fn guard_controls(
    name: &str,
    forbid: Option<&std::ffi::OsStr>,
    marker: Option<&std::ffi::OsStr>,
) -> Result<()> {
    if forbid.is_some_and(|value| !value.is_empty()) {
        return Err(error(format!(
            "AWSCLI_FORBID_EXPENSIVE_BUILDS forbids builder {name}"
        )));
    }
    if let Some(directory) = marker.filter(|value| !value.is_empty()) {
        fs::create_dir_all(directory)?;
        let mut output = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(Path::new(directory).join(name))?;
        output.write_all(b"ran\n")?;
    }
    Ok(())
}

fn download_command(root: &Path) -> Result<Command> {
    let mut command = tool_command(root, "curl")?;
    // Transport settings cannot change an accepted archive's pinned bytes.
    for name in [
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "ALL_PROXY",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "CURL_CA_BUNDLE",
    ] {
        if let Some(value) = std::env::var_os(name) {
            command.env(name, value);
        }
    }
    // Ignore user curl configuration; every request parameter is explicit.
    command.arg("--disable");
    Ok(command)
}

pub fn file_hash(path: &Path) -> Result<String> {
    let mut source = File::open(path)?;
    let mut hash = Sha256::new();
    let mut buffer = [0; 64 * 1024];
    loop {
        let count = source.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
    }
    Ok(format!("{:x}", hash.finalize()))
}

/// The key of a dependency stage: its source inventory, its pins (see
/// `inputs::stage_pins`), the versions of the host tools it runs (see
/// `inputs::stage_tools`), and the caller's `extra` inputs.
pub fn digest(root: &Path, label: &str, extra: &[&[u8]]) -> Result<String> {
    let mut versions = Vec::new();
    for program in inputs::stage_tools(label)? {
        let output = process::output(tool_command(root, program)?.arg("--version"))?;
        versions.push(output.stdout);
    }
    stage_key(root, label, &versions, extra)
}

/// The key `digest` derives from already captured tool `versions`.
fn stage_key(root: &Path, label: &str, versions: &[Vec<u8>], extra: &[&[u8]]) -> Result<String> {
    let mut hash = Sha256::new();
    hash.update(label);
    hash.update(TARGET);
    for relative in inputs::stage_files(label)? {
        hash.update(relative.as_bytes());
        hash.update(fs::read(root.join(relative))?);
    }
    let pins = Pins::load(root)?;
    for name in inputs::stage_pins(label)? {
        hash.update(pin_identity(&pins, name)?);
    }
    if hashes_cli_source(label) {
        hash.update(aws_cli_digest(root)?.as_bytes());
    }
    for version in versions {
        hash.update(version);
    }
    for bytes in extra {
        hash.update((bytes.len() as u64).to_le_bytes());
        hash.update(bytes);
    }
    Ok(format!("{:x}", hash.finalize()))
}

/// What keys a stage on the pin `name`: a source's URL, digest, and the
/// leading directories its unpack strips, or a version's value. A source's
/// `original_url` only documents where its archive came from. A stage keys
/// on its own pins rather than the whole of deps/pins.toml.
fn pin_identity(pins: &Pins, name: &str) -> Result<String> {
    if let Some(source) = pins.sources.get(name) {
        Ok(format!(
            "source\0{name}\0{}\0{}\0{}\n",
            source.url, source.sha256, source.strip_components
        ))
    } else if let Some(version) = pins.versions.get(name) {
        Ok(format!("version\0{name}\0{version}\n"))
    } else {
        Err(error(format!("stage key names missing pin {name}")))
    }
}

/// Whether a stage key covers the AWS CLI source contents. Only the payload's
/// does, because it packs the CLI; the runtime and published fallback stages
/// follow it through the payload prefix in their keys. CPython's key never
/// does, even when Linux PGO trains on the CLI: the training source's contents
/// deliberately do not invalidate the interpreter, and only its constant path
/// is an input, so a CLI update does not force a PGO rebuild. The trade-off
/// is that the PGO profile can go stale until something else invalidates the
/// interpreter.
fn hashes_cli_source(label: &str) -> bool {
    label == "fallback-payload"
}

pub fn download(root: &Path, pins: &Pins, name: &str) -> Result<PathBuf> {
    let pin = pins
        .sources
        .get(name)
        .ok_or_else(|| error(format!("missing source pin {name}")))?;
    let _lock = lock_stage(&download_lock(root, pin))?;
    let directory = std::env::var_os("AWS_NATIVE_DISTFILES")
        .map(PathBuf::from)
        .unwrap_or_else(|| store(root).join("downloads"));
    fs::create_dir_all(&directory)?;
    let archive = directory.join(archive_name(&pin.sha256, &pin.url));
    if !archive.is_file() {
        let legacy = directory.join(archive_name(name, &pin.url));
        if legacy.is_file() && file_hash(&legacy)? == pin.sha256 {
            fs::rename(legacy, &archive)?;
        } else {
            if std::env::var_os("AWS_NATIVE_OFFLINE")
                .is_some_and(|value| value != "0" && !value.is_empty())
            {
                return Err(error(format!(
                    "offline dependency input missing: {}",
                    archive.display()
                )));
            }
            let temporary = directory.join(format!("{}.{}.part", pin.sha256, std::process::id()));
            let result = process::run(
                download_command(root)?
                    .args([
                        "--fail",
                        "--location",
                        "--silent",
                        "--show-error",
                        "--retry",
                        "3",
                        "--proto",
                        "=https",
                        "--tlsv1.2",
                        "--output",
                    ])
                    .arg(&temporary)
                    .arg(&pin.url),
            );
            if let Err(failure) = result {
                let _ = fs::remove_file(&temporary);
                return Err(failure);
            }
            if file_hash(&temporary)? != pin.sha256 {
                fs::remove_file(&temporary)?;
                return Err(error(format!("SHA-256 mismatch downloading {name}")));
            }
            fs::rename(temporary, &archive)?;
        }
    }
    if file_hash(&archive)? != pin.sha256 {
        return Err(error(format!(
            "SHA-256 mismatch in cached source {name}: {}",
            archive.display()
        )));
    }
    Ok(archive)
}

/// The file name `download` saves the archive at `url` under: `stem` and
/// the archive's compression suffix.
fn archive_name(stem: &str, url: &str) -> String {
    let suffix = if url.ends_with(".zst") {
        "tar.zst"
    } else if url.ends_with(".xz") {
        "tar.xz"
    } else {
        "tar.gz"
    };
    format!("{stem}.{suffix}")
}

/// The path whose lock `download` holds for `pin`'s archive. Its lock file
/// also records the archive's last use.
fn download_lock(root: &Path, pin: &Source) -> PathBuf {
    store(root).join("download-locks").join(&pin.sha256)
}

/// The directory `source` unpacks the pin `name` into: one per recipe, the
/// archive digest, the leading directories stripped, and the members taken,
/// so a changed recipe unpacks beside a tree another build may be reading
/// rather than replacing it.
fn source_dir(root: &Path, name: &str, pin: &Source) -> PathBuf {
    let base = if name == "llvm_binary" {
        "toolchain"
    } else {
        "sources"
    };
    let mut recipe = Sha256::new();
    recipe.update(&pin.sha256);
    recipe.update([0, pin.strip_components]);
    for member in llvm::archive_members(name) {
        recipe.update([0]);
        recipe.update(member);
    }
    store(root)
        .join(base)
        .join(format!("{name}-{:x}", recipe.finalize()))
}

pub fn source(root: &Path, pins: &Pins, name: &str) -> Result<PathBuf> {
    let pin = pins
        .sources
        .get(name)
        .ok_or_else(|| error(format!("missing source {name}")))?;
    let destination = source_dir(root, name, pin);
    let members = llvm::archive_members(name);
    let marker = unpacked_marker(&pin.sha256, members);
    let _lock = lock_stage(&destination)?;
    if fs::read_to_string(destination.join(".unpacked")).is_ok_and(|text| text == marker) {
        // The archive is kept as long as its unpacked tree is used.
        touch_stage(&download_lock(root, pin))?;
        return Ok(destination);
    }
    let archive = download(root, pins, name)?;
    // Only an unpack that never wrote its marker is left here: a changed
    // recipe unpacks into another directory.
    if destination.exists() {
        fs::remove_dir_all(&destination)?;
    }
    fs::create_dir_all(&destination)?;
    let listing = process::output(tool_command(root, "tar")?.arg("-tf").arg(&archive))?;
    let listing = String::from_utf8_lossy(&listing.stdout);
    for entry in listing.lines() {
        if Path::new(entry).is_absolute()
            || Path::new(entry)
                .components()
                .any(|component| matches!(component, std::path::Component::ParentDir))
        {
            return Err(error(format!("unsafe archive entry {entry}")));
        }
    }
    process::run(
        tool_command(root, "tar")?
            .arg("-xf")
            .arg(&archive)
            .arg(format!("--strip-components={}", pin.strip_components))
            .arg("-C")
            .arg(&destination)
            .args(member_paths(&listing, pin.strip_components, members)?),
    )?;
    fs::write(destination.join(".unpacked"), &marker)?;
    // Nothing reads the archive while the marker matches, and a partial
    // unpack exists to save the space a large archive takes. A changed
    // member list unpacks the archive again: the shared store keeps it for
    // other checkouts' member lists until `deps gc` finds it unused, and a
    // local store downloads it again.
    if !members.is_empty()
        && !store::is_shared(root)
        && archive.starts_with(store(root).join("downloads"))
    {
        fs::remove_file(&archive)?;
    }
    Ok(destination)
}

/// The `.unpacked` contents for an archive digest and the members taken from
/// it. A full unpack records only the digest.
fn unpacked_marker(sha256: &str, members: &[&str]) -> String {
    let mut marker = sha256.to_owned();
    for member in members {
        marker.push('\n');
        marker.push_str(member);
    }
    marker
}

/// The archive paths of `members`, which are relative to the directory that
/// `--strip-components` removes. Every entry of a stripped archive shares
/// that directory, so the first entry names it.
fn member_paths(listing: &str, strip: u8, members: &[&str]) -> Result<Vec<String>> {
    if members.is_empty() {
        return Ok(Vec::new());
    }
    let first = listing
        .lines()
        .next()
        .ok_or_else(|| error("archive has no entries"))?;
    let strip = usize::from(strip);
    let prefix: Vec<&str> = first.split('/').take(strip).collect();
    if prefix.len() != strip || prefix.iter().any(|component| component.is_empty()) {
        return Err(error(format!(
            "archive entry {first} has fewer than {strip} leading directories"
        )));
    }
    Ok(members
        .iter()
        .map(|member| {
            prefix
                .iter()
                .copied()
                .chain(std::iter::once(*member))
                .collect::<Vec<_>>()
                .join("/")
        })
        .collect())
}

/// Return the application-owned upstream source without downloading a second copy.
pub fn aws_cli_source(root: &Path) -> Result<PathBuf> {
    let source = root.join("aws-cli");
    if !source.join("awscli/__init__.py").is_file() {
        return Err(error(
            "tracked aws-cli source is missing awscli/__init__.py",
        ));
    }
    Ok(source)
}

/// Read the CLI version from its authoritative Python package.
pub fn aws_cli_version(root: &Path) -> Result<String> {
    let text = fs::read_to_string(aws_cli_source(root)?.join("awscli/__init__.py"))?;
    text.lines()
        .find_map(|line| {
            let value = line
                .strip_prefix("__version__")?
                .trim()
                .strip_prefix('=')?
                .trim();
            let quote = value.chars().next()?;
            if !matches!(quote, '\'' | '"') {
                return None;
            }
            value
                .strip_prefix(quote)?
                .strip_suffix(quote)
                .map(str::to_owned)
        })
        .ok_or_else(|| error("tracked aws-cli source has no literal __version__"))
}

/// Select the upstream host lockfile used to provision the embedded payload.
pub fn aws_cli_runtime_lock(root: &Path) -> Result<PathBuf> {
    Ok(aws_cli_source(root)?.join(if cfg!(windows) {
        "requirements/download-deps/system-sandbox-win-lock.txt"
    } else {
        "requirements/download-deps/system-sandbox-lock.txt"
    }))
}

/// Fingerprint package files and runtime locks, excluding generated bytecode.
pub fn aws_cli_digest(root: &Path) -> Result<String> {
    let source = aws_cli_source(root)?;
    let mut files = Vec::new();
    let mut remaining = SOURCE_ENTRY_LIMIT;
    collect_source_files(&source, Path::new("awscli"), &mut files, &mut remaining)?;
    for lock in ["system-sandbox-lock.txt", "system-sandbox-win-lock.txt"] {
        files.push(Path::new("requirements/download-deps").join(lock));
    }
    files.sort();
    let mut hash = Sha256::new();
    for relative in files {
        let name = relative.as_os_str().as_encoded_bytes();
        hash.update((name.len() as u64).to_le_bytes());
        hash.update(name);
        let contents = fs::read(source.join(relative))?;
        hash.update((contents.len() as u64).to_le_bytes());
        hash.update(contents);
    }
    Ok(format!("{:x}", hash.finalize()))
}

/// Hash every regular file in a source tree without generated Python caches.
pub fn tree_digest(root: &Path) -> Result<String> {
    tree_digest_with_entry_limit(root, SOURCE_ENTRY_LIMIT)
}

const SOURCE_ENTRY_LIMIT: usize = 1_000_000;

fn tree_digest_with_entry_limit(root: &Path, entry_limit: usize) -> Result<String> {
    let mut files = Vec::new();
    let mut remaining = entry_limit;
    collect_source_files(root, Path::new(""), &mut files, &mut remaining)?;
    files.sort();
    let mut digest = Sha256::new();
    for path in files {
        let name = path.as_os_str().as_encoded_bytes();
        digest.update((name.len() as u64).to_le_bytes());
        digest.update(name);
        let contents = fs::read(root.join(path))?;
        digest.update((contents.len() as u64).to_le_bytes());
        digest.update(contents);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn collect_source_files(
    root: &Path,
    relative: &Path,
    files: &mut Vec<PathBuf>,
    remaining: &mut usize,
) -> Result<()> {
    for entry in fs::read_dir(root.join(relative))? {
        // Directory and skipped-cache entries count too. Reaching the bound is
        // a failure even when the final entry is a file.
        *remaining = remaining
            .checked_sub(1)
            .filter(|remaining| *remaining != 0)
            .ok_or_else(|| error("source tree reaches the enumeration entry limit"))?;
        let entry = entry?;
        if entry.file_name() == "__pycache__"
            || entry.path().extension().is_some_and(|ext| ext == "pyc")
        {
            continue;
        }
        let path = relative.join(entry.file_name());
        let kind = entry.file_type()?;
        if kind.is_dir() {
            collect_source_files(root, &path, files, remaining)?;
        } else if kind.is_file() {
            files.push(path);
        } else {
            return Err(error(format!(
                "unsupported AWS CLI source entry: {}",
                path.display()
            )));
        }
    }
    Ok(())
}

pub fn check_pins(root: &Path, pins: &Pins) -> Result<()> {
    let _ = aws_cli_version(root)?;
    if pins.sources.contains_key("aws_cli") || pins.versions.contains_key("aws_cli_version") {
        return Err(error(
            "AWS CLI source and version must come from the tracked aws-cli tree",
        ));
    }
    check_cli_awscrt(
        &read_text(root, "aws-cli/pyproject.toml")?,
        pins.version("awscrt_version")?,
    )?;
    check_python_abi(pins.version("python_version")?, crate::python::PYTHON_ABI)?;
    check_rust_version(
        pins.version("rust_version")?,
        &RustPinCopies {
            toolchain: &read_text(root, "rust-toolchain.toml")?,
            mise: &read_text(root, "mise.toml")?,
            manifest: &read_text(root, "Cargo.toml")?,
        },
    )?;
    check_archive_urls(pins)?;
    check_source_versions(pins)
}

fn read_text(root: &Path, relative: &str) -> Result<String> {
    fs::read_to_string(root.join(relative))
        .map_err(|failure| error(format!("{relative}: {failure}")))
}

/// Require the tracked CLI to declare exactly the pinned awscrt: the first
/// quoted `awscrt` requirement in aws-cli/pyproject.toml must be
/// `awscrt==<awscrt_version>`. The pin names the awscrt the user agent reports
/// and the payload builds.
fn check_cli_awscrt(project: &str, awscrt_version: &str) -> Result<()> {
    let line = project
        .lines()
        .map(|line| line.trim_matches([' ', '\t', '\r']))
        .find(|line| line.starts_with("\"awscrt") || line.starts_with("'awscrt"))
        .ok_or_else(|| error("aws-cli/pyproject.toml: missing awscrt requirement"))?;
    let requirement = quoted_value(line)?;
    let expected = format!("awscrt=={awscrt_version}");
    if requirement != expected {
        return Err(error(format!(
            "aws-cli/pyproject.toml requires {requirement}, but deps/pins.toml pins \
             {expected}; update the aws-crt-python version and package pin together"
        )));
    }
    Ok(())
}

/// The text between matching quotes once spaces, tabs, carriage returns and
/// commas are trimmed from both ends.
fn quoted_value(value: &str) -> Result<&str> {
    let trimmed = value.trim_matches([' ', '\t', '\r', ',']);
    trimmed
        .chars()
        .next()
        .filter(|quote| matches!(quote, '\'' | '"') && trimmed.len() >= 3)
        .and_then(|quote| trimmed.strip_prefix(quote)?.strip_suffix(quote))
        .ok_or_else(|| {
            error(format!(
                "AWS CLI metadata: expected a quoted value, found {trimmed}"
            ))
        })
}

/// "3.14" from "3.14.8": everything before the last dot.
fn major_minor(version: &str) -> Option<&str> {
    version.rsplit_once('.').map(|(major_minor, _)| major_minor)
}

/// Require the ABI name xtask builds with to name the pinned Python's
/// major.minor, so a `python_version` bump fails here rather than after
/// CPython builds.
fn check_python_abi(python_version: &str, abi: &str) -> Result<()> {
    let major_minor = major_minor(python_version).ok_or_else(|| {
        error(format!(
            "deps/pins.toml: python_version must be MAJOR.MINOR.MICRO, found {python_version}"
        ))
    })?;
    if abi != format!("python{major_minor}") {
        return Err(error(format!(
            "xtask/src/python/interpreter.rs: PYTHON_ABI = {abi}, but deps/pins.toml pins Python \
             {python_version}; update them together"
        )));
    }
    Ok(())
}

/// The text of each file that repeats the Rust toolchain pin.
struct RustPinCopies<'a> {
    toolchain: &'a str,
    mise: &'a str,
    manifest: &'a str,
}

/// Require every copy of deps/pins.toml `rust_version` to agree:
/// rust-toolchain.toml and mise.toml select that release, and the workspace
/// `rust-version` names it or its major.minor.
fn check_rust_version(pinned: &str, copies: &RustPinCopies<'_>) -> Result<()> {
    for (path, text, table, key) in [
        (
            "rust-toolchain.toml",
            copies.toolchain,
            "toolchain",
            "channel",
        ),
        ("mise.toml", copies.mise, "tools", "rust"),
    ] {
        let value = toml_string(path, text, &[table, key])?;
        if value != pinned {
            return Err(error(format!(
                "{path}: {key} = {value}, but deps/pins.toml pins {pinned}"
            )));
        }
    }
    let minimum = toml_string(
        "Cargo.toml",
        copies.manifest,
        &["workspace", "package", "rust-version"],
    )?;
    if minimum != pinned && Some(minimum.as_str()) != major_minor(pinned) {
        return Err(error(format!(
            "Cargo.toml: rust-version = {minimum}, but deps/pins.toml pins {pinned}"
        )));
    }
    Ok(())
}

/// The string at `keys` in the TOML document `text`, read from `path`.
fn toml_string(path: &str, text: &str, keys: &[&str]) -> Result<String> {
    let document: toml::Value =
        toml::from_str(text).map_err(|failure| error(format!("invalid {path}: {failure}")))?;
    keys.iter()
        .try_fold(&document, |value, key| value.get(key))
        .and_then(toml::Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| error(format!("{path}: missing {}", keys.join("."))))
}

fn check_archive_urls(pins: &Pins) -> Result<()> {
    for (name, pin) in &pins.sources {
        let Some(original) = &pin.original_url else {
            continue;
        };
        let expected = if let Some(rest) = original.strip_prefix("git+") {
            let (repo, revision) = rest
                .split_once('#')
                .ok_or_else(|| error("git dependency has no revision"))?;
            format!(
                "{}/archive/{revision}.tar.gz",
                repo.trim_end_matches(".git")
            )
        } else {
            original.clone()
        };
        if pin.url != expected {
            return Err(error(format!(
                "{name}: fetched URL differs from its source revision"
            )));
        }
    }
    Ok(())
}

fn check_source_versions(pins: &Pins) -> Result<()> {
    for (source, version_key) in [
        ("cpython", "python_version"),
        ("awscrt", "awscrt_commit"),
        ("musl", "musl_version"),
        ("linux_headers", "linux_version"),
        ("llvm_binary", "llvm_version"),
        ("llvm_binary_aarch64", "llvm_version"),
        ("llvm_source", "llvm_version"),
        ("cmake_source", "llvm_version"),
        ("third_party_source", "llvm_version"),
        ("compiler_rt_source", "llvm_version"),
    ] {
        let pin = pins
            .sources
            .get(source)
            .ok_or_else(|| error(format!("missing source {source}")))?;
        let version = pins.version(version_key)?;
        if !pin.url.contains(version) {
            return Err(error(format!("{source}: URL disagrees with {version_key}")));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests;
