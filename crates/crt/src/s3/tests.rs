use super::*;
use cli_core::interrupt::State;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
#[test]
fn downloads_split_into_parts_are_conditioned_on_the_object_etag() {
    const MIB: u64 = 1024 * 1024;
    let checksum = FullObjectChecksum::Unavailable;
    let condition = DownloadCondition {
        etag: b"\"original\"",
        full_object_checksum: &checksum,
    };
    for (threshold, size, expected) in [
        (Some(8 * MIB), Some(0), None),
        (Some(8 * MIB), Some(8 * MIB - 1), None),
        (Some(8 * MIB), Some(8 * MIB), None),
        (Some(8 * MIB), Some(9 * MIB), Some(condition)),
        (None, Some(0), Some(condition)),
        (Some(8 * MIB), None, Some(condition)),
    ] {
        assert_eq!(
            download_condition(threshold, size, Some(condition)),
            expected,
            "{threshold:?} {size:?}"
        );
    }
    assert_eq!(download_condition(Some(8 * MIB), Some(9 * MIB), None), None);
}

fn known(algorithm: ChecksumAlgorithm, value: &[u8]) -> FullObjectChecksum {
    FullObjectChecksum::Known {
        algorithm,
        value: value.into(),
    }
}

#[test]
fn a_head_object_reports_a_full_object_crc_none_or_maybe_one() {
    let full = Some(&b"FULL_OBJECT"[..]);
    for (checksum_type, crc32, crc32c, crc64nvme, reported, expected) in [
        (
            full,
            &b"AAAAAA=="[..],
            &b""[..],
            &b""[..],
            true,
            known(ChecksumAlgorithm::Crc32, b"AAAAAA=="),
        ),
        (
            Some(&b"full_Object"[..]),
            b"",
            b"BBBBBB==",
            b"",
            true,
            known(ChecksumAlgorithm::Crc32c, b"BBBBBB=="),
        ),
        (
            full,
            b"",
            b"",
            b"CCCCCCCCCCC=",
            true,
            known(ChecksumAlgorithm::Crc64Nvme, b"CCCCCCCCCCC="),
        ),
        (
            full,
            b"AAAAAA==",
            b"",
            b"CCCCCCCCCCC=",
            true,
            known(ChecksumAlgorithm::Crc32, b"AAAAAA=="),
        ),
        (full, b"", b"", b"", true, FullObjectChecksum::Unknown),
        (full, b"", b"", b"", false, FullObjectChecksum::Unknown),
        (
            Some(&b"COMPOSITE"[..]),
            b"AAAAAA==",
            b"",
            b"",
            true,
            FullObjectChecksum::Unavailable,
        ),
        (
            Some(&b""[..]),
            b"AAAAAA==",
            b"",
            b"",
            true,
            FullObjectChecksum::Unavailable,
        ),
        (None, b"", b"", b"", false, FullObjectChecksum::Unavailable),
        (
            None,
            b"AAAAAA==",
            b"",
            b"",
            true,
            FullObjectChecksum::Unknown,
        ),
    ] {
        assert_eq!(
            FullObjectChecksum::from_head(checksum_type, crc32, crc32c, crc64nvme, reported),
            expected,
            "{checksum_type:?} {reported}"
        );
    }
}

#[test]
fn a_listing_entry_reports_no_full_object_checksum_or_maybe_one() {
    for (checksum_type, listed, expected) in [
        (Some(&b"FULL_OBJECT"[..]), true, FullObjectChecksum::Unknown),
        (
            Some(&b"full_object"[..]),
            false,
            FullObjectChecksum::Unknown,
        ),
        (
            Some(&b"COMPOSITE"[..]),
            true,
            FullObjectChecksum::Unavailable,
        ),
        (None, true, FullObjectChecksum::Unknown),
        (None, false, FullObjectChecksum::Unavailable),
    ] {
        assert_eq!(
            FullObjectChecksum::from_listing(checksum_type, listed),
            expected,
            "{checksum_type:?} {listed}"
        );
    }
}

#[derive(Debug, Default)]
struct RecordingMetaRequestOps {
    canceled: Vec<usize>,
    released: Vec<usize>,
}
impl MetaRequestOps for RecordingMetaRequestOps {
    type Handle = usize;
    fn cancel(&mut self, h: usize) {
        self.canceled.push(h);
    }
    fn release(&mut self, h: usize) {
        self.released.push(h);
    }
}
fn recording_submission() -> Arc<Submission<RecordingMetaRequestOps>> {
    Arc::new(Submission::new(RecordingMetaRequestOps::default()))
}
#[test]
fn submission_cancels_owned_reference_releases_once() {
    let state = State::new();
    let s = recording_submission();
    let mut registration = s.adopt(0x1000, &state);
    s.with_ops(|o| {
        assert!(o.canceled.is_empty());
        assert!(o.released.is_empty());
    });
    state.request();
    s.with_ops(|o| {
        assert_eq!(o.canceled, [0x1000]);
        assert!(o.released.is_empty());
    });
    s.finish(TransferResult {
        error_code: CANCELED_ERROR_CODE,
        ..TransferResult::default()
    });
    s.shutdown();
    let result = s.wait_with_unregister(|| registration.unregister());
    assert!(result.canceled_by_interrupt);
    assert_eq!(result.error_code, CANCELED_ERROR_CODE);
    state.request();
    s.with_ops(|o| {
        assert_eq!(o.canceled, [0x1000]);
        assert_eq!(o.released, [0x1000]);
    });
}
#[test]
fn submission_adopt_after_interrupt_cancels_immediately() {
    let state = State::new();
    state.request();
    let s = recording_submission();
    let mut registration = s.adopt(0x2000, &state);
    s.with_ops(|o| assert_eq!(o.canceled, [0x2000]));
    s.finish(TransferResult {
        error_code: CANCELED_ERROR_CODE,
        ..TransferResult::default()
    });
    s.shutdown();
    assert!(
        s.wait_with_unregister(|| registration.unregister())
            .canceled_by_interrupt
    );
    s.with_ops(|o| assert_eq!(o.released, [0x2000]));
}
#[test]
fn submission_other_cancellation_not_interrupt() {
    let state = State::new();
    let s = recording_submission();
    let _registration = s.adopt(0x3000, &state);
    s.finish(TransferResult {
        error_code: CANCELED_ERROR_CODE,
        ..TransferResult::default()
    });
    s.shutdown();
    let result = s.wait();
    assert_eq!(result.error_code, CANCELED_ERROR_CODE);
    assert!(!result.canceled_by_interrupt);
    s.with_ops(|o| assert!(o.canceled.is_empty()));
}
#[test]
fn submission_interrupt_losing_race_keeps_result() {
    let state = State::new();
    let s = recording_submission();
    let _registration = s.adopt(0x4000, &state);
    state.request();
    s.finish(TransferResult {
        response_status: 200,
        ..TransferResult::default()
    });
    s.shutdown();
    let result = s.wait();
    assert_eq!(result.error_code, 0);
    assert!(!result.canceled_by_interrupt);
    s.with_ops(|o| assert_eq!(o.canceled, [0x4000]));
}
#[test]
fn submission_without_adoption_waits_only_callbacks() {
    let s = Submission::new(RecordingMetaRequestOps::default());
    s.cancel_for_interrupt();
    s.finish(TransferResult {
        response_status: 200,
        ..TransferResult::default()
    });
    s.shutdown();
    let result = s.wait();
    assert_eq!(result.response_status, 200);
    assert!(!result.canceled_by_interrupt);
    s.with_ops(|o| {
        assert!(o.canceled.is_empty());
        assert!(o.released.is_empty());
    });
}
#[derive(Debug, Default)]
struct FakeBodyTicketOps {
    fail: bool,
    acquired: Vec<usize>,
}
impl BodyTicketOps for FakeBodyTicketOps {
    type Ticket = usize;
    fn acquire(&mut self, t: usize) -> Option<usize> {
        self.acquired.push(t);
        (!self.fail).then_some(t)
    }
}
fn offered(storage: Option<&[u8]>, ticket: Option<usize>) -> OfferedBody<&[u8], usize> {
    OfferedBody {
        len: storage.map_or(0, <[u8]>::len),
        storage,
        ticket,
    }
}
type Forwarded = (Result<(), i32>, Vec<BodyDelivery<Vec<u8>, usize>>, bool);
fn forward(
    ops: &mut FakeBodyTicketOps,
    body: OfferedBody<&[u8], usize>,
    single_request: bool,
    result: Result<(), i32>,
) -> Forwarded {
    let delivered = AtomicBool::new(false);
    let mut seen = Vec::new();
    let forwarded = forward_body(ops, body, single_request, &delivered, |delivery| {
        seen.push(match delivery {
            BodyDelivery::Empty => BodyDelivery::Empty,
            BodyDelivery::Missing => BodyDelivery::Missing,
            BodyDelivery::Lent(bytes) => BodyDelivery::Lent(bytes.to_vec()),
            BodyDelivery::Ticketed(bytes, ticket) => BodyDelivery::Ticketed(bytes.to_vec(), ticket),
        });
        result
    });
    (forwarded, seen, delivered.load(Ordering::Acquire))
}
#[test]
fn body_null_empty_need_no_ticket() {
    let mut ops = FakeBodyTicketOps::default();
    for body in [offered(None, None), offered(Some(&[42][..0]), None)] {
        let (forwarded, seen, delivered) = forward(&mut ops, body, false, Ok(()));
        assert_eq!(forwarded, Ok(()));
        assert_eq!(seen, [BodyDelivery::Empty]);
        assert!(delivered);
    }
    assert!(ops.acquired.is_empty());
}
#[test]
fn body_missing_or_failed_ticket_rejected() {
    let mut ops = FakeBodyTicketOps::default();
    let invalid = Err(INVALID_ARGUMENT_ERROR_CODE);
    let (forwarded, seen, delivered) =
        forward(&mut ops, offered(Some(&[1, 2, 3]), None), false, Ok(()));
    assert_eq!(
        (forwarded, seen.is_empty(), delivered),
        (invalid, true, false)
    );
    assert!(ops.acquired.is_empty());
    ops.fail = true;
    let body = offered(Some(&[1, 2, 3]), Some(0x2000));
    let (forwarded, seen, delivered) = forward(&mut ops, body, false, Ok(()));
    assert_eq!(
        (forwarded, seen.is_empty(), delivered),
        (invalid, true, false)
    );
    assert_eq!(ops.acquired, [0x2000]);
}
#[test]
fn a_single_request_body_arrives_without_a_ticket_a_ranged_one_never_does() {
    let mut ops = FakeBodyTicketOps::default();
    let body = offered(Some(&[8, 9]), None);
    let (forwarded, seen, delivered) = forward(&mut ops, body, true, Ok(()));
    assert_eq!((forwarded, delivered), (Ok(()), true));
    assert_eq!(seen, [BodyDelivery::Lent(vec![8, 9])]);
    let rejected = Err(UNKNOWN_ERROR_CODE);
    let (forwarded, seen, _) = forward(&mut ops, body, true, rejected);
    assert_eq!((forwarded, seen.len()), (rejected, 1));
    let (forwarded, seen, _) = forward(&mut ops, body, false, Ok(()));
    assert_eq!(
        (forwarded, seen.is_empty()),
        (Err(INVALID_ARGUMENT_ERROR_CODE), true)
    );
    assert!(ops.acquired.is_empty());
}
#[test]
fn body_rejection_releases_acceptance_transfers() {
    for result in [Err(UNKNOWN_ERROR_CODE), Ok(())] {
        let mut ops = FakeBodyTicketOps::default();
        let body = offered(Some(&[4, 5, 6, 7]), Some(0x2000));
        let (forwarded, seen, delivered) = forward(&mut ops, body, false, result);
        assert_eq!((forwarded, delivered), (result, true));
        assert_eq!(seen, [BodyDelivery::Ticketed(vec![4, 5, 6, 7], 0x2000)]);
        assert_eq!(ops.acquired, [0x2000]);
    }
}
#[test]
fn a_body_without_storage_is_missing_and_acquires_nothing() {
    let mut ops = FakeBodyTicketOps::default();
    let body = OfferedBody {
        len: 3,
        storage: None,
        ticket: Some(0x2000),
    };
    let (forwarded, seen, delivered) = forward(&mut ops, body, false, Ok(()));
    assert_eq!((forwarded, delivered), (Ok(()), true));
    assert_eq!(seen, [BodyDelivery::Missing]);
    assert!(ops.acquired.is_empty());
}
#[test]
fn submission_interrupt_registration_removed_before_release() {
    let state = State::new();
    let submission = recording_submission();
    let mut registration = submission.adopt(0x1000, &state);
    state.request();
    submission.finish(TransferResult {
        error_code: CANCELED_ERROR_CODE,
        ..TransferResult::default()
    });
    submission.shutdown();
    let result = submission.wait_with_unregister(|| registration.unregister());
    assert!(result.canceled_by_interrupt);
    state.request();
    submission.with_ops(|ops| {
        assert_eq!(ops.canceled, [0x1000]);
        assert_eq!(ops.released, [0x1000]);
    });
}
#[test]
fn archive_state_only_unrestored_glacier_and_deep_archive_are_unreadable() {
    let restored: &[u8] =
        b"ongoing-request=\"false\", expiry-date=\"Fri, 21 Dec 2012 00:00:00 GMT\"";
    let in_progress: &[u8] = b"ongoing-request=\"true\"";
    for (storage_class, restore, readable) in [
        (&b""[..], &b""[..], true),
        (b"STANDARD", b"", true),
        (b"GLACIER_IR", b"", true),
        (b"GLACIER", b"", false),
        (b"DEEP_ARCHIVE", b"", false),
        (b"GLACIER", in_progress, false),
        (b"DEEP_ARCHIVE", in_progress, false),
        (b"GLACIER", restored, true),
        (b"DEEP_ARCHIVE", restored, true),
        (b"glacier", b"", true),
    ] {
        let state = ArchiveState::from_headers(storage_class, restore);
        assert_eq!(state.readable(), readable, "{storage_class:?} {restore:?}");
    }
    assert!(!ArchiveState::from_storage_class(b"GLACIER").readable());
}
#[test]
fn archive_state_from_headers_keeps_the_class_and_a_finished_restore() {
    let archived = ArchiveState {
        archived: true,
        restored: false,
    };
    for (storage_class, restore, expected) in [
        (&b""[..], &b""[..], ArchiveState::default()),
        (b"GLACIER_IR", b"", ArchiveState::default()),
        (b"GLACIER", b"", archived),
        (b"DEEP_ARCHIVE", b"ongoing-request=\"true\"", archived),
        (
            b"GLACIER",
            b"ongoing-request=\"false\", expiry-date=\"Fri, 21 Dec 2012 00:00:00 GMT\"",
            ArchiveState {
                archived: true,
                restored: true,
            },
        ),
    ] {
        assert_eq!(ArchiveState::from_headers(storage_class, restore), expected);
    }
    assert_eq!(ArchiveState::from_storage_class(b"DEEP_ARCHIVE"), archived);
}
#[test]
fn header_debug_hides_only_the_customer_key() {
    let shown = format!("{:?}", Header::new("Cache-Control", "max-age=60"));
    assert_eq!(
        shown,
        r#"Header { name: "Cache-Control", value: "max-age=60" }"#
    );
    for name in [
        "x-amz-server-side-encryption-customer-key",
        "X-Amz-Server-Side-Encryption-Customer-Key",
    ] {
        let shown = format!("{:?}", Header::new(name, "c2VjcmV0"));
        assert!(!shown.contains("c2VjcmV0"), "{shown}");
        assert!(shown.contains("<redacted>"), "{shown}");
    }
    let md5 = Header::new("x-amz-server-side-encryption-customer-key-MD5", "bWQ1");
    assert!(format!("{md5:?}").contains("bWQ1"));
}
