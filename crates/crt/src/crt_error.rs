use crate::s3::UNKNOWN_ERROR_CODE;
use crt_sys as ffi;
use std::ffi::c_int;
use std::ptr::NonNull;

pub(crate) fn check(status: c_int) -> Result<(), i32> {
    check_keeping_status(status).map_err(|(_, code)| code)
}
pub(crate) fn check_keeping_status(status: c_int) -> Result<(), (c_int, i32)> {
    if status == 0 {
        Ok(())
    } else {
        Err((status, last_error_or_unknown()))
    }
}
pub(crate) fn check_pointer<T>(pointer: *mut T) -> Result<NonNull<T>, i32> {
    NonNull::new(pointer).ok_or_else(last_error_or_unknown)
}
#[cfg(test)]
pub(crate) fn last_raised() -> i32 {
    last_error_or_unknown()
}
fn last_error_or_unknown() -> i32 {
    // SAFETY: reads only calling-thread error state.
    let error = unsafe { ffi::rust_crt_last_error() };
    if error == 0 {
        UNKNOWN_ERROR_CODE
    } else {
        error
    }
}
