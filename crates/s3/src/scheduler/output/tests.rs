#![expect(
    clippy::expect_used,
    reason = "deterministic filesystem fixture assertions"
)]
use super::*;
use crate::download::{
    Body, CloseError, SharedConfig, SharedWriterService, WorkerSpawner, WriteError, WriterMode,
    testing::fakes,
};
use std::fs;
static NEXT: AtomicUsize = AtomicUsize::new(0);
struct Directory(PathBuf);
impl Directory {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "scheduler-output-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).expect("temporary directory");
        Self(path)
    }
    fn job(&self) -> Job {
        Job {
            direction: crate::transfer::Direction::Download,
            raw_key: b"key".to_vec(),
            request_key: "key".into(),
            local_path: self.0.join("final"),
            temp_path: Some(self.0.join("temp")),
            size: Some(4),
            size_listed: false,
            size_changed: AtomicBool::new(false),
            modified: None,
            condition: ObjectCondition::default(),
            case_name: None,
            output: Mutex::default(),
            custom_writer: AtomicBool::new(false),
        }
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
#[derive(Debug)]
struct ThreadSpawner;
impl WorkerSpawner for ThreadSpawner {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> io::Result<std::thread::JoinHandle<()>> {
        std::thread::Builder::new().name(name).spawn(worker)
    }
}
fn service() -> SharedWriterService {
    service_on(Arc::new(fakes::FakePlatform::default()))
}
fn service_on(platform: Arc<fakes::FakePlatform>) -> SharedWriterService {
    SharedWriterService::start_with(
        SharedConfig {
            writer: fakes::config(WriterMode::Pwrite),
            custom_writer_required: true,
            in_flight_max: 1,
            ..SharedConfig::default()
        },
        platform,
        Arc::new(ThreadSpawner),
    )
    .expect("shared service")
}
fn failed_get() -> TransferResult {
    TransferResult {
        error_code: 1,
        ..Default::default()
    }
}
#[test]
fn download_success_renames_temp_and_failure_preserves_existing_final() {
    let directory = Directory::new();
    let job = directory.job();
    let temp = job.temp_path.as_ref().expect("temp path");
    fs::write(&job.local_path, b"old").expect("old final");
    fs::write(temp, b"new").expect("temp");
    assert!(matches!(
        finalize(&job, &TransferResult::default()),
        Finalize::Success
    ));
    assert_eq!(fs::read(&job.local_path).expect("new final"), b"new");
    assert!(!temp.exists());
    fs::write(temp, b"partial").expect("failed temp");
    assert!(matches!(
        finalize(
            &job,
            &TransferResult {
                error_code: 1,
                ..Default::default()
            }
        ),
        Finalize::Transfer(_)
    ));
    assert_eq!(fs::read(&job.local_path).expect("preserved final"), b"new");
    assert!(!temp.exists());
}
fn native(output: Output<'_>) -> Option<SharedOutput> {
    match output {
        Output::Native(output) => Some(output),
        Output::RecvFile(_) => None,
    }
}
#[test]
fn shared_preparation_fails_an_output_it_cannot_open() {
    let directory = Directory::new();
    let mut job = directory.job();
    let service = service();
    fs::write(&job.local_path, b"blocker").expect("blocker");
    job.temp_path = Some(job.local_path.join("child"));
    assert!(prepare(&job, Some(&service), 4).is_err());
    assert!(lock(&job.output).prepared.is_none());
    assert!(!job.custom_writer.load(Ordering::Acquire));
    assert_eq!(service.active_outputs(), 1);
    abandon(&job);
    assert_eq!(service.active_outputs(), 0);
    service.close_and_join();
}
#[test]
fn a_download_without_a_temp_path_is_outside_its_root() {
    let directory = Directory::new();
    let mut job = directory.job();
    job.temp_path = None;
    let service = service();
    for service in [None, Some(&service)] {
        assert!(matches!(
            prepare(&job, service, 4),
            Err(ref name) if name == "DownloadDestinationOutsideRoot"
        ));
    }
    assert!(lock(&job.output).slot.is_none());
    service.close_and_join();
}
#[test]
fn a_closed_service_fails_the_download_as_a_closed_shared_writer() {
    let directory = Directory::new();
    let job = directory.job();
    let service = service();
    service.close_and_join();
    assert!(matches!(
        prepare(&job, Some(&service), 4),
        Err(ref name) if name == "DownloadSharedWriterClosed"
    ));
    assert!(lock(&job.output).slot.is_none());
    assert!(!job.custom_writer.load(Ordering::Acquire));
}
#[test]
fn shared_adapter_finalizes_or_abandons_prepared_outputs_once() {
    let directory = Directory::new();
    let job = directory.job();
    let service = service();
    let prepared = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    prepared
        .enqueue(Body::owned(0, b"data".to_vec()))
        .expect("body");
    drop(prepared);
    assert_eq!(service.active_outputs(), 1);
    assert!(matches!(
        finalize(&job, &TransferResult::default()),
        Finalize::Success
    ));
    assert!(lock(&job.output).prepared.is_none());
    assert_eq!(service.active_outputs(), 0);
    let prepared = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare second")
        .expect("custom output");
    drop(prepared);
    abandon(&job);
    abandon(&job);
    assert_eq!(service.active_outputs(), 0);
    assert!(lock(&job.output).prepared.is_none());
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    assert!(job.local_path.exists());
    service.close_and_join();
}
#[test]
fn an_object_below_the_native_threshold_keeps_recv_filepath_unless_required() {
    let directory = Directory::new();
    let job = directory.job();
    let implicit = SharedWriterService::start_with(
        SharedConfig {
            writer: fakes::config(WriterMode::Pwrite),
            custom_writer_required: false,
            in_flight_max: 1,
            ..SharedConfig::default()
        },
        Arc::new(fakes::FakePlatform::default()),
        Arc::new(ThreadSpawner),
    )
    .expect("shared service");
    assert!(matches!(
        prepare(&job, Some(&implicit), 4).expect("prepare"),
        Output::RecvFile(path) if Some(path) == job.temp_path.as_deref()
    ));
    assert!(!job.custom_writer.load(Ordering::Acquire));
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    implicit.close_and_join();
    let required = service();
    let output = prepare(&job, Some(&required), 4)
        .map(native)
        .expect("prepare")
        .expect("native output");
    assert!(job.custom_writer.load(Ordering::Acquire));
    assert!(job.temp_path.as_ref().expect("temp").exists());
    drop(output);
    abandon(&job);
    required.close_and_join();
}

#[test]
fn a_disk_error_racing_a_failed_get_outranks_its_result() {
    let directory = Directory::new();
    let job = directory.job();
    let platform = Arc::new(fakes::FakePlatform::default());
    let hold = Arc::new(std::sync::Barrier::new(2));
    *lock(&platform.write_hold) = Some(Arc::clone(&hold));
    lock(&platform.faults).push_back(fakes::Fault::Failed);
    let service = service_on(platform);
    let output = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    output
        .enqueue(Body::owned(0, b"da".to_vec()))
        .expect("body");
    hold.wait();
    std::thread::scope(|scope| {
        let finalized = scope.spawn(|| finalize(&job, &failed_get()));
        while !output.is_closed() {
            std::thread::yield_now();
        }
        hold.wait();
        let full = WriteError::from(io::Error::from(io::ErrorKind::StorageFull));
        assert!(matches!(
            finalized.join().expect("finalizer"),
            Finalize::Write(name) if name == crate::cp::write_error_name(&full)
        ));
    });
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    assert_eq!(service.active_outputs(), 0);
    service.close_and_join();
}
#[test]
fn a_failed_gets_incomplete_body_leaves_it_the_request_result() {
    let directory = Directory::new();
    let job = directory.job();
    let service = service();
    let output = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    output
        .enqueue(Body::owned(0, b"da".to_vec()))
        .expect("body");
    drop(output);
    assert!(matches!(
        finalize(&job, &failed_get()),
        Finalize::Transfer(result) if result.error_code == 1
    ));
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    service.close_and_join();
}
#[test]
fn retiring_an_attempt_keeps_its_slot_for_a_fresh_output() {
    let directory = Directory::new();
    let job = directory.job();
    let temp = job.temp_path.clone().expect("temp path");
    let service = service();
    let output = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    let consumer = Mutex::new(Some(output));
    let shut_down = AtomicBool::new(false);
    let error = retire(&job, &failed_get(), &|| {
        assert!(lock(&job.output).prepared.is_none());
        assert!(temp.exists(), "the temp file outlives the shutdown wait");
        drop(lock(&consumer).take());
        shut_down.store(true, Ordering::Release);
    });
    assert_eq!(error, None);
    assert!(shut_down.load(Ordering::Acquire));
    assert!(!temp.exists());
    assert!(lock(&job.output).slot.is_some());
    assert_eq!(service.active_outputs(), 1);
    let replay = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare the replay")
        .expect("custom output");
    assert!(temp.exists());
    assert_eq!(service.active_outputs(), 1);
    drop(replay);
    abandon(&job);
    assert_eq!(service.active_outputs(), 0);
    service.close_and_join();
}
#[test]
fn retiring_an_attempt_reports_the_outputs_local_error() {
    let directory = Directory::new();
    let job = directory.job();
    let service = service();
    let output = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    let full = WriteError::from(io::Error::from(io::ErrorKind::StorageFull));
    output.fail(full.clone());
    drop(output);
    assert_eq!(
        retire(&job, &failed_get(), &|| {}),
        Some(crate::cp::write_error_name(&full))
    );
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    abandon(&job);
    assert_eq!(service.active_outputs(), 0);
    service.close_and_join();
}
fn finalized_without_output(
    job: &Job,
    failure: OutputFailure,
    result: &TransferResult,
) -> Result<String, i32> {
    record_failure(job, Some(failure));
    match finalize(job, result) {
        Finalize::Write(name) => Ok(name),
        Finalize::Transfer(result) => Err(result.error_code),
        _ => Err(i32::MIN),
    }
}
#[test]
fn a_get_sent_without_its_output_reports_the_output_failure_after_a_body() {
    let directory = Directory::new();
    let mut job = directory.job();
    job.temp_path = None;
    let failed = |body_delivered, canceled_by_interrupt| TransferResult {
        error_code: 1,
        body_delivered,
        canceled_by_interrupt,
        ..Default::default()
    };
    let refused = Box::new(TransferResult {
        error_code: 42,
        ..Default::default()
    });
    let write = || OutputFailure::Write("OutsideRoot".into());
    for (result, written, refusal) in [
        (TransferResult::default(), Ok("OutsideRoot".into()), Err(42)),
        (failed(true, false), Ok("OutsideRoot".into()), Err(42)),
        (failed(false, false), Err(1), Err(1)),
        (failed(true, true), Err(1), Err(1)),
    ] {
        assert_eq!(finalized_without_output(&job, write(), &result), written);
        let crt = OutputFailure::Crt(refused.clone());
        assert_eq!(finalized_without_output(&job, crt, &result), refusal);
    }
    assert!(!job.local_path.exists());
}
struct CloseCase {
    body: &'static [u8],
    local_error: Option<WriteError>,
    error_code: i32,
    abandon: bool,
}
fn end_with_a_failing_close(
    directory: &Directory,
    platform: &fakes::FakePlatform,
    service: &SharedWriterService,
    case: &CloseCase,
) -> Option<Result<String, i32>> {
    let job = directory.job();
    fs::write(&job.local_path, b"original").expect("destination");
    let closes = platform.closes.load(Ordering::SeqCst);
    let output = prepare(&job, Some(service), 5)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    if !case.body.is_empty() {
        output
            .enqueue(Body::owned(0, case.body.to_vec()))
            .expect("body");
    }
    if let Some(error) = &case.local_error {
        output.fail(error.clone());
    }
    drop(output);
    let finalized = end(&job, case);
    assert_eq!(platform.closes.load(Ordering::SeqCst), closes + 1);
    assert!(lock(&job.output).prepared.is_none());
    assert!(lock(&job.output).slot.is_none());
    assert_eq!(service.active_outputs(), 0);
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    assert_eq!(fs::read(&job.local_path).expect("destination"), b"original");
    finalized
}
fn end(job: &Job, case: &CloseCase) -> Option<Result<String, i32>> {
    if case.abandon {
        abandon(job);
        abandon(job);
        return None;
    }
    let result = TransferResult {
        error_code: case.error_code,
        ..Default::default()
    };
    Some(match finalize(job, &result) {
        Finalize::Write(name) => Ok(name),
        Finalize::Transfer(result) => Err(result.error_code),
        _ => Err(i32::MIN),
    })
}
#[test]
fn close_failure_prevents_commit_and_preserves_earlier_failures() {
    let directory = Directory::new();
    let platform = Arc::new(fakes::FakePlatform::default());
    *lock(&platform.close_failure) = Some(CloseError::InputOutput);
    let service = service_on(Arc::clone(&platform));
    let full = WriteError::from(io::Error::from(io::ErrorKind::StorageFull));
    for (case, expected) in [
        (
            CloseCase {
                body: b"hello",
                local_error: None,
                error_code: 0,
                abandon: false,
            },
            Some(Ok("Input/output error".to_owned())),
        ),
        (
            CloseCase {
                body: b"hello",
                local_error: Some(full),
                error_code: 123,
                abandon: false,
            },
            Some(Ok("No space left on device".to_owned())),
        ),
        (
            CloseCase {
                body: b"",
                local_error: None,
                error_code: 123,
                abandon: false,
            },
            Some(Err(123)),
        ),
        (
            CloseCase {
                body: b"",
                local_error: None,
                error_code: 0,
                abandon: true,
            },
            None,
        ),
    ] {
        assert_eq!(
            end_with_a_failing_close(&directory, &platform, &service, &case),
            expected
        );
    }
    service.close_and_join();
}
#[test]
fn retiring_an_attempt_reports_a_delayed_close_failure() {
    let directory = Directory::new();
    let job = directory.job();
    let platform = Arc::new(fakes::FakePlatform::default());
    *lock(&platform.close_failure) = Some(CloseError::InputOutput);
    let service = service_on(Arc::clone(&platform));
    let output = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    drop(output);
    let error = retire(&job, &failed_get(), &|| {
        assert_eq!(platform.closes.load(Ordering::SeqCst), 0);
    });
    assert_eq!(error.as_deref(), Some("Input/output error"));
    assert_eq!(platform.closes.load(Ordering::SeqCst), 1);
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    abandon(&job);
    assert_eq!(platform.closes.load(Ordering::SeqCst), 1);
    assert_eq!(service.active_outputs(), 0);
    service.close_and_join();
}
#[test]
fn an_abandoned_output_still_writes_its_queued_bodies() {
    let directory = Directory::new();
    let job = directory.job();
    let platform = Arc::new(fakes::FakePlatform::default());
    let hold = Arc::new(std::sync::Barrier::new(2));
    *lock(&platform.write_hold) = Some(Arc::clone(&hold));
    let service = SharedWriterService::start_with(
        SharedConfig {
            writer: crate::download::WriterConfig {
                workers: Some(1),
                ..fakes::config(WriterMode::Pwrite)
            },
            custom_writer_required: true,
            in_flight_max: 1,
            ..SharedConfig::default()
        },
        Arc::<fakes::FakePlatform>::clone(&platform),
        Arc::new(ThreadSpawner),
    )
    .expect("shared service");
    let output = prepare(&job, Some(&service), 4)
        .map(native)
        .expect("prepare")
        .expect("custom output");
    output
        .enqueue(Body::owned(0, b"da".to_vec()))
        .expect("body");
    hold.wait();
    output
        .enqueue(Body::owned(2, b"ta".to_vec()))
        .expect("body");
    std::thread::scope(|scope| {
        let abandoned = scope.spawn(|| abandon(&job));
        while !output.is_closed() {
            std::thread::yield_now();
        }
        hold.wait();
        abandoned.join().expect("abandon");
    });
    assert_eq!(&lock(&platform.disk)[..4], b"data");
    assert_eq!(platform.closes.load(Ordering::SeqCst), 1);
    assert!(!job.temp_path.as_ref().expect("temp").exists());
    assert_eq!(service.active_outputs(), 0);
    service.close_and_join();
}
