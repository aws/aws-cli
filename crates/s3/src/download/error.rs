use std::fmt;

#[derive(Clone, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum WriteError {
    /// A failed system call: its kind and message, and the stable name of
    /// what that call reported.
    Io {
        kind: std::io::ErrorKind,
        name: &'static str,
        message: String,
    },
    OutOfBounds,
    /// A write position or file length past the largest `off_t`, which no
    /// positional call or length change accepts.
    FileTooBig,
    /// A write position that overflows `u64`.
    Overflow,
    Overlap,
    Missing,
    Closed,
    /// The writer service closed before admitting an output.
    SharedWriterClosed,
    MultipleProducers,
    WriteZero,
    WriteRejected,
    DirectInvalidAlignment,
    DirectMemoryAlignmentUnsupported,
    DirectOffsetUnaligned,
    DirectNonFinalLengthUnaligned,
    DirectShortWriteUnaligned,
    DirectUnavailable,
    DirectUnsupportedOperatingSystem,
    MmapUnavailable,
    MmapEvictFailed,
    PageAlreadyEvicted,
    PageCompletedTwice,
    ReceivedSizeMismatch,
    EnqueuedSizeMismatch,
    WrittenSizeMismatch,
    Interrupted,
    Numa(String),
    /// Closing the output file reported a delayed failure, after which the
    /// file is never committed.
    Close(CloseError),
}
/// A delayed failure closing an output file reports. The file is consumed
/// either way: a failed close is never retried, because the descriptor is
/// already released and could name another file by now. This is no
/// durability guarantee.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CloseError {
    InputOutput,
    NoSpaceLeft,
    DiskQuota,
    /// A signal interrupted the close; never a Ctrl-C cancellation.
    Interrupted,
    Unexpected,
}
impl CloseError {
    pub fn name(self) -> &'static str {
        match self {
            Self::InputOutput => crate::local_error::INPUT_OUTPUT,
            Self::NoSpaceLeft => crate::local_error::NO_SPACE_LEFT,
            Self::DiskQuota => crate::local_error::DISK_QUOTA,
            Self::Interrupted => crate::local_error::INTERRUPTED,
            Self::Unexpected => crate::local_error::UNEXPECTED,
        }
    }
}
impl fmt::Display for CloseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.name())
    }
}
impl std::error::Error for CloseError {}
impl From<std::io::Error> for WriteError {
    fn from(error: std::io::Error) -> Self {
        let name = crate::cp::io_error_name(&error);
        Self::io(error, name)
    }
}
#[derive(Clone, Copy, Debug)]
enum Call {
    Create,
    Preallocate,
    SetLength,
    PositionalWrite,
}
impl Call {
    fn error_name(self, error: &std::io::Error) -> &'static str {
        #[cfg(unix)]
        if let Some(errno) = error.raw_os_error() {
            return self.errno_name(errno);
        }
        crate::cp::io_error_name(error)
    }
    #[cfg(unix)]
    fn errno_name(self, errno: i32) -> &'static str {
        match (self, errno) {
            (Self::Create, libc::EINVAL | libc::EILSEQ) => crate::local_error::BAD_PATH_NAME,
            (Self::Create, libc::EACCES) => crate::local_error::ACCESS_DENIED,
            (Self::Create, libc::EFBIG | libc::EOVERFLOW) => crate::local_error::FILE_TOO_BIG,
            (Self::Create, libc::EISDIR) => crate::local_error::IS_DIR,
            (Self::Create, libc::ELOOP) => crate::local_error::SYM_LINK_LOOP,
            (Self::Create, libc::EMFILE) => crate::local_error::PROCESS_FD_QUOTA_EXCEEDED,
            (Self::Create, libc::ENAMETOOLONG) => crate::local_error::NAME_TOO_LONG,
            (Self::Create, libc::ENFILE) => crate::local_error::SYSTEM_FD_QUOTA_EXCEEDED,
            (Self::Create, libc::ENODEV | libc::ENXIO) => crate::local_error::NO_DEVICE,
            (Self::Create, libc::ENOENT | libc::ESRCH) => crate::local_error::FILE_NOT_FOUND,
            (Self::Create, libc::ENOMEM) => crate::local_error::SYSTEM_RESOURCES,
            (Self::Create, libc::ENOSPC) => crate::local_error::NO_SPACE_LEFT,
            (Self::Create, libc::ENOTDIR) => crate::local_error::NOT_DIR,
            (Self::Create, libc::EPERM) => crate::local_error::PERMISSION_DENIED,
            (Self::Create, libc::EEXIST) => crate::local_error::PATH_ALREADY_EXISTS,
            (Self::Create, libc::EBUSY) => crate::local_error::DEVICE_BUSY,
            (Self::Create, libc::EOPNOTSUPP) => crate::local_error::FILE_LOCKS_UNSUPPORTED,
            (Self::Create, libc::EAGAIN) => crate::local_error::WOULD_BLOCK,
            (Self::Create, libc::ETXTBSY) => crate::local_error::FILE_BUSY,
            (Self::Create, libc::EROFS) => crate::local_error::READ_ONLY_FILE_SYSTEM,
            (Self::Create, _) => crate::local_error::UNEXPECTED,
            (Self::Preallocate, libc::EACCES) => crate::local_error::ACCESS_DENIED,
            (Self::SetLength, libc::ETXTBSY) => crate::local_error::FILE_BUSY,
            (Self::SetLength, libc::EINVAL) => crate::local_error::FILE_RESIZE_FAILED,
            (Self::PositionalWrite, libc::EINTR) => crate::local_error::INTERRUPTED,
            (Self::PositionalWrite, libc::EACCES) => crate::local_error::ACCESS_DENIED,
            (Self::PositionalWrite, libc::EPIPE) => crate::local_error::BROKEN_PIPE,
            (Self::PositionalWrite, libc::EINVAL | libc::EOPNOTSUPP) => {
                "DownloadPositionalWriteRejected"
            }
            (Self::PositionalWrite, libc::ENXIO | libc::ESPIPE | libc::EOVERFLOW) => {
                crate::local_error::UNSEEKABLE
            }
            (_, libc::ENOSPC) => crate::local_error::NO_SPACE_LEFT,
            (_, libc::EDQUOT) => crate::local_error::DISK_QUOTA,
            (_, libc::EPERM) => crate::local_error::PERMISSION_DENIED,
            (_, libc::EFBIG) => crate::local_error::FILE_TOO_BIG,
            (_, libc::EBADF) => crate::local_error::NOT_OPEN_FOR_WRITING,
            (_, libc::EIO) => crate::local_error::INPUT_OUTPUT,
            _ => crate::local_error::UNEXPECTED,
        }
    }
}
impl fmt::Display for WriteError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io { message, .. } | Self::Numa(message) => f.write_str(message),
            error => f.write_str(error.name()),
        }
    }
}
impl WriteError {
    fn io(error: std::io::Error, name: &'static str) -> Self {
        Self::Io {
            kind: error.kind(),
            name,
            message: error.to_string(),
        }
    }
    fn call(call: Call, error: std::io::Error) -> Self {
        let name = call.error_name(&error);
        Self::io(error, name)
    }
    pub(crate) fn create(error: std::io::Error) -> Self {
        Self::call(Call::Create, error)
    }
    pub(crate) fn preallocate(error: std::io::Error) -> Self {
        Self::call(Call::Preallocate, error)
    }
    pub(crate) fn set_length(error: std::io::Error) -> Self {
        Self::call(Call::SetLength, error)
    }
    pub(crate) fn positional_write(error: std::io::Error) -> Self {
        Self::call(Call::PositionalWrite, error)
    }
    fn name(&self) -> &'static str {
        match self {
            Self::OutOfBounds => "DownloadWriteOutOfBounds",
            Self::FileTooBig => crate::local_error::FILE_TOO_BIG,
            Self::Overflow => crate::local_error::OVERFLOW,
            Self::Overlap => "DownloadWriteRangeOverlap",
            Self::Missing => "DownloadBodyMissing",
            Self::Closed => "DownloadPipelineClosed",
            Self::SharedWriterClosed => "DownloadSharedWriterClosed",
            Self::MultipleProducers => "DownloadMultipleProducers",
            Self::WriteZero => "DownloadWriteZero",
            Self::WriteRejected => "DownloadPositionalWriteRejected",
            Self::DirectInvalidAlignment => "DownloadDirectInvalidAlignment",
            Self::DirectMemoryAlignmentUnsupported => "DownloadDirectMemoryAlignmentUnsupported",
            Self::DirectOffsetUnaligned => "DownloadDirectOffsetUnaligned",
            Self::DirectNonFinalLengthUnaligned => "DownloadDirectNonFinalLengthUnaligned",
            Self::DirectShortWriteUnaligned => "DownloadDirectShortWriteUnaligned",
            Self::DirectUnavailable => "DownloadDirectWriterUnavailable",
            Self::DirectUnsupportedOperatingSystem => "DownloadDirectUnsupportedOperatingSystem",
            Self::MmapUnavailable => "DownloadMmapWriterUnavailable",
            Self::MmapEvictFailed => "DownloadMmapEvictFailed",
            Self::PageAlreadyEvicted => "DownloadMmapPageAlreadyEvicted",
            Self::PageCompletedTwice => "DownloadMmapPageCompletedTwice",
            Self::ReceivedSizeMismatch => "DownloadReceivedSizeMismatch",
            Self::EnqueuedSizeMismatch => "DownloadEnqueuedSizeMismatch",
            Self::WrittenSizeMismatch => "DownloadWrittenSizeMismatch",
            Self::Interrupted => crate::local_error::INTERRUPTED,
            Self::Close(error) => error.name(),
            Self::Io { .. } | Self::Numa(_) => crate::local_error::UNEXPECTED,
        }
    }
}
impl std::error::Error for WriteError {}

#[cfg(test)]
mod tests;
