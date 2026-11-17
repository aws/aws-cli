use super::*;
#[test]
fn suggestions_match_aws_cli_choice_tables() {
    let outputs = ["json", "text", "table", "yaml", "yaml-stream", "off"];
    for (word, expected) in [
        ("jsn", vec!["json"]),
        ("jsonn", vec!["json"]),
        ("yaml-strea", vec!["yaml-stream"]),
        ("yml", vec!["yaml"]),
        ("tabl", vec!["table"]),
        ("", vec![]),
        ("jsön", vec![]),
        ("jsoñn", vec!["json"]),
    ] {
        assert_eq!(close_matches(word.as_bytes(), &outputs), expected);
    }
    let commands = [
        "ls", "website", "cp", "mv", "rm", "sync", "mb", "rb", "presign",
    ];
    for (word, expected) in [
        ("sycn", vec![]),
        ("synk", vec![]),
        ("presgn", vec!["presign"]),
        ("webiste", vec!["website"]),
    ] {
        assert_eq!(close_matches(word.as_bytes(), &commands), expected);
    }
    for (word, choices, expected) in [
        ("o", vec!["on", "off", "auto"], vec![]),
        ("ofF", vec!["on", "off", "auto"], vec![]),
        ("aut", vec!["on", "off", "auto"], vec!["auto"]),
        ("AES256 ", vec!["AES256", "aws:kms"], vec!["AES256"]),
        ("aws:kmss", vec!["AES256", "aws:kms"], vec!["aws:kms"]),
        ("REPLACE", vec!["COPY", "REPLACE"], vec!["REPLACE"]),
        ("replace", vec!["COPY", "REPLACE"], vec![]),
        ("COPY1", vec!["COPY", "REPLACE"], vec!["COPY"]),
        ("requster", vec!["requester"], vec!["requester"]),
    ] {
        assert_eq!(close_matches(word.as_bytes(), &choices), expected);
    }
    let acls = [
        "private",
        "public-read",
        "public-read-write",
        "authenticated-read",
        "aws-exec-read",
        "bucket-owner-read",
        "bucket-owner-full-control",
        "log-delivery-write",
    ];
    assert!(close_matches(b"private-read", &acls).is_empty());
    assert_eq!(
        close_matches(b"bucket-owner-rea", &acls),
        ["bucket-owner-read"]
    );
}
#[test]
fn code_points_and_surrogate_escaped_bytes() {
    assert_eq!(close_matches(b"\xe2\x82json", &["json"]), ["json"]);
    assert_eq!(
        decode(b"a\xe2\x82\xff\xc3\xa9\xed\xa0\x80"),
        [97, 0xdce2, 0xdc82, 0xdcff, 0xe9, 0xdced, 0xdca0, 0xdc80]
    );
}
#[test]
fn an_empty_choice_matches_only_an_empty_word() {
    assert_eq!(close_matches(b"json", &["", "json"]), ["json"]);
    assert!(close_matches(b"jsn", &[""]).is_empty());
    assert_eq!(close_matches(b"", &["", "json"]), [""]);
}
#[test]
fn ties_order_by_greater_string_and_stop_at_three() {
    assert_eq!(
        close_matches(b"abc", &["abcd", "abce", "abcf", "abcg"]),
        ["abcg", "abcf", "abce"]
    );
    assert_eq!(
        close_matches(b"abc", &["abcd", "abce", "abc", "xabc"]),
        ["abc", "xabc", "abce"]
    );
}
#[test]
fn long_words_apply_popular_element_heuristic() {
    let ab = "ab".repeat(120);
    let ba = "ba".repeat(118);
    let longer = "ab".repeat(130);
    let suffixed = format!("{ab}c");
    assert_eq!(
        close_matches(ab.as_bytes(), &["abab", &ba, &longer, &suffixed]),
        [suffixed.as_str(), longer.as_str()]
    );
    let many = "a".repeat(300);
    let short = "a".repeat(299);
    let shorter = "a".repeat(250);
    let shifted = format!("b{short}");
    assert_eq!(
        close_matches(many.as_bytes(), &[&short, &shorter, &shifted]),
        [short.as_str(), shorter.as_str()]
    );
    let outputs = ["json", "text", "table", "yaml", "yaml-stream", "off"];
    assert!(close_matches(format!("{}json", "x".repeat(250)).as_bytes(), &outputs).is_empty());
    assert!(close_matches(format!("json{}", "a".repeat(300)).as_bytes(), &outputs).is_empty());
}
