use std::path::{Path, PathBuf};

/// What a transfer does with the links it meets, upstream's `follow_symlinks`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub enum LinkPolicy {
    /// Follow every link, upstream's default and `--follow-symlinks`.
    #[default]
    Follow,
    /// `--no-follow-symlinks`, checked from the local operand.
    ///
    /// A walk names no link it lists, and nothing from a root that is a
    /// link to a directory; a single upload of a link names nothing. A
    /// download is skipped when its destination is a link or goes through
    /// one, from `root` down. A link above `root` is followed.
    Skip {
        /// The local operand as `abspath` spells it, which both of upstream's
        /// checks start from: no separator ends it but the filesystem root's.
        root: PathBuf,
    },
}
impl LinkPolicy {
    /// The policy `--follow-symlinks` chooses for the local operand `operand`.
    ///
    /// The operand is absolute, as the command normalized it; a separator
    /// after it is dropped.
    pub fn from_flag(follow_symlinks: bool, operand: &Path) -> Self {
        if follow_symlinks {
            Self::Follow
        } else {
            Self::Skip {
                root: crate::local_path::absolute_path(Path::new(""), operand),
            }
        }
    }
    /// Whether a walk drops the entry it listed at `path`, a symbolic link.
    pub fn drops(&self, path: &Path) -> bool {
        matches!(self, Self::Skip { .. }) && is_symlink(path)
    }
    /// Whether a single upload drops its source, the operand: a symbolic link.
    pub fn drops_operand(&self) -> bool {
        matches!(self, Self::Skip { root } if is_symlink(root))
    }
    /// Whether a walk names nothing from its root, a link to a directory.
    ///
    /// Upstream drops the separator its root ends in for the check only
    /// once that root is a directory, so a link to anything else is walked,
    /// and fails, as a followed one is.
    pub fn drops_root(&self) -> bool {
        matches!(self, Self::Skip { root } if is_directory(root) && is_symlink(root))
    }
    /// Whether a download to `destination` would follow a link it skips.
    ///
    /// This is upstream's `_find_link_in_dest_path`. The root is checked,
    /// then each directory below it on the way to `destination`, outermost
    /// first, then `destination`, so each path is examined only through
    /// paths that are not links. A parent reference below the root is never
    /// followed: no check can resolve one through a directory the download
    /// has yet to create. Nothing outside the root is checked.
    pub fn skips_download(&self, destination: &Path) -> bool {
        let Self::Skip { root } = self else {
            return false;
        };
        if is_link(root) {
            return true;
        }
        if !lies_below(root, destination) {
            return false;
        }
        let parents = parents_below(root, destination);
        parents.iter().rev().any(|parent| {
            crate::local_path::file_name(parent.as_os_str()) == b".." || is_link(parent)
        }) || is_link(destination)
    }
}

/// Whether `path` is a symbolic link, as `os.path.islink` decides.
///
/// A path that cannot be examined is none. On Windows only a symbolic
/// link's reparse tag counts, so a junction is no link.
fn is_symlink(path: &Path) -> bool {
    #[cfg(windows)]
    {
        windows::reparse_tag(path) == Some(windows::IO_REPARSE_TAG_SYMLINK)
    }
    #[cfg(not(windows))]
    {
        std::fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_symlink())
    }
}

/// Whether `path` redirects elsewhere, as s3handler's `is_link` decides.
///
/// A path that cannot be examined is none. On Windows that is a symbolic
/// link or a junction, the redirect a process without privileges can make.
fn is_link(path: &Path) -> bool {
    #[cfg(windows)]
    {
        matches!(
            windows::reparse_tag(path),
            Some(windows::IO_REPARSE_TAG_SYMLINK | windows::IO_REPARSE_TAG_MOUNT_POINT)
        )
    }
    #[cfg(not(windows))]
    {
        std::fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_symlink())
    }
}

fn is_directory(path: &Path) -> bool {
    std::fs::metadata(path).is_ok_and(|metadata| metadata.is_dir())
}

fn lies_below(root: &Path, destination: &Path) -> bool {
    let root = root.as_os_str().as_encoded_bytes();
    let separator = std::path::MAIN_SEPARATOR_STR.as_bytes();
    destination
        .as_os_str()
        .as_encoded_bytes()
        .strip_prefix(root)
        .is_some_and(|rest| root.ends_with(separator) || rest.starts_with(separator))
}

fn parents_below<'a>(root: &Path, destination: &'a Path) -> Vec<&'a Path> {
    let mut parents = Vec::new();
    let mut path = crate::local_path::dir_name(destination);
    while path.as_os_str() != root.as_os_str() {
        parents.push(path);
        let parent = crate::local_path::dir_name(path);
        if parent.as_os_str() == path.as_os_str() {
            break;
        }
        path = parent;
    }
    parents
}

#[cfg(windows)]
mod windows;

#[cfg(test)]
mod tests;
