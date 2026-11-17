//! CPython-independent exit truncation, bytecode compatibility, standard
//! stream codec and locale name policy.
use std::ffi::CStr;
#[cfg(not(windows))]
use std::ffi::{c_char, c_int};

/// Exit-status bits visible to the parent process on this host.
#[cfg(windows)]
pub type HostExitStatus = u32;
/// Exit-status bits visible to the parent process on this host.
#[cfg(not(windows))]
pub type HostExitStatus = u8;

/// Classification of the value stored in `SystemExit.code`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SystemExitValue {
    None,
    Integer(i64),
    Overflow,
    Invalid,
}

/// Preserve the host's visible bits after CPython narrows through a C integer.
pub fn normalize_system_exit_code(value: SystemExitValue) -> HostExitStatus {
    exit_bits(value) as HostExitStatus
}

fn exit_bits(value: SystemExitValue) -> u32 {
    match value {
        SystemExitValue::None => 0,
        SystemExitValue::Integer(code) => code as u32,
        SystemExitValue::Overflow => u32::MAX,
        SystemExitValue::Invalid => 1,
    }
}

/// A dynamically loaded interpreter must accept the embedded bytecode format.
pub fn bytecode_magic_is_compatible(
    dynamic: bool,
    payload_magic: i64,
    interpreter_magic: i64,
) -> bool {
    !dynamic || payload_magic == interpreter_magic
}

/// Convert a Rust buffer length to CPython's signed `Py_ssize_t` without truncation.
pub fn checked_python_size(length: usize) -> Option<isize> {
    isize::try_from(length).ok()
}

/// Encoding the fallback pins for the embedded interpreter's standard streams
/// through `PyConfig.stdio_encoding`.
pub const STDIO_ENCODING: &CStr = c"utf-8";

/// Error handler the fallback pins alongside [`STDIO_ENCODING`], through
/// `PyConfig.stdio_errors`.
pub const STDIO_ERRORS: &CStr = c"surrogateescape";

/// Whether the embedded interpreter can decode a C library locale name.
pub fn locale_name_is_decodable(name: &[u8]) -> bool {
    std::str::from_utf8(name).is_ok()
}

/// C entry point for [`locale_name_is_decodable`], which `shim/python.c`
/// calls before it preinitializes the interpreter.
///
/// # Safety
/// `name` must point to a NUL-terminated string that stays live for the call.
#[cfg(not(windows))]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn aws_python_locale_name_is_decodable(name: *const c_char) -> c_int {
    // SAFETY: the caller passes a live NUL-terminated string.
    let name = unsafe { CStr::from_ptr(name) };
    c_int::from(locale_name_is_decodable(name.to_bytes()))
}

#[cfg(test)]
mod tests;
