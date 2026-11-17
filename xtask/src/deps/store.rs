//! The dependency store every checkout of a user shares, and its cleanup.
//!
//! Managed dependency builds live in one store per user, `v1` in
//! `$AWS_NATIVE_CACHE_DIR` or by default in `aws-cli-native/build` under the
//! user's cache directory: `$XDG_CACHE_HOME` or `~/.cache`, and
//! `%LOCALAPPDATA%` on Windows. It holds the downloads and their locks, the
//! unpacked sources, the LLVM builds under `toolchain`, and every stage prefix
//! under `deps/<TARGET>`, each beside its `.lock`. Every checkout resolves the
//! same canonical store, so a checkout whose stage inputs match another's
//! reuses that stage. A stage builds at its permanent prefix, whose path its
//! outputs embed, under its lock, and is reused once its `.complete` marker is
//! written. Cargo output, the stages' scratch (`target/deps/<TARGET>/work`),
//! and the captured MSVC environment stay in each checkout's `target`.
//!
//! `AWS_NATIVE_CACHE=local` keeps the store in the checkout's `target`, the
//! layout CI snapshots, as does a host with no cache directory to default to.
//!
//! A stage's lock ends once its prefix is resolved, before Cargo reads it, so
//! every xtask command except `deps reset` also holds the store's lock shared
//! until it returns, after the builds and tests it runs exit.
//!
//! - `cargo xtask deps gc [--days=N] [--dry-run]` removes every entry unused
//!   for N days, 30 by default, including those of deleted checkouts. Each
//!   build or reuse of an entry sets its lock file's modification time. An
//!   entry whose lock is held is skipped, and no lock file is removed, since a
//!   build may be waiting on it.
//! - `cargo xtask deps reset PATH...|--all` removes the named entries, or the
//!   whole store, at once, and refuses while any other command holds the
//!   store.
//! - `cargo xtask deps prune` compacts only a local store: one checkout's
//!   roots cannot name what the others use.
//!
//! What the store cannot detect is recovered by stopping running builds,
//! `deps reset` of the entry, and a rebuild: a builder process that outlived
//! its killed xtask and kept writing a prefix, an edit to an input that
//! `deps::inputs` does not list, which publishes an entry other checkouts
//! then reuse, and a power loss during a build.

use std::ffi::{OsStr, OsString};
use std::fmt::Display;
use std::fs::{self, TryLockError};
use std::io::{self, Write};
use std::path::{Component, Path, PathBuf};
use std::sync::OnceLock;
use std::time::{Duration, SystemTime};

use super::roots::lock_base;
use super::{Result, error};
use crate::TaskError;
use crate::file_lock::FileLock;

/// The variable that selects the store: `shared`, the default, or `local`.
const MODE: &str = "AWS_NATIVE_CACHE";

/// The variable that names the shared store's directory in place of the
/// default in the user's cache directory. Prefixes embed paths in the store,
/// so builds that set it alike reuse each other's stages from any checkout.
const DIRECTORY: &str = "AWS_NATIVE_CACHE_DIR";

/// The shared store's layout version, which names its directory. A layout
/// change takes a new version, which starts empty.
const VERSION: &str = "v1";

/// The store directories a local store's `--all` reset removes; the rest of
/// `target` is Cargo's.
const MANAGED: &[&str] = &[
    "downloads",
    "download-locks",
    "sources",
    "toolchain",
    "deps",
];

/// How long `deps gc` keeps an unused entry without `--days`.
const DEFAULT_DAYS: u64 = 30;

const SECONDS_PER_DAY: u64 = 24 * 60 * 60;

const GC_USAGE: &str = "usage: cargo xtask deps gc [--days=N] [--dry-run]";
const RESET_USAGE: &str = "usage: cargo xtask deps reset PATH... | --all";

/// Where a checkout's managed dependency builds live.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Store {
    /// The directory of `downloads`, `download-locks`, `sources`,
    /// `toolchain`, and `deps`.
    pub(super) directory: PathBuf,
    /// The lock every command but `deps reset` holds shared. A reset never
    /// unlinks it: the shared store's sits beside `directory`, and a reset
    /// refuses the local store's, which `target` holds.
    lock: PathBuf,
    pub(super) kind: Kind,
}

/// Whether a store serves every checkout of a user or one checkout.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Kind {
    Shared,
    Local,
}

/// The store of the checkout at `root`.
///
/// `hold` reports a store that cannot be used before any command resolves a
/// path; here one selects the local store.
pub(super) fn resolve(root: &Path) -> Store {
    current(root).unwrap_or_else(|_| local(root))
}

/// Whether the store of `root` is the shared store.
pub(super) fn is_shared(root: &Path) -> bool {
    resolve(root).kind == Kind::Shared
}

/// The store of `root`, or why the one the environment selects cannot be
/// used.
///
/// It is resolved once per invocation, so every path in it is spelled alike.
fn current(root: &Path) -> Result<Store> {
    // Unit tests build stages in temporary checkouts, each of which keeps
    // them in its own `target` rather than in the user's cache.
    if cfg!(test) {
        return Ok(local(root));
    }
    static RESOLVED: OnceLock<(PathBuf, std::result::Result<Store, String>)> = OnceLock::new();
    let selected =
        || locate(root, |name| std::env::var_os(name)).map_err(|failure| failure.to_string());
    let (resolved, store) = RESOLVED.get_or_init(|| (root.to_owned(), selected()));
    if resolved == root {
        store.clone()
    } else {
        selected()
    }
    .map_err(error)
}

/// The store that the environment, read through `variable`, selects for the
/// checkout at `root`: the local store, or the shared store in
/// `AWS_NATIVE_CACHE_DIR` or else the user's cache directory, which is
/// created. A host with no cache directory keeps the local store.
fn locate(root: &Path, variable: impl Fn(&str) -> Option<OsString>) -> Result<Store> {
    let directory = variable(DIRECTORY).filter(|value| !value.is_empty());
    match (kind(variable(MODE))?, directory) {
        (Kind::Local, None) => Ok(local(root)),
        (Kind::Local, Some(_)) => Err(error(format!(
            "{MODE}=local keeps dependencies in target, so {DIRECTORY} must be unset"
        ))),
        (Kind::Shared, Some(directory)) => {
            let directory = PathBuf::from(directory);
            if !directory.is_absolute() {
                return Err(error(format!(
                    "{DIRECTORY} must be an absolute path, not {}",
                    directory.display()
                )));
            }
            shared(&directory)
        }
        (Kind::Shared, None) => {
            cache_directory(variable).map_or_else(|| Ok(local(root)), |cache| shared(&cache))
        }
    }
}

fn kind(value: Option<OsString>) -> Result<Kind> {
    match value {
        None => Ok(Kind::Shared),
        Some(value) if value.is_empty() || value == "shared" => Ok(Kind::Shared),
        Some(value) if value == "local" => Ok(Kind::Local),
        Some(value) => Err(error(format!(
            "{MODE} must be `shared` or `local`, not `{}`",
            value.to_string_lossy()
        ))),
    }
}

/// The shared store's default directory, `aws-cli-native/build` in the user's
/// cache directory: `%LOCALAPPDATA%` on Windows, and elsewhere
/// `$XDG_CACHE_HOME`, else `~/.cache`. A relative path is ignored, as the XDG
/// specification requires of `XDG_CACHE_HOME`.
///
/// `build` keeps these dependency builds apart from anything the CLI caches
/// as it runs.
fn cache_directory(variable: impl Fn(&str) -> Option<OsString>) -> Option<PathBuf> {
    let absolute = |name| {
        variable(name)
            .map(PathBuf::from)
            .filter(|path| path.is_absolute())
    };
    let cache = if cfg!(windows) {
        absolute("LOCALAPPDATA")?
    } else {
        absolute("XDG_CACHE_HOME").or_else(|| Some(absolute("HOME")?.join(".cache")))?
    };
    Some(cache.join("aws-cli-native").join("build"))
}

/// The shared store in `directory`, created, then canonicalized so every
/// checkout spells its paths alike: the `cpython` and fallback keys hash the
/// paths of the stages before them.
fn shared(directory: &Path) -> Result<Store> {
    fs::create_dir_all(directory).map_err(|failure| unopened(directory, failure))?;
    let directory =
        canonical(directory).ok_or_else(|| unopened(directory, "its path cannot be resolved"))?;
    Ok(Store {
        directory: directory.join(VERSION),
        lock: directory.join(format!("{VERSION}.lock")),
        kind: Kind::Shared,
    })
}

/// The local store, in the `target` of the checkout at `root`.
fn local(root: &Path) -> Store {
    let target = root.join("target");
    Store {
        lock: target.join("xtask-cache.lock"),
        directory: target,
        kind: Kind::Local,
    }
}

/// `path` with every link resolved, so each checkout spells it alike.
///
/// Windows resolves a path to its verbatim form, `\\?\C:\...`, which
/// cmd.exe, nmake, and CMake misread, so a drive path drops the prefix and
/// any other verbatim path is refused.
fn canonical(path: &Path) -> Option<PathBuf> {
    let resolved = fs::canonicalize(path).ok()?;
    if !cfg!(windows) {
        return Some(resolved);
    }
    match resolved.to_str()?.strip_prefix(r"\\?\") {
        None => Some(resolved),
        Some(plain) if plain.as_bytes().get(1) == Some(&b':') => Some(PathBuf::from(plain)),
        Some(_) => None,
    }
}

/// Hold the store of `root` shared until the guard drops, first waiting out
/// a `deps reset`.
///
/// # Errors
/// Rejects an invalid `AWS_NATIVE_CACHE` or `AWS_NATIVE_CACHE_DIR`, and
/// reports a store that cannot be created or locked.
pub(super) fn hold(root: &Path) -> Result<FileLock> {
    let store = current(root)?;
    if let Some(parent) = store.lock.parent() {
        fs::create_dir_all(parent).map_err(|failure| unopened(&store.directory, failure))?;
    }
    match FileLock::try_lock_shared(&store.lock) {
        Ok(lock) => Ok(lock),
        Err(TryLockError::WouldBlock) => {
            writeln!(
                io::stderr().lock(),
                "xtask: waiting for `deps reset` to finish with {}",
                store.directory.display()
            )?;
            FileLock::lock_shared(&store.lock)
                .map_err(|failure| unopened(&store.directory, failure))
        }
        Err(TryLockError::Error(failure)) => Err(unopened(&store.directory, failure)),
    }
}

fn unopened(directory: &Path, failure: impl Display) -> TaskError {
    error(format!(
        "cannot open the dependency store {}: {failure}; set {DIRECTORY} to another \
         directory, or {MODE}=local to keep dependencies in target",
        directory.display()
    ))
}

/// The options of `deps gc`.
#[derive(Debug, PartialEq, Eq)]
struct GcOptions {
    /// How many days an entry may go unused before it is removed.
    days: u64,
    /// List what would be removed without removing it.
    dry_run: bool,
}

fn gc_options(args: &[String]) -> Result<GcOptions> {
    let (mut days, mut dry_run) = (None, false);
    for arg in args {
        if arg == "--dry-run" && !dry_run {
            dry_run = true;
            continue;
        }
        match arg.strip_prefix("--days=").map(str::parse::<u64>) {
            Some(Ok(value)) if days.is_none() && value >= 1 => days = Some(value),
            _ => {
                return Err(error(format!(
                    "unknown, duplicate, or invalid gc argument {arg}; --days is at \
                     least 1, since `deps reset` removes entries at once\n{GC_USAGE}"
                )));
            }
        }
    }
    Ok(GcOptions {
        days: days.unwrap_or(DEFAULT_DAYS),
        dry_run,
    })
}

/// `cargo xtask deps gc`: remove every store entry whose lock was last set
/// longer ago than the window, reporting each to stdout.
///
/// It runs beside builds, which `dispatch`'s shared hold on the store
/// allows. Each idle entry's lock is taken without waiting, and the entry is
/// removed only if it is still idle then; its lock file is kept. An entry
/// is used whenever a build resolves it or an option such as `--crt-prefix`
/// names it (see `deps::register_input`), so only a command that has run
/// for longer than the window can lose an entry it read.
pub(super) fn gc(root: &Path, args: &[String]) -> Result<()> {
    let options = gc_options(args)?;
    let store = current(root)?;
    let window = Duration::from_secs(options.days.saturating_mul(SECONDS_PER_DAY));
    let mut output = io::stdout().lock();
    let (mut idle, mut removed) = (0, 0);
    for lock in entry_locks(&store.directory)? {
        if !unused(&lock, window)? || guarded(&store.directory, &lock)?.is_empty() {
            continue;
        }
        idle += 1;
        if options.dry_run {
            for path in guarded(&store.directory, &lock)? {
                writeln!(output, "would remove {}", path.display())?;
            }
            continue;
        }
        let _held = match FileLock::try_lock(&lock) {
            Ok(held) => held,
            Err(TryLockError::WouldBlock) => {
                writeln!(output, "skipped locked {}", lock.display())?;
                continue;
            }
            Err(TryLockError::Error(failure)) => return Err(failure.into()),
        };
        // A build may have used the entry between the scan and the lock.
        if !unused(&lock, window)? {
            continue;
        }
        for path in guarded(&store.directory, &lock)? {
            remove(&path)?;
            writeln!(output, "removed {}", path.display())?;
        }
        removed += 1;
    }
    if options.dry_run {
        writeln!(
            output,
            "would remove {idle} entries unused for {} days",
            options.days
        )?;
    } else {
        writeln!(
            output,
            "removed {removed} of {idle} entries unused for {} days",
            options.days
        )?;
    }
    Ok(())
}

/// Every entry lock in the store `directory`: the downloads', the unpacked
/// sources' and LLVM builds', and each target's stage prefixes'.
fn entry_locks(directory: &Path) -> Result<Vec<PathBuf>> {
    let mut parents = vec![
        directory.join("download-locks"),
        directory.join("sources"),
        directory.join("toolchain"),
    ];
    for path in entries(&directory.join("deps"))? {
        if fs::symlink_metadata(&path)?.is_dir() {
            parents.push(path);
        }
    }
    let mut locks = Vec::new();
    for parent in parents {
        for path in entries(&parent)? {
            if lock_base(&path).is_some() && fs::symlink_metadata(&path)?.is_file() {
                locks.push(path);
            }
        }
    }
    locks.sort();
    Ok(locks)
}

/// The paths in `directory`, or none if it is absent.
fn entries(directory: &Path) -> Result<Vec<PathBuf>> {
    match fs::read_dir(directory) {
        Ok(entries) => entries.map(|entry| Ok(entry?.path())).collect(),
        Err(failure) if failure.kind() == io::ErrorKind::NotFound => Ok(Vec::new()),
        Err(failure) => Err(failure.into()),
    }
}

/// Whether the entry `lock` guards was last used longer than `window` ago.
fn unused(lock: &Path, window: Duration) -> Result<bool> {
    let modified = fs::metadata(lock)?.modified()?;
    Ok(SystemTime::now()
        .duration_since(modified)
        .is_ok_and(|age| age > window))
}

/// The existing paths the entry lock `lock` guards: the prefix, unpacked
/// source, or LLVM build beside it, or for a download lock, the archive and
/// any partial download its digest names.
fn guarded(directory: &Path, lock: &Path) -> Result<Vec<PathBuf>> {
    let Some(base) = lock_base(lock) else {
        return Ok(Vec::new());
    };
    if lock.parent() == Some(directory.join("download-locks").as_path()) {
        let Some(digest) = base.file_name().and_then(OsStr::to_str) else {
            return Ok(Vec::new());
        };
        let stem = format!("{digest}.");
        return Ok(entries(&directory.join("downloads"))?
            .into_iter()
            .filter(|path| {
                path.file_name()
                    .and_then(OsStr::to_str)
                    .is_some_and(|name| name.starts_with(&stem))
            })
            .collect());
    }
    Ok(Vec::from_iter(
        fs::symlink_metadata(&base).is_ok().then_some(base),
    ))
}

/// Remove the file or directory at `path`, reporting whether it existed.
fn remove(path: &Path) -> Result<bool> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_dir() => fs::remove_dir_all(path)?,
        Ok(_) => fs::remove_file(path)?,
        Err(failure) if failure.kind() == io::ErrorKind::NotFound => return Ok(false),
        Err(failure) => return Err(failure.into()),
    }
    Ok(true)
}

/// `cargo xtask deps reset`: remove the named store entries, or with
/// `--all` the whole store, reporting each removal to stdout.
///
/// It takes the store's lock exclusively without waiting, so it fails while
/// any other command holds the store; no build is then reading, building,
/// or waiting on an entry it removes.
pub(super) fn reset(root: &Path, args: &[String]) -> Result<()> {
    let store = current(root)?;
    let paths = reset_paths(&store, args)?;
    if let Some(parent) = store.lock.parent() {
        fs::create_dir_all(parent)?;
    }
    let _exclusive = match FileLock::try_lock(&store.lock) {
        Ok(lock) => lock,
        Err(TryLockError::WouldBlock) => {
            return Err(error("busy: stop running builds, then reset"));
        }
        Err(TryLockError::Error(failure)) => return Err(failure.into()),
    };
    let mut output = io::stdout().lock();
    for path in paths {
        if remove(&path)? {
            writeln!(output, "removed {}", path.display())?;
        }
    }
    Ok(())
}

/// What `deps reset` removes for `args`: with `--all` the store's
/// directories, otherwise each PATH, absolute or relative to the store,
/// which must name an existing path inside it that no link leads to.
fn reset_paths(store: &Store, args: &[String]) -> Result<Vec<PathBuf>> {
    if matches!(args, [all] if all == "--all") {
        return Ok(match store.kind {
            Kind::Shared => vec![store.directory.clone()],
            Kind::Local => MANAGED
                .iter()
                .map(|name| store.directory.join(name))
                .collect(),
        });
    }
    if args.is_empty() || args.iter().any(|arg| arg.starts_with("--")) {
        return Err(error(RESET_USAGE));
    }
    args.iter().map(|arg| reset_path(store, arg)).collect()
}

/// The path the `deps reset` argument `arg` names.
///
/// Only the path itself may be a link, which is removed rather than followed:
/// a link among its parents, such as a stage scratch directory's link to its
/// unpacked source, may lead into another store, whose lock this reset does
/// not hold.
fn reset_path(store: &Store, arg: &str) -> Result<PathBuf> {
    // Rebuilt from its components, `link/` and `link/.` name the link
    // itself rather than the directory the system would follow it to.
    let path: PathBuf = store.directory.join(arg).components().collect();
    let Some(parent) = path
        .strip_prefix(&store.directory)
        .ok()
        .filter(|relative| {
            relative.components().next().is_some()
                && relative
                    .components()
                    .all(|component| matches!(component, Component::Normal(_)))
        })
        // A local store holds its own lock, which waiting commands have open.
        .filter(|_| path != store.lock)
        .and_then(Path::parent)
    else {
        return Err(error(format!(
            "{arg} names no entry of the dependency store {}\n{RESET_USAGE}",
            store.directory.display()
        )));
    };
    if fs::symlink_metadata(&path).is_err() {
        return Err(error(format!("{} does not exist", path.display())));
    }
    let unlinked = canonical(&store.directory)
        .zip(path.parent().and_then(canonical))
        .is_some_and(|(directory, resolved)| directory.join(parent) == resolved);
    if !unlinked {
        return Err(error(format!(
            "{} is reached through a link, which may lead out of the dependency store",
            path.display()
        )));
    }
    Ok(path)
}

/// The store entry of `root` that holds `path` once its links are resolved:
/// a stage prefix, unpacked source, or LLVM build. A path outside every
/// entry, or one that does not exist, has none.
pub(super) fn entry(root: &Path, path: &Path) -> Result<Option<PathBuf>> {
    let directory = resolve(root).directory;
    let (Some(directory), Some(path)) = (canonical(&directory), canonical(path)) else {
        return Ok(None);
    };
    if !path.starts_with(&directory) {
        return Ok(None);
    }
    Ok(entry_locks(&directory)?.into_iter().find_map(|lock| {
        let base = lock_base(&lock)?;
        path.starts_with(&base).then_some(base)
    }))
}

#[cfg(test)]
mod tests;
