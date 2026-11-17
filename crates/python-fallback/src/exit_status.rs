//! Translate a raised CPython `SystemExit` using its host process status rules.

use crate::ffi;
use crate::helpers::{HostExitStatus, SystemExitValue, normalize_system_exit_code};

/// Consume the currently raised `SystemExit` and return the host process status.
///
/// # Safety
/// The caller must hold the live interpreter's GIL and have matched the pending exception
/// against `SystemExit`. The function retains no references after returning.
pub unsafe fn from_raised_system_exit() -> HostExitStatus {
    // SAFETY: the caller guarantees a live interpreter and owns its pending exception.
    unsafe {
        let exception = ffi::aws_python_take_raised_exception();
        if exception.is_null() {
            return 0;
        }
        let code = ffi::PyObject_GetAttrString(exception, c"code".as_ptr());
        if code.is_null() {
            ffi::PyErr_Clear();
            ffi::Py_DecRef(exception);
            return 1;
        }
        let status = status_for_code(code);
        ffi::Py_DecRef(code);
        ffi::Py_DecRef(exception);
        status
    }
}

unsafe fn status_for_code(code: *mut ffi::PyObject) -> HostExitStatus {
    // SAFETY: the caller owns the non-null code reference and holds the GIL.
    unsafe {
        if code == ffi::aws_python_none() {
            return normalize_system_exit_code(SystemExitValue::None);
        }
        if ffi::aws_python_is_long(code) != 0 {
            return normalize_system_exit_code(integer_code(code));
        }
        report_non_integer_code(code);
        normalize_system_exit_code(SystemExitValue::Invalid)
    }
}

unsafe fn integer_code(code: *mut ffi::PyObject) -> SystemExitValue {
    // SAFETY: the caller holds the GIL and has checked that code is a Python int.
    unsafe {
        let value = ffi::PyLong_AsLongLong(code);
        if ffi::PyErr_Occurred().is_null() {
            SystemExitValue::Integer(value)
        } else {
            // CPython exits with -1 when the Python int exceeds C long long.
            ffi::PyErr_Clear();
            SystemExitValue::Overflow
        }
    }
}

unsafe fn report_non_integer_code(code: *mut ffi::PyObject) {
    // SAFETY: code is owned by the caller; the new text reference is released here.
    unsafe {
        let text = ffi::PyObject_Str(code);
        if text.is_null() {
            ffi::PyErr_Clear();
            return;
        }
        let utf8 = ffi::PyUnicode_AsUTF8(text);
        if utf8.is_null() {
            ffi::PyErr_Clear();
        } else {
            ffi::PySys_WriteStderr(c"%s\n".as_ptr(), utf8);
        }
        ffi::Py_DecRef(text);
    }
}
