//! The dependency cache roots a configuration owns, and pruning the rest.
//!
//! Stage prefixes are content-addressed, so every key change leaves the
//! previous generation behind in `target/deps/<TARGET>`, and a CI snapshot
//! restored from an older key carries all of them forward. `deps
//! --print-roots` names every prefix and scratch directory the selected
//! stages own, and `deps prune` removes every other entry.
//!
//! Prune reads the roots from files rather than keying the stages itself:
//! every key follows the toolchain's, and `toolchain` unpacks and checks the
//! pinned LLVM release before it returns one. `deps --print-roots` resolves
//! them through the build, and on a warm cache builds nothing.

use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, TryLockError};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use super::{Pins, Result, TARGET, archive_name, error, lock_path, source_dir};
use crate::file_lock::FileLock;

/// Where `cargo xtask ci deps` records the roots it prepared, for
/// `deps prune` to compact the CI snapshot to. It sits outside `target/deps`,
/// so no prune removes it.
pub const ROOTS_FILE: &str = "target/dependency-cache-roots.json";

const PRUNE_USAGE: &str =
    "usage: cargo xtask deps prune --roots=FILE [--roots=FILE...] [--sources] [--dry-run]";

/// The paths a configuration's stages own below `target/deps/<TARGET>`,
/// by name: each stage prefix under its label, such as `crt`, and each
/// scratch directory under its path there, such as `work/cpython/pgo`.
///
/// A root implies its `.lock` sibling, which `lock_stage` keeps beside it.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Roots(BTreeMap<String, PathBuf>);

impl Roots {
    /// Name `path` a root under `name`, such as a stage prefix under its label.
    pub fn insert(&mut self, name: impl Into<String>, path: PathBuf) {
        self.0.insert(name.into(), path);
    }

    /// Name the scratch directory `work` a root under its path below the
    /// target's dependency directory, such as `work/cpython/pgo`.
    pub fn insert_work(&mut self, root: &Path, work: PathBuf) {
        let name = work.strip_prefix(stage_dir(root)).map_or_else(
            |_| work.display().to_string(),
            |relative| {
                relative
                    .iter()
                    .map(|component| component.to_string_lossy())
                    .collect::<Vec<_>>()
                    .join("/")
            },
        );
        self.0.insert(name, work);
    }

    pub fn extend(&mut self, other: Self) {
        self.0.extend(other.0);
    }

    fn paths(&self) -> impl Iterator<Item = &Path> {
        self.0.values().map(PathBuf::as_path)
    }

    /// Write the roots as one line of JSON, the `--print-roots` format.
    pub fn write(&self, output: &mut impl Write) -> Result<()> {
        serde_json::to_writer(&mut *output, self)
            .map_err(|failure| error(format!("cannot encode dependency roots: {failure}")))?;
        output.write_all(b"\n")?;
        Ok(())
    }

    /// Record the roots at `path`, as `deps prune --roots` reads them.
    pub fn save(&self, path: &Path) -> Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let mut text = Vec::new();
        self.write(&mut text)?;
        fs::write(path, text)?;
        Ok(())
    }

    fn read(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path)
            .map_err(|failure| error(format!("{}: {failure}", path.display())))?;
        serde_json::from_str(&text)
            .map_err(|failure| error(format!("invalid roots file {}: {failure}", path.display())))
    }
}

/// The directory of this target's stage prefixes and scratch.
fn stage_dir(root: &Path) -> PathBuf {
    root.join("target/deps").join(TARGET)
}

/// The options of `deps prune`.
#[derive(Debug, Default, PartialEq, Eq)]
struct PruneOptions {
    /// The `--print-roots` outputs whose roots are kept; their union is.
    roots: Vec<PathBuf>,
    /// Also prune unpacked sources, archives, and download locks that no
    /// current pin names.
    sources: bool,
    /// List what would be removed without removing it.
    dry_run: bool,
}

fn prune_options(args: &[String]) -> Result<PruneOptions> {
    let mut options = PruneOptions::default();
    for arg in args {
        match arg.as_str() {
            "--sources" if !options.sources => options.sources = true,
            "--dry-run" if !options.dry_run => options.dry_run = true,
            _ => match arg.strip_prefix("--roots=") {
                Some(file) if !file.is_empty() => options.roots.push(PathBuf::from(file)),
                _ => {
                    return Err(error(format!(
                        "unknown or duplicate prune argument {arg}\n{PRUNE_USAGE}"
                    )));
                }
            },
        }
    }
    if options.roots.is_empty() {
        return Err(error(format!(
            "deps prune keeps only the roots it is given; pass the output of \
             `cargo xtask deps all --print-roots`\n{PRUNE_USAGE}"
        )));
    }
    Ok(options)
}

/// `cargo xtask deps prune`: remove every entry under `target/deps/<TARGET>`
/// that the given roots files neither name nor contain, and with
/// `--sources` every unpacked source, archive, and download lock no pin in
/// deps/pins.toml names.
///
/// An entry a running build holds the lock of, or any lock below it, is
/// skipped. Nothing outside `target` is removed, nor any other target's
/// prefixes. Outputs the roots do not name, such as another PGO mode's or
/// those `package consumers` keys on its own prefixes, are removed and
/// rebuild on next use; to keep both PGO modes, pass the roots of each.
///
/// Only a local store is pruned: one checkout's roots cannot name what the
/// other checkouts sharing a store use.
pub(super) fn prune(root: &Path, pins: &Pins, args: &[String]) -> Result<()> {
    if super::store::is_shared(root) {
        return Err(error(
            "deps prune compacts only a local store, since one checkout's roots cannot \
             name what the others use; run `deps gc` or `deps reset` on the shared store, \
             or set AWS_NATIVE_CACHE=local",
        ));
    }
    prune_reporting(root, pins, args, &mut io::stdout().lock())
}

/// `prune`, reporting each stale entry's outcome to `output`.
fn prune_reporting(
    root: &Path,
    pins: &Pins,
    args: &[String],
    output: &mut impl Write,
) -> Result<()> {
    let options = prune_options(args)?;
    // Each file is kept whole: the files of both PGO modes name different
    // prefixes under the same labels, such as `cpython`.
    let roots = options
        .roots
        .iter()
        .map(|file| Roots::read(file))
        .collect::<Result<Vec<_>>>()?;
    let live = live_paths(root, &roots)?;
    let mut stale = stale_entries(&stage_dir(root), &live)?;
    if options.sources {
        stale.extend(stale_sources(root, pins)?);
    }
    let target = root.join("target");
    if let Some(path) = stale
        .iter()
        .flat_map(|entry| &entry.paths)
        .find(|path| !path.starts_with(&target))
    {
        return Err(error(format!(
            "refusing to remove {} outside {}",
            path.display(),
            target.display()
        )));
    }
    let mut removed = 0;
    for entry in &stale {
        let outcome = if options.dry_run {
            "would remove"
        } else if remove(entry)? {
            removed += 1;
            "removed"
        } else {
            "skipped locked"
        };
        writeln!(output, "{outcome} {}", entry.paths[0].display())?;
    }
    if !options.dry_run {
        writeln!(output, "pruned {removed} of {} stale entries", stale.len())?;
    }
    Ok(())
}

/// The union of the paths every one of `roots` keeps. Every one must lie
/// in this checkout's `target` and one at least in its stage directory, so
/// a roots file from another checkout or the system CRT's cannot empty the
/// cache.
fn live_paths(root: &Path, roots: &[Roots]) -> Result<BTreeSet<PathBuf>> {
    let paths: BTreeSet<PathBuf> = roots
        .iter()
        .flat_map(Roots::paths)
        .map(Path::to_owned)
        .collect();
    let target = root.join("target");
    if let Some(outside) = paths.iter().find(|path| !path.starts_with(&target)) {
        return Err(error(format!(
            "dependency root {} lies outside {}",
            outside.display(),
            target.display()
        )));
    }
    let stages = stage_dir(root);
    if !paths.iter().any(|path| path.starts_with(&stages)) {
        return Err(error(format!(
            "no dependency root lies in {}; pass the roots `deps --print-roots` \
             prints in this checkout",
            stages.display()
        )));
    }
    Ok(paths)
}

/// Entries a prune removes together, under the lock their builder holds.
#[derive(Clone, Debug, PartialEq, Eq)]
struct Stale {
    /// The lock taken, without waiting, before any path is removed, with
    /// every lock below the paths, as `remove` finds them.
    lock: Option<PathBuf>,
    /// The paths removed, in order: an entry before its own lock.
    paths: Vec<PathBuf>,
}

/// The entries below `directory` that are not in `live` and contain no
/// path in `live`, with the locks that guard them.
///
/// A live path keeps its `.lock` sibling. A stale entry's lock is removed
/// with it, and one whose entry is gone or still contains a live path is
/// removed alone. A directory that contains a live path is searched rather
/// than removed, as `work` is for `work/crt`. A missing `directory` has no
/// stale entries.
fn stale_entries(directory: &Path, live: &BTreeSet<PathBuf>) -> Result<Vec<Stale>> {
    let mut stale = Vec::new();
    collect_stale(directory, live, &mut stale)?;
    Ok(stale)
}

fn collect_stale(directory: &Path, live: &BTreeSet<PathBuf>, stale: &mut Vec<Stale>) -> Result<()> {
    let entries = match fs::read_dir(directory) {
        Ok(entries) => entries,
        Err(failure) if failure.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(failure) => return Err(failure.into()),
    };
    let mut paths = BTreeSet::new();
    for entry in entries {
        paths.insert(entry?.path());
    }
    for path in &paths {
        if live.contains(path) {
            continue;
        }
        if let Some(base) = lock_base(path) {
            // A live stage keeps its lock, and a stale one takes it along.
            if live.contains(&base) || (paths.contains(&base) && !contains_live(&base, live)?) {
                continue;
            }
            stale.push(Stale {
                lock: Some(path.clone()),
                paths: vec![path.clone()],
            });
        } else if contains_live(path, live)? {
            collect_stale(path, live, stale)?;
        } else {
            let lock = lock_path(path);
            stale.push(if paths.contains(&lock) {
                Stale {
                    lock: Some(lock.clone()),
                    paths: vec![path.clone(), lock],
                }
            } else {
                Stale {
                    lock: None,
                    paths: vec![path.clone()],
                }
            });
        }
    }
    Ok(())
}

/// The path `lock_stage` guards with the lock file `path`, if it is one.
pub(super) fn lock_base(path: &Path) -> Option<PathBuf> {
    let name = path.file_name()?.to_str()?.strip_suffix(".lock")?;
    (!name.is_empty()).then(|| path.with_file_name(name))
}

/// Whether `path` is a directory, not a link to one, below which `live`
/// names a path.
fn contains_live(path: &Path, live: &BTreeSet<PathBuf>) -> Result<bool> {
    if !live
        .iter()
        .any(|kept| kept != path && kept.starts_with(path))
    {
        return Ok(false);
    }
    Ok(fs::symlink_metadata(path)?.is_dir())
}

/// The unpacked sources, archives, and download locks of `target` that no
/// pin names, as `source` and `download` name them. Only the checkout's own
/// `target/downloads` is pruned, never an `AWS_NATIVE_DISTFILES` directory.
///
/// The x86_64 LLVM release unpacks under `target/toolchain`, and only that
/// unpack keeps it, since `source` deletes its archive, so CI snapshots the
/// directory and a superseded release is pruned like any other source.
fn stale_sources(root: &Path, pins: &Pins) -> Result<Vec<Stale>> {
    let downloads = root.join("target/downloads");
    let locks = root.join("target/download-locks");
    let toolchain = root.join("target/toolchain");
    let (mut sources, mut archives, mut downloading) =
        (BTreeSet::new(), BTreeSet::new(), BTreeSet::new());
    for (name, pin) in &pins.sources {
        sources.insert(source_dir(root, name, pin));
        archives.insert(downloads.join(archive_name(&pin.sha256, &pin.url)));
        // `download` still adopts an archive saved under its pin name.
        archives.insert(downloads.join(archive_name(name, &pin.url)));
        downloading.insert(locks.join(&pin.sha256));
    }
    let mut stale = stale_entries(&root.join("target/sources"), &sources)?;
    stale.extend(stale_entries(&toolchain, &sources)?);
    // An archive, and a download's `.part` file, are guarded by the lock of
    // the digest that begins their name, which is never removed with them.
    for mut entry in stale_entries(&downloads, &archives)? {
        entry.lock = entry.paths[0]
            .file_name()
            .and_then(|name| name.to_str()?.split('.').next())
            .map(|digest| lock_path(&locks.join(digest)))
            .filter(|lock| lock.is_file());
        stale.push(entry);
    }
    stale.extend(stale_entries(&locks, &downloading)?);
    Ok(stale)
}

/// Remove `stale`'s paths under its lock and every lock below them, or
/// report that a build holds one.
///
/// A stale directory can hold the lock of a running build without a lock
/// of its own, as `work/cpython` holds `work/cpython/pgo.lock` when the
/// roots name only the CRT's scratch.
fn remove(stale: &Stale) -> Result<bool> {
    let mut locks = Vec::from_iter(stale.lock.clone());
    for path in &stale.paths {
        locks_below(path, &mut locks)?;
    }
    let mut _held = Vec::with_capacity(locks.len());
    for lock in &locks {
        match FileLock::try_lock(lock) {
            Ok(guard) => _held.push(guard),
            Err(TryLockError::WouldBlock) => return Ok(false),
            Err(TryLockError::Error(failure)) => return Err(failure.into()),
        }
    }
    // Removing a lock file while it is held lets a builder already waiting
    // on it proceed on the unlinked file. Only a build of a superseded key
    // waits on a stale lock, and it rebuilds the prefix it finds gone.
    for path in &stale.paths {
        match fs::symlink_metadata(path) {
            Ok(metadata) if metadata.is_dir() => fs::remove_dir_all(path)?,
            Ok(_) => fs::remove_file(path)?,
            Err(failure) if failure.kind() == io::ErrorKind::NotFound => {}
            Err(failure) => return Err(failure.into()),
        }
    }
    Ok(true)
}

/// Add to `locks` every lock file below `path`, if it is a directory, not
/// a link to one.
fn locks_below(path: &Path, locks: &mut Vec<PathBuf>) -> Result<()> {
    let entries = match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_dir() => fs::read_dir(path)?,
        Ok(_) => return Ok(()),
        Err(failure) if failure.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(failure) => return Err(failure.into()),
    };
    for entry in entries {
        let entry = entry?;
        let file_type = entry.file_type()?;
        if file_type.is_dir() {
            locks_below(&entry.path(), locks)?;
        } else if file_type.is_file() && lock_base(&entry.path()).is_some() {
            locks.push(entry.path());
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests;
