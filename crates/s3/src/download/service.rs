use super::{
    diagnostics::{self, ObjectPhases},
    output::{Output, Policy},
    platform::{NativePlatform, Platform},
    prefault::{PrefaultPool, PrefaultSource},
    *,
};
use std::{
    collections::VecDeque,
    fs::{File, OpenOptions},
    path::Path,
    sync::{
        Arc, Condvar, Mutex,
        atomic::{AtomicU64, AtomicUsize, Ordering},
    },
    thread::{self, JoinHandle},
    time::Instant,
};

/// The smallest object that takes a native writer on its own size: eight
/// nominal chunks amortize the writer's setup.
pub const CUSTOM_WRITER_SIZE_MIN: u64 = 64 * 1024 * 1024;
/// The most writers a command starts on its own; fewer CPUs lower it, and
/// more locality shards raise it.
pub const WORKER_COUNT_MAX: usize = 8;
const SOURCE_POOLS_MAX: u64 = 2;

/// The jobs each shard's queue holds: every buffer the command's source pools
/// can lend at once. A queued job holds its part's buffer ticket, so the
/// queues never hold more jobs than the pools have lent buffers. Within a
/// pool of `pool_bytes`, every reservation is at least a part of `part_size`
/// bytes except the short final part of a GET, and each object in the
/// `window` has one GET at a time, so at most one short part.
pub fn queue_jobs_per_shard(pool_bytes: u64, part_size: u64, window: u32) -> usize {
    assert!(pool_bytes > 0);
    assert!(part_size > 0);
    assert!(window > 0);
    let jobs = pool_bytes
        .div_ceil(part_size)
        .saturating_mul(SOURCE_POOLS_MAX)
        .saturating_add(u64::from(window));
    usize::try_from(jobs).unwrap_or(usize::MAX)
}

#[derive(Clone, Debug)]
pub struct SharedConfig {
    pub writer: WriterConfig,
    /// Whether every object takes a native writer: an explicit download
    /// setting asks for one, and a command of one object always gives its
    /// object one. Otherwise only an object of at least
    /// `CUSTOM_WRITER_SIZE_MIN` bytes does.
    pub custom_writer_required: bool,
    /// The engine's transfer window, one for a command of one object: the
    /// most outputs admitted at once.
    pub in_flight_max: usize,
    /// The jobs each shard's queue holds; see `queue_jobs_per_shard`.
    pub queue_jobs_per_shard: usize,
}
impl SharedConfig {
    /// Whether an object of `size` bytes takes a native writer: every object
    /// when a setting or the command's one-object shape requires one, else
    /// only one of at least `CUSTOM_WRITER_SIZE_MIN` bytes. A `crt` writer
    /// sends every object to `recv_filepath`, ahead of that requirement.
    pub fn should_use_custom_writer(&self, size: u64) -> bool {
        self.writer.mode != WriterMode::Crt
            && (self.custom_writer_required || size >= CUSTOM_WRITER_SIZE_MIN)
    }
}
impl Default for SharedConfig {
    fn default() -> Self {
        Self {
            writer: WriterConfig::default(),
            custom_writer_required: false,
            in_flight_max: 64,
            queue_jobs_per_shard: 64,
        }
    }
}
/// The command-wide writer count: the override, else up to `WORKER_COUNT_MAX`
/// writers bounded by the CPUs the thread's affinity allows, and never fewer
/// than one per locality shard.
pub fn shared_worker_count(workers: Option<usize>, shards: usize) -> usize {
    shared_worker_count_with_cpus(workers, shards, numa::cpu_count())
}
fn shared_worker_count_with_cpus(workers: Option<usize>, shards: usize, cpus: usize) -> usize {
    shards
        .max(1)
        .max(workers.unwrap_or_else(|| WORKER_COUNT_MAX.min(cpus)))
}
/// Spawns workers after their heap-stable state is built; failures are injectable.
pub trait WorkerSpawner: std::fmt::Debug + Send + Sync {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> std::io::Result<JoinHandle<()>>;
}
#[derive(Debug)]
pub(crate) struct ThreadSpawner;
impl WorkerSpawner for ThreadSpawner {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> std::io::Result<JoinHandle<()>> {
        cli_core::thread::builder().name(name).spawn(worker)
    }
}
#[derive(Debug, Default)]
struct ProducerGuard(Option<thread::ThreadId>);
impl ProducerGuard {
    fn check(&mut self) -> Result<(), WriteError> {
        let current = thread::current().id();
        if self.0.is_some_and(|owner| owner != current) {
            return Err(WriteError::MultipleProducers);
        }
        self.0 = Some(current);
        Ok(())
    }
}
#[derive(Debug)]
struct Job {
    body: Body,
    prepared: Arc<Prepared>,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct FullWaits {
    count: u64,
    ns: u64,
    ns_max: u64,
}
impl FullWaits {
    fn add(&mut self, other: Self) {
        self.count = self.count.saturating_add(other.count);
        self.ns = self.ns.saturating_add(other.ns);
        self.ns_max = self.ns_max.max(other.ns_max);
    }
}
#[derive(Debug)]
struct ShardState {
    jobs: VecDeque<Job>,
    closed: bool,
    full_waits: FullWaits,
}
#[derive(Debug)]
struct ShardQueue {
    state: Mutex<ShardState>,
    not_full: Condvar,
}
impl ShardQueue {
    fn new(capacity: usize) -> Result<Self, WriteError> {
        let mut jobs = VecDeque::new();
        jobs.try_reserve_exact(capacity)
            .map_err(|_| WriteError::from(std::io::Error::from(std::io::ErrorKind::OutOfMemory)))?;
        Ok(Self {
            state: Mutex::new(ShardState {
                jobs,
                closed: false,
                full_waits: FullWaits::default(),
            }),
            not_full: Condvar::new(),
        })
    }
    fn push(&self, capacity: usize, job: Job) -> Result<(), Job> {
        let mut state = lock(&self.state);
        let mut waited = None;
        while !state.closed && state.jobs.len() >= capacity {
            if waited.is_none() {
                state.full_waits.count += 1;
                waited = Some(diagnostics::start());
            }
            state = wait(&self.not_full, state);
        }
        if let Some(start) = waited {
            let ns = diagnostics::elapsed_ns(start);
            state.full_waits.ns = state.full_waits.ns.saturating_add(ns);
            state.full_waits.ns_max = state.full_waits.ns_max.max(ns);
        }
        if state.closed {
            return Err(job);
        }
        state.jobs.push_back(job);
        Ok(())
    }
    fn pop(&self) -> Option<Job> {
        let job = lock(&self.state).jobs.pop_front()?;
        self.not_full.notify_one();
        Some(job)
    }
    fn close(&self) {
        lock(&self.state).closed = true;
        self.not_full.notify_all();
    }
    fn is_empty(&self) -> bool {
        lock(&self.state).jobs.is_empty()
    }
}
#[derive(Debug, Default)]
struct WakeState {
    permits: usize,
    closed: bool,
    #[cfg(test)]
    waiters: usize,
}
#[derive(Debug, Default)]
struct Wake {
    state: Mutex<WakeState>,
    posted: Condvar,
}
impl Wake {
    fn post(&self) {
        lock(&self.state).permits += 1;
        self.posted.notify_one();
    }
    fn wait(&self) {
        let mut state = lock(&self.state);
        while state.permits == 0 && !state.closed {
            #[cfg(test)]
            {
                state.waiters += 1;
            }
            state = wait(&self.posted, state);
            #[cfg(test)]
            {
                state.waiters -= 1;
            }
        }
        state.permits = state.permits.saturating_sub(1);
    }
    fn close(&self) {
        lock(&self.state).closed = true;
        self.posted.notify_all();
    }
    fn is_closed(&self) -> bool {
        lock(&self.state).closed
    }
}
#[derive(Debug)]
struct Queues {
    shards: Vec<ShardQueue>,
    wake: Wake,
    capacity: usize,
}
impl Queues {
    fn new(shards: usize, capacity: usize) -> Result<Self, WriteError> {
        assert!(capacity > 0);
        let mut queues = Vec::with_capacity(shards);
        for _ in 0..shards {
            queues.push(ShardQueue::new(capacity)?);
        }
        Ok(Self {
            shards: queues,
            wake: Wake::default(),
            capacity,
        })
    }
    fn push(&self, shard: usize, job: Job) -> Result<(), Job> {
        self.shards[shard].push(self.capacity, job)?;
        self.wake.post();
        Ok(())
    }
    fn pop(&self, preferred: usize) -> Option<Job> {
        loop {
            if let Some(job) = self.take(preferred) {
                return Some(job);
            }
            if self.wake.is_closed() && self.is_empty() {
                return None;
            }
            self.wake.wait();
        }
    }
    fn take(&self, preferred: usize) -> Option<Job> {
        let count = self.shards.len();
        (0..count).find_map(|offset| self.shards[(preferred + offset) % count].pop())
    }
    fn is_empty(&self) -> bool {
        self.shards.iter().all(ShardQueue::is_empty)
    }
    fn close(&self) {
        for shard in &self.shards {
            shard.close();
        }
        self.wake.close();
    }
    fn full_waits(&self) -> FullWaits {
        let mut total = FullWaits::default();
        for shard in &self.shards {
            total.add(lock(&shard.state).full_waits);
        }
        total
    }
}
/// The admission class of an object's output.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OutputClass {
    /// An object below `CUSTOM_WRITER_SIZE_MIN` bytes, which takes only a
    /// place in the window.
    Small,
    /// An object of at least `CUSTOM_WRITER_SIZE_MIN` bytes, which also takes
    /// one of the per-writer large places.
    Large,
}
impl OutputClass {
    /// The class of an object of `size` bytes.
    pub fn of(size: u64) -> Self {
        if size >= CUSTOM_WRITER_SIZE_MIN {
            Self::Large
        } else {
            Self::Small
        }
    }
}
/// One admitted output, held by its download from `acquire_output_slot`
/// until it drops, across every output the download prepares.
pub struct OutputSlot {
    class: OutputClass,
    owner: Arc<Shared>,
}
impl OutputSlot {
    pub fn class(&self) -> OutputClass {
        self.class
    }
}
impl std::fmt::Debug for OutputSlot {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("OutputSlot")
            .field("class", &self.class)
            .finish_non_exhaustive()
    }
}
impl Drop for OutputSlot {
    fn drop(&mut self) {
        self.owner.release_output(self.class);
    }
}
#[derive(Debug, Default)]
struct OutputSlots {
    active: usize,
    active_large: usize,
    closed: bool,
    #[cfg(test)]
    waiters: usize,
}
#[derive(Debug)]
struct Shared {
    config: SharedConfig,
    platform: Arc<dyn Platform>,
    spawner: Arc<dyn WorkerSpawner>,
    locality: LocalityContext,
    queues: Queues,
    slots: Mutex<OutputSlots>,
    available: Condvar,
    max_outputs: usize,
    max_large_outputs: usize,
    pending_jobs_hwm: AtomicUsize,
    jobs_enqueued: AtomicU64,
    jobs_written: AtomicU64,
}
impl Shared {
    fn acquire_output(&self, class: OutputClass) -> Result<(), WriteError> {
        let mut state = lock(&self.slots);
        while !state.closed
            && (state.active >= self.max_outputs
                || (class == OutputClass::Large && state.active_large >= self.max_large_outputs))
        {
            #[cfg(test)]
            {
                state.waiters += 1;
            }
            state = wait(&self.available, state);
            #[cfg(test)]
            {
                state.waiters -= 1;
            }
        }
        if state.closed {
            return Err(WriteError::SharedWriterClosed);
        }
        state.active += 1;
        if class == OutputClass::Large {
            state.active_large += 1;
        }
        Ok(())
    }
    fn release_output(&self, class: OutputClass) {
        let mut state = lock(&self.slots);
        assert!(state.active > 0);
        state.active -= 1;
        if class == OutputClass::Large {
            assert!(state.active_large > 0);
            state.active_large -= 1;
        }
        self.available.notify_all();
    }
    fn close(&self) {
        lock(&self.slots).closed = true;
        self.available.notify_all();
        self.queues.close();
    }
}
#[derive(Debug)]
struct Prepared {
    output: Arc<Output>,
    producer: Mutex<ProducerGuard>,
    started: Option<Instant>,
    phases: ObjectPhases,
}
impl Drop for Prepared {
    fn drop(&mut self) {
        self.output.close();
    }
}
/// Per-object callback state; clone it into the request and conclude after request shutdown.
#[derive(Clone, Debug)]
pub struct SharedOutput {
    prepared: Arc<Prepared>,
    shared: Arc<Shared>,
}
impl SharedOutput {
    pub fn enqueue(&self, body: Body) -> Result<(), WriteError> {
        let len = body.as_bytes().len();
        if len == 0 {
            return Ok(());
        }
        let output = &self.prepared.output;
        output.ticket_seen();
        let queued = self.enqueue_ticketed(body, len);
        if queued.is_err() {
            output.ticket_failed_pre_enqueue();
        }
        queued
    }
    fn enqueue_ticketed(&self, body: Body, len: usize) -> Result<(), WriteError> {
        let output = &self.prepared.output;
        let accepted = lock(&self.prepared.producer)
            .check()
            .map(|()| output.enter_callback())
            .and_then(|callback| output.accept(&body).map(|()| callback));
        let callback = match accepted {
            Ok(callback) => callback,
            Err(error) => {
                output.fail(error.clone());
                return Err(error);
            }
        };
        let shard = self
            .shared
            .locality
            .shard_for_body(body.offset, body.source_node);
        output.enqueued(len);
        let job = Job {
            body,
            prepared: Arc::clone(&self.prepared),
        };
        if let Err(job) = self.shared.queues.push(shard, job) {
            drop(job);
            output.reject_pending(WriteError::SharedWriterClosed);
            return Err(WriteError::SharedWriterClosed);
        }
        output.queued(&callback, len);
        self.shared.jobs_enqueued.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }
    /// Writes a body the CRT lends only for its callback before returning: a
    /// single-request GET's response, which no ticket keeps alive. It takes
    /// no pending-job slot and no queue slot. A failure is recorded, refuses the
    /// object's later bodies, and the returned error fails the request.
    pub fn write_now(&self, bytes: &[u8], offset: u64) -> Result<(), WriteError> {
        if bytes.is_empty() {
            return Ok(());
        }
        let output = &self.prepared.output;
        let written = lock(&self.prepared.producer)
            .check()
            .and_then(|()| output.write_now(offset, bytes));
        match &written {
            Ok(()) => {
                self.shared.jobs_enqueued.fetch_add(1, Ordering::Relaxed);
                self.shared.jobs_written.fetch_add(1, Ordering::Relaxed);
            }
            Err(error) => output.fail(error.clone()),
        }
        written
    }
    pub fn fail(&self, error: WriteError) {
        self.prepared.output.fail(error);
    }
    pub fn mode(&self) -> WriterMode {
        self.prepared.output.mode()
    }
    #[cfg(test)]
    pub(crate) fn is_closed(&self) -> bool {
        self.prepared.output.is_closed()
    }
    /// Refuses the object's further bodies, waits for its accepted ones, and
    /// concludes the output. After a failed transfer only a local error is
    /// reported: the transfer's result describes the incomplete body. The
    /// file stays open for `close_file`.
    pub fn finish(&self, transfer_succeeded: bool) -> Result<WriterStats, WriteError> {
        let drain_ns = self.close_and_wait();
        let result = self.prepared.output.conclude(transfer_succeeded);
        if diagnostics::ENABLED {
            self.log_phases(drain_ns);
            self.prepared.output.log_summary();
            diagnostics::log_memory_snapshot("summary", self.shared.platform.page_size());
        }
        result
    }
    #[cfg(test)]
    pub(crate) fn summary(&self) -> Option<diagnostics::OutputSummary> {
        self.prepared.output.summary()
    }
    /// Records when the CRT's finish callback ran, with instrumentation.
    /// The callback precedes the finish work that concludes the output, so
    /// the output is still live here.
    pub fn note_finish(&self) {
        self.prepared.output.record_finish();
    }
    /// Closes the object's input without concluding its transfer: refuses
    /// its further bodies and waits for its accepted ones, which are still
    /// written. Nothing is validated or evicted, and no failure is recorded.
    /// The file stays open for `close_file`.
    pub fn discard(&self) {
        let drain_ns = self.close_and_wait();
        self.log_phases(drain_ns);
    }
    fn close_and_wait(&self) -> u64 {
        let output = &self.prepared.output;
        let start = diagnostics::start();
        output.close_and_wait();
        let drain_ns = diagnostics::elapsed_ns(start);
        if diagnostics::ENABLED {
            self.shared
                .pending_jobs_hwm
                .fetch_max(output.pending_jobs_hwm(), Ordering::Relaxed);
        }
        drain_ns
    }
    fn log_phases(&self, drain_ns: u64) {
        if diagnostics::ENABLED {
            let mut phases = self.prepared.phases;
            phases.drain_ns = drain_ns;
            phases.total_ns = diagnostics::elapsed_ns(self.prepared.started);
            diagnostics::log_object_phases(&phases);
        }
    }
    /// Consumes the object's mapping and closes its file, once, even when the
    /// close fails; the caller never retries. A clone a request still holds
    /// finds the object closed. A delayed failure the close reports fails
    /// the download before its commit. The output slot stays with the
    /// download, which may prepare another output under it.
    pub fn close_file(self) -> Result<(), CloseError> {
        self.prepared.output.close_file()
    }
}
#[derive(Debug)]
pub struct SharedWriterService {
    shared: Arc<Shared>,
    workers: Mutex<Vec<JoinHandle<()>>>,
    prefault_pool: Option<PrefaultPool>,
}
impl SharedWriterService {
    pub fn start(config: SharedConfig) -> Result<Self, WriteError> {
        Self::start_with(config, Arc::new(NativePlatform), Arc::new(ThreadSpawner))
    }
    pub fn start_with_locality(
        config: SharedConfig,
        locality: LocalityContext,
    ) -> Result<Self, WriteError> {
        Self::start_resolved(
            config,
            Arc::new(NativePlatform),
            Arc::new(ThreadSpawner),
            locality,
        )
    }
    /// Starts the service on `platform`. `spawner` starts every writer and
    /// prefault worker: the pool's, and each mapped output's own.
    pub fn start_with(
        config: SharedConfig,
        platform: Arc<dyn Platform>,
        spawner: Arc<dyn WorkerSpawner>,
    ) -> Result<Self, WriteError> {
        let locality = LocalityContext::resolve(&config.writer.numa, Arc::clone(&platform))?;
        Self::start_resolved(config, platform, spawner, locality)
    }
    fn start_resolved(
        config: SharedConfig,
        platform: Arc<dyn Platform>,
        spawner: Arc<dyn WorkerSpawner>,
        locality: LocalityContext,
    ) -> Result<Self, WriteError> {
        let workers = shared_worker_count(config.writer.workers, locality.shard_count());
        let queues = Queues::new(locality.shard_count(), config.queue_jobs_per_shard)?;
        let shared = Arc::new(Shared {
            max_outputs: config.in_flight_max.max(1),
            max_large_outputs: workers,
            config,
            platform,
            spawner: Arc::clone(&spawner),
            locality,
            queues,
            slots: Mutex::new(OutputSlots::default()),
            available: Condvar::new(),
            pending_jobs_hwm: AtomicUsize::new(0),
            jobs_enqueued: AtomicU64::new(0),
            jobs_written: AtomicU64::new(0),
        });
        let mut this = Self {
            shared,
            workers: Mutex::new(Vec::new()),
            prefault_pool: None,
        };
        if this.shared.config.writer.mode == WriterMode::Crt {
            return Ok(this);
        }
        this.spawn(workers, spawner.as_ref())?;
        if this.uses_small_prefault_pool() {
            let started = PrefaultPool::start(
                &this.shared.locality,
                Arc::clone(&this.shared.platform),
                spawner.as_ref(),
            );
            diagnostics::log_shared_prefault(
                started.as_ref().ok().map(PrefaultPool::worker_count),
                started.as_ref().err(),
            );
            this.prefault_pool = started.ok();
        }
        Ok(this)
    }
    fn uses_small_prefault_pool(&self) -> bool {
        let writer = &self.shared.config.writer;
        let mapped = match writer.mode {
            WriterMode::Mmap => true,
            WriterMode::Direct => writer.requirement == Requirement::Preferred,
            WriterMode::Pwrite | WriterMode::Crt => false,
        };
        self.shared.max_outputs > 1
            && self.shared.config.custom_writer_required
            && mapped
            && writer.prefault == PrefaultMode::Enabled
    }
    pub(crate) fn prefault_source(&self, size: u64) -> PrefaultSource {
        if self.shared.config.writer.prefault == PrefaultMode::Disabled {
            return PrefaultSource::Disabled;
        }
        if self.uses_small_prefault_pool() && OutputClass::of(size) == OutputClass::Small {
            return self
                .prefault_pool
                .as_ref()
                .map_or(PrefaultSource::Disabled, |pool| {
                    PrefaultSource::Pooled(Arc::clone(pool.pool()))
                });
        }
        PrefaultSource::Private
    }
    /// Admits one output of `size` bytes for a download, waiting while the
    /// window's outputs, or for a large object the large ones, are all
    /// admitted. A closed service admits none.
    pub fn acquire_output_slot(&self, size: u64) -> Result<OutputSlot, WriteError> {
        let class = OutputClass::of(size);
        self.shared.acquire_output(class)?;
        Ok(OutputSlot {
            class,
            owner: Arc::clone(&self.shared),
        })
    }
    fn spawn(&mut self, count: usize, spawner: &dyn WorkerSpawner) -> Result<(), WriteError> {
        let (sender, receiver) = std::sync::mpsc::channel();
        for index in 0..count {
            let shared = Arc::clone(&self.shared);
            let shard = index % shared.locality.shard_count();
            let startup = sender.clone();
            lock(&self.workers).push(spawner.spawn(
                format!("download-shared-{index}"),
                Box::new(move || {
                    let placement = shared
                        .locality
                        .apply_to_shard(shard, shared.platform.as_ref());
                    let _ = startup.send(placement.clone());
                    drop(startup);
                    if placement.is_err() {
                        return;
                    }
                    while let Some(job) = shared.queues.pop(shard) {
                        shared.write_job(job);
                    }
                }),
            )?);
        }
        drop(sender);
        for result in receiver {
            result?;
        }
        Ok(())
    }
    /// Whether an object of `size` bytes takes a native writer; see
    /// `SharedConfig::should_use_custom_writer`.
    pub fn should_use_custom_writer(&self, size: u64) -> bool {
        self.shared.config.should_use_custom_writer(size)
    }
    /// Creates or truncates the temp file at `path` and prepares it for an
    /// object of `size` bytes, under the `slot` the caller's download holds.
    /// A failure leaves the slot with the caller.
    pub fn prepare_path(
        &self,
        slot: &OutputSlot,
        path: &Path,
        size: u64,
    ) -> Result<SharedOutput, WriteError> {
        self.check_slot(slot, size);
        let started = diagnostics::start();
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(true)
            .open(path)
            .map_err(|error| WriteError::create(create_error(error, path)))?;
        let phases = ObjectPhases {
            file_create_ns: diagnostics::elapsed_ns(started),
            ..ObjectPhases::default()
        };
        self.prepare_timed(file, size, started, phases)
    }
    /// Prepares `file` for an object of `size` bytes under the caller's `slot`.
    pub fn prepare(
        &self,
        slot: &OutputSlot,
        file: File,
        size: u64,
    ) -> Result<SharedOutput, WriteError> {
        self.check_slot(slot, size);
        self.prepare_timed(file, size, diagnostics::start(), ObjectPhases::default())
    }
    fn check_slot(&self, slot: &OutputSlot, size: u64) {
        assert!(
            Arc::ptr_eq(&slot.owner, &self.shared),
            "a slot of another service"
        );
        assert_eq!(slot.class, OutputClass::of(size), "a slot of another class");
    }
    fn prepare_timed(
        &self,
        file: File,
        size: u64,
        started: Option<Instant>,
        mut phases: ObjectPhases,
    ) -> Result<SharedOutput, WriteError> {
        let policy = Policy {
            config: &self.shared.config.writer,
            prefault: self.prefault_source(size),
            spawner: self.shared.spawner.as_ref(),
        };
        let output = Output::prepare(
            file,
            size,
            policy,
            Arc::clone(&self.shared.platform),
            &self.shared.locality,
            &mut phases,
        )?;
        phases.file_prepare_ns = phases
            .file_create_ns
            .saturating_add(phases.preallocate_ns)
            .saturating_add(phases.set_length_ns);
        let prepared = Arc::new(Prepared {
            output,
            producer: Mutex::new(ProducerGuard::default()),
            started,
            phases,
        });
        prepared.output.mark_transfer_start();
        Ok(SharedOutput {
            prepared,
            shared: Arc::clone(&self.shared),
        })
    }
    #[cfg(test)]
    pub(crate) fn active_outputs(&self) -> usize {
        lock(&self.shared.slots).active
    }
    #[cfg(test)]
    pub(crate) fn large_admission_full(&self) -> bool {
        lock(&self.shared.slots).active_large == self.shared.max_large_outputs
    }
    #[cfg(test)]
    pub(crate) fn admission_waiters(&self) -> usize {
        lock(&self.shared.slots).waiters
    }
    pub fn worker_count(&self) -> usize {
        lock(&self.workers).len()
    }
    pub fn close_and_join(&self) {
        self.shared.close();
        for worker in lock(&self.workers).drain(..) {
            assert!(worker.join().is_ok(), "shared writer panicked");
        }
    }
    /// The command's writer line, logged with instrumentation once the
    /// service has joined.
    pub fn log_summary(&self) {
        if diagnostics::ENABLED {
            diagnostics::log_shared_service_summary(&self.summary());
        }
    }
    fn summary(&self) -> diagnostics::SharedServiceSummary {
        let shared = &self.shared;
        let queues = &shared.queues;
        let full_waits = queues.full_waits();
        diagnostics::SharedServiceSummary {
            worker_count: shared.max_large_outputs,
            shard_count: queues.shards.len(),
            queue_capacity: queues.shards.len().saturating_mul(queues.capacity),
            active_outputs_max: shared.max_outputs,
            pending_jobs_hwm: shared.pending_jobs_hwm.load(Ordering::Relaxed),
            shard_full_wait_count: full_waits.count,
            shard_full_wait_ns: full_waits.ns,
            shard_full_wait_ns_max: full_waits.ns_max,
            jobs_enqueued: shared.jobs_enqueued.load(Ordering::Relaxed),
            jobs_written: shared.jobs_written.load(Ordering::Relaxed),
        }
    }
}
impl Drop for SharedWriterService {
    fn drop(&mut self) {
        self.close_and_join();
    }
}
impl Shared {
    fn write_job(&self, job: Job) {
        let Job { body, prepared } = job;
        let len = body.as_bytes().len();
        let result = prepared.output.write(&body);
        // Releasing the ticket before the job's pending count permits
        // reentrant CRT future completion during the release.
        drop(body);
        prepared.output.ticket_released();
        prepared.output.complete(len, result);
        self.jobs_written.fetch_add(1, Ordering::Relaxed);
    }
}
#[cfg(any(test, feature = "testing"))]
pub(crate) mod testing;
/// The error creating a temp file at `path` reports. Windows refuses to
/// create a file over a directory with `PermissionDenied`; this reports
/// `IsDir` for it instead, as POSIX already does.
fn create_error(error: std::io::Error, path: &Path) -> std::io::Error {
    directory_create_error(error, || path.is_dir())
}
fn directory_create_error(error: std::io::Error, is_dir: impl FnOnce() -> bool) -> std::io::Error {
    if error.kind() == std::io::ErrorKind::PermissionDenied && is_dir() {
        std::io::ErrorKind::IsADirectory.into()
    } else {
        error
    }
}
#[cfg(test)]
mod tests;
