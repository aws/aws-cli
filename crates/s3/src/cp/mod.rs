//! Native copy command boundaries and transfer result rendering.
pub use crate::cp_args::{Args, admit};
pub mod backstop;
mod native;
mod producer;
pub mod recursive;
mod runner;
pub use native::run;
pub(crate) use native::{CopyMode, load_settings, prepare_runtime, run_copy, run_request};

/// Stable filesystem error names used in user-visible native diagnostics. An
/// OS error is named by its errno, for the errnos named alike whichever call
/// reports them; an errno a call names its own way (such as `EIO`, `EINVAL`
/// or `ESPIPE`) is named where that call is made. Any other error is named
/// by its kind.
pub fn io_error_name(error: &std::io::Error) -> &'static str {
    #[cfg(unix)]
    if let Some(name) = error.raw_os_error().and_then(errno_name) {
        return name;
    }
    use std::io::ErrorKind;
    match error.kind() {
        ErrorKind::NotFound => crate::local_error::FILE_NOT_FOUND,
        ErrorKind::PermissionDenied => crate::local_error::ACCESS_DENIED,
        ErrorKind::AlreadyExists => crate::local_error::PATH_ALREADY_EXISTS,
        ErrorKind::NotADirectory => crate::local_error::NOT_DIR,
        ErrorKind::IsADirectory => crate::local_error::IS_DIR,
        ErrorKind::InvalidInput => crate::local_error::INVALID_ARGUMENT,
        ErrorKind::StorageFull => crate::local_error::NO_SPACE_LEFT,
        ErrorKind::ReadOnlyFilesystem => crate::local_error::READ_ONLY_FILE_SYSTEM,
        ErrorKind::FileTooLarge => crate::local_error::FILE_TOO_BIG,
        ErrorKind::WriteZero => crate::local_error::WRITE_ZERO,
        _ => crate::local_error::UNEXPECTED,
    }
}
#[cfg(unix)]
fn errno_name(errno: i32) -> Option<&'static str> {
    Some(match errno {
        libc::EACCES => crate::local_error::ACCESS_DENIED,
        libc::EPERM => crate::local_error::PERMISSION_DENIED,
        libc::EDQUOT => crate::local_error::DISK_QUOTA,
        libc::EEXIST => crate::local_error::PATH_ALREADY_EXISTS,
        libc::EFBIG => crate::local_error::FILE_TOO_BIG,
        libc::EILSEQ => crate::local_error::BAD_PATH_NAME,
        libc::EISDIR => crate::local_error::IS_DIR,
        libc::ELOOP => crate::local_error::SYM_LINK_LOOP,
        libc::EMFILE => crate::local_error::PROCESS_FD_QUOTA_EXCEEDED,
        libc::EMLINK => crate::local_error::LINK_QUOTA_EXCEEDED,
        libc::ENAMETOOLONG => crate::local_error::NAME_TOO_LONG,
        libc::ENFILE => crate::local_error::SYSTEM_FD_QUOTA_EXCEEDED,
        libc::ENOENT => crate::local_error::FILE_NOT_FOUND,
        libc::ENOMEM => crate::local_error::SYSTEM_RESOURCES,
        libc::ENOSPC => crate::local_error::NO_SPACE_LEFT,
        libc::ENOTDIR => crate::local_error::NOT_DIR,
        libc::EROFS => crate::local_error::READ_ONLY_FILE_SYSTEM,
        libc::ETXTBSY => crate::local_error::FILE_BUSY,
        _ => return None,
    })
}
/// The name a native writer failure is reported by: an I/O error's stable
/// filesystem name, as the failing call names it, or the writer error's own.
pub fn write_error_name(error: &crate::download::WriteError) -> String {
    match error {
        crate::download::WriteError::Io { name, .. } => (*name).into(),
        _ => error.to_string(),
    }
}

#[cfg(test)]
mod tests;
