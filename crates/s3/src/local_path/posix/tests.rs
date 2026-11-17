use super::*;

#[test]
fn only_what_follows_the_last_slash_names_the_extension() {
    for (path, name) in [
        ("report.txt", "report.txt"),
        ("/x.y/z.txt", "z.txt"),
        ("dir/", ""),
        (r"dir\.txt", r"dir\.txt"),
        ("C:.txt", "C:.txt"),
    ] {
        assert_eq!(file_name(path.as_bytes()), name.as_bytes(), "{path:?}");
    }
}

#[test]
fn absolute_path_spells_a_path_as_cpython_s_abspath_does() {
    for (cwd, path, expected) in [
        ("/home/u", "report.txt", "/home/u/report.txt"),
        ("/home/u", "./a//b/../c.txt", "/home/u/a/c.txt"),
        ("/home/u", "../../../../x", "/x"),
        ("/", "a", "/a"),
        ("/", "../a", "/a"),
        ("/\n/[foo", "report.txt", "/\n/[foo/report.txt"),
        ("/home/u", "../../\n/[foo/report.txt", "/\n/[foo/report.txt"),
        ("/home/u", "//x", "//x"),
        ("", "/a/./b/../c", "/a/c"),
        ("", "//a/../[foo/x", "//[foo/x"),
        ("", "///a//b", "/a/b"),
        ("", "//./[foo/x", "//[foo/x"),
        ("", "//..", "//"),
        ("", "/..", "/"),
        ("", "//", "//"),
        ("", "/a/b/", "/a/b"),
    ] {
        assert_eq!(
            absolute_path(cwd.as_bytes(), path.as_bytes()),
            expected.as_bytes(),
            "{cwd:?} {path:?}"
        );
    }
}

#[test]
fn dir_name_is_posixpath_dirname() {
    for (path, directory) in [
        ("a.txt", ""),
        ("dir/a.txt", "dir"),
        ("dir//a.txt", "dir"),
        ("/a.txt", "/"),
        ("//a.txt", "//"),
        ("///a", "///"),
        ("/", "/"),
        ("dir/", "dir"),
        ("", ""),
        ("a/b/c", "a/b"),
        ("./a", "."),
    ] {
        assert_eq!(dir_name(path.as_bytes()), directory.as_bytes(), "{path:?}");
    }
}
