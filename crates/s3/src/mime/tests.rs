use super::*;
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

#[test]
fn default_types_match_cpython_case_hidden_and_compound_suffixes() {
    let database = Database::default();
    for (name, expected) in [
        ("index.html", Some("text/html")),
        ("notes.txt", Some("text/plain")),
        ("photo.jpeg", Some("image/jpeg")),
        ("photo.JPEG", Some("image/jpeg")),
        ("report.PDF", Some("application/pdf")),
        ("x.Ksh", Some("text/plain")),
        ("x.KSH", Some("text/plain")),
        ("a.b.c.json", Some("application/json")),
        ("a.wasm", Some("application/wasm")),
        ("a.unknownext", None),
        ("noext", None),
        ("a.tar.gz", Some("application/x-tar")),
        ("a.tgz", Some("application/x-tar")),
        ("a.TGZ", Some("application/x-tar")),
        ("a.taz", Some("application/x-tar")),
        ("a.tz", Some("application/x-tar")),
        ("a.tbz2", Some("application/x-tar")),
        ("a.txz", Some("application/x-tar")),
        ("a.tar.br", Some("application/x-tar")),
        ("a.tar.bz2", Some("application/x-tar")),
        ("a.tar.xz", Some("application/x-tar")),
        ("a.svgz", Some("image/svg+xml")),
        ("a.tar.Z", Some("application/x-tar")),
        ("a.tar.z", None),
        ("a.gz", None),
        ("a.GZ", Some("application/gzip")),
        ("a.Z", None),
        ("archive.tar.gz.part", None),
        (".bashrc", None),
        ("..txt", None),
        ("a..txt", Some("text/plain")),
        ("dir.d/file", None),
        ("/x.y/z.txt", Some("text/plain")),
        ("./sub.dir/.hidden", None),
        ("a.", None),
    ] {
        assert_eq!(
            database.name_type(name.as_bytes()),
            expected.map(str::as_bytes),
            "{name}"
        );
    }
    assert_eq!(defaults::DEFAULT_TYPES.len(), 198);
}

#[test]
fn files_preserve_case_raw_bytes_and_unicode_whitespace_with_later_overrides() {
    let mut database = Database::default();
    database.read_types(
        concat!(
            "text/x-first\tfirst alpha\n# comment\ntext/x-alpha alpha #trailing words\n",
            "application/x-upper UPPER\n\u{2003}text/x-emsp\u{2003}emsp\u{85}nel\r\n",
            "text/x-cr cr\rtext/x-after-cr aftercr\ntext/html txt\n\u{feff}text/x-bom bom\n",
        )
        .as_bytes(),
    );
    database
        .read_types(b"text/x-second alpha\n# \xed\xa0\x80\xff\ntext/x-raw raw\xff\xc2\xa0other\n");
    for (name, expected) in [
        (b"a.first".as_slice(), Some(b"text/x-first".as_slice())),
        (b"a.alpha", Some(b"text/x-second")),
        (b"a.UPPER", None),
        (b"a.upper", None),
        (b"a.emsp", Some(b"text/x-emsp")),
        (b"a.nel", Some(b"text/x-emsp")),
        (b"a.cr", Some(b"text/x-cr")),
        (b"a.aftercr", Some(b"text/x-after-cr")),
        (b"a.txt", Some(b"text/html")),
        (b"a.bom", Some("\u{feff}text/x-bom".as_bytes())),
        (b"a.raw\xff", Some(b"text/x-raw")),
        (b"a.raw", None),
        (b"a.other", Some(b"text/x-raw")),
        (b"a.trailing", None),
        (b"a.comment", None),
        (b"a.html", Some(b"text/html")),
    ] {
        assert_eq!(database.name_type(name), expected, "{name:?}");
    }
}

#[test]
fn guesses_preserve_invalid_mime_bytes_and_read_only_the_file_name() {
    let mut database = Database::default();
    database.read_types(b"text/x-valid valid\ntext/x-before before\n");
    database.read_types(b"# \xed\xa0\x80\xff\ntext/x-after after # \xff\n");
    assert!(database.upload_failure().is_none());
    for (path, mime) in [
        ("a.valid", b"text/x-valid".as_slice()),
        ("a.before", b"text/x-before"),
        ("a.after", b"text/x-after"),
        ("index.html", b"text/html"),
        ("//[::1]/report.txt", b"text/plain"),
        ("//[V1.host]/report.txt", b"text/plain"),
        ("report.txt", b"text/plain"),
        ("//[foo/index.html", b"text/html"),
    ] {
        assert_eq!(database.guess(Path::new(path)).ok(), Some(Some(mime)));
    }
}

#[test]
#[cfg(unix)]
fn unreadable_file_retains_the_open_error_for_every_guess() -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new()?;
    let source = directory.0.join("locked.types");
    fs::write(&source, b"text/x-locked locked\n")?;
    fs::set_permissions(&source, fs::Permissions::from_mode(0o000))?;
    if fs::File::open(&source).is_ok() {
        return Ok(()); // A privileged user opens it anyway; nothing to check.
    }
    let database = Database::from_files([&source]);
    let expected = format!("[Errno 13] Permission denied: '{}'", source.display());
    assert_eq!(
        database.upload_failure().map(GuessError::as_bytes),
        Some(expected.as_bytes())
    );
    assert_eq!(
        database
            .guess(Path::new("index.html"))
            .err()
            .as_ref()
            .map(GuessError::as_bytes),
        Some(expected.as_bytes())
    );
    Ok(())
}

#[test]
fn failed_initialization_fails_every_upload() {
    let message = errors::from_errno(libc::EACCES, Some(Path::new("types")));
    let database = Database {
        failure: Some(message.clone()),
        ..Database::default()
    };
    assert_eq!(
        database.guess(Path::new("index.html")),
        Err(message.clone())
    );
    assert_eq!(database.upload_failure(), Some(&message));
    assert_eq!(message.as_bytes(), b"[Errno 13] Permission denied: 'types'");
}

#[test]
#[cfg(target_os = "linux")]
fn os_errors_keep_the_errno_the_os_reported() {
    let types = Path::new("/etc/mime.types");
    for (errno, source, expected) in [
        (
            libc::ESTALE,
            Some(types),
            "[Errno 116] Stale file handle: '/etc/mime.types'",
        ),
        (
            libc::ENOSPC,
            Some(types),
            "[Errno 28] No space left on device: '/etc/mime.types'",
        ),
        (libc::ENOBUFS, None, "[Errno 105] No buffer space available"),
    ] {
        let error = io::Error::from_raw_os_error(errno);
        assert_eq!(os_error(&error, source).as_bytes(), expected.as_bytes());
    }
}

#[test]
#[cfg(target_os = "linux")]
fn a_file_that_cannot_be_read_fails_every_upload_with_the_errno_read_reported() {
    let database = Database::from_files(["/proc/self/ns/mnt"]);
    let expected = b"[Errno 22] Invalid argument".as_slice();
    assert_eq!(
        database.upload_failure().map(GuessError::as_bytes),
        Some(expected)
    );
    assert_eq!(
        database
            .guess(Path::new("index.html"))
            .err()
            .as_ref()
            .map(GuessError::as_bytes),
        Some(expected)
    );
}

#[test]
fn loading_skips_missing_and_nonregular_paths_but_retains_ordered_files() -> io::Result<()> {
    let directory = Directory::new()?;
    let first = directory.0.join("first");
    let second = directory.0.join("second");
    fs::write(&first, b"text/first txt\n")?;
    fs::write(&second, b"text/second txt\n")?;
    let database =
        Database::from_files([&directory.0, &directory.0.join("missing"), &first, &second]);
    assert!(database.upload_failure().is_none());
    assert_eq!(
        database.guess(Path::new("file.txt")).ok(),
        Some(Some(b"text/second".as_slice()))
    );
    Ok(())
}

#[test]
fn mime_file_byte_budget_accepts_boundary_and_rejects_one_more_byte() -> io::Result<()> {
    let directory = Directory::new()?;
    let source = directory.0.join("types");
    let mut bytes = vec![b'\n'; MIME_TYPES_BYTES_MAX];
    let first = b"text/edge edge\n";
    bytes[..first.len()].copy_from_slice(first);
    fs::write(&source, &bytes)?;
    let database = Database::from_files([&source]);
    assert_eq!(database.name_type(b"a.edge"), Some(b"text/edge".as_slice()));
    assert!(database.upload_failure().is_none());
    bytes.push(b'\n');
    fs::write(&source, bytes)?;
    let database = Database::from_files([&source]);
    assert_eq!(
        database.upload_failure().map(GuessError::as_bytes),
        Some(b"[Errno 27] File too large".as_slice())
    );
    Ok(())
}

struct Directory(PathBuf);
impl Directory {
    fn new() -> io::Result<Self> {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../target/mime-tests")
            .join(format!(
                "{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
        fs::create_dir_all(&path)?;
        Ok(Self(path))
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
