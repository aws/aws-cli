#![expect(
    clippy::expect_used,
    clippy::panic,
    reason = "fixtures fail at the violated setup"
)]
use super::*;
use crate::download::WriterMode;
use crate::scheduler::{Completion, Event, Finalize, Job, Operations, OwnedRequest, SubmitError};
use cli_core::output::BufferedStream;
use crt::s3::EntryKind;
use std::cell::Cell;
use std::io;
use std::sync::Mutex;

#[derive(Debug, Default)]
struct FakeOperations {
    modified: Mutex<Vec<Option<i64>>>,
}
#[derive(Debug)]
struct FakeRequest(Arc<dyn Completion>);
impl OwnedRequest for FakeRequest {
    fn cancel(&self) {}
}
impl Drop for FakeRequest {
    fn drop(&mut self) {
        self.0.shutdown();
    }
}
impl Operations for FakeOperations {
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
        completion: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        self.modified
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .push(job.modified);
        completion.finish(crt::s3::TransferResult::default());
        Ok(Box::new(FakeRequest(completion)))
    }
    fn finalize(&self, _: &Job, _: &crt::s3::TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}
#[derive(Debug)]
struct FakeSink;
impl Sink for FakeSink {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
}
fn request() -> recursive::TransferRequest {
    recursive::TransferRequest {
        direction: Direction::Download,
        bucket: "bucket".into(),
        prefix: Vec::new(),
        local_root: "output".into(),
        runtime: RuntimeOptions::default(),
        quiet: false,
        dryrun: false,
        no_overwrite: false,
        glacier: crate::transfer::GlacierPolicy::Warn,
        content_types: None,
        refusal: None,
        page_size: 0,
        max_in_flight: 1,
        collect_stats: true,
        prefetch: true,
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
#[test]
fn cancellation_before_listing_skips_paginator_and_joins_submit_worker() -> io::Result<()> {
    for interrupted in [false, true] {
        let request = request();
        let scheduler = Scheduler::new(
            request.clone(),
            "/".into(),
            Arc::new(FakeOperations::default()),
            Arc::new(FakeSink),
        );
        let state = interrupt::State::new();
        if interrupted {
            state.request();
        }
        let called = Cell::new(false);
        let ProducerResult {
            outcome: producer,
            list_stats: stats,
            ..
        } = produce_listing_with(
            &request,
            &state,
            Arc::clone(&scheduler),
            |scheduler| SubmitQueue::new(scheduler, 1),
            |stats, _| {
                called.set(true);
                assert!(stats.is_some());
                crt::s3::ListResult::default()
            },
            &mut |_: &ListedObject<'_>| Selection::QUEUE,
        );
        assert_eq!(called.get(), !interrupted);
        assert_eq!(stats.is_none(), interrupted);
        assert_eq!(
            matches!(producer, recursive::ProducerOutcome::WalkCompleted),
            interrupted
        );
        assert_eq!(Arc::strong_count(&scheduler), 1);
        scheduler.drain();
        let finished = scheduler.finished();
        assert_eq!(finished.failed, 0);
        assert!(finished.fatal.is_none());
    }
    Ok(())
}
#[test]
fn submit_worker_start_failure_is_fatal_without_an_upload_traversal_error() {
    let cases = [
        (io::ErrorKind::PermissionDenied, "Permission denied"),
        (io::ErrorKind::WouldBlock, "Insufficient system resources"),
        (io::ErrorKind::OutOfMemory, "Out of memory"),
    ];
    for (kind, name) in cases {
        assert_eq!(submit_worker_start_failure(kind), name, "{kind:?}");
    }
}
fn submit_worker_start_failure(kind: io::ErrorKind) -> String {
    let request = request();
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        Arc::new(FakeOperations::default()),
        Arc::new(FakeSink),
    );
    let called = Cell::new(false);
    let ProducerResult {
        outcome: producer,
        list_stats: stats,
        ..
    } = produce_listing_with(
        &request,
        &interrupt::State::new(),
        Arc::clone(&scheduler),
        |_| Err(io::Error::from(kind)),
        |_, _| {
            called.set(true);
            crt::s3::ListResult::default()
        },
        &mut |_: &ListedObject<'_>| Selection::QUEUE,
    );
    assert!(!called.get());
    assert!(stats.is_none());
    assert!(matches!(
        producer,
        recursive::ProducerOutcome::WalkCompleted
    ));
    assert!(producer.exhausted(false));
    assert_eq!(Arc::strong_count(&scheduler), 1);
    scheduler.drain();
    let mut finished = scheduler.finished();
    finished.producer = producer;
    let processor = results::Processor::new(None);
    let publisher = processor.publisher();
    let rendered = recursive::finish_transfer(
        recursive::CommandReport::new(&publisher, request.quiet),
        OsStr::new("s3://bucket/"),
        &request,
        &recursive::Completion::Finished(Box::new(finished)),
    );
    let events = publisher.take_events();
    assert!(
        !events.iter().any(|event| matches!(
            event,
            results::Event::Diagnostic(text) if String::from_utf8_lossy(text).contains("upload")
        )),
        "{events:?}"
    );
    match rendered {
        Err(recursive::RenderError::Fatal(error)) => error,
        other => panic!("expected a fatal error, got {other:?}"),
    }
}

#[test]
fn listed_mtime_keeps_pre_epoch_epoch_and_later_values() -> io::Result<()> {
    let request = request();
    let operations = Arc::new(FakeOperations::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        operations.clone(),
        Arc::new(FakeSink),
    );
    let ProducerResult {
        outcome: producer, ..
    } = produce_listing_with(
        &request,
        &interrupt::State::new(),
        Arc::clone(&scheduler),
        |scheduler| SubmitQueue::new(scheduler, 1),
        |_, callback| {
            for modified in [None, Some(-1), Some(0), Some(253402300799)] {
                assert_eq!(
                    callback(crt::s3::ListEntry {
                        name: b"key".to_vec(),
                        size: 1,
                        date: modified.map(|epoch_seconds| crt::s3::LastModified {
                            epoch_seconds,
                            ..Default::default()
                        }),
                        ..crt::s3::ListEntry::new(EntryKind::Object)
                    }),
                    0
                );
            }
            crt::s3::ListResult::default()
        },
        &mut |_: &ListedObject<'_>| Selection::QUEUE,
    );
    assert!(matches!(
        producer,
        recursive::ProducerOutcome::ListCompleted(_)
    ));
    scheduler.drain();
    assert_eq!(
        *operations
            .modified
            .lock()
            .unwrap_or_else(|error| error.into_inner()),
        [None, Some(-1), Some(0), Some(253402300799)]
    );
    assert_eq!(scheduler.finished().failed, 0);
    Ok(())
}

#[test]
fn listing_filters_keep_markers_and_keys_outside_the_prefix_out_of_the_queue() {
    let request = recursive::TransferRequest {
        prefix: "p/".into(),
        ..request()
    };
    let operations = Arc::new(FakeOperations::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        operations.clone(),
        Arc::new(FakeSink),
    );
    let queued = || scheduler.finished().stats.map(|stats| stats.queue_hwm);
    let entry = |kind, name: &[u8], size| crt::s3::ListEntry {
        name: name.to_vec(),
        size,
        date: Some(crt::s3::LastModified {
            epoch_seconds: size as i64,
            ..Default::default()
        }),
        ..crt::s3::ListEntry::new(kind)
    };
    let produced = produce_listing_with(
        &request,
        &interrupt::State::new(),
        Arc::clone(&scheduler),
        |scheduler| SubmitQueue::new(scheduler, 4),
        |_, callback| {
            for filtered in [
                entry(EntryKind::Object, b"p/marker/", 0),
                entry(EntryKind::Object, b"p/", 0),
                entry(EntryKind::Object, b"q/outside", 1),
                entry(EntryKind::Object, b"outside/", 1),
                entry(EntryKind::CommonPrefix, b"p/dir/", 0),
            ] {
                assert_eq!(callback(filtered), 0);
            }
            assert_eq!(queued(), Some(0));
            assert_eq!(callback(entry(EntryKind::Object, b"p/empty", 0)), 0);
            crt::s3::ListResult::default()
        },
        &mut |_: &ListedObject<'_>| Selection::QUEUE,
    );
    scheduler.drain();
    assert!(produced.exhausted(false));
    assert_eq!(queued(), Some(1));
    assert_eq!(
        *operations
            .modified
            .lock()
            .unwrap_or_else(|error| error.into_inner()),
        [Some(0)]
    );
    assert_eq!(scheduler.finished().failed, 0);
}

#[test]
fn a_listing_that_ends_without_a_repeated_token_raises_nothing() {
    let request = request();
    let sink = Arc::new(RecordingSink::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        Arc::new(FakeOperations::default()),
        sink.clone(),
    );
    let produced = produce_listing_with(
        &request,
        &interrupt::State::new(),
        Arc::clone(&scheduler),
        |scheduler| SubmitQueue::new(scheduler, 1),
        |_, callback| {
            let entry = crt::s3::ListEntry {
                name: b"key".to_vec(),
                size: 1,
                ..crt::s3::ListEntry::new(EntryKind::Object)
            };
            assert_eq!(callback(entry), 0);
            crt::s3::ListResult {
                transfer: crt::s3::TransferResult {
                    response_status: 200,
                    ..Default::default()
                },
                ..Default::default()
            }
        },
        &mut |_: &ListedObject<'_>| Selection::QUEUE,
    );
    scheduler.drain();
    assert!(produced.exhausted(false));
    let events = sink.0.lock().unwrap_or_else(|error| error.into_inner());
    assert!(
        !events.iter().any(|event| matches!(
            event,
            crate::results::Event::Fatal(_) | crate::results::Event::CtrlC
        )),
        "{events:?}"
    );
    let finished = scheduler.finished();
    assert!(!finished.canceled);
    assert!(finished.fatal.is_none());
    assert_eq!(finished.failed, 0);
}

#[derive(Debug, Default)]
struct HeldOperations {
    submitted: Mutex<Vec<Vec<u8>>>,
    discarded: std::sync::atomic::AtomicUsize,
    canceled: Arc<std::sync::atomic::AtomicUsize>,
}
#[derive(Debug)]
struct HeldRequest {
    completion: Arc<dyn Completion>,
    canceled: Arc<std::sync::atomic::AtomicUsize>,
}
impl OwnedRequest for HeldRequest {
    fn cancel(&self) {
        self.canceled
            .fetch_add(1, std::sync::atomic::Ordering::AcqRel);
        // The CRT delivers a cancellation's finish on its own thread.
        let completion = Arc::clone(&self.completion);
        std::thread::spawn(move || {
            completion.finish(crt::s3::TransferResult::from_crt_error(
                crt::s3::CANCELED_ERROR_CODE,
            ));
        });
    }
}
impl Drop for HeldRequest {
    fn drop(&mut self) {
        self.completion.shutdown();
    }
}
impl Operations for HeldOperations {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, path: &Path) -> crate::transfer::SourceInspection {
        crate::transfer::inspect_upload_source(path)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        completion: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        self.submitted
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .push(job.raw_key.clone());
        Ok(Box::new(HeldRequest {
            completion,
            canceled: Arc::clone(&self.canceled),
        }))
    }
    fn finalize(&self, _: &Job, _: &crt::s3::TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {
        self.discarded
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }
}
#[derive(Debug, Default)]
struct RecordingSink(Mutex<Vec<crate::results::Event>>);
impl Sink for RecordingSink {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: crate::results::Event, _: bool) -> Result<(), String> {
        self.0
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .push(event);
        Ok(())
    }
}

fn await_submission(operations: &HeldOperations) {
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while operations
        .submitted
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .is_empty()
        && std::time::Instant::now() < deadline
    {
        std::thread::yield_now();
    }
}
fn drain_once_canceled(scheduler: &Scheduler, operations: &HeldOperations) -> io::Result<()> {
    let submitted = || {
        operations
            .submitted
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .len()
    };
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while operations
        .canceled
        .load(std::sync::atomic::Ordering::Acquire)
        < submitted()
    {
        if std::time::Instant::now() >= deadline {
            <Scheduler as cli_core::InterruptHook>::cancel(scheduler);
            scheduler.drain();
            return Err(io::Error::other("a held request was never canceled"));
        }
        std::thread::yield_now();
    }
    scheduler.drain();
    Ok(())
}
fn assert_raised(sink: &RecordingSink, exception: &[u8]) -> io::Result<()> {
    let events = sink.0.lock().unwrap_or_else(|error| error.into_inner());
    let fatal = events
        .iter()
        .position(|event| matches!(event, crate::results::Event::Fatal(_)))
        .ok_or_else(|| io::Error::other("the exception is not published"))?;
    assert_eq!(
        events[fatal],
        crate::results::Event::Fatal(exception.to_vec())
    );
    assert!(
        events[fatal..]
            .iter()
            .any(|event| matches!(event, crate::results::Event::CtrlC))
    );
    assert!(!events[..fatal].iter().any(|event| matches!(
        event,
        crate::results::Event::CtrlC | crate::results::Event::Success { .. }
    )));
    Ok(())
}

fn forbidden_page() -> crt::s3::ListResult {
    crt::s3::ListResult {
        transfer: crt::s3::TransferResult {
            error_code: 3,
            response_status: 403,
            service_error: crt::s3::ServiceError {
                operation: crt::s3::BoundedText::new("ListObjectsV2"),
                ..Default::default()
            },
            ..Default::default()
        },
        ..Default::default()
    }
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_listing_exception_cancels_before_the_submitter_drains_its_queue() -> io::Result<()> {
    let repeated_token = crt::s3::ListResult {
        repeated_token: Some(b"same-token".to_vec()),
        ..Default::default()
    };
    for (result, exception) in [
        (
            repeated_token,
            &b"Error during pagination: The same next token was received twice: \
               {'ContinuationToken': 'same-token'}"[..],
        ),
        (
            forbidden_page(),
            b"An error occurred (403) when calling the ListObjectsV2 operation: Forbidden",
        ),
    ] {
        let request = request();
        let operations = Arc::new(HeldOperations::default());
        let sink = Arc::new(RecordingSink::default());
        let scheduler = Scheduler::new(
            request.clone(),
            "/".into(),
            operations.clone(),
            sink.clone(),
        );
        let ProducerResult {
            outcome: producer, ..
        } = produce_listing_with(
            &request,
            &interrupt::State::new(),
            Arc::clone(&scheduler),
            |scheduler| SubmitQueue::new(scheduler, 4),
            |_, callback| {
                for index in 0..3 {
                    let entry = crt::s3::ListEntry {
                        name: format!("key{index}").into_bytes(),
                        size: 1,
                        ..crt::s3::ListEntry::new(EntryKind::Object)
                    };
                    assert_eq!(callback(entry), 0);
                }
                await_submission(&operations);
                result
            },
            &mut |_: &ListedObject<'_>| Selection::QUEUE,
        );
        drain_once_canceled(&scheduler, &operations)?;
        assert!(!producer.exhausted(false));
        assert_eq!(
            *operations
                .submitted
                .lock()
                .unwrap_or_else(|error| error.into_inner()),
            [b"key0".to_vec()]
        );
        assert_eq!(
            operations
                .discarded
                .load(std::sync::atomic::Ordering::Relaxed),
            1
        );
        assert_raised(&sink, exception)?;
        let finished = scheduler.finished();
        assert!(!finished.canceled);
        assert!(finished.fatal.is_none());
    }
    Ok(())
}
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn an_interrupted_listing_publishes_no_exception() -> io::Result<()> {
    let request = request();
    let operations = Arc::new(HeldOperations::default());
    let sink = Arc::new(RecordingSink::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        operations.clone(),
        sink.clone(),
    );
    let state = interrupt::State::new();
    let produced = produce_listing_with(
        &request,
        &state,
        Arc::clone(&scheduler),
        |scheduler| SubmitQueue::new(scheduler, 4),
        |_, callback| {
            let entry = crt::s3::ListEntry {
                name: b"key0".to_vec(),
                size: 1,
                ..crt::s3::ListEntry::new(EntryKind::Object)
            };
            assert_eq!(callback(entry), 0);
            await_submission(&operations);
            state.request();
            forbidden_page()
        },
        &mut |_: &ListedObject<'_>| Selection::QUEUE,
    );
    drain_once_canceled(&scheduler, &operations)?;
    assert!(!produced.outcome.exhausted(true));
    let events = sink.0.lock().unwrap_or_else(|error| error.into_inner());
    assert!(
        !events
            .iter()
            .any(|event| matches!(event, crate::results::Event::Fatal(_))),
        "{events:?}"
    );
    Ok(())
}
#[cfg(unix)]
#[derive(Debug)]
struct TemporaryDirectory(std::path::PathBuf);
#[cfg(unix)]
impl TemporaryDirectory {
    fn new(name: &str) -> io::Result<Self> {
        let path =
            std::env::temp_dir().join(format!("s3-crt-backend-{}-{name}", std::process::id()));
        std::fs::create_dir_all(&path)?;
        Ok(Self(path))
    }
}
#[cfg(unix)]
impl Drop for TemporaryDirectory {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
#[cfg(unix)]
#[derive(Debug, Default)]
struct LosesWarnings(RecordingSink);
#[cfg(unix)]
impl Sink for LosesWarnings {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: crate::results::Event, quiet: bool) -> Result<(), String> {
        if matches!(event, crate::results::Event::Warning(_)) {
            return Err("WriteFailed".into());
        }
        self.0.publish(event, quiet)
    }
}

#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_failed_sync_destination_walk_cancels_the_downloads_in_flight() -> io::Result<()> {
    let root = TemporaryDirectory::new("failed-destination-walk")?;
    std::fs::create_dir_all(root.0.join("b"))?;
    std::fs::write(root.0.join("a0"), b"a0")?;
    std::os::unix::fs::symlink("missing", root.0.join("b").join("broken"))?;
    let request = recursive::TransferRequest {
        local_root: crate::transfer::normalize_local_directory_root(&root.0),
        sync: Some(crate::sync::Plan::default()),
        ..request()
    };
    let operations = Arc::new(HeldOperations::default());
    let sink = Arc::new(LosesWarnings::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        operations.clone(),
        sink.clone(),
    );
    let state = interrupt::State::new();
    let produced = produce_sync_listing_with(
        &request,
        &state,
        &scheduler,
        crate::sync::Strategies::default(),
        |select| {
            produce_listing_with(
                &request,
                &state,
                Arc::clone(&scheduler),
                |scheduler| SubmitQueue::new(scheduler, 4),
                |_, callback| {
                    let entry = |name: &str| crt::s3::ListEntry {
                        name: name.into(),
                        size: 1,
                        ..crt::s3::ListEntry::new(EntryKind::Object)
                    };
                    assert_eq!(callback(entry("a")), 0);
                    await_submission(&operations);
                    assert_eq!(callback(entry("c")), -1);
                    crt::s3::ListResult {
                        callback_error: -1,
                        ..Default::default()
                    }
                },
                select,
            )
        },
    );
    drain_once_canceled(&scheduler, &operations)?;
    let recursive::ProducerOutcome::ComparatorRaised(error) = &produced.outcome else {
        return Err(io::Error::other(format!("{:?}", produced.outcome)));
    };
    assert_eq!(
        *operations
            .submitted
            .lock()
            .unwrap_or_else(|error| error.into_inner()),
        [b"a".to_vec()]
    );
    assert_raised(&sink.0, error.as_bytes())?;
    Ok(())
}
#[cfg(unix)]
#[test]
fn a_sync_downloads_delete_is_done_before_its_walk_goes_on() -> io::Result<()> {
    let root = TemporaryDirectory::new("delete-before-walk")?;
    std::fs::create_dir_all(root.0.join("z"))?;
    std::fs::write(root.0.join("z").join("file"), b"f")?;
    std::os::unix::fs::symlink("z", root.0.join("a"))?;
    let strategies = crate::sync::Strategies {
        both: crate::sync::BothSides::SizeOnly,
        destination_only: crate::sync::DestinationOnly::Delete,
        ..crate::sync::Strategies::default()
    };
    let request = recursive::TransferRequest {
        local_root: crate::transfer::normalize_local_directory_root(&root.0),
        sync: Some(crate::sync::Plan {
            strategies,
            ..crate::sync::Plan::default()
        }),
        ..request()
    };
    let operations = Arc::new(FakeOperations::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        operations.clone(),
        Arc::new(FakeSink),
    );
    let state = interrupt::State::new();
    let produced = produce_sync_listing_with(&request, &state, &scheduler, strategies, |select| {
        produce_listing_with(
            &request,
            &state,
            Arc::clone(&scheduler),
            |scheduler| SubmitQueue::new(scheduler, 4),
            |_, callback| {
                let entry = crt::s3::ListEntry {
                    name: b"z/file".to_vec(),
                    size: 1,
                    ..crt::s3::ListEntry::new(EntryKind::Object)
                };
                assert_eq!(callback(entry), 0);
                crt::s3::ListResult::default()
            },
            select,
        )
    });
    scheduler.drain();
    assert!(produced.exhausted(false), "{:?}", produced.outcome);
    assert!(!root.0.join("z").join("file").exists());
    let stats = scheduler
        .finished()
        .stats
        .ok_or_else(|| io::Error::other("no stats"))?;
    assert_eq!((stats.submitted, stats.succeeded, stats.failed), (2, 2, 0));
    assert_eq!(
        operations
            .modified
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .len(),
        1
    );
    Ok(())
}
#[derive(Debug)]
struct LosesQueued;
impl Sink for LosesQueued {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: crate::results::Event, _: bool) -> Result<(), String> {
        if matches!(event, crate::results::Event::Queued { .. }) {
            Err("Out of memory".into())
        } else {
            Ok(())
        }
    }
}

#[test]
fn a_listing_whose_submitter_failed_is_not_exhausted() -> io::Result<()> {
    let request = request();
    let operations = Arc::new(FakeOperations::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/".into(),
        operations.clone(),
        Arc::new(LosesQueued),
    );
    let produced = produce_listing_with(
        &request,
        &interrupt::State::new(),
        Arc::clone(&scheduler),
        |scheduler| SubmitQueue::new(scheduler, 4),
        |_, callback| {
            let entry = crt::s3::ListEntry {
                name: b"key".to_vec(),
                size: 1,
                ..crt::s3::ListEntry::new(EntryKind::Object)
            };
            assert_eq!(callback(entry), 0);
            crt::s3::ListResult::default()
        },
        &mut |_: &ListedObject<'_>| Selection::QUEUE,
    );
    scheduler.drain();
    assert!(produced.submit_queue_failed);
    assert!(produced.outcome.exhausted(false));
    assert!(!produced.exhausted(false));
    assert_eq!(scheduler.finished().fatal.as_deref(), Some("Out of memory"));
    assert!(
        operations
            .modified
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .is_empty()
    );
    Ok(())
}
fn download_tuning(settings: &config::Settings) -> recursive::TransferRequest {
    recursive::TransferRequest {
        download: Some(settings.resolve_download()),
        ..sized_download(config::Shape::ManyObjects, 10.0, 0)
    }
}
fn sized_download(
    shape: config::Shape,
    target_gbps: f64,
    part_size: u64,
) -> recursive::TransferRequest {
    use cli_core::client_config::MemoryLimit;
    let inputs = config::SizingInputs {
        direction: Direction::Download,
        shape,
        target_gbps,
        memory_limit: MemoryLimit::Tier,
        part_size,
        max_connections: None,
        in_flight_max: crate::constants::IN_FLIGHT_MAX_DEFAULT,
        configured_writer: None,
    };
    recursive::TransferRequest {
        runtime: RuntimeOptions {
            part_size,
            ..RuntimeOptions::default()
        },
        max_in_flight: inputs.in_flight_max,
        sizing: config::resolve_client_sizing(&inputs),
        download: Some(config::Settings::default().resolve_download()),
        object: (shape == config::Shape::OneObject).then(recursive::SingleObject::default),
        ..request()
    }
}

#[test]
fn a_downloads_writer_queue_holds_every_buffer_its_pool_can_lend() {
    use config::Shape::{ManyObjects, OneObject};
    let mapped = cfg!(any(target_os = "linux", target_os = "macos"));
    let pick = |mapped_jobs, unmapped_jobs| if mapped { mapped_jobs } else { unmapped_jobs };
    for (shape, target_gbps, part_size, jobs) in [
        (OneObject, 200.0, 0, pick(1025, 6145)),
        (OneObject, 200.0, 16 << 20, pick(513, 3073)),
        (ManyObjects, 200.0, 0, pick(1536, 6656)),
        (ManyObjects, 200.0, 16 << 20, pick(1536, 3584)),
        (ManyObjects, 10.0, 0, 1024),
        (OneObject, 10.0, 0, 513),
        (ManyObjects, 4.0, 0, 576),
        (OneObject, 4.0, 0, 65),
    ] {
        let request = sized_download(shape, target_gbps, part_size);
        let (config, _) =
            service_config(&request, Some(DownloadLocality::default())).expect("a native writer");
        assert_eq!(
            config.queue_jobs_per_shard, jobs,
            "{shape:?} {target_gbps} {part_size}"
        );
    }
}
#[test]
fn writer_and_source_pool_are_chosen_independently() -> Result<(), SetupError> {
    let mut crt = download_tuning(&config::Settings {
        download_writer: Some(WriterMode::Crt),
        ..config::Settings::default()
    });
    let tuning = crt.download.as_mut().map(|tuning| &mut tuning.writer.numa);
    if let Some(numa) = tuning {
        numa.mode = crate::download::NumaMode::SameNode;
        numa.requirement = crate::download::Requirement::Required;
    }
    let writers = resolve_writers(&crt)?;
    let options = runtime_options(&crt, writers.as_ref());
    assert_eq!(options, sized(&crt));
    let (config, _) = service_config(&crt, writers).expect("a crt service");
    assert!(!config.should_use_custom_writer(u64::MAX));

    for writer in [WriterMode::Crt, WriterMode::Pwrite] {
        let request = download_tuning(&config::Settings {
            download_writer: Some(writer),
            download_writer_numa: Some(crate::download::NumaMode::Disabled),
            download_numa_pool: Some(crate::download::NumaPoolMode::Disabled),
            ..config::Settings::default()
        });
        let writers = resolve_writers(&request)?;
        let options = runtime_options(&request, writers.as_ref());
        assert_eq!(options.numa_source_pool_config, None);
        let (config, _) = service_config(&request, writers).expect("a service");
        assert_eq!(
            config.should_use_custom_writer(u64::MAX),
            writer != WriterMode::Crt
        );
    }
    let upload = recursive::TransferRequest {
        direction: Direction::Upload,
        ..request()
    };
    assert!(resolve_writers(&upload)?.is_none());
    assert_eq!(runtime_options(&upload, None), sized(&upload));
    Ok(())
}
fn sized(request: &recursive::TransferRequest) -> RuntimeOptions {
    RuntimeOptions {
        throughput_target_gbps: request.sizing.throughput_target_gbps,
        memory_limit_in_bytes: request.sizing.memory_limit_in_bytes,
        max_active_connections_override: request.sizing.max_connections,
        ..request.runtime.clone()
    }
}

#[test]
fn runtime_options_carry_the_requests_client_target_and_pool() {
    use cli_core::client_config::{MemoryLimit, Resolved, Source};
    let client = RuntimeOptions {
        user_agent: "aws-cli/2.0 md/test".into(),
        keep_alive: true,
        connect_timeout_ms: 5000,
        part_size: 5 << 20,
        multipart_upload_threshold: Some(6 << 20),
        single_request_threshold: Some(6 << 20),
        max_active_connections_override: 10,
        throughput_target_gbps: 100.0,
        ..RuntimeOptions::default()
    };
    for shape in [config::Shape::OneObject, config::Shape::ManyObjects] {
        let sizing = config::resolve_client_sizing(&config::SizingInputs {
            direction: Direction::Download,
            shape,
            target_gbps: 100.0,
            memory_limit: MemoryLimit::Tier,
            part_size: client.part_size,
            max_connections: Some(Resolved::new(3, Source::S3("max_concurrent_requests"))),
            in_flight_max: crate::constants::IN_FLIGHT_MAX_DEFAULT,
            configured_writer: None,
        });
        let request = recursive::TransferRequest {
            runtime: client.clone(),
            sizing,
            download: Some(config::Settings::default().resolve_download()),
            object: (shape == config::Shape::OneObject).then(recursive::SingleObject::default),
            ..request()
        };
        let options = runtime_options(&request, None);
        assert_eq!(
            options.throughput_target_gbps,
            sizing.throughput_target_gbps
        );
        assert_eq!(options.memory_limit_in_bytes, sizing.memory_limit_in_bytes);
        if shape == config::Shape::OneObject {
            assert_eq!(options.throughput_target_gbps, 100.0);
            let mapped = cfg!(any(target_os = "linux", target_os = "macos"));
            assert_eq!(
                options.memory_limit_in_bytes,
                if mapped { 4 << 30 } else { 0 }
            );
        }
        assert_eq!(
            options,
            RuntimeOptions {
                throughput_target_gbps: sizing.throughput_target_gbps,
                memory_limit_in_bytes: sizing.memory_limit_in_bytes,
                max_active_connections_override: 3,
                ..client.clone()
            }
        );
        let pooled = runtime_options(
            &request,
            Some(&DownloadLocality {
                source_pool: Some(vec![3]),
                ..DownloadLocality::default()
            }),
        );
        assert_eq!(
            pooled.numa_source_pool_config,
            Some(crt::source_pool::Config {
                nodes: vec![3],
                budget_bytes: 0,
            })
        );
    }
}

fn single_download(settings: &config::Settings) -> recursive::TransferRequest {
    recursive::TransferRequest {
        download: Some(settings.resolve_download()),
        object: Some(recursive::SingleObject {
            key: b"key".to_vec(),
            local_path: "object".into(),
            ..Default::default()
        }),
        max_in_flight: 4,
        ..sized_download(config::Shape::OneObject, 10.0, 0)
    }
}

#[test]
fn a_single_downloads_writer_service_takes_every_configured_writer_setting()
-> Result<(), SetupError> {
    use crate::download::{CopyMode, NumaMode, PrefaultMode, Requirement};
    let settings = config::Settings {
        io_workers: Some(7),
        download_writer: Some(WriterMode::Mmap),
        download_writer_copy: Some(CopyMode::Memcpy),
        download_writer_prefault: Some(PrefaultMode::Disabled),
        download_writer_numa: Some(NumaMode::Disabled),
        ..config::Settings::default()
    };
    let mut request = single_download(&settings);
    request.download = request.download.map(|tuning| tuning.with_direct_io(true));
    let writers = resolve_writers(&request)?;
    let (config, locality) = service_config(&request, writers).expect("a native writer");
    assert_eq!(config.writer.mode, WriterMode::Mmap);
    assert_eq!(config.writer.requirement, Requirement::Required);
    assert_eq!(config.writer.copy_mode, CopyMode::Memcpy);
    assert_eq!(config.writer.prefault, PrefaultMode::Disabled);
    assert!(config.should_use_custom_writer(0));
    assert_eq!(config.in_flight_max, 1);
    let service = SharedWriterService::start_with_locality(config, locality)
        .map_err(|error| SetupError::write(&error))?;
    assert_eq!(service.worker_count(), 7);
    service.close_and_join();
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test keeps every size and explicit setting"
)]
fn recursive_downloads_take_recv_filepath_below_64_mib_unless_a_setting_is_explicit()
-> Result<(), SetupError> {
    use crate::download::{CUSTOM_WRITER_SIZE_MIN, CopyMode, NumaMode, PrefaultMode};
    let implicit = download_tuning(&config::Settings::default());
    let (config, _) = service_config(&implicit, resolve_writers(&implicit)?).expect("a service");
    assert!(!config.should_use_custom_writer(CUSTOM_WRITER_SIZE_MIN - 1));
    assert!(config.should_use_custom_writer(CUSTOM_WRITER_SIZE_MIN));
    let explicit = [
        config::Settings {
            io_workers: Some(4),
            ..config::Settings::default()
        },
        config::Settings {
            download_writer: Some(WriterMode::Mmap),
            ..config::Settings::default()
        },
        config::Settings {
            download_writer_copy: Some(CopyMode::Memcpy),
            ..config::Settings::default()
        },
        config::Settings {
            download_writer_prefault: Some(PrefaultMode::Disabled),
            ..config::Settings::default()
        },
        config::Settings {
            download_writer_numa: Some(NumaMode::Disabled),
            ..config::Settings::default()
        },
        config::Settings {
            download_writer_node: Some(Vec::new()),
            download_writer_numa: Some(NumaMode::Disabled),
            ..config::Settings::default()
        },
    ];
    for settings in &explicit {
        let request = download_tuning(settings);
        let (config, _) = service_config(&request, resolve_writers(&request)?).expect("service");
        for size in [0, CUSTOM_WRITER_SIZE_MIN - 1, CUSTOM_WRITER_SIZE_MIN] {
            assert!(config.should_use_custom_writer(size), "{settings:?} {size}");
        }
    }
    let one = single_download(&config::Settings::default());
    let (config, _) = service_config(&one, resolve_writers(&one)?).expect("a service");
    assert!(config.should_use_custom_writer(0));
    for request in [
        download_tuning(&config::Settings {
            download_writer: Some(WriterMode::Crt),
            ..config::Settings::default()
        }),
        single_download(&config::Settings {
            download_writer: Some(WriterMode::Crt),
            ..config::Settings::default()
        }),
    ] {
        let (config, locality) =
            service_config(&request, resolve_writers(&request)?).expect("a crt service");
        for size in [0, CUSTOM_WRITER_SIZE_MIN - 1, CUSTOM_WRITER_SIZE_MIN] {
            assert!(!config.should_use_custom_writer(size), "{size}");
        }
        let service = SharedWriterService::start_with_locality(config, locality)
            .map_err(|error| SetupError::write(&error))?;
        assert_eq!(service.worker_count(), 0);
        service.close_and_join();
    }
    Ok(())
}

struct FailingStream(fn() -> io::Error);
impl Write for FailingStream {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> {
        Err((self.0)())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
fn publish_success_and_warning(publisher: &results::Publisher) {
    publisher.publish(results::Event::Success {
        key: 0,
        line: results::Line {
            transfer_type: results::TransferType::Upload,
            source: b"a".to_vec(),
            destination: Some(b"s3://b/a".to_vec()),
        },
    });
    publisher.publish(results::Event::Warning(b"warning: w".to_vec()));
    publisher.close();
}
type Closed = (Result<u8, String>, Vec<u8>);
fn close_failing(stdout_fails: bool, cause: fn() -> io::Error) -> Closed {
    let mut processor = results::Processor::with_diagnostics(Some(results::PrinterConfig {
        mode: results::Mode::NoProgress,
        ..Default::default()
    }));
    let publisher = processor.publisher();
    publish_success_and_warning(&publisher);
    let (mut failing, mut written) = (FailingStream(cause), Vec::new());
    let mut failing = BufferedStream::new(&mut failing, 4096);
    let mut written = BufferedStream::new(&mut written, 4096);
    let output = if stdout_fails {
        processor.run(&mut failing, &mut written)
    } else {
        processor.run(&mut written, &mut failing)
    };
    let kept = failing.buffered().to_vec();
    let Err(errors) = output else {
        return (Err("the printer wrote everything".to_owned()), Vec::new());
    };
    let status = close_output(errors, Ok(0))
        .map_err(|failure| String::from_utf8_lossy(&failure.message).into_owned());
    (status, kept)
}
#[test]
fn a_failed_stream_write_with_no_errno_fails_the_command() {
    let broken = || io::Error::from(io::ErrorKind::BrokenPipe);
    let broken_pipe = Err(cli_core::cli_error::BROKEN_PIPE_MESSAGE.to_owned());
    assert_eq!(close_failing(true, broken).0, broken_pipe);
    assert_eq!(close_failing(false, broken).0, broken_pipe);
    let no_errno = || io::Error::from(io::ErrorKind::StorageFull);
    let write_failed = Err("WriteFailed".to_owned());
    assert_eq!(close_failing(true, no_errno).0, write_failed);
    assert_eq!(close_failing(false, no_errno).0, write_failed);
    let mut processor = results::Processor::with_diagnostics(None);
    let publisher = processor.publisher();
    publish_success_and_warning(&publisher);
    let output = processor.run(&mut FailingStream(broken), &mut FailingStream(broken));
    assert!(output.is_ok());
}
#[cfg(unix)]
#[test]
fn a_failed_stdout_write_keeps_its_output_for_the_flush_at_exit() {
    let line = b"upload: a to s3://b/a\n".to_vec();
    let causes: [fn() -> io::Error; 3] = [
        || io::Error::from_raw_os_error(libc::EPIPE),
        || io::Error::from_raw_os_error(libc::ENOSPC),
        || io::Error::from_raw_os_error(libc::EBADF),
    ];
    for cause in causes {
        assert_eq!(close_failing(true, cause), (Ok(0), line.clone()));
    }
    let again = || io::Error::from_raw_os_error(libc::EAGAIN);
    assert_eq!(close_failing(true, again).0, Err("WriteFailed".to_owned()));
    let errors = results::WriteErrors {
        stdout: Some(io::Error::from_raw_os_error(libc::EPIPE)),
        stderr: None,
    };
    let status = close_output(errors, Err(command::failure("fatal")));
    assert_eq!(
        status.map_err(|failure| failure.message),
        Err(b"fatal".to_vec())
    );
}
#[cfg(unix)]
#[test]
fn a_failed_stderr_write_keeps_its_line_for_the_flush_at_exit() {
    let line = b"warning: w\n".to_vec();
    let causes: [fn() -> io::Error; 3] = [
        || io::Error::from_raw_os_error(libc::EPIPE),
        || io::Error::from_raw_os_error(libc::ENOSPC),
        || io::Error::from_raw_os_error(libc::EBADF),
    ];
    for cause in causes {
        assert_eq!(close_failing(false, cause), (Ok(0), line.clone()));
    }
    let again = || io::Error::from_raw_os_error(libc::EAGAIN);
    assert_eq!(close_failing(false, again).0, Err("WriteFailed".to_owned()));
    let errors = results::WriteErrors {
        stdout: None,
        stderr: Some(io::Error::from_raw_os_error(libc::ENOSPC)),
    };
    let status = close_output(errors, Err(command::failure("fatal")));
    assert_eq!(
        status.map_err(|failure| failure.message),
        Err(b"fatal".to_vec())
    );
}
#[test]
fn a_single_downloads_head_asks_for_the_checksum_when_the_download_checks_it() {
    use crt::runtime::ChecksumMode;
    use crt::s3::Header;
    let customer = Header::new("x-amz-server-side-encryption-customer-algorithm", "AES256");
    let mode = Header::new("x-amz-checksum-mode", "ENABLED");
    for (validate, runtime_mode, asks) in [
        (false, ChecksumMode::WhenRequired, false),
        (true, ChecksumMode::WhenRequired, true),
        (false, ChecksumMode::WhenSupported, true),
        (true, ChecksumMode::WhenSupported, true),
    ] {
        let mut request = request();
        request.headers.object = vec![customer.clone()];
        request.checksums.validate_downloads = validate;
        request.runtime.response_checksum_validation = runtime_mode;
        let mut expected = vec![customer.clone()];
        if asks {
            expected.push(mode.clone());
        }
        assert_eq!(
            head_object_headers(&request),
            expected,
            "{validate} {runtime_mode:?}"
        );
    }
}
