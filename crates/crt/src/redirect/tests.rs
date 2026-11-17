use super::*;

#[test]
fn metadata_precedence_and_dns_label_validation() {
    let mut error = ServiceError::default();
    assert_eq!(target_region(&error), Target::Missing);
    error.region_body.set(b"eu-west-1");
    assert_eq!(target_region(&error), Target::Region("eu-west-1"));
    let long = "a".repeat(64);
    for bad in ["", "123", "-bad", "bad-", "us\nwest", "us.east", &long] {
        error.region_header.set(bad.as_bytes());
        assert_eq!(target_region(&error), Target::Invalid, "{bad:?}");
    }
    let longest = "a".repeat(63);
    error.region_header.set(longest.as_bytes());
    assert_eq!(target_region(&error), Target::Region(longest.as_str()));
    error.region_header = Default::default();
    error.region_body.set(long.as_bytes());
    assert_eq!(target_region(&error), Target::Invalid);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "One ordered table mutates a single result through every replay boundary"
)]
fn response_classes_and_replay_boundaries() {
    let mut result = TransferResult {
        error_code: 1,
        response_status: 301,
        ..TransferResult::default()
    };
    result.service_error.operation.set(b"GetObject");
    for status in [301, 302, 307] {
        result.response_status = status;
        assert!(is_candidate("bucket", &result, true));
    }
    result.response_status = 403;
    result.service_error.region_header.set(b"eu-west-1");
    assert!(!is_candidate("bucket", &result, true));
    result
        .service_error
        .code
        .set(b"AuthorizationHeaderMalformed");
    assert!(!is_candidate("bucket", &result, true));
    result.service_error.region_body.set(b"eu-west-1");
    assert!(is_candidate("bucket", &result, true));
    result
        .service_error
        .code
        .set(b"IllegalLocationConstraintException");
    result.service_error.operation.set(b"CreateBucket");
    assert!(!is_candidate("bucket", &result, false));
    result.service_error.code.set(b"");
    result.response_status = 400;
    result.service_error.operation.set(b"HeadObject");
    assert!(is_candidate("bucket", &result, true));
    result.service_error.operation.set(b"HeadBucket");
    assert!(is_candidate("bucket", &result, false));
    result.service_error.region_header = Default::default();
    assert!(!is_candidate("bucket", &result, false));
    result.response_status = 301;
    for bucket in ["", "arn:aws:s3:::bucket", "bucket--zone--x-s3"] {
        assert!(!is_candidate(bucket, &result, false), "{bucket}");
    }
    result.service_error.operation.set(b"ListBuckets");
    assert!(!is_candidate("bucket", &result, false));
    result.service_error.operation.set(b"UploadPart");
    result.bytes_transferred = 1;
    assert!(!is_candidate("bucket", &result, true));
    result.bytes_transferred = 0;
    result.body_delivered = true;
    assert!(!is_candidate("bucket", &result, true));
    result.body_delivered = false;
    result.error_code = CANCELED_ERROR_CODE;
    assert!(!is_candidate("bucket", &result, false));
    result.error_code = 0;
    assert!(!is_candidate("bucket", &result, false));
    result.error_code = 1;
    result.response_status = 200;
    result.service_error.code.set(b"PermanentRedirect");
    assert!(!is_candidate("bucket", &result, false));
}
