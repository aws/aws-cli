#![expect(
    clippy::expect_used,
    reason = "deterministic scheduler fixtures fail immediately on invalid state"
)]
use super::*;
use crate::filter::FilterKind::{Exclude, Include};
use cli_core::InterruptHook;
use std::sync::atomic::AtomicUsize;
mod publication;
mod redirect;

#[derive(Debug, Default)]
struct Output {
    events: Mutex<Vec<Event>>,
    fail: AtomicBool,
}
impl Sink for Output {
    fn emit(&self, event: Event) -> Result<(), String> {
        if self.fail.load(Ordering::Acquire) {
            return Err("WriteFailed".into());
        }
        lock(&self.events).push(event);
        Ok(())
    }
}
#[derive(Debug, Default)]
struct Gate {
    state: Mutex<(bool, bool)>,
    changed: Condvar,
}
impl Gate {
    fn enter(&self) {
        let mut state = lock(&self.state);
        state.0 = true;
        self.changed.notify_all();
        while !state.1 {
            state = wait(&self.changed, state);
        }
    }
    fn await_entered(&self) {
        let mut state = lock(&self.state);
        while !state.0 {
            state = wait(&self.changed, state);
        }
    }
    fn release(&self) {
        lock(&self.state).1 = true;
        self.changed.notify_all();
    }
}
type Submitted = (Vec<u8>, PathBuf, Option<PathBuf>, Option<u64>);
#[derive(Debug)]
struct Control {
    callbacks: Mutex<Vec<Weak<dyn Completion>>>,
    delayed: Mutex<Vec<Arc<dyn Completion>>>,
    submissions: Mutex<Vec<Submitted>>,
    request_keys: Mutex<Vec<String>>,
    parents: AtomicUsize,
    releases: AtomicUsize,
    cancels: AtomicUsize,
    discards: AtomicUsize,
    finalized: AtomicUsize,
    events: Mutex<Vec<&'static str>>,
    immediate: AtomicBool,
    reject: AtomicBool,
    parent_error: AtomicBool,
    temp_error: AtomicBool,
    random: Mutex<fn() -> io::Result<u64>>,
    inspections: Mutex<std::collections::VecDeque<transfer::SourceInspection>>,
    inspected: AtomicUsize,
    exists: AtomicBool,
    custom: AtomicBool,
    delay_shutdown: AtomicBool,
    outcome: Mutex<Finalize>,
    gate: Mutex<Option<Arc<Gate>>>,
    submit_gate: Mutex<Option<Arc<Gate>>>,
    recovery: Mutex<crt::redirect::Outcome>,
    recoveries: AtomicUsize,
    interrupt_on_recovery: Mutex<Option<Weak<Scheduler>>>,
    raise_on_recovery: Mutex<Option<Weak<Scheduler>>>,
    retirement_entered: AtomicBool,
    retire_error: Mutex<Option<String>>,
    refused_submission: Mutex<Option<usize>>,
    replay_finishes_before_adoption: AtomicBool,
    deleted: Mutex<Vec<Vec<u8>>>,
    delete_failure: Mutex<Option<TransferResult>>,
}
impl Default for Control {
    fn default() -> Self {
        Self {
            callbacks: Mutex::new(Vec::new()),
            delayed: Mutex::new(Vec::new()),
            submissions: Mutex::new(Vec::new()),
            request_keys: Mutex::new(Vec::new()),
            parents: AtomicUsize::new(0),
            releases: AtomicUsize::new(0),
            cancels: AtomicUsize::new(0),
            discards: AtomicUsize::new(0),
            finalized: AtomicUsize::new(0),
            events: Mutex::new(Vec::new()),
            immediate: AtomicBool::new(false),
            reject: AtomicBool::new(false),
            parent_error: AtomicBool::new(false),
            temp_error: AtomicBool::new(false),
            random: Mutex::new(|| Ok(0xabab_abab_abab_abab)),
            inspections: Mutex::new(std::collections::VecDeque::new()),
            inspected: AtomicUsize::new(0),
            exists: AtomicBool::new(false),
            custom: AtomicBool::new(false),
            delay_shutdown: AtomicBool::new(false),
            outcome: Mutex::new(Finalize::Success),
            gate: Mutex::new(None),
            submit_gate: Mutex::new(None),
            recovery: Mutex::new(crt::redirect::Outcome::Unavailable),
            recoveries: AtomicUsize::new(0),
            interrupt_on_recovery: Mutex::new(None),
            raise_on_recovery: Mutex::new(None),
            retirement_entered: AtomicBool::new(false),
            retire_error: Mutex::new(None),
            refused_submission: Mutex::new(None),
            replay_finishes_before_adoption: AtomicBool::new(false),
            deleted: Mutex::new(Vec::new()),
            delete_failure: Mutex::new(None),
        }
    }
}
#[derive(Debug)]
struct FakeOps(Arc<Control>);
#[derive(Debug)]
struct Handle {
    callback: Arc<dyn Completion>,
    control: Arc<Control>,
}
impl OwnedRequest for Handle {
    fn cancel(&self) {
        self.control.cancels.fetch_add(1, Ordering::Relaxed);
    }
}
impl Drop for Handle {
    fn drop(&mut self) {
        self.control.releases.fetch_add(1, Ordering::Relaxed);
        lock(&self.control.events).push("release");
        if self.control.delay_shutdown.load(Ordering::Acquire) {
            lock(&self.control.delayed).push(Arc::clone(&self.callback));
        } else {
            self.callback.shutdown();
        }
    }
}
impl Operations for FakeOps {
    fn temp_path(&self, path: &Path) -> Result<PathBuf, TempPathError> {
        if self.0.temp_error.load(Ordering::Acquire) {
            Err(TempPathError::OutOfMemory)
        } else {
            let id = (*lock(&self.0.random))().map_err(|_| TempPathError::RandomUnavailable)?;
            entries::temp_path(path, id)
        }
    }
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        self.0.parents.fetch_add(1, Ordering::Relaxed);
        if self.0.parent_error.load(Ordering::Acquire) {
            Err(io::ErrorKind::PermissionDenied.into())
        } else {
            Ok(())
        }
    }
    fn exists(&self, _: &Path) -> bool {
        self.0.exists.load(Ordering::Acquire)
    }
    fn inspect_source(&self, _: &Path) -> transfer::SourceInspection {
        self.0.inspected.fetch_add(1, Ordering::Relaxed);
        lock(&self.0.inspections)
            .pop_front()
            .unwrap_or(transfer::SourceInspection::Size(4))
    }
    fn submit(
        &self,
        job: Arc<Job>,
        callback: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        if self.0.reject.load(Ordering::Acquire) {
            return Err(SubmitError::Local("rejected".into()));
        }
        job.custom_writer
            .store(self.0.custom.load(Ordering::Acquire), Ordering::Release);
        lock(&self.0.submissions).push((
            job.raw_key.clone(),
            job.local_path.clone(),
            job.temp_path.clone(),
            job.size,
        ));
        lock(&self.0.request_keys).push(job.request_key.clone());
        let index = {
            let mut callbacks = lock(&self.0.callbacks);
            callbacks.push(Arc::downgrade(&callback));
            callbacks.len() - 1
        };
        if *lock(&self.0.refused_submission) == Some(index) {
            return Err(SubmitError::Transfer(Box::new(TransferResult {
                error_code: 92,
                ..TransferResult::default()
            })));
        }
        if index == 1
            && self
                .0
                .replay_finishes_before_adoption
                .load(Ordering::Acquire)
        {
            callback.finish(TransferResult::default());
            await_condition("the replay's finalization", || {
                self.0.finalized.load(Ordering::Acquire) != 0
            });
        }
        let request = Box::new(Handle {
            callback: Arc::clone(&callback),
            control: Arc::clone(&self.0),
        });
        if self.0.immediate.load(Ordering::Acquire) {
            callback.finish(TransferResult::default());
        }
        if let Some(gate) = lock(&self.0.submit_gate).clone() {
            gate.enter();
        }
        Ok(request)
    }
    fn finalize(&self, _: &Job, _: &TransferResult) -> Finalize {
        let gate = lock(&self.0.gate).clone();
        if let Some(gate) = gate {
            gate.enter();
        }
        self.0.finalized.fetch_add(1, Ordering::Relaxed);
        lock(&self.0.events).push("finalize");
        lock(&self.0.outcome).clone()
    }
    fn delete_source(&self, job: &Job) -> Result<(), SourceDeleteError> {
        lock(&self.0.events).push("delete");
        lock(&self.0.deleted).push(job.raw_key.clone());
        match lock(&self.0.delete_failure).clone() {
            Some(result) => Err(SourceDeleteError::Request(Box::new(result))),
            None => Ok(()),
        }
    }
    fn discard(&self, _: &Job) {
        self.0.discards.fetch_add(1, Ordering::Relaxed);
    }
    fn retire_attempt(
        &self,
        job: &Job,
        _: &TransferResult,
        await_shutdown: &dyn Fn(),
    ) -> Option<String> {
        self.0.retirement_entered.store(true, Ordering::Release);
        await_shutdown();
        self.discard(job);
        lock(&self.0.retire_error).clone()
    }
    fn recover_region(&self, _: &TransferResult) -> crt::redirect::Outcome {
        self.0.recoveries.fetch_add(1, Ordering::AcqRel);
        let interrupted = lock(&self.0.interrupt_on_recovery)
            .as_ref()
            .and_then(Weak::upgrade);
        if let Some(scheduler) = interrupted {
            scheduler.cancel();
        }
        let raised = lock(&self.0.raise_on_recovery)
            .as_ref()
            .and_then(Weak::upgrade);
        if let Some(scheduler) = raised {
            scheduler.cancel_for_exception(
                b"repeated token".to_vec(),
                &cli_core::interrupt::State::new(),
            );
        }
        *lock(&self.0.recovery)
    }
}
fn await_condition(what: &str, ready: impl Fn() -> bool) {
    let deadline = Instant::now() + std::time::Duration::from_secs(30);
    while !ready() {
        assert!(Instant::now() < deadline, "timed out waiting for {what}");
        std::thread::yield_now();
    }
}
struct Fixture {
    scheduler: Arc<Scheduler>,
    control: Arc<Control>,
    output: Arc<Output>,
}
impl Fixture {
    fn new(download: bool, pool: bool) -> Self {
        Self::configured(download, pool, false, false, 4)
    }
    fn configured(download: bool, pool: bool, quiet: bool, overwrite: bool, limit: u32) -> Self {
        let control = Arc::new(Control::default());
        let output = Arc::new(Output::default());
        let request = TransferRequest {
            direction: if download {
                transfer::Direction::Download
            } else {
                transfer::Direction::Upload
            },
            bucket: "bucket".into(),
            prefix: "prefix/".into(),
            local_root: "/tmp/local".into(),
            runtime: Default::default(),
            quiet,
            dryrun: false,
            no_overwrite: overwrite,
            glacier: crate::transfer::GlacierPolicy::Warn,
            content_types: None,
            refusal: None,
            page_size: 0,
            max_in_flight: limit,
            collect_stats: true,
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
        };
        let scheduler = Scheduler::new(
            request,
            "/tmp".into(),
            Arc::new(FakeOps(control.clone())),
            output.clone(),
        );
        if pool {
            scheduler.start_finish_pool(1).expect("finish pool");
        }
        Self {
            scheduler,
            control,
            output,
        }
    }
    fn with_native_root(mut self) -> Self {
        let scheduler = Arc::get_mut(&mut self.scheduler).expect("exclusive fixture");
        scheduler.cwd = native_cwd();
        scheduler.request.local_root = native_cwd().join("local");
        self
    }
    fn submit(&self, key: &str) {
        self.scheduler
            .handle_download_entry(&format!("prefix/{key}"), 4, Some(1))
            .expect("entry");
    }
    fn finish(&self, index: usize, result: TransferResult) {
        let callback = lock(&self.control.callbacks)[index]
            .upgrade()
            .expect("pending callback");
        callback.finish(result);
    }
    fn shutdown(&self) {
        let callbacks = std::mem::take(&mut *lock(&self.control.delayed));
        for callback in callbacks {
            callback.shutdown();
        }
    }
    fn stats(&self) -> Stats {
        self.scheduler.finished().stats.expect("stats enabled")
    }
    fn count(&self) -> usize {
        lock(&self.control.submissions).len()
    }
}
fn native_cwd() -> PathBuf {
    PathBuf::from(if cfg!(windows) { r"C:\tmp" } else { "/tmp" })
}
fn native_local(relative: &str) -> String {
    let sep = std::path::MAIN_SEPARATOR_STR;
    let root = native_cwd().join("local");
    format!("{}{sep}{}", root.display(), relative.replace('/', sep))
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let callbacks: Vec<_> = lock(&self.control.callbacks)
            .iter()
            .filter_map(Weak::upgrade)
            .collect();
        for callback in callbacks {
            if self.control.releases.load(Ordering::Acquire) == self.count() {
                break;
            }
            callback.finish(TransferResult::default());
        }
        self.shutdown();
        self.scheduler.drain();
        self.scheduler.close_write_pool();
    }
}
#[test]
#[cfg(unix)]
fn recursive_upload_preserves_distinct_non_utf8_filename_bytes() {
    use std::{ffi::OsStr, os::unix::ffi::OsStrExt};

    let f = Fixture::new(false, false);
    f.control.immediate.store(true, Ordering::Release);
    for name in [
        b"file-\xfe".as_slice(),
        b"file-\xff",
        "file-\u{fffd}".as_bytes(),
    ] {
        f.scheduler
            .handle_upload_entry(Path::new(OsStr::from_bytes(name)), None)
            .expect("upload entry");
    }
    f.scheduler.drain();
    assert_eq!(
        *lock(&f.control.request_keys),
        [
            "prefix/file-%FE",
            "prefix/file-%FF",
            "prefix/file-%EF%BF%BD"
        ]
    );
    assert_eq!(f.stats().succeeded, 3);
}

#[test]
fn filters_entries_and_preserves_submission_metadata() {
    let f = Fixture::new(true, false);
    for (key, size) in [("other/key", 1), ("prefix/folder/", 0)] {
        f.scheduler
            .handle_download_entry(key, size, None)
            .expect("filter");
    }
    assert_eq!(f.count(), 0);
    f.submit("space key");
    let jobs = lock(&f.control.submissions);
    assert_eq!(jobs[0].0, b"prefix/space key");
    assert_eq!(jobs[0].1, Path::new("/tmp/local/space key"));
    assert_eq!(
        jobs[0].2.as_deref(),
        Some(Path::new("/tmp/local/space key.abababababababab"))
    );
    assert_eq!(jobs[0].3, Some(4));
}
#[test]
fn include_and_exclude_filter_listed_objects() {
    let mut f = Fixture::new(true, false);
    let filters =
        [(Exclude, "*"), (Include, "*.txt")].map(|(kind, pattern)| (kind, pattern.to_owned()));
    Arc::get_mut(&mut f.scheduler)
        .expect("exclusive fixture")
        .request
        .filter = crate::filter::Filter::new(
        &filters,
        crate::filter::Roots {
            source: b"bucket/prefix/",
            destination: b"/tmp/local",
        },
        b"bucket/",
    );
    for key in ["a.txt", "a.bin", "nested/b.txt", "folder/"] {
        f.submit(key);
    }
    let jobs = lock(&f.control.submissions);
    let keys: Vec<_> = jobs.iter().map(|job| job.0.as_slice()).collect();
    assert_eq!(keys, [b"prefix/a.txt".as_slice(), b"prefix/nested/b.txt"]);
}
fn delete_fixture(delete: crate::cp::recursive::DeleteOptions) -> Fixture {
    let mut f = Fixture::new(false, false);
    let request = &mut Arc::get_mut(&mut f.scheduler)
        .expect("exclusive fixture")
        .request;
    request.direction = transfer::Direction::Delete;
    request.local_root = PathBuf::new();
    request.delete = delete;
    f
}
#[test]
fn a_delete_listing_keeps_folder_markers_and_names_no_local_path() {
    let f = delete_fixture(Default::default());
    let passes = |key: &str, size| {
        f.scheduler
            .listed_entry_passes_filters(key.as_bytes(), size)
    };
    assert!(passes("prefix/a.txt", 4));
    assert!(passes("prefix/folder/", 0));
    assert!(passes("prefix/", 0));
    assert!(!passes("other/key", 1));
    f.scheduler
        .handle_listed_entry(
            "prefix/folder/",
            0,
            None,
            Archive::default(),
            None,
            ObjectCondition::default(),
        )
        .expect("entry");
    let jobs = lock(&f.control.submissions).clone();
    assert_eq!(
        jobs,
        [(b"prefix/folder/".to_vec(), PathBuf::new(), None, Some(0))]
    );
    assert_eq!(*lock(&f.control.request_keys), ["prefix/folder/"]);
    f.finish(0, TransferResult::default());
    f.shutdown();
    f.scheduler.drain();
    let lines: Vec<_> = lock(&f.output.events)
        .iter()
        .map(|event| String::from_utf8_lossy(&event.text).into_owned())
        .collect();
    assert_eq!(lines, ["delete: s3://bucket/prefix/folder/\n"]);
}
#[test]
fn a_folder_marker_delete_keeps_only_zero_size_keys_ending_in_a_slash() {
    let f = delete_fixture(crate::cp::recursive::DeleteOptions {
        folder_markers_only: true,
    });
    let passes = |key: &str, size| {
        f.scheduler
            .listed_entry_passes_filters(key.as_bytes(), size)
    };
    assert!(passes("prefix/folder/", 0));
    assert!(!passes("prefix/a.txt", 4));
    assert!(!passes("prefix/empty.txt", 0));
    assert!(!passes("prefix/sized/", 5));
}
#[test]
fn a_nonempty_object_named_by_the_prefix_downloads_onto_the_root() {
    let f = Fixture::new(true, false).with_native_root();
    f.scheduler
        .handle_download_entry("prefix/", 10, None)
        .expect("entry");
    let jobs = lock(&f.control.submissions);
    assert_eq!(jobs.len(), 1);
    assert_eq!(jobs[0].0, b"prefix/");
    let mut root = native_cwd().join("local").into_os_string();
    root.push(std::path::MAIN_SEPARATOR_STR);
    assert_eq!(jobs[0].1.as_os_str(), root);
    drop(jobs);
    f.finish(0, TransferResult::default());
    f.shutdown();
    f.scheduler.drain();
}
#[test]
fn every_download_temp_name_draws_a_fresh_random_id() {
    let f = Fixture::new(true, false);
    *lock(&f.control.random) = transfer::temp_name_id;
    f.submit("foo");
    f.submit("foo");
    let jobs = lock(&f.control.submissions);
    let names: Vec<_> = jobs
        .iter()
        .map(|job| {
            let temp = job.2.as_deref().expect("temp");
            assert_eq!(temp.parent(), job.1.parent());
            temp.file_name()
                .expect("name")
                .to_str()
                .expect("UTF-8")
                .to_owned()
        })
        .collect();
    for name in &names {
        assert_eq!(&name[..4], "foo.");
        assert_eq!(name[4..].len(), 16);
    }
    assert_ne!(names[0], names[1]);
}
#[test]
fn download_no_overwrite_is_silent_and_skips_preparation() {
    let f = Fixture::configured(true, false, false, true, 4);
    f.control.exists.store(true, Ordering::Release);
    f.submit("key");
    assert_eq!(f.stats().skipped, 1);
    assert_eq!(f.stats().submitted, 0);
    assert_eq!(f.control.parents.load(Ordering::Relaxed), 0);
    assert!(lock(&f.output.events).is_empty());
}
#[test]
fn download_through_a_link_it_does_not_follow_is_a_silent_skip() {
    let mut f = Fixture::new(true, false).with_native_root();
    let scheduler = Arc::get_mut(&mut f.scheduler).expect("exclusive fixture");
    scheduler.request.links = transfer::LinkPolicy::from_flag(false, &native_cwd().join("local"));
    let archived = Archive {
        archived: true,
        restored: false,
    };
    f.scheduler
        .handle_download_entry_with_archive("prefix/missing/../cold", 4, None, archived)
        .expect("archived entry");
    assert_eq!(f.scheduler.finished().warned, 1);
    f.submit("missing/../key");
    assert_eq!(f.scheduler.finished().warned, 1);
    assert_eq!((f.stats().skipped, f.stats().submitted), (2, 0));
    assert_eq!(f.control.parents.load(Ordering::Relaxed), 0);
    f.submit("dir/key");
    assert_eq!(f.stats().submitted, 1);
}
#[test]
fn sizes_and_rate_are_counted_only_when_requested() {
    let f = Fixture::new(true, false);
    for (i, size) in [4096, 65536, 1048576, 1048577].iter().enumerate() {
        f.scheduler
            .handle_download_entry(&format!("prefix/{i}"), *size, None)
            .expect("entry");
    }
    for i in 0..4 {
        f.finish(i, TransferResult::default());
    }
    f.scheduler.drain();
    let stats = f.stats();
    assert_eq!(
        (
            stats.size_le_4_kib,
            stats.size_le_64_kib,
            stats.size_le_1_mib,
            stats.size_gt_1_mib
        ),
        (1, 1, 1, 1)
    );
    assert_eq!(stats.succeeded, 4);
    assert!(stats.files_per_second() >= 0.0);
}
#[test]
fn rejected_submission_cleans_up_and_frees_slot_once() {
    let f = Fixture::new(true, false);
    f.control.reject.store(true, Ordering::Release);
    f.submit("key");
    assert_eq!(f.stats().submitted, 1);
    assert_eq!(f.stats().failed, 1);
    assert_eq!(f.control.discards.load(Ordering::Relaxed), 1);
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
    assert_eq!(lock(&f.scheduler.state).in_flight, 0);
}
#[test]
fn a_producers_exception_drops_the_entry_waiting_for_a_slot() {
    let f = Fixture::configured(true, false, false, false, 1);
    f.submit("first");
    let submitter = {
        let scheduler = Arc::clone(&f.scheduler);
        std::thread::spawn(move || scheduler.handle_download_entry("prefix/raced", 4, Some(1)))
    };
    let deadline = Instant::now() + std::time::Duration::from_secs(30);
    while lock(&f.scheduler.state).stats.stall_count == 0 {
        assert!(Instant::now() < deadline, "in-flight slot backpressure");
        std::thread::yield_now();
    }
    f.control.immediate.store(true, Ordering::Release);
    f.scheduler.cancel_for_exception(
        b"Error during pagination".to_vec(),
        &cli_core::interrupt::State::new(),
    );
    f.finish(
        0,
        TransferResult {
            error_code: crt::s3::CANCELED_ERROR_CODE,
            ..Default::default()
        },
    );
    submitter.join().expect("submitter").expect("entry");
    f.scheduler.drain();
    assert_eq!(f.count(), 1);
    assert_eq!(f.stats().submitted, 1);
    assert_eq!(lock(&f.scheduler.state).destroyed, 2);
}
#[test]
fn asynchronous_failure_holds_slot_until_shutdown() {
    let f = Fixture::new(true, false);
    f.control.delay_shutdown.store(true, Ordering::Release);
    f.submit("key");
    f.finish(
        0,
        TransferResult {
            error_code: 91,
            ..Default::default()
        },
    );
    assert_eq!(f.stats().failed, 1);
    assert_eq!(lock(&f.scheduler.state).in_flight, 1);
    f.shutdown();
    assert_eq!(lock(&f.scheduler.state).in_flight, 0);
}
#[test]
fn commit_failures_fail_and_mtime_warnings_also_succeed() {
    let f = Fixture::new(true, false).with_native_root();
    f.submit("commit.txt");
    f.submit("mtime.txt");
    *lock(&f.control.outcome) = Finalize::Commit(transfer::CommitFailure {
        error: "Permission denied",
        removing_destination: false,
    });
    f.finish(0, TransferResult::default());
    *lock(&f.control.outcome) = Finalize::Mtime("Permission denied".into());
    f.finish(1, TransferResult::default());
    assert_eq!(f.stats().succeeded, 1);
    assert_eq!(f.stats().failed, 1);
    assert_eq!(f.scheduler.finished().warned, 1);

    let quoted = |relative: &str| {
        let path = native_local(relative);
        format!("'{}'", path.replace('\\', "\\\\"))
    };
    let oserror = if cfg!(windows) {
        "[WinError 5] Access is denied"
    } else {
        "[Errno 13] Permission denied"
    };
    let local = |relative: &str| {
        Path::new("local")
            .join(relative)
            .to_string_lossy()
            .into_owned()
    };
    let mtime = native_local("mtime.txt");
    let printed: Vec<String> = lock(&f.output.events)
        .iter()
        .map(|event| String::from_utf8_lossy(&event.text).into_owned())
        .collect();
    assert_eq!(
        printed,
        [
            format!(
                "download failed: s3://bucket/prefix/commit.txt to {} {oserror}: {} -> {}\n",
                local("commit.txt"),
                quoted("commit.txt.abababababababab"),
                quoted("commit.txt"),
            ),
            format!(
                "warning: Skipping file {mtime}. Successfully Downloaded {mtime} but was \
                unable to update the last modified time. Permission denied\n"
            ),
            format!(
                "download: s3://bucket/prefix/mtime.txt to {}\n",
                local("mtime.txt")
            ),
        ]
    );
}
#[test]
fn quiet_suppresses_completion_output_but_not_counters() {
    let f = Fixture::configured(true, false, true, false, 4);
    f.submit("key");
    f.finish(0, TransferResult::default());
    assert_eq!(f.stats().succeeded, 1);
    assert!(lock(&f.output.events).is_empty());
}
#[test]
fn first_fatal_output_error_is_preserved() {
    let f = Fixture::new(true, false);
    f.output.fail.store(true, Ordering::Release);
    f.submit("key");
    f.finish(0, TransferResult::default());
    f.scheduler.record_fatal("later");
    assert_eq!(f.scheduler.finished().fatal.as_deref(), Some("WriteFailed"));
}
#[test]
fn interruption_cancels_owned_requests_without_counting_failures() {
    let f = Fixture::new(true, false);
    f.submit("a");
    f.submit("b");
    f.scheduler.cancel();
    assert_eq!(f.control.cancels.load(Ordering::Relaxed), 2);
    for i in 0..2 {
        f.finish(
            i,
            TransferResult {
                error_code: crt::s3::CANCELED_ERROR_CODE,
                ..Default::default()
            },
        );
    }
    assert_eq!(f.stats().failed, 0);
    assert_eq!(lock(&f.scheduler.state).canceled, 2);
    f.submit("c");
    assert_eq!(f.count(), 2);
}
#[test]
fn finish_before_adoption_releases_from_submitter_exactly_once() {
    let f = Fixture::new(true, false);
    f.control.immediate.store(true, Ordering::Release);
    f.submit("key");
    assert_eq!(f.stats().succeeded, 1);
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 1);
    assert_eq!(*lock(&f.control.events), vec!["finalize", "release"]);
    assert_eq!(lock(&f.scheduler.state).in_flight, 0);
}
#[test]
fn callbacks_complete_slots_out_of_order() {
    let f = Fixture::new(true, false);
    for key in ["a", "b", "c"] {
        f.submit(key);
    }
    for i in [2, 0, 1] {
        f.finish(i, TransferResult::default());
    }
    assert_eq!(f.stats().succeeded, 3);
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 3);
}
#[test]
fn canceled_without_interrupt_is_a_transfer_failure() {
    let f = Fixture::new(true, false);
    f.submit("key");
    f.finish(
        0,
        TransferResult {
            error_code: crt::s3::CANCELED_ERROR_CODE,
            ..Default::default()
        },
    );
    assert_eq!(f.stats().failed, 1);
    assert_eq!(lock(&f.scheduler.state).canceled, 0);
}
#[test]
fn upload_precondition_failure_is_a_silent_skip() {
    let f = Fixture::configured(false, false, false, true, 4);
    f.scheduler
        .handle_upload_entry(Path::new("key"), None)
        .expect("upload");
    f.finish(
        0,
        TransferResult {
            error_code: 91,
            response_status: 412,
            ..Default::default()
        },
    );
    assert_eq!(f.stats().skipped, 1);
    assert_eq!(f.stats().failed, 0);
    assert!(lock(&f.output.events).is_empty());
}
#[test]
fn upload_scheduler_records_keys_skipped_sources_and_completions() {
    use transfer::{SourceInspection::*, SourceSkip};
    let f = Fixture::configured(false, false, false, false, 2).with_native_root();
    lock(&f.control.inspections).extend([
        Skipped(SourceSkip::Special),
        Size(7),
        Size(0),
        Skipped(SourceSkip::Missing),
        Skipped(SourceSkip::Missing),
        Skipped(SourceSkip::UnreadableFile),
    ]);
    for name in [
        "pipe",
        "nested/space %.txt",
        "link.txt",
        "broken-link",
        "missing.txt",
        "locked.txt",
    ] {
        f.scheduler
            .handle_upload_entry(Path::new(name), None)
            .expect("upload entry");
    }
    assert_eq!(
        (f.control.inspected.load(Ordering::Relaxed), f.count()),
        (6, 2)
    );
    let stats = f.stats();
    assert_eq!((stats.submitted, stats.failed, stats.skipped), (2, 0, 4));
    assert_eq!(f.scheduler.finished().warned, 4);
    assert_upload_submissions(&f);
    assert_skip_warnings(&f);
    f.finish(
        1,
        TransferResult {
            error_code: 87,
            response_status: 500,
            ..Default::default()
        },
    );
    f.finish(0, TransferResult::default());
    f.scheduler.drain();
    let stats = f.stats();
    assert_eq!((stats.succeeded, stats.failed), (1, 1));
    assert_eq!(lock(&f.scheduler.state).destroyed, 2);
}
fn assert_upload_submissions(f: &Fixture) {
    let jobs = lock(&f.control.submissions);
    assert_eq!(
        (&jobs[0].0, &jobs[0].1, jobs[0].3),
        (
            &b"prefix/nested/space %.txt".to_vec(),
            &PathBuf::from(native_local("nested/space %.txt")),
            Some(7)
        )
    );
    assert_eq!(
        (&jobs[1].0, jobs[1].3),
        (&b"prefix/link.txt".to_vec(), Some(0))
    );
    assert_eq!(
        lock(&f.control.request_keys)[0],
        "prefix/nested/space%20%25.txt"
    );
}
fn assert_skip_warnings(f: &Fixture) {
    let warnings: Vec<_> = lock(&f.output.events)
        .iter()
        .map(|event| String::from_utf8_lossy(&event.text).into_owned())
        .collect();
    let skipped =
        |name, reason| format!("warning: Skipping file {}. {reason}\n", native_local(name));
    assert_eq!(
        warnings,
        [
            skipped(
                "pipe",
                "File is character special device, block special device, FIFO, or socket."
            ),
            skipped("broken-link", "File does not exist."),
            skipped("missing.txt", "File does not exist."),
            skipped("locked.txt", "File/Directory is not readable."),
        ]
    );
}
#[test]
fn a_quiet_upload_counts_the_sources_it_skips() {
    let f = Fixture::configured(false, false, true, false, 4);
    lock(&f.control.inspections).push_back(transfer::SourceInspection::Skipped(
        transfer::SourceSkip::Missing,
    ));
    f.scheduler
        .handle_upload_entry(Path::new("broken"), None)
        .expect("skip");
    assert_eq!(f.count(), 0);
    assert_eq!(f.scheduler.finished().warned, 1);
    assert_eq!(f.stats().skipped, 1);
    assert!(lock(&f.output.events).is_empty());
}
#[test]
fn parent_failure_is_per_file_and_later_entries_continue() {
    let f = Fixture::new(true, false).with_native_root();
    f.control.parent_error.store(true, Ordering::Release);
    f.submit("a");
    f.control.parent_error.store(false, Ordering::Release);
    f.submit("b");
    assert_eq!(f.count(), 1);
    assert_eq!(f.stats().submitted, 2);
    f.finish(0, TransferResult::default());
    assert_eq!(f.stats().failed, 1);
    assert_eq!(f.stats().succeeded, 1);
    assert!(f.scheduler.finished().fatal.is_none());
    assert_eq!(lock(&f.control.submissions)[0].0, b"prefix/b");
    assert_eq!(
        String::from_utf8_lossy(&lock(&f.output.events)[0].text),
        format!(
            "error: unable to create parent directory for {}: Permission denied\n",
            native_local("a")
        )
    );
}
#[test]
fn parent_escape_is_skipped_and_absolute_suffix_stays_beneath_root() {
    let f = Fixture::new(true, false);
    f.submit("../escape");
    assert_eq!(f.stats().skipped, 1);
    f.submit("/inside");
    assert_eq!(
        lock(&f.control.submissions)[0].1,
        Path::new("/tmp/local/inside")
    );
}
#[test]
fn parent_cache_reuses_successful_directories() {
    let f = Fixture::new(true, false);
    f.submit("dir/a");
    f.submit("dir/b");
    assert_eq!(f.control.parents.load(Ordering::Relaxed), 1);
}
#[test]
fn parent_cache_entry_limit_still_creates_uncached_directories() {
    let control = Arc::new(Control::default());
    let ops = FakeOps(control.clone());
    let mut cache = ParentDirectoryCache::default();
    for i in 0..parents::PARENT_COUNT_MAX {
        cache.remember(Path::new(&format!("parent{i}")));
    }
    for _ in 0..2 {
        cache
            .ensure(&ops, Path::new("uncached/file"))
            .expect("uncached creation");
    }
    assert_eq!(control.parents.load(Ordering::Relaxed), 2);
    ensure_uncached_parent(&mut cache, Path::new("parent0/file"));
}
#[test]
fn parent_cache_refuses_a_parent_holding_a_nul() {
    let control = Arc::new(Control::default());
    let ops = FakeOps(control.clone());
    let mut cache = ParentDirectoryCache::default();
    assert_eq!(
        cache.ensure(&ops, Path::new("file\0x/report")),
        Err("Invalid path name")
    );
    assert_eq!(control.parents.load(Ordering::Relaxed), 0);
}
#[test]
fn parent_cache_exact_byte_fit_and_oversized_keys() {
    let control = Arc::new(Control::default());
    let ops = FakeOps(control.clone());
    let mut cache = ParentDirectoryCache::default();
    let oversized = PathBuf::from("p".repeat(parents::PARENT_BYTES_MAX + 1));
    cache.remember(&oversized);
    let exact = PathBuf::from("x".repeat(parents::PARENT_BYTES_MAX));
    cache.remember(&exact);
    for _ in 0..2 {
        cache
            .ensure(&ops, &oversized.join("file"))
            .expect("oversized");
    }
    assert_eq!(control.parents.load(Ordering::Relaxed), 2);
    cache.ensure(&ops, &exact.join("file")).expect("cached");
    assert_eq!(control.parents.load(Ordering::Relaxed), 2);
    for _ in 0..2 {
        cache
            .ensure(&ops, Path::new("next/file"))
            .expect("uncached");
    }
    assert_eq!(control.parents.load(Ordering::Relaxed), 4);
    ensure_uncached_parent(&mut cache, &exact.join("file"));
}
#[derive(Debug, Default)]
struct DiskOps(AtomicUsize);
impl Operations for DiskOps {
    fn create_parent(&self, path: &Path) -> io::Result<()> {
        self.0.fetch_add(1, Ordering::Relaxed);
        transfer::create_local_dir_path(path)
    }
    fn exists(&self, path: &Path) -> bool {
        path.exists()
    }
    fn inspect_source(&self, path: &Path) -> transfer::SourceInspection {
        transfer::inspect_upload_source(path)
    }
    fn submit(
        &self,
        _: Arc<Job>,
        _: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        Err(SubmitError::Local("no requests".into()))
    }
    fn finalize(&self, _: &Job, _: &TransferResult) -> Finalize {
        Finalize::Success
    }
    fn delete_source(&self, _: &Job) -> Result<(), SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}
fn ensure_uncached_parent(cache: &mut ParentDirectoryCache, cached: &Path) {
    static NEXT: AtomicU64 = AtomicU64::new(0);
    let root = std::env::temp_dir().join(format!(
        "scheduler-parents-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::create_dir(&root).expect("temp directory");
    let ops = DiskOps::default();
    let destination = root.join("uncached").join("file");
    for created in 1..=2 {
        cache.ensure(&ops, &destination).expect("uncached parent");
        assert!(root.join("uncached").is_dir());
        assert_eq!(ops.0.load(Ordering::Relaxed), created);
    }
    std::fs::write(root.join("blocker"), b"").expect("blocking file");
    let blocked = root.join("blocker").join("child").join("file");
    assert_eq!(cache.ensure(&ops, &blocked), Err("Not a directory"));
    let _ = std::fs::remove_dir_all(&root);
    cache.ensure(&ops, cached).expect("cached parent");
    assert_eq!(ops.0.load(Ordering::Relaxed), 3);
}
#[test]
fn pool_and_shutdown_legs_both_hold_the_slot() {
    let f = Fixture::new(true, true);
    let gate = Arc::new(Gate::default());
    *lock(&f.control.gate) = Some(gate.clone());
    f.submit("key");
    f.finish(0, TransferResult::default());
    gate.await_entered();
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 1);
    assert_eq!(lock(&f.scheduler.state).in_flight, 1);
    gate.release();
    f.scheduler.drain();
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
}
#[test]
fn a_download_submitted_before_the_pool_starts_finishes_on_its_callback() {
    let f = Fixture::new(true, false);
    f.submit("key");
    f.scheduler.start_finish_pool(1).expect("finish pool");
    f.finish(0, TransferResult::default());
    assert_eq!(f.stats().succeeded, 1);
    assert_eq!(f.control.finalized.load(Ordering::Relaxed), 1);
    f.scheduler.drain();
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
}
#[test]
fn an_upload_finishes_on_its_callback_beside_a_started_pool() {
    let f = Fixture::new(false, true);
    f.scheduler
        .handle_upload_entry(Path::new("file"), None)
        .expect("entry");
    f.finish(0, TransferResult::default());
    assert_eq!(f.stats().succeeded, 1);
    assert_eq!(f.control.finalized.load(Ordering::Relaxed), 1);
    f.scheduler.drain();
    f.scheduler.close_write_pool();
    assert_eq!(f.stats().writes_completed, 0);
}
#[test]
fn pool_completion_before_shutdown_keeps_the_other_leg() {
    let f = Fixture::new(true, true);
    f.control.delay_shutdown.store(true, Ordering::Release);
    f.submit("key");
    f.finish(0, TransferResult::default());
    f.scheduler.close_write_pool();
    assert_eq!(f.stats().succeeded, 1);
    assert_eq!(lock(&f.scheduler.state).in_flight, 1);
    f.shutdown();
    f.scheduler.drain();
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
}
#[test]
fn failed_file_download_drops_unused_pool_leg() {
    let f = Fixture::new(true, true);
    f.submit("key");
    f.finish(
        0,
        TransferResult {
            error_code: 91,
            ..Default::default()
        },
    );
    f.scheduler.drain();
    assert_eq!(f.stats().failed, 1);
    assert_eq!(f.control.finalized.load(Ordering::Relaxed), 0);
}
#[test]
fn closed_pool_is_fatal_and_fails_the_file_without_leaking() {
    let f = Fixture::new(true, true);
    f.submit("key");
    f.scheduler.close_write_pool();
    f.finish(0, TransferResult::default());
    f.scheduler.drain();
    assert_eq!(f.stats().failed, 1);
    assert_eq!(
        f.scheduler.finished().fatal.as_deref(),
        Some("WritePoolClosed")
    );
}
#[test]
fn submit_queue_close_drains_entries_and_preserves_metadata() {
    let f = Fixture::new(true, false);
    f.control.immediate.store(true, Ordering::Release);
    let mut queue = SubmitQueue::new(f.scheduler.clone(), 2).expect("queue");
    for key in ["a", "b", "c"] {
        queue
            .push(format!("prefix/{key}"), 5, Some(12))
            .expect("push");
    }
    queue.close_and_join();
    f.scheduler.drain();
    assert_eq!(f.stats().succeeded, 3);
    assert!(matches!(
        queue.push("prefix/late".into(), 1, None),
        Err(Error::QueueClosed)
    ));
}
#[test]
fn queue_failure_rejects_later_pushes() {
    let f = Fixture::new(true, false);
    f.output.fail.store(true, Ordering::Release);
    let mut queue = SubmitQueue::new(f.scheduler.clone(), 2).expect("queue");
    queue
        .push("prefix/../escape".into(), 1, None)
        .expect("first");
    queue.close_and_join();
    assert_eq!(f.scheduler.finished().fatal.as_deref(), Some("WriteFailed"));
    assert!(queue.push("prefix/later".into(), 1, None).is_err());
}
#[test]
fn hooks_and_subsystems_are_isolated() {
    let a = Fixture::new(true, false);
    let b = Fixture::new(true, false);
    a.submit("a");
    b.submit("b");
    a.scheduler.cancel();
    assert_eq!(a.control.cancels.load(Ordering::Relaxed), 1);
    assert_eq!(b.control.cancels.load(Ordering::Relaxed), 0);
    assert!(!b.scheduler.interrupted());
}
#[test]
fn completion_output_uses_local_paths_remote_keys_and_streams() {
    let f = Fixture::new(true, false).with_native_root();
    f.submit("a");
    f.finish(0, TransferResult::default());
    let sep = std::path::MAIN_SEPARATOR_STR;
    assert_eq!(
        *lock(&f.output.events),
        vec![Event {
            stream: Stream::Stdout,
            text: format!("download: s3://bucket/prefix/a to local{sep}a\n").into()
        }]
    );
}
#[test]
fn custom_writer_cancellation_waits_for_pool_and_counts_canceled() {
    let f = Fixture::new(true, true);
    f.control.custom.store(true, Ordering::Release);
    let gate = Arc::new(Gate::default());
    *lock(&f.control.gate) = Some(gate.clone());
    *lock(&f.control.outcome) = Finalize::Write("interrupted".into());
    f.submit("key");
    f.scheduler.cancel();
    f.finish(
        0,
        TransferResult {
            error_code: crt::s3::CANCELED_ERROR_CODE,
            ..Default::default()
        },
    );
    gate.await_entered();
    assert_eq!(lock(&f.scheduler.state).in_flight, 1);
    gate.release();
    f.scheduler.drain();
    assert_eq!(f.stats().failed, 0);
    assert_eq!(lock(&f.scheduler.state).canceled, 1);
}
#[test]
fn writer_cancellation_is_failed_when_it_was_not_ctrl_c() {
    let f = Fixture::new(true, true);
    f.control.custom.store(true, Ordering::Release);
    *lock(&f.control.outcome) = Finalize::Write("write failure".into());
    f.submit("key");
    f.finish(
        0,
        TransferResult {
            error_code: crt::s3::CANCELED_ERROR_CODE,
            ..Default::default()
        },
    );
    f.scheduler.drain();
    assert_eq!(f.stats().failed, 1);
    assert_eq!(lock(&f.scheduler.state).canceled, 0);
    assert!(lock(&f.output.events)[0].text.ends_with(b"write failure\n"));
}
#[test]
fn slot_reservation_waits_until_shutdown_releases_capacity() {
    let f = Fixture::configured(true, false, false, false, 1);
    f.submit("a");
    let scheduler = Arc::clone(&f.scheduler);
    let (started, ready) = std::sync::mpsc::channel();
    let worker = std::thread::spawn(move || {
        started.send(()).expect("started");
        scheduler
            .handle_download_entry("prefix/b", 1, None)
            .expect("second");
    });
    ready.recv().expect("worker ready");
    assert_eq!(lock(&f.scheduler.state).in_flight, 1);
    f.finish(0, TransferResult::default());
    worker.join().expect("submitter");
    assert_eq!(f.count(), 2);
    f.finish(1, TransferResult::default());
    f.scheduler.drain();
    assert_eq!(f.stats().succeeded, 2);
}
#[test]
fn drain_waits_until_shutdown_releases_the_last_slot() {
    let f = Fixture::new(true, false);
    f.control.delay_shutdown.store(true, Ordering::Release);
    f.submit("key");
    f.finish(0, TransferResult::default());
    let scheduler = Arc::clone(&f.scheduler);
    let (done, finished) = std::sync::mpsc::channel();
    let worker = std::thread::spawn(move || {
        scheduler.drain();
        done.send(()).expect("drain signal");
    });
    assert!(finished.try_recv().is_err());
    f.shutdown();
    finished.recv().expect("drained");
    worker.join().expect("drain worker");
}
#[test]
fn submit_queue_bounds_producer_backpressure() {
    let f = Fixture::configured(true, false, false, false, 1);
    f.control.immediate.store(true, Ordering::Release);
    let mut queue = SubmitQueue::new(f.scheduler.clone(), 1).expect("queue");
    for index in 0..64 {
        queue
            .push(format!("prefix/{index}"), 1, None)
            .expect("bounded push");
    }
    queue.close_and_join();
    f.scheduler.drain();
    let stats = f.stats();
    assert_eq!(stats.succeeded, 64);
    assert_eq!(stats.queue_hwm, 1);
    assert_eq!(stats.in_flight_hwm, 1);
}
#[test]
fn interrupted_producers_do_not_submit_walker_or_listing_entries() {
    for download in [false, true] {
        let f = Fixture::new(download, false);
        f.scheduler.cancel();
        if download {
            let mut queue = SubmitQueue::new(f.scheduler.clone(), 2).expect("queue");
            assert!(queue.push("prefix/key".into(), 1, None).is_err());
            queue.close_and_join();
        } else {
            f.scheduler
                .handle_upload_entry(Path::new("key"), None)
                .expect("stopped upload");
        }
        assert_eq!(f.stats().submitted, 0);
    }
}

#[test]
fn interrupt_racing_submission_cancels_the_adopted_reference() {
    let f = Fixture::new(true, false);
    let gate = Arc::new(Gate::default());
    *lock(&f.control.submit_gate) = Some(gate.clone());
    let scheduler = Arc::clone(&f.scheduler);
    let worker = std::thread::spawn(move || scheduler.handle_download_entry("prefix/key", 1, None));
    gate.await_entered();
    f.scheduler.cancel();
    assert_eq!(f.control.cancels.load(Ordering::Relaxed), 0);
    gate.release();
    worker.join().expect("submitter").expect("entry");
    assert_eq!(f.control.cancels.load(Ordering::Relaxed), 1);
    f.finish(
        0,
        TransferResult {
            error_code: crt::s3::CANCELED_ERROR_CODE,
            ..Default::default()
        },
    );
    f.scheduler.drain();
    assert_eq!(f.stats().failed, 0);
    assert_eq!(lock(&f.scheduler.state).canceled, 1);
}

#[test]
fn drain_waits_for_callback_owners_after_the_slot_is_released() {
    let f = Fixture::new(true, false);
    f.submit("key");
    let retained = lock(&f.control.callbacks)[0].upgrade().expect("callback");
    f.finish(0, TransferResult::default());
    assert_eq!(lock(&f.scheduler.state).in_flight, 0);
    let scheduler = Arc::clone(&f.scheduler);
    let (done, finished) = std::sync::mpsc::channel();
    let worker = std::thread::spawn(move || {
        scheduler.drain();
        done.send(()).expect("drain signal");
    });
    assert!(finished.try_recv().is_err());
    drop(retained);
    finished.recv().expect("owners drained");
    worker.join().expect("drain worker");
}

#[test]
fn temp_path_failure_is_per_entry_and_later_entries_continue() {
    let f = Fixture::new(true, false).with_native_root();
    f.control.temp_error.store(true, Ordering::Release);
    f.submit("first");
    f.control.temp_error.store(false, Ordering::Release);
    f.submit("second");
    f.finish(0, TransferResult::default());
    f.scheduler.drain();
    assert_eq!(f.stats().failed, 1);
    assert_eq!(f.stats().succeeded, 1);
    assert_eq!(f.stats().submitted, 2);
    assert_eq!(f.count(), 1);
    assert!(f.scheduler.finished().fatal.is_none());
    let events = lock(&f.output.events);
    let line = |relative: &str, error: &str| {
        format!(
            "error: unable to prepare download destination {}: {error}\n",
            native_local(relative)
        )
        .into_bytes()
    };
    assert_eq!(events[0].text, line("first", "Out of memory"));
    drop(events);
    assert_eq!(lock(&f.control.submissions)[0].0, b"prefix/second");
}

#[test]
fn upload_completion_and_failures_release_each_reference_once() {
    let f = Fixture::new(false, false);
    for name in ["ok", "failed"] {
        f.scheduler
            .handle_upload_entry(Path::new(name), None)
            .expect("upload");
    }
    f.finish(0, TransferResult::default());
    f.finish(
        1,
        TransferResult {
            error_code: 1,
            ..Default::default()
        },
    );
    f.control.reject.store(true, Ordering::Release);
    f.output.fail.store(true, Ordering::Release);
    f.scheduler
        .handle_upload_entry(Path::new("rejected"), None)
        .expect("recorded failure");
    f.scheduler.drain();
    assert_eq!(f.stats().succeeded, 1);
    assert_eq!(f.stats().failed, 2);
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 2);
    assert_eq!(f.control.discards.load(Ordering::Relaxed), 2);
    assert_eq!(lock(&f.scheduler.state).destroyed, 3);
    assert_eq!(f.scheduler.finished().fatal.as_deref(), Some("WriteFailed"));
}

#[test]
fn upload_capacity_waits_and_fatal_drain_keeps_owned_requests_alive() {
    let f = Fixture::configured(false, false, false, false, 1);
    f.scheduler
        .handle_upload_entry(Path::new("first"), None)
        .expect("first");
    f.scheduler.record_fatal("writer failed");
    let scheduler = Arc::clone(&f.scheduler);
    let worker =
        std::thread::spawn(move || scheduler.handle_upload_entry(Path::new("second"), None));
    assert_eq!(lock(&f.scheduler.state).in_flight, 1);
    f.finish(0, TransferResult::default());
    worker.join().expect("submitter").expect("second");
    f.finish(1, TransferResult::default());
    f.scheduler.drain();
    assert_eq!(f.stats().succeeded, 2);
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 2);
    assert_eq!(
        f.scheduler.finished().fatal.as_deref(),
        Some("writer failed")
    );
}

#[test]
fn public_error_variants_have_exhaustive_contracts() {
    fn classify(error: Error) -> &'static str {
        match error {
            Error::Output(_) => "output",
            Error::QueueClosed => "queue",
        }
    }
    fn classify_submission(error: SubmitError) -> &'static str {
        match error {
            SubmitError::Transfer(_) => "transfer",
            SubmitError::Local(_) | SubmitError::RawLocal(_) => "local",
        }
    }
    assert_eq!(classify(Error::Output("failed".into())), "output");
    assert_eq!(classify(Error::QueueClosed), "queue");
    assert_eq!(
        classify_submission(SubmitError::Transfer(Box::default())),
        "transfer"
    );
    assert_eq!(
        classify_submission(SubmitError::Local("failed".into())),
        "local"
    );
}

#[test]
fn glacier_skip_precedes_parent_escape_and_existing_destination() {
    for (policy, restored, expected_warnings, glacier_warning) in [
        (transfer::GlacierPolicy::Warn, false, 1, true),
        (transfer::GlacierPolicy::Skip, false, 0, false),
        (transfer::GlacierPolicy::Transfer, false, 1, false),
        (transfer::GlacierPolicy::Warn, true, 1, false),
    ] {
        let mut fixture = Fixture::configured(true, false, false, true, 4);
        Arc::get_mut(&mut fixture.scheduler)
            .expect("exclusive fixture")
            .request
            .glacier = policy;
        fixture.control.exists.store(true, Ordering::Release);
        fixture
            .scheduler
            .handle_download_entry_with_archive(
                "prefix/../cold",
                12,
                None,
                Archive {
                    archived: true,
                    restored,
                },
            )
            .expect("archive entry");
        assert_eq!(fixture.count(), 0);
        assert_eq!(fixture.stats().skipped, 1);
        assert_eq!(fixture.scheduler.finished().warned, expected_warnings);
        assert_eq!(fixture.control.parents.load(Ordering::Acquire), 0);
        let output = lock(&fixture.output.events);
        assert_eq!(output.len(), expected_warnings as usize);
        assert_eq!(
            output.first().is_some_and(|event| event
                .text
                .windows(21)
                .any(|text| text == b"storage class GLACIER")),
            glacier_warning
        );
    }
}

#[derive(Debug, Default)]
struct Published {
    results: Mutex<Vec<crate::results::Event>>,
    emitted: Mutex<Vec<Event>>,
}
impl Sink for Published {
    fn emit(&self, event: Event) -> Result<(), String> {
        lock(&self.emitted).push(event);
        Ok(())
    }
    fn publish(&self, event: crate::results::Event, _: bool) -> Result<(), String> {
        lock(&self.results).push(event);
        Ok(())
    }
}
#[test]
fn download_skip_warnings_publish_warning_results() {
    for quiet in [false, true] {
        let mut fixture = Fixture::configured(true, false, quiet, false, 4);
        let sink = Arc::new(Published::default());
        Arc::get_mut(&mut fixture.scheduler)
            .expect("exclusive fixture")
            .sink = sink.clone();
        let archived = Archive {
            archived: true,
            restored: false,
        };
        fixture
            .scheduler
            .handle_download_entry_with_archive("prefix/cold", 12, None, archived)
            .expect("archived entry");
        fixture
            .scheduler
            .handle_download_entry("prefix/../escape", 12, None)
            .expect("escaping entry");
        assert_eq!(fixture.count(), 0);
        assert_eq!(fixture.stats().skipped, 2);
        assert_eq!(fixture.scheduler.finished().warned, 2);
        let expected = if quiet {
            Vec::new()
        } else {
            vec![
                crate::results::Event::Warning(transfer::glacier_warning(
                    b"s3://bucket/prefix/cold",
                )),
                crate::results::Event::Warning(
                    transfer::parent_escape_warning("../escape").into_bytes(),
                ),
            ]
        };
        assert_eq!(*lock(&sink.results), expected);
        assert!(lock(&sink.emitted).is_empty());
    }
}

fn shown_local(name: &str) -> Vec<u8> {
    Path::new("local")
        .join(name)
        .into_os_string()
        .into_encoded_bytes()
}
fn dry_run_fixture(download: bool, quiet: bool) -> (Fixture, Arc<Published>) {
    let mut fixture = Fixture::configured(download, false, quiet, true, 4).with_native_root();
    let sink = Arc::new(Published::default());
    let scheduler = Arc::get_mut(&mut fixture.scheduler).expect("exclusive fixture");
    scheduler.request.dryrun = true;
    scheduler.sink = sink.clone();
    (fixture, sink)
}

#[test]
fn dry_run_reports_each_download_the_skip_rules_pass() {
    for quiet in [false, true] {
        let (fixture, sink) = dry_run_fixture(true, quiet);
        fixture.submit("a");
        let archived = Archive {
            archived: true,
            restored: false,
        };
        fixture
            .scheduler
            .handle_download_entry_with_archive("prefix/cold", 12, None, archived)
            .expect("archived entry");
        fixture.submit("../escape");
        fixture.control.exists.store(true, Ordering::Release);
        fixture.submit("existing");
        fixture.scheduler.finish_submissions(true);
        assert_eq!(fixture.count(), 0);
        assert_eq!(fixture.control.parents.load(Ordering::Acquire), 0);
        let stats = fixture.stats();
        assert_eq!((stats.submitted, stats.skipped), (0, 3));
        assert_eq!(fixture.scheduler.finished().warned, 2);
        let mut expected = vec![
            crate::results::Event::DryRun(crate::results::Line {
                transfer_type: crate::results::TransferType::Download,
                source: b"s3://bucket/prefix/a".to_vec(),
                destination: Some(shown_local("a")),
            }),
            crate::results::Event::Warning(transfer::glacier_warning(b"s3://bucket/prefix/cold")),
            crate::results::Event::Warning(
                transfer::parent_escape_warning("../escape").into_bytes(),
            ),
        ];
        if quiet {
            expected.clear();
        }
        expected.push(crate::results::Event::FinalTotal(0));
        assert_eq!(*lock(&sink.results), expected);
    }
}

#[test]
fn dry_run_reports_each_upload_its_inspection_passes() {
    let (fixture, sink) = dry_run_fixture(false, false);
    fixture.control.reject.store(true, Ordering::Release);
    lock(&fixture.control.inspections).extend([
        transfer::SourceInspection::Skipped(transfer::SourceSkip::Missing),
        transfer::SourceInspection::Size(transfer::MAX_UPLOAD_SIZE + 1),
    ]);
    for name in ["missing", "huge"] {
        fixture
            .scheduler
            .handle_upload_entry(Path::new(name), None)
            .expect("inspected entry");
    }
    fixture
        .scheduler
        .handle_upload_entry(Path::new("walked"), Some(4))
        .expect("walked entry");
    assert_eq!(fixture.count(), 0);
    let stats = fixture.stats();
    assert_eq!((stats.submitted, stats.failed, stats.skipped), (0, 0, 1));
    assert_eq!(fixture.scheduler.finished().warned, 2);
    let line = |name: &str| crate::results::Line {
        transfer_type: crate::results::TransferType::Upload,
        source: shown_local(name),
        destination: Some(format!("s3://bucket/prefix/{name}").into_bytes()),
    };
    let missing = native_cwd().join("local").join("missing");
    let huge = Path::new("local").join("huge");
    assert_eq!(
        *lock(&sink.results),
        vec![
            crate::results::Event::Warning(transfer::source_skip_warning(
                &native_cwd(),
                &missing,
                transfer::SourceSkip::Missing,
            )),
            crate::results::Event::Warning(transfer::upload_size_warning(&huge)),
            crate::results::Event::DryRun(line("huge")),
            crate::results::Event::DryRun(line("walked")),
        ]
    );
}

#[test]
fn an_upload_whose_mtime_upstream_cannot_read_warns_first_and_is_kept() {
    let (fixture, sink) = dry_run_fixture(false, false);
    lock(&fixture.control.inspections).extend([
        transfer::SourceInspection::InvalidTimestamp(transfer::MAX_UPLOAD_SIZE + 1),
        transfer::SourceInspection::InvalidTimestamp(4),
    ]);
    fixture
        .scheduler
        .handle_upload_entry(Path::new("huge"), None)
        .expect("inspected entry");
    fixture
        .scheduler
        .exclude_upload_source(Path::new("excluded"))
        .expect("excluded source");
    let stats = fixture.stats();
    assert_eq!((stats.submitted, stats.failed, stats.skipped), (0, 0, 0));
    assert_eq!(fixture.scheduler.finished().warned, 3);
    let huge = Path::new("local").join("huge");
    let invalid = || crate::results::Event::Warning(transfer::INVALID_TIMESTAMP_WARNING.to_vec());
    assert_eq!(
        *lock(&sink.results),
        vec![
            invalid(),
            crate::results::Event::Warning(transfer::upload_size_warning(&huge)),
            crate::results::Event::DryRun(crate::results::Line {
                transfer_type: crate::results::TransferType::Upload,
                source: shown_local("huge"),
                destination: Some(b"s3://bucket/prefix/huge".to_vec()),
            }),
            invalid(),
        ]
    );
}

#[test]
fn upload_past_the_size_limit_warns_and_is_still_submitted() {
    let mut fixture = Fixture::new(false, false).with_native_root();
    let sink = Arc::new(Published::default());
    Arc::get_mut(&mut fixture.scheduler)
        .expect("exclusive fixture")
        .sink = sink.clone();
    fixture
        .scheduler
        .handle_upload_entry(Path::new("huge"), Some(transfer::MAX_UPLOAD_SIZE + 1))
        .expect("huge entry");
    assert_eq!(fixture.count(), 1);
    assert_eq!(fixture.scheduler.finished().warned, 1);
    assert_eq!(
        lock(&sink.results).first(),
        Some(&crate::results::Event::Warning(
            transfer::upload_size_warning(&Path::new("local").join("huge"))
        ))
    );
    fixture.finish(0, TransferResult::default());
}

#[test]
fn single_request_admission_accounts_for_size_budget_and_overflow() {
    let mut fixture = Fixture::new(true, false);
    let request = &mut Arc::get_mut(&mut fixture.scheduler)
        .expect("exclusive fixture")
        .request;
    request.runtime.single_request_threshold = Some(10);
    request.sizing.single_request_bytes_max = 6;
    request.sizing.source_pool_bytes = 1;
    assert_eq!(
        fixture
            .scheduler
            .single_request_bytes(transfer::Direction::Download, Some(10)),
        10
    );
    assert_eq!(
        fixture
            .scheduler
            .single_request_bytes(transfer::Direction::Download, Some(11)),
        0
    );
    assert_eq!(
        fixture
            .scheduler
            .single_request_bytes(transfer::Direction::Download, None),
        0
    );
    let mut state = State::default();
    assert!(fixture.scheduler.admits(&state, 10));
    state.in_flight = 1;
    state.single_request_bytes = 4;
    assert!(fixture.scheduler.admits(&state, 2));
    assert!(!fixture.scheduler.admits(&state, 4));
    assert!(fixture.scheduler.admits(&state, 0));
    state.single_request_bytes = u64::MAX;
    assert!(!fixture.scheduler.admits(&state, 1));
    state.in_flight = 4;
    assert!(!fixture.scheduler.admits(&state, 0));
}
#[test]
fn accepted_download_requests_count_on_their_writer_path() {
    let f = Fixture::new(true, false);
    f.control.immediate.store(true, Ordering::Release);
    f.submit("recv-a");
    f.submit("recv-b");
    f.control.custom.store(true, Ordering::Release);
    f.submit("custom");
    f.control.reject.store(true, Ordering::Release);
    f.submit("refused");
    f.control.reject.store(false, Ordering::Release);
    f.control.custom.store(false, Ordering::Release);
    f.control.immediate.store(false, Ordering::Release);
    f.submit("failed");
    f.finish(
        3,
        TransferResult {
            error_code: 1,
            response_status: 500,
            ..Default::default()
        },
    );
    f.scheduler.drain();
    let stats = f.stats();
    assert_eq!(
        (stats.custom_writer_requests, stats.recv_file_requests),
        (1, 3)
    );
    assert_eq!(stats.failed, 2);

    let upload = Fixture::new(false, false);
    upload.control.immediate.store(true, Ordering::Release);
    upload
        .scheduler
        .handle_upload_entry(Path::new("a"), None)
        .expect("upload entry");
    upload.scheduler.drain();
    let stats = upload.stats();
    assert_eq!(stats.succeeded, 1);
    assert_eq!(
        (stats.custom_writer_requests, stats.recv_file_requests),
        (0, 0)
    );
}
fn install_prepare_pool(f: &Fixture, workers: usize, capacity: usize) {
    *lock(&f.scheduler.prepare_pool) = Some(completion::prepare_pool(workers, capacity));
}
fn drain_prepare_pool(f: &Fixture) {
    {
        let mut pool = lock(&f.scheduler.prepare_pool);
        let pool = pool.as_mut().expect("installed pool");
        pool.close();
        pool.start().expect("preparation workers");
    }
    f.scheduler.stop_prepare_pool();
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Stop {
    None,
    Interrupt,
    Exception,
}
fn queue_two_preparations() -> Fixture {
    let mut f = Fixture::configured(true, false, true, false, 2);
    let request = &mut Arc::get_mut(&mut f.scheduler)
        .expect("exclusive fixture")
        .request;
    request.runtime.single_request_threshold = Some(32);
    request.sizing.single_request_bytes_max = 26;
    f.control.immediate.store(true, Ordering::Release);
    install_prepare_pool(&f, 2, 2);
    for (key, size) in [("prefix/first", 7), ("prefix/second", 19)] {
        f.scheduler
            .handle_download_entry(key, size, None)
            .expect("entry");
    }
    f
}
#[test]
fn queued_preparation_retains_budgets_through_completion_or_cancellation() {
    for stop in [Stop::None, Stop::Interrupt, Stop::Exception] {
        let f = queue_two_preparations();
        {
            let state = lock(&f.scheduler.state);
            let queued = (state.in_flight, state.single_request_bytes, state.destroyed);
            assert_eq!(queued, (2, 26, 0));
        }
        assert_eq!(f.count(), 0);
        match stop {
            Stop::None => {}
            Stop::Interrupt => InterruptHook::cancel(&*f.scheduler),
            Stop::Exception => f.scheduler.cancel_for_exception(
                b"Error during pagination".to_vec(),
                &cli_core::interrupt::State::new(),
            ),
        }
        drain_prepare_pool(&f);
        f.scheduler.drain();
        let state = lock(&f.scheduler.state);
        let released = (state.in_flight, state.single_request_bytes, state.destroyed);
        assert_eq!(released, (0, 0, 2));
        let ended = (state.stats.failed, state.canceled, state.stats.succeeded);
        drop(state);
        let sent = (f.count(), f.control.discards.load(Ordering::Relaxed));
        if stop == Stop::None {
            assert_eq!((ended, sent), ((0, 0, 2), (2, 0)));
        } else {
            assert_eq!((ended, sent), ((0, 2, 0), (0, 2)));
        }
    }
}
#[test]
fn closed_preparation_queue_releases_its_reserved_job() {
    let f = Fixture::new(true, false);
    install_prepare_pool(&f, 1, 1);
    lock(&f.scheduler.prepare_pool)
        .as_ref()
        .expect("installed pool")
        .close();
    f.submit("closed");
    f.scheduler.drain();
    assert_eq!(
        f.scheduler.finished().fatal.as_deref(),
        Some("WritePoolClosed")
    );
    let reported = lock(&f.output.events)
        .iter()
        .any(|event| String::from_utf8_lossy(&event.text).contains("WritePoolClosed"));
    assert!(reported, "{:?}", lock(&f.output.events));
    assert_eq!(f.count(), 0);
    assert_eq!(f.control.discards.load(Ordering::Relaxed), 1);
    assert_eq!(f.stats().failed, 1);
    let state = lock(&f.scheduler.state);
    assert_eq!((state.destroyed, state.in_flight), (1, 0));
}

fn conditioned_job(etag: Option<&[u8]>) -> Job {
    Job {
        direction: transfer::Direction::Download,
        raw_key: b"a b".to_vec(),
        request_key: "a%20b".into(),
        local_path: native_cwd().join("file"),
        temp_path: None,
        size: Some(9 * 1024 * 1024),
        size_listed: false,
        size_changed: AtomicBool::new(false),
        modified: None,
        condition: ObjectCondition {
            etag: etag.map(<[u8]>::to_vec),
            ..ObjectCondition::default()
        },
        case_name: None,
        output: Mutex::default(),
        custom_writer: AtomicBool::new(false),
    }
}
fn precondition_failed(operation: &str) -> TransferResult {
    let mut result = TransferResult {
        error_code: 14_343,
        response_status: 412,
        ..TransferResult::default()
    };
    result.service_error.code.set(b"PreconditionFailed");
    result.service_error.message = b"object changed".to_vec();
    result.service_error.operation.set(operation.as_bytes());
    result
}
#[test]
fn a_conditioned_downloads_412_reports_the_service_error() {
    let service = b"An error occurred (PreconditionFailed) when calling the GetObject \
        operation: object changed";
    let get = precondition_failed("GetObject");
    let mut head = TransferResult {
        error_code: 1,
        response_status: 412,
        ..TransferResult::default()
    };
    head.service_error.operation.set(b"HeadObject");
    let conditioned = conditioned_job(Some(b"\"original\""));
    let unconditioned = conditioned_job(None);
    let download = Fixture::new(true, false);
    for result in [&get, &head] {
        assert_eq!(
            download
                .scheduler
                .transfer_failure(&conditioned, result)
                .exception,
            download
                .scheduler
                .transfer_failure(&unconditioned, result)
                .exception
        );
    }
    let failure = download.scheduler.transfer_failure(&conditioned, &get);
    assert_eq!(failure.exception, service);
    let upload = Fixture::new(false, false);
    let conditioned_upload = Job {
        direction: transfer::Direction::Upload,
        ..conditioned_job(Some(b"\"original\""))
    };
    let failure = upload.scheduler.transfer_failure(&conditioned_upload, &get);
    assert_eq!(failure.exception, service);
}
#[test]
fn a_conditioned_download_entry_fails_its_412_with_the_service_error() {
    let f = Fixture::new(true, false);
    f.scheduler
        .submit_entry(Entry {
            key: b"a b".to_vec(),
            local_path: native_cwd().join("file"),
            size: Some(4),
            condition: ObjectCondition {
                etag: Some(b"\"original\"".to_vec()),
                ..ObjectCondition::default()
            },
            ..Entry::default()
        })
        .expect("entry");
    f.finish(0, precondition_failed("GetObject"));
    assert_eq!(f.stats().failed, 1);
    let events = lock(&f.output.events);
    let line = events
        .iter()
        .find(|event| {
            event
                .text
                .starts_with(b"download failed: s3://bucket/a b to ")
        })
        .expect("failure line");
    assert!(
        line.text.ends_with(
            b" An error occurred (PreconditionFailed) when calling the GetObject \
            operation: object changed\n"
        ),
        "{}",
        String::from_utf8_lossy(&line.text)
    );
}

fn move_fixture(download: bool) -> Fixture {
    let mut f = Fixture::new(download, false).with_native_root();
    Arc::get_mut(&mut f.scheduler)
        .expect("exclusive fixture")
        .request
        .sources = transfer::SourceDisposition::Delete {
        user_agent: "agent".into(),
    };
    f
}
fn printed(f: &Fixture) -> Vec<String> {
    lock(&f.output.events)
        .iter()
        .map(|event| String::from_utf8_lossy(&event.text).into_owned())
        .collect()
}
fn local_display(relative: &str) -> String {
    Path::new("local")
        .join(relative)
        .to_string_lossy()
        .into_owned()
}
#[test]
fn a_move_deletes_each_source_its_transfer_moved() {
    let f = move_fixture(true);
    f.submit("moved.txt");
    f.submit("warned.txt");
    f.submit("failed.txt");
    f.finish(0, TransferResult::default());
    *lock(&f.control.outcome) = Finalize::Mtime("Permission denied".into());
    f.finish(1, TransferResult::default());
    f.finish(
        2,
        TransferResult {
            error_code: 1,
            ..TransferResult::default()
        },
    );
    assert_eq!(
        *lock(&f.control.deleted),
        [b"prefix/moved.txt".to_vec(), b"prefix/warned.txt".to_vec()]
    );
    let events: Vec<_> = lock(&f.control.events)
        .iter()
        .copied()
        .filter(|event| *event != "release")
        .collect();
    assert_eq!(events, ["finalize", "delete", "finalize", "delete"]);
    assert_eq!((f.stats().succeeded, f.stats().failed), (2, 1));
    let printed = printed(&f);
    assert_eq!(
        printed[0],
        format!(
            "move: s3://bucket/prefix/moved.txt to {}\n",
            local_display("moved.txt")
        )
    );
    assert!(printed[1].starts_with("warning: Skipping file "));
    assert_eq!(
        printed[2],
        format!(
            "move: s3://bucket/prefix/warned.txt to {}\n",
            local_display("warned.txt")
        )
    );
    assert!(printed[3].starts_with("move failed: s3://bucket/prefix/failed.txt to "));
}
#[test]
fn a_source_that_cannot_be_deleted_fails_the_move() {
    let f = move_fixture(true);
    let mut denied = TransferResult {
        error_code: 14_343,
        response_status: 403,
        ..TransferResult::default()
    };
    denied.service_error.code.set(b"AccessDenied");
    denied.service_error.message = b"Access Denied".to_vec();
    denied.service_error.operation.set(b"DeleteObject");
    *lock(&f.control.delete_failure) = Some(denied);
    f.submit("kept.txt");
    f.finish(0, TransferResult::default());
    assert_eq!((f.stats().succeeded, f.stats().failed), (0, 1));
    assert_eq!(
        printed(&f),
        [format!(
            "move failed: s3://bucket/prefix/kept.txt to {} An error occurred \
            (AccessDenied) when calling the DeleteObject operation: Access Denied\n",
            local_display("kept.txt")
        )]
    );
}
#[test]
fn a_canceled_source_delete_counts_as_ctrl_c() {
    let f = move_fixture(true);
    *lock(&f.control.delete_failure) = Some(TransferResult {
        error_code: crt::s3::CANCELED_ERROR_CODE,
        canceled_by_interrupt: true,
        ..TransferResult::default()
    });
    f.submit("a.txt");
    f.finish(0, TransferResult::default());
    assert_eq!((f.stats().succeeded, f.stats().failed), (0, 0));
    assert_eq!(lock(&f.scheduler.state).canceled, 1);
}
#[test]
fn a_moves_lines_name_the_move_and_a_copy_deletes_nothing() {
    let moved = move_fixture(false);
    let line = moved
        .scheduler
        .entry_line(transfer::Direction::Upload, b"prefix/a", Path::new("a"));
    assert_eq!(line.transfer_type, crate::results::TransferType::Move);
    let copied = Fixture::new(false, false);
    copied.control.immediate.store(true, Ordering::Release);
    copied
        .scheduler
        .handle_upload_entry(Path::new("a"), None)
        .expect("upload entry");
    copied.scheduler.drain();
    assert_eq!(copied.stats().succeeded, 1);
    assert!(lock(&copied.control.deleted).is_empty());
    let line =
        copied
            .scheduler
            .entry_line(transfer::Direction::Upload, b"prefix/a", Path::new("a"));
    assert_eq!(line.transfer_type, crate::results::TransferType::Upload);
}

#[test]
fn a_sync_uploads_delete_names_the_object_alone_among_its_uploads() {
    let f = Fixture::new(false, false);
    f.scheduler
        .handle_upload_entry(Path::new("a"), None)
        .expect("upload entry");
    f.scheduler
        .submit_destination_delete(b"prefix/old".to_vec(), 7)
        .expect("delete entry");
    let jobs = lock(&f.control.submissions).clone();
    assert_eq!(
        jobs[1],
        (b"prefix/old".to_vec(), PathBuf::new(), None, Some(7))
    );
    f.finish(1, TransferResult::default());
    f.finish(0, TransferResult::default());
    f.shutdown();
    f.scheduler.drain();
    let lines: Vec<_> = lock(&f.output.events)
        .iter()
        .map(|event| String::from_utf8_lossy(&event.text).into_owned())
        .collect();
    assert_eq!(lines[0], "delete: s3://bucket/prefix/old\n");
    assert_eq!(f.stats().succeeded, 2);
}

struct LocalFiles(PathBuf);
impl LocalFiles {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!("s3-scheduler-{name}-{}", std::process::id()));
        drop(std::fs::remove_dir_all(&path));
        std::fs::create_dir_all(&path).expect("temporary directory");
        Self(path)
    }
}
impl Drop for LocalFiles {
    fn drop(&mut self) {
        drop(std::fs::remove_dir_all(&self.0));
    }
}
fn local_delete_lines(dryrun: bool) -> (Vec<String>, Stats, bool, LocalFiles) {
    let files = LocalFiles::new(if dryrun { "dryrun-delete" } else { "delete" });
    let gone = files.0.join("gone.txt");
    std::fs::write(&gone, b"gone").expect("file");
    let missing = files.0.join("missing.txt");
    let mut f = Fixture::new(true, false);
    Arc::get_mut(&mut f.scheduler)
        .expect("exclusive fixture")
        .request
        .dryrun = dryrun;
    for path in [&gone, &missing] {
        f.scheduler.delete_local_file(path).expect("delete");
    }
    f.scheduler.drain();
    let lines = lock(&f.output.events)
        .iter()
        .map(|event| String::from_utf8_lossy(&event.text).into_owned())
        .collect();
    (lines, f.stats(), gone.exists(), files)
}

#[test]
fn a_sync_downloads_delete_removes_the_file_or_fails_it() {
    let (lines, stats, kept, files) = local_delete_lines(false);
    let display = |path: &Path| {
        transfer::display_local_path(Path::new("/tmp"), path)
            .display()
            .to_string()
    };
    let (gone, missing) = (files.0.join("gone.txt"), files.0.join("missing.txt"));
    // Windows fails this removal with another error once the directory is
    // gone, so `files` holds it to the end of the test.
    let error = std::fs::remove_file(&missing).expect_err("missing file");
    let failure = transfer::source_removal_failure(Path::new("/tmp"), &missing, &error);
    assert_eq!(
        lines,
        [
            format!("delete: {}\n", display(&gone)),
            format!(
                "delete failed: {} {}\n",
                display(&missing),
                String::from_utf8_lossy(&failure)
            ),
        ]
    );
    assert!(!kept);
    assert_eq!((stats.submitted, stats.succeeded, stats.failed), (2, 1, 1));
}

#[test]
fn a_queued_local_delete_is_done_when_the_queue_returns() {
    let files = LocalFiles::new("queued-delete");
    let gone = files.0.join("gone.txt");
    std::fs::write(&gone, b"gone").expect("file");
    let f = Fixture::new(true, false);
    let gate = Arc::new(Gate::default());
    *lock(&f.control.submit_gate) = Some(gate.clone());
    let mut queue = SubmitQueue::new(f.scheduler.clone(), 2).expect("queue");
    queue.push("prefix/a".into(), 1, None).expect("download");
    let (held, removed) = std::thread::scope(|scope| {
        let deleter = scope.spawn(|| queue.delete_local_file(gone.clone()));
        gate.await_entered();
        let held = !deleter.is_finished() && gone.exists();
        gate.release();
        let deleted = deleter.join().expect("deleter");
        (held, deleted.map(|()| !gone.exists()))
    });
    assert!(held);
    assert!(matches!(removed, Ok(true)));
    queue.close_and_join();
    f.finish(0, TransferResult::default());
    f.shutdown();
    f.scheduler.drain();
    assert_eq!(f.stats().succeeded, 2);
}

#[test]
fn a_local_delete_behind_a_failed_entry_is_refused() {
    let files = LocalFiles::new("refused-delete");
    let kept = files.0.join("kept.txt");
    std::fs::write(&kept, b"kept").expect("file");
    let f = Fixture::new(true, false);
    f.output.fail.store(true, Ordering::Release);
    let mut queue = SubmitQueue::new(f.scheduler.clone(), 2).expect("queue");
    queue
        .push("prefix/../escape".into(), 1, None)
        .expect("first");
    assert!(matches!(
        queue.delete_local_file(kept.clone()),
        Err(Error::QueueClosed)
    ));
    assert!(kept.exists());
    queue.close_and_join();
    f.scheduler.drain();
}

#[test]
fn a_sync_downloads_dry_run_delete_keeps_the_file() {
    let (lines, stats, kept, files) = local_delete_lines(true);
    let display = |path: &Path| {
        transfer::display_local_path(Path::new("/tmp"), path)
            .display()
            .to_string()
    };
    let (gone, missing) = (files.0.join("gone.txt"), files.0.join("missing.txt"));
    assert_eq!(
        lines,
        [
            format!("(dryrun) delete: {}\n", display(&gone)),
            format!("(dryrun) delete: {}\n", display(&missing)),
        ]
    );
    assert!(kept);
    assert_eq!(stats.submitted, 0);
}

#[test]
fn a_case_name_is_held_until_the_download_that_took_it_ends() {
    let f = Fixture::new(true, false);
    assert!(!f.scheduler.holds_case_name("a.txt"));
    f.scheduler.claim_case_name("a.txt");
    f.scheduler
        .handle_listed_entry(
            "prefix/A.txt",
            4,
            Some(1),
            Archive::default(),
            Some("a.txt".into()),
            ObjectCondition::default(),
        )
        .expect("entry");
    assert!(f.scheduler.holds_case_name("a.txt"));
    f.finish(0, TransferResult::default());
    f.shutdown();
    f.scheduler.drain();
    assert!(!f.scheduler.holds_case_name("a.txt"));
}
