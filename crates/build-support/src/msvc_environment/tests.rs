use super::*;
use std::{ffi::OsStr, fs, time::SystemTime};

#[test]
fn captured_names_are_case_insensitive_and_home_is_never_exported() -> io::Result<()> {
    let captured = read_variables(
        br#"{"Path":"captured","Include":"headers","HOME":"ignored","_CL_":"/test"}"#.as_slice(),
    )?;
    assert_eq!(captured.len(), 3);
    assert_eq!(captured["PATH"], "captured");
    assert_eq!(captured["INCLUDE"], "headers");
    assert_eq!(captured["_CL_"], "/test");
    assert!(!captured.contains_key("HOME"));
    Ok(())
}

#[test]
fn malformed_captures_fail_before_applying_child_variables() {
    for bytes in [
        br#"[]"#.as_slice(),
        br#"{"PATH":0}"#.as_slice(),
        br#"{"":"value"}"#.as_slice(),
        br#"{"A=B":"value"}"#.as_slice(),
        br#"{"A\u0000":"value"}"#.as_slice(),
        br#"{"A":"value\u0000"}"#.as_slice(),
        br#"{"Path":"one","PATH":"two"}"#.as_slice(),
        b"\xff".as_slice(),
    ] {
        assert_eq!(
            read_variables(bytes).err().map(|error| error.kind()),
            Some(io::ErrorKind::InvalidData)
        );
    }
}

#[test]
fn capture_limits_accept_the_exact_boundary_and_reject_overflow() -> io::Result<()> {
    let mut bytes = b"{}".to_vec();
    bytes.resize(CAPTURE_BYTES_MAX, b' ');
    assert!(read_variables(bytes.as_slice())?.is_empty());
    bytes.push(b' ');
    assert!(read_variables(bytes.as_slice()).is_err());
    let mut variables: BTreeMap<_, _> = (0..CAPTURE_VARIABLES_MAX)
        .map(|index| (format!("VARIABLE_{index}"), String::new()))
        .collect();
    let encode = |variables: &BTreeMap<String, String>| {
        serde_json::to_vec(variables).map_err(io::Error::other)
    };
    assert_eq!(
        read_variables(encode(&variables)?.as_slice())?.len(),
        CAPTURE_VARIABLES_MAX
    );
    variables.insert("ONE_MORE".into(), String::new());
    assert!(read_variables(encode(&variables)?.as_slice()).is_err());
    Ok(())
}

#[test]
fn input_read_errors_propagate() {
    struct FailedRead;
    impl Read for FailedRead {
        fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
            Err(io::Error::from_raw_os_error(5))
        }
    }
    assert_eq!(
        read_variables(FailedRead)
            .err()
            .and_then(|error| error.raw_os_error()),
        Some(5)
    );
}

#[test]
fn file_handoff_tracks_cargo_dependencies_and_overrides_only_captured_variables() -> io::Result<()>
{
    let stamp = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map_err(io::Error::other)?
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "awscli-msvc-capture-{}-{stamp}.json",
        std::process::id()
    ));
    fs::write(
        &path,
        br#"{"Include":"selected-headers","Path":"selected-tools","hOmE":"ignored"}"#,
    )?;
    let mut command = Command::new("unlaunched-compiler");
    command.env("INCLUDE", "ambient-headers");
    let mut output = Vec::new();
    let applied = apply_file(&mut command, &mut output, &path);
    fs::remove_file(&path)?;
    applied?;
    let variables: BTreeMap<_, _> = command.get_envs().collect();
    assert_eq!(
        variables[OsStr::new("INCLUDE")],
        Some(OsStr::new("selected-headers"))
    );
    assert_eq!(
        variables[OsStr::new("PATH")],
        Some(OsStr::new("selected-tools"))
    );
    assert!(
        !variables
            .keys()
            .any(|name| name.to_string_lossy().eq_ignore_ascii_case("HOME"))
    );
    assert_eq!(
        String::from_utf8(output).map_err(io::Error::other)?,
        format!(
            "cargo:rerun-if-env-changed={VARIABLE}\ncargo:rerun-if-changed={}\n",
            path.display()
        )
    );
    assert_eq!(
        apply_file(&mut command, &mut Vec::new(), &path)
            .err()
            .map(|error| error.kind()),
        Some(io::ErrorKind::NotFound)
    );
    Ok(())
}
