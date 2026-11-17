#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;

#[cfg(unix)]
#[test]
fn recursive_paths_and_keys_preserve_non_unicode_root_and_relative_names() {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let root = normalize_local_directory_root(Path::new(OsStr::from_bytes(b"root-\xff")));
    assert_eq!(root.as_os_str().as_bytes(), b"root-\xff/");
    assert_eq!(
        build_recursive_destination_path(&root, "a/b")
            .as_os_str()
            .as_bytes(),
        b"root-\xff/a/b",
    );
    let relative = Path::new(OsStr::from_bytes(b"dir-\xfe/file-\xff"));
    assert_eq!(
        build_recursive_source_path(&root, relative)
            .as_os_str()
            .as_bytes(),
        b"root-\xff/dir-\xfe/file-\xff",
    );
    assert_eq!(
        build_recursive_upload_key(b"prefix/", relative),
        b"prefix/dir-\xfe/file-\xff"
    );
}
use std::sync::atomic::{AtomicU64, Ordering};
static NEXT: AtomicU64 = AtomicU64::new(0);
struct Directory(PathBuf);
impl Directory {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "s3-transfer-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
/// Link `link` to `target`; Windows needs to know whether `target` is a
/// directory. `false` when the host refuses symbolic links, as Windows does
/// without Developer Mode or elevation, so the caller skips.
fn symlink(target: &Path, link: &Path, directory: bool) -> bool {
    #[cfg(unix)]
    let linked = {
        let _ = directory;
        std::os::unix::fs::symlink(target, link)
    };
    #[cfg(windows)]
    let linked = if directory {
        std::os::windows::fs::symlink_dir(target, link)
    } else {
        std::os::windows::fs::symlink_file(target, link)
    };
    match linked {
        Err(error) if error.kind() == io::ErrorKind::PermissionDenied => false,
        linked => {
            linked.unwrap();
            true
        }
    }
}
// POSIX spellings: a Windows absolute path needs a drive, so these are
// skipped there.
#[cfg(unix)]
#[test]
fn display_paths_match_python_relpath() {
    for (path, expected) in [
        ("foo.txt", "./foo.txt"),
        ("./foo.txt", "./foo.txt"),
        ("/work/foo.txt", "./foo.txt"),
        ("sub/../foo.txt", "./foo.txt"),
        ("/work/sub/..", "sub/.."),
        ("/work/..", "./.."),
        ("/work/sub/.", "sub/."),
        ("..", "./.."),
        ("./sub/foo.txt", "sub/foo.txt"),
        ("sub/deep/foo.txt", "sub/deep/foo.txt"),
        ("../foo.txt", "../foo.txt"),
        ("/tmp/x/foo.txt", "../tmp/x/foo.txt"),
    ] {
        assert_eq!(
            display_local_path(Path::new("/work"), Path::new(path)),
            Path::new(expected)
        );
    }
    for (cwd, path, expected) in [
        ("/work/sub", "/work/foo.txt", "../foo.txt"),
        ("/", "/foo.txt", "./foo.txt"),
        ("/", "x/foo.txt", "x/foo.txt"),
        ("/a/b/c", "/foo.txt", "../../../foo.txt"),
        ("/a/b/c", "//d/foo.txt", "../../../d/foo.txt"),
        ("/a/b/c", "../../../foo.txt", "../../../foo.txt"),
    ] {
        assert_eq!(
            display_local_path(Path::new(cwd), Path::new(path)),
            Path::new(expected),
            "{cwd:?} {path:?}"
        );
    }
}
#[cfg(unix)]
#[test]
fn display_paths_keep_a_directory_sources_trailing_separator() {
    use std::os::unix::ffi::OsStrExt;
    for (path, expected) in [
        ("sub/dir/", "sub/dir/"),
        ("/work/dir//", "dir/"),
        ("/work/", "./"),
        ("/work/sub/../", "./"),
    ] {
        let display = display_local_path(Path::new("/work"), Path::new(path));
        assert_eq!(
            display.as_os_str().as_bytes(),
            expected.as_bytes(),
            "{path:?}"
        );
    }
}
#[cfg(unix)]
#[test]
fn display_paths_spell_the_root_with_a_trailing_separator() {
    use std::os::unix::ffi::OsStrExt;
    for (cwd, expected) in [("/home/u", "../../"), ("/a/b/c", "../../../"), ("/", "./")] {
        let display = display_local_path(Path::new(cwd), Path::new("/"));
        assert_eq!(
            display.as_os_str().as_bytes(),
            expected.as_bytes(),
            "{cwd:?}"
        );
    }
}
#[test]
fn upload_keys_botocore_cannot_send_are_refused_with_its_exception() {
    for (key, expected) in [
        ("dir/\u{e9}.txt".as_bytes(), None),
        (
            b"".as_slice(),
            Some(
                "Parameter validation failed:\n\
                Invalid length for parameter Key, value: 0, valid min length: 1",
            ),
        ),
        (
            b"invalid-\xff.txt",
            Some(
                "'utf-8' codec can't encode character '\\udcff' in position 8: \
                surrogates not allowed",
            ),
        ),
        (
            b"\xc3\xa9\xe2\x82x\xff",
            Some("'utf-8' codec can't encode characters in position 1-2: surrogates not allowed"),
        ),
    ] {
        assert_eq!(upload_key_refusal(key).as_deref(), expected, "{key:?}");
    }
}
#[test]
fn keys_and_prefixes_botocore_cannot_encode_are_refused_empty_ones_are_not() {
    assert_eq!(key_encode_refusal(b""), None);
    assert_eq!(key_encode_refusal("dir/\u{e9}".as_bytes()), None);
    assert_eq!(
        key_encode_refusal(b"key-\xff").as_deref(),
        Some(
            "'utf-8' codec can't encode character '\\udcff' in position 4: surrogates not allowed"
        )
    );
}
#[test]
fn normalize_directory_root() {
    for (value, expected) in [
        ("", "./"),
        ("downloads", "downloads/"),
        ("downloads/", "downloads/"),
        ("/downloads", "/downloads/"),
    ] {
        assert_eq!(
            normalize_local_directory_root(Path::new(value)),
            Path::new(expected)
        );
    }
}
#[test]
fn a_directorys_entries_sort_as_upstreams_file_generator_sorts_them() {
    let file = |name: &'static str| ListedName {
        name: name.as_bytes(),
        directory: false,
    };
    let directory = |name: &'static str| ListedName {
        directory: true,
        ..file(name)
    };
    let undecodable = ListedName {
        name: b"\x80",
        directory: false,
    };
    let cases = [
        (file("a.txt"), directory("a")),
        (directory("a"), file("a0")),
        (file("a"), file("a.txt")),
        (file("B"), file("a")),
        // An undecodable byte is a surrogate escape, U+DC80 here: after
        // U+00E9 although its byte is lower, and before U+E000.
        (file("\u{e9}"), undecodable),
        (undecodable, file("\u{e000}")),
    ];
    for (first, second) in cases {
        assert!(lists_before(first, second), "{first:?} before {second:?}");
        assert!(!lists_before(second, first), "{second:?} after {first:?}");
    }
    let same = file("same");
    assert!(!lists_before(same, same));
}
#[cfg(unix)]
#[test]
fn directory_creation_accepts_roots() {
    for root in ["/", "//"] {
        create_local_dir_path(Path::new(root)).unwrap();
    }
    assert_eq!(
        create_local_dir_path(Path::new("")).unwrap_err().kind(),
        io::ErrorKind::InvalidInput
    );
}
#[test]
fn creates_nested_directories() {
    let dir = Directory::new();
    let path = dir.0.join("a/b/c");
    create_local_dir_path(&path).unwrap();
    assert!(path.is_dir());
    create_local_dir_path(&path).unwrap();
}
#[test]
fn symlinked_directory_is_accepted() {
    let dir = Directory::new();
    let real = dir.0.join("real");
    fs::create_dir(&real).unwrap();
    let link = dir.0.join("link");
    if !symlink(&real, &link, true) {
        return;
    }
    create_local_dir_path(&link.join("child")).unwrap();
    assert!(real.join("child").is_dir());
}
#[test]
fn dangling_and_file_symlinks_rejected() {
    let dir = Directory::new();
    let link = dir.0.join("link");
    if !symlink(&dir.0.join("missing"), &link, false) {
        return;
    }
    assert_eq!(
        create_local_dir_path(&link).unwrap_err().kind(),
        io::ErrorKind::NotADirectory
    );
    fs::write(dir.0.join("missing"), b"file").unwrap();
    assert_eq!(
        create_local_dir_path(&link).unwrap_err().kind(),
        io::ErrorKind::NotADirectory
    );
}
#[cfg(unix)]
#[test]
fn an_unreachable_symlink_target_keeps_its_stat_error() {
    use std::os::unix::fs::PermissionsExt;
    let dir = Directory::new();
    let locked = dir.0.join("locked");
    fs::create_dir_all(locked.join("target")).unwrap();
    let link = dir.0.join("link");
    std::os::unix::fs::symlink(locked.join("target"), &link).unwrap();
    fs::set_permissions(&locked, fs::Permissions::from_mode(0o000)).unwrap();
    // A privileged user searches the directory anyway.
    let searchable = fs::metadata(&link).is_ok();
    let result = create_local_dir_path(&link);
    fs::set_permissions(&locked, fs::Permissions::from_mode(0o755)).unwrap();
    if !searchable {
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::PermissionDenied);
    }
}
#[cfg(target_os = "linux")]
#[test]
fn removed_base_returns_without_retry_loop() {
    use std::os::fd::AsRawFd;
    let dir = Directory::new();
    let removed = dir.0.join("removed");
    fs::create_dir(&removed).unwrap();
    let handle = fs::File::open(&removed).unwrap();
    fs::remove_dir(&removed).unwrap();
    let path = PathBuf::from(format!("/proc/self/fd/{}/.metadata", handle.as_raw_fd()));
    let error = create_local_dir_path(&path).unwrap_err();
    assert_eq!(error.raw_os_error(), Some(libc::ENOENT));
    assert_eq!(create_dir_error_name(&error), "No such file or directory");
}
#[cfg(unix)]
#[test]
fn directory_creation_failures_are_named_by_mkdir_errno() {
    let dir = Directory::new();
    let long = dir.0.join("a".repeat(300)).join("sub");
    let error = create_local_dir_path(&long).unwrap_err();
    assert_eq!(create_dir_error_name(&error), "File name too long");
    let link = dir.0.join("loop");
    std::os::unix::fs::symlink("loop", &link).unwrap();
    let error = create_local_dir_path(&link.join("sub")).unwrap_err();
    assert_eq!(
        create_dir_error_name(&error),
        "Too many levels of symbolic links"
    );
    let error = create_local_dir_path(Path::new("")).unwrap_err();
    assert_eq!(create_dir_error_name(&error), "Invalid path name");
    for (errno, name) in [
        (libc::EDQUOT, "Disk quota exceeded"),
        (libc::EPERM, "Operation not permitted"),
        (libc::EACCES, "Permission denied"),
        (libc::EMLINK, "Too many links"),
        (libc::ENOMEM, "Insufficient system resources"),
        (libc::EILSEQ, "Invalid path name"),
        (libc::EIO, "Unexpected error"),
        (libc::EINVAL, "Unexpected error"),
    ] {
        assert_eq!(
            create_dir_error_name(&io::Error::from_raw_os_error(errno)),
            name,
            "errno {errno}"
        );
    }
    assert_eq!(
        create_dir_error_name(&io::Error::from(io::ErrorKind::NotADirectory)),
        "Not a directory"
    );
}
#[test]
fn recursive_destination_keeps_components() {
    assert_eq!(
        build_recursive_destination_path(Path::new("root/"), "a//b"),
        PathBuf::from("root/a//b")
    );
}
#[test]
fn recursive_source_appends_to_root() {
    assert_eq!(
        build_recursive_source_path(Path::new("root/"), Path::new("a/b")),
        PathBuf::from("root/a/b")
    );
}
#[test]
fn recursive_upload_key_retains_prefix() {
    assert_eq!(
        build_recursive_upload_key(b"prefix/", Path::new("a/b")),
        b"prefix/a/b"
    );
}
#[test]
fn upload_walker_follows_directory_symlinks() {
    let dir = Directory::new();
    let target = dir.0.join("directory");
    fs::create_dir(&target).unwrap();
    let link = dir.0.join("link");
    if !symlink(&target, &link, true) {
        return;
    }
    assert_eq!(
        recursive_upload_walk_step(&link).unwrap(),
        UploadWalkStep::Descend
    );
    fs::remove_dir(&target).unwrap();
    assert!(recursive_upload_walk_step(&link).is_err());
    // A link to a file is a file link: Windows cannot resolve a directory
    // link whose target became a file. With the separator a walk appends, a
    // file does not resolve as a directory, so the walk inspects it.
    fs::write(&target, b"file").unwrap();
    let file_link = dir.0.join("file-link");
    assert!(symlink(&target, &file_link, false));
    assert!(!matches!(
        recursive_upload_walk_step(&file_link),
        Ok(UploadWalkStep::Descend)
    ));
}
#[test]
fn download_temp_names_append_the_id_as_16_hex_digits() {
    let nested = Path::new("dir").join("file.txt");
    let mut nested_expected = nested.clone().into_os_string();
    nested_expected.push(".ffffffffffffffff");
    for (destination, id, expected) in [
        (
            Path::new("file"),
            0x1234_5678_9abc_def0,
            PathBuf::from("file.123456789abcdef0"),
        ),
        (
            Path::new("archive.tar.gz"),
            0,
            PathBuf::from("archive.tar.gz.0000000000000000"),
        ),
        (nested.as_path(), u64::MAX, PathBuf::from(nested_expected)),
    ] {
        assert_eq!(make_download_temp_path(destination, id).unwrap(), expected);
    }
}
fn temp_name_truncation_cases() -> [(String, String); 6] {
    let fits = "a".repeat(238);
    [
        (fits.clone(), fits.clone()),
        (format!("{fits}b"), fits),
        ("c".repeat(255), "c".repeat(238)),
        (format!("{}é", "a".repeat(237)), "a".repeat(237)),
        (format!("{}€", "a".repeat(236)), "a".repeat(236)),
        (
            format!("{}éz", "a".repeat(236)),
            format!("{}é", "a".repeat(236)),
        ),
    ]
}
#[test]
fn download_temp_names_keep_the_destination_name_only_as_long_as_255_bytes_allow() {
    let dir = Path::new("dir");
    for (name, kept) in temp_name_truncation_cases() {
        let temp = make_download_temp_path(&dir.join(&name), 0x0123_4567_89ab_cdef).unwrap();
        assert_eq!(temp, dir.join(format!("{kept}.0123456789abcdef")));
        assert_eq!(temp.parent(), Some(dir));
        let basename = temp.file_name().unwrap();
        assert!(basename.len() <= 255);
        assert!(basename.to_str().is_some());
    }
}
#[test]
fn wide_download_temp_names_cut_where_utf8_names_do() {
    let wide = |text: &str| text.encode_utf16().collect::<Vec<u16>>();
    let suffix = ".0123456789abcdef";
    for (name, kept) in temp_name_truncation_cases() {
        for parent in ["", "dir/", "dir\\"] {
            let temp = temp_path_wide(&wide(&format!("{parent}{name}")), suffix.as_bytes());
            assert_eq!(temp.unwrap(), wide(&format!("{parent}{kept}{suffix}")));
        }
    }
    let mut name = wide(&format!("{}😀", "a".repeat(236)));
    assert_eq!(
        temp_path_wide(&name, suffix.as_bytes()).unwrap(),
        wide(&format!("{}{suffix}", "a".repeat(236)))
    );
    name.truncate(236);
    name.push(0xd800);
    assert_eq!(
        temp_path_wide(&name, suffix.as_bytes()).unwrap(),
        wide(&format!("{}{suffix}", "a".repeat(236)))
    );
}
#[test]
fn commit_moves_temp_file() {
    let dir = Directory::new();
    let temp = dir.0.join("temp");
    let dest = dir.0.join("dest");
    fs::write(&temp, b"new").unwrap();
    complete_downloaded_temp_file(&temp, &dest).unwrap();
    assert!(!temp.exists());
    assert_eq!(fs::read(dest).unwrap(), b"new");
}
#[test]
fn commit_replaces_destination() {
    let dir = Directory::new();
    let temp = dir.0.join("temp");
    let dest = dir.0.join("dest");
    fs::write(&temp, b"new").unwrap();
    fs::write(&dest, b"old").unwrap();
    complete_downloaded_temp_file(&temp, &dest).unwrap();
    assert_eq!(fs::read(dest).unwrap(), b"new");
}
#[test]
fn failed_commit_deletes_temp() {
    let dir = Directory::new();
    let temp = dir.0.join("temp");
    fs::write(&temp, b"new").unwrap();
    assert_eq!(
        complete_downloaded_temp_file(&temp, &dir.0.join("missing").join("dest")),
        Err(CommitFailure {
            error: "No such file or directory",
            removing_destination: false,
        })
    );
    assert!(!temp.exists());
}
#[test]
fn a_commit_to_a_destination_holding_a_nul_refuses_it() {
    let dir = Directory::new();
    let temp = dir.0.join("temp");
    let prefix = dir.0.join("report");
    fs::write(&temp, b"new").unwrap();
    fs::write(&prefix, b"old").unwrap();
    assert_eq!(
        complete_downloaded_temp_file(&temp, &dir.0.join("report\0.backup")),
        Err(CommitFailure {
            error: "Invalid path name",
            removing_destination: cfg!(windows),
        })
    );
    assert!(!temp.exists());
    assert_eq!(fs::read(&prefix).unwrap(), b"old");
    assert_eq!(fs::read_dir(&dir.0).unwrap().count(), 1);
}
#[test]
fn deletion_skips_a_path_holding_a_nul() {
    let dir = Directory::new();
    let prefix = dir.0.join("report");
    fs::write(&prefix, b"old").unwrap();
    assert!(path_holds_nul(&dir.0.join("report\0x")));
    assert!(!path_holds_nul(&prefix));
    delete_file_best_effort(&dir.0.join("report\0x"));
    assert_eq!(fs::read(&prefix).unwrap(), b"old");
}
#[test]
fn deletion_tolerates_missing_file() {
    let dir = Directory::new();
    delete_file_best_effort(&dir.0.join("missing"));
}
#[test]
fn mtime_uses_service_epoch() {
    assert_eq!(
        timestamp_from_list_entry(true, 123),
        Some(SystemTime::UNIX_EPOCH + Duration::from_secs(123))
    );
}
#[test]
fn list_mtime_observes_presence_and_keeps_pre_epoch_values() {
    assert_eq!(timestamp_from_list_entry(false, 12), None);
    assert_eq!(
        timestamp_from_list_entry(true, -60),
        Some(SystemTime::UNIX_EPOCH - Duration::from_secs(60))
    );
    assert_eq!(
        timestamp_from_list_entry(true, 0),
        Some(SystemTime::UNIX_EPOCH)
    );
    assert_eq!(
        timestamp_from_list_entry(true, 253_402_300_799),
        Some(SystemTime::UNIX_EPOCH + Duration::from_secs(253_402_300_799))
    );
}
#[test]
fn mtime_warning_matches_cli() {
    assert_eq!(
        mtime_warning(Path::new("/work/file"), "Permission denied"),
        b"warning: Skipping file /work/file. Successfully Downloaded /work/file but was \
        unable to update the last modified time. Permission denied"
    );
}
#[test]
fn download_failure_texts_match_the_named_formats() {
    assert_eq!(
        PARENT_DIRECTORY_FAILURE,
        "error: unable to create parent directory for"
    );
    assert_eq!(
        TEMP_PATH_FAILURE,
        "error: unable to prepare download destination"
    );
}
#[test]
fn sets_destination_mtime() {
    let dir = Directory::new();
    let path = dir.0.join("file");
    fs::write(&path, b"file").unwrap();
    set_destination_mtime(&path, 1_609_459_200).unwrap();
    let timestamp = timestamp_from_epoch_seconds(1_609_459_200);
    let metadata = fs::metadata(path).unwrap();
    assert_eq!(metadata.modified().unwrap(), timestamp);
    assert_eq!(metadata.accessed().unwrap(), timestamp);
}
#[test]
fn sets_a_pre_epoch_destination_mtime() {
    let dir = Directory::new();
    let path = dir.0.join("file");
    fs::write(&path, b"file").unwrap();
    set_destination_mtime(&path, -60).unwrap();
    let metadata = fs::metadata(path).unwrap();
    assert_eq!(
        metadata.modified().unwrap(),
        timestamp_from_epoch_seconds(-60)
    );
    assert_eq!(
        metadata.accessed().unwrap(),
        timestamp_from_epoch_seconds(-60)
    );
}
#[cfg(unix)]
#[test]
fn sets_mtime_on_a_file_its_owner_cannot_open() {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new();
    let path = directory.0.join("unopenable");
    fs::write(&path, b"contents").unwrap();
    fs::set_permissions(&path, fs::Permissions::from_mode(0o000)).unwrap();
    set_destination_mtime(&path, 1_609_459_200).unwrap();
    assert_eq!(
        fs::metadata(&path).unwrap().modified().unwrap(),
        timestamp_from_epoch_seconds(1_609_459_200)
    );
    assert_eq!(
        set_destination_mtime(&directory.0.join("missing"), 0),
        Err("Unexpected error")
    );
}

#[cfg(unix)]
#[test]
fn sets_mtime_without_write_permission() {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new();
    let path = directory.0.join("readonly");
    fs::write(&path, b"contents").unwrap();
    fs::set_permissions(&path, fs::Permissions::from_mode(0o444)).unwrap();
    set_destination_mtime(&path, 1_609_459_200).unwrap();
    assert_eq!(
        fs::metadata(&path).unwrap().modified().unwrap(),
        timestamp_from_epoch_seconds(1_609_459_200)
    );
}

#[test]
fn upload_sources_each_skip_names_upstreams_reason() {
    for (skip, reason, suffix) in [
        (SourceSkip::Missing, "File does not exist.", ""),
        (
            SourceSkip::Special,
            "File is character special device, block special device, FIFO, or socket.",
            "",
        ),
        (
            SourceSkip::UnreadableFile,
            "File/Directory is not readable.",
            "",
        ),
        (
            SourceSkip::UnreadableDirectory,
            "File/Directory is not readable.",
            std::path::MAIN_SEPARATOR_STR,
        ),
        (
            SourceSkip::UnreadableSubdirectory,
            "File/Directory is not readable.",
            "",
        ),
    ] {
        assert_eq!(skip.reason(), reason);
        assert_eq!(skip.path_suffix(), suffix);
        if cfg!(unix) {
            assert_eq!(
                source_skip_warning(Path::new("/"), Path::new("/absolute/source"), skip),
                format!("warning: Skipping file /absolute/source{suffix}. {reason}").as_bytes()
            );
        }
    }
}

#[cfg(unix)]
#[test]
fn a_directory_source_fails_with_upstreams_is_a_directory_error() {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    for (source, path) in [
        (&b"/work/d/"[..], &b"'/work/d/'"[..]),
        (b"/work/d", b"'/work/d/'"),
        (b"/work/a/../d/.", b"'/work/d/'"),
        (b"/", b"'//'"),
        (b"//", b"'///'"),
        (b"/work/it's", b"\"/work/it's/\""),
        (b"/work/d\xff/", br"'/work/d\udcff/'"),
    ] {
        assert_eq!(
            directory_source_failure(Path::new(OsStr::from_bytes(source))),
            [b"[Errno 21] Is a directory: ".as_slice(), path].concat(),
            "{}",
            source.escape_ascii()
        );
    }
}

#[test]
fn an_errno_oserror_reads_as_cpythons_str_of_it() {
    for (code, message, path, expected) in [
        (
            2,
            "No such file or directory",
            r"C:\work\d\",
            r"[Errno 2] No such file or directory: 'C:\\work\\d\\'",
        ),
        (
            13,
            "Permission denied",
            r"C:\work\it's\",
            r#"[Errno 13] Permission denied: "C:\\work\\it's\\""#,
        ),
    ] {
        assert_eq!(
            errno_error_text(code, message.as_bytes(), path.as_bytes()),
            expected.as_bytes()
        );
    }
}

#[cfg(unix)]
#[test]
fn a_source_that_cannot_be_removed_fails_with_upstreams_oserror() {
    for (cwd, source, errno, expected) in [
        (
            "/work",
            "locked/a.txt",
            libc::EACCES,
            "[Errno 13] Permission denied: '/work/locked/a.txt'",
        ),
        (
            "/work",
            "/other/../gone.txt",
            libc::ENOENT,
            "[Errno 2] No such file or directory: '/gone.txt'",
        ),
        (
            "/work",
            "it's",
            libc::EROFS,
            "[Errno 30] Read-only file system: \"/work/it's\"",
        ),
    ] {
        let error = io::Error::from_raw_os_error(errno);
        assert_eq!(
            String::from_utf8_lossy(&source_removal_failure(
                Path::new(cwd),
                Path::new(source),
                &error
            )),
            expected
        );
    }
}

#[cfg(unix)]
#[test]
fn source_skip_warnings_resolve_the_path_and_keep_a_root_separator() {
    let cwd = Path::new("/work");
    for (source, skip, expected) in [
        (
            "pipe",
            SourceSkip::Special,
            "/work/pipe. File is character special device, \
            block special device, FIFO, or socket.",
        ),
        (
            "locked",
            SourceSkip::UnreadableDirectory,
            "/work/locked/. File/Directory is not readable.",
        ),
        (
            "tree/blocked",
            SourceSkip::UnreadableSubdirectory,
            "/work/tree/blocked. File/Directory is not readable.",
        ),
        (
            "/abs/source.txt/",
            SourceSkip::Missing,
            "/abs/source.txt/. File does not exist.",
        ),
        (
            "/abs/dir/",
            SourceSkip::UnreadableDirectory,
            "/abs/dir/. File/Directory is not readable.",
        ),
        (
            "/",
            SourceSkip::UnreadableDirectory,
            "/. File/Directory is not readable.",
        ),
    ] {
        assert_eq!(
            String::from_utf8(source_skip_warning(cwd, Path::new(source), skip)).unwrap(),
            format!("warning: Skipping file {expected}"),
            "{source}"
        );
    }
}

#[cfg(unix)]
#[test]
fn upload_sources_special_files_are_skipped_before_anything_opens_them() {
    use std::os::unix::{ffi::OsStrExt, net::UnixListener};
    let special = SourceInspection::Skipped(SourceSkip::Special);
    let directory = Directory::new();
    assert_eq!(inspect_upload_source(Path::new("/dev/null")), special);
    let link = directory.0.join("null-link");
    std::os::unix::fs::symlink("/dev/null", &link).unwrap();
    assert_eq!(inspect_upload_source(&link), special);
    let socket_path = directory.0.join("socket");
    let _listener = UnixListener::bind(&socket_path).unwrap();
    assert_eq!(inspect_upload_source(&socket_path), special);
    let fifo = directory.0.join("fifo");
    let fifo_c = std::ffi::CString::new(fifo.as_os_str().as_bytes()).unwrap();
    // SAFETY: fifo_c is a live, terminated path; mkfifo retains no pointer.
    assert_eq!(unsafe { libc::mkfifo(fifo_c.as_ptr(), 0o600) }, 0);
    assert_eq!(inspect_upload_source(&fifo), special);
}

#[cfg(unix)]
#[test]
fn upload_sources_readable_ones_pass_with_their_size() {
    let directory = Directory::new();
    let plain = directory.0.join("plain.txt");
    fs::write(&plain, b"plain").unwrap();
    let listed = directory.0.join("listed");
    fs::create_dir(&listed).unwrap();
    let link = directory.0.join("plain-link");
    std::os::unix::fs::symlink(&plain, &link).unwrap();
    for path in [&plain, &listed, &link] {
        assert_eq!(
            inspect_upload_source(path),
            SourceInspection::Size(fs::metadata(path).unwrap().len())
        );
    }
    assert_eq!(inspect_upload_source(&link), SourceInspection::Size(5));
    let missing = SourceInspection::Skipped(SourceSkip::Missing);
    assert_eq!(inspect_upload_source(&directory.0.join("missing")), missing);
    let broken = directory.0.join("broken");
    std::os::unix::fs::symlink(directory.0.join("absent"), &broken).unwrap();
    assert_eq!(inspect_upload_source(&broken), missing);
}

#[test]
fn an_upload_source_with_an_unreadable_mtime_is_marked() {
    let directory = Directory::new();
    let path = directory.0.join("dated.txt");
    fs::write(&path, b"dated").unwrap();
    if crate::sync::comparator::set_unreadable_mtime(&path) {
        assert_eq!(
            inspect_upload_source(&path),
            SourceInspection::InvalidTimestamp(5)
        );
    }
}

#[cfg(unix)]
#[test]
fn unreadable_upload_sources_are_skipped_when_permissions_are_enforced() {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new();
    let path = directory.0.join("file");
    fs::write(&path, b"data").unwrap();
    fs::set_permissions(&path, fs::Permissions::from_mode(0o0)).unwrap();
    if fs::File::open(&path).is_err() {
        assert_eq!(
            inspect_upload_source(&path),
            SourceInspection::Skipped(SourceSkip::UnreadableFile)
        );
    }
    fs::set_permissions(&path, fs::Permissions::from_mode(0o600)).unwrap();
    fs::set_permissions(&directory.0, fs::Permissions::from_mode(0o0)).unwrap();
    if fs::read_dir(&directory.0).is_err() {
        assert_eq!(
            inspect_upload_source(&directory.0),
            SourceInspection::Skipped(SourceSkip::UnreadableDirectory)
        );
    }
    fs::set_permissions(&directory.0, fs::Permissions::from_mode(0o700)).unwrap();
}

#[cfg(unix)]
#[test]
fn raw_filename_warnings_preserve_undecodable_bytes() {
    use std::os::unix::ffi::OsStrExt;
    let path = Path::new(std::ffi::OsStr::from_bytes(b"/absolute/\xff"));
    assert_eq!(
        source_skip_warning(Path::new("/"), path, SourceSkip::Missing),
        b"warning: Skipping file /absolute/\xff. File does not exist."
    );
    assert_eq!(
        mtime_warning(path, "Permission denied"),
        b"warning: Skipping file /absolute/\xff. Successfully Downloaded \
        /absolute/\xff but was unable to update the last modified time. Permission denied"
    );
}

static SOURCE_CALLS: AtomicU64 = AtomicU64::new(0);
fn counting_source() -> io::Result<[u8; random::BATCH_BYTES]> {
    let call = SOURCE_CALLS.fetch_add(1, Ordering::Relaxed);
    let mut bytes = [0; random::BATCH_BYTES];
    for (index, chunk) in bytes.chunks_exact_mut(8).enumerate() {
        let id = call * 1_000_000 + u64::try_from(index).unwrap();
        chunk.copy_from_slice(&id.to_ne_bytes());
    }
    Ok(bytes)
}
#[test]
fn a_batch_hands_out_each_id_once_and_refills_when_spent() {
    let mut batch = random::Batch::empty();
    let before = SOURCE_CALLS.load(Ordering::Relaxed);
    let ids: Vec<u64> = (0..random::IDS_PER_BATCH + 1)
        .map(|_| batch.draw(counting_source).unwrap())
        .collect();
    assert_eq!(SOURCE_CALLS.load(Ordering::Relaxed) - before, 2);
    assert_eq!(ids[1] - ids[0], 1);
    assert_eq!(ids[random::IDS_PER_BATCH - 1] - ids[0], 511);
    assert_eq!(
        ids[random::IDS_PER_BATCH] / 1_000_000,
        ids[0] / 1_000_000 + 1
    );
}
fn failing_source() -> io::Result<[u8; random::BATCH_BYTES]> {
    Err(io::Error::from_raw_os_error(libc::ENOSYS))
}
fn constant_source() -> io::Result<[u8; random::BATCH_BYTES]> {
    Ok([7; random::BATCH_BYTES])
}
#[test]
fn a_failing_random_source_fails_the_draw_and_is_retried_next_time() {
    let mut batch = random::Batch::empty();
    assert_eq!(
        batch.draw(failing_source).unwrap_err().raw_os_error(),
        Some(libc::ENOSYS)
    );
    assert_eq!(
        batch.draw(constant_source).unwrap(),
        u64::from_ne_bytes([7; 8])
    );
}
#[test]
fn temp_name_ids_come_from_the_os_and_name_the_temp_file() {
    let (first, second) = (temp_name_id().unwrap(), temp_name_id().unwrap());
    assert_ne!(first, second);
    let temp = make_download_temp_path(Path::new("file"), first).unwrap();
    assert_eq!(temp, PathBuf::from(format!("file.{first:016x}")));
}
#[test]
fn upload_size_warning_names_the_source_and_the_limit() {
    assert_eq!(MAX_UPLOAD_SIZE, 53_687_091_200_000);
    let display = Path::new(".").join("huge.bin");
    assert_eq!(
        upload_size_warning(&display),
        format!(
            "warning: File {} exceeds s3 upload limit of 48.8 TiB.",
            display.display()
        )
        .into_bytes()
    );
}
