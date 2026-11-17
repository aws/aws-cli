use super::*;

/// Only the default artifact names `deps::TARGET`, so only it takes the
/// static host list; an explicit binary runs on any host.
#[test]
fn only_the_default_artifact_takes_the_static_host_check() -> Result<(), TaskError> {
    fn unsupported() -> Result<String, TaskError> {
        Err(deps::error("unsupported native host"))
    }
    let explicit = std::env::current_exe()?;
    let path = explicit
        .to_str()
        .ok_or_else(|| deps::error("test executable path is not UTF-8"))?;
    let args = ["--aws-binary".to_owned(), path.to_owned()];
    assert_eq!(
        select_binary(Path::new("/workspace"), &args, unsupported)?,
        explicit
    );
    assert_eq!(
        select_binary(Path::new("/workspace"), &[], unsupported).map_err(|error| error.to_string()),
        Err("unsupported native host".to_owned())
    );
    Ok(())
}

/// A system build's default artifact lies under the triple its target
/// check names, as the build writes it.
#[test]
fn the_default_artifact_lies_under_the_default_target() {
    fn system() -> Result<String, TaskError> {
        Ok("x86_64-unknown-linux-gnu".to_owned())
    }
    // Joined component by component, as the host spells a path.
    let expected = [
        "/workspace",
        "target",
        "x86_64-unknown-linux-gnu",
        "release-safe",
        "aws",
    ]
    .iter()
    .collect::<PathBuf>()
    .with_extension(std::env::consts::EXE_EXTENSION);
    assert_eq!(
        select_binary(Path::new("/workspace"), &[], system).map_err(|error| error.to_string()),
        Err(format!(
            "Rust CLI is absent: {}; build it or supply --aws-binary",
            expected.display()
        ))
    );
}

#[test]
fn selection_and_early_stop_arguments_are_rejected() {
    for args in [
        ["-k", "test_ls"],
        ["--deselect", "test"],
        ["-x", "--run-all"],
    ] {
        assert!(binary(Path::new("/workspace"), &args.map(str::to_owned)).is_err());
    }
}

#[test]
fn junit_distinguishes_expected_failures_from_unexecuted_skips() {
    let xml = concat!(
        "<testsuites><testsuite tests=\"3\" failures=\"0\" errors=\"0\" skipped=\"2\">",
        "<testcase/><testcase><skipped type=\"pytest.xfail\" message=\"known\"/></testcase>",
        "<testcase><skipped type=\"pytest.skip\" message=\"platform\"/></testcase>",
        "</testsuite></testsuites>"
    );
    assert_eq!(
        counts(xml).ok(),
        Some(Counts {
            tests: 3,
            failures: 0,
            errors: 0,
            skipped: 1,
            xfailed: 1,
            native_parity_failures: 0,
        })
    );
}

#[test]
fn junit_reports_native_parity_separately_from_shared_harness_failures() -> Result<(), TaskError> {
    let xml = concat!(
        "<testsuite tests=\"3\" failures=\"0\" errors=\"0\" skipped=\"2\">",
        "<testcase><skipped type=\"pytest.xfail\" message=\"parity-gap: output\"/>",
        "</testcase><testcase><skipped type=\"pytest.xfail\" ",
        "message=\"shared-harness-failure: local mock\"/></testcase><testcase/>",
        "</testsuite>"
    );
    let actual = counts(xml)?;
    assert_eq!(actual.native_parity_failures, 1);
    assert_eq!(actual.xfailed, 2);
    Ok(())
}

#[test]
fn malformed_junit_does_not_silently_produce_passing_counts() {
    for xml in [
        "",
        "<testsuite",
        "<testsuite tests=\"bad\">",
        "<testsuite skipped=\"0\">",
    ] {
        assert!(counts(xml).is_err());
    }
}

#[test]
fn self_tests_run_through_their_runner_and_preserve_home() {
    let root = Path::new("/workspace");
    let forwarded = ["-k".to_owned(), "payload".to_owned()];
    let command = self_test_command(root, Some(Path::new("/toolchain/bin/cc")), &forwarded);
    assert_eq!(command.get_program(), "python3");
    let args: Vec<_> = command.get_args().collect();
    assert_eq!(
        args,
        [
            "-B".as_ref(),
            root.join("tests/deps/run.py").as_os_str(),
            "--cache-dir".as_ref(),
            root.join("target/harness-test").as_os_str(),
            "-k".as_ref(),
            "payload".as_ref(),
        ]
    );
    assert!(!command.get_envs().any(|(key, _)| key == "HOME"));
    assert!(
        command
            .get_envs()
            .any(|(key, value)| key == "AWS_NATIVE_TEST_CC"
                && value == Some("/toolchain/bin/cc".as_ref()))
    );
    let without = self_test_command(root, None, &[]);
    assert!(
        !without
            .get_envs()
            .any(|(key, _)| key == "AWS_NATIVE_TEST_CC")
    );
}
