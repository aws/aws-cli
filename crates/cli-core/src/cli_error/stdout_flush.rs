use super::BROKEN_PIPE_MESSAGE;
use crate::output::BufferedStream;
use std::io::{self, Write};

/// The name for a failed write that has no Python counterpart here: a
/// stderr write, or one whose error names no exception CPython raises.
pub const WRITE_FAILED_MESSAGE: &str = "WriteFailed";
/// What a write to the None `sys.stdout` of a Python CLI that started without
/// a stdout raises.
pub const NO_STDOUT_MESSAGE: &str = "'NoneType' object has no attribute 'write'";
/// CPython's exit status when its flush of `sys.stdout` or `sys.stderr` at
/// exit fails (`Py_RunMain` and `Py_Exit`). It replaces the command's own
/// status.
pub const FLUSH_FAILURE_STATUS: u8 = 120;
/// The Python CLI's status when its general handler cannot write a failure's
/// report: the handler raises the OSError of that write, nothing catches it,
/// and the process exits 1 without reaching `Py_Exit`.
pub const UNREPORTED_FAILURE_STATUS: u8 = 1;

/// CPython's `io.DEFAULT_BUFFER_SIZE`, the buffer of a descriptor that
/// reports no block size and the smallest any buffer gets.
#[cfg(unix)]
const BUFFER_LEN_DEFAULT: usize = 128 * 1024;
/// The largest block size CPython sizes a buffer by.
#[cfg(unix)]
const BUFFER_LEN_MAX: usize = 8 * 1024 * 1024;
#[cfg(windows)]
const BUFFER_LEN_WINDOWS: usize = 4096;

#[cfg(unix)]
const STDOUT_WRITE_ERRNOS: [i32; 8] = [
    libc::ENOSPC,
    libc::EPIPE,
    libc::EIO,
    libc::EDQUOT,
    libc::EFBIG,
    libc::EPERM,
    libc::EBUSY,
    libc::EBADF,
];

/// A standard stream CPython opens a buffered writer over.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StandardStream {
    Stdout,
    Stderr,
}

/// The size of CPython's buffer for `stream`, stdout or stderr, which it
/// opens alike and which bounds the output a failed write leaves for the
/// flush at exit: the descriptor's block size, bounded to [128 KiB, 8 MiB].
/// A pipe, a terminal, or a device reports one page, so its buffer is
/// 128 KiB.
#[cfg(unix)]
pub fn stream_buffer_len(stream: StandardStream) -> usize {
    use std::os::fd::AsFd;
    use std::os::unix::fs::MetadataExt;
    let descriptor = match stream {
        StandardStream::Stdout => io::stdout().as_fd().try_clone_to_owned(),
        StandardStream::Stderr => io::stderr().as_fd().try_clone_to_owned(),
    };
    descriptor
        .and_then(|descriptor| std::fs::File::from(descriptor).metadata())
        .map_or(BUFFER_LEN_DEFAULT, |metadata| {
            buffer_len(metadata.blksize())
        })
}
#[cfg(windows)]
pub fn stream_buffer_len(_: StandardStream) -> usize {
    BUFFER_LEN_WINDOWS
}
/// CPython's buffer for a descriptor whose block size is `block_size`, which
/// is 0 or 1 when the system reports none.
#[cfg(unix)]
fn buffer_len(block_size: u64) -> usize {
    if block_size <= 1 {
        return BUFFER_LEN_DEFAULT;
    }
    usize::try_from(block_size)
        .unwrap_or(BUFFER_LEN_MAX)
        .clamp(BUFFER_LEN_DEFAULT, BUFFER_LEN_MAX)
}

#[cfg(unix)]
fn errno(error: &io::Error) -> Option<i32> {
    error.raw_os_error()
}
#[cfg(not(unix))]
fn errno(_: &io::Error) -> Option<i32> {
    None
}

fn errno_text(errno: i32) -> String {
    let text = io::Error::from_raw_os_error(errno).to_string();
    let message = text.split(" (os error ").next().unwrap_or(&text);
    format!("[Errno {errno}] {message}")
}

/// `str()` of the OSError CPython raises for a call that failed with
/// `error`; None for an error with no errno.
pub fn os_error_text(error: &io::Error) -> Option<String> {
    errno(error).map(errno_text)
}

/// What the Python CLI raises for a stdout write that failed with `error`:
/// the None stdout of a process that started without one, the OSError of
/// an errno CPython raises it for, or else Python's broken pipe. Any other
/// failure is `WriteFailed`.
pub fn stdout_write_failure_message(error: &io::Error) -> String {
    if crate::startup::stdout_closed_at_start() {
        return NO_STDOUT_MESSAGE.to_owned();
    }
    if let Some(failure) = StdoutFailure::from_write_error(error) {
        return failure.text();
    }
    if error.kind() == io::ErrorKind::BrokenPipe {
        return BROKEN_PIPE_MESSAGE.to_owned();
    }
    WRITE_FAILED_MESSAGE.to_owned()
}

/// The OSError a failed write to stdout raises in the AWS CLI. A listing's
/// own write reaches the general handler, while the copy's result printer
/// swallows it. Either way the output stays in Python's stdout buffer, and
/// the interpreter writes it again when it flushes stdout at exit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StdoutFailure {
    class: &'static str,
    errno: i32,
}
impl StdoutFailure {
    /// The exception CPython raises for a stdout write that failed with
    /// `error`. None for an error it reports some other way, and for a
    /// process that started without a stdout, whose `sys.stdout` is None
    /// and keeps nothing.
    pub fn from_write_error(error: &io::Error) -> Option<Self> {
        if crate::startup::stdout_closed_at_start() {
            return None;
        }
        Self::from_stream_error(error)
    }
    /// The exception CPython raises for a write to either standard stream
    /// that failed with `error`: a failed stderr write raises what a stdout
    /// write would. None for an error it reports some other way.
    pub fn from_stream_error(error: &io::Error) -> Option<Self> {
        stdout_write_errno(error).map(|errno| Self {
            class: os_error_class(errno),
            errno,
        })
    }
    /// The exception's class, `type(e).__name__`.
    pub fn class(&self) -> &'static str {
        self.class
    }
    /// `str()` of the exception, `[Errno N] <strerror>`.
    pub fn text(&self) -> String {
        errno_text(self.errno)
    }
}
#[cfg(unix)]
fn stdout_write_errno(error: &io::Error) -> Option<i32> {
    errno(error).filter(|errno| STDOUT_WRITE_ERRNOS.contains(errno))
}
#[cfg(not(unix))]
fn stdout_write_errno(error: &io::Error) -> Option<i32> {
    errno(error)
}
#[cfg(unix)]
fn os_error_class(errno: i32) -> &'static str {
    match errno {
        libc::EPIPE => "BrokenPipeError",
        libc::EPERM => "PermissionError",
        _ => "OSError",
    }
}
#[cfg(not(unix))]
fn os_error_class(_: i32) -> &'static str {
    "OSError"
}

/// How a native command ended, which decides what a failed flush of the
/// standard streams at exit does to its status.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Termination {
    /// The command returned this status, or a handler wrote the failure's
    /// report and returned it. Upstream's interpreter then exits through
    /// `Py_Exit`, which replaces the status when the flush at exit fails.
    Exited(u8),
    /// A handler could not write the failure's report, so upstream's
    /// interpreter never reaches `Py_Exit`, and the flush at exit cannot
    /// change the status.
    Unreported,
}
impl Termination {
    /// The status to exit with, given whether the flush at exit wrote
    /// everything the streams kept.
    pub fn status(self, flushed: bool) -> u8 {
        match self {
            Self::Exited(status) if flushed => status,
            Self::Exited(_) => FLUSH_FAILURE_STATUS,
            Self::Unreported => UNREPORTED_FAILURE_STATUS,
        }
    }
}

/// Writes the output a failed stdout write left in `stdout`, as upstream's
/// interpreter flushes stdout at exit, after everything the command
/// printed. Only a failure CPython raises an exception for keeps output. A
/// stdout that works again takes it all and leaves None; otherwise the
/// result is the exception the flush raised, or the first write's when the
/// native path cannot name the new one.
pub fn flush_pending_stdout<W: Write>(stdout: &mut BufferedStream<W>) -> Option<StdoutFailure> {
    let first = stdout
        .last_error()
        .and_then(StdoutFailure::from_write_error)?;
    let error = stdout.flush().err()?;
    Some(StdoutFailure::from_write_error(&error).unwrap_or(first))
}

/// Keeps what a copy's failed stderr writes left in `stderr` only when
/// CPython raises an exception for such a write, which leaves the output in
/// `sys.stderr`'s buffer for the flush at exit. Any other failure is the
/// command's own, which the handler reports in place of the output.
pub fn forget_unkept_stderr<W: Write>(stderr: &mut BufferedStream<W>) {
    if let Some(error) = stderr.last_error()
        && StdoutFailure::from_stream_error(error).is_none()
    {
        stderr.discard();
    }
}

const UNRAISABLEHOOK_FAILURE_LINE: &str =
    "Exception ignored in sys.unraisablehook: <built-in function unraisablehook>\n";

/// The status a native command ends with once the standard streams are
/// flushed as upstream's interpreter flushes them at exit: what stdout kept
/// first, then `stderr`, which holds everything written to it since the
/// command ended, behind what a copy's failed writes left there. A flush
/// that fails replaces the status, unless the failure's report never
/// reached stderr.
pub fn flush_streams_at_exit<O: Write, E: Write>(
    stdout: &mut BufferedStream<O>,
    stderr: &mut BufferedStream<E>,
    termination: Termination,
) -> u8 {
    let mut flushed = true;
    if let Some(failure) = flush_pending_stdout(stdout) {
        report_stdout_flush_failure(stderr, &failure);
        flushed = false;
    }
    if stderr.flush().is_err() {
        flushed = false;
    }
    termination.status(flushed)
}

/// CPython's report of a stdout flush that fails at exit, written to
/// `stderr` behind everything the command wrote there. CPython's stderr is
/// line-buffered, so its unraisable hook flushes each line. A line stderr
/// refuses fails the hook, and CPython reports that failure in its place,
/// with the exception stderr's write raised; it stops at the first line of
/// that report stderr refuses.
pub fn report_stdout_flush_failure<W: Write>(
    stderr: &mut BufferedStream<W>,
    failure: &StdoutFailure,
) {
    let exception = format!("{}: {}\n", failure.class, failure.text());
    for line in ["Exception ignored while flushing sys.stdout:\n", &exception] {
        if write_flushed_line(stderr, line).is_err() {
            return report_unraisablehook_failure(stderr);
        }
    }
}
fn report_unraisablehook_failure<W: Write>(stderr: &mut BufferedStream<W>) {
    let Some(failure) = stderr
        .last_error()
        .and_then(StdoutFailure::from_stream_error)
    else {
        return;
    };
    let exception = format!("{}: {}\n", failure.class, failure.text());
    for line in [UNRAISABLEHOOK_FAILURE_LINE, &exception] {
        if write_flushed_line(stderr, line).is_err() {
            return;
        }
    }
}
fn write_flushed_line<W: Write>(stderr: &mut BufferedStream<W>, line: &str) -> io::Result<()> {
    stderr.write_all(line.as_bytes())?;
    stderr.flush()
}

#[cfg(test)]
mod tests;
