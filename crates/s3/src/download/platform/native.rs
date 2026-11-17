use super::*;
use crt::page_mapping;
use std::{
    os::fd::{AsFd, AsRawFd},
    ptr::NonNull,
};

#[derive(Clone, Copy, Debug, Default)]
pub struct NativePlatform;
impl PositionalWriter for NativePlatform {
    fn write_at(&self, file: &File, bytes: &[u8], offset: u64) -> io::Result<usize> {
        use std::os::unix::fs::FileExt;
        file.write_at(bytes, offset)
    }
}
impl Platform for NativePlatform {
    fn direct_io_available(&self) -> bool {
        cfg!(target_os = "linux")
    }
    fn mmap_available(&self) -> bool {
        cfg!(target_os = "linux")
    }
    fn page_size(&self) -> usize {
        page_mapping::page_size()
    }
    fn mmap_file(&self, file: &File, size: usize) -> io::Result<Arc<dyn MappedFile>> {
        if !self.mmap_available() {
            return Err(io::ErrorKind::Unsupported.into());
        }
        let pointer = page_mapping::map_file_shared(file.as_fd(), size)?;
        Ok(Arc::new(Mapping {
            pointer,
            length: size,
        }))
    }
    fn enable_direct_io(&self, file: &File) -> io::Result<()> {
        set_direct(file, true)
    }
    fn disable_direct_io(&self, file: &File) -> io::Result<()> {
        set_direct(file, false)
    }
    fn direct_io_alignment(&self, file: &File) -> io::Result<DirectAlignment> {
        direct_alignment(file, self.page_size())
    }
    fn preallocate(&self, file: &File, size: u64) -> io::Result<Preallocation> {
        preallocate(file, size)
    }
    fn discover_numa(&self) -> Result<numa::Topology, numa::NumaError> {
        numa::discover()
    }
    fn apply_numa(&self, node: &numa::NodeInfo) -> Result<(), numa::NumaError> {
        numa::apply_current_thread(node)
    }
    fn probe_numa(&self, node: &numa::NodeInfo) -> Result<(), numa::NumaError> {
        numa::apply_current_thread(node)?;
        bind_probe_page(node.id).map(|_| ())
    }
    fn probe_numa_memory(&self, node: u32) -> Result<(), numa::NumaError> {
        bind_probe_page(node).map(|_| ())
    }
    fn thread_minor_faults(&self) -> u64 {
        minor_faults()
    }
    fn close_file(&self, file: File) -> Result<(), CloseError> {
        close_once(file)
    }
}
pub(super) fn bind_probe_page(node: u32) -> Result<usize, numa::NumaError> {
    let mut page = probe_mapping(page_mapping::page_size())?;
    numa::bind_memory_to_node(page.as_mut_slice(), node)?;
    Ok(page.as_ptr().addr())
}
pub(super) fn probe_mapping(len: usize) -> Result<page_mapping::AnonymousMapping, numa::NumaError> {
    page_mapping::AnonymousMapping::new(len).map_err(|_| numa::NumaError::MappingFailed)
}
/// Closes the descriptor `file` owns exactly once. Linux and macOS release
/// it even when the close fails, so a failed close is never retried: by then
/// another thread could have opened a file under the same number.
fn close_once(file: File) -> Result<(), CloseError> {
    use std::os::fd::IntoRawFd;
    let descriptor = file.into_raw_fd();
    // SAFETY: `into_raw_fd` gave up the file's ownership of this live
    // descriptor, so nothing else closes it or uses it after this call.
    if unsafe { close_descriptor(descriptor) } == 0 {
        return Ok(());
    }
    Err(close_error(io::Error::last_os_error().raw_os_error()))
}
#[cfg(target_os = "macos")]
unsafe extern "C" {
    /// macOS's close that is not a pthread cancellation point, so a pending
    /// cancellation cannot leave before the descriptor is released. It is bound
    /// here on every macOS architecture, where `libc` maps it only on x86.
    #[link_name = "close$NOCANCEL"]
    fn close_nocancel(descriptor: libc::c_int) -> libc::c_int;
}
/// # Safety
/// The caller owns `descriptor`, which nothing uses after this call.
#[cfg(target_os = "macos")]
unsafe fn close_descriptor(descriptor: libc::c_int) -> libc::c_int {
    // SAFETY: forwarded from the caller.
    unsafe { close_nocancel(descriptor) }
}
/// # Safety
/// The caller owns `descriptor`, which nothing uses after this call.
#[cfg(not(target_os = "macos"))]
unsafe fn close_descriptor(descriptor: libc::c_int) -> libc::c_int {
    // SAFETY: forwarded from the caller.
    unsafe { libc::close(descriptor) }
}
pub(super) fn close_error(errno: Option<i32>) -> CloseError {
    match errno {
        Some(libc::EIO) => CloseError::InputOutput,
        Some(libc::ENOSPC) => CloseError::NoSpaceLeft,
        Some(libc::EDQUOT) => CloseError::DiskQuota,
        Some(libc::EINTR) => CloseError::Interrupted,
        errno => {
            debug_assert_ne!(errno, Some(libc::EBADF), "closed an invalid descriptor");
            CloseError::Unexpected
        }
    }
}
#[derive(Debug)]
struct Mapping {
    pointer: NonNull<u8>,
    length: usize,
}
// SAFETY: copies require exclusive byte ranges; advice never creates Rust references.
unsafe impl Send for Mapping {}
// SAFETY: users must audit disjoint ranges before concurrent copies; lifetime is Arc-owned.
unsafe impl Sync for Mapping {}
impl MappedFile for Mapping {
    fn len(&self) -> usize {
        self.length
    }
    unsafe fn copy_unique(&self, offset: usize, bytes: &[u8], mode: CopyMode) -> CopyPath {
        assert!(offset <= self.length && bytes.len() <= self.length - offset);
        // SAFETY: caller supplies an in-bounds range disjoint from all other writers.
        let target = unsafe {
            std::slice::from_raw_parts_mut(self.pointer.as_ptr().add(offset), bytes.len())
        };
        super::super::stream_copy::copy(mode, target, bytes)
    }
    fn advise(&self, range: Range<usize>, advice: Advice) -> io::Result<()> {
        if range.start > range.end || range.end > self.length {
            return Err(io::ErrorKind::InvalidInput.into());
        }
        if range.is_empty() {
            return Ok(());
        }
        // SAFETY: the checked range starts inside this live mapping.
        let start = unsafe { self.pointer.add(range.start) };
        // SAFETY: the checked range is inside this live shared file mapping,
        // so evicted pages reload from the file; advice changes paging only.
        unsafe {
            match advice {
                Advice::Evict => page_mapping::evict(start, range.len()),
                Advice::Populate => page_mapping::prefault(start, range.len()),
                Advice::HugePages => page_mapping::prefer_huge_pages(start, range.len()),
            }
        }
    }
}
impl Drop for Mapping {
    fn drop(&mut self) {
        // SAFETY: this owner unmaps once after all Arc users have released the region.
        unsafe {
            page_mapping::unmap(self.pointer, self.length);
        }
    }
}
#[cfg(target_os = "linux")]
fn set_direct(file: &File, enabled: bool) -> io::Result<()> {
    let flags = retry(|| {
        // SAFETY: F_GETFL reads flags from a live descriptor.
        unsafe { libc::fcntl(file.as_raw_fd(), libc::F_GETFL) }
    })?;
    if (flags & libc::O_DIRECT != 0) == enabled {
        return Ok(());
    }
    retry(|| {
        let flags = if enabled {
            flags | libc::O_DIRECT
        } else {
            flags & !libc::O_DIRECT
        };
        // SAFETY: F_SETFL preserves unrelated status flags and changes only O_DIRECT.
        unsafe { libc::fcntl(file.as_raw_fd(), libc::F_SETFL, flags) }
    })
    .map(|_| ())
}
#[cfg(not(target_os = "linux"))]
fn set_direct(_: &File, enabled: bool) -> io::Result<()> {
    if enabled {
        Err(io::ErrorKind::Unsupported.into())
    } else {
        Ok(())
    }
}
#[cfg(target_os = "linux")]
fn direct_alignment(file: &File, page_size: usize) -> io::Result<DirectAlignment> {
    // SAFETY: zero initializes plain kernel output storage.
    let mut stat: super::statx::Statx = unsafe { std::mem::zeroed() };
    // SAFETY: AT_EMPTY_PATH selects the live file descriptor, stat is writable output storage.
    let result = unsafe {
        libc::syscall(
            libc::SYS_statx,
            file.as_raw_fd(),
            c"".as_ptr(),
            libc::AT_EMPTY_PATH,
            super::statx::STATX_DIOALIGN,
            &mut stat as *mut super::statx::Statx,
        )
    };
    if result == 0
        && stat.stx_mask & super::statx::STATX_DIOALIGN != 0
        && stat.stx_dio_mem_align > 0
        && stat.stx_dio_offset_align > 0
    {
        return Ok(DirectAlignment {
            memory: stat.stx_dio_mem_align as usize,
            offset: stat.stx_dio_offset_align as usize,
        });
    }
    if result != 0 {
        let error = io::Error::last_os_error();
        if !matches!(
            error.raw_os_error(),
            Some(libc::EINVAL | libc::ENOSYS | libc::EOPNOTSUPP)
        ) {
            return Err(error);
        }
    }
    Ok(DirectAlignment {
        memory: page_size,
        offset: page_size,
    })
}
#[cfg(not(target_os = "linux"))]
fn direct_alignment(_: &File, _: usize) -> io::Result<DirectAlignment> {
    Err(io::ErrorKind::Unsupported.into())
}
#[cfg(target_os = "linux")]
fn preallocate(file: &File, size: u64) -> io::Result<Preallocation> {
    // SAFETY: caller bounds size to off_t and retains the writable file descriptor.
    let result = unsafe { libc::fallocate(file.as_raw_fd(), 0, 0, size as libc::off_t) };
    if result == 0 {
        return Ok(Preallocation::Confirmed);
    }
    let error = io::Error::last_os_error();
    if matches!(
        error.raw_os_error(),
        Some(libc::EOPNOTSUPP | libc::ENOSYS | libc::EINVAL)
    ) {
        Ok(Preallocation::Unsupported)
    } else {
        Err(error)
    }
}
#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn preallocate(_: &File, _: u64) -> io::Result<Preallocation> {
    Ok(Preallocation::Unsupported)
}
#[cfg(target_os = "linux")]
fn minor_faults() -> u64 {
    // SAFETY: zero initializes plain kernel output storage.
    let mut usage: libc::rusage = unsafe { std::mem::zeroed() };
    // SAFETY: usage points to live writable output storage.
    let result = unsafe { libc::getrusage(libc::RUSAGE_THREAD, &mut usage) };
    if result == 0 {
        usage.ru_minflt.max(0) as u64
    } else {
        0
    }
}
#[cfg(not(target_os = "linux"))]
fn minor_faults() -> u64 {
    0
}
#[cfg(target_os = "linux")]
fn retry(mut syscall: impl FnMut() -> i32) -> io::Result<i32> {
    loop {
        let result = syscall();
        if result >= 0 {
            return Ok(result);
        }
        let error = io::Error::last_os_error();
        if error.kind() != io::ErrorKind::Interrupted {
            return Err(error);
        }
    }
}

#[cfg(target_os = "macos")]
fn preallocate(file: &File, size: u64) -> io::Result<Preallocation> {
    let mut store = libc::fstore_t {
        fst_flags: libc::F_ALLOCATEALL,
        fst_posmode: libc::F_PEOFPOSMODE,
        fst_offset: 0,
        fst_length: size as libc::off_t,
        fst_bytesalloc: 0,
    };
    // SAFETY: F_PREALLOCATE receives its native fstore_t layout and a live writable descriptor.
    let result = unsafe { libc::fcntl(file.as_raw_fd(), libc::F_PREALLOCATE, &mut store) };
    if result == 0 {
        return Ok(Preallocation::Confirmed);
    }
    let error = io::Error::last_os_error();
    if matches!(
        error.raw_os_error(),
        Some(libc::EOPNOTSUPP | libc::ENOSYS | libc::EINVAL)
    ) {
        Ok(Preallocation::Unsupported)
    } else {
        Err(error)
    }
}
