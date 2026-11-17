use std::ffi::{CStr, c_char};

unsafe extern "C" {
    fn lzma_version_string() -> *const c_char;
    fn ffi_get_version() -> *const c_char;
}

#[test]
fn linked_liblzma_and_libffi_versions_match_the_managed_graph() {
    // SAFETY: both library APIs return immutable, NUL-terminated static version strings.
    let (lzma, ffi) = unsafe {
        (
            CStr::from_ptr(lzma_version_string()),
            CStr::from_ptr(ffi_get_version()),
        )
    };
    assert_eq!(lzma, c"5.8.4");
    assert_eq!(ffi, c"3.8.0");
}
