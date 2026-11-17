use super::*;
use std::os::windows::fs::FileExt;

#[derive(Clone, Copy, Debug, Default)]
pub struct NativePlatform;
impl PositionalWriter for NativePlatform {
    fn write_at(&self, file: &File, bytes: &[u8], offset: u64) -> io::Result<usize> {
        file.seek_write(bytes, offset)
    }
}
impl Platform for NativePlatform {
    fn direct_io_available(&self) -> bool {
        false
    }
    fn mmap_available(&self) -> bool {
        false
    }
    fn page_size(&self) -> usize {
        // The supported Windows/MSVC x64 host uses 4 KiB virtual pages.
        4096
    }
    fn mmap_file(&self, _: &File, _: usize) -> io::Result<Arc<dyn MappedFile>> {
        Err(io::ErrorKind::Unsupported.into())
    }
    fn enable_direct_io(&self, _: &File) -> io::Result<()> {
        Err(io::ErrorKind::Unsupported.into())
    }
    fn disable_direct_io(&self, _: &File) -> io::Result<()> {
        Ok(())
    }
    fn direct_io_alignment(&self, _: &File) -> io::Result<DirectAlignment> {
        Err(io::ErrorKind::Unsupported.into())
    }
    fn preallocate(&self, _: &File, _: u64) -> io::Result<Preallocation> {
        Ok(Preallocation::Unsupported)
    }
    fn discover_numa(&self) -> Result<numa::Topology, numa::NumaError> {
        Err(numa::NumaError::Unsupported)
    }
    fn apply_numa(&self, _: &numa::NodeInfo) -> Result<(), numa::NumaError> {
        Err(numa::NumaError::Unsupported)
    }
    fn probe_numa(&self, _: &numa::NodeInfo) -> Result<(), numa::NumaError> {
        Err(numa::NumaError::Unsupported)
    }
    fn probe_numa_memory(&self, _: u32) -> Result<(), numa::NumaError> {
        Err(numa::NumaError::Unsupported)
    }
    fn thread_minor_faults(&self) -> u64 {
        0
    }
    /// The standard close reports nothing here: a failing handle close does
    /// not guarantee the handle was released, so it cannot report a delayed
    /// failure the way a POSIX close does.
    fn close_file(&self, file: File) -> Result<(), CloseError> {
        drop(file);
        Ok(())
    }
}

#[cfg(test)]
mod tests;
