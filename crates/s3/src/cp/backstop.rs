//! Errors that escape a transfer to the general handler, under stable names.
use crate::download::WriteError;
use std::borrow::Cow;
use std::io;

/// A finish pushed to a finish pool that had already closed.
pub const WRITE_POOL_CLOSED: &str = "WritePoolClosed";

/// A CRT client upstream builds before any transfer and could not build:
/// awscrt raises the RuntimeError `PyErr_AwsLastError` composes
/// (aws-crt-python module.c), which the general handler reports.
pub fn client_failure_message(result: &crt::s3::TransferResult) -> String {
    format!(
        "{} ({}): {}",
        result.error_code,
        String::from_utf8_lossy(result.crt_name.as_bytes()),
        String::from_utf8_lossy(result.crt_message.as_bytes())
    )
}

/// A transfer setup step that failed, which the general handler reports with
/// status 255 and an absorbed Ctrl-C does not outrank.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SetupError(Cow<'static, str>);
impl SetupError {
    /// The working directory could not be looked up; getcwd's `ENOENT` is a
    /// directory that was removed.
    pub fn current_dir(error: &io::Error) -> Self {
        Self(Cow::Borrowed(match error.kind() {
            io::ErrorKind::NotFound => crate::local_error::CURRENT_DIR_UNLINKED,
            _ => super::io_error_name(error),
        }))
    }
    /// A worker pool or its queue that could not start: a queue that cannot
    /// be reserved is out of memory, and a thread the system refuses
    /// (`EAGAIN`) is out of system resources.
    pub fn spawn(error: &io::Error) -> Self {
        Self(Cow::Borrowed(match error.kind() {
            io::ErrorKind::OutOfMemory => crate::local_error::OUT_OF_MEMORY,
            io::ErrorKind::WouldBlock => crate::local_error::SYSTEM_RESOURCES,
            _ => super::io_error_name(error),
        }))
    }
    /// A writer placement, source pool, or writer service that could not be
    /// set up: NUMA failures keep their own names, and an I/O error there is
    /// a worker that could not start.
    pub fn write(error: &WriteError) -> Self {
        match error {
            WriteError::Io { kind, .. } => Self::spawn(&io::Error::from(*kind)),
            error => Self(Cow::Owned(error.to_string())),
        }
    }
    /// A local file operation, named as a filesystem error.
    pub fn io(error: &io::Error) -> Self {
        Self(Cow::Borrowed(super::io_error_name(error)))
    }
    pub fn name(&self) -> &str {
        &self.0
    }
}
impl std::fmt::Display for SetupError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
impl std::error::Error for SetupError {}

#[cfg(all(test, unix))]
mod tests;
