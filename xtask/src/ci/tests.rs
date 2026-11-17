use super::*;

/// No forwarded options: every child builds the default static configuration.
fn defaults() -> Forwarded {
    Forwarded {
        build: Vec::new(),
        target: deps::TARGET.to_owned(),
        blackbox: Vec::new(),
    }
}

#[test]
fn every_product_child_forbids_dependency_builds_and_preserves_home() {
    for arguments in product_commands_for(Host::current(), &defaults()) {
        let command = product_command(Path::new("/workspace"), &arguments);
        let environment = command.get_envs().collect::<Vec<_>>();
        assert_eq!(
            environment,
            [(
                std::ffi::OsStr::new("AWSCLI_FORBID_EXPENSIVE_BUILDS"),
                Some(std::ffi::OsStr::new("1"))
            )]
        );
        assert_eq!(command.get_program(), "cargo");
    }
}

#[test]
fn product_checks_both_profiles_before_local_only_parity_and_fuzz() {
    let commands = product_commands_for(Host::Linux, &defaults());
    assert!(contains(&commands, &["xtask", "test"]));
    assert!(contains(
        &commands,
        &["xtask", "test", "--profile", "release-safe"]
    ));
    assert!(contains(
        &commands,
        &[
            "xtask",
            "test",
            "--sanitize-c",
            "full",
            "--profile",
            "release-safe"
        ]
    ));
    assert!(contains(
        &commands,
        &[
            "xtask",
            "integ",
            "--aws-binary",
            &artifact(deps::TARGET, "release-safe"),
            "--",
            "--collect-only"
        ]
    ));
    assert!(contains(&commands, &["xtask", "fuzz", "--runs", "1000"]));
}

#[test]
fn platform_matrix_keeps_linux_tools_off_other_native_hosts() {
    for host in [Host::Linux, Host::Macos, Host::Windows] {
        let commands = product_commands_for(host, &defaults());
        let has = |name: &str| {
            commands
                .iter()
                .any(|command| command.iter().any(|argument| argument == name))
        };
        assert_eq!(has("--sanitize-c"), host == Host::Linux);
        assert_eq!(has("fuzz"), host != Host::Windows);
        assert!(has("fuzz-argparse"));
        assert!(has("check-argparse"));
        assert!(has("harness-test"));
        assert!(contains(
            &commands,
            &["xtask", "test", "--profile", "release-safe"]
        ));
        assert!(has("--collect-only"));
    }
}

#[test]
fn product_restores_the_release_artifact_after_tests_before_harnesses() -> Result<(), TaskError> {
    let artifact_path = artifact(deps::TARGET, "release-safe");
    for host in [Host::Linux, Host::Macos, Host::Windows] {
        let commands = product_commands_for(host, &defaults());
        let release = position(&commands, &["xtask", "build", "--profile", "release-safe"])?;
        let blackbox = position(
            &commands,
            &["xtask", "blackbox", "--aws-binary", &artifact_path],
        )?;
        assert!(
            release < blackbox,
            "blackbox must use the restored release product"
        );
        assert!(
            commands.iter().enumerate().all(|(index, command)| {
                command.get(1).is_none_or(|name| name != "test") || index < release
            }),
            "all test builds must precede the release product consumed by later harnesses"
        );
    }
    Ok(())
}

#[test]
fn blackbox_runs_the_release_product_in_main_order() -> Result<(), TaskError> {
    let release = artifact(deps::TARGET, "release-safe");
    for &host in ALL {
        let commands = product_commands_for(host, &defaults());
        let blackbox = position(&commands, &["xtask", "blackbox", "--aws-binary", &release])?;
        let argparse = position(&commands, &["xtask", "check-argparse"])?;
        assert!(blackbox < argparse);
    }
    Ok(())
}

fn position(commands: &[Vec<String>], expected: &[&str]) -> Result<usize, TaskError> {
    commands
        .iter()
        .position(|command| {
            command
                .iter()
                .map(String::as_str)
                .eq(expected.iter().copied())
        })
        .ok_or_else(|| deps::error(format!("missing CI command: {}", expected.join(" "))))
}

fn contains(commands: &[Vec<String>], expected: &[&str]) -> bool {
    commands.iter().any(|command| {
        command
            .iter()
            .map(String::as_str)
            .eq(expected.iter().copied())
    })
}

const ALL: &[Host] = &[Host::Linux, Host::Macos, Host::Windows];
const LINUX: &[Host] = &[Host::Linux];
const UNIX: &[Host] = &[Host::Linux, Host::Macos];

/// Each Rust product command with its lane and hosts (`{release}` names the
/// built artifact).
const LANE_TABLE: &[(Lane, &[Host], &[&str])] = &[
    (Lane::Checks, ALL, &["xtask", "lint"]),
    (Lane::Checks, ALL, &["xtask", "test"]),
    (
        Lane::Checks,
        ALL,
        &["xtask", "test", "--profile", "release-safe"],
    ),
    (Lane::Checks, ALL, &["xtask", "harness-test"]),
    (Lane::Checks, LINUX, &SANITIZED_TEST),
    (Lane::Runtime, ALL, &RELEASE_BUILD),
    (
        Lane::Runtime,
        ALL,
        &["xtask", "blackbox", "--aws-binary", "{release}"],
    ),
    (
        Lane::Runtime,
        ALL,
        &[
            "xtask",
            "blackbox",
            "--aws-binary",
            "{release}",
            "--suite",
            "repo",
            "--env",
            "AWS_CLI_NATIVE_ROUTER=python",
        ],
    ),
    (Lane::Checks, ALL, &["xtask", "check-argparse"]),
    (Lane::Checks, ALL, &["xtask", "fuzz-argparse"]),
    (Lane::Checks, UNIX, &["xtask", "fuzz", "--runs", "1000"]),
    (
        Lane::Runtime,
        ALL,
        &[
            "xtask",
            "integ",
            "--aws-binary",
            "{release}",
            "--",
            "--collect-only",
        ],
    ),
];

const LANES: [Lane; 2] = [Lane::Runtime, Lane::Checks];

fn expected_inventory(host: Host) -> Vec<(Lane, Vec<String>)> {
    let release = artifact(deps::TARGET, "release-safe");
    LANE_TABLE
        .iter()
        .filter(|(_, hosts, _)| hosts.contains(&host))
        .map(|(lane, _, arguments)| {
            let arguments = arguments
                .iter()
                .map(|argument| match *argument {
                    "{release}" => release.clone(),
                    other => other.to_owned(),
                })
                .collect();
            (*lane, arguments)
        })
        .collect()
}

#[test]
fn lane_table_matches_main_lane_and_host_assignment() {
    for &host in ALL {
        let actual = lane_inventory_for(host, &defaults())
            .into_iter()
            .map(|command| (command.lane, command.arguments))
            .collect::<Vec<_>>();
        assert_eq!(actual, expected_inventory(host));
    }
}

#[test]
fn lanes_partition_product_in_order() {
    for &host in ALL {
        let product = product_commands_for(host, &defaults());
        let partitions = LANES.map(|lane| partition_for(host, lane, &defaults()));
        for command in &product {
            let owners = partitions
                .iter()
                .filter(|partition| partition.contains(command))
                .count();
            assert_eq!(owners, 1, "{command:?} must belong to exactly one lane");
        }
        // Each partition is a subsequence of product, so merging them in
        // product order reproduces product exactly.
        let mut cursors = [0; LANES.len()];
        let mut merged = Vec::new();
        for command in &product {
            for (cursor, partition) in cursors.iter_mut().zip(&partitions) {
                if partition.get(*cursor) == Some(command) {
                    merged.push(command.clone());
                    *cursor += 1;
                }
            }
        }
        assert_eq!(merged, product);
        assert_eq!(
            partitions.iter().map(Vec::len).sum::<usize>(),
            product.len()
        );
    }
}

#[test]
fn phases_select_product_or_one_lane_and_reject_others() {
    let commands =
        |host, name| Phase::parse(name).map(|phase| phase_commands_for(host, phase, &defaults()));
    for &host in ALL {
        assert_eq!(
            commands(host, "product"),
            Some(product_commands_for(host, &defaults()))
        );
        for (name, lane) in [("runtime", Lane::Runtime), ("checks", Lane::Checks)] {
            assert_eq!(
                commands(host, name),
                Some(partition_for(host, lane, &defaults()))
            );
        }
        for name in ["deps", "lanes", "", "Product", "functional"] {
            assert_eq!(commands(host, name), None);
        }
    }
}

#[test]
fn missing_unknown_or_extra_phase_arguments_print_the_usage() {
    let usage = |args: &[&str]| {
        run(Path::new("/workspace"), &owned(args)).map_err(|error| error.to_string())
    };
    let expected = Err(USAGE.to_owned());
    assert_eq!(usage(&[]), expected);
    assert_eq!(usage(&["lanes"]), expected);
    // `deps` prepares the default dependency outputs and takes no options.
    assert_eq!(usage(&["deps", "--cpu", "baseline"]), expected);
    assert_eq!(
        usage(&["runtime", "checks"]),
        Err(format!("unexpected CI argument: checks\n{USAGE}"))
    );
}

/// Every command of every lane on every host, with `forwarded`.
fn every_command(forwarded: &Forwarded) -> Vec<Vec<String>> {
    ALL.iter()
        .flat_map(|&host| LANES.map(|lane| partition_for(host, lane, forwarded)))
        .flatten()
        .collect()
}

fn without_builds(commands: Vec<Vec<String>>) -> Vec<Vec<String>> {
    let build = owned(&["xtask", "build"]);
    commands
        .into_iter()
        .filter(|command| !command.starts_with(&build))
        .collect()
}

#[test]
fn forwarded_options_reach_every_build_child_and_no_other() -> Result<(), TaskError> {
    let options = owned(&[
        "--cpu",
        "baseline",
        "--python-pgo=false",
        "--strip",
        "false",
    ]);
    let forwarded = Forwarded::parse(&options)?;
    assert_eq!(forwarded.build, options);
    assert_eq!(forwarded.target, deps::TARGET);
    assert!(
        forwarded.blackbox.is_empty(),
        "a static build needs no blackbox options"
    );
    let build = owned(&["xtask", "build"]);
    for command in every_command(&forwarded) {
        assert_eq!(
            command.ends_with(&options),
            command.starts_with(&build),
            "{command:?}"
        );
        let profiles = command.iter().filter(|word| *word == "--profile").count();
        assert!(
            profiles <= 1,
            "{command:?} must keep its own --profile only"
        );
    }
    assert_eq!(
        without_builds(every_command(&forwarded)),
        without_builds(every_command(&defaults()))
    );
    Ok(())
}

#[test]
fn system_blackbox_options_describe_the_system_build() -> Result<(), TaskError> {
    let mut options = build_options::parse(&[])?;
    options.link_mode = LinkMode::System;
    options.python_exe = "/usr/bin/python3.14".into();
    assert_eq!(
        blackbox_options(&options),
        owned(&[
            "--link-mode",
            "system",
            "--python-exe",
            "/usr/bin/python3.14"
        ])
    );
    options.crt_static_prefix = Some("/crt".into());
    options.python_payload = PythonPayload::System;
    options.python_exe = "/opt/python/bin/python3".into();
    assert_eq!(
        blackbox_options(&options),
        owned(&[
            "--link-mode",
            "system",
            "--crt-link",
            "static",
            "--python-payload",
            "system",
            "--python-exe",
            "/opt/python/bin/python3",
        ])
    );
    options.link_mode = LinkMode::Static;
    assert!(blackbox_options(&options).is_empty());
    Ok(())
}

#[test]
fn forwarded_target_selects_every_harness_artifact() -> Result<(), TaskError> {
    let target = "x86_64-unknown-linux-gnu";
    let forwarded = Forwarded {
        build: owned(&["--link-mode", "system"]),
        target: target.to_owned(),
        blackbox: owned(&["--link-mode", "system"]),
    };
    let commands = product_commands_for(Host::Linux, &forwarded);
    let release = artifact(target, "release-safe");
    for expected in [
        vec![
            "xtask",
            "blackbox",
            "--aws-binary",
            &release,
            "--link-mode",
            "system",
        ],
        vec![
            "xtask",
            "blackbox",
            "--aws-binary",
            &release,
            "--suite",
            "repo",
            "--env",
            "AWS_CLI_NATIVE_ROUTER=python",
            "--link-mode",
            "system",
        ],
        vec![
            "xtask",
            "integ",
            "--aws-binary",
            &release,
            "--",
            "--collect-only",
        ],
        vec![
            "xtask",
            "build",
            "--profile",
            "release-safe",
            "--link-mode",
            "system",
        ],
    ] {
        position(&commands, &expected)?;
    }
    Ok(())
}

/// A product phase's host check follows the forwarded link mode, through
/// the build option parser: the static host list for static options, and
/// `product::system_target` for `--link-mode system`, whose artifacts then
/// live under the native rustc's glibc triple.
#[test]
fn forwarded_link_mode_selects_the_host_check() {
    let message = |error: TaskError| error.to_string();
    let static_options = Forwarded::parse(&[]).map(|forwarded| forwarded.target);
    assert_eq!(
        static_options.map_err(message),
        deps::native_host()
            .map(|()| deps::TARGET.to_owned())
            .map_err(message)
    );
    let system_options =
        Forwarded::parse(&owned(&["--link-mode", "system"])).map(|forwarded| forwarded.target);
    assert_eq!(
        system_options.map_err(message),
        crate::product::system_target().map_err(message)
    );
}

#[test]
fn phase_errors_come_before_the_options_and_their_host_check() {
    let outcome = |args: &[&str]| {
        run(Path::new("/workspace"), &owned(args)).map_err(|error| error.to_string())
    };
    for args in [
        &["lanes", "--link-mode", "system"][..],
        &["deps", "--link-mode", "system"][..],
        &["Product"][..],
    ] {
        assert_eq!(outcome(args), Err(USAGE.to_owned()), "{args:?}");
    }
}

#[test]
fn sequence_owned_and_unknown_options_are_usage_errors() {
    let refused = |args: &[&str]| Forwarded::parse(&owned(args)).map_err(|error| error.to_string());
    for (args, message) in [
        (
            &["--profile", "dev"][..],
            "--profile is set by each CI command",
        ),
        (
            &["--profile=dev"][..],
            "--profile is set by each CI command",
        ),
        (
            &["--sanitize-c", "full"][..],
            "--sanitize-c is set by each CI command",
        ),
        (&["--cpu"][..], "--cpu needs a value"),
        (&["--bogus", "x"][..], "invalid build option: --bogus=x"),
        (&["baseline"][..], "unexpected CI argument: baseline"),
    ] {
        assert_eq!(refused(args), Err(message.to_owned()), "{args:?}");
    }
    assert_eq!(
        run(Path::new("/workspace"), &owned(&["checks", "--bogus=x"]))
            .map_err(|error| error.to_string()),
        Err(format!("invalid build option: --bogus=x\n{USAGE}"))
    );
}

#[test]
fn failed_child_error_names_every_argument() {
    for command in product_commands_for(Host::Linux, &defaults()) {
        let message = failure(&label(&command), &"exit status: 101").to_string();
        assert_eq!(
            message,
            format!(
                "ci command failed: cargo {}: exit status: 101",
                command.join(" ")
            )
        );
    }
}
