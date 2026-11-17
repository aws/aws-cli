use super::*;
#[test]
fn analysis_modes_reject_conflicting_or_unknown_options() {
    assert!(options(&["--miri".into(), "--sanitize-thread".into()]).is_err());
    assert!(options(&["--target".into(), "aarch64-apple-darwin".into()]).is_err());
    // One configuration builds every test, so no mode selects the native code.
    for removed in ["--native", "--crt", "--python"] {
        assert_eq!(
            failure(options(&[removed.into()])),
            format!("unknown test option: {removed}")
        );
    }
}
#[test]
fn explicit_packages_remain_within_the_analysis_harness() -> Result<(), TaskError> {
    let result = options(&["--miri".into(), "-p".into(), "pyload".into()])?;
    assert_eq!(result.mode, Mode::Miri);
    assert_eq!(result.packages, ["pyload"]);
    assert!(packages(&["python-fallback".into()], &["pyload"]).is_err());
    Ok(())
}

#[test]
fn sanitizer_and_coverage_modes_reject_partial_or_ignored_options() -> Result<(), TaskError> {
    assert_eq!(
        options(&["--sanitize-c".into(), "full".into()])?.mode,
        Mode::C(sanitizers::CMode::Full)
    );
    assert!(options(&["--sanitize-c".into(), "off".into()]).is_err());
    assert!(options(&["--coverage".into(), "-p".into(), "s3".into()]).is_err());
    assert!(options(&["--miri".into(), "--profile".into(), "release".into()]).is_err());
    assert_eq!(
        options(&["--profile".into(), "release-small".into()])?.profile,
        "release-small"
    );
    Ok(())
}

#[test]
fn default_tsan_runs_one_instrumented_lib_command_per_package() -> Result<(), TaskError> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("workspace root missing"))?;
    let target = "x86_64-unknown-linux-gnu";
    let commands = thread_sanitizer_commands(root, &[], target, None)?;
    assert_eq!(commands.len(), THREAD_SANITIZER_PACKAGES.len());
    for (command, &package) in commands.iter().zip(THREAD_SANITIZER_PACKAGES) {
        let expected = [
            "+nightly-2026-08-28",
            "test",
            "--locked",
            "-Zbuild-std",
            "--target",
            target,
            "--lib",
            "-p",
            package,
        ];
        assert!(arguments(command).starts_with(&expected.map(String::from)));
        let environment = command.get_envs().collect::<Vec<_>>();
        assert!(environment.iter().any(|(name, value)| {
            *name == "RUSTFLAGS" && value.is_some_and(|value| value == "-Zsanitizer=thread")
        }));
        assert!(environment.iter().any(|(name, value)| {
            *name == "TSAN_OPTIONS" && value.is_some_and(|value| value == "halt_on_error=1")
        }));
    }

    let selected = thread_sanitizer_commands(root, &["cli-core".into()], target, None)?;
    assert_eq!(selected.len(), 1);
    assert!(
        selected[0]
            .get_args()
            .any(|argument| argument == std::ffi::OsStr::new("cli-core"))
    );
    // Linux TSan builds for glibc, which the C libraries are not built for.
    assert_eq!(
        THREAD_SANITIZER_PACKAGES.contains(&"crt"),
        !cfg!(target_os = "linux")
    );
    Ok(())
}

fn arguments(command: &Command) -> Vec<String> {
    command
        .get_args()
        .map(|argument| argument.to_string_lossy().into_owned())
        .collect()
}

fn failure<T>(result: Result<T, TaskError>) -> String {
    result
        .err()
        .map(|failure| failure.to_string())
        .unwrap_or_default()
}

#[test]
fn filter_option_keeps_its_value_in_every_test_mode() -> Result<(), TaskError> {
    let selected = options(&["--filter".into(), "scheduler".into()])?;
    assert_eq!(selected.mode, Mode::Workspace);
    assert_eq!(selected.filter.as_deref(), Some("scheduler"));
    assert_eq!(options(&[])?.filter, None);
    assert_eq!(
        failure(options(&["--filter".into()])),
        "--filter requires a value"
    );
    let repeated = ["--filter", "a", "--filter", "b"].map(String::from);
    assert_eq!(failure(options(&repeated)), "--filter may be given once");
    // `--filter` also selects the tests a `--coverage` run collects.
    let coverage = options(&["--coverage", "--filter", "scheduler"].map(String::from))?;
    assert_eq!(coverage.mode, Mode::Coverage);
    assert_eq!(coverage.filter.as_deref(), Some("scheduler"));
    assert_eq!(
        failure(options(&["--miri".into(), "scheduler".into()])),
        "select one test mode"
    );
    assert_eq!(
        failure(options(&["--test-filter".into(), "scheduler".into()])),
        "unknown test option: --test-filter"
    );
    Ok(())
}

#[test]
fn cargo_test_modes_forward_the_filter_after_their_test_arguments() -> Result<(), TaskError> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("workspace root missing"))?;
    let selected = options(&[
        "-p".into(),
        "s3".into(),
        "--filter".into(),
        "scheduler".into(),
    ])?;
    assert_eq!(
        arguments(&workspace_command(root, &selected)),
        [
            "test",
            "--locked",
            "--profile",
            "dev",
            "--target",
            deps::TARGET,
            "-p",
            "s3",
            "--",
            "scheduler"
        ]
    );
    let unfiltered = arguments(&workspace_command(root, &options(&[])?));
    assert!(unfiltered.contains(&"--workspace".into()));
    assert!(!unfiltered.contains(&"--".into()));

    let numa = miri_commands(root, &["numa".into()], Some("scheduler"))?;
    assert!(arguments(&numa[0]).ends_with(&["--".into(), "scheduler".into()]));
    let s3 = miri_commands(root, &["s3".into()], Some("download::io::tests::x"))?;
    let skips = S3_MIRI_EXCLUSIONS.iter().flat_map(|name| ["--skip", name]);
    let expected = std::iter::once("--")
        .chain(skips)
        .chain(["download::io::tests::x"]);
    let expected = expected.map(String::from).collect::<Vec<_>>();
    assert!(arguments(&s3[0]).ends_with(&expected));
    Ok(())
}

#[test]
fn default_miri_runs_only_the_packages_that_reach_unsafe_code() -> Result<(), TaskError> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("workspace root missing"))?;
    let selected = |commands: &[Command]| {
        commands
            .iter()
            .filter_map(|command| {
                let arguments = arguments(command);
                let package = arguments.iter().position(|argument| argument == "-p")?;
                arguments.get(package + 1).cloned()
            })
            .collect::<Vec<_>>()
    };
    assert_eq!(
        selected(&miri_commands(root, &[], None)?),
        MIRI_DEFAULT_PACKAGES
    );
    // A package without unsafe code still runs whole when named.
    let config = miri_commands(root, &["awscli-config".into()], None)?;
    assert!(arguments(&config[0]).ends_with(&["-p".into(), "awscli-config".into()]));
    Ok(())
}

#[test]
fn fixed_package_filters_accept_only_narrower_filters() -> Result<(), TaskError> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("workspace root missing"))?;
    let crt = ["crt".to_owned()];
    let fixed = MIRI_FILTERS
        .iter()
        .find(|(package, _)| *package == "crt")
        .map(|(_, fixed)| *fixed)
        .ok_or_else(|| error("crt filters missing"))?;
    let every = ["-p", "crt", "--"].into_iter().chain(fixed.iter().copied());
    let every = every.map(String::from).collect::<Vec<_>>();
    assert!(arguments(&miri_commands(root, &crt, None)?[0]).ends_with(&every));
    for filter in ["source_pool::tests::reuse", fixed[1]] {
        let narrowed = miri_commands(root, &crt, Some(filter))?;
        let narrowed = arguments(&narrowed[0]);
        assert!(narrowed.ends_with(&["-p", "crt", "--", filter].map(String::from)));
    }
    // A filter wider than the fixed ones would select tests outside them.
    let wider = failure(miri_commands(root, &["s3".into()], Some("download::")));
    assert!(wider.starts_with(
        "Miri runs only the s3 tests matching download::platform::tests:: or download::io::tests::"
    ));
    assert!(wider.contains("; --filter download:: must contain download::platform::tests:: or "));
    // Without -p, the filter must fit every filtered package, from the first.
    assert!(
        failure(miri_commands(root, &[], Some("source_pool::")))
            .starts_with("Miri runs only the pyload tests matching swiss_group:: or ")
    );
    Ok(())
}

#[test]
fn fixed_tsan_filters_accept_only_narrower_filters() -> Result<(), TaskError> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| error("workspace root missing"))?;
    let crt = ["crt".to_owned()];
    let target = "x86_64-unknown-linux-gnu";
    let tsan = |requested: &[String], filter| {
        failure(thread_sanitizer_commands(
            root,
            requested,
            target,
            Some(filter),
        ))
    };
    assert!(
        tsan(&[], "scheduler")
            .starts_with("TSan runs only the cli-core tests matching interrupt::concurrency;")
    );
    if THREAD_SANITIZER_PACKAGES.contains(&"crt") {
        assert!(
            tsan(&crt, "scheduler")
                .starts_with("TSan runs only the crt tests matching source_pool::;")
        );
        let s3 = thread_sanitizer_commands(root, &["s3".into()], target, Some("scheduler"))?;
        assert!(arguments(&s3[0]).ends_with(&["--".into(), "scheduler".into()]));
    } else {
        assert_eq!(
            tsan(&crt, "source_pool::"),
            "crt is outside this analysis harness"
        );
    }
    let cli_core = ["cli-core".to_owned()];
    assert!(
        tsan(&cli_core, "source_pool")
            .starts_with("TSan runs only the cli-core tests matching interrupt::concurrency;")
    );
    let narrowed = thread_sanitizer_commands(
        root,
        &cli_core,
        target,
        Some("interrupt::concurrency::tests::x"),
    )?;
    assert!(arguments(&narrowed[0]).ends_with(&["interrupt::concurrency::tests::x".into()]));
    Ok(())
}
