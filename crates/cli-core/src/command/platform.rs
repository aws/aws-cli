#[cfg(unix)]
use std::os::fd::{AsRawFd, BorrowedFd};
/// Returns terminal columns when the host supports TIOCGWINSZ and the value is nonzero.
#[cfg(unix)]
pub fn terminal_columns(fd: BorrowedFd<'_>) -> Option<usize> {
    let mut size = std::mem::MaybeUninit::<libc::winsize>::uninit();
    // SAFETY: the descriptor is borrowed for this call and ioctl initializes a winsize on success.
    let status = unsafe { libc::ioctl(fd.as_raw_fd(), libc::TIOCGWINSZ, size.as_mut_ptr()) };
    if status != 0 {
        return None;
    }
    // SAFETY: the successful TIOCGWINSZ call initialized the complete structure.
    let columns = unsafe { size.assume_init() }.ws_col;
    (columns != 0).then_some(usize::from(columns))
}

/// The target CLI measures terminal descriptors on POSIX only; Windows uses COLUMNS or 80.
#[cfg(windows)]
pub fn terminal_columns() -> Option<usize> {
    None
}
