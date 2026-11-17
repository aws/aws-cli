//! The expiry a provider's source names, as an instant.
//!
//! botocore reads an expiry with `dateutil.parser.parse`, which guesses at
//! many forms. Only the form the credential sources are documented to
//! write is read here, with the spellings of it dateutil reads as the same
//! instant: an ISO 8601 date and time with a
//! zone, `2037-10-21T07:28:00Z`, with `T`, `t` or a space between the two,
//! optional fractional seconds, and `Z`, `z`, `+05:30`, `-0530` or `+05` for
//! the zone, which a space may precede.
//!
//! dateutil reads more: a zone's name (`UTC`, `GMT`), a comma before the
//! fraction, a time without seconds, a date without hyphens, an offset of
//! one digit, and text that is not ISO 8601 at all. Those are refused.
//!
//! A time without a zone is refused. botocore accepts it and then fails
//! the first time it compares the expiry with its zone-aware clock
//! (`RefreshableCredentials._seconds_remaining`).
use crate::LoadError;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// The instant `value` names.
///
/// # Errors
/// `value` is not in the form this module reads.
pub(crate) fn parse(provider: &'static str, value: &str) -> Result<SystemTime, LoadError> {
    instant(value.as_bytes()).ok_or_else(|| LoadError::Expiry {
        provider,
        value: value.to_owned(),
    })
}

fn instant(text: &[u8]) -> Option<SystemTime> {
    // `2037-10-21T07:28:00`, then an optional fraction, then the zone.
    let (stamp, rest) = text.split_first_chunk::<19>()?;
    let separators = [(4, b'-'), (7, b'-'), (13, b':'), (16, b':')];
    if separators.iter().any(|&(at, byte)| stamp[at] != byte)
        || !matches!(stamp[10], b'T' | b't' | b' ')
    {
        return None;
    }
    let (year, month, day) = (
        number(&stamp[..4])?,
        number(&stamp[5..7])?,
        number(&stamp[8..10])?,
    );
    let (hour, minute, second) = (
        number(&stamp[11..13])?,
        number(&stamp[14..16])?,
        number(&stamp[17..])?,
    );
    if !(1..=12).contains(&month) || !(1..=days_in_month(year, month)).contains(&day) {
        return None;
    }
    if hour > 23 || minute > 59 || second > 59 {
        return None;
    }
    let (nanos, zone) = fraction(rest)?;
    let zone = zone.strip_prefix(b" ").unwrap_or(zone);
    let seconds = days_from_civil(year, month, day) * 86_400 + hour * 3600 + minute * 60 + second
        - offset(zone)?;
    let whole = Duration::from_secs(seconds.unsigned_abs());
    let instant = if seconds < 0 {
        UNIX_EPOCH.checked_sub(whole)?
    } else {
        UNIX_EPOCH.checked_add(whole)?
    };
    instant.checked_add(Duration::from_nanos(nanos))
}

/// A run of ASCII digits as a number.
fn number(digits: &[u8]) -> Option<i64> {
    digits.iter().try_fold(0_i64, |value, digit| {
        digit
            .is_ascii_digit()
            .then(|| value * 10 + i64::from(digit - b'0'))
    })
}

/// The nanoseconds of an optional `.123` and what follows it.
fn fraction(rest: &[u8]) -> Option<(u64, &[u8])> {
    let Some(digits) = rest.strip_prefix(b".") else {
        return Some((0, rest));
    };
    let count = digits
        .iter()
        .take_while(|digit| digit.is_ascii_digit())
        .count();
    let (digits, zone) = digits.split_at(count);
    if digits.is_empty() {
        return None;
    }
    // Digits past the ninth are finer than a nanosecond.
    let nanos = (0..9).try_fold(0_u64, |value, index| {
        let digit = digits.get(index).map_or(0, |digit| digit - b'0');
        value.checked_mul(10)?.checked_add(u64::from(digit))
    })?;
    Some((nanos, zone))
}

/// A zone designator's offset from UTC in seconds.
fn offset(zone: &[u8]) -> Option<i64> {
    let (sign, digits) = match zone {
        b"Z" | b"z" => return Some(0),
        [b'+', digits @ ..] => (1, digits),
        [b'-', digits @ ..] => (-1, digits),
        _ => return None,
    };
    let (hours, minutes) = match digits {
        [h1, h2] => (number(&[*h1, *h2])?, 0),
        [h1, h2, m1, m2] | [h1, h2, b':', m1, m2] => (number(&[*h1, *h2])?, number(&[*m1, *m2])?),
        _ => return None,
    };
    (hours < 24 && minutes < 60).then_some(sign * (hours * 3600 + minutes * 60))
}

pub(crate) fn days_in_month(year: i64, month: i64) -> i64 {
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    match month {
        2 if leap => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    }
}

/// Days from 1970-01-01 to a proleptic Gregorian date, by counting whole
/// 400-year eras of 146,097 days from 0000-03-01.
pub(crate) fn days_from_civil(year: i64, month: i64, day: i64) -> i64 {
    let year = if month <= 2 { year - 1 } else { year };
    let era = year.div_euclid(400);
    let year_of_era = year.rem_euclid(400);
    let day_of_year = (153 * ((month + 9) % 12) + 2) / 5 + day - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    // 719,468 days separate 0000-03-01 from 1970-01-01.
    era * 146_097 + day_of_era - 719_468
}

#[cfg(test)]
mod tests;
