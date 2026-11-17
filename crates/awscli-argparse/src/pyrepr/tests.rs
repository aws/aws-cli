#![expect(clippy::unwrap_used, reason = "pinned test fixtures and assertions")]
use super::*;
fn json(text: &str) -> Value {
    crate::json::parse(text.as_bytes()).unwrap()
}
#[test]
fn quote_selection_escapes_and_unicode_passthrough() {
    assert_eq!(repr("a'b\n\0\\"), "\"a'b\\n\\x00\\\\\"");
    assert_eq!(repr("é\x7f"), "'é\\x7f'");
    let mut output = Vec::new();
    write(b"\xc3\xa9\xff\x80", &mut output);
    assert_eq!(String::from_utf8(output).unwrap(), "'é\\udcff\\udc80'");
}

#[test]
fn undecodable_bytes_count_and_print_as_surrogate_escapes() {
    for (text, count, written) in [
        (&b""[..], 0, ""),
        (b"js\xffon", 5, "js\\udcffon"),
        (b"\xc3\xa9\xff", 2, "é\\udcff"),
        (b"\xe2\x82a", 3, "\\udce2\\udc82a"),
        // UTF-8 never encodes a surrogate, so those bytes are three escapes.
        (b"\xed\xa0\x80", 3, "\\udced\\udca0\\udc80"),
    ] {
        assert_eq!(code_point_count(text), count, "{text:?}");
        assert_eq!(backslash_replaced(text), written, "{text:?}");
    }
}

#[test]
#[cfg(windows)]
fn argv_reprs_spell_an_unpaired_surrogate_by_its_encoded_bytes() {
    use std::os::windows::ffi::OsStringExt;
    let value = std::ffi::OsString::from_wide(&[0x61, 0xd800]);
    assert_eq!(argv(&value), "'a\\udced\\udca0\\udc80'");
    assert_eq!(
        backslash_replaced(value.as_encoded_bytes()),
        "a\\udced\\udca0\\udc80"
    );
}

#[test]
#[cfg(unix)]
fn os_repr_escapes_surrogateescaped_bytes_without_replacing_valid_unicode() {
    use std::os::unix::ffi::OsStrExt;
    assert_eq!(
        os(std::ffi::OsStr::from_bytes(b"a'\xff\n\xc3\xa9\xc3")),
        "\"a'\\udcff\\né\\udcc3\""
    );
    assert_eq!(
        os(std::ffi::OsStr::from_bytes(b"\xed\xa0\x80")),
        "'\\udced\\udca0\\udc80'"
    );
}

#[test]
#[cfg(windows)]
fn os_repr_retains_unpaired_surrogates_and_decodes_valid_pairs() {
    use std::os::windows::ffi::OsStringExt;
    let value = std::ffi::OsString::from_wide(&[0xd800, 0xd83d, 0xde00, 0xdcff]);
    assert_eq!(os(&value), "'\\ud800😀\\udcff'");
}
#[test]
fn precision_counts_code_points_of_rendered_repr() {
    for (input, limit, expected) in [
        ("abc", 200, "'abc'"),
        ("abc", 5, "'abc'"),
        ("abc", 4, "'abc"),
        ("abc", 1, "'"),
        ("abc", 0, ""),
        ("\0", 3, "'\\x"),
        ("\n\n", 4, "'\\n\\"),
        ("éé", 2, "'é"),
        ("☃x", 3, "'☃x"),
    ] {
        assert_eq!(limited(input, limit), expected);
    }
    assert_eq!(
        limited("x".repeat(250), 200),
        format!("'{}", "x".repeat(199))
    );
}
#[test]
#[cfg(unix)]
fn precision_counts_each_character_of_a_surrogate_escape() {
    use std::os::unix::ffi::OsStrExt;
    for (input, limit, expected) in [
        (&b"1\xff"[..], 200, "'1\\udcff'"),
        (b"\xff\xff", 9, "'\\udcff\\u"),
        (b"\x80x", 8, "'\\udc80x"),
    ] {
        assert_eq!(limited(std::ffi::OsStr::from_bytes(input), limit), expected);
    }
}
#[test]
fn nested_lists_and_dicts_use_python_separators() {
    for (input, ordered, expected) in [
        (json("[]"), false, "[]"),
        (json("{}"), false, "{}"),
        (json(r#"["x",65,null]"#), false, "['x', 65, None]"),
        (
            json(r#"{"b":"it's","c":[{}]}"#),
            false,
            "{'b': \"it's\", 'c': [{}]}",
        ),
        (json("[[true]]"), false, "[[True]]"),
        (json("{}"), true, "OrderedDict()"),
        (
            json(r#"{"a":{"b":[1]}}"#),
            true,
            "OrderedDict({'a': OrderedDict({'b': [1]})})",
        ),
    ] {
        let rendered = if ordered {
            input.repr()
        } else {
            value(&input, ordered)
        };
        assert_eq!(rendered, expected);
    }
}
#[test]
fn bytes_repr_escapes_everything_outside_printable_ascii() {
    assert_eq!(
        bytes(b"a'\xff\n\x7f\\\0~"),
        "b\"a'\\xff\\n\\x7f\\\\\\x00~\""
    );
    assert_eq!(bytes(b"q\"'"), "b'q\"\\''");
    assert_eq!(bytes(b""), "b''");
}
