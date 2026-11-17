use super::*;

#[test]
#[cfg_attr(
    miri,
    ignore = "calls the C library's strerror, which Miri does not implement"
)]
fn the_message_is_the_c_librarys_strerror() {
    for errno in [
        libc::ENOENT,
        libc::EACCES,
        libc::EXDEV,
        libc::EISDIR,
        99_999,
    ] {
        // SAFETY: the message is copied before this test calls `strerror`
        // again, and no other test calls it concurrently with a different errno
        // whose message could overwrite a shared buffer before the copy.
        let expected = unsafe { std::ffi::CStr::from_ptr(libc::strerror(errno)) }
            .to_bytes()
            .to_vec();
        assert_eq!(strerror(errno), expected, "{errno}");
    }
}

#[test]
#[cfg_attr(
    miri,
    ignore = "Miri's strerror_r emulation does not produce the C library's text"
)]
fn the_message_is_the_one_std_reports() {
    for errno in [libc::ENOENT, libc::EACCES, libc::EXDEV, 99_999] {
        let text = std::io::Error::from_raw_os_error(errno).to_string();
        let expected = text.split(" (os error ").next().unwrap_or(&text);
        assert_eq!(strerror(errno), expected.as_bytes(), "{errno}");
    }
}
