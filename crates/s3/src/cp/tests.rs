use super::*;
use std::io;

#[cfg(unix)]
#[test]
fn io_errors_are_named_by_errno_before_kind() {
    for (errno, name) in [
        (libc::ENAMETOOLONG, "File name too long"),
        (libc::ELOOP, "Too many levels of symbolic links"),
        (libc::EDQUOT, "Disk quota exceeded"),
        (libc::EACCES, "Permission denied"),
        (libc::EPERM, "Operation not permitted"),
        (libc::EMLINK, "Too many links"),
        (libc::ENOMEM, "Insufficient system resources"),
        (libc::EILSEQ, "Invalid path name"),
        (libc::ETXTBSY, "File is busy"),
        (libc::ENOENT, "No such file or directory"),
        (libc::ENOSPC, "No space left on device"),
        (libc::EINVAL, "Invalid argument"),
        (libc::EIO, "Unexpected error"),
        (libc::ESPIPE, "Unexpected error"),
    ] {
        assert_eq!(
            io_error_name(&io::Error::from_raw_os_error(errno)),
            name,
            "errno {errno}"
        );
    }
}

#[test]
fn io_errors_without_an_errno_are_named_by_kind() {
    for (kind, name) in [
        (io::ErrorKind::NotFound, "No such file or directory"),
        (io::ErrorKind::PermissionDenied, "Permission denied"),
        (io::ErrorKind::NotADirectory, "Not a directory"),
        (io::ErrorKind::InvalidInput, "Invalid argument"),
        (io::ErrorKind::StorageFull, "No space left on device"),
        (io::ErrorKind::ResourceBusy, "Unexpected error"),
    ] {
        assert_eq!(io_error_name(&io::Error::from(kind)), name, "{kind:?}");
    }
}
