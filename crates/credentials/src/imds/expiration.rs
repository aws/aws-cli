//! The expiry of a role's credentials, as botocore's fetcher and then its
//! provider read the service's `Expiration`.
//!
//! The fetcher reads it with `strptime` and moves an expiry that is past,
//! or about to be, some minutes into the future, so that the credentials
//! stay in use through an outage of the service
//! (`InstanceMetadataFetcher._evaluate_expiration`). The provider then
//! reads the text the fetcher left with dateutil
//! (`RefreshableCredentials.create_from_metadata`). An expiry in any form
//! but the service's own, `YYYY-MM-DDTHH:MM:SSZ`, is never moved, so a
//! refresh asks the service again as soon as it comes due. `strptime`
//! reads a few more forms, with one-digit fields among them, which are not
//! read here.
use super::METHOD;
use crate::LoadError;
use crate::expiry::{self, days_from_civil, days_in_month};
use std::ops::Range;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// The `ec2_credential_refresh_window` botocore's chain gives its fetcher
/// (`create_credential_resolver`), in place of the fetcher's own ten
/// minutes.
const REFRESH_WINDOW: Duration = Duration::from_secs(15 * 60);
/// The least of the two to ten minutes botocore adds to the window, and
/// how many whole seconds it picks from (`_evaluate_expiration`).
const JITTER_FLOOR: Duration = Duration::from_secs(120);
const JITTER_CHOICES: u64 = 481;
/// The form the service writes an expiry in: a digit wherever this has a
/// `0`, and each other byte as it is.
const FORM: &[u8; 20] = b"0000-00-00T00:00:00Z";

/// The time botocore's fetcher keeps ahead of an expiry: its refresh
/// window and a jitter of two to ten minutes, which `random` picks
/// (`_evaluate_expiration`). It is longer than the advisory window of the
/// refresh, so credentials the fetcher extends sign at once.
pub(super) fn offset(random: u64) -> Duration {
    REFRESH_WINDOW + JITTER_FLOOR + Duration::from_secs(random % JITTER_CHOICES)
}

/// The expiry botocore's provider holds for a service's `Expiration` of
/// `text`, fetched at `now`.
///
/// botocore's `_evaluate_expiration`: an expiry [`strptime`] reads that is
/// past, or less than `offset` after `now`, becomes `offset` after `now`,
/// to the whole second botocore formats it to. Any other is the instant
/// dateutil reads from the text.
///
/// # Errors
/// Text neither [`strptime`] nor [`expiry::parse`] reads.
pub(super) fn evaluate(
    text: &str,
    now: SystemTime,
    offset: Duration,
) -> Result<SystemTime, LoadError> {
    let Some(stamp) = strptime(text) else {
        return expiry::parse(METHOD, text);
    };
    let due = stamp
        .checked_sub(offset)
        .is_none_or(|threshold| now >= threshold);
    if due && let Some(extended) = now.checked_add(offset) {
        return Ok(extended
            .duration_since(UNIX_EPOCH)
            .map_or(extended, |since| {
                UNIX_EPOCH + Duration::from_secs(since.as_secs())
            }));
    }
    Ok(stamp)
}

/// CPython's `datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")`, as UTC
/// (`_evaluate_expiration`), for the form the service sends: every field of
/// its full width, a date that exists, in the years 1 to 9999. `None` for
/// any other text.
fn strptime(text: &str) -> Option<SystemTime> {
    let bytes: &[u8; 20] = text.as_bytes().try_into().ok()?;
    let in_form = bytes.iter().zip(FORM).all(|(byte, form)| match form {
        b'0' => byte.is_ascii_digit(),
        _ => byte == form,
    });
    if !in_form {
        return None;
    }
    let number = |range: Range<usize>| {
        bytes[range]
            .iter()
            .fold(0, |value, digit| value * 10 + i64::from(digit - b'0'))
    };
    let (year, month, day) = (number(0..4), number(5..7), number(8..10));
    let (hour, minute, second) = (number(11..13), number(14..16), number(17..19));
    let valid = year > 0
        && (1..=12).contains(&month)
        && (1..=days_in_month(year, month)).contains(&day)
        && hour < 24
        && minute < 60
        && second < 60;
    if !valid {
        return None;
    }
    let seconds = days_from_civil(year, month, day) * 86_400 + hour * 3600 + minute * 60 + second;
    let whole = Duration::from_secs(seconds.unsigned_abs());
    if seconds < 0 {
        UNIX_EPOCH.checked_sub(whole)
    } else {
        UNIX_EPOCH.checked_add(whole)
    }
}

#[cfg(test)]
mod tests;
