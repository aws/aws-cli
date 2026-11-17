use crate::{INPUT_SIZE_MAX, Status};
use std::{fmt, io::Read, path::Path};

/// Filesystem failures, including resource errors that must propagate.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum ReadError {
    FileNotFound,
    NotDir,
    IsDir,
    NotRegularFile,
    AccessDenied,
    PermissionDenied,
    SymLinkLoop,
    InputOutput,
    BadPathName,
    Canceled,
    SystemResources,
    ProcessFdQuotaExceeded,
    SystemFdQuotaExceeded,
    Other {
        kind: std::io::ErrorKind,
        raw_os_error: Option<i32>,
    },
}
impl fmt::Display for ReadError {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(out, "filesystem read failed: {self:?}")
    }
}
impl std::error::Error for ReadError {}
impl From<std::io::Error> for ReadError {
    fn from(error: std::io::Error) -> Self {
        #[cfg(windows)]
        return windows_error(error.raw_os_error(), error.kind());
        #[cfg(not(windows))]
        match error.raw_os_error() {
            Some(errno::ENOENT | errno::ESRCH) => Self::FileNotFound,
            Some(errno::ENOTDIR) => Self::NotDir,
            Some(errno::EISDIR) => Self::IsDir,
            Some(errno::EACCES) => Self::AccessDenied,
            Some(errno::EPERM) => Self::PermissionDenied,
            Some(errno::EIO) => Self::InputOutput,
            Some(errno::ENOMEM) => Self::SystemResources,
            #[cfg(any(target_os = "linux", target_os = "macos"))]
            Some(errno::ENOBUFS) => Self::SystemResources,
            Some(errno::ENFILE) => Self::SystemFdQuotaExceeded,
            Some(errno::EMFILE) => Self::ProcessFdQuotaExceeded,
            #[cfg(any(target_os = "linux", target_os = "macos"))]
            Some(errno::ELOOP) => Self::SymLinkLoop,
            _ => Self::Other {
                kind: error.kind(),
                raw_os_error: error.raw_os_error(),
            },
        }
    }
}
#[cfg(not(windows))]
mod errno {
    pub(super) const EPERM: i32 = 1;
    pub(super) const ENOENT: i32 = 2;
    pub(super) const ESRCH: i32 = 3;
    pub(super) const EIO: i32 = 5;
    pub(super) const ENOMEM: i32 = 12;
    pub(super) const EACCES: i32 = 13;
    pub(super) const ENOTDIR: i32 = 20;
    pub(super) const EISDIR: i32 = 21;
    pub(super) const ENFILE: i32 = 23;
    pub(super) const EMFILE: i32 = 24;
    #[cfg(target_os = "linux")]
    pub(super) const ENOBUFS: i32 = 105;
    #[cfg(target_os = "macos")]
    pub(super) const ENOBUFS: i32 = 55;
    #[cfg(target_os = "linux")]
    pub(super) const ELOOP: i32 = 40;
    #[cfg(target_os = "macos")]
    pub(super) const ELOOP: i32 = 62;
}

#[cfg(any(windows, test))]
fn windows_error(raw_os_error: Option<i32>, kind: std::io::ErrorKind) -> ReadError {
    use win32::*;
    match raw_os_error {
        Some(ERROR_FILE_NOT_FOUND | ERROR_PATH_NOT_FOUND) => ReadError::FileNotFound,
        Some(ERROR_TOO_MANY_OPEN_FILES) => ReadError::ProcessFdQuotaExceeded,
        Some(ERROR_ACCESS_DENIED) => ReadError::AccessDenied,
        Some(ERROR_NOT_ENOUGH_MEMORY | ERROR_OUTOFMEMORY | ERROR_NO_SYSTEM_RESOURCES) => {
            ReadError::SystemResources
        }
        Some(ERROR_INVALID_NAME | ERROR_BAD_PATHNAME) => ReadError::BadPathName,
        Some(ERROR_DIRECTORY) => ReadError::NotDir,
        Some(ERROR_OPERATION_ABORTED) => ReadError::Canceled,
        Some(ERROR_PRIVILEGE_NOT_HELD) => ReadError::PermissionDenied,
        _ => ReadError::Other { kind, raw_os_error },
    }
}
#[cfg(any(windows, test))]
mod win32 {
    pub(super) const ERROR_FILE_NOT_FOUND: i32 = 2;
    pub(super) const ERROR_PATH_NOT_FOUND: i32 = 3;
    pub(super) const ERROR_TOO_MANY_OPEN_FILES: i32 = 4;
    pub(super) const ERROR_ACCESS_DENIED: i32 = 5;
    pub(super) const ERROR_NOT_ENOUGH_MEMORY: i32 = 8;
    pub(super) const ERROR_OUTOFMEMORY: i32 = 14;
    pub(super) const ERROR_INVALID_NAME: i32 = 123;
    pub(super) const ERROR_BAD_PATHNAME: i32 = 161;
    pub(super) const ERROR_DIRECTORY: i32 = 267;
    pub(super) const ERROR_OPERATION_ABORTED: i32 = 995;
    pub(super) const ERROR_PRIVILEGE_NOT_HELD: i32 = 1314;
    pub(super) const ERROR_NO_SYSTEM_RESOURCES: i32 = 1450;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FileKind {
    Regular,
    Directory,
    Other,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Metadata {
    pub kind: FileKind,
    pub len: u64,
}
/// An owned open handle, released by its destructor on every path.
pub trait ReadHandle {
    fn metadata(&self) -> Result<Metadata, ReadError>;
    fn read(&mut self, bytes: &mut [u8]) -> Result<usize, ReadError>;
}
/// Filesystem injection seam used before and after opening each path.
pub trait Fs {
    type Handle: ReadHandle;
    fn metadata(&self, path: &Path) -> Result<Metadata, ReadError>;
    fn open(&self, path: &Path) -> Result<Self::Handle, ReadError>;
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct StdFs;
impl Fs for StdFs {
    type Handle = std::fs::File;
    fn metadata(&self, path: &Path) -> Result<Metadata, ReadError> {
        std::fs::metadata(path)
            .map(convert_metadata)
            .map_err(Into::into)
    }
    fn open(&self, path: &Path) -> Result<Self::Handle, ReadError> {
        std::fs::File::open(path).map_err(Into::into)
    }
}
impl ReadHandle for std::fs::File {
    fn metadata(&self) -> Result<Metadata, ReadError> {
        self.metadata().map(convert_metadata).map_err(Into::into)
    }
    fn read(&mut self, bytes: &mut [u8]) -> Result<usize, ReadError> {
        Read::read(self, bytes).map_err(Into::into)
    }
}
fn convert_metadata(metadata: std::fs::Metadata) -> Metadata {
    Metadata {
        kind: if metadata.is_file() {
            FileKind::Regular
        } else if metadata.is_dir() {
            FileKind::Directory
        } else {
            FileKind::Other
        },
        len: metadata.len(),
    }
}
#[derive(Debug)]
pub(crate) enum ReadResult {
    Bytes(Vec<u8>),
    Status(Status),
}
fn retry<T>(
    mut operation: impl FnMut() -> Result<T, ReadError>,
    retryable: fn(ReadError) -> bool,
) -> Result<T, ReadError> {
    let mut result = operation();
    while let Err(error) = result
        && retryable(error)
    {
        result = operation();
    }
    result
}
fn interrupted(error: ReadError) -> bool {
    matches!(
        error,
        ReadError::Other {
            kind: std::io::ErrorKind::Interrupted,
            ..
        }
    )
}
/// ETIMEDOUT, which some network filesystems return from a read.
#[cfg(target_os = "linux")]
const ETIMEDOUT: Option<i32> = Some(110);
#[cfg(target_os = "macos")]
const ETIMEDOUT: Option<i32> = Some(60);
#[cfg(not(any(target_os = "linux", target_os = "macos")))]
const ETIMEDOUT: Option<i32> = None;
fn read_retryable(error: ReadError) -> bool {
    let timed_out = matches!(
        error,
        ReadError::Other { raw_os_error, .. } if raw_os_error.is_some() && raw_os_error == ETIMEDOUT
    );
    timed_out || interrupted(error)
}
fn file_classify(error: ReadError) -> Result<ReadResult, ReadError> {
    let status = match error {
        ReadError::Canceled
        | ReadError::SystemResources
        | ReadError::ProcessFdQuotaExceeded
        | ReadError::SystemFdQuotaExceeded => return Err(error),
        ReadError::FileNotFound | ReadError::NotDir => Status::Missing,
        ReadError::IsDir => Status::Directory,
        other => Status::Unreadable(other),
    };
    Ok(ReadResult::Status(status))
}
fn kind_status(kind: FileKind) -> Option<ReadResult> {
    match kind {
        FileKind::Regular => None,
        FileKind::Directory => Some(ReadResult::Status(Status::Directory)),
        FileKind::Other => Some(ReadResult::Status(Status::Unreadable(
            ReadError::NotRegularFile,
        ))),
    }
}
pub(crate) fn file(fs: &impl Fs, path: &Path) -> Result<ReadResult, ReadError> {
    let metadata = match retry(|| fs.metadata(path), interrupted) {
        Ok(value) => value,
        Err(error) => return file_classify(error),
    };
    // Reject FIFOs/devices before open; they can otherwise block before handle stat.
    if let Some(status) = kind_status(metadata.kind) {
        return Ok(status);
    }
    // std's open already retries EINTR; retrying here keeps injected handles honest.
    let mut handle = match retry(|| fs.open(path), interrupted) {
        Ok(value) => value,
        Err(error) => return file_classify(error),
    };
    let metadata = match retry(|| handle.metadata(), interrupted) {
        Ok(value) => value,
        Err(error) => return file_classify(error),
    };
    if let Some(status) = kind_status(metadata.kind) {
        return Ok(status);
    }
    if metadata.len > INPUT_SIZE_MAX as u64 {
        return Ok(ReadResult::Status(Status::ResourceLimit));
    }
    file_read(&mut handle)
}
fn file_read(handle: &mut impl ReadHandle) -> Result<ReadResult, ReadError> {
    let mut bytes = Vec::new();
    let mut buffer = [0_u8; 8192];
    while bytes.len() <= INPUT_SIZE_MAX {
        let capacity = buffer.len().min(INPUT_SIZE_MAX + 1 - bytes.len());
        let count = match retry(|| handle.read(&mut buffer[..capacity]), read_retryable) {
            Ok(value) => value,
            Err(error) => return file_classify(error),
        };
        if count == 0 {
            return Ok(ReadResult::Bytes(bytes));
        }
        bytes.extend_from_slice(&buffer[..count]);
    }
    Ok(ReadResult::Status(Status::ResourceLimit))
}

#[cfg(test)]
mod tests;
