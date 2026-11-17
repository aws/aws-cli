use super::*;

#[test]
fn ascii_text_is_written_as_cpython_writes_it() {
    for (value, expected) in [
        ("1.5", "'1.5'"),
        ("", "''"),
        ("it's", r#""it's""#),
        ("\x1c4", r"'\x1c4'"),
        ("a\tb\\", r"'a\tb\\'"),
    ] {
        assert_eq!(text(value), expected);
    }
}
