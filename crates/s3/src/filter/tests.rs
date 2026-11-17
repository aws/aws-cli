use super::*;
use FilterKind::{Exclude, Include};

fn units(text: &str) -> Vec<Unit> {
    text.chars().map(Unit::from).collect()
}

const NAMES: &[&str] = &[
    "", "a", "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "ab",
    "abc", "aXbYc", "acb", "a.txt", ".txt", "aa", "a/b", "/", "é", "ê", "aé", "*", "?", "]a", "a]",
    "x]", "[x]", "[x", "ba", "y",
];
const FNMATCH: &[(&str, &[&str])] = &[
    ("", &[""]),
    (
        "*",
        &[
            "", "a", "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^",
            "ab", "abc", "aXbYc", "acb", "a.txt", ".txt", "aa", "a/b", "/", "é", "ê", "aé", "*",
            "?", "]a", "a]", "x]", "[x]", "[x", "ba", "y",
        ],
    ),
    (
        "**",
        &[
            "", "a", "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^",
            "ab", "abc", "aXbYc", "acb", "a.txt", ".txt", "aa", "a/b", "/", "é", "ê", "aé", "*",
            "?", "]a", "a]", "x]", "[x]", "[x", "ba", "y",
        ],
    ),
    (
        "?",
        &[
            "a", "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/",
            "é", "ê", "*", "?", "y",
        ],
    ),
    ("a", &["a"]),
    (
        "a*",
        &[
            "a", "ab", "abc", "aXbYc", "acb", "a.txt", "aa", "a/b", "aé", "a]",
        ],
    ),
    ("*a", &["a", "aa", "]a", "ba"]),
    (
        "*a*",
        &[
            "a", "ab", "abc", "aXbYc", "acb", "a.txt", "aa", "a/b", "aé", "]a", "a]", "ba",
        ],
    ),
    ("a*b", &["ab", "acb", "a/b"]),
    ("a*b*c", &["abc", "aXbYc"]),
    ("*.txt", &["a.txt", ".txt"]),
    ("?.txt", &["a.txt"]),
    ("??", &["ab", "aa", "aé", "]a", "a]", "x]", "[x", "ba"]),
    ("a?c", &["abc"]),
    ("[ab]", &["a", "b"]),
    (
        "[!ab]",
        &[
            "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/", "é", "ê",
            "*", "?", "y",
        ],
    ),
    ("[a-c]", &["a", "b", "c"]),
    (
        "[!a-c]",
        &[
            "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/", "é", "ê", "*",
            "?", "y",
        ],
    ),
    ("[]]", &["]"]),
    (
        "[!]]",
        &[
            "a", "b", "c", "d", "e", "x", "z", "-", "!", "[", "\\", "&", "~", "|", "^", "/", "é",
            "ê", "*", "?", "y",
        ],
    ),
    ("[]a]", &["a", "]"]),
    (
        "[!]a]",
        &[
            "b", "c", "d", "e", "x", "z", "-", "!", "[", "\\", "&", "~", "|", "^", "/", "é", "ê",
            "*", "?", "y",
        ],
    ),
    ("[]-a]", &["a", "]", "^"]),
    ("[a-]", &["a", "-"]),
    ("[-a]", &["a", "-"]),
    (
        "[!-a]",
        &[
            "b", "c", "d", "e", "x", "z", "!", "]", "[", "\\", "&", "~", "|", "^", "/", "é", "ê",
            "*", "?", "y",
        ],
    ),
    ("[z-a]", &[]),
    (
        "[!z-a]",
        &[
            "a", "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/",
            "é", "ê", "*", "?", "y",
        ],
    ),
    (
        "[z-a!]",
        &[
            "a", "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/",
            "é", "ê", "*", "?", "y",
        ],
    ),
    (
        "[z-a!x]",
        &[
            "a", "b", "c", "d", "e", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/", "é",
            "ê", "*", "?", "y",
        ],
    ),
    ("[a-c-e]", &["a", "b", "c", "e", "-"]),
    ("[a-cx-z]", &["a", "b", "c", "x", "z", "y"]),
    ("[x-ab-c]", &["b", "c"]),
    (
        "[!x-ab-c]",
        &[
            "a", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/", "é", "ê",
            "*", "?", "y",
        ],
    ),
    (
        "[!z-ab-c]",
        &[
            "a", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/", "é", "ê",
            "*", "?", "y",
        ],
    ),
    ("[[]", &["["]),
    ("[[]x]", &["[x]"]),
    ("[x", &["[x"]),
    ("[x*", &["[x]", "[x"]),
    ("[!", &[]),
    ("[!]", &[]),
    ("[]", &[]),
    ("[\\]", &["\\"]),
    (
        "[\\-z]",
        &["a", "b", "c", "d", "e", "x", "z", "]", "\\", "^", "y"],
    ),
    ("[a\\]", &["a", "\\"]),
    ("[&&]", &["&"]),
    ("[a&&b]", &["a", "b", "&"]),
    ("[~~]", &["~"]),
    ("[||]", &["|"]),
    ("[^a]", &["a", "^"]),
    ("[a^]", &["a", "^"]),
    ("[--a]", &["a", "-", "]", "[", "\\", "^", "/", "?"]),
    ("[a--]", &[]),
    (
        "[!--]",
        &[
            "a", "b", "c", "d", "e", "x", "z", "!", "]", "[", "\\", "&", "~", "|", "^", "/", "é",
            "ê", "*", "?", "y",
        ],
    ),
    ("[a-c][!a]", &["ab", "aé", "a]"]),
    (
        "*[ab]*",
        &[
            "a", "b", "ab", "abc", "aXbYc", "acb", "a.txt", "aa", "a/b", "aé", "]a", "a]", "ba",
        ],
    ),
    ("\\*", &["\\"]),
    ("a\\", &[]),
    ("[é-ê]", &["é", "ê"]),
    ("?é", &["aé"]),
    (
        "[!é]",
        &[
            "a", "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "/",
            "ê", "*", "?", "y",
        ],
    ),
    ("*/*", &["a/b", "/"]),
    ("a/?", &["a/b"]),
    ("[/]", &["/"]),
    ("[a-a]", &["a"]),
    ("[b-a-c]", &["c", "-"]),
    ("[a-]]", &["a]"]),
    ("[[a-c]", &["a", "b", "c", "["]),
    (
        "[!!]",
        &[
            "a", "b", "c", "d", "e", "x", "z", "-", "]", "[", "\\", "&", "~", "|", "^", "/", "é",
            "ê", "*", "?", "y",
        ],
    ),
    (
        "[!!-a]",
        &["b", "c", "d", "e", "x", "z", "~", "|", "é", "ê", "y"],
    ),
    ("[*]", &["*"]),
    ("[?]", &["?"]),
    (
        "*[!a]",
        &[
            "b", "c", "d", "e", "x", "z", "-", "!", "]", "[", "\\", "&", "~", "|", "^", "ab",
            "abc", "aXbYc", "acb", "a.txt", ".txt", "a/b", "/", "é", "ê", "aé", "*", "?", "a]",
            "x]", "[x]", "[x", "y",
        ],
    ),
];

#[test]
fn patterns_match_as_cpython_fnmatchcase() {
    for (pattern, matched) in FNMATCH {
        let compiled = compile(&units(pattern));
        for name in NAMES {
            assert_eq!(
                matches(&compiled, &units(name)),
                matched.contains(name),
                "{pattern:?} against {name:?}"
            );
        }
    }
}

#[test]
fn ranges_order_surrogates_among_code_points() {
    let compiled = compile(&units("[\u{d7ff}-\u{e000}].txt"));
    assert!(matches(&compiled, &[0xdcff, 0x2e, 0x74, 0x78, 0x74]));
    assert!(!matches(&compiled, &units("a.txt")));
}

fn filter_of(filters: &[(FilterKind, &str)], roots: [&str; 2], prefix: &str) -> Filter {
    let filters: Vec<_> = filters
        .iter()
        .map(|&(kind, pattern)| (kind, pattern.to_owned()))
        .collect();
    let [source, destination] = roots.map(str::as_bytes);
    Filter::new(
        &filters,
        Roots {
            source,
            destination,
        },
        prefix.as_bytes(),
    )
}

#[test]
fn filter_kinds_are_named_by_their_options() {
    assert_eq!(FilterKind::try_from("--include"), Ok(Include));
    assert_eq!(FilterKind::try_from("--exclude"), Ok(Exclude));
    assert_eq!(FilterKind::try_from("--inc"), Err(UnknownFilterOption));
}

#[test]
fn no_filter_includes_everything() {
    assert!(Filter::default().includes(b"anything"));
    assert!(filter_of(&[], ["/src", "bucket/"], "/src/").includes(b"a.txt"));
}

#[test]
fn the_last_matching_pattern_decides() {
    let roots = ["bucket/tree", "/out"];
    let filter = filter_of(
        &[(Exclude, "*"), (Include, "*.txt"), (Exclude, "nested/*")],
        roots,
        "bucket/",
    );
    for (key, included) in [
        ("tree/a.txt", true),
        ("tree/a.bin", false),
        ("tree/nested/b.txt", false),
        ("tree/deeper/nested/b.txt", true),
    ] {
        assert_eq!(filter.includes(key.as_bytes()), included, "{key}");
    }
}

#[cfg(not(windows))]
mod posix_paths {
    use super::*;

    #[test]
    fn patterns_are_rooted_at_the_source() {
        let filter = filter_of(&[(Exclude, "a.txt")], ["/src", "bucket/prefix/"], "/src/");
        assert!(!filter.includes(b"a.txt"));
        assert!(filter.includes(b"nested/a.txt"));
        let filter = filter_of(&[(Exclude, "/src/nested/*")], ["/src", "bucket/"], "/src/");
        assert!(filter.includes(b"a.txt"));
        assert!(!filter.includes(b"nested/a.txt"));
    }

    #[test]
    fn a_root_walk_names_its_files_after_two_slashes() {
        let filter = filter_of(
            &[(Exclude, "*"), (Include, "etc/*")],
            ["/", "bucket/"],
            "//",
        );
        assert!(!filter.includes(b"etc/passwd"));
    }

    #[test]
    fn patterns_are_also_rooted_at_the_destination() {
        let filter = filter_of(&[(Exclude, "*.txt")], ["/src", "/dst"], "");
        assert!(!filter.includes(b"/src/a.txt"));
        assert!(!filter.includes(b"/dst/a.txt"));
        assert!(filter.includes(b"/elsewhere/a.txt"));
    }

    #[test]
    fn a_name_that_is_not_utf8_matches_as_its_escapes() {
        let filter = filter_of(&[(Exclude, "?.txt")], ["/src", "bucket/"], "/src/");
        assert!(!filter.includes(b"\xff.txt"));
        assert!(filter.includes(b"\xff\xfe.txt"));
    }

    #[test]
    fn case_is_significant() {
        let filter = filter_of(&[(Exclude, "A.TXT")], ["/src", "bucket/"], "/src/");
        assert!(filter.includes(b"a.txt"));
        assert!(!filter.includes(b"A.TXT"));
    }
}

#[cfg(windows)]
mod windows_paths {
    use super::*;

    #[test]
    fn case_and_separators_fold() {
        let filter = filter_of(
            &[(Exclude, "Nested/A.TXT")],
            ["C:\\src", "bucket/"],
            "C:\\src\\",
        );
        assert!(!filter.includes(b"nested\\a.txt"));
        let filter = filter_of(
            &[(Exclude, "Nested/A.TXT")],
            ["bucket/tree", "C:\\out"],
            "bucket/",
        );
        assert!(!filter.includes(b"tree/nested/a.txt"));
    }
}
