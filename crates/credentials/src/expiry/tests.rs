use super::*;

/// Seconds from the epoch to the instant `text` names, negative before it.
fn seconds(text: &str) -> Option<f64> {
    let instant = instant(text.as_bytes())?;
    Some(match instant.duration_since(UNIX_EPOCH) {
        Ok(after) => after.as_secs_f64(),
        Err(before) => -before.duration().as_secs_f64(),
    })
}

#[test]
fn reads_an_iso_8601_time_with_a_zone() {
    for (text, expected) in [
        ("1970-01-01T00:00:00Z", 0.0),
        ("2037-10-21T07:28:00Z", 2_139_722_880.0),
        ("2037-10-21t07:28:00z", 2_139_722_880.0),
        // dateutil reads each of these as the instant above.
        ("2037-10-21 07:28:00Z", 2_139_722_880.0),
        ("2037-10-21 07:28:00z", 2_139_722_880.0),
        ("2037-10-21T07:28:00 Z", 2_139_722_880.0),
        ("2037-10-21T07:28:00+00:00", 2_139_722_880.0),
        ("2037-10-21 07:28:00 +05:30", 2_139_703_080.0),
        ("2037-10-21T07:28:00+0530", 2_139_703_080.0),
        ("2037-10-21 07:28:00.250-0530", 2_139_742_680.25),
        ("2037-10-21T07:28:00+05:30", 2_139_703_080.0),
        ("2037-10-21T07:28:00.25-0530", 2_139_742_680.25),
        ("2000-02-29T00:00:00+05", 951_764_400.0),
        ("1969-12-31T23:59:59Z", -1.0),
    ] {
        assert_eq!(seconds(text), Some(expected), "{text}");
    }
}

#[test]
fn refuses_what_it_cannot_place_on_the_clock() {
    for text in [
        "",
        "soon",
        "2037-10-21",
        "2037-10-21T07:28:00",
        "2037-10-21  07:28:00Z",
        "2037-10-21T07:28:00  Z",
        // Forms dateutil reads and this module does not.
        "2037-10-21T07:28:00 UTC",
        "2037-10-21T07:28:00,5Z",
        "2037-10-21T07:28Z",
        "20371021T072800Z",
        "2037-02-30T07:28:00Z",
        "2037-13-01T07:28:00Z",
        "2037-10-21T24:00:00Z",
        "2037-10-21T07:28:00.Z",
        "2037-10-21T07:28:00+5",
        "2037-10-21T07:28:00+05:60",
        "2037-10-21T07:28:00Zjunk",
    ] {
        assert_eq!(seconds(text), None, "{text}");
    }
    assert_eq!(
        parse("env", "soon"),
        Err(LoadError::Expiry {
            provider: "env",
            value: "soon".into()
        })
    );
}
