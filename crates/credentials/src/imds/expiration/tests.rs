use super::*;
use crate::tests::TestResult;

fn seconds(count: u64) -> Duration {
    Duration::from_secs(count)
}

/// Seconds from the epoch to the instant `strptime` reads from `text`.
fn strict(text: &str) -> Option<u64> {
    let since = strptime(text)?.duration_since(UNIX_EPOCH).ok()?;
    Some(since.as_secs())
}

/// botocore keeps its refresh window and a jitter ahead of an expiry:
/// fifteen minutes and two to ten more (`_evaluate_expiration`).
#[test]
fn the_offset_is_seventeen_to_twenty_five_minutes() {
    assert_eq!(offset(0), seconds(17 * 60));
    assert_eq!(offset(480), seconds(25 * 60));
    assert_eq!(offset(481), seconds(17 * 60));
    assert!((seconds(17 * 60)..=seconds(25 * 60)).contains(&offset(u64::MAX)));
}

/// The service's form is read; each other form is one CPython's
/// `strptime` refuses, or one it reads and this crate does not.
#[test]
fn strptime_reads_the_services_form() {
    const EXPIRY: u64 = 2_139_722_880;
    for (text, expected) in [
        ("2037-10-21T07:28:00Z", Some(EXPIRY)),
        ("2037-10-21t07:28:00z", None),
        ("2037-10-21T7:28:0Z", None),
        ("2037-10- 1T07:28:00Z", None),
        ("1970-01-01T00:00:00Z", Some(0)),
        ("2000-02-29T00:00:00Z", Some(951_782_400)),
        ("2037-10-21T07:28:00.000Z", None),
        ("2037-10-21T07:28:00+00:00", None),
        ("2037-10-21 07:28:00Z", None),
        ("2037-10-21T07:28:00Z ", None),
        (" 2037-10-21T07:28:00Z", None),
        ("2037-10-21T07:28:60Z", None),
        ("2037-10-21T07:60:00Z", None),
        ("2037-10-21T24:00:00Z", None),
        ("2037-02-30T07:28:00Z", None),
        ("2037-00-21T07:28:00Z", None),
        ("2037-10-00T07:28:00Z", None),
        ("2037-010-21T07:28:00Z", None),
        ("2037-10-021T07:28:00Z", None),
        ("2037- 1-21T07:28:00Z", None),
        ("2037-10-21T07: 5:00Z", None),
        ("0000-01-01T00:00:00Z", None),
        ("20371-10-21T07:28:00Z", None),
        ("2037-10-21T07:28:00", None),
        ("not a date", None),
        ("", None),
    ] {
        assert_eq!(strict(text), expected, "{text:?}");
    }
    // Windows' clock starts at 1601-01-01, so there an earlier expiry is no
    // instant `strptime` can return, and is refused as unreadable.
    assert_eq!(
        strptime("0001-01-01T00:00:00Z").is_some(),
        cfg!(not(windows))
    );
    assert!(strptime("1601-01-01T00:00:00Z").is_some());
}

/// The service's expiry at 07:28:00; `now` is given as seconds before it.
#[test]
fn an_expiry_inside_the_offset_moves_ahead_of_the_clock() -> TestResult {
    let text = "2037-10-21T07:28:00Z";
    let expiry = UNIX_EPOCH + seconds(2_139_722_880);
    let offset = seconds(17 * 60);
    for (before, moved) in [
        (3600, false),
        (17 * 60 + 1, false),
        (17 * 60, true),
        (1, true),
    ] {
        let now = expiry - seconds(before);
        let expected = if moved { now + offset } else { expiry };
        assert_eq!(
            evaluate(text, now, offset)?,
            expected,
            "{before} seconds before"
        );
    }
    // Credentials the service returns already expired stay in use, and the
    // new expiry is cut to the whole second botocore formats it to.
    let now = expiry + seconds(86_400) + Duration::from_millis(250);
    assert_eq!(
        evaluate(text, now, offset)?,
        expiry + seconds(86_400) + offset
    );
    Ok(())
}

/// `strptime` refuses a fraction, so botocore leaves such an expiry alone
/// and its provider reads it with dateutil.
#[test]
fn an_expiry_strptime_refuses_is_never_moved() -> TestResult {
    let expiry = UNIX_EPOCH + seconds(2_139_722_880);
    let offset = seconds(17 * 60);
    for now in [expiry - seconds(1), expiry + seconds(86_400)] {
        for text in ["2037-10-21T07:28:00.000Z", "2037-10-21T07:28:00+00:00"] {
            assert_eq!(evaluate(text, now, offset)?, expiry, "{text}");
        }
    }
    Ok(())
}

#[test]
fn an_expiry_nothing_reads_is_an_error() {
    let now = UNIX_EPOCH + seconds(2_139_722_880);
    let unreadable = |text: &str| {
        Err(LoadError::Expiry {
            provider: "iam-role",
            value: text.to_owned(),
        })
    };
    assert_eq!(
        evaluate("not a date", now, seconds(1020)),
        unreadable("not a date")
    );
}
