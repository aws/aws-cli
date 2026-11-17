#![expect(clippy::unwrap_used, reason = "scanner assertion cases")]
use super::*;
#[test]
fn numeric_lexemes_are_preserved_without_conversion() {
    let value = parse(br#"[-0,1E2,10.50,1e309,1.0]"#).unwrap();
    assert_eq!(value.to_string(), "[-0,1E2,10.50,1e309,1.0]");
    let number = "1".repeat(10000);
    assert_eq!(parse(number.as_bytes()).unwrap().to_string(), number);
}
#[test]
fn strings_validate_utf8_and_surrogate_pairs() {
    assert_eq!(parse(br#""\ud83d\ude00""#).unwrap(), "😀");
    for invalid in [
        br#""\ud800""#.as_slice(),
        br#""\udc00""#,
        br#""\ud800 \udc00""#,
        b"\"\xff\"",
        br#""\x20""#,
        b"\"\x00\"",
    ] {
        assert!(parse(invalid).is_err(), "{invalid:?}");
    }
}
#[test]
fn malformed_and_nonstandard_numbers_are_rejected() {
    for invalid in [
        "NaN",
        "Infinity",
        "-Infinity",
        "01",
        "+1",
        "1.",
        "1e",
        "1e+",
        "--1",
        "[1,]",
        "{\"x\":1,}",
        "{}{}",
    ] {
        assert!(parse(invalid.as_bytes()).is_err(), "{invalid}");
    }
}
#[test]
fn duplicate_keys_retain_order_but_validate_discarded_values() {
    assert_eq!(
        parse(br#"{"x":1,"y":"b","x":"a"}"#).unwrap().to_string(),
        r#"{"x":"a","y":"b"}"#
    );
    assert!(parse(br#"{"x":NaN,"x":"ok"}"#).is_err());
}
#[test]
fn nesting_and_input_caps_are_inclusive() {
    let supported = format!("{{\"x\":{}{}}}", "[".repeat(32), "]".repeat(32));
    assert!(parse(supported.as_bytes()).is_ok());
    let deep = format!("{{\"x\":{}{}}}", "[".repeat(33), "]".repeat(33));
    assert_eq!(parse(deep.as_bytes()), Err(JsonError::TooDeep));
    let largest = format!("\"{}\"", "x".repeat(crate::SHORTHAND_INPUT_BYTES_MAX - 2));
    assert!(parse(largest.as_bytes()).is_ok());
    assert_eq!(
        parse(format!("{largest} ").as_bytes()),
        Err(JsonError::TooLong)
    );
}

#[test]
fn object_index_preserves_replacement_and_clone_order() {
    let mut object: Object = [("a", 1), ("b", 2), ("a", 3)]
        .into_iter()
        .map(|(key, value)| (key.into(), JsonValue::from(value)))
        .collect();
    assert_eq!(object.len(), 2);
    assert_eq!(object.get("a"), Some(&3.into()));
    assert_eq!(
        object
            .iter()
            .map(|(key, _)| key.as_str())
            .collect::<Vec<_>>(),
        ["a", "b"]
    );
    let original = object.clone();
    object.insert("b".into(), 4.into());
    object.insert("c".into(), 5.into());
    assert_eq!(original.get("b"), Some(&2.into()));
    assert_eq!(
        JsonValue::Object(object).to_string(),
        r#"{"a":3,"b":4,"c":5}"#
    );
    let duplicates = Object::from(vec![("a".into(), 1.into()), ("a".into(), 2.into())]);
    assert_eq!(duplicates.get("a"), Some(&1.into()));
}
fn syntax_error(input: &[u8]) -> (usize, bool) {
    match parse(input) {
        Err(JsonError::Syntax { offset, incomplete }) => (offset, incomplete),
        other => (usize::MAX, other.is_ok()),
    }
}
#[test]
fn escapes_fail_at_the_first_byte_std_json_rejects() {
    for (input, expected) in [
        (br#"{"a":"\q"}"#.as_slice(), (7, false)),
        (br#"{"a":"\q"#, (7, false)),
        (br#"{"a":"\"#, (7, true)),
        (br#"{"a":"\u12x"}"#, (10, false)),
        (br#"{"a":"\u12"#, (10, true)),
        (br#"{"a":"\ud800A"}"#, (12, false)),
        (br#"{"a":"\ud800"#, (12, true)),
        (br#"{"a":"\ud800\n"}"#, (13, false)),
        (br#"{"a":"\ud800\"#, (13, true)),
        (br#"{"a":"\ud800\uA"}"#, (14, false)),
        (br#"{"a":"\ud800\u12"}"#, (14, false)),
        (br#"{"a":"\ud800\u"#, (14, true)),
        (br#"{"a":"\ud800\ud800"}"#, (15, false)),
        (br#"{"a":"\ud800\udb00"}"#, (15, false)),
        (br#"{"a":"\ud800\ud"#, (15, true)),
        (br#"{"a":"\ud800\udcxx"}"#, (16, false)),
        (br#"{"a":"\ud800\udc"#, (16, true)),
        (br#"{"a":"\ud800\udc0"#, (17, true)),
        (br#"{"a":"\udc00"}"#, (12, false)),
        (br#"{"a":"\udc00"#, (12, false)),
    ] {
        assert_eq!(syntax_error(input), expected, "{}", input.escape_ascii());
    }
    assert_eq!(parse(br#""\uD83D\uDE00""#).unwrap(), "😀");
    assert_eq!(parse(br#""\ud83d\uDe00\u00e9\/""#).unwrap(), "😀é/");
}
#[test]
fn utf8_sequences_fail_at_the_first_byte_out_of_range() {
    for (input, expected) in [
        (b"{\"x\":\"\xc3\"}".as_slice(), (7, false)),
        (b"{\"x\":\"\xc3", (7, true)),
        (b"\"\xc0\x80\"", (1, false)),
        (b"\"\xc1\xbf\"", (1, false)),
        (b"\"\x80\"", (1, false)),
        (b"\"\xf5\x80\x80\x80\"", (1, false)),
        (b"\"\xff\"", (1, false)),
        // E0 and F0 guard against overlong forms, ED against surrogate
        // halves and F4 against code points past U+10FFFF.
        (b"\"\xe0\x9f\xbf\"", (2, false)),
        (b"\"\xed\xa0\x80\"", (2, false)),
        (b"\"\xf0\x8f\xbf\xbf\"", (2, false)),
        (b"\"\xf4\x90\x80\x80\"", (2, false)),
        (b"\"\xe2\x82\x28\"", (3, false)),
        (b"\"\xf0\x9f\x98\x28\"", (4, false)),
        (b"\"\xe2\x82", (3, true)),
        (b"\"\xf0\x9f\x98", (4, true)),
    ] {
        assert_eq!(syntax_error(input), expected, "{}", input.escape_ascii());
    }
    for (input, expected) in [
        (b"\"\xe0\xa0\x80\"".as_slice(), "\u{800}"),
        (b"\"\xed\x9f\xbf\"", "\u{d7ff}"),
        (b"\"\xee\x80\x80\"", "\u{e000}"),
        (b"\"\xf0\x90\x80\x80\"", "\u{10000}"),
        (b"\"\xf4\x8f\xbf\xbf\"", "\u{10ffff}"),
        (b"\"caf\xc3\xa9 \xf0\x9f\x98\x80\"", "café 😀"),
    ] {
        assert_eq!(parse(input).unwrap(), expected);
    }
}
#[test]
fn describe_reports_std_json_line_column_and_byte() {
    let text = "{\n\"a\":\"\\q\"}";
    let error = parse(text.as_bytes()).unwrap_err();
    assert_eq!(
        error.describe(text),
        "syntax error: line 2 column 7 (byte 8)"
    );
    let text = "{\"a\":\"\\";
    let error = parse(text.as_bytes()).unwrap_err();
    assert_eq!(
        error.describe(text),
        "unexpected end of input: line 1 column 8 (byte 7)"
    );
}
