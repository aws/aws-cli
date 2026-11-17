use super::*;
use crate::tests::{TestResult, Time};
use std::collections::VecDeque;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc;
use std::time::UNIX_EPOCH;

/// The clock's reading, in seconds since the epoch, when a test begins.
const START: u64 = 2_000_000_000;
const MINUTE: u64 = 60;
const HOUR: u64 = 60 * MINUTE;

/// Credentials that expire `lifetime` seconds after `START`.
fn expiring(access_key: &str, lifetime: u64) -> Credentials {
    Credentials::new("test", access_key, "secret")
        .with_expiry(Some(UNIX_EPOCH + Duration::from_secs(START + lifetime)))
}

fn failed() -> LoadError {
    LoadError::CredentialRetrieval {
        provider: "test",
        error_msg: "the source is down".into(),
    }
}

/// A provider's refresh operation: it hands out a script of results in
/// order, fails once the script runs out, and counts its calls.
#[derive(Clone, Default)]
struct Script {
    results: Arc<Mutex<VecDeque<Result<Credentials, LoadError>>>>,
    calls: Arc<AtomicUsize>,
}

impl Script {
    fn of(results: impl IntoIterator<Item = Result<Credentials, LoadError>>) -> Self {
        Self {
            results: Arc::new(Mutex::new(results.into_iter().collect())),
            calls: Arc::default(),
        }
    }
    fn calls(&self) -> usize {
        self.calls.load(Ordering::SeqCst)
    }
    fn next(&self) -> Result<Credentials, LoadError> {
        self.calls.fetch_add(1, Ordering::SeqCst);
        lock(&self.results).pop_front().unwrap_or(Err(failed()))
    }
    /// Credentials `initial` that refresh from this script.
    fn refreshable(&self, initial: Credentials, time: &Time) -> Refreshable {
        let script = self.clone();
        Refreshable::new(initial, move || script.next()).with_clock(time.clock())
    }
}

fn access_key(credentials: Option<Credentials>) -> Option<String> {
    credentials.map(|credentials| credentials.access_key_id().to_owned())
}

#[test]
fn credentials_outside_the_advisory_window_are_not_refreshed() -> TestResult {
    let time = Time::new(START);
    let script = Script::default();
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDA");
    // Exactly fifteen minutes left is not yet inside the window.
    time.advance(HOUR - 15 * MINUTE);
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDA");
    assert_eq!(script.calls(), 0);
    Ok(())
}

/// What a caller that must not block reads: the credentials while each
/// window is still ahead, without a call to the provider.
#[test]
fn the_windows_are_read_without_refreshing() {
    let time = Time::new(START + HOUR - 15 * MINUTE);
    let script = Script::default();
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    let read = |credentials: &Refreshable| {
        (
            access_key(credentials.outside_advisory()),
            access_key(credentials.outside_mandatory()),
        )
    };
    let current = Some("AKIDA".to_owned());
    // Exactly the window left is not yet inside it.
    assert_eq!(read(&credentials), (current.clone(), current.clone()));
    time.advance(1);
    assert_eq!(read(&credentials), (None, current.clone()));
    time.advance(5 * MINUTE - 1);
    assert_eq!(read(&credentials), (None, current));
    time.advance(1);
    assert_eq!(read(&credentials), (None, None));
    assert_eq!(script.calls(), 0);
}

#[test]
fn credentials_without_an_expiry_are_never_refreshed() -> TestResult {
    let time = Time::new(START);
    let script = Script::default();
    let credentials = script.refreshable(Credentials::new("test", "AKIDA", "secret"), &time);
    time.advance(1000 * HOUR);
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDA");
    assert_eq!(script.calls(), 0);
    Ok(())
}

#[test]
fn the_advisory_window_refreshes_through_the_provider() -> TestResult {
    let time = Time::new(START);
    let refreshed = expiring("AKIDB", 2 * HOUR).with_session_token(Some("token-b".into()));
    let script = Script::of([Ok(refreshed.clone())]);
    let initial = expiring("AKIDA", HOUR)
        .with_session_token(Some("token-a".into()))
        .with_account_id(Some("111111111111".into()));
    let credentials = script.refreshable(initial, &time);
    time.advance(HOUR - 15 * MINUTE + 1);
    // Every field is replaced: the account the refresh left out is gone.
    assert_eq!(credentials.frozen()?, refreshed);
    assert_eq!(credentials.frozen()?, refreshed);
    assert_eq!(script.calls(), 1);
    Ok(())
}

#[test]
fn a_failed_advisory_refresh_keeps_the_current_credentials() -> TestResult {
    // Exactly ten minutes left is advisory, not yet mandatory.
    let time = Time::new(START + HOUR - 10 * MINUTE);
    let script = Script::of([
        Err(failed()),
        Err(failed()),
        Ok(expiring("AKIDB", 2 * HOUR)),
    ]);
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDA");
    assert_eq!(script.calls(), 1);
    // Nothing backs off: the next caller tries the provider again.
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDA");
    assert_eq!(script.calls(), 2);
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDB");
    assert_eq!(script.calls(), 3);
    Ok(())
}

#[test]
fn a_failed_mandatory_refresh_is_an_error() -> TestResult {
    let time = Time::new(START + HOUR - 10 * MINUTE + 1);
    let script = Script::of([Err(failed()), Ok(expiring("AKIDB", 2 * HOUR))]);
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    // The current credentials have minutes left; botocore still refuses to
    // go on with them.
    let error = credentials.frozen();
    assert_eq!(error, Err(RefreshError::Provider(failed())));
    assert_eq!(
        error.map_err(|error| error.to_string()),
        Err("Error when retrieving credentials from test: the source is down".into())
    );
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDB");
    assert_eq!(script.calls(), 2);
    Ok(())
}

#[test]
fn refreshed_credentials_that_are_still_expired_are_an_error() -> TestResult {
    // The advisory window: botocore raises this in either one.
    let time = Time::new(START + HOUR - 14 * MINUTE);
    let script = Script::of([
        Ok(expiring("AKIDSTALE", MINUTE)),
        Ok(expiring("AKIDB", 2 * HOUR)),
    ]);
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    let error = credentials.frozen();
    assert_eq!(error, Err(RefreshError::StillExpired));
    assert_eq!(
        error.map_err(|error| error.to_string()),
        Err("Credentials were refreshed, but the refreshed credentials are still expired.".into())
    );
    // The expired set replaced the old one, so the next caller refreshes.
    assert_eq!(credentials.outside_mandatory(), None);
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDB");
    assert_eq!(script.calls(), 2);
    Ok(())
}

#[test]
fn refreshed_credentials_that_expire_this_instant_are_not_yet_expired() -> TestResult {
    let time = Time::new(START + HOUR - MINUTE);
    let script = Script::of([Ok(expiring("AKIDNOW", HOUR - MINUTE))]);
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDNOW");
    Ok(())
}

#[test]
fn a_refresh_without_a_usable_expiry_is_an_error_in_the_advisory_window_too() -> TestResult {
    let time = Time::new(START + HOUR - 14 * MINUTE);
    let unreadable = LoadError::Expiry {
        provider: "test",
        value: "soon".into(),
    };
    let not_text = LoadError::Metadata {
        provider: "test",
        key: "SecretAccessKey",
    };
    let script = Script::of([
        Ok(Credentials::new("test", "AKIDFOREVER", "secret")),
        Err(unreadable.clone()),
        Err(not_text.clone()),
    ]);
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    let missing = credentials.frozen();
    assert_eq!(
        missing,
        Err(RefreshError::MissingExpiry { provider: "test" })
    );
    assert_eq!(
        missing.map_err(|error| error.to_string()),
        Err("Error when retrieving credentials from test: \
             Credential refresh failed, response did not contain: expiry_time"
            .into())
    );
    assert_eq!(
        credentials.frozen(),
        Err(RefreshError::Metadata(unreadable))
    );
    assert_eq!(credentials.frozen(), Err(RefreshError::Metadata(not_text)));
    // No refresh replaced anything, so a provider failure still falls
    // back on the first credentials.
    assert_eq!(credentials.frozen()?.access_key_id(), "AKIDA");
    assert_eq!(script.calls(), 4);
    Ok(())
}

#[test]
fn deferred_credentials_refresh_on_first_use_and_that_refresh_is_mandatory() -> TestResult {
    let time = Time::new(START);
    let script = Script::of([Err(failed()), Ok(expiring("AKIDB", HOUR))]);
    let deferred = {
        let script = script.clone();
        Refreshable::deferred("test", move || script.next()).with_clock(time.clock())
    };
    assert_eq!(deferred.method(), "test");
    assert_eq!(deferred.outside_advisory(), None);
    assert_eq!(deferred.outside_mandatory(), None);
    assert_eq!(deferred.frozen(), Err(RefreshError::Provider(failed())));
    assert_eq!(deferred.frozen()?.access_key_id(), "AKIDB");
    assert_eq!(deferred.frozen()?.access_key_id(), "AKIDB");
    assert_eq!(script.calls(), 2);
    Ok(())
}

/// How long a gated refresh waits to be released before it gives up, so a
/// failed assertion cannot leave a thread waiting for ever.
const GATE_TIMEOUT: Duration = Duration::from_secs(10);

/// Long enough for a thread that has announced itself to reach the refresh
/// lock. A thread that has not reached it sees the same outcome.
const SETTLE: Duration = Duration::from_millis(50);

/// The test's side of a refresh that holds the lock until it is released.
struct Gate {
    /// Receives once per refresh, as the refresh starts.
    entered: mpsc::Receiver<()>,
    /// Lets one refresh finish per message.
    release: mpsc::Sender<()>,
}

/// Credentials whose every refresh reports that it has started, waits for
/// its release, then takes the script's next result.
fn gated(initial: Credentials, script: &Script, time: &Time) -> (Refreshable, Gate) {
    let (entered, gate_entered) = mpsc::channel();
    let (gate_release, release) = mpsc::channel::<()>();
    let release = Mutex::new(release);
    let script = script.clone();
    let refreshable = Refreshable::new(initial, move || {
        // A test that has stopped listening fails on its own assertions.
        let _ = entered.send(());
        let _ = lock(&release).recv_timeout(GATE_TIMEOUT);
        script.next()
    });
    let gate = Gate {
        entered: gate_entered,
        release: gate_release,
    };
    (refreshable.with_clock(time.clock()), gate)
}

type Outcome = Result<Credentials, RefreshError>;

fn joined(thread: std::thread::ScopedJoinHandle<'_, Outcome>) -> Result<Outcome, &'static str> {
    thread.join().map_err(|_| "a caller panicked")
}

#[test]
fn a_caller_in_the_advisory_window_does_not_wait_for_another_callers_refresh() -> TestResult {
    let time = Time::new(START + HOUR - 14 * MINUTE);
    let script = Script::of([Ok(expiring("AKIDB", 2 * HOUR))]);
    let (credentials, gate) = gated(expiring("AKIDA", HOUR), &script, &time);
    let credentials = &credentials;
    std::thread::scope(|scope| -> TestResult {
        let refresher = scope.spawn(|| credentials.frozen());
        gate.entered.recv()?;
        // The refresh is under way and holds the lock.
        assert_eq!(credentials.frozen()?.access_key_id(), "AKIDA");
        gate.release.send(())?;
        assert_eq!(joined(refresher)??.access_key_id(), "AKIDB");
        Ok(())
    })?;
    assert_eq!(script.calls(), 1);
    Ok(())
}

#[test]
fn callers_in_the_mandatory_window_wait_for_one_refresh() -> TestResult {
    let time = Time::new(START + HOUR - 5 * MINUTE);
    let script = Script::of([Ok(expiring("AKIDB", 2 * HOUR))]);
    let (credentials, gate) = gated(expiring("AKIDA", HOUR), &script, &time);
    let credentials = &credentials;
    std::thread::scope(|scope| -> TestResult {
        let refresher = scope.spawn(|| credentials.frozen());
        gate.entered.recv()?;
        // A caller that must not block is told so rather than handed the
        // credentials that are about to expire.
        assert_eq!(credentials.outside_mandatory(), None);
        let (started, starts) = mpsc::channel();
        let waiters: Vec<_> = (0..4)
            .map(|_| {
                let started = started.clone();
                scope.spawn(move || {
                    let _ = started.send(());
                    credentials.frozen()
                })
            })
            .collect();
        for _ in &waiters {
            starts.recv()?;
        }
        std::thread::sleep(SETTLE);
        gate.release.send(())?;
        for caller in waiters.into_iter().chain([refresher]) {
            assert_eq!(joined(caller)??.access_key_id(), "AKIDB");
        }
        Ok(())
    })?;
    assert_eq!(script.calls(), 1);
    Ok(())
}

#[test]
fn a_waiter_refreshes_again_when_the_refresh_it_waited_for_failed() -> TestResult {
    let time = Time::new(START + HOUR - 5 * MINUTE);
    let script = Script::of([Err(failed()), Ok(expiring("AKIDB", 2 * HOUR))]);
    let (credentials, gate) = gated(expiring("AKIDA", HOUR), &script, &time);
    let credentials = &credentials;
    std::thread::scope(|scope| -> TestResult {
        let refresher = scope.spawn(|| credentials.frozen());
        gate.entered.recv()?;
        let (started, starts) = mpsc::channel();
        let waiter = scope.spawn(move || {
            let _ = started.send(());
            credentials.frozen()
        });
        starts.recv()?;
        std::thread::sleep(SETTLE);
        // One release for the refresh under way, one for the waiter's own.
        gate.release.send(())?;
        gate.release.send(())?;
        assert_eq!(joined(refresher)?, Err(RefreshError::Provider(failed())));
        assert_eq!(joined(waiter)??.access_key_id(), "AKIDB");
        Ok(())
    })?;
    assert_eq!(script.calls(), 2);
    Ok(())
}

/// A caller that waited behind a refresh checks the mandatory window
/// alone: it never starts an advisory refresh of its own.
#[test]
fn a_caller_that_waited_refreshes_only_inside_the_mandatory_window() -> TestResult {
    let time = Time::new(START + HOUR - 12 * MINUTE);
    let script = Script::of([Err(failed()), Ok(expiring("AKIDB", 2 * HOUR))]);
    let credentials = script.refreshable(expiring("AKIDA", HOUR), &time);
    // Twelve minutes left: advisory, where `frozen` would refresh.
    assert_eq!(credentials.frozen_after_waiting()?.access_key_id(), "AKIDA");
    assert_eq!(script.calls(), 0);
    // Nine minutes left: the refresh is mandatory, so a failure is raised.
    time.advance(3 * MINUTE);
    assert_eq!(
        credentials.frozen_after_waiting(),
        Err(RefreshError::Provider(failed()))
    );
    assert_eq!(credentials.frozen_after_waiting()?.access_key_id(), "AKIDB");
    assert_eq!(script.calls(), 2);
    Ok(())
}

#[test]
fn debug_output_never_shows_the_secret() {
    let credentials = Refreshable::new(expiring("AKIDA", HOUR), || Err(failed()));
    let debug = format!("{credentials:?}");
    assert!(debug.contains("AKIDA") && debug.contains("test"));
    assert!(!debug.contains("secret"));
}
