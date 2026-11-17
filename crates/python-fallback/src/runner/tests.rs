use super::*;
#[cfg(unix)]
use std::os::unix::ffi::OsStringExt;

#[test]
#[cfg(unix)]
fn argv_preserves_program_name_empty_arguments_and_non_utf8_bytes() -> Result<(), RunError> {
    let argv = [
        "/path/aws".into(),
        "".into(),
        OsString::from_vec(vec![0xff, b'a']),
    ];
    let encoded = arguments(&argv)?;
    assert_eq!(encoded[0].as_bytes(), b"/path/aws");
    assert_eq!(encoded[1].as_bytes(), b"");
    assert_eq!(encoded[2].as_bytes(), &[0xff, b'a']);
    assert_eq!(
        arguments(&[OsString::from_vec(vec![b'a', 0])]),
        Err(RunError::InvalidArgument)
    );
    Ok(())
}

#[test]
#[cfg(windows)]
fn argv_preserves_utf16_including_unpaired_surrogates() -> Result<(), RunError> {
    use std::os::windows::ffi::OsStringExt;
    let argv = [
        OsString::from("aws"),
        OsString::new(),
        OsString::from_wide(&[0xd800, 0x61]),
    ];
    let encoded = arguments(&argv)?;
    assert_eq!(encoded[0], [0x61, 0x77, 0x73, 0]);
    assert_eq!(encoded[1], [0]);
    assert_eq!(encoded[2], [0xd800, 0x61, 0]);
    assert_eq!(
        arguments(&[OsString::from_wide(&[0])]),
        Err(RunError::InvalidArgument)
    );
    Ok(())
}

#[test]
fn setup_failures_render_their_stderr_diagnostic_lines() {
    for (error, line) in [
        (
            RunError::ConfigureStdioEncoding,
            "error: failed to configure Python stdio err=StdioEncodingFailed\n",
        ),
        (
            RunError::ConfigureStdioErrors,
            "error: failed to configure Python stdio err=StdioErrorHandlerFailed\n",
        ),
        (
            RunError::AlreadyStarted,
            "error(python_fallback): the Python interpreter has already run in this process\n",
        ),
        (
            RunError::TooManyArguments,
            "error(python_fallback): too many argv entries for CPython\n",
        ),
        (
            RunError::InvalidArgument,
            "error(python_fallback): an argv entry contains a NUL byte\n",
        ),
        (
            RunError::RegisterExtensions,
            "error(python_fallback): failed to register builtin extensions\n",
        ),
        (
            RunError::ConfigureArguments,
            "error(python_fallback): failed to set argv\n",
        ),
        (
            RunError::ConfigureExecutable,
            "error(python_fallback): failed to configure selected Python executable\n",
        ),
        (
            RunError::Initialize,
            "error(python_fallback): failed to initialize CPython\n",
        ),
    ] {
        assert_eq!(error.diagnostic_line(), line);
    }
}

#[test]
fn failed_finalization_after_an_exit_exits_120_as_py_exit_does() {
    for status in [0, 1, 2, 252, 254, 255] {
        assert_eq!(status_after_finalization(Ending::Exited(status), 0), status);
        assert_eq!(
            status_after_finalization(Ending::Exited(status), -1),
            FINALIZATION_FAILURE_STATUS
        );
    }
    assert_eq!(FINALIZATION_FAILURE_STATUS, 120);
}

#[test]
fn failed_finalization_after_an_uncaught_exception_keeps_status_1() {
    assert_eq!(status_after_finalization(Ending::Failed, 0), 1);
    assert_eq!(status_after_finalization(Ending::Failed, -1), 1);
}
