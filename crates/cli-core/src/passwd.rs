use std::ffi::{CStr, OsStr};
use std::os::unix::ffi::OsStrExt;
use std::path::PathBuf;

/// The first and largest buffers `getpwuid_r` receives, doubling between
/// them: the range aws-c-common's `aws_get_home_directory` tries, so any
/// entry the CRT can read is one this reads too.
const BUFFER_BYTES_MIN: usize = 1024;
const BUFFER_BYTES_MAX: usize = 16384;

pub(crate) fn home_directory() -> Option<PathBuf> {
    home_directory_from(BUFFER_BYTES_MIN)
}

fn home_directory_from(mut buffer_bytes: usize) -> Option<PathBuf> {
    while buffer_bytes <= BUFFER_BYTES_MAX {
        let mut buffer = vec![0 as libc::c_char; buffer_bytes];
        // SAFETY: `passwd` is a C struct of integers and pointers, for which
        // all-zero bytes are a valid value; `getpwuid_r` overwrites it.
        let mut entry: libc::passwd = unsafe { std::mem::zeroed() };
        let mut found: *mut libc::passwd = std::ptr::null_mut();
        // SAFETY: every pointer is valid for the call, and `buffer.len()` is
        // the length of the buffer the entry's strings are written into.
        let status = unsafe {
            libc::getpwuid_r(
                libc::getuid(),
                &raw mut entry,
                buffer.as_mut_ptr(),
                buffer.len(),
                &raw mut found,
            )
        };
        if status == libc::ERANGE {
            buffer_bytes *= 2;
            continue;
        }
        if status != 0 || found.is_null() || entry.pw_dir.is_null() {
            return None;
        }
        // SAFETY: on success `pw_dir` points at a NUL-terminated string in
        // `buffer`, which outlives this borrow.
        let home = unsafe { CStr::from_ptr(entry.pw_dir) }.to_bytes();
        return (!home.is_empty()).then(|| PathBuf::from(OsStr::from_bytes(home)));
    }
    None
}

#[cfg(test)]
mod tests;
