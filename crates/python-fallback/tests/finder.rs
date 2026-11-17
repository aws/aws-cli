#[path = "finder/assertions.rs"]
mod assertions;
#[path = "finder/fixture.rs"]
mod fixture;
#[path = "finder/support.rs"]
mod support;

use python_fallback::{ffi as py, finder};
use std::error::Error;
use std::ffi::CString;
use std::io::Write;

const TEST_NAME: &str =
    "python_module_serves_synthetic_payload_methods_and_imports_in_isolated_cpython";

fn main() -> Result<(), Box<dyn Error>> {
    if std::env::args().any(|argument| argument == "--list") {
        writeln!(std::io::stdout().lock(), "{TEST_NAME}: test")?;
        return Ok(());
    }
    if std::env::args().any(|argument| argument == "--child") {
        return child();
    }
    let executable = std::env::current_exe()?;
    let output = std::process::Command::new(executable)
        .arg("--child")
        .output()?;
    assert!(
        output.status.success(),
        "finder harness failed: {}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    writeln!(std::io::stdout().lock(), "test {TEST_NAME} ... ok")?;
    Ok(())
}

fn child() -> Result<(), Box<dyn Error>> {
    finder::force_link();
    let mut interpreter = support::Interpreter::new()?;
    expect_init_allocation_failures_release_module()?;
    support::run(assertions::MISSING_PAYLOAD)?;
    // SAFETY: this process owns the initialized interpreter's GIL throughout the harness.
    unsafe {
        assert!(!finder::install_payload(b"ZIPPY003"));
        support::expect_exception(py::PyExc_RuntimeError);
    }
    let payload = fixture::payload()?;
    install(payload);
    support::expected(20, payload.len())?;
    support::run(assertions::ASSERTIONS)?;
    edge_cases()?;
    reinstall()?;
    support::run_in_subinterpreter(assertions::SUBINTERPRETER)?;
    support::run(assertions::AFTER_SUBINTERPRETER)?;
    unsorted_listings()?;
    finalization(&mut interpreter)?;
    Ok(())
}

const INIT_ALLOCATION_COUNT_MAX: usize = 1024;

fn expect_init_allocation_failures_release_module() -> Result<(), Box<dyn Error>> {
    for served in 0..INIT_ALLOCATION_COUNT_MAX {
        let (module, failed) = support::fail_object_allocation_after(served, || {
            // SAFETY: the harness holds the GIL, as CPython does when it initializes a module.
            unsafe { finder::PyInit__zippy_finder() }
        });
        if module.is_null() {
            assert!(failed);
            support::expect_memory_error();
        } else {
            // SAFETY: the initializer returned a new reference the harness owns.
            unsafe { py::Py_DecRef(module) };
            support::expect_clear();
        }
        support::run(assertions::INIT_FAILURE_ASSERTIONS)?;
        if !failed {
            return Ok(());
        }
    }
    Err("every module initialization failed an allocation".into())
}

fn edge_cases() -> Result<(), Box<dyn Error>> {
    install(fixture::edges()?);
    support::run(assertions::EDGES)?;
    expect_file_allocation_failure_propagates()
}

fn expect_file_allocation_failure_propagates() -> Result<(), Box<dyn Error>> {
    support::run(assertions::FILE_ALLOCATION_SETUP)?;
    let exec_module = support::main_global(c"file_allocation_exec")?;
    let args = support::main_global(c"file_allocation_args")?;
    let size = support::main_size(c"file_allocation_size")?;
    let (result, failures) = support::fail_object_allocation_of_size(size, || {
        // SAFETY: both borrowed objects live in `__main__`; the harness holds the GIL.
        unsafe { py::PyObject_CallObject(exec_module, args) }
    });
    if !result.is_null() {
        // SAFETY: a non-null result is a new reference the harness owns.
        unsafe { py::Py_DecRef(result) };
    }
    assert_eq!(failures, 1);
    assert!(result.is_null());
    support::expect_memory_error();
    support::run(assertions::FILE_ALLOCATION_ASSERTIONS)
}

fn install(payload: &'static [u8]) {
    // SAFETY: fixture owners retain their bytes for process lifetime; the harness holds the GIL.
    assert!(unsafe { finder::install_payload(payload) });
    support::expect_clear();
}

fn reinstall() -> Result<(), Box<dyn Error>> {
    let replacement = fixture::replacement();
    install(replacement);
    support::expected(1, replacement.len())?;
    support::run(assertions::REPLACEMENT_ASSERTIONS)?;
    // SAFETY: the harness owns the GIL; a malformed payload must preserve the previous view.
    unsafe {
        assert!(!finder::install_payload(b"not-a-payload"));
        support::expect_exception(py::PyExc_RuntimeError);
    }
    support::run(assertions::REJECTED_REINSTALL_ASSERTIONS)?;
    failed_setup_reinstall()?;
    install(replacement);
    support::run(assertions::REPLACEMENT_ASSERTIONS)
}

fn failed_setup_reinstall() -> Result<(), Box<dyn Error>> {
    support::run("saved_meta_path = sys.meta_path\nsys.meta_path = None")?;
    let other = fixture::alternate();
    // SAFETY: the harness owns the GIL; invalid meta_path makes finder setup fail.
    unsafe {
        assert!(!finder::install_payload(other));
        assert!(!py::PyErr_Occurred().is_null());
        py::PyErr_Clear();
    }
    support::run("sys.meta_path = saved_meta_path")?;
    support::run(assertions::REJECTED_REINSTALL_ASSERTIONS)
}

fn unsorted_listings() -> Result<(), Box<dyn Error>> {
    for payload in fixture::unsorted()? {
        install(payload);
        support::run(assertions::UNSORTED_ASSERTIONS)?;
    }
    Ok(())
}

fn finalization(interpreter: &mut support::Interpreter) -> Result<(), Box<dyn Error>> {
    let marker = std::env::temp_dir().join(format!("aws-python-finder-{}", std::process::id()));
    let text = CString::new(marker.as_os_str().as_encoded_bytes())?;
    support::set_text(c"FINALIZE_MARKER_PATH", &text)?;
    support::run(assertions::ATEXIT_IMPORT_REGISTRATION)?;
    interpreter.finalize();
    assert_eq!(std::fs::read(&marker)?, b"imported");
    std::fs::remove_file(marker)?;
    Ok(())
}
