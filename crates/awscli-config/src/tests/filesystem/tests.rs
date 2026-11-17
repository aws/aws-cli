use super::*;
use std::{
    cell::{Cell, RefCell},
    path::Path,
    rc::Rc,
};
#[derive(Debug, Default)]
struct Counts {
    opens: Cell<usize>,
    closes: Cell<usize>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Call {
    PathMetadata,
    Open,
    HandleMetadata,
    Read,
}
type Failures = Rc<RefCell<Vec<(Call, ReadError)>>>;
fn fail_once(failures: &Failures, call: Call) -> Result<(), ReadError> {
    let mut failures = failures.borrow_mut();
    match failures.iter().position(|(queued, _)| *queued == call) {
        Some(index) => Err(failures.remove(index).1),
        None => Ok(()),
    }
}
#[derive(Debug)]
struct FakeFs {
    bytes: Vec<u8>,
    counts: Rc<Counts>,
    path_error: Option<ReadError>,
    open_error: Option<ReadError>,
    read_error: Option<ReadError>,
    once: Failures,
    kind: FileKind,
    hide_size: bool,
}
impl FakeFs {
    fn new(bytes: Vec<u8>) -> Self {
        Self {
            bytes,
            counts: Rc::default(),
            path_error: None,
            open_error: None,
            read_error: None,
            once: Failures::default(),
            kind: FileKind::Regular,
            hide_size: false,
        }
    }
    fn fail_once(&self, failures: impl IntoIterator<Item = (Call, ReadError)>) {
        self.once.borrow_mut().extend(failures);
    }
}
#[derive(Debug)]
struct Handle {
    bytes: std::io::Cursor<Vec<u8>>,
    counts: Rc<Counts>,
    read_error: Option<ReadError>,
    once: Failures,
    hide_size: bool,
}
impl Drop for Handle {
    fn drop(&mut self) {
        self.counts.closes.set(self.counts.closes.get() + 1);
    }
}
impl ReadHandle for Handle {
    fn metadata(&self) -> Result<Metadata, ReadError> {
        fail_once(&self.once, Call::HandleMetadata)?;
        Ok(Metadata {
            kind: FileKind::Regular,
            len: if self.hide_size {
                0
            } else {
                self.bytes.get_ref().len() as u64
            },
        })
    }
    fn read(&mut self, bytes: &mut [u8]) -> Result<usize, ReadError> {
        if let Some(error) = self.read_error {
            return Err(error);
        }
        fail_once(&self.once, Call::Read)?;
        std::io::Read::read(&mut self.bytes, bytes).map_err(Into::into)
    }
}
impl Fs for FakeFs {
    type Handle = Handle;
    fn metadata(&self, _: &Path) -> Result<Metadata, ReadError> {
        if let Some(error) = self.path_error {
            return Err(error);
        }
        fail_once(&self.once, Call::PathMetadata)?;
        Ok(Metadata {
            kind: self.kind,
            len: self.bytes.len() as u64,
        })
    }
    fn open(&self, _: &Path) -> Result<Handle, ReadError> {
        if let Some(error) = self.open_error {
            return Err(error);
        }
        fail_once(&self.once, Call::Open)?;
        self.counts.opens.set(self.counts.opens.get() + 1);
        Ok(Handle {
            bytes: std::io::Cursor::new(self.bytes.clone()),
            counts: self.counts.clone(),
            read_error: self.read_error,
            once: self.once.clone(),
            hide_size: self.hide_size,
        })
    }
}
fn load(fs: &FakeFs) -> Result<ParsedFiles, ReadError> {
    ParsedFiles::load(
        fs,
        Paths {
            config: Some(Path::new("shared")),
            ..Paths::default()
        },
    )
}
#[cfg(not(miri))]
#[derive(Debug)]
struct Scratch(std::path::PathBuf);
#[cfg(not(miri))]
impl Scratch {
    fn new() -> Self {
        use std::sync::atomic::{AtomicUsize, Ordering};
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let dir = std::env::temp_dir().join(format!(
            "awscli-config-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&dir).unwrap();
        Self(dir)
    }
}
#[cfg(not(miri))]
impl Drop for Scratch {
    fn drop(&mut self) {
        // Best effort: panicking while a failed assertion unwinds would abort.
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
#[cfg(not(miri))]
pub(in crate::tests) fn load_fixture(case: &Fixture) -> ParsedFiles {
    let scratch = Scratch::new();
    let dir = &scratch.0;
    let paths = [
        dir.join("config"),
        dir.join("credentials"),
        dir.join("aliases"),
    ];
    for (index, input) in case.inputs.iter().enumerate() {
        if let Some(bytes) = input {
            std::fs::write(&paths[index], bytes).unwrap();
        }
    }
    let path = |index: usize| case.inputs[index].as_ref().map(|_| paths[index].as_path());
    ParsedFiles::load(
        &StdFs,
        Paths {
            config: path(0),
            credentials: path(1),
            aliases: path(2),
        },
    )
    .unwrap()
}
#[cfg(miri)]
pub(in crate::tests) fn load_fixture(case: &Fixture) -> ParsedFiles {
    #[derive(Debug)]
    struct CorpusFs<'a>(&'a Fixture);
    impl Fs for CorpusFs<'_> {
        type Handle = Handle;
        fn metadata(&self, path: &Path) -> Result<Metadata, ReadError> {
            let index = path.to_str().unwrap().parse::<usize>().unwrap();
            Ok(Metadata {
                kind: FileKind::Regular,
                len: self.0.inputs[index].as_ref().unwrap().len() as u64,
            })
        }
        fn open(&self, path: &Path) -> Result<Handle, ReadError> {
            let index = path.to_str().unwrap().parse::<usize>().unwrap();
            Ok(Handle {
                bytes: std::io::Cursor::new(self.0.inputs[index].clone().unwrap()),
                counts: Rc::default(),
                read_error: None,
                once: Failures::default(),
                hide_size: false,
            })
        }
    }
    let names = [Path::new("0"), Path::new("1"), Path::new("2")];
    let path = |index: usize| case.inputs[index].as_ref().map(|_| names[index]);
    ParsedFiles::load(
        &CorpusFs(case),
        Paths {
            config: path(0),
            credentials: path(1),
            aliases: path(2),
        },
    )
    .unwrap()
}
#[test]
fn unavailable_files_and_literal_paths() {
    let fs = FakeFs::new(b"[default]\nx=literal\n".to_vec());
    let loaded = ParsedFiles::load(
        &fs,
        Paths {
            config: Some(Path::new("$AWS_CONFIG_FILE")),
            ..Paths::default()
        },
    )
    .unwrap();
    assert_eq!(loaded.config.source, "$AWS_CONFIG_FILE");
    assert_eq!(
        loaded
            .profiles
            .unwrap()
            .get("default")
            .unwrap()
            .get("x")
            .unwrap()
            .value
            .as_str(),
        Some("literal")
    );
    for (error, status) in [
        (ReadError::FileNotFound, Status::Missing),
        (ReadError::NotDir, Status::Missing),
        (ReadError::IsDir, Status::Directory),
    ] {
        let mut fs = FakeFs::new(vec![]);
        fs.path_error = Some(error);
        assert_eq!(load(&fs).unwrap().config.status, status);
        assert_eq!(fs.counts.opens.get(), 0);
    }
    for (kind, status) in [
        (FileKind::Directory, Status::Directory),
        (
            FileKind::Other,
            Status::Unreadable(ReadError::NotRegularFile),
        ),
    ] {
        let mut fs = FakeFs::new(vec![]);
        fs.kind = kind;
        assert_eq!(load(&fs).unwrap().config.status, status);
        assert_eq!(fs.counts.opens.get(), 0);
    }
}
#[test]
#[cfg_attr(
    miri,
    ignore = "8 MiB resource boundary is covered natively; parser paths run in the corpus"
)]
fn byte_and_file_size_boundaries_include_eight_mib() {
    let mut bytes = vec![b'x'; INPUT_SIZE_MAX + 1];
    bytes[0] = b'#';
    for size in [INPUT_SIZE_MAX - 1, INPUT_SIZE_MAX, INPUT_SIZE_MAX + 1] {
        let expected = if size > INPUT_SIZE_MAX {
            Status::ResourceLimit
        } else {
            Status::Loaded
        };
        let parsed = ParsedFiles::parse(Inputs {
            config: Some(Contents {
                bytes: &bytes[..size],
                source: "size",
            }),
            ..Inputs::default()
        });
        let loaded = load(&FakeFs::new(bytes[..size].to_vec())).unwrap();
        assert_eq!(parsed.config.status, expected);
        assert_eq!(loaded.config.status, expected);
        assert_eq!(parsed.profiles.is_none(), size > INPUT_SIZE_MAX);
        assert_eq!(loaded.profiles.is_none(), size > INPUT_SIZE_MAX);
    }
}
#[test]
fn unreadable_files_preserve_cause_and_do_not_block_merging() {
    for error in [ReadError::SymLinkLoop, ReadError::BadPathName] {
        let mut fs = FakeFs::new(vec![]);
        fs.path_error = Some(error);
        let parsed = load(&fs).unwrap();
        assert_eq!(parsed.config.status, Status::Unreadable(error));
        assert_eq!(parsed.config.source, "shared");
        assert!(parsed.profiles.unwrap().is_empty());
    }
}
#[test]
fn denied_files_contribute_no_entries() {
    for error in [ReadError::AccessDenied, ReadError::PermissionDenied] {
        let mut fs = FakeFs::new(vec![]);
        fs.open_error = Some(error);
        let parsed = load(&fs).unwrap();
        assert_eq!(parsed.config.status, Status::Unreadable(error));
        assert!(parsed.profiles.unwrap().is_empty());
    }
}
#[test]
fn identical_paths_share_one_handle_across_grammars() {
    let fs = FakeFs::new(b"[default]\nx=\n k=v\n".to_vec());
    let path = Some(Path::new("shared"));
    let parsed = ParsedFiles::load(
        &fs,
        Paths {
            config: path,
            credentials: path,
            aliases: path,
        },
    )
    .unwrap();
    assert_eq!(fs.counts.opens.get(), 1);
    assert_eq!(fs.counts.closes.get(), 1);
    let fs = FakeFs::new(b"[default]\nx=v\n".to_vec());
    ParsedFiles::load(
        &fs,
        Paths {
            config: Some(Path::new("shared/")),
            credentials: Some(Path::new("shared")),
            ..Paths::default()
        },
    )
    .unwrap();
    assert_eq!(fs.counts.opens.get(), 2);
    assert_eq!(
        parsed
            .aliases
            .sections
            .get("default")
            .unwrap()
            .get("x")
            .unwrap()
            .value
            .as_str(),
        Some("\nk=v")
    );
    assert_eq!(
        parsed
            .profiles
            .unwrap()
            .get("default")
            .unwrap()
            .get("x")
            .unwrap()
            .value
            .as_nested()
            .unwrap()
            .get("k")
            .map(String::as_str),
        Some("v")
    );
}
#[test]
fn read_errors_close_handles_and_resources_propagate() {
    let mut fs = FakeFs::new(b"[default]\nx=1\n".to_vec());
    fs.read_error = Some(ReadError::InputOutput);
    let parsed = load(&fs).unwrap();
    assert_eq!(
        parsed.config.status,
        Status::Unreadable(ReadError::InputOutput)
    );
    assert!(parsed.profiles.unwrap().is_empty());
    assert_eq!(fs.counts.opens.get(), fs.counts.closes.get());
    for error in [
        ReadError::SystemResources,
        ReadError::ProcessFdQuotaExceeded,
        ReadError::SystemFdQuotaExceeded,
        ReadError::Canceled,
    ] {
        let mut fs = FakeFs::new(vec![]);
        fs.open_error = Some(error);
        assert_eq!(load(&fs), Err(error));
        assert_eq!(fs.counts.opens.get(), fs.counts.closes.get());
        fs.open_error = None;
        fs.read_error = Some(error);
        assert_eq!(load(&fs), Err(error));
        assert_eq!(fs.counts.opens.get(), fs.counts.closes.get());
    }
}
#[test]
#[cfg_attr(miri, ignore = "8 MiB streamed growth boundary is covered natively")]
fn streaming_limit_survives_growth_after_stat() {
    let mut fs = FakeFs::new(vec![0; INPUT_SIZE_MAX + 1]);
    fs.hide_size = true;
    let parsed = load(&fs).unwrap();
    assert_eq!(parsed.config.status, Status::ResourceLimit);
    assert!(parsed.profiles.is_none());
    assert_eq!(fs.counts.opens.get(), fs.counts.closes.get());
}
#[test]
fn interrupted_calls_retry_and_load_the_file() {
    let interrupted = || ReadError::from(std::io::Error::from(std::io::ErrorKind::Interrupted));
    for call in [
        Call::PathMetadata,
        Call::Open,
        Call::HandleMetadata,
        Call::Read,
    ] {
        let fs = FakeFs::new(b"[default]\nx=1\n".to_vec());
        fs.fail_once([(call, interrupted()), (call, interrupted())]);
        let parsed = load(&fs).unwrap();
        assert_eq!(parsed.config.status, Status::Loaded, "{call:?}");
        assert!(fs.once.borrow().is_empty(), "{call:?}");
        assert_eq!(
            parsed
                .profiles
                .unwrap()
                .get("default")
                .unwrap()
                .get("x")
                .unwrap()
                .value
                .as_str(),
            Some("1")
        );
        assert_eq!(fs.counts.opens.get(), 1);
        assert_eq!(fs.counts.closes.get(), 1);
    }
}
#[test]
#[cfg(target_os = "linux")]
fn timed_out_reads_retry_like_positional_reads() {
    let timed_out = || ReadError::from(std::io::Error::from_raw_os_error(110));
    let fs = FakeFs::new(b"[default]\nx=1\n".to_vec());
    fs.fail_once([(Call::Read, timed_out())]);
    assert_eq!(load(&fs).unwrap().config.status, Status::Loaded);
    let fs = FakeFs::new(b"[default]\nx=1\n".to_vec());
    fs.fail_once([(Call::HandleMetadata, timed_out())]);
    assert_eq!(
        load(&fs).unwrap().config.status,
        Status::Unreadable(timed_out())
    );
    assert_eq!(fs.counts.opens.get(), fs.counts.closes.get());
}
#[test]
#[cfg(target_os = "linux")]
fn buffer_exhaustion_propagates_and_exited_procfs_files_are_missing() {
    let fs = FakeFs::new(b"[default]\nx=1\n".to_vec());
    fs.fail_once([(Call::Read, std::io::Error::from_raw_os_error(105).into())]);
    assert_eq!(load(&fs), Err(ReadError::SystemResources));
    assert_eq!(fs.counts.opens.get(), fs.counts.closes.get());
    let fs = FakeFs::new(b"[default]\nx=1\n".to_vec());
    fs.fail_once([(Call::Open, std::io::Error::from_raw_os_error(3).into())]);
    let parsed = load(&fs).unwrap();
    assert_eq!(parsed.config.status, Status::Missing);
    assert!(parsed.profiles.unwrap().is_empty());
}
#[test]
#[cfg(all(unix, not(miri)))]
fn std_fs_classifies_real_unavailable_paths() {
    let scratch = Scratch::new();
    let dir = &scratch.0;
    std::os::unix::fs::symlink("loop", dir.join("loop")).unwrap();
    std::fs::create_dir(dir.join("directory")).unwrap();
    std::fs::write(dir.join("file"), b"[default]\nx=1\n").unwrap();
    for (name, status) in [
        ("loop", Status::Unreadable(ReadError::SymLinkLoop)),
        ("missing", Status::Missing),
        ("directory", Status::Directory),
        ("file/", Status::Missing),
        ("file", Status::Loaded),
    ] {
        let path = dir.join(name);
        let parsed = ParsedFiles::load(
            &StdFs,
            Paths {
                config: Some(&path),
                credentials: Some(&dir.join("missing")),
                ..Paths::default()
            },
        )
        .unwrap();
        assert_eq!(parsed.config.status, status, "{name}");
        assert_eq!(parsed.config.source, path.to_string_lossy(), "{name}");
        assert_eq!(parsed.credentials.status, Status::Missing);
        let loaded = usize::from(status == Status::Loaded);
        assert_eq!(parsed.profiles.unwrap().len(), loaded, "{name}");
    }
}
#[test]
#[cfg(all(unix, not(miri)))]
fn std_fs_denied_files_contribute_no_entries() {
    use std::os::unix::fs::PermissionsExt;
    let scratch = Scratch::new();
    let path = scratch.0.join("denied");
    std::fs::write(&path, b"[default]\nx=1\n").unwrap();
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o000)).unwrap();
    let parsed = ParsedFiles::load(
        &StdFs,
        Paths {
            config: Some(&path),
            ..Paths::default()
        },
    )
    .unwrap();
    // A privileged process bypasses mode bits, so the file still loads; the
    // symlink loop above still covers unreadability on such hosts.
    if std::fs::read(&path).is_ok() {
        assert_eq!(parsed.config.status, Status::Loaded);
        return;
    }
    assert!(matches!(
        parsed.config.status,
        Status::Unreadable(ReadError::AccessDenied | ReadError::PermissionDenied)
    ));
    assert!(parsed.profiles.unwrap().is_empty());
}
