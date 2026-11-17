use super::ffi::{self, FutureOps};
use crate::page_mapping;
use std::{alloc::Layout, fmt, ptr::NonNull, sync::Arc};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AllocationKind {
    Pool,
    Shards,
    Slots,
    Pending,
    Ticket,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MappingError;
impl fmt::Display for MappingError {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        out.write_str("source buffer allocation failed")
    }
}
impl std::error::Error for MappingError {}
/// All fallible external operations are invoked outside the pool spin lock.
///
/// # Safety
/// Successful allocations must satisfy the requested layout and remain valid
/// until their matching release. Mappings must cover `size` writable bytes.
/// Implementations must support calls from multiple CRT threads.
pub unsafe trait AllocationOps: Send + Sync + fmt::Debug {
    fn allocate(&self, kind: AllocationKind, layout: Layout) -> Option<NonNull<u8>>;
    /// # Safety
    /// `pointer` must be the still-live allocation returned for this layout.
    unsafe fn release(&self, kind: AllocationKind, pointer: NonNull<u8>, layout: Layout);
    fn mmap(&self, size: usize) -> Result<NonNull<u8>, MappingError>;
    /// # Safety
    /// The pointer must cover a live mapping of `size` bytes from this backend.
    unsafe fn mbind(
        &self,
        pointer: NonNull<u8>,
        size: usize,
        node: u32,
    ) -> Result<(), MappingError>;
    /// # Safety
    /// The pointer must uniquely own a live mapping allocated by this backend.
    unsafe fn munmap(&self, pointer: NonNull<u8>, size: usize);
    /// Offers optional huge-page advice outside the pool lock.
    ///
    /// # Safety
    /// The pointer covers a live writable mapping of `size` bytes.
    unsafe fn prefer_huge_pages(&self, _pointer: NonNull<u8>, _size: usize) {}
    fn current_node(&self) -> Option<u32>;
    fn page_size(&self) -> usize;
    /// Called immediately before a future completion, outside the spin lock.
    fn before_completion(&self) {}
}
/// An owned mapping; dropping it performs its matching unmap outside the lock.
pub struct Mapping {
    pointer: NonNull<u8>,
    size: usize,
    ops: Arc<dyn AllocationOps>,
}
impl fmt::Debug for Mapping {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        out.debug_struct("Mapping")
            .field("size", &self.size)
            .finish_non_exhaustive()
    }
}
// SAFETY: Mapping exclusively owns the allocation and its backend supports cross-thread releases.
unsafe impl Send for Mapping {}
impl Mapping {
    pub(super) fn allocate(
        ops: &Arc<dyn AllocationOps>,
        futures: &dyn FutureOps,
        size: usize,
        node: u32,
    ) -> Result<Self, MappingError> {
        let raise_allocation_failed =
            || futures.raise_error(ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
        let pointer = ops.mmap(size).inspect_err(|_| raise_allocation_failed())?;
        // SAFETY: pointer is the new live mapping returned by this backend.
        if let Err(error) = unsafe { ops.mbind(pointer, size, node) } {
            // SAFETY: failed placement leaves the new mapping exclusively owned here.
            unsafe {
                ops.munmap(pointer, size);
            }
            raise_allocation_failed();
            return Err(error);
        }
        // SAFETY: placement is installed before the optional advice; the mapping is live.
        unsafe { ops.prefer_huge_pages(pointer, size) };
        Ok(Self {
            pointer,
            size,
            ops: Arc::clone(ops),
        })
    }
    pub fn as_ptr(&self) -> *mut u8 {
        self.pointer.as_ptr()
    }
    pub fn len(&self) -> usize {
        self.size
    }
    pub fn is_empty(&self) -> bool {
        self.size == 0
    }
}
impl Drop for Mapping {
    fn drop(&mut self) {
        // SAFETY: this mapping owns the unique live allocation until its destructor.
        unsafe {
            self.ops.munmap(self.pointer, self.size);
        }
    }
}

#[cfg(unix)]
const ALLOCATOR_ALIGNMENT: usize = std::mem::align_of::<libc::max_align_t>();
// The Windows x64 CRT malloc contract provides 16-byte fundamental alignment.
#[cfg(windows)]
const ALLOCATOR_ALIGNMENT: usize = 16;

#[derive(Debug)]
pub(super) struct CrtAllocationOps {
    allocator: *mut crt_sys::AwsAllocator,
}
impl CrtAllocationOps {
    pub(super) fn new(allocator: *mut crt_sys::AwsAllocator) -> Self {
        Self { allocator }
    }
}
// SAFETY: the CRT allocator supports concurrent allocation and outlives every pool reference.
unsafe impl Send for CrtAllocationOps {}
// SAFETY: no mutable Rust state is stored; the CRT allocator synchronizes its own state.
unsafe impl Sync for CrtAllocationOps {}
// SAFETY: CRT allocation, mmap, and matching releases implement the required storage contracts.
unsafe impl AllocationOps for CrtAllocationOps {
    fn allocate(&self, _: AllocationKind, layout: Layout) -> Option<NonNull<u8>> {
        if layout.align() > ALLOCATOR_ALIGNMENT {
            return None;
        }
        // SAFETY: allocator remains valid for this pool; count and size describe writable aligned
        // storage.
        NonNull::new(
            unsafe { crt_sys::native::zaws_allocate_zeroed(self.allocator, 1, layout.size()) }
                .cast(),
        )
    }
    unsafe fn release(&self, _: AllocationKind, pointer: NonNull<u8>, _: Layout) {
        // SAFETY: caller supplies one matching still-live CRT allocation.
        unsafe {
            crt_sys::native::aws_mem_release(self.allocator, pointer.as_ptr().cast());
        }
    }
    fn mmap(&self, size: usize) -> Result<NonNull<u8>, MappingError> {
        page_mapping::map(size).map_err(|_| MappingError)
    }
    unsafe fn mbind(
        &self,
        pointer: NonNull<u8>,
        size: usize,
        node: u32,
    ) -> Result<(), MappingError> {
        // SAFETY: caller guarantees an exclusively owned writable mapping for this length.
        let bytes = unsafe { std::slice::from_raw_parts_mut(pointer.as_ptr(), size) };
        numa::bind_memory_to_node(bytes, node).map_err(|_| MappingError)
    }
    unsafe fn munmap(&self, pointer: NonNull<u8>, size: usize) {
        // SAFETY: caller transfers the unique matching mmap allocation.
        unsafe {
            page_mapping::unmap(pointer, size);
        }
    }
    unsafe fn prefer_huge_pages(&self, pointer: NonNull<u8>, size: usize) {
        // SAFETY: the caller retains a live mapping; this hint changes paging policy only.
        let _ = unsafe { page_mapping::prefer_huge_pages(pointer, size) };
    }
    fn current_node(&self) -> Option<u32> {
        numa::current_cpu().ok().map(|cpu| cpu.node)
    }
    fn page_size(&self) -> usize {
        page_mapping::page_size()
    }
}

#[cfg(all(test, not(miri)))]
mod tests;
