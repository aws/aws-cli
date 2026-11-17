use super::ffi;
use crate::allocator;
#[cfg(target_os = "linux")]
use std::ptr::NonNull;

pub(super) struct Allocator(allocator::Allocator);

impl Allocator {
    pub(super) fn new(fail_at: usize) -> Result<Self, &'static str> {
        allocator::Allocator::failing_at(fail_at)
            .map(Self)
            .ok_or("allocator adapter allocation failed")
    }

    pub(super) fn as_ptr(&self) -> *mut ffi::AwsAllocator {
        // SAFETY: each test releases its storage before the fixture drops, and the
        // adapter's drop asserts that no block is outstanding.
        unsafe { self.0.as_ptr() }
    }

    pub(super) fn counts(&self) -> (usize, usize, usize) {
        self.0.counts()
    }
}

#[cfg(target_os = "linux")]
pub(super) struct Pool(NonNull<ffi::AwsS3BufferPool>);

#[cfg(target_os = "linux")]
impl Pool {
    pub(super) fn new(raw: *mut ffi::AwsS3BufferPool) -> Option<Self> {
        NonNull::new(raw).map(Self)
    }
}

#[cfg(target_os = "linux")]
impl Drop for Pool {
    fn drop(&mut self) {
        // SAFETY: factory returned one owned reference with the pool's matching release callback.
        unsafe {
            if let Some(release) = (*self.0.as_ref().vtable).release {
                release(self.0.as_ptr());
            }
        }
    }
}
