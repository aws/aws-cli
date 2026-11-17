use crt_sys::{AwsByteCursor, native as c};
use std::ffi::{CString, c_void};
use std::ptr::NonNull;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

static DEBUG_ENABLED: AtomicBool = AtomicBool::new(false);

struct LoggerState {
    pointer: Option<NonNull<c_void>>,
    users: usize,
    failed: bool,
}
// SAFETY: the state is accessed only under LOGGER_SLOT; the CRT logger itself
// supports worker-thread logging and cleanup after all owners release it.
unsafe impl Send for LoggerState {}
static LOGGER_SLOT: Mutex<LoggerState> = Mutex::new(LoggerState {
    pointer: None,
    users: 0,
    failed: false,
});
#[cfg(test)]
pub(super) static FAIL_INSTALLATION: AtomicBool = AtomicBool::new(false);
/// Shared process logger retained until all command runtimes have shut down.
///
/// Records are gated on the process-wide flag, not on the instance: a
/// disabled logger leaves the flag alone.
#[derive(Debug)]
pub struct Logger {
    enabled: bool,
}
impl Logger {
    /// Enables diagnostics, then installs or retains the one active
    /// CRT logger. A failed installation is recorded once and records still
    /// reach stderr without it.
    pub fn new(enabled: bool) -> Arc<Self> {
        if !enabled {
            return Arc::new(Self { enabled: false });
        }
        let mut slot = super::super::signal::lock(&LOGGER_SLOT);
        DEBUG_ENABLED.store(true, Ordering::Release);
        if slot.users == 0 && !slot.failed {
            slot.pointer = install();
            if slot.pointer.is_none() {
                slot.failed = true;
                emit("awscli.native", b"Unable to initialize CRT debug logger");
            }
        }
        slot.users += 1;
        Arc::new(Self { enabled: true })
    }
    pub fn record(&self, logger: &str, message: &str) {
        self.record_bytes(logger, message.as_bytes());
    }
    /// Records a message whose bytes need not be Unicode, such as a path.
    pub fn record_bytes(&self, logger: &str, message: &[u8]) {
        if DEBUG_ENABLED.load(Ordering::Acquire) {
            emit(logger, message);
        }
    }
    pub fn arguments(&self, argv: &[impl AsRef<std::ffi::OsStr>]) {
        if !DEBUG_ENABLED.load(Ordering::Acquire) {
            return;
        }
        let mut bytes = Vec::new();
        if super::write_arguments(&mut bytes, argv).is_ok() {
            emit("awscli.clidriver", &bytes);
        }
    }
}
impl Drop for Logger {
    fn drop(&mut self) {
        if !self.enabled {
            return;
        }
        let mut slot = super::super::signal::lock(&LOGGER_SLOT);
        slot.users -= 1;
        if slot.users != 0 {
            return;
        }
        DEBUG_ENABLED.store(false, Ordering::Release);
        if let Some(pointer) = slot.pointer.take() {
            // SAFETY: no Arc runtime owners remain; no worker can still use this logger.
            unsafe {
                c::zaws_logger_destroy(pointer.as_ptr());
            }
        }
    }
}
fn install() -> Option<NonNull<c_void>> {
    #[cfg(test)]
    if FAIL_INSTALLATION.load(Ordering::Acquire) {
        return None;
    }
    // SAFETY: the caller holds LOGGER_SLOT, which serializes process-global
    // logger installation.
    NonNull::new(unsafe { c::zaws_logger_new() })
}
fn emit(logger: &str, message: &[u8]) {
    let text = message.split(|&byte| byte == 0).next().unwrap_or_default();
    let Ok(text) = CString::new(text) else {
        return;
    };
    // SAFETY: synchronous stdio copies both input strings during this call.
    unsafe {
        c::zaws_debug_emit(AwsByteCursor::from_bytes(logger.as_bytes()), text.as_ptr());
    }
}
