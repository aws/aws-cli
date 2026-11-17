use super::*;

#[test]
fn dump_starts_at_marker_and_preserves_empty_values() -> Result<()> {
    let dump = concat!(
        "[vcvarsall.bat] Environment initialized\r\nPATH=C:\\before\r\n",
        "__msvc_env__\r\nPATH=C:\\tools;C:\\before\r\n",
        "VCToolsVersion=14.44.35207\r\nWindowsSDKVersion=10.0.26100.0\\\r\n",
        "EMPTY=\r\n=ExitCode=00000000\r\n",
    );
    let variables = parse_dump(dump)?.ok_or_else(|| error("missing marker"))?;
    assert_eq!(variables.len(), 4);
    assert_eq!(variables["PATH"], "C:\\tools;C:\\before");
    assert_eq!(variables["VCToolsVersion"], "14.44.35207");
    assert_eq!(variables["WindowsSDKVersion"], "10.0.26100.0\\");
    assert_eq!(variables["EMPTY"], "");
    assert!(!variables.contains_key("ExitCode"));
    Ok(())
}

#[test]
fn driver_carries_paths_only_in_environment_and_switches_to_utf8() -> Result<()> {
    for hostile in [
        "C:\\Program Files (x86)\\Microsoft Visual Studio",
        "C:\\vs%OS%\\VC",
        "C:\\café\\VC",
    ] {
        assert!(!DRIVER_CONTENTS.contains(hostile));
    }
    let position = |needle| {
        DRIVER_CONTENTS
            .find(needle)
            .ok_or_else(|| error("missing driver text"))
    };
    assert!(
        position("call \"%AWSCLI_NATIVE_VCVARS%\"")?
            < position("\r\nset AWSCLI_NATIVE_VCVARS=\r\n")?
    );
    assert!(position("\r\nset AWSCLI_NATIVE_VCVARS=\r\n")? < position("echo __msvc_env__")?);
    assert!(position("chcp 65001")? < position("echo __msvc_env__")?);
    assert_eq!(
        DRIVER_CONTENTS.matches('\n').count(),
        DRIVER_CONTENTS.matches("\r\n").count()
    );
    Ok(())
}

#[test]
fn dump_values_keep_equals_and_unicode() -> Result<()> {
    let variables =
        parse_dump("__msvc_env__\r\nINCLUDE=C:\\café\\include\r\n_CL_=-DGREETING=hello\r\n")?
            .ok_or_else(|| error("missing marker"))?;
    assert_eq!(variables.len(), 2);
    assert_eq!(variables["INCLUDE"], "C:\\café\\include");
    assert_eq!(variables["_CL_"], "-DGREETING=hello");
    Ok(())
}

#[test]
fn missing_marker_reports_failed_batch_file() -> Result<()> {
    assert!(parse_dump("The system cannot find the path specified.\r\n")?.is_none());
    assert!(parse_dump("")?.is_none());
    Ok(())
}

#[test]
fn captured_variables_apply_without_mutating_home() {
    let environment = Environment {
        variables: BTreeMap::from([
            ("INCLUDE".into(), "C:\\sdk\\include".into()),
            ("LIB".into(), "C:\\sdk\\lib".into()),
            ("HOME".into(), "must remain inherited".into()),
        ]),
        tools_version: "14.44.35207".into(),
        sdk_version: "10.0.26100.0".into(),
    };
    let mut command = Command::new("unused-native-tool");
    environment.apply(&mut command);
    let variables: BTreeMap<_, _> = command.get_envs().collect();
    assert_eq!(
        variables[OsStr::new("INCLUDE")],
        Some(OsStr::new("C:\\sdk\\include"))
    );
    assert_eq!(
        variables[OsStr::new("LIB")],
        Some(OsStr::new("C:\\sdk\\lib"))
    );
    assert!(!variables.contains_key(OsStr::new("HOME")));
    assert_eq!(variables[OsStr::new("CL")], None);
    assert_eq!(variables[OsStr::new("_CL_")], None);
}

#[test]
fn oversized_dump_is_rejected_before_parsing() {
    assert!(parse_dump(&"x".repeat(DUMP_BYTES_MAX + 1)).is_err());
    assert!(parse_dump(&"\n".repeat(DUMP_LINES_MAX - 1)).is_err());
}

#[test]
fn identity_tracks_captured_headers_libraries_and_toolset_versions() -> Result<()> {
    let initial = Environment {
        variables: BTreeMap::from([
            ("INCLUDE".into(), "headers".into()),
            ("LIB".into(), "libraries".into()),
            ("LIBPATH".into(), "metadata".into()),
        ]),
        tools_version: "14.44.35207".into(),
        sdk_version: "10.0.26100.0".into(),
    };
    let identity = initial.identity()?;
    for name in ["INCLUDE", "LIB", "LIBPATH"] {
        let mut changed = initial.clone();
        changed.variables.insert(name.into(), "changed".into());
        assert_ne!(changed.identity()?, identity);
    }
    let mut changed = initial.clone();
    changed.tools_version.push('1');
    assert_ne!(changed.identity()?, identity);
    let mut changed = initial.clone();
    changed.sdk_version.push('1');
    assert_ne!(changed.identity()?, identity);
    Ok(())
}

#[cfg(unix)]
#[test]
fn bounded_capture_keeps_utf8_and_rejects_either_stream_overflow() -> Result<()> {
    assert_eq!(
        capture::output(Command::new("sh").args(["-c", "printf 'café'"]), 64)?,
        "café",
    );
    for script in ["printf '12345'", "printf '12345' >&2"] {
        let failure = capture::output(Command::new("sh").args(["-c", script]), 4);
        assert!(matches!(failure, Err(crate::TaskError::Message(message))
            if message == "unable to run sh: StreamTooLong"));
    }
    let failure = capture::output(
        Command::new("sh").args(["-c", "printf 'error\\n' >&2; exit 3"]),
        64,
    );
    assert!(matches!(failure, Err(crate::TaskError::Message(message))
        if message == "sh failed"));
    Ok(())
}

// Discovery children get the null device as stdin, whatever stdin the
// caller's command carried.
#[cfg(target_os = "linux")]
#[test]
fn capture_gives_the_child_null_stdin() -> Result<()> {
    let mut command = Command::new("sh");
    command
        .args(["-c", "readlink /proc/self/fd/0"])
        .stdin(std::process::Stdio::piped());
    assert_eq!(capture::output(&mut command, 256)?.trim_end(), "/dev/null");
    Ok(())
}

#[cfg(unix)]
#[test]
fn capture_failures_name_the_program() {
    let missing = capture::output(&mut Command::new("/nonexistent/vswhere.exe"), 64);
    assert!(matches!(missing, Err(crate::TaskError::Message(message))
        if message.starts_with("unable to run /nonexistent/vswhere.exe: ")));
    let failed = capture::output(Command::new("sh").args(["-c", "exit 1"]), 64);
    assert!(matches!(failed, Err(crate::TaskError::Message(message)) if message == "sh failed"));
    let binary = capture::output(Command::new("sh").args(["-c", "printf '\\377'"]), 64);
    assert!(matches!(binary, Err(crate::TaskError::Message(message))
        if message.starts_with("sh did not emit UTF-8: ")));
}

// The Perl probe fails quietly.
#[cfg(unix)]
#[test]
fn probe_returns_only_a_successful_stdout() {
    let probe = |script| capture::probe(Command::new("sh").args(["-c", script]), 64);
    assert_eq!(probe("printf MSWin32").as_deref(), Some("MSWin32"));
    assert_eq!(probe("printf MSWin32; exit 1"), None);
    assert_eq!(
        probe("printf 'longer than sixty-four bytes of output %064d' 0"),
        None
    );
}

// An overflow on one stream returns at once, even while a grandchild still
// holds the other stream open.
#[cfg(unix)]
#[test]
fn overflow_returns_without_draining_the_other_stream() {
    let start = std::time::Instant::now();
    let failure = capture::output(
        Command::new("sh").args([
            "-c",
            "sleep 20 </dev/null & head -c 100 /dev/zero >&2; wait",
        ]),
        16,
    );
    assert!(
        start.elapsed() < std::time::Duration::from_secs(10),
        "capture waited {:?} for the grandchild's stdout",
        start.elapsed()
    );
    assert!(matches!(failure, Err(crate::TaskError::Message(message))
        if message == "unable to run sh: StreamTooLong"));
}
