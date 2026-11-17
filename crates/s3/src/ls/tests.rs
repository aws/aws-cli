#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
use cli_core::{
    cli_error::{Category, ErrorFormat, exit_status, render_command_failure},
    output::EntryDate,
};
use crt::s3::{BoundedText, ListResult, TransferResult};
use std::ffi::OsString;
use std::io::{self, Write};
#[derive(Default)]
struct FakeBackend {
    entries: Vec<Entry>,
    result: ListResult,
    expected: Option<Expected>,
    pages: u64,
    stats_requested: Option<bool>,
    calls: usize,
}
struct Expected {
    bucket: Option<&'static str>,
    prefix: &'static str,
    recursive: bool,
    page_size: u32,
    payer: Option<&'static str>,
    bucket_prefix: Option<&'static str>,
    bucket_region: Option<&'static str>,
}
impl Expected {
    fn check(&self, request: Request<'_>) {
        assert_eq!(request.target.bucket, self.bucket);
        assert_eq!(request.target.prefix, self.prefix.as_bytes());
        assert_eq!(request.recursive, self.recursive);
        assert_eq!(request.page_size, self.page_size);
        assert_eq!(request.request_payer, self.payer);
        assert_eq!(request.bucket_name_prefix, self.bucket_prefix);
        assert_eq!(request.bucket_region, self.bucket_region);
    }
}
impl Backend for FakeBackend {
    fn list(
        &mut self,
        request: Request<'_>,
        callback: &mut dyn FnMut(Entry) -> i32,
        stats: Option<&mut crt::s3::ListStats>,
    ) -> ListResult {
        self.calls += 1;
        if let Some(expected) = &self.expected {
            expected.check(request);
        }
        self.stats_requested = Some(stats.is_some());
        if let Some(stats) = stats {
            stats.pages = self.pages;
        }
        for entry in self.entries.clone() {
            if callback(entry) != 0 {
                self.result.callback_error = -1;
                break;
            }
        }
        self.result.clone()
    }
}
fn args(paths: &str) -> Args {
    Args {
        paths: paths.into(),
        dir_op: false,
        page_size: None,
        human_readable: false,
        summarize: false,
        request_payer: None,
        bucket_name_prefix: None,
        bucket_region: None,
    }
}
fn entry(kind: EntryKind, name: &[u8], size: u64) -> Entry {
    Entry {
        kind,
        name: name.into(),
        size,
        date: EntryDate::default(),
    }
}
fn options(args: &Args, collect_stats: bool) -> ListExecutionOptions<'_> {
    let target = uri::parse_s3_list_target(Some(args.paths.as_encoded_bytes())).unwrap();
    ListExecutionOptions::new(args, target, collect_stats)
}
fn list(
    backend: &mut FakeBackend,
    args: &Args,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
    collect_stats: bool,
) -> Result<u8, Error> {
    execute(backend, options(args, collect_stats), stdout, stderr)
}
fn run_fake(args: &Args, entries: Vec<Entry>) -> (u8, Vec<u8>) {
    let mut out = Vec::new();
    let mut backend = FakeBackend {
        entries,
        ..Default::default()
    };
    let status = list(&mut backend, args, &mut out, &mut Vec::new(), false).unwrap();
    (status, out)
}
#[test]
fn parses_bucket_and_object_targets() {
    let target =
        |original: &'static str, bucket, prefix: &'static str, has_prefix| uri::S3ListTarget {
            original: original.as_bytes(),
            bucket,
            prefix: prefix.as_bytes(),
            has_prefix,
        };
    for value in [None, Some("s3://")] {
        assert_eq!(
            uri::parse_s3_list_target(value.map(str::as_bytes)),
            Ok(target("s3://", None, "", false))
        );
    }
    for (value, bucket, prefix, has_prefix) in [
        ("s3://bucket", "bucket", "", false),
        ("s3://bucket/", "bucket", "", false),
        ("s3://bucket/path/to", "bucket", "path/to", true),
        ("bucket", "bucket", "", false),
        ("bucket/path/to", "bucket", "path/to", true),
    ] {
        assert_eq!(
            uri::parse_s3_list_target(Some(value.as_bytes())),
            Ok(target(value, Some(bucket), prefix, has_prefix))
        );
    }
}
#[test]
fn rejects_missing_buckets_and_foreign_schemes() {
    for value in ["/prefix", "s3:///prefix", "s3:////"] {
        assert_eq!(
            uri::parse_s3_list_target(Some(value.as_bytes())),
            Err(uri::S3ListTargetParseError::MissingS3Bucket)
        );
    }
    for value in ["s3:/bad", "https://bucket", "S3://bucket"] {
        assert_eq!(
            uri::parse_s3_list_target(Some(value.as_bytes())),
            Err(uri::S3ListTargetParseError::InvalidS3UriScheme)
        );
    }
}
#[test]
fn a_refused_target_is_a_general_failure_with_an_invalid_ls_uri_message() {
    for (target, message) in [
        (
            "https://bucket",
            "error: invalid S3 URI for ls: expected s3://bucket[/prefix] or bucket[/prefix]",
        ),
        (
            "s3:bucket",
            "error: invalid S3 URI for ls: expected s3://bucket[/prefix] or bucket[/prefix]",
        ),
        (
            "s3:///prefix",
            "error: invalid S3 URI for ls: missing bucket name",
        ),
    ] {
        let error = uri::parse_s3_list_target(Some(target.as_bytes())).unwrap_err();
        let failure = listing::invalid_target_failure(error);
        assert_eq!(failure.category, Category::General);
        assert_eq!(String::from_utf8_lossy(&failure.message), message);
    }
}
#[test]
fn absent_or_bare_target_lists_buckets() {
    for value in [None, Some("s3://")] {
        let input = args(value.unwrap_or("s3://"));
        let target = uri::parse_s3_list_target(value.map(str::as_bytes)).unwrap();
        let mut backend = FakeBackend {
            expected: Some(Expected {
                bucket: None,
                prefix: "",
                recursive: false,
                page_size: 0,
                payer: None,
                bucket_prefix: None,
                bucket_region: None,
            }),
            ..Default::default()
        };
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let options = ListExecutionOptions::new(&input, target, false);
        assert_eq!(
            execute(&mut backend, options, &mut stdout, &mut stderr).unwrap(),
            0
        );
        assert_eq!(backend.calls, 1);
        assert!(stdout.is_empty() && stderr.is_empty());
    }
    assert_eq!(uri::parse_s3_list_target(Some(b"")).unwrap().bucket, None);
}
#[test]
fn object_output_raw_recursive_and_human() {
    let object = entry(EntryKind::Object, b"path/file", 1024);
    let mut input = args("bucket");
    assert_eq!(
        run_fake(&input, vec![object.clone()]).1,
        b"0000-00-00 00:00:00       1024 file\n"
    );
    input.dir_op = true;
    input.human_readable = true;
    assert_eq!(
        run_fake(&input, vec![object]).1,
        b"0000-00-00 00:00:00    1.0 KiB path/file\n"
    );
}
#[test]
fn plain_and_uri_targets_are_equivalent() {
    let entries = vec![entry(EntryKind::Object, b"prefix/file", 7)];
    assert_eq!(
        run_fake(&args("bucket/prefix"), entries.clone()),
        run_fake(&args("s3://bucket/prefix"), entries)
    );
}
#[test]
fn prefix_and_bucket_entries_render_by_kind() {
    let entries = vec![
        entry(EntryKind::CommonPrefix, b"a/b/", 100),
        entry(EntryKind::Bucket, b"bucket", 99),
        entry(EntryKind::Object, b"a/key", 3),
    ];
    let output = run_fake(&args("bucket"), entries).1;
    assert_eq!(
        String::from_utf8(output).unwrap(),
        "                           PRE b/\n\
         0000-00-00 00:00:00 bucket\n\
         0000-00-00 00:00:00          3 key\n"
    );
}
#[test]
fn prefix_delimiter_basename_rules() {
    for (prefix, name) in [("a/b/", "b"), ("a//", ""), ("name", "name"), ("/", "")] {
        let common_prefix = entry(EntryKind::CommonPrefix, prefix.as_bytes(), 0);
        let output = run_fake(&args("bucket"), vec![common_prefix]).1;
        assert_eq!(
            String::from_utf8(output).unwrap(),
            format!("                           PRE {name}/\n")
        );
    }
}
#[test]
fn summaries_count_only_objects() {
    let mut input = args("bucket");
    input.summarize = true;
    assert_eq!(
        run_fake(&input, vec![]).1,
        b"\nTotal Objects: 0\n   Total Size: 0\n"
    );
    let (_, out) = run_fake(
        &input,
        vec![
            entry(EntryKind::Object, b"one", 1),
            entry(EntryKind::CommonPrefix, b"prefix/", 0),
        ],
    );
    assert!(out.ends_with(b"\nTotal Objects: 1\n   Total Size: 1\n"));
    input.human_readable = true;
    let (_, out) = run_fake(
        &input,
        vec![
            entry(EntryKind::Object, b"one", 1024),
            entry(EntryKind::Object, b"two", 1024),
        ],
    );
    assert!(out.ends_with(b"\nTotal Objects: 2\n   Total Size: 2.0 KiB\n"));
}
#[test]
fn requested_prefix_without_matches_exits_one() {
    assert_eq!(run_fake(&args("bucket"), vec![]).0, 0);
    assert_eq!(run_fake(&args("bucket/"), vec![]).0, 0);
    assert_eq!(run_fake(&args("bucket/prefix"), vec![]).0, 1);
}
struct BrokenWriter;
impl Write for BrokenWriter {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> {
        Err(io::ErrorKind::BrokenPipe.into())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[test]
fn callback_preserves_underlying_output_failure() {
    let mut backend = FakeBackend {
        entries: vec![entry(EntryKind::Object, b"key", 1)],
        ..Default::default()
    };
    let listed = list(
        &mut backend,
        &args("bucket"),
        &mut BrokenWriter,
        &mut Vec::new(),
        false,
    );
    assert!(matches!(listed, Err(Error::Stdout(e)) if e.kind() == io::ErrorKind::BrokenPipe));
}
#[test]
fn callback_errors_are_user_visible_status_one() {
    let mut backend = FakeBackend {
        result: ListResult {
            callback_error: -1,
            ..Default::default()
        },
        ..Default::default()
    };
    let mut err = Vec::new();
    assert_eq!(
        list(
            &mut backend,
            &args("bucket"),
            &mut Vec::new(),
            &mut err,
            false
        )
        .unwrap(),
        1
    );
    assert_eq!(err, b"error: failed to write S3 listing output\n");
}
fn list_failure(
    error_code: i32,
    response_status: i32,
    crt_name: &str,
    crt_message: &str,
) -> ListResult {
    let mut result = ListResult {
        transfer: TransferResult {
            error_code,
            response_status,
            crt_name: BoundedText::new(crt_name),
            crt_message: BoundedText::new(crt_message),
            ..Default::default()
        },
        request_path: b"/bucket?list-type=2&prefix=&delimiter=%2F&encoding-type=url".to_vec(),
        ..Default::default()
    };
    result
        .transfer
        .service_error
        .operation
        .set(b"ListObjectsV2");
    result
}
type Classified = (ListResult, Category, u8, &'static str);
fn classified_response_failures() -> Vec<Classified> {
    let invalid_status = "AWS_ERROR_S3_INVALID_RESPONSE_STATUS";
    let mut no_such_bucket = list_failure(
        14361,
        404,
        invalid_status,
        "Invalid response status from request",
    );
    let service_error = &mut no_such_bucket.transfer.service_error;
    service_error.code.set(b"NoSuchBucket");
    service_error.message = b"The specified bucket does not exist".to_vec();
    let internal_error = "Response code indicates internal server error";
    vec![
        (
            no_such_bucket,
            Category::ClientError,
            254,
            "\naws: [ERROR]: An error occurred (NoSuchBucket) when calling the \
             ListObjectsV2 operation: The specified bucket does not exist\n",
        ),
        (
            list_failure(14361, 503, invalid_status, "x"),
            Category::ClientError,
            254,
            "\naws: [ERROR]: An error occurred (503) when calling the \
             ListObjectsV2 operation: Service Unavailable\n",
        ),
        (
            list_failure(14341, 500, "AWS_ERROR_S3_INTERNAL_ERROR", internal_error),
            Category::ClientError,
            254,
            "\naws: [ERROR]: An error occurred (500) when calling the \
             ListObjectsV2 operation: Internal Server Error\n",
        ),
        (
            list_failure(0, 204, "", ""),
            Category::ClientError,
            254,
            "\naws: [ERROR]: An error occurred (204) when calling the \
             ListObjectsV2 operation: No Content\n",
        ),
    ]
}
fn classified_retry_failures() -> Vec<Classified> {
    let mut rejected_page = list_failure(0, 500, "", "");
    rejected_page.transfer.retries_exhausted = Some(2);
    let invalid_status = "AWS_ERROR_S3_INVALID_RESPONSE_STATUS";
    let mut denied_last = list_failure(14361, 403, invalid_status, "x");
    denied_last.transfer.retries_exhausted = Some(2);
    let denied_last_bodiless = denied_last.clone();
    let service_error = &mut denied_last.transfer.service_error;
    service_error.code.set(b"AccessDenied");
    service_error.message = b"Access Denied".to_vec();
    vec![
        (
            rejected_page,
            Category::ClientError,
            254,
            "\naws: [ERROR]: An error occurred (500) when calling the \
             ListObjectsV2 operation (reached max retries: 2): Internal Server Error\n",
        ),
        (
            denied_last,
            Category::ClientError,
            254,
            "\naws: [ERROR]: An error occurred (AccessDenied) when calling the \
             ListObjectsV2 operation (reached max retries: 2): Access Denied\n",
        ),
        (
            denied_last_bodiless,
            Category::ClientError,
            254,
            "\naws: [ERROR]: An error occurred (403) when calling the \
             ListObjectsV2 operation (reached max retries: 2): Forbidden\n",
        ),
    ]
}
fn classified_request_failures() -> Vec<Classified> {
    let mut no_credentials = list_failure(
        crt::s3::NO_CREDENTIALS_ERROR_CODE,
        0,
        "AWS_AUTH_SIGNING_NO_CREDENTIALS",
        "Attempt to sign an http request without credentials.",
    );
    no_credentials.transfer.service_error.operation.set(b"");
    let refused = crt::s3::CONNECTION_REFUSED_ERROR_CODE;
    let refused_text = "socket connection refused.";
    let closed = "The connection has closed or is closing.";
    let mut repeated_token = list_failure(0, 200, "", "");
    repeated_token.repeated_token = Some(b"same'token".to_vec());
    vec![
        (
            no_credentials,
            Category::NoCredentials,
            253,
            "\naws: [ERROR]: An error occurred (NoCredentials): Unable to locate \
             credentials. You can configure credentials by running \"aws login\".\n",
        ),
        (
            list_failure(refused, 0, "AWS_IO_SOCKET_CONNECTION_REFUSED", refused_text),
            Category::General,
            255,
            "\naws: [ERROR]: Could not connect to the endpoint URL: \
             \"https://s3.test/bucket?list-type=2&prefix=&delimiter=%2F&encoding-type=url\"\n",
        ),
        (
            list_failure(
                1062,
                0,
                "AWS_IO_SOCKET_TIMEOUT",
                "socket operation timed out.",
            ),
            Category::General,
            255,
            "\naws: [ERROR]: socket operation timed out.\n",
        ),
        (
            list_failure(2058, 0, "AWS_ERROR_HTTP_CONNECTION_CLOSED", closed),
            Category::General,
            255,
            "\naws: [ERROR]: The connection has closed or is closing.\n",
        ),
        (
            repeated_token,
            Category::General,
            255,
            "\naws: [ERROR]: Error during pagination: The same next token was \
             received twice: {'ContinuationToken': \"same'token\"}\n",
        ),
    ]
}
fn failed_listing(result: &ListResult) -> ListResult {
    let mut backend = FakeBackend {
        result: result.clone(),
        ..Default::default()
    };
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    let input = args("s3://bucket");
    let listed = list(&mut backend, &input, &mut stdout, &mut stderr, false);
    assert!(stdout.is_empty() && stderr.is_empty());
    match listed {
        Err(Error::Request(failed)) => Some(*failed),
        _ => None,
    }
    .unwrap()
}
#[test]
fn listing_request_failures_classify_for_the_handler_chain() {
    let cases = [
        classified_response_failures(),
        classified_retry_failures(),
        classified_request_failures(),
    ];
    for (result, category, status, stderr) in cases.into_iter().flatten() {
        let failed = failed_listing(&result);
        assert_eq!(failed, result, "{stderr}");
        let failure = list_command_failure(&failed, "https://s3.test/bucket");
        assert_eq!(failure.category, category, "{stderr}");
        assert_eq!(failure.crt_code, result.transfer.error_code);
        assert_eq!(failure.http_status, result.transfer.response_status);
        let crt_name = result.transfer.crt_name.as_bytes();
        assert_eq!(failure.crt_name.as_bytes(), crt_name);
        let mut rendered = Vec::new();
        render_command_failure(&mut rendered, &failure, ErrorFormat::Enhanced).unwrap();
        assert_eq!(String::from_utf8(rendered).unwrap(), stderr);
        assert_eq!(exit_status(failure.category), status, "{stderr}");
    }
}
#[test]
fn object_request_forwards_all_bound_values() {
    let mut input = args("s3://bucket/prefix");
    input.dir_op = true;
    input.page_size = Some(7);
    input.request_payer = Some("requester".into());
    let mut backend = FakeBackend {
        expected: Some(Expected {
            bucket: Some("bucket"),
            prefix: "prefix",
            recursive: true,
            page_size: 7,
            payer: Some("requester"),
            bucket_prefix: None,
            bucket_region: None,
        }),
        ..Default::default()
    };
    list(
        &mut backend,
        &input,
        &mut Vec::new(),
        &mut Vec::new(),
        false,
    )
    .unwrap();
    assert_eq!(backend.stats_requested, Some(false));
}
#[test]
fn collected_stats_are_printed_when_pages_arrive() {
    let mut backend = FakeBackend {
        pages: 2,
        ..Default::default()
    };
    let mut err = Vec::new();
    list(
        &mut backend,
        &args("bucket"),
        &mut Vec::new(),
        &mut err,
        true,
    )
    .unwrap();
    assert_eq!(backend.stats_requested, Some(true));
    assert!(err.starts_with(b"zs3-list-stats: pages=2"));
}
#[test]
fn absent_pages_leave_stats_silent() {
    let mut backend = FakeBackend::default();
    let mut err = Vec::new();
    list(
        &mut backend,
        &args("bucket"),
        &mut Vec::new(),
        &mut err,
        true,
    )
    .unwrap();
    assert_eq!(backend.stats_requested, Some(true));
    assert!(err.is_empty());
}
#[test]
fn bucket_request_forwards_filters_and_ignores_stats() {
    let mut input = args("s3://");
    input.bucket_name_prefix = Some("pre".into());
    input.bucket_region = Some("us-west-2".into());
    input.page_size = Some(5);
    let mut backend = FakeBackend {
        expected: Some(Expected {
            bucket: None,
            prefix: "",
            recursive: false,
            page_size: 5,
            payer: None,
            bucket_prefix: Some("pre"),
            bucket_region: Some("us-west-2"),
        }),
        pages: 2,
        ..Default::default()
    };
    let mut err = Vec::new();
    list(&mut backend, &input, &mut Vec::new(), &mut err, true).unwrap();
    assert_eq!(backend.stats_requested, Some(false));
    assert!(err.is_empty());
}
fn bound_args(argv: &[&str]) -> Args {
    let argv: Vec<String> = argv.iter().map(|&value| value.to_owned()).collect();
    let mut result = awscli_argparse::parse(
        &argv,
        &Default::default(),
        &awscli_argparse::tables::TABLES_DEFAULT,
    );
    assert_eq!(
        result.outcome,
        awscli_argparse::chain::Outcome::Parsed,
        "{argv:?}"
    );
    let environment = awscli_argparse::unpack::Environment {
        directory: std::path::Path::new("."),
        variables: &std::collections::HashMap::new(),
        files: &awscli_argparse::unpack::FsParamfiles,
        preferred_encoding: awscli_argparse::unpack::PreferredEncoding::Locale,
    };
    assert!(!awscli_argparse::complete(&mut result, &environment));
    assert_eq!(
        result.outcome,
        awscli_argparse::chain::Outcome::Parsed,
        "{argv:?}"
    );
    Args::from_result(&result).unwrap()
}
#[test]
fn bound_arguments_arrive_resolved_from_the_upstream_ls_table() {
    for (argv, request_payer, paths, recursive) in [
        (
            &["s3", "ls", "s3://bucket", "--request-payer"][..],
            Some("requester"),
            "s3://bucket",
            false,
        ),
        (
            &["s3", "ls", "--request-payer", "--recursive", "s3://bucket"],
            Some("requester"),
            "s3://bucket",
            true,
        ),
        (
            &["s3", "ls", "--request-payer", "requester", "s3://bucket"],
            Some("requester"),
            "s3://bucket",
            false,
        ),
        (
            &["s3", "ls", "--request-payer=requester", "s3://bucket"],
            Some("requester"),
            "s3://bucket",
            false,
        ),
        (
            &[
                "s3",
                "ls",
                "s3://bucket",
                "--request-payer",
                "--request-payer",
            ],
            Some("requester"),
            "s3://bucket",
            false,
        ),
        (&["s3", "ls", "s3://bucket"], None, "s3://bucket", false),
        (&["s3", "ls"], None, "s3://", false),
    ] {
        let bound = bound_args(argv);
        assert_eq!(bound.request_payer.as_deref(), request_payer, "{argv:?}");
        assert_eq!(bound.paths, paths, "{argv:?}");
        assert_eq!(bound.dir_op, recursive, "{argv:?}");
        assert_eq!(bound.page_size, None, "{argv:?}");
        assert_eq!(admit(&bound), None, "{argv:?}");
    }
}
#[cfg(unix)]
#[test]
fn a_bucket_listing_refuses_a_filter_that_is_not_utf8_name_prefix_first() {
    use std::os::unix::ffi::OsStrExt;
    let raw = |value: &[u8]| Some(std::ffi::OsStr::from_bytes(value).to_os_string());
    let refusal = |position| {
        format!(
            "'utf-8' codec can't encode character '\\udcff' in position {position}: \
             surrogates not allowed"
        )
    };
    for (name_prefix, region, expected) in [
        (raw(b"pre-\xff"), None, Some(refusal(4))),
        (None, raw(b"region-\xff"), Some(refusal(7))),
        (raw(b"p\xff"), raw(b"region-\xff"), Some(refusal(1))),
        (raw(b"pre"), raw(b"us-west-2"), None),
    ] {
        for (paths, bucket_listing) in [("s3://", true), ("s3://bucket/prefix", false)] {
            let mut input = args(paths);
            input.bucket_name_prefix.clone_from(&name_prefix);
            input.bucket_region.clone_from(&region);
            let target = uri::parse_s3_list_target(Some(input.paths.as_encoded_bytes())).unwrap();
            let failure = native::encode(target, &input).err();
            assert_eq!(
                failure.map(|failure| String::from_utf8(failure.message).unwrap()),
                expected.clone().filter(|_| bucket_listing),
                "{paths} {name_prefix:?} {region:?}"
            );
        }
    }
}
#[cfg(unix)]
#[test]
fn admission_keeps_prefixes_that_are_not_utf8_and_refuses_such_buckets() {
    use std::os::unix::ffi::OsStrExt;
    for (target, reason) in [
        (b"s3://bucket/key-\xff".as_slice(), None),
        (b"bucket/key-\xff", None),
        (
            b"s3://bucket-\xff/key",
            Some(AdmissionReason::UnsupportedOperand),
        ),
        (b"bucket-\xff", Some(AdmissionReason::UnsupportedOperand)),
    ] {
        let mut input = args("");
        input.paths = std::ffi::OsStr::from_bytes(target).into();
        assert_eq!(admit(&input), reason, "{target:?}");
    }
    for paths in ["s3://", "s3://bucket"] {
        let mut input = args(paths);
        input.bucket_name_prefix = Some(std::ffi::OsStr::from_bytes(b"pre-\xff").into());
        input.bucket_region = Some(std::ffi::OsStr::from_bytes(b"region-\xff").into());
        assert_eq!(admit(&input), None, "{paths}");
    }
}
#[test]
fn admission_bounds_targets_and_nul_operands() {
    for target in [
        "s3://",
        "s3://bucket",
        "s3://bucket/prefix",
        "bucket",
        "bucket/prefix",
    ] {
        assert_eq!(admit(&args(target)), None, "{target}");
    }
    for target in [
        "s3:/bucket/prefix",
        "arn:aws:s3:us-east-1:123456789012:accesspoint/example",
        "s3://arn:aws:s3:us-east-1:123456789012:accesspoint/example",
        "example-123456789012-s3alias/prefix",
        "s3://example.mrap/prefix",
        "s3://example--usw2-az1--x-s3/prefix",
        "bucket name",
        "s3://bucket#name/prefix",
        "https://bucket",
        "s3://bucket/prefix\0rest",
        "s3://bucket/\0",
        "s3://bucket\0",
    ] {
        assert_eq!(
            admit(&args(target)),
            Some(AdmissionReason::UnsupportedOperand),
            "{target:?}"
        );
    }
}
#[test]
fn admission_bounds_filters_and_page_sizes() {
    for filter in ["\0", "pre\0fix"] {
        let mut input = args("s3://");
        input.bucket_name_prefix = Some(filter.into());
        assert_eq!(admit(&input), Some(AdmissionReason::UnsupportedValue));
        let mut input = args("s3://");
        input.bucket_region = Some(filter.into());
        assert_eq!(admit(&input), Some(AdmissionReason::UnsupportedValue));
    }
    for filter in [None, Some("prefix"), Some("us-east-1")] {
        let mut input = args("s3://");
        input.bucket_name_prefix = filter.map(OsString::from);
        input.bucket_region = filter.map(OsString::from);
        assert_eq!(admit(&input), None, "{filter:?}");
    }
    for size in [1, 1000, i64::from(u32::MAX)] {
        let mut input = args("s3://");
        input.page_size = Some(size);
        assert_eq!(admit(&input), None, "{size}");
    }
    for size in [0, -1, i64::from(u32::MAX) + 1] {
        let mut input = args("s3://");
        input.page_size = Some(size);
        assert_eq!(
            admit(&input),
            Some(AdmissionReason::UnsupportedValue),
            "{size}"
        );
    }
}
#[test]
fn local_listing_failures_return_before_callback_error_handling() {
    use crt::s3::ListLocalError;
    for error in [
        ListLocalError::UnexpectedRoot,
        ListLocalError::InvalidNumber,
        ListLocalError::CrtFailure,
        ListLocalError::PageBodyTooLarge,
        ListLocalError::PageLimitExceeded,
    ] {
        let mut backend = FakeBackend {
            result: ListResult {
                local_error: Some(error),
                callback_error: -1,
                ..Default::default()
            },
            ..Default::default()
        };
        let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
        let result = list(
            &mut backend,
            &args("bucket"),
            &mut stdout,
            &mut stderr,
            false,
        );
        assert!(matches!(result, Err(Error::Local(value)) if value == error));
        assert!(stdout.is_empty() && stderr.is_empty());
    }
}
struct FailingWriter(io::ErrorKind);
impl Write for FailingWriter {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> {
        Err(self.0.into())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[test]
fn buffered_output_preserves_broken_pipe_at_callback_and_final_flush() {
    for capacity in [16, 1024] {
        for kind in [io::ErrorKind::BrokenPipe, io::ErrorKind::StorageFull] {
            let mut backend = FakeBackend {
                entries: vec![entry(EntryKind::Object, b"object", 1)],
                ..Default::default()
            };
            let mut stdout = io::BufWriter::with_capacity(capacity, FailingWriter(kind));
            let mut stderr = Vec::new();
            let result = list(
                &mut backend,
                &args("bucket"),
                &mut stdout,
                &mut stderr,
                false,
            );
            assert!(matches!(result, Err(Error::Stdout(error)) if error.kind() == kind));
            assert!(stderr.is_empty());
        }
    }
}
#[test]
fn a_failed_stats_line_is_a_stderr_failure() {
    let mut backend = FakeBackend {
        entries: vec![entry(EntryKind::Object, b"object", 1)],
        pages: 1,
        ..Default::default()
    };
    let mut stdout = Vec::new();
    let result = list(
        &mut backend,
        &args("bucket"),
        &mut stdout,
        &mut FailingWriter(io::ErrorKind::BrokenPipe),
        true,
    );
    assert!(
        matches!(result, Err(Error::Stderr(error)) if error.kind() == io::ErrorKind::BrokenPipe)
    );
}
fn assert_listing_failure(error: Error, message: &str) {
    let failure = listing::listing_failure(error, "http://endpoint");
    assert_eq!(failure.category, Category::General);
    assert_eq!(String::from_utf8_lossy(&failure.message), message);
}
#[test]
fn listing_failures_name_the_stream_that_failed() {
    for (error, message) in [
        (
            Error::Stdout(io::ErrorKind::BrokenPipe.into()),
            "[Errno 32] Broken pipe",
        ),
        (
            Error::Stdout(io::ErrorKind::StorageFull.into()),
            "WriteFailed",
        ),
        (
            Error::Stderr(io::ErrorKind::BrokenPipe.into()),
            "WriteFailed",
        ),
        (
            Error::Stderr(io::Error::from_raw_os_error(libc::ENOSPC)),
            "WriteFailed",
        ),
    ] {
        assert_listing_failure(error, message);
    }
}
// Windows reports its own error codes, which have no errno text.
#[cfg(unix)]
#[test]
fn a_stdout_errno_is_the_oserror_python_raises() {
    assert_listing_failure(
        Error::Stdout(io::Error::from_raw_os_error(libc::EPIPE)),
        "[Errno 32] Broken pipe",
    );
    assert_listing_failure(
        Error::Stdout(io::Error::from_raw_os_error(libc::ENOSPC)),
        "[Errno 28] No space left on device",
    );
}
#[test]
fn execute_to_file_reports_the_commands_failure() {
    let mut backend = FakeBackend {
        result: list_failure(0, 503, "", ""),
        ..Default::default()
    };
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    let input = args("s3://bucket");
    let options = options(&input, false);
    let failure = listing::execute_to_file(
        &mut backend,
        options,
        &mut stdout,
        &mut stderr,
        "https://s3.test",
    )
    .unwrap_err();
    assert_eq!(failure.category, Category::ClientError);
    assert_eq!(failure.code, "503");
    assert!(stdout.is_empty() && stderr.is_empty());
    let mut backend = FakeBackend {
        entries: vec![entry(EntryKind::Object, b"key", 1)],
        ..Default::default()
    };
    let failure = listing::execute_to_file(
        &mut backend,
        options,
        &mut BrokenWriter,
        &mut stderr,
        "https://s3.test",
    )
    .unwrap_err();
    assert_eq!(failure.category, Category::General);
    assert_eq!(failure.message, b"[Errno 32] Broken pipe");
    assert!(stderr.is_empty());
}
#[cfg(unix)]
struct FailingStdout(i32);
#[cfg(unix)]
impl Write for FailingStdout {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> {
        Err(io::Error::from_raw_os_error(self.0))
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[cfg(unix)]
#[test]
fn a_failed_stdout_write_keeps_its_cause() {
    let row = b"2026-07-12 01:02:03          1 object\n";
    let dated = Entry {
        date: EntryDate {
            present: true,
            year: 2026,
            month: 7,
            day: 12,
            hour: 1,
            minute: 2,
            second: 3,
        },
        ..entry(EntryKind::Object, b"object", 1)
    };
    for (errno, message, kept) in [
        (libc::EPIPE, "[Errno 32] Broken pipe", true),
        (libc::ENOSPC, "[Errno 28] No space left on device", true),
        (libc::EBADF, "[Errno 9] Bad file descriptor", true),
        // CPython reports EAGAIN with a sentence of its own.
        (libc::EAGAIN, "WriteFailed", false),
    ] {
        for capacity in [16, 1024] {
            let mut backend = FakeBackend {
                entries: vec![dated.clone()],
                ..Default::default()
            };
            let mut stdout = cli_core::output::BufferedStream::new(FailingStdout(errno), capacity);
            let mut stderr = Vec::new();
            let input = args("s3://bucket");
            let failure = listing::execute_to_file(
                &mut backend,
                options(&input, false),
                &mut stdout,
                &mut stderr,
                "https://s3.test",
            )
            .unwrap_err();
            assert_eq!(failure.category, Category::General);
            assert_eq!(failure.message, message.as_bytes());
            assert!(stderr.is_empty());
            assert_eq!(stdout.last_error().unwrap().raw_os_error(), Some(errno));
            let pending = cli_core::cli_error::flush_pending_stdout(&mut stdout);
            assert_eq!(pending.map(|failure| failure.text()).is_some(), kept);
            let buffered = stdout.buffered();
            assert!(
                !buffered.is_empty() && row.starts_with(buffered),
                "{buffered:?}"
            );
        }
    }
}
#[test]
fn a_repeated_token_is_the_paginators_general_error() {
    let result = ListResult {
        transfer: TransferResult {
            response_status: 200,
            ..Default::default()
        },
        repeated_token: Some(b"same'token".to_vec()),
        ..Default::default()
    };
    let failure = list_command_failure(&result, "http://endpoint");
    assert_eq!(failure.category, Category::General);
    assert_eq!(
        failure.message,
        b"Error during pagination: The same next token was received twice: \
          {'ContinuationToken': \"same'token\"}"
    );
    assert_eq!(failure.http_status, 200);
    assert_eq!(failure.crt_code, 0);
    assert_eq!(failure.crt_name, "");
}
#[test]
fn a_later_page_failure_keeps_earlier_output_and_prints_no_summary() {
    let failures = [
        ListResult {
            transfer: TransferResult {
                error_code: 14361,
                response_status: 403,
                ..Default::default()
            },
            ..Default::default()
        },
        ListResult {
            repeated_token: Some(b"same-token".to_vec()),
            ..Default::default()
        },
        ListResult {
            local_error: Some(crt::s3::ListLocalError::CrtFailure),
            ..Default::default()
        },
    ];
    for (target, entry, expected) in [
        (
            "s3://bucket/prefix/",
            entry(EntryKind::Object, b"prefix/key", 17),
            "0000-00-00 00:00:00         17 key\n",
        ),
        (
            "s3://",
            entry(EntryKind::Bucket, b"project-a", 0),
            "0000-00-00 00:00:00 project-a\n",
        ),
    ] {
        for result in &failures {
            let mut backend = FakeBackend {
                entries: vec![entry.clone()],
                result: result.clone(),
                ..Default::default()
            };
            let mut stdout = io::BufWriter::with_capacity(1024, Vec::new());
            let mut stderr = Vec::new();
            let mut args = args(target);
            args.summarize = true;
            let listed = list(&mut backend, &args, &mut stdout, &mut stderr, false);
            assert!(
                matches!(listed, Err(Error::Request(_) | Error::Local(_))),
                "{listed:?}"
            );
            assert!(stdout.buffer().is_empty());
            assert_eq!(String::from_utf8_lossy(stdout.get_ref()), expected);
            assert!(stderr.is_empty());
        }
    }
}
#[derive(Default)]
struct DrainLog(Vec<Vec<u8>>);
impl Write for DrainLog {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.0.push(bytes.to_vec());
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[test]
fn each_row_and_summary_statement_reaches_stdout_as_it_is_printed() {
    let mut backend = FakeBackend {
        entries: vec![
            entry(EntryKind::Object, b"prefix/key", 17),
            entry(EntryKind::CommonPrefix, b"parent/child/", 0),
            entry(EntryKind::Bucket, b"bucket-name", 0),
        ],
        ..Default::default()
    };
    let mut stdout = io::BufWriter::with_capacity(1024, DrainLog::default());
    let mut stderr = Vec::new();
    let mut args = args("s3://bucket/prefix/");
    args.summarize = true;
    let listed = list(&mut backend, &args, &mut stdout, &mut stderr, false);
    assert_eq!(listed.unwrap(), 0);
    let writes: Vec<String> = stdout
        .get_ref()
        .0
        .iter()
        .map(|write| String::from_utf8_lossy(write).into_owned())
        .collect();
    assert_eq!(
        writes,
        [
            "0000-00-00 00:00:00         17 key\n",
            "                           PRE child/\n",
            "0000-00-00 00:00:00 bucket-name\n",
            "\nTotal Objects: 1\n",
            "   Total Size: 17\n",
        ]
    );
    assert!(stderr.is_empty());
}
fn crt_backend(env: &[(&str, &str)]) -> native::CrtBackend {
    let env: std::collections::BTreeMap<String, String> = env
        .iter()
        .map(|(name, value)| ((*name).to_owned(), (*value).to_owned()))
        .collect();
    let prepared = crate::command::PreparedRuntime {
        options: crt::runtime::RuntimeOptions::default(),
        refusal: None,
        resolver: None,
    };
    native::CrtBackend::new(prepared, None, &env)
}
#[test]
fn crt_backend_prefetches_unless_the_pipeline_is_off() {
    assert!(crt_backend(&[]).prefetch);
    assert!(crt_backend(&[("ZS3_LIST_PIPELINE", "1")]).prefetch);
    assert!(!crt_backend(&[("ZS3_LIST_PIPELINE", "0")]).prefetch);
}
#[test]
fn crt_entries_convert_to_typed_ls_entries() {
    for kind in [
        EntryKind::Object,
        EntryKind::CommonPrefix,
        EntryKind::Bucket,
    ] {
        let converted = native::list_entry(crt::s3::ListEntry {
            name: b"name".to_vec(),
            size: 5,
            date: Some(crt::s3::LastModified {
                year: 2026,
                month: 7,
                day: 12,
                hour: 1,
                minute: 2,
                second: 3,
                epoch_seconds: 0,
            }),
            ..crt::s3::ListEntry::new(kind)
        });
        assert_eq!(converted.kind, kind);
        assert_eq!(
            (converted.name.as_slice(), converted.size),
            (&b"name"[..], 5)
        );
        let date = converted.date;
        assert!(date.present);
        assert_eq!(
            [
                date.year,
                date.month,
                date.day,
                date.hour,
                date.minute,
                date.second
            ],
            [2026, 7, 12, 1, 2, 3]
        );
    }
    let undated = native::list_entry(crt::s3::ListEntry::new(EntryKind::CommonPrefix));
    assert_eq!(undated.date, EntryDate::default());
}
#[test]
fn listings_pass_the_tier_as_an_explicit_memory_limit() {
    use cli_core::client_config::{ClientConfig, Command};
    let client = ClientConfig::new(Command::Ls);
    let options = native::list_runtime_options(&client, crt::runtime::RuntimeOptions::default());
    assert_eq!(options.throughput_target_gbps, client.target_gbps.value);
    assert_eq!(options.throughput_target_gbps, 10.0);
    assert_eq!(options.memory_limit_in_bytes, client.memory_bytes());
    assert!(options.memory_limit_in_bytes > 0);
}
fn run_failure_with(
    input: &Args,
    globals: &cli_core::command::Globals,
    client: &cli_core::client_config::ClientConfig,
    payload: &[u8],
) -> (String, u8) {
    let env = std::collections::BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let context = cli_core::command::CommandContext {
        env: &env,
        shared_files: &files,
        globals,
        client,
        directory: std::path::Path::new("/"),
        payload,
    };
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    let failure = run(&context, input, &mut stdout, &mut stderr).unwrap_err();
    assert!(stdout.is_empty() && stderr.is_empty());
    let mut rendered = Vec::new();
    render_command_failure(&mut rendered, &failure, ErrorFormat::Enhanced).unwrap();
    (
        String::from_utf8(rendered).unwrap(),
        exit_status(failure.category),
    )
}
fn run_failure(paths: &str, region: &str) -> (String, u8) {
    use cli_core::client_config::{ClientConfig, Command};
    let globals = cli_core::command::Globals {
        region: Some(region.into()),
        ..Default::default()
    };
    run_failure_with(&args(paths), &globals, &ClientConfig::new(Command::Ls), &[])
}
#[test]
fn run_refuses_an_empty_region_before_the_target() {
    for paths in ["s3://bucket", "https://bucket"] {
        assert_eq!(
            run_failure(paths, ""),
            (
                "\naws: [ERROR]: error: --region must not be empty\n".to_owned(),
                255
            )
        );
    }
    assert_eq!(
        run_failure("https://bucket", "us-east-1"),
        (
            "\naws: [ERROR]: error: invalid S3 URI for ls: \
             expected s3://bucket[/prefix] or bucket[/prefix]\n"
                .to_owned(),
            255
        )
    );
    assert_eq!(
        run_failure("s3:///prefix", "us-east-1").0,
        "\naws: [ERROR]: error: invalid S3 URI for ls: missing bucket name\n"
    );
}
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn run_reports_an_endpoint_rule_error_before_any_request() {
    use cli_core::client_config::{ClientConfig, Command};
    let prefix = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX").unwrap();
    let payload = std::fs::read(std::path::Path::new(&prefix).join("awscli-v2.blob")).unwrap();
    let mut client = ClientConfig::new(Command::Ls);
    client.use_accelerate_endpoint.value = true;
    for (paths, region, endpoint_url, message) in [
        (
            "s3://bucket.with.dots",
            "us-east-1",
            None,
            "Path-style addressing cannot be used with S3 Accelerate",
        ),
        (
            "s3://bucket",
            "us-east-1",
            Some("http://127.0.0.1:9"),
            "A custom endpoint cannot be combined with S3 Accelerate",
        ),
        (
            "s3://bucket",
            "cn-north-1",
            None,
            "S3 Accelerate cannot be used in this region",
        ),
    ] {
        let globals = cli_core::command::Globals {
            region: Some(region.into()),
            endpoint_url: endpoint_url.map(str::to_owned),
            ..Default::default()
        };
        assert_eq!(
            run_failure_with(&args(paths), &globals, &client, &payload),
            (format!("\naws: [ERROR]: {message}\n"), 255)
        );
    }
}
#[cfg(unix)]
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn run_refuses_a_prefix_that_is_not_utf8_after_the_endpoint_rules() {
    use cli_core::client_config::{ClientConfig, Command};
    use std::os::unix::ffi::OsStrExt;
    let prefix = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX").unwrap();
    let payload = std::fs::read(std::path::Path::new(&prefix).join("awscli-v2.blob")).unwrap();
    let globals = cli_core::command::Globals {
        region: Some("us-east-1".into()),
        ..Default::default()
    };
    let mut client = ClientConfig::new(Command::Ls);
    client.use_accelerate_endpoint.value = true;
    let mut input = args("");
    input.paths = std::ffi::OsStr::from_bytes(b"s3://bucket.with.dots/key-\xff").into();
    assert_eq!(
        run_failure_with(&input, &globals, &client, &payload),
        (
            "\naws: [ERROR]: Path-style addressing cannot be used with S3 Accelerate\n".to_owned(),
            255
        )
    );
    client.use_accelerate_endpoint.value = false;
    for paths in [b"s3://bucket/key-\xff".as_slice(), b"bucket/key-\xff"] {
        input.paths = std::ffi::OsStr::from_bytes(paths).into();
        input.dir_op = paths.starts_with(b"bucket");
        assert_eq!(
            run_failure_with(&input, &globals, &client, &payload),
            (
                "\naws: [ERROR]: 'utf-8' codec can't encode character '\\udcff' in position 4: \
                 surrogates not allowed\n"
                    .to_owned(),
                255
            )
        );
    }
}
#[test]
fn a_runtime_failure_is_a_failed_request() {
    let result = native::runtime_failure(TransferResult {
        error_code: crt::s3::CONNECTION_REFUSED_ERROR_CODE,
        response_status: 503,
        ..Default::default()
    });
    assert_eq!(
        result.transfer.error_code,
        crt::s3::CONNECTION_REFUSED_ERROR_CODE
    );
    assert_eq!(result.transfer.response_status, 0);
    assert!(result.repeated_token.is_none() && result.local_error.is_none());
    let mut backend = FakeBackend {
        result,
        ..Default::default()
    };
    let (mut stdout, mut stderr) = (Vec::new(), Vec::new());
    let mut input = args("bucket");
    input.summarize = true;
    let listed = list(&mut backend, &input, &mut stdout, &mut stderr, false);
    assert!(matches!(listed, Err(Error::Request(_))), "{listed:?}");
    assert!(stdout.is_empty() && stderr.is_empty());
}

// A listing that fails for want of credentials is botocore's
// NoCredentialsError when the chain found none, and the error of the
// refresh the request waited for when the chain's credentials were due
// one: the signer reports both as one code.
#[test]
fn a_listing_reports_the_refresh_its_request_waited_for() -> Result<(), Box<dyn std::error::Error>>
{
    use crate::credentials::Chain;
    use cli_core::cli_error::CommandFailure;
    use crt::credentials::{Delegate, Query};
    let unsigned = || CommandFailure {
        message: crate::request_failure::NO_CREDENTIALS_MESSAGE.into(),
        ..CommandFailure::new(Category::NoCredentials)
    };
    let files = awscli_config::ParsedFiles::parse(awscli_config::Inputs::default());
    let profile = ::credentials::Profile::Ambient("default");
    let disabled = ("AWS_EC2_METADATA_DISABLED", "true");
    let none = Chain::walk(
        &cli_core::SnapshotEnv::from_pairs([disabled]),
        &files,
        profile,
    )?;
    for credentials in [crt::credentials::Source::default(), none.source()] {
        assert_eq!(
            native::refresh_failure(unsigned(), &credentials),
            unsigned()
        );
    }
    // The environment's credentials expired long ago, and a refresh reads
    // the same ones again.
    let expired = cli_core::SnapshotEnv::from_pairs([
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
        ("AWS_CREDENTIAL_EXPIRATION", "2000-01-01T00:00:00Z"),
        disabled,
    ]);
    let chain = Chain::walk(&expired, &files, profile)?;
    let (answered, answers) = std::sync::mpsc::channel();
    chain.credentials(Query::new(move |view| {
        let _ = answered.send(view.is_some());
    }));
    assert!(!answers.recv_timeout(std::time::Duration::from_secs(10))?);
    let failure = native::refresh_failure(unsigned(), &chain.source());
    assert_eq!(failure.category, Category::General);
    assert_eq!(
        String::from_utf8_lossy(&failure.message),
        "Credentials were refreshed, but the refreshed credentials are still expired."
    );
    // Another failure is the listing's own.
    let other = CommandFailure::new(Category::General);
    assert_eq!(
        native::refresh_failure(other.clone(), &chain.source()),
        other
    );
    Ok(())
}
