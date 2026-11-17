#[path = "exit_status/cases.rs"]
mod cases;

use pyload as _;
use python_fallback::{configuration, exit_status, ffi, helpers};
use std::ffi::{CStr, CString};
use std::io::{self, Write};
use std::ptr;

const TEST_NAME: &str = "raised_system_exit_values_translate_to_host_process_exit_statuses";

fn main() -> io::Result<()> {
    if std::env::args().any(|argument| argument == "--list") {
        return writeln!(io::stdout(), "{TEST_NAME}: test");
    }
    let interpreter = Interpreter::new()?;
    run_cases(interpreter.globals)?;
    interpreter.finish()?;
    writeln!(
        io::stdout(),
        "test {TEST_NAME} ... ok (27 baseline and 4 error/lifetime cases)"
    )
}

struct Interpreter {
    globals: *mut ffi::PyObject,
}

impl Interpreter {
    fn new() -> io::Result<Self> {
        python_fallback::finder::force_link();
        let arguments = [c"aws-python-exit-harness".as_ptr()];
        let executable = CString::new(configuration::EXECUTABLE)?;
        let executable_pointer = if configuration::DYNAMIC {
            executable.as_ptr()
        } else {
            ptr::null()
        };
        let mut exit_code = 0;
        // SAFETY: this standalone process initializes CPython once; argv lives through the call.
        let initialized = unsafe {
            ffi::aws_python_initialize(
                1,
                arguments.as_ptr(),
                1,
                executable_pointer,
                1,
                helpers::STDIO_ENCODING.as_ptr(),
                helpers::STDIO_ERRORS.as_ptr(),
                &mut exit_code,
            )
        };
        assert_eq!(initialized, 0, "CPython initialization status {exit_code}");
        // SAFETY: initialization returned with the GIL; main/globals are interpreter-owned borrows.
        let globals = unsafe {
            let main = ffi::PyImport_AddModule(c"__main__".as_ptr());
            assert!(!main.is_null());
            ffi::PyModule_GetDict(main)
        };
        assert!(!globals.is_null());
        let interpreter = Self { globals };
        let path_assertions = if configuration::DYNAMIC {
            c"import sys\nassert sys.path\nassert '' not in sys.path"
        } else {
            c"import sys\nassert sys.path == []"
        };
        run_statements(globals, path_assertions)?;
        run_statements(globals, cases::CAPTURE_STDERR)?;
        Ok(interpreter)
    }

    fn finish(self) -> io::Result<()> {
        run_statements(self.globals, c"sys.stderr = sys.__stderr__")?;
        // SAFETY: all owned references are released; only inert raw borrows remain in self.
        let result = unsafe { ffi::Py_FinalizeEx() };
        assert_eq!(result, 0);
        Ok(())
    }
}

impl Drop for Interpreter {
    fn drop(&mut self) {
        // SAFETY: this single-threaded harness exclusively owns the interpreter lifecycle.
        unsafe {
            if ffi::Py_IsInitialized() != 0 {
                let _ = run_statements(self.globals, c"sys.stderr = sys.__stderr__");
                let _ = ffi::Py_FinalizeEx();
            }
        }
    }
}

fn run_cases(globals: *mut ffi::PyObject) -> io::Result<()> {
    for case in cases::CASES.iter().chain(cases::ERROR_CASES) {
        // SAFETY: globals is borrowed from the live interpreter; each result is decref'd here.
        unsafe {
            let result = ffi::PyRun_StringFlags(
                case.source.as_ptr(),
                ffi::PY_FILE_INPUT,
                globals,
                globals,
                ptr::null_mut(),
            );
            if !result.is_null() {
                ffi::Py_DecRef(result);
            }
            assert!(result.is_null(), "source {:?} did not raise", case.source);
            assert_ne!(ffi::PyErr_ExceptionMatches(ffi::PyExc_SystemExit), 0);
            assert_eq!(
                exit_status::from_raised_system_exit(),
                case.status,
                "{:?}",
                case.source
            );
            assert!(ffi::PyErr_Occurred().is_null());
        }
        let diagnostic = take_captured_stderr(globals)?;
        if case.stderr_contains.is_empty() {
            assert_eq!(diagnostic, "", "{:?}", case.source);
        } else {
            assert!(
                diagnostic.contains(case.stderr_contains),
                "{:?}: {diagnostic}",
                case.source
            );
        }
    }
    Ok(())
}

fn run_statements(globals: *mut ffi::PyObject, source: &CStr) -> io::Result<()> {
    // SAFETY: caller's globals comes from the live GIL-held interpreter; source is NUL-terminated.
    unsafe {
        let result = ffi::PyRun_StringFlags(
            source.as_ptr(),
            ffi::PY_FILE_INPUT,
            globals,
            globals,
            ptr::null_mut(),
        );
        if result.is_null() {
            ffi::PyErr_Print();
            return Err(io::Error::other("unexpected Python exception"));
        }
        ffi::Py_DecRef(result);
        Ok(())
    }
}

fn take_captured_stderr(globals: *mut ffi::PyObject) -> io::Result<String> {
    // SAFETY: interpreter is live with the GIL; UTF-8 is copied before releasing its text owner.
    unsafe {
        let text = ffi::PyRun_StringFlags(
            c"sys.stderr.take()".as_ptr(),
            ffi::PY_EVAL_INPUT,
            globals,
            globals,
            ptr::null_mut(),
        );
        if text.is_null() {
            ffi::PyErr_Print();
            return Err(io::Error::other("cannot read captured stderr"));
        }
        let mut length = 0;
        let utf8 = ffi::PyUnicode_AsUTF8AndSize(text, &mut length);
        let copied = if utf8.is_null() || length < 0 {
            Err(io::Error::other("captured stderr is not UTF-8"))
        } else {
            let bytes = std::slice::from_raw_parts(utf8.cast::<u8>(), length as usize);
            String::from_utf8(bytes.to_vec()).map_err(io::Error::other)
        };
        ffi::Py_DecRef(text);
        copied
    }
}
