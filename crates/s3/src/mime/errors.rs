use super::GuessError;
use std::{io, path::Path};

pub(super) fn errno(error: &io::Error) -> i32 {
    #[cfg(windows)]
    return windows_errno(error.kind());
    #[cfg(not(windows))]
    error.raw_os_error().unwrap_or(libc::EIO)
}

#[cfg(any(windows, test))]
fn windows_errno(kind: io::ErrorKind) -> i32 {
    match kind {
        io::ErrorKind::NotFound => libc::ENOENT,
        io::ErrorKind::PermissionDenied => libc::EACCES,
        io::ErrorKind::NotADirectory => libc::ENOTDIR,
        io::ErrorKind::IsADirectory => libc::EISDIR,
        io::ErrorKind::OutOfMemory => libc::ENOMEM,
        io::ErrorKind::FileTooLarge => libc::EFBIG,
        _ => libc::EIO,
    }
}

pub(super) fn from_errno(number: i32, source: Option<&Path>) -> GuessError {
    let message = message(number);
    super::error_text(number, &message, source)
}

#[cfg(not(windows))]
fn message(number: i32) -> String {
    let text = io::Error::from_raw_os_error(number).to_string();
    text.split(" (os error ").next().unwrap_or(&text).to_owned()
}

#[cfg(windows)]
fn message(number: i32) -> String {
    unsafe extern "C" {
        fn strerror_s(buffer: *mut std::ffi::c_char, count: usize, number: i32) -> i32;
    }
    let mut buffer = [0_u8; 256];
    // SAFETY: strerror_s writes at most count bytes to this private buffer and
    // retains no pointer. The errno value is unrestricted; unknown codes are valid.
    let status = unsafe { strerror_s(buffer.as_mut_ptr().cast(), buffer.len(), number) };
    if status != 0 {
        return "Unknown error".into();
    }
    let length = buffer
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(buffer.len());
    String::from_utf8_lossy(&buffer[..length]).into_owned()
}

#[cfg(test)]
mod tests;
