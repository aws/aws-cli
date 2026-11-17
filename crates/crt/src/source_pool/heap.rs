use super::allocation::{AllocationKind, AllocationOps};
use std::{
    alloc::Layout,
    ops::{Deref, DerefMut},
    ptr::NonNull,
    sync::Arc,
};
pub(super) fn allocate_value<T>(
    ops: &Arc<dyn AllocationOps>,
    kind: AllocationKind,
    value: T,
) -> Result<*mut T, T> {
    let Some(pointer) = ops.allocate(kind, Layout::new::<T>()) else {
        return Err(value);
    };
    let pointer = pointer.cast::<T>().as_ptr();
    // SAFETY: the AllocationOps contract provides correctly aligned storage for T.
    unsafe {
        pointer.write(value);
    }
    Ok(pointer)
}
/// # Safety
/// The pointer must uniquely own an initialized value allocated by allocate_value.
pub(super) unsafe fn release_value<T>(
    ops: &Arc<dyn AllocationOps>,
    kind: AllocationKind,
    pointer: *mut T,
) {
    // SAFETY: caller transfers the matching unique value and storage.
    unsafe {
        std::ptr::drop_in_place(pointer);
        ops.release(
            kind,
            NonNull::new_unchecked(pointer.cast()),
            Layout::new::<T>(),
        );
    }
}
#[derive(Debug)]
pub(super) struct HeapSlice<T> {
    pointer: NonNull<T>,
    len: usize,
    ops: Arc<dyn AllocationOps>,
    kind: AllocationKind,
}
// SAFETY: the slice exclusively owns its values and its allocator supports cross-thread releases.
unsafe impl<T: Send> Send for HeapSlice<T> {}
impl<T> HeapSlice<T> {
    pub(super) fn new(
        ops: &Arc<dyn AllocationOps>,
        kind: AllocationKind,
        len: usize,
        mut value: impl FnMut(usize) -> T,
    ) -> Option<Self> {
        let layout = Layout::array::<T>(len).ok()?;
        let pointer = ops.allocate(kind, layout)?.cast::<T>();
        for index in 0..len {
            // SAFETY: each indexed slot is within this allocation and initialized exactly once.
            unsafe {
                pointer.as_ptr().add(index).write(value(index));
            }
        }
        Some(Self {
            pointer,
            len,
            ops: Arc::clone(ops),
            kind,
        })
    }
}
impl<T> Deref for HeapSlice<T> {
    type Target = [T];
    fn deref(&self) -> &[T] {
        // SAFETY: the allocation contains len initialized T values for this owner's lifetime.
        unsafe { std::slice::from_raw_parts(self.pointer.as_ptr(), self.len) }
    }
}
impl<T> DerefMut for HeapSlice<T> {
    fn deref_mut(&mut self) -> &mut [T] {
        // SAFETY: mutable access to the owner provides exclusive access to its initialized values.
        unsafe { std::slice::from_raw_parts_mut(self.pointer.as_ptr(), self.len) }
    }
}
impl<T> Drop for HeapSlice<T> {
    fn drop(&mut self) {
        let layout = Layout::array::<T>(self.len);
        if let Ok(layout) = layout {
            // SAFETY: the unique owner drops each initialized value before releasing its matching
            // allocation.
            unsafe {
                std::ptr::drop_in_place(std::ptr::slice_from_raw_parts_mut(
                    self.pointer.as_ptr(),
                    self.len,
                ));
                self.ops.release(self.kind, self.pointer.cast(), layout);
            }
        }
    }
}

pub(super) struct UninitValue<T> {
    pointer: NonNull<T>,
    ops: Arc<dyn AllocationOps>,
    kind: AllocationKind,
}
impl<T> UninitValue<T> {
    pub(super) fn new(ops: &Arc<dyn AllocationOps>, kind: AllocationKind) -> Option<Self> {
        Some(Self {
            pointer: ops.allocate(kind, Layout::new::<T>())?.cast(),
            ops: Arc::clone(ops),
            kind,
        })
    }
    pub(super) fn initialize(self, value: T) -> *mut T {
        let pointer = self.pointer.as_ptr();
        // SAFETY: this guard uniquely owns correctly aligned uninitialized storage for T.
        unsafe {
            pointer.write(value);
        }
        let mut owner = std::mem::ManuallyDrop::new(self);
        // SAFETY: only the guard's Arc field is dropped; storage moved to the initialized value.
        unsafe {
            std::ptr::drop_in_place(&mut owner.ops);
        }
        pointer
    }
}
impl<T> Drop for UninitValue<T> {
    fn drop(&mut self) {
        // SAFETY: storage remains uninitialized and uniquely owned by this guard.
        unsafe {
            self.ops
                .release(self.kind, self.pointer.cast(), Layout::new::<T>());
        }
    }
}
