use super::*;
use cli_core::interrupt::Canceled;

unsafe extern "C" {
    fn aws_default_allocator() -> *mut ffi::AwsAllocator;
    fn aws_byte_buf_append_encoding_uri_param(
        buffer: *mut ffi::AwsByteBuf,
        cursor: *const ffi::AwsByteCursor,
    ) -> i32;
}

#[test]
fn query_encoding_matches_the_crt_for_every_byte() {
    let _library = Library::acquire();
    let input: Vec<_> = (u8::MIN..=u8::MAX).collect();
    let mut encoded = [0; 256 * 3];
    let mut buffer = ffi::AwsByteBuf {
        len: 0,
        buffer: encoded.as_mut_ptr(),
        capacity: encoded.len(),
        // SAFETY: the process-wide allocator is live, and sufficient fixed
        // capacity ensures the encoder never reallocates this borrowed buffer.
        allocator: unsafe { aws_default_allocator() },
    };
    let cursor = ffi::AwsByteCursor::from_bytes(&input);
    // SAFETY: output capacity covers the worst-case percent expansion, and
    // both caller-owned buffers remain live for the synchronous CRT encoder.
    let status = unsafe { aws_byte_buf_append_encoding_uri_param(&mut buffer, &cursor) };
    assert_eq!(status, 0);
    let query = Query {
        prefix: &input,
        ..options(false).query
    };
    let mut expected = b"/bucket?list-type=2&prefix=".to_vec();
    expected.extend_from_slice(&encoded[..buffer.len]);
    expected.extend_from_slice(b"&delimiter=%2F&max-keys=2&encoding-type=url");
    assert_eq!(query.build_path(b"/bucket", None), expected);
}

struct FailedOperation {
    paths: Vec<Vec<u8>>,
}
impl PageOps for FailedOperation {
    type Handle = std::convert::Infallible;
    fn submit(
        &mut self,
        _: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        self.paths.push(path.to_vec());
        Err(Box::new(TransferResult {
            error_code: 123,
            response_status: 503,
            ..TransferResult::default()
        }))
    }
    fn cancel(&mut self, handle: &Self::Handle) {
        match *handle {}
    }
    fn release(&mut self, handle: Self::Handle) {
        match handle {}
    }
    fn backoff(&mut self, _: u64, _: crate::s3::botocore_retry::ErrorKind) -> Result<(), Canceled> {
        Ok(())
    }
}

#[test]
fn both_listing_operations_forward_query_and_failed_submission_outcome() {
    for operation in [Operation::ListObjectsV2, Operation::ListBuckets] {
        let query = Query {
            operation,
            prefix: b"prefix",
            delimiter: b"",
            region: b"",
            page_size: 1,
        };
        let mut ops = FailedOperation { paths: Vec::new() };
        let mut emitted = 0;
        let result = driver::run(
            Options::new(b"/bucket", query, operation == Operation::ListObjectsV2),
            &mut ops,
            None,
            &mut |_| {
                emitted += 1;
                0
            },
        );
        assert_eq!(emitted, 0);
        assert_eq!(
            (result.transfer.error_code, result.transfer.response_status),
            (123, 503)
        );
        assert_eq!(ops.paths, [query.build_path(b"/bucket", None)]);
        assert_eq!(result.request_path, ops.paths[0]);
    }
}

#[test]
fn finish_parses_the_whole_error_response_with_provenance_and_status() {
    let _library = Library::acquire();
    let page = Page::new(4096);
    let endpoint = b"https://bucket.s3.us-east-1.amazonaws.com";
    page.record_provenance(b"us-east-1", endpoint);
    let mut body = b"<Error><Code>Early</Code>".to_vec();
    body.resize(4096, b' ');
    body.extend_from_slice(b"<Message>late message</Message><Region>eu-west-1</Region></Error>");
    page.finish_response(3, 301, &body, b"ListObjectsV2");
    page.wait_complete();
    let state = crate::signal::lock(&page.inner);
    let result = state.result.as_ref().unwrap();
    assert_eq!((result.error_code, result.response_status), (3, 301));
    assert_eq!(result.service_error.code.as_bytes(), b"Early");
    assert_eq!(result.service_error.message, b"late message");
    assert_eq!(result.service_error.region_body.as_bytes(), b"eu-west-1");
    assert_eq!(result.service_error.operation.as_bytes(), b"ListObjectsV2");
    assert_eq!(result.request_region.as_bytes(), b"us-east-1");
    assert_eq!(result.endpoint_url.as_bytes(), endpoint);
}

#[test]
fn probe_handles_final_markers_late_tokens_empty_entities_and_unresolved_bodies() {
    let final_page = b"<ListBucketResult><IsTruncated>false</IsTruncated></ListBucketResult>";
    let late_token = b"<ListBucketResult><Contents><Key>key</Key></Contents><NextContinu\
        ationToken>next</NextContinuationToken></ListBucketResult>";
    for body in [final_page.as_slice(), late_token.as_slice()] {
        for split in 0..=body.len() {
            let mut probe = TokenProbe::default();
            probe.scan(&body[..split]);
            assert_eq!(
                probe.scan(body),
                if body == final_page {
                    ProbeState::FinalPage
                } else {
                    ProbeState::Token
                }
            );
            if body == late_token {
                assert_eq!(&body[probe.value_range()], b"next");
            }
        }
    }
    for body in [
        b"<NextContinuationToken></NextContinuationToken>".as_slice(),
        b"<NextContinuationToken>a&amp;b</NextContinuationToken>",
        b"<ListBucketResult/>",
    ] {
        let mut probe = TokenProbe::default();
        probe.scan(body);
        probe.finish();
        assert_eq!(probe.state(), ProbeState::Unresolved);
    }
}

#[test]
fn next_action_matrix_preserves_all_boolean_combinations() {
    use driver::{Action, NextActionInputs, next_action};
    for page_ok in [false, true] {
        for should_continue in [false, true] {
            let expected = if page_ok && should_continue {
                [
                    Action::SubmitSerial,
                    Action::SubmitSerial,
                    Action::CancelAndSubmit,
                    Action::Advance,
                ]
            } else {
                [
                    Action::Done,
                    Action::Done,
                    Action::CancelAndDone,
                    Action::CancelAndDone,
                ]
            };
            let actions = [(false, false), (false, true), (true, false), (true, true)].map(
                |(prefetch_in_flight, prefetch_token_matches)| {
                    next_action(NextActionInputs {
                        page_ok,
                        should_continue,
                        prefetch_in_flight,
                        prefetch_token_matches,
                    })
                },
            );
            assert_eq!(actions, expected);
        }
    }
}

#[test]
fn oversized_initial_body_allocates_nothing_and_statistics_initialize_minimum() {
    let page = Page::new(4);
    assert!(page.append_chunk(b"12345").is_err());
    assert_eq!(crate::signal::lock(&page.inner).body.capacity(), 0);
    let mut stats = ListPhaseStats::default();
    stats.add(12);
    assert_eq!((stats.ns_min, stats.ns_max, stats.count), (12, 12, 1));
    stats.add(3);
    assert_eq!((stats.ns_min, stats.ns_max, stats.count), (3, 12, 2));
}

#[test]
fn empty_continuation_remains_empty_and_url_decoding_handles_all_bytes() {
    let _library = Library::acquire();
    let mut parsed = parse::State::default();
    parse::parse_page(
        b"<ListBucketResult><NextContinuationToken></NextContinuationToken></ListBucketResult>",
        Operation::ListObjectsV2,
        &mut parsed,
        &mut |_| 0,
    )
    .unwrap();
    assert_eq!(parsed.next_token, Some(Vec::new()));
    for byte in u8::MIN..=u8::MAX {
        let encoded = format!(
            "<ListBucketResult><EncodingType>url</EncodingType><Contents><Key>%{byte:02X}</Key>\
             </Contents></ListBucketResult>"
        );
        let mut names = Vec::new();
        parse::parse_page(
            encoded.as_bytes(),
            Operation::ListObjectsV2,
            &mut parsed,
            &mut |entry| {
                names.push(entry.name);
                0
            },
        )
        .unwrap();
        let expected = if byte.is_ascii() {
            vec![byte]
        } else {
            "\u{fffd}".into()
        };
        assert_eq!(names, [expected]);
    }
}
