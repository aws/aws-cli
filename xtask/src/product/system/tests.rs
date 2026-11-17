use super::*;
#[test]
fn probe_preserves_values_and_library_order() -> Result<(), TaskError> {
    let facts = parse_probe(
        b"ignored line\nabi=python3.9\ninclude=/first\ninclude=/headers=selected\n\
        platlib=/packages\nlibdir=/libraries\nlibdir_is_loader_path=false\n\
        magic=1234\nunknown=ignored\nlink_libraries=m,,dl,\nlink_libraries=pthread\n",
    )?;
    for (key, expected) in [
        ("abi", "python3.9"),
        ("include", "/headers=selected"),
        ("platlib", "/packages"),
        ("libdir", "/libraries"),
        ("libdir_is_loader_path", "false"),
        ("magic", "1234"),
        ("link_libraries", "m,dl,pthread"),
    ] {
        assert_eq!(fact(&facts, key)?, expected);
    }
    Ok(())
}

#[test]
fn probe_preserves_missing_fields_and_accepts_loader_paths() -> Result<(), TaskError> {
    let facts = parse_probe(b" \nlibdir_is_loader_path=true\n ")?;
    assert_eq!(fact(&facts, "libdir_is_loader_path")?, "true");
    for key in [
        "abi",
        "include",
        "platlib",
        "libdir",
        "magic",
        "link_libraries",
    ] {
        assert!(!facts.contains_key(key));
    }
    assert!(validate_probe(&facts).is_err());
    assert!(parse_probe(b"libdir_is_loader_path=invalid\n").is_err());
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn missing_selected_interpreter_is_named_like_main() -> Result<(), TaskError> {
    let scratch =
        std::env::temp_dir().join(format!("aws-system-python-missing-{}", std::process::id()));
    fs::create_dir_all(&scratch)?;
    let python = scratch.join("missing-python3");
    let options = super::super::options::parse(&[
        "--link-mode=system".into(),
        format!("--python-exe={}", python.display()),
    ])?;
    let probed = probe(&scratch, &options, "system", "0.0.0");
    let validated = validate_bytecode(&scratch, &options, &scratch, "0");
    fs::remove_dir_all(&scratch)?;
    let expected = format!(
        "selected CPython executable {} was not found",
        python.display()
    );
    for result in [probed.map(|_| ()), validated] {
        assert_eq!(
            result.err().map(|failure| failure.to_string()),
            Some(expected.clone())
        );
    }
    Ok(())
}

#[test]
fn interpreter_failures_other_than_a_missing_executable_are_unchanged() {
    let python = Path::new("/usr/bin/python3.14");
    let message = missing_python(python, error("command failed"));
    assert!(matches!(message, TaskError::Message(text) if text == "command failed"));
    let denied = missing_python(
        python,
        TaskError::Io(io::Error::from(io::ErrorKind::PermissionDenied)),
    );
    assert!(
        matches!(denied, TaskError::Io(error) if error.kind() == io::ErrorKind::PermissionDenied)
    );
}

#[test]
fn crt_libraries_are_found_in_the_debian_multiarch_directory_of_each_system_architecture() {
    let directories = build_support::SYSTEM_ARCHITECTURES
        .map(|(arch, _)| multiarch_library_dir(&format!("{arch}-unknown-linux-gnu")));
    assert_eq!(
        directories,
        [
            "lib/x86_64-linux-gnu",
            "lib/aarch64-linux-gnu",
            "lib/riscv64-linux-gnu",
            "lib/powerpc64le-linux-gnu",
            "lib/loongarch64-linux-gnu",
        ]
    );
}

#[test]
fn payload_scratch_sits_outside_the_prefix_and_splits_by_mode() {
    let root = Path::new("/checkout");
    let target = "x86_64-unknown-linux-gnu";
    let embedded = payload_work(root, target, "embedded");
    assert_eq!(
        embedded,
        root.join("target/deps")
            .join(target)
            .join("work/system-payload/embedded")
    );
    assert_ne!(payload_work(root, target, "system"), embedded);
    assert!(!embedded.starts_with(root.join("target/deps").join(target).join("system-0123")));
}
