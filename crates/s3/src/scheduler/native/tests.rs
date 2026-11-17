#![expect(
    clippy::expect_used,
    reason = "deterministic request fixtures fail immediately on invalid state"
)]
use super::*;
use crate::download::{SharedConfig, WorkerSpawner, WriterMode, testing::fakes};
use crate::results;
use std::fs;
use std::time::{Duration, Instant};
mod replay;
mod without_output;

struct Directory(PathBuf);
impl Directory {
    fn new() -> io::Result<Self> {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = std::env::temp_dir().join(format!(
            "scheduler-native-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path)?;
        Ok(Self(path))
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn request(root: &Path) -> TransferRequest {
    TransferRequest {
        direction: transfer::Direction::Upload,
        bucket: "bucket".into(),
        prefix: "prefix/".into(),
        local_root: root.into(),
        runtime: Default::default(),
        quiet: false,
        dryrun: false,
        no_overwrite: true,
        glacier: transfer::GlacierPolicy::Warn,
        content_types: Some(Arc::new(crate::mime::Database::default())),
        refusal: None,
        page_size: 0,
        max_in_flight: 2,
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
fn job(path: &Path) -> Job {
    Job {
        direction: transfer::Direction::Upload,
        raw_key: b"prefix/key".to_vec(),
        request_key: "prefix/key".into(),
        local_path: path.into(),
        temp_path: None,
        size: Some(7),
        size_listed: false,
        size_changed: AtomicBool::new(false),
        modified: None,
        condition: ObjectCondition::default(),
        case_name: None,
        output: Mutex::default(),
        custom_writer: AtomicBool::new(false),
    }
}

#[test]
fn upload_request_options_use_each_source_name_and_measured_size() -> io::Result<()> {
    let directory = Directory::new()?;
    let operations = CrtOperations {
        runtime: None,
        service: None,
        request: request(&directory.0),
        random: transfer::temp_name_id,
    };
    for (name, expected) in [
        ("file.txt", Some(&b"text/plain"[..])),
        ("file.no-known-extension", None),
    ] {
        let path = directory.0.join(name);
        fs::write(&path, b"1234567")?;
        assert_eq!(
            operations.inspect_source(&path),
            transfer::SourceInspection::Size(7)
        );
        let job = job(&path);
        let content_type = operations
            .content_type(&job)
            .map_err(|error| io::Error::other(format!("{error:?}")))?;
        let options = request_options(&operations.request, &job, None, content_type);
        assert_eq!(options.content_type, expected);
        assert_eq!(options.kind, RequestKind::Put);
        assert_eq!(options.object_size_hint, Some(7));
        assert_eq!(options.filepath, Some(path.as_path()));
        assert!(options.if_none_match);
    }
    Ok(())
}

#[test]
fn each_direction_sends_only_its_own_checksum_setting() -> io::Result<()> {
    use crate::cp::recursive::ChecksumSettings;
    use crt::s3::ChecksumAlgorithm;
    use transfer::Direction;
    let directory = Directory::new()?;
    let mut request = request(&directory.0);
    for (settings, sha256, validate) in [
        (
            ChecksumSettings {
                upload_algorithm: Some(ChecksumAlgorithm::Sha256),
                validate_downloads: true,
            },
            Some(ChecksumAlgorithm::Sha256),
            true,
        ),
        (ChecksumSettings::default(), None, false),
    ] {
        request.checksums = settings;
        for (direction, algorithm, validates) in [
            (Direction::Upload, sha256, false),
            (Direction::Download, None, validate),
            (Direction::Delete, None, false),
        ] {
            request.direction = direction;
            let job = Job {
                direction,
                ..job(&directory.0.join("file"))
            };
            let options = request_options(&request, &job, None, None);
            assert_eq!(
                (options.checksum_algorithm, options.validate_checksum),
                (algorithm, validates),
                "{direction}"
            );
        }
    }
    Ok(())
}

#[test]
fn a_delete_sends_none_of_the_uploads_object_headers() -> io::Result<()> {
    let directory = Directory::new()?;
    let mut request = request(&directory.0);
    request.headers.object = vec![crt::s3::Header::new("cache-control", "max-age=60")];
    let path = directory.0.join("file");
    let upload = job(&path);
    assert_eq!(
        request_options(&request, &upload, None, None).headers.len(),
        1
    );
    let delete = Job {
        direction: transfer::Direction::Delete,
        ..job(&path)
    };
    let options = request_options(&request, &delete, None, None);
    assert_eq!(
        (options.kind, options.headers.len()),
        (RequestKind::Delete, 0)
    );
    Ok(())
}

#[derive(Debug, Default)]
struct Captured(Mutex<Vec<results::Event>>);
impl Sink for Captured {
    fn emit(&self, event: Event) -> Result<(), String> {
        lock(&self.0).push(results::Event::Diagnostic(event.text));
        Ok(())
    }
    fn publish(&self, event: results::Event, _: bool) -> Result<(), String> {
        lock(&self.0).push(event);
        Ok(())
    }
}

#[test]
fn refused_uploads_fail_individually_and_mime_errors_precede_endpoint_rules() -> io::Result<()> {
    let directory = Directory::new()?;
    for name in ["first.txt", "second.txt"] {
        fs::write(directory.0.join(name), b"payload")?;
    }
    let oversized = directory.0.join("mime.types");
    fs::File::create(&oversized)?.set_len(16 * 1024 * 1024 + 1)?;
    for mime_failure in [false, true] {
        let mut request = request(&directory.0);
        request.refusal = Some("endpoint rule refused".into());
        if mime_failure {
            request.content_types = Some(Arc::new(crate::mime::Database::from_files([&oversized])));
        }
        let sink = Arc::new(Captured::default());
        let scheduler = Scheduler::native(request, directory.0.clone(), None, None, sink.clone());
        for name in ["first.txt", "second.txt"] {
            scheduler
                .handle_upload_entry(Path::new(name), None)
                .map_err(|error| io::Error::other(format!("{error:?}")))?;
        }
        scheduler.drain();
        assert_eq!(scheduler.finished().failed, 2);
        let captured = lock(&sink.0);
        let failures: Vec<_> = captured
            .iter()
            .filter_map(|event| match event {
                results::Event::Failure { exception, .. } => Some(exception.as_slice()),
                _ => None,
            })
            .collect();
        assert_eq!(failures.len(), 2);
        assert_refused_messages(&failures, mime_failure);
    }
    Ok(())
}

fn assert_refused_messages(failures: &[&[u8]], mime_failure: bool) {
    for failure in failures {
        if mime_failure {
            assert!(String::from_utf8_lossy(failure).contains("too large"));
            assert!(!String::from_utf8_lossy(failure).contains("endpoint rule"));
        } else {
            assert_eq!(*failure, b"endpoint rule refused");
        }
    }
}

// Botocore resolves the endpoint before it validates the key, so a guess
// that raises, then the command's refusal, outrank an empty key's parameter
// validation; each fails the queued upload without a request.
#[test]
fn an_upload_with_an_empty_key_fails_validation_after_the_refusal() -> io::Result<()> {
    let directory = Directory::new()?;
    let source = directory.0.join("dir");
    fs::create_dir(&source)?;
    let oversized = directory.0.join("mime.types");
    fs::File::create(&oversized)?.set_len(16 * 1024 * 1024 + 1)?;
    let accelerate = "Path-style addressing cannot be used with S3 Accelerate";
    let empty_key = "Parameter validation failed:\n\
        Invalid length for parameter Key, value: 0, valid min length: 1";
    for (refusal, mime_failure, expected) in [
        (None, false, empty_key),
        (Some(accelerate), false, accelerate),
        (Some(accelerate), true, "[Errno 27] File too large"),
    ] {
        let mut request = request(&directory.0);
        request.refusal = refusal.map(Into::into);
        if mime_failure {
            request.content_types = Some(Arc::new(crate::mime::Database::from_files([&oversized])));
        }
        let runtime = Arc::new(FakeRequestRuntime::default());
        *lock(&runtime.submit_failure) = Some(1);
        let sink = Arc::new(Captured::default());
        let scheduler = Scheduler::with_request_runtime(
            request,
            directory.0.clone(),
            Some(Arc::new(Shared(Arc::clone(&runtime)))),
            None,
            sink.clone(),
            transfer::temp_name_id,
        );
        scheduler
            .submit_entry(Entry {
                key: Vec::new(),
                local_path: transfer::normalize_local_directory_root(&source),
                ..Entry::default()
            })
            .map_err(|error| io::Error::other(format!("{error:?}")))?;
        scheduler.drain();
        assert_eq!(runtime.count(), 0);
        assert_eq!(scheduler.finished().failed, 1);
        let failures: Vec<_> = lock(&sink.0)
            .iter()
            .filter_map(|event| match event {
                results::Event::Failure { exception, .. } => Some(exception.clone()),
                _ => None,
            })
            .collect();
        assert_eq!(failures, [expected.as_bytes()]);
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn a_single_upload_of_a_non_utf8_key_fails_with_escaped_name_bytes() -> io::Result<()> {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let directory = Directory::new()?;
    let name = b"invalid-\xff.txt";
    let local = directory.0.join(OsStr::from_bytes(name));
    // APFS and HFS+ refuse a name that is not UTF-8; only that skips.
    match fs::write(&local, b"payload") {
        Err(error) if error.raw_os_error() == Some(libc::EILSEQ) => return Ok(()),
        result => result?,
    }
    let mut request = request(&directory.0);
    request.prefix = Vec::new();
    request.object = Some(crate::cp::recursive::SingleObject {
        key: name.to_vec(),
        local_path: local.clone(),
        ..Default::default()
    });
    let runtime = Arc::new(FakeRequestRuntime::default());
    *lock(&runtime.submit_failure) = Some(1);
    let sink = Arc::new(Captured::default());
    let scheduler = Scheduler::with_request_runtime(
        request,
        directory.0.clone(),
        Some(Arc::new(Shared(Arc::clone(&runtime)))),
        None,
        sink.clone(),
        transfer::temp_name_id,
    );
    scheduler
        .submit_entry(Entry {
            key: name.to_vec(),
            local_path: local,
            ..Entry::default()
        })
        .map_err(|error| io::Error::other(format!("{error:?}")))?;
    scheduler.drain();
    assert_eq!(runtime.count(), 0);
    let mut processor = results::Processor::new(Some(results::PrinterConfig {
        mode: results::Mode::NoProgress,
        ..Default::default()
    }));
    let publisher = processor.publisher();
    for event in lock(&sink.0).drain(..) {
        publisher.publish(event);
    }
    publisher.close();
    let (mut out, mut err) = (Vec::new(), Vec::new());
    processor.run(&mut out, &mut err)?;
    assert!(out.is_empty());
    assert_eq!(
        err,
        [
            br"upload failed: ./invalid-\udcff.txt to s3://bucket/invalid-\udcff.txt ".as_slice(),
            br"'utf-8' codec can't encode character '\udcff' in position 8: ",
            b"surrogates not allowed\n",
        ]
        .concat()
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[cfg_attr(
    miri,
    ignore = "calls the C library's strerror, which Miri does not implement"
)]
fn a_single_upload_of_a_directory_fails_opening_it_after_the_refusals() -> io::Result<()> {
    let directory = Directory::new()?;
    let source = directory.0.join("dir");
    fs::create_dir(&source)?;
    let link = directory.0.join("link");
    std::os::unix::fs::symlink(&source, &link)?;
    let file = directory.0.join("file.txt");
    fs::write(&file, b"payload")?;
    let accelerate = "Path-style addressing cannot be used with S3 Accelerate";
    let empty_key = "Parameter validation failed:\n\
        Invalid length for parameter Key, value: 0, valid min length: 1";
    let open_failure = |path: &Path| format!("[Errno 21] Is a directory: '{}/'", path.display());
    for (path, key, refusal, expected) in [
        (&source, &b"k"[..], None, Some(open_failure(&source))),
        (&link, b"k", None, Some(open_failure(&link))),
        (&source, b"", None, Some(empty_key.to_owned())),
        (&source, b"k", Some(accelerate), Some(accelerate.to_owned())),
        (&file, b"k", None, None),
    ] {
        let local_path = if path.is_dir() {
            transfer::normalize_local_directory_root(path)
        } else {
            path.clone()
        };
        let mut request = request(&directory.0);
        request.prefix = Vec::new();
        request.refusal = refusal.map(Into::into);
        request.object = Some(crate::cp::recursive::SingleObject {
            key: key.to_vec(),
            local_path: local_path.clone(),
            ..Default::default()
        });
        let runtime = Arc::new(FakeRequestRuntime::default());
        *lock(&runtime.submit_failure) = Some(1);
        let sink = Arc::new(Captured::default());
        let scheduler = Scheduler::with_request_runtime(
            request,
            directory.0.clone(),
            Some(Arc::new(Shared(Arc::clone(&runtime)))),
            None,
            sink.clone(),
            transfer::temp_name_id,
        );
        scheduler
            .submit_entry(Entry {
                key: key.to_vec(),
                local_path,
                ..Entry::default()
            })
            .map_err(|error| io::Error::other(format!("{error:?}")))?;
        scheduler.drain();
        assert_eq!(scheduler.finished().failed, 1);
        assert_eq!(runtime.count(), usize::from(expected.is_none()));
        let failures: Vec<_> = lock(&sink.0)
            .iter()
            .filter_map(|event| match event {
                results::Event::Failure { exception, .. } => Some(exception.clone()),
                _ => None,
            })
            .collect();
        if let Some(expected) = expected {
            assert_eq!(failures, [expected.into_bytes()]);
        }
    }
    Ok(())
}

#[test]
fn every_download_temp_name_draws_a_fresh_random_id() {
    let operations = CrtOperations {
        runtime: None,
        service: None,
        request: request(Path::new("/")),
        random: transfer::temp_name_id,
    };
    let first = operations.temp_path(Path::new("foo")).expect("first name");
    let second = operations.temp_path(Path::new("foo")).expect("second name");
    for temp in [&first, &second] {
        let name = temp.to_str().expect("UTF-8");
        assert_eq!(&name[..4], "foo.");
        assert_eq!(name[4..].len(), 16);
    }
    assert_ne!(first, second);
}

struct Sent {
    key: Vec<u8>,
    filepath: Option<PathBuf>,
    body_consumer: bool,
    if_match: Option<Vec<u8>>,
    check_object_size: bool,
    body: Mutex<Option<CallbackBodyFn>>,
    callbacks: Mutex<Option<Arc<dyn RequestCallbacks>>>,
    released: AtomicBool,
}
impl fmt::Debug for Sent {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Sent")
            .field("key", &self.key)
            .finish_non_exhaustive()
    }
}
type RecoveryHook = Box<dyn Fn() + Send + Sync>;
#[derive(Default)]
struct FakeRequestRuntime {
    sent: Mutex<Vec<Arc<Sent>>>,
    changed: Condvar,
    recovery: Mutex<Option<Outcome>>,
    recoveries: AtomicUsize,
    before_recovery: Mutex<Option<RecoveryHook>>,
    submit_failure: Mutex<Option<i32>>,
    recv_file_failure: Mutex<Option<i32>>,
    waited: Mutex<Vec<Waited>>,
    waited_result: Mutex<Option<TransferResult>>,
}
type Waited = (RequestKind, Vec<u8>, Option<Vec<u8>>);
impl fmt::Debug for FakeRequestRuntime {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("FakeRequestRuntime")
            .field("sent", &self.sent)
            .finish_non_exhaustive()
    }
}
#[derive(Debug)]
struct FakeRequest {
    sent: Arc<Sent>,
    runtime: Arc<FakeRequestRuntime>,
}
impl OwnedRequest for FakeRequest {
    fn cancel(&self) {}
}
impl Drop for FakeRequest {
    fn drop(&mut self) {
        let _sent = lock(&self.runtime.sent);
        self.sent.released.store(true, Ordering::Release);
        self.runtime.changed.notify_all();
    }
}
#[derive(Debug)]
struct Shared(Arc<FakeRequestRuntime>);
impl RequestRuntime for Shared {
    fn submit(
        &self,
        options: RequestOptions<'_>,
        body: Option<CallbackBodyFn>,
        callbacks: Arc<dyn RequestCallbacks>,
    ) -> Result<Box<dyn OwnedRequest>, Box<TransferResult>> {
        let refusal = (*lock(&self.0.submit_failure)).or_else(|| {
            body.is_none()
                .then(|| *lock(&self.0.recv_file_failure))
                .flatten()
        });
        let accepted = refusal.is_none();
        let sent = Arc::new(Sent {
            key: options.key.to_vec(),
            filepath: options.filepath.map(Path::to_path_buf),
            body_consumer: body.is_some(),
            if_match: options.condition.map(|condition| condition.etag.to_vec()),
            check_object_size: options.check_object_size,
            body: Mutex::new(body.filter(|_| accepted)),
            callbacks: Mutex::new(accepted.then_some(callbacks)),
            released: AtomicBool::new(false),
        });
        lock(&self.0.sent).push(Arc::clone(&sent));
        self.0.changed.notify_all();
        if let Some(code) = refusal {
            return Err(Box::new(TransferResult {
                error_code: code,
                ..TransferResult::default()
            }));
        }
        Ok(Box::new(FakeRequest {
            sent,
            runtime: Arc::clone(&self.0),
        }))
    }
    fn recover_region(&self, _: &TransferResult) -> Outcome {
        self.0.recoveries.fetch_add(1, Ordering::AcqRel);
        if let Some(hook) = lock(&self.0.before_recovery).as_ref() {
            hook();
        }
        lock(&self.0.recovery).unwrap_or(Outcome::Unavailable)
    }
    fn send(&self, options: RequestOptions<'_>) -> Result<TransferResult, Box<TransferResult>> {
        lock(&self.0.waited).push((
            options.kind,
            options.key.to_vec(),
            options.user_agent.map(<[u8]>::to_vec),
        ));
        Ok(lock(&self.0.waited_result).clone().unwrap_or_default())
    }
}
impl FakeRequestRuntime {
    fn sent(&self, index: usize) -> Arc<Sent> {
        Arc::clone(&lock(&self.sent)[index])
    }
    fn count(&self) -> usize {
        lock(&self.sent).len()
    }
    fn await_sent(&self, count: usize) {
        let deadline = Instant::now() + Duration::from_secs(30);
        let mut sent = lock(&self.sent);
        while sent.len() < count {
            assert!(Instant::now() < deadline, "timed out waiting for requests");
            sent = self
                .changed
                .wait_timeout(sent, Duration::from_millis(10))
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .0;
        }
    }
    fn deliver_body(&self, index: usize, bytes: &[u8]) -> Result<(), i32> {
        let sent = self.sent(index);
        let mut body = lock(&sent.body);
        let consume = body.as_mut().expect("a body consumer");
        consume(CallbackBody::Transient {
            bytes,
            range_start: 0,
        })
    }
    fn progress(&self, index: usize, bytes: u64) {
        let callbacks = lock(&self.sent(index).callbacks)
            .clone()
            .expect("a request not shut down");
        callbacks.progress(bytes);
    }
    fn write_recv_file(&self, index: usize, bytes: &[u8]) -> io::Result<()> {
        let sent = self.sent(index);
        assert!(!sent.body_consumer);
        fs::write(sent.filepath.as_ref().expect("recv_filepath"), bytes)
    }
    fn finish(&self, index: usize, result: TransferResult) {
        let callbacks = lock(&self.sent(index).callbacks)
            .clone()
            .expect("a request not shut down");
        callbacks.finish(result);
    }
    fn shutdown(&self, index: usize) {
        let mut sent = lock(&self.sent);
        while !sent[index].released.load(Ordering::Acquire) {
            sent = wait(&self.changed, sent);
        }
        let request = Arc::clone(&sent[index]);
        drop(sent);
        drop(lock(&request.body).take());
        let callbacks = lock(&request.callbacks).take();
        callbacks.expect("one shutdown").shutdown();
    }
    fn released(&self) -> usize {
        lock(&self.sent)
            .iter()
            .filter(|sent| sent.released.load(Ordering::Acquire))
            .count()
    }
}

#[derive(Debug)]
struct Spawner;
impl WorkerSpawner for Spawner {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> io::Result<std::thread::JoinHandle<()>> {
        std::thread::Builder::new().name(name).spawn(worker)
    }
}
fn one_object_service(mode: WriterMode) -> Arc<SharedWriterService> {
    Arc::new(
        SharedWriterService::start(SharedConfig {
            writer: fakes::config(mode),
            custom_writer_required: true,
            in_flight_max: 1,
            ..SharedConfig::default()
        })
        .expect("shared service"),
    )
}

const TEMP_NAME_ID: u64 = 0xabab_abab_abab_abab;
fn fixed_temp_name_id() -> std::io::Result<u64> {
    Ok(TEMP_NAME_ID)
}
struct Fixture {
    directory: Directory,
    runtime: Arc<FakeRequestRuntime>,
    service: Arc<SharedWriterService>,
    scheduler: Arc<Scheduler>,
    sink: Arc<Captured>,
}
impl Fixture {
    fn new(service: Arc<SharedWriterService>, window: u32, finish_workers: usize) -> Self {
        Self::configured(service, finish_workers, |request| {
            request.max_in_flight = window;
        })
    }
    fn configured(
        service: Arc<SharedWriterService>,
        finish_workers: usize,
        configure: impl FnOnce(&mut TransferRequest),
    ) -> Self {
        let directory = Directory::new().expect("directory");
        let mut request = request(&directory.0);
        request.direction = transfer::Direction::Download;
        request.prefix = Vec::new();
        request.no_overwrite = false;
        request.content_types = None;
        request.collect_stats = true;
        request.quiet = true;
        configure(&mut request);
        let runtime = Arc::new(FakeRequestRuntime::default());
        let sink = Arc::new(Captured::default());
        let scheduler = Scheduler::with_request_runtime(
            request,
            directory.0.clone(),
            Some(Arc::new(Shared(Arc::clone(&runtime)))),
            Some(Arc::clone(&service)),
            sink.clone(),
            fixed_temp_name_id,
        );
        scheduler
            .start_finish_pool(finish_workers)
            .expect("finish pool");
        Self {
            directory,
            runtime,
            service,
            scheduler,
            sink,
        }
    }
    fn one_object(mode: WriterMode) -> Self {
        let fixture = Self::new(one_object_service(mode), 1, 1);
        fs::write(fixture.destination_path(), b"old").expect("existing destination");
        *lock(&fixture.runtime.recovery) = Some(Outcome::Ready);
        fixture
    }
    fn destination_path(&self) -> PathBuf {
        self.directory.0.join("file")
    }
    fn submit(&self, key: &str, size: u64) {
        self.scheduler
            .handle_download_entry(key, size, None)
            .expect("entry");
    }
    fn drain(&self) {
        self.scheduler.drain();
        self.scheduler.close_write_pool();
    }
    fn destination(&self) -> Vec<u8> {
        fs::read(self.destination_path()).expect("destination")
    }
    fn stray_files(&self) -> usize {
        fs::read_dir(&self.directory.0)
            .expect("directory")
            .filter(|entry| entry.as_ref().expect("entry").file_name() != "file")
            .count()
    }
    fn stats(&self) -> crate::cp::recursive::Stats {
        self.scheduler.finished().stats.expect("stats")
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        self.service.close_and_join();
    }
}
fn moved() -> TransferResult {
    TransferResult {
        error_code: 91,
        response_status: 301,
        ..TransferResult::default()
    }
}
fn failed() -> TransferResult {
    TransferResult {
        error_code: 1,
        response_status: 500,
        ..TransferResult::default()
    }
}
fn ok() -> TransferResult {
    TransferResult {
        response_status: 200,
        ..TransferResult::default()
    }
}
fn size_changed() -> TransferResult {
    TransferResult {
        error_code: crt::s3::SIZE_CHANGED_ERROR_CODE,
        response_status: 200,
        size_changed: true,
        ..TransferResult::default()
    }
}
fn failure_exceptions(sink: &Captured) -> Vec<Vec<u8>> {
    lock(&sink.0)
        .iter()
        .filter_map(|event| match event {
            results::Event::Failure { exception, .. } => Some(exception.clone()),
            _ => None,
        })
        .collect()
}

// A one-object download's every GET carries its HEAD's ETag, whoever
// receives its bodies: the CRT writing the temp path itself, a native
// output, or none when the output could not be prepared. A listed download
// carries none: the CRT conditions its ranged GETs on its own discovery.
#[test]
fn every_get_of_a_one_object_download_carries_its_head_etag() {
    let etag = b"\"original\"";
    for (mode, unprepared) in [
        (WriterMode::Crt, false),
        (WriterMode::Pwrite, false),
        (WriterMode::Pwrite, true),
    ] {
        let f = Fixture::one_object(mode);
        if unprepared {
            let blocker = format!("file.{TEMP_NAME_ID:016x}");
            fs::create_dir(f.directory.0.join(blocker)).expect("blocker");
        }
        f.scheduler
            .submit_entry(Entry {
                key: b"file".to_vec(),
                local_path: f.destination_path(),
                size: Some(5),
                condition: ObjectCondition {
                    etag: Some(etag.to_vec()),
                    ..ObjectCondition::default()
                },
                ..Entry::default()
            })
            .expect("entry");
        f.runtime.await_sent(1);
        let sent = f.runtime.sent(0);
        assert_eq!(sent.if_match.as_deref(), Some(&etag[..]), "{mode:?}");
        assert_eq!(sent.body_consumer, mode != WriterMode::Crt, "{mode:?}");
        f.runtime.finish(0, failed());
        f.runtime.shutdown(0);
        f.drain();
    }
    let f = Fixture::one_object(WriterMode::Pwrite);
    f.submit("file", 5);
    f.runtime.await_sent(1);
    assert_eq!(f.runtime.sent(0).if_match, None);
    f.runtime.finish(0, failed());
    f.runtime.shutdown(0);
    f.drain();
}

#[test]
fn a_body_without_bytes_fails_the_output() {
    let f = Fixture::configured(one_object_service(WriterMode::Pwrite), 1, |request| {
        request.max_in_flight = 1;
    });
    f.submit("file", 5);
    let sent = f.runtime.sent(0);
    assert!(sent.body_consumer);
    let refused = lock(&sent.body).as_mut().expect("a body consumer")(CallbackBody::Missing);
    assert_eq!(refused, Err(crt::s3::UNKNOWN_ERROR_CODE));
    // The CRT fails a request whose body callback failed.
    f.runtime.finish(
        0,
        TransferResult {
            error_code: crt::s3::UNKNOWN_ERROR_CODE,
            response_status: 200,
            body_delivered: true,
            ..TransferResult::default()
        },
    );
    f.runtime.shutdown(0);
    f.drain();

    assert!(!f.destination_path().exists());
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.service.active_outputs(), 0);
    let stats = f.stats();
    assert_eq!((stats.failed, stats.succeeded), (1, 0));
    assert_eq!(
        failure_exceptions(&f.sink),
        [b"DownloadBodyMissing".to_vec()]
    );
}

#[test]
#[cfg_attr(
    miri,
    ignore = "calls the C library's strerror, which Miri does not implement"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test follows the download from its temp file to the failed commit"
)]
fn a_nul_the_temp_name_drops_fails_only_the_commit() {
    let f = Fixture::configured(one_object_service(WriterMode::Pwrite), 1, |request| {
        request.max_in_flight = 1;
    });
    fs::write(f.destination_path(), b"old").expect("existing destination");
    f.submit(&format!("{}\0.backup", "a".repeat(238)), 5);

    assert_eq!(f.runtime.count(), 1);
    assert!(f.runtime.sent(0).body_consumer);
    assert_eq!(f.service.active_outputs(), 1);
    assert_eq!(f.stray_files(), 1);
    assert_eq!(f.runtime.deliver_body(0, b"hello"), Ok(()));
    f.runtime.finish(
        0,
        TransferResult {
            body_delivered: true,
            ..ok()
        },
    );
    f.runtime.shutdown(0);
    f.drain();

    assert_eq!(f.destination(), b"old");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.stats().failed, 1);
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
    let stats = f.stats();
    assert_eq!(
        (stats.custom_writer_requests, stats.recv_file_requests),
        (1, 0)
    );
}

#[derive(Debug, Default)]
struct Progressing {
    captured: Captured,
    wants: bool,
    reported: AtomicU64,
}
impl Sink for Progressing {
    fn emit(&self, event: Event) -> Result<(), String> {
        self.captured.emit(event)
    }
    fn publish(&self, event: results::Event, quiet: bool) -> Result<(), String> {
        self.captured.publish(event, quiet)
    }
    fn progress(&self, bytes: u64) {
        self.reported.fetch_add(bytes, Ordering::Relaxed);
    }
    fn wants_progress(&self) -> bool {
        self.wants
    }
}
fn progress_through_the_crt(mode: Option<WriterMode>, wants: bool) -> (u64, Option<u64>) {
    let directory = Directory::new().expect("directory");
    let mut request = request(&directory.0);
    let service = mode.map(one_object_service);
    if service.is_some() {
        request.direction = transfer::Direction::Download;
        request.prefix = Vec::new();
        request.no_overwrite = false;
        request.max_in_flight = 1;
    }
    let runtime = Arc::new(FakeRequestRuntime::default());
    let sink = Arc::new(Progressing {
        wants,
        ..Progressing::default()
    });
    let scheduler = Scheduler::with_request_runtime(
        request,
        directory.0.clone(),
        Some(Arc::new(Shared(Arc::clone(&runtime)))),
        service.clone(),
        sink.clone(),
        fixed_temp_name_id,
    );
    scheduler.start_finish_pool(1).expect("finish pool");
    if service.is_some() {
        scheduler.handle_download_entry("file", 5, None)
    } else {
        fs::write(directory.0.join("file"), b"payload").expect("source");
        scheduler.handle_upload_entry(Path::new("file"), None)
    }
    .expect("entry");
    runtime.progress(0, 5);
    runtime.finish(0, failed());
    runtime.shutdown(0);
    scheduler.drain();
    scheduler.close_write_pool();
    if let Some(service) = service {
        service.close_and_join();
    }
    let transferred = lock(&sink.captured.0)
        .iter()
        .find_map(|event| match event {
            results::Event::Failure { transferred, .. } => Some(*transferred),
            _ => None,
        })
        .expect("a failure");
    (sink.reported.load(Ordering::Relaxed), transferred)
}

#[test]
fn only_a_sink_that_draws_progress_hears_of_each_requests_progress() {
    for mode in [None, Some(WriterMode::Crt), Some(WriterMode::Pwrite)] {
        for wants in [false, true] {
            let moved = if wants { 5 } else { 0 };
            assert_eq!(
                progress_through_the_crt(mode, wants),
                (moved, Some(moved)),
                "{mode:?} wants={wants}"
            );
        }
    }
}

fn move_operations(
    root: &Path,
    direction: transfer::Direction,
    runtime: &Arc<FakeRequestRuntime>,
) -> CrtOperations {
    CrtOperations {
        runtime: Some(Arc::new(Shared(Arc::clone(runtime)))),
        service: None,
        request: TransferRequest {
            direction,
            sources: transfer::SourceDisposition::Delete {
                user_agent: "agent".into(),
            },
            ..request(root)
        },
        random: transfer::temp_name_id,
    }
}
#[test]
fn a_moved_downloads_object_is_deleted_with_the_moves_user_agent() -> io::Result<()> {
    let directory = Directory::new()?;
    let runtime = Arc::new(FakeRequestRuntime::default());
    let operations = move_operations(&directory.0, transfer::Direction::Download, &runtime);
    let job = job(&directory.0.join("key"));
    assert!(operations.delete_source(&job).is_ok());
    *lock(&runtime.waited_result) = Some(failed());
    let error = operations.delete_source(&job);
    assert!(
        matches!(&error, Err(SourceDeleteError::Request(result)) if **result == failed()),
        "{error:?}"
    );
    let delete = (
        RequestKind::Delete,
        b"prefix/key".to_vec(),
        Some(b"agent".to_vec()),
    );
    assert_eq!(*lock(&runtime.waited), [delete.clone(), delete]);
    assert_eq!(runtime.count(), 0);
    Ok(())
}
#[cfg(unix)]
#[test]
fn a_moved_uploads_file_is_unlinked() -> io::Result<()> {
    let directory = Directory::new()?;
    let target = directory.0.join("target");
    let link = directory.0.join("link");
    fs::write(&target, b"payload")?;
    std::os::unix::fs::symlink(&target, &link)?;
    let runtime = Arc::new(FakeRequestRuntime::default());
    let copy = CrtOperations {
        runtime: None,
        service: None,
        request: request(&directory.0),
        random: transfer::temp_name_id,
    };
    assert!(copy.delete_source(&job(&link)).is_ok());
    assert!(fs::symlink_metadata(&link).is_ok());
    let operations = move_operations(&directory.0, transfer::Direction::Upload, &runtime);
    assert!(operations.delete_source(&job(&link)).is_ok());
    assert!(fs::symlink_metadata(&link).is_err());
    assert_eq!(fs::read(&target)?, b"payload");
    let error = operations.delete_source(&job(&link));
    let missing = |error: &io::Error| error.kind() == io::ErrorKind::NotFound;
    assert!(
        matches!(&error, Err(SourceDeleteError::Local(error)) if missing(error)),
        "{error:?}"
    );
    assert!(lock(&runtime.waited).is_empty());
    Ok(())
}
