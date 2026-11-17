//! Filesystem and environment operations shared by dependency builders.

use std::collections::BTreeMap;
use std::ffi::{OsStr, OsString};
use std::fs;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

use super::{Result, error};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CopyMode {
    Replace,
    Merge,
}

pub fn copy_tree(source: &Path, destination: &Path, mode: CopyMode) -> Result<()> {
    let source = fs::canonicalize(source)?;
    let destination = std::path::absolute(destination)?;
    let resolved = canonicalize_existing(&destination)?;
    if source.starts_with(&resolved) || resolved.starts_with(&source) {
        return Err(error("source and destination trees must not overlap"));
    }
    if mode == CopyMode::Replace {
        remove_path(&destination)?;
    }
    copy_entries(&source, &destination, Placement::Copy)
}

/// Merge `source` into `destination` with hard links, copying only where
/// the filesystem refuses a link, as the fallback stage publishes its phases.
///
/// A linked file shares its storage with `source`, so a later in-place
/// write to it through `destination` would change `source` too. Callers
/// link only files that nothing installed afterwards overwrites; each
/// destination file is removed before it is linked, never written through.
pub fn link_tree(source: &Path, destination: &Path) -> Result<()> {
    let source = fs::canonicalize(source)?;
    let destination = std::path::absolute(destination)?;
    let resolved = canonicalize_existing(&destination)?;
    if source.starts_with(&resolved) || resolved.starts_with(&source) {
        return Err(error("source and destination trees must not overlap"));
    }
    copy_entries(&source, &destination, Placement::Link)
}

/// Merge a DESTDIR staging tree into the prefix that contains it.
///
/// Unlike `copy_tree`, the prefix may enclose the staging tree; it must not
/// lie inside it, where copying would revisit its own output.
pub fn install_staged(staged: &Path, prefix: &Path) -> Result<()> {
    let staged = fs::canonicalize(staged)?;
    let prefix = std::path::absolute(prefix)?;
    if canonicalize_existing(&prefix)?.starts_with(&staged) {
        return Err(error(
            "an installation prefix must not lie inside its staging tree",
        ));
    }
    copy_entries(&staged, &prefix, Placement::Copy)
}

/// `path`, absolute, with its longest existing ancestor canonicalized and the
/// components that do not exist yet appended unchanged.
///
/// A tree being copied is canonical, so a destination compares with it only
/// once its symlinks resolve too: macOS's temporary directory, for one, is
/// `/var`, a link to `/private/var`.
fn canonicalize_existing(path: &Path) -> Result<PathBuf> {
    let mut missing = Vec::new();
    let mut existing = path;
    loop {
        match fs::canonicalize(existing) {
            Ok(canonical) => {
                return Ok(missing
                    .iter()
                    .rev()
                    .fold(canonical, |path, name| path.join(name)));
            }
            Err(failure) if failure.kind() == std::io::ErrorKind::NotFound => {
                let (Some(parent), Some(name)) = (existing.parent(), existing.file_name()) else {
                    return Err(failure.into());
                };
                missing.push(name);
                existing = parent;
            }
            Err(failure) => return Err(failure.into()),
        }
    }
}

fn remove_path(path: &Path) -> Result<()> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_dir() => fs::remove_dir_all(path)?,
        Ok(_) => fs::remove_file(path)?,
        Err(failure) if failure.kind() == std::io::ErrorKind::NotFound => {}
        Err(failure) => return Err(failure.into()),
    }
    Ok(())
}

/// How `copy_entries` places a regular file.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Placement {
    Copy,
    Link,
}

fn copy_entries(source: &Path, destination: &Path, placement: Placement) -> Result<()> {
    if fs::symlink_metadata(destination).is_ok_and(|metadata| !metadata.is_dir()) {
        remove_path(destination)?;
    }
    fs::create_dir_all(destination)?;
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let output = destination.join(entry.file_name());
        let kind = entry.file_type()?;
        if kind.is_dir() {
            copy_entries(&entry.path(), &output, placement)?;
        } else {
            remove_path(&output)?;
            if kind.is_symlink() {
                #[cfg(unix)]
                std::os::unix::fs::symlink(fs::read_link(entry.path())?, output)?;
                #[cfg(windows)]
                {
                    use std::os::windows::fs::FileTypeExt;
                    let target = fs::read_link(entry.path())?;
                    if kind.is_symlink_dir() {
                        std::os::windows::fs::symlink_dir(target, output)?;
                    } else {
                        std::os::windows::fs::symlink_file(target, output)?;
                    }
                }
            } else if kind.is_file() {
                if placement == Placement::Copy || fs::hard_link(entry.path(), &output).is_err() {
                    fs::copy(entry.path(), output)?;
                }
            } else {
                return Err(error(format!(
                    "unsupported source entry {}",
                    entry.path().display()
                )));
            }
        }
    }
    Ok(())
}

pub fn tool_environment(
    parent: impl IntoIterator<Item = (OsString, OsString)>,
    allowlist: &str,
) -> BTreeMap<OsString, OsString> {
    tool_environment_for_host(parent, allowlist, cfg!(windows))
}

/// The variable names of a tool `allowlist`: one per line, skipping blank
/// lines and `#` comments.
pub fn allowed_names(allowlist: &str) -> impl Iterator<Item = &str> {
    allowlist
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
}

fn tool_environment_for_host(
    parent: impl IntoIterator<Item = (OsString, OsString)>,
    allowlist: &str,
    windows: bool,
) -> BTreeMap<OsString, OsString> {
    let allowed: Vec<_> = allowed_names(allowlist).collect();
    let mut result: BTreeMap<_, _> = parent
        .into_iter()
        .filter(|(name, _)| {
            allowed.iter().any(|allowed| {
                name == *allowed
                    || (windows
                        && name
                            .to_str()
                            .is_some_and(|name| name.eq_ignore_ascii_case(allowed)))
            })
        })
        .collect();
    result.insert(OsString::from("LC_ALL"), OsString::from("C"));
    result
}

pub fn find_executable(search: &OsStr, names: &[&str]) -> Result<Option<PathBuf>> {
    find_executable_for_host(search, names, cfg!(windows))
}

fn find_executable_for_host(
    search: &OsStr,
    names: &[&str],
    windows: bool,
) -> Result<Option<PathBuf>> {
    // Bound the search against accidental or malformed PATH expansion.
    for (index, directory) in std::env::split_paths(search).enumerate() {
        if index >= 256 {
            return Err(error("executable search has more than 256 PATH entries"));
        }
        if directory.as_os_str().is_empty() {
            continue;
        }
        for name in names {
            for suffix in if windows {
                &[".exe", ".cmd", ".bat", ""][..]
            } else {
                &[""][..]
            } {
                let candidate = directory.join(format!("{name}{suffix}"));
                if fs::metadata(&candidate).is_ok_and(|metadata| {
                    #[cfg(unix)]
                    let executable = windows || metadata.permissions().mode() & 0o111 != 0;
                    #[cfg(windows)]
                    let executable = true;
                    metadata.is_file() && executable
                }) {
                    return Ok(Some(candidate));
                }
            }
        }
    }
    Ok(None)
}

pub fn glob_matches(pattern: &str, name: &str) -> bool {
    let (pattern, name) = (pattern.as_bytes(), name.as_bytes());
    let (mut p, mut n, mut star, mut retry) = (0, 0, None, 0);
    while n < name.len() {
        if pattern.get(p) == Some(&b'*') {
            star = Some(p);
            p += 1;
            retry = n;
        } else if pattern.get(p) == name.get(n) {
            p += 1;
            n += 1;
        } else if let Some(position) = star {
            retry += 1;
            n = retry;
            p = position + 1;
        } else {
            return false;
        }
    }
    while pattern.get(p) == Some(&b'*') {
        p += 1;
    }
    p == pattern.len()
}

pub fn prune_matching(directory: &Path, pattern: &str) -> Result<()> {
    let entries = match fs::read_dir(directory) {
        Ok(entries) => entries,
        Err(failure) if failure.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(failure) => return Err(failure.into()),
    };
    for entry in entries {
        let entry = entry?;
        if !entry.file_type()?.is_dir()
            && entry
                .file_name()
                .to_str()
                .is_some_and(|name| glob_matches(pattern, name))
        {
            fs::remove_file(entry.path())?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests;
