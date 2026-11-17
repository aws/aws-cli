use super::*;

#[test]
fn setup_errors_carry_stable_names() {
    let errno = io::Error::from_raw_os_error;
    let cases = [
        (
            SetupError::current_dir(&errno(libc::ENOENT)),
            "Current directory was removed",
        ),
        (
            SetupError::current_dir(&errno(libc::EACCES)),
            "Permission denied",
        ),
        (
            SetupError::spawn(&io::Error::from(io::ErrorKind::OutOfMemory)),
            "Out of memory",
        ),
        (
            SetupError::spawn(&errno(libc::EAGAIN)),
            "Insufficient system resources",
        ),
        (
            SetupError::write(&WriteError::Numa("NumaUnavailable".into())),
            "NumaUnavailable",
        ),
        (
            SetupError::write(&WriteError::from(errno(libc::EAGAIN))),
            "Insufficient system resources",
        ),
        (
            SetupError::write(&WriteError::MmapUnavailable),
            "DownloadMmapWriterUnavailable",
        ),
        (SetupError::io(&errno(libc::ENOTDIR)), "Not a directory"),
    ];
    for (error, name) in cases {
        assert_eq!(error.name(), name);
        assert_eq!(error.to_string(), name);
    }
    assert_eq!(WRITE_POOL_CLOSED, "WritePoolClosed");
}
