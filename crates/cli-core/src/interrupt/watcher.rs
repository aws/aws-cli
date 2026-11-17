use super::{EXIT_STATUS, Signal, State};
use std::{
    io,
    sync::{
        Arc, Mutex, MutexGuard,
        atomic::{AtomicBool, AtomicI32, AtomicPtr, Ordering},
    },
    thread::JoinHandle,
};
mod pipe;
use pipe::Reason;

static WATCHED_STATE: AtomicPtr<State> = AtomicPtr::new(std::ptr::null_mut());
static WATCHER_LOCK: Mutex<()> = Mutex::new(());
static WAKE_READ: AtomicI32 = AtomicI32::new(-1);
static WAKE_WRITE: AtomicI32 = AtomicI32::new(-1);
static PROCESS_STATE: State = State::new();
/// Why `install` left SIGINT alone.
#[derive(Debug)]
#[non_exhaustive]
pub enum InstallError {
    /// The parent asked this process to ignore Ctrl-C.
    InterruptIgnored,
    /// Another watcher is installed, or a thread panicked while holding the
    /// installation lock.
    AlreadyInstalled,
    /// The self-pipe could not be created or configured.
    WakePipeUnavailable(io::Error),
    /// The watcher thread could not be started.
    Spawn(io::Error),
    /// Querying or replacing the SIGINT disposition failed.
    Sigaction(io::Error),
}
impl std::fmt::Display for InstallError {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InterruptIgnored => out.write_str("SIGINT is inherited as ignored"),
            Self::AlreadyInstalled => out.write_str("an interrupt watcher is already installed"),
            Self::WakePipeUnavailable(error) => write!(out, "wake pipe unavailable: {error}"),
            Self::Spawn(error) => write!(out, "interrupt watcher thread unavailable: {error}"),
            Self::Sigaction(error) => write!(out, "SIGINT disposition unavailable: {error}"),
        }
    }
}
impl std::error::Error for InstallError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::WakePipeUnavailable(error) | Self::Spawn(error) | Self::Sigaction(error) => {
                Some(error)
            }
            Self::InterruptIgnored | Self::AlreadyInstalled => None,
        }
    }
}
/// Owns the active watcher and restores the previous disposition on drop.
///
/// Only one watcher may be active. The state and pipe publication remain valid
/// after drop so a handler dispatched during teardown cannot use freed storage.
pub struct Watcher {
    previous: libc::sigaction,
    thread: Option<JoinHandle<()>>,
    stopping: Arc<AtomicBool>,
    _ownership: MutexGuard<'static, ()>,
}
impl std::fmt::Debug for Watcher {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.debug_struct("Watcher")
            .field("running", &self.thread.is_some())
            .finish_non_exhaustive()
    }
}
impl Watcher {
    /// Installs the handler without changing the caller's signal mask.
    ///
    /// # Errors
    /// Reports ignored SIGINT, an existing watcher, or pipe/thread/signal failures.
    pub fn install(state: &'static State) -> Result<Self, InstallError> {
        let ownership = WATCHER_LOCK
            .try_lock()
            .map_err(|_| InstallError::AlreadyInstalled)?;
        let previous = current_action().map_err(InstallError::Sigaction)?;
        if previous.sa_sigaction == libc::SIG_IGN {
            return Err(InstallError::InterruptIgnored);
        }
        pipe::ensure().map_err(InstallError::WakePipeUnavailable)?;
        pipe::drain_stale();
        let stopping = Arc::new(AtomicBool::new(false));
        let thread_stopping = Arc::clone(&stopping);
        let thread = crate::thread::builder()
            .name("aws-sigint".into())
            .spawn(move || run(state, &thread_stopping))
            .map_err(InstallError::Spawn)?;
        WATCHED_STATE.store(std::ptr::from_ref(state).cast_mut(), Ordering::Release);
        if let Err(error) = set_handler() {
            stop_thread(&stopping, thread);
            return Err(InstallError::Sigaction(error));
        }
        Ok(Self {
            previous,
            thread: Some(thread),
            stopping,
            _ownership: ownership,
        })
    }
    fn stop(&mut self) {
        if let Some(thread) = self.thread.take() {
            stop_thread(&self.stopping, thread);
        }
    }
}
fn stop_thread(stopping: &AtomicBool, thread: JoinHandle<()>) {
    stopping.store(true, Ordering::Release);
    pipe::post(Reason::Stop);
    let _ = thread.join();
}
fn set_handler() -> io::Result<()> {
    #[cfg(all(test, not(miri)))]
    if tests::FAIL_HANDLER.load(Ordering::Acquire) {
        return Err(io::Error::from_raw_os_error(libc::EINVAL));
    }
    // SAFETY: all-zero sigaction is valid storage; sigemptyset initializes its mask.
    let mut action: libc::sigaction = unsafe { std::mem::zeroed() };
    action.sa_sigaction = on_interrupt as *const () as usize;
    action.sa_flags = libc::SA_RESTART;
    // SAFETY: action and its mask are valid local writable storage.
    let result = unsafe {
        libc::sigemptyset(&mut action.sa_mask);
        libc::sigaction(libc::SIGINT, &action, std::ptr::null_mut())
    };
    if result != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}
impl Drop for Watcher {
    fn drop(&mut self) {
        // SAFETY: previous was filled by sigaction, and restoration prevents new handler
        // dispatches.
        unsafe {
            libc::sigaction(libc::SIGINT, &self.previous, std::ptr::null_mut());
        }
        self.stop();
    }
}
/// Installs a watcher for the executable's shared, static-lifetime interrupt state.
///
/// # Errors
/// Returns the same installation failures as [`Watcher::install`].
pub fn install_process_watcher() -> Result<Watcher, InstallError> {
    Watcher::install(&PROCESS_STATE)
}
/// The default interrupt state used by process-wide native transfers.
pub fn process_state() -> &'static State {
    &PROCESS_STATE
}
fn current_action() -> io::Result<libc::sigaction> {
    // SAFETY: all-zero initialization provides valid storage for the query output.
    let mut action = unsafe { std::mem::zeroed() };
    // SAFETY: action is a writable sigaction; a null new action requests a query.
    if unsafe { libc::sigaction(libc::SIGINT, std::ptr::null(), &mut action) } != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(action)
}
fn run(state: &State, stopping: &AtomicBool) {
    while let Some(wake) = pipe::wait() {
        if wake.interrupt {
            state.request();
        }
        if wake.stop || (wake.interrupt && stopping.load(Ordering::Acquire)) {
            return;
        }
    }
}
extern "C" fn on_interrupt(_: libc::c_int) {
    // SAFETY: errno_location returns this thread's valid errno cell.
    let saved = unsafe { *errno_location() };
    let state = WATCHED_STATE.load(Ordering::Acquire);
    if state.is_null() {
        terminate();
    } else {
        // SAFETY: publication only accepts &'static State and is deliberately never cleared.
        match unsafe { &*state }.record_interrupt() {
            Signal::Canceled => pipe::post(Reason::Interrupt),
            Signal::Terminate => terminate(),
        }
    }
    // SAFETY: this is the same thread-local errno cell saved above.
    unsafe {
        *errno_location() = saved;
    }
}
#[cfg(target_os = "linux")]
unsafe fn errno_location() -> *mut libc::c_int {
    // SAFETY: libc returns the calling thread's valid errno cell.
    unsafe { libc::__errno_location() }
}
#[cfg(target_os = "macos")]
unsafe fn errno_location() -> *mut libc::c_int {
    // SAFETY: libc returns the calling thread's valid errno cell.
    unsafe { libc::__error() }
}
fn terminate() {
    #[cfg(all(test, not(miri)))]
    if tests::FAKE_TERMINATE.load(Ordering::Acquire) {
        tests::TERMINATIONS.fetch_add(1, Ordering::AcqRel);
        return;
    }
    // SAFETY: these are async-signal-safe POSIX operations on valid local storage. Restoring
    // default and unblocking SIGINT permits re-raise; _exit is the PID-namespace fallback.
    unsafe {
        let mut action: libc::sigaction = std::mem::zeroed();
        action.sa_sigaction = libc::SIG_DFL;
        libc::sigemptyset(&mut action.sa_mask);
        libc::sigaction(libc::SIGINT, &action, std::ptr::null_mut());
        let mut set: libc::sigset_t = std::mem::zeroed();
        libc::sigemptyset(&mut set);
        libc::sigaddset(&mut set, libc::SIGINT);
        libc::pthread_sigmask(libc::SIG_UNBLOCK, &set, std::ptr::null_mut());
        libc::raise(libc::SIGINT);
        libc::_exit(libc::c_int::from(EXIT_STATUS));
    }
}
#[cfg(all(test, not(miri)))]
mod tests;
