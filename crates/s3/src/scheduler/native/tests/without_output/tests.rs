#![expect(
    clippy::expect_used,
    reason = "deterministic request fixtures fail immediately on invalid state"
)]
use super::*;

fn first_temp_name(name: &str) -> String {
    format!("{name}.{TEMP_NAME_ID:016x}")
}
fn failed_after_body() -> TransferResult {
    TransferResult {
        error_code: 1,
        response_status: 200,
        body_delivered: true,
        ..TransferResult::default()
    }
}
fn destroyed(f: &Fixture) -> u64 {
    lock(&f.scheduler.state).destroyed
}
fn request_counters(f: &Fixture) -> (u64, u64) {
    let stats = f.stats();
    (stats.custom_writer_requests, stats.recv_file_requests)
}

#[test]
fn a_download_without_a_size_fails_before_reaching_the_crt() {
    let f = Fixture::one_object(WriterMode::Pwrite);
    let path = f.destination_path();
    f.scheduler
        .submit(Job {
            direction: crate::transfer::Direction::Download,
            raw_key: b"key".to_vec(),
            request_key: "key".into(),
            local_path: path.clone(),
            temp_path: Some(path),
            size: None,
            size_listed: false,
            size_changed: AtomicBool::new(false),
            modified: None,
            condition: ObjectCondition::default(),
            case_name: None,
            output: Mutex::default(),
            custom_writer: AtomicBool::new(false),
        })
        .expect("queued");
    f.drain();

    assert_eq!(f.runtime.count(), 0);
    assert_eq!(f.stats().failed, 1);
    let events = lock(&f.sink.0);
    assert!(events.iter().any(|event| matches!(
        event,
        results::Event::Failure { exception, .. } if exception == b"DownloadMissingContentLength"
    )));
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test follows the transfer from its GET to its failure"
)]
fn a_key_at_the_roots_parent_sends_its_get_and_writes_nothing() {
    for key in ["../outside/..", "../"] {
        let f = Fixture::configured(one_object_service(WriterMode::Pwrite), 1, |request| {
            request.max_in_flight = 1;
            request.local_root = request.local_root.join("destination");
        });
        fs::create_dir(f.directory.0.join("destination")).expect("destination root");
        f.submit(key, 5);

        assert_eq!(f.runtime.count(), 1);
        let sent = f.runtime.sent(0);
        assert!(sent.body_consumer);
        assert_eq!(sent.filepath, None);
        assert_eq!(f.service.active_outputs(), 0);
        assert!(f.runtime.deliver_body(0, b"hello").is_err());
        f.runtime.finish(0, failed_after_body());
        f.runtime.shutdown(0);
        f.drain();

        assert_eq!(f.stats().failed, 1, "{key}");
        assert_eq!(destroyed(&f), 1);
        assert_eq!(f.stray_files(), 1);
        let root = fs::read_dir(f.directory.0.join("destination")).expect("root");
        assert_eq!(root.count(), 0);
        let events = lock(&f.sink.0);
        assert!(events.iter().any(|event| matches!(
            event,
            results::Event::Failure { exception, .. }
                if exception == b"DownloadDestinationOutsideRoot"
        )));
    }
}

// A listed key holding a NUL names a path no file system represents. The CRT
// would cut the path at the NUL and replace the file its prefix names, so no
// output receives a temp path holding one: that download sends its GET
// without an output. A parent holding one is not created, and that download
// fails before any GET. Either fails and leaves the file the prefix names
// alone, for either writer and under `--no-overwrite`.
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test keeps both writers and both overwrite modes"
)]
fn a_key_holding_a_nul_fails_without_touching_the_file_its_prefix_names() {
    for (key, exception, gets) in [
        ("file\0.backup", "DownloadDestinationEmbeddedNull", 1),
        ("file\0x/report", "Invalid path name", 0),
    ] {
        for (mode, no_overwrite) in [
            (WriterMode::Crt, false),
            (WriterMode::Pwrite, false),
            (WriterMode::Crt, true),
            (WriterMode::Pwrite, true),
        ] {
            let f = Fixture::configured(one_object_service(mode), 1, |request| {
                request.max_in_flight = 1;
                request.no_overwrite = no_overwrite;
            });
            fs::write(f.destination_path(), b"old").expect("existing destination");
            f.submit(key, 5);
            let output_prepared = f.service.active_outputs() != 0;
            assert_eq!(f.runtime.count(), gets, "{key:?}");
            for index in 0..gets {
                let sent = f.runtime.sent(index);
                assert!(sent.body_consumer);
                assert_eq!(sent.filepath, None);
                f.runtime.finish(index, failed_after_body());
                f.runtime.shutdown(index);
            }
            f.drain();

            assert!(!output_prepared);
            assert_eq!(f.destination(), b"old");
            assert_eq!(f.stray_files(), 0);
            assert_eq!(f.stats().failed, 1);
            assert_eq!(destroyed(&f), 1);
            assert_eq!(request_counters(&f), (0, 0));
            let events = lock(&f.sink.0);
            assert!(
                events.iter().any(|event| matches!(
                    event,
                    results::Event::Failure { exception: name, .. } if name == exception.as_bytes()
                )),
                "{key:?} {mode:?}"
            );
        }
    }
}

#[test]
fn a_crt_download_whose_file_cannot_be_opened_still_sends_its_get() {
    let f = Fixture::one_object(WriterMode::Crt);
    *lock(&f.runtime.recv_file_failure) = Some(42);
    f.submit("file", 5);

    assert_eq!(f.runtime.count(), 2);
    assert!(!f.runtime.sent(0).body_consumer);
    assert!(f.runtime.sent(1).body_consumer);
    assert!(f.runtime.deliver_body(1, b"hello").is_err());
    f.runtime.finish(1, failed_after_body());
    f.runtime.shutdown(1);
    f.drain();

    assert_eq!(f.destination(), b"old");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.stats().failed, 1);
    assert_eq!(destroyed(&f), 1);
    assert_eq!(request_counters(&f), (0, 0));
}

#[test]
fn a_refused_crt_submission_counts_no_request_and_keeps_the_destination() {
    let f = Fixture::one_object(WriterMode::Crt);
    *lock(&f.runtime.submit_failure) = Some(42);
    f.submit("file", 5);
    f.drain();

    assert_eq!(f.destination(), b"old");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.stats().failed, 1);
    assert_eq!(request_counters(&f), (0, 0));
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Answer {
    Body,
    Empty,
    ServiceError,
}
fn rendered(f: &Fixture) -> Vec<u8> {
    let mut processor = results::Processor::new(Some(results::PrinterConfig {
        mode: results::Mode::NoProgress,
        ..Default::default()
    }));
    let publisher = processor.publisher();
    for event in lock(&f.sink.0).drain(..) {
        publisher.publish(event);
    }
    publisher.close();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    processor.run(&mut out, &mut err).expect("rendered results");
    [out, err].concat()
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test keeps every outcome of the GET sent without an output"
)]
fn an_output_that_cannot_be_prepared_still_sends_its_get() {
    for answer in [Answer::Body, Answer::Empty, Answer::ServiceError] {
        let f = Fixture::configured(one_object_service(WriterMode::Pwrite), 1, |request| {
            request.max_in_flight = 1;
            request.object = Some(crate::cp::recursive::SingleObject {
                key: b"as typed".to_vec(),
                remote: Some("s3://bucket/as typed".into()),
                ..Default::default()
            });
        });
        fs::create_dir(f.directory.0.join(first_temp_name("file"))).expect("blocker");
        f.scheduler
            .submit_entry(Entry {
                key: b"as typed".to_vec(),
                local_path: f.destination_path(),
                size: Some(5),
                ..Entry::default()
            })
            .expect("entry");
        assert!(f.runtime.sent(0).body_consumer);
        assert_eq!(f.service.active_outputs(), 1);
        match answer {
            Answer::Body => {
                assert!(f.runtime.deliver_body(0, b"hello").is_err());
                f.runtime.progress(0, 5);
                f.runtime.finish(0, failed_after_body());
            }
            Answer::Empty => f.runtime.finish(0, ok()),
            Answer::ServiceError => f.runtime.finish(
                0,
                TransferResult {
                    error_code: 1,
                    response_status: 403,
                    ..TransferResult::default()
                },
            ),
        }
        f.runtime.shutdown(0);
        f.drain();
        f.scheduler.finish_submissions(true);

        let transferred = lock(&f.sink.0).iter().find_map(|event| match event {
            results::Event::Failure { transferred, .. } => Some(*transferred),
            _ => None,
        });
        assert_eq!(transferred, Some(Some(0)));
        let printed = rendered(&f);
        assert!(
            printed.starts_with(b"download failed: s3://bucket/as typed to "),
            "{}",
            String::from_utf8_lossy(&printed)
        );
        assert_eq!(
            printed.ends_with(b"file Is a directory\n"),
            answer != Answer::ServiceError,
            "{}",
            String::from_utf8_lossy(&printed)
        );
        assert_eq!(f.runtime.count(), 1);
        assert_eq!(f.stats().failed, 1);
        assert_eq!(destroyed(&f), 1);
        assert_eq!(f.stray_files(), 1);
        assert_eq!(f.service.active_outputs(), 0);
        assert_eq!(request_counters(&f), (0, 0));
    }
}
