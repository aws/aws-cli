use super::*;
use cli_core::output::BufferedStream;

fn progress() -> Event {
    Event::Progress {
        key: None,
        bytes: 0,
        total_size: None,
        timestamp_ns: 0,
    }
}
fn failure(line: Line) -> Event {
    Event::Failure {
        key: 1,
        line,
        exception: b"failed".to_vec(),
        transferred: None,
        text: None,
    }
}
fn recorder() -> Recorder {
    let mut recorder = Recorder::default();
    recorder.bytes_transferred = 1024 * 1024;
    recorder.expected_bytes_transferred = 20 * 1024 * 1024;
    recorder.expected_files_transferred = 4;
    recorder.files_transferred = 1;
    recorder.final_expected_files_transferred = Some(4);
    recorder
}
fn render(config: PrinterConfig, recorder: &Recorder, events: &[Event]) -> (Vec<u8>, Vec<u8>) {
    let mut printer = Printer::new(config);
    let (mut out, mut err) = (Vec::new(), Vec::new());
    for event in events {
        printer.handle(recorder, event, 0, &mut out, &mut err);
    }
    (out, err)
}

#[test]
fn progress_formats_final_estimated_file_and_byte_totals() {
    for (bytes, final_total, expected) in [
        (
            true,
            true,
            "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 3 file(s) remaining",
        ),
        (
            true,
            false,
            "Completed 1.0 MiB/~20.0 MiB (0 Bytes/s) with ~3 file(s) remaining (calculating...)",
        ),
        (false, true, "Completed 1 file(s) with 3 file(s) remaining"),
        (
            false,
            false,
            "Completed 1 file(s) with ~3 file(s) remaining (calculating...)",
        ),
    ] {
        for oneline in [true, false] {
            let mut recorder = recorder();
            if !bytes {
                recorder.expected_bytes_transferred = 0;
            }
            if !final_total {
                recorder.final_expected_files_transferred = None;
            }
            let (out, err) = render(
                PrinterConfig {
                    oneline,
                    ..Default::default()
                },
                &recorder,
                &[progress(), progress()],
            );
            let line = [expected.as_bytes(), if oneline { b"\r" } else { b"\n" }].concat();
            assert_eq!(out, line.repeat(2));
            assert!(err.is_empty());
        }
    }
}

#[test]
fn selection_precedence_and_progress_interest_match_all_flag_combinations() {
    for bits in 0_u8..16 {
        let flags = Flags {
            quiet: bits & 1 != 0,
            only_show_errors: bits & 2 != 0,
            is_stream: bits & 4 != 0,
            progress: bits & 8 != 0,
            progress_frequency: 17,
            progress_multiline: true,
        };
        let expected = if flags.quiet {
            None
        } else if flags.only_show_errors || flags.is_stream {
            Some(Mode::OnlyErrors)
        } else if !flags.progress {
            Some(Mode::NoProgress)
        } else {
            Some(Mode::Full)
        };
        assert_eq!(flags.select().map(|config| config.mode), expected);
        assert_eq!(
            Processor::new(flags.select()).publisher().wants_progress(),
            expected == Some(Mode::Full)
        );
        if expected == Some(Mode::Full) {
            assert_eq!(
                flags.select(),
                Some(PrinterConfig {
                    mode: Mode::Full,
                    frequency_s: 17,
                    oneline: false
                })
            );
        }
    }
}

#[test]
fn modes_render_only_their_selected_results_and_keep_dry_run() {
    for mode in [Mode::NoProgress, Mode::OnlyErrors] {
        let events = [
            Event::Queued { key: 1, size: None },
            progress(),
            Event::Success {
                key: 1,
                line: line(),
            },
            failure(line()),
            Event::Warning(b"warning".to_vec()),
            Event::DryRun(line()),
            Event::Skip { key: 1 },
            Event::FinalTotal(1),
        ];
        let (out, err) = render(
            PrinterConfig {
                mode,
                ..Default::default()
            },
            &recorder(),
            &events,
        );
        let expected = if mode == Mode::NoProgress {
            b"download: s3://bucket/key to file\n(dryrun) download: s3://bucket/key to file\n"
                .as_slice()
        } else {
            b"(dryrun) download: s3://bucket/key to file\n".as_slice()
        };
        assert_eq!(out, expected);
        assert_eq!(
            err,
            b"download failed: s3://bucket/key to file failed\nwarning\n"
        );
    }
}

#[test]
fn unicode_and_destinationless_lines_preserve_exact_statements() {
    let mut recorder = Recorder::default();
    recorder.final_expected_files_transferred = Some(0);
    for destination in [None, Some("./é".as_bytes().to_vec())] {
        let line = Line {
            transfer_type: TransferType::Download,
            source: "s3://b/é".as_bytes().to_vec(),
            destination,
        };
        let locations = line.locations();
        let (out, err) = render(
            PrinterConfig::default(),
            &recorder,
            &[
                Event::Success {
                    key: 1,
                    line: line.clone(),
                },
                Event::DryRun(line.clone()),
                failure(line),
                Event::Warning("warning: é".as_bytes().to_vec()),
                Event::Fatal("é".as_bytes().to_vec()),
            ],
        );
        assert_eq!(
            out,
            [
                b"download: ",
                locations.as_slice(),
                b"\n(dryrun) download: ",
                locations.as_slice(),
                b"\n"
            ]
            .concat()
        );
        assert_eq!(
            err,
            [
                b"download failed: ",
                locations.as_slice(),
                " failed\nwarning: é\nfatal error: é\n".as_bytes()
            ]
            .concat()
        );
    }
}

// Python's stderr encodes with `backslashreplace`, so each byte a path
// decoded into a surrogate escape prints as `\udcXX` there; stdout keeps the
// raw byte.
#[test]
fn stderr_escapes_undecodable_path_bytes_and_stdout_keeps_them() {
    let mut recorder = Recorder::default();
    recorder.final_expected_files_transferred = Some(0);
    let line = Line {
        transfer_type: TransferType::Upload,
        source: [b"dir/".as_slice(), "é".as_bytes(), b"\xff"].concat(),
        destination: Some(b"s3://mybucket/\xff".to_vec()),
    };
    let failure = Event::Failure {
        key: 1,
        line: line.clone(),
        exception: b"my exception".to_vec(),
        transferred: None,
        text: None,
    };
    let (out, err) = render(PrinterConfig::default(), &recorder, &[failure]);
    assert!(out.is_empty());
    assert_eq!(
        err,
        "upload failed: dir/é\\udcff to s3://mybucket/\\udcff my exception\n".as_bytes()
    );
    let (out, err) = render(
        PrinterConfig::default(),
        &recorder,
        &[Event::Success { key: 1, line }],
    );
    assert!(err.is_empty());
    assert_eq!(
        out,
        [
            b"upload: dir/".as_slice(),
            "é".as_bytes(),
            b"\xff to s3://mybucket/\xff\n"
        ]
        .concat()
    );
}

#[test]
fn stderr_padding_counts_each_escaped_byte_once() {
    let mut printer = Printer::new(PrinterConfig::default());
    let (mut out, mut err) = (Vec::new(), Vec::new());
    let recorder = recorder();
    printer.handle(&recorder, &progress(), 0, &mut out, &mut err);
    let progress_width = out.len() - 1;
    let warning = Event::Warning(b"w\xe2\x9c\xff".to_vec());
    printer.handle(&recorder, &warning, 0, &mut out, &mut err);
    let padding = vec![b' '; progress_width - 4];
    assert_eq!(
        err,
        [br"w\udce2\udc9c\udcff".as_slice(), &padding, b"\n"].concat()
    );
}

#[test]
fn padding_counts_unicode_scalars_and_each_invalid_byte() {
    for (source, width) in [
        (b"a\xe2\x9c\xff".as_slice(), 4),
        (b"\x80\xc3\xa9".as_slice(), 2),
        ("✓".as_bytes(), 1),
    ] {
        let mut printer = Printer::new(PrinterConfig::default());
        let (mut out, mut err) = (Vec::new(), Vec::new());
        let mut recorder = recorder();
        printer.handle(&recorder, &progress(), 0, &mut out, &mut err);
        let progress_width = out.len() - 1;
        recorder.files_transferred = 4;
        printer.handle(
            &recorder,
            &Event::Success {
                key: 1,
                line: Line {
                    transfer_type: TransferType::Download,
                    source: source.to_vec(),
                    destination: None,
                },
            },
            0,
            &mut out,
            &mut err,
        );
        let expected = [
            b"download: ".as_slice(),
            source,
            &vec![b' '; progress_width - 10 - width],
            b"\n",
        ]
        .concat();
        assert!(out.ends_with(&expected));
    }
}

#[test]
fn diagnostic_and_replacement_failure_use_literal_bytes_and_do_not_redraw() {
    let mut recorder = recorder();
    let (out, err) = render(
        PrinterConfig::default(),
        &recorder,
        &[progress(), Event::Diagnostic(b"diagnostic".to_vec())],
    );
    assert_eq!(out.iter().filter(|&&byte| byte == b'\r').count(), 1);
    assert!(err.starts_with(b"diagnostic "));
    recorder.files_transferred = 4;
    let (out, err) = render(
        PrinterConfig::default(),
        &recorder,
        &[Event::Failure {
            key: 1,
            line: line(),
            exception: b"unused".to_vec(),
            transferred: None,
            text: Some(b"replacement".to_vec()),
        }],
    );
    assert!(out.is_empty());
    assert_eq!(err, b"replacement\n");
}

#[test]
fn final_total_clears_last_visible_progress_and_empty_commands_print_nothing() {
    let mut printer = Printer::new(PrinterConfig::default());
    let (mut out, mut err) = (Vec::new(), Vec::new());
    let mut recorder = recorder();
    printer.handle(&recorder, &progress(), 0, &mut out, &mut err);
    let width = out.len() - 1;
    recorder.files_transferred = 4;
    printer.handle(&recorder, &Event::FinalTotal(4), 0, &mut out, &mut err);
    assert!(out.ends_with(&[vec![b' '; width], vec![b'\n']].concat()));
    let mut empty = Recorder::default();
    empty.final_expected_files_transferred = Some(0);
    assert_eq!(
        render(
            PrinterConfig::default(),
            &empty,
            &[Event::FinalTotal(0), Event::Skip { key: 1 }]
        ),
        (Vec::new(), Vec::new())
    );
}

#[test]
fn throttled_progress_never_changes_width_of_visible_line() {
    let mut printer = Printer::new(PrinterConfig {
        frequency_s: 10,
        ..Default::default()
    });
    let (mut out, mut err) = (Vec::new(), Vec::new());
    let mut recorder = recorder();
    printer.handle(&recorder, &progress(), 0, &mut out, &mut err);
    let width = out.len() - 1;
    recorder.expected_files_transferred = 1_000_000;
    recorder.final_expected_files_transferred = None;
    printer.handle(&recorder, &progress(), 1_000_000_000, &mut out, &mut err);
    printer.handle(
        &recorder,
        &Event::Diagnostic(b"x".to_vec()),
        1_000_000_000,
        &mut out,
        &mut err,
    );
    assert_eq!(
        err,
        [b"x".as_slice(), &vec![b' '; width - 1], b"\n"].concat()
    );
}

#[test]
fn completion_and_warning_redraw_final_and_estimated_progress_with_padding() {
    for case in 0_u8..24 {
        redraw_case(case);
    }
}
fn redraw_case(case: u8) {
    let kind = case % 3;
    let final_total = (case / 3) & 1 != 0;
    let previous_progress = (case / 6) & 1 != 0;
    let destination = (case / 12) & 1 != 0;
    let mut recorder = recorder();
    recorder.final_expected_files_transferred = final_total.then_some(4);
    let mut printer = Printer::new(PrinterConfig::default());
    let (mut out, mut err) = (Vec::new(), Vec::new());
    if previous_progress {
        printer.handle(&recorder, &progress(), 0, &mut out, &mut err);
    }
    let previous = out.clone();
    let width = previous.len().saturating_sub(1);
    let line = Line {
        transfer_type: TransferType::Download,
        source: b"source".to_vec(),
        destination: destination.then(|| b"dest".to_vec()),
    };
    let (event, statement, remaining) = match kind {
        0 => (
            Event::Success {
                key: 1,
                line: line.clone(),
            },
            [b"download: ".as_slice(), line.locations().as_slice()].concat(),
            2,
        ),
        1 => (
            failure(line.clone()),
            [
                b"download failed: ".as_slice(),
                line.locations().as_slice(),
                b" failed",
            ]
            .concat(),
            2,
        ),
        _ => (Event::Warning(b"warning".to_vec()), b"warning".to_vec(), 3),
    };
    recorder.files_transferred = 4 - remaining;
    printer.handle(&recorder, &event, 0, &mut out, &mut err);
    let estimate = if final_total { "" } else { "~" };
    let suffix = if final_total { "" } else { " (calculating...)" };
    let redraw = format!(
        "Completed 1.0 MiB/{estimate}20.0 MiB (0 Bytes/s) with {estimate}{remaining} \
            file(s) remaining{suffix}\r"
    );
    let padded = [
        statement.as_slice(),
        &vec![b' '; width.saturating_sub(statement.len())],
        b"\n",
    ]
    .concat();
    if kind == 0 {
        assert_eq!(out, [previous, padded, redraw.into_bytes()].concat());
        assert!(err.is_empty());
    } else {
        assert_eq!(out, [previous, redraw.into_bytes()].concat());
        assert_eq!(err, padded);
    }
}

#[test]
fn multiline_completion_stacks_unpadded_lines_and_reports_speed() {
    let mut recorder = recorder();
    recorder.bytes_transfer_speed = 2.5 * 1024.0;
    let (out, err) = render(
        PrinterConfig {
            oneline: false,
            ..Default::default()
        },
        &recorder,
        &[
            progress(),
            Event::Success {
                key: 1,
                line: line(),
            },
        ],
    );
    assert_eq!(
        out,
        b"Completed 1.0 MiB/20.0 MiB (2.5 KiB/s) with 3 file(s) \
        remaining\ndownload: s3://bucket/key to file\nCompleted 1.0 MiB/20.0 MiB (2.5 \
        KiB/s) with 3 file(s) remaining\n"
    );
    assert!(err.is_empty());
}

#[derive(Debug, Default)]
struct Recovering {
    failures: usize,
    log: Vec<u8>,
}
impl std::io::Write for Recovering {
    fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
        if self.failures > 0 {
            self.failures -= 1;
            return Err(std::io::ErrorKind::BrokenPipe.into());
        }
        self.log.extend_from_slice(bytes);
        Ok(bytes.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}
fn upload() -> Event {
    Event::Success {
        key: 1,
        line: Line {
            transfer_type: TransferType::Upload,
            source: b"file".to_vec(),
            destination: Some(b"s3://mybucket/mykey".to_vec()),
        },
    }
}
fn bare() -> Event {
    Event::Success {
        key: 2,
        line: Line {
            transfer_type: TransferType::Upload,
            source: b"s3://mybucket/mykey".to_vec(),
            destination: None,
        },
    }
}
fn printer_over(stdout: Recovering) -> (Printer, BufferedStream<Recovering>) {
    let printer = Printer::new(PrinterConfig {
        mode: Mode::NoProgress,
        ..Default::default()
    });
    (printer, BufferedStream::new(stdout, 64))
}
#[test]
fn a_failed_stdout_keeps_whole_statements_until_its_buffer_fills() {
    let (mut printer, mut stdout) = printer_over(Recovering {
        failures: usize::MAX,
        ..Recovering::default()
    });
    let mut stderr = Vec::new();
    let recorder = Recorder::default();
    printer.handle(&recorder, &upload(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    for event in [bare(), upload(), bare()] {
        printer.handle(&recorder, &event, 0, &mut stdout, &mut stderr);
    }
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        stdout.buffered(),
        b"upload: file to s3://mybucket/mykey\nupload: s3://mybucket/mykey\n"
    );
    assert!(stdout.get_ref().log.is_empty() && stderr.is_empty());
    assert_eq!(
        printer.take_errors().stdout.expect("first failure").kind(),
        std::io::ErrorKind::BrokenPipe
    );
}
#[test]
fn a_stdout_that_recovers_writes_what_its_failed_flush_kept() {
    let (mut printer, mut stdout) = printer_over(Recovering {
        failures: 1,
        ..Recovering::default()
    });
    let mut stderr = Vec::new();
    let recorder = Recorder::default();
    printer.handle(&recorder, &upload(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    assert!(stdout.last_error().is_some());
    printer.handle(&recorder, &bare(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        stdout.get_ref().log,
        b"upload: file to s3://mybucket/mykey\nupload: s3://mybucket/mykey\n"
    );
    assert!(stdout.buffered().is_empty());
}

fn upload_failure(source: &[u8]) -> Event {
    Event::Failure {
        key: 1,
        line: Line {
            transfer_type: TransferType::Upload,
            source: source.to_vec(),
            destination: Some(b"s3://mybucket/mykey".to_vec()),
        },
        exception: b"my exception".to_vec(),
        transferred: None,
        text: None,
    }
}
fn no_progress_printer() -> Printer {
    Printer::new(PrinterConfig {
        mode: Mode::NoProgress,
        ..Default::default()
    })
}
#[test]
fn a_failed_stream_does_not_stop_the_other() {
    let mut printer = no_progress_printer();
    let mut stdout = Recovering {
        failures: usize::MAX,
        ..Recovering::default()
    };
    let mut stderr = Vec::new();
    let recorder = Recorder::default();
    printer.handle(&recorder, &upload(), 0, &mut stdout, &mut stderr);
    printer.handle(
        &recorder,
        &upload_failure(b"file"),
        0,
        &mut stdout,
        &mut stderr,
    );
    printer.handle(&recorder, &upload(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        String::from_utf8_lossy(&stderr),
        "upload failed: file to s3://mybucket/mykey my exception\n"
    );
    let errors = printer.take_errors();
    assert!(errors.stdout.is_some() && errors.stderr.is_none());
}
#[test]
fn a_failed_stderr_keeps_whole_statements_until_its_buffer_fills() {
    let mut printer = no_progress_printer();
    let mut stdout = Vec::new();
    let mut stderr = BufferedStream::new(
        Recovering {
            failures: usize::MAX,
            ..Recovering::default()
        },
        60,
    );
    let recorder = Recorder::default();
    let failure = Event::Failure {
        key: 0,
        line: Line {
            transfer_type: TransferType::Upload,
            source: b"f\xff".to_vec(),
            destination: Some(b"s3://b/k".to_vec()),
        },
        exception: b"my exception".to_vec(),
        transferred: None,
        text: None,
    };
    printer.handle(&recorder, &failure, 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    assert!(stderr.last_error().is_some());
    for event in [
        Event::Warning(b"warning: \xff".to_vec()),
        Event::Warning(b"warning: w1".to_vec()),
        upload(),
    ] {
        printer.handle(&recorder, &event, 0, &mut stdout, &mut stderr);
    }
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        String::from_utf8_lossy(stderr.buffered()),
        "upload failed: f\\udcff to s3://b/k my exception\nwarning: w1\n"
    );
    assert!(stderr.get_ref().log.is_empty());
    assert_eq!(
        String::from_utf8_lossy(&stdout),
        "upload: file to s3://mybucket/mykey\n"
    );
}
#[test]
fn a_stderr_that_recovers_writes_what_its_failed_flush_kept() {
    let mut printer = no_progress_printer();
    let mut stdout = Vec::new();
    let mut stderr = BufferedStream::new(
        Recovering {
            failures: 1,
            ..Recovering::default()
        },
        64,
    );
    let recorder = Recorder::default();
    printer.handle(
        &recorder,
        &upload_failure(b"file"),
        0,
        &mut stdout,
        &mut stderr,
    );
    printer.flush(&mut stdout, &mut stderr);
    assert!(stderr.last_error().is_some());
    let warning = Event::Warning(b"warning: w".to_vec());
    printer.handle(&recorder, &warning, 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        String::from_utf8_lossy(&stderr.get_ref().log),
        "upload failed: file to s3://mybucket/mykey my exception\nwarning: w\n"
    );
    assert!(stderr.buffered().is_empty());
}
#[test]
fn a_failed_stderr_waits_for_its_next_line_not_a_switch_to_stdout() {
    let log = std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let mut stdout = StreamLog::new(b"out:", &log);
    let mut stderr = StreamLog {
        failures: 1,
        ..StreamLog::new(b"err:", &log)
    };
    let mut printer = no_progress_printer();
    let recorder = Recorder::default();
    let warning = |text: &[u8]| Event::Warning(text.to_vec());
    printer.handle(
        &recorder,
        &warning(b"warning: w1"),
        0,
        &mut stdout,
        &mut stderr,
    );
    printer.flush(&mut stdout, &mut stderr);
    assert!(printer.take_errors().stderr.is_some());
    printer.handle(&recorder, &upload(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    let upload = "out:upload: file to s3://mybucket/mykey\n";
    assert_eq!(String::from_utf8_lossy(&log.borrow()), upload);
    printer.handle(
        &recorder,
        &warning(b"warning: w2"),
        0,
        &mut stdout,
        &mut stderr,
    );
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        String::from_utf8_lossy(&log.borrow()),
        format!("{upload}err:warning: w1\nwarning: w2\n")
    );
}
#[test]
fn a_failed_stdout_waits_for_its_next_line_not_a_switch_to_stderr() {
    let log = std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let mut stdout = StreamLog {
        failures: 1,
        ..StreamLog::new(b"out:", &log)
    };
    let mut stderr = StreamLog::new(b"err:", &log);
    let mut printer = no_progress_printer();
    let recorder = Recorder::default();
    printer.handle(&recorder, &upload(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    assert!(printer.take_errors().stdout.is_some());
    let failed = upload_failure(b"file");
    printer.handle(&recorder, &failed, 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    let failure = "err:upload failed: file to s3://mybucket/mykey my exception\n";
    assert_eq!(String::from_utf8_lossy(&log.borrow()), failure);
    assert_eq!(stdout.pending, b"upload: file to s3://mybucket/mykey\n");
    printer.handle(&recorder, &bare(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        String::from_utf8_lossy(&log.borrow()),
        format!("{failure}out:upload: file to s3://mybucket/mykey\nupload: s3://mybucket/mykey\n")
    );
}

#[test]
fn a_success_line_stdout_refuses_redraws_no_progress() {
    let mut printer = Printer::new(PrinterConfig::default());
    let mut stdout = BufferedStream::new(
        Recovering {
            failures: usize::MAX,
            ..Recovering::default()
        },
        256,
    );
    let mut stderr = Vec::new();
    let mut recorder = Recorder::default();
    recorder.expected_bytes_transferred = 20 * 1024 * 1024;
    recorder.expected_files_transferred = 2;
    recorder.final_expected_files_transferred = Some(2);
    recorder.bytes_transferred = 1024 * 1024;
    printer.handle(&recorder, &progress(), 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    recorder.files_transferred = 1;
    printer.handle(&recorder, &upload(), 0, &mut stdout, &mut stderr);
    recorder.files_transferred = 2;
    printer.handle(&recorder, &bare(), 0, &mut stdout, &mut stderr);
    let warning = Event::Warning(b"warning: w".to_vec());
    printer.handle(&recorder, &warning, 0, &mut stdout, &mut stderr);
    printer.flush(&mut stdout, &mut stderr);
    let progress = "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 2 file(s) remaining";
    let padded = |line: &str| format!("{line:<width$}\n", width = progress.len());
    assert_eq!(
        String::from_utf8_lossy(stdout.buffered()),
        format!(
            "{progress}\r{}{}",
            padded("upload: file to s3://mybucket/mykey"),
            padded("upload: s3://mybucket/mykey")
        )
    );
    assert_eq!(String::from_utf8_lossy(&stderr), padded("warning: w"));
}

#[test]
fn a_line_stderr_refuses_redraws_no_progress() {
    let mut printer = Printer::new(PrinterConfig::default());
    let mut stdout = Vec::new();
    let mut stderr = BufferedStream::new(
        Recovering {
            failures: usize::MAX,
            ..Recovering::default()
        },
        256,
    );
    let mut recorder = Recorder::default();
    recorder.expected_bytes_transferred = 20 * 1024 * 1024;
    recorder.expected_files_transferred = 2;
    recorder.final_expected_files_transferred = Some(2);
    recorder.bytes_transferred = 1024 * 1024;
    let warning = Event::Warning(b"warning: w".to_vec());
    for event in [progress(), warning, upload_failure(b"file")] {
        printer.handle(&recorder, &event, 0, &mut stdout, &mut stderr);
    }
    printer.flush(&mut stdout, &mut stderr);
    let progress = "Completed 1.0 MiB/20.0 MiB (0 Bytes/s) with 2 file(s) remaining";
    assert_eq!(String::from_utf8_lossy(&stdout), format!("{progress}\r"));
    let padded = |line: &str| format!("{line:<width$}\n", width = progress.len());
    assert_eq!(
        String::from_utf8_lossy(stderr.buffered()),
        format!(
            "{}{}",
            padded("warning: w"),
            padded("upload failed: file to s3://mybucket/mykey my exception")
        )
    );
}

#[derive(Debug)]
struct StreamLog {
    label: &'static [u8],
    pending: Vec<u8>,
    log: std::rc::Rc<std::cell::RefCell<Vec<u8>>>,
    failures: usize,
}
impl StreamLog {
    fn new(label: &'static [u8], log: &std::rc::Rc<std::cell::RefCell<Vec<u8>>>) -> Self {
        Self {
            label,
            pending: Vec::new(),
            log: log.clone(),
            failures: 0,
        }
    }
}
impl std::io::Write for StreamLog {
    fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
        self.pending.extend_from_slice(bytes);
        Ok(bytes.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        if self.failures > 0 {
            self.failures -= 1;
            return Err(std::io::ErrorKind::BrokenPipe.into());
        }
        if !self.pending.is_empty() {
            let mut log = self.log.borrow_mut();
            log.extend_from_slice(self.label);
            log.append(&mut self.pending);
        }
        Ok(())
    }
}
#[test]
fn switching_streams_flushes_previous_bytes_in_event_order() {
    let log = std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let mut stdout = StreamLog::new(b"out:", &log);
    let mut stderr = StreamLog::new(b"err:", &log);
    let mut printer = Printer::new(PrinterConfig {
        mode: Mode::NoProgress,
        ..Default::default()
    });
    for event in [
        Event::Success {
            key: 1,
            line: line(),
        },
        Event::Warning(b"warning".to_vec()),
        Event::Success {
            key: 2,
            line: line(),
        },
    ] {
        printer.handle(&Recorder::default(), &event, 0, &mut stdout, &mut stderr);
    }
    printer.flush(&mut stdout, &mut stderr);
    assert_eq!(
        *log.borrow(),
        b"out:download: s3://bucket/key to \
        file\nerr:warning\nout:download: s3://bucket/key to file\n"
    );
}

#[test]
fn each_statement_reaches_its_stream_in_one_write() {
    #[derive(Default)]
    struct Writes(Vec<Vec<u8>>);
    impl std::io::Write for Writes {
        fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
            self.0.push(buf.to_vec());
            Ok(buf.len())
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }
    let mut printer = Printer::new(PrinterConfig::default());
    let (mut out, mut err) = (Writes::default(), Writes::default());
    let recorder = recorder();
    printer.handle(&recorder, &progress(), 0, &mut out, &mut err);
    let warning = Event::Warning(b"w\xff".to_vec());
    printer.handle(&recorder, &warning, 0, &mut out, &mut err);
    printer.handle(
        &recorder,
        &Event::Diagnostic(b"d".to_vec()),
        0,
        &mut out,
        &mut err,
    );
    assert_eq!(out.0.len(), 2);
    assert_eq!(err.0.len(), 2);
    for (write, text) in err.0.iter().zip([br"w\udcff".as_slice(), b"d"]) {
        assert!(
            write.starts_with(text) && write.ends_with(b"\n"),
            "{write:?}"
        );
        assert!(
            write[text.len()..write.len() - 1]
                .iter()
                .all(|&byte| byte == b' ')
        );
    }
}
