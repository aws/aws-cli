use super::*;

#[test]
fn separators_and_a_drive_end_the_part_that_names_the_extension() {
    for (path, name) in [
        (b"report.txt".as_slice(), b"report.txt".as_slice()),
        (br"C:\dir\report.txt", b"report.txt"),
        (br"dir/sub\report.txt", b"report.txt"),
        (br"dir\.txt", b".txt"),
        (b"C:.txt", b".txt"),
        ("\u{e9}:.txt".as_bytes(), b".txt"),
        (b"\xed\xa0\x80:.txt", b".txt"),
        ("\u{20000}:.txt".as_bytes(), "\u{20000}:.txt".as_bytes()),
    ] {
        assert_eq!(file_name(path), name, "{path:?}");
    }
}

#[test]
fn special_roots_and_normalization_stay_with_python() {
    for path in [
        r"\\?\C:\..\out.txt",
        r"\\?\UNC\server\share\..\out.txt",
        r"\\.\C:\out.txt",
        r"\\server\share\out.txt",
        "D:foo",
        "D:",
        r"\foo",
        "/foo",
        r"..\file",
        "dir/../file",
        r"C:\..\file",
        "file. ",
        r"dir.\file",
        "NUL.txt",
        "con",
        "COM1",
        "LPT\u{b2}",
        "dir/a:b",
        "//[foo/report.txt",
        "blocker/../dir",
        "out/../dir/",
    ] {
        assert!(!supports(path.as_bytes()), "{path:?}");
    }
    for path in [r"file.txt", r".\dir/file", r"C:\dir\file", "c:/dir/", "."] {
        assert!(supports(path.as_bytes()), "{path:?}");
    }
}

#[test]
fn admitted_operands_retain_the_drive_spelling() {
    for (cwd, path, expected) in [
        (r"c:\work", "file.txt", r"c:\work\file.txt"),
        (r"c:\work", r".\dir//file", r"c:\work\dir\file"),
        (r"c:\work", "d:/dir/file", r"d:\dir\file"),
        (r"c:\work", r"C:\dir\", r"C:\dir"),
        (r"c:\", "file", r"c:\file"),
        (
            r"\\server\share\dir",
            r"sub\file",
            r"\\server\share\dir\sub\file",
        ),
    ] {
        assert_eq!(
            absolute_path(cwd.as_bytes(), path.as_bytes()),
            expected.as_bytes(),
            "{cwd:?} {path:?}"
        );
    }
}

#[test]
fn a_path_made_absolute_comes_back_unchanged() {
    for path in [
        r"c:\work\file.txt",
        r"C:\",
        r"\\server\share\dir\sub\file",
        r"\\server\share\",
    ] {
        for cwd in ["", r"c:\work", r"\\server\share\dir"] {
            assert_eq!(
                absolute_path(cwd.as_bytes(), path.as_bytes()),
                path.as_bytes(),
                "{cwd:?} {path:?}"
            );
        }
    }
}

#[test]
fn dir_name_is_ntpath_dirname_of_admitted_operands() {
    for (path, directory) in [
        ("a.txt", ""),
        (r"dir\a.txt", "dir"),
        ("dir/a.txt", "dir"),
        (r"dir\\a.txt", "dir"),
        (r"C:\a.txt", r"C:\"),
        (r"C:\dir\a.txt", r"C:\dir"),
        (r"C:\dir\\a.txt", r"C:\dir"),
        (r"C:\", r"C:\"),
        (r"dir\", "dir"),
        ("", ""),
        (r"a\b/c", r"a\b"),
    ] {
        assert_eq!(dir_name(path.as_bytes()), directory.as_bytes(), "{path:?}");
    }
}
