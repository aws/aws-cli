use super::*;

#[test]
fn artifact_selection_keeps_both_interpreter_harnesses_and_unit_tests() -> Result<(), TaskError> {
    let bytes = br#"{"reason":"compiler-artifact","profile":{"test":true},"executable":"/finder"}
{"reason":"compiler-artifact","profile":{"test":true},"executable":"/exit-status"}
{"reason":"compiler-artifact","profile":{"test":true},"executable":"/unit"}
{"reason":"compiler-artifact","profile":{"test":false},"executable":"/build-script"}
{"reason":"build-finished","success":true}"#;
    assert_eq!(
        test_artifacts(bytes)?,
        ["/exit-status", "/finder", "/unit"].map(PathBuf::from)
    );
    assert!(test_artifacts(b"{}").is_err());
    Ok(())
}

#[test]
fn test_runs_pass_the_filter_first_under_the_build_environment() {
    let mut build = Command::new("cargo");
    build.env("AWS_NATIVE_CRT_PREFIX", "/crt");
    let profile = Path::new("/coverage/profiles/%p-%m.profraw");
    let filtered = test_command(
        Path::new("/workspace"),
        Path::new("/unit"),
        &build,
        profile,
        Some("scheduler"),
    );
    assert_eq!(filtered.get_program(), "/unit");
    assert_eq!(filtered.get_args().collect::<Vec<_>>(), ["scheduler"]);
    assert_eq!(filtered.get_current_dir(), Some(Path::new("/workspace")));
    let environment = filtered.get_envs().collect::<Vec<_>>();
    assert!(environment.contains(&("AWS_NATIVE_CRT_PREFIX".as_ref(), Some("/crt".as_ref()))));
    assert!(environment.contains(&("LLVM_PROFILE_FILE".as_ref(), Some(profile.as_os_str()))));
    let unfiltered = test_command(
        Path::new("/workspace"),
        Path::new("/unit"),
        &build,
        profile,
        None,
    );
    assert_eq!(unfiltered.get_args().count(), 0);
}
