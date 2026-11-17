use super::*;
use crt::redirect::Outcome;

fn redirect_fixture() -> Fixture {
    redirect_fixture_into(None)
}
fn redirect_fixture_into(sink: Option<Arc<dyn Sink>>) -> Fixture {
    let mut f = Fixture::new(true, false);
    let scheduler = Arc::get_mut(&mut f.scheduler).expect("exclusive fixture");
    scheduler.request.runtime.single_request_threshold = Some(20);
    scheduler.request.sizing.single_request_bytes_max = 20;
    if let Some(sink) = sink {
        scheduler.sink = sink;
    }
    f.scheduler.start_finish_pool(2).expect("finish pool");
    f.control.delay_shutdown.store(true, Ordering::Release);
    f
}
fn submit_redirected(f: &Fixture) {
    f.scheduler
        .handle_download_entry("prefix/redirect.txt", 20, None)
        .expect("entry");
    f.finish(0, moved());
}
fn moved() -> TransferResult {
    TransferResult {
        error_code: 91,
        response_status: 301,
        ..TransferResult::default()
    }
}
fn expect_redirect_waiting(f: &Fixture) {
    await_condition("the redirect's retirement", || {
        f.control.retirement_entered.load(Ordering::Acquire)
    });
    assert_eq!(f.control.recoveries.load(Ordering::Acquire), 0);
    assert_eq!(f.count(), 1);
    let state = lock(&f.scheduler.state);
    assert_eq!(state.destroyed, 0);
    assert_eq!(state.in_flight, 1);
    assert_eq!(state.single_request_bytes, 20);
}
fn expect_released(f: &Fixture) {
    let state = lock(&f.scheduler.state);
    assert_eq!(state.destroyed, 1);
    assert_eq!(state.in_flight, 0);
    assert_eq!(state.single_request_bytes, 0);
}
fn await_attempts(f: &Fixture, count: usize) {
    await_condition("the replay", || lock(&f.control.callbacks).len() == count);
}
fn same_attempt(f: &Fixture, first: usize, second: usize) -> bool {
    let callbacks = lock(&f.control.callbacks);
    std::ptr::addr_eq(callbacks[first].as_ptr(), callbacks[second].as_ptr())
}

#[test]
fn a_redirect_replay_finishes_on_a_second_worker_before_adoption() {
    let f = redirect_fixture();
    *lock(&f.control.recovery) = Outcome::Ready;
    f.control
        .replay_finishes_before_adoption
        .store(true, Ordering::Release);
    submit_redirected(&f);
    expect_redirect_waiting(&f);
    f.control.delay_shutdown.store(false, Ordering::Release);
    f.shutdown();
    f.scheduler.drain();
    f.scheduler.close_write_pool();

    assert_eq!(f.count(), 2);
    assert!(!same_attempt(&f, 0, 1));
    assert_eq!(f.control.recoveries.load(Ordering::Acquire), 1);
    expect_one_success(&f);
    assert_eq!(f.control.finalized.load(Ordering::Relaxed), 1);
    assert_eq!(f.control.discards.load(Ordering::Relaxed), 1);
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 2);
    assert_eq!(f.stats().writes_completed, 2);
    expect_released(&f);
}
fn expect_one_success(f: &Fixture) {
    let stats = f.stats();
    assert_eq!((stats.submitted, stats.succeeded, stats.failed), (1, 1, 0));
    assert_eq!(lock(&f.scheduler.state).canceled, 0);
    let events = lock(&f.output.events);
    assert_eq!(events.len(), 1);
    assert_eq!(events[0].stream, Stream::Stdout);
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Veto {
    Unavailable,
    DiscoveryCanceled,
    InterruptBeforeDiscovery,
    InterruptAfterDiscovery,
    LocalError,
    ReplaySubmitFailure,
    ReplayRedirect,
}
impl Veto {
    const ALL: [Self; 7] = [
        Self::Unavailable,
        Self::DiscoveryCanceled,
        Self::InterruptBeforeDiscovery,
        Self::InterruptAfterDiscovery,
        Self::LocalError,
        Self::ReplaySubmitFailure,
        Self::ReplayRedirect,
    ];
    fn canceled(self) -> bool {
        matches!(
            self,
            Self::DiscoveryCanceled
                | Self::InterruptBeforeDiscovery
                | Self::InterruptAfterDiscovery
        )
    }
    fn replayed(self) -> bool {
        matches!(self, Self::ReplaySubmitFailure | Self::ReplayRedirect)
    }
    fn discovered(self) -> bool {
        !matches!(self, Self::InterruptBeforeDiscovery | Self::LocalError)
    }
    fn arm(self, f: &Fixture) {
        *lock(&f.control.recovery) = match self {
            Self::Unavailable => Outcome::Unavailable,
            Self::DiscoveryCanceled => Outcome::Canceled,
            _ => Outcome::Ready,
        };
        match self {
            Self::InterruptAfterDiscovery => {
                *lock(&f.control.interrupt_on_recovery) = Some(Arc::downgrade(&f.scheduler));
            }
            Self::LocalError => *lock(&f.control.retire_error) = Some("NoSpaceLeft".into()),
            Self::ReplaySubmitFailure => *lock(&f.control.refused_submission) = Some(1),
            _ => {}
        }
    }
}

fn run_veto(veto: Veto) -> Fixture {
    let f = redirect_fixture();
    veto.arm(&f);
    submit_redirected(&f);
    expect_redirect_waiting(&f);
    if veto == Veto::InterruptBeforeDiscovery {
        f.scheduler.cancel();
    }
    f.shutdown();
    if veto == Veto::ReplayRedirect {
        await_attempts(&f, 2);
        f.finish(1, moved());
        f.shutdown();
    }
    f.scheduler.drain();
    f.scheduler.close_write_pool();
    f
}

#[test]
fn redirect_failures_and_cancellation_veto_replay_without_losing_ownership() {
    for veto in Veto::ALL {
        let f = run_veto(veto);
        assert_eq!(f.count(), if veto.replayed() { 2 } else { 1 }, "{veto:?}");
        assert_eq!(
            f.control.recoveries.load(Ordering::Acquire),
            usize::from(veto.discovered()),
            "{veto:?}"
        );
        expect_vetoed_result(&f, veto);
        assert_eq!(f.control.finalized.load(Ordering::Relaxed), 0, "{veto:?}");
        assert_eq!(
            f.control.releases.load(Ordering::Relaxed),
            if veto == Veto::ReplayRedirect { 2 } else { 1 },
            "{veto:?}"
        );
        expect_released(&f);
    }
}
fn expect_vetoed_result(f: &Fixture, veto: Veto) {
    let canceled = veto.canceled();
    let stats = f.stats();
    assert_eq!((stats.submitted, stats.succeeded), (1, 0), "{veto:?}");
    assert_eq!(stats.failed, u64::from(!canceled), "{veto:?}");
    assert_eq!(
        lock(&f.scheduler.state).canceled,
        u64::from(canceled),
        "{veto:?}"
    );
    let failures: Vec<_> = lock(&f.output.events)
        .iter()
        .filter(|event| event.text.starts_with(b"download failed:"))
        .map(|event| event.text.clone())
        .collect();
    assert_eq!(failures.len(), usize::from(!canceled), "{veto:?}");
    if veto == Veto::LocalError {
        assert!(failures[0].ends_with(b"NoSpaceLeft\n"));
    }
}

#[test]
fn a_producers_exception_vetoes_a_pending_redirect_replay() {
    for after_discovery in [false, true] {
        let f = run_exception_veto(after_discovery);
        assert!(!f.scheduler.interrupted(), "{after_discovery}");
        assert_eq!(f.count(), 1, "{after_discovery}");
        assert_eq!(
            f.control.recoveries.load(Ordering::Acquire),
            usize::from(after_discovery),
            "{after_discovery}"
        );
        expect_canceled_unsent(&f);
    }
}
fn run_exception_veto(after_discovery: bool) -> Fixture {
    let f = redirect_fixture();
    *lock(&f.control.recovery) = Outcome::Ready;
    f.control
        .replay_finishes_before_adoption
        .store(true, Ordering::Release);
    if after_discovery {
        *lock(&f.control.raise_on_recovery) = Some(Arc::downgrade(&f.scheduler));
    }
    submit_redirected(&f);
    expect_redirect_waiting(&f);
    if !after_discovery {
        f.scheduler.cancel_for_exception(
            b"repeated token".to_vec(),
            &cli_core::interrupt::State::new(),
        );
    }
    f.shutdown();
    f.scheduler.drain();
    f.scheduler.close_write_pool();
    f
}
fn expect_canceled_unsent(f: &Fixture) {
    let stats = f.stats();
    assert_eq!((stats.submitted, stats.succeeded, stats.failed), (1, 0, 0));
    assert_eq!(lock(&f.scheduler.state).canceled, 1);
    assert!(
        !lock(&f.output.events)
            .iter()
            .any(|event| event.text.starts_with(b"download"))
    );
    assert_eq!(f.control.finalized.load(Ordering::Relaxed), 0);
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 1);
    expect_released(f);
}

#[test]
fn a_redirected_upload_replays_once_on_a_finish_worker() {
    let f = Fixture::new(false, true);
    *lock(&f.control.recovery) = Outcome::Ready;
    f.scheduler
        .handle_upload_entry(Path::new("file"), None)
        .expect("entry");
    f.finish(0, moved());
    await_attempts(&f, 2);
    assert!(!same_attempt(&f, 0, 1));
    f.finish(1, TransferResult::default());
    f.scheduler.drain();
    f.scheduler.close_write_pool();
    assert_eq!(f.control.recoveries.load(Ordering::Acquire), 1);
    let stats = f.stats();
    assert_eq!((stats.submitted, stats.succeeded, stats.failed), (1, 1, 0));
    assert_eq!(stats.writes_completed, 1);
    assert_eq!(f.control.releases.load(Ordering::Relaxed), 2);
    assert_eq!(lock(&f.scheduler.state).destroyed, 1);
}

#[test]
fn an_unsafe_redirect_is_reported_without_discovery() {
    for result in [
        TransferResult {
            bytes_transferred: 1,
            ..moved()
        },
        TransferResult {
            body_delivered: true,
            ..moved()
        },
        TransferResult {
            response_status: 403,
            ..moved()
        },
    ] {
        let f = Fixture::new(false, true);
        *lock(&f.control.recovery) = Outcome::Ready;
        f.scheduler
            .handle_upload_entry(Path::new("file"), None)
            .expect("entry");
        f.finish(0, result);
        assert_eq!(f.stats().failed, 1);
        f.scheduler.drain();
        f.scheduler.close_write_pool();
        assert_eq!(f.control.recoveries.load(Ordering::Acquire), 0);
        assert_eq!(f.count(), 1);
        assert_eq!(f.stats().writes_completed, 0);
    }
}

#[derive(Debug, Default)]
struct Failures(Mutex<Vec<Option<u64>>>);
impl Sink for Failures {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
    fn publish(&self, event: crate::results::Event, _: bool) -> Result<(), String> {
        if let crate::results::Event::Failure { transferred, .. } = event {
            lock(&self.0).push(transferred);
        }
        Ok(())
    }
}
fn progress(f: &Fixture, index: usize, bytes: u64) {
    lock(&f.control.callbacks)[index]
        .upgrade()
        .expect("pending callback")
        .progress(bytes);
}

#[test]
fn a_failed_replay_reports_the_bytes_of_both_attempts() {
    let failures = Arc::new(Failures::default());
    let f = redirect_fixture_into(Some(failures.clone()));
    *lock(&f.control.recovery) = Outcome::Ready;
    f.scheduler
        .handle_download_entry("prefix/redirect.txt", 20, None)
        .expect("entry");
    progress(&f, 0, 7);
    f.finish(0, moved());
    expect_redirect_waiting(&f);
    f.shutdown();
    await_attempts(&f, 2);
    progress(&f, 1, 5);
    f.finish(
        1,
        TransferResult {
            error_code: 1,
            response_status: 500,
            ..TransferResult::default()
        },
    );
    f.shutdown();
    f.scheduler.drain();
    f.scheduler.close_write_pool();
    assert_eq!(f.stats().failed, 1);
    assert_eq!(*lock(&failures.0), [Some(12)]);
    expect_released(&f);
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum MessageEnd {
    Reported,
    Quiet,
    Canceled,
    Replayed,
}
fn owned_service_error(status: i32, code: &[u8]) -> TransferResult {
    let mut result = TransferResult {
        error_code: 91,
        response_status: status,
        ..TransferResult::default()
    };
    result.service_error.code.set(code);
    result.service_error.message = owned_message();
    result
}
fn owned_message() -> Vec<u8> {
    let mut message = vec![b'a'; 1023];
    message.extend_from_slice("\u{e9}".as_bytes());
    message
}
fn message_fixture(quiet: bool) -> Fixture {
    let mut f = Fixture::configured(true, false, quiet, false, 4);
    let scheduler = Arc::get_mut(&mut f.scheduler).expect("exclusive fixture");
    scheduler.request.runtime.single_request_threshold = Some(20);
    scheduler.request.sizing.single_request_bytes_max = 20;
    f.scheduler.start_finish_pool(2).expect("finish pool");
    f.control.delay_shutdown.store(true, Ordering::Release);
    f
}
fn run_message_end(end: MessageEnd) -> Fixture {
    let f = message_fixture(end == MessageEnd::Quiet);
    *lock(&f.control.recovery) = match end {
        MessageEnd::Reported | MessageEnd::Quiet => Outcome::Unavailable,
        MessageEnd::Canceled => Outcome::Canceled,
        MessageEnd::Replayed => Outcome::Ready,
    };
    f.scheduler
        .handle_download_entry("prefix/redirect.txt", 20, None)
        .expect("entry");
    f.finish(0, owned_service_error(301, b"PermanentRedirect"));
    expect_redirect_waiting(&f);
    f.shutdown();
    if end == MessageEnd::Replayed {
        await_attempts(&f, 2);
        f.finish(1, owned_service_error(403, b"AccessDenied"));
        await_condition("the replay's release", || {
            f.control.releases.load(Ordering::Acquire) == 2
        });
        f.shutdown();
    }
    f.scheduler.drain();
    f.scheduler.close_write_pool();
    f
}

#[test]
fn an_attempt_owns_its_service_error_message_however_it_ends() {
    use MessageEnd::{Canceled, Quiet, Replayed, Reported};
    for end in [Reported, Quiet, Canceled, Replayed] {
        let f = run_message_end(end);
        assert_eq!(f.count(), if end == Replayed { 2 } else { 1 }, "{end:?}");
        let stats = f.stats();
        assert_eq!(stats.failed, u64::from(end != Canceled), "{end:?}");
        assert_eq!(
            lock(&f.scheduler.state).canceled,
            u64::from(end == Canceled),
            "{end:?}"
        );
        expect_failure_line(&f, end);
        expect_released(&f);
    }
}

fn expect_failure_line(f: &Fixture, end: MessageEnd) {
    let failures: Vec<_> = lock(&f.output.events)
        .iter()
        .filter(|event| event.text.starts_with(b"download failed:"))
        .map(|event| event.text.clone())
        .collect();
    let reported = matches!(end, MessageEnd::Reported | MessageEnd::Replayed);
    assert_eq!(failures.len(), usize::from(reported), "{end:?}");
    if !reported {
        return;
    }
    let line = String::from_utf8(failures[0].clone()).expect("UTF-8 line");
    let code = if end == MessageEnd::Replayed {
        "AccessDenied"
    } else {
        "PermanentRedirect"
    };
    assert!(line.contains(&format!("({code})")), "{end:?}: {line}");
    let message = String::from_utf8(owned_message()).expect("UTF-8 message");
    assert!(line.ends_with(&format!("{message}\n")), "{end:?}: {line}");
}
