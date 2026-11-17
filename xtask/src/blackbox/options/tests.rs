use super::*;

fn strings(args: &[&str]) -> Vec<String> {
    args.iter().map(|&arg| arg.to_owned()).collect()
}

#[test]
fn no_arguments_run_the_built_binary_with_its_ledger() -> Result<(), TaskError> {
    let options = parse(&[])?;
    assert_eq!(options, Options::default());
    assert!(options.binary.is_built());
    assert_eq!(options.binary.report_name(), "built");
    assert!(options.artifact_args().is_empty());
    Ok(())
}

#[test]
fn own_options_precede_selection_forwarded_unchanged() -> Result<(), TaskError> {
    let options = parse(&strings(&[
        "--aws-binary",
        "target/aws",
        "--run-all",
        "--",
        "-k",
        "test_ls and not recursive",
        "tests/blackbox/test_ls_command.py::TestLSCommand",
        "-x",
        "-n",
        "4",
    ]))?;
    assert_eq!(options.binary, Binary::Explicit("target/aws".to_owned()));
    assert!(options.binary.is_built());
    assert!(options.run_all);
    assert_eq!(options.artifact_args(), ["--aws-binary", "target/aws"]);
    assert_eq!(
        options.forwarded,
        [
            "-k",
            "test_ls and not recursive",
            "tests/blackbox/test_ls_command.py::TestLSCommand",
            "-x",
            "-n",
            "4"
        ]
    );
    Ok(())
}

#[test]
fn an_external_binary_is_no_artifact_and_has_no_known_gaps() -> Result<(), TaskError> {
    let options = parse(&strings(&["--external-binary", "/usr/local/bin/aws"]))?;
    assert_eq!(
        options.binary,
        Binary::External("/usr/local/bin/aws".to_owned())
    );
    assert!(!options.binary.is_built());
    assert_eq!(options.binary.report_name(), "external");
    assert!(options.artifact_args().is_empty());
    Ok(())
}

#[test]
fn env_assignments_split_at_the_first_equals_in_order() -> Result<(), TaskError> {
    let options = parse(&strings(&[
        "--env",
        "AWS_CLI_NATIVE_ROUTER=python",
        "--external-binary",
        "/usr/local/bin/aws",
        "--env",
        "AWS_CA_BUNDLE=a=b",
        "--env",
        "AWS_PROFILE=",
        "--env",
        "AWS_CLI_NATIVE_ROUTER=native",
    ]))?;
    assert_eq!(
        options.binary,
        Binary::External("/usr/local/bin/aws".to_owned())
    );
    assert_eq!(
        options.env,
        [
            ("AWS_CLI_NATIVE_ROUTER", "python"),
            ("AWS_CA_BUNDLE", "a=b"),
            ("AWS_PROFILE", ""),
            ("AWS_CLI_NATIVE_ROUTER", "native"),
        ]
        .map(|(name, value)| (name.to_owned(), value.to_owned()))
    );
    Ok(())
}

#[test]
fn a_suite_selects_its_session_alone() -> Result<(), TaskError> {
    assert_eq!(Suite::default().sessions(), ["upstream", "repo"]);
    assert_eq!(Suite::default().runner_arg(), None);
    for (name, suite) in [("upstream", Suite::Upstream), ("repo", Suite::Repo)] {
        let options = parse(&strings(&["--suite", name, "--", "-x"]))?;
        assert_eq!(options.suite, suite);
        assert_eq!(options.suite.sessions(), [name]);
        assert_eq!(options.suite.runner_arg(), Some(name));
        assert_eq!(options.forwarded, ["-x"]);
    }
    Ok(())
}

#[test]
fn an_env_argument_without_equals_is_rejected() {
    assert_eq!(
        parse(&strings(&["--env", "AWS_CLI_NATIVE_ROUTER"])).map_err(|error| error.to_string()),
        Err("--env requires NAME=VALUE, not \"AWS_CLI_NATIVE_ROUTER\"".to_owned())
    );
}

#[test]
fn unknown_repeated_or_valueless_options_are_rejected() {
    for args in [
        &["-k", "test_ls"][..],
        &["--route", "python"],
        &["--aws-binary"],
        &["--external-binary"],
        &["--env"],
        &["--env=AWS_CLI_NATIVE_ROUTER=python"],
        &["--aws-binary", "a", "--aws-binary", "b"],
        &["--aws-binary", "a", "--external-binary", "b"],
        &["--external-binary", "a", "--aws-binary", "b"],
        &["--external-binary", "a", "--external-binary", "b"],
        &["--run-all", "--run-all"],
        &["--suite"],
        &["--suite", "all"],
        &["--suite=repo"],
        &["--suite", "repo", "--suite", "upstream"],
        &["--link-mode", "dynamic"],
        &["--link-mode", "system", "--link-mode", "system"],
        &["--crt-link", "unknown"],
        &["--python-payload", "unknown"],
        &["--python-exe"],
    ] {
        assert!(parse(&strings(args)).is_err(), "{args:?}");
    }
}

#[test]
fn the_build_is_static_unless_the_options_say_system() -> Result<(), TaskError> {
    let options = parse(&strings(&["--aws-binary", "target/aws"]))?;
    assert_eq!(options.build, Build::default());
    assert_eq!(options.build.link_mode, LinkMode::Static);
    assert_eq!(options.build.crt_link, CrtLink::Static);
    assert_eq!(options.build.payload, PythonPayload::Embedded);
    let options = parse(&strings(&[
        "--aws-binary",
        "target/aws",
        "--link-mode",
        "system",
        "--python-payload",
        "system",
    ]))?;
    assert_eq!(
        options.build,
        Build {
            link_mode: LinkMode::System,
            crt_link: CrtLink::Shared,
            payload: PythonPayload::System,
            python_exe: None,
        }
    );
    let options = parse(&strings(&[
        "--crt-link",
        "static",
        "--link-mode",
        "system",
        "--python-exe",
        "/usr/bin/python3.13",
    ]))?;
    assert_eq!(
        options.build,
        Build {
            link_mode: LinkMode::System,
            crt_link: CrtLink::Static,
            payload: PythonPayload::Embedded,
            python_exe: Some("/usr/bin/python3.13".into()),
        }
    );
    Ok(())
}

#[test]
fn the_static_build_and_another_aws_cli_refuse_system_options() {
    let refused = |args: &[&str]| parse(&strings(args)).map_err(|error| error.to_string());
    for (args, message) in [
        (
            &["--crt-link", "shared"][..],
            "shared CRT requires --link-mode system",
        ),
        (
            &["--link-mode", "static", "--python-payload", "system"],
            "system Python payload requires --link-mode system",
        ),
        (
            &["--python-exe", "python3"],
            "--python-exe requires --link-mode system",
        ),
    ] {
        assert_eq!(refused(args), Err(message.to_owned()), "{args:?}");
    }
    let error = refused(&["--external-binary", "/usr/bin/aws", "--link-mode", "static"]);
    assert!(
        error
            .as_ref()
            .is_err_and(|error| error.starts_with("another AWS CLI has no build options")),
        "{error:?}"
    );
}

#[test]
fn forwarded_arguments_cannot_replace_runner_inputs_or_report() {
    for arg in [
        "--aws-binary",
        "--aws-binary=/other",
        "--aws-cli-source",
        "--cache-dir=/tmp/cache",
        "--known-gaps",
        "--upstream-failures=/tmp/ledger.txt",
        "--run-all",
        "--suite",
        "--suite=repo",
        "--env",
        "--env=AWS_CLI_NATIVE_ROUTER=python",
        "--junit-dir=/tmp/reports",
        "--junitxml=/tmp/report.xml",
        "--junit-xml",
        "--link-mode=system",
        "--crt-link",
        "--python-payload",
        "--python-abi=python3.14",
    ] {
        assert!(parse(&strings(&["--", arg])).is_err(), "{arg}");
    }
    assert!(parse(&strings(&["--", "--junit-prefix=rust"])).is_ok());
}
