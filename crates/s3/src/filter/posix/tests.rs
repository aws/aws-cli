use super::*;

fn units(text: &str) -> Vec<Unit> {
    text.chars().map(Unit::from).collect()
}

fn decode(bytes: &[u8]) -> Vec<Unit> {
    let mut units = Vec::new();
    decode_into(bytes, &mut units);
    units
}

#[test]
fn decode_escapes_each_byte_that_is_not_utf8() {
    assert_eq!(decode("a\u{e9}".as_bytes()), [0x61, 0xe9]);
    assert_eq!(
        decode(b"\xff\xed\xa0\x80"),
        [0xdcff, 0xdced, 0xdca0, 0xdc80]
    );
    let mut units = vec![0x2f];
    decode_into(b"a\xff", &mut units);
    assert_eq!(units, [0x2f, 0x61, 0xdcff]);
}

#[test]
fn join_joins_as_posixpath() {
    for (root, pattern, joined) in [
        ("/src", "a.txt", "/src/a.txt"),
        ("/", "a.txt", "/a.txt"),
        ("//", "a.txt", "//a.txt"),
        ("bucket/", "a.txt", "bucket/a.txt"),
        ("bucket/tree", "a.txt", "bucket/tree/a.txt"),
        ("/src", "/abs/*", "/abs/*"),
        ("/src", "", "/src/"),
        ("", "a.txt", "a.txt"),
        ("/src", "./a.txt", "/src/./a.txt"),
    ] {
        assert_eq!(
            join(&units(root), &units(pattern)),
            units(joined),
            "{root:?} {pattern:?}"
        );
    }
}
