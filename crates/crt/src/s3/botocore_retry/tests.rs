use super::*;

fn longest(attempt: u64, kind: ErrorKind) -> Duration {
    backoff_delay(&mut || u64::MAX, attempt, kind) + Duration::from_nanos(1)
}

#[test]
fn each_backoffs_ceiling_doubles_from_its_kinds_scale_up_to_twenty_seconds() {
    for (attempt, seconds) in (1..).zip([1, 2, 4, 8, 16, 20, 20]) {
        assert_eq!(
            longest(attempt, ErrorKind::Throttling),
            Duration::from_secs(seconds)
        );
    }
    let transient = [
        50, 100, 200, 400, 800, 1600, 3200, 6400, 12_800, 20_000, 20_000,
    ];
    for (attempt, millis) in (1..).zip(transient) {
        assert_eq!(
            longest(attempt, ErrorKind::Transient),
            Duration::from_millis(millis)
        );
    }
    for kind in [ErrorKind::Throttling, ErrorKind::Transient] {
        assert_eq!(longest(u64::MAX, kind), Duration::from_secs(20));
    }
}
#[test]
fn backoffs_spread_across_the_whole_wait_below_the_ceiling() {
    let mut state: u64 = 0x5eed;
    let mut random = || {
        state = state.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = state;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^ (z >> 31)
    };
    for attempt in [1, 2] {
        let ceiling = Duration::from_secs(1 << (attempt - 1));
        let delays: Vec<_> = (0..1000)
            .map(|_| backoff_delay(&mut random, attempt, ErrorKind::Throttling))
            .collect();
        assert!(delays.iter().all(|delay| *delay < ceiling));
        assert!(
            delays
                .iter()
                .min()
                .is_some_and(|delay| *delay < ceiling / 10)
        );
        assert!(
            delays
                .iter()
                .max()
                .is_some_and(|delay| *delay > ceiling * 9 / 10)
        );
    }
}
#[test]
fn the_quota_covers_retries_by_their_kinds_cost() {
    for (kind, retries) in [(ErrorKind::Transient, 35), (ErrorKind::Throttling, 100)] {
        let mut quota = Quota::default();
        for _ in 0..retries {
            assert!(quota.acquire(kind).is_some());
        }
        assert_eq!(quota.acquire(kind), None);
    }
    let mut quota = Quota { available: 13 };
    assert_eq!(quota.acquire(ErrorKind::Transient), None);
    assert_eq!(quota.acquire(ErrorKind::Throttling), Some(5));
    assert_eq!(quota.available, 8);
}
#[test]
fn a_success_gives_back_its_last_retrys_cost() {
    let mut quota = Quota { available: 8 };
    quota.release(Some(14));
    assert_eq!(quota.available, 22);
    quota.release(None);
    assert_eq!(quota.available, 23);
    let mut full = Quota::default();
    full.release(None);
    full.release(Some(5));
    assert_eq!(full.available, Quota::CAPACITY_MAX);
}
#[test]
fn a_retry_is_admitted_while_an_attempt_is_left_and_the_quota_covers_it() {
    let mut quota = Quota::default();
    let mut attempts = Attempts::default();
    assert!(attempts.admit_retry(3, &mut quota, ErrorKind::Throttling));
    assert_eq!(attempts.last_retry_cost, Some(5));
    attempts.count += 1;
    assert!(attempts.admit_retry(3, &mut quota, ErrorKind::Transient));
    assert_eq!(attempts.last_retry_cost, Some(14));
    attempts.count += 1;
    assert!(!attempts.admit_retry(3, &mut quota, ErrorKind::Transient));
    assert_eq!(attempts.exhausted(3), Some(2));
    assert_eq!(quota.available, Quota::CAPACITY_MAX - 5 - 14);
    let mut empty = Quota { available: 4 };
    let mut first = Attempts::default();
    assert!(!first.admit_retry(3, &mut empty, ErrorKind::Throttling));
    assert_eq!((first.last_retry_cost, empty.available), (None, 4));
}
#[test]
fn a_429_the_crt_gave_up_on_is_a_throttle_unless_modeled() {
    let failure = |error_code: i32, status: i32, code: &[u8]| {
        let mut failure = TransferResult {
            error_code,
            response_status: status,
            ..TransferResult::default()
        };
        failure.service_error.code.set(code);
        failure
    };
    let gave_up = INVALID_RESPONSE_STATUS_ERROR_CODE;
    let modeled: &[&[u8]] = &[b"NoSuchBucket"];
    for (result, throttled) in [
        (failure(gave_up, 429, b""), true),
        (failure(gave_up, 429, b"TooManyRequests"), true),
        (failure(gave_up, 429, b"NoSuchBucket"), false),
        (failure(gave_up, 403, b""), false),
        (failure(gave_up, 503, b""), false),
        (
            failure(crt_sys::AWS_ERROR_S3_SLOW_DOWN, 429, b"SlowDown"),
            false,
        ),
        (failure(0, 200, b""), false),
    ] {
        assert_eq!(
            is_unmodeled_throttle(&result, modeled),
            throttled,
            "{result:?}"
        );
    }
}
