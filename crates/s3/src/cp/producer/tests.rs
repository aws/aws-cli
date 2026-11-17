#![allow(
    clippy::expect_used,
    clippy::panic,
    reason = "producer fixtures fail at the unexpected outcome or warning"
)]
use super::*;
use crate::cp::recursive::{self, Completion, Finished};
use crate::filter::FilterKind::{self, Exclude};
use crate::filter::{Filter, Roots};
use crate::scheduler::{
    Completion as Callbacks, Event, Finalize, Job, Operations, OwnedRequest, Sink, SubmitError,
};
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT: AtomicU64 = AtomicU64::new(0);

struct Directory(PathBuf);
impl Directory {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "s3-producer-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).expect("temporary directory");
        Self(path)
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[derive(Debug, Default)]
struct Uploads(Mutex<Vec<String>>);
#[derive(Debug)]
struct Sent(Arc<dyn Callbacks>);
impl OwnedRequest for Sent {
    fn cancel(&self) {}
}
impl Drop for Sent {
    fn drop(&mut self) {
        self.0.shutdown();
    }
}
impl Operations for Uploads {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, path: &Path) -> transfer::SourceInspection {
        transfer::inspect_upload_source(path)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        completion: Arc<dyn Callbacks>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push(String::from_utf8_lossy(&job.raw_key).into_owned());
        completion.finish(crt::s3::TransferResult::default());
        Ok(Box::new(Sent(completion)))
    }
    fn finalize(&self, _: &Job, _: &crt::s3::TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}
#[derive(Debug, Default)]
struct Warnings(Mutex<Vec<String>>);
impl Sink for Warnings {
    fn emit(&self, event: Event) -> Result<(), String> {
        if event.text.starts_with(b"warning:") {
            self.0
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .push(String::from_utf8_lossy(&event.text).into_owned());
        }
        Ok(())
    }
}

fn request(local_root: &Path) -> TransferRequest {
    TransferRequest {
        direction: transfer::Direction::Upload,
        bucket: "bucket".into(),
        prefix: "prefix/".into(),
        local_root: transfer::normalize_local_directory_root(local_root),
        runtime: Default::default(),
        quiet: false,
        dryrun: false,
        no_overwrite: false,
        glacier: transfer::GlacierPolicy::Warn,
        content_types: None,
        refusal: None,
        page_size: 0,
        max_in_flight: 4,
        collect_stats: false,
        prefetch: true,
        sizing: Default::default(),
        download: None,
        object: None,
        filter: Default::default(),
        headers: Default::default(),
        checksums: Default::default(),
        delete: Default::default(),
        sources: Default::default(),
        sync: None,
        listing_user_agent: None,
        links: Default::default(),
    }
}

struct Walked {
    outcome: ProducerOutcome,
    keys: Vec<String>,
    warnings: Vec<String>,
    finished: Finished,
}
fn walk_tree(request: &TransferRequest, state: &interrupt::State) -> Walked {
    let operations = Arc::new(Uploads::default());
    let warnings = Arc::new(Warnings::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/work".into(),
        operations.clone(),
        warnings.clone(),
    );
    let source = open_local_root(request)
        .expect("walk root")
        .expect("a walk opens its root");
    let outcome = produce_walk(request, &scheduler, source, state);
    scheduler.drain();
    let mut keys = std::mem::take(
        &mut *operations
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner),
    );
    keys.sort();
    let warnings = std::mem::take(
        &mut *warnings
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner),
    );
    Walked {
        finished: Finished {
            producer: outcome.clone(),
            ..scheduler.finished()
        },
        outcome,
        keys,
        warnings,
    }
}
fn status(request: &TransferRequest, finished: Finished) -> u8 {
    let processor = crate::results::Processor::new(None);
    let publisher = processor.publisher();
    recursive::finish_transfer(
        recursive::CommandReport::new(&publisher, request.quiet),
        std::ffi::OsStr::new("source"),
        request,
        &Completion::Finished(Box::new(finished)),
    )
    .expect("status")
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_walk_descends_directories_and_uploads_only_files() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("sub")).expect("tree");
    fs::write(tree.join("top.txt"), b"top").expect("top");
    fs::write(tree.join("sub/file.txt"), b"file").expect("file");
    std::os::unix::fs::symlink("sub", tree.join("linked")).expect("directory link");
    let request = request(&tree);
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert_eq!(
        walked.keys,
        [
            "prefix/linked/file.txt",
            "prefix/sub/file.txt",
            "prefix/top.txt"
        ]
    );
    assert!(walked.warnings.is_empty());
    assert_eq!(status(&request, walked.finished), 0);
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_warns_for_each_source_it_skips_and_exits_2() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir(&tree).expect("tree");
    std::os::unix::fs::symlink("/dev/null", tree.join("device")).expect("device link");
    std::os::unix::fs::symlink("missing.txt", tree.join("broken")).expect("broken link");
    let request = request(&tree);
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(walked.keys.is_empty());
    let root = tree.display();
    let mut warnings = walked.warnings;
    warnings.sort();
    assert_eq!(
        warnings,
        [
            format!("warning: Skipping file {root}/broken. File does not exist.\n"),
            format!(
                "warning: Skipping file {root}/device. File is character special device, \
                 block special device, FIFO, or socket.\n"
            ),
        ]
    );
    assert_eq!((walked.finished.failed, walked.finished.warned), (0, 2));
    assert_eq!(status(&request, walked.finished), 2);
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_walk_skips_a_subdirectory_it_cannot_open() {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("blocked")).expect("tree");
    fs::write(tree.join("top.txt"), b"top").expect("top");
    fs::write(tree.join("blocked/hidden.txt"), b"hidden").expect("hidden");
    fs::set_permissions(tree.join("blocked"), fs::Permissions::from_mode(0o000))
        .expect("deny access");
    // A privileged user opens it anyway; the case needs denied access.
    let denied = fs::read_dir(tree.join("blocked")).is_err();
    let request = request(&tree);
    let walked = walk_tree(&request, &interrupt::State::new());
    fs::set_permissions(tree.join("blocked"), fs::Permissions::from_mode(0o700))
        .expect("restore access");
    if !denied {
        return;
    }
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert_eq!(walked.keys, ["prefix/top.txt"]);
    assert_eq!(
        walked.warnings,
        [format!(
            "warning: Skipping file {}/blocked. File/Directory is not readable.\n",
            tree.display()
        )]
    );
    assert_eq!(walked.finished.warned, 1);
    assert_eq!(status(&request, walked.finished), 2);
}

#[derive(Debug, Default)]
struct Ordered(Mutex<Vec<String>>);
impl Ordered {
    fn push(&self, line: String) {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push(line);
    }
}
impl Operations for Ordered {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, path: &Path) -> transfer::SourceInspection {
        transfer::inspect_upload_source(path)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        completion: Arc<dyn Callbacks>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        self.push(format!("upload: {}", String::from_utf8_lossy(&job.raw_key)));
        completion.finish(crt::s3::TransferResult::default());
        Ok(Box::new(Sent(completion)))
    }
    fn finalize(&self, _: &Job, _: &crt::s3::TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}
impl Sink for Ordered {
    fn emit(&self, event: Event) -> Result<(), String> {
        if event.text.starts_with(b"warning:") {
            self.push(String::from_utf8_lossy(&event.text).into_owned());
        }
        Ok(())
    }
}

fn walk_in_order(
    request: &TransferRequest,
    list: impl Fn(&Path) -> io::Result<ReadDir>,
) -> (Result<(), String>, Vec<String>, Finished) {
    let ordered = Arc::new(Ordered::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/work".into(),
        ordered.clone(),
        ordered.clone(),
    );
    let Some(LocalRoot::Directory(source)) = open_local_root(request).expect("walk root") else {
        panic!("the walk lists its root");
    };
    let state = interrupt::State::new();
    let walk = Walk {
        request,
        scheduler: &scheduler,
        state: &state,
        list,
    };
    let outcome = walk.run(source);
    scheduler.drain();
    let log = std::mem::take(
        &mut *ordered
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner),
    );
    (outcome, log, scheduler.finished())
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_walk_warns_as_it_lists_and_uploads_in_sorted_order() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("a")).expect("tree");
    std::os::unix::fs::symlink("missing", tree.join("c-link")).expect("broken link");
    fs::write(tree.join("b"), b"b").expect("b");
    fs::write(tree.join("a/x"), b"x").expect("x");
    fs::write(tree.join("a.txt"), b"a").expect("a.txt");
    let request = request(&tree);
    let (outcome, log, finished) = walk_in_order(&request, |path| fs::read_dir(path));
    assert_eq!(outcome, Ok(()));
    assert_eq!(
        log,
        [
            format!(
                "warning: Skipping file {}/c-link. File does not exist.\n",
                tree.display()
            ),
            "upload: prefix/a.txt".into(),
            "upload: prefix/a/x".into(),
            "upload: prefix/b".into(),
        ]
    );
    assert_eq!((finished.failed, finished.warned), (0, 1));
}

#[test]
fn a_recursive_upload_walk_skips_entries_removed_after_their_listing() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("a")).expect("tree");
    fs::create_dir_all(tree.join("c")).expect("c");
    fs::write(tree.join("a").join("x"), b"x").expect("x");
    fs::write(tree.join("b.txt"), b"b").expect("b.txt");
    fs::write(tree.join("c").join("f"), b"f").expect("f");
    fs::write(tree.join("d.txt"), b"d").expect("d.txt");
    let request = request(&tree);
    let (outcome, log, finished) = walk_in_order(&request, |path| {
        if path.ends_with("a") {
            fs::remove_file(tree.join("b.txt")).expect("remove b.txt");
            fs::remove_dir_all(tree.join("c")).expect("remove c");
        }
        fs::read_dir(path)
    });
    assert_eq!(outcome, Ok(()));
    let separator = std::path::MAIN_SEPARATOR;
    let root = request.local_root.display();
    assert_eq!(
        log,
        [
            "upload: prefix/a/x".into(),
            format!("warning: Skipping file {root}b.txt. File does not exist.\n"),
            format!("warning: Skipping file {root}c{separator}. File does not exist.\n"),
            "upload: prefix/d.txt".into(),
        ]
    );
    assert_eq!((finished.failed, finished.warned), (0, 2));
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_walk_skips_a_link_to_an_overlong_name_as_missing() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("sub")).expect("tree");
    fs::write(tree.join("sub/file.txt"), b"file").expect("file");
    std::os::unix::fs::symlink("x".repeat(256), tree.join("sub/long-link")).expect("long link");
    let request = request(&tree);
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert_eq!(walked.keys, ["prefix/sub/file.txt"]);
    assert_eq!(
        walked.warnings,
        [format!(
            "warning: Skipping file {}/sub/long-link. File does not exist.\n",
            tree.display()
        )]
    );
    assert_eq!(status(&request, walked.finished), 2);
}

#[cfg(unix)]
#[test]
fn an_upload_walk_stops_at_a_symlink_loop_with_one_warning() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("t")).expect("tree");
    fs::write(tree.join("t/b.txt"), b"payload").expect("file");
    std::os::unix::fs::symlink(".", tree.join("t/loop")).expect("loop");
    let request = request(&tree);
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    let [warning] = walked.warnings.as_slice() else {
        panic!("one warning: {:?}", walked.warnings);
    };
    let prefix = format!("warning: Skipping file {}/t/", tree.display());
    let loops = warning
        .strip_prefix(&prefix)
        .and_then(|rest| rest.strip_suffix(". File does not exist.\n"))
        .expect("a missing link below the tree");
    let depth = loops.split('/').count();
    assert_eq!(loops, vec!["loop"; depth].join("/"));
    assert!((8..=64).contains(&depth), "{depth}");
    let mut expected: Vec<_> = (0..depth)
        .map(|level| format!("prefix/t/{}b.txt", "loop/".repeat(level)))
        .collect();
    expected.sort();
    assert_eq!(walked.keys, expected);
    assert_eq!(status(&request, walked.finished), 2);
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_stops_at_a_directory_whose_path_is_too_long() {
    let directory = Directory::new();
    let mut tree = DeepTree::new(&directory.0.join("tree"));
    let root = tree.path.clone();
    let near = tree.descend_near(PATH_BYTES_MAX - 2);
    tree.descend(&near);
    let name = "d".repeat(250);
    tree.descend(&name);
    let warning = format!(
        "warning: Skipping file {}. File does not exist.\n",
        tree.path.display()
    );
    for _ in 0..4 {
        tree.write_file("file.txt", b"x");
        tree.descend(&name);
    }
    let request = request(&root);
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty());
    assert_eq!(walked.warnings, [warning]);
    assert_eq!(status(&request, walked.finished), 2);
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_skips_a_directory_one_byte_short_of_the_path_limit() {
    let directory = Directory::new();
    let mut tree = DeepTree::new(&directory.0.join("tree"));
    let root = tree.path.clone();
    let near = tree.descend_near(PATH_BYTES_MAX - 1);
    tree.descend(&near);
    let warning = format!(
        "warning: Skipping file {}/. File does not exist.\n",
        tree.path.display()
    );
    let request = request(&root);
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty());
    assert_eq!(walked.warnings, [warning]);
    assert_eq!(status(&request, walked.finished), 2);
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_warns_of_an_unreadable_directory_one_byte_short_of_the_path_limit() {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new();
    let mut tree = DeepTree::new(&directory.0.join("tree"));
    let root = tree.path.clone();
    let near = tree.descend_near(PATH_BYTES_MAX - 1);
    let blocked = tree.path.join(&near);
    tree.make_directory(&near, 0o000);
    // A privileged user opens it anyway; the case needs denied access.
    let denied = fs::read_dir(&blocked).is_err();
    let request = request(&root);
    let walked = walk_tree(&request, &interrupt::State::new());
    fs::set_permissions(&blocked, fs::Permissions::from_mode(0o700)).expect("restore access");
    if !denied {
        return;
    }
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty());
    assert_eq!(
        walked.warnings,
        [format!(
            "warning: Skipping file {}. File/Directory is not readable.\n",
            blocked.display()
        )]
    );
    assert_eq!(status(&request, walked.finished), 2);
}

#[cfg(unix)]
const PATH_BYTES_MAX: usize = libc::PATH_MAX as usize;

#[cfg(unix)]
#[derive(Debug)]
struct DeepTree {
    path: PathBuf,
    directory: std::os::fd::OwnedFd,
}
#[cfg(unix)]
impl DeepTree {
    const NAME_BYTES_MAX: usize = 255;

    fn new(root: &Path) -> Self {
        fs::create_dir(root).expect("tree root");
        // The kernel counts the resolved path against the limit, and macOS's
        // temporary directory is under `/var`, a link to `/private/var`, so
        // levels sized against the unresolved path would cross it early.
        let root = fs::canonicalize(root).expect("canonical tree root");
        let directory = fs::File::open(&root).expect("tree root handle").into();
        Self {
            path: root,
            directory,
        }
    }

    fn make_directory(&self, name: &str, mode: libc::mode_t) {
        use std::os::fd::AsRawFd;
        let name = std::ffi::CString::new(name).expect("directory name");
        // SAFETY: the descriptor is open and `name` is NUL-terminated.
        let made = unsafe { libc::mkdirat(self.directory.as_raw_fd(), name.as_ptr(), mode) };
        assert_eq!(made, 0, "{}", io::Error::last_os_error());
    }

    fn open(&self, name: &str, flags: libc::c_int) -> std::os::fd::OwnedFd {
        use std::os::fd::{AsRawFd, FromRawFd};
        let name = std::ffi::CString::new(name).expect("entry name");
        // SAFETY: the descriptor is open and `name` is NUL-terminated.
        let opened = unsafe {
            libc::openat(
                self.directory.as_raw_fd(),
                name.as_ptr(),
                flags | libc::O_CLOEXEC,
                0o600,
            )
        };
        assert!(opened >= 0, "{}", io::Error::last_os_error());
        // SAFETY: `openat` returned a new descriptor nothing else owns.
        unsafe { std::os::fd::OwnedFd::from_raw_fd(opened) }
    }

    fn descend(&mut self, name: &str) {
        self.make_directory(name, 0o700);
        self.directory = self.open(name, libc::O_RDONLY | libc::O_DIRECTORY);
        self.path.push(name);
    }

    fn write_file(&self, name: &str, data: &[u8]) {
        use std::io::Write;
        let file = self.open(name, libc::O_WRONLY | libc::O_CREAT | libc::O_EXCL);
        fs::File::from(file).write_all(data).expect("file contents");
    }

    fn descend_near(&mut self, path_bytes: usize) -> String {
        let name = "d".repeat(250);
        assert!(self.len() + 1 < path_bytes);
        for _ in 0..=path_bytes / (name.len() + 1) {
            let rest = path_bytes - self.len() - 1;
            if rest <= Self::NAME_BYTES_MAX {
                return "e".repeat(rest);
            }
            self.descend(&name);
        }
        panic!("the tree never came within a name of {path_bytes} bytes");
    }

    fn len(&self) -> usize {
        self.path.as_os_str().len()
    }
}

#[test]
fn a_regular_file_walk_root_is_skipped_by_the_producer() {
    let directory = Directory::new();
    let file = directory.0.join("source.txt");
    fs::write(&file, b"contents").expect("source");
    let request = request(&file);
    assert!(matches!(
        open_local_root(&request).expect("not a directory"),
        Some(LocalRoot::Skipped(SourceSkip::Missing))
    ));
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty());
    assert_eq!(
        walked.warnings,
        [format!(
            "warning: Skipping file {}{}. File does not exist.\n",
            file.display(),
            std::path::MAIN_SEPARATOR
        )]
    );
    assert_eq!(status(&request, walked.finished), 2);
    assert_eq!(fs::read(&file).expect("source kept"), b"contents");
}

#[test]
fn only_an_upload_opens_its_local_root() {
    let directory = Directory::new();
    let missing = request(&directory.0.join("missing"));
    assert!(matches!(
        open_local_root(&missing).expect("missing root"),
        Some(LocalRoot::Skipped(SourceSkip::Missing))
    ));
    let file = directory.0.join("destination.txt");
    fs::write(&file, b"kept").expect("destination");
    let download = TransferRequest {
        direction: transfer::Direction::Download,
        ..request(&file)
    };
    assert!(open_local_root(&download).expect("no source").is_none());
    assert_eq!(fs::read(&file).expect("destination kept"), b"kept");
    let single = TransferRequest {
        object: Some(SingleObject::default()),
        ..missing
    };
    assert!(open_local_root(&single).expect("no source").is_none());
}

#[cfg(unix)]
#[test]
fn a_walk_root_it_cannot_list_is_skipped_by_the_producer() {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(&tree).expect("tree");
    fs::write(tree.join("hidden.txt"), b"hidden").expect("hidden");
    fs::set_permissions(&tree, fs::Permissions::from_mode(0o000)).expect("deny access");
    // A privileged user opens it anyway; the case needs denied access.
    let denied = fs::read_dir(&tree).is_err();
    let request = request(&tree);
    let walked = walk_tree(&request, &interrupt::State::new());
    fs::set_permissions(&tree, fs::Permissions::from_mode(0o700)).expect("restore access");
    if !denied {
        return;
    }
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty());
    assert_eq!(
        walked.warnings,
        [format!(
            "warning: Skipping file {}{}. File/Directory is not readable.\n",
            tree.display(),
            std::path::MAIN_SEPARATOR
        )]
    );
    assert_eq!((walked.finished.failed, walked.finished.warned), (0, 1));
    assert_eq!(status(&request, walked.finished), 2);
}

#[cfg(unix)]
#[test]
fn a_walk_root_below_an_unsearchable_directory_is_skipped_as_missing() {
    use std::os::unix::fs::PermissionsExt;
    let directory = Directory::new();
    let blocked = directory.0.join("blocked");
    let root = blocked.join("root");
    fs::create_dir_all(&root).expect("root");
    fs::write(root.join("hidden.txt"), b"hidden").expect("hidden");
    fs::set_permissions(&blocked, fs::Permissions::from_mode(0o000)).expect("deny search");
    // A privileged user stats it anyway; the case needs denied access.
    let denied = fs::metadata(&root).is_err();
    let request = request(&root);
    let walked = walk_tree(&request, &interrupt::State::new());
    fs::set_permissions(&blocked, fs::Permissions::from_mode(0o700)).expect("restore search");
    if !denied {
        return;
    }
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty());
    assert_eq!(
        walked.warnings,
        [format!(
            "warning: Skipping file {}{}. File does not exist.\n",
            root.display(),
            std::path::MAIN_SEPARATOR
        )]
    );
    assert_eq!((walked.finished.failed, walked.finished.warned), (0, 1));
    assert_eq!(status(&request, walked.finished), 2);
}

#[test]
fn an_interrupted_walk_names_nothing_more() {
    let directory = Directory::new();
    fs::write(directory.0.join("file.txt"), b"file").expect("file");
    let state = interrupt::State::new();
    state.request();
    let walked = walk_tree(&request(&directory.0), &state);
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty());
}

#[derive(Debug)]
struct Unpublishable;
impl Sink for Unpublishable {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: crate::results::Event, _: bool) -> Result<(), String> {
        match event {
            crate::results::Event::Queued { .. } => Err("WriteFailed".into()),
            _ => Ok(()),
        }
    }
}

#[test]
fn an_object_upload_hands_its_one_entry_over_unsized_and_completes() {
    let directory = Directory::new();
    let source = directory.0.join("a b.txt");
    fs::write(&source, b"12345").expect("source");
    let object = SingleObject {
        key: b"prefix/a b.txt".to_vec(),
        local_path: source.clone(),
        local: Default::default(),
        remote: None,
    };
    let request = TransferRequest {
        object: Some(object.clone()),
        collect_stats: true,
        ..request(&directory.0)
    };
    let operations = Arc::new(Uploads::default());
    let scheduler = Scheduler::new(
        request,
        "/work".into(),
        operations.clone(),
        Arc::new(Warnings::default()),
    );
    let outcome = produce_object(&scheduler, &object);
    scheduler.drain();
    assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
    assert!(outcome.exhausted(false));
    assert_eq!(
        *operations
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner),
        ["prefix/a b.txt"]
    );
    let stats = scheduler.finished().stats.expect("stats");
    assert_eq!((stats.submitted, stats.succeeded), (1, 1));
}

fn filter(filters: &[(FilterKind, &str)], roots: [&Path; 2], prefix: &[u8]) -> Filter {
    let filters: Vec<_> = filters
        .iter()
        .map(|&(kind, pattern)| (kind, pattern.to_owned()))
        .collect();
    let [source, destination] = roots.map(|root| root.as_os_str().as_encoded_bytes());
    Filter::new(
        &filters,
        Roots {
            source,
            destination,
        },
        prefix,
    )
}

#[cfg(unix)]
#[test]
fn a_recursive_upload_walk_filters_files_after_warning_of_skipped_sources() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("sub")).expect("tree");
    fs::write(tree.join("top.txt"), b"top").expect("top");
    fs::write(tree.join("sub/file.txt"), b"file").expect("file");
    fs::write(tree.join("sub/skip.bin"), b"skip").expect("skip");
    std::os::unix::fs::symlink("absent", tree.join("broken")).expect("broken link");
    let mut prefix = tree.clone().into_os_string();
    prefix.push("/");
    let request = TransferRequest {
        filter: filter(
            &[(Exclude, "*.bin"), (Exclude, "broken")],
            [&tree, Path::new("bucket/prefix/")],
            prefix.as_encoded_bytes(),
        ),
        ..request(&tree)
    };
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert_eq!(walked.keys, ["prefix/sub/file.txt", "prefix/top.txt"]);
    assert_eq!(walked.warnings.len(), 1, "{:?}", walked.warnings);
    assert!(walked.warnings[0].contains("broken. File does not exist."));
    assert_eq!(status(&request, walked.finished), 2);
}

#[test]
fn an_excluded_object_upload_is_only_inspected() {
    let directory = Directory::new();
    let present = directory.0.join("a.txt");
    fs::write(&present, b"12345").expect("source");
    for (source, warned) in [(present, 0), (directory.0.join("missing.txt"), 1)] {
        let object = SingleObject {
            key: b"key".to_vec(),
            local_path: source,
            local: Default::default(),
            remote: None,
        };
        let request = TransferRequest {
            object: Some(object.clone()),
            filter: filter(&[(Exclude, "*")], [&directory.0, Path::new("bucket/")], b""),
            ..request(&directory.0)
        };
        let operations = Arc::new(Uploads::default());
        let warnings = Arc::new(Warnings::default());
        let scheduler = Scheduler::new(
            request,
            "/work".into(),
            operations.clone(),
            warnings.clone(),
        );
        let outcome = produce_object(&scheduler, &object);
        scheduler.drain();
        assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
        assert!(outcome.exhausted(false));
        assert!(
            operations
                .0
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .is_empty()
        );
        let finished = scheduler.finished();
        assert_eq!((finished.failed, finished.warned), (0, warned));
        assert_eq!(
            warnings
                .0
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .len() as u64,
            warned
        );
    }
}

#[test]
fn an_object_the_engine_cannot_take_stops_the_producer_unexhausted() {
    let directory = Directory::new();
    let source = directory.0.join("object");
    fs::write(&source, b"12345").expect("source");
    let object = SingleObject {
        key: b"object".to_vec(),
        local_path: source,
        local: Default::default(),
        remote: None,
    };
    let request = TransferRequest {
        object: Some(object.clone()),
        ..request(&directory.0)
    };
    let operations = Arc::new(Uploads::default());
    let scheduler = Scheduler::new(
        request,
        "/work".into(),
        operations.clone(),
        Arc::new(Unpublishable),
    );
    let outcome = produce_object(&scheduler, &object);
    scheduler.drain();
    assert!(matches!(&outcome, ProducerOutcome::SubmitFailed(error) if error == "WriteFailed"));
    assert!(!outcome.exhausted(false));
    assert!(
        operations
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .is_empty()
    );
}

type SentDownload = (PathBuf, Option<u64>, Option<i64>, Option<Vec<u8>>);
#[derive(Debug, Default)]
struct Downloads(Mutex<Vec<SentDownload>>);
impl Downloads {
    fn sent(&self) -> Vec<SentDownload> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone()
    }
}
impl Operations for Downloads {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, _: &Path) -> transfer::SourceInspection {
        transfer::SourceInspection::Size(0)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        completion: Arc<dyn Callbacks>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push((
                job.local_path.clone(),
                job.size,
                job.modified,
                job.condition.etag.clone(),
            ));
        completion.finish(crt::s3::TransferResult::default());
        Ok(Box::new(Sent(completion)))
    }
    fn finalize(&self, _: &Job, _: &crt::s3::TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}
fn download_object() -> (SingleObject, TransferRequest) {
    let object = SingleObject {
        key: b"prefix/object".to_vec(),
        local_path: "/work/object".into(),
        local: Default::default(),
        remote: Some("s3://bucket/prefix/object".into()),
    };
    let request = TransferRequest {
        direction: transfer::Direction::Download,
        object: Some(object.clone()),
        ..request(Path::new("/work"))
    };
    (object, request)
}
fn head(content_length: Option<u64>) -> HeadObjectResult {
    HeadObjectResult {
        transfer: TransferResult {
            response_status: 200,
            ..TransferResult::default()
        },
        content_length,
        last_modified_epoch_seconds: Some(946_684_801),
        ..HeadObjectResult::default()
    }
}

#[test]
fn an_object_download_heads_its_source_before_the_engine_takes_it() {
    let failed = || TransferResult {
        error_code: 14_361,
        response_status: 404,
        ..TransferResult::default()
    };
    let canceled = || TransferResult {
        error_code: crt::s3::CANCELED_ERROR_CODE,
        canceled_by_interrupt: true,
        ..TransferResult::default()
    };
    let cases: [(Result<HeadObjectResult, Box<TransferResult>>, usize); 5] = [
        (Ok(head(Some(5))), 1),
        (Err(Box::new(failed())), 0),
        (Err(Box::new(canceled())), 0),
        (
            Ok(HeadObjectResult {
                transfer: failed(),
                ..head(None)
            }),
            0,
        ),
        (
            Ok(HeadObjectResult {
                transfer: canceled(),
                ..head(None)
            }),
            0,
        ),
    ];
    for (result, sent) in cases {
        let (object, request) = download_object();
        let operations = Arc::new(Downloads::default());
        let scheduler = Scheduler::new(
            request,
            "/work".into(),
            operations.clone(),
            Arc::new(Warnings::default()),
        );
        let mut heads = 0;
        let outcome = produce_download_object(&scheduler, &object, || {
            heads += 1;
            result
        });
        scheduler.drain();
        assert_eq!(heads, 1);
        let jobs = operations.sent();
        assert_eq!(jobs.len(), sent);
        match &outcome {
            ProducerOutcome::ObjectCompleted => {
                assert_eq!(
                    jobs,
                    [("/work/object".into(), Some(5), Some(946_684_801), None)]
                )
            }
            ProducerOutcome::HeadFailed(result) => assert_eq!(result.response_status, 404),
            ProducerOutcome::HeadCanceled => {}
            outcome => panic!("unexpected outcome {outcome:?}"),
        }
        assert_eq!(
            outcome.exhausted(false),
            matches!(outcome, ProducerOutcome::ObjectCompleted)
        );
    }
}

#[test]
fn an_object_download_without_a_length_fails_in_place_of_its_request() {
    let (object, request) = download_object();
    let operations = Arc::new(Downloads::default());
    let scheduler = Scheduler::new(
        request,
        "/work".into(),
        operations.clone(),
        Arc::new(Warnings::default()),
    );
    let outcome = produce_download_object(&scheduler, &object, || Ok(head(None)));
    scheduler.drain();
    assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
    assert!(operations.sent().is_empty());
    assert_eq!(scheduler.finished().failed, 1);
}

#[test]
fn an_excluded_object_download_is_headed_and_named_nothing() {
    for (content_length, failed) in [(Some(5), 0), (None, 1)] {
        let (object, request) = download_object();
        let request = TransferRequest {
            filter: filter(
                &[(Exclude, "object")],
                [Path::new("bucket/prefix"), Path::new("/work")],
                b"bucket/",
            ),
            ..request
        };
        let operations = Arc::new(Downloads::default());
        let scheduler = Scheduler::new(
            request,
            "/work".into(),
            operations.clone(),
            Arc::new(Warnings::default()),
        );
        let mut heads = 0;
        let outcome = produce_download_object(&scheduler, &object, || {
            heads += 1;
            Ok(head(content_length))
        });
        scheduler.drain();
        assert_eq!(heads, 1);
        assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
        assert!(operations.sent().is_empty());
        assert_eq!(scheduler.finished().failed, failed);
    }
}

#[test]
fn an_object_download_whose_queued_result_was_lost_sends_no_request() {
    let (object, request) = download_object();
    let operations = Arc::new(Downloads::default());
    let scheduler = Scheduler::new(
        request,
        "/work".into(),
        operations.clone(),
        Arc::new(Unpublishable),
    );
    let outcome = produce_download_object(&scheduler, &object, || Ok(head(Some(5))));
    scheduler.drain();
    assert!(matches!(&outcome, ProducerOutcome::SubmitFailed(error) if error == "WriteFailed"));
    assert!(!outcome.exhausted(false));
    assert!(operations.sent().is_empty());
    assert_eq!(scheduler.finished().fatal.as_deref(), Some("WriteFailed"));
}

#[test]
fn an_object_download_hands_over_its_head_etag_within_the_bound() {
    let original = b"\"original\"".to_vec();
    let long = vec![b'e'; crt::s3::ETAG_MAX + 1];
    for (etag, expected) in [(original.clone(), Some(original)), (long, None)] {
        let (object, request) = download_object();
        let operations = Arc::new(Downloads::default());
        let scheduler = Scheduler::new(
            request,
            "/work".into(),
            operations.clone(),
            Arc::new(Warnings::default()),
        );
        let mut head = head(Some(5));
        head.etag.set(&etag);
        let outcome = produce_download_object(&scheduler, &object, || Ok(head));
        scheduler.drain();
        assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
        assert_eq!(
            operations.sent(),
            [("/work/object".into(), Some(5), Some(946_684_801), expected)]
        );
    }
}

#[test]
fn a_head_without_last_modified_fails_before_the_engine_unless_it_lacks_a_length() {
    for (length, failed) in [(Some(5), 0), (None, 1)] {
        let (object, request) = download_object();
        let operations = Arc::new(Downloads::default());
        let scheduler = Scheduler::new(
            request,
            "/work".into(),
            operations.clone(),
            Arc::new(Warnings::default()),
        );
        let head = HeadObjectResult {
            last_modified_epoch_seconds: None,
            ..head(length)
        };
        let outcome = produce_download_object(&scheduler, &object, || Ok(head));
        scheduler.drain();
        assert_eq!(
            matches!(outcome, ProducerOutcome::HeadMissingLastModified),
            length.is_some()
        );
        assert_eq!(outcome.exhausted(false), length.is_none());
        assert!(operations.sent().is_empty());
        assert_eq!(scheduler.finished().failed, failed);
    }
}

#[derive(Debug, Default)]
struct Requested(Mutex<Vec<(Vec<u8>, String)>>);
impl Operations for Requested {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, _: &Path) -> transfer::SourceInspection {
        transfer::SourceInspection::Size(0)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        completion: Arc<dyn Callbacks>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push((job.raw_key.clone(), job.request_key.clone()));
        completion.finish(crt::s3::TransferResult::default());
        Ok(Box::new(Sent(completion)))
    }
    fn finalize(&self, _: &Job, _: &crt::s3::TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), crate::scheduler::SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}

#[test]
fn an_object_download_hands_over_its_archive_state_and_destination_outcome() {
    use crate::scheduler::EntryLocal;
    use transfer::GlacierPolicy::{Transfer, Warn};
    let key = b"dir/a b%.txt";
    let glacier = transfer::glacier_warning(b"s3://bucket/dir/a b%.txt");
    let escape = transfer::parent_escape_warning("..").into_bytes();
    let cases = [
        (Warn, EntryLocal::Resolved, Some(glacier.clone())),
        (Warn, EntryLocal::ParentEscape("..".into()), Some(glacier)),
        (
            Transfer,
            EntryLocal::ParentEscape("..".into()),
            Some(escape),
        ),
        (Transfer, EntryLocal::Resolved, None),
    ];
    for (policy, local, warning) in cases {
        let (mut object, mut request) = download_object();
        object.key = key.to_vec();
        object.local = local.clone();
        request.object = Some(object.clone());
        request.glacier = policy;
        let operations = Arc::new(Requested::default());
        let warnings = Arc::new(Warnings::default());
        let scheduler = Scheduler::new(
            request,
            "/work".into(),
            operations.clone(),
            warnings.clone(),
        );
        let mut head = head(Some(5));
        head.archive = crt::s3::ArchiveState::from_storage_class(b"GLACIER");
        let outcome = produce_download_object(&scheduler, &object, || Ok(head));
        scheduler.drain();
        assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
        let printed = warnings
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone();
        let expected: Vec<String> = warning
            .iter()
            .map(|text| format!("{}\n", String::from_utf8_lossy(text)))
            .collect();
        assert_eq!(printed, expected, "{policy:?} {local:?}");
        let requested = operations
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone();
        let sent = warning
            .is_none()
            .then(|| (key.to_vec(), "dir/a%20b%25.txt".to_owned()));
        assert_eq!(requested, Vec::from_iter(sent), "{policy:?} {local:?}");
    }
}

#[derive(Debug, Default)]
struct Lines(Mutex<Vec<String>>);
impl Lines {
    fn take(&self) -> Vec<String> {
        std::mem::take(
            &mut *self
                .0
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
        )
    }
}
impl Sink for Lines {
    fn emit(&self, event: Event) -> Result<(), String> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .push(String::from_utf8_lossy(&event.text).into_owned());
        Ok(())
    }
}

fn delete_object(
    key: &str,
    delete: recursive::DeleteOptions,
    filters: &[(FilterKind, String)],
) -> (SingleObject, TransferRequest) {
    let object = SingleObject {
        key: key.as_bytes().to_vec(),
        ..SingleObject::default()
    };
    let roots = Roots {
        source: b"bucket/dir",
        destination: b"bucket/dir",
    };
    let request = TransferRequest {
        direction: transfer::Direction::Delete,
        prefix: Vec::new(),
        local_root: PathBuf::new(),
        object: Some(object.clone()),
        filter: Filter::new(filters, roots, b"bucket/"),
        delete,
        ..request(Path::new("/unused"))
    };
    (object, request)
}

fn produce_delete(
    object: &SingleObject,
    request: TransferRequest,
) -> (ProducerOutcome, Vec<String>, Vec<String>) {
    let operations = Arc::new(Uploads::default());
    let lines = Arc::new(Lines::default());
    let scheduler = Scheduler::new(request, PathBuf::new(), operations.clone(), lines.clone());
    let outcome = produce_delete_object(&scheduler, object);
    scheduler.drain();
    let sent = std::mem::take(
        &mut *operations
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner),
    );
    (outcome, sent, lines.take())
}

#[test]
fn a_single_delete_sends_its_key_and_reports_the_object() {
    let (object, request) = delete_object("dir/a b.txt", Default::default(), &[]);
    let (outcome, sent, lines) = produce_delete(&object, request);
    assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
    assert_eq!(sent, ["dir/a b.txt"]);
    assert_eq!(lines, ["delete: s3://bucket/dir/a b.txt\n"]);
}

#[test]
fn a_single_delete_the_filters_leave_out_sends_nothing() {
    let filters = [(Exclude, "*".to_owned())];
    let (object, request) = delete_object("dir/a.txt", Default::default(), &filters);
    let (outcome, sent, lines) = produce_delete(&object, request);
    assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
    assert!(sent.is_empty());
    assert!(lines.is_empty());
}

#[test]
fn a_dry_run_delete_reports_the_object_and_sends_nothing() {
    let (object, mut request) = delete_object("dir/a.txt", Default::default(), &[]);
    request.dryrun = true;
    let (outcome, sent, lines) = produce_delete(&object, request);
    assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
    assert!(sent.is_empty());
    assert_eq!(lines, ["(dryrun) delete: s3://bucket/dir/a.txt\n"]);
}

#[test]
fn a_delete_opens_no_local_root() {
    let directory = Directory::new();
    let (_, mut request) = delete_object("dir/a.txt", Default::default(), &[]);
    request.object = None;
    request.local_root = directory.0.clone();
    assert!(open_local_root(&request).expect("no root").is_none());
}

#[derive(Debug, Default)]
struct Listed {
    entries: std::collections::VecDeque<comparator::Entry<Vec<u8>>>,
    pulls: usize,
    failing: bool,
}
impl Listed {
    fn new(entries: &[(&str, u64, i64)]) -> Self {
        Self {
            entries: entries
                .iter()
                .map(|&(name, size, seconds)| comparator::Entry {
                    name: name.as_bytes().to_vec(),
                    size,
                    modified: Modified::from_epoch_seconds(seconds),
                })
                .collect(),
            ..Self::default()
        }
    }
}
impl Destination for Listed {
    type Name = Vec<u8>;
    type Error = &'static str;
    fn next_entry(&mut self) -> Result<Option<comparator::Entry<Vec<u8>>>, &'static str> {
        self.pulls += 1;
        if self.failing {
            return Err("listing failed");
        }
        Ok(self.entries.pop_front())
    }
}
fn write_modified(path: &Path, body: &[u8], seconds: u64) {
    fs::create_dir_all(path.parent().expect("parent")).expect("parent directory");
    fs::write(path, body).expect("file");
    let time = std::time::UNIX_EPOCH + std::time::Duration::from_secs(seconds);
    fs::File::options()
        .write(true)
        .open(path)
        .and_then(|file| file.set_modified(time))
        .expect("mtime");
}
struct SyncWalked {
    outcome: Result<ProducerOutcome, &'static str>,
    keys: Vec<String>,
    warnings: Vec<String>,
    destination: Listed,
}
fn sync_walk_tree(
    request: &TransferRequest,
    destination: Listed,
    state: &interrupt::State,
) -> SyncWalked {
    let operations = Arc::new(Uploads::default());
    let warnings = Arc::new(Warnings::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/work".into(),
        operations.clone(),
        warnings.clone(),
    );
    let source = open_local_root(request)
        .expect("walk root")
        .expect("a walk opens its root");
    let strategies = crate::sync::Strategies::default();
    let mut comparator = Comparator::new(strategies, comparator::LocalSide::Source, destination);
    let outcome = produce_sync_walk(request, &scheduler, source, state, &mut comparator);
    scheduler.drain();
    let take = |lines: &Mutex<Vec<String>>| {
        let mut lines = std::mem::take(
            &mut *lines
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
        );
        lines.sort();
        lines
    };
    SyncWalked {
        outcome,
        keys: take(&operations.0),
        warnings: take(&warnings.0),
        destination: comparator.into_destination(),
    }
}

#[test]
fn a_sync_walk_uploads_only_the_files_its_comparator_pairs_for_transfer() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    for name in ["a.txt", "b.txt", "sub/c.txt", "z.txt"] {
        write_modified(&tree.join(name), b"four", 100);
    }
    let destination = Listed::new(&[
        ("a.txt", 4, 200),
        ("b.txt", 5, 200),
        ("only-remote.txt", 1, 0),
        ("sub/c.txt", 4, 50),
        ("zz.txt", 1, 0),
    ]);
    let request = request(&tree);
    let walked = sync_walk_tree(&request, destination, &interrupt::State::new());
    assert!(matches!(walked.outcome, Ok(ProducerOutcome::WalkCompleted)));
    assert_eq!(
        walked.keys,
        ["prefix/b.txt", "prefix/sub/c.txt", "prefix/z.txt"]
    );
    assert!(walked.warnings.is_empty());
    assert!(walked.destination.entries.is_empty());
    assert_eq!(walked.destination.pulls, 6);
}

fn invalid_timestamp_line() -> String {
    format!(
        "{}\n",
        String::from_utf8_lossy(transfer::INVALID_TIMESTAMP_WARNING)
    )
}

#[test]
fn a_sync_walk_warns_of_an_unreadable_mtime_and_compares_the_epoch() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    for name in ["after.txt", "before.txt"] {
        write_modified(&tree.join(name), b"four", 100);
        if !comparator::set_unreadable_mtime(&tree.join(name)) {
            return;
        }
    }
    let destination = Listed::new(&[("after.txt", 4, 86_400), ("before.txt", 4, -86_400)]);
    let walked = sync_walk_tree(&request(&tree), destination, &interrupt::State::new());
    assert!(matches!(walked.outcome, Ok(ProducerOutcome::WalkCompleted)));
    assert_eq!(walked.keys, ["prefix/before.txt"]);
    assert_eq!(
        walked.warnings,
        [invalid_timestamp_line(), invalid_timestamp_line()]
    );
}

#[test]
fn a_sync_walk_ends_with_its_destination_s_failure() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    write_modified(&tree.join("a.txt"), b"a", 100);
    let mut destination = Listed::new(&[]);
    destination.failing = true;
    let walked = sync_walk_tree(&request(&tree), destination, &interrupt::State::new());
    assert!(matches!(walked.outcome, Err("listing failed")));
    assert!(walked.keys.is_empty());
    assert_eq!(walked.destination.pulls, 1);
}

#[test]
fn a_skipped_sync_root_still_lists_the_destination() {
    let directory = Directory::new();
    let file = directory.0.join("source.txt");
    fs::write(&file, b"contents").expect("source");
    let destination = Listed::new(&[("a.txt", 1, 0), ("b.txt", 1, 0)]);
    let walked = sync_walk_tree(&request(&file), destination, &interrupt::State::new());
    assert!(matches!(walked.outcome, Ok(ProducerOutcome::WalkCompleted)));
    assert!(walked.keys.is_empty());
    assert_eq!(walked.warnings.len(), 1);
    assert_eq!(walked.destination.pulls, 3);
}

#[test]
fn an_interrupted_sync_walk_lists_no_more_of_the_destination() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    write_modified(&tree.join("a.txt"), b"a", 100);
    let state = interrupt::State::new();
    state.request();
    let destination = Listed::new(&[("a.txt", 1, 0)]);
    let walked = sync_walk_tree(&request(&tree), destination, &state);
    assert!(matches!(walked.outcome, Ok(ProducerOutcome::WalkCompleted)));
    assert!(walked.keys.is_empty());
    assert_eq!(walked.destination.pulls, 0);
}

fn download_destination(root: &Path) -> (TransferRequest, Arc<Scheduler>, Arc<Warnings>) {
    let request = TransferRequest {
        direction: transfer::Direction::Download,
        ..request(root)
    };
    let warnings = Arc::new(Warnings::default());
    let scheduler = Scheduler::new(
        request.clone(),
        "/work".into(),
        Arc::new(Uploads::default()),
        warnings.clone(),
    );
    (request, scheduler, warnings)
}
fn warned(warnings: &Warnings) -> Vec<String> {
    warnings
        .0
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
        .clone()
}

#[test]
fn a_download_destination_file_with_an_unreadable_mtime_has_the_epoch_s() {
    let directory = Directory::new();
    let root = directory.0.join("dest");
    write_modified(&root.join("a.txt"), b"a", 100);
    if !comparator::set_unreadable_mtime(&root.join("a.txt")) {
        return;
    }
    let (request, scheduler, warnings) = download_destination(&root);
    let state = interrupt::State::new();
    let mut destination = LocalDestination::new(&request, &scheduler, &state);
    let entry = destination.next_entry().expect("walk").expect("a.txt");
    assert_eq!((entry.size, entry.modified), (1, Modified::EPOCH));
    assert_eq!(warned(&warnings), [invalid_timestamp_line()]);
    assert!(destination.next_entry().expect("walk").is_none());
}

#[cfg(unix)]
#[test]
fn a_download_destination_is_walked_from_its_first_pull_in_upstream_s_order() {
    let directory = Directory::new();
    let root = directory.0.join("dest");
    write_modified(&root.join("a.txt"), b"a", 100);
    write_modified(&root.join("a").join("b.txt"), b"bb", 200);
    write_modified(&root.join("a-b.txt"), b"ccc", 300);
    std::os::unix::fs::symlink("missing.txt", root.join("broken")).expect("broken link");
    let (request, scheduler, warnings) = download_destination(&root);
    let state = interrupt::State::new();
    let mut destination = LocalDestination::new(&request, &scheduler, &state);
    assert!(warned(&warnings).is_empty());
    let mut entries = Vec::new();
    while let Some(entry) = destination.next_entry().expect("walk") {
        entries.push((
            std::str::from_utf8(entry.name.as_bytes())
                .expect("name")
                .to_owned(),
            entry.size,
            entry.modified,
        ));
    }
    assert_eq!(
        entries,
        [
            ("a-b.txt".to_owned(), 3, Modified::from_epoch_seconds(300)),
            ("a.txt".to_owned(), 1, Modified::from_epoch_seconds(100)),
            ("a/b.txt".to_owned(), 2, Modified::from_epoch_seconds(200)),
        ]
    );
    assert_eq!(
        warned(&warnings),
        [format!(
            "warning: Skipping file {}/broken. File does not exist.\n",
            root.display()
        )]
    );
    assert_eq!(destination.next_entry(), Ok(None));
}

#[test]
fn a_missing_download_destination_is_warned_about_and_names_nothing() {
    let directory = Directory::new();
    let root = directory.0.join("file.txt");
    fs::write(&root, b"a file").expect("file");
    let (request, scheduler, warnings) = download_destination(&root);
    let state = interrupt::State::new();
    let mut destination = LocalDestination::new(&request, &scheduler, &state);
    assert_eq!(destination.next_entry(), Ok(None));
    assert_eq!(destination.next_entry(), Ok(None));
    assert_eq!(
        warned(&warnings),
        [format!(
            "warning: Skipping file {}{}. File does not exist.\n",
            root.display(),
            std::path::MAIN_SEPARATOR
        )]
    );
}

#[cfg(unix)]
fn unfollowed(request: TransferRequest) -> TransferRequest {
    TransferRequest {
        links: transfer::LinkPolicy::from_flag(false, &request.local_root),
        ..request
    }
}

#[cfg(unix)]
#[test]
fn a_walk_that_does_not_follow_links_drops_each_one_silently() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("sub")).expect("tree");
    fs::write(tree.join("top.txt"), b"top").expect("top");
    fs::write(tree.join("sub/file.txt"), b"file").expect("file");
    std::os::unix::fs::symlink("sub", tree.join("linked")).expect("directory link");
    std::os::unix::fs::symlink("top.txt", tree.join("top-link")).expect("file link");
    std::os::unix::fs::symlink("/dev/null", tree.join("device")).expect("device link");
    std::os::unix::fs::symlink("missing.txt", tree.join("broken")).expect("broken link");
    let request = unfollowed(request(&tree));
    let walked = walk_tree(&request, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert_eq!(walked.keys, ["prefix/sub/file.txt", "prefix/top.txt"]);
    assert!(walked.warnings.is_empty());
    assert_eq!(status(&request, walked.finished), 0);
}

#[cfg(unix)]
#[test]
fn a_walk_root_that_links_to_a_directory_is_not_followed() {
    let directory = Directory::new();
    let tree = directory.0.join("tree");
    fs::create_dir_all(tree.join("sub")).expect("tree");
    fs::write(tree.join("top.txt"), b"top").expect("top");
    fs::write(tree.join("sub/deep.txt"), b"deep").expect("deep");
    fs::write(directory.0.join("file.txt"), b"file").expect("file");
    std::os::unix::fs::symlink("tree", directory.0.join("tree-link")).expect("root link");
    std::os::unix::fs::symlink("file.txt", directory.0.join("file-link")).expect("file link");
    let linked = unfollowed(request(&directory.0.join("tree-link")));
    assert!(matches!(
        open_local_root(&linked).expect("linked root"),
        Some(LocalRoot::Unfollowed)
    ));
    let walked = walk_tree(&linked, &interrupt::State::new());
    assert!(matches!(walked.outcome, ProducerOutcome::WalkCompleted));
    assert!(walked.keys.is_empty() && walked.warnings.is_empty());
    assert_eq!(status(&linked, walked.finished), 0);
    let file = unfollowed(request(&directory.0.join("file-link")));
    assert!(matches!(
        open_local_root(&file).expect("file root"),
        Some(LocalRoot::Skipped(SourceSkip::Missing))
    ));
    let below = unfollowed(request(&directory.0.join("tree-link").join("sub")));
    let walked = walk_tree(&below, &interrupt::State::new());
    assert_eq!(walked.keys, ["prefix/deep.txt"]);
}

#[cfg(unix)]
#[test]
fn a_download_destination_walk_that_does_not_follow_links_names_none() {
    let directory = Directory::new();
    let root = directory.0.join("dest");
    write_modified(&root.join("a.txt"), b"a", 100);
    write_modified(&directory.0.join("outside").join("b.txt"), b"b", 100);
    std::os::unix::fs::symlink("../outside", root.join("sub")).expect("directory link");
    std::os::unix::fs::symlink("a.txt", root.join("link.txt")).expect("file link");
    std::os::unix::fs::symlink("dest", directory.0.join("dest-link")).expect("root link");
    for (root, names) in [
        (root, &["a.txt"][..]),
        (directory.0.join("dest-link"), &[][..]),
    ] {
        let (request, _, warnings) = download_destination(&root);
        let request = unfollowed(request);
        let scheduler = Scheduler::new(
            request.clone(),
            "/work".into(),
            Arc::new(Uploads::default()),
            warnings.clone(),
        );
        let state = interrupt::State::new();
        let mut destination = LocalDestination::new(&request, &scheduler, &state);
        let mut entries = Vec::new();
        while let Some(entry) = destination.next_entry().expect("walk") {
            entries.push(String::from_utf8(entry.name.as_bytes().to_vec()).expect("name"));
        }
        assert_eq!(entries, names, "{root:?}");
        assert!(warned(&warnings).is_empty(), "{root:?}");
    }
}

#[cfg(unix)]
#[test]
fn a_single_upload_of_a_link_it_does_not_follow_names_nothing() {
    let directory = Directory::new();
    fs::create_dir(directory.0.join("dir")).expect("dir");
    fs::write(directory.0.join("dir").join("a.txt"), b"a").expect("source");
    std::os::unix::fs::symlink("dir/a.txt", directory.0.join("link.txt")).expect("file link");
    std::os::unix::fs::symlink("dir", directory.0.join("dir-link")).expect("directory link");
    std::os::unix::fs::symlink("missing", directory.0.join("broken")).expect("broken link");
    for (source, uploaded) in [
        (directory.0.join("link.txt"), &[][..]),
        (directory.0.join("broken"), &[]),
        (directory.0.join("dir-link"), &[]),
        (directory.0.join("dir-link").join("a.txt"), &["key"]),
    ] {
        let object = SingleObject {
            key: b"key".to_vec(),
            local_path: source.clone(),
            local: Default::default(),
            remote: None,
        };
        let request = TransferRequest {
            object: Some(object.clone()),
            links: transfer::LinkPolicy::from_flag(false, &source),
            ..request(&directory.0)
        };
        let operations = Arc::new(Uploads::default());
        let warnings = Arc::new(Warnings::default());
        let scheduler = Scheduler::new(
            request,
            "/work".into(),
            operations.clone(),
            warnings.clone(),
        );
        let outcome = produce_object(&scheduler, &object);
        scheduler.drain();
        assert!(matches!(outcome, ProducerOutcome::ObjectCompleted));
        assert_eq!(
            *operations
                .0
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
            uploaded,
            "{source:?}"
        );
        assert!(warned(&warnings).is_empty(), "{source:?}");
    }
}
