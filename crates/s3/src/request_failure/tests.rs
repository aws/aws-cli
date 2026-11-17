use super::*;
use crt::s3::{BoundedText, CONNECTION_REFUSED_ERROR_CODE, ServiceError};
fn result(code: i32, status: i32) -> TransferResult {
    TransferResult {
        error_code: code,
        response_status: status,
        service_error: ServiceError {
            operation: BoundedText::new("HeadObject"),
            ..ServiceError::default()
        },
        ..TransferResult::default()
    }
}
fn reason(result: &TransferResult) -> Reason<'_> {
    Reason {
        result,
        url: RequestUrl::Object {
            endpoint_url: "http://localhost/b",
            request_key: "a%20b",
        },
        missing_key: Some("a b"),
    }
}
#[test]
fn exception_sentence_covers_each_failure_kind() {
    assert_eq!(
        sentence(reason(&result(1, 404))),
        "An error occurred (404) when calling the HeadObject operation: Key \"a b\" does not exist"
    );
    assert_eq!(
        sentence(reason(&result(1, 403))),
        "An error occurred (403) when calling the HeadObject operation: Forbidden"
    );
    assert_eq!(
        sentence(reason(&result(NO_CREDENTIALS_ERROR_CODE, 0))),
        "Unable to locate credentials"
    );
    assert_eq!(
        sentence(reason(&result(CONNECTION_REFUSED_ERROR_CODE, 200))),
        "Could not connect to the endpoint URL: \"http://localhost/b/a%20b\""
    );
    assert_eq!(sentence(reason(&result(999999, 0))), "CRT error 999999");
    let mut service = result(1, 403);
    service.service_error.code.set(b"AccessDenied");
    service.service_error.message = b"denied".to_vec();
    assert_eq!(
        sentence(reason(&service)),
        "An error occurred (AccessDenied) when calling the HeadObject operation: denied"
    );
    service.service_error.code.set(b"");
    service.response_status = 0;
    service.crt_message.set(b"timed out.");
    assert_eq!(sentence(reason(&service)), "timed out.");
}
#[test]
fn proxy_context_preserves_service_and_credential_precedence() {
    let mut failure = result(CONNECTION_REFUSED_ERROR_CODE, 0);
    failure.proxy_url = crt::s3::masked_proxy("http://user:secret@proxy:8080");
    assert_eq!(
        sentence(reason(&failure)),
        "Failed to connect to proxy URL: \"http://***:***@proxy:8080\""
    );
    failure.proxy_url = crt::s3::masked_proxy("http://h:p@127.0.0.1:8");
    assert_eq!(
        sentence(reason(&failure)),
        "Failed to connect to proxy URL: \"***tt***://h:p@127.0.0.1:8\""
    );
    failure.error_code = NO_CREDENTIALS_ERROR_CODE;
    assert_eq!(sentence(reason(&failure)), "Unable to locate credentials");
    failure.response_status = 403;
    assert!(matches!(
        classify(&failure),
        Kind::HttpStatus { status: 403, .. }
    ));
}
#[test]
fn checksum_mismatch_names_the_error_and_preserves_response_precedence() {
    let mut failure = result(crt::s3::CHECKSUM_MISMATCH_ERROR_CODE, 200);
    failure
        .crt_name
        .set(b"AWS_ERROR_S3_RESPONSE_CHECKSUM_MISMATCH");
    failure
        .crt_message
        .set(b"response checksum header does not match calculated checksum");
    assert_eq!(
        sentence(reason(&failure)),
        "AWS_ERROR_S3_RESPONSE_CHECKSUM_MISMATCH: response checksum header does not match \
            calculated checksum"
    );
    failure.response_status = 403;
    assert!(matches!(
        classify(&failure),
        Kind::HttpStatus { status: 403, .. }
    ));
    failure.service_error.code.set(b"AccessDenied");
    assert!(matches!(
        classify(&failure),
        Kind::ServiceError {
            code: b"AccessDenied",
            ..
        }
    ));
}
#[test]
fn request_urls_retain_endpoint_path_and_query() {
    for (endpoint, key, expected) in [
        (
            "https://b.s3.amazonaws.com",
            "k",
            "https://b.s3.amazonaws.com/k",
        ),
        (
            "http://localhost/base/b/",
            "d/k",
            "http://localhost/base/b/d/k",
        ),
    ] {
        assert_eq!(
            RequestUrl::Object {
                endpoint_url: endpoint,
                request_key: key
            }
            .to_string(),
            expected
        );
    }
    assert_eq!(
        RequestUrl::Listing {
            endpoint_url: "http://localhost/base/b",
            request_path: "/base/b?list-type=2"
        }
        .to_string(),
        "http://localhost/base/b?list-type=2"
    );
    assert_eq!(endpoint_origin("no-scheme"), "no-scheme");
}
#[test]
fn reason_phrases_match_cpython() {
    for (status, expected) in [
        (404, "Not Found"),
        (503, "Service Unavailable"),
        (301, "Moved Permanently"),
        (413, "Content Too Large"),
        (422, "Unprocessable Content"),
        (599, ""),
    ] {
        assert_eq!(http_reason_phrase(status), expected);
    }
}
#[test]
fn missing_keys_unknown_operations_and_listing_connections_keep_the_full_sentence() {
    let mut transfer = result(1, 404);
    let mut input = reason(&transfer);
    input.missing_key = None;
    assert_eq!(
        sentence(input),
        "An error occurred (404) when calling the HeadObject operation: Not Found"
    );
    transfer.response_status = 599;
    transfer.service_error.operation.set(b"");
    assert_eq!(
        sentence(reason(&transfer)),
        "An error occurred (599) when calling the Unknown operation: "
    );
    transfer.response_status = 0;
    transfer.error_code = CONNECTION_REFUSED_ERROR_CODE;
    assert_eq!(
        sentence(Reason {
            result: &transfer,
            missing_key: None,
            url: RequestUrl::Listing {
                endpoint_url: "http://127.0.0.1:9/bucket",
                request_path: "/bucket?list-type=2&prefix=&delimiter=%2F&encoding-type=url",
            }
        }),
        concat!(
            "Could not connect to the endpoint URL: ",
            "\"http://127.0.0.1:9/bucket?list-type=2&prefix=&delimiter=%2F&encoding-type=url\""
        )
    );
    transfer.proxy_url = crt::s3::masked_proxy("http://user:secret@proxy.test:8080");
    transfer.response_status = 403;
    transfer.service_error.code.set(b"AccessDenied");
    transfer.service_error.message = b"Access denied".to_vec();
    transfer.service_error.operation.set(b"PutObject");
    assert_eq!(
        sentence(reason(&transfer)),
        "An error occurred (AccessDenied) when calling the PutObject operation: Access denied"
    );
}

#[test]
fn bucket_listing_urls_preserve_the_root_slash_before_queries() {
    assert_eq!(
        RequestUrl::Listing {
            endpoint_url: "https://s3.amazonaws.com",
            request_path: "/?max-buckets=5"
        }
        .to_string(),
        "https://s3.amazonaws.com/?max-buckets=5"
    );
    assert_eq!(
        endpoint_origin("https://s3.amazonaws.com"),
        "https://s3.amazonaws.com"
    );
}

#[test]
fn a_repeated_token_is_the_pagination_error_dict_repr() {
    for (token, quoted) in [
        ("same-token", "'same-token'"),
        ("same'token", "\"same'token\""),
        ("same\u{a0}token", "'same\\xa0token'"),
        ("same\u{85}token", "'same\\x85token'"),
    ] {
        let expected = format!(
            "Error during pagination: The same next token was received twice: \
             {{'ContinuationToken': {quoted}}}"
        );
        let repeated = RepeatedToken {
            token: token.as_bytes(),
        };
        assert_eq!(repeated.to_vec(), expected.as_bytes());
    }
}

#[test]
fn redirect_connection_diagnostics_use_the_failed_attempt_endpoint() {
    let mut failure = TransferResult {
        error_code: CONNECTION_REFUSED_ERROR_CODE,
        ..TransferResult::default()
    };
    failure
        .endpoint_url
        .set(b"https://bucket.s3.us-west-2.amazonaws.com");
    assert_eq!(
        sentence(Reason {
            result: &failure,
            missing_key: None,
            url: RequestUrl::Object {
                endpoint_url: "https://bucket.s3.us-east-1.amazonaws.com",
                request_key: "a%20b",
            },
        }),
        "Could not connect to the endpoint URL: \
         \"https://bucket.s3.us-west-2.amazonaws.com/a%20b\""
    );
    failure.endpoint_url.set(b"http://127.0.0.1:9/base/bucket");
    assert_eq!(
        sentence(Reason {
            result: &failure,
            missing_key: None,
            url: RequestUrl::Listing {
                endpoint_url: "http://127.0.0.1:8/base/bucket",
                request_path: "/base/bucket?list-type=2",
            },
        }),
        "Could not connect to the endpoint URL: \"http://127.0.0.1:9/base/bucket?list-type=2\""
    );
}

#[test]
fn redirect_capture_cut_at_its_bound_names_the_whole_requested_endpoint() {
    let origin = "http://127.0.0.1:9/";
    let bound = crt::s3::ENDPOINT_URL_MAX;
    let endpoints = [
        format!("{origin}{}/bucket", "p".repeat(bound)),
        format!(
            "{origin}{}\u{e9}z/bucket",
            "p".repeat(bound - origin.len() - 1)
        ),
    ];
    for endpoint_url in &endpoints {
        let mut failure = TransferResult {
            error_code: CONNECTION_REFUSED_ERROR_CODE,
            ..TransferResult::default()
        };
        failure.endpoint_url.set(endpoint_url.as_bytes());
        assert!(failure.endpoint_url.is_truncated());
        assert_eq!(
            sentence(Reason {
                result: &failure,
                missing_key: None,
                url: RequestUrl::Object {
                    endpoint_url,
                    request_key: "key.txt",
                },
            }),
            format!("Could not connect to the endpoint URL: \"{endpoint_url}/key.txt\"")
        );
    }

    let mut redirected = TransferResult {
        error_code: CONNECTION_REFUSED_ERROR_CODE,
        ..TransferResult::default()
    };
    let other = format!("http://127.0.0.2:9/{}", "p".repeat(bound));
    redirected.endpoint_url.set(other.as_bytes());
    let requested = format!("{origin}{}", "p".repeat(bound));
    assert_eq!(
        sentence(Reason {
            result: &redirected,
            missing_key: None,
            url: RequestUrl::Object {
                endpoint_url: &requested,
                request_key: "key.txt",
            },
        }),
        format!(
            "Could not connect to the endpoint URL: \"http://127.0.0.2:9/{}/key.txt\"",
            "p".repeat(bound - origin.len())
        )
    );
}

#[test]
fn service_messages_keep_their_bytes() {
    let mut service = result(1, 403);
    service.service_error.code.set(b"AccessDenied");
    service.service_error.message = b"caf\xc3".to_vec();
    let bytes = sentence_bytes(reason(&service));
    assert_eq!(
        bytes,
        b"An error occurred (AccessDenied) when calling the HeadObject operation: caf\xc3"
    );
}
fn listing(result: &TransferResult) -> Reason<'_> {
    Reason {
        result,
        url: RequestUrl::Listing {
            endpoint_url: "http://127.0.0.1:9",
            request_path: "/bucket?list-type=2",
        },
        missing_key: None,
    }
}
#[test]
fn a_listing_failure_names_the_retries_botocore_ran_out_of() {
    let mut rejected = TransferResult {
        response_status: 500,
        retries_exhausted: Some(2),
        ..TransferResult::default()
    };
    rejected.service_error.operation.set(b"ListObjectsV2");
    for (retries, note) in [
        (Some(2), " (reached max retries: 2)"),
        (Some(0), " (reached max retries: 0)"),
        (None, ""),
    ] {
        rejected.retries_exhausted = retries;
        assert_eq!(
            sentence(listing(&rejected)),
            format!(
                "An error occurred (500) when calling the ListObjectsV2 operation{note}: \
                 Internal Server Error"
            )
        );
    }
    let mut denied = TransferResult {
        error_code: 1,
        response_status: 403,
        retries_exhausted: Some(2),
        ..TransferResult::default()
    };
    denied.service_error.operation.set(b"ListObjectsV2");
    denied.service_error.code.set(b"AccessDenied");
    denied.service_error.message = b"Access Denied".to_vec();
    assert_eq!(
        sentence(listing(&denied)),
        "An error occurred (AccessDenied) when calling the ListObjectsV2 operation \
         (reached max retries: 2): Access Denied"
    );
}
fn transfer_sentence(reason: Reason<'_>) -> String {
    String::from_utf8_lossy(&transfer_sentence_bytes(reason)).into_owned()
}
#[test]
fn a_transfer_names_the_crt_error_it_failed_with() {
    let mut failure = result(crt::s3::UNKNOWN_ERROR_CODE, 0);
    failure.crt_name.set(b"AWS_ERROR_S3_INTERNAL_ERROR");
    failure
        .crt_message
        .set(b"Response code indicates internal server error");
    assert_eq!(
        transfer_sentence(reason(&failure)),
        "AWS_ERROR_S3_INTERNAL_ERROR: Response code indicates internal server error"
    );
    assert_eq!(
        sentence(reason(&failure)),
        "Response code indicates internal server error"
    );
    let mut service = failure.clone();
    service.response_status = 403;
    service.service_error.code.set(b"AccessDenied");
    service.service_error.message = b"denied".to_vec();
    assert_eq!(
        transfer_sentence(reason(&service)),
        "An error occurred (AccessDenied) when calling the HeadObject operation: denied"
    );
    let unnamed = result(999999, 0);
    assert_eq!(transfer_sentence(reason(&unnamed)), "CRT error 999999");
}

/// A delegate that failed its latest query for `self.0`.
#[derive(Debug)]
struct Refused(Option<&'static str>);

impl crt::credentials::Delegate for Refused {
    fn credentials(&self, query: crt::credentials::Query) {
        query.fail();
    }
    fn failure(&self) -> Option<String> {
        self.0.map(str::to_owned)
    }
}

// Upstream sends a HeadObject, a listing and a move's DeleteObject through
// its botocore client, where a refresh that fails raises its own error and
// a chain without credentials raises NoCredentialsError. The signer reports
// both as one code, so the delegate that signed says which.
#[test]
fn a_client_request_reads_the_refresh_its_signing_waited_for() {
    use crt::credentials::Source;
    let client = |result: &TransferResult, credentials: &Source| {
        String::from_utf8_lossy(&client_sentence_bytes(reason(result), credentials)).into_owned()
    };
    let still_expired =
        "Credentials were refreshed, but the refreshed credentials are still expired.";
    let refreshed = Source::Delegate(std::sync::Arc::new(Refused(Some(still_expired))));
    let found_none = Source::Delegate(std::sync::Arc::new(Refused(None)));
    let unsigned = result(NO_CREDENTIALS_ERROR_CODE, 0);
    assert_eq!(client(&unsigned, &refreshed), still_expired);
    for credentials in [&found_none, &Source::default()] {
        assert_eq!(
            client(&unsigned, credentials),
            "Unable to locate credentials"
        );
    }
    // Any other failure is the request's own, whatever the delegate holds.
    assert_eq!(
        client(&result(1, 403), &refreshed),
        "An error occurred (403) when calling the HeadObject operation: Forbidden"
    );
    // The CRT client's transfer keeps the one sentence, as upstream's does.
    assert_eq!(sentence(reason(&unsigned)), "Unable to locate credentials");
}
