//! Anonymous, page-aligned read/write mappings, and the file mapping and
//! page advice the download writer's mmap path needs.
use std::{fmt, ptr::NonNull};

/// The kernel refused the mapping. Callers treat it as a resource failure,
/// never as a programming error, because it depends on the address space.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MapError;
impl fmt::Display for MapError {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        out.write_str("page mapping failed")
    }
}
impl std::error::Error for MapError {}

/// An anonymous mapping this value owns; dropping it unmaps the pages, and
/// with them any memory policy bound to them.
#[derive(Debug)]
pub struct AnonymousMapping {
    pointer: NonNull<u8>,
    len: usize,
}
// SAFETY: the mapping is exclusively owned, and unmapping it from another
// thread is valid.
unsafe impl Send for AnonymousMapping {}
impl AnonymousMapping {
    /// Maps `len` bytes of zero-filled, readable, writable memory.
    pub fn new(len: usize) -> Result<Self, MapError> {
        map(len).map(|pointer| Self { pointer, len })
    }
    pub fn as_ptr(&self) -> *const u8 {
        self.pointer.as_ptr()
    }
    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        // SAFETY: the exclusive borrow covers the whole live zero-filled
        // mapping, which no other reference aliases.
        unsafe { std::slice::from_raw_parts_mut(self.pointer.as_ptr(), self.len) }
    }
}
impl Drop for AnonymousMapping {
    fn drop(&mut self) {
        // SAFETY: this owner releases its unique mapping once; no borrow of
        // it outlives the owner.
        unsafe { unmap(self.pointer, self.len) };
    }
}

/// Reserves and commits `len` bytes of zero-filled, readable, writable memory.
#[cfg(unix)]
pub fn map(len: usize) -> Result<NonNull<u8>, MapError> {
    // SAFETY: anonymous mmap returns a new writable region with no borrowed address.
    let pointer = unsafe {
        libc::mmap(
            std::ptr::null_mut(),
            len,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANONYMOUS,
            -1,
            0,
        )
    };
    if pointer == libc::MAP_FAILED {
        return Err(MapError);
    }
    if let Some(pointer) = NonNull::new(pointer.cast()) {
        return Ok(pointer);
    }
    // SAFETY: even a successful mapping at address zero needs its matching release.
    unsafe { libc::munmap(pointer, len) };
    Err(MapError)
}
/// Maps `len` bytes of an open file so writes reach the file's pages.
#[cfg(unix)]
pub fn map_file_shared(
    file: std::os::fd::BorrowedFd<'_>,
    len: usize,
) -> std::io::Result<NonNull<u8>> {
    use std::os::fd::AsRawFd;
    // SAFETY: the borrowed descriptor stays open for the call; the kernel
    // chooses a new address, so no existing memory is replaced.
    let pointer = unsafe {
        libc::mmap(
            std::ptr::null_mut(),
            len,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_SHARED,
            file.as_raw_fd(),
            0,
        )
    };
    if pointer == libc::MAP_FAILED {
        return Err(std::io::Error::last_os_error());
    }
    if let Some(pointer) = NonNull::new(pointer.cast()) {
        return Ok(pointer);
    }
    // SAFETY: a successful null mapping still needs to be released.
    unsafe { libc::munmap(pointer, len) };
    Err(std::io::Error::other("null file mapping"))
}
/// Releases a mapping from `map` or `map_file_shared`.
///
/// # Safety
/// The caller transfers the uniquely owned live mapping of `len` bytes at
/// `pointer` and holds no pointers into it afterwards.
#[cfg(unix)]
pub unsafe fn unmap(pointer: NonNull<u8>, len: usize) {
    // SAFETY: forwarded from the caller.
    unsafe { libc::munmap(pointer.as_ptr().cast(), len) };
}
#[cfg(unix)]
pub fn page_size() -> usize {
    // SAFETY: sysconf is a process-local query with no pointer arguments.
    usize::try_from(unsafe { libc::sysconf(libc::_SC_PAGESIZE) }).unwrap_or(4096)
}
/// Drops the resident pages of a range without writing them back to a file.
/// This is `MADV_DONTNEED`, which the mmap download writer uses to keep its
/// dirty-page footprint bounded.
///
/// # Safety
/// The range lies inside a live mapping the caller owns; no Rust reference
/// reads the dropped pages.
#[cfg(unix)]
pub unsafe fn evict(pointer: NonNull<u8>, len: usize) -> std::io::Result<()> {
    // SAFETY: forwarded from the caller.
    unsafe { advise(pointer, len, libc::MADV_DONTNEED) }
}
/// Faults in a range's pages for writing ahead of the writes themselves.
/// Older kernels refuse the advice, which disables opportunistic prefaulting.
///
/// # Safety
/// The range lies inside a live mapping the caller owns.
#[cfg(target_os = "linux")]
pub unsafe fn prefault(pointer: NonNull<u8>, len: usize) -> std::io::Result<()> {
    // SAFETY: forwarded from the caller.
    unsafe { advise(pointer, len, libc::MADV_POPULATE_WRITE) }
}
/// Prefers transparent huge pages when the kernel can provide them. This is
/// an allocation hint, not a requirement: callers keep usable mappings on
/// refusal.
///
/// # Safety
/// The range lies inside a live mapping the caller owns.
#[cfg(target_os = "linux")]
pub unsafe fn prefer_huge_pages(pointer: NonNull<u8>, len: usize) -> std::io::Result<()> {
    // SAFETY: forwarded from the caller.
    unsafe { advise(pointer, len, libc::MADV_HUGEPAGE) }
}
/// Other POSIX hosts do not provide Linux's writable-prefault advice.
///
/// # Safety
/// The range lies inside a live mapping the caller owns.
#[cfg(all(unix, not(target_os = "linux")))]
pub unsafe fn prefault(_: NonNull<u8>, _: usize) -> std::io::Result<()> {
    Err(std::io::ErrorKind::Unsupported.into())
}
/// Hosts other than Linux do not provide transparent-hugepage advice.
///
/// # Safety
/// The range lies inside a live mapping the caller owns.
#[cfg(not(target_os = "linux"))]
pub unsafe fn prefer_huge_pages(_: NonNull<u8>, _: usize) -> std::io::Result<()> {
    Err(std::io::ErrorKind::Unsupported.into())
}
/// # Safety
/// The range lies inside a live mapping the caller owns, and `advice`
/// cannot invalidate memory a Rust reference still reads.
#[cfg(unix)]
unsafe fn advise(pointer: NonNull<u8>, len: usize, advice: libc::c_int) -> std::io::Result<()> {
    // SAFETY: the caller's range is live; madvise changes paging only.
    if unsafe { libc::madvise(pointer.as_ptr().cast(), len, advice) } == 0 {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}

#[cfg(windows)]
#[link(name = "kernel32")]
// SAFETY: callers uphold the documented Win32 mapping ownership contract.
unsafe extern "system" {
    fn VirtualAlloc(
        address: *mut libc::c_void,
        size: usize,
        kind: u32,
        protection: u32,
    ) -> *mut libc::c_void;
    fn VirtualFree(address: *mut libc::c_void, size: usize, kind: u32) -> i32;
}
#[cfg(windows)]
const MEM_COMMIT: u32 = 0x1000;
#[cfg(windows)]
const MEM_RESERVE: u32 = 0x2000;
#[cfg(windows)]
const MEM_RELEASE: u32 = 0x8000;
#[cfg(windows)]
const PAGE_READWRITE: u32 = 0x04;
/// Reserves and commits `len` bytes of zero-filled, readable, writable memory.
#[cfg(windows)]
pub fn map(len: usize) -> Result<NonNull<u8>, MapError> {
    // SAFETY: a null requested address leaves placement to the kernel.
    NonNull::new(
        unsafe {
            VirtualAlloc(
                std::ptr::null_mut(),
                len,
                MEM_COMMIT | MEM_RESERVE,
                PAGE_READWRITE,
            )
        }
        .cast(),
    )
    .ok_or(MapError)
}
/// Releases a reservation from `map`.
///
/// # Safety
/// The caller transfers the one live reservation at `pointer` and holds no
/// pointers into it afterwards.
#[cfg(windows)]
pub unsafe fn unmap(pointer: NonNull<u8>, _: usize) {
    // MEM_RELEASE requires zero size and the original reservation address.
    // SAFETY: forwarded from the caller.
    unsafe { VirtualFree(pointer.as_ptr().cast(), 0, MEM_RELEASE) };
}
#[cfg(windows)]
pub fn page_size() -> usize {
    4096
}

#[cfg(test)]
mod tests;
