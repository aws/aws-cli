//! The HTTP date botocore sends for a timestamp header such as `Expires`.
//!
//! botocore's merged S3 model types `Expires` as a timestamp
//! (data/s3/2006-03-01/service-2.sdk-extras.json). Its serializer reads the
//! value with `parse_to_aware_datetime`, which takes an epoch or anything
//! `dateutil.parser.parse` reads, with UTC for a value without a zone, then
//! sends the instant's whole seconds as an RFC 822 date
//! (`Serializer._timestamp_rfc822`).
//!
//! Only the forms whose instant depends on neither dateutil's guesses nor
//! the local zone are read here:
//!
//! * an ISO 8601 date, `2037-10-21`, or date and time,
//!   `2037-10-21T07:28[:00[.5]]`, with an optional `Z`, `+05:30`, or `-0530`
//! * an IMF-fixdate, `Wed, 21 Oct 2037 07:28:00 GMT`, whose weekday dateutil
//!   ignores
//!
//! An epoch is left out: botocore reads it in the local zone. So is a year
//! before 1000, which dateutil reads as a two-digit year in some forms, and an
//! instant on or after 9999-12-31, which botocore cannot convert from every
//! local zone back to UTC.
use std::fmt;
use std::str::FromStr;

/// An instant botocore sends as an HTTP date, to the whole second.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct HttpDate {
    seconds: i64,
}

/// A timestamp outside the forms [`HttpDate`] reads as botocore does.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct UnconvertedTimestamp;
impl fmt::Display for UnconvertedTimestamp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("timestamp is not in a form native converts")
    }
}
impl std::error::Error for UnconvertedTimestamp {}

impl FromStr for HttpDate {
    type Err = UnconvertedTimestamp;
    /// The instant `text` names, as botocore reads it.
    fn from_str(text: &str) -> Result<Self, UnconvertedTimestamp> {
        let text = text.as_bytes();
        iso_8601(text)
            .or_else(|| imf_fixdate(text))
            .filter(|&seconds| seconds < LAST_DAY * SECONDS_PER_DAY)
            .map(|seconds| Self { seconds })
            .ok_or(UnconvertedTimestamp)
    }
}

/// The IMF-fixdate `formatdate(..., usegmt=True)` writes.
impl fmt::Display for HttpDate {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let days = self.seconds.div_euclid(SECONDS_PER_DAY);
        let time = self.seconds.rem_euclid(SECONDS_PER_DAY);
        let (year, month, day) = civil_from_days(days);
        let weekday = WEEKDAYS[usize::try_from((days + 3).rem_euclid(7)).unwrap_or(0)];
        write!(
            f,
            "{weekday}, {day:02} {} {year:04} {:02}:{:02}:{:02} GMT",
            MONTHS[month as usize - 1],
            time / 3600,
            time / 60 % 60,
            time % 60,
        )
    }
}

const SECONDS_PER_DAY: i64 = 86_400;
/// The days from the epoch to 9999-12-31, where an instant stops converting
/// back to UTC in a zone east of UTC.
const LAST_DAY: i64 = 2_932_896;
const WEEKDAYS: [&str; 7] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTHS: [&str; 12] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

fn iso_8601(text: &[u8]) -> Option<i64> {
    let mut rest = Cursor(text);
    let year = rest.digits(4)?;
    rest.expect(b'-')?;
    let month = rest.digits(2)?;
    rest.expect(b'-')?;
    let date = date_seconds(year, month, rest.digits(2)?)?;
    if rest.0.is_empty() {
        return Some(date);
    }
    rest.expect(b'T')?;
    let hour = rest.digits(2)?;
    rest.expect(b':')?;
    let minute = rest.digits(2)?;
    let second = if rest.eat(b':') { rest.seconds()? } else { 0 };
    Some(date + clock(hour, minute, second)? - zone_offset(rest.0)?)
}

fn zone_offset(zone: &[u8]) -> Option<i64> {
    let (sign, rest) = match zone {
        [] | [b'Z'] => return Some(0),
        [b'+', rest @ ..] => (1, rest),
        [b'-', rest @ ..] => (-1, rest),
        _ => return None,
    };
    let mut rest = Cursor(rest);
    let hours = rest.digits(2)?;
    rest.eat(b':');
    let minutes = rest.digits(2)?;
    (rest.0.is_empty() && hours < 24 && minutes < 60)
        .then(|| sign * i64::from(hours * 3600 + minutes * 60))
}

fn imf_fixdate(text: &[u8]) -> Option<i64> {
    let mut rest = Cursor(text);
    rest.name(&WEEKDAYS)?;
    rest.literal(b", ")?;
    let day = rest.digits(2)?;
    rest.expect(b' ')?;
    let month = rest.name(&MONTHS)?;
    rest.expect(b' ')?;
    let year = rest.digits(4)?;
    rest.expect(b' ')?;
    let time = rest.clock()?;
    (rest.0 == b" GMT").then_some(())?;
    Some(date_seconds(year, month, day)? + time)
}

fn date_seconds(year: u32, month: u32, day: u32) -> Option<i64> {
    Some(days_from_civil(year, month, day)? * SECONDS_PER_DAY)
}

fn clock(hour: u32, minute: u32, second: u32) -> Option<i64> {
    (hour < 24 && minute < 60 && second < 60).then(|| i64::from(hour * 3600 + minute * 60 + second))
}

fn days_from_civil(year: u32, month: u32, day: u32) -> Option<i64> {
    let leap = year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
    let month_days = match month {
        2 if leap => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        1..=12 => 31,
        _ => return None,
    };
    if year < 1000 || !(1..=month_days).contains(&day) {
        return None;
    }
    let year = i64::from(year) - i64::from(month <= 2);
    let era = year.div_euclid(400);
    let year_of_era = year - era * 400;
    let march_month = i64::from((month + 9) % 12);
    let day_of_year = (153 * march_month + 2) / 5 + i64::from(day) - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    Some(era * 146_097 + day_of_era - 719_468)
}

fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let days = days + 719_468;
    let era = days.div_euclid(146_097);
    let day_of_era = days - era * 146_097;
    let year_of_era =
        (day_of_era - day_of_era / 1460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let march_month = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * march_month + 2) / 5 + 1;
    let month = if march_month < 10 {
        march_month + 3
    } else {
        march_month - 9
    };
    let year = year_of_era + era * 400 + i64::from(month <= 2);
    (year, month as u32, day as u32)
}

struct Cursor<'a>(&'a [u8]);
impl Cursor<'_> {
    fn digits(&mut self, count: usize) -> Option<u32> {
        let (digits, rest) = self.0.split_at_checked(count)?;
        let mut value = 0;
        for &digit in digits {
            digit.is_ascii_digit().then_some(())?;
            value = value * 10 + u32::from(digit - b'0');
        }
        self.0 = rest;
        Some(value)
    }
    fn eat(&mut self, byte: u8) -> bool {
        let Some((&first, rest)) = self.0.split_first() else {
            return false;
        };
        let matched = first == byte;
        if matched {
            self.0 = rest;
        }
        matched
    }
    fn expect(&mut self, byte: u8) -> Option<()> {
        self.eat(byte).then_some(())
    }
    fn literal(&mut self, text: &[u8]) -> Option<()> {
        self.0 = self.0.strip_prefix(text)?;
        Some(())
    }
    fn name(&mut self, names: &[&str]) -> Option<u32> {
        let (number, name) = (1..)
            .zip(names)
            .find(|(_, name)| self.0.starts_with(name.as_bytes()))?;
        self.0 = &self.0[name.len()..];
        Some(number)
    }
    fn seconds(&mut self) -> Option<u32> {
        let second = self.digits(2)?;
        if self.eat(b'.') {
            let fraction = self
                .0
                .iter()
                .take_while(|byte| byte.is_ascii_digit())
                .count();
            (1..=6).contains(&fraction).then_some(())?;
            self.0 = &self.0[fraction..];
        }
        Some(second)
    }
    fn clock(&mut self) -> Option<i64> {
        let hour = self.digits(2)?;
        self.expect(b':')?;
        let minute = self.digits(2)?;
        self.expect(b':')?;
        clock(hour, minute, self.digits(2)?)
    }
}

#[cfg(test)]
mod tests;
