use std::ffi::OsStr;
use std::path::PathBuf;

use super::*;

const ROOT: &str = "/workspace";

fn blackbox_command(args: &[&str]) -> Result<Command, TaskError> {
    let args: Vec<_> = args.iter().map(|&arg| arg.to_owned()).collect();
    let options = options::parse(&args)?;
    Ok(command(
        Path::new(ROOT),
        Path::new("/rust/aws"),
        Path::new("/pinned/aws-cli"),
        &options,
        &build_args(Path::new(ROOT), &options.build)?,
    ))
}

fn under_root(path: &str) -> PathBuf {
    Path::new(ROOT).join(path)
}

/// A binary's report directory, its name joined with the host separator as
/// `junit_dir` joins it.
fn report_dir(binary: &str) -> PathBuf {
    under_root("target/blackbox/junit").join(binary)
}

#[test]
fn default_run_uses_the_copied_runner_without_the_router_variable() -> Result<(), TaskError> {
    let command = blackbox_command(&[])?;
    assert_eq!(command.get_program(), "python3");
    assert_eq!(command.get_current_dir(), Some(Path::new(ROOT)));
    let runner = under_root("tests/blackbox/run.py");
    let known_gaps = under_root("tests/blackbox/failures.txt");
    let upstream_failures = under_root("tests/blackbox/upstream-failures.txt");
    let cache = under_root("target/blackbox");
    let junit = report_dir("built");
    let expected: [&OsStr; 16] = [
        "-B".as_ref(),
        runner.as_ref(),
        "--aws-binary".as_ref(),
        "/rust/aws".as_ref(),
        "--binary-kind".as_ref(),
        "built".as_ref(),
        "--known-gaps".as_ref(),
        known_gaps.as_ref(),
        "--upstream-failures".as_ref(),
        upstream_failures.as_ref(),
        "--aws-cli-source".as_ref(),
        "/pinned/aws-cli".as_ref(),
        "--cache-dir".as_ref(),
        cache.as_ref(),
        "--junit-dir".as_ref(),
        junit.as_ref(),
    ];
    assert_eq!(command.get_args().collect::<Vec<_>>(), expected);
    // The binary runs in its default configuration, so the router variable
    // is removed; HOME and the ledger variable stay the caller's and the
    // runner's to decide.
    assert_eq!(
        command.get_envs().collect::<Vec<_>>(),
        [(OsStr::new("AWS_CLI_NATIVE_ROUTER"), None)]
    );
    Ok(())
}

#[test]
fn run_all_and_selection_reach_the_runner_unchanged() -> Result<(), TaskError> {
    let command = blackbox_command(&[
        "--run-all",
        "--",
        "-k",
        "test_ls",
        "tests/blackbox/test_ls_command.py",
    ])?;
    let junit = report_dir("built");
    let expected: [&OsStr; 6] = [
        "--run-all".as_ref(),
        "--junit-dir".as_ref(),
        junit.as_ref(),
        "-k".as_ref(),
        "test_ls".as_ref(),
        "tests/blackbox/test_ls_command.py".as_ref(),
    ];
    assert_eq!(command.get_args().skip(14).collect::<Vec<_>>(), expected);
    Ok(())
}

/// Each assignment reaches run.py, which hands it to the commands alone:
/// pytest's own environment keeps no router variable.
#[test]
fn env_assignments_reach_the_runner_for_either_binary() -> Result<(), TaskError> {
    for binary in [
        &["--aws-binary", "target/aws"][..],
        &["--external-binary", "/usr/bin/aws"],
    ] {
        let mut args = binary.to_vec();
        args.extend([
            "--env",
            "AWS_CLI_NATIVE_ROUTER=python",
            "--env",
            "AWS_CA_BUNDLE=a=b",
            "--",
            "-x",
        ]);
        let command = blackbox_command(&args)?;
        let actual: Vec<_> = command.get_args().collect();
        let start = actual
            .iter()
            .position(|&argument| argument == "--env")
            .ok_or_else(|| deps::error(format!("no --env in {actual:?}")))?;
        let expected: [&OsStr; 5] = [
            "--env".as_ref(),
            "AWS_CLI_NATIVE_ROUTER=python".as_ref(),
            "--env".as_ref(),
            "AWS_CA_BUNDLE=a=b".as_ref(),
            "--junit-dir".as_ref(),
        ];
        assert_eq!(actual[start..start + 5], expected, "{binary:?}");
        assert_eq!(
            command.get_envs().collect::<Vec<_>>(),
            [(OsStr::new("AWS_CLI_NATIVE_ROUTER"), None)],
            "{binary:?}"
        );
    }
    Ok(())
}

#[test]
fn external_binary_drops_the_known_gaps_and_runs_as_external() -> Result<(), TaskError> {
    let built = blackbox_command(&["--aws-binary", "target/aws", "--", "-x"])?;
    let external = blackbox_command(&["--external-binary", "/usr/bin/aws", "--", "-x"])?;
    assert_eq!(
        external.get_envs().collect::<Vec<_>>(),
        built.get_envs().collect::<Vec<_>>()
    );
    // The runner skips the `native_only` tests for an external binary.
    let expected: Vec<_> = built
        .get_args()
        .filter(|&argument| {
            argument != "--known-gaps" && argument != under_root("tests/blackbox/failures.txt")
        })
        .map(|argument| {
            if argument == report_dir("built") {
                report_dir("external").into_os_string()
            } else if argument == "built" {
                "external".into()
            } else {
                argument.to_owned()
            }
        })
        .collect();
    assert_eq!(
        external.get_args().collect::<Vec<_>>(),
        expected
            .iter()
            .map(|argument| argument.as_os_str())
            .collect::<Vec<_>>()
    );
    Ok(())
}

#[test]
fn each_session_reports_into_the_binary_directory() {
    assert_eq!(
        reports(Path::new(ROOT), &Options::default()),
        [
            ("upstream", report_dir("built").join("upstream.xml")),
            ("repo", report_dir("built").join("repo.xml")),
        ]
    );
    let external = Options {
        binary: Binary::External("/usr/bin/aws".to_owned()),
        ..Options::default()
    };
    assert_eq!(
        reports(Path::new(ROOT), &external),
        [
            ("upstream", report_dir("external").join("upstream.xml")),
            ("repo", report_dir("external").join("repo.xml")),
        ]
    );
}

/// A run of one suite passes it to run.py and verifies only its report.
#[test]
fn a_single_suite_reaches_the_runner_and_alone_reports() -> Result<(), TaskError> {
    for (suite, session) in [
        (options::Suite::Upstream, "upstream"),
        (options::Suite::Repo, "repo"),
    ] {
        let command = blackbox_command(&["--suite", session, "--run-all", "--", "-x"])?;
        let expected: [&OsStr; 4] = [
            "--suite".as_ref(),
            session.as_ref(),
            "--run-all".as_ref(),
            "--junit-dir".as_ref(),
        ];
        assert_eq!(
            command.get_args().skip(14).take(4).collect::<Vec<_>>(),
            expected
        );
        let options = Options {
            suite,
            ..Options::default()
        };
        assert_eq!(
            reports(Path::new(ROOT), &options),
            [(session, report_dir("built").join(format!("{session}.xml")))]
        );
    }
    Ok(())
}

#[test]
fn listing_options_skip_report_verification_but_selections_keep_it() {
    let runs =
        |args: &[&str]| runs_tests(&args.iter().map(|&arg| arg.to_owned()).collect::<Vec<_>>());
    for listing in [
        &["--collect-only"][..],
        &["-q", "--co"],
        &["-h"],
        &["--help"],
        &["--fixtures"],
        &["--fixtures-per-test"],
        &["--markers"],
        &["--version"],
    ] {
        assert!(!runs(listing), "{listing:?}");
    }
    assert!(runs(&[]));
    assert!(runs(&["-k", "foo", "-q"]));
    assert!(runs(&["tests/blackbox/tests/s3", "-x"]));
}

/// Options come first, and an explicit binary takes no host check: checking
/// that the binary exists is the first thing `run` does with it.
#[test]
fn explicit_binary_is_checked_before_any_harness_step() {
    let args = ["--aws-binary", "/absent/aws", "--run-all"].map(str::to_owned);
    assert_eq!(
        run(Path::new(ROOT), &args).map_err(|error| error.to_string()),
        Err("Rust CLI is absent: /absent/aws; build it or supply --aws-binary".to_owned())
    );
    let args = ["--external-binary", "/absent/aws", "--run-all"].map(str::to_owned);
    assert_eq!(
        run(Path::new(ROOT), &args).map_err(|error| error.to_string()),
        Err("external AWS CLI is absent: /absent/aws".to_owned())
    );
}

/// A system build's facts follow the binary kind; the static build, which
/// run.py assumes, adds none.
#[test]
fn a_system_build_describes_itself_to_the_runner() -> Result<(), TaskError> {
    let command = blackbox_command(&[
        "--aws-binary",
        "target/aws",
        "--link-mode",
        "system",
        "--crt-link",
        "static",
        "--python-payload",
        "system",
    ])?;
    let expected: [&OsStr; 10] = [
        "--binary-kind".as_ref(),
        "built".as_ref(),
        "--link-mode".as_ref(),
        "system".as_ref(),
        "--crt-link".as_ref(),
        "static".as_ref(),
        "--python-payload".as_ref(),
        "system".as_ref(),
        "--python-abi".as_ref(),
        PYTHON_ABI.as_ref(),
    ];
    let actual: Vec<_> = command.get_args().collect();
    assert_eq!(actual[4..14], expected);
    let command = blackbox_command(&["--aws-binary", "target/aws", "--link-mode", "static"])?;
    assert!(
        !command
            .get_args()
            .any(|argument| argument == "--link-mode" || argument == "--python-abi")
    );
    Ok(())
}

/// A named system Python reports its own ABI; without one the build used
/// the pinned ABI's interpreter.
#[test]
fn the_python_abi_comes_from_the_named_interpreter() -> Result<(), TaskError> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let abi = python_abi(root, Some(Path::new("python3")))?;
    assert!(abi.starts_with("python3."), "{abi}");
    assert_eq!(python_abi(root, None)?, PYTHON_ABI);
    Ok(())
}

/// A relative interpreter resolves under the root, as the build's
/// discovery resolves it, not under the directory the tests run in.
#[cfg(unix)]
#[test]
fn a_relative_python_resolves_under_the_root() -> Result<(), TaskError> {
    let output = process::output(Command::new("python3").args([
        "-I",
        "-c",
        "import sys; print(sys.executable)",
    ]))?;
    let executable = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim());
    let (Some(root), Some(name)) = (executable.parent(), executable.file_name()) else {
        return Err(deps::error(format!(
            "python3 reported no executable: {}",
            executable.display()
        )));
    };
    let abi = python_abi(root, Some(&Path::new(".").join(name)))?;
    assert!(abi.starts_with("python3."), "{abi}");
    Ok(())
}
