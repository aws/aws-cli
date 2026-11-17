use super::*;

#[test]
fn insensitive_collection_preserves_first_spelling_and_last_value_including_empty() {
    let values = collect(
        [
            ("HTTP_PROXY".into(), "upper".into()),
            ("http_proxy".into(), "".into()),
            ("No_Proxy".into(), "localhost".into()),
        ],
        str::eq_ignore_ascii_case,
    );
    assert_eq!(values.len(), 2);
    assert_eq!(
        values.keys().map(String::as_str).collect::<Vec<_>>(),
        ["HTTP_PROXY", "No_Proxy"]
    );
    assert_eq!(
        get(&values, "HtTp_PrOxY", str::eq_ignore_ascii_case).map(String::as_str),
        Some("")
    );
    assert_eq!(
        get(&values, "no_proxy", str::eq_ignore_ascii_case).map(String::as_str),
        Some("localhost")
    );
    assert_eq!(get(&values, "missing", str::eq_ignore_ascii_case), None);
}

#[test]
fn nt_comparison_uses_simple_bmp_mapping_without_expansion_or_supplementary_folding() {
    let upcase = |value| match value {
        0x0061..=0x007a | 0x0430..=0x044f => value - 32,
        0x0250 => 0x2c6f,
        _ => value,
    };
    for (left, right, expected) in [
        ("HTTP_PROXY", "http_proxy", true),
        ("КИРиллИЦА", "кириллица", true),
        ("ɐ", "Ɐ", true),
        ("ß", "SS", false),
        ("𐐀", "𐐨", false),
        ("x", "xx", false),
        ("", "", true),
    ] {
        assert_eq!(names_equal_with(left, right, upcase), expected);
    }
}

#[test]
fn snapshot_preserves_native_case_semantics() {
    use crate::{EnvMap, SnapshotEnv};
    let snapshot = SnapshotEnv::from_pairs([("HTTP_PROXY", "upper"), ("http_proxy", "")]);
    assert_eq!(snapshot.var("http_proxy"), Some(""));
    assert_eq!(
        snapshot.var("HTTP_PROXY"),
        Some(if cfg!(windows) { "" } else { "upper" })
    );
    assert_eq!(snapshot.names().len(), if cfg!(windows) { 1 } else { 2 });
}
