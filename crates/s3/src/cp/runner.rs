use super::backstop::SetupError;
use super::recursive::{
    CommandReport, Completion, Finished, ProducerResult, RenderError, TransferRequest,
};
use crate::download::{DownloadLocality, SharedWriterService};
use crate::results;
use crate::scheduler::{Event, Scheduler, Sink};
use crate::transfer::Direction;
use cli_core::interrupt::{Registration, Scope, State};
use crt::s3::TransferResult;
use std::ffi::OsStr;
use std::io;
use std::path::PathBuf;
use std::sync::Arc;

pub(crate) trait TransferEnv {
    type Source;
    type Runtime;
    fn open_local_root(&self, request: &TransferRequest) -> io::Result<Option<Self::Source>>;
    fn checked_invocation_dir(&self) -> io::Result<PathBuf>;
    fn resolve_writers(
        &self,
        request: &TransferRequest,
    ) -> Result<Option<DownloadLocality>, SetupError>;
    fn create_runtime(
        &self,
        request: &TransferRequest,
        writers: Option<&DownloadLocality>,
    ) -> Result<Result<Self::Runtime, Box<TransferResult>>, SetupError>;
    fn start_service(
        &self,
        request: &TransferRequest,
        writers: Option<DownloadLocality>,
    ) -> Result<Option<Arc<SharedWriterService>>, SetupError>;
    fn scheduler(
        &self,
        request: &TransferRequest,
        cwd: PathBuf,
        runtime: Option<&Self::Runtime>,
        service: Option<&Arc<SharedWriterService>>,
        sink: Arc<dyn Sink>,
    ) -> Result<Arc<Scheduler>, SetupError>;
    fn start_finish_pool(&self, scheduler: &Scheduler, workers: usize) -> io::Result<()>;
    fn start_prepare_pool(&self, scheduler: &Scheduler, workers: usize) -> io::Result<()>;
    fn produce(
        &self,
        request: &TransferRequest,
        runtime: Option<&Self::Runtime>,
        scheduler: &Arc<Scheduler>,
        source: Option<Self::Source>,
    ) -> ProducerResult;
}

pub(crate) fn run_transfer<E: TransferEnv>(
    env: &E,
    request: &TransferRequest,
    state: &State,
    publisher: &results::Publisher,
    ignored: &str,
) -> Result<Completion, SetupError> {
    let mut scope = Scope::enter(state);
    if request.refusal.is_some() {
        warn_ignored(publisher, ignored);
    }
    let source = match env.open_local_root(request) {
        Ok(source) => source,
        Err(error) if request.direction == Direction::Upload => {
            return Ok(Completion::SourceOpenFailed(
                super::io_error_name(&error).into(),
            ));
        }
        Err(error) => return Err(SetupError::io(&error)),
    };
    let display = look_up_working_directory(env, request)?;
    let mode = ResultMode::for_display(&display);
    let sink: Arc<dyn Sink> = Arc::new(ResultSink {
        publisher: publisher.clone(),
        mode,
    });
    if request.refusal.is_some() {
        return transfer_refused(
            env,
            request,
            (&mut scope, state),
            source,
            display,
            mode,
            sink,
        );
    }
    let writers = env.resolve_writers(request)?;
    let numa_source_pool = writers
        .as_ref()
        .is_some_and(|writers| writers.source_pool.is_some());
    let runtime = match env.create_runtime(request, writers.as_ref())? {
        Ok(runtime) => runtime,
        Err(result) => return Ok(Completion::ClientFailed(result)),
    };
    // Upstream's transfer manager warns once it has built its client.
    warn_ignored(publisher, ignored);
    let service = env.start_service(request, writers)?;
    let scheduler = env.scheduler(request, display.cwd, Some(&runtime), service.as_ref(), sink)?;
    let registration = state.register(scheduler.clone());
    let produced = produce(env, request, &runtime, &scheduler, source);
    finish_submissions(&scheduler, &produced, state.is_requested(), mode);
    let mut finished = drain(
        request,
        &scheduler,
        service.as_ref(),
        produced,
        numa_source_pool,
    );
    finished.display_failure = display.failure;
    Ok(release(
        &mut scope,
        registration,
        finished,
        (scheduler, service, runtime),
    ))
}

#[derive(Debug, Default)]
struct Display {
    cwd: PathBuf,
    failure: Option<SetupError>,
}

fn look_up_working_directory<E: TransferEnv>(
    env: &E,
    request: &TransferRequest,
) -> Result<Display, SetupError> {
    if request.quiet || request.direction == Direction::Delete {
        return Ok(Display::default());
    }
    match env.checked_invocation_dir() {
        Ok(cwd) => Ok(Display { cwd, failure: None }),
        Err(error) if request.object.is_some() => Ok(Display {
            cwd: PathBuf::new(),
            failure: Some(SetupError::current_dir(&error)),
        }),
        Err(error) => Err(SetupError::current_dir(&error)),
    }
}

fn transfer_refused<E: TransferEnv>(
    env: &E,
    request: &TransferRequest,
    (scope, state): (&mut Scope<'_>, &State),
    source: Option<E::Source>,
    display: Display,
    mode: ResultMode,
    sink: Arc<dyn Sink>,
) -> Result<Completion, SetupError> {
    let scheduler = env.scheduler(request, display.cwd, None, None, sink)?;
    let registration = state.register(scheduler.clone());
    let produced = env.produce(request, None, &scheduler, source);
    finish_submissions(&scheduler, &produced, state.is_requested(), mode);
    scheduler.drain();
    let mut finished = scheduler.finished();
    finished.display_failure = display.failure;
    finished.stats = None;
    finished.producer = produced.outcome;
    finished.canceled = leave_scope_and_release(scope, registration, scheduler);
    Ok(Completion::Finished(Box::new(finished)))
}

fn produce<E: TransferEnv>(
    env: &E,
    request: &TransferRequest,
    runtime: &E::Runtime,
    scheduler: &Arc<Scheduler>,
    source: Option<E::Source>,
) -> ProducerResult {
    if let Err(error) = env.start_finish_pool(scheduler, request.finish_workers()) {
        scheduler.record_fatal(SetupError::spawn(&error));
        return ProducerResult::default();
    }
    let cpus = numa::cpu_count();
    if let Some(workers) = request.prepare_workers(cpus)
        && let Err(error) = env.start_prepare_pool(scheduler, workers)
    {
        scheduler.record_fatal(SetupError::spawn(&error));
        return ProducerResult::default();
    }
    let produced = env.produce(request, Some(runtime), scheduler, source);
    scheduler.stop_prepare_pool();
    produced
}

fn finish_submissions(
    scheduler: &Scheduler,
    produced: &ProducerResult,
    interrupted: bool,
    mode: ResultMode,
) {
    if mode == ResultMode::Render {
        scheduler.finish_submissions(produced.exhausted(interrupted));
    }
}

fn drain(
    request: &TransferRequest,
    scheduler: &Scheduler,
    service: Option<&Arc<SharedWriterService>>,
    produced: ProducerResult,
    numa_source_pool: bool,
) -> Finished {
    scheduler.drain();
    if let Some(service) = service {
        service.close_and_join();
        service.log_summary();
    }
    scheduler.close_write_pool();
    Finished {
        producer: produced.outcome,
        list_stats: produced.list_stats,
        numa_source_pool,
        crt_target_gbps: request.sizing.throughput_target_gbps,
        memory_limit_bytes: request.sizing.memory_limit_in_bytes,
        ..scheduler.finished()
    }
}

fn release(
    scope: &mut Scope<'_>,
    registration: Registration<'_>,
    mut finished: Finished,
    owners: impl Sized,
) -> Completion {
    finished.canceled = leave_scope_and_release(scope, registration, owners);
    Completion::Finished(Box::new(finished))
}

pub(crate) fn leave_scope_and_release(
    scope: &mut Scope<'_>,
    registration: Registration<'_>,
    owners: impl Sized,
) -> bool {
    let canceled = scope.leave();
    drop(registration);
    drop(owners);
    canceled
}

pub(crate) fn report_completion(
    publisher: &results::Publisher,
    source: &OsStr,
    request: &TransferRequest,
    completion: &Completion,
) -> Result<u8, RenderError> {
    let report = CommandReport::new(publisher, request.quiet);
    super::recursive::finish_transfer(report, source, request, completion)
}
pub(crate) fn warn_ignored(publisher: &results::Publisher, ignored: &str) {
    for line in ignored.lines() {
        publisher.publish(results::Event::Diagnostic(line.as_bytes().to_vec()));
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ResultMode {
    Render,
    CountOnly,
}
impl ResultMode {
    fn for_display(display: &Display) -> Self {
        if display.failure.is_some() {
            Self::CountOnly
        } else {
            Self::Render
        }
    }
}
#[derive(Debug)]
struct ResultSink {
    publisher: results::Publisher,
    mode: ResultMode,
}
impl Sink for ResultSink {
    fn emit(&self, event: Event) -> Result<(), String> {
        if self.mode == ResultMode::CountOnly {
            return Ok(());
        }
        let text = event.text.trim_ascii_end().to_vec();
        self.publisher.publish(results::Event::Diagnostic(text));
        Ok(())
    }
    fn publish(&self, event: results::Event, _quiet: bool) -> Result<(), String> {
        let counted = matches!(
            event,
            results::Event::Queued { .. } | results::Event::FinalTotal(_)
        );
        if counted || self.mode == ResultMode::Render {
            self.publisher.publish(event);
        }
        Ok(())
    }
    fn progress(&self, bytes: u64) {
        self.publisher.add_progress(bytes);
    }
    fn wants_progress(&self) -> bool {
        self.publisher.wants_progress()
    }
}

#[cfg(test)]
mod tests;
