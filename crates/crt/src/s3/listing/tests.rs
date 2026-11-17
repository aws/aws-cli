#![expect(
    clippy::unwrap_used,
    clippy::expect_used,
    reason = "scripted fixtures assert their setup and expected parse success"
)]
use super::*;
use super::{
    driver::{Options, PageOps, Submit},
    page::Page,
    request::{Operation, Query},
};
use crate::{
    runtime::Library,
    s3::{ArchiveState, TransferResult},
};
use cli_core::interrupt::Canceled;
use std::{collections::VecDeque, sync::Arc};

#[derive(Default)]
struct FakePages {
    bodies: VecDeque<&'static [u8]>,
    paths: Vec<Vec<u8>>,
    canceled: usize,
    released: usize,
}
impl PageOps for FakePages {
    type Handle = Arc<Page>;
    fn submit(
        &mut self,
        page: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        self.paths.push(path.to_vec());
        let body = self.bodies.pop_front().expect("scripted page");
        let result = match page.append_chunk(body) {
            Ok(()) => TransferResult {
                response_status: 200,
                ..TransferResult::default()
            },
            Err(code) => TransferResult::from_crt_error(code),
        };
        page.finish(result);
        Ok(Submit::Submitted(Arc::clone(page)))
    }
    fn cancel(&mut self, _: &Self::Handle) {
        self.canceled += 1;
    }
    fn release(&mut self, page: Self::Handle) {
        self.released += 1;
        page.shutdown();
    }
    fn backoff(&mut self, _: u64, _: crate::s3::botocore_retry::ErrorKind) -> Result<(), Canceled> {
        Ok(())
    }
}
fn options(prefetch: bool) -> Options<'static> {
    Options::new(
        b"/bucket",
        Query {
            operation: Operation::ListObjectsV2,
            prefix: b"a b",
            delimiter: b"/",
            region: b"",
            page_size: 2,
        },
        prefetch,
    )
}
#[test]
fn page_parser_preserves_prefix_order_dates_binary_names_and_archive_state() {
    let _library = Library::acquire();
    let body = b"<ListBucketResult><Contents><Key>a%00%FF+z</Key><Size>42</Size><L\
        astModified>2021-06-01T12:00:00.000Z</LastModified><StorageClass>\
        GLACIER</StorageClass></Contents><CommonPrefixes><Prefix>p%2F</Pr\
        efix></CommonPrefixes><Contents><Key>b</Key><StorageClass>DEEP_AR\
        CHIVE</StorageClass></Contents><EncodingType>url</EncodingType><I\
        sTruncated>TRUE</IsTruncated><NextContinuationToken>next</NextCon\
        tinuationToken></ListBucketResult>";
    let mut parsed = parse::State::default();
    let mut entries = Vec::new();
    parse::parse_page(body, Operation::ListObjectsV2, &mut parsed, &mut |entry| {
        entries.push(entry);
        0
    })
    .unwrap();
    assert_eq!(
        entries.iter().map(|e| e.kind).collect::<Vec<_>>(),
        [
            EntryKind::CommonPrefix,
            EntryKind::Object,
            EntryKind::Object
        ]
    );
    assert_eq!(entries[1].name, "a\0\u{fffd} z".as_bytes());
    assert_eq!(entries[1].size, 42);
    assert_eq!(
        entries[1].date.map(|date| date.epoch_seconds),
        Some(1622548800)
    );
    assert!(entries[1].archive.archived && entries[2].archive.archived);
    assert!(!entries[1].archive.restored);
    assert_eq!(entries[0].name, b"p/");
    assert_eq!(parsed.next_token.as_deref(), Some(b"next".as_slice()));
    assert!(parsed.has_more_results);
}
#[test]
fn finish_response_keeps_the_status_of_a_precondition_failure() {
    let _library = Library::acquire();
    let page = Page::new(4096);
    let body = b"<Error><Code>PreconditionFailed</Code><Message>m</Message></Error>";
    page.finish_response(3, 400, body, b"ListObjectsV2");
    page.wait_complete();
    let state = crate::signal::lock(&page.inner);
    let result = state.result.as_ref().unwrap();
    assert_eq!((result.error_code, result.response_status), (3, 400));
    assert_eq!(result.service_error.code.as_bytes(), b"PreconditionFailed");
}
#[test]
fn each_object_keeps_what_the_glacier_rule_reads_from_its_storage_class() -> Result<(), i32> {
    let _library = Library::acquire();
    let body = concat!(
        "<ListBucketResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\">",
        "<Name>bucket</Name><EncodingType>url</EncodingType><IsTruncated>false</IsTruncated>",
        "<Contents><Key>glacier</Key><Size>1</Size><StorageClass>GLACIER</StorageClass>",
        "</Contents>",
        "<Contents><Key>deep</Key><Size>1</Size><StorageClass>DEEP_ARCHIVE</StorageClass>",
        "</Contents>",
        "<Contents><Key>instant</Key><Size>1</Size><StorageClass>GLACIER_IR</StorageClass>",
        "</Contents>",
        "<Contents><Key>restored</Key><Size>1</Size><StorageClass>GLACIER</StorageClass>",
        "<RestoreStatus><IsRestoreInProgress>false</IsRestoreInProgress>",
        "<RestoreExpiryDate>2012-12-21T00:00:00.000Z</RestoreExpiryDate></RestoreStatus>",
        "</Contents>",
        "<Contents><Key>standard</Key><Size>1</Size><StorageClass>STANDARD</StorageClass>",
        "</Contents>",
        "<Contents><Key>unclassed</Key><Size>1</Size></Contents>",
        "</ListBucketResult>",
    );
    let mut parsed = parse::State::default();
    let mut entries = Vec::new();
    parse::parse_page(
        body.as_bytes(),
        Operation::ListObjectsV2,
        &mut parsed,
        &mut |entry| {
            entries.push(entry);
            0
        },
    )?;
    let listed = entries
        .iter()
        .map(|entry| {
            let ArchiveState { archived, restored } = entry.archive;
            (entry.name.as_slice(), archived, restored)
        })
        .collect::<Vec<_>>();
    assert_eq!(
        listed,
        [
            (&b"glacier"[..], true, false),
            (b"deep", true, false),
            (b"instant", false, false),
            (b"restored", true, false),
            (b"standard", false, false),
            (b"unclassed", false, false),
        ]
    );
    Ok(())
}
#[test]
fn parser_rejects_bad_roots_sizes_escapes_and_preserves_sink_failure() {
    let _library = Library::acquire();
    for (body, expected) in [
        (
            b"<Wrong/>".as_slice(),
            crate::s3::ListLocalError::UnexpectedRoot,
        ),
        (
            b"<ListBucketResult><Contents><Size>big</Size></Contents></ListBucketResult>",
            crate::s3::ListLocalError::InvalidNumber,
        ),
        (
            b"<ListBucketResult><Contents><Key>&undefined;</Key></Contents></ListBucketResult>",
            crate::s3::ListLocalError::InvalidXmlText,
        ),
    ] {
        let mut parsed = parse::State::default();
        assert!(
            parse::parse_page(body, Operation::ListObjectsV2, &mut parsed, &mut |_| 0).is_err()
        );
        assert_eq!(parsed.local_error, Some(expected));
    }
    let mut parsed = parse::State::default();
    assert_eq!(
        parse::parse_page(
            b"<ListBucketResult><Contents><Key>a</Key></Contents><Contents><Key\
        >b</Key></Contents></ListBucketResult>",
            Operation::ListObjectsV2,
            &mut parsed,
            &mut |_| 17
        ),
        Err(crate::s3::CANCELED_ERROR_CODE)
    );
    assert_eq!(parsed.callback_error, 17);
    assert_eq!(parsed.local_error, None);
    assert_eq!(parsed.entries_emitted, 1);
}
#[test]
fn query_order_and_bucket_pagination_are_distinct() {
    assert_eq!(
        options(true).query.build_path(b"/bucket", Some(b"a+/=")),
        b"/bucket?list-type=2&prefix=a%20b&delimiter=%2F&max-keys=2&continu\
        ation-token=a%2B%2F%3D&encoding-type=url"
    );
    let query = Query {
        operation: Operation::ListBuckets,
        prefix: b"a",
        delimiter: b"",
        region: b"us-east-1",
        page_size: 3,
    };
    assert_eq!(
        query.build_path(b"", Some(b"next")),
        b"/?prefix=a&bucket-region=us-east-1&max-buckets=3&continuation-token=next"
    );
    let mut parsed = parse::State::default();
    let _library = Library::acquire();
    let mut names = Vec::new();
    parse::parse_page(
        b"<ListAllMyBucketsResult><Buckets><Bucket><Name>a</Name><CreationD\
        ate>2021-06-01T12:00:00Z</CreationDate></Bucket></Buckets><Contin\
        uationToken>next</ContinuationToken></ListAllMyBucketsResult>",
        Operation::ListBuckets,
        &mut parsed,
        &mut |entry| {
            names.push(entry.name);
            0
        },
    )
    .unwrap();
    assert_eq!(names, [b"a"]);
    assert!(parsed.has_more_results);
}
fn expect_path(base: &[u8], query: Query<'_>, token: Option<&[u8]>, expected: &str) {
    assert_eq!(
        String::from_utf8_lossy(&query.build_path(base, token)),
        expected
    );
}
fn objects<'a>(prefix: &'a [u8], delimiter: &'a [u8], page_size: u32) -> Query<'a> {
    Query {
        operation: Operation::ListObjectsV2,
        prefix,
        delimiter,
        region: b"",
        page_size,
    }
}
fn buckets<'a>(prefix: &'a [u8], region: &'a [u8], page_size: u32) -> Query<'a> {
    Query {
        operation: Operation::ListBuckets,
        prefix,
        delimiter: b"",
        region,
        page_size,
    }
}
#[test]
fn list_objects_path_follows_the_cli_parameter_order() {
    expect_path(
        b"",
        objects(b"", b"", 0),
        None,
        "/?list-type=2&prefix=&encoding-type=url",
    );
    expect_path(
        b"/bucket",
        objects(b"a b/c", b"/", 1000),
        Some(b"t/+="),
        "/bucket?list-type=2&prefix=a%20b%2Fc&delimiter=%2F&max-keys=1000\
        &continuation-token=t%2F%2B%3D&encoding-type=url",
    );
    expect_path(
        b"/base/",
        objects(b"~-_.", b"", 0),
        Some(b""),
        "/base/?list-type=2&prefix=~-_.&encoding-type=url",
    );
}
#[test]
fn list_buckets_path_sends_only_the_filters_given() {
    expect_path(b"", buckets(b"", b"", 0), None, "/");
    expect_path(
        b"",
        buckets(b"team-", b"us-west-2", 5),
        Some(b"x y"),
        "/?prefix=team-&bucket-region=us-west-2&max-buckets=5&continuation-token=x%20y",
    );
    expect_path(b"/custom", buckets(b"", b"", 0), None, "/custom");
}
fn message_fields(message: &super::message::Message) -> Vec<(String, String)> {
    use crt_sys::{AwsByteCursor, native as c};
    let text = |cursor: AwsByteCursor| {
        if cursor.len == 0 {
            return String::new();
        }
        // SAFETY: a nonempty cursor borrows the live message's storage.
        let bytes = unsafe { std::slice::from_raw_parts(cursor.ptr, cursor.len) };
        String::from_utf8_lossy(bytes).into_owned()
    };
    // SAFETY: the message is live.
    let count = unsafe { c::aws_http_message_get_header_count(message.pointer()) };
    (0..count as u32 + 2)
        .map(|index| {
            let mut name = AwsByteCursor::from_bytes(&[]);
            let mut value = name;
            // SAFETY: the message is live, and the cursors are copied before it is dropped.
            let rc =
                unsafe { c::zaws_message_field(message.pointer(), index, &mut name, &mut value) };
            assert_eq!(rc, 0);
            (text(name), text(value))
        })
        .collect()
}
fn expect_message(message: &super::message::Message, path: &str, headers: &[(&str, &str)]) {
    let mut expected = vec![("", "GET"), ("", path)];
    expected.extend_from_slice(headers);
    let fields = message_fields(message);
    let actual = fields
        .iter()
        .map(|(name, value)| (name.as_str(), value.as_str()))
        .collect::<Vec<_>>();
    assert_eq!(actual, expected);
}
#[test]
fn the_get_message_carries_the_host_accept_user_agent_and_payer_headers() {
    let _library = Library::acquire();
    let message = super::message::Message::new(
        b"bucket.s3.test",
        b"/?list-type=2",
        b"requester",
        b"aws-cli/2.0 md/test",
    )
    .unwrap();
    expect_message(
        &message,
        "/?list-type=2",
        &[
            ("host", "bucket.s3.test"),
            ("accept", "application/xml"),
            ("user-agent", "aws-cli/2.0 md/test"),
            ("x-amz-request-payer", "requester"),
        ],
    );
    let bare = super::message::Message::new(b"s3.test", b"/", b"", b"aws-cli-native").unwrap();
    expect_message(
        &bare,
        "/",
        &[
            ("host", "s3.test"),
            ("accept", "application/xml"),
            ("user-agent", "aws-cli-native"),
        ],
    );
}
#[test]
fn incremental_probe_finds_every_chunk_boundary_and_rejects_entities() {
    let body = b"<ListBucketResult><NextContinuationToken>token</NextContinuationT\
        oken></ListBucketResult>";
    for boundary in 0..body.len() {
        let mut probe = TokenProbe::default();
        probe.scan(&body[..boundary]);
        assert_eq!(probe.scan(body), ProbeState::Token);
        assert_eq!(&body[probe.value_range()], b"token");
    }
    let mut probe = TokenProbe::default();
    assert_eq!(
        probe.scan(b"<NextContinuationToken>a&amp;b</NextContinuationToken>"),
        ProbeState::Unresolved
    );
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one assertion sequence covers cancellation, reissue, and final statistics"
)]
fn driver_releases_both_slots_and_reconciles_prefetch_token_with_authoritative_parse() {
    let _library = Library::acquire();
    let first = b"<ListBucketResult><NextContinuationToken>guess</NextContinuationT\
        oken><NextContinuationToken>actual</NextContinuationToken><IsTrun\
        cated>true</IsTruncated></ListBucketResult>"
        .as_slice();
    let final_page = b"<ListBucketResult><Contents><Key>last</Key></Contents><IsTruncate\
        d>false</IsTruncated></ListBucketResult>"
        .as_slice();
    let mut ops = FakePages {
        bodies: [first, final_page, final_page].into(),
        ..FakePages::default()
    };
    let mut stats = ListStats::default();
    let mut names = Vec::new();
    let result = driver::run(options(true), &mut ops, Some(&mut stats), &mut |entry| {
        names.push(entry.name);
        0
    });
    assert_eq!(result.transfer.error_code, 0);
    assert_eq!(ops.paths.len(), 3);
    assert!(ops.paths[1].windows(5).any(|v| v == b"guess"));
    assert!(ops.paths[2].windows(6).any(|v| v == b"actual"));
    assert_eq!(ops.canceled, 1);
    assert_eq!(ops.released, 3);
    assert_eq!(names, [b"last"]);
    assert_eq!(stats.pages, 2);
    assert_eq!(stats.token_mismatch, 1);
    assert_eq!(stats.shutdown_wait.count, 2);
}
#[test]
fn a_page_that_is_not_utf8_fails_as_a_500_with_every_attempt_folded() {
    assert_malformed_second_page_ends_the_run(
        b"<ListBucketResult><Contents><Key>a</Key></Contents><Contents><Key>\
        k\xff</Key></Contents></ListBucketResult>",
    );
}
#[test]
fn a_page_with_a_character_xml_does_not_allow_fails_as_a_500_with_every_attempt_folded() {
    assert_malformed_second_page_ends_the_run(
        b"<ListBucketResult><Contents><Key>a</Key></Contents><Contents><Key>\
        k&#1;</Key></Contents></ListBucketResult>",
    );
}
fn assert_malformed_second_page_ends_the_run(second: &'static [u8]) {
    let _library = Library::acquire();
    let first = b"<ListBucketResult><Contents><Key>first</Key></Contents><IsTruncated>t\
        rue</IsTruncated><NextContinuationToken>next</NextContinuationToken></List\
        BucketResult>"
        .as_slice();
    for prefetch in [false, true] {
        let mut ops = FakePages {
            bodies: [first, second, second, second].into(),
            ..FakePages::default()
        };
        let mut stats = ListStats::default();
        let mut names = Vec::new();
        let result = driver::run(
            options(prefetch),
            &mut ops,
            Some(&mut stats),
            &mut |entry| {
                names.push(entry.name);
                0
            },
        );
        let failed = (
            result.local_error,
            result.transfer.response_status,
            result.transfer.retries_exhausted,
            result.request_path.clone(),
        );
        let expected = (None, 500, Some(2), ops.paths[1].clone());
        assert_eq!(failed, expected, "prefetch {prefetch}");
        assert_eq!(
            ops.paths[1..],
            [
                ops.paths[1].clone(),
                ops.paths[1].clone(),
                ops.paths[1].clone()
            ]
        );
        assert_eq!(
            (names, ops.paths.len(), ops.released),
            (vec![b"first".to_vec()], 4, 4),
            "prefetch {prefetch}"
        );
        assert_eq!(
            (stats.pages, stats.entries, stats.body_bytes),
            (4, 1, (first.len() + 3 * second.len()) as u64),
            "prefetch {prefetch}"
        );
    }
}
#[test]
fn driver_enforces_body_and_page_budgets() {
    let _library = Library::acquire();
    let page = b"<ListBucketResult><NextContinuationToken>next</NextContinuationTo\
        ken><IsTruncated>true</IsTruncated></ListBucketResult>"
        .as_slice();
    let mut ops = FakePages {
        bodies: [page].into(),
        ..FakePages::default()
    };
    let mut opts = options(true);
    opts.page_body_bytes_max = 32;
    assert_ne!(
        driver::run(opts, &mut ops, None, &mut |_| 0)
            .transfer
            .error_code,
        0
    );
    assert_eq!(ops.released, 1);
    let mut ops = FakePages {
        bodies: [page].into(),
        ..FakePages::default()
    };
    let mut opts = options(true);
    opts.page_count_max = 1;
    let result = driver::run(opts, &mut ops, None, &mut |_| 0);
    assert_eq!(
        result.local_error,
        Some(crate::s3::ListLocalError::PageLimitExceeded)
    );
    assert_eq!(result.transfer.error_code, 0);
    assert!(result.transfer.crt_name.as_bytes().is_empty());
    assert!(result.transfer.crt_message.as_bytes().is_empty());
    assert!(result.request_path.is_empty());
    assert_eq!(ops.paths.len(), 1);
}
#[test]
fn page_budget_bounds_cycled_continuations_and_submissions() {
    let _library = Library::acquire();
    let first = b"<ListBucketResult><Contents><Key>a</Key><Size>1</Size></Contents>\
        <IsTruncated>true</IsTruncated><NextContinuationToken>token-1</NextContinuat\
        ionToken></ListBucketResult>"
        .as_slice();
    let second = b"<ListBucketResult><Contents><Key>b</Key><Size>2</Size></Contents>\
        <IsTruncated>true</IsTruncated><NextContinuationToken>token-2</NextContinuat\
        ionToken></ListBucketResult>"
        .as_slice();
    for prefetch in [false, true] {
        for page_limit in 1..=3 {
            let mut ops = FakePages {
                bodies: [first, second, first].into(),
                ..FakePages::default()
            };
            let mut opts = options(prefetch);
            opts.page_count_max = page_limit;
            let mut stats = ListStats::default();
            let mut emitted = 0;
            let result = driver::run(opts, &mut ops, Some(&mut stats), &mut |_| {
                emitted += 1;
                0
            });
            assert_eq!(
                result.local_error,
                Some(crate::s3::ListLocalError::PageLimitExceeded)
            );
            assert_eq!(ops.paths.len(), page_limit);
            assert_eq!(ops.released, page_limit);
            assert_eq!(emitted, page_limit);
            assert_eq!(stats.pages, page_limit as u64);
            assert_eq!(ops.canceled, 0);
        }
    }
}
#[test]
fn a_page_that_repeats_its_request_token_stops_the_run_after_emitting() {
    let _library = Library::acquire();
    let first = b"<ListBucketResult><Contents><Key>a</Key></Contents><IsTruncated>t\
        rue</IsTruncated><NextContinuationToken>token-1</NextContinuationT\
        oken></ListBucketResult>"
        .as_slice();
    let repeat = b"<ListBucketResult><Contents><Key>b</Key></Contents><IsTruncated>t\
        rue</IsTruncated><NextContinuationToken>token-1</NextContinuationT\
        oken></ListBucketResult>"
        .as_slice();
    let final_page = b"<ListBucketResult><Contents><Key>c</Key></Contents><IsTruncate\
        d>false</IsTruncated></ListBucketResult>"
        .as_slice();
    for prefetch in [true, false] {
        let mut ops = FakePages {
            bodies: [first, repeat, final_page].into(),
            ..FakePages::default()
        };
        let mut names = Vec::new();
        let result = driver::run(options(prefetch), &mut ops, None, &mut |entry| {
            names.push(entry.name);
            0
        });
        assert_eq!(result.transfer.error_code, 0);
        assert_eq!(
            result.repeated_token.as_deref(),
            Some(b"token-1".as_slice())
        );
        assert_eq!(names, [b"a", b"b"]);
        assert_eq!(ops.paths.len(), 2);
        assert!(ops.paths[1].windows(7).any(|v| v == b"token-1"));
        assert_eq!(ops.canceled, 0);
    }
}

mod contracts;
mod fuzz;
mod lifecycle;
mod loopback;
mod retry;
mod xml;

#[test]
fn listing_dates_retain_signed_epoch_and_missing_dates() {
    let _library = Library::acquire();
    for (date, epoch) in [
        (b"1969-12-31T23:59:59Z".as_slice(), -1),
        (b"1970-01-01T00:00:00Z", 0),
        (b"2021-06-01T12:00:00.000Z", 1_622_548_800),
    ] {
        assert_eq!(
            parse_list_date(date).map(|date| date.epoch_seconds),
            Some(epoch)
        );
    }
    assert!(parse_list_date(b"not a date").is_none());
}

#[derive(Default)]
struct RedirectPages {
    responses: VecDeque<(&'static [u8], i32, i32)>,
    paths: Vec<Vec<u8>>,
    recoveries: usize,
    released: usize,
}
impl PageOps for RedirectPages {
    type Handle = Arc<Page>;
    fn submit(
        &mut self,
        page: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        self.paths.push(path.to_vec());
        let (body, error_code, response_status) =
            self.responses.pop_front().expect("scripted page");
        page.append_chunk(body).unwrap();
        page.finish(TransferResult {
            error_code,
            response_status,
            ..TransferResult::default()
        });
        Ok(Submit::Submitted(Arc::clone(page)))
    }
    fn recover_region(&mut self, _failed: &crate::s3::ListResult) -> bool {
        self.recoveries += 1;
        true
    }
    fn cancel(&mut self, _: &Self::Handle) {}
    fn release(&mut self, page: Self::Handle) {
        self.released += 1;
        page.shutdown();
    }
    fn backoff(&mut self, _: u64, _: crate::s3::botocore_retry::ErrorKind) -> Result<(), Canceled> {
        Ok(())
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test follows every page of the redirected listing"
)]
fn redirect_replays_only_the_failed_page_with_its_authoritative_token() {
    let _library = Library::acquire();
    let first: &[u8] = b"<ListBucketResult><Contents><Key>a</Key><Size>1</Size></Contents><Is\
        Truncated>true</IsTruncated><NextContinuationToken>token-1</NextContinuationTok\
        en></ListBucketResult>";
    let last: &[u8] = b"<ListBucketResult><Contents><Key>c</Key><Size>3</Size></Contents><Is\
        Truncated>false</IsTruncated></ListBucketResult>";
    let query = Query {
        operation: Operation::ListObjectsV2,
        prefix: b"",
        delimiter: b"",
        region: b"",
        page_size: 0,
    };
    let token_path = query.build_path(b"/bucket", Some(b"token-1"));
    for prefetch in [false, true] {
        for retry_fails in [false, true] {
            let mut ops = RedirectPages {
                responses: [
                    (first, 0, 200),
                    (b"".as_slice(), 1, 301),
                    if retry_fails {
                        (b"".as_slice(), 1, 307)
                    } else {
                        (last, 0, 200)
                    },
                ]
                .into(),
                ..RedirectPages::default()
            };
            let mut names = Vec::new();
            let result = driver::run(
                Options::new(b"/bucket", query, prefetch),
                &mut ops,
                None,
                &mut |entry| {
                    names.push(entry.name);
                    0
                },
            );
            assert_eq!(ops.paths.len(), 3);
            assert_eq!(ops.released, 3);
            assert_eq!(ops.recoveries, 1);
            assert_eq!(ops.paths[1], token_path);
            assert_eq!(ops.paths[2], token_path);
            let expected: &[&[u8]] = if retry_fails { &[b"a"] } else { &[b"a", b"c"] };
            assert_eq!(names, expected);
            assert_eq!(
                result.transfer.response_status,
                if retry_fails { 307 } else { 200 }
            );
            let failed_path: &[u8] = if retry_fails { &token_path } else { b"" };
            assert_eq!(result.request_path, failed_path);
        }
    }
}

#[derive(Default)]
struct RefusedPages {
    paths: Vec<Vec<u8>>,
}
impl PageOps for RefusedPages {
    type Handle = Arc<Page>;
    fn submit(
        &mut self,
        page: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        self.paths.push(path.to_vec());
        page.finish(TransferResult::from_crt_error(
            crt_sys::AWS_IO_SOCKET_CONNECTION_REFUSED,
        ));
        Ok(Submit::Submitted(Arc::clone(page)))
    }
    fn cancel(&mut self, _: &Self::Handle) {}
    fn release(&mut self, page: Self::Handle) {
        page.shutdown();
    }
    fn backoff(&mut self, _: u64, _: crate::s3::botocore_retry::ErrorKind) -> Result<(), Canceled> {
        Ok(())
    }
}

#[test]
fn a_failed_page_carries_its_whole_request_path_however_long() {
    let _library = Library::acquire();
    let endpoint_path = [b"/".as_slice(), &[b'p'; 5000], b"/bucket"].concat();
    let query = Query {
        operation: Operation::ListObjectsV2,
        prefix: b"",
        delimiter: b"",
        region: b"",
        page_size: 0,
    };
    let mut ops = RefusedPages::default();
    let result = driver::run(
        Options::new(&endpoint_path, query, true),
        &mut ops,
        None,
        &mut |_| 0,
    );
    assert_eq!(
        result.transfer.error_code,
        crt_sys::AWS_IO_SOCKET_CONNECTION_REFUSED
    );
    let expected = [
        endpoint_path.as_slice(),
        b"?list-type=2&prefix=&encoding-type=url",
    ]
    .concat();
    assert_eq!(result.request_path, expected);
    assert_eq!(ops.paths, [expected]);
}
