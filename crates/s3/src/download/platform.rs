//! Injectable operating-system boundaries for file preparation and mapped output.
mod aligned;
#[cfg(unix)]
mod native;
#[cfg(target_os = "linux")]
mod statx;
#[cfg(windows)]
mod windows;
#[doc(inline)]
pub use super::io::{DirectAlignment, PositionalWriter};
use super::{
    CloseError, WriteError,
    stream_copy::{CopyMode, CopyPath},
};
#[doc(inline)]
pub use aligned::AlignedBuffer;
#[doc(inline)]
#[cfg(unix)]
pub use native::NativePlatform;
use std::{fmt, fs::File, io, ops::Range, sync::Arc};
#[doc(inline)]
#[cfg(windows)]
pub use windows::NativePlatform;

/// The host's stable name in writer diagnostics: `linux`, `macos`, and
/// `unsupported` on any other host.
pub const NAME: &str = if cfg!(target_os = "linux") {
    "linux"
} else if cfg!(target_os = "macos") {
    "macos"
} else {
    "unsupported"
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Preallocation {
    NotNeeded,
    Confirmed,
    Unsupported,
}
/// A mapped output region, owned until every writer and prefaulter has joined.
pub trait MappedFile: fmt::Debug + Send + Sync {
    fn len(&self) -> usize;
    fn is_empty(&self) -> bool {
        self.len() == 0
    }
    /// Copies one audited, nonoverlapping body into this mapping.
    ///
    /// # Safety
    /// The byte range must be in bounds and disjoint from every concurrent copy.
    unsafe fn copy_unique(&self, offset: usize, bytes: &[u8], mode: CopyMode) -> CopyPath;
    fn advise(&self, range: Range<usize>, advice: Advice) -> io::Result<()>;
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Advice {
    Evict,
    Populate,
    HugePages,
}
pub(crate) fn advise_error_name(error: &io::Error) -> &'static str {
    if error.kind() == io::ErrorKind::Unsupported {
        crate::local_error::UNSUPPORTED
    } else {
        crate::local_error::ADVISE_FAILED
    }
}
#[cfg_attr(
    not(unix),
    expect(unused_variables, reason = "only unix names mmap errnos")
)]
pub(crate) fn mmap_error_name(error: &io::Error) -> &'static str {
    #[cfg(unix)]
    if let Some(errno) = error.raw_os_error() {
        return match errno {
            libc::ETXTBSY | libc::EACCES => crate::local_error::ACCESS_DENIED,
            libc::EPERM => crate::local_error::PERMISSION_DENIED,
            libc::EAGAIN => crate::local_error::LOCKED_MEMORY_LIMIT_EXCEEDED,
            libc::ENODEV => crate::local_error::MEMORY_MAPPING_NOT_SUPPORTED,
            libc::EMFILE => crate::local_error::PROCESS_FD_QUOTA_EXCEEDED,
            libc::ENFILE => crate::local_error::SYSTEM_FD_QUOTA_EXCEEDED,
            libc::ENOMEM => crate::local_error::OUT_OF_MEMORY,
            libc::EEXIST => crate::local_error::MAPPING_ALREADY_EXISTS,
            _ => crate::local_error::UNEXPECTED,
        };
    }
    crate::local_error::UNEXPECTED
}
pub(crate) fn direct_io_error_name(error: &io::Error) -> &'static str {
    #[cfg(unix)]
    match error.raw_os_error() {
        Some(libc::EINVAL | libc::EOPNOTSUPP) => return "DownloadDirectWriterUnavailable",
        Some(libc::EBADF) => return crate::local_error::NOT_OPEN_FOR_WRITING,
        _ => {}
    }
    if error.kind() == io::ErrorKind::Unsupported {
        "DownloadDirectWriterUnavailable"
    } else {
        crate::local_error::UNEXPECTED
    }
}
/// File, topology, and mapping operations used by the writer state machine.
pub trait Platform: PositionalWriter {
    fn direct_io_available(&self) -> bool;
    fn mmap_available(&self) -> bool;
    fn page_size(&self) -> usize;
    fn mmap_file(&self, file: &File, size: usize) -> io::Result<Arc<dyn MappedFile>>;
    fn enable_direct_io(&self, file: &File) -> io::Result<()>;
    fn disable_direct_io(&self, file: &File) -> io::Result<()>;
    fn direct_io_alignment(&self, file: &File) -> io::Result<DirectAlignment>;
    fn preallocate(&self, file: &File, size: u64) -> io::Result<Preallocation>;
    fn discover_numa(&self) -> Result<numa::Topology, numa::NumaError>;
    fn apply_numa(&self, node: &numa::NodeInfo) -> Result<(), numa::NumaError>;
    fn probe_numa(&self, node: &numa::NodeInfo) -> Result<(), numa::NumaError>;
    /// Binds one fresh page to `node` and releases it. Memory only: unlike
    /// `probe_numa`, no thread is pinned.
    fn probe_numa_memory(&self, node: u32) -> Result<(), numa::NumaError>;
    fn thread_minor_faults(&self) -> u64;
    fn set_length(&self, file: &File, size: u64) -> io::Result<()> {
        file.set_len(size)
    }
    /// Closes an output file once, consuming it on success or error, and
    /// reports a delayed write failure the close found. It never retries.
    fn close_file(&self, file: File) -> Result<(), CloseError>;
}
pub(crate) fn reserve(
    platform: &dyn Platform,
    file: &File,
    size: u64,
) -> Result<Preallocation, WriteError> {
    if size == 0 {
        return Ok(Preallocation::NotNeeded);
    }
    if size > i64::MAX as u64 {
        return Err(WriteError::FileTooBig);
    }
    loop {
        match platform.preallocate(file, size) {
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            result => return result.map_err(WriteError::preallocate),
        }
    }
}
pub(crate) fn set_length(
    platform: &dyn Platform,
    file: &File,
    size: u64,
) -> Result<(), WriteError> {
    if size > i64::MAX as u64 {
        return Err(WriteError::FileTooBig);
    }
    loop {
        match platform.set_length(file, size) {
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            result => return result.map_err(WriteError::set_length),
        }
    }
}

#[cfg(all(test, unix))]
mod tests;
