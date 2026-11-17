/// Has every download request its parts in object order.
///
/// Body callbacks take parts as they complete (the shim's GET options ask for
/// out-of-order delivery), and aws-c-s3 otherwise spreads that mode's
/// requests across far-apart regions of the object. The CRT reads
/// `AWS_CRT_S3_FORCE_SEQUENTIAL_REQUESTS`, which has no API field, once per
/// client, so this runs before any runtime exists. A value the caller set is
/// left alone; the CRT ignores an empty one, so that counts as unset. The
/// live C environment is read, not an entrypoint snapshot, since that is what
/// the CRT reads. A failed publication is ignored: the CRT then spreads parts
/// as it would without the variable.
///
/// # Safety
/// The caller must invoke this before any thread that reads or writes the
/// process environment can run: before any CRT runtime, Python interpreter,
/// interrupt watcher, or worker thread starts.
pub unsafe fn request_sequential_parts() {
    // SAFETY: the caller guarantees no concurrent environment access.
    unsafe { platform::request() }
}

#[cfg(not(windows))]
mod platform {
    use std::ffi::{c_char, c_int};

    unsafe extern "C" {
        fn getenv(name: *const c_char) -> *const c_char;
        fn setenv(name: *const c_char, value: *const c_char, overwrite: c_int) -> c_int;
    }

    pub(super) unsafe fn request() {
        let name = c"AWS_CRT_S3_FORCE_SEQUENTIAL_REQUESTS";
        // SAFETY: the name is a NUL-terminated literal, and the caller
        // guarantees no thread mutates the environment during this call.
        let existing = unsafe { getenv(name.as_ptr()) };
        // SAFETY: a non-null getenv result is a NUL-terminated string that
        // stays valid until the environment next changes.
        if existing.is_null() || unsafe { *existing } == 0 {
            // SAFETY: both strings are NUL-terminated literals, and the
            // caller guarantees no thread reads or writes the environment.
            unsafe {
                setenv(name.as_ptr(), c"1".as_ptr(), 1);
            }
        }
    }
}

/// The Microsoft C runtime has no `setenv`, and aws-c-common reads its wide
/// environment there.
#[cfg(windows)]
mod platform {
    unsafe extern "C" {
        fn _wgetenv(name: *const u16) -> *const u16;
        fn _wputenv_s(name: *const u16, value: *const u16) -> std::ffi::c_int;
    }

    pub(super) unsafe fn request() {
        let name: Vec<u16> = "AWS_CRT_S3_FORCE_SEQUENTIAL_REQUESTS"
            .encode_utf16()
            .chain([0])
            .collect();
        // SAFETY: the name is terminated and live for the call, and the
        // caller guarantees no thread mutates the environment meanwhile.
        let existing = unsafe { _wgetenv(name.as_ptr()) };
        // SAFETY: a non-null _wgetenv result is a terminated wide string that
        // stays valid until the environment next changes.
        if existing.is_null() || unsafe { *existing } == 0 {
            let value = [u16::from(b'1'), 0];
            // SAFETY: both strings are terminated and live for this copying
            // call, and the caller guarantees no concurrent environment use.
            unsafe {
                _wputenv_s(name.as_ptr(), value.as_ptr());
            }
        }
    }
}

#[cfg(test)]
mod tests;
