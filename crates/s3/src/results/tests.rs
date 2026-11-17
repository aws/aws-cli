#![expect(
    clippy::expect_used,
    reason = "result fixtures fail at the violated contract"
)]
use super::*;
mod printer;
mod processor;
mod recorder;
fn line() -> Line {
    Line {
        transfer_type: TransferType::Download,
        source: "s3://bucket/key".into(),
        destination: Some("file".into()),
    }
}
#[test]
fn recorder_tracks_unknown_sizes_failed_remainders_and_command_outcomes() {
    let mut r = Recorder::default();
    r.record(&Event::Queued { key: 1, size: None }, 0);
    r.record(
        &Event::Progress {
            key: Some(1),
            bytes: 10,
            total_size: None,
            timestamp_ns: 1_000_000_000,
        },
        0,
    );
    assert_eq!(r.expected_bytes_transferred, 10);
    r.record(
        &Event::Progress {
            key: Some(1),
            bytes: 10,
            total_size: Some(100),
            timestamp_ns: 2_000_000_000,
        },
        0,
    );
    assert_eq!(r.expected_bytes_transferred, 100);
    assert_eq!(r.bytes_transfer_speed, 10.0);
    r.record(
        &Event::Failure {
            key: 1,
            line: line(),
            exception: "failed".into(),
            transferred: None,
            text: None,
        },
        0,
    );
    assert_eq!(r.bytes_failed_to_transfer, 80);
    r.record(&Event::Warning("warning".into()), 0);
    r.record(&Event::FinalTotal(1), 0);
    assert!(!r.has_remaining_progress());
    assert_eq!(
        r.command_result(),
        CommandResult {
            num_tasks_failed: 1,
            num_tasks_warned: 1
        }
    );
}
#[test]
fn first_progress_is_immediate_and_later_updates_are_event_throttled() {
    let mut r = Recorder::default();
    let mut p = Printer::new(PrinterConfig {
        frequency_s: 10,
        ..Default::default()
    });
    let mut out = Vec::new();
    let mut err = Vec::new();
    for event in [
        Event::Queued {
            key: 1,
            size: Some(100),
        },
        Event::FinalTotal(1),
    ] {
        r.record(&event, 0);
    }
    for (time, bytes) in [(0, 10), (1_000_000_000, 20), (10_000_000_000, 30)] {
        let event = Event::Progress {
            key: Some(1),
            bytes,
            total_size: None,
            timestamp_ns: time,
        };
        r.record(&event, time);
        p.handle(&r, &event, time, &mut out, &mut err);
    }
    let text = String::from_utf8(out).expect("valid result fixture");
    assert_eq!(text.matches('\r').count(), 2);
    assert!(text.starts_with("Completed 10 Bytes/100 Bytes"));
    assert!(text.contains("Completed 60 Bytes/100 Bytes"));
}
#[test]
fn processor_folds_progress_before_completion_and_disables_after_fatal() {
    let mut p = Processor::new(Some(PrinterConfig {
        oneline: false,
        ..Default::default()
    }));
    let sender = p.publisher();
    sender.publish(Event::Queued {
        key: 1,
        size: Some(100),
    });
    sender.publish(Event::FinalTotal(1));
    sender.add_progress(100);
    sender.publish(Event::Success {
        key: 1,
        line: line(),
    });
    sender.publish(Event::CtrlC);
    sender.publish(Event::CtrlC);
    sender.publish(Event::Warning("late".into()));
    sender.publish(Event::Diagnostic("diagnostic".into()));
    sender.close();
    let mut out = Vec::new();
    let mut err = Vec::new();
    p.run_with_clock(&mut out, &mut err, || 1_000_000_000)
        .expect("valid result fixture");
    let out = String::from_utf8(out).expect("valid result fixture");
    assert!(
        out.find("Completed").expect("valid result fixture")
            < out.find("download:").expect("valid result fixture")
    );
    assert_eq!(p.recorder.bytes_transferred, 100);
    assert_eq!(p.recorder.errors, 1);
    assert!(
        !String::from_utf8(err)
            .expect("valid result fixture")
            .contains("late")
    );
}
#[test]
fn quiet_records_and_only_errors_suppresses_success_and_progress() {
    for flags in [
        Flags {
            quiet: true,
            ..Default::default()
        },
        Flags {
            only_show_errors: true,
            ..Default::default()
        },
        Flags {
            progress: false,
            ..Default::default()
        },
    ] {
        let mut p = Processor::new(flags.select());
        let sender = p.publisher();
        assert!(!sender.wants_progress());
        sender.publish(Event::Queued {
            key: 1,
            size: Some(100),
        });
        sender.publish(Event::Success {
            key: 1,
            line: line(),
        });
        sender.publish(Event::Warning("warn".into()));
        sender.close();
        let mut out = Vec::new();
        let mut err = Vec::new();
        p.run(&mut out, &mut err).expect("valid result fixture");
        assert_eq!(p.recorder.files_transferred, 1);
        assert_eq!(p.recorder.files_warned, 1);
        if flags.quiet || flags.only_show_errors {
            assert!(out.is_empty());
        }
        assert_eq!(err.is_empty(), flags.quiet);
    }
}
#[test]
fn unbounded_publish_does_not_wait_for_a_slow_printer() {
    let mut p = Processor::new(None);
    let sender = p.publisher();
    std::thread::spawn(move || {
        for _ in 0..10000 {
            sender.publish(Event::Warning("w".into()));
        }
        sender.close();
    })
    .join()
    .expect("valid result fixture");
    p.run(&mut Vec::new(), &mut Vec::new())
        .expect("valid result fixture");
    assert_eq!(p.recorder.files_warned, 10000);
}
#[test]
fn failed_stdout_does_not_block_recording_or_stderr() {
    struct Broken;
    impl std::io::Write for Broken {
        fn write(&mut self, _: &[u8]) -> std::io::Result<usize> {
            Err(std::io::ErrorKind::BrokenPipe.into())
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }
    let mut p = Processor::new(Some(PrinterConfig {
        mode: Mode::NoProgress,
        ..Default::default()
    }));
    let sender = p.publisher();
    sender.publish(Event::Queued { key: 1, size: None });
    sender.publish(Event::Success {
        key: 1,
        line: line(),
    });
    sender.publish(Event::Warning("warning".into()));
    sender.close();
    let mut err = Vec::new();
    assert!(p.run(&mut Broken, &mut err).is_err());
    assert_eq!(p.recorder.files_transferred, 1);
    assert_eq!(err, b"warning\n");
}

#[test]
fn result_lines_keep_raw_bytes_on_stdout_and_escape_them_on_stderr() {
    let mut processor = Processor::new(Some(PrinterConfig {
        mode: Mode::NoProgress,
        ..Default::default()
    }));
    let sender = processor.publisher();
    let line = Line {
        transfer_type: TransferType::Upload,
        source: b"local-\xff".to_vec(),
        destination: Some(b"s3://bucket/remote-\xfe".to_vec()),
    };
    sender.publish(Event::Success {
        key: 1,
        line: line.clone(),
    });
    sender.publish(Event::Failure {
        key: 2,
        line,
        exception: b"bad-\xfd".to_vec(),
        transferred: None,
        text: None,
    });
    sender.publish(Event::Warning(b"warning-\xfc".to_vec()));
    sender.close();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    processor
        .run(&mut out, &mut err)
        .expect("raw result output");
    assert_eq!(out, b"upload: local-\xff to s3://bucket/remote-\xfe\n");
    assert_eq!(
        err,
        [
            br"upload failed: local-\udcff to s3://bucket/remote-\udcfe bad-\udcfd".as_slice(),
            b"\n",
            br"warning-\udcfc",
            b"\n",
        ]
        .concat()
    );
}

#[test]
fn speed_divides_the_bytes_by_the_elapsed_seconds() {
    for (bytes, elapsed_ns, speed, rate) in [
        (7, 70_000_000, 99.999_999_999_999_99, "(99 Bytes/s)"),
        (1998, 2_160_000_000, 924.999_999_999_999_9, "(924 Bytes/s)"),
    ] {
        let mut recorder = Recorder::default();
        let start = 5_000_000_000;
        let queued = Event::Queued {
            key: 1,
            size: Some(10_000),
        };
        recorder.record(&queued, start);
        let progress = Event::Progress {
            key: Some(1),
            bytes,
            total_size: None,
            timestamp_ns: start + elapsed_ns,
        };
        recorder.record(&progress, start + elapsed_ns);
        assert_eq!(recorder.bytes_transfer_speed.to_bits(), f64::to_bits(speed));
        assert_eq!(
            recorder.bytes_transfer_speed.to_bits(),
            (bytes as f64 / (elapsed_ns as f64 / 1e9)).to_bits()
        );
        let mut printer = Printer::new(PrinterConfig::default());
        let (mut out, mut err) = (Vec::new(), Vec::new());
        printer.handle(&recorder, &progress, start + elapsed_ns, &mut out, &mut err);
        let text = String::from_utf8(out).expect("progress text");
        assert!(text.contains(rate), "{text:?}");
    }
}

#[test]
fn a_started_processor_drains_on_its_own_thread_until_stopped() {
    let (mut out, mut err) = (Vec::new(), Vec::new());
    let caller = std::thread::current().id();
    std::thread::scope(|scope| {
        let processor = Processor::new(Some(PrinterConfig {
            mode: Mode::NoProgress,
            ..Default::default()
        }));
        let sender = processor.publisher();
        let running = processor
            .start_with(scope, &mut out, &mut err, |scope, drain| {
                spawn_drain(
                    scope,
                    Box::new(move || {
                        assert_ne!(std::thread::current().id(), caller);
                        drain()
                    }),
                )
            })
            .expect("processor thread");
        sender.publish(Event::Success {
            key: 1,
            line: line(),
        });
        sender.publish(Event::Warning("warning".into()));
        running.stop().expect("printed results");
        sender.publish(Event::Warning("late".into()));
    });
    assert_eq!(out, b"download: s3://bucket/key to file\n");
    assert_eq!(err, b"warning\n");
    let (mut out, mut err) = (Vec::new(), std::io::sink());
    std::thread::scope(|scope| {
        let processor = Processor::new(Some(PrinterConfig::default()));
        let running = processor
            .start(scope, &mut out, &mut err)
            .expect("processor thread");
        drop(running);
    });
    assert!(out.is_empty());
}

#[test]
fn the_started_thread_drains_results_published_from_other_threads() {
    let (mut out, mut err) = (Vec::new(), Vec::new());
    std::thread::scope(|scope| {
        let processor = Processor::new(Some(PrinterConfig {
            mode: Mode::NoProgress,
            ..Default::default()
        }));
        let sender = processor.publisher();
        let running = processor
            .start(scope, &mut out, &mut err)
            .expect("processor thread");
        std::thread::scope(|publishers| {
            for key in 0..4 {
                let sender = sender.clone();
                publishers.spawn(move || {
                    sender.publish(Event::Queued { key, size: Some(1) });
                    sender.add_progress(1);
                    sender.publish(Event::Success {
                        key,
                        line: Line {
                            transfer_type: TransferType::Upload,
                            source: b"src".to_vec(),
                            destination: Some(b"dest".to_vec()),
                        },
                    });
                });
            }
        });
        running.stop().expect("printed results");
    });
    assert_eq!(out, b"upload: src to dest\n".repeat(4));
    assert!(err.is_empty());
}

#[cfg(unix)]
#[test]
fn a_refused_processor_thread_is_the_start_error() {
    let processor = Processor::new(Some(PrinterConfig::default()));
    let sender = processor.publisher();
    let (mut out, mut err) = (std::io::sink(), std::io::sink());
    let error = std::thread::scope(|scope| {
        processor
            .start_with(scope, &mut out, &mut err, |_, _| {
                Err(std::io::Error::from_raw_os_error(libc::EAGAIN))
            })
            .expect_err("refused thread")
    });
    assert_eq!(error.kind(), std::io::ErrorKind::WouldBlock);
    sender.publish(Event::Warning("unprocessed".into()));
    assert_eq!(sender.take_events().len(), 1);
}
