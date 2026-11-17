#![allow(
    clippy::expect_used,
    clippy::panic,
    clippy::too_many_lines,
    reason = "recursive fixtures fail at the unexpected status or event; each matrix stays one test"
)]
use super::*;
use results::Event;
use std::io::Write;

fn finish(
    source: &str,
    request: &TransferRequest,
    completion: &Completion,
) -> (Result<u8, RenderError>, Vec<Event>) {
    let processor = results::Processor::new(None);
    let publisher = processor.publisher();
    let report = CommandReport::new(&publisher, request.quiet);
    let status = finish_transfer(report, OsStr::new(source), request, completion);
    (status, publisher.take_events())
}
fn diagnostic(text: &str) -> Event {
    Event::Diagnostic(text.as_bytes().to_vec())
}
fn fatal(text: &str) -> Event {
    Event::Fatal(text.as_bytes().to_vec())
}

#[test]
fn only_a_producer_that_named_every_object_is_exhausted() {
    let listing = |status, error_code, callback_error| {
        ProducerOutcome::ListCompleted(Box::new(ListResult {
            callback_error,
            transfer: TransferResult {
                response_status: status,
                error_code,
                ..Default::default()
            },
            ..Default::default()
        }))
    };
    let cases = [
        (listing(200, 0, 0), true),
        (listing(0, 0, 0), true),
        (listing(503, 0, 0), false),
        (listing(200, 0, -1), false),
        (listing(0, crt::s3::CONNECTION_REFUSED_ERROR_CODE, 0), false),
        (
            ProducerOutcome::ListCompleted(Box::new(ListResult {
                local_error: Some(ListLocalError::CrtFailure),
                ..Default::default()
            })),
            false,
        ),
        (
            ProducerOutcome::ListCompleted(Box::new(ListResult {
                repeated_token: Some(b"same-token".to_vec()),
                ..Default::default()
            })),
            false,
        ),
        (ProducerOutcome::WalkCompleted, true),
        (ProducerOutcome::WalkFailed("AccessDenied".into()), false),
        (ProducerOutcome::ObjectCompleted, true),
        (
            ProducerOutcome::HeadFailed(Box::new(TransferResult {
                error_code: 1,
                ..Default::default()
            })),
            false,
        ),
        (ProducerOutcome::HeadCanceled, false),
        (ProducerOutcome::HeadMissingLastModified, false),
        (ProducerOutcome::SubmitFailed("OutOfMemory".into()), false),
    ];
    for (outcome, exhausted) in cases {
        assert_eq!(outcome.exhausted(false), exhausted, "{outcome:?}");
        assert!(!outcome.exhausted(true), "{outcome:?}");
        for submit_queue_failed in [false, true] {
            let result = ProducerResult {
                outcome: outcome.clone(),
                submit_queue_failed,
                list_stats: None,
            };
            assert_eq!(
                result.exhausted(false),
                exhausted && !submit_queue_failed,
                "{outcome:?}"
            );
        }
    }
}

#[test]
fn a_producer_whose_entry_the_engine_refused_escapes_to_the_general_handler() {
    for canceled in [false, true] {
        let (result, events) = finish(
            "source",
            &request(),
            &Completion::Finished(Box::new(Finished {
                canceled,
                producer: ProducerOutcome::SubmitFailed("OutOfMemory".into()),
                warned: 1,
                ..Default::default()
            })),
        );
        if canceled {
            assert!(matches!(result, Ok(1)));
            assert_eq!(events, [Event::CtrlC]);
        } else {
            assert!(matches!(result, Err(RenderError::Fatal(name)) if name == "OutOfMemory"));
            assert!(events.is_empty());
        }
    }
}

#[test]
fn a_repeated_listing_token_is_a_fatal_result_and_quiet_suppresses_it() {
    for quiet in [false, true] {
        let mut request = request();
        request.quiet = quiet;
        let completion = Completion::Finished(Box::new(Finished {
            producer: ProducerOutcome::ListCompleted(Box::new(ListResult {
                transfer: TransferResult {
                    response_status: 200,
                    ..Default::default()
                },
                repeated_token: Some(b"same-token".to_vec()),
                ..Default::default()
            })),
            ..Default::default()
        }));
        let (status, events) = finish("s3://bucket/prefix/", &request, &completion);
        assert_eq!(status.expect("repeated token"), 1);
        let expected = if quiet {
            vec![]
        } else {
            vec![fatal(
                "Error during pagination: The same next token was received twice: \
                 {'ContinuationToken': 'same-token'}",
            )]
        };
        assert_eq!(events, expected);
    }
}

#[test]
fn listing_parse_failures_are_fatal_results_and_quiet_suppresses_them() {
    for (error, cause) in [
        (ListLocalError::UnexpectedRoot, "unexpected root element"),
        (ListLocalError::InvalidNumber, "invalid numeric value"),
    ] {
        for quiet in [false, true] {
            let mut request = request();
            request.quiet = quiet;
            let completion = Completion::Finished(Box::new(Finished {
                producer: ProducerOutcome::ListCompleted(Box::new(ListResult {
                    local_error: Some(error),
                    ..Default::default()
                })),
                ..Default::default()
            }));
            let (status, events) = finish("s3://bucket", &request, &completion);
            assert_eq!(status.expect("parse failure"), 1);
            let expected = if quiet {
                vec![]
            } else {
                vec![fatal(&format!(
                    "Unable to parse response ({cause}), invalid XML received"
                ))]
            };
            assert_eq!(events, expected);
        }
    }
}

#[test]
fn local_listing_errors_escape_to_main_unless_cancellation_supersedes_them() {
    for error in [
        ListLocalError::CrtFailure,
        ListLocalError::PageBodyTooLarge,
        ListLocalError::PageLimitExceeded,
        ListLocalError::Canceled,
    ] {
        for canceled in [false, true] {
            let mut request = request();
            request.quiet = true;
            let completion = Completion::Finished(Box::new(Finished {
                canceled,
                producer: ProducerOutcome::ListCompleted(Box::new(ListResult {
                    local_error: Some(error),
                    ..Default::default()
                })),
                ..Default::default()
            }));
            let (result, events) = finish("s3://bucket", &request, &completion);
            assert_local_failure(result, error, canceled);
            assert!(events.is_empty());
        }
    }
}

fn request() -> TransferRequest {
    TransferRequest {
        direction: transfer::Direction::Download,
        bucket: "bucket".into(),
        prefix: "prefix/".into(),
        local_root: "destination/".into(),
        runtime: RuntimeOptions::default(),
        quiet: false,
        dryrun: false,
        no_overwrite: false,
        glacier: crate::transfer::GlacierPolicy::Warn,
        content_types: None,
        refusal: None,
        page_size: 10,
        max_in_flight: 512,
        collect_stats: false,
        prefetch: true,
        sizing: Default::default(),
        download: Some(config::Settings::default().resolve_download()),
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
fn failed_wins_over_warned_and_cancellation_overrides_all_failures() -> io::Result<()> {
    for (failed, warned, expected) in [(0, 0, 0), (0, 1, 2), (1, 0, 1), (1, 1, 1)] {
        let result = Finished {
            failed,
            warned,
            ..Default::default()
        };
        let (code, events) = finish(
            "s3://bucket",
            &request(),
            &Completion::Finished(Box::new(result)),
        );
        assert_eq!(code.expect("finish"), expected);
        assert!(events.is_empty());
    }
    for quiet in [false, true] {
        let request = TransferRequest { quiet, ..request() };
        let result = Finished {
            canceled: true,
            failed: 9,
            warned: 2,
            fatal: Some("OutOfMemory".into()),
            producer: ProducerOutcome::WalkFailed("AccessDenied".into()),
            ..Default::default()
        };
        let (code, events) = finish("source", &request, &Completion::Finished(Box::new(result)));
        assert_eq!(code.expect("finish"), 1);
        assert_eq!(events, if quiet { vec![] } else { vec![Event::CtrlC] });
    }
    Ok(())
}
#[test]
fn a_client_that_cannot_be_built_is_the_general_handlers_failure() {
    for quiet in [false, true] {
        let request = TransferRequest {
            quiet,
            collect_stats: true,
            ..request()
        };
        let (result, events) = finish(
            "source",
            &request,
            &Completion::ClientFailed(Box::new(TransferResult {
                error_code: 999999,
                crt_name: crt::s3::BoundedText::new("AWS_ERROR_OOM"),
                crt_message: crt::s3::BoundedText::new("Memory allocation failed."),
                ..Default::default()
            })),
        );
        let Err(error @ RenderError::ClientFailed(_)) = result else {
            panic!("client failure escapes: {result:?}");
        };
        assert_eq!(
            error.to_string(),
            "999999 (AWS_ERROR_OOM): Memory allocation failed."
        );
        assert!(events.is_empty());
    }
}
#[test]
fn recursive_completion_covers_source_and_producer_failures() {
    let mut request = request();
    request.runtime.endpoint_url = "http://localhost/bucket".into();
    let cases = [
        (
            Completion::SourceOpenFailed("FileNotFound".into()),
            "error: unable to open recursive upload source source: FileNotFound",
        ),
        (
            Completion::Finished(Box::new(Finished {
                producer: ProducerOutcome::WalkFailed("AccessDenied".into()),
                ..Default::default()
            })),
            "error: unable to enumerate recursive upload source source: AccessDenied",
        ),
        (
            Completion::Finished(Box::new(Finished {
                producer: ProducerOutcome::ListCompleted(Box::new(ListResult {
                    callback_error: -1,
                    ..Default::default()
                })),
                ..Default::default()
            })),
            "error: recursive S3 download failed while processing listing output",
        ),
    ];
    for (completion, expected) in cases {
        for quiet in [false, true] {
            let request = TransferRequest {
                quiet,
                ..request.clone()
            };
            let (status, events) = finish("source", &request, &completion);
            assert_eq!(status.expect("finish"), 1);
            assert_eq!(events, [diagnostic(expected)]);
        }
    }
}
#[derive(Debug, PartialEq)]
enum Reported {
    Status(u8),
    Escaped(&'static str),
}
#[test]
fn completion_precedence_follows_one_table() {
    for (finished, expected, events) in precedence_cases().into_iter().chain(status_cases()) {
        let (result, published) = finish(
            "source",
            &request(),
            &Completion::Finished(Box::new(finished)),
        );
        let reported = match result {
            Ok(status) => Reported::Status(status),
            Err(RenderError::Fatal(name)) if name == "OutOfMemory" => {
                Reported::Escaped("OutOfMemory")
            }
            Err(RenderError::Fatal(name)) if name == "WritePoolClosed" => {
                Reported::Escaped("WritePoolClosed")
            }
            Err(error) => panic!("unexpected escape: {error:?}"),
        };
        assert_eq!(reported, expected);
        assert_eq!(published, events);
    }
}
fn precedence_cases() -> [(Finished, Reported, Vec<Event>); 4] {
    const WALK: &str = "error: unable to enumerate recursive upload source source: AccessDenied";
    let walk_failed = || ProducerOutcome::WalkFailed("AccessDenied".into());
    [
        (
            Finished {
                canceled: true,
                fatal: Some("OutOfMemory".into()),
                producer: walk_failed(),
                failed: 1,
                warned: 1,
                ..Default::default()
            },
            Reported::Status(1),
            vec![Event::CtrlC],
        ),
        (
            Finished {
                fatal: Some("OutOfMemory".into()),
                producer: walk_failed(),
                failed: 1,
                warned: 1,
                ..Default::default()
            },
            Reported::Escaped("OutOfMemory"),
            vec![],
        ),
        (
            Finished {
                fatal: Some("WritePoolClosed".into()),
                ..Default::default()
            },
            Reported::Escaped("WritePoolClosed"),
            vec![],
        ),
        (
            Finished {
                producer: walk_failed(),
                failed: 1,
                warned: 1,
                ..Default::default()
            },
            Reported::Status(1),
            vec![diagnostic(WALK)],
        ),
    ]
}
fn status_cases() -> [(Finished, Reported, Vec<Event>); 4] {
    const STATS: &str = "zs3_transfer_stats direction=download submitted=0 succeeded=0 failed=0 \
        skipped=0 elapsed_ns=0 files_per_second=0.000 stall_ns=0 stall_count=0 \
        size_le_4_kib=0 size_le_64_kib=0 size_le_1_mib=0 size_gt_1_mib=0 \
        producer_wait_ns=0 producer_wait_count=0 queue_hwm=0 in_flight_hwm=0 \
        write_queue_hwm=0 writes_completed=0 write_ns=0 crt_target_gbps=12.500 \
        memory_limit_bytes=7 source_pool=crt custom_writer_requests=0 \
        recv_file_requests=0";
    [
        (
            Finished {
                failed: 1,
                warned: 1,
                ..Default::default()
            },
            Reported::Status(1),
            vec![],
        ),
        (
            Finished {
                warned: 1,
                ..Default::default()
            },
            Reported::Status(2),
            vec![],
        ),
        (Finished::default(), Reported::Status(0), vec![]),
        (
            Finished {
                canceled: true,
                stats: Some(Stats::default()),
                crt_target_gbps: 12.5,
                memory_limit_bytes: 7,
                ..Default::default()
            },
            Reported::Status(1),
            vec![diagnostic(STATS), Event::CtrlC],
        ),
    ]
}
#[test]
fn failed_listing_is_fatal_and_quiet_suppresses_it() {
    let result = Finished {
        producer: ProducerOutcome::ListCompleted(Box::new(ListResult {
            transfer: TransferResult {
                error_code: 3,
                response_status: 403,
                service_error: crt::s3::ServiceError {
                    operation: crt::s3::BoundedText::new("ListObjectsV2"),
                    ..Default::default()
                },
                ..Default::default()
            },
            ..Default::default()
        })),
        ..Default::default()
    };
    for quiet in [false, true] {
        let (status, events) = finish(
            "source",
            &TransferRequest { quiet, ..request() },
            &Completion::Finished(Box::new(result.clone())),
        );
        assert_eq!(status.expect("finish"), 1);
        let expected = if quiet {
            vec![]
        } else {
            vec![fatal(
                "An error occurred (403) when calling the ListObjectsV2 operation: Forbidden",
            )]
        };
        assert_eq!(events, expected);
    }
}
#[test]
fn stats_preserve_parser_keys_precision_and_histogram_boundaries() {
    let mut stats = Stats {
        submitted: 4,
        succeeded: 3,
        failed: 1,
        skipped: 2,
        elapsed_ns: 2_000_000_000,
        ..Default::default()
    };
    for size in [0, 4096, 4097, 65536, 65537, 1048576, 1048577] {
        stats.record_size(size);
    }
    assert_eq!(
        [
            stats.size_le_4_kib,
            stats.size_le_64_kib,
            stats.size_le_1_mib,
            stats.size_gt_1_mib
        ],
        [2, 2, 2, 1]
    );
    assert_eq!(stats.files_per_second(), 1.5);
    assert_eq!(Stats::default().files_per_second(), 0.0);
    stats.custom_writer_requests = 13;
    stats.recv_file_requests = 14;
    for (numa_source_pool, pool) in [(true, "numa"), (false, "crt")] {
        let processor = results::Processor::new(None);
        let publisher = processor.publisher();
        write_transfer_stats(
            CommandReport::new(&publisher, false),
            transfer::Direction::Download,
            &stats,
            217.6,
            2 << 30,
            numa_source_pool,
        );
        assert_eq!(
            publisher.take_events(),
            [Event::Diagnostic(
                format!(
                    "zs3_transfer_stats direction=download submitted=4 succeeded=3 failed=1 \
                skipped=2 elapsed_ns=2000000000 files_per_second=1.500 stall_ns=0 \
                stall_count=0 size_le_4_kib=2 size_le_64_kib=2 size_le_1_mib=2 \
                size_gt_1_mib=1 producer_wait_ns=0 producer_wait_count=0 queue_hwm=0 \
                in_flight_hwm=0 write_queue_hwm=0 writes_completed=0 write_ns=0 \
                crt_target_gbps=217.600 memory_limit_bytes=2147483648 \
                source_pool={pool} custom_writer_requests=13 recv_file_requests=14"
                )
                .into_bytes()
            )]
        );
    }
}
#[test]
fn listing_stats_print_only_collected_nonempty_pages() {
    for pages in [0, 3] {
        for quiet in [false, true] {
            let completion = Completion::Finished(Box::new(Finished {
                stats: Some(Stats::default()),
                list_stats: Some(crt::s3::ListStats {
                    pages,
                    ..Default::default()
                }),
                ..Default::default()
            }));
            let (status, events) = finish(
                "source",
                &TransferRequest { quiet, ..request() },
                &completion,
            );
            assert_eq!(status.expect("finish"), 0);
            let lines: Vec<_> = events
                .iter()
                .map(|event| match event {
                    Event::Diagnostic(line) => line.as_slice(),
                    event => panic!("only diagnostics: {event:?}"),
                })
                .collect();
            assert_eq!(lines.len(), 1 + usize::from(pages > 0), "{events:?}");
            assert!(lines[0].starts_with(b"zs3_transfer_stats direction=download "));
            if pages > 0 {
                assert!(lines[1].starts_with(b"zs3-list-stats: pages=3 "));
            }
            assert!(lines.iter().all(|line| !line.contains(&b'\n')));
        }
    }
}
struct BrokenWriter(usize);
impl Write for BrokenWriter {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> {
        self.0 += 1;
        Err(io::ErrorKind::BrokenPipe.into())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[test]
fn quiet_recursive_completion_propagates_diagnostic_writer_failures() {
    let request = TransferRequest {
        quiet: true,
        ..request()
    };
    let mut processor = results::Processor::with_diagnostics(None);
    let publisher = processor.publisher();
    let report = CommandReport::new(&publisher, true);
    let listing = ProducerOutcome::ListCompleted(Box::new(ListResult {
        callback_error: -1,
        ..Default::default()
    }));
    for producer in [listing, ProducerOutcome::WalkFailed("AccessDenied".into())] {
        let completion = Completion::Finished(Box::new(Finished {
            producer,
            ..Default::default()
        }));
        let status = finish_transfer(report, OsStr::new("source"), &request, &completion);
        assert!(matches!(status, Ok(1)));
    }
    publisher.close();
    let mut stderr = BrokenWriter(0);
    let errors = processor
        .run(&mut Vec::new(), &mut stderr)
        .expect_err("stderr fails");
    assert!(errors.stdout.is_none());
    assert_eq!(
        errors.stderr.map(|error| error.kind()),
        Some(io::ErrorKind::BrokenPipe)
    );
    assert_eq!(stderr.0, 1);
    let (status, _) = finish(
        "source",
        &request,
        &Completion::Finished(Box::new(Finished {
            fatal: Some("OutOfMemory".into()),
            ..Default::default()
        })),
    );
    assert!(matches!(status, Err(RenderError::Fatal(_))));
}
#[test]
fn a_missing_keys_fatal_sentence_is_one_event_whatever_lines_it_holds() {
    for key in ["a\n\nb", "a\nfatal error: b", "a\nb"] {
        for canceled in [false, true] {
            let request = TransferRequest {
                object: Some(SingleObject {
                    key: key.as_bytes().to_vec(),
                    ..SingleObject::default()
                }),
                ..request()
            };
            let completion = Completion::Finished(Box::new(Finished {
                producer: ProducerOutcome::HeadFailed(Box::new(TransferResult {
                    error_code: 14_361,
                    response_status: 404,
                    service_error: crt::s3::ServiceError {
                        operation: crt::s3::BoundedText::new("HeadObject"),
                        ..Default::default()
                    },
                    ..Default::default()
                })),
                canceled,
                ..Default::default()
            }));
            let sentence = format!(
                "An error occurred (404) when calling the HeadObject operation: \
                 Key \"{key}\" does not exist"
            );
            let (status, events) = finish("source", &request, &completion);
            assert_eq!(status.expect("finish"), 1);
            let mut expected = vec![fatal(&sentence)];
            expected.extend(canceled.then_some(Event::CtrlC));
            assert_eq!(events, expected);
            assert_eq!(
                printed(&request, &completion),
                format!("fatal error: {sentence}\n").as_bytes()
            );
            let quiet = TransferRequest {
                quiet: true,
                ..request
            };
            assert_eq!(finish("source", &quiet, &completion).1, []);
        }
    }
}
fn printed(request: &TransferRequest, completion: &Completion) -> Vec<u8> {
    printed_from(OsStr::new("source"), request, completion)
}
fn printed_from(source: &OsStr, request: &TransferRequest, completion: &Completion) -> Vec<u8> {
    let printer = (!request.quiet).then_some(results::PrinterConfig {
        mode: results::Mode::NoProgress,
        ..Default::default()
    });
    let mut processor = results::Processor::with_diagnostics(printer);
    let publisher = processor.publisher();
    let report = CommandReport::new(&publisher, request.quiet);
    finish_transfer(report, source, request, completion).expect("finish");
    publisher.close();
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    processor
        .run(&mut stdout, &mut stderr)
        .expect("processor output");
    assert!(stdout.is_empty());
    stderr
}
#[cfg(unix)]
#[test]
fn quiet_diagnostics_print_the_source_as_written() {
    use std::os::unix::ffi::OsStrExt;
    let source = OsStr::from_bytes(b"d\xff");
    let completion = Completion::Finished(Box::new(Finished {
        producer: ProducerOutcome::WalkFailed("AccessDenied".into()),
        ..Default::default()
    }));
    for (quiet, spelled) in [(true, b"d\xff".as_slice()), (false, br"d\udcff")] {
        let request = TransferRequest { quiet, ..request() };
        let expected = [
            b"error: unable to enumerate recursive upload source ".as_slice(),
            spelled,
            b": AccessDenied\n",
        ]
        .concat();
        assert_eq!(printed_from(source, &request, &completion), expected);
    }
}

fn assert_local_failure(result: Result<u8, RenderError>, error: ListLocalError, canceled: bool) {
    if canceled {
        assert!(matches!(result, Ok(1)));
    } else {
        assert!(matches!(&result, Err(RenderError::Fatal(_))));
        if let Err(RenderError::Fatal(message)) = result {
            assert_eq!(message, format!("{error:?}"));
        }
    }
}
