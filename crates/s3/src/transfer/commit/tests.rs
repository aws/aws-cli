#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
use std::sync::atomic::{AtomicU64, Ordering};

struct Directory(std::path::PathBuf);
impl Directory {
    fn new() -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = std::env::temp_dir().join(format!(
            "s3-commit-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[cfg(unix)]
#[test]
fn a_failed_rename_reads_as_upstreams_oserror_with_absolute_paths() {
    let text = rename_error_text(
        Path::new("/work"),
        CommitFailure {
            error: "Directory not empty",
            removing_destination: false,
        },
        Path::new("downloads/.tmp"),
        Path::new("downloads/"),
    );
    assert_eq!(
        String::from_utf8(text).unwrap(),
        format!(
            "[Errno {}] Directory not empty: '/work/downloads/.tmp' -> '/work/downloads/'",
            libc::ENOTEMPTY
        )
    );
}

#[cfg(unix)]
#[test]
fn a_failed_rename_reads_as_the_errno_its_name_maps_to() {
    for (errno, expected) in [
        (libc::EACCES, libc::EACCES),
        (libc::EPERM, libc::EPERM),
        (libc::EEXIST, libc::ENOTEMPTY),
        (libc::EXDEV, libc::EXDEV),
        (libc::EIO, libc::EIO),
        (libc::EINVAL, libc::EIO),
        (libc::EILSEQ, libc::EIO),
    ] {
        let failure = CommitFailure {
            error: rename_error_name(&io::Error::from_raw_os_error(errno)),
            removing_destination: false,
        };
        assert_eq!(
            posix_rename_failure(failure).code,
            expected.unsigned_abs(),
            "{errno}"
        );
    }
    let nul = CommitFailure {
        error: "Invalid path name",
        removing_destination: false,
    };
    assert_eq!(posix_rename_failure(nul).code, libc::EIO.unsigned_abs());
}

#[cfg(not(windows))]
#[test]
fn a_failed_windows_rename_reads_as_the_failing_calls_oserror() {
    let busy = "[WinError 32] The process cannot access the file because it is \
        being used by another process: ";
    let both = "'/work/downloads/.tmp' -> '/work/downloads/'";
    for (error, removing_destination, expected) in [
        (
            "Is a directory",
            true,
            "[WinError 5] Access is denied: '/work/downloads/'".to_owned(),
        ),
        ("File is busy", true, format!("{busy}'/work/downloads/'")),
        ("File is busy", false, format!("{busy}{both}")),
        (
            "Permission denied",
            false,
            format!("[WinError 5] Access is denied: {both}"),
        ),
        (
            "No such file or directory",
            false,
            format!("[WinError 2] The system cannot find the file specified: {both}"),
        ),
        (
            "Unexpected error",
            false,
            format!(
                "[WinError 1117] The request could not be performed because of an \
                I/O device error: {both}"
            ),
        ),
    ] {
        let failure = windows_rename_failure(CommitFailure {
            error,
            removing_destination,
        });
        let text = rename_failure_text(
            Path::new("/work"),
            failure,
            Path::new("downloads/.tmp"),
            Path::new("downloads/"),
        );
        assert_eq!(String::from_utf8(text).unwrap(), expected);
    }
}

#[cfg(unix)]
#[test]
fn a_failed_rename_quotes_its_paths_as_pythons_repr_does() {
    let text = rename_error_text(
        Path::new("/work"),
        CommitFailure {
            error: "Directory not empty",
            removing_destination: false,
        },
        Path::new("down\u{a0}load/.tmp"),
        Path::new("down\u{a0}load/"),
    );
    assert!(
        text.ends_with(b": '/work/down\\xa0load/.tmp' -> '/work/down\\xa0load/'"),
        "{}",
        String::from_utf8_lossy(&text)
    );
}

#[test]
fn a_commit_that_removes_the_destination_first_reports_which_call_failed() {
    let directory = Directory::new();
    let temp = directory.0.join("file.tmp");
    let occupied = directory.0.join("directory");
    fs::create_dir(&occupied).unwrap();
    fs::write(&temp, b"contents").unwrap();
    assert_eq!(
        commit_temp_file(&temp, &occupied, true),
        Err(CommitFailure {
            error: if cfg!(windows) {
                "Permission denied"
            } else {
                "Is a directory"
            },
            removing_destination: true,
        })
    );
    assert!(!temp.exists());

    fs::write(&temp, b"contents").unwrap();
    let missing = directory.0.join("missing.txt");
    assert_eq!(commit_temp_file(&temp, &missing, true), Ok(()));
    assert_eq!(fs::read(&missing).unwrap(), b"contents");
}
