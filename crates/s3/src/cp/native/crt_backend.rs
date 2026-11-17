use super::*;
use crate::cp::backstop::SetupError;
use crate::cp::producer::{self, LocalRoot};
use crate::cp::recursive::ProducerResult;
use crate::cp::runner::{self, TransferEnv};
use crate::download::{
    DownloadLocality, LocalityContext, SharedConfig, SharedWriterService, platform::NativePlatform,
    queue_jobs_per_shard,
};
use crate::results;
use crate::scheduler::{ObjectCondition, Scheduler, Sink, SubmitQueue};
use crate::sync::comparator::{self, Comparator, LocalSide, Modified, Pairing};
use crate::sync::{CaseConflict, SourceOnly};
use crt::redirect::Resolver;
use crt::runtime::BucketRuntime;
use crt::s3::{HeadObject, ListEntry, ListOptions, ListResult, ListStats};
use std::ops::ControlFlow;
use std::sync::{Arc, mpsc};
const SOURCE_POOL_BUDGET_FROM_MEMORY_LIMIT: usize = 0;

pub(super) fn run(
    request: recursive::TransferRequest,
    env: &NativeEnv<'_>,
    source: &OsStr,
    printer: Option<results::PrinterConfig>,
    ignored: &str,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let processor = results::Processor::with_diagnostics(printer);
    run_reported(
        processor,
        (stdout, stderr),
        results::spawn_drain,
        |publisher| transfer(env, &request, source, publisher, ignored),
    )
}
pub(super) fn run_reported(
    processor: results::Processor,
    (stdout, stderr): (&mut (dyn Write + Send), &mut (dyn Write + Send)),
    spawn: impl for<'scope, 'env> FnOnce(
        &'scope std::thread::Scope<'scope, 'env>,
        results::Drain<'scope>,
    ) -> std::io::Result<results::DrainThread<'scope>>,
    transfer: impl FnOnce(&results::Publisher) -> Result<u8, CommandFailure>,
) -> Result<u8, CommandFailure> {
    let publisher = processor.publisher();
    let (status, output) = std::thread::scope(|scope| {
        let running = match processor.start_with(scope, &mut *stdout, &mut *stderr, spawn) {
            Ok(running) => running,
            Err(error) => {
                return (
                    Err(command::failure(SetupError::spawn(&error).name())),
                    Ok(()),
                );
            }
        };
        let status = transfer(&publisher);
        (status, running.stop())
    });
    match output {
        Ok(()) => status,
        Err(errors) => close_output(errors, status),
    }
}
fn close_output(
    errors: results::WriteErrors,
    status: Result<u8, CommandFailure>,
) -> Result<u8, CommandFailure> {
    use cli_core::cli_error::{self, StdoutFailure};
    let printer_swallowed_stdout_error = errors
        .stdout
        .as_ref()
        .and_then(StdoutFailure::from_write_error)
        .is_some();
    let printer_swallowed_stderr_error = errors
        .stderr
        .as_ref()
        .and_then(StdoutFailure::from_stream_error)
        .is_some();
    if printer_swallowed_stdout_error || printer_swallowed_stderr_error {
        return status;
    }
    let broken_pipe = |error: &Option<std::io::Error>| {
        error
            .as_ref()
            .is_some_and(|error| error.kind() == std::io::ErrorKind::BrokenPipe)
    };
    if broken_pipe(&errors.stdout) || broken_pipe(&errors.stderr) {
        return Err(command::failure(cli_error::BROKEN_PIPE_MESSAGE));
    }
    Err(command::failure(cli_error::WRITE_FAILED_MESSAGE))
}
fn transfer(
    env: &NativeEnv<'_>,
    request: &recursive::TransferRequest,
    source: &OsStr,
    publisher: &results::Publisher,
    ignored: &str,
) -> Result<u8, CommandFailure> {
    // A single download looked up the working directory its results are
    // spelled against before it reported any outcome, so a lookup that fails
    // still ends the command first.
    if request.refusal_is_fatal()
        && let Some(refusal) = &request.refusal
    {
        runner::warn_ignored(publisher, ignored);
        if request.object.is_some() && !request.quiet {
            env.checked_invocation_dir()
                .map_err(|error| command::failure(SetupError::current_dir(&error).name()))?;
        }
        recursive::CommandReport::new(publisher, request.quiet).fatal(refusal.as_bytes());
        return Ok(1);
    }
    let completion =
        runner::run_transfer(env, request, interrupt::process_state(), publisher, ignored)
            .map_err(|error| command::failure(error.name()))?;
    runner::report_completion(publisher, source, request, &completion).map_err(
        |error| match error {
            recursive::RenderError::ClientFailed(result) => {
                command::client_failure(&result, &request.runtime.credentials)
            }
            error => command::failure(error.to_string()),
        },
    )
}
#[derive(Debug)]
pub(super) struct NativeEnv<'a> {
    pub(super) cwd: &'a Path,
    pub(super) debug: bool,
    pub(super) resolver: Option<Arc<dyn Resolver>>,
}
impl TransferEnv for NativeEnv<'_> {
    type Source = LocalRoot;
    type Runtime = Arc<BucketRuntime>;
    fn open_local_root(
        &self,
        request: &recursive::TransferRequest,
    ) -> std::io::Result<Option<LocalRoot>> {
        producer::open_local_root(request)
    }
    fn checked_invocation_dir(&self) -> std::io::Result<PathBuf> {
        let current = std::env::current_dir()?;
        Ok(if self.cwd.is_absolute() {
            self.cwd.to_path_buf()
        } else {
            current
        })
    }
    fn resolve_writers(
        &self,
        request: &recursive::TransferRequest,
    ) -> Result<Option<DownloadLocality>, SetupError> {
        resolve_writers(request)
    }
    fn create_runtime(
        &self,
        request: &recursive::TransferRequest,
        writers: Option<&DownloadLocality>,
    ) -> Result<Result<Arc<BucketRuntime>, Box<crt::s3::TransferResult>>, SetupError> {
        Ok(BucketRuntime::new(
            runtime_options(request, writers),
            self.resolver.clone(),
            Some(crt::debug::Logger::new(self.debug)),
        )
        .map(Arc::new))
    }
    fn start_service(
        &self,
        request: &recursive::TransferRequest,
        writers: Option<DownloadLocality>,
    ) -> Result<Option<Arc<SharedWriterService>>, SetupError> {
        service_config(request, writers)
            .map(|(config, locality)| SharedWriterService::start_with_locality(config, locality))
            .transpose()
            .map(|service| service.map(Arc::new))
            .map_err(|error| SetupError::write(&error))
    }
    fn scheduler(
        &self,
        request: &recursive::TransferRequest,
        cwd: PathBuf,
        runtime: Option<&Arc<BucketRuntime>>,
        service: Option<&Arc<SharedWriterService>>,
        sink: Arc<dyn Sink>,
    ) -> Result<Arc<Scheduler>, SetupError> {
        Ok(Scheduler::native(
            request.clone(),
            cwd,
            runtime.cloned(),
            service.cloned(),
            sink,
        ))
    }
    fn start_finish_pool(&self, scheduler: &Scheduler, workers: usize) -> std::io::Result<()> {
        scheduler.start_finish_pool(workers)
    }
    fn start_prepare_pool(&self, scheduler: &Scheduler, workers: usize) -> std::io::Result<()> {
        scheduler.start_prepare_pool(workers)
    }
    fn produce(
        &self,
        request: &recursive::TransferRequest,
        runtime: Option<&Arc<BucketRuntime>>,
        scheduler: &Arc<Scheduler>,
        source: Option<LocalRoot>,
    ) -> ProducerResult {
        if let Some(object) = &request.object {
            let outcome = match runtime {
                Some(runtime) if request.direction == Direction::Download => {
                    let key = crate::uri::encode_s3_request_path_key_bytes(&object.key);
                    let headers = head_object_headers(request);
                    let head = HeadObject {
                        key: key.as_bytes(),
                        request_payer: request.headers.request_payer_value(),
                        headers: &headers,
                    };
                    producer::produce_download_object(scheduler, object, || {
                        runtime.head_object(head, interrupt::process_state())
                    })
                }
                _ if request.direction == Direction::Delete => {
                    producer::produce_delete_object(scheduler, object)
                }
                _ => producer::produce_object(scheduler, object),
            };
            return ProducerResult {
                outcome,
                ..ProducerResult::default()
            };
        }
        match (runtime, source, &request.sync) {
            (Some(runtime), _, Some(sync)) if request.direction == Direction::Download => {
                produce_sync_listing(request, runtime, scheduler, sync.strategies)
            }
            (Some(runtime), _, _) if request.direction != Direction::Upload => produce_listing(
                request,
                runtime,
                Arc::clone(scheduler),
                &mut |_: &ListedObject<'_>| Selection::QUEUE,
            ),
            (Some(runtime), Some(source), Some(sync)) => {
                produce_sync_walk(request, runtime, scheduler, source, sync.strategies)
            }
            (_, Some(source), _) => ProducerResult {
                outcome: producer::produce_walk(
                    request,
                    scheduler,
                    source,
                    interrupt::process_state(),
                ),
                ..ProducerResult::default()
            },
            (_, None, _) => ProducerResult::default(),
        }
    }
}
fn resolve_writers(
    request: &recursive::TransferRequest,
) -> Result<Option<DownloadLocality>, SetupError> {
    let Some(tuning) = &request.download else {
        return Ok(None);
    };
    LocalityContext::resolve_download(
        &tuning.writer.numa,
        tuning.writer.mode,
        tuning.numa_pool,
        Arc::new(NativePlatform),
    )
    .map(Some)
    .map_err(|error| SetupError::write(&error))
}
fn runtime_options(
    request: &recursive::TransferRequest,
    writers: Option<&DownloadLocality>,
) -> RuntimeOptions {
    let mut options = request.runtime.clone();
    options.throughput_target_gbps = request.sizing.throughput_target_gbps;
    options.memory_limit_in_bytes = request.sizing.memory_limit_in_bytes;
    options.max_active_connections_override = request.sizing.max_connections;
    let (Some(_), Some(writers)) = (&request.download, writers) else {
        return options;
    };
    options.numa_source_pool_config =
        writers
            .source_pool
            .clone()
            .map(|nodes| crt::source_pool::Config {
                nodes,
                budget_bytes: SOURCE_POOL_BUDGET_FROM_MEMORY_LIMIT,
            });
    options
}
fn service_config(
    request: &recursive::TransferRequest,
    writers: Option<DownloadLocality>,
) -> Option<(SharedConfig, LocalityContext)> {
    let (Some(tuning), Some(writers)) = (&request.download, writers) else {
        return None;
    };
    let config = SharedConfig {
        writer: tuning.writer.clone(),
        custom_writer_required: tuning.custom_writer_required || request.object.is_some(),
        in_flight_max: request.engine_window() as usize,
        queue_jobs_per_shard: queue_jobs_per_shard(
            request.sizing.source_pool_bytes,
            config::buffer_part_size(request.runtime.part_size),
            request.engine_window(),
        ),
    };
    Some((config, writers.locality))
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Selection {
    Queue { case_name: Option<String> },
    Skip,
    Stop,
}
impl Selection {
    const QUEUE: Self = Self::Queue { case_name: None };
}
trait Select {
    fn select(&mut self, listed: &ListedObject<'_>, queue: &SubmitQueue) -> Selection;
    fn listed(&mut self, _result: &ListResult, _queue: &SubmitQueue) {}
}
impl<F: FnMut(&ListedObject<'_>) -> Selection> Select for F {
    fn select(&mut self, listed: &ListedObject<'_>, _: &SubmitQueue) -> Selection {
        self(listed)
    }
}
fn list_options(request: &recursive::TransferRequest) -> ListOptions<'_> {
    ListOptions {
        prefetch: request.prefetch,
        bucket: request.bucket.as_bytes(),
        prefix: &request.prefix,
        request_payer: request.headers.request_payer_value().unwrap_or_default(),
        recursive: true,
        page_size: request.page_size,
        user_agent: request.listing_user_agent.as_deref().map(str::as_bytes),
        object_conditions: request.direction == transfer::Direction::Download,
    }
}
fn produce_listing(
    request: &recursive::TransferRequest,
    runtime: &BucketRuntime,
    scheduler: Arc<Scheduler>,
    select: &mut dyn Select,
) -> ProducerResult {
    produce_listing_with(
        request,
        interrupt::process_state(),
        scheduler,
        |scheduler| SubmitQueue::new(scheduler, crate::constants::SUBMIT_QUEUE_CAPACITY_DEFAULT),
        |stats, callback| {
            runtime.list_objects(
                list_options(request),
                stats,
                callback,
                interrupt::process_state(),
            )
        },
        select,
    )
}
#[derive(Debug, Clone, Copy)]
struct ListedObject<'a> {
    key: &'a str,
    size: u64,
    modified: Option<i64>,
}
fn produce_listing_with(
    request: &recursive::TransferRequest,
    state: &interrupt::State,
    scheduler: Arc<Scheduler>,
    start_queue: impl FnOnce(Arc<Scheduler>) -> std::io::Result<SubmitQueue>,
    list: impl FnOnce(Option<&mut ListStats>, &mut dyn FnMut(ListEntry) -> i32) -> ListResult,
    select: &mut dyn Select,
) -> ProducerResult {
    let mut queue = match start_queue(Arc::clone(&scheduler)) {
        Ok(queue) => queue,
        Err(error) => {
            scheduler.record_fatal(SetupError::spawn(&error));
            return ProducerResult::default();
        }
    };
    if state.is_requested() {
        return ProducerResult::default();
    }
    let mut stats = crt::s3::ListStats::default();
    let result = list(request.collect_stats.then_some(&mut stats), &mut |entry| {
        if state.is_requested() {
            return -1;
        }
        queue_listed_entry(&scheduler, &mut queue, entry, select)
    });
    if let Some(exception) = recursive::listing_exception(request, &result) {
        scheduler.cancel_for_exception(exception, state);
    }
    select.listed(&result, &queue);
    queue.close_and_join();
    ProducerResult {
        outcome: recursive::ProducerOutcome::ListCompleted(Box::new(result)),
        submit_queue_failed: queue.is_failed(),
        list_stats: request.collect_stats.then_some(stats),
    }
}
fn queue_listed_entry(
    scheduler: &Scheduler,
    queue: &mut SubmitQueue,
    entry: ListEntry,
    select: &mut dyn Select,
) -> i32 {
    if entry.kind != crt::s3::EntryKind::Object {
        return 0;
    }
    let Ok(key) = String::from_utf8(entry.name) else {
        return -1;
    };
    if !scheduler.listed_entry_passes_filters(key.as_bytes(), entry.size) {
        return 0;
    }
    let modified = entry.date.map(|date| date.epoch_seconds);
    let listed = ListedObject {
        key: &key,
        size: entry.size,
        modified,
    };
    let case_name = match select.select(&listed, queue) {
        Selection::Queue { case_name } => case_name,
        Selection::Skip => return 0,
        Selection::Stop => return -1,
    };
    let condition = ObjectCondition {
        etag: entry.etag,
        full_object_checksum: entry.full_object_checksum,
    };
    let pushed = queue.push_case_named(
        key,
        entry.size,
        modified,
        entry.archive,
        case_name,
        condition,
    );
    if pushed.is_ok() { 0 } else { -1 }
}
/// The headers a single download's HeadObject sends after its own: the
/// transfer's, then the checksum mode when the download checks checksums,
/// as upstream's file generator asks for the checksum then
/// (`FileGenerator._list_single_object`,
/// `RequestParamsMapper.map_head_object_params`).
fn head_object_headers(request: &recursive::TransferRequest) -> Vec<crt::s3::Header> {
    let mut headers = request.headers.object.clone();
    if request.checksums.validate_downloads
        || request.runtime.response_checksum_validation == crt::runtime::ChecksumMode::WhenSupported
    {
        headers.push(crt::s3::Header::new("x-amz-checksum-mode", "ENABLED"));
    }
    headers
}
/// The comparator's time of a listed object.
///
/// Upstream raises for a listing without one (utils.py `BucketLister`),
/// which S3 always sends; the comparator takes it as the epoch.
fn listed_modified(modified: Option<i64>) -> Modified {
    modified.map_or(Modified::EPOCH, Modified::from_epoch_seconds)
}
fn produce_sync_listing(
    request: &recursive::TransferRequest,
    runtime: &BucketRuntime,
    scheduler: &Arc<Scheduler>,
    strategies: crate::sync::Strategies,
) -> ProducerResult {
    produce_sync_listing_with(
        request,
        interrupt::process_state(),
        scheduler,
        strategies,
        |select| produce_listing(request, runtime, Arc::clone(scheduler), select),
    )
}
fn produce_sync_listing_with(
    request: &recursive::TransferRequest,
    state: &interrupt::State,
    scheduler: &Arc<Scheduler>,
    strategies: crate::sync::Strategies,
    produce: impl FnOnce(&mut dyn Select) -> ProducerResult,
) -> ProducerResult {
    let destination = producer::LocalDestination::new(request, scheduler, state);
    let mut select = SyncDownload {
        request,
        scheduler,
        state,
        strategies,
        comparator: Comparator::new(strategies, LocalSide::Destination, destination),
        failure: None,
    };
    let mut produced = produce(&mut select);
    if let Some(error) = select.failure {
        produced.outcome = recursive::ProducerOutcome::ComparatorRaised(error);
    }
    produced
}
struct SyncDownload<'a> {
    request: &'a recursive::TransferRequest,
    scheduler: &'a Arc<Scheduler>,
    state: &'a interrupt::State,
    strategies: crate::sync::Strategies,
    comparator: Comparator<producer::LocalDestination<'a>>,
    failure: Option<String>,
}
impl SyncDownload<'_> {
    fn raise(&mut self, error: String) {
        self.scheduler
            .cancel_for_exception(error.clone().into_bytes(), self.state);
        self.failure = Some(error);
    }
    /// The strategy for an object only the source holds: a download, unless
    /// `--case-conflict` finds a file whose name differs only by case, which
    /// either exists or is being downloaded
    /// (`CaseConflictSync`).
    fn source_only(&mut self, listed: &ListedObject<'_>) -> Selection {
        let SourceOnly::CaseConflict(conflict) = self.strategies.source_only else {
            return Selection::QUEUE;
        };
        let relative = listed
            .key
            .get(self.request.prefix.len()..)
            .unwrap_or_default();
        let name = relative.to_lowercase();
        let root = transfer::normalize_local_directory_root(&self.request.local_root);
        let destination = transfer::build_recursive_destination_path(&root, relative);
        if self.scheduler.holds_case_name(&name) || destination.exists() {
            let message = |text: &str| {
                [
                    text.as_bytes(),
                    b" ",
                    self.request.bucket.as_bytes(),
                    b"/",
                    listed.key.as_bytes(),
                    b" -> ",
                    destination.as_os_str().as_encoded_bytes(),
                ]
                .concat()
            };
            let (warning, downloads) = match conflict {
                CaseConflict::Skip => (message("warning: Skipping"), false),
                CaseConflict::Warn => (message("warning: Downloading"), true),
                CaseConflict::Error => {
                    let error =
                        [message("Failed to download"), CASE_CONFLICT_ERROR.into()].concat();
                    self.raise(String::from_utf8_lossy(&error).into_owned());
                    return Selection::Stop;
                }
            };
            let suffix = if downloads {
                CASE_CONFLICT_WARNING
            } else {
                CASE_CONFLICT_SKIP
            };
            if let Err(error) = self
                .scheduler
                .print_diagnostic([warning, suffix.into()].concat())
            {
                self.scheduler.record_fatal(error);
                return Selection::Stop;
            }
            if !downloads {
                return Selection::Skip;
            }
        }
        self.scheduler.claim_case_name(&name);
        Selection::Queue {
            case_name: Some(name),
        }
    }
}
/// The end of upstream's case conflict messages, after the object and its
/// destination (`CaseConflictSync`).
const CASE_CONFLICT_SKIP: &str =
    " because a file whose name differs only by case either exists or is being downloaded.";
const CASE_CONFLICT_ERROR: &str = CASE_CONFLICT_SKIP;
const CASE_CONFLICT_WARNING: &str = concat!(
    " despite a file whose name differs only by case either existing or being ",
    "downloaded. This behavior is not defined on case-insensitive filesystems and ",
    "may result in overwriting existing files or race conditions between concurrent ",
    "downloads. For more information, see ",
    "https://docs.aws.amazon.com/cli/latest/topic/s3-case-insensitivity.html."
);
impl Select for SyncDownload<'_> {
    fn select(&mut self, listed: &ListedObject<'_>, queue: &SubmitQueue) -> Selection {
        let source = comparator::Entry {
            name: listed
                .key
                .as_bytes()
                .get(self.request.prefix.len()..)
                .unwrap_or_default(),
            size: listed.size,
            modified: listed_modified(listed.modified),
        };
        let mut remover = FileRemover {
            request: self.request,
            queue,
        };
        match self.comparator.pair(&source, &mut remover) {
            Ok(Pairing::Both(true)) => Selection::QUEUE,
            Ok(Pairing::Both(false)) => Selection::Skip,
            Ok(Pairing::SourceOnly) => self.source_only(listed),
            Ok(Pairing::Stopped) => Selection::Stop,
            Err(error) => {
                self.raise(error);
                Selection::Stop
            }
        }
    }
    fn listed(&mut self, result: &ListResult, queue: &SubmitQueue) {
        if self.failure.is_some()
            || self.state.is_requested()
            || queue.is_failed()
            || !recursive::list_completed(result)
        {
            return;
        }
        let mut remover = FileRemover {
            request: self.request,
            queue,
        };
        if let Err(error) = self.comparator.finish(&mut remover) {
            self.raise(error);
        }
    }
}
struct FileRemover<'a> {
    request: &'a recursive::TransferRequest,
    queue: &'a SubmitQueue,
}
impl comparator::Remover<comparator::LocalName> for FileRemover<'_> {
    fn remove(&mut self, entry: comparator::Entry<comparator::LocalName>) -> ControlFlow<()> {
        let relative = entry.name.into_relative_path();
        let path = transfer::build_recursive_source_path(&self.request.local_root, &relative);
        match self.queue.delete_local_file(path) {
            Ok(()) => ControlFlow::Continue(()),
            Err(_) => ControlFlow::Break(()),
        }
    }
}
fn produce_sync_walk(
    request: &recursive::TransferRequest,
    runtime: &BucketRuntime,
    scheduler: &Arc<Scheduler>,
    source: LocalRoot,
    strategies: crate::sync::Strategies,
) -> ProducerResult {
    let state = interrupt::process_state();
    std::thread::scope(|scope| {
        let destination = RemoteDestination::new(scope, request, runtime, state);
        let mut comparator = Comparator::new(strategies, LocalSide::Source, destination);
        let walked =
            producer::produce_sync_walk(request, scheduler, source, state, &mut comparator);
        let ended = comparator.into_destination().close();
        let mut list_stats = None;
        let listing = match ended {
            Some(ListingEnd::Listed(result, stats)) => {
                list_stats = request.collect_stats.then_some(*stats);
                Some(result)
            }
            Some(ListingEnd::Unstarted(error)) => {
                return ProducerResult {
                    outcome: recursive::ProducerOutcome::SubmitFailed(error),
                    ..ProducerResult::default()
                };
            }
            None => None,
        };
        let outcome = match (walked, listing) {
            (Ok(outcome), _) => outcome,
            (Err(ListingFailed), Some(listing)) => {
                if let Some(exception) = recursive::listing_exception(request, &listing) {
                    scheduler.cancel_for_exception(exception, state);
                }
                recursive::ProducerOutcome::ListCompleted(listing)
            }
            (Err(ListingFailed), None) => {
                recursive::ProducerOutcome::SubmitFailed("ListingNotEnded".into())
            }
        };
        ProducerResult {
            outcome,
            submit_queue_failed: false,
            list_stats,
        }
    })
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct ListingFailed;
struct RemoteDestination<'scope, 'env> {
    scope: &'scope std::thread::Scope<'scope, 'env>,
    request: &'env recursive::TransferRequest,
    runtime: &'env BucketRuntime,
    state: &'env interrupt::State,
    lister: Option<Lister<'scope>>,
    ended: Option<ListingEnd>,
}
#[derive(Debug)]
enum ListingEnd {
    Listed(Box<ListResult>, Box<ListStats>),
    Unstarted(String),
}
impl ListingEnd {
    fn pulled(&self) -> Result<Option<comparator::Entry<Vec<u8>>>, ListingFailed> {
        let completed = match self {
            Self::Listed(result, _) => recursive::list_completed(result),
            Self::Unstarted(_) => false,
        };
        if completed {
            Ok(None)
        } else {
            Err(ListingFailed)
        }
    }
}
struct Lister<'scope> {
    entries: mpsc::Receiver<ListEntry>,
    thread: std::thread::ScopedJoinHandle<'scope, (ListResult, ListStats)>,
}
impl Lister<'_> {
    fn join(self) -> ListingEnd {
        drop(self.entries);
        let (result, stats) = self
            .thread
            .join()
            .unwrap_or_else(|panic| std::panic::resume_unwind(panic));
        ListingEnd::Listed(Box::new(result), Box::new(stats))
    }
}
impl std::fmt::Debug for RemoteDestination<'_, '_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RemoteDestination")
            .field("bucket", &self.request.bucket)
            .field("listing", &self.lister.is_some())
            .field("ended", &self.ended.is_some())
            .finish()
    }
}
impl<'scope, 'env> RemoteDestination<'scope, 'env> {
    fn new(
        scope: &'scope std::thread::Scope<'scope, 'env>,
        request: &'env recursive::TransferRequest,
        runtime: &'env BucketRuntime,
        state: &'env interrupt::State,
    ) -> Self {
        Self {
            scope,
            request,
            runtime,
            state,
            lister: None,
            ended: None,
        }
    }
    fn start(&mut self) {
        let capacity = crate::constants::SYNC_DESTINATION_QUEUE_CAPACITY;
        let (sender, entries) = mpsc::sync_channel(capacity);
        let (request, runtime, state) = (self.request, self.runtime, self.state);
        let list = move || list_destination(request, runtime, state, &sender);
        match cli_core::thread::builder()
            .name("s3-sync-list".into())
            .spawn_scoped(self.scope, list)
        {
            Ok(thread) => self.lister = Some(Lister { entries, thread }),
            Err(error) => {
                let name = SetupError::spawn(&error).name().to_owned();
                self.ended = Some(ListingEnd::Unstarted(name));
            }
        }
    }
    fn close(mut self) -> Option<ListingEnd> {
        if let Some(lister) = self.lister.take() {
            self.ended = Some(lister.join());
        }
        self.ended
    }
}
impl comparator::Destination for RemoteDestination<'_, '_> {
    type Name = Vec<u8>;
    type Error = ListingFailed;
    fn next_entry(&mut self) -> Result<Option<comparator::Entry<Vec<u8>>>, ListingFailed> {
        if self.lister.is_none() && self.ended.is_none() {
            self.start();
        }
        let Some(lister) = &self.lister else {
            return self.ended.as_ref().map_or(Ok(None), ListingEnd::pulled);
        };
        let prefix = self.request.prefix.len();
        for entry in lister.entries.iter() {
            let mut name = entry.name;
            if entry.size == 0 && name.ends_with(b"/") {
                continue;
            }
            // An object `--include` and `--exclude` leave out is no entry at
            // all, as upstream filters the destination before its comparator.
            let filter = self
                .request
                .sync
                .as_ref()
                .map(|sync| &sync.destination_filter);
            if filter.is_some_and(|filter| !filter.includes(&name)) {
                continue;
            }
            name.drain(..prefix.min(name.len()));
            return Ok(Some(comparator::Entry {
                name,
                size: entry.size,
                modified: listed_modified(entry.date.map(|date| date.epoch_seconds)),
            }));
        }
        let Some(lister) = self.lister.take() else {
            return Ok(None);
        };
        self.ended.insert(lister.join()).pulled()
    }
}
fn list_destination(
    request: &recursive::TransferRequest,
    runtime: &BucketRuntime,
    state: &interrupt::State,
    entries: &mpsc::SyncSender<ListEntry>,
) -> (ListResult, ListStats) {
    let mut stats = ListStats::default();
    let result = runtime.list_objects(
        list_options(request),
        request.collect_stats.then_some(&mut stats),
        &mut |entry| {
            if state.is_requested() {
                return -1;
            }
            if entry.kind != crt::s3::EntryKind::Object {
                return 0;
            }
            if std::str::from_utf8(&entry.name).is_err() {
                return -1;
            }
            if entries.send(entry).is_ok() { 0 } else { -1 }
        },
        state,
    );
    (result, stats)
}
#[cfg(test)]
mod tests;
