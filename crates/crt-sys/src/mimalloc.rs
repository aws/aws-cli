use std::alloc::{GlobalAlloc, Layout};
use std::ffi::c_void;

// SAFETY CONTRACT: mimalloc's aligned API from the pinned 3.3.2 headers.
// Each call accepts any size and power-of-two alignment, returns null on
// failure, and frees only blocks mimalloc allocated.
unsafe extern "C" {
    fn mi_malloc_aligned(size: usize, alignment: usize) -> *mut c_void;
    fn mi_zalloc_aligned(size: usize, alignment: usize) -> *mut c_void;
    fn mi_realloc_aligned(ptr: *mut c_void, newsize: usize, alignment: usize) -> *mut c_void;
    fn mi_free(ptr: *mut c_void);
}

/// The process allocator for the static musl executable.
#[derive(Debug, Clone, Copy, Default)]
pub struct Mimalloc;

// SAFETY: every block comes from mimalloc with the layout's alignment, and
// `dealloc` and `realloc` receive only blocks this allocator returned.
unsafe impl GlobalAlloc for Mimalloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        // SAFETY: Layout guarantees a power-of-two alignment.
        unsafe { mi_malloc_aligned(layout.size(), layout.align()).cast() }
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        // SAFETY: Layout guarantees a power-of-two alignment.
        unsafe { mi_zalloc_aligned(layout.size(), layout.align()).cast() }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, _layout: Layout) {
        // SAFETY: the caller passes a live block this allocator returned.
        unsafe { mi_free(ptr.cast()) }
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        // SAFETY: the caller passes a live block this allocator returned with
        // `layout`, whose alignment the grown block keeps.
        unsafe { mi_realloc_aligned(ptr.cast(), new_size, layout.align()).cast() }
    }
}
