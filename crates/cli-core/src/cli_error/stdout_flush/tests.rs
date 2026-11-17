#![cfg_attr(
    unix,
    expect(
        clippy::unwrap_used,
        reason = "fixture output is infallible and valid UTF-8"
    )
)]
use super::*;

#[cfg(unix)]
#[test]
fn os_errors_read_as_python_formats_them() {
    let error = io::Error::from_raw_os_error(libc::ENOSPC);
    assert_eq!(
        os_error_text(&error).as_deref(),
        Some("[Errno 28] No space left on device")
    );
    assert_eq!(
        os_error_text(&io::Error::from_raw_os_error(libc::EPIPE)).as_deref(),
        Some(BROKEN_PIPE_MESSAGE)
    );
    assert_eq!(os_error_text(&io::ErrorKind::StorageFull.into()), None);
}

#[cfg(unix)]
#[test]
fn write_errors_name_the_exception_cpython_raises() {
    for (errno, class, text) in [
        (
            libc::ENOSPC,
            "OSError",
            "[Errno 28] No space left on device",
        ),
        (libc::EPIPE, "BrokenPipeError", "[Errno 32] Broken pipe"),
        (
            libc::EPERM,
            "PermissionError",
            "[Errno 1] Operation not permitted",
        ),
        (libc::EBADF, "OSError", "[Errno 9] Bad file descriptor"),
    ] {
        let failure = StdoutFailure::from_write_error(&io::Error::from_raw_os_error(errno));
        let failure = failure.unwrap();
        assert_eq!((failure.class(), failure.text().as_str()), (class, text));
    }
    for errno in [libc::EAGAIN, libc::EACCES, libc::ENOBUFS] {
        assert_eq!(
            StdoutFailure::from_write_error(&io::Error::from_raw_os_error(errno)),
            None
        );
    }
    let failure = StdoutFailure::from_write_error(&io::Error::from_raw_os_error(libc::EIO));
    let failure = failure.unwrap();
    assert_eq!(failure.class(), "OSError");
    assert!(failure.text().starts_with("[Errno 5] "));
}

#[cfg(unix)]
#[test]
fn a_stdout_write_failure_reads_as_python_raises_it() {
    for (error, message) in [
        (
            io::Error::from_raw_os_error(libc::ENOSPC),
            "[Errno 28] No space left on device",
        ),
        (
            io::Error::from_raw_os_error(libc::EPIPE),
            BROKEN_PIPE_MESSAGE,
        ),
        (io::ErrorKind::BrokenPipe.into(), BROKEN_PIPE_MESSAGE),
        (
            io::Error::from_raw_os_error(libc::EAGAIN),
            WRITE_FAILED_MESSAGE,
        ),
        (io::ErrorKind::StorageFull.into(), WRITE_FAILED_MESSAGE),
    ] {
        assert_eq!(stdout_write_failure_message(&error), message);
    }
}

#[test]
fn only_an_errno_cpython_raises_keeps_output() {
    assert_eq!(
        StdoutFailure::from_write_error(&io::ErrorKind::BrokenPipe.into()),
        None
    );
    assert_eq!(
        StdoutFailure::from_write_error(&io::ErrorKind::StorageFull.into()),
        None
    );
}

#[cfg(unix)]
#[test]
fn a_failed_stdout_flush_reports_as_cpython_does_at_exit() {
    let failure = StdoutFailure::from_write_error(&io::Error::from_raw_os_error(libc::EPIPE));
    let mut stderr = BufferedStream::new(Vec::new(), 64);
    report_stdout_flush_failure(&mut stderr, &failure.unwrap());
    assert_eq!(
        String::from_utf8(stderr.get_ref().clone()).unwrap(),
        "Exception ignored while flushing sys.stdout:\nBrokenPipeError: [Errno 32] Broken pipe\n"
    );
}

#[test]
fn a_failed_flush_at_exit_makes_the_status_120_unless_the_failure_went_unreported() {
    for (termination, flushed, expected) in [
        (Termination::Exited(0), true, 0),
        (Termination::Exited(254), true, 254),
        (Termination::Exited(0), false, FLUSH_FAILURE_STATUS),
        (Termination::Exited(254), false, FLUSH_FAILURE_STATUS),
        (Termination::Unreported, true, UNREPORTED_FAILURE_STATUS),
        (Termination::Unreported, false, UNREPORTED_FAILURE_STATUS),
    ] {
        assert_eq!(termination.status(flushed), expected);
    }
    assert_eq!((FLUSH_FAILURE_STATUS, UNREPORTED_FAILURE_STATUS), (120, 1));
}

#[cfg(unix)]
#[derive(Debug, Default)]
struct TestStdout {
    cause: Option<i32>,
    written: Vec<u8>,
}
#[cfg(unix)]
impl Write for TestStdout {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if let Some(errno) = self.cause {
            return Err(io::Error::from_raw_os_error(errno));
        }
        self.written.extend_from_slice(buf);
        Ok(buf.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[cfg(unix)]
fn stdout_after_a_broken_pipe() -> BufferedStream<TestStdout> {
    let mut stdout = BufferedStream::new(
        TestStdout {
            cause: Some(libc::EPIPE),
            ..TestStdout::default()
        },
        64,
    );
    stdout.write_all(b"row one\nrow two\n").unwrap();
    assert!(stdout.flush().is_err());
    stdout
}

#[cfg(unix)]
#[test]
fn pending_stdout_is_reported_only_when_its_flush_at_exit_fails() {
    for (cause, expected) in [
        (None, None),
        (Some(libc::EPIPE), Some("[Errno 32] Broken pipe")),
        (
            Some(libc::ENOSPC),
            Some("[Errno 28] No space left on device"),
        ),
        (Some(libc::EAGAIN), Some("[Errno 32] Broken pipe")),
    ] {
        let mut stdout = stdout_after_a_broken_pipe();
        stdout.get_mut().cause = cause;
        let failure = flush_pending_stdout(&mut stdout);
        assert_eq!(failure.map(|failure| failure.text()).as_deref(), expected);
        if expected.is_none() {
            assert_eq!(stdout.get_ref().written, b"row one\nrow two\n");
        }
    }
}

#[cfg(unix)]
#[test]
fn only_a_failure_cpython_raises_leaves_pending_stdout() {
    let mut stdout = BufferedStream::new(
        TestStdout {
            cause: Some(libc::EAGAIN),
            ..TestStdout::default()
        },
        64,
    );
    stdout.write_all(b"row\n").unwrap();
    assert!(stdout.flush().is_err());
    stdout.get_mut().cause = None;
    assert_eq!(flush_pending_stdout(&mut stdout), None);
    assert!(stdout.get_ref().written.is_empty());
    let mut stdout = BufferedStream::new(TestStdout::default(), 64);
    stdout.write_all(b"row\n").unwrap();
    stdout.flush().unwrap();
    assert_eq!(flush_pending_stdout(&mut stdout), None);
    assert_eq!(stdout.get_ref().written, b"row\n");
}

#[cfg(unix)]
#[test]
fn only_a_failure_cpython_raises_leaves_pending_stderr() {
    for (cause, kept) in [
        (libc::EPIPE, b"warning: w\n".as_slice()),
        (libc::ENOSPC, b"warning: w\n"),
        (libc::EAGAIN, b""),
    ] {
        let mut stderr = BufferedStream::new(
            TestStdout {
                cause: Some(cause),
                ..TestStdout::default()
            },
            64,
        );
        stderr.write_all(b"warning: w\n").unwrap();
        assert!(stderr.flush().is_err());
        forget_unkept_stderr(&mut stderr);
        assert_eq!(stderr.buffered(), kept);
        assert_eq!(stderr.last_error().is_some(), !kept.is_empty());
    }
}

#[cfg(unix)]
#[test]
fn a_streams_buffer_is_sized_as_cpython_sizes_it() {
    for (block_size, expected) in [
        (0, 128 * 1024),
        (1, 128 * 1024),
        (4096, 128 * 1024),
        (1024 * 1024, 1024 * 1024),
        (16 * 1024 * 1024, 8 * 1024 * 1024),
    ] {
        assert_eq!(buffer_len(block_size), expected, "{block_size}");
    }
    for stream in [StandardStream::Stdout, StandardStream::Stderr] {
        let len = stream_buffer_len(stream);
        assert!(
            (128 * 1024..=8 * 1024 * 1024).contains(&len),
            "{stream:?} {len}"
        );
    }
}

#[cfg(unix)]
#[derive(Debug)]
struct RefusingStream {
    refusals: usize,
    cause: i32,
    written: Vec<u8>,
}
#[cfg(unix)]
impl Write for RefusingStream {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if self.refusals > 0 {
            self.refusals -= 1;
            return Err(io::Error::from_raw_os_error(self.cause));
        }
        self.written.extend_from_slice(buf);
        Ok(buf.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

#[cfg(unix)]
fn stderr_keeping(kept: &str, refusals: usize) -> BufferedStream<RefusingStream> {
    let mut stderr = BufferedStream::new(
        RefusingStream {
            refusals: refusals + 1,
            cause: libc::EBADF,
            written: Vec::new(),
        },
        2 * kept.len(),
    );
    stderr.write_all(kept.as_bytes()).unwrap();
    assert!(stderr.flush().is_err());
    stderr
}

#[cfg(unix)]
#[test]
fn kept_stderr_output_waits_whole_for_the_flush_at_exit() {
    let kept = "warning: Skipping file /src/link. File does not exist.\n".repeat(100);
    assert!(kept.len() > 4096);
    for (termination, expected) in [
        (Termination::Exited(2), FLUSH_FAILURE_STATUS),
        (Termination::Unreported, UNREPORTED_FAILURE_STATUS),
    ] {
        let mut stdout = BufferedStream::new(TestStdout::default(), 64);
        let mut stderr = stderr_keeping(&kept, usize::MAX - 1);
        assert_eq!(
            flush_streams_at_exit(&mut stdout, &mut stderr, termination),
            expected
        );
    }
    let mut stdout = BufferedStream::new(TestStdout::default(), 64);
    let mut stderr = stderr_keeping(&kept, 0);
    assert!(stderr.get_ref().written.is_empty());
    assert_eq!(
        flush_streams_at_exit(&mut stdout, &mut stderr, Termination::Exited(2)),
        2
    );
    assert_eq!(stderr.get_ref().written, kept.as_bytes());
}

#[cfg(unix)]
#[test]
fn a_failed_stdout_flush_reports_behind_kept_stderr_output_as_cpython_does() {
    let warning = "warning: Skipping file /src/link. File does not exist.\n";
    let mut stdout = BufferedStream::new(
        TestStdout {
            cause: Some(libc::ENOSPC),
            ..TestStdout::default()
        },
        64,
    );
    stdout.write_all(b"upload: a to s3://b/a\n").unwrap();
    assert!(stdout.flush().is_err());
    let mut stderr = BufferedStream::new(
        RefusingStream {
            refusals: 1,
            cause: libc::EPIPE,
            written: Vec::new(),
        },
        4096,
    );
    stderr.write_all(warning.as_bytes()).unwrap();
    assert_eq!(
        flush_streams_at_exit(&mut stdout, &mut stderr, Termination::Exited(2)),
        FLUSH_FAILURE_STATUS
    );
    assert_eq!(
        String::from_utf8(stderr.get_ref().written.clone()).unwrap(),
        format!(
            "{warning}Exception ignored while flushing sys.stdout:\n\
            Exception ignored in sys.unraisablehook: <built-in function unraisablehook>\n\
            BrokenPipeError: [Errno 32] Broken pipe\n"
        )
    );
}
