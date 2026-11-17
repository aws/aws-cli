#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::{super::*, *};
use crate::download::{
    STRIPE_BYTES,
    service::WorkerSpawner,
    stream_copy::{CopyMode, CopyPath},
    testing::fakes::{self, FakePlatform},
};
use std::{
    sync::atomic::AtomicBool,
    time::{Duration, Instant},
};

const PAGE: usize = 4096;

#[derive(Debug, Default)]
struct Controlled {
    len: usize,
    fail: bool,
    held: Mutex<bool>,
    released: Condvar,
    advised: Mutex<Vec<(Range<usize>, Option<u32>)>>,
}
impl Controlled {
    fn new(len: usize) -> Arc<Self> {
        Arc::new(Self {
            len,
            ..Self::default()
        })
    }
    fn release(&self) {
        *lock(&self.held) = false;
        self.released.notify_all();
    }
    fn advised(&self) -> Vec<(Range<usize>, Option<u32>)> {
        lock(&self.advised).clone()
    }
}
impl MappedFile for Controlled {
    fn len(&self) -> usize {
        self.len
    }
    unsafe fn copy_unique(&self, _: usize, _: &[u8], _: CopyMode) -> CopyPath {
        CopyPath::Requested
    }
    fn advise(&self, range: Range<usize>, advice: Advice) -> std::io::Result<()> {
        assert_eq!(advice, Advice::Populate);
        lock(&self.advised).push((range, fakes::placed_node()));
        let mut held = lock(&self.held);
        while *held {
            held = wait(&self.released, held);
        }
        if self.fail {
            return Err(std::io::ErrorKind::Unsupported.into());
        }
        Ok(())
    }
}
#[derive(Debug, Default)]
struct Counting {
    fail_after: Option<usize>,
    starts: AtomicUsize,
    joins: Arc<AtomicUsize>,
}
impl WorkerSpawner for Counting {
    fn spawn(
        &self,
        name: String,
        run: Box<dyn FnOnce() + Send>,
    ) -> std::io::Result<JoinHandle<()>> {
        if self.fail_after == Some(self.starts.load(Ordering::SeqCst)) {
            return Err(std::io::ErrorKind::WouldBlock.into());
        }
        let joins = Arc::clone(&self.joins);
        let handle = std::thread::Builder::new().name(name).spawn(move || {
            run();
            joins.fetch_add(1, Ordering::SeqCst);
        })?;
        self.starts.fetch_add(1, Ordering::SeqCst);
        Ok(handle)
    }
}
fn eventually(condition: impl Fn() -> bool) {
    let deadline = Instant::now() + Duration::from_secs(10);
    while !condition() {
        assert!(Instant::now() < deadline, "never observed");
        std::thread::yield_now();
    }
}
fn idle(pool: &Pool) {
    eventually(|| lock(&pool.state).reserved == 0);
}
fn outstanding(pool: &Pool) -> usize {
    pool.outstanding.load(Ordering::Acquire)
}
fn two_shards() -> LocalityContext {
    struct Reader;
    impl numa::NodeReader for Reader {
        fn read(&self, _: u32) -> Result<String, numa::NumaError> {
            Ok("0".into())
        }
    }
    let mut cpus = numa::CpuSet::default();
    cpus.set(0).unwrap();
    let nodes = numa::parse_node_mask("0-1").unwrap();
    LocalityContext {
        nodes: numa::discover_from_node_reader(&nodes, &cpus, &Reader)
            .unwrap()
            .nodes,
    }
}
fn start(locality: &LocalityContext, spawner: &Counting) -> Result<PrefaultPool, WriteError> {
    PrefaultPool::start(locality, Arc::new(FakePlatform::default()), spawner)
}

#[test]
fn command_pool_reuses_workers_across_completed_mappings() {
    let spawner = Counting::default();
    let pool = start(&LocalityContext::default(), &spawner).unwrap();
    let platform = FakePlatform::default();
    for _ in 0..24 {
        let mapping = Controlled::new(PAGE);
        let mut prefaulter = Prefaulter::attach(mapping.clone(), pool.pool().clone(), &platform);
        eventually(|| mapping.advised().len() == 1);
        idle(pool.pool());
        assert_eq!(pool.pool().scheduled(), (0, 1));
        assert_eq!(outstanding(pool.pool()), PAGE);
        prefaulter.mark_copied_range(0, PAGE);
        prefaulter.stop();
    }
    assert_eq!(
        spawner.starts.load(Ordering::SeqCst),
        PREFAULT_THREADS_PER_SHARD
    );
    assert_eq!(outstanding(pool.pool()), 0);
    assert_eq!(pool.pool().scheduled(), (0, 0));
}

#[test]
fn detach_waits_for_active_advice_and_cancels_unclaimed_windows() {
    let pool = start(&LocalityContext::default(), &Counting::default()).unwrap();
    lock(&pool.pool().state).lookahead = PAGE;
    let platform = FakePlatform::default();
    let active = Controlled::new(PAGE);
    *lock(&active.held) = true;
    let mut running = Prefaulter::attach(active.clone(), pool.pool().clone(), &platform);
    eventually(|| active.advised().len() == 1);
    let queued = Controlled::new(PAGE);
    let mut waiting = Prefaulter::attach(queued.clone(), pool.pool().clone(), &platform);
    waiting.stop();
    assert_eq!(lock(&waiting.shared.state).next_window_by_shard[0], 0);
    assert!(queued.advised().is_empty());

    let state = Arc::clone(&running.shared);
    let stopped = Arc::new(AtomicBool::new(false));
    let stopper = {
        let stopped = Arc::clone(&stopped);
        std::thread::spawn(move || {
            running.stop();
            stopped.store(true, Ordering::SeqCst);
        })
    };
    eventually(|| !lock(&state.state).link.registered);
    let stopped_early = stopped.load(Ordering::SeqCst);
    let active_jobs = lock(&state.state).link.active;
    active.release();
    stopper.join().unwrap();
    assert!(!stopped_early);
    assert_eq!(active_jobs, 1);
    assert!(stopped.load(Ordering::SeqCst));
    assert_eq!(outstanding(pool.pool()), 0);
}

#[test]
fn one_mapping_advice_failure_leaves_reusable_workers_available() {
    let pool = start(&LocalityContext::default(), &Counting::default()).unwrap();
    let platform = FakePlatform::default();
    let failing = Arc::new(Controlled {
        len: PAGE,
        fail: true,
        ..Controlled::default()
    });
    let failed = Prefaulter::attach(failing.clone(), pool.pool().clone(), &platform);
    eventually(|| failing.advised().len() == 1);
    idle(pool.pool());
    assert!(lock(&failed.shared.state).disabled);
    let mapping = Controlled::new(PAGE);
    let healthy = Prefaulter::attach(mapping.clone(), pool.pool().clone(), &platform);
    eventually(|| mapping.advised().len() == 1);
    idle(pool.pool());
    assert!(!lock(&healthy.shared.state).disabled);
    assert_eq!(lock(&healthy.shared.state).outstanding, 1);
    healthy.mark_copied_range(0, PAGE);
}

#[test]
fn failed_pool_spawn_joins_the_already_started_worker() {
    let spawner = Counting {
        fail_after: Some(1),
        ..Counting::default()
    };
    let error = start(&LocalityContext::default(), &spawner).unwrap_err();
    assert!(matches!(
        error,
        WriteError::Io {
            kind: std::io::ErrorKind::WouldBlock,
            ..
        }
    ));
    assert_eq!(
        crate::download::diagnostics::shared_prefault_unavailable_line(&error),
        "shared mmap prefault unavailable err=Insufficient system resources"
    );
    assert_eq!(spawner.starts.load(Ordering::SeqCst), 1);
    assert_eq!(spawner.joins.load(Ordering::SeqCst), 1);
}

#[test]
fn failed_pool_placement_joins_every_successful_spawn() {
    let spawner = Counting::default();
    let platform = FakePlatform::default();
    *lock(&platform.placement_failure) = Some(1);
    assert!(matches!(
        PrefaultPool::start(&two_shards(), Arc::new(platform), &spawner),
        Err(WriteError::Numa(_))
    ));
    let started = spawner.starts.load(Ordering::SeqCst);
    assert_eq!(started, 2 * PREFAULT_THREADS_PER_SHARD);
    assert_eq!(spawner.joins.load(Ordering::SeqCst), started);
}

#[test]
fn multiple_shards_drain_every_window_and_recycle_global_credit() {
    let window = STRIPE_BYTES as usize;
    let pool = PrefaultPool::start(
        &two_shards(),
        Arc::new(FakePlatform::default()),
        &Counting::default(),
    )
    .unwrap();
    lock(&pool.pool().state).lookahead = 0;
    let platform = FakePlatform::default();
    let mappings = [Controlled::new(3 * window), Controlled::new(2 * window)];
    let prefaulters = mappings.each_ref().map(|mapping| {
        Prefaulter::attach_windows(mapping.clone(), pool.pool().clone(), &platform, window)
    });
    lock(&pool.pool().state).lookahead = window;
    pool.pool().wake();
    let mut seen = Vec::new();
    for advised in 1..=5 {
        eventually(|| mappings.iter().map(|m| m.advised().len()).sum::<usize>() == advised);
        idle(pool.pool());
        assert_eq!(outstanding(pool.pool()), window);
        let all: Vec<_> = mappings
            .iter()
            .enumerate()
            .flat_map(|(index, mapping)| mapping.advised().into_iter().map(move |a| (index, a)))
            .collect();
        let (index, (range, node)) = all
            .into_iter()
            .find(|(index, (range, _))| !seen.contains(&(*index, range.start)))
            .unwrap();
        seen.push((index, range.start));
        let number = range.start / window;
        assert_eq!(range.len(), window);
        assert_eq!(node, Some((number % 2) as u32));
        prefaulters[index].mark_copied_range((number * window) as u64, window);
    }
    for mapping in &mappings {
        let mut windows: Vec<_> = mapping
            .advised()
            .iter()
            .map(|(r, _)| r.start / window)
            .collect();
        windows.sort_unstable();
        assert_eq!(windows, (0..mapping.len / window).collect::<Vec<_>>());
    }
    assert_eq!(pool.pool().scheduled(), (0, 2));
    assert_eq!(outstanding(pool.pool()), 0);
}
