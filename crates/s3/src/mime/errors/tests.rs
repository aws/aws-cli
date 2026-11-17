use super::*;

#[test]
fn windows_failures_translate_to_c_errno_instead_of_win32_numbers() {
    for (kind, expected) in [
        (io::ErrorKind::NotFound, libc::ENOENT),
        (io::ErrorKind::PermissionDenied, libc::EACCES),
        (io::ErrorKind::NotADirectory, libc::ENOTDIR),
        (io::ErrorKind::IsADirectory, libc::EISDIR),
        (io::ErrorKind::OutOfMemory, libc::ENOMEM),
        (io::ErrorKind::FileTooLarge, libc::EFBIG),
        (io::ErrorKind::Other, libc::EIO),
    ] {
        assert_eq!(windows_errno(kind), expected);
    }
}
