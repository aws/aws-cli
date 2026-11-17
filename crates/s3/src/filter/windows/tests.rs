use super::*;

fn units(text: &str) -> Vec<Unit> {
    text.chars().map(Unit::from).collect()
}

fn decode(bytes: &[u8]) -> Vec<Unit> {
    let mut units = Vec::new();
    decode_into(bytes, &mut units);
    units
}

fn text(units: &[Unit]) -> String {
    units
        .iter()
        .map(|&unit| char::from_u32(unit).unwrap_or(char::REPLACEMENT_CHARACTER))
        .collect()
}

const JOINS: &[(&str, &str, &str)] = &[
    ("C:\\x\\src", "a.txt", "C:\\x\\src\\a.txt"),
    ("C:\\x\\src", "/a", "C:/a"),
    ("C:\\x\\src", "\\a", "C:\\a"),
    ("C:\\x\\src", "C:a", "C:\\x\\src\\a"),
    ("C:\\x\\src", "c:a", "c:\\x\\src\\a"),
    ("C:\\x\\src", "D:a", "D:a"),
    ("C:\\x\\src", "D:\\a", "D:\\a"),
    ("C:\\x\\src", "\\\\h\\s\\a", "\\\\h\\s\\a"),
    ("C:\\x\\src", "\\\\h\\s", "\\\\h\\s"),
    ("C:\\x\\src", "\\\\?\\UNC\\h\\s\\a", "\\\\?\\UNC\\h\\s\\a"),
    ("C:\\x\\src", "", "C:\\x\\src\\"),
    ("C:\\x\\src", "?:*", "?:*"),
    ("C:\\x\\src", "É:a", "É:a"),
    ("C:\\x\\src", "\u{20000}:a", "C:\\x\\src\\\u{20000}:a"),
    ("C:\\", "a.txt", "C:\\a.txt"),
    ("C:\\", "/a", "C:/a"),
    ("C:\\", "\\a", "C:\\a"),
    ("C:\\", "C:a", "C:\\a"),
    ("C:\\", "c:a", "c:\\a"),
    ("C:\\", "D:a", "D:a"),
    ("C:\\", "D:\\a", "D:\\a"),
    ("C:\\", "\\\\h\\s\\a", "\\\\h\\s\\a"),
    ("C:\\", "\\\\h\\s", "\\\\h\\s"),
    ("C:\\", "\\\\?\\UNC\\h\\s\\a", "\\\\?\\UNC\\h\\s\\a"),
    ("C:\\", "", "C:\\"),
    ("C:\\", "?:*", "?:*"),
    ("C:\\", "É:a", "É:a"),
    ("C:\\", "\u{20000}:a", "C:\\\u{20000}:a"),
    (
        "\\\\server\\share\\dir",
        "a.txt",
        "\\\\server\\share\\dir\\a.txt",
    ),
    ("\\\\server\\share\\dir", "/a", "\\\\server\\share/a"),
    ("\\\\server\\share\\dir", "\\a", "\\\\server\\share\\a"),
    ("\\\\server\\share\\dir", "C:a", "C:a"),
    ("\\\\server\\share\\dir", "c:a", "c:a"),
    ("\\\\server\\share\\dir", "D:a", "D:a"),
    ("\\\\server\\share\\dir", "D:\\a", "D:\\a"),
    ("\\\\server\\share\\dir", "\\\\h\\s\\a", "\\\\h\\s\\a"),
    ("\\\\server\\share\\dir", "\\\\h\\s", "\\\\h\\s"),
    (
        "\\\\server\\share\\dir",
        "\\\\?\\UNC\\h\\s\\a",
        "\\\\?\\UNC\\h\\s\\a",
    ),
    ("\\\\server\\share\\dir", "", "\\\\server\\share\\dir\\"),
    ("\\\\server\\share\\dir", "?:*", "?:*"),
    ("\\\\server\\share\\dir", "É:a", "É:a"),
    (
        "\\\\server\\share\\dir",
        "\u{20000}:a",
        "\\\\server\\share\\dir\\\u{20000}:a",
    ),
    ("\\\\server\\share", "a.txt", "\\\\server\\share\\a.txt"),
    ("\\\\server\\share", "/a", "\\\\server\\share/a"),
    ("\\\\server\\share", "\\a", "\\\\server\\share\\a"),
    ("\\\\server\\share", "C:a", "C:a"),
    ("\\\\server\\share", "c:a", "c:a"),
    ("\\\\server\\share", "D:a", "D:a"),
    ("\\\\server\\share", "D:\\a", "D:\\a"),
    ("\\\\server\\share", "\\\\h\\s\\a", "\\\\h\\s\\a"),
    ("\\\\server\\share", "\\\\h\\s", "\\\\h\\s"),
    (
        "\\\\server\\share",
        "\\\\?\\UNC\\h\\s\\a",
        "\\\\?\\UNC\\h\\s\\a",
    ),
    ("\\\\server\\share", "", "\\\\server\\share"),
    ("\\\\server\\share", "?:*", "?:*"),
    ("\\\\server\\share", "É:a", "É:a"),
    (
        "\\\\server\\share",
        "\u{20000}:a",
        "\\\\server\\share\\\u{20000}:a",
    ),
    ("bucket/tree", "a.txt", "bucket/tree\\a.txt"),
    ("bucket/tree", "/a", "/a"),
    ("bucket/tree", "\\a", "\\a"),
    ("bucket/tree", "C:a", "C:a"),
    ("bucket/tree", "c:a", "c:a"),
    ("bucket/tree", "D:a", "D:a"),
    ("bucket/tree", "D:\\a", "D:\\a"),
    ("bucket/tree", "\\\\h\\s\\a", "\\\\h\\s\\a"),
    ("bucket/tree", "\\\\h\\s", "\\\\h\\s"),
    ("bucket/tree", "\\\\?\\UNC\\h\\s\\a", "\\\\?\\UNC\\h\\s\\a"),
    ("bucket/tree", "", "bucket/tree\\"),
    ("bucket/tree", "?:*", "?:*"),
    ("bucket/tree", "É:a", "É:a"),
    ("bucket/tree", "\u{20000}:a", "bucket/tree\\\u{20000}:a"),
    ("bucket/", "a.txt", "bucket/a.txt"),
    ("bucket/", "/a", "/a"),
    ("bucket/", "\\a", "\\a"),
    ("bucket/", "C:a", "C:a"),
    ("bucket/", "c:a", "c:a"),
    ("bucket/", "D:a", "D:a"),
    ("bucket/", "D:\\a", "D:\\a"),
    ("bucket/", "\\\\h\\s\\a", "\\\\h\\s\\a"),
    ("bucket/", "\\\\h\\s", "\\\\h\\s"),
    ("bucket/", "\\\\?\\UNC\\h\\s\\a", "\\\\?\\UNC\\h\\s\\a"),
    ("bucket/", "", "bucket/"),
    ("bucket/", "?:*", "?:*"),
    ("bucket/", "É:a", "É:a"),
    ("bucket/", "\u{20000}:a", "bucket/\u{20000}:a"),
];
const ROOTS: &[(&str, [&str; 3])] = &[
    ("", ["", "", ""]),
    ("a", ["", "", "a"]),
    ("\\a", ["", "\\", "a"]),
    ("/a", ["", "/", "a"]),
    ("\\/a", ["\\/a", "", ""]),
    ("C:", ["C:", "", ""]),
    ("C:a", ["C:", "", "a"]),
    ("C:\\a", ["C:", "\\", "a"]),
    ("é:/a", ["é:", "/", "a"]),
    ("\u{20000}:a", ["", "", "\u{20000}:a"]),
    ("\u{20000}:\\a", ["", "", "\u{20000}:\\a"]),
    ("\\\\h", ["\\\\h", "", ""]),
    ("\\\\h\\s", ["\\\\h\\s", "", ""]),
    ("\\\\h\\s\\a", ["\\\\h\\s", "\\", "a"]),
    ("//h/s/a", ["//h/s", "/", "a"]),
    ("\\\\\u{20000}\\s\\a", ["\\\\\u{20000}\\s", "\\", "a"]),
    ("\\\\.\\dev", ["\\\\.\\dev", "", ""]),
    ("\\\\?\\c:\\a", ["\\\\?\\c:", "\\", "a"]),
    ("\\\\?\\UNC\\h\\s\\a", ["\\\\?\\UNC\\h\\s", "\\", "a"]),
    ("\\\\?\\unc\\h", ["\\\\?\\unc\\h", "", ""]),
    ("\\\\?\\UNCX\\h\\s", ["\\\\?\\UNCX", "\\", "h\\s"]),
    ("\\\\?\\UNC\\", ["\\\\?\\UNC\\", "", ""]),
    ("\\\\", ["\\\\", "", ""]),
];

#[test]
fn split_root_splits_as_ntpath() {
    for (path, [drive, root, tail]) in ROOTS {
        let (drive_len, root_len) = split_root(&units(path));
        let path = units(path);
        let (got_drive, rest) = path.split_at(drive_len);
        let (got_root, got_tail) = rest.split_at(root_len);
        assert_eq!(
            [text(got_drive), text(got_root), text(got_tail)],
            [*drive, *root, *tail],
            "{}",
            text(&path)
        );
    }
    assert_eq!(split_root(&[0xd800, COLON, Unit::from(b'a')]), (2, 0));
}

#[test]
fn join_joins_as_ntpath() {
    for (root, pattern, joined) in JOINS {
        assert_eq!(
            text(&join(&units(root), &units(pattern))),
            *joined,
            "{root:?} {pattern:?}"
        );
    }
}

#[test]
fn decode_reads_wtf8() {
    assert_eq!(decode("a\u{e9}\u{1f600}".as_bytes()), [0x61, 0xe9, 0x1f600]);
    assert_eq!(
        decode(b"\xed\xa0\x80.txt"),
        [0xd800, 0x2e, 0x74, 0x78, 0x74]
    );
    let mut units = vec![0x5c];
    decode_into(b"a\xed\xa0\x80", &mut units);
    assert_eq!(units, [0x5c, 0x61, 0xd800]);
}

#[cfg(windows)]
#[test]
fn normcase_lowercases_with_backslashes() {
    assert_eq!(
        text(&normcase(&units("C:/Dir\\\u{c0}B.TXT"))),
        "c:\\dir\\\u{e0}b.txt"
    );
    assert_eq!(normcase(&[0xd800, 0x41]), [0xd800, 0x61]);
    assert_eq!(normcase(&[]), Vec::<Unit>::new());
}
