//! The channel is created on first install and never closed, because a handler
//! dispatched just before a watcher was torn down can still be holding the
//! descriptor, and a closed descriptor number would be reused by the next
//! `open` in the process.
use super::{WAKE_READ, WAKE_WRITE};
use std::{
    io,
    sync::{Mutex, atomic::Ordering},
};
static CREATION: Mutex<()> = Mutex::new(());
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub(super) enum Reason {
    Interrupt = b'c',
    Stop = b's',
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub(super) struct Wake {
    pub(super) interrupt: bool,
    pub(super) stop: bool,
}
/// The most a wake pipe can hold. Linux allocates 16 pages per pipe and the
/// pipe is never resized; 64 KiB is the largest page size the build
/// supports, and macOS caps a pipe at 64 KiB outright.
const CAPACITY_BYTES_MAX: usize = 16 * 64 * 1024;
const DRAIN_READ_BYTES: usize = 4096;
const WAIT_READ_BYTES: usize = 16;
const _: () = assert!(CAPACITY_BYTES_MAX.is_multiple_of(DRAIN_READ_BYTES));
pub(super) fn ensure() -> io::Result<()> {
    let _lock = CREATION
        .lock()
        .map_err(|_| io::Error::other("wake-pipe creation lock poisoned"))?;
    if WAKE_READ.load(Ordering::Acquire) >= 0 {
        return Ok(());
    }
    let mut fds = [-1; 2];
    // SAFETY: fds contains writable storage for both returned file descriptors.
    if unsafe { libc::pipe(fds.as_mut_ptr()) } != 0 {
        return Err(io::Error::last_os_error());
    }
    let configure = || -> io::Result<()> {
        flags(fds[0], libc::F_GETFD, libc::F_SETFD, libc::FD_CLOEXEC)?;
        flags(fds[1], libc::F_GETFD, libc::F_SETFD, libc::FD_CLOEXEC)?;
        flags(fds[1], libc::F_GETFL, libc::F_SETFL, libc::O_NONBLOCK)
    };
    if let Err(error) = configure() {
        // SAFETY: both descriptors remain exclusively owned until publication.
        unsafe {
            libc::close(fds[0]);
            libc::close(fds[1]);
        }
        return Err(error);
    }
    WAKE_READ.store(fds[0], Ordering::Release);
    WAKE_WRITE.store(fds[1], Ordering::Release);
    Ok(())
}
fn flags(fd: libc::c_int, get: libc::c_int, set: libc::c_int, bit: libc::c_int) -> io::Result<()> {
    // SAFETY: commands are nonblocking descriptor flag operations on a valid descriptor.
    let current = unsafe { libc::fcntl(fd, get, 0) };
    if current < 0 {
        return Err(io::Error::last_os_error());
    }
    // SAFETY: current is a valid flag word returned above, with one supported flag added.
    if unsafe { libc::fcntl(fd, set, current | bit) } < 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}
pub(super) fn post(reason: Reason) {
    let fd = WAKE_WRITE.load(Ordering::Acquire);
    if fd < 0 {
        return;
    }
    let byte = reason as u8;
    // SAFETY: fd is nonblocking and retained forever; byte is a valid one-byte buffer.
    unsafe {
        libc::write(fd, std::ptr::from_ref(&byte).cast(), 1);
    }
}
pub(super) fn wait() -> Option<Wake> {
    let mut buffer = [0_u8; WAIT_READ_BYTES];
    // SAFETY: the read descriptor lives for the process and buffer is writable for its length.
    let count = unsafe {
        libc::read(
            WAKE_READ.load(Ordering::Acquire),
            buffer.as_mut_ptr().cast(),
            buffer.len(),
        )
    };
    if count < 0 {
        let interrupted = io::Error::last_os_error().raw_os_error() == Some(libc::EINTR);
        return interrupted.then_some(Wake::default());
    }
    let bytes = buffer.get(..usize::try_from(count).ok()?)?;
    if bytes.is_empty() {
        return None;
    }
    Some(Wake {
        interrupt: bytes.contains(&(Reason::Interrupt as u8)),
        stop: bytes.contains(&(Reason::Stop as u8)),
    })
}
pub(super) fn drain_stale() {
    let read_fd = WAKE_READ.load(Ordering::Acquire);
    let mut pending = [0_u8; DRAIN_READ_BYTES];
    for _ in 0..CAPACITY_BYTES_MAX / DRAIN_READ_BYTES + 1 {
        let mut poll_fd = libc::pollfd {
            fd: read_fd,
            events: libc::POLLIN,
            revents: 0,
        };
        // SAFETY: the poll descriptor is valid writable storage and timeout zero cannot block.
        if unsafe { libc::poll(&mut poll_fd, 1, 0) } <= 0 {
            return;
        }
        // SAFETY: the process-lifetime pipe was readable and pending covers the read length.
        if unsafe { libc::read(read_fd, pending.as_mut_ptr().cast(), pending.len()) } <= 0 {
            return;
        }
    }
    debug_assert!(false, "wake pipe still readable after the drain bound");
}
