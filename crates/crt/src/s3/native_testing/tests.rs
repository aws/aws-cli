use super::*;
use crate::crt_error::last_raised;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::Path;
use std::process::Command;
use std::sync::Arc;
use std::time::Duration;

#[test]
fn token_probe_every_chunk_split() {
    let page = b"<?xml version=\"1.0\"?><ListBucketResult><Name>bucket</Name><Pref\
            ix></Prefix><IsTruncated>true</IsTruncated><NextContinuationToken\
            >1dMBcpc/token+value=</NextContinuationToken><Contents><Key>a/b.t\
            xt</Key></Contents></ListBucketResult>";
    let offset = page
        .windows(23)
        .position(|w| w == b"<NextContinuationToken>");
    assert!(offset.is_some());
    for split in 0..=page.len() {
        let mut probe = TokenProbe::default();
        probe.scan(&page[..split]);
        probe.scan(page);
        assert_eq!(probe.state(), ProbeState::Token);
        assert_eq!(&page[probe.value_range()], b"1dMBcpc/token+value=");
        assert_eq!(Some(probe.match_offset()), offset);
    }
}
#[test]
fn token_probe_final_marker_every_split() {
    let page = b"<?xml version=\"1.0\"?><ListBucketResult><Name>bucket</Name><KeyC\
            ount>3</KeyCount><IsTruncated>false</IsTruncated><Contents><Key>a\
            </Key></Contents></ListBucketResult>";
    for split in 0..=page.len() {
        let mut probe = TokenProbe::default();
        probe.scan(&page[..split]);
        probe.scan(page);
        assert_eq!(probe.state(), ProbeState::FinalPage);
        assert_eq!(
            &page[probe.match_offset()..probe.match_offset() + 18],
            b"<IsTruncated>false"
        );
    }
}
#[test]
fn token_probe_after_contents() {
    let page = b"<ListBucketResult><Contents><Key>x</Key></Contents><NextContinuat\
            ionToken>tail-token</NextContinuationToken></ListBucketResult>";
    let mut probe = TokenProbe::default();
    probe.scan(&page[..page.len() / 2]);
    probe.scan(page);
    assert_eq!(probe.state(), ProbeState::Token);
    assert_eq!(&page[probe.value_range()], b"tail-token");
}
#[test]
fn token_probe_refuses_entities_empty_and_unresolved() {
    for page in [
        b"<NextContinuationToken>a&amp;b</NextContinuationToken>".as_slice(),
        b"<NextContinuationToken></NextContinuationToken>",
    ] {
        let mut probe = TokenProbe::default();
        probe.scan(page);
        assert_eq!(probe.state(), ProbeState::Unresolved);
    }
    let mut probe = TokenProbe::default();
    probe.scan(b"<Error><Code>AccessDenied</Code></Error>");
    assert_eq!(probe.state(), ProbeState::Scanning);
    probe.finish();
    assert_eq!(probe.state(), ProbeState::Unresolved);
}
#[test]
fn token_probe_shrinking_input_cannot_underflow_value_length() {
    let mut probe = TokenProbe::default();
    probe.scan(b"<ListBucketResult><NextContinuationToken>pending");
    assert_eq!(probe.state(), ProbeState::Scanning);
    assert_eq!(
        probe.scan(b"</NextContinuationToken>"),
        ProbeState::Unresolved
    );
}
#[test]
fn pipeline_matrix() {
    for ((page_ok, should_continue, prefetch_in_flight, prefetch_token_matches), expected) in [
        ((false, false, false, false), Action::Done),
        ((false, true, false, false), Action::Done),
        ((false, false, true, false), Action::CancelAndDone),
        ((false, true, true, true), Action::CancelAndDone),
        ((true, false, false, false), Action::Done),
        ((true, false, true, false), Action::CancelAndDone),
        ((true, false, true, true), Action::CancelAndDone),
        ((true, true, true, true), Action::Advance),
        ((true, true, false, false), Action::SubmitSerial),
        ((true, true, true, false), Action::CancelAndSubmit),
    ] {
        let inputs = NextActionInputs {
            page_ok,
            should_continue,
            prefetch_in_flight,
            prefetch_token_matches,
        };
        assert_eq!(next_action(inputs), expected);
    }
}
#[test]
fn http_dates_exact_epoch() {
    for (value, expected) in [
        ("Wed, 12 Oct 2009 17:50:00 GMT", Some(1255369800)),
        ("Thu, 01 Jan 1970 00:00:00 GMT", Some(0)),
        ("Wed, 31 Dec 1969 23:59:59 GMT", Some(-1)),
        ("", None),
        ("not a date", None),
    ] {
        assert_eq!(parse_http_date_epoch_seconds(value.as_bytes()), expected);
    }
}
#[test]
fn list_date_exact_epoch_and_local_display() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::var_os("ZAWS_DATE_CHILD").is_some() {
        let date = parse_list_date(b"2021-06-01T12:00:00.000Z").ok_or("invalid date")?;
        assert_eq!(
            date,
            LastModified {
                year: 2021,
                month: 6,
                day: 1,
                hour: 7,
                minute: 0,
                second: 0,
                epoch_seconds: 1622548800,
            }
        );
        return Ok(());
    }
    let output = Command::new(std::env::current_exe()?)
        .args([
            "--exact",
            "s3::native_testing::tests::list_date_exact_epoch_and_local_display",
            "--nocapture",
        ])
        .env("ZAWS_DATE_CHILD", "1")
        .env("TZ", "EST5")
        .output()?;
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    Ok(())
}
#[test]
fn real_get_head_put_message_headers() -> Result<(), Box<dyn std::error::Error>> {
    for (method, length, content_type, conditional, if_match) in [
        (b"GET".as_slice(), None, None, false, None),
        (b"GET", None, None, false, Some(b"\"etag-1\"".as_slice())),
        (b"HEAD", None, None, false, None),
        (b"PUT", Some(123456789), None, false, None),
        (b"PUT", Some(123456789), None, true, None),
        (b"PUT", Some(5), Some(b"text/plain".as_slice()), true, None),
    ] {
        let message = HttpMessage::new(
            b"bucket.s3.us-east-1.amazonaws.com",
            b"/nested//key%20name",
            method,
            TransferHeaders {
                content_length: length,
                content_type,
                if_none_match: conditional,
                if_match,
                request_payer: None,
                headers: &[],
                user_agent: b"aws-cli/2.0 md/test",
            },
        )?;
        assert_eq!(message.method(), method);
        assert_eq!(message.path(), b"/nested//key%20name");
        let mut expected = vec![
            (
                b"Host".to_vec(),
                b"bucket.s3.us-east-1.amazonaws.com".to_vec(),
            ),
            (b"accept".to_vec(), b"*/*".to_vec()),
        ];
        if let Some(length) = length {
            expected.push((b"content-length".to_vec(), length.to_string().into_bytes()));
        }
        if let Some(content_type) = content_type {
            expected.push((b"Content-Type".to_vec(), content_type.to_vec()));
        }
        if conditional {
            expected.push((b"If-None-Match".to_vec(), b"*".to_vec()));
        }
        if let Some(etag) = if_match {
            expected.push((b"If-Match".to_vec(), etag.to_vec()));
        }
        expected.push((b"user-agent".to_vec(), b"aws-cli/2.0 md/test".to_vec()));
        assert_eq!(message.headers(), expected);
    }
    Ok(())
}
#[test]
fn caller_headers_follow_the_request_payer_and_precede_the_user_agent()
-> Result<(), Box<dyn std::error::Error>> {
    let headers = [
        Header::new("Cache-Control", "max-age=60"),
        Header::new("x-amz-meta-Mixed-Case", ""),
    ];
    let message = HttpMessage::new(
        b"bucket.s3.us-east-1.amazonaws.com",
        b"/key",
        b"PUT",
        TransferHeaders {
            content_length: Some(5),
            content_type: Some(b"text/plain"),
            if_none_match: false,
            if_match: None,
            request_payer: Some(b"requester"),
            headers: &headers,
            user_agent: b"aws-cli/2.0 md/test",
        },
    )?;
    let names: Vec<Vec<u8>> = message
        .headers()
        .into_iter()
        .map(|(name, _)| name)
        .collect();
    assert_eq!(
        names,
        [
            b"Host".as_slice(),
            b"accept",
            b"content-length",
            b"Content-Type",
            b"x-amz-request-payer",
            b"Cache-Control",
            b"x-amz-meta-Mixed-Case",
            b"user-agent",
        ]
        .map(<[u8]>::to_vec)
    );
    assert_eq!(message.headers()[6].1, b"");
    Ok(())
}
#[test]
fn malformed_xml_cannot_become_missing_region_metadata() {
    use crate::redirect::{Target, target_region};
    for body in [
        b"<Error><Code>PermanentRedirect</Code><Region>us-west-2".as_slice(),
        b"<Error><Region>us-west-2&invalid;</Region></Error>",
    ] {
        let mut error = ServiceError::default();
        parse_service_error_body(body, &mut error);
        assert!(error.region_body_invalid);
        assert_eq!(target_region(&error), Target::Invalid);
        error.region_header.set(b"eu-west-1");
        assert_eq!(target_region(&error), Target::Region("eu-west-1"));
    }
    for body in [
        b"<Error></Error>".as_slice(),
        b"<Error><Region></Region></Error>",
    ] {
        let mut error = ServiceError::default();
        parse_service_error_body(body, &mut error);
        assert!(!error.region_body_invalid);
        assert_eq!(target_region(&error), Target::Missing);
    }
}
#[test]
fn errors_read_cdata_literally() {
    use crate::redirect::{Target, target_region};
    let mut error = ServiceError::default();
    parse_service_error_body(
        b"<Error><Code><![CDATA[AccessDenied]]></Code><Message>a &amp; <![CDATA[b & <c>\
            &amp;]]> d</Message><Region><![CDATA[us-west-2]]></Region></Error>",
        &mut error,
    );
    assert!(!error.region_body_invalid);
    assert_eq!(error.code.as_bytes(), b"AccessDenied");
    assert_eq!(error.message, b"a & b & <c>&amp; d");
    assert_eq!(target_region(&error), Target::Region("us-west-2"));
    for body in [
        b"<Error><Code>AccessDenied</Code><Message><![CDATA[bad & x</Message></Error>".as_slice(),
        b"<Error><Code>AccessDenied</Code><Message>bad & x</Message></Error>",
    ] {
        let mut error = ServiceError::default();
        parse_service_error_body(body, &mut error);
        assert!(error.region_body_invalid);
    }
}
#[test]
fn cdata_in_the_error_body_is_read_as_botocore_reads_it() {
    use crate::redirect::{Target, target_region};
    for body in [
        b"<Error><Code>PermanentRedirect</Code><Region><![CDATA[eu-west-1]]></Region></Error>"
            .as_slice(),
        b"<Error><Code>PermanentRedirect</Code><Region>eu-<![CDATA[west]]>-1</Region></Error>",
        b"<Error><Code>PermanentRedirect</Code><Message><![CDATA[a & b]]></Message>\
            <Region>eu-west-1</Region></Error>",
        b"<Error><Code>PermanentRedirect</Code><Message><!-- <![CDATA[ -->moved</Message>\
            <Region>eu-west-1</Region></Error>",
        b"<Error><Code>PermanentRedirect</Code><Message><?pi <![CDATA[ ?>moved</Message>\
            <Region>eu-west-1</Region></Error>",
    ] {
        let mut error = ServiceError::default();
        parse_service_error_body(body, &mut error);
        assert!(
            !error.region_body_invalid,
            "{}",
            String::from_utf8_lossy(body)
        );
        assert_eq!(target_region(&error), Target::Region("eu-west-1"));
    }
}
#[test]
fn comments_and_processing_instructions_in_the_error_body_are_dropped() {
    use crate::redirect::{Target, target_region};
    for body in [
        b"<Error><Code>PermanentRedirect</Code><Region>eu-west-1<!-- c --></Region></Error>"
            .as_slice(),
        b"<Error><Code>PermanentRedirect</Code><Region>eu-<?pi x?>west-1</Region></Error>",
        b"<Error><Code>PermanentRedirect</Code><Message><!-- a & b -->moved</Message>\
            <Region>eu-west-1</Region></Error>",
    ] {
        let mut error = ServiceError::default();
        parse_service_error_body(body, &mut error);
        assert!(
            !error.region_body_invalid,
            "{}",
            String::from_utf8_lossy(body)
        );
        assert_eq!(target_region(&error), Target::Region("eu-west-1"));
    }
}
#[test]
fn xml_region_overflow_is_retained_as_truncated() {
    let mut error = ServiceError::default();
    let body = format!("<Error><Region>{}</Region></Error>", "a".repeat(64));
    parse_service_error_body(body.as_bytes(), &mut error);
    assert!(error.region_body.is_present() && error.region_body.is_truncated());
    assert_eq!(error.region_body.as_bytes(), "a".repeat(63).as_bytes());
    assert_eq!(
        crate::redirect::target_region(&error),
        crate::redirect::Target::Invalid
    );
}
#[test]
fn bodies_decode_xml_entities_and_keep_a_long_message_whole() {
    let mut error = ServiceError::default();
    parse_service_error_body(
        b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Error><Code>InvalidA\
            rgument</Code><Message>Key &quot;a &amp; b&quot; is &lt;invalid&g\
            t;, isn&apos;t it&#63;</Message><ArgumentName>key</ArgumentName></Error>",
        &mut error,
    );
    assert_eq!(error.code.as_bytes(), b"InvalidArgument");
    assert_eq!(error.message, b"Key \"a & b\" is <invalid>, isn't it?");
    let long_message = format!("{}\u{e9} tail {}", "a".repeat(1023), "m".repeat(8192));
    let long = format!("<Error><Code>Long</Code><Message>{long_message}</Message></Error>");
    error = ServiceError::default();
    parse_service_error_body(long.as_bytes(), &mut error);
    assert_eq!(error.code.as_bytes(), b"Long");
    assert_eq!(error.message, long_message.as_bytes());
    error = ServiceError::default();
    parse_service_error_body(
        b"<ListBucketResult><Name>b</Name></ListBucketResult>",
        &mut error,
    );
    parse_service_error_body(b"", &mut error);
    assert!(error.code.is_empty());
}
#[test]
fn a_body_botocore_cannot_parse_leaves_the_code_and_message_empty() {
    for body in [
        b"<Error><Code>NoSuchBucket</Code><Message>gone</Message><BucketName>bu".as_slice(),
        b"<Error><Code>Bad\xffCode</Code><Message>gone</Message></Error>",
        b"<Error><Code>NoSuchBucket</Code><Message>caf\xe9</Message></Error>",
        b"<Error><Code>NoSuchBucket</Code><Message>gone</Message>\
            <RequestId>\xed\xa0\x80</RequestId></Error>",
    ] {
        let mut error = ServiceError::default();
        parse_service_error_body(body, &mut error);
        assert!(!error.code.is_present());
        assert!(error.message.is_empty());
    }
    let mut error = ServiceError::default();
    parse_service_error_body(
        b"<Error><Code>PermanentRedirect</Code><Message>caf\xe9</Message>\
            <Region>eu-west-1</Region></Error>",
        &mut error,
    );
    assert!(!error.code.is_present());
    assert!(!error.region_body_invalid);
    assert_eq!(error.region_body.as_bytes(), b"eu-west-1");
}
#[test]
fn well_formed_xml_the_crts_parser_rejects_keeps_its_code_and_message() {
    for body in [
        b"<Error><Code>AccessDenied</Code><Message>denied</Message>\
            <RequestId>id</RequestId ></Error>"
            .as_slice(),
        b"<Error><Code>AccessDenied</Code\n><Message>denied</Message></Error>",
        b"<!-- a > b --><Error><Code>AccessDenied</Code><Message>denied</Message></Error>",
    ] {
        let mut error = ServiceError::default();
        parse_service_error_body(body, &mut error);
        assert_eq!(error.code.as_bytes(), b"AccessDenied");
        assert_eq!(error.message, b"denied");
        assert!(error.region_body_invalid);
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Keeps the whole failure matrix and every assertion in one test"
)]
fn finish_classifies_embedded_412() {
    let precondition = b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Error><Code>Precondi\
            tionFailed</Code><Message>At least one of the pre-conditions you \
            specified did not hold</Message><RequestId>4442587FB7D0A2F9</RequestId></Error>";
    let internal = b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Error><Code>Internal\
            Error</Code><Message>We encountered an internal error. Please tr\
            y again.</Message></Error>";
    for (body, code, status, want_status, want_code, want_message) in [
        (
            precondition.as_slice(),
            3,
            200,
            412,
            "PreconditionFailed",
            "At least one of the pre-conditions you specified did not hold",
        ),
        (
            precondition,
            3,
            412,
            412,
            "PreconditionFailed",
            "At least one of the pre-conditions you specified did not hold",
        ),
        (
            internal,
            3,
            200,
            200,
            "InternalError",
            "We encountered an internal error. Please try again.",
        ),
        (b"not an xml document", 3, 200, 200, "", ""),
        (precondition, 0, 200, 200, "", ""),
    ] {
        let result = transfer_result(code, status, body, b"CompleteMultipartUpload", "");
        assert_eq!(result.error_code, code);
        assert_eq!(result.response_status, want_status);
        assert_eq!(result.service_error.code.as_bytes(), want_code.as_bytes());
        assert_eq!(result.service_error.message, want_message.as_bytes());
        assert_eq!(
            result.service_error.operation.as_bytes(),
            if code != 0 {
                b"CompleteMultipartUpload".as_slice()
            } else {
                b""
            }
        );
        assert_eq!(!result.crt_name.is_empty(), code != 0);
        assert_eq!(!result.crt_message.is_empty(), code != 0);
    }
    let result = transfer_result(3, 200, b"", b"", "");
    assert_eq!(result.response_status, 200);
    assert!(result.service_error.operation.is_empty());
}
#[test]
fn proxy_failure_snapshot_survives_owner() {
    let mut proxy = String::from("http://user:secret@proxy.test:8080");
    let failure = transfer_result(3, 0, b"", b"", &proxy);
    proxy.clear();
    assert_eq!(
        failure.proxy_url.as_bytes(),
        b"http://***:***@proxy.test:8080"
    );
    let success = transfer_result(0, 200, b"", b"", "http://user:secret@proxy.test:8080");
    assert!(success.proxy_url.is_empty());
}
#[test]
fn last_error_preserved_or_unknown() {
    // SAFETY: these functions touch only the calling thread's error state.
    unsafe {
        crt_sys::native::aws_reset_error();
        assert_eq!(last_raised(), 3);
        crt_sys::aws_raise_error(INVALID_ARGUMENT_ERROR_CODE);
        assert_eq!(last_raised(), INVALID_ARGUMENT_ERROR_CODE);
        crt_sys::native::aws_reset_error();
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "One complete process-isolated local HTTP scenario keeps ownershi\
            p and requests visible"
)]
fn real_loopback_head_and_listing_two_runtimes() -> Result<(), Box<dyn std::error::Error>> {
    for _ in 0..2 {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let address = listener.local_addr()?;
        let server = std::thread::spawn(move || -> std::io::Result<Vec<String>> {
            let mut requests = Vec::new();
            for index in 0..2 {
                let (mut stream, _) = listener.accept()?;
                stream.set_read_timeout(Some(Duration::from_secs(15)))?;
                let mut request = Vec::new();
                let mut chunk = [0; 1024];
                while !request.windows(4).any(|w| w == b"\r\n\r\n") {
                    let count = stream.read(&mut chunk)?;
                    if count == 0 {
                        break;
                    }
                    request.extend_from_slice(&chunk[..count]);
                }
                requests.push(String::from_utf8_lossy(&request).into_owned());
                if index == 0 {
                    stream.write_all(
                        b"HTTP/1.1 200 OK\r\nContent-Length: 17\r\nLast-Modified: Tue, 01 J\
            un 2021 12:00:00 GMT\r\nConnection: close\r\n\r\n",
                    )?;
                } else {
                    let body = b"<ListBucketResult><IsTruncated>false</IsTruncated><Contents><Key>\
            nested/key</Key><Size>17</Size><LastModified>2021-06-01T12:00:00.\
            000Z</LastModified></Contents></ListBucketResult>";
                    write!(
                        stream,
                        "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                        body.len()
                    )?;
                    stream.write_all(body)?;
                }
            }
            Ok(requests)
        });
        let runtime = crate::Runtime::new(crate::RuntimeOptions {
            endpoint_url: format!("http://{address}/bucket"),
            credentials: crate::credentials::Source::Delegate(Arc::new(Loopback)),
            event_loop_count: 1,
            ..crate::RuntimeOptions::default()
        })?;
        let head = runtime.head_object(
            HeadObject {
                key: b"nested/key",
                request_payer: None,
                headers: &[],
            },
            &cli_core::interrupt::State::new(),
        )?;
        assert_eq!(head.transfer.error_code, 0);
        assert_eq!(head.content_length, Some(17));
        assert_eq!(head.last_modified_epoch_seconds, Some(1622548800));
        let mut entries = Vec::new();
        let result = runtime.list_objects(
            ListOptions {
                object_conditions: false,
                prefetch: true,
                bucket: b"bucket",
                prefix: b"nested/",
                request_payer: b"",
                recursive: true,
                page_size: 1,
                user_agent: None,
            },
            None,
            &mut |entry| {
                entries.push(entry);
                0
            },
        );
        assert_eq!(result.transfer.error_code, 0);
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].name, b"nested/key");
        assert_eq!(entries[0].size, 17);
        drop(runtime);
        let requests = server.join().map_err(|_| "server panic")??;
        assert!(
            requests
                .iter()
                .all(|request| request.contains("Credential=loopback-only/"))
        );
        assert!(requests[0].starts_with("HEAD /bucket/nested/key "));
        assert!(requests[1].contains("list-type=2"));
        assert!(requests[1].contains("max-keys=1"));
    }
    Ok(())
}
/// Answers every query with keys that sign only loopback requests.
#[derive(Debug)]
struct Loopback;

impl crate::credentials::Delegate for Loopback {
    fn credentials(&self, query: crate::credentials::Query) {
        query.complete(crate::credentials::View {
            access_key_id: "loopback-only",
            secret_access_key: "loopback-only",
            session_token: None,
            account_id: None,
            expiration: None,
        });
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "Keeps the whole option matrix and every boolean assertion in one test"
)]
fn meta_options_classify_hints_body_and_paths() {
    use crt_sys::{AwsByteCursor, native as c};
    let empty = AwsByteCursor::from_bytes(b"");
    let mut options = c::RequestOptions {
        kind: c::REQUEST_KIND_GET,
        key: empty,
        filepath: AwsByteCursor::from_bytes(b"destination.tmp"),
        single_request: false,
        has_body_callback: false,
        if_none_match: false,
        content_type: empty,
        if_match: empty,
        check_object_size: false,
        request_payer: empty,
        user_agent: empty,
        headers: std::ptr::null(),
        header_count: 0,
        checksum_algorithm: 0,
        validate_checksum: false,
        expected_checksum: empty,
        expected_checksum_algorithm: 0,
        checksum_unavailable: false,
    };
    let mut snapshot = c::OptionSnapshot {
        kind: 0,
        out_of_order: -1,
        has_hint: false,
        body: false,
        recv_delete: false,
        progress: false,
        headers: true,
        hint: 0,
        operation: empty,
        recv_path: empty,
        send_path: empty,
    };
    // SAFETY: snapshots only borrow the static inputs alive throughout this test.
    unsafe {
        c::zaws_request_option_snapshot(&options, &mut snapshot);
        assert_eq!(snapshot.kind, 1);
        assert!(!snapshot.has_hint);
        assert!(!snapshot.body);
        assert!(!snapshot.recv_delete);
        assert!(!snapshot.progress);
        assert_eq!(
            std::slice::from_raw_parts(snapshot.recv_path.ptr, snapshot.recv_path.len),
            b"destination.tmp"
        );
        assert_eq!(snapshot.out_of_order, crt_sys::AWS_TRIBOOL_UNSET);
        assert!(!snapshot.headers);
        options.check_object_size = true;
        c::zaws_request_option_snapshot(&options, &mut snapshot);
        assert!(!snapshot.headers);
        options.check_object_size = false;
        options.has_body_callback = true;
        options.single_request = true;
        c::zaws_request_option_snapshot(&options, &mut snapshot);
        assert!(!snapshot.has_hint);
        assert_eq!(snapshot.hint, 0);
        assert!(snapshot.body);
        assert_eq!(snapshot.recv_path.len, 0);
        assert!(!snapshot.recv_delete);
        assert_eq!(snapshot.out_of_order, crt_sys::AWS_TRIBOOL_TRUE);
        assert!(!snapshot.headers);
        options.check_object_size = true;
        c::zaws_request_option_snapshot(&options, &mut snapshot);
        assert!(snapshot.headers);
        options.check_object_size = false;
        options.kind = c::REQUEST_KIND_PUT;
        options.filepath = AwsByteCursor::from_bytes(b"upload.bin");
        c::zaws_request_option_snapshot(&options, &mut snapshot);
        assert_eq!(snapshot.kind, 2);
        assert_eq!(snapshot.out_of_order, crt_sys::AWS_TRIBOOL_UNSET);
        assert_eq!(snapshot.operation.len, 0);
        assert!(!snapshot.progress);
        assert!(!snapshot.headers);
        assert_eq!(
            std::slice::from_raw_parts(snapshot.send_path.ptr, snapshot.send_path.len),
            b"upload.bin"
        );
        options.kind = c::REQUEST_KIND_HEAD;
        c::zaws_request_option_snapshot(&options, &mut snapshot);
        assert_eq!(snapshot.kind, 0);
        assert!(snapshot.headers);
        assert_eq!(snapshot.out_of_order, crt_sys::AWS_TRIBOOL_UNSET);
        assert_eq!(
            std::slice::from_raw_parts(snapshot.operation.ptr, snapshot.operation.len),
            b"HeadObject"
        );
    }
}
fn endpoint_request_path(base: &[u8], key: &[u8], kind: RequestKind) -> Result<Vec<u8>, i32> {
    use crt_sys::{AwsByteBuf, AwsByteCursor, native as c};
    let mut out = AwsByteBuf {
        len: 0,
        buffer: std::ptr::null_mut(),
        capacity: 0,
        allocator: std::ptr::null_mut(),
    };
    // SAFETY: the cursors outlive the synchronous call, which initializes
    // `out` on success; it is copied and cleaned up before it is dropped.
    unsafe {
        let kind = kind as i32;
        let base = AwsByteCursor::from_bytes(base);
        let key = AwsByteCursor::from_bytes(key);
        if c::zaws_endpoint_request_path(crt_sys::rust_crt_allocator(), base, key, kind, &mut out)
            != 0
        {
            return Err(last_raised());
        }
        let path = std::slice::from_raw_parts(out.buffer, out.len).to_vec();
        c::aws_byte_buf_clean_up(&mut out);
        Ok(path)
    }
}
#[test]
fn endpoint_paths_preserve_prefixes_and_encoding() -> Result<(), i32> {
    let _library = crate::runtime::Library::acquire();
    for (base, key, kind, expected) in [
        (
            "",
            "nested//already%20encoded/key",
            RequestKind::Get,
            "/nested//already%20encoded/key",
        ),
        (
            "/bucket.with.dots",
            "nested/key",
            RequestKind::Get,
            "/bucket.with.dots/nested/key",
        ),
        (
            "/custom/base/",
            "object",
            RequestKind::Get,
            "/custom/base/object",
        ),
        ("", "object", RequestKind::Head, "/object"),
        ("/bucket/", "a//b", RequestKind::Put, "/bucket/a//b"),
        ("", "", RequestKind::HeadBucket, "/"),
        ("/bucket", "", RequestKind::HeadBucket, "/bucket"),
        (
            "/custom/base/",
            "ignored",
            RequestKind::HeadBucket,
            "/custom/base/",
        ),
    ] {
        let path = endpoint_request_path(base.as_bytes(), key.as_bytes(), kind)?;
        assert_eq!(
            String::from_utf8_lossy(&path),
            expected,
            "{base:?} {key:?} {kind:?}"
        );
    }
    Ok(())
}
fn upload_length(path: &Path, ops: Option<&crt_sys::native::FileLengthOps>) -> Result<u64, i32> {
    use crt_sys::{AwsByteCursor, native as c};
    let path = AwsByteCursor::from_bytes(path.as_os_str().as_encoded_bytes());
    let mut length = 0;
    // SAFETY: aws_reset_error only clears this thread's error; the
    // cursor and the ops outlive the synchronous lookup.
    let rc = unsafe {
        c::aws_reset_error();
        let allocator = crt_sys::rust_crt_allocator();
        match ops {
            Some(ops) => c::zaws_upload_length_with_ops(allocator, path, ops, &mut length),
            None => c::zaws_upload_length(allocator, path, &mut length),
        }
    };
    if rc == 0 {
        Ok(length)
    } else {
        Err(last_raised())
    }
}
#[test]
fn upload_file_length_real_empty_nonempty_missing() -> Result<(), Box<dyn std::error::Error>> {
    let _library = crate::runtime::Library::acquire();
    let directory = std::env::temp_dir().join(format!("crt-file-length-{}", std::process::id()));
    std::fs::create_dir_all(&directory)?;
    for (name, data, wanted) in [
        ("empty", "", Some(0)),
        ("nonempty", "sixteen-byte-file", Some(17)),
        ("missing", "", None),
    ] {
        let path = directory.join(name);
        if wanted.is_some() {
            std::fs::write(&path, data)?;
        }
        assert_eq!(upload_length(&path, None).ok(), wanted, "{name}");
    }
    std::fs::remove_dir_all(directory)?;
    Ok(())
}
#[derive(Debug, Default)]
struct FakeFileLengthOps {
    mode: FileLengthFailure,
    open_count: usize,
    get_length_count: usize,
    release_count: usize,
}
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
enum FileLengthFailure {
    #[default]
    Open,
    Length,
    NegativeLength,
}
unsafe extern "C" fn fake_open(
    data: *mut std::ffi::c_void,
    _allocator: *mut crt_sys::AwsAllocator,
    _path: *const std::ffi::c_char,
) -> *mut crt_sys::native::InputStream {
    // SAFETY: `data` is the live fake the test passed with these ops.
    let fake = unsafe { &mut *data.cast::<FakeFileLengthOps>() };
    fake.open_count += 1;
    if fake.mode == FileLengthFailure::Open {
        return std::ptr::null_mut();
    }
    std::ptr::dangling_mut()
}
unsafe extern "C" fn fake_get_length(
    data: *mut std::ffi::c_void,
    _stream: *mut crt_sys::native::InputStream,
    out: *mut i64,
) -> std::ffi::c_int {
    // SAFETY: `data` is the live fake and `out` the lookup's length.
    let fake = unsafe { &mut *data.cast::<FakeFileLengthOps>() };
    fake.get_length_count += 1;
    if fake.mode == FileLengthFailure::Length {
        return -1;
    }
    // SAFETY: as above.
    unsafe { *out = -1 };
    0
}
unsafe extern "C" fn fake_release(
    data: *mut std::ffi::c_void,
    _stream: *mut crt_sys::native::InputStream,
) {
    // SAFETY: `data` is the live fake the test passed with these ops.
    unsafe { (*data.cast::<FakeFileLengthOps>()).release_count += 1 };
}
#[test]
fn upload_length_lookup_failures_release_the_stream() {
    let _library = crate::runtime::Library::acquire();
    for mode in [
        FileLengthFailure::Open,
        FileLengthFailure::Length,
        FileLengthFailure::NegativeLength,
    ] {
        let mut fake = FakeFileLengthOps {
            mode,
            ..FakeFileLengthOps::default()
        };
        let ops = crt_sys::native::FileLengthOps {
            open: Some(fake_open),
            get_length: Some(fake_get_length),
            release: Some(fake_release),
            data: std::ptr::from_mut(&mut fake).cast(),
        };
        let failure = upload_length(Path::new("unused"), Some(&ops)).err();
        assert!(failure.is_some(), "{mode:?}");
        if mode == FileLengthFailure::NegativeLength {
            assert_eq!(failure, Some(INVALID_ARGUMENT_ERROR_CODE));
        }
        let opened = usize::from(mode != FileLengthFailure::Open);
        assert_eq!(fake.open_count, 1);
        assert_eq!(
            (fake.get_length_count, fake.release_count),
            (opened, opened)
        );
    }
}
fn proxy_runtime(
    endpoint: &str,
    proxy: Option<&str>,
) -> Result<crate::Runtime, Box<TransferResult>> {
    crate::Runtime::new(crate::RuntimeOptions {
        endpoint_url: endpoint.into(),
        proxy_url: proxy.map(str::to_owned),
        event_loop_count: 1,
        ..crate::RuntimeOptions::default()
    })
}
fn proxy_snapshot(runtime: &crate::Runtime) -> (crt_sys::native::ProxySnapshot, Vec<u8>) {
    use crt_sys::{AwsByteCursor, native as c};
    let mut snapshot = c::ProxySnapshot {
        host: AwsByteCursor::from_bytes(b""),
        port: 0,
        connection_type: 0,
        strategy: false,
        tls: false,
        env_disabled: false,
        configured: false,
    };
    // SAFETY: the runtime lives while its borrowed proxy host is copied.
    let host = unsafe {
        c::zaws_proxy_snapshot(runtime.pointer(), &mut snapshot);
        if snapshot.host.len == 0 {
            Vec::new()
        } else {
            std::slice::from_raw_parts(snapshot.host.ptr, snapshot.host.len).to_vec()
        }
    };
    (snapshot, host)
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Keeps the four destination and proxy TLS combinations, the default-port \
              table and the direct case in one test"
)]
fn explicit_proxy_owns_auth_and_independent_tls() -> Result<(), Box<dyn std::error::Error>> {
    for destination_tls in [false, true] {
        for proxy_tls in [false, true] {
            let scheme = if proxy_tls { "https" } else { "http" };
            let url = format!("{scheme}://user:secret@proxy.test:8080");
            let endpoint = if destination_tls {
                "https://127.0.0.1:9"
            } else {
                "http://127.0.0.1:9"
            };
            let (snapshot, host) = proxy_snapshot(&proxy_runtime(endpoint, Some(&url))?);
            assert!(snapshot.configured);
            assert_eq!(host, b"proxy.test");
            assert_eq!(snapshot.port, 8080);
            assert_eq!(
                snapshot.connection_type,
                if destination_tls { 2 } else { 1 }
            );
            assert!(snapshot.strategy);
            assert_eq!(snapshot.tls, proxy_tls);
            assert!(snapshot.env_disabled);
            assert_eq!(
                crate::s3::masked_proxy(&url).as_bytes(),
                format!("{scheme}://***:***@proxy.test:8080").as_bytes()
            );
        }
    }
    for (url, port) in [
        ("http://proxy.test", 80),
        ("http://proxy.test:0", 80),
        ("http://proxy.test:", 80),
        ("proxy.test", 80),
        ("https://proxy.test", 443),
        ("HTTPS://user:secret@proxy.test", 443),
        ("https://proxy.test:8443", 8443),
    ] {
        let (snapshot, host) = proxy_snapshot(&proxy_runtime("https://127.0.0.1:9", Some(url))?);
        assert!(snapshot.configured, "{url}");
        assert_eq!(host, b"proxy.test", "{url}");
        assert_eq!(snapshot.port, port, "{url}");
    }
    let runtime = proxy_runtime("http://127.0.0.1:9", None)?;
    let (snapshot, host) = proxy_snapshot(&runtime);
    assert!(!snapshot.configured);
    assert!(host.is_empty());
    assert_eq!(snapshot.port, 0);
    assert!(snapshot.env_disabled);
    assert!(crate::s3::masked_proxy("").is_empty());
    assert!(runtime.options().proxy_url.is_none());
    Ok(())
}
fn serve_empty_listing(listener: &TcpListener) -> std::io::Result<String> {
    let (mut stream, _) = listener.accept()?;
    stream.set_read_timeout(Some(Duration::from_secs(15)))?;
    let mut request = Vec::new();
    let mut chunk = [0; 1024];
    while !request.windows(4).any(|w| w == b"\r\n\r\n") {
        let count = stream.read(&mut chunk)?;
        if count == 0 {
            break;
        }
        request.extend_from_slice(&chunk[..count]);
    }
    let body = b"<ListBucketResult><IsTruncated>false</IsTruncated></ListBucketResult>";
    write!(
        stream,
        "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    )?;
    stream.write_all(body)?;
    Ok(String::from_utf8_lossy(&request).into_owned())
}
#[test]
fn listings_name_the_proxy_only_when_they_fail() -> Result<(), Box<dyn std::error::Error>> {
    let list = |proxy: &str| -> Result<ListResult, Box<TransferResult>> {
        let runtime = crate::Runtime::new(crate::RuntimeOptions {
            endpoint_url: "http://127.0.0.1:9/bucket".into(),
            proxy_url: Some(proxy.into()),
            no_sign_request: true,
            max_attempts: Some(2),
            event_loop_count: 1,
            ..crate::RuntimeOptions::default()
        })?;
        let options = ListOptions {
            object_conditions: false,
            prefetch: false,
            bucket: b"bucket",
            prefix: b"",
            request_payer: b"",
            recursive: true,
            page_size: 1000,
            user_agent: None,
        };
        Ok(runtime.list_objects(options, None, &mut |_| 0))
    };
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let server = std::thread::spawn(move || serve_empty_listing(&listener));
    let listed = list(&format!("http://user:secret@{address}"))?;
    let request = server.join().map_err(|_| "proxy panic")??;
    assert!(
        request.starts_with("GET http://127.0.0.1:9/bucket?"),
        "{request}"
    );
    assert_eq!(listed.transfer.error_code, 0);
    assert!(listed.transfer.proxy_url.is_empty());
    let failed = list("http://user:secret@127.0.0.1:9")?;
    assert_ne!(failed.transfer.error_code, 0);
    assert_eq!(
        failed.transfer.proxy_url.as_bytes(),
        b"http://***:***@127.0.0.1:9"
    );
    Ok(())
}
const REFUSAL_CHILD: &str = "ZAWS_REFUSAL_CHILD";
const REFUSAL_TEST: &str = "s3::native_testing::tests::refused_submissions_record_their_outcome";
#[derive(Debug)]
struct RaisesOnDrop;
impl RequestCallbacks for RaisesOnDrop {
    fn finish(&self, _result: TransferResult) {}
    fn shutdown(&self) {}
}
impl Drop for RaisesOnDrop {
    fn drop(&mut self) {
        // SAFETY: raising touches only the calling thread's error state.
        unsafe { crt_sys::aws_raise_error(INVALID_ARGUMENT_ERROR_CODE) };
    }
}
fn refused_put(case: &str, source: &Path) -> Result<i32, Box<dyn std::error::Error>> {
    let runtime = Arc::new(crate::Runtime::new_with_logger(
        crate::RuntimeOptions {
            endpoint_url: "http://127.0.0.1:9/bucket".into(),
            no_sign_request: true,
            event_loop_count: 1,
            ..crate::RuntimeOptions::default()
        },
        crate::debug::Logger::new(true),
    )?);
    let options = RequestOptions {
        kind: RequestKind::Put,
        key: b"object",
        filepath: Some(source),
        object_size_hint: None,
        if_none_match: false,
        content_type: None,
        condition: None,
        check_object_size: false,
        request_payer: None,
        user_agent: None,
        headers: &[],
        checksum_algorithm: None,
        validate_checksum: false,
    };
    let refused = if case == "waiting" {
        let interrupt = cli_core::interrupt::State::new();
        runtime.submit(options, &interrupt).err()
    } else {
        runtime
            .submit_callbacks(options, None, Arc::new(RaisesOnDrop))
            .err()
    };
    refused
        .map(|failure| failure.error_code)
        .ok_or_else(|| "the PUT was submitted".into())
}
#[test]
fn refused_submissions_record_their_outcome() -> Result<(), Box<dyn std::error::Error>> {
    let missing = std::env::temp_dir()
        .join(format!("crt-refused-{}-absent", std::process::id()))
        .join("missing.bin");
    if let Some(case) = std::env::var_os(REFUSAL_CHILD) {
        let case = case.to_string_lossy();
        let source = if case == "nul" {
            Path::new("upload\0.bin")
        } else {
            missing.as_path()
        };
        let code = refused_put(&case, source)?;
        return if code == FILE_INVALID_PATH_ERROR_CODE {
            Ok(())
        } else {
            Err(format!("refused with CRT {code}").into())
        };
    }
    let outcome = format!(
        " - awscli.native.request - DEBUG - Request outcome: HTTP 0, CRT 44 \
         (AWS_ERROR_FILE_INVALID_PATH): {}",
        String::from_utf8_lossy(&error_message(FILE_INVALID_PATH_ERROR_CODE))
    );
    for case in ["callbacks", "waiting", "nul"] {
        let output = Command::new(std::env::current_exe()?)
            .args(["--exact", REFUSAL_TEST, "--nocapture"])
            .env(REFUSAL_CHILD, case)
            .output()?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(output.status.success(), "{case}: {stderr}");
        let records = stderr
            .lines()
            .filter(|line| line.contains(" - awscli.native.request - "))
            .filter_map(|line| line.get(23..))
            .collect::<Vec<_>>();
        assert_eq!(records, [outcome.as_str()], "{case}");
    }
    Ok(())
}
