#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;

#[test]
fn each_read_form_sends_the_date_botocore_sends() {
    for (value, expected) in [
        ("2037-10-21", "Wed, 21 Oct 2037 00:00:00 GMT"),
        ("2037-10-21T07:28Z", "Wed, 21 Oct 2037 07:28:00 GMT"),
        ("2037-10-21T07:28:00Z", "Wed, 21 Oct 2037 07:28:00 GMT"),
        ("2037-10-21T07:28:00", "Wed, 21 Oct 2037 07:28:00 GMT"),
        (
            "2037-10-21T07:28:00.999999Z",
            "Wed, 21 Oct 2037 07:28:00 GMT",
        ),
        (
            "2037-10-21T07:28:00.5-00:30",
            "Wed, 21 Oct 2037 07:58:00 GMT",
        ),
        ("2037-10-21T07:28:00-0530", "Wed, 21 Oct 2037 12:58:00 GMT"),
        ("2037-10-21T07:28+05:30", "Wed, 21 Oct 2037 01:58:00 GMT"),
        ("2037-10-21T00:00:00-23:59", "Wed, 21 Oct 2037 23:59:00 GMT"),
        ("2037-10-21T23:59:59+00:00", "Wed, 21 Oct 2037 23:59:59 GMT"),
        ("2024-02-29T12:00:00Z", "Thu, 29 Feb 2024 12:00:00 GMT"),
        ("2000-02-29", "Tue, 29 Feb 2000 00:00:00 GMT"),
        ("1000-01-01T00:00:00+23:59", "Tue, 31 Dec 0999 00:01:00 GMT"),
        ("1969-12-31T23:59:59Z", "Wed, 31 Dec 1969 23:59:59 GMT"),
        ("1970-01-01", "Thu, 01 Jan 1970 00:00:00 GMT"),
        ("9999-12-30T23:59:59Z", "Thu, 30 Dec 9999 23:59:59 GMT"),
        ("9999-12-31T00:00:00+00:01", "Thu, 30 Dec 9999 23:59:00 GMT"),
        (
            "Wed, 21 Oct 2037 07:28:00 GMT",
            "Wed, 21 Oct 2037 07:28:00 GMT",
        ),
        (
            "Mon, 21 Oct 2037 07:28:00 GMT",
            "Wed, 21 Oct 2037 07:28:00 GMT",
        ),
        (
            "Thu, 29 Feb 2024 23:59:59 GMT",
            "Thu, 29 Feb 2024 23:59:59 GMT",
        ),
        (
            "Sat, 01 Jan 1000 00:00:00 GMT",
            "Wed, 01 Jan 1000 00:00:00 GMT",
        ),
        (
            "Thu, 30 Dec 9999 23:59:59 GMT",
            "Thu, 30 Dec 9999 23:59:59 GMT",
        ),
    ] {
        let date: HttpDate = value.parse().unwrap();
        assert_eq!(date.to_string(), expected, "{value:?}");
    }
}

#[test]
fn every_other_value_is_unconverted() {
    for value in [
        "",
        "90",
        "2037",
        "tomorrow",
        "2037-10-21 07:28:00Z",
        "2037-10-21t07:28:00z",
        "21 Oct 2037",
        "Wed, 21 Oct 2037 07:28:00 UTC",
        "Wed, 21 Oct 2037 07:28:00 +0000",
        "wed, 21 Oct 2037 07:28:00 GMT",
        "Wed, 1 Oct 2037 07:28:00 GMT",
        "Wed,  21 Oct 2037 07:28:00 GMT",
        "Wed, 21 Oct 2037 07:28:00 GMT ",
        " 2037-10-21",
        "2023-02-29",
        "1900-02-29",
        "2037-13-01",
        "2037-00-10",
        "2037-10-00",
        "2037-10-21T24:00:00Z",
        "2037-10-21T07:60:00Z",
        "2037-10-21T07:28:60Z",
        "2037-10-21T07:28:00+24:00",
        "2037-10-21Z",
        "2037-10-21T07:28:00.Z",
        "2037-10-21T07:28:00+05:30:00",
        "2037-10-21T07Z",
        "2037-10-21T07:28:00.1234567Z",
        "2037-10-21T07:28:00+05",
        "2037-10-21T07:28:00+05:60",
        "2037-10-21T07:28:00ZZ",
        "\u{ff12}037-10-21",
        "0999-12-31",
        "Wed, 21 Oct 0099 07:28:00 GMT",
        "9999-12-31",
        "9999-12-31T00:00:00Z",
        "9999-12-30T23:59:59-00:01",
    ] {
        assert_eq!(
            value.parse::<HttpDate>(),
            Err(UnconvertedTimestamp),
            "{value:?}"
        );
    }
}

#[test]
fn civil_days_round_trip() {
    let first = days_from_civil(2000, 1, 1).unwrap();
    assert_eq!(first, 10_957);
    for days in first..first + 146_097 {
        let (year, month, day) = civil_from_days(days);
        let year = u32::try_from(year).unwrap();
        assert_eq!(days_from_civil(year, month, day), Some(days), "{days}");
    }
    assert_eq!(days_from_civil(9999, 12, 31), Some(LAST_DAY));
}
