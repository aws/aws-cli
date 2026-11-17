use super::*;

fn progress(key: Option<u64>, bytes: u64, size: Option<u64>, timestamp_ns: u64) -> Event {
    Event::Progress {
        key,
        bytes,
        total_size: size,
        timestamp_ns,
    }
}
fn failure(key: u64, transferred: Option<u64>) -> Event {
    Event::Failure {
        key,
        line: line(),
        exception: b"failed".to_vec(),
        transferred,
        text: None,
    }
}

#[test]
fn queue_totals_unknown_sizes_and_first_timestamp_are_independent() {
    let mut recorder = Recorder::default();
    for (key, size) in [(1, Some(100)), (2, None), (3, Some(0)), (4, Some(300))] {
        recorder.record(&Event::Queued { key, size }, key * 100);
    }
    assert_eq!(recorder.expected_bytes_transferred, 400);
    assert_eq!(recorder.expected_files_transferred, 4);
    assert_eq!(recorder.start_time_ns, Some(100));
    assert!(!recorder.expected_totals_are_final());
    recorder.record(&Event::FinalTotal(5), 0);
    assert!(!recorder.expected_totals_are_final());
    recorder.record(&Event::Queued { key: 5, size: None }, 1000);
    assert!(recorder.expected_totals_are_final());
    assert!(recorder.has_remaining_progress());
}

#[test]
fn unknown_size_progress_learns_once_and_saturates_smaller_reported_size() {
    for (size, expected) in [(100, 100), (5, 10)] {
        let mut recorder = Recorder::default();
        recorder.record(&Event::Queued { key: 1, size: None }, 0);
        recorder.record(&progress(Some(1), 10, None, 0), 0);
        assert_eq!(recorder.expected_bytes_transferred, 10);
        recorder.record(&progress(Some(1), 20, Some(size), 0), 0);
        recorder.record(&progress(Some(1), 30, Some(500), 0), 0);
        assert_eq!(recorder.expected_bytes_transferred, expected);
        assert_eq!(recorder.bytes_transferred, 60);
    }
}

#[test]
fn keyless_and_unknown_transfer_progress_do_not_invent_sizes() {
    let mut recorder = Recorder::default();
    recorder.record(&Event::Queued { key: 1, size: None }, 1_000_000_000);
    recorder.record(&progress(None, 10, Some(100), 500_000_000), 0);
    recorder.record(&progress(Some(2), 20, Some(100), 1_000_000_000), 0);
    assert_eq!(recorder.bytes_transfer_speed, 0.0);
    recorder.record(&progress(None, 30, None, 3_000_000_000), 0);
    assert_eq!(recorder.expected_bytes_transferred, 0);
    assert_eq!(recorder.bytes_transfer_speed, 30.0);
    recorder.record(&failure(1, Some(60)), 0);
    assert_eq!(recorder.bytes_failed_to_transfer, 0);
}

#[test]
fn failure_remainders_use_each_transfer_and_explicit_live_byte_count() {
    for (size, progress_bytes, revealed, transferred, remainder) in [
        (Some(100), 0, None, None, 100),
        (Some(100), 40, None, None, 60),
        (None, 40, None, None, 0),
        (None, 40, Some(100), None, 60),
        (Some(100), 0, None, Some(30), 70),
        (Some(100), 0, None, Some(200), 0),
    ] {
        let mut recorder = Recorder::default();
        for key in 1..=2 {
            recorder.record(&Event::Queued { key, size }, 0);
            recorder.record(&progress(Some(key), progress_bytes, revealed, 0), 0);
            recorder.record(&failure(key, transferred), 0);
        }
        assert_eq!(recorder.bytes_failed_to_transfer, remainder * 2);
        assert_eq!(recorder.files_failed, 2);
        assert_eq!(recorder.files_transferred, 2);
    }
}

#[test]
fn terminal_counters_and_nontransfer_events_match_command_result() {
    let mut recorder = Recorder::default();
    for key in 1..=4 {
        recorder.record(
            &Event::Queued {
                key,
                size: Some(10),
            },
            0,
        );
    }
    for key in 1..=2 {
        recorder.record(&Event::Success { key, line: line() }, 0);
    }
    recorder.record(&failure(3, None), 0);
    recorder.record(&Event::Skip { key: 4 }, 0);
    recorder.record(&Event::FinalTotal(4), 0);
    assert!(!recorder.has_remaining_progress());
    for event in [
        Event::Warning(b"one".to_vec()),
        Event::Warning(b"two".to_vec()),
        Event::Fatal(b"fatal".to_vec()),
        Event::CtrlC,
    ] {
        recorder.record(&event, 0);
    }
    assert_eq!(
        recorder.command_result(),
        CommandResult {
            num_tasks_failed: 3,
            num_tasks_warned: 2
        }
    );
    let previous = recorder.clone();
    recorder.record(&Event::Diagnostic(b"diagnostic".to_vec()), 0);
    recorder.record(&Event::DryRun(line()), 0);
    assert_eq!(recorder, previous);
}

#[test]
fn completion_removes_tracking_and_accepts_all_path_encodings() {
    for source in [b"plain".as_slice(), "é".as_bytes(), b"\xff"] {
        for destination in [None, Some(b"destination".to_vec())] {
            let mut recorder = Recorder::default();
            recorder.record(
                &Event::Queued {
                    key: 1,
                    size: Some(10),
                },
                0,
            );
            recorder.record(
                &Event::Success {
                    key: 1,
                    line: Line {
                        transfer_type: TransferType::Upload,
                        source: source.to_vec(),
                        destination,
                    },
                },
                0,
            );
            recorder.record(&failure(1, None), 0);
            assert_eq!(recorder.bytes_failed_to_transfer, 0);
            assert_eq!(recorder.files_transferred, 2);
        }
    }
}
