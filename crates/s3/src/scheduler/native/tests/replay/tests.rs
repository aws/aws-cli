#![expect(
    clippy::expect_used,
    reason = "deterministic request fixtures fail immediately on invalid state"
)]
use super::*;

#[test]
fn a_redirect_replays_a_download_once_on_a_fresh_output() {
    let f = Fixture::one_object(WriterMode::Pwrite);
    f.submit("file", 5);
    assert_eq!(f.service.active_outputs(), 1);
    f.runtime.finish(0, moved());
    f.runtime.shutdown(0);
    f.runtime.await_sent(2);
    assert_eq!(f.runtime.deliver_body(1, b"hello"), Ok(()));
    assert_eq!(f.service.active_outputs(), 1);
    f.runtime.finish(1, ok());
    f.runtime.shutdown(1);
    f.drain();

    assert_eq!(f.destination(), b"hello");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.service.active_outputs(), 0);
    assert_eq!(f.runtime.recoveries.load(Ordering::Acquire), 1);
    let stats = f.stats();
    assert_eq!((stats.submitted, stats.succeeded), (1, 1));
    assert_eq!(f.runtime.released(), 2);
}

#[test]
fn close_failure_during_redirect_retirement_prevents_region_recovery() {
    let platform = Arc::new(fakes::FakePlatform::default());
    *lock(&platform.close_failure) = Some(crate::download::CloseError::InputOutput);
    let service = Arc::new(
        SharedWriterService::start_with(
            SharedConfig {
                writer: fakes::config(WriterMode::Pwrite),
                custom_writer_required: true,
                in_flight_max: 1,
                ..SharedConfig::default()
            },
            Arc::clone(&platform) as Arc<dyn crate::download::platform::Platform>,
            Arc::new(Spawner),
        )
        .expect("shared service"),
    );
    let f = Fixture::new(service, 1, 1);
    fs::write(f.destination_path(), b"original").expect("existing destination");
    *lock(&f.runtime.recovery) = Some(Outcome::Ready);
    f.submit("file", 5);
    f.runtime.finish(0, moved());
    f.runtime.shutdown(0);
    f.drain();

    assert_eq!(f.destination(), b"original");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.service.active_outputs(), 0);
    assert_eq!(platform.closes.load(Ordering::Acquire), 1);
    assert_eq!(f.runtime.recoveries.load(Ordering::Acquire), 0);
    assert_eq!(f.runtime.count(), 1);
    let stats = f.stats();
    assert_eq!((stats.failed, stats.succeeded), (1, 0));
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
    assert!(lock(&f.sink.0).iter().any(|event| matches!(
        event,
        results::Event::Failure { exception, .. } if exception == b"Input/output error"
    )));
}

#[test]
fn a_redirect_replay_keeps_the_heads_etag() {
    let etag = b"\"original\"";
    let f = Fixture::one_object(WriterMode::Pwrite);
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
    f.runtime.finish(0, moved());
    f.runtime.shutdown(0);
    f.runtime.await_sent(2);
    for index in 0..2 {
        assert_eq!(f.runtime.sent(index).if_match.as_deref(), Some(&etag[..]));
    }
    f.runtime.finish(1, failed());
    f.runtime.shutdown(1);
    f.drain();
    assert_eq!(f.stats().failed, 1);
}

#[test]
fn a_redirect_replays_a_crt_download_as_a_second_counted_recv_filepath_get() {
    let f = Fixture::one_object(WriterMode::Crt);
    f.submit("file", 5);
    f.runtime.finish(0, moved());
    f.runtime.shutdown(0);
    f.runtime.await_sent(2);
    f.runtime.write_recv_file(1, b"hello").expect("recv file");
    f.runtime.finish(1, ok());
    f.runtime.shutdown(1);
    f.drain();

    assert_eq!(f.destination(), b"hello");
    assert_eq!(f.stray_files(), 0);
    let stats = f.stats();
    assert_eq!(stats.succeeded, 1);
    assert_eq!(
        (stats.custom_writer_requests, stats.recv_file_requests),
        (0, 2)
    );
}

#[test]
#[cfg_attr(miri, ignore = "replays large objects, which takes Miri too long")]
fn redirect_replays_of_large_objects_never_wait_for_output_admission() {
    for first_preparation_fails in [false, true] {
        replay_large_objects_beside_a_waiting_one(first_preparation_fails);
    }
}
fn replay_large_objects_beside_a_waiting_one(first_preparation_fails: bool) {
    const LARGE: u64 = 64 * 1024 * 1024;
    let service = Arc::new(
        SharedWriterService::start_with(
            SharedConfig {
                writer: fakes::config(WriterMode::Pwrite),
                custom_writer_required: false,
                in_flight_max: 3,
                ..SharedConfig::default()
            },
            Arc::new(fakes::FakePlatform::default()),
            Arc::new(Spawner),
        )
        .expect("shared service"),
    );
    let f = Fixture::new(Arc::clone(&service), 3, 2);
    *lock(&f.runtime.recovery) = Some(Outcome::Ready);
    let full = Arc::clone(&service);
    *lock(&f.runtime.before_recovery) = Some(Box::new(move || {
        let deadline = Instant::now() + Duration::from_secs(30);
        while !full.large_admission_full() {
            assert!(Instant::now() < deadline, "large admission never filled");
            std::thread::yield_now();
        }
    }));
    if first_preparation_fails {
        let blocker = format!("first.{TEMP_NAME_ID:016x}");
        fs::create_dir(f.directory.0.join(blocker)).expect("blocker");
    }
    f.submit("first", LARGE);
    f.submit("second", LARGE);
    std::thread::scope(|scope| {
        let waiting = scope.spawn(|| f.submit("third", LARGE));
        await_admission_waiters(&service, 1);
        for index in 0..2 {
            f.runtime.finish(index, moved());
            f.runtime.shutdown(index);
        }
        f.runtime.await_sent(4);
        for index in 2..4 {
            assert_ne!(f.runtime.sent(index).key, b"third");
        }
        assert_eq!(service.admission_waiters(), 1);
        for index in 2..4 {
            f.runtime.finish(index, failed());
            f.runtime.shutdown(index);
        }
        f.runtime.await_sent(5);
        f.runtime.finish(4, failed());
        f.runtime.shutdown(4);
        waiting.join().expect("waiting submitter");
    });
    f.drain();

    assert_eq!(service.active_outputs(), 0);
    assert_eq!(f.runtime.recoveries.load(Ordering::Acquire), 2);
    assert_eq!(f.stats().failed, 3);
    assert_eq!(lock(&f.scheduler.state).destroyed, 3);
    assert_eq!(f.runtime.count(), 5);
}
fn await_admission_waiters(service: &SharedWriterService, count: usize) {
    let deadline = Instant::now() + Duration::from_secs(30);
    while service.admission_waiters() != count {
        assert!(
            Instant::now() < deadline,
            "no submitter waits for admission"
        );
        std::thread::yield_now();
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SlotPath {
    Committed,
    Failed,
    Refused,
    PreparationFailed,
    ReplayCommitted,
    ReplayAfterFailedPreparation,
    ReplayRefused,
    ReplayRedirected,
    DiscoveryUnavailable,
    DiscoveryCanceled,
    ReplayInterrupted,
    ServiceClosedBeforeAcquire,
    ServiceClosedAfterAcquire,
}
impl SlotPath {
    const ALL: [Self; 13] = [
        Self::Committed,
        Self::Failed,
        Self::Refused,
        Self::PreparationFailed,
        Self::ReplayCommitted,
        Self::ReplayAfterFailedPreparation,
        Self::ReplayRefused,
        Self::ReplayRedirected,
        Self::DiscoveryUnavailable,
        Self::DiscoveryCanceled,
        Self::ReplayInterrupted,
        Self::ServiceClosedBeforeAcquire,
        Self::ServiceClosedAfterAcquire,
    ];
    fn redirects(self) -> bool {
        !matches!(
            self,
            Self::Committed | Self::Failed | Self::Refused | Self::PreparationFailed
        )
    }
    fn commits(self) -> bool {
        matches!(
            self,
            Self::Committed | Self::ReplayCommitted | Self::ReplayAfterFailedPreparation
        )
    }
    fn preparation_fails(self) -> bool {
        matches!(
            self,
            Self::PreparationFailed | Self::ReplayAfterFailedPreparation
        )
    }
    fn holds_slot(self) -> bool {
        !matches!(self, Self::Refused | Self::ServiceClosedBeforeAcquire)
    }
    fn large(self) -> bool {
        matches!(
            self,
            Self::ServiceClosedBeforeAcquire | Self::ServiceClosedAfterAcquire
        )
    }
    fn recovery(self) -> Outcome {
        match self {
            Self::DiscoveryUnavailable => Outcome::Unavailable,
            Self::DiscoveryCanceled => Outcome::Canceled,
            _ => Outcome::Ready,
        }
    }
}

#[test]
fn every_terminal_path_releases_a_downloads_output_slot_exactly_once() {
    for path in SlotPath::ALL {
        let f = Fixture::new(one_object_service(WriterMode::Pwrite), 1, 1);
        let admitted = Arc::new(Mutex::new(None));
        *lock(&f.runtime.recovery) = Some(path.recovery());
        *lock(&f.runtime.before_recovery) = Some(slot_recovery(&f, path, Arc::clone(&admitted)));
        if path == SlotPath::Refused {
            *lock(&f.runtime.submit_failure) = Some(42);
        }
        if path.preparation_fails() {
            fs::create_dir(f.directory.0.join(format!("file.{TEMP_NAME_ID:016x}")))
                .expect("blocker");
        }
        if path == SlotPath::ServiceClosedBeforeAcquire {
            f.service.close_and_join();
        }
        f.submit("file", if path.large() { 64 << 20 } else { 5 });
        assert_eq!(
            f.service.active_outputs(),
            usize::from(path.holds_slot()),
            "{path:?}"
        );
        if path == SlotPath::ServiceClosedAfterAcquire {
            f.service.close_and_join();
        }
        answer_first_attempt(&f, path);
        answer_replay(&f, path);
        f.drain();
        expect_slot_released(&f, path, *lock(&admitted));
    }
}
fn slot_recovery(f: &Fixture, path: SlotPath, admitted: Arc<Mutex<Option<usize>>>) -> RecoveryHook {
    let service = Arc::clone(&f.service);
    let runtime = Arc::downgrade(&f.runtime);
    let scheduler = Arc::downgrade(&f.scheduler);
    let blocker = f.directory.0.join(format!("file.{TEMP_NAME_ID:016x}"));
    Box::new(move || {
        *lock(&admitted) = Some(service.active_outputs());
        match path {
            SlotPath::ReplayAfterFailedPreparation => {
                fs::remove_dir(&blocker).expect("unblock the temp path");
            }
            SlotPath::ReplayRefused => {
                let runtime = runtime.upgrade().expect("runtime");
                *lock(&runtime.submit_failure) = Some(42);
            }
            SlotPath::ReplayInterrupted => {
                let scheduler = scheduler.upgrade().expect("scheduler");
                cli_core::InterruptHook::cancel(scheduler.as_ref());
            }
            _ => {}
        }
    })
}
fn answer_first_attempt(f: &Fixture, path: SlotPath) {
    let result = match path {
        SlotPath::Refused => return,
        SlotPath::Committed => {
            assert_eq!(f.runtime.deliver_body(0, b"hello"), Ok(()));
            ok()
        }
        SlotPath::Failed | SlotPath::PreparationFailed => failed(),
        _ => moved(),
    };
    f.runtime.finish(0, result);
    f.runtime.shutdown(0);
}
fn answer_replay(f: &Fixture, path: SlotPath) {
    let result = match path {
        SlotPath::ReplayCommitted | SlotPath::ReplayAfterFailedPreparation => {
            f.runtime.await_sent(2);
            assert_eq!(f.runtime.deliver_body(1, b"hello"), Ok(()));
            ok()
        }
        SlotPath::ReplayRedirected => moved(),
        SlotPath::ServiceClosedBeforeAcquire | SlotPath::ServiceClosedAfterAcquire => failed(),
        _ => return,
    };
    f.runtime.await_sent(2);
    f.runtime.finish(1, result);
    f.runtime.shutdown(1);
}
fn expect_slot_released(f: &Fixture, path: SlotPath, admitted: Option<usize>) {
    let expected = path.redirects().then(|| usize::from(path.holds_slot()));
    assert_eq!(admitted, expected, "{path:?}");
    assert_eq!(f.service.active_outputs(), 0, "{path:?}");
    let state = lock(&f.scheduler.state);
    assert_eq!(state.in_flight, 0);
    assert_eq!(state.destroyed, 1, "{path:?}");
    assert_eq!(state.stats.succeeded, u64::from(path.commits()), "{path:?}");
    drop(state);
    assert_eq!(f.destination_path().exists(), path.commits(), "{path:?}");
    assert_eq!(
        f.stray_files(),
        usize::from(path == SlotPath::PreparationFailed),
        "{path:?}"
    );
}

fn request_counters(f: &Fixture) -> (u64, u64) {
    let stats = f.stats();
    (stats.custom_writer_requests, stats.recv_file_requests)
}

#[test]
fn a_listed_crt_download_commits_a_file_of_another_size_than_listed() {
    for body in [&b"{}"[..], b"hello!"] {
        let f = Fixture::one_object(WriterMode::Crt);
        f.submit("file", 5);
        let sent = f.runtime.sent(0);
        assert!(!sent.body_consumer);
        assert!(!sent.check_object_size);
        f.runtime.write_recv_file(0, body).expect("recv file");
        f.runtime.finish(0, ok());
        f.runtime.shutdown(0);
        f.drain();

        assert_eq!(f.destination(), body);
        assert_eq!(f.stray_files(), 0);
        let stats = f.stats();
        assert_eq!((stats.failed, stats.succeeded), (0, 1));
        assert_eq!(request_counters(&f), (0, 1));
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test follows the download through its replay"
)]
fn a_listed_native_download_of_another_size_replays_as_a_crt_download() {
    let f = Fixture::one_object(WriterMode::Pwrite);
    f.submit("file", 5);
    let first = f.runtime.sent(0);
    assert!(first.body_consumer);
    assert!(first.check_object_size);
    f.runtime.finish(0, size_changed());
    f.runtime.shutdown(0);
    f.runtime.await_sent(2);
    let replay = f.runtime.sent(1);
    assert!(!replay.body_consumer);
    assert!(!replay.check_object_size);
    assert_eq!(f.service.active_outputs(), 0);
    f.runtime.write_recv_file(1, b"hello!").expect("recv file");
    f.runtime.finish(1, ok());
    f.runtime.shutdown(1);
    f.drain();

    assert_eq!(f.destination(), b"hello!");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.runtime.recoveries.load(Ordering::Acquire), 0);
    let stats = f.stats();
    assert_eq!((stats.failed, stats.succeeded), (0, 1));
    assert_eq!(request_counters(&f), (1, 1));
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
}

#[test]
fn a_size_fallback_still_follows_a_region_redirect() {
    let f = Fixture::one_object(WriterMode::Pwrite);
    f.submit("file", 5);
    f.runtime.finish(0, size_changed());
    f.runtime.shutdown(0);
    f.runtime.await_sent(2);
    assert!(!f.runtime.sent(1).body_consumer);
    f.runtime.finish(1, moved());
    f.runtime.shutdown(1);
    f.runtime.await_sent(3);
    assert!(!f.runtime.sent(2).body_consumer);
    f.runtime.write_recv_file(2, b"hello!").expect("recv file");
    f.runtime.finish(2, ok());
    f.runtime.shutdown(2);
    f.drain();

    assert_eq!(f.destination(), b"hello!");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.runtime.recoveries.load(Ordering::Acquire), 1);
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
    let stats = f.stats();
    assert_eq!((stats.failed, stats.succeeded), (0, 1));
    assert_eq!(request_counters(&f), (1, 2));
    assert_eq!(f.runtime.released(), 3);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test follows the transfer through all three sends"
)]
fn a_redirect_replay_can_still_take_the_size_fallback() {
    let f = Fixture::one_object(WriterMode::Pwrite);
    f.submit("file", 5);
    f.runtime.finish(0, moved());
    f.runtime.shutdown(0);
    f.runtime.await_sent(2);
    let redirected = f.runtime.sent(1);
    assert!(redirected.body_consumer);
    assert!(redirected.check_object_size);
    f.runtime.finish(1, size_changed());
    f.runtime.shutdown(1);
    f.runtime.await_sent(3);
    assert!(!f.runtime.sent(2).body_consumer);
    assert_eq!(f.service.active_outputs(), 0);
    f.runtime.finish(2, moved());
    f.runtime.shutdown(2);
    f.drain();

    assert_eq!(f.destination(), b"old");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.runtime.count(), 3);
    assert_eq!(f.runtime.recoveries.load(Ordering::Acquire), 1);
    let stats = f.stats();
    assert_eq!((stats.failed, stats.succeeded), (1, 0));
    assert_eq!(request_counters(&f), (2, 1));
}

#[test]
fn a_one_object_download_keeps_checking_the_head_size_after_its_body() {
    let f = Fixture::one_object(WriterMode::Pwrite);
    f.scheduler
        .submit_entry(Entry {
            key: b"file".to_vec(),
            local_path: f.destination_path(),
            size: Some(5),
            ..Entry::default()
        })
        .expect("entry");
    assert!(!f.runtime.sent(0).check_object_size);
    assert_eq!(f.runtime.deliver_body(0, b"hell"), Ok(()));
    f.runtime.finish(0, ok());
    f.runtime.shutdown(0);
    f.drain();

    assert_eq!(f.destination(), b"old");
    assert_eq!(f.stray_files(), 0);
    assert_eq!(f.runtime.count(), 1);
    assert_eq!(f.stats().failed, 1);
    assert_eq!(
        failure_exceptions(&f.sink),
        [b"DownloadReceivedSizeMismatch".to_vec()]
    );
}

#[test]
fn a_size_change_releases_the_output_slot_its_replay_does_not_need() {
    let f = Fixture::new(one_object_service(WriterMode::Pwrite), 2, 1);
    f.submit("first", 5);
    std::thread::scope(|scope| {
        let waiting = scope.spawn(|| f.submit("second", 5));
        await_admission_waiters(&f.service, 1);
        f.runtime.finish(0, size_changed());
        f.runtime.shutdown(0);
        waiting.join().expect("waiting submitter");
    });
    f.runtime.await_sent(3);
    let index = |key: &[u8]| {
        (1..3)
            .find(|index| f.runtime.sent(*index).key == key)
            .expect("a request for the key")
    };
    let (replay, second) = (index(b"first"), index(b"second"));
    assert!(!f.runtime.sent(replay).body_consumer);
    assert!(f.runtime.sent(second).body_consumer);
    assert_eq!(f.service.active_outputs(), 1);
    f.runtime
        .write_recv_file(replay, b"hello!")
        .expect("recv file");
    assert_eq!(f.runtime.deliver_body(second, b"hello"), Ok(()));
    for index in [replay, second] {
        f.runtime.finish(index, ok());
        f.runtime.shutdown(index);
    }
    f.drain();

    let read = |name: &str| fs::read(f.directory.0.join(name)).expect("destination");
    assert_eq!(
        (read("first"), read("second")),
        (b"hello!".to_vec(), b"hello".to_vec())
    );
    assert_eq!(f.service.active_outputs(), 0);
    let stats = f.stats();
    assert_eq!((stats.failed, stats.succeeded), (0, 2));
    assert_eq!(request_counters(&f), (2, 1));
}
