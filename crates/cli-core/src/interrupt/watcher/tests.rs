#![expect(
    clippy::unwrap_used,
    reason = "test assertions require successful local setup"
)]
use super::*;
use crate::{InterruptHook, interrupt::Scope};
use std::{
    process::Command,
    sync::{Condvar, atomic::AtomicUsize},
    time::Duration,
};
pub(super) static FAKE_TERMINATE: AtomicBool = AtomicBool::new(false);
pub(super) static TERMINATIONS: AtomicUsize = AtomicUsize::new(0);
pub(super) static FAIL_HANDLER: AtomicBool = AtomicBool::new(false);
static STATE: State = State::new();
#[derive(Debug, Default)]
struct Counter {
    count: Mutex<usize>,
    changed: Condvar,
}
impl InterruptHook for Counter {
    fn cancel(&self) {
        *self.count.lock().unwrap() += 1;
        self.changed.notify_all();
    }
}
impl Counter {
    fn wait(&self) {
        let count = self.count.lock().unwrap();
        let (count, timeout) = self
            .changed
            .wait_timeout_while(count, Duration::from_secs(5), |count| *count == 0)
            .unwrap();
        assert!(!timeout.timed_out());
        assert_eq!(*count, 1);
    }
}
fn isolated(name: &str, body: impl FnOnce()) {
    if std::env::var("AWSCLI_INTERRUPT_TEST_CHILD").as_deref() == Ok(name) {
        FAKE_TERMINATE.store(true, Ordering::Release);
        body();
        return;
    }
    let output = Command::new(std::env::current_exe().unwrap())
        .args([
            "--exact",
            &format!("interrupt::watcher::tests::{name}"),
            "--nocapture",
        ])
        .env("AWSCLI_INTERRUPT_TEST_CHILD", name)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}
fn raise() {
    // SAFETY: raise delivers SIGINT to this isolated test thread with its installed handler.
    assert_eq!(unsafe { libc::raise(libc::SIGINT) }, 0);
}
#[test]
fn handler_records_before_raise_returns() {
    isolated("handler_records_before_raise_returns", || {
        let _watcher = Watcher::install(&STATE).unwrap();
        let mut scope = Scope::enter(&STATE);
        raise();
        assert!(STATE.is_requested());
        assert!(scope.leave());
        assert_eq!(TERMINATIONS.load(Ordering::Acquire), 0);
    });
}
#[test]
fn sigint_cancels_hook_and_second_terminates() {
    isolated("sigint_cancels_hook_and_second_terminates", || {
        let counter = Arc::new(Counter::default());
        let _registration = STATE.register(counter.clone());
        let watcher = Watcher::install(&STATE).unwrap();
        let mut scope = Scope::enter(&STATE);
        raise();
        counter.wait();
        assert!(STATE.is_requested());
        assert_eq!(TERMINATIONS.load(Ordering::Acquire), 0);
        raise();
        assert_eq!(TERMINATIONS.load(Ordering::Acquire), 1);
        assert!(scope.leave());
        drop(watcher);
        assert_eq!(*counter.count.lock().unwrap(), 1);
    });
}
#[test]
fn sigint_outside_scope_takes_default_action() {
    isolated("sigint_outside_scope_takes_default_action", || {
        let _watcher = Watcher::install(&STATE).unwrap();
        raise();
        assert_eq!(TERMINATIONS.load(Ordering::Acquire), 1);
        assert!(!STATE.is_requested());
        let mut scope = Scope::enter(&STATE);
        raise();
        assert_eq!(TERMINATIONS.load(Ordering::Acquire), 1);
        assert!(scope.leave());
    });
}
fn current_mask() -> libc::sigset_t {
    // SAFETY: zeroed sigset_t is valid storage; the query only fills current.
    unsafe {
        let mut current = std::mem::zeroed();
        assert_eq!(
            libc::pthread_sigmask(libc::SIG_BLOCK, std::ptr::null(), &mut current),
            0
        );
        current
    }
}
#[test]
fn installation_preserves_signal_mask() {
    isolated("installation_preserves_signal_mask", || {
        let before = current_mask();
        let _watcher = Watcher::install(&STATE).unwrap();
        let during = current_mask();
        // SAFETY: both masks were initialized by pthread_sigmask; SIGINT is a valid signal number.
        unsafe {
            assert_eq!(
                libc::sigismember(&before, libc::SIGINT),
                libc::sigismember(&during, libc::SIGINT)
            );
        }
    });
}
#[test]
fn teardown_restores_disposition_and_retains_publication() {
    isolated(
        "teardown_restores_disposition_and_retains_publication",
        || {
            let before = current_action().unwrap();
            let watcher = Watcher::install(&STATE).unwrap();
            let installed = current_action().unwrap();
            assert_eq!(installed.sa_sigaction, on_interrupt as *const () as usize);
            assert_ne!(installed.sa_flags & libc::SA_RESTART, 0);
            drop(watcher);
            assert_eq!(current_action().unwrap().sa_sigaction, before.sa_sigaction);
            assert_eq!(
                WATCHED_STATE.load(Ordering::Acquire),
                std::ptr::from_ref(&STATE).cast_mut()
            );
        },
    );
}
#[test]
fn pipe_is_close_on_exec_and_write_nonblocking() {
    isolated("pipe_is_close_on_exec_and_write_nonblocking", || {
        pipe::ensure().unwrap();
        for fd in [
            WAKE_READ.load(Ordering::Acquire),
            WAKE_WRITE.load(Ordering::Acquire),
        ] {
            // SAFETY: the descriptor is valid and F_GETFD has no pointer argument.
            assert_ne!(
                // SAFETY: fd is a valid retained descriptor and the command takes no pointer.
                unsafe { libc::fcntl(fd, libc::F_GETFD, 0) } & libc::FD_CLOEXEC,
                0
            );
        }
        // SAFETY: the write descriptor is valid and F_GETFL has no pointer argument.
        assert_ne!(
            // SAFETY: the retained descriptor is valid and the command takes no pointer.
            unsafe { libc::fcntl(WAKE_WRITE.load(Ordering::Acquire), libc::F_GETFL, 0) }
                & libc::O_NONBLOCK,
            0
        );
    });
}
fn fill_pipe() {
    let bytes = [Reason::Interrupt as u8; 4096];
    loop {
        // SAFETY: the retained descriptor is nonblocking and bytes is a valid buffer.
        if unsafe {
            libc::write(
                WAKE_WRITE.load(Ordering::Acquire),
                bytes.as_ptr().cast(),
                bytes.len(),
            )
        } >= 0
        {
            continue;
        }
        let error = io::Error::last_os_error().raw_os_error();
        if error == Some(libc::EINTR) {
            continue;
        }
        assert_eq!(error, Some(libc::EAGAIN));
        break;
    }
}
#[test]
fn full_pipe_cannot_block_handler_and_errno_is_preserved() {
    isolated(
        "full_pipe_cannot_block_handler_and_errno_is_preserved",
        || {
            pipe::ensure().unwrap();
            pipe::drain_stale();
            fill_pipe();
            WATCHED_STATE.store(std::ptr::from_ref(&STATE).cast_mut(), Ordering::Release);
            let mut scope = Scope::enter(&STATE);
            // SAFETY: errno_location returns this isolated thread's errno cell.
            unsafe {
                *errno_location() = libc::EDOM;
            }
            on_interrupt(libc::SIGINT);
            // SAFETY: errno_location returns the cell saved and restored by the handler.
            assert_eq!(unsafe { *errno_location() }, libc::EDOM);
            assert!(scope.leave());
            assert_eq!(TERMINATIONS.load(Ordering::Acquire), 0);
            pipe::drain_stale();
        },
    );
}
#[test]
fn a_stop_posted_to_a_full_wake_pipe_still_ends_the_watcher() {
    isolated(
        "a_stop_posted_to_a_full_wake_pipe_still_ends_the_watcher",
        || {
            pipe::ensure().unwrap();
            pipe::drain_stale();
            fill_pipe();
            let stopping = Arc::new(AtomicBool::new(true));
            pipe::post(Reason::Stop);
            let (ended, watcher_ended) = std::sync::mpsc::channel();
            let thread_stopping = Arc::clone(&stopping);
            let _watcher = std::thread::spawn(move || {
                run(&STATE, &thread_stopping);
                let _ = ended.send(());
            });
            assert!(watcher_ended.recv_timeout(Duration::from_secs(5)).is_ok());
            pipe::drain_stale();
        },
    );
}
#[test]
fn inherited_ignored_sigint_is_left_untouched() {
    isolated("inherited_ignored_sigint_is_left_untouched", || {
        let mut ignored = current_action().unwrap();
        ignored.sa_sigaction = libc::SIG_IGN;
        // SAFETY: ignored is initialized and this is an isolated child process.
        assert_eq!(
            // SAFETY: ignored is initialized and this child process owns its signal disposition.
            unsafe { libc::sigaction(libc::SIGINT, &ignored, std::ptr::null_mut()) },
            0
        );
        assert!(matches!(
            Watcher::install(&STATE),
            Err(InstallError::InterruptIgnored)
        ));
        assert_eq!(current_action().unwrap().sa_sigaction, libc::SIG_IGN);
        assert_eq!(WAKE_READ.load(Ordering::Acquire), -1);
    });
}
#[test]
fn default_termination_re_raises_sigint() {
    use std::os::unix::process::ExitStatusExt;
    let name = "default_termination_re_raises_sigint";
    if std::env::var("AWSCLI_INTERRUPT_TEST_CHILD").as_deref() == Ok(name) {
        let _watcher = Watcher::install(&STATE).unwrap();
        raise();
        return;
    }
    let status = Command::new(std::env::current_exe().unwrap())
        .args(["--exact", &format!("interrupt::watcher::tests::{name}")])
        .env("AWSCLI_INTERRUPT_TEST_CHILD", name)
        .stdout(std::process::Stdio::null())
        .status()
        .unwrap();
    assert!(status.signal() == Some(libc::SIGINT) || status.code() == Some(i32::from(EXIT_STATUS)));
}

#[test]
fn second_sigint_terminates_while_hook_is_blocked() {
    use std::os::unix::process::ExitStatusExt;
    const NAME: &str = "second_sigint_terminates_while_hook_is_blocked";
    if std::env::var("AWSCLI_INTERRUPT_TEST_CHILD").as_deref() == Ok(NAME) {
        #[derive(Debug)]
        struct Blocked(AtomicBool);
        impl InterruptHook for Blocked {
            fn cancel(&self) {
                self.0.store(true, Ordering::Release);
                loop {
                    std::thread::park();
                }
            }
        }
        let hook = Arc::new(Blocked(AtomicBool::new(false)));
        let _registration = STATE.register(hook.clone());
        let _watcher = Watcher::install(&STATE).unwrap();
        let _scope = Scope::enter(&STATE);
        raise();
        while !hook.0.load(Ordering::Acquire) {
            std::thread::yield_now();
        }
        raise();
        return;
    }
    let status = Command::new(std::env::current_exe().unwrap())
        .args(["--exact", &format!("interrupt::watcher::tests::{NAME}")])
        .env("AWSCLI_INTERRUPT_TEST_CHILD", NAME)
        .stdout(std::process::Stdio::null())
        .status()
        .unwrap();
    assert!(status.signal() == Some(libc::SIGINT) || status.code() == Some(i32::from(EXIT_STATUS)));
}

fn pipe_is_empty() -> bool {
    let mut poll_fd = libc::pollfd {
        fd: WAKE_READ.load(Ordering::Acquire),
        events: libc::POLLIN,
        revents: 0,
    };
    // SAFETY: poll_fd is valid writable storage and a zero timeout cannot block.
    unsafe { libc::poll(&mut poll_fd, 1, 0) == 0 }
}
#[test]
fn failed_handler_install_tears_down_once() {
    isolated("failed_handler_install_tears_down_once", || {
        let before = current_action().unwrap();
        FAIL_HANDLER.store(true, Ordering::Release);
        assert!(matches!(
            Watcher::install(&STATE),
            Err(InstallError::Sigaction(_))
        ));
        FAIL_HANDLER.store(false, Ordering::Release);
        assert!(pipe_is_empty());
        assert_eq!(current_action().unwrap().sa_sigaction, before.sa_sigaction);
        let _watcher = Watcher::install(&STATE).unwrap();
    });
}
#[test]
fn one_wait_reports_both_reasons() {
    isolated("one_wait_reports_both_reasons", || {
        pipe::ensure().unwrap();
        pipe::drain_stale();
        pipe::post(Reason::Interrupt);
        pipe::post(Reason::Stop);
        assert_eq!(
            pipe::wait(),
            Some(pipe::Wake {
                interrupt: true,
                stop: true,
            })
        );
        assert!(pipe_is_empty());
    });
}
