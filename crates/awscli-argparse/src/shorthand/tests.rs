#![expect(clippy::unwrap_used, reason = "pinned test fixtures and assertions")]
use super::*;
#[test]
fn grammar_corpus_matches_reference_parser() {
    let cases: Value = crate::json::parse(include_bytes!("../testdata/shorthand.json")).unwrap();
    for case in cases.as_array().unwrap() {
        let input = case["input"].as_str().unwrap();
        if let Some(expected) = case["ok"].as_str() {
            let expected: Value = crate::json::parse(expected.as_bytes()).unwrap();
            assert_eq!(parse(input.as_bytes()), Ok(expected), "{input:?}");
        } else {
            assert_eq!(
                parse(input.as_bytes()),
                Err(ParseError::Syntax(case["err"].as_str().unwrap().into())),
                "{input:?}"
            );
        }
    }
}
#[test]
fn speculative_csv_failures_keep_only_final_values() {
    let input = (0..4000)
        .map(|i| format!("k{i}=v"))
        .collect::<Vec<_>>()
        .join(",");
    let value = parse(input.as_bytes()).unwrap();
    let pairs = value.as_object().unwrap();
    assert_eq!(pairs.len(), 4000);
    for (i, (key, value)) in pairs.iter().enumerate() {
        assert_eq!(key, &format!("k{i}"));
        assert_eq!(value, "v");
    }
}
#[test]
fn unsupported_inputs_are_refused_without_a_message() {
    for input in ["a@=b", "a @= b", "a=b,c@=file://x", "a={b@=c}"] {
        assert_eq!(parse(input.as_bytes()), Err(ParseError::Paramfile));
    }
    for bytes in [b"a=b\xff".as_slice(), b"a=\xed\xa0\x80"] {
        assert_eq!(parse(bytes), Err(ParseError::InvalidUtf8));
    }
    let deep = format!("a={}x{}", "[".repeat(33), "]".repeat(33));
    assert_eq!(parse(deep.as_bytes()), Err(ParseError::TooDeep));
    let deepest = format!("a={}x{}", "[".repeat(32), "]".repeat(32));
    assert_eq!(
        parse(deepest.as_bytes()).unwrap().to_string(),
        format!("{{\"a\":{}\"x\"{}}}", "[".repeat(32), "]".repeat(32))
    );
    let long = format!("a={}", "b".repeat(SHORTHAND_INPUT_BYTES_MAX - 1));
    assert_eq!(parse(long.as_bytes()), Err(ParseError::TooLong));
    assert_eq!(
        parse(&long.as_bytes()[..long.len() - 1]).unwrap()["a"]
            .as_str()
            .unwrap()
            .len(),
        SHORTHAND_INPUT_BYTES_MAX - 2
    );
}
#[test]
fn strip_helpers_use_python_whitespace() {
    assert_eq!(lstrip(" \t\u{a0}\u{3000}\x1cx"), "x");
    assert_eq!(rstrip("x\u{2028} \x1f\u{85}"), "x");
    assert_eq!(rstrip("\u{2000}\n"), "");
    assert_eq!(rstrip("x\u{2000}y"), "x\u{2000}y");
    assert_eq!(lstrip("\u{a0}{"), "{");
}
