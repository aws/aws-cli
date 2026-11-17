use std::ffi::OsStr;

/// The errno CPython's `FileIO` raises opening the directory at `path` for
/// reading: `open(2)` admits a directory, and the check `FileIO` makes next
/// refuses it with EISDIR (Modules/_io/fileio.c).
#[cfg(unix)]
pub(super) fn open_errno(_path: &OsStr) -> i32 {
    libc::EISDIR
}

/// `FileIO`'s flags for reading on Windows.
#[cfg(windows)]
const READ_FLAGS: std::ffi::c_int = libc::O_RDONLY | libc::O_BINARY | libc::O_NOINHERIT;

// The Microsoft C runtime's open, close, errno cell, and messages, which
// CPython's `FileIO` and its OSError use on Windows.
#[cfg(windows)]
unsafe extern "C" {
    fn _wopen(path: *const u16, flags: std::ffi::c_int, ...) -> std::ffi::c_int;
    fn _close(fd: std::ffi::c_int) -> std::ffi::c_int;
    fn _errno() -> *mut std::ffi::c_int;
    #[link_name = "strerror"]
    fn crt_strerror(errnum: std::ffi::c_int) -> *mut std::ffi::c_char;
}

/// The errno CPython's `FileIO` gets opening `path` for reading on Windows,
/// from the same `_wopen` call with the same flags (Modules/_io/fileio.c).
/// Windows refuses a directory there, and the errno the C runtime reports
/// depends on the path's spelling and the host's error mapping. Every errno
/// the runtime maps an open failure to is below `_sys_nerr`, where its
/// `strerror` is the `_sys_errlist` entry CPython prints. An open that
/// succeeds is closed and reads as the EISDIR `FileIO`'s directory check
/// raises next.
#[cfg(windows)]
pub(super) fn open_errno(path: &OsStr) -> i32 {
    use std::os::windows::ffi::OsStrExt;
    let wide: Vec<u16> = path.encode_wide().chain(Some(0)).collect();
    let mode: std::ffi::c_int = 0o666;
    // SAFETY: `wide` is NUL-terminated and outlives the call, which keeps no
    // pointer to it.
    let fd = unsafe { _wopen(wide.as_ptr(), READ_FLAGS, mode) };
    if fd < 0 {
        // SAFETY: the C runtime returns the calling thread's valid errno cell.
        return unsafe { *_errno() };
    }
    // SAFETY: `fd` is the descriptor the open above returned, closed once.
    unsafe { _close(fd) };
    libc::EISDIR
}

#[cfg(unix)]
pub(super) fn strerror(errno: i32) -> Vec<u8> {
    let mut buffer = [0_u8; 1024];
    // SAFETY: `strerror_r` writes at most the length passed, one less than the
    // buffer's, into this private buffer and keeps no pointer to it, so the
    // buffer's last byte stays NUL.
    unsafe { libc::strerror_r(errno, buffer.as_mut_ptr().cast(), buffer.len() - 1) };
    let length = buffer
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(buffer.len());
    buffer[..length].to_vec()
}

#[cfg(windows)]
pub(super) fn strerror(errno: i32) -> Vec<u8> {
    // SAFETY: `strerror` returns a NUL-terminated message for any errno,
    // copied here before another call can replace it.
    unsafe { std::ffi::CStr::from_ptr(crt_strerror(errno)) }
        .to_bytes()
        .to_vec()
}

#[cfg(all(test, unix))]
mod tests;
