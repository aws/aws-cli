use super::*;

fn arguments(args: &[&str]) -> Vec<String> {
    args.iter().copied().map(str::to_owned).collect()
}

#[test]
fn default_campaign_matches_all_eleven_targets() -> Result<(), TaskError> {
    let options = options(&[])?;
    assert_eq!(options, Options::default());
    assert_eq!(budget_flags(&options), ["-runs=1000"]);
    assert_eq!(budget_text(&options), "1000 runs");
    assert_eq!(TARGETS.len(), 11);
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| deps::error("root"))?;
    for target in TARGETS {
        assert!(
            root.join("fuzz/fuzz_targets")
                .join(format!("{target}.rs"))
                .is_file()
        );
        assert!(
            fs::read_dir(root.join("fuzz/corpus").join(target))?
                .next()
                .is_some()
        );
    }
    Ok(())
}

#[test]
fn bounded_campaign_rejects_unlimited_budgets_and_unknown_options() {
    for args in [
        &["--runs", "0"][..],
        &["--runs", "-1"],
        &["--runs"],
        &["--time", "0"],
        &["--seed", "0"],
        &["--seed", "4294967296"],
        &["--target", "unknown"],
        &["--target"],
        &["--max_len", "10"],
        &["--merge", "--runs", "5"],
        &["--merge", "--seed", "5"],
    ] {
        assert!(options(&arguments(args)).is_err(), "{args:?}");
    }
}

#[test]
fn selected_campaign_retains_explicit_budget_and_seed() -> Result<(), TaskError> {
    let args = arguments(&["--runs", "42", "--target", "writer_retries", "--seed", "7"]);
    let options = options(&args)?;
    assert_eq!(
        options,
        Options {
            runs: Some(42),
            seed: Some(7),
            target: Some("writer_retries"),
            ..Options::default()
        }
    );
    assert_eq!(budget_flags(&options), ["-runs=42"]);
    let timed = options_with(&["--time", "300"])?;
    assert_eq!(budget_flags(&timed), ["-max_total_time=300"]);
    assert_eq!(budget_text(&timed), "300 seconds");
    let both = options_with(&["--time", "300", "--runs", "9"])?;
    assert_eq!(budget_flags(&both), ["-runs=9", "-max_total_time=300"]);
    assert_eq!(budget_text(&both), "9 runs or 300 seconds");
    let merge = options_with(&["--merge", "--target", "error_body"])?;
    assert!(merge.merge);
    Ok(())
}

fn options_with(args: &[&str]) -> Result<Options<'static>, TaskError> {
    let args: &'static [String] = Vec::leak(arguments(args));
    options(args)
}

#[test]
fn campaigns_bound_the_sanitizer_quarantine_unless_the_caller_sets_one() {
    assert_eq!(sanitizer_options(None), "quarantine_size_mb=16");
    assert_eq!(sanitizer_options(Some("")), "quarantine_size_mb=16");
    assert_eq!(
        sanitizer_options(Some("detect_leaks=0")),
        "detect_leaks=0:quarantine_size_mb=16"
    );
    let caller = "quarantine_size_mb=256:detect_leaks=0";
    assert_eq!(sanitizer_options(Some(caller)), caller);
}

#[test]
fn random_seeds_are_never_the_seed_libfuzzer_replaces() {
    for _ in 0..64 {
        assert!(random_seed() >= 1);
    }
}

/// One input decodes to one trace under libFuzzer and under `cargo test`
/// only while the fuzz package's lockfile and the workspace's pin the
/// `arbitrary` the workspace declares.
#[test]
fn fuzz_and_workspace_lockfiles_pin_the_declared_arbitrary() -> Result<(), TaskError> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| deps::error("root"))?;
    let read = |relative: &str| -> Result<toml::Value, TaskError> {
        toml::from_str(&fs::read_to_string(root.join(relative))?)
            .map_err(|error| deps::error(error.to_string()))
    };
    let manifest = read("Cargo.toml")?;
    let declared = manifest
        .get("workspace")
        .and_then(|workspace| workspace.get("dependencies"))
        .and_then(|dependencies| dependencies.get("arbitrary"))
        .and_then(toml::Value::as_str);
    let mut pins = Vec::new();
    for lockfile in ["Cargo.lock", "fuzz/Cargo.lock"] {
        let lock = read(lockfile)?;
        let packages = lock
            .get("package")
            .and_then(toml::Value::as_array)
            .ok_or_else(|| deps::error(format!("{lockfile} has no packages")))?;
        let arbitrary: Vec<_> = packages
            .iter()
            .filter(|package| {
                package.get("name").and_then(toml::Value::as_str) == Some("arbitrary")
            })
            .map(|package| {
                let field = |name| package.get(name).and_then(toml::Value::as_str);
                (
                    field("version").map(str::to_owned),
                    field("checksum").map(str::to_owned),
                )
            })
            .collect();
        assert_eq!(arbitrary.len(), 1, "{lockfile}");
        assert_eq!(
            declared.and_then(|pin| pin.strip_prefix('=')),
            arbitrary[0].0.as_deref(),
            "{lockfile}"
        );
        pins.extend(arbitrary);
    }
    assert_eq!(pins[0], pins[1]);
    Ok(())
}
