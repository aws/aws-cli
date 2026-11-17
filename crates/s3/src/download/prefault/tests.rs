#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::*;
use crate::download::{
    STRIPE_BYTES,
    service::ThreadSpawner,
    stream_copy::{CopyMode, CopyPath},
    testing::fakes::{self, FakePlatform},
};
use std::{
    sync::{
        atomic::{AtomicUsize, Ordering},
        mpsc,
    },
    time::Duration,
};

const PAGE: usize = 4096;

#[derive(Debug, Default)]
struct Recorded {
    len: usize,
    advised: Mutex<Vec<Range<usize>>>,
}
impl Recorded {
    fn new(len: usize) -> Arc<Self> {
        Arc::new(Self {
            len,
            ..Self::default()
        })
    }
}
impl MappedFile for Recorded {
    fn len(&self) -> usize {
        self.len
    }
    unsafe fn copy_unique(&self, _: usize, _: &[u8], _: CopyMode) -> CopyPath {
        CopyPath::Requested
    }
    fn advise(&self, range: Range<usize>, advice: Advice) -> std::io::Result<()> {
        assert_eq!(advice, Advice::Populate);
        lock(&self.advised).push(range);
        Ok(())
    }
}
fn driven(mapping: Arc<dyn MappedFile>, window_pages: usize) -> Prefaulter {
    let platform = Arc::new(FakePlatform::default());
    let mut state = Accounting::new(mapping.len(), platform.page_size(), 1);
    state.window_bytes = window_pages * PAGE;
    Prefaulter {
        shared: Arc::new(Shared {
            state: Mutex::new(state),
            wake: Condvar::new(),
            mapping,
            locality: LocalityContext::default(),
            platform,
        }),
        threads: Vec::new(),
        pool: None,
    }
}
#[test]
fn mmap_prefaulter_accounting_narrows_windows_and_releases_capacity() {
    let mut state = Accounting::new(16, 4, 1);
    state.window_bytes = 16;
    state.mark_copied_page(0);
    state.mark_copied_page(3);
    assert_eq!(state.pending(0), Some(1..3));
    state.populated(
        1..3,
        Advised {
            trimmed: true,
            ..Advised::default()
        },
    );
    assert_eq!(state.outstanding, 2);
    state.mark_copied_page(1);
    assert_eq!(state.outstanding, 1);
    state.mark_copied_page(1);
    assert_eq!(state.outstanding, 1);
    state.mark_copied_page(2);
    assert_eq!(state.outstanding, 0);
    assert_eq!(state.pending(0), None);
    assert_eq!(state.pending(1), None);
    let skipped = u64::from(diagnostics::ENABLED);
    assert_eq!(state.summary.windows_skipped, skipped);
}
#[test]
fn mmap_prefaulter_claims_only_windows_owned_by_the_shard() {
    let locality = shards(2);
    let mut state = Accounting::new(4 * STRIPE_BYTES as usize, 4096, 2);
    state.window_bytes = STRIPE_BYTES as usize;
    state.outstanding_pages_max = 100;
    for window in 0..4 {
        let offset = window * STRIPE_BYTES;
        assert_eq!(locality.shard_for_offset(offset), window as usize % 2);
    }
    assert_eq!(state.claim(0, &locality), Some(0));
    assert_eq!(state.claim(1, &locality), Some(1));
    assert_eq!(state.claim(0, &locality), Some(2));
    assert_eq!(state.claim(0, &locality), None);
    assert_eq!(state.claim(1, &locality), Some(3));
    assert_eq!(state.claim(1, &locality), None);
    state.next_window_by_shard.fill(0);
    state.outstanding = state.outstanding_pages_max;
    assert_eq!(state.claim(0, &locality), None);
}
#[test]
fn mmap_prefaulter_classifies_clean_and_partial_windows() {
    let mapping = Recorded::new(8 * PAGE);
    let prefaulter = driven(mapping.clone(), 4);
    let shared = &prefaulter.shared;
    lock(&shared.state).outstanding_pages_max = 100;
    let counts = || {
        let summary = lock(&shared.state).summary;
        (
            summary.windows_populated_clean,
            summary.windows_populated_partial,
            summary.populated_bytes,
        )
    };
    let enabled = |counts: (u64, u64, u64)| {
        if diagnostics::ENABLED {
            counts
        } else {
            (0, 0, 0)
        }
    };
    populate(shared, 0, None);
    assert_eq!(counts(), enabled((1, 0, 4 * PAGE as u64)));
    prefaulter.mark_copied_range(5 * PAGE as u64, PAGE);
    assert_eq!(lock(&shared.state).pending(1), Some(4..8));
    populate(shared, 1, None);
    assert_eq!(*lock(&mapping.advised), [0..4 * PAGE, 4 * PAGE..8 * PAGE]);
    assert_eq!(counts(), enabled((1, 1, 8 * PAGE as u64)));
    assert_eq!(lock(&shared.state).outstanding, 7);
    let trimmed = Advised {
        trimmed: true,
        ..Advised::default()
    };
    assert_eq!(lock(&shared.state).populated(6..8, trimmed), 0);
    assert_eq!(counts(), enabled((1, 2, 8 * PAGE as u64)));
}

#[test]
fn a_refused_populate_advice_disables_prefaulting() {
    let platform = Arc::new(FakePlatform::default());
    let mapping = platform.mmap_file(&fakes::file(), 4096).unwrap();
    platform
        .populate_error
        .store(true, std::sync::atomic::Ordering::Relaxed);
    let mut prefaulter = Prefaulter::start_with(
        mapping,
        LocalityContext::default(),
        platform,
        &ThreadSpawner,
    )
    .unwrap();
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while !lock(&prefaulter.shared.state).disabled {
        assert!(std::time::Instant::now() < deadline, "never disabled");
        std::thread::yield_now();
    }
    prefaulter.stop();
    assert_eq!(prefaulter.summary().windows_populated, 0);
    assert_eq!(
        advise_error_name(&std::io::ErrorKind::Unsupported.into()),
        "Operation not supported"
    );
    assert_eq!(
        advise_error_name(&std::io::Error::from_raw_os_error(22)),
        "madvise failed"
    );
}
#[test]
fn mmap_prefaulter_start_and_stop_lifecycle() {
    let platform = Arc::new(FakePlatform::default());
    let mapping = platform.mmap_file(&fakes::file(), 8 * PAGE).unwrap();
    let len = mapping.len();
    let mut prefaulter = Prefaulter::start_with(
        mapping,
        LocalityContext::default(),
        platform,
        &ThreadSpawner,
    )
    .unwrap();
    assert_eq!(prefaulter.thread_count(), PREFAULT_THREADS_PER_SHARD);
    prefaulter.mark_copied_range(0, len);
    assert!((0..8).all(|page| prefaulter.page_completed(page)));
    prefaulter.stop();
    assert!(prefaulter.threads.is_empty());
    assert_eq!(lock(&prefaulter.shared.state).outstanding, 0);
    prefaulter.stop();
}

#[test]
fn a_wait_at_the_lookahead_gate_is_counted() {
    let platform = Arc::new(FakePlatform::default());
    let mut state = Accounting::new(4096, 4096, 1);
    state.outstanding = state.outstanding_pages_max;
    let shared = Arc::new(Shared {
        state: Mutex::new(state),
        wake: Condvar::new(),
        mapping: platform.mmap_file(&fakes::file(), 4096).unwrap(),
        locality: LocalityContext::default(),
        platform,
    });
    let waiter = {
        let shared = Arc::clone(&shared);
        std::thread::spawn(move || claim_wait(&shared, 0))
    };
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while diagnostics::ENABLED && lock(&shared.state).summary.gate_wait_count == 0 {
        assert!(std::time::Instant::now() < deadline, "never waited");
        shared.wake.notify_all();
        std::thread::yield_now();
    }
    lock(&shared.state).closed = true;
    shared.wake.notify_all();
    assert_eq!(waiter.join().unwrap(), None);
    let waits = lock(&shared.state).summary.gate_wait_count;
    if diagnostics::ENABLED {
        assert!(waits >= 2, "{waits}");
    } else {
        assert_eq!(waits, 0);
    }
}

#[test]
fn marking_a_copied_range_completes_every_page_it_touches() {
    let prefaulter = driven(Recorded::new(12_000), 3);
    let state = || lock(&prefaulter.shared.state);
    state().populated(0..3, Advised::default());
    for (offset, len) in [(0, 0), (8_192, 4_000), (12_000, 1), (u64::MAX, 2)] {
        prefaulter.mark_copied_range(offset, len);
    }
    assert_eq!(state().outstanding, 3);
    assert_eq!(state().pending(0), Some(0..3));
    let completed = || (0..3).map(|page| prefaulter.page_completed(page));
    prefaulter.mark_copied_range(0, 6_000);
    assert!(completed().eq([true, true, false]));
    assert_eq!(state().outstanding, 1);
    assert_eq!(state().pending(0), Some(2..3));
    prefaulter.mark_copied_range(6_000, 6_000);
    assert!(completed().all(|completed| completed));
    assert_eq!(state().outstanding, 0);
    assert_eq!(state().pending(0), None);
}

#[test]
fn a_copy_that_releases_nothing_wakes_no_gate_waiter() {
    let prefaulter = driven(Recorded::new(4 * PAGE), 2);
    {
        let mut state = lock(&prefaulter.shared.state);
        state.populated(0..1, Advised::default());
        state.outstanding_pages_max = 1;
    }
    let waiter = {
        let shared = Arc::clone(&prefaulter.shared);
        std::thread::spawn(move || claim_wait(&shared, 0))
    };
    std::thread::sleep(Duration::from_millis(100));
    prefaulter.mark_copied_range(2 * PAGE as u64, PAGE);
    std::thread::sleep(Duration::from_millis(100));
    prefaulter.mark_copied_range(0, PAGE);
    assert_eq!(waiter.join().unwrap(), Some(0));
    let waits = lock(&prefaulter.shared.state).summary.gate_wait_count;
    if diagnostics::ENABLED {
        assert!(waits <= 1, "{waits}");
    } else {
        assert_eq!(waits, 0);
    }
}

#[test]
fn an_exhausted_shard_stops_before_the_lookahead_gate() {
    let prefaulter = driven(Recorded::new(PAGE), 1);
    let shared = &prefaulter.shared;
    {
        let mut state = lock(&shared.state);
        assert_eq!(state.claim(0, &shared.locality), Some(0));
        state.outstanding = state.outstanding_pages_max;
    }
    let (done, finished) = mpsc::channel();
    let waiter = {
        let shared = Arc::clone(shared);
        std::thread::spawn(move || {
            let claimed = claim_wait(&shared, 0);
            let _ = done.send(());
            claimed
        })
    };
    let stopped = finished.recv_timeout(Duration::from_secs(5)).is_ok();
    lock(&shared.state).closed = true;
    shared.wake.notify_all();
    assert_eq!(waiter.join().unwrap(), None);
    assert!(stopped, "the exhausted worker waited at the gate");
    assert_eq!(lock(&shared.state).summary.gate_wait_count, 0);
}

#[derive(Debug, Default)]
struct RefusingSpawner {
    refuse: Option<usize>,
    spawns: AtomicUsize,
    placed: Placements,
}
type Placements = Arc<Mutex<Vec<(usize, Option<u32>)>>>;
impl RefusingSpawner {
    fn refusing(index: usize) -> Self {
        Self {
            refuse: Some(index),
            ..Self::default()
        }
    }
    fn placed(&self) -> Vec<Option<u32>> {
        let mut placed = lock(&self.placed).clone();
        placed.sort_unstable();
        placed.into_iter().map(|(_, node)| node).collect()
    }
}
impl WorkerSpawner for RefusingSpawner {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> std::io::Result<JoinHandle<()>> {
        let index = self.spawns.fetch_add(1, Ordering::SeqCst);
        if self.refuse == Some(index) {
            return Err(std::io::ErrorKind::WouldBlock.into());
        }
        let placed = Arc::clone(&self.placed);
        ThreadSpawner.spawn(
            name,
            Box::new(move || {
                worker();
                lock(&placed).push((index, fakes::placed_node()));
            }),
        )
    }
}
fn shards(count: u32) -> LocalityContext {
    LocalityContext {
        nodes: (0..count)
            .map(|id| numa::NodeInfo::new(id, numa::CpuSet::default(), ""))
            .collect(),
    }
}
fn start_private(
    locality: LocalityContext,
    spawner: &RefusingSpawner,
) -> std::io::Result<Prefaulter> {
    let platform = Arc::new(FakePlatform::default());
    let mapping = platform.mmap_file(&fakes::file(), 8 * PAGE).unwrap();
    Prefaulter::start_with(mapping, locality, platform, spawner)
}

#[test]
fn private_prefault_workers_interleave_the_shards() {
    let spawner = RefusingSpawner::default();
    let mut prefaulter = start_private(shards(2), &spawner).unwrap();
    assert_eq!(prefaulter.thread_count(), 2 * PREFAULT_THREADS_PER_SHARD);
    prefaulter.stop();
    assert_eq!(spawner.placed(), [Some(0), Some(1), Some(0), Some(1)]);
}
#[test]
fn a_later_refused_private_spawn_keeps_the_started_workers() {
    let spawner = RefusingSpawner::refusing(1);
    let mut prefaulter = start_private(LocalityContext::default(), &spawner).unwrap();
    assert_eq!(prefaulter.thread_count(), 1);
    prefaulter.stop();
    assert_eq!(spawner.spawns.load(Ordering::SeqCst), 2);

    let spawner = RefusingSpawner::refusing(2);
    let mut prefaulter = start_private(shards(2), &spawner).unwrap();
    assert_eq!(prefaulter.thread_count(), 2);
    prefaulter.stop();
    assert_eq!(spawner.spawns.load(Ordering::SeqCst), 3);
    assert_eq!(spawner.placed(), [Some(0), Some(1)]);
}
#[test]
fn a_refused_first_private_spawn_fails_the_start() {
    let spawner = RefusingSpawner::refusing(0);
    let error = start_private(shards(2), &spawner).unwrap_err();
    assert_eq!(error.kind(), std::io::ErrorKind::WouldBlock);
    assert_eq!(spawner.spawns.load(Ordering::SeqCst), 1);
    assert!(spawner.placed().is_empty());
}
#[test]
fn a_refused_private_spawn_logs_its_index_and_error() {
    assert_eq!(
        diagnostics::prefault_spawn_failed_line(1, &std::io::ErrorKind::WouldBlock.into()),
        "mmap prefault thread spawn failed index=1 err=Insufficient system resources"
    );
}
