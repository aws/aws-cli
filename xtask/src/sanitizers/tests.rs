use super::*;

/// One Cargo `compiler-artifact` message line.
fn artifact(test: bool, executable: Option<&str>, manifest: Option<&str>) -> String {
    let mut message = serde_json::json!({
        "reason": "compiler-artifact",
        "profile": {"test": test},
        "executable": executable,
    });
    if let Some(manifest) = manifest {
        message["manifest_path"] = manifest.into();
    }
    format!("{message}\n")
}

#[test]
fn cargo_artifacts_include_harnessless_tests_and_deduplicate_executables() -> Result<(), TaskError>
{
    let finder = Some("/src/crates/finder/Cargo.toml");
    let messages = [
        artifact(true, Some("/tmp/finder"), finder),
        artifact(false, Some("/tmp/aws"), Some("/src/crates/aws/Cargo.toml")),
        artifact(true, Some("/tmp/finder"), finder),
        artifact(true, None, finder),
        "{\"reason\":\"build-finished\",\"success\":true}\n".to_owned(),
    ]
    .concat();
    assert_eq!(
        executables(messages.as_bytes())?,
        [TestBinary {
            path: PathBuf::from("/tmp/finder"),
            package: PathBuf::from("/src/crates/finder"),
        }]
    );
    Ok(())
}

#[test]
fn test_executables_without_a_package_directory_are_rejected() {
    let message = artifact(true, Some("/tmp/finder"), None);
    assert!(executables(message.as_bytes()).is_err());
}

#[test]
fn missing_test_artifacts_fail_instead_of_claiming_a_pass() {
    assert!(executables(br#"{"reason":"build-finished","success":true}"#).is_err());
    assert!(executables(b"not json").is_err());
}

#[test]
fn the_runtime_prefix_is_the_directory_above_its_lib() -> Result<(), TaskError> {
    let prefix = Path::new("/deps/ubsan-minimal-0123");
    assert_eq!(
        runtime_prefix(&prefix.join("lib/libclang_rt.ubsan_minimal-musl.a"))?,
        prefix
    );
    assert!(runtime_prefix(Path::new("archive.a")).is_err());
    Ok(())
}
