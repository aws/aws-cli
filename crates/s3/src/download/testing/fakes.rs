#![expect(clippy::unwrap_used, reason = "bounded test model invariants")]
use super::super::{platform::*, *};
use std::{
    collections::VecDeque,
    fs::{File, OpenOptions},
    io,
    ops::Range,
    sync::{
        Arc, Mutex,
        atomic::{AtomicBool, AtomicUsize, Ordering},
    },
};

#[derive(Clone, Copy, Debug)]
pub(crate) enum Fault {
    Interrupted,
    Zero,
    Short(usize),
    Rejected,
    Failed,
    #[cfg_attr(
        any(not(unix), not(test)),
        expect(dead_code, reason = "only the POSIX errno tests inject one")
    )]
    Errno(i32),
}
#[derive(Debug, Default)]
pub(crate) struct FakePlatform {
    pub(crate) disk: Mutex<Vec<u8>>,
    pub(crate) faults: Mutex<VecDeque<Fault>>,
    pub(crate) write_hold: Mutex<Option<Arc<std::sync::Barrier>>>,
    pub(crate) preallocation: Mutex<VecDeque<io::ErrorKind>>,
    pub(crate) preallocations: AtomicUsize,
    pub(crate) unsupported_preallocation: AtomicBool,
    pub(crate) map_unavailable: AtomicBool,
    /// Whether mapping the file fails, on a host that offers mappings.
    pub(crate) map_error: AtomicBool,
    pub(crate) direct_unavailable: AtomicBool,
    pub(crate) direct_refused: AtomicBool,
    pub(crate) direct_enables: AtomicUsize,
    pub(crate) direct_disables: AtomicUsize,
    pub(crate) disable_error: AtomicBool,
    pub(crate) huge_pages_error: Arc<AtomicBool>,
    pub(crate) evict_error: Arc<AtomicBool>,
    pub(crate) populate_error: Arc<AtomicBool>,
    pub(crate) advice: Arc<Mutex<Vec<Advice>>>,
    pub(crate) mapping: Mutex<Option<Arc<FakeMapping>>>,
    pub(crate) direct_enabled: AtomicBool,
    pub(crate) bounce_failure: AtomicBool,
    pub(crate) alignment: Mutex<Option<DirectAlignment>>,
    /// Whether the direct-I/O alignment query fails.
    pub(crate) alignment_error: AtomicBool,
    pub(crate) bounce_sizes: Mutex<Vec<usize>>,
    pub(crate) bounce_alignments: Mutex<Vec<usize>>,
    pub(crate) write_sizes: Mutex<Vec<usize>>,
    pub(crate) write_offsets: Mutex<Vec<u64>>,
    pub(crate) topology: Mutex<Option<numa::Topology>>,
    pub(crate) discoveries: AtomicUsize,
    pub(crate) thread_probes: AtomicUsize,
    pub(crate) bind_fails: AtomicBool,
    pub(crate) bound_nodes: Mutex<Vec<u32>>,
    pub(crate) placement_failure: Mutex<Option<u32>>,
    pub(crate) close_failure: Mutex<Option<CloseError>>,
    pub(crate) closes: AtomicUsize,
    pub(crate) closes_while_mapped: AtomicUsize,
    pub(crate) set_length_failure: Mutex<Option<i32>>,
    pub(crate) set_lengths: AtomicUsize,
}
std::thread_local! {
    static PLACED_NODE: std::cell::Cell<Option<u32>> = const { std::cell::Cell::new(None) };
}
#[cfg(test)]
pub(crate) fn placed_node() -> Option<u32> {
    PLACED_NODE.with(std::cell::Cell::get)
}
impl PositionalWriter for FakePlatform {
    fn allocate_bounce(&self, size: usize, alignment: usize) -> io::Result<AlignedBuffer> {
        lock(&self.bounce_sizes).push(size);
        lock(&self.bounce_alignments).push(alignment);
        if self.bounce_failure.load(Ordering::Relaxed) {
            Err(io::ErrorKind::OutOfMemory.into())
        } else {
            AlignedBuffer::new(size, alignment)
        }
    }
    fn write_at(&self, _: &File, bytes: &[u8], offset: u64) -> io::Result<usize> {
        lock(&self.write_sizes).push(bytes.len());
        lock(&self.write_offsets).push(offset);
        let hold = lock(&self.write_hold).take();
        if let Some(hold) = hold {
            hold.wait();
            hold.wait();
        }
        let length = match lock(&self.faults).pop_front() {
            Some(Fault::Interrupted) => return Err(io::ErrorKind::Interrupted.into()),
            Some(Fault::Zero) => return Ok(0),
            Some(Fault::Failed) => return Err(io::ErrorKind::StorageFull.into()),
            Some(Fault::Errno(code)) => return Err(io::Error::from_raw_os_error(code)),
            Some(Fault::Rejected) => return Ok(bytes.len() + 1),
            Some(Fault::Short(len)) => len.min(bytes.len()),
            None => bytes.len(),
        };
        let offset = usize::try_from(offset).map_err(|_| io::ErrorKind::InvalidInput)?;
        let mut disk = lock(&self.disk);
        let end = disk.len().max(offset + length);
        disk.resize(end, 0);
        disk[offset..offset + length].copy_from_slice(&bytes[..length]);
        Ok(length)
    }
}
impl Platform for FakePlatform {
    fn direct_io_available(&self) -> bool {
        !self.direct_unavailable.load(Ordering::Relaxed)
    }
    fn mmap_available(&self) -> bool {
        !self.map_unavailable.load(Ordering::Relaxed)
    }
    fn page_size(&self) -> usize {
        4096
    }
    fn mmap_file(&self, _: &File, size: usize) -> io::Result<Arc<dyn MappedFile>> {
        if self.map_error.load(Ordering::Relaxed) {
            return Err(io::ErrorKind::OutOfMemory.into());
        }
        let map = Arc::new(FakeMapping {
            bytes: Mutex::new(vec![0; size]),
            advice: Arc::clone(&self.advice),
            evict_error: Arc::clone(&self.evict_error),
            populate_error: Arc::clone(&self.populate_error),
            huge_pages_error: Arc::clone(&self.huge_pages_error),
        });
        *lock(&self.mapping) = Some(Arc::clone(&map));
        Ok(map)
    }
    fn enable_direct_io(&self, _: &File) -> io::Result<()> {
        if self.direct_unavailable.load(Ordering::Relaxed) {
            return Err(io::ErrorKind::Unsupported.into());
        }
        if self.direct_refused.load(Ordering::Relaxed) {
            return Err(io::Error::from_raw_os_error(libc::EINVAL));
        }
        self.direct_enables.fetch_add(1, Ordering::Relaxed);
        self.direct_enabled.store(true, Ordering::Relaxed);
        Ok(())
    }
    fn disable_direct_io(&self, _: &File) -> io::Result<()> {
        if self.disable_error.load(Ordering::Relaxed) {
            return Err(io::ErrorKind::PermissionDenied.into());
        }
        self.direct_disables.fetch_add(1, Ordering::Relaxed);
        self.direct_enabled.store(false, Ordering::Relaxed);
        Ok(())
    }
    fn direct_io_alignment(&self, _: &File) -> io::Result<DirectAlignment> {
        if self.alignment_error.load(Ordering::Relaxed) {
            return Err(io::ErrorKind::InvalidInput.into());
        }
        Ok(lock(&self.alignment).unwrap_or(DirectAlignment {
            memory: 16,
            offset: 16,
        }))
    }
    fn preallocate(&self, _: &File, _: u64) -> io::Result<Preallocation> {
        self.preallocations.fetch_add(1, Ordering::Relaxed);
        if let Some(error) = lock(&self.preallocation).pop_front() {
            return Err(error.into());
        }
        if self.unsupported_preallocation.load(Ordering::Relaxed) {
            Ok(Preallocation::Unsupported)
        } else {
            Ok(Preallocation::Confirmed)
        }
    }
    fn discover_numa(&self) -> Result<numa::Topology, numa::NumaError> {
        self.discoveries.fetch_add(1, Ordering::Relaxed);
        lock(&self.topology)
            .clone()
            .ok_or(numa::NumaError::Unsupported)
    }
    fn apply_numa(&self, node: &numa::NodeInfo) -> Result<(), numa::NumaError> {
        if *lock(&self.placement_failure) == Some(node.id) {
            return Err(numa::NumaError::ThreadPlacementMismatch);
        }
        PLACED_NODE.with(|placed| placed.set(Some(node.id)));
        Ok(())
    }
    fn probe_numa(&self, _: &numa::NodeInfo) -> Result<(), numa::NumaError> {
        self.thread_probes.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }
    fn probe_numa_memory(&self, node: u32) -> Result<(), numa::NumaError> {
        if self.bind_fails.load(Ordering::Relaxed) {
            return Err(numa::NumaError::Io(io::Error::from_raw_os_error(1)));
        }
        lock(&self.bound_nodes).push(node);
        Ok(())
    }
    fn thread_minor_faults(&self) -> u64 {
        0
    }
    fn set_length(&self, _: &File, size: u64) -> io::Result<()> {
        self.set_lengths.fetch_add(1, Ordering::Relaxed);
        if let Some(code) = *lock(&self.set_length_failure) {
            return Err(io::Error::from_raw_os_error(code));
        }
        lock(&self.disk).resize(size as usize, 0);
        Ok(())
    }
    fn close_file(&self, file: File) -> Result<(), CloseError> {
        if lock(&self.mapping)
            .as_ref()
            .is_some_and(|mapping| Arc::strong_count(mapping) > 1)
        {
            self.closes_while_mapped.fetch_add(1, Ordering::Relaxed);
        }
        drop(file);
        self.closes.fetch_add(1, Ordering::Relaxed);
        lock(&self.close_failure).map_or(Ok(()), Err)
    }
}
#[derive(Debug)]
pub(crate) struct FakeMapping {
    pub(crate) bytes: Mutex<Vec<u8>>,
    pub(crate) advice: Arc<Mutex<Vec<Advice>>>,
    evict_error: Arc<AtomicBool>,
    populate_error: Arc<AtomicBool>,
    huge_pages_error: Arc<AtomicBool>,
}
impl MappedFile for FakeMapping {
    fn len(&self) -> usize {
        lock(&self.bytes).len()
    }
    unsafe fn copy_unique(
        &self,
        offset: usize,
        bytes: &[u8],
        mode: CopyMode,
    ) -> stream_copy::CopyPath {
        stream_copy::copy(
            mode,
            &mut lock(&self.bytes)[offset..offset + bytes.len()],
            bytes,
        )
    }
    fn advise(&self, _: Range<usize>, advice: Advice) -> io::Result<()> {
        lock(&self.advice).push(advice);
        let error = match advice {
            Advice::Evict => &self.evict_error,
            Advice::Populate => &self.populate_error,
            Advice::HugePages => &self.huge_pages_error,
        };
        if error.load(Ordering::Relaxed) {
            Err(io::ErrorKind::Unsupported.into())
        } else {
            Ok(())
        }
    }
}
pub(crate) fn file() -> File {
    static NEXT: AtomicUsize = AtomicUsize::new(0);
    let path = std::env::temp_dir().join(format!(
        "rust-writer-{}-{}",
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
pub(crate) fn config(mode: WriterMode) -> WriterConfig {
    WriterConfig {
        mode,
        requirement: Requirement::Required,
        workers: Some(2),
        prefault: PrefaultMode::Disabled,
        numa: NumaConfig {
            mode: NumaMode::Disabled,
            ..NumaConfig::default()
        },
        ..WriterConfig::default()
    }
}
