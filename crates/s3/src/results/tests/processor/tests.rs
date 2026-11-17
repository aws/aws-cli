use super::*;

fn failure(key: u64, transferred: u64) -> Event {
    Event::Failure {
        key,
        line: line(),
        exception: b"failed".to_vec(),
        transferred: Some(transferred),
        text: None,
    }
}
fn finish(processor: &mut Processor) -> (Vec<u8>, Vec<u8>) {
    processor.publisher().close();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    processor
        .run_with_clock(&mut out, &mut err, || 1_000_000_000)
        .expect("result processor");
    (out, err)
}

#[test]
fn completion_marks_include_only_preceding_progress_and_each_failure_remainder() {
    let mut processor = Processor::new(Some(PrinterConfig {
        oneline: false,
        ..Default::default()
    }));
    let sender = processor.publisher();
    for key in 1..=2 {
        sender.publish(Event::Queued {
            key,
            size: Some(100),
        });
    }
    sender.publish(Event::FinalTotal(2));
    sender.add_progress(20);
    sender.publish(failure(1, 20));
    sender.add_progress(100);
    sender.publish(Event::Success {
        key: 2,
        line: line(),
    });
    let (out, _) = finish(&mut processor);
    let output = String::from_utf8(out).expect("progress text");
    assert!(output.starts_with("Completed 20 Bytes/200 Bytes"));
    assert!(output.contains("Completed 100 Bytes/200 Bytes"));
    assert!(output.contains("Completed 200 Bytes/200 Bytes"));
    assert!(!output.contains("280 Bytes"));
    assert_eq!(processor.recorder.bytes_transferred, 120);
    assert_eq!(processor.recorder.bytes_failed_to_transfer, 80);
}

#[test]
fn warning_folds_preceding_live_progress_before_rendering() {
    let mut processor = Processor::new(Some(PrinterConfig::default()));
    let sender = processor.publisher();
    sender.publish(Event::Queued {
        key: 1,
        size: Some(100),
    });
    sender.add_progress(10);
    sender.publish(Event::Warning(b"warn".to_vec()));
    let (out, err) = finish(&mut processor);
    assert!(out.starts_with(b"Completed 10 Bytes/~100 Bytes"));
    assert!(err.starts_with(b"warn "));
    assert_eq!(processor.recorder.bytes_transferred, 10);
}

#[test]
fn closed_queue_rejects_later_results_and_progress() {
    let mut processor = Processor::new(Some(PrinterConfig::default()));
    let sender = processor.publisher();
    sender.publish(Event::Queued {
        key: 1,
        size: Some(100),
    });
    sender.publish(Event::FinalTotal(1));
    sender.close();
    sender.add_progress(100);
    sender.publish(Event::Success {
        key: 1,
        line: line(),
    });
    let (out, err) = finish(&mut processor);
    assert!(out.is_empty() && err.is_empty());
    assert_eq!(processor.recorder.bytes_transferred, 0);
    assert_eq!(processor.recorder.files_transferred, 0);
}

#[test]
fn fatal_and_control_c_end_results_once_but_preserve_diagnostics() {
    for terminal in [Event::Fatal(b"failed".to_vec()), Event::CtrlC] {
        let mut processor = Processor::new(Some(PrinterConfig::default()));
        let sender = processor.publisher();
        sender.publish(terminal.clone());
        sender.publish(terminal);
        sender.publish(Event::Warning(b"late warning".to_vec()));
        sender.publish(Event::Success {
            key: 1,
            line: line(),
        });
        sender.publish(Event::Diagnostic(b"diagnostic".to_vec()));
        let (out, err) = finish(&mut processor);
        assert!(out.is_empty());
        assert_eq!(err.iter().filter(|&&byte| byte == b'\n').count(), 2);
        assert!(err.ends_with(b"diagnostic\n"));
        assert_eq!(
            processor.recorder.command_result(),
            CommandResult {
                num_tasks_failed: 1,
                num_tasks_warned: 0
            }
        );
    }
}

#[test]
fn quiet_diagnostics_are_opt_in_and_do_not_change_transfer_counts() {
    let mut processor = Processor::with_diagnostics(None);
    let sender = processor.publisher();
    sender.publish(Event::Warning(b"quiet".to_vec()));
    sender.publish(Event::Diagnostic(b"stats".to_vec()));
    let (out, err) = finish(&mut processor);
    assert!(out.is_empty());
    assert_eq!(err, b"stats\n");
    assert_eq!(processor.recorder.files_warned, 1);
}

#[test]
fn threaded_publisher_wakes_and_drains_complete_transfers() {
    let mut processor = Processor::new(None);
    let sender = processor.publisher();
    let worker = std::thread::spawn(move || {
        for key in 0..1000 {
            sender.publish(Event::Queued { key, size: None });
            sender.publish(Event::Success { key, line: line() });
        }
        sender.publish(Event::FinalTotal(1000));
        sender.close();
    });
    processor
        .run(&mut Vec::new(), &mut Vec::new())
        .expect("concurrent processor");
    worker.join().expect("publisher");
    assert_eq!(processor.recorder.files_transferred, 1000);
    assert!(!processor.recorder.has_remaining_progress());
}

#[test]
fn progress_after_last_completion_is_recorded_without_redrawing() {
    let mut processor = Processor::new(Some(PrinterConfig::default()));
    let sender = processor.publisher();
    sender.publish(Event::Queued {
        key: 1,
        size: Some(100),
    });
    sender.publish(Event::FinalTotal(1));
    sender.publish(Event::Success {
        key: 1,
        line: line(),
    });
    sender.add_progress(100);
    sender.publish(Event::Warning(b"warning".to_vec()));
    let (out, err) = finish(&mut processor);
    assert_eq!(out, b"download: s3://bucket/key to file\n");
    assert_eq!(err, b"warning\n");
    assert_eq!(processor.recorder.bytes_transferred, 100);
}

#[test]
fn owned_events_survive_original_buffers_and_dropping_an_unstarted_processor() {
    let mut source = b"source".to_vec();
    let mut destination = b"destination".to_vec();
    let mut exception = b"exception".to_vec();
    let event = Event::Failure {
        key: 1,
        line: Line {
            transfer_type: TransferType::Upload,
            source: source.clone(),
            destination: Some(destination.clone()),
        },
        exception: exception.clone(),
        transferred: None,
        text: None,
    };
    source.clear();
    destination.clear();
    exception.clear();
    let mut processor = Processor::new(Some(PrinterConfig {
        mode: Mode::NoProgress,
        ..Default::default()
    }));
    processor.publisher().publish(event.clone());
    let (_, err) = finish(&mut processor);
    assert_eq!(err, b"upload failed: source to destination exception\n");
    let processor = Processor::new(None);
    processor.publisher().publish(event);
    drop(processor);
}

#[derive(Debug)]
struct ProgressSignal {
    output: Vec<u8>,
    printed: Option<std::sync::mpsc::Sender<()>>,
}
impl std::io::Write for ProgressSignal {
    fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
        self.output.extend_from_slice(bytes);
        if bytes.contains(&b'\r')
            && let Some(sender) = self.printed.take()
        {
            let _ = sender.send(());
        }
        Ok(bytes.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}
#[test]
fn live_progress_wakes_the_processor_without_a_following_result() {
    let mut processor = Processor::new(Some(PrinterConfig::default()));
    let sender = processor.publisher();
    sender.publish(Event::Queued {
        key: 1,
        size: Some(100),
    });
    sender.publish(Event::FinalTotal(1));
    let (printed, receiver) = std::sync::mpsc::channel();
    let publisher = std::thread::spawn(move || {
        sender.add_progress(10);
        let observed = receiver
            .recv_timeout(std::time::Duration::from_secs(5))
            .is_ok();
        sender.publish(Event::Success {
            key: 1,
            line: line(),
        });
        sender.close();
        observed
    });
    let mut stdout = ProgressSignal {
        output: Vec::new(),
        printed: Some(printed),
    };
    processor
        .run(&mut stdout, &mut Vec::new())
        .expect("live result processor");
    assert!(publisher.join().expect("live publisher"));
    assert!(stdout.output.starts_with(b"Completed 10 Bytes/100 Bytes"));
    assert_eq!(processor.recorder.bytes_transferred, 10);
}

fn step(processor: &mut Processor) -> (String, String) {
    let publisher = processor.publisher();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    processor
        .run_with_clock(&mut out, &mut err, || {
            publisher.close();
            1_000_000_000
        })
        .expect("result processor");
    let text = |bytes| String::from_utf8(bytes).expect("result text");
    (text(out), text(err))
}
fn queued(key: u64, size: u64) -> Event {
    Event::Queued {
        key,
        size: Some(size),
    }
}
fn success(key: u64) -> Event {
    Event::Success { key, line: line() }
}
fn multiline() -> Processor {
    Processor::new(Some(PrinterConfig {
        oneline: false,
        ..Default::default()
    }))
}
const FAILED_LINE: &str = "download failed: s3://bucket/key to file failed\n";

#[test]
fn a_transfers_progress_prints_before_its_done_line_in_the_same_batch() {
    let mut processor = Processor::new(Some(PrinterConfig::default()));
    let sender = processor.publisher();
    sender.publish(queued(1, 10));
    sender.publish(Event::FinalTotal(1));
    sender.add_progress(10);
    sender.publish(success(1));
    let (out, err) = step(&mut processor);
    let progress = "Completed 10 Bytes/10 Bytes (0 Bytes/s) with 1 file(s) remaining";
    let done = "download: s3://bucket/key to file";
    let padding = " ".repeat(progress.len() - done.len());
    assert_eq!(out, format!("{progress}\r{done}{padding}\n"));
    assert_eq!(err, "");
}

#[test]
fn a_done_result_folds_only_the_bytes_reported_ahead_of_it() {
    let mut processor = Processor::new(Some(PrinterConfig::default()));
    let sender = processor.publisher();
    sender.publish(queued(1, 10));
    sender.add_progress(10);
    sender.publish(success(1));
    sender.publish(queued(2, 5));
    sender.add_progress(5);
    let (out, _) = step(&mut processor);
    let first = "Completed 10 Bytes/~10 Bytes (0 Bytes/s) with ~1 file(s) remaining \
                 (calculating...)";
    let done = "download: s3://bucket/key to file";
    let padding = " ".repeat(first.len() - done.len());
    let redrawn = "Completed 10 Bytes/~10 Bytes (0 Bytes/s) with ~0 file(s) remaining \
                   (calculating...)";
    let last = "Completed 15 Bytes/~15 Bytes (0 Bytes/s) with ~1 file(s) remaining \
                (calculating...)";
    assert_eq!(
        out,
        format!("{first}\r{done}{padding}\n{redrawn}\r{last}\r")
    );
    assert_eq!(processor.recorder.bytes_transferred, 15);
}

#[test]
fn a_failures_remainder_keeps_folded_bytes_within_the_totals() {
    let mut processor = multiline();
    let sender = processor.publisher();
    sender.publish(queued(1, 10));
    sender.add_progress(5);
    sender.publish(failure(1, 5));
    sender.publish(queued(2, 10));
    sender.add_progress(7);
    let (out, err) = step(&mut processor);
    assert_eq!(
        out,
        "Completed 5 Bytes/~10 Bytes (0 Bytes/s) with ~1 file(s) remaining (calculating...)\n\
         Completed 10 Bytes/~10 Bytes (0 Bytes/s) with ~0 file(s) remaining (calculating...)\n\
         Completed 17 Bytes/~20 Bytes (0 Bytes/s) with ~1 file(s) remaining (calculating...)\n"
    );
    assert_eq!(err, FAILED_LINE);
    assert_eq!(processor.recorder.bytes_transferred, 12);
}

#[test]
fn a_later_transfers_bytes_never_count_against_earlier_failures() {
    let mut processor = multiline();
    let sender = processor.publisher();
    for event in [
        queued(1, 10),
        queued(2, 10),
        failure(1, 0),
        failure(2, 0),
        queued(3, 15),
    ] {
        sender.publish(event);
    }
    sender.add_progress(15);
    let (out, err) = step(&mut processor);
    assert_eq!(
        out,
        "Completed 10 Bytes/~20 Bytes (0 Bytes/s) with ~1 file(s) remaining (calculating...)\n\
         Completed 20 Bytes/~20 Bytes (0 Bytes/s) with ~0 file(s) remaining (calculating...)\n\
         Completed 35 Bytes/~35 Bytes (0 Bytes/s) with ~1 file(s) remaining (calculating...)\n"
    );
    assert_eq!(err, FAILED_LINE.repeat(2));
}

struct Lines {
    output: Vec<u8>,
    written: std::sync::mpsc::Sender<Vec<u8>>,
}
impl std::io::Write for Lines {
    fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
        self.output.extend_from_slice(bytes);
        let _ = self.written.send(bytes.to_vec());
        Ok(bytes.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

#[test]
fn progress_from_many_threads_coalesces_and_a_later_report_wakes_the_loop_again() {
    let mut processor = multiline();
    let sender = processor.publisher();
    sender.publish(queued(1, 1000));
    sender.publish(Event::FinalTotal(1));
    std::thread::scope(|scope| {
        for _ in 0..4 {
            scope.spawn(|| {
                for _ in 0..100 {
                    sender.add_progress(1);
                }
            });
        }
    });
    let (written, printed) = std::sync::mpsc::channel();
    let later = std::thread::spawn(move || {
        let wait = || printed.recv_timeout(std::time::Duration::from_secs(5));
        let first = wait();
        sender.add_progress(100);
        let second = wait();
        sender.publish(success(1));
        sender.close();
        (first, second)
    });
    let mut stdout = Lines {
        output: Vec::new(),
        written,
    };
    processor
        .run_with_clock(&mut stdout, &mut Vec::new(), || 1_000_000_000)
        .expect("result processor");
    let (first, second) = later.join().expect("later reports");
    let first = first.expect("a first progress line");
    let second = second.expect("a second progress line");
    let line = |bytes| {
        format!("Completed {bytes} Bytes/1000 Bytes (0 Bytes/s) with 1 file(s) remaining\n")
    };
    assert_eq!(String::from_utf8_lossy(&first), line(400));
    assert_eq!(String::from_utf8_lossy(&second), line(500));
    assert_eq!(
        String::from_utf8_lossy(&stdout.output),
        format!(
            "{}{}download: s3://bucket/key to file\n",
            line(400),
            line(500)
        )
    );
    assert_eq!(processor.recorder.bytes_transferred, 500);
}
