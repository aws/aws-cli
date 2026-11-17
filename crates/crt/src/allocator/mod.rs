//! Rust allocation adapter with CRT-compatible alignment and allocation tracking.
use crt_sys::{self as ffi, native as c};
use std::alloc::{Layout, alloc, dealloc};
use std::ffi::c_void;
use std::ptr::NonNull;
use std::sync::atomic::{AtomicUsize, Ordering};

const HEADER_LEN: usize = 16;
#[cfg(test)]
const POISON: u8 = 0xa5;

#[derive(Debug, Default)]
struct State {
    outstanding: AtomicUsize,
    #[cfg(test)]
    attempts: AtomicUsize,
    #[cfg(test)]
    released: AtomicUsize,
    #[cfg(test)]
    fail_at: usize,
}

/// A heap-stable adapter retaining block lengths for Rust deallocation. It is
/// the crate's tracking allocator: tests pass it to CRT-owned objects and the
/// drop check reports any block left outstanding.
#[derive(Debug)]
pub struct Allocator {
    pointer: NonNull<ffi::AwsAllocator>,
    state: Box<State>,
}
impl Allocator {
    pub fn new() -> Option<Self> {
        Self::with_state(Box::default())
    }
    #[cfg(all(test, not(miri)))]
    pub(crate) fn failing_at(fail_at: usize) -> Option<Self> {
        Self::with_state(Box::new(State {
            fail_at,
            ..State::default()
        }))
    }
    fn with_state(state: Box<State>) -> Option<Self> {
        let data = (&raw const *state).cast_mut().cast();
        // SAFETY: callback data is heap-stable until all blocks and adapter die.
        let pointer = NonNull::new(unsafe { c::zaws_allocator_new(acquire, release, data) })?;
        Some(Self { pointer, state })
    }
    /// Borrows the CRT allocator table.
    ///
    /// # Safety
    /// Every object allocated through this pointer must be released before self.
    pub unsafe fn as_ptr(&self) -> *mut ffi::AwsAllocator {
        self.pointer.as_ptr()
    }
    pub fn outstanding(&self) -> usize {
        self.state.outstanding.load(Ordering::Relaxed)
    }
    #[cfg(all(test, not(miri)))]
    pub(crate) fn counts(&self) -> (usize, usize, usize) {
        (
            self.state.attempts.load(Ordering::Relaxed),
            self.state.released.load(Ordering::Relaxed),
            self.outstanding(),
        )
    }
}
impl Drop for Allocator {
    fn drop(&mut self) {
        assert_eq!(self.outstanding(), 0, "allocator still owns CRT blocks");
        // SAFETY: all blocks are gone and this adapter has one owner.
        unsafe {
            c::zaws_allocator_destroy(self.pointer.as_ptr());
        }
    }
}
unsafe extern "C" fn acquire(data: *mut c_void, size: usize) -> *mut c_void {
    // SAFETY: data is the adapter's boxed State, retained until its last block is released.
    let state = unsafe { &*data.cast::<State>() };
    #[cfg(test)]
    if state.attempts.fetch_add(1, Ordering::Relaxed) + 1 == state.fail_at {
        return std::ptr::null_mut();
    }
    let Some(total) = size.checked_add(HEADER_LEN) else {
        return std::ptr::null_mut();
    };
    let Ok(layout) = Layout::from_size_align(total, HEADER_LEN) else {
        return std::ptr::null_mut();
    };
    // SAFETY: layout is valid and nonzero; allocation failure is represented null.
    let base = unsafe { alloc(layout) };
    if base.is_null() {
        return std::ptr::null_mut();
    }
    // SAFETY: base spans layout.size bytes and is usize-aligned; the size bytes
    // after the header are the block this acquisition owns.
    let block = unsafe {
        base.cast::<usize>().write(total);
        let block = base.add(HEADER_LEN);
        #[cfg(test)]
        block.write_bytes(POISON, size);
        block
    };
    state.outstanding.fetch_add(1, Ordering::Relaxed);
    block.cast()
}
unsafe extern "C" fn release(data: *mut c_void, ptr: *mut c_void) {
    if ptr.is_null() {
        return;
    }
    // SAFETY: CRT returns exactly a block from acquire; its header records layout.
    // data is the adapter's State, retained until this last release returns.
    unsafe {
        let base = ptr.cast::<u8>().sub(HEADER_LEN);
        let total = base.cast::<usize>().read();
        let layout = Layout::from_size_align_unchecked(total, HEADER_LEN);
        dealloc(base, layout);
        let state = &*data.cast::<State>();
        state.outstanding.fetch_sub(1, Ordering::Relaxed);
        #[cfg(test)]
        state.released.fetch_add(1, Ordering::Relaxed);
    }
}
#[cfg(test)]
mod tests;
