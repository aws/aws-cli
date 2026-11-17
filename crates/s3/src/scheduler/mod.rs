//! Bounded transfer slots retained through request shutdown and file finalization.
use crate::{
    cp::recursive::{Finished, Stats, TransferRequest},
    transfer, uri,
};
use crt::s3::TransferResult;
use std::{
    collections::{BTreeMap, HashSet},
    fmt, io,
    path::{Path, PathBuf},
    sync::{
        Arc, Condvar, Mutex, MutexGuard, Weak,
        atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering},
    },
    time::Instant,
};

mod completion;
mod entries;
mod lifetime;
#[cfg(any(test, feature = "testing"))]
pub mod model;
mod native;
mod output;
mod parents;
mod queue;
mod render;
use crate::download::{OutputSlot, SharedOutput};
use completion::CompletionState;
pub use entries::{Archive, Entry, EntryLocal, ObjectCondition};
use parents::ParentDirectoryCache;
pub use queue::SubmitQueue;
pub use render::{Event, Sink, Stream};

/// A retained request reference; dropping it permits the final shutdown callback.
pub trait OwnedRequest: Send + Sync + fmt::Debug {
    fn cancel(&self);
}
/// Callback seam used by native CRT requests and deterministic test schedules.
pub trait Completion: Send + Sync + fmt::Debug {
    fn finish(&self, result: TransferResult);
    fn shutdown(&self);
    fn progress(&self, _bytes: u64) {}
    /// Whether the request is sent with a CRT progress hook that reports to
    /// `progress`; see `Scheduler::wants_progress_hook`.
    fn wants_progress_hook(&self) -> bool {
        false
    }
}
#[derive(Debug)]
pub enum SubmitError {
    Transfer(Box<TransferResult>),
    Local(String),
    RawLocal(Vec<u8>),
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TempPathError {
    OutOfMemory,
    /// The random source a temp name's id comes from failed.
    RandomUnavailable,
}
impl TempPathError {
    /// The error name a failed entry reports.
    pub fn name(self) -> &'static str {
        match self {
            Self::OutOfMemory => crate::local_error::OUT_OF_MEMORY,
            Self::RandomUnavailable => crate::local_error::RANDOM_UNAVAILABLE,
        }
    }
}
/// Why a move could not delete a source whose transfer succeeded.
#[derive(Debug)]
pub enum SourceDeleteError {
    /// The upload's file could not be removed.
    Local(io::Error),
    /// The download's DeleteObject failed, or Ctrl-C canceled it.
    Request(Box<TransferResult>),
}
#[derive(Debug, Clone)]
pub enum Finalize {
    Success,
    Transfer(Box<TransferResult>),
    Write(String),
    Commit(transfer::CommitFailure),
    Mtime(String),
}
/// Filesystem and request operations use the same scheduler in native and fake runs.
pub trait Operations: Send + Sync + fmt::Debug {
    fn create_parent(&self, path: &Path) -> io::Result<()>;
    fn exists(&self, path: &Path) -> bool;
    /// Inspects an upload's source as upstream's file generator does: its
    /// size, or why it is skipped.
    fn inspect_source(&self, path: &Path) -> transfer::SourceInspection;
    /// Names a download's temp path with a fresh random id, so seeing one
    /// temp name says nothing about the next.
    fn temp_path(&self, path: &Path) -> Result<PathBuf, TempPathError> {
        let id = transfer::temp_name_id().map_err(|_| TempPathError::RandomUnavailable)?;
        entries::temp_path(path, id)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        callbacks: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError>;
    fn finalize(&self, job: &Job, result: &TransferResult) -> Finalize;
    /// Deletes the source of a move's transfer that succeeded: an upload's
    /// file, or a download's object, whose DeleteObject the caller, a finish
    /// worker, waits for.
    fn delete_source(&self, job: &Job) -> Result<(), SourceDeleteError>;
    fn discard(&self, job: &Job);
    /// Retires a failed attempt that may be replayed: its output concludes,
    /// `await_shutdown` waits until no request can reach the output, and the
    /// output and its temp file go. The output slot stays with the job, so a
    /// replay prepares under it without waiting for admission, unless the
    /// replay lets the CRT write the file (`Job::size_changed`). Returns the
    /// local error the attempt found, which ends the download instead.
    fn retire_attempt(
        &self,
        job: &Job,
        _result: &TransferResult,
        await_shutdown: &dyn Fn(),
    ) -> Option<String> {
        await_shutdown();
        self.discard(job);
        None
    }
    /// Discovers the bucket's region for a failed transfer that redirected;
    /// runs on a finish worker, never a CRT callback.
    fn recover_region(&self, _result: &TransferResult) -> crt::redirect::Outcome {
        crt::redirect::Outcome::Unavailable
    }
}
#[derive(Debug)]
pub struct Job {
    /// What the job does: the command's transfer, or the DeleteObject a
    /// sync upload sends for an object only its destination holds.
    pub direction: transfer::Direction,
    pub raw_key: Vec<u8>,
    pub request_key: String,
    pub local_path: PathBuf,
    pub temp_path: Option<PathBuf>,
    pub size: Option<u64>,
    /// See `Entry::size_listed`.
    pub size_listed: bool,
    /// A native output's GET found the listed object another size than
    /// listed, or of no known size (`TransferResult::size_changed`), so the
    /// replay lets the CRT write the file, which needs no size up front.
    /// Set once, by the finish worker.
    pub size_changed: AtomicBool,
    pub modified: Option<i64>,
    /// What the download's object was found with, which conditions every
    /// attempt's GET of a download the CRT splits into parts.
    pub condition: ObjectCondition,
    /// The case-folded name a sync download under `--case-conflict` holds
    /// until the job ends.
    pub case_name: Option<String>,
    pub(crate) output: Mutex<DownloadOutput>,
    pub custom_writer: AtomicBool,
}
#[derive(Debug, Default)]
pub(crate) struct DownloadOutput {
    pub(crate) slot: Option<OutputSlot>,
    pub(crate) prepared: Option<SharedOutput>,
    pub(crate) failure: Option<OutputFailure>,
}
#[derive(Debug, Clone)]
pub(crate) enum OutputFailure {
    Write(String),
    Crt(Box<TransferResult>),
}
impl Job {
    fn sent_without_output(&self) -> bool {
        lock(&self.output).failure.is_some()
    }
    fn output_failure_result(&self, result: &TransferResult) -> Option<Finalize> {
        let failure = lock(&self.output).failure.clone()?;
        if result.canceled_by_interrupt || (result.error_code != 0 && !result.body_delivered) {
            return None;
        }
        Some(match failure {
            OutputFailure::Write(name) => Finalize::Write(name),
            OutputFailure::Crt(result) => Finalize::Transfer(result),
        })
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    Output(String),
    QueueClosed,
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Output(text) => f.write_str(text),
            Self::QueueClosed => f.write_str("submit queue failed"),
        }
    }
}
impl std::error::Error for Error {}
#[derive(Debug, Default)]
struct State {
    in_flight: usize,
    single_request_bytes: u64,
    requests: BTreeMap<u64, (Box<dyn OwnedRequest>, Arc<AtomicBool>)>,
    fatal: Option<String>,
    stats: Stats,
    warned: u64,
    canceled: u64,
    destroyed: u64,
    first_submission: Option<Instant>,
}
#[derive(Debug)]
pub struct Scheduler {
    request: TransferRequest,
    cwd: PathBuf,
    operations: Arc<dyn Operations>,
    sink: Arc<dyn Sink>,
    state: Mutex<State>,
    available: Condvar,
    interrupted: AtomicBool,
    raised: AtomicBool,
    sequence: AtomicU64,
    callbacks: Arc<lifetime::Lifetimes>,
    parents: Mutex<ParentDirectoryCache>,
    pool: Mutex<Option<crate::write_pool::WritePool<Arc<CompletionState>>>>,
    finish_on_pool: AtomicBool,
    prepare_pool: Mutex<Option<crate::write_pool::WritePool<Arc<CompletionState>>>>,
    case_names: Mutex<HashSet<String>>,
}
impl Scheduler {
    pub fn new(
        request: TransferRequest,
        cwd: PathBuf,
        operations: Arc<dyn Operations>,
        sink: Arc<dyn Sink>,
    ) -> Arc<Self> {
        assert!(request.engine_window() > 0);
        Arc::new(Self {
            request,
            cwd,
            operations,
            sink,
            state: Mutex::new(State::default()),
            available: Condvar::new(),
            interrupted: AtomicBool::new(false),
            raised: AtomicBool::new(false),
            sequence: AtomicU64::new(0),
            callbacks: Arc::new(lifetime::Lifetimes::default()),
            parents: Mutex::new(ParentDirectoryCache::default()),
            pool: Mutex::new(None),
            finish_on_pool: AtomicBool::new(false),
            prepare_pool: Mutex::new(None),
            case_names: Mutex::default(),
        })
    }
    /// Starts the workers that finish transfers off the CRT's threads, sized
    /// to the window so a push from a finish callback never blocks: each
    /// queued object still holds its slot. Downloads conclude there, and a
    /// failed transfer that redirected is replayed there; any other upload's
    /// result is still reported on its callback. Called before the first
    /// submission; a failure leaves no pool.
    pub fn start_finish_pool(&self, workers: usize) -> io::Result<()> {
        let mut pool = crate::write_pool::WritePool::new(
            workers,
            self.request.engine_window() as usize,
            |state: Arc<CompletionState>| state.execute_finish(),
        );
        pool.start()?;
        *lock(&self.pool) = Some(pool);
        self.finish_on_pool.store(true, Ordering::Release);
        Ok(())
    }
    /// Starts the workers that prepare each queued download's native output
    /// and send its request, so preparation that waits for an output slot or
    /// preallocates a file overlaps the producer within the existing window.
    /// They stay apart from the finish workers, which release the slots a
    /// blocked preparation waits for. The queue holds one job per engine
    /// slot, so a push never blocks. Called before the first submission; a
    /// failure leaves no pool.
    pub fn start_prepare_pool(&self, workers: usize) -> io::Result<()> {
        let mut pool = completion::prepare_pool(workers, self.request.engine_window() as usize);
        pool.start()?;
        *lock(&self.prepare_pool) = Some(pool);
        Ok(())
    }
    /// Closes the preparation queue once the producer stopped, and waits
    /// for its workers to submit or drop every job still queued; later
    /// submissions run on the submitting thread.
    pub fn stop_prepare_pool(&self) {
        let Some(mut pool) = lock(&self.prepare_pool).take() else {
            return;
        };
        pool.close();
        pool.join();
    }
    fn finishes_on_pool(&self) -> bool {
        self.finish_on_pool.load(Ordering::Acquire)
    }
    pub fn interrupted(&self) -> bool {
        self.interrupted.load(Ordering::Acquire)
    }
    fn stopped(&self) -> bool {
        self.interrupted() || self.raised.load(Ordering::Acquire)
    }
    /// Ends the transfers for an exception the producer raised, as upstream's
    /// transfer manager does when its file generator raises
    /// (s3transfer's `TransferManager.__exit__`): `exception` is published as
    /// the command's fatal error, and then every request in flight is canceled.
    /// Each cancellation is recorded as Ctrl-C's, whose result the processor
    /// drops after that error; a canceled download discards its temp file.
    ///
    /// A Ctrl-C `interrupt` recorded first outranks the exception: the
    /// transfers still end, but `exception` is not published, since the
    /// processor takes nothing after a fatal error, and the cancellation the
    /// command reports instead would be lost.
    pub fn cancel_for_exception(&self, exception: Vec<u8>, interrupt: &cli_core::interrupt::State) {
        if !interrupt.is_requested() {
            self.publish(crate::results::Event::Fatal(exception));
        }
        // Entries still queued for submission are dropped, and a request
        // being submitted is canceled as it is adopted. Raised only after the
        // fatal result is queued: that cancellation's result must not reach
        // the processor first, or it reads as Ctrl-C.
        self.raised.store(true, Ordering::Release);
        self.cancel_in_flight();
    }
    fn cancel_in_flight(&self) {
        let state = lock(&self.state);
        for (request, canceled) in state.requests.values() {
            canceled.store(true, Ordering::Release);
            request.cancel();
        }
    }
    pub fn drain(&self) {
        let mut state = lock(&self.state);
        while state.in_flight != 0 {
            state = wait(&self.available, state);
        }
        assert!(state.requests.is_empty());
        drop(state);
        self.callbacks.drain();
        let mut state = lock(&self.state);
        if self.request.collect_stats {
            state.stats.elapsed_ns = state
                .first_submission
                .map_or(0, |start| ns(start.elapsed()));
        }
    }
    pub fn close_write_pool(&self) {
        let Some(mut pool) = lock(&self.pool).take() else {
            return;
        };
        pool.close();
        pool.join();
        let stats = pool.stats();
        let mut state = lock(&self.state);
        state.stats.write_queue_hwm = stats.queue_hwm;
        state.stats.writes_completed = stats.executed;
        state.stats.write_ns = stats.execute_ns;
    }
    pub fn finished(&self) -> Finished {
        let state = lock(&self.state);
        Finished {
            fatal: state.fatal.clone(),
            canceled: self.interrupted(),
            failed: state.stats.failed,
            warned: state.warned,
            stats: self.request.collect_stats.then(|| state.stats.clone()),
            ..Default::default()
        }
    }
    pub fn record_fatal(&self, error: impl fmt::Display) {
        let mut state = lock(&self.state);
        if state.fatal.is_none() {
            state.fatal = Some(error.to_string());
        }
    }
    fn single_request_bytes(&self, direction: transfer::Direction, size: Option<u64>) -> u64 {
        if direction != transfer::Direction::Download {
            return 0;
        }
        match (self.request.runtime.single_request_threshold, size) {
            (Some(threshold), Some(size)) if size <= threshold => size,
            _ => 0,
        }
    }
    fn admits(&self, state: &State, bytes: u64) -> bool {
        state.in_flight < self.request.engine_window() as usize
            && (bytes == 0
                || state.single_request_bytes == 0
                || state
                    .single_request_bytes
                    .checked_add(bytes)
                    .is_some_and(|total| total <= self.request.sizing.single_request_bytes_max))
    }
    fn reserve(&self, bytes: u64) {
        let mut state = lock(&self.state);
        let start = Instant::now();
        let stalled = !self.admits(&state, bytes);
        if self.request.collect_stats && stalled {
            state.stats.stall_count += 1;
        }
        while !self.admits(&state, bytes) {
            state = wait(&self.available, state);
        }
        state.in_flight += 1;
        state.single_request_bytes += bytes;
        if self.request.collect_stats {
            if stalled {
                state.stats.stall_ns += ns(start.elapsed());
            }
            state.stats.in_flight_hwm = state.stats.in_flight_hwm.max(state.in_flight as u64);
            state.first_submission.get_or_insert_with(Instant::now);
        }
    }
    fn unreserve(&self, bytes: u64) {
        let mut state = lock(&self.state);
        assert!(state.in_flight > 0);
        state.in_flight -= 1;
        assert!(bytes <= state.single_request_bytes);
        state.single_request_bytes -= bytes;
        self.available.notify_all();
    }
    fn retire(&self, job: &Job, bytes: u64) {
        if let Some(name) = &job.case_name {
            lock(&self.case_names).remove(name);
        }
        self.release_slot(bytes);
    }
    /// Takes `name`, a sync download's case-folded name, for a download
    /// whose job releases it when it ends.
    pub fn claim_case_name(&self, name: &str) {
        lock(&self.case_names).insert(name.to_owned());
    }
    /// Whether a download that has not finished holds the case-folded `name`.
    pub fn holds_case_name(&self, name: &str) -> bool {
        lock(&self.case_names).contains(name)
    }
    fn release_slot(&self, bytes: u64) {
        let mut state = lock(&self.state);
        assert!(state.in_flight > 0);
        state.in_flight -= 1;
        assert!(bytes <= state.single_request_bytes);
        state.single_request_bytes -= bytes;
        state.destroyed += 1;
        self.available.notify_all();
    }
    /// Publishes the submission total once the producer has stopped, unless
    /// it stopped before naming every object, which leaves the totals
    /// estimates. Upstream reports it once its file generator is exhausted.
    /// One object's total already went out with its queued result.
    pub fn finish_submissions(&self, exhausted: bool) {
        if !exhausted {
            return;
        }
        if self.request.object.is_some() && self.sequence.load(Ordering::Relaxed) > 0 {
            return;
        }
        self.notify_total_submissions();
    }
    pub fn notify_total_submissions(&self) {
        self.publish(crate::results::Event::FinalTotal(
            self.sequence.load(Ordering::Relaxed),
        ));
    }
    fn publish(&self, event: crate::results::Event) {
        if let Err(error) = self.sink.publish(event, self.request.quiet) {
            self.record_fatal(error);
        }
    }
    pub(super) fn wants_progress_hook(&self) -> bool {
        self.sink.wants_progress()
    }
}
impl cli_core::InterruptHook for Scheduler {
    fn cancel(&self) {
        self.interrupted.store(true, Ordering::Release);
        self.cancel_in_flight();
    }
}
impl Drop for Scheduler {
    fn drop(&mut self) {
        assert_eq!(
            lock(&self.state).in_flight,
            0,
            "scheduler dropped before drain"
        );
        assert!(lock(&self.state).requests.is_empty());
        self.stop_prepare_pool();
        self.close_write_pool();
    }
}
fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(|e| e.into_inner())
}
fn wait<'a, T>(wake: &Condvar, guard: MutexGuard<'a, T>) -> MutexGuard<'a, T> {
    wake.wait(guard).unwrap_or_else(|e| e.into_inner())
}
fn ns(duration: std::time::Duration) -> u64 {
    u64::try_from(duration.as_nanos()).unwrap_or(u64::MAX)
}
#[cfg(test)]
mod tests;
