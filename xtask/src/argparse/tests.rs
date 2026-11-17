use super::*;

#[test]
fn oracle_receives_explicit_binaries_sources_and_ledger() {
    let command = oracle_command(
        Path::new("/workspace"),
        Path::new("/rust/argparse-tool"),
        Path::new("/rust/capture/aws"),
        Path::new("/pinned/aws-cli"),
        Path::new("/tables.json"),
        Path::new("/results"),
    );
    // Compared as paths, which a Windows join spells with `\`.
    let arguments: Vec<_> = command.get_args().map(Path::new).collect();
    assert_eq!(
        arguments,
        [
            "-B",
            "/workspace/tests/argparse/parse_oracle.py",
            "--capture-binary",
            "/rust/capture/aws",
            "--native-parser",
            "/rust/argparse-tool",
            "--aws-cli-source",
            "/pinned/aws-cli",
            "--native-tables",
            "/tables.json",
            "--ledger",
            "/results/divergences.jsonl",
        ]
        .map(Path::new)
    );
    assert_eq!(command.get_envs().count(), 0);
}

#[test]
fn table_check_provisions_its_own_venv() {
    let root = Path::new("/workspace");
    let command = table_check_command(
        root,
        Path::new("/pinned/aws-cli"),
        Path::new("/tables.json"),
    );
    let arguments: Vec<_> = command.get_args().map(PathBuf::from).collect();
    assert_eq!(
        arguments,
        [
            PathBuf::from("-B"),
            root.join("tests/argparse/argtables.py"),
            PathBuf::from("--aws-cli-source"),
            PathBuf::from("/pinned/aws-cli"),
            PathBuf::from("--cache-dir"),
            root.join("target/argtables"),
            PathBuf::from("--native-tables"),
            PathBuf::from("/tables.json"),
        ]
    );
    assert_eq!(command.get_current_dir(), Some(root));
    assert_eq!(command.get_envs().count(), 0);
}

#[test]
fn options_reject_missing_values_and_invalid_fuzz_counts() {
    for args in [
        vec!["--capture-binary"],
        vec!["--aws-binary", "target/aws"],
        vec!["--fuzz", "0"],
        vec!["--fuzz", "-1"],
        vec!["--seed", "invalid"],
        vec!["--other", "value"],
    ] {
        assert!(options(&args.into_iter().map(str::to_owned).collect::<Vec<_>>()).is_err());
    }
}

#[test]
fn parser_runner_preserves_forwarded_arguments_and_baseline_mode_defaults() -> Result<(), TaskError>
{
    let options = options(&["--", "--seed", "42", "--fuzz", "7"].map(str::to_owned))?;
    let mut command = Command::new("python3");
    configure_mode(&mut command, "fuzz-argparse", &options)?;
    assert_eq!(
        command.get_args().collect::<Vec<_>>(),
        ["--fuzz", "3000", "--seed", "42", "--fuzz", "7"]
    );
    let mut command = Command::new("python3");
    configure_mode(&mut command, "check-argparse", &options)?;
    assert_eq!(
        command.get_args().collect::<Vec<_>>(),
        ["--seed", "42", "--fuzz", "7"]
    );
    let mut command = Command::new("python3");
    configure_mode(&mut command, "check-argparse", &Options::default())?;
    assert_eq!(command.get_args().collect::<Vec<_>>(), ["--check"]);
    Ok(())
}

#[test]
fn check_failures_combine_so_drift_does_not_hide_the_replay() {
    let failed = |message: &str| Err(deps::error(message));
    let combined = |results| combine(results).map_err(|error| error.to_string());
    assert_eq!(combined([Ok(()), Ok(())]), Ok(()));
    assert_eq!(
        combined([
            failed("argument table drift: command \"python3\" failed with exit status: 1"),
            failed("corpus replay: command \"python3\" failed with exit status: 1"),
        ]),
        Err(
            "argument table drift: command \"python3\" failed with exit status: 1\n\
             corpus replay: command \"python3\" failed with exit status: 1"
                .to_owned()
        )
    );
    assert_eq!(
        combined([Ok(()), failed("corpus replay: diverged")]),
        Err("corpus replay: diverged".to_owned())
    );
    let drift = combine([Err(TaskError::Io(io::Error::other("drift"))), Ok(())]);
    assert!(matches!(drift, Err(TaskError::Io(error)) if error.to_string() == "drift"));
}
