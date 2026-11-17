use std::{alloc::Layout, io, ptr::NonNull};

#[derive(Debug)]
pub struct AlignedBuffer {
    pointer: NonNull<u8>,
    layout: Layout,
}
impl AlignedBuffer {
    pub fn new(size: usize, alignment: usize) -> io::Result<Self> {
        let layout = Layout::from_size_align(size.max(1), alignment)
            .map_err(|_| io::Error::from(io::ErrorKind::InvalidInput))?;
        // SAFETY: layout is valid and nonempty; zero padding is part of the direct tail contract.
        let pointer = unsafe { std::alloc::alloc_zeroed(layout) };
        let pointer =
            NonNull::new(pointer).ok_or_else(|| io::Error::from(io::ErrorKind::OutOfMemory))?;
        Ok(Self { pointer, layout })
    }
    pub fn as_slice(&self) -> &[u8] {
        // SAFETY: allocation is initialized and owned for the lifetime of this borrow.
        unsafe { std::slice::from_raw_parts(self.pointer.as_ptr(), self.layout.size()) }
    }
    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        // SAFETY: the exclusive borrow owns all initialized allocation bytes.
        unsafe { std::slice::from_raw_parts_mut(self.pointer.as_ptr(), self.layout.size()) }
    }
}
impl Drop for AlignedBuffer {
    fn drop(&mut self) {
        // SAFETY: pointer was allocated with this layout and is released exactly once.
        unsafe {
            std::alloc::dealloc(self.pointer.as_ptr(), self.layout);
        }
    }
}
