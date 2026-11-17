use super::*;

#[test]
fn runner_receives_pinned_inputs_and_preserves_environment() {
    let forwarded = [
        "--collect-only",
        "-q",
        "--tests-path",
        "tests/integration/example.py",
    ]
    .map(str::to_owned);
    let command = command(
        Path::new("/workspace"),
        Path::new("/rust/aws"),
        Path::new("/pinned/aws-cli"),
        &forwarded,
    );
    // Compared as paths, which a Windows join spells with `\`.
    assert_eq!(
        command.get_args().map(Path::new).collect::<Vec<_>>(),
        [
            "-B",
            "/workspace/tests/integ/run_integ_tests.py",
            "--aws-binary",
            "/rust/aws",
            "--aws-cli-source",
            "/pinned/aws-cli",
            "--cache-dir",
            "/workspace/target/integ-test",
            "--collect-only",
            "-q",
            "--tests-path",
            "tests/integration/example.py",
        ]
        .map(Path::new)
    );
    assert_eq!(command.get_envs().count(), 0);
    assert_eq!(command.get_current_dir(), Some(Path::new("/workspace")));
}

#[test]
fn arguments_after_separator_reach_pytest_unchanged() {
    let args = [
        "--aws-binary",
        "/rust/aws",
        "--",
        "--collect-only",
        "-k",
        "name with spaces",
    ]
    .map(str::to_owned);
    let (artifact, forwarded) = arguments(&args);
    assert_eq!(artifact, ["--aws-binary", "/rust/aws"]);
    assert_eq!(forwarded, ["--collect-only", "-k", "name with spaces"]);
    assert_eq!(arguments(&[]), (&[][..], &[][..]));
}

/// An explicit binary takes no host check: checking that it exists is the
/// first thing `run` does with it.
#[test]
fn explicit_binary_is_checked_before_any_harness_step() {
    let args = ["--aws-binary", "/absent/aws", "--", "--collect-only"].map(str::to_owned);
    assert_eq!(
        run(Path::new("/workspace"), &args).map_err(|error| error.to_string()),
        Err("Rust CLI is absent: /absent/aws; build it or supply --aws-binary".to_owned())
    );
}
