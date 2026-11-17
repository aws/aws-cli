use super::{delete_file_best_effort, path_holds_nul};
use std::{fs, io, path::Path};

/// Why a completed download could not be committed, and which of upstream's
/// calls failed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CommitFailure {
    /// The error's stable filesystem name.
    pub error: &'static str,
    /// Whether removing the destination failed, which upstream's Windows
    /// rename does first; otherwise the rename itself failed.
    pub removing_destination: bool,
}

/// Moves a completed download's temp file onto its destination, or deletes
/// it if that fails. On Windows, upstream first removes the destination,
/// ignoring one that is missing (s3transfer's `rename_file`), and its error
/// names the call that failed, so this makes the same two calls.
pub fn complete_downloaded_temp_file(temp: &Path, destination: &Path) -> Result<(), CommitFailure> {
    commit_temp_file(temp, destination, cfg!(windows))
}

pub(super) fn commit_temp_file(
    temp: &Path,
    destination: &Path,
    remove_destination: bool,
) -> Result<(), CommitFailure> {
    if path_holds_nul(destination) {
        delete_file_best_effort(temp);
        return Err(CommitFailure {
            error: crate::local_error::BAD_PATH_NAME,
            removing_destination: remove_destination,
        });
    }
    if remove_destination && let Err(error) = fs::remove_file(destination) {
        let error = delete_error_name(destination, &error);
        if error != crate::local_error::FILE_NOT_FOUND {
            delete_file_best_effort(temp);
            return Err(CommitFailure {
                error,
                removing_destination: true,
            });
        }
    }
    fs::rename(temp, destination).map_err(|error| {
        delete_file_best_effort(temp);
        CommitFailure {
            error: rename_error_name(&error),
            removing_destination: false,
        }
    })
}

#[cfg(unix)]
fn rename_error_name(error: &io::Error) -> &'static str {
    match error.raw_os_error() {
        Some(libc::EACCES) => crate::local_error::ACCESS_DENIED,
        Some(libc::EPERM) => crate::local_error::PERMISSION_DENIED,
        Some(libc::EBUSY) => crate::local_error::FILE_BUSY,
        Some(libc::EDQUOT) => crate::local_error::DISK_QUOTA,
        Some(libc::EISDIR) => crate::local_error::IS_DIR,
        Some(libc::EIO) => crate::local_error::INPUT_OUTPUT,
        Some(libc::ELOOP) => crate::local_error::SYM_LINK_LOOP,
        Some(libc::EMLINK) => crate::local_error::LINK_QUOTA_EXCEEDED,
        Some(libc::ENAMETOOLONG) => crate::local_error::NAME_TOO_LONG,
        Some(libc::ENOENT) => crate::local_error::FILE_NOT_FOUND,
        Some(libc::ENOTDIR) => crate::local_error::NOT_DIR,
        Some(libc::ENOMEM) => crate::local_error::SYSTEM_RESOURCES,
        Some(libc::ENOSPC) => crate::local_error::NO_SPACE_LEFT,
        Some(libc::EEXIST | libc::ENOTEMPTY) => crate::local_error::DIR_NOT_EMPTY,
        Some(libc::EROFS) => crate::local_error::READ_ONLY_FILE_SYSTEM,
        Some(libc::EXDEV) => crate::local_error::CROSS_DEVICE,
        Some(libc::EILSEQ) => crate::local_error::BAD_PATH_NAME,
        _ => crate::local_error::UNEXPECTED,
    }
}

/// The name of a failed removal's error, from what `unlinkat` reports.
/// Some systems refuse to unlink a directory with EPERM, which reads as the
/// directory it is.
#[cfg(unix)]
fn delete_error_name(path: &Path, error: &io::Error) -> &'static str {
    match error.raw_os_error() {
        Some(libc::EPERM)
            if !cfg!(target_os = "linux")
                && fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_dir()) =>
        {
            crate::local_error::IS_DIR
        }
        Some(libc::EPERM) => crate::local_error::PERMISSION_DENIED,
        Some(libc::EACCES) => crate::local_error::ACCESS_DENIED,
        Some(libc::EBUSY) => crate::local_error::FILE_BUSY,
        Some(libc::EIO) => crate::local_error::INPUT_OUTPUT,
        Some(libc::EISDIR) => crate::local_error::IS_DIR,
        Some(libc::ELOOP) => crate::local_error::SYM_LINK_LOOP,
        Some(libc::ENAMETOOLONG) => crate::local_error::NAME_TOO_LONG,
        Some(libc::ENOENT) => crate::local_error::FILE_NOT_FOUND,
        Some(libc::ENOTDIR) => crate::local_error::NOT_DIR,
        Some(libc::ENOMEM) => crate::local_error::SYSTEM_RESOURCES,
        Some(libc::EROFS) => crate::local_error::READ_ONLY_FILE_SYSTEM,
        Some(libc::EILSEQ) => crate::local_error::BAD_PATH_NAME,
        _ => crate::local_error::UNEXPECTED,
    }
}

#[cfg(windows)]
fn rename_error_name(error: &io::Error) -> &'static str {
    windows_error_name(error)
}

#[cfg(windows)]
fn delete_error_name(_: &Path, error: &io::Error) -> &'static str {
    windows_error_name(error)
}

#[cfg(windows)]
fn windows_error_name(error: &io::Error) -> &'static str {
    match error.raw_os_error() {
        Some(5) => crate::local_error::ACCESS_DENIED, // ERROR_ACCESS_DENIED
        // ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND
        Some(2 | 3) => crate::local_error::FILE_NOT_FOUND,
        Some(32) => crate::local_error::FILE_BUSY, // ERROR_SHARING_VIOLATION
        Some(17) => crate::local_error::CROSS_DEVICE, // ERROR_NOT_SAME_DEVICE
        Some(145) => crate::local_error::DIR_NOT_EMPTY, // ERROR_DIR_NOT_EMPTY
        Some(267) => crate::local_error::NOT_DIR,  // ERROR_DIRECTORY
        Some(206) => crate::local_error::NAME_TOO_LONG, // ERROR_FILENAME_EXCED_RANGE
        Some(112) => crate::local_error::NO_SPACE_LEFT, // ERROR_DISK_FULL
        _ => crate::local_error::UNEXPECTED,
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct RenameFailure {
    label: &'static str,
    code: u32,
    message: Vec<u8>,
    names_temp: bool,
}

/// `str()` of the OSError upstream's rename of a completed download raises.
/// On POSIX it is `os.rename(temp, destination)`'s, `[Errno N] strerror:
/// 'temp' -> 'destination'`, whose message is the C library's `strerror`,
/// which the native path shares with the embedded interpreter. Both paths
/// are absolute, as upstream's are, and the destination keeps a trailing
/// separator.
pub fn rename_error_text(
    cwd: &Path,
    failure: CommitFailure,
    temp: &Path,
    destination: &Path,
) -> Vec<u8> {
    #[cfg(windows)]
    let failure = windows_rename_failure(failure);
    #[cfg(not(windows))]
    let failure = posix_rename_failure(failure);
    rename_failure_text(cwd, failure, temp, destination)
}

#[cfg(not(windows))]
const RENAME_ERRNOS: [(&str, i32); 15] = [
    (crate::local_error::ACCESS_DENIED, libc::EACCES),
    (crate::local_error::PERMISSION_DENIED, libc::EPERM),
    (crate::local_error::DIR_NOT_EMPTY, libc::ENOTEMPTY),
    (crate::local_error::FILE_BUSY, libc::EBUSY),
    (crate::local_error::DISK_QUOTA, libc::EDQUOT),
    (crate::local_error::IS_DIR, libc::EISDIR),
    (crate::local_error::SYM_LINK_LOOP, libc::ELOOP),
    (crate::local_error::LINK_QUOTA_EXCEEDED, libc::EMLINK),
    (crate::local_error::NAME_TOO_LONG, libc::ENAMETOOLONG),
    (crate::local_error::FILE_NOT_FOUND, libc::ENOENT),
    (crate::local_error::NOT_DIR, libc::ENOTDIR),
    (crate::local_error::SYSTEM_RESOURCES, libc::ENOMEM),
    (crate::local_error::NO_SPACE_LEFT, libc::ENOSPC),
    (crate::local_error::READ_ONLY_FILE_SYSTEM, libc::EROFS),
    (crate::local_error::CROSS_DEVICE, libc::EXDEV),
];

#[cfg(not(windows))]
fn posix_rename_failure(failure: CommitFailure) -> RenameFailure {
    assert!(!failure.removing_destination);
    let errno = RENAME_ERRNOS
        .iter()
        .find(|(name, _)| *name == failure.error)
        .map_or(libc::EIO, |&(_, errno)| errno);
    RenameFailure {
        label: "Errno",
        code: errno.unsigned_abs(),
        message: super::directory_open::strerror(errno),
        names_temp: true,
    }
}

#[cfg(any(windows, test))]
type WindowsRenameError = (u32, &'static str);

/// The Windows error behind each rename error name. The messages are
/// Windows' English system messages, which CPython strips of their trailing
/// period (Python/errors.c).
#[cfg(any(windows, test))]
const WINDOWS_RENAME_ERRORS: [(&str, WindowsRenameError); 10] = [
    (crate::local_error::ACCESS_DENIED, (5, "Access is denied")), // ERROR_ACCESS_DENIED
    (
        crate::local_error::PERMISSION_DENIED,
        (5, "Access is denied"),
    ),
    (crate::local_error::IS_DIR, (5, "Access is denied")),
    (crate::local_error::DIR_NOT_EMPTY, (5, "Access is denied")),
    (
        crate::local_error::FILE_BUSY,
        (
            32, // ERROR_SHARING_VIOLATION
            "The process cannot access the file because it is being used by another process",
        ),
    ),
    (
        crate::local_error::FILE_NOT_FOUND,
        (2, "The system cannot find the file specified"),
    ), // ERROR_FILE_NOT_FOUND
    (
        crate::local_error::NOT_DIR,
        (267, "The directory name is invalid"),
    ), // ERROR_DIRECTORY
    (
        crate::local_error::CROSS_DEVICE,
        (
            17,
            "The system cannot move the file to a different disk drive",
        ), // ERROR_NOT_SAME_DEVICE
    ),
    (
        crate::local_error::NAME_TOO_LONG,
        (206, "The filename or extension is too long"),
    ), // ERROR_FILENAME_EXCED_RANGE
    (
        crate::local_error::NO_SPACE_LEFT,
        (112, "There is not enough space on the disk"),
    ), // ERROR_DISK_FULL
];

#[cfg(any(windows, test))]
fn windows_rename_failure(failure: CommitFailure) -> RenameFailure {
    let (code, message) = WINDOWS_RENAME_ERRORS
        .iter()
        .find(|(name, _)| *name == failure.error)
        .map_or(
            (
                1117, // ERROR_IO_DEVICE
                "The request could not be performed because of an I/O device error",
            ),
            |&(_, known)| known,
        );
    RenameFailure {
        label: "WinError",
        code,
        message: message.as_bytes().to_vec(),
        names_temp: !failure.removing_destination,
    }
}

fn rename_failure_text(
    cwd: &Path,
    failure: RenameFailure,
    temp: &Path,
    destination: &Path,
) -> Vec<u8> {
    let mut text = format!("[{} {}] ", failure.label, failure.code).into_bytes();
    text.extend_from_slice(&failure.message);
    text.extend_from_slice(b": ");
    if failure.names_temp {
        text.extend(absolute_repr(cwd, temp));
        text.extend_from_slice(b" -> ");
    }
    text.extend(absolute_repr(cwd, destination));
    text
}

fn absolute_repr(cwd: &Path, path: &Path) -> Vec<u8> {
    let absolute = crate::local_path::absolute_path(cwd, path);
    let mut spelled = absolute.as_os_str().as_encoded_bytes().to_vec();
    let ends_in_separator = |bytes: &[u8]| {
        bytes
            .last()
            .is_some_and(|&byte| std::path::is_separator(char::from(byte)))
    };
    if ends_in_separator(path.as_os_str().as_encoded_bytes()) && !ends_in_separator(&spelled) {
        spelled.extend_from_slice(std::path::MAIN_SEPARATOR_STR.as_bytes());
    }
    crate::mime::repr(&spelled)
}

#[cfg(test)]
mod tests;
