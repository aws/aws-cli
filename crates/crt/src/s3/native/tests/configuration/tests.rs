use super::*;
use crate::runtime::{ChecksumMode, RuntimeOptions};
type TestResult = Result<(), Box<dyn std::error::Error>>;

#[test]
fn unsigned_runtime_builds_no_chain_and_uses_valid_anonymous_signing() -> TestResult {
    let runtime = Runtime::new(RuntimeOptions {
        region: "eu-west-1".into(),
        endpoint_url: "https://localhost".into(),
        event_loop_count: 1,
        no_sign_request: true,
        ..RuntimeOptions::default()
    })?;
    let mut snapshot = std::mem::MaybeUninit::<c::SigningSnapshot>::uninit();
    // SAFETY: the shim fills every field and the runtime retains every borrowed cursor.
    let snapshot = unsafe {
        c::zaws_runtime_signing_snapshot(runtime.pointer(), snapshot.as_mut_ptr());
        snapshot.assume_init()
    };
    assert!(!snapshot.chain && !snapshot.provider);
    assert!(snapshot.anonymous && snapshot.same_credentials);
    assert_eq!(snapshot.validation, 0);
    // SAFETY: runtime remains alive while these borrowed signing cursors are read.
    unsafe {
        assert_eq!(bytes(snapshot.region), b"eu-west-1");
        assert_eq!(bytes(snapshot.service), b"s3");
        assert_eq!(bytes(snapshot.body), b"UNSIGNED-PAYLOAD");
    }
    Ok(())
}

fn submitted(
    runtime: &Runtime,
    size: Option<u64>,
    body: bool,
    kind: RequestKind,
) -> c::RequestOptions {
    raw(runtime, &request(kind, size), body)
}
fn request(kind: RequestKind, size: Option<u64>) -> RequestOptions<'static> {
    RequestOptions {
        kind,
        key: b"key",
        filepath: None,
        object_size_hint: size,
        if_none_match: false,
        content_type: None,
        condition: None,
        check_object_size: false,
        request_payer: None,
        user_agent: None,
        headers: &[],
        checksum_algorithm: None,
        validate_checksum: false,
    }
}
fn raw(runtime: &Runtime, request: &RequestOptions<'_>, body: bool) -> c::RequestOptions {
    request.raw(
        b"file",
        body,
        runtime.options().single_request_threshold,
        &[],
    )
}
fn configured(
    runtime: &Runtime,
    size: Option<u64>,
    body: bool,
    kind: RequestKind,
    progress: bool,
) -> c::ConfiguredSnapshot {
    snapshot_options(runtime, &submitted(runtime, size, body, kind), progress)
}
fn snapshot_options(
    runtime: &Runtime,
    options: &c::RequestOptions,
    progress: bool,
) -> c::ConfiguredSnapshot {
    let mut snapshot = std::mem::MaybeUninit::uninit();
    // SAFETY: the shim fills every field and only borrows the static input cursors.
    unsafe {
        c::zaws_configured_request_snapshot(
            runtime.pointer(),
            options,
            progress,
            snapshot.as_mut_ptr(),
        );
        snapshot.assume_init()
    }
}
fn runtime(threshold: Option<u64>, mode: ChecksumMode) -> Result<Runtime, Box<TransferResult>> {
    Runtime::new(RuntimeOptions {
        endpoint_url: "http://127.0.0.1:9/bucket".into(),
        event_loop_count: 1,
        no_sign_request: true,
        single_request_threshold: threshold,
        request_checksum_calculation: mode,
        response_checksum_validation: mode,
        ..RuntimeOptions::default()
    })
}

#[test]
fn single_request_threshold_matrix_reaches_both_real_meta_option_sinks() -> TestResult {
    for (threshold, size, single) in [
        (None, Some(0), false),
        (None, Some(1), false),
        (Some(8), None, false),
        (Some(8), Some(0), true),
        (Some(8), Some(1), true),
        (Some(8), Some(8), true),
        (Some(8), Some(9), false),
        (Some(u64::MAX), Some(u64::MAX), true),
    ] {
        let runtime = runtime(threshold, ChecksumMode::WhenRequired)?;
        for body in [false, true] {
            let snapshot = configured(&runtime, size, body, RequestKind::Get, true);
            assert_sink_snapshot(&snapshot.meta, body, single);
        }
    }
    Ok(())
}
#[test]
fn get_meta_options_follow_the_submitted_single_request_flag() -> TestResult {
    let runtime = runtime(Some(8), ChecksumMode::WhenRequired)?;
    for (size, single) in [(8, true), (9, false)] {
        for body in [false, true] {
            let mut options = submitted(&runtime, Some(size), body, RequestKind::Get);
            assert_eq!(options.single_request, single);
            assert_sink_snapshot(
                &snapshot_options(&runtime, &options, true).meta,
                body,
                single,
            );
            options.single_request = !single;
            assert_sink_snapshot(
                &snapshot_options(&runtime, &options, true).meta,
                body,
                !single,
            );
        }
    }
    Ok(())
}
#[expect(
    clippy::cognitive_complexity,
    reason = "one helper checks every sink option of a snapshot"
)]
fn assert_sink_snapshot(snapshot: &c::OptionSnapshot, body: bool, single: bool) {
    assert_eq!(snapshot.kind, i32::from(!single));
    assert_eq!(snapshot.operation.len, if single { 9 } else { 0 });
    assert!(!snapshot.has_hint && !snapshot.recv_delete);
    assert_eq!(snapshot.body, body);
    assert_eq!(snapshot.recv_path.len, if body { 0 } else { 4 });
    let order = if body {
        crt_sys::AWS_TRIBOOL_TRUE
    } else {
        crt_sys::AWS_TRIBOOL_UNSET
    };
    assert_eq!(snapshot.out_of_order, order);
    assert!(snapshot.progress);
}

#[test]
fn checksum_configuration_is_owned_by_each_request_for_every_transfer_kind() -> TestResult {
    for mode in [ChecksumMode::WhenSupported, ChecksumMode::WhenRequired] {
        let runtime = runtime(Some(4), mode)?;
        for (kind, size, body) in [
            (RequestKind::Get, Some(4), false),
            (RequestKind::Get, Some(4), true),
            (RequestKind::Get, Some(5), false),
            (RequestKind::Get, Some(5), true),
            (RequestKind::Head, None, false),
            (RequestKind::Put, None, false),
        ] {
            let snapshot = configured(&runtime, size, body, kind, true);
            assert_checksum_snapshot(&snapshot, kind, mode);
            assert!(!snapshot.meta.has_hint);
            assert!(snapshot.meta.progress);
        }
    }
    Ok(())
}
fn assert_checksum_snapshot(
    snapshot: &c::ConfiguredSnapshot,
    kind: RequestKind,
    mode: ChecksumMode,
) {
    let enabled = mode == ChecksumMode::WhenSupported && kind != RequestKind::Head;
    assert_eq!(snapshot.has_checksum, enabled);
    assert_eq!(snapshot.owns_checksum, enabled);
    assert_eq!(
        snapshot.validate_response,
        enabled && kind == RequestKind::Get
    );
    let (location, algorithm) = if enabled && kind == RequestKind::Put {
        (2, 5)
    } else {
        (0, 0)
    };
    assert_eq!(snapshot.checksum_location, location);
    assert_eq!(snapshot.checksum_algorithm, algorithm);
    assert!(snapshot.validation_algorithms_null);
    assert!(snapshot.full_object_callback_null);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test keeps the whole request and runtime mode matrix"
)]
fn a_requests_checksum_settings_apply_whatever_the_runtime_modes() -> TestResult {
    use crate::s3::ChecksumAlgorithm;
    let algorithms = [
        ChecksumAlgorithm::Crc32c,
        ChecksumAlgorithm::Crc32,
        ChecksumAlgorithm::Sha1,
        ChecksumAlgorithm::Sha256,
        ChecksumAlgorithm::Crc64Nvme,
        ChecksumAlgorithm::Sha512,
        ChecksumAlgorithm::Xxhash64,
        ChecksumAlgorithm::Xxhash3,
        ChecksumAlgorithm::Xxhash128,
    ];
    for mode in [ChecksumMode::WhenSupported, ChecksumMode::WhenRequired] {
        let runtime = runtime(Some(4), mode)?;
        for (number, algorithm) in (1..).zip(algorithms) {
            let put = RequestOptions {
                checksum_algorithm: Some(algorithm),
                ..request(RequestKind::Put, None)
            };
            let snapshot = snapshot_options(&runtime, &raw(&runtime, &put, false), true);
            assert!(snapshot.has_checksum && snapshot.owns_checksum);
            assert!(!snapshot.validate_response);
            assert_eq!(
                (snapshot.checksum_location, snapshot.checksum_algorithm),
                (2, number)
            );
        }
        for (size, body) in [
            (Some(4), false),
            (Some(4), true),
            (Some(5), false),
            (Some(5), true),
        ] {
            let get = RequestOptions {
                validate_checksum: true,
                ..request(RequestKind::Get, size)
            };
            let snapshot = snapshot_options(&runtime, &raw(&runtime, &get, body), true);
            assert!(snapshot.has_checksum && snapshot.owns_checksum);
            assert!(snapshot.validate_response);
            assert_eq!(
                (snapshot.checksum_location, snapshot.checksum_algorithm),
                (0, 0)
            );
        }
        for kind in [RequestKind::Head, RequestKind::Delete] {
            let other = RequestOptions {
                checksum_algorithm: Some(ChecksumAlgorithm::Sha256),
                validate_checksum: true,
                ..request(kind, None)
            };
            let snapshot = snapshot_options(&runtime, &raw(&runtime, &other, false), true);
            assert!(!snapshot.has_checksum && !snapshot.validate_response);
            assert_eq!(
                (snapshot.checksum_location, snapshot.checksum_algorithm),
                (0, 0)
            );
        }
    }
    Ok(())
}

#[test]
fn a_validating_split_download_hands_the_crt_its_full_object_checksum() -> TestResult {
    use crate::s3::{ChecksumAlgorithm, DownloadCondition, FullObjectChecksum};
    let value = b"AAAAAAAAAAA=";
    let known = FullObjectChecksum::Known {
        algorithm: ChecksumAlgorithm::Crc64Nvme,
        value: (*value).into(),
    };
    for mode in [ChecksumMode::WhenSupported, ChecksumMode::WhenRequired] {
        let runtime = runtime(Some(4), mode)?;
        for (checksum, size) in [
            (&known, Some(5)),
            (&known, Some(4)),
            (&FullObjectChecksum::Unavailable, Some(5)),
            (&FullObjectChecksum::Unavailable, Some(4)),
            (&FullObjectChecksum::Unknown, Some(5)),
        ] {
            let get = RequestOptions {
                condition: Some(DownloadCondition {
                    etag: b"\"etag\"",
                    full_object_checksum: checksum,
                }),
                ..request(RequestKind::Get, size)
            };
            let snapshot = snapshot_options(&runtime, &raw(&runtime, &get, false), true);
            let handed = mode == ChecksumMode::WhenSupported && size == Some(5);
            let expected: (&[u8], i32, i32) = match checksum {
                FullObjectChecksum::Known { .. } if handed => (
                    value,
                    ChecksumAlgorithm::Crc64Nvme as i32,
                    c::VALIDATION_MODE_DEFAULT,
                ),
                FullObjectChecksum::Unavailable if handed => {
                    (b"", 0, c::VALIDATION_MODE_REQUEST_ONLY)
                }
                _ => (b"", 0, c::VALIDATION_MODE_DEFAULT),
            };
            // SAFETY: the cursor borrows `known`'s value, which outlives the read.
            let sent = unsafe { bytes(snapshot.expected_checksum) };
            assert_eq!(
                (
                    sent,
                    snapshot.expected_checksum_algorithm,
                    snapshot.validation_mode
                ),
                expected,
                "{mode:?} {checksum:?} {size:?}"
            );
        }
    }
    Ok(())
}
