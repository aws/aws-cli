#![cfg_attr(
    unix,
    expect(clippy::unwrap_used, reason = "fixed fault fixtures and assertions")
)]
use super::*;
use crate::cp::write_error_name;
use std::io;

type Constructor = fn(io::Error) -> WriteError;

#[cfg(unix)]
#[test]
fn each_output_call_names_its_errno_its_own_way() {
    let create: Constructor = WriteError::create;
    let preallocate: Constructor = WriteError::preallocate;
    let set_length: Constructor = WriteError::set_length;
    let write: Constructor = WriteError::positional_write;
    let cases = [
        (write, libc::EDQUOT, "Disk quota exceeded"),
        (write, libc::EIO, "Input/output error"),
        (write, libc::ESPIPE, "File is not seekable"),
        (write, libc::ENXIO, "File is not seekable"),
        (write, libc::EOVERFLOW, "File is not seekable"),
        (write, libc::EBADF, "File not open for writing"),
        (write, libc::EPERM, "Operation not permitted"),
        (write, libc::EACCES, "Permission denied"),
        (write, libc::EINVAL, "DownloadPositionalWriteRejected"),
        (write, libc::EOPNOTSUPP, "DownloadPositionalWriteRejected"),
        (write, libc::EPIPE, "Broken pipe"),
        (write, libc::EFBIG, "File too large"),
        (write, libc::ENOSPC, "No space left on device"),
        (write, libc::ETXTBSY, "Unexpected error"),
        (write, libc::EROFS, "Unexpected error"),
        (set_length, libc::EDQUOT, "Disk quota exceeded"),
        (set_length, libc::EIO, "Input/output error"),
        (set_length, libc::EPERM, "Operation not permitted"),
        (set_length, libc::EINVAL, "Could not resize file"),
        (set_length, libc::ETXTBSY, "File is busy"),
        (set_length, libc::EBADF, "File not open for writing"),
        (set_length, libc::ENOSPC, "No space left on device"),
        (set_length, libc::EACCES, "Unexpected error"),
        (set_length, libc::ESPIPE, "Unexpected error"),
        (preallocate, libc::EDQUOT, "Disk quota exceeded"),
        (preallocate, libc::EIO, "Input/output error"),
        (preallocate, libc::EACCES, "Permission denied"),
        (preallocate, libc::EPERM, "Operation not permitted"),
        (preallocate, libc::EBADF, "File not open for writing"),
        (preallocate, libc::ETXTBSY, "Unexpected error"),
        (create, libc::ENAMETOOLONG, "File name too long"),
        (create, libc::ELOOP, "Too many levels of symbolic links"),
        (create, libc::EACCES, "Permission denied"),
        (create, libc::EPERM, "Operation not permitted"),
        (create, libc::EISDIR, "Is a directory"),
        (create, libc::ENOENT, "No such file or directory"),
        (create, libc::ENOTDIR, "Not a directory"),
        (create, libc::EROFS, "Read-only file system"),
        (create, libc::ENOSPC, "No space left on device"),
        (create, libc::ETXTBSY, "File is busy"),
        (create, libc::EINVAL, "Invalid path name"),
        (create, libc::EMFILE, "Too many open files"),
        (create, libc::ENFILE, "Too many open files in system"),
        (create, libc::ENXIO, "No such device"),
        (create, libc::EOVERFLOW, "File too large"),
        (create, libc::EAGAIN, "Resource temporarily unavailable"),
        (create, libc::EDQUOT, "Unexpected error"),
        (create, libc::EIO, "Unexpected error"),
    ];
    for (call, errno, name) in cases {
        let error = call(io::Error::from_raw_os_error(errno));
        assert!(
            matches!(&error, WriteError::Io { name: found, .. } if *found == name),
            "errno {errno}: {error:?}"
        );
        assert_eq!(write_error_name(&error), name, "errno {errno}");
        assert_eq!(
            error.to_string(),
            io::Error::from_raw_os_error(errno).to_string()
        );
    }
}

#[test]
fn an_error_without_an_errno_is_named_by_its_kind() {
    let calls: [Constructor; 5] = [
        WriteError::create,
        WriteError::preallocate,
        WriteError::set_length,
        WriteError::positional_write,
        WriteError::from,
    ];
    for call in calls {
        let full = call(io::ErrorKind::StorageFull.into());
        assert_eq!(write_error_name(&full), "No space left on device");
        let busy = call(io::ErrorKind::ResourceBusy.into());
        assert_eq!(write_error_name(&busy), "Unexpected error");
    }
}

#[cfg(unix)]
#[test]
fn any_other_calls_errno_is_named_as_any_calls() {
    for (errno, name) in [
        (libc::EDQUOT, "Disk quota exceeded"),
        (libc::ENAMETOOLONG, "File name too long"),
        (libc::EPERM, "Operation not permitted"),
        (libc::EIO, "Unexpected error"),
        (libc::EINVAL, "Invalid argument"),
    ] {
        let error = WriteError::from(io::Error::from_raw_os_error(errno));
        assert_eq!(write_error_name(&error), name, "errno {errno}");
    }
}

#[cfg(unix)]
#[test]
fn writes_and_length_changes_report_their_calls_names() {
    use crate::download::{
        io::write_all,
        lock, platform,
        testing::fakes::{self, FakePlatform, Fault},
    };
    let platform = FakePlatform::default();
    let file = fakes::file();
    for (errno, name) in [
        (libc::EDQUOT, "Disk quota exceeded"),
        (libc::EIO, "Input/output error"),
        (libc::ESPIPE, "File is not seekable"),
        (libc::EBADF, "File not open for writing"),
    ] {
        lock(&platform.faults).push_back(Fault::Errno(errno));
        let error = write_all(&platform, &file, &[1], 0, None).unwrap_err();
        assert_eq!(write_error_name(&error), name, "errno {errno}");
    }
    for (errno, name) in [
        (libc::EDQUOT, "Disk quota exceeded"),
        (libc::EIO, "Input/output error"),
        (libc::ETXTBSY, "File is busy"),
        (libc::EINVAL, "Could not resize file"),
    ] {
        *lock(&platform.set_length_failure) = Some(errno);
        let error = platform::set_length(&platform, &file, 1).unwrap_err();
        assert_eq!(write_error_name(&error), name, "errno {errno}");
    }
}

#[test]
fn positions_past_the_files_offsets_keep_their_own_names() {
    for (error, name) in [
        (WriteError::FileTooBig, "File too large"),
        (WriteError::Overflow, "Value too large"),
        (WriteError::OutOfBounds, "DownloadWriteOutOfBounds"),
    ] {
        assert_eq!(write_error_name(&error), name);
        assert_eq!(error.to_string(), name);
    }
}
