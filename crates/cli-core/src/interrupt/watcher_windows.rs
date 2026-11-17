use super::{EXIT_STATUS, Signal, State};
use std::{
    ffi::c_void,
    io,
    sync::{
        Mutex, MutexGuard,
        atomic::{AtomicPtr, AtomicU8, Ordering},
    },
    thread::JoinHandle,
};

static WATCHED_STATE: AtomicPtr<State> = AtomicPtr::new(std::ptr::null_mut());
static WATCHER_LOCK: Mutex<()> = Mutex::new(());
static WAKE_EVENT: AtomicPtr<c_void> = AtomicPtr::new(std::ptr::null_mut());
static PENDING: AtomicU8 = AtomicU8::new(0);
static PROCESS_STATE: State = State::new();
const INTERRUPT: u8 = 1;
const STOP: u8 = 2;

#[derive(Debug)]
#[non_exhaustive]
pub enum InstallError {
    InterruptIgnored,
    AlreadyInstalled,
    Io(io::Error),
}
impl std::fmt::Display for InstallError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InterruptIgnored => formatter.write_str("Ctrl-C is inherited as ignored"),
            Self::AlreadyInstalled => {
                formatter.write_str("an interrupt watcher is already installed")
            }
            Self::Io(error) => write!(formatter, "interrupt watcher unavailable: {error}"),
        }
    }
}
impl std::error::Error for InstallError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        if let Self::Io(error) = self {
            Some(error)
        } else {
            None
        }
    }
}
impl From<io::Error> for InstallError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

/// Owns console registration while state and wake storage retain process lifetime.
#[derive(Debug)]
pub struct Watcher {
    thread: Option<JoinHandle<()>>,
    _ownership: MutexGuard<'static, ()>,
}
impl Watcher {
    pub fn install(state: &'static State) -> Result<Self, InstallError> {
        let ownership = WATCHER_LOCK
            .try_lock()
            .map_err(|_| InstallError::AlreadyInstalled)?;
        ensure_event()?;
        // SAFETY: the handle is a valid process-lifetime event.
        // A zero timeout consumes a stale signal.
        unsafe {
            WaitForSingleObject(WAKE_EVENT.load(Ordering::Acquire), 0);
        }
        PENDING.store(0, Ordering::Release);
        let thread = std::thread::Builder::new()
            .name("aws-ctrl-c".into())
            .spawn(move || run(state))?;
        let mut watcher = Self {
            thread: Some(thread),
            _ownership: ownership,
        };
        WATCHED_STATE.store(std::ptr::from_ref(state).cast_mut(), Ordering::Release);
        // SAFETY: the handler has the documented ABI and process lifetime.
        if unsafe { SetConsoleCtrlHandler(Some(on_console_control), 1) } == 0 {
            let error = io::Error::last_os_error();
            watcher.stop();
            return Err(error.into());
        }
        Ok(watcher)
    }
    fn stop(&mut self) {
        post(STOP);
        if let Some(thread) = self.thread.take() {
            let _ = thread.join();
        }
    }
}
impl Drop for Watcher {
    fn drop(&mut self) {
        // SAFETY: removes only our process-lifetime callback from the handler list.
        unsafe {
            SetConsoleCtrlHandler(Some(on_console_control), 0);
        }
        self.stop();
    }
}
pub fn install_process_watcher() -> Result<Watcher, InstallError> {
    Watcher::install(&PROCESS_STATE)
}
pub fn process_state() -> &'static State {
    &PROCESS_STATE
}
fn ensure_event() -> io::Result<()> {
    if !WAKE_EVENT.load(Ordering::Acquire).is_null() {
        return Ok(());
    }
    // SAFETY: null security attributes make the unnamed, auto-reset event non-inheritable.
    let event = unsafe { CreateEventW(std::ptr::null(), 0, 0, std::ptr::null()) };
    if event.is_null() {
        return Err(io::Error::last_os_error());
    }
    // Retained deliberately: a console dispatch can still hold this handle during teardown.
    WAKE_EVENT.store(event, Ordering::Release);
    Ok(())
}
fn post(reason: u8) {
    PENDING.fetch_or(reason, Ordering::AcqRel);
    // SAFETY: installed handlers only run after publication of the process-lifetime event.
    unsafe {
        SetEvent(WAKE_EVENT.load(Ordering::Acquire));
    }
}
fn run(state: &State) {
    loop {
        // SAFETY: the retained event cannot be closed while this waiter uses it.
        if unsafe { WaitForSingleObject(WAKE_EVENT.load(Ordering::Acquire), INFINITE) }
            != WAIT_OBJECT_0
        {
            return;
        }
        let reasons = PENDING.swap(0, Ordering::AcqRel);
        if reasons & INTERRUPT != 0 {
            state.request();
        }
        if reasons & STOP != 0 {
            return;
        }
    }
}
unsafe extern "system" fn on_console_control(event: u32) -> i32 {
    if event != CTRL_C_EVENT {
        return 0;
    }
    let state = WATCHED_STATE.load(Ordering::Acquire);
    let signal = if state.is_null() {
        Signal::Terminate
    } else {
        // SAFETY: publication accepts only static State references and is never cleared.
        unsafe { &*state }.record_interrupt()
    };
    match signal {
        Signal::Canceled => post(INTERRUPT),
        Signal::Terminate => terminate(),
    }
    1
}
fn terminate() {
    #[cfg(test)]
    if tests::FAKE_TERMINATE.load(Ordering::Acquire) {
        tests::TERMINATIONS.fetch_add(1, Ordering::AcqRel);
        return;
    }
    // SAFETY: the pseudo-handle denotes this process.
    // Immediate termination runs no loader or stdio cleanup.
    unsafe {
        NtTerminateProcess(GetCurrentProcess(), i32::from(EXIT_STATUS));
    }
}
#[link(name = "kernel32")]
unsafe extern "system" {
    fn CreateEventW(
        attributes: *const c_void,
        manual_reset: i32,
        initial: i32,
        name: *const u16,
    ) -> *mut c_void;
    fn SetEvent(event: *mut c_void) -> i32;
    fn WaitForSingleObject(object: *mut c_void, timeout_ms: u32) -> u32;
    fn SetConsoleCtrlHandler(
        handler: Option<unsafe extern "system" fn(u32) -> i32>,
        add: i32,
    ) -> i32;
    fn GetCurrentProcess() -> *mut c_void;
}
#[link(name = "ntdll")]
unsafe extern "system" {
    fn NtTerminateProcess(process: *mut c_void, exit_status: i32) -> i32;
}
const CTRL_C_EVENT: u32 = 0;
const WAIT_OBJECT_0: u32 = 0;
const INFINITE: u32 = u32::MAX;

#[cfg(test)]
mod tests;
