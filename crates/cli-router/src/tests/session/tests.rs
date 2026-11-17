use super::*;

fn evaluate_on(
    args: &[&str],
    env: &BTreeMap<String, String>,
    files: &ParsedFiles,
    platform: cli_core::client_config::Platform,
) -> Verdict {
    let argv = args.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>();
    let mut result = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    route_with_platform(
        &mut result,
        &unpack::Environment {
            directory: Path::new("."),
            variables: &HashMap::new(),
            files: &unpack::FsParamfiles,
            preferred_encoding: unpack::PreferredEncoding::Locale,
        },
        &Configuration {
            env,
            shared_files: files,
            boto_config_credentials: false,
            embedded_trust: true,
        },
        platform,
    )
}

fn assert_native(verdict: &Verdict, cp: bool) {
    let Verdict::Native(native) = verdict else {
        panic!("{verdict:?}")
    };
    assert_eq!(matches!(native.command, Command::S3Cp(_)), cp);
}

#[test]
fn a_plugins_section_hands_every_command_after_the_first_pass_to_python() {
    let env = BTreeMap::new();
    for text in [
        "[plugins]\ncli_legacy_plugin_path = /plugins\nmine = mine.plugin\n",
        "[plugins]\n",
    ] {
        let config = files(text);
        for argv in [
            &["s3", "ls", "s3://bucket"][..],
            &["s3", "cp", "a", "s3://b/k"],
            &["s3", "ls", "--bogus"],
            &["--output", "bogus", "s3", "ls"],
            &["--cli-auto-prompt", "--no-cli-auto-prompt", "s3"],
        ] {
            assert_eq!(
                evaluate(argv, &env, &config),
                Verdict::Python(PythonReason::Plugins),
                "{argv:?}"
            );
        }
        // The first pass fails before the CLI loads plugins.
        let first_pass = evaluate(&["ec2", "describe-instances", "--profile"], &env, &config);
        assert!(
            matches!(&first_pass, Verdict::Failure(failure) if failure.kind == "parse"),
            "{first_pass:?}"
        );
    }
    // A plugins key in a profile, or a profile named plugins, loads nothing.
    let profile = files("[default]\ncli_legacy_plugin_path = /plugins\n[profile plugins]\n");
    assert_native(
        &evaluate(&["s3", "ls", "s3://bucket"], &env, &profile),
        false,
    );
}

#[test]
fn a_streaming_transfer_runs_cp_natively_on_every_host() {
    let config = files(concat!(
        "[default]\ns3 =\n  should_stream = True\n",
        "[profile buffered]\ns3 =\n  should_stream = false\n",
    ));
    let env = BTreeMap::new();
    let tuned = cli_core::client_config::Platform {
        optimized: true,
        recommended_gbps: Some(100.0),
    };
    for platform in [cli_core::client_config::Platform::default(), tuned] {
        let streaming = evaluate_on(&["s3", "cp", "a", "s3://b/k"], &env, &config, platform);
        let Verdict::Native(native) = &streaming else {
            panic!("{streaming:?}")
        };
        assert!(
            native
                .client
                .should_stream
                .as_ref()
                .is_some_and(|v| v.value)
        );
        assert_native(&evaluate_on(&["s3", "ls"], &env, &config, platform), false);
        let buffered = ["--profile", "buffered", "s3", "cp", "a", "s3://b/k"];
        assert_native(&evaluate_on(&buffered, &env, &config, platform), true);
    }
}

#[test]
fn an_empty_region_from_any_source_is_python_s() {
    let config = files("[default]\nregion =\n[profile set]\nregion = eu-west-1\n");
    let ls = ["s3", "ls", "s3://bucket"];
    let set = ["--profile", "set", "s3", "cp", "a", "s3://b/k"];
    let flag = ["--region", "us-west-2", "s3", "ls"];
    let python = Verdict::Python(PythonReason::EndpointSetting);
    let mut env = BTreeMap::new();
    assert_eq!(evaluate(&ls, &env, &config), python);
    assert_native(&evaluate(&set, &env, &config), true);
    assert_native(&evaluate(&flag, &env, &config), false);
    env.insert("AWS_DEFAULT_REGION".to_owned(), String::new());
    assert_eq!(evaluate(&set, &env, &config), python);
    env.insert("AWS_REGION".to_owned(), "us-west-2".to_owned());
    assert_native(&evaluate(&ls, &env, &config), false);
    env.insert("AWS_REGION".to_owned(), String::new());
    env.insert("AWS_DEFAULT_REGION".to_owned(), "us-west-2".to_owned());
    assert_eq!(evaluate(&ls, &env, &config), python);
    assert_native(&evaluate(&flag, &env, &config), false);
}

#[test]
fn a_configured_endpoint_botocore_s_client_creation_rejects_is_python_s() {
    let config = files(concat!(
        "[default]\nservices = absent\n",
        "[profile empty]\nservices = blank\n[services blank]\n",
        "[profile local]\nservices = local\n",
        "[services local]\ns3 =\n  endpoint_url = http://localhost:4566\n",
    ));
    let ls = ["s3", "ls", "s3://bucket"];
    let python = Verdict::Python(PythonReason::EndpointSetting);
    let mut env = BTreeMap::new();
    assert_eq!(evaluate(&ls, &env, &config), python);
    assert_eq!(
        evaluate(&["--profile", "empty", "s3", "ls"], &env, &config),
        python
    );
    assert_native(
        &evaluate(&["--profile", "local", "s3", "ls"], &env, &config),
        false,
    );
    let flag = ["--endpoint-url", "http://h:1", "s3", "ls"];
    assert_native(&evaluate(&flag, &env, &config), false);
    env.insert("AWS_ENDPOINT_URL".to_owned(), "http://h:1".to_owned());
    assert_native(&evaluate(&ls, &env, &config), false);
    env.insert("AWS_ENDPOINT_URL_S3".to_owned(), "not-a-url".to_owned());
    assert_eq!(evaluate(&ls, &env, &config), python);
    env.insert(
        "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS".to_owned(),
        "true".to_owned(),
    );
    assert_native(&evaluate(&ls, &env, &config), false);
}

#[test]
fn variable_references_in_shared_file_paths_are_python_s() {
    let none = files("");
    for variable in ["AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE"] {
        for (value, python) in [("$HOME/config", true), ("${X}", true), ("~/config", false)] {
            let env = BTreeMap::from([(variable.to_owned(), value.to_owned())]);
            for argv in [&["s3", "ls"][..], &["s3", "cp", "a", "s3://b/k"]] {
                let verdict = evaluate(argv, &env, &none);
                if python {
                    assert_eq!(verdict, Verdict::Python(PythonReason::SharedFilePath));
                } else {
                    assert_native(&verdict, argv[1] == "cp");
                }
            }
        }
    }
}

#[cfg(unix)]
#[test]
fn a_variable_reference_in_a_non_unicode_path_is_python_s() {
    use std::os::unix::ffi::OsStringExt;
    let path = std::ffi::OsString::from_vec(b"/raw/\xff/$DIR/config".to_vec());
    let env = cli_core::SnapshotEnv::from_pairs([("AWS_CONFIG_FILE", path)]);
    let reason = effective_config::admit(&effective_config::Inputs {
        env: &env,
        shared_files: &files(""),
        cli_profile: None,
        cli_error_format: None,
        transfers: false,
        boto_config_credentials: false,
    });
    assert_eq!(reason, Some(PythonReason::SharedFilePath));
}
