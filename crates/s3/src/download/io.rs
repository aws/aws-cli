use super::{WriteError, diagnostics};
use std::fs::File;
use std::io;

// The probe block and every bounce buffer are aligned to the largest base
// page size each supported host can run with.
pub(crate) const BOUNCE_ALIGNMENT: usize =
    if cfg!(all(target_os = "linux", target_arch = "aarch64")) {
        64 * 1024
    } else if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
        16 * 1024
    } else {
        4096
    };
const BOUNCE_BYTES_MAX: usize = 1024 * 1024;
#[cfg(any(test, feature = "testing"))]
std::thread_local! {
    /// The bounce capacity on this thread, which the writer output model
    /// lowers to a few blocks so a bounced body takes several chunks.
    pub(crate) static BOUNCE_BYTES: std::cell::Cell<usize> =
        const { std::cell::Cell::new(BOUNCE_BYTES_MAX) };
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DirectAlignment {
    pub memory: usize,
    pub offset: usize,
}
impl DirectAlignment {
    pub fn validate(self) -> Result<(), WriteError> {
        if !self.memory.is_power_of_two() || !self.offset.is_power_of_two() {
            return Err(WriteError::DirectInvalidAlignment);
        }
        if self.memory > BOUNCE_ALIGNMENT {
            return Err(WriteError::DirectMemoryAlignmentUnsupported);
        }
        Ok(())
    }
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct IoStats {
    pub calls: u64,
    pub syscall_ns_total: u64,
    pub syscall_ns_max: u64,
    pub interrupted: u64,
    pub short_writes: u64,
    pub madvise_count: u64,
    pub madvise_ns_total: u64,
    pub madvise_ns_max: u64,
    pub mmap_evicted_bytes: u64,
    pub direct_bounce_count: u64,
    pub bounce_bytes: u64,
    pub padded_bytes: u64,
}
impl IoStats {
    fn record_syscall(&mut self, ns: u64) {
        self.calls += 1;
        self.syscall_ns_total = self.syscall_ns_total.saturating_add(ns);
        self.syscall_ns_max = self.syscall_ns_max.max(ns);
    }
    pub(crate) fn record_madvise(&mut self, ns: u64, bytes: usize) {
        self.madvise_count += 1;
        self.madvise_ns_total = self.madvise_ns_total.saturating_add(ns);
        self.madvise_ns_max = self.madvise_ns_max.max(ns);
        self.mmap_evicted_bytes = self.mmap_evicted_bytes.saturating_add(bytes as u64);
    }
    fn add_writes(&mut self, chunk: &Self) {
        self.calls += chunk.calls;
        self.syscall_ns_total = self.syscall_ns_total.saturating_add(chunk.syscall_ns_total);
        self.syscall_ns_max = self.syscall_ns_max.max(chunk.syscall_ns_max);
        self.interrupted += chunk.interrupted;
        self.short_writes += chunk.short_writes;
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DirectPlan {
    pub length: usize,
    pub bounce: bool,
    pub padding: usize,
}
pub fn direct_plan(
    bytes: &[u8],
    offset: u64,
    size: u64,
    alignment: DirectAlignment,
) -> Result<DirectPlan, WriteError> {
    alignment.validate()?;
    let end = offset
        .checked_add(bytes.len() as u64)
        .filter(|&end| end <= size)
        .ok_or(WriteError::OutOfBounds)?;
    if !offset.is_multiple_of(alignment.offset as u64) {
        return Err(WriteError::DirectOffsetUnaligned);
    }
    if bytes.is_empty() {
        return Ok(DirectPlan {
            length: 0,
            bounce: false,
            padding: 0,
        });
    }
    let aligned = bytes.len().is_multiple_of(alignment.offset);
    if !aligned && end != size {
        return Err(WriteError::DirectNonFinalLengthUnaligned);
    }
    let length = bytes
        .len()
        .checked_add(alignment.offset - 1)
        .ok_or(WriteError::OutOfBounds)?
        & !(alignment.offset - 1);
    Ok(DirectPlan {
        length,
        bounce: !aligned || !(bytes.as_ptr() as usize).is_multiple_of(alignment.memory),
        padding: length - bytes.len(),
    })
}
pub trait PositionalWriter: std::fmt::Debug + Send + Sync {
    fn write_at(&self, file: &File, bytes: &[u8], offset: u64) -> io::Result<usize>;
    fn allocate_bounce(
        &self,
        size: usize,
        alignment: usize,
    ) -> io::Result<super::platform::AlignedBuffer> {
        super::platform::AlignedBuffer::new(size, alignment)
    }
}
pub fn write_all(
    writer: &dyn PositionalWriter,
    file: &File,
    bytes: &[u8],
    offset: u64,
    alignment: Option<DirectAlignment>,
) -> Result<IoStats, WriteError> {
    write_loop(bytes, offset, alignment, |bytes, offset| {
        writer.write_at(file, bytes, offset)
    })
}
pub(crate) fn write_loop(
    bytes: &[u8],
    offset: u64,
    alignment: Option<DirectAlignment>,
    mut write: impl FnMut(&[u8], u64) -> io::Result<usize>,
) -> Result<IoStats, WriteError> {
    let mut stats = IoStats::default();
    let mut index = 0;
    while index < bytes.len() {
        let position = offset
            .checked_add(index as u64)
            .ok_or(WriteError::Overflow)?;
        if position > i64::MAX as u64 {
            return Err(WriteError::FileTooBig);
        }
        let remaining = &bytes[index..];
        let started = diagnostics::start();
        let result = write(remaining, position);
        if diagnostics::ENABLED {
            stats.record_syscall(diagnostics::elapsed_ns(started));
        }
        let written = match result {
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {
                stats.interrupted += u64::from(cfg!(feature = "download-writer-debug"));
                continue;
            }
            result => result.map_err(WriteError::positional_write)?,
        };
        validate_written(written, remaining.len(), alignment)?;
        stats.short_writes +=
            u64::from(cfg!(feature = "download-writer-debug") && written < remaining.len());
        index += written;
    }
    Ok(stats)
}
fn validate_written(
    written: usize,
    length: usize,
    alignment: Option<DirectAlignment>,
) -> Result<(), WriteError> {
    if written == 0 {
        return Err(WriteError::WriteZero);
    }
    if written > length {
        return Err(WriteError::WriteRejected);
    }
    if written < length
        && alignment
            .is_some_and(|a| !written.is_multiple_of(a.offset) || !written.is_multiple_of(a.memory))
    {
        return Err(WriteError::DirectShortWriteUnaligned);
    }
    Ok(())
}
pub fn write_direct(
    writer: &dyn PositionalWriter,
    file: &File,
    bytes: &[u8],
    offset: u64,
    size: u64,
    alignment: DirectAlignment,
) -> Result<IoStats, WriteError> {
    let plan = direct_plan(bytes, offset, size, alignment)?;
    if !plan.bounce {
        return write_all(writer, file, bytes, offset, Some(alignment));
    }
    #[cfg(not(any(test, feature = "testing")))]
    let capacity = BOUNCE_BYTES_MAX.max(alignment.offset).min(plan.length);
    #[cfg(any(test, feature = "testing"))]
    let capacity = BOUNCE_BYTES.get().max(alignment.offset).min(plan.length);
    let mut bounce = writer.allocate_bounce(capacity, BOUNCE_ALIGNMENT)?;
    let mut stats = IoStats::default();
    let mut written = 0;
    while written < plan.length {
        let length = capacity.min(plan.length - written);
        let end = (written + length).min(bytes.len());
        let copied = end - written;
        bounce.as_mut_slice()[..copied].copy_from_slice(&bytes[written..end]);
        bounce.as_mut_slice()[copied..length].fill(0);
        let position = offset
            .checked_add(written as u64)
            .ok_or(WriteError::Overflow)?;
        let chunk = write_all(
            writer,
            file,
            &bounce.as_slice()[..length],
            position,
            Some(alignment),
        )?;
        stats.add_writes(&chunk);
        written += length;
    }
    if cfg!(feature = "download-writer-debug") {
        stats.direct_bounce_count = 1;
        stats.bounce_bytes = bytes.len() as u64;
        stats.padded_bytes = plan.padding as u64;
    }
    Ok(stats)
}
#[cfg(test)]
mod tests;
