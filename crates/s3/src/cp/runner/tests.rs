#![allow(
    clippy::expect_used,
    clippy::panic,
    reason = "runner fixtures fail at the unexpected render error or completion"
)]
use super::*;
use crate::cp::recursive::{ProducerOutcome, SingleObject};
use crate::download::WriteError;
use crate::results::{Mode, PrinterConfig, Processor};
use crate::scheduler::SubmitError;
use crate::scheduler::{Completion as Callbacks, Finalize, Job, Operations, OwnedRequest};
use cli_core::interrupt::Signal;
use crt::s3::HeadObjectResult;
use std::cell::{Cell, RefCell};
use std::path::Path;
use std::rc::Rc;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Step {
    OpenRoot,
    Cwd,
    Writers,
    Runtime,
    Service,
    Engine,
    FinishPool,
    PreparePool,
    Produce,
    Release,
}
use Step::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RuntimeFailure {
    Client,
    Setup,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Source {
    Regular,
    Special,
    Rejected(&'static str),
}

#[derive(Debug)]
struct FakeEnv<'a> {
    state: &'a State,
    steps: Rc<RefCell<Vec<Step>>>,
    signals: Rc<RefCell<Vec<(Step, Signal)>>>,
    active_at_release: Rc<RefCell<Option<u32>>>,
    finish_workers: RefCell<Vec<usize>>,
    prepare_workers: RefCell<Vec<usize>>,
    interrupt_at: Option<Step>,
    fail_at: Option<Step>,
    runtime_failure: RuntimeFailure,
    entries: usize,
    source: Source,
    interrupt_at_inspection: Option<&'static State>,
    sent: Arc<std::sync::atomic::AtomicUsize>,
    cwd_unlinked: bool,
    head: Result<HeadObjectResult, Box<TransferResult>>,
    heads: Cell<usize>,
    interrupt_at_head: bool,
    destination: Destination,
    numa_source_pool: bool,
    custom_writer: bool,
}
#[derive(Debug, Clone, Copy, Default)]
struct Destination {
    exists: bool,
    parent_error: Option<io::ErrorKind>,
    interrupt: Option<&'static State>,
}
impl<'a> FakeEnv<'a> {
    fn new(state: &'a State) -> Self {
        Self {
            state,
            steps: Rc::default(),
            signals: Rc::default(),
            active_at_release: Rc::default(),
            finish_workers: RefCell::default(),
            prepare_workers: RefCell::default(),
            interrupt_at: None,
            fail_at: None,
            runtime_failure: RuntimeFailure::Client,
            entries: 2,
            source: Source::Regular,
            interrupt_at_inspection: None,
            sent: Arc::default(),
            cwd_unlinked: false,
            head: Ok(head(Some(5))),
            heads: Cell::new(0),
            interrupt_at_head: false,
            destination: Destination::default(),
            numa_source_pool: false,
            custom_writer: false,
        }
    }
    fn sent(&self) -> usize {
        self.sent.load(std::sync::atomic::Ordering::Relaxed)
    }
    fn enter(&self, step: Step) -> bool {
        self.steps.borrow_mut().push(step);
        if self.interrupt_at == Some(step) {
            self.signals.borrow_mut().push((step, deliver(self.state)));
        }
        self.fail_at == Some(step)
    }
    fn steps(&self) -> Vec<Step> {
        self.steps.borrow().clone()
    }
}
fn deliver(state: &State) -> Signal {
    let signal = state.record_interrupt();
    if signal == Signal::Canceled {
        state.request();
    }
    signal
}
#[derive(Debug)]
struct FakeRuntime<'a> {
    state: &'a State,
    steps: Rc<RefCell<Vec<Step>>>,
    signals: Rc<RefCell<Vec<(Step, Signal)>>>,
    active_at_release: Rc<RefCell<Option<u32>>>,
    interrupt: bool,
}
impl Drop for FakeRuntime<'_> {
    fn drop(&mut self) {
        self.steps.borrow_mut().push(Release);
        *self.active_at_release.borrow_mut() = Some(self.state.active_count());
        if self.interrupt {
            self.signals
                .borrow_mut()
                .push((Release, deliver(self.state)));
        }
    }
}
impl<'a> TransferEnv for FakeEnv<'a> {
    type Source = ();
    type Runtime = FakeRuntime<'a>;
    fn open_local_root(&self, request: &TransferRequest) -> io::Result<Option<()>> {
        if self.enter(OpenRoot) {
            return Err(io::Error::from(io::ErrorKind::PermissionDenied));
        }
        Ok((request.direction == Direction::Upload).then_some(()))
    }
    fn checked_invocation_dir(&self) -> io::Result<PathBuf> {
        if self.enter(Cwd) || self.cwd_unlinked {
            return Err(io::Error::from(io::ErrorKind::NotFound));
        }
        Ok(native_cwd())
    }
    fn resolve_writers(
        &self,
        request: &TransferRequest,
    ) -> Result<Option<DownloadLocality>, SetupError> {
        if self.enter(Writers) {
            return Err(SetupError::write(&WriteError::Numa(
                "NumaUnavailable".into(),
            )));
        }
        Ok(
            (request.direction == Direction::Download).then(|| DownloadLocality {
                source_pool: self.numa_source_pool.then(|| vec![0]),
                ..DownloadLocality::default()
            }),
        )
    }
    fn create_runtime(
        &self,
        _: &TransferRequest,
        _: Option<&DownloadLocality>,
    ) -> Result<Result<FakeRuntime<'a>, Box<TransferResult>>, SetupError> {
        if self.enter(Runtime) {
            return match self.runtime_failure {
                RuntimeFailure::Client => Ok(Err(Box::new(TransferResult {
                    error_code: 34,
                    crt_name: crt::s3::BoundedText::new("AWS_ERROR_INVALID_ARGUMENT"),
                    crt_message: crt::s3::BoundedText::new(
                        "An invalid argument was passed to a function.",
                    ),
                    ..Default::default()
                }))),
                RuntimeFailure::Setup => Err(SetupError::spawn(&io::Error::from(
                    io::ErrorKind::OutOfMemory,
                ))),
            };
        }
        Ok(Ok(FakeRuntime {
            state: self.state,
            steps: Rc::clone(&self.steps),
            signals: Rc::clone(&self.signals),
            active_at_release: Rc::clone(&self.active_at_release),
            interrupt: self.interrupt_at == Some(Release),
        }))
    }
    fn start_service(
        &self,
        _: &TransferRequest,
        _: Option<DownloadLocality>,
    ) -> Result<Option<Arc<SharedWriterService>>, SetupError> {
        self.enter(Service);
        Ok(None)
    }
    fn scheduler(
        &self,
        request: &TransferRequest,
        cwd: PathBuf,
        _: Option<&FakeRuntime<'a>>,
        _: Option<&Arc<SharedWriterService>>,
        sink: Arc<dyn Sink>,
    ) -> Result<Arc<Scheduler>, SetupError> {
        self.enter(Engine);
        let operations = SourceOperations {
            source: self.source,
            interrupt: self.interrupt_at_inspection,
            sent: Arc::clone(&self.sent),
            destination: self.destination,
            custom_writer: self.custom_writer,
        };
        Ok(Scheduler::new(
            request.clone(),
            cwd,
            Arc::new(operations),
            sink,
        ))
    }
    fn start_finish_pool(&self, scheduler: &Scheduler, workers: usize) -> io::Result<()> {
        self.finish_workers.borrow_mut().push(workers);
        if self.enter(FinishPool) {
            return Err(io::Error::from(io::ErrorKind::OutOfMemory));
        }
        scheduler.start_finish_pool(workers)
    }
    fn start_prepare_pool(&self, scheduler: &Scheduler, workers: usize) -> io::Result<()> {
        self.prepare_workers.borrow_mut().push(workers);
        if self.enter(PreparePool) {
            return Err(io::Error::from(io::ErrorKind::OutOfMemory));
        }
        scheduler.start_prepare_pool(workers)
    }
    fn produce(
        &self,
        request: &TransferRequest,
        _: Option<&FakeRuntime<'a>>,
        scheduler: &Arc<Scheduler>,
        _: Option<()>,
    ) -> ProducerResult {
        self.enter(Produce);
        if let Some(object) = &request.object {
            let outcome = if request.direction == Direction::Download {
                crate::cp::producer::produce_download_object(scheduler, object, || {
                    self.heads.set(self.heads.get() + 1);
                    if self.interrupt_at_head {
                        self.signals
                            .borrow_mut()
                            .push((Produce, deliver(self.state)));
                    }
                    self.head.clone()
                })
            } else {
                crate::cp::producer::produce_object(scheduler, object)
            };
            return ProducerResult {
                outcome,
                ..ProducerResult::default()
            };
        }
        for index in 0..self.entries {
            let name = format!("object{index}");
            let named = if request.direction == Direction::Upload {
                scheduler.handle_upload_entry(Path::new(&name), None)
            } else {
                scheduler.handle_download_entry(
                    &format!("{}{name}", String::from_utf8_lossy(&request.prefix)),
                    5,
                    None,
                )
            };
            named.expect("entry submitted");
        }
        let outcome = if request.direction == Direction::Upload {
            ProducerOutcome::WalkCompleted
        } else {
            ProducerOutcome::ListCompleted(Box::default())
        };
        ProducerResult {
            outcome,
            ..ProducerResult::default()
        }
    }
}

#[derive(Debug)]
struct SourceOperations {
    source: Source,
    interrupt: Option<&'static State>,
    sent: Arc<std::sync::atomic::AtomicUsize>,
    destination: Destination,
    custom_writer: bool,
}
impl Operations for SourceOperations {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        self.destination
            .parent_error
            .map_or(Ok(()), |kind| Err(io::Error::from(kind)))
    }
    fn exists(&self, _: &Path) -> bool {
        if let Some(state) = self.destination.interrupt {
            assert_eq!(deliver(state), Signal::Canceled);
        }
        self.destination.exists
    }
    fn inspect_source(&self, _: &Path) -> crate::transfer::SourceInspection {
        if let Some(state) = self.interrupt {
            assert_eq!(deliver(state), Signal::Canceled);
        }
        match self.source {
            Source::Special => {
                crate::transfer::SourceInspection::Skipped(crate::transfer::SourceSkip::Special)
            }
            Source::Regular | Source::Rejected(_) => crate::transfer::SourceInspection::Size(5),
        }
    }
    fn submit(
        &self,
        job: Arc<Job>,
        completion: Arc<dyn Callbacks>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        if let Source::Rejected(exception) = self.source {
            return Err(SubmitError::Local(exception.into()));
        }
        job.custom_writer
            .store(self.custom_writer, std::sync::atomic::Ordering::Release);
        self.sent.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        ImmediateOperations.submit(job, completion)
    }
    fn finalize(&self, _: &Job, _: &TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}

#[derive(Debug)]
struct ImmediateOperations;
#[derive(Debug)]
struct ImmediateRequest(Arc<dyn Callbacks>);
impl OwnedRequest for ImmediateRequest {
    fn cancel(&self) {}
}
impl Drop for ImmediateRequest {
    fn drop(&mut self) {
        self.0.shutdown();
    }
}
impl Operations for ImmediateOperations {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, _: &Path) -> crate::transfer::SourceInspection {
        crate::transfer::SourceInspection::Size(0)
    }
    fn submit(
        &self,
        _: Arc<Job>,
        completion: Arc<dyn Callbacks>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        completion.finish(TransferResult::default());
        Ok(Box::new(ImmediateRequest(completion)))
    }
    fn finalize(&self, _: &Job, _: &TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}

fn request(direction: Direction, quiet: bool) -> TransferRequest {
    TransferRequest {
        direction,
        bucket: "bucket".into(),
        prefix: "prefix/".into(),
        local_root: "/work/root/".into(),
        runtime: Default::default(),
        quiet,
        dryrun: false,
        no_overwrite: false,
        glacier: crate::transfer::GlacierPolicy::Warn,
        content_types: None,
        refusal: None,
        page_size: 0,
        max_in_flight: 4,
        collect_stats: false,
        prefetch: false,
        sizing: Default::default(),
        download: None,
        object: None,
        filter: Default::default(),
        headers: Default::default(),
        checksums: Default::default(),
        delete: Default::default(),
        sources: Default::default(),
        sync: None,
        listing_user_agent: None,
        links: Default::default(),
    }
}
const IGNORED: &str = "warning: ignored setting\n";
const CANCEL: &str = "cancelled: ctrl-c received\n";

#[derive(Debug, PartialEq)]
enum Reported {
    Status(u8),
    Setup(String),
    Fatal(String),
    Client(String),
}
#[derive(Debug)]
struct Ran {
    reported: Reported,
    stdout: String,
    stderr: String,
    queued: u64,
    final_total: Option<u64>,
    bytes: u64,
}
fn run(env: &FakeEnv<'_>, request: &TransferRequest) -> Ran {
    let printer = (!request.quiet).then_some(PrinterConfig {
        mode: Mode::NoProgress,
        ..Default::default()
    });
    run_printed(env, request, printer)
}
fn run_printed(
    env: &FakeEnv<'_>,
    request: &TransferRequest,
    printer: Option<PrinterConfig>,
) -> Ran {
    assert_eq!(request.quiet, printer.is_none());
    let mut processor = Processor::with_diagnostics(printer);
    let publisher = processor.publisher();
    let reported = match run_transfer(env, request, env.state, &publisher, IGNORED) {
        Err(error) => Reported::Setup(error.name().into()),
        Ok(completion) => {
            match report_completion(&publisher, OsStr::new("source"), request, &completion) {
                Ok(status) => Reported::Status(status),
                Err(RenderError::Fatal(name)) => Reported::Fatal(name),
                Err(error @ RenderError::ClientFailed(_)) => Reported::Client(error.to_string()),
                Err(RenderError::Io(error)) => panic!("render failed: {error}"),
            }
        }
    };
    publisher.close();
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    processor
        .run(&mut stdout, &mut stderr)
        .expect("processor output");
    Ran {
        reported,
        stdout: String::from_utf8(stdout).expect("stdout"),
        stderr: String::from_utf8(stderr).expect("stderr"),
        queued: processor.recorder.expected_files_transferred,
        final_total: processor.recorder.final_expected_files_transferred,
        bytes: processor.recorder.expected_bytes_transferred,
    }
}
const DIRECTIONS: [Direction; 2] = [Direction::Upload, Direction::Download];
fn native_cwd() -> PathBuf {
    PathBuf::from(if cfg!(windows) { r"C:\work" } else { "/work" })
}
fn local() -> PathBuf {
    native_cwd().join("local.txt")
}
fn single_upload(quiet: bool) -> TransferRequest {
    TransferRequest {
        object: Some(SingleObject {
            key: b"key".to_vec(),
            local_path: local(),
            local: Default::default(),
            remote: None,
        }),
        ..request(Direction::Upload, quiet)
    }
}
fn shapes(quiet: bool) -> [TransferRequest; 3] {
    [
        request(Direction::Upload, quiet),
        request(Direction::Download, quiet),
        single_upload(quiet),
    ]
}
fn local_display() -> String {
    crate::transfer::display_local_path(&native_cwd(), &local())
        .to_string_lossy()
        .into_owned()
}

#[test]
fn every_shape_runs_the_steps_in_order() {
    for request in shapes(false) {
        let state = State::new();
        let env = FakeEnv::new(&state);
        let ran = run(&env, &request);
        assert_eq!(
            env.steps(),
            [
                OpenRoot, Cwd, Writers, Runtime, Service, Engine, FinishPool, Produce, Release
            ]
        );
        let (named, workers) = if request.object.is_some() {
            (1, 1)
        } else {
            (2, crate::constants::FINISH_WORKERS_DEFAULT)
        };
        assert_eq!(*env.finish_workers.borrow(), [workers]);
        assert_eq!(ran.reported, Reported::Status(0));
        assert_eq!(ran.stderr, IGNORED);
        assert_eq!(ran.stdout.lines().count(), named, "{}", ran.stdout);
        assert_eq!(
            (ran.queued, ran.final_total),
            (named as u64, Some(named as u64))
        );
        assert_eq!(*env.active_at_release.borrow(), Some(0));
    }
}

#[test]
fn a_client_that_cannot_be_built_fails_every_shape_through_the_general_handler() {
    for quiet in [false, true] {
        for request in shapes(quiet) {
            let state = State::new();
            let env = FakeEnv {
                fail_at: Some(Runtime),
                ..FakeEnv::new(&state)
            };
            let ran = run(&env, &request);
            assert_eq!(
                ran.reported,
                Reported::Client(
                    "34 (AWS_ERROR_INVALID_ARGUMENT): An invalid argument was passed to a \
                    function."
                        .into()
                )
            );
            assert_eq!((ran.stdout.as_str(), ran.stderr.as_str()), ("", ""));
            assert_eq!(env.steps().last(), Some(&Runtime));
            assert_eq!((ran.queued, ran.final_total), (0, None));
        }
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "keep the setup-failure and Ctrl-C matrix in one table"
)]
fn a_ctrl_c_during_setup_yields_to_a_setup_failure_only() {
    for request in shapes(false) {
        for fail_at in [None, Some(Writers), Some(Runtime)] {
            let state = State::new();
            assert_eq!(deliver(&state), Signal::Terminate);
            assert!(!state.is_requested());
            let env = FakeEnv {
                interrupt_at: Some(Cwd),
                fail_at,
                ..FakeEnv::new(&state)
            };
            let ran = run(&env, &request);
            assert_eq!(*env.signals.borrow(), [(Cwd, Signal::Canceled)]);
            assert!(state.is_requested());
            assert_eq!(ran.stdout, "");
            assert_eq!((ran.queued, ran.final_total), (0, None));
            assert_eq!(env.sent(), 0);
            match fail_at {
                None => {
                    assert_eq!(ran.reported, Reported::Status(1));
                    assert_eq!(ran.stderr, format!("{IGNORED}{CANCEL}"));
                }
                Some(Writers) => {
                    assert_eq!(ran.reported, Reported::Setup("NumaUnavailable".into()));
                    assert_eq!(ran.stderr, "");
                    assert_eq!(env.steps().last(), Some(&Writers));
                }
                Some(_) => {
                    assert!(matches!(ran.reported, Reported::Client(_)));
                    assert_eq!(ran.stderr, "");
                }
            }
        }
    }
}

#[test]
fn a_runtime_setup_error_ends_the_transfer_ahead_of_a_ctrl_c() {
    for quiet in [false, true] {
        for request in shapes(quiet) {
            for interrupted in [false, true] {
                let state = State::new();
                let env = FakeEnv {
                    fail_at: Some(Runtime),
                    runtime_failure: RuntimeFailure::Setup,
                    interrupt_at: interrupted.then_some(Runtime),
                    ..FakeEnv::new(&state)
                };
                let ran = run(&env, &request);
                assert_eq!(ran.reported, Reported::Setup("Out of memory".into()));
                assert_eq!((ran.stdout.as_str(), ran.stderr.as_str()), ("", ""));
                assert_eq!((ran.queued, ran.final_total), (0, None));
                assert_eq!(state.is_requested(), interrupted);
            }
        }
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "keep the output-mode and Ctrl-C matrix in one table"
)]
fn a_ctrl_c_outranks_a_finish_pool_that_could_not_start() {
    for quiet in [false, true] {
        for request in shapes(quiet) {
            for interrupted in [false, true] {
                let state = State::new();
                let env = FakeEnv {
                    fail_at: Some(FinishPool),
                    interrupt_at: interrupted.then_some(FinishPool),
                    ..FakeEnv::new(&state)
                };
                let ran = run(&env, &request);
                assert!(!env.steps().contains(&Produce));
                assert_eq!(ran.stdout, "");
                assert_eq!(ran.queued, 0);
                let warning = IGNORED;
                if interrupted {
                    assert_eq!(ran.reported, Reported::Status(1));
                    let cancel = if quiet { "" } else { CANCEL };
                    assert_eq!(ran.stderr, format!("{warning}{cancel}"));
                    assert_eq!(ran.final_total, None);
                } else {
                    assert_eq!(ran.reported, Reported::Fatal("Out of memory".into()));
                    assert_eq!(ran.stderr, warning);
                    assert_eq!(ran.final_total, Some(0));
                }
            }
        }
    }
}

#[test]
fn a_recursive_transfer_needs_its_working_directory_only_to_print() {
    for direction in DIRECTIONS {
        let state = State::new();
        let env = FakeEnv {
            fail_at: Some(Cwd),
            ..FakeEnv::new(&state)
        };
        let ran = run(&env, &request(direction, false));
        assert_eq!(
            ran.reported,
            Reported::Setup("Current directory was removed".into())
        );
        assert_eq!(env.steps(), [OpenRoot, Cwd]);
        assert_eq!((ran.stdout.as_str(), ran.stderr.as_str()), ("", ""));

        let quiet = run(&env, &request(direction, true));
        assert_eq!(quiet.reported, Reported::Status(0));
        assert_eq!(env.steps().iter().filter(|step| **step == Cwd).count(), 1);
        assert_eq!(quiet.stderr, IGNORED);
    }
}

#[test]
fn a_finished_transfer_reports_the_sizings_target_and_pool() {
    let state = State::new();
    let env = FakeEnv::new(&state);
    let mut request = request(Direction::Download, true);
    request.runtime.throughput_target_gbps = 10.0;
    request.sizing = crate::config::ClientSizing {
        throughput_target_gbps: 217.6,
        memory_limit_in_bytes: 4 << 30,
        ..Default::default()
    };
    let mut processor = Processor::with_diagnostics(None);
    let publisher = processor.publisher();
    let completion = run_transfer(&env, &request, &state, &publisher, IGNORED);
    publisher.close();
    processor
        .run(&mut Vec::new(), &mut Vec::new())
        .expect("processor output");
    let Ok(Completion::Finished(finished)) = completion else {
        panic!("a finished transfer: {completion:?}");
    };
    assert_eq!(
        (finished.crt_target_gbps, finished.memory_limit_bytes),
        (217.6, 4 << 30)
    );
}

#[test]
fn a_refused_upload_warns_first_and_builds_no_client() {
    let state = State::new();
    let env = FakeEnv {
        fail_at: Some(OpenRoot),
        ..FakeEnv::new(&state)
    };
    let refused = TransferRequest {
        refusal: Some("refused".into()),
        collect_stats: true,
        ..request(Direction::Upload, false)
    };
    let ran = run(&env, &refused);
    assert_eq!(ran.reported, Reported::Status(1));
    assert_eq!(
        ran.stderr,
        format!(
            "{IGNORED}error: unable to open recursive upload source source: Permission denied\n"
        )
    );
    let env = FakeEnv::new(&state);
    let ran = run(&env, &refused);
    assert_eq!(
        env.steps(),
        [OpenRoot, Cwd, Engine, Produce],
        "no client, service, or finish pool"
    );
    assert_eq!(ran.reported, Reported::Status(0));
    assert_eq!(ran.stderr, IGNORED);
}

#[test]
fn a_ctrl_c_during_the_runtimes_release_terminates_the_command() {
    #[derive(Debug, Default)]
    struct Hook(std::sync::atomic::AtomicUsize);
    impl cli_core::InterruptHook for Hook {
        fn cancel(&self) {
            self.0.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        }
    }
    struct Owner<'a>(&'a State, &'a RefCell<Option<Signal>>);
    impl Drop for Owner<'_> {
        fn drop(&mut self) {
            *self.1.borrow_mut() = Some(deliver(self.0));
        }
    }
    for interrupted_first in [false, true] {
        let state = State::new();
        let hook = Arc::new(Hook::default());
        let mut scope = Scope::enter(&state);
        let registration = state.register(hook.clone());
        if interrupted_first {
            assert_eq!(deliver(&state), Signal::Canceled);
        }
        let delivered = RefCell::new(None);
        let canceled = leave_scope_and_release(&mut scope, registration, Owner(&state, &delivered));
        assert_eq!(canceled, interrupted_first);
        assert_eq!(*delivered.borrow(), Some(Signal::Terminate));
        state.request();
        assert_eq!(
            hook.0.load(std::sync::atomic::Ordering::Relaxed),
            usize::from(interrupted_first)
        );
    }
    for request in shapes(false) {
        let state = State::new();
        let env = FakeEnv {
            interrupt_at: Some(Release),
            ..FakeEnv::new(&state)
        };
        let ran = run(&env, &request);
        assert_eq!(*env.signals.borrow(), [(Release, Signal::Terminate)]);
        assert_eq!(ran.reported, Reported::Status(0));
    }
}

#[derive(Debug, Default)]
struct UnpublishableQueue(std::sync::Mutex<Vec<results::Event>>);
impl Sink for UnpublishableQueue {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: results::Event, _: bool) -> Result<(), String> {
        if matches!(event, results::Event::Queued { .. }) {
            return Err("Out of memory".into());
        }
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push(event);
        Ok(())
    }
}
#[derive(Debug, Default)]
struct CountingOperations(std::sync::atomic::AtomicUsize);
impl Operations for CountingOperations {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, _: &Path) -> crate::transfer::SourceInspection {
        crate::transfer::SourceInspection::Size(0)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        completion: Arc<dyn Callbacks>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        self.0.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        ImmediateOperations.submit(job, completion)
    }
    fn finalize(&self, _: &Job, _: &TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}

#[test]
fn a_queued_result_that_cannot_be_published_sends_no_request() {
    for direction in DIRECTIONS {
        let operations = Arc::new(CountingOperations::default());
        let sink = Arc::new(UnpublishableQueue::default());
        let scheduler = Scheduler::new(
            request(direction, false),
            "/work".into(),
            operations.clone(),
            sink.clone(),
        );
        let named = if direction == Direction::Upload {
            scheduler.handle_upload_entry(Path::new("object"), None)
        } else {
            scheduler.handle_download_entry("prefix/object", 5, None)
        };
        assert_eq!(
            named,
            Err(crate::scheduler::Error::Output("Out of memory".into()))
        );
        if direction == Direction::Download {
            assert_eq!(
                scheduler.submit_entry(crate::scheduler::Entry {
                    key: b"prefix/unsized".to_vec(),
                    local_path: "/work/root/unsized".into(),
                    ..Default::default()
                }),
                Err(crate::scheduler::Error::Output("Out of memory".into()))
            );
        }
        scheduler.drain();
        assert_eq!(operations.0.load(std::sync::atomic::Ordering::Relaxed), 0);
        let finished = scheduler.finished();
        assert_eq!(finished.fatal.as_deref(), Some("Out of memory"));
        assert_eq!((finished.failed, finished.warned), (0, 0));
        assert!(
            sink.0
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .is_empty()
        );
        assert_recorded_error_yields_to_ctrl_c(direction, &finished);
    }
}

fn assert_recorded_error_yields_to_ctrl_c(direction: Direction, finished: &Finished) {
    for canceled in [false, true] {
        let (result, events) = finish(
            "source",
            &request(direction, false),
            &Completion::Finished(Box::new(Finished {
                canceled,
                producer: ProducerOutcome::WalkFailed("Out of memory".into()),
                ..finished.clone()
            })),
        );
        if canceled {
            assert!(matches!(result, Ok(1)));
            assert_eq!(events, [results::Event::CtrlC]);
        } else {
            assert!(matches!(result, Err(RenderError::Fatal(name)) if name == "Out of memory"));
            assert!(events.is_empty());
        }
    }
}
fn finish(
    source: &str,
    request: &TransferRequest,
    completion: &Completion,
) -> (Result<u8, RenderError>, Vec<results::Event>) {
    let processor = Processor::new(None);
    let publisher = processor.publisher();
    let status = report_completion(&publisher, OsStr::new(source), request, completion);
    (status, publisher.take_events())
}

#[derive(Debug, Default)]
struct Published(std::sync::Mutex<Vec<results::Event>>);
impl Sink for Published {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: results::Event, _: bool) -> Result<(), String> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push(event);
        Ok(())
    }
}

#[test]
fn the_recursive_final_total_follows_only_an_exhausted_producer() {
    let listing = |status| {
        ProducerOutcome::ListCompleted(Box::new(crt::s3::ListResult {
            transfer: TransferResult {
                response_status: status,
                ..Default::default()
            },
            ..Default::default()
        }))
    };
    let produced = |outcome, submit_queue_failed| ProducerResult {
        outcome,
        submit_queue_failed,
        list_stats: None,
    };
    let cases = [
        (
            produced(ProducerOutcome::WalkCompleted, false),
            false,
            Some(3),
        ),
        (produced(listing(200), false), false, Some(3)),
        (produced(listing(503), false), false, None),
        (
            produced(
                ProducerOutcome::WalkFailed("Permission denied".into()),
                false,
            ),
            false,
            None,
        ),
        (
            produced(
                ProducerOutcome::ListCompleted(Box::new(crt::s3::ListResult {
                    local_error: Some(crt::s3::ListLocalError::CrtFailure),
                    ..Default::default()
                })),
                false,
            ),
            false,
            None,
        ),
        (produced(listing(200), true), false, None),
        (produced(ProducerOutcome::WalkCompleted, false), true, None),
    ];
    for (producer, interrupted, total) in cases {
        assert_eq!(
            published_totals(&producer, interrupted),
            Vec::from_iter(total),
            "{producer:?}"
        );
    }
}
fn published_totals(producer: &ProducerResult, interrupted: bool) -> Vec<u64> {
    let sink = Arc::new(Published::default());
    let scheduler = Scheduler::new(
        request(Direction::Upload, false),
        "/work".into(),
        Arc::new(ImmediateOperations),
        sink.clone(),
    );
    for name in ["a", "b", "c"] {
        scheduler
            .handle_upload_entry(Path::new(name), None)
            .expect("queued upload");
    }
    scheduler.drain();
    finish_submissions(&scheduler, producer, interrupted, ResultMode::Render);
    sink.0
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
        .iter()
        .filter_map(|event| match event {
            results::Event::FinalTotal(total) => Some(*total),
            _ => None,
        })
        .collect()
}

fn special() -> PathBuf {
    native_cwd().join("device")
}
fn special_warning() -> String {
    format!(
        "warning: Skipping file {}. File is character special device, block special device, \
        FIFO, or socket.\n",
        special().display()
    )
}
fn single_upload_of(source: PathBuf, quiet: bool) -> TransferRequest {
    let mut request = single_upload(quiet);
    if let Some(object) = &mut request.object {
        object.local_path = source;
    }
    request
}
fn leaked_state() -> &'static State {
    Box::leak(Box::new(State::new()))
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "keep the client and source matrix in one table"
)]
fn a_single_upload_builds_its_client_before_it_warns_or_inspects_its_source() {
    let cases = [
        (Source::Special, Some(Runtime), false),
        (Source::Regular, Some(Runtime), false),
        (Source::Special, None, false),
        (Source::Special, Some(Runtime), true),
    ];
    for (source, fail_at, refused) in cases {
        let state = State::new();
        let env = FakeEnv {
            source,
            fail_at,
            ..FakeEnv::new(&state)
        };
        let request = TransferRequest {
            refusal: refused.then(|| "refused".into()),
            ..single_upload_of(special(), true)
        };
        let ran = run(&env, &request);
        assert_eq!(ran.stdout, "");
        if fail_at.is_some() && !refused {
            assert!(matches!(ran.reported, Reported::Client(_)));
            assert_eq!(ran.stderr, "");
            assert!(!env.steps().contains(&Produce));
        } else {
            assert_eq!(ran.reported, Reported::Status(2));
            assert_eq!(ran.stderr, IGNORED);
            assert_eq!(env.steps().contains(&Runtime), !refused);
        }
    }
}

#[test]
fn a_ctrl_c_after_a_single_uploads_first_check_reports_the_entry_then_the_cancellation() {
    let guess = "[Errno 13] Permission denied: '/etc/mime.types'";
    let refusal = "Path-style addressing cannot be used with S3 Accelerate";
    let failed = |message: &str| {
        format!(
            "upload failed: {} to s3://bucket/key {message}\n",
            local_display()
        )
    };
    let cases = [
        (Source::Special, None, special_warning()),
        (Source::Rejected(guess), None, failed(guess)),
        (Source::Rejected(refusal), Some(refusal), failed(refusal)),
    ];
    for (source, refused, line) in cases {
        let state = leaked_state();
        let env = FakeEnv {
            source,
            interrupt_at_inspection: Some(state),
            ..FakeEnv::new(state)
        };
        let local = if source == Source::Special {
            special()
        } else {
            local()
        };
        let request = TransferRequest {
            refusal: refused.map(Into::into),
            ..single_upload_of(local, false)
        };
        let ran = run(&env, &request);
        assert!(state.is_requested());
        assert_eq!(ran.reported, Reported::Status(1));
        assert_eq!(ran.stdout, "");
        assert_eq!(ran.stderr, format!("{IGNORED}{line}{CANCEL}"));
    }
}

#[test]
fn a_ctrl_c_before_a_refused_single_uploads_first_check_drops_the_entry() {
    let guess = "[Errno 13] Permission denied: '/etc/mime.types'";
    for (source, local) in [
        (Source::Special, special()),
        (Source::Rejected(guess), local()),
        (Source::Regular, local()),
    ] {
        let state = State::new();
        let env = FakeEnv {
            source,
            interrupt_at: Some(Cwd),
            ..FakeEnv::new(&state)
        };
        let request = TransferRequest {
            refusal: Some("refused".into()),
            ..single_upload_of(local, false)
        };
        let ran = run(&env, &request);
        assert_eq!(*env.signals.borrow(), [(Cwd, Signal::Canceled)]);
        assert_eq!(ran.reported, Reported::Status(1));
        assert_eq!(ran.stdout, "");
        assert_eq!(ran.stderr, format!("{IGNORED}{CANCEL}"));
        assert_eq!((ran.queued, ran.final_total), (0, None));
        assert_eq!(env.sent(), 0);
    }
}

#[test]
fn a_single_uploads_skipped_source_warns_by_its_absolute_path_in_every_output_mode() {
    let progress = "Completed 0 file(s) with ~0 file(s) remaining (calculating...)";
    let cleared = format!("{progress}\r{}\n", " ".repeat(progress.len()));
    let modes = [
        (results::Flags::default(), cleared.as_str()),
        (
            results::Flags {
                progress: false,
                ..Default::default()
            },
            "",
        ),
        (
            results::Flags {
                only_show_errors: true,
                ..Default::default()
            },
            "",
        ),
        (
            results::Flags {
                quiet: true,
                ..Default::default()
            },
            "",
        ),
    ];
    for (flags, stdout) in modes {
        let state = State::new();
        let env = FakeEnv {
            source: Source::Special,
            ..FakeEnv::new(&state)
        };
        let ran = run_printed(
            &env,
            &single_upload_of(special(), flags.quiet),
            flags.select(),
        );
        assert_eq!(ran.reported, Reported::Status(2));
        assert_eq!(ran.stdout, stdout);
        let warning = if flags.quiet {
            String::new()
        } else {
            special_warning()
        };
        assert_eq!(ran.stderr, format!("{IGNORED}{warning}"));
        assert_eq!((ran.queued, ran.final_total), (0, Some(0)));
    }
}

#[test]
fn a_refused_single_upload_fails_its_queued_transfer() {
    let state = State::new();
    let env = FakeEnv {
        source: Source::Rejected("refused"),
        ..FakeEnv::new(&state)
    };
    let request = TransferRequest {
        refusal: Some("refused".into()),
        ..single_upload(false)
    };
    let ran = run_printed(&env, &request, Some(PrinterConfig::default()));
    assert_eq!(ran.reported, Reported::Status(1));
    assert_eq!(ran.stdout, "");
    assert_eq!(
        ran.stderr,
        format!(
            "{IGNORED}upload failed: {} to s3://bucket/key refused\n",
            local_display()
        )
    );
    assert_eq!((ran.queued, ran.final_total, ran.bytes), (1, Some(1), 5));
    assert_eq!(env.steps(), [OpenRoot, Cwd, Engine, Produce]);
}

#[test]
fn a_quiet_single_upload_looks_up_no_working_directory() {
    let cases = [
        (Source::Rejected("refused"), true, 1),
        (Source::Special, false, 2),
    ];
    for (source, refused, status) in cases {
        let state = State::new();
        let env = FakeEnv {
            source,
            fail_at: Some(Cwd),
            ..FakeEnv::new(&state)
        };
        let request = TransferRequest {
            refusal: refused.then(|| "refused".into()),
            ..single_upload(true)
        };
        let ran = run(&env, &request);
        assert_eq!(ran.reported, Reported::Status(status));
        assert!(!env.steps().contains(&Cwd));
    }
}

#[test]
fn a_single_upload_reports_a_missing_working_directory_once_its_transfer_ran() {
    let cases = [
        (Source::Regular, Some(Runtime), false, 0, None),
        (Source::Rejected("refused"), None, true, 1, Some(1)),
        (Source::Special, None, false, 0, None),
    ];
    for (source, fail_runtime, refused, queued, final_total) in cases {
        let state = State::new();
        let env = FakeEnv {
            source,
            fail_at: fail_runtime,
            cwd_unlinked: true,
            ..FakeEnv::new(&state)
        };
        let request = TransferRequest {
            refusal: refused.then(|| "refused".into()),
            ..single_upload(false)
        };
        let ran = run(&env, &request);
        assert_eq!(ran.stdout, "");
        assert_eq!((ran.queued, ran.final_total), (queued, final_total));
        if fail_runtime.is_some() {
            assert!(matches!(ran.reported, Reported::Client(_)));
            assert_eq!(ran.stderr, "");
        } else {
            assert_eq!(
                ran.reported,
                Reported::Fatal("Current directory was removed".into())
            );
            assert_eq!(ran.stderr, IGNORED);
        }
    }
}

#[test]
fn a_single_upload_with_no_working_directory_still_submits_and_completes() {
    let state = State::new();
    let env = FakeEnv {
        fail_at: Some(Cwd),
        ..FakeEnv::new(&state)
    };
    let request = single_upload(false);
    let ran = run(&env, &request);
    assert_eq!(env.sent(), 1);
    assert_eq!((ran.queued, ran.final_total, ran.bytes), (1, Some(1), 5));
    assert_eq!((ran.stdout.as_str(), ran.stderr.as_str()), ("", IGNORED));
    assert_eq!(
        ran.reported,
        Reported::Fatal("Current directory was removed".into())
    );
}

#[test]
fn a_missing_working_directory_outranks_what_one_object_reported() {
    let finished = |producer, canceled| Finished {
        display_failure: Some(SetupError::current_dir(&io::Error::from(
            io::ErrorKind::NotFound,
        ))),
        fatal: Some("Out of memory".into()),
        producer,
        canceled,
        failed: 1,
        ..Finished::default()
    };
    let render = |finished| {
        let (status, events) = finish(
            "source",
            &single_upload(true),
            &Completion::Finished(Box::new(finished)),
        );
        assert!(events.is_empty());
        status.map_err(|error| error.to_string())
    };
    let submit_failed = || ProducerOutcome::SubmitFailed("Out of memory".into());
    for (producer, canceled, status) in [
        (
            ProducerOutcome::ObjectCompleted,
            true,
            Err("Current directory was removed"),
        ),
        (submit_failed(), false, Err("Out of memory")),
        (submit_failed(), true, Ok(1)),
    ] {
        assert_eq!(
            render(finished(producer, canceled)),
            status.map_err(str::to_owned)
        );
    }
}

fn root() -> PathBuf {
    PathBuf::from(if cfg!(windows) { r"C:\" } else { "/" })
}
#[test]
fn a_single_uploads_result_names_its_destination_as_the_operand_spells_it() {
    let state = State::new();
    let env = FakeEnv {
        source: Source::Rejected("refused"),
        ..FakeEnv::new(&state)
    };
    let request = TransferRequest {
        refusal: Some("refused".into()),
        object: Some(SingleObject {
            key: Vec::new(),
            local_path: root(),
            local: Default::default(),
            remote: Some("s3://bucket".into()),
        }),
        ..request(Direction::Upload, false)
    };
    let ran = run(&env, &request);
    assert_eq!(ran.reported, Reported::Status(1));
    // Upstream's `relative_path` joins the root's empty basename, so the
    // root one level up keeps its separator.
    let display = if cfg!(windows) { r"..\" } else { "../" };
    assert_eq!(
        ran.stderr,
        format!("{IGNORED}upload failed: {display} to s3://bucket refused\n")
    );
}

#[test]
fn a_single_upload_renders_the_shared_transfer_statistics() {
    let state = State::new();
    let env = FakeEnv::new(&state);
    let request = TransferRequest {
        collect_stats: true,
        ..single_upload(false)
    };
    let ran = run(&env, &request);
    assert_eq!(ran.reported, Reported::Status(0));
    let stats = ran.stderr.strip_prefix(IGNORED).expect("warning first");
    assert!(
        stats.starts_with(
            "zs3_transfer_stats direction=upload submitted=1 succeeded=1 failed=0 skipped=0 "
        ),
        "{stats}"
    );
    assert!(stats.ends_with(" source_pool=crt custom_writer_requests=0 recv_file_requests=0\n"));
    assert_eq!(stats.lines().count(), 1);
}

#[test]
fn one_object_gets_one_engine_slot_and_one_finish_worker() {
    let many = request(Direction::Upload, false);
    assert_eq!(
        (many.engine_window(), many.finish_workers()),
        (4, crate::constants::FINISH_WORKERS_DEFAULT)
    );
    let one = single_upload(false);
    assert_eq!(one.max_in_flight, 4);
    assert_eq!((one.engine_window(), one.finish_workers()), (1, 1));
}

fn tuning(settings: crate::config::Settings) -> Option<crate::config::DownloadTuning> {
    Some(settings.resolve_download())
}
fn explicit_writer() -> Option<crate::config::DownloadTuning> {
    tuning(crate::config::Settings {
        io_workers: Some(2),
        ..Default::default()
    })
}
fn recursive_download(download: Option<crate::config::DownloadTuning>) -> TransferRequest {
    TransferRequest {
        download,
        ..request(Direction::Download, false)
    }
}

#[test]
fn only_explicit_native_writers_of_many_objects_prepare_on_workers() {
    use crate::download::WriterMode;
    let max = crate::constants::PREPARE_WORKERS_MAX;
    assert_eq!(max, 4);
    let pooled = recursive_download(explicit_writer());
    for (cpus, window, workers) in [(0, 4, 1), (1, 4, 1), (3, 4, 3), (64, 4, 4), (64, 512, max)] {
        let request = TransferRequest {
            max_in_flight: window,
            ..pooled.clone()
        };
        assert_eq!(
            request.prepare_workers(cpus),
            Some(workers),
            "{cpus} {window}"
        );
    }
    let one_slot = TransferRequest {
        max_in_flight: 1,
        ..pooled.clone()
    };
    assert_eq!(one_slot.prepare_workers(64), Some(1));
    let crt = tuning(crate::config::Settings {
        download_writer: Some(WriterMode::Crt),
        ..Default::default()
    });
    let default = tuning(crate::config::Settings::default());
    let unpooled = [
        recursive_download(default),
        recursive_download(crt),
        recursive_download(None),
        TransferRequest {
            download: explicit_writer(),
            ..single_download(false)
        },
        TransferRequest {
            direction: Direction::Upload,
            ..pooled
        },
    ];
    for request in unpooled {
        assert_eq!(request.prepare_workers(64), None, "{request:?}");
    }
}

#[test]
fn a_download_with_explicit_native_writers_prepares_on_its_own_pool() {
    let state = State::new();
    let env = FakeEnv::new(&state);
    let ran = run(&env, &recursive_download(explicit_writer()));
    assert_eq!(
        env.steps(),
        [
            OpenRoot,
            Cwd,
            Writers,
            Runtime,
            Service,
            Engine,
            FinishPool,
            PreparePool,
            Produce,
            Release
        ]
    );
    let cpus = numa::cpu_count();
    assert_eq!(*env.prepare_workers.borrow(), [cpus.clamp(1, 4)]);
    assert_eq!(ran.reported, Reported::Status(0));
    assert_eq!(env.sent(), 2);
    assert_eq!(ran.stdout.lines().count(), 2, "{}", ran.stdout);
    assert_eq!((ran.queued, ran.final_total), (2, Some(2)));
}

#[test]
fn a_ctrl_c_outranks_a_preparation_pool_that_could_not_start() {
    for interrupted in [false, true] {
        let state = State::new();
        let env = FakeEnv {
            fail_at: Some(PreparePool),
            interrupt_at: interrupted.then_some(PreparePool),
            ..FakeEnv::new(&state)
        };
        let ran = run(&env, &recursive_download(explicit_writer()));
        assert!(!env.steps().contains(&Produce));
        assert_eq!((ran.stdout.as_str(), ran.queued, env.sent()), ("", 0, 0));
        let expected = if interrupted {
            (Reported::Status(1), format!("{IGNORED}{CANCEL}"), None)
        } else {
            (
                Reported::Fatal("Out of memory".into()),
                IGNORED.into(),
                Some(0),
            )
        };
        assert_eq!((ran.reported, ran.stderr, ran.final_total), expected);
    }
}

fn head(content_length: Option<u64>) -> HeadObjectResult {
    HeadObjectResult {
        transfer: TransferResult {
            response_status: 200,
            ..TransferResult::default()
        },
        content_length,
        last_modified_epoch_seconds: Some(946_684_801),
        ..HeadObjectResult::default()
    }
}
fn destination() -> PathBuf {
    native_cwd().join("object")
}
fn single_download(quiet: bool) -> TransferRequest {
    TransferRequest {
        object: Some(SingleObject {
            key: b"key".to_vec(),
            local_path: destination(),
            local: Default::default(),
            remote: Some("s3://bucket/key".into()),
        }),
        ..request(Direction::Download, quiet)
    }
}
fn object_display() -> String {
    format!(".{}object", std::path::MAIN_SEPARATOR)
}
fn downloaded() -> String {
    format!("download: s3://bucket/key to {}\n", object_display())
}

#[test]
fn a_single_download_heads_its_source_on_the_runner_then_transfers_it() {
    let state = State::new();
    let env = FakeEnv::new(&state);
    let ran = run(&env, &single_download(false));
    assert_eq!(
        env.steps(),
        [
            OpenRoot, Cwd, Writers, Runtime, Service, Engine, FinishPool, Produce, Release
        ]
    );
    assert_eq!(*env.finish_workers.borrow(), [1]);
    assert_eq!((env.heads.get(), env.sent()), (1, 1));
    assert_eq!(ran.reported, Reported::Status(0));
    assert_eq!(
        (ran.stdout.as_str(), ran.stderr.as_str()),
        (downloaded().as_str(), IGNORED)
    );
    assert_eq!((ran.queued, ran.final_total, ran.bytes), (1, Some(1), 5));
}

#[test]
fn a_ctrl_c_after_a_single_downloads_first_check_leaves_its_no_overwrite_skip() {
    let state = leaked_state();
    let env = FakeEnv {
        destination: Destination {
            exists: true,
            interrupt: Some(state),
            ..Destination::default()
        },
        ..FakeEnv::new(state)
    };
    let request = TransferRequest {
        no_overwrite: true,
        ..single_download(false)
    };
    let ran = run(&env, &request);
    assert!(state.is_requested());
    assert_eq!(ran.reported, Reported::Status(1));
    assert_eq!(ran.stdout, "");
    assert_eq!(ran.stderr, format!("{IGNORED}{CANCEL}"));
    assert_eq!((ran.queued, ran.final_total), (0, None));
    assert_eq!((env.heads.get(), env.sent()), (1, 0));
    assert_eq!(env.steps().last(), Some(&Release));
}

#[test]
fn a_single_downloads_parent_failure_precedes_a_later_cancellation() {
    for interrupted in [false, true] {
        let state = leaked_state();
        let env = FakeEnv {
            destination: Destination {
                parent_error: Some(io::ErrorKind::NotADirectory),
                interrupt: interrupted.then_some(state),
                ..Destination::default()
            },
            ..FakeEnv::new(state)
        };
        let request = TransferRequest {
            no_overwrite: true,
            ..single_download(false)
        };
        let ran = run(&env, &request);
        assert_eq!(state.is_requested(), interrupted);
        assert_eq!(ran.reported, Reported::Status(1));
        assert_eq!(ran.stdout, "");
        let cancel = if interrupted { CANCEL } else { "" };
        assert_eq!(
            ran.stderr,
            format!(
                "{IGNORED}error: unable to create parent directory for {}: \
                 Not a directory\n{cancel}",
                destination().display()
            )
        );
        assert_eq!((ran.queued, ran.final_total), (1, Some(1)));
        assert_eq!(env.sent(), 0);
    }
}

#[test]
fn a_single_download_with_no_working_directory_still_heads_and_gets() {
    let state = State::new();
    let env = FakeEnv {
        cwd_unlinked: true,
        ..FakeEnv::new(&state)
    };
    let ran = run(&env, &single_download(false));
    assert_eq!(
        ran.reported,
        Reported::Fatal("Current directory was removed".into())
    );
    assert_eq!((ran.stdout.as_str(), ran.stderr.as_str()), ("", IGNORED));
    assert_eq!((ran.queued, ran.final_total), (1, Some(1)));
    assert_eq!((env.heads.get(), env.sent()), (1, 1));
    assert_eq!(env.steps().last(), Some(&Release));
}

#[test]
fn a_single_downloads_head_outcomes_end_it_before_any_transfer() {
    let missing = TransferResult {
        error_code: 14_361,
        response_status: 404,
        service_error: crt::s3::ServiceError {
            operation: crt::s3::BoundedText::new("HeadObject"),
            ..crt::s3::ServiceError::default()
        },
        ..TransferResult::default()
    };
    let fatal = "fatal error: An error occurred (404) when calling the HeadObject operation: \
                 Key \"key\" does not exist\n";
    let canceled = TransferResult {
        error_code: crt::s3::CANCELED_ERROR_CODE,
        canceled_by_interrupt: true,
        ..TransferResult::default()
    };
    let unsized_line = format!(
        "download failed: s3://bucket/key to {} DownloadMissingContentLength\n",
        object_display()
    );
    let unmodified = HeadObjectResult {
        last_modified_epoch_seconds: None,
        ..head(Some(5))
    };
    let cases = [
        (Err(Box::new(missing.clone())), false, fatal, (0, None)),
        (
            Ok(unmodified),
            false,
            "fatal error: 'LastModified'\n",
            (0, None),
        ),
        (Err(Box::new(missing)), true, fatal, (0, None)),
        (Err(Box::new(canceled)), true, CANCEL, (0, None)),
        (Ok(head(None)), false, unsized_line.as_str(), (1, Some(1))),
    ];
    for (result, interrupted, line, totals) in cases {
        for quiet in [false, true] {
            let state = State::new();
            let env = FakeEnv {
                head: result.clone(),
                interrupt_at_head: interrupted,
                ..FakeEnv::new(&state)
            };
            let ran = run(&env, &single_download(quiet));
            assert_eq!(ran.reported, Reported::Status(1));
            assert_eq!(ran.stdout, "");
            let line = if quiet { "" } else { line };
            assert_eq!(ran.stderr, format!("{IGNORED}{line}"));
            assert_eq!((ran.queued, ran.final_total), totals);
            assert_eq!((env.heads.get(), env.sent()), (1, 0));
        }
    }
}

#[test]
fn a_missing_working_directory_outranks_a_single_downloads_head_outcomes() {
    for producer in [
        ProducerOutcome::HeadFailed(Box::new(TransferResult {
            error_code: 14_361,
            response_status: 404,
            ..TransferResult::default()
        })),
        ProducerOutcome::HeadCanceled,
        ProducerOutcome::HeadMissingLastModified,
    ] {
        let (status, events) = finish(
            "s3://bucket/key",
            &single_download(false),
            &Completion::Finished(Box::new(Finished {
                display_failure: Some(SetupError::current_dir(&io::Error::from(
                    io::ErrorKind::NotFound,
                ))),
                producer,
                canceled: true,
                ..Finished::default()
            })),
        );
        assert!(matches!(status, Err(RenderError::Fatal(name))
                if name == crate::local_error::CURRENT_DIR_UNLINKED));
        assert!(events.is_empty());
    }
}

#[test]
fn a_single_downloads_statistics_name_its_pool_and_writer_path() {
    for custom_writer in [false, true] {
        for numa_source_pool in [false, true] {
            let state = State::new();
            let env = FakeEnv {
                custom_writer,
                numa_source_pool,
                ..FakeEnv::new(&state)
            };
            let request = TransferRequest {
                collect_stats: true,
                ..single_download(false)
            };
            let ran = run(&env, &request);
            assert_eq!(ran.reported, Reported::Status(0));
            let stats = ran.stderr.strip_prefix(IGNORED).expect("warning first");
            assert!(stats.starts_with("zs3_transfer_stats direction=download "));
            let pool = if numa_source_pool { "numa" } else { "crt" };
            let tail = format!(
                " source_pool={pool} custom_writer_requests={} recv_file_requests={}\n",
                u8::from(custom_writer),
                u8::from(!custom_writer)
            );
            assert!(stats.ends_with(&tail), "{stats}");
        }
    }
}
