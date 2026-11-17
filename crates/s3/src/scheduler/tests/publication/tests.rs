use super::*;
use crate::results::{self, Processor, Publisher};

#[derive(Debug)]
struct TypedOutput(Publisher);
impl Sink for TypedOutput {
    fn emit(&self, event: Event) -> Result<(), String> {
        self.0.publish(results::Event::Diagnostic(event.text));
        Ok(())
    }
    fn publish(&self, event: results::Event, _: bool) -> Result<(), String> {
        self.0.publish(event);
        Ok(())
    }
    fn progress(&self, bytes: u64) {
        self.0.add_progress(bytes);
    }
    fn wants_progress(&self) -> bool {
        self.0.wants_progress()
    }
}
fn attach(fixture: &mut Fixture, processor: &Processor) {
    Arc::get_mut(&mut fixture.scheduler)
        .expect("exclusive fixture")
        .sink = Arc::new(TypedOutput(processor.publisher()));
}

#[test]
fn queued_sizes_and_explicit_progress_reach_a_processor_without_a_printer() {
    let mut fixture = Fixture::new(true, false);
    let mut processor = Processor::new(None);
    attach(&mut fixture, &processor);
    assert!(!fixture.scheduler.wants_progress_hook());
    for (name, size) in [("prefix/first", 11), ("prefix/second", 22)] {
        fixture
            .scheduler
            .handle_download_entry(name, size, None)
            .expect("entry");
    }
    let first = lock(&fixture.control.callbacks)[0]
        .upgrade()
        .expect("retained callback");
    assert!(!first.wants_progress_hook());
    first.progress(5);
    drop(first);
    fixture.finish(0, TransferResult::default());
    fixture.finish(1, TransferResult::default());
    fixture.scheduler.drain();
    fixture.scheduler.notify_total_submissions();
    processor.publisher().close();
    processor
        .run(&mut Vec::new(), &mut Vec::new())
        .expect("processor");
    assert_eq!(processor.recorder.expected_bytes_transferred, 33);
    assert_eq!(processor.recorder.expected_files_transferred, 2);
    assert_eq!(processor.recorder.final_expected_files_transferred, Some(2));
    assert_eq!(processor.recorder.files_transferred, 2);
    assert_eq!(processor.recorder.bytes_transferred, 5);
}

#[test]
fn only_a_processor_that_draws_progress_asks_for_a_progress_hook() {
    let mode = |mode| {
        Some(results::PrinterConfig {
            mode,
            ..Default::default()
        })
    };
    for (printer, wants) in [
        (mode(results::Mode::Full), true),
        (mode(results::Mode::NoProgress), false),
        (mode(results::Mode::OnlyErrors), false),
        (None, false),
    ] {
        let mut fixture = Fixture::new(true, false);
        let processor = Processor::new(printer);
        attach(&mut fixture, &processor);
        assert_eq!(
            fixture.scheduler.wants_progress_hook(),
            wants,
            "{printer:?}"
        );
        fixture.submit("file");
        let callback = lock(&fixture.control.callbacks)[0]
            .upgrade()
            .expect("retained callback");
        assert_eq!(callback.wants_progress_hook(), wants, "{printer:?}");
        drop(callback);
        fixture.finish(0, TransferResult::default());
        fixture.scheduler.drain();
    }
}

#[test]
fn skip_and_interrupt_publish_one_cancel_line_without_transfer_lines() {
    let mut fixture = Fixture::configured(false, false, false, true, 4);
    let mut processor = Processor::new(Some(results::PrinterConfig {
        mode: results::Mode::NoProgress,
        ..Default::default()
    }));
    attach(&mut fixture, &processor);
    for name in ["existing", "pending"] {
        fixture
            .scheduler
            .handle_upload_entry(Path::new(name), None)
            .expect("upload entry");
    }
    fixture.finish(
        0,
        TransferResult {
            error_code: 1,
            response_status: 412,
            ..Default::default()
        },
    );
    fixture.scheduler.cancel();
    fixture.finish(
        1,
        TransferResult {
            error_code: crt::s3::CANCELED_ERROR_CODE,
            ..Default::default()
        },
    );
    fixture.scheduler.drain();
    processor.publisher().close();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    processor.run(&mut out, &mut err).expect("processor");
    assert_eq!(processor.recorder.files_skipped, 1);
    assert_eq!(processor.recorder.errors, 1);
    assert!(out.is_empty());
    assert_eq!(err, b"cancelled: ctrl-c received\n");
}

#[test]
fn submit_queue_preserves_archive_and_restoration_before_skip_rules() {
    let fixture = Fixture::new(true, false);
    fixture.control.immediate.store(true, Ordering::Release);
    let mut queue = SubmitQueue::new(fixture.scheduler.clone(), 2).expect("submit queue");
    queue
        .push_with_archive(
            "prefix/cold".into(),
            11,
            None,
            Archive {
                archived: true,
                restored: false,
            },
        )
        .expect("cold");
    queue
        .push_with_archive(
            "prefix/restored".into(),
            22,
            Some(7),
            Archive {
                archived: true,
                restored: true,
            },
        )
        .expect("restored");
    queue.close_and_join();
    fixture.scheduler.drain();
    assert_eq!(fixture.count(), 1);
    assert_eq!(fixture.stats().skipped, 1);
    assert_eq!(fixture.scheduler.finished().warned, 1);
    assert_eq!(lock(&fixture.control.submissions)[0].0, b"prefix/restored");
    assert_eq!(lock(&fixture.control.submissions)[0].3, Some(22));
}

#[test]
fn parent_references_follow_only_the_native_separator_rules() {
    for (key, escapes) in [
        ("prefix/../escape", true),
        ("prefix/..\\escape", cfg!(windows)),
        ("prefix/a/../safe", false),
    ] {
        let fixture = Fixture::new(true, false);
        fixture.control.immediate.store(true, Ordering::Release);
        fixture
            .scheduler
            .handle_download_entry(key, 1, None)
            .expect("entry");
        fixture.scheduler.drain();
        assert_eq!(fixture.count(), usize::from(!escapes), "{key}");
        assert_eq!(fixture.stats().skipped, u64::from(escapes), "{key}");
    }
}

#[test]
fn a_download_without_a_size_fails_ahead_of_every_rule() {
    let mut fixture = Fixture::configured(true, false, false, true, 4).with_native_root();
    Arc::get_mut(&mut fixture.scheduler)
        .expect("exclusive fixture")
        .request
        .glacier = transfer::GlacierPolicy::Skip;
    fixture.control.exists.store(true, Ordering::Release);
    let processor = Processor::new(Some(results::PrinterConfig {
        mode: results::Mode::NoProgress,
        ..Default::default()
    }));
    attach(&mut fixture, &processor);
    for local in [
        EntryLocal::Resolved,
        EntryLocal::ParentEscape("../existing.txt".into()),
    ] {
        fixture
            .scheduler
            .submit_entry(Entry {
                key: b"archived.txt".to_vec(),
                local_path: native_local("existing.txt").into(),
                local,
                size: None,
                size_listed: false,
                modified: None,
                archive: Archive {
                    archived: true,
                    restored: false,
                },
                condition: ObjectCondition::default(),
                case_name: None,
            })
            .expect("queued failure");
    }
    let stats = fixture.stats();
    assert_eq!((stats.submitted, stats.failed, stats.skipped), (2, 2, 0));
    assert_eq!(fixture.scheduler.finished().warned, 0);
    assert_eq!(
        (
            fixture.count(),
            fixture.control.parents.load(Ordering::Relaxed)
        ),
        (0, 0)
    );
    assert_released(&fixture, 2);
    let (err, totals) = totals(&fixture, processor);
    assert_eq!(totals, (2, 0, Some(2)));
    let sep = std::path::MAIN_SEPARATOR;
    assert_eq!(
        err,
        format!(
            "download failed: s3://bucket/archived.txt to local{sep}existing.txt \
             DownloadMissingContentLength\n"
        )
        .repeat(2)
    );
}
fn assert_released(fixture: &Fixture, destroyed: u64) {
    let state = lock(&fixture.scheduler.state);
    assert_eq!((state.destroyed, state.in_flight), (destroyed, 0));
}
fn totals(fixture: &Fixture, mut processor: Processor) -> (String, (u64, u64, Option<u64>)) {
    fixture.scheduler.notify_total_submissions();
    processor.publisher().close();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    processor.run(&mut out, &mut err).expect("processor");
    let recorder = &processor.recorder;
    (
        String::from_utf8_lossy(&err).into_owned(),
        (
            recorder.expected_files_transferred,
            recorder.expected_bytes_transferred,
            recorder.final_expected_files_transferred,
        ),
    )
}

#[test]
fn a_preparation_failure_is_a_queued_failure_without_bytes() {
    let mut fixture = Fixture::new(true, false).with_native_root();
    let processor = Processor::new(Some(results::PrinterConfig {
        mode: results::Mode::NoProgress,
        ..Default::default()
    }));
    attach(&mut fixture, &processor);
    fixture.control.parent_error.store(true, Ordering::Release);
    fixture
        .scheduler
        .handle_download_entry("prefix/unwritable/file.txt", 11, None)
        .expect("queued failure");
    fixture.control.parent_error.store(false, Ordering::Release);
    fixture.control.temp_error.store(true, Ordering::Release);
    fixture
        .scheduler
        .handle_download_entry("prefix/second.txt", 2, None)
        .expect("queued failure");
    assert_eq!(fixture.count(), 0);
    assert_eq!((fixture.stats().submitted, fixture.stats().failed), (2, 2));
    let (err, totals) = totals(&fixture, processor);
    assert_eq!(totals, (2, 0, Some(2)));
    assert_eq!(
        err,
        format!(
            "error: unable to create parent directory for {}: Permission denied\n\
             error: unable to prepare download destination {}: Out of memory\n",
            native_local("unwritable/file.txt"),
            native_local("second.txt")
        )
    );
}

#[derive(Debug, Default)]
struct LosesQueued;
impl Sink for LosesQueued {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: results::Event, _: bool) -> Result<(), String> {
        if matches!(event, results::Event::Queued { .. }) {
            Err("Out of memory".into())
        } else {
            Ok(())
        }
    }
}

#[test]
fn a_queued_result_lost_after_the_listing_returned_fails_the_submit_queue() {
    let mut fixture = Fixture::new(true, false);
    Arc::get_mut(&mut fixture.scheduler)
        .expect("exclusive fixture")
        .sink = Arc::new(LosesQueued);
    let mut queue = SubmitQueue::new(fixture.scheduler.clone(), 8).expect("submit queue");
    for (name, size) in [("first", 1), ("second", 2), ("third", 3)] {
        let _ = queue.push(format!("prefix/{name}"), size, None);
    }
    queue.close_and_join();
    assert!(queue.is_failed());
    assert_eq!(
        fixture.scheduler.finished().fatal.as_deref(),
        Some("Out of memory")
    );
    assert_eq!(fixture.control.parents.load(Ordering::Relaxed), 1);
    assert_eq!(fixture.count(), 0);
    assert_eq!(fixture.stats().submitted, 0);
    assert_released(&fixture, 0);
}

#[test]
fn a_preparation_failure_that_cannot_be_reported_stops_the_submit_queue() {
    let fixture = Fixture::new(true, false);
    fixture.control.parent_error.store(true, Ordering::Release);
    fixture.output.fail.store(true, Ordering::Release);
    let mut queue = SubmitQueue::new(fixture.scheduler.clone(), 8).expect("submit queue");
    for (name, size) in [("first", 1), ("second", 2), ("third", 3)] {
        let _ = queue.push(format!("prefix/dir/{name}"), size, None);
    }
    queue.close_and_join();
    assert!(queue.is_failed());
    assert_eq!(
        fixture.scheduler.finished().fatal.as_deref(),
        Some("WriteFailed")
    );
    assert_eq!(
        (
            fixture.control.parents.load(Ordering::Relaxed),
            fixture.count()
        ),
        (1, 0)
    );
    assert_eq!((fixture.stats().submitted, fixture.stats().failed), (1, 1));
    assert_released(&fixture, 1);
    assert_eq!(
        fixture
            .scheduler
            .handle_download_entry("prefix/other/fourth", 4, None),
        Err(Error::Output("WriteFailed".into()))
    );
    assert_released(&fixture, 2);
}

#[derive(Debug)]
struct BeforeRequest {
    control: Arc<Control>,
    published: Mutex<Vec<(results::Event, usize)>>,
}
impl Sink for BeforeRequest {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: results::Event, _: bool) -> Result<(), String> {
        let sent = lock(&self.control.submissions).len();
        lock(&self.published).push((event, sent));
        Ok(())
    }
}
fn one_object(remote: Option<&str>) -> (Fixture, Arc<BeforeRequest>) {
    let mut fixture = Fixture::configured(false, false, false, true, 512).with_native_root();
    let sink = Arc::new(BeforeRequest {
        control: Arc::clone(&fixture.control),
        published: Mutex::new(Vec::new()),
    });
    let scheduler = Arc::get_mut(&mut fixture.scheduler).expect("exclusive fixture");
    scheduler.request.object = Some(crate::cp::recursive::SingleObject {
        key: b"object".to_vec(),
        local_path: native_cwd().join("source.bin"),
        local: Default::default(),
        remote: remote.map(Into::into),
    });
    scheduler.sink = sink.clone();
    (fixture, sink)
}
fn single_entry() -> Entry {
    Entry {
        key: b"object".to_vec(),
        local_path: native_cwd().join("source.bin"),
        ..Entry::default()
    }
}

#[test]
fn a_one_object_total_is_published_with_its_queued_result_before_the_request() {
    for status in [200, 412] {
        let (fixture, sink) = one_object(None);
        assert_eq!(fixture.scheduler.request.engine_window(), 1);
        lock(&fixture.control.inspections).push_back(transfer::SourceInspection::Size(9));
        fixture
            .scheduler
            .submit_entry(single_entry())
            .expect("entry");
        assert_eq!(fixture.count(), 1);
        fixture.finish(
            0,
            TransferResult {
                error_code: i32::from(status == 412),
                response_status: status,
                ..Default::default()
            },
        );
        fixture.scheduler.drain();
        fixture.scheduler.finish_submissions(true);
        let published = lock(&sink.published).clone();
        assert_eq!(
            published[..2],
            [
                (
                    results::Event::Queued {
                        key: 0,
                        size: Some(9)
                    },
                    0
                ),
                (results::Event::FinalTotal(1), 0),
            ]
        );
        let after: Vec<_> = published[2..].iter().map(|(event, _)| event).collect();
        if status == 412 {
            assert_eq!(after, [&results::Event::Skip { key: 0 }]);
        } else {
            assert!(matches!(
                after[..],
                [results::Event::Success { key: 0, .. }]
            ));
        }
    }
}

#[test]
fn a_one_object_entry_that_queues_nothing_finishes_with_a_total_of_zero() {
    let (fixture, sink) = one_object(None);
    lock(&fixture.control.inspections).push_back(transfer::SourceInspection::Skipped(
        transfer::SourceSkip::Special,
    ));
    fixture
        .scheduler
        .submit_entry(single_entry())
        .expect("entry");
    let totals = || {
        lock(&sink.published)
            .iter()
            .filter(|(event, _)| {
                matches!(
                    event,
                    results::Event::Queued { .. } | results::Event::FinalTotal(_)
                )
            })
            .map(|(event, _)| event.clone())
            .collect::<Vec<_>>()
    };
    assert!(totals().is_empty());
    fixture.scheduler.finish_submissions(true);
    assert_eq!(totals(), [results::Event::FinalTotal(0)]);
    assert_eq!(fixture.count(), 0);
}

#[test]
fn a_one_object_result_names_its_remote_side_as_given() {
    for (remote, destination) in [
        (Some("s3://bucket"), b"s3://bucket".as_slice()),
        (None, b"s3://bucket/object".as_slice()),
    ] {
        let (fixture, sink) = one_object(remote);
        fixture.control.immediate.store(true, Ordering::Release);
        fixture
            .scheduler
            .submit_entry(single_entry())
            .expect("entry");
        fixture.scheduler.drain();
        let published = lock(&sink.published);
        let line = published
            .iter()
            .find_map(|(event, _)| match event {
                results::Event::Success { line, .. } => Some(line.clone()),
                _ => None,
            })
            .expect("success");
        let source = format!(".{}source.bin", std::path::MAIN_SEPARATOR);
        assert_eq!(line.source, source.as_bytes());
        assert_eq!(line.destination.as_deref(), Some(destination));
    }
}
