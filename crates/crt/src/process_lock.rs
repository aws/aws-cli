//! The AWS CLI's CRT process lock, which upstream takes before it runs the
//! CRT transfer client, so one AWS CLI process on a host runs it at a time.
//!
//! The lock is aws-c-common's cross-process lock, an `flock` on a file on
//! POSIX and a named mutex on Windows; neither needs the CRT library
//! initialized. No child process inherits it, or a `credential_process`
//! helper's own children could hold it after this process exits. On POSIX
//! aws-c-common opens the lock file without close-on-exec
//! (posix/cross_process_lock.c) and the CRT starts the helper through
//! `popen`, so the descriptor is marked here; the AWS CLI's helpers inherit
//! nothing, because Python's `subprocess` closes every other descriptor. On
//! Windows there is nothing to do: aws-c-common creates the named mutex
//! without security attributes (windows/cross_process_lock.c), so no child
//! inherits its handle.
use crate::signal::lock;
use crt_sys as ffi;
use std::ptr::NonNull;
use std::sync::Mutex;

const PROCESS_LOCK_NAME: &str = "aws-cli";

static PROCESS_LOCK: ProcessLock = ProcessLock::new();

/// Takes the AWS CLI's CRT process lock, as upstream does before it runs the
/// CRT client (`acquire_crt_s3_process_lock`), and reports whether this
/// process holds it. False means another process holds it, or this process
/// could not take it, which upstream reads the same way.
/// The lock stays held until [`release`] or the process exits, so an AWS CLI
/// that starts meanwhile resolves `auto` to its classic client.
pub fn acquire() -> bool {
    PROCESS_LOCK.acquire(PROCESS_LOCK_NAME)
}

/// Gives the lock back (`release_crt_s3_process_lock`).
/// A process that hands its command to the embedded AWS CLI releases it
/// first: the AWS CLI takes the lock itself, and a second acquisition fails
/// within one process as it does across two.
pub fn release() {
    PROCESS_LOCK.release();
}

#[derive(Debug)]
struct ProcessLock {
    held: Mutex<Option<Held>>,
}
impl ProcessLock {
    const fn new() -> Self {
        Self {
            held: Mutex::new(None),
        }
    }
    fn acquire(&self, name: &str) -> bool {
        let mut held = lock(&self.held);
        if held.is_some() {
            return true;
        }
        let Some(taken) = Held::try_acquire(name) else {
            return false;
        };
        if !make_non_inheritable(taken.0) {
            return false;
        }
        *held = Some(taken);
        true
    }
    fn release(&self) {
        *lock(&self.held) = None;
    }
}

#[derive(Debug)]
struct Held(NonNull<ffi::AwsCrossProcessLock>);
// SAFETY: the lock is an open file or a named mutex's handle, which any
// thread may release, and its owner is the only holder of the pointer.
unsafe impl Send for Held {}
impl Held {
    fn try_acquire(name: &str) -> Option<Self> {
        // SAFETY: the allocator is process-lifetime, and aws-c-common reads
        // the cursor's bytes only during the call.
        let raw = unsafe {
            ffi::aws_cross_process_lock_try_acquire(
                ffi::rust_crt_allocator(),
                ffi::AwsByteCursor::from_bytes(name.as_bytes()),
            )
        };
        NonNull::new(raw).map(Self)
    }
}
impl Drop for Held {
    fn drop(&mut self) {
        // SAFETY: this owner releases its live lock once, and no copy of the
        // pointer outlives it.
        unsafe { ffi::aws_cross_process_lock_release(self.0.as_ptr()) };
    }
}

/// Layout-compatible mirror of aws-c-common's POSIX `struct
/// aws_cross_process_lock`. The header declares the struct opaque and no
/// function returns its descriptor; a test checks the mirror against the
/// lock file.
#[cfg(unix)]
#[repr(C)]
struct LockLayout {
    _allocator: *mut ffi::AwsAllocator,
    locked_fd: libc::c_int,
}

#[cfg(unix)]
fn descriptor(lock: NonNull<ffi::AwsCrossProcessLock>) -> libc::c_int {
    // SAFETY: on POSIX the lock is the `struct aws_cross_process_lock`
    // [`LockLayout`] mirrors, live until its release, and nothing writes it
    // after the acquisition.
    unsafe { (*lock.cast::<LockLayout>().as_ptr()).locked_fd }
}

#[cfg(unix)]
fn make_non_inheritable(lock: NonNull<ffi::AwsCrossProcessLock>) -> bool {
    let fd = descriptor(lock);
    // SAFETY: F_GETFD only reads the flags of the lock's open descriptor.
    let flags = unsafe { libc::fcntl(fd, libc::F_GETFD) };
    // SAFETY: F_SETFD changes only that descriptor's flags, adding one to the
    // flag word read above.
    flags != -1 && unsafe { libc::fcntl(fd, libc::F_SETFD, flags | libc::FD_CLOEXEC) } != -1
}

/// Leaves the handle as the CRT created it, already non-inheritable.
#[cfg(windows)]
fn make_non_inheritable(_: NonNull<ffi::AwsCrossProcessLock>) -> bool {
    true
}

#[cfg(test)]
mod tests;
