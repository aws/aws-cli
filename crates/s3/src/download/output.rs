use super::diagnostics::{
    self, DirectFallback, MmapWriterSetup, ObjectPhases, OutputCounters, OutputStats,
    OutputSummary, Traced,
};
use super::{
    io::{self, DirectAlignment, IoStats},
    pages::PageCompletionTracker,
    platform::{Advice, MappedFile, Platform, Preallocation},
    prefault::{PrefaultSource, Prefaulter},
    range::CallbackRangeTracker,
    stream_copy::CopyPath,
    *,
};
use crate::cp::backstop::SetupError;
use std::{
    fs::File,
    sync::{Arc, Condvar, Mutex, MutexGuard, RwLock, RwLockReadGuard},
    time::Instant,
};

/// Retains source storage across the worker handoff.
#[derive(Debug)]
pub struct Body {
    pub offset: u64,
    storage: Storage,
    pub source_node: Option<u32>,
}
#[derive(Debug)]
enum Storage {
    Owned(Vec<u8>),
    Ticket(crt::s3::BodyChunk),
    #[cfg(test)]
    Tracked(Vec<u8>, DropCounter),
    #[cfg(any(test, feature = "testing"))]
    Observed(ObservedBody),
}
#[cfg(any(test, feature = "testing"))]
struct ObservedBody {
    bytes: Vec<u8>,
    release: Option<Box<dyn FnOnce() + Send>>,
}
#[cfg(any(test, feature = "testing"))]
impl std::fmt::Debug for ObservedBody {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct(
                "ObservedBod\
            y",
            )
            .field("bytes", &self.bytes.len())
            .finish_non_exhaustive()
    }
}
#[cfg(any(test, feature = "testing"))]
impl Drop for ObservedBody {
    fn drop(&mut self) {
        self.bytes.fill(0xdd);
        if let Some(release) = self.release.take() {
            release();
        }
    }
}
#[cfg(test)]
#[derive(Debug)]
pub(crate) struct DropCounter(pub(crate) Arc<std::sync::atomic::AtomicUsize>);
#[cfg(test)]
impl Drop for DropCounter {
    fn drop(&mut self) {
        self.0.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    }
}
impl Body {
    pub fn owned(offset: u64, bytes: Vec<u8>) -> Self {
        Self {
            offset,
            storage: Storage::Owned(bytes),
            source_node: None,
        }
    }
    pub fn as_bytes(&self) -> &[u8] {
        match &self.storage {
            Storage::Owned(bytes) => bytes,
            #[cfg(any(test, feature = "testing"))]
            Storage::Observed(body) => &body.bytes,
            Storage::Ticket(chunk) => chunk.as_bytes(),
            #[cfg(test)]
            Storage::Tracked(bytes, counter) => {
                let _ = counter;
                bytes
            }
        }
    }
    #[cfg(any(test, feature = "testing"))]
    pub(crate) fn observed(offset: u64, bytes: Vec<u8>, release: Box<dyn FnOnce() + Send>) -> Self {
        Self {
            offset,
            storage: Storage::Observed(ObservedBody {
                bytes,
                release: Some(release),
            }),
            source_node: None,
        }
    }
    #[cfg(test)]
    pub(crate) fn tracked(offset: u64, bytes: Vec<u8>, counter: DropCounter) -> Self {
        Self {
            offset,
            storage: Storage::Tracked(bytes, counter),
            source_node: None,
        }
    }
}
impl From<crt::s3::BodyChunk> for Body {
    fn from(chunk: crt::s3::BodyChunk) -> Self {
        Self {
            offset: chunk.range_start,
            source_node: chunk.source_node(),
            storage: Storage::Ticket(chunk),
        }
    }
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WriterStats {
    pub received_bytes: u64,
    pub enqueued_bytes: u64,
    pub written_bytes: u64,
    pub jobs: u64,
    pub write_calls: u64,
    pub interrupted_writes: u64,
    pub short_writes: u64,
    pub copy_requested_bytes: u64,
    pub copy_fallback_bytes: u64,
    pub direct_bounce_bytes: u64,
    pub direct_padded_bytes: u64,
}
#[derive(Debug, Default)]
struct State {
    ranges: CallbackRangeTracker,
    first_error: Option<WriteError>,
    closed: bool,
    pending: usize,
    pending_hwm: usize,
    #[cfg(test)]
    drain_waiters: usize,
    stats: WriterStats,
    trace: Traced<OutputTrace>,
}
#[derive(Clone, Copy, Debug, Default)]
struct OutputTrace {
    transfer_start: Option<Instant>,
    active_callbacks: usize,
    stats: OutputStats,
    counters: OutputCounters,
}
impl OutputTrace {
    fn new(config: &WriterConfig, mode: &Mode, locality: &LocalityContext) -> Self {
        let copy = match mode {
            Mode::Mmap { copy, .. } => *copy,
            Mode::Pwrite | Mode::Direct(_) => CopyMode::Memcpy,
        };
        Self {
            counters: OutputCounters {
                requested_writer_mode: diagnostics::writer_mode_name(config.mode),
                requested_writer_requirement: diagnostics::requirement_name(config.requirement),
                copy_mode: diagnostics::copy_mode_name(copy),
                numa_active: !locality.nodes.is_empty(),
                shard_count: locality.shard_count(),
                ..OutputCounters::default()
            },
            ..Self::default()
        }
    }
}
#[derive(Debug)]
pub(crate) struct Callback<'a> {
    output: &'a Output,
    started: Option<Instant>,
}
impl Drop for Callback<'_> {
    fn drop(&mut self) {
        self.output.record(|trace| trace.active_callbacks -= 1);
    }
}
#[derive(Debug)]
enum Mode {
    Pwrite,
    Direct(DirectAlignment),
    Mmap {
        mapping: Arc<dyn MappedFile>,
        tracker: Box<Mutex<PageCompletionTracker>>,
        prefaulter: Mutex<Option<Prefaulter>>,
        copy: CopyMode,
    },
}
impl Mode {
    fn writer(&self) -> WriterMode {
        match self {
            Self::Pwrite => WriterMode::Pwrite,
            Self::Mmap { .. } => WriterMode::Mmap,
            Self::Direct(_) => WriterMode::Direct,
        }
    }
}
#[derive(Debug)]
struct Target {
    mode: Mode,
    file: File,
}
#[derive(Debug)]
pub(crate) struct Output {
    target: RwLock<Option<Target>>,
    writer: WriterMode,
    pub(crate) size: u64,
    platform: Arc<dyn Platform>,
    state: Mutex<State>,
    wake: Condvar,
}
#[derive(Debug)]
pub(crate) struct Policy<'a> {
    pub(crate) config: &'a WriterConfig,
    pub(crate) prefault: PrefaultSource,
    pub(crate) spawner: &'a dyn WorkerSpawner,
}
impl Output {
    pub(crate) fn prepare(
        file: File,
        size: u64,
        policy: Policy<'_>,
        platform: Arc<dyn Platform>,
        locality: &LocalityContext,
        phases: &mut ObjectPhases,
    ) -> Result<Arc<Self>, WriteError> {
        assert_ne!(
            policy.config.mode,
            WriterMode::Crt,
            "a crt object has no native output"
        );
        let mode = match prepare_file(&file, size, &policy, &platform, locality, phases) {
            Ok(mode) => mode,
            Err(error) => {
                let _ = platform.close_file(file);
                return Err(error);
            }
        };
        let trace = Traced::new(OutputTrace::new(policy.config, &mode, locality));
        Ok(Arc::new(Self {
            writer: mode.writer(),
            target: RwLock::new(Some(Target { mode, file })),
            size,
            platform,
            state: Mutex::new(State {
                trace,
                ..State::default()
            }),
            wake: Condvar::new(),
        }))
    }
    fn record(&self, update: impl FnOnce(&mut OutputTrace)) {
        if diagnostics::ENABLED {
            lock(&self.state).trace.update(update);
        }
    }
    pub(crate) fn mark_transfer_start(&self) {
        self.record(|trace| trace.transfer_start = Some(Instant::now()));
    }
    pub(crate) fn record_finish(&self) {
        self.record(|trace| {
            if trace.transfer_start.is_some() {
                trace.stats.finish_rel_ns = diagnostics::elapsed_ns(trace.transfer_start);
            }
        });
    }
    pub(crate) fn enter_callback(&self) -> Callback<'_> {
        self.record(|trace| {
            trace.active_callbacks += 1;
            let max = &mut trace.counters.concurrent_callbacks_max;
            *max = (*max).max(trace.active_callbacks);
        });
        Callback {
            output: self,
            started: diagnostics::start(),
        }
    }
    pub(crate) fn ticket_seen(&self) {
        self.record(|trace| trace.counters.tickets_seen += 1);
    }
    pub(crate) fn ticket_failed_pre_enqueue(&self) {
        self.record(|trace| trace.counters.tickets_failed_pre_enqueue += 1);
    }
    pub(crate) fn ticket_released(&self) {
        self.record(|trace| trace.counters.tickets_released_by_writer += 1);
    }
    pub(crate) fn queued(&self, callback: &Callback<'_>, len: usize) {
        self.record_chunk(callback, len, true);
    }
    fn record_chunk(&self, callback: &Callback<'_>, len: usize, ticketed: bool) {
        self.record(|trace| {
            trace.counters.tickets_enqueued += u64::from(ticketed);
            let start_rel_ns = trace
                .transfer_start
                .zip(callback.started)
                .map(|(origin, started)| diagnostics::ns_between(origin, started));
            let callback_ns = diagnostics::elapsed_ns(callback.started);
            trace.stats.chunk(len, start_rel_ns, callback_ns);
        });
    }
    pub(crate) fn mode(&self) -> WriterMode {
        self.writer
    }
    fn target(&self) -> RwLockReadGuard<'_, Option<Target>> {
        self.target
            .read()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
    pub(crate) fn accept(&self, body: &Body) -> Result<(), WriteError> {
        let mut state = self.admit(body.offset, body.as_bytes().len())?;
        state.pending_hwm = state.pending_hwm.max(state.pending);
        Ok(())
    }
    fn admit(&self, offset: u64, len: usize) -> Result<MutexGuard<'_, State>, WriteError> {
        let mut state = lock(&self.state);
        if let Some(error) = state.first_error.clone() {
            state
                .trace
                .update(|trace| trace.counters.callbacks_after_first_error += 1);
            return Err(error);
        }
        if state.closed {
            state
                .trace
                .update(|trace| trace.counters.callbacks_after_input_closed += 1);
            return Err(WriteError::Closed);
        }
        state.ranges.add(self.size, offset, len)?;
        state.stats.received_bytes += len as u64;
        state.pending += 1;
        Ok(state)
    }
    pub(crate) fn write_now(&self, offset: u64, bytes: &[u8]) -> Result<(), WriteError> {
        let callback = self.enter_callback();
        drop(self.admit(offset, bytes.len())?);
        self.enqueued(bytes.len());
        self.record_chunk(&callback, bytes.len(), false);
        let result = self.write_at(offset, bytes);
        let error = result.as_ref().err().cloned();
        self.complete(bytes.len(), result);
        error.map_or(Ok(()), Err)
    }
    pub(crate) fn enqueued(&self, len: usize) {
        lock(&self.state).stats.enqueued_bytes += len as u64;
    }
    pub(crate) fn reject_pending(&self, error: WriteError) {
        let mut state = lock(&self.state);
        assert!(state.pending > 0);
        state.pending -= 1;
        state.first_error.get_or_insert(error);
        self.wake.notify_all();
    }
    pub(crate) fn write(&self, body: &Body) -> Result<IoStats, WriteError> {
        self.write_at(body.offset, body.as_bytes())
    }
    fn write_at(&self, offset: u64, bytes: &[u8]) -> Result<IoStats, WriteError> {
        if let Some(error) = self.error() {
            return Err(error);
        }
        if bytes.is_empty() {
            return Ok(IoStats::default());
        }
        let started = diagnostics::start();
        let result = self.write_target(offset, bytes);
        let write_ns = diagnostics::elapsed_ns(started);
        self.record(|trace| trace.stats.write_attempted(write_ns, result.as_ref()));
        result
    }
    fn write_target(&self, offset: u64, bytes: &[u8]) -> Result<IoStats, WriteError> {
        let target = self.target();
        let Some(Target { mode, file }) = target.as_ref() else {
            return Err(WriteError::Closed);
        };
        match mode {
            Mode::Pwrite => io::write_all(self.platform.as_ref(), file, bytes, offset, None),
            Mode::Direct(alignment) => io::write_direct(
                self.platform.as_ref(),
                file,
                bytes,
                offset,
                self.size,
                *alignment,
            ),
            Mode::Mmap {
                mapping,
                tracker,
                prefaulter,
                copy,
            } => {
                // SAFETY: accept audits every nonempty range before any job is published
                // or written; each accepted range is written exactly once, and Arc
                // retains the mapping through copying.
                let path = unsafe { mapping.copy_unique(offset as usize, bytes, *copy) };
                if let Some(prefaulter) = lock(prefaulter).as_ref() {
                    prefaulter.mark_copied_range(offset, bytes.len());
                }
                self.mapped_complete(offset, bytes.len(), mapping, tracker, path)
            }
        }
    }
    fn mapped_complete(
        &self,
        offset: u64,
        len: usize,
        mapping: &Arc<dyn MappedFile>,
        tracker: &Mutex<PageCompletionTracker>,
        path: CopyPath,
    ) -> Result<IoStats, WriteError> {
        let evictions = {
            let mut tracker = lock(tracker);
            tracker.complete_range(offset, len)?;
            tracker.take_pending_eviction_ranges(false)
        };
        let evicted = self.evict(mapping, &evictions)?;
        if cfg!(feature = "download-writer-debug") {
            let mut state = lock(&self.state);
            match path {
                CopyPath::Requested => state.stats.copy_requested_bytes += len as u64,
                CopyPath::MemcpyFallback => state.stats.copy_fallback_bytes += len as u64,
            }
        }
        Ok(evicted)
    }
    fn evict(
        &self,
        mapping: &Arc<dyn MappedFile>,
        ranges: &[std::ops::Range<usize>],
    ) -> Result<IoStats, WriteError> {
        let page = self.platform.page_size();
        let mut stats = IoStats::default();
        for range in ranges {
            let bytes = range.start * page..(range.end * page).min(mapping.len());
            let (start, len) = (bytes.start, bytes.len());
            let started = diagnostics::start();
            mapping.advise(bytes, Advice::Evict).map_err(|error| {
                let name = platform::advise_error_name(&error);
                diagnostics::log_mmap_evict_failed(start, len, name);
                WriteError::MmapEvictFailed
            })?;
            if diagnostics::ENABLED {
                stats.record_madvise(diagnostics::elapsed_ns(started), len);
            }
        }
        Ok(stats)
    }
    pub(crate) fn complete(&self, len: usize, result: Result<IoStats, WriteError>) {
        let mut state = lock(&self.state);
        assert!(state.pending > 0);
        match result {
            Ok(stats) => {
                state.stats.written_bytes += len as u64;
                add_stats(&mut state.stats, stats);
            }
            Err(error) => {
                state.first_error.get_or_insert(error);
            }
        }
        state.pending -= 1;
        self.wake.notify_all();
    }
    pub(crate) fn fail(&self, error: WriteError) {
        let mut state = lock(&self.state);
        state.first_error.get_or_insert(error);
        self.wake.notify_all();
    }
    pub(crate) fn error(&self) -> Option<WriteError> {
        lock(&self.state).first_error.clone()
    }
    #[cfg(any(test, feature = "testing"))]
    pub(crate) fn pending_jobs(&self) -> usize {
        lock(&self.state).pending
    }
    #[cfg(test)]
    pub(crate) fn prefault(&self) -> Option<Option<bool>> {
        match &self.target().as_ref()?.mode {
            Mode::Mmap { prefaulter, .. } => {
                Some(lock(prefaulter).as_ref().map(Prefaulter::is_pooled))
            }
            _ => None,
        }
    }
    pub(crate) fn pending_jobs_hwm(&self) -> usize {
        lock(&self.state).pending_hwm
    }
    #[cfg(test)]
    pub(crate) fn drain_waiters(&self) -> usize {
        lock(&self.state).drain_waiters
    }
    #[cfg(any(test, feature = "testing"))]
    pub(crate) fn observed_stats(&self) -> WriterStats {
        lock(&self.state).stats
    }
    #[cfg(test)]
    pub(crate) fn is_closed(&self) -> bool {
        lock(&self.state).closed
    }
    pub(crate) fn close(&self) {
        lock(&self.state).closed = true;
        self.wake.notify_all();
    }
    pub(crate) fn close_and_wait(&self) {
        let mut state = lock(&self.state);
        state.closed = true;
        self.wake.notify_all();
        while state.pending != 0 {
            #[cfg(test)]
            {
                state.drain_waiters += 1;
            }
            state = wait(&self.wake, state);
            #[cfg(test)]
            {
                state.drain_waiters -= 1;
            }
        }
    }
    pub(crate) fn conclude(&self, transfer_succeeded: bool) -> Result<WriterStats, WriteError> {
        self.close_and_wait();
        let state = lock(&self.state);
        let stats = state.stats;
        let error = state.first_error.clone();
        drop(state);
        let mapped_result = self.finish_mapping();
        if let Some(error) = error {
            return Err(error);
        }
        mapped_result?;
        if !transfer_succeeded {
            return Ok(stats);
        }
        validate_stats(stats, self.size)?;
        debug_assert!(lock(&self.state).ranges.is_complete(self.size));
        self.finish_direct_output()?;
        Ok(stats)
    }
    fn finish_direct_output(&self) -> Result<(), WriteError> {
        let target = self.target();
        let Some(Target { mode, file }) = target.as_ref() else {
            return Err(WriteError::Closed);
        };
        if matches!(mode, Mode::Direct(_)) {
            platform::set_length(self.platform.as_ref(), file, self.size)?;
        }
        Ok(())
    }
    pub(crate) fn close_file(&self) -> Result<(), CloseError> {
        self.close_and_wait();
        let target = self
            .target
            .write()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .take();
        let Some(Target { mode, file }) = target else {
            return Ok(());
        };
        drop(mode);
        self.platform.close_file(file)
    }
    fn finish_mapping(&self) -> Result<(), WriteError> {
        let target = self.target();
        if let Some(Target {
            mode:
                Mode::Mmap {
                    mapping,
                    tracker,
                    prefaulter,
                    ..
                },
            ..
        }) = target.as_ref()
        {
            let prefaulter = lock(prefaulter).take();
            drop(prefaulter);
            let evictions = lock(tracker).take_pending_eviction_ranges(true);
            let evicted = self.evict(mapping, &evictions)?;
            self.record(|trace| trace.stats.evicted(&evicted));
        }
        Ok(())
    }
    pub(crate) fn summary(&self) -> Option<OutputSummary> {
        let state = lock(&self.state);
        let trace = state.trace.get()?;
        let totals = state.stats;
        Some(OutputSummary {
            stats: OutputStats {
                active_writer_mode: diagnostics::writer_mode_name(self.writer),
                direct_active: self.writer == WriterMode::Direct,
                ..trace.stats
            },
            counters: OutputCounters {
                bytes_enqueued: totals.enqueued_bytes,
                bytes_written: totals.written_bytes,
                write_job_count: totals.jobs,
                copy_requested_bytes: totals.copy_requested_bytes,
                copy_fallback_bytes: totals.copy_fallback_bytes,
                ..trace.counters
            },
        })
    }
    pub(crate) fn log_summary(&self) {
        if let Some(summary) = self.summary() {
            diagnostics::log_output_summary(&summary);
        }
    }
}
fn add_stats(stats: &mut WriterStats, io: IoStats) {
    if !cfg!(feature = "download-writer-debug") {
        return;
    }
    stats.jobs += 1;
    stats.write_calls += io.calls;
    stats.short_writes += io.short_writes;
    stats.interrupted_writes += io.interrupted;
    stats.direct_bounce_bytes += io.bounce_bytes;
    stats.direct_padded_bytes += io.padded_bytes;
}
fn validate_stats(stats: WriterStats, size: u64) -> Result<(), WriteError> {
    if stats.received_bytes != size {
        return Err(WriteError::ReceivedSizeMismatch);
    }
    if stats.enqueued_bytes != size {
        return Err(WriteError::EnqueuedSizeMismatch);
    }
    if stats.written_bytes != size {
        return Err(WriteError::WrittenSizeMismatch);
    }
    Ok(())
}
fn prepare_file(
    file: &File,
    size: u64,
    policy: &Policy<'_>,
    platform: &Arc<dyn Platform>,
    locality: &LocalityContext,
    phases: &mut ObjectPhases,
) -> Result<Mode, WriteError> {
    let config = policy.config;
    if config.mode == WriterMode::Direct
        && config.requirement == Requirement::Required
        && !platform.direct_io_available()
    {
        return Err(WriteError::DirectUnsupportedOperatingSystem);
    }
    let start = diagnostics::start();
    let preallocation = platform::reserve(platform.as_ref(), file, size)?;
    phases.preallocate_ns = diagnostics::elapsed_ns(start);
    let start = diagnostics::start();
    platform::set_length(platform.as_ref(), file, size)?;
    phases.set_length_ns = diagnostics::elapsed_ns(start);
    prepare_mode(file, size, policy, platform, locality, preallocation)
}
fn prepare_mode(
    file: &File,
    size: u64,
    policy: &Policy<'_>,
    platform: &Arc<dyn Platform>,
    locality: &LocalityContext,
    preallocation: Preallocation,
) -> Result<Mode, WriteError> {
    let config = policy.config;
    match config.mode {
        WriterMode::Pwrite | WriterMode::Crt => Ok(Mode::Pwrite),
        WriterMode::Direct => {
            if let Some(mode) = prepare_direct(file, size, config.requirement, platform.as_ref())? {
                return Ok(mode);
            }
            if size == 0 {
                return Ok(Mode::Pwrite);
            }
            Ok(
                prepare_mmap(file, size, policy, platform, locality, preallocation)
                    .unwrap_or(Mode::Pwrite),
            )
        }
        WriterMode::Mmap if size == 0 => Ok(Mode::Pwrite),
        WriterMode::Mmap => {
            match prepare_mmap(file, size, policy, platform, locality, preallocation) {
                Err(_) if config.requirement == Requirement::Preferred => Ok(Mode::Pwrite),
                Err(_) => Err(WriteError::MmapUnavailable),
                result => result,
            }
        }
    }
}
fn prepare_direct(
    file: &File,
    size: u64,
    requirement: Requirement,
    platform: &dyn Platform,
) -> Result<Option<Mode>, WriteError> {
    if let Err(error) = platform.enable_direct_io(file) {
        if requirement == Requirement::Preferred {
            let name = platform::direct_io_error_name(&error);
            diagnostics::log_direct_fallback(DirectFallback::Unavailable(name));
            return Ok(None);
        }
        return Err(
            if matches!(error.raw_os_error(), Some(libc::EINVAL | libc::EOPNOTSUPP))
                || error.kind() == std::io::ErrorKind::Unsupported
            {
                WriteError::DirectUnavailable
            } else {
                error.into()
            },
        );
    }
    match probe_direct(file, size, platform) {
        Ok(mode) => Ok(Some(mode)),
        Err(error) if requirement == Requirement::Preferred => {
            let name = crate::cp::write_error_name(&error);
            diagnostics::log_direct_fallback(DirectFallback::Rejected(&name));
            platform.disable_direct_io(file)?;
            platform::set_length(platform, file, size)?;
            Ok(None)
        }
        Err(error) => Err(error),
    }
}
fn probe_direct(file: &File, size: u64, platform: &dyn Platform) -> Result<Mode, WriteError> {
    let alignment = platform.direct_io_alignment(file)?;
    alignment.validate()?;
    if size != 0 {
        let probe = platform.allocate_bounce(alignment.offset, io::BOUNCE_ALIGNMENT)?;
        io::write_all(platform, file, probe.as_slice(), 0, Some(alignment))?;
        platform::set_length(platform, file, size)?;
    }
    diagnostics::log_direct_writer(alignment);
    Ok(Mode::Direct(alignment))
}
fn prepare_mmap(
    file: &File,
    size: u64,
    policy: &Policy<'_>,
    platform: &Arc<dyn Platform>,
    locality: &LocalityContext,
    preallocation: Preallocation,
) -> Result<Mode, WriteError> {
    let mapping = map_output(file, size, policy, platform.as_ref(), preallocation)?;
    let size = mapping.len();
    let page = platform.page_size();
    let mut prefault_unavailable = None;
    let prefaulter = match &policy.prefault {
        PrefaultSource::Disabled => None,
        PrefaultSource::Private => Prefaulter::start_with(
            Arc::clone(&mapping),
            locality.clone(),
            Arc::clone(platform),
            policy.spawner,
        )
        .inspect_err(|error| {
            prefault_unavailable = Some(SetupError::spawn(error));
        })
        .ok(),
        PrefaultSource::Pooled(pool) => Some(Prefaulter::attach(
            Arc::clone(&mapping),
            Arc::clone(pool),
            platform.as_ref(),
        )),
    };
    let tracker = PageCompletionTracker::new(size, page, EVICTION_BYTES);
    if diagnostics::ENABLED {
        let setup = MmapWriterSetup {
            size,
            page_size: page,
            page_count: tracker.page_count(),
            eviction_batch_pages: tracker.eviction_batch_pages(),
            prefault_threads: prefaulter.as_ref().map_or(0, Prefaulter::thread_count),
            prefault_shared: prefaulter.as_ref().is_some_and(Prefaulter::is_pooled),
            numa_active: !locality.nodes.is_empty(),
            copy_mode: policy.config.copy_mode,
        };
        diagnostics::log_mmap_writer(&setup, prefault_unavailable.as_ref().map(SetupError::name));
    }
    Ok(Mode::Mmap {
        mapping,
        tracker: Box::new(Mutex::new(tracker)),
        prefaulter: Mutex::new(prefaulter),
        copy: policy.config.copy_mode,
    })
}
fn map_output(
    file: &File,
    size: u64,
    policy: &Policy<'_>,
    platform: &dyn Platform,
    preallocation: Preallocation,
) -> Result<Arc<dyn MappedFile>, WriteError> {
    use diagnostics::MmapUnavailableReason as Reason;
    if !platform.mmap_available() {
        diagnostics::log_mmap_unavailable(Reason::Os(platform::NAME));
        return Err(WriteError::MmapUnavailable);
    }
    if preallocation != Preallocation::Confirmed {
        diagnostics::log_mmap_unavailable(Reason::Preallocation(preallocation));
        return Err(WriteError::MmapUnavailable);
    }
    let Ok(len) = usize::try_from(size) else {
        diagnostics::log_mmap_unavailable(Reason::TooLarge(size));
        return Err(WriteError::OutOfBounds);
    };
    let mapping = platform.mmap_file(file, len).map_err(|error| {
        let name = platform::mmap_error_name(&error);
        diagnostics::log_mmap_unavailable(Reason::MmapFailed(name));
        WriteError::from(error)
    })?;
    let _ = mapping.advise(0..len, Advice::HugePages);
    if policy.config.requirement == Requirement::Preferred {
        let probe = 0..len.min(platform.page_size());
        mapping.advise(probe, Advice::Evict).map_err(|error| {
            let name = platform::advise_error_name(&error);
            diagnostics::log_mmap_unavailable(Reason::EvictProbeFailed(name));
            WriteError::from(error)
        })?;
    }
    Ok(mapping)
}
#[cfg(test)]
mod tests;
