use super::*;
use crate::{InterruptHook, interrupt::Scope};
use std::{
    process::{Command, Stdio},
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicUsize},
        mpsc,
    },
    time::{Duration, Instant},
};

pub(super) static FAKE_TERMINATE: AtomicBool = AtomicBool::new(false);
pub(super) static TERMINATIONS: AtomicUsize = AtomicUsize::new(0);
static STATE: State = State::new();
const CHILD_MARKER: &str = "AWSCLI_WINDOWS_INTERRUPT_TEST_CHILD";
const WAIT_TIMEOUT: u32 = 0x102;
const CTRL_BREAK_EVENT: u32 = 1;
const CTRL_CLOSE_EVENT: u32 = 2;
const CTRL_LOGOFF_EVENT: u32 = 5;
const CTRL_SHUTDOWN_EVENT: u32 = 6;
const ERROR_INVALID_PARAMETER: i32 = 87;

fn isolated(name: &str, body: impl FnOnce() -> io::Result<()>) -> io::Result<()> {
    if std::env::var(CHILD_MARKER).as_deref() == Ok(name) {
        FAKE_TERMINATE.store(true, Ordering::Release);
        return body();
    }
    let mut child = Command::new(std::env::current_exe()?)
        .args([
            "--exact",
            &format!("interrupt::watcher_windows::tests::{name}"),
            "--nocapture",
        ])
        .env(CHILD_MARKER, name)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    let deadline = Instant::now() + Duration::from_secs(15);
    while child.try_wait()?.is_none() {
        if Instant::now() >= deadline {
            child.kill()?;
            child.wait()?;
            return Err(io::Error::new(io::ErrorKind::TimedOut, name.to_owned()));
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    let output = child.wait_with_output()?;
    assert!(
        output.status.success(),
        "{name}: {}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    Ok(())
}

fn fresh_channel() -> io::Result<()> {
    ensure_event()?;
    let _ = consume_signal()?;
    PENDING.store(0, Ordering::Release);
    WATCHED_STATE.store(std::ptr::from_ref(&STATE).cast_mut(), Ordering::Release);
    Ok(())
}

fn consume_signal() -> io::Result<bool> {
    // SAFETY: every caller has initialized the retained process-lifetime event.
    match unsafe { WaitForSingleObject(WAKE_EVENT.load(Ordering::Acquire), 0) } {
        WAIT_OBJECT_0 => Ok(true),
        WAIT_TIMEOUT => Ok(false),
        _ => Err(io::Error::last_os_error()),
    }
}

fn dispatch(event: u32) -> i32 {
    // SAFETY: each isolated fixture has published static state and a retained
    // event before dispatch. Direct calls avoid signaling the whole console group.
    unsafe { on_console_control(event) }
}

#[derive(Debug)]
struct Counter {
    count: AtomicUsize,
    changed: mpsc::Sender<()>,
}
impl InterruptHook for Counter {
    fn cancel(&self) {
        self.count.fetch_add(1, Ordering::AcqRel);
        let _ = self.changed.send(());
    }
}

#[test]
fn handler_records_before_return_without_watcher_thread() -> io::Result<()> {
    isolated(
        "handler_records_before_return_without_watcher_thread",
        || {
            fresh_channel()?;
            let mut scope = Scope::enter(&STATE);
            assert_eq!(dispatch(CTRL_C_EVENT), 1);
            assert!(STATE.is_requested());
            assert!(scope.leave());
            assert_eq!(TERMINATIONS.load(Ordering::Acquire), 0);
            assert!(consume_signal()?);
            Ok(())
        },
    )
}

#[test]
fn ctrl_c_cancels_hook_and_second_event_terminates() -> io::Result<()> {
    isolated("ctrl_c_cancels_hook_and_second_event_terminates", || {
        let (changed, receiver) = mpsc::channel();
        let counter = Arc::new(Counter {
            count: AtomicUsize::new(0),
            changed,
        });
        let _registration = STATE.register(counter.clone());
        let watcher = Watcher::install(&STATE).map_err(io::Error::other)?;
        let mut scope = Scope::enter(&STATE);
        assert_eq!(dispatch(CTRL_C_EVENT), 1);
        receiver
            .recv_timeout(Duration::from_secs(5))
            .map_err(io::Error::other)?;
        assert!(STATE.is_requested());
        assert_eq!(TERMINATIONS.load(Ordering::Acquire), 0);
        assert_eq!(dispatch(CTRL_C_EVENT), 1);
        assert_eq!(TERMINATIONS.load(Ordering::Acquire), 1);
        assert!(scope.leave());
        drop(watcher);
        assert_eq!(counter.count.load(Ordering::Acquire), 1);
        Ok(())
    })
}

#[test]
fn ctrl_c_outside_scope_terminates_without_poisoning_later_scope() -> io::Result<()> {
    isolated(
        "ctrl_c_outside_scope_terminates_without_poisoning_later_scope",
        || {
            let _watcher = Watcher::install(&STATE).map_err(io::Error::other)?;
            assert_eq!(dispatch(CTRL_C_EVENT), 1);
            assert_eq!(TERMINATIONS.load(Ordering::Acquire), 1);
            assert!(!STATE.is_requested());
            let mut scope = Scope::enter(&STATE);
            assert_eq!(dispatch(CTRL_C_EVENT), 1);
            assert_eq!(TERMINATIONS.load(Ordering::Acquire), 1);
            assert!(scope.leave());
            Ok(())
        },
    )
}

#[test]
fn other_console_events_remain_unhandled_without_record_or_wake() -> io::Result<()> {
    isolated(
        "other_console_events_remain_unhandled_without_record_or_wake",
        || {
            fresh_channel()?;
            let mut scope = Scope::enter(&STATE);
            for event in [
                CTRL_BREAK_EVENT,
                CTRL_CLOSE_EVENT,
                CTRL_LOGOFF_EVENT,
                CTRL_SHUTDOWN_EVENT,
                u32::MAX,
            ] {
                assert_eq!(dispatch(event), 0);
                assert!(!STATE.is_requested());
                assert_eq!(TERMINATIONS.load(Ordering::Acquire), 0);
                assert!(!consume_signal()?);
                assert_eq!(PENDING.load(Ordering::Acquire), 0);
            }
            assert!(!scope.leave());
            Ok(())
        },
    )
}

#[test]
fn teardown_removes_handler_and_retains_state_publication() -> io::Result<()> {
    isolated(
        "teardown_removes_handler_and_retains_state_publication",
        || {
            let watcher = Watcher::install(&STATE).map_err(io::Error::other)?;
            assert!(watcher.thread.is_some());
            drop(watcher);
            // SAFETY: the callback is static; removal only queries this child's
            // handler list after the watcher has already unregistered it.
            let removed = unsafe { SetConsoleCtrlHandler(Some(on_console_control), 0) };
            let error = io::Error::last_os_error();
            assert_eq!(removed, 0);
            assert_eq!(error.raw_os_error(), Some(ERROR_INVALID_PARAMETER));
            assert_eq!(
                WATCHED_STATE.load(Ordering::Acquire),
                std::ptr::from_ref(&STATE).cast_mut()
            );
            Ok(())
        },
    )
}

#[test]
fn repeated_posts_leave_handler_nonblocking_and_coalesce_both_reasons() -> io::Result<()> {
    isolated(
        "repeated_posts_leave_handler_nonblocking_and_coalesce_both_reasons",
        || {
            fresh_channel()?;
            for _ in 0..10 {
                post(INTERRUPT);
            }
            let mut scope = Scope::enter(&STATE);
            assert_eq!(dispatch(CTRL_C_EVENT), 1);
            assert!(scope.leave());
            assert_eq!(TERMINATIONS.load(Ordering::Acquire), 0);
            post(STOP);
            assert!(consume_signal()?);
            let reasons = PENDING.swap(0, Ordering::AcqRel);
            assert_ne!(reasons & INTERRUPT, 0);
            assert_ne!(reasons & STOP, 0);
            assert!(!consume_signal()?);
            Ok(())
        },
    )
}
