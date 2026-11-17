use super::*;
use crate::download::platform::{DirectAlignment, MappedFile, PositionalWriter, Preallocation};
use std::{
    fs::{File, OpenOptions},
    io,
    sync::{
        Weak,
        atomic::{AtomicUsize, Ordering},
    },
};

#[derive(Debug)]
pub(super) struct ActorPlatform(pub(super) Weak<Round>);
impl PositionalWriter for ActorPlatform {
    fn write_at(&self, file: &File, bytes: &[u8], offset: u64) -> io::Result<usize> {
        let round = self.0.upgrade().unwrap();
        let index = lock(&round.ledger).files[&file_key(file)];
        round.writing[index].open();
        round.allowed[index].wait();
        let mut ledger = lock(&round.ledger);
        let entry = &mut ledger.entries[index];
        assert_eq!(offset, 0);
        assert_eq!(entry.releases, 0);
        assert_eq!(bytes, entry.expected);
        entry.writes += 1;
        if index == 0 && round.choices.terminal == Terminal::WriteFailure {
            return Err(io::ErrorKind::StorageFull.into());
        }
        entry.image.copy_from_slice(bytes);
        Ok(bytes.len())
    }
}
impl Platform for ActorPlatform {
    fn direct_io_available(&self) -> bool {
        false
    }
    fn mmap_available(&self) -> bool {
        false
    }
    fn page_size(&self) -> usize {
        4096
    }
    fn mmap_file(&self, _: &File, _: usize) -> io::Result<Arc<dyn MappedFile>> {
        Err(io::ErrorKind::Unsupported.into())
    }
    fn enable_direct_io(&self, _: &File) -> io::Result<()> {
        Err(io::ErrorKind::Unsupported.into())
    }
    fn disable_direct_io(&self, _: &File) -> io::Result<()> {
        Err(io::ErrorKind::Unsupported.into())
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
        Ok(())
    }
    fn probe_numa(&self, _: &numa::NodeInfo) -> Result<(), numa::NumaError> {
        Ok(())
    }
    fn probe_numa_memory(&self, _: u32) -> Result<(), numa::NumaError> {
        Err(numa::NumaError::Unsupported)
    }
    fn thread_minor_faults(&self) -> u64 {
        0
    }
    fn set_length(&self, _: &File, _: u64) -> io::Result<()> {
        Ok(())
    }
    fn close_file(&self, file: File) -> Result<(), crate::download::CloseError> {
        drop(file);
        Ok(())
    }
}

#[cfg(unix)]
pub(super) fn file_key(file: &File) -> usize {
    use std::os::fd::AsRawFd;
    file.as_raw_fd() as usize
}
#[cfg(windows)]
pub(super) fn file_key(file: &File) -> usize {
    use std::os::windows::io::AsRawHandle;
    file.as_raw_handle() as usize
}
pub(super) fn output_file() -> File {
    static NEXT: AtomicUsize = AtomicUsize::new(0);
    let path = std::env::temp_dir().join(format!(
        "rust-shared-actor-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    let file = OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .open(&path)
        .unwrap();
    std::fs::remove_file(path).unwrap();
    file
}
