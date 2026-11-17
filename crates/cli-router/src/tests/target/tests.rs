use super::*;

#[test]
fn proxy_case_bypass_and_cgi_rules_apply_to_both_s3_commands() {
    let cased = cli_core::proxy::NAMES_HAVE_CASE;
    let cases: &[(&[(&str, &str)], bool)] = &[
        (&[], false),
        (&[("HTTP_PROXY", "http://upper:80")], false),
        (
            &[("HTTP_PROXY", "http://upper:80"), ("http_proxy", "")],
            cased,
        ),
        (
            &[("HTTPS_PROXY", "http://upper:80"), ("https_proxy", "")],
            cased,
        ),
        (
            &[
                ("HTTP_PROXY", "http://upper:80"),
                ("http_proxy", "http://lower:80"),
            ],
            false,
        ),
        (&[("Http_Proxy", "http://x:1")], cased),
        (
            &[("REQUEST_METHOD", "GET"), ("HTTP_PROXY", "http://x:1")],
            true,
        ),
        (&[("NO_PROXY", "éxample.com")], true),
        (&[("NO_PROXY", "localhost"), ("no_proxy", "")], cased),
        (&[("NO_PROXY", "localhost")], false),
        (&[("no_proxy", "*")], false),
    ];
    for (entries, python) in cases {
        let env = cli_core::SnapshotEnv::from_pairs(entries.iter().copied());
        for command in [&["s3", "ls"][..], &["s3", "cp", "local", "s3://bucket/key"]] {
            let actual = evaluate(command, &env, &files(""));
            if *python {
                assert_eq!(actual, Verdict::Python(PythonReason::NetworkSetting));
            } else {
                assert!(
                    matches!(actual, Verdict::Native(_)),
                    "{entries:?} {actual:?}"
                );
            }
        }
    }
}
#[test]
fn proxy_environments_the_native_reader_cannot_reproduce_are_pythons() {
    let cased = cli_core::proxy::NAMES_HAVE_CASE;
    let cases: &[(&[(&str, &str)], bool)] = &[
        (&[("NO_PROXY", "localhost")], false),
        (&[("no_proxy", "")], false),
        (&[("NO_PROXY", ""), ("no_proxy", "")], false),
        (&[("Http_Proxy", "http://x:1")], cased),
        // A CGI process: Python drops HTTP_PROXY, the CRT's reader keeps it.
        (
            &[("REQUEST_METHOD", "GET"), ("HTTP_PROXY", "http://x:1")],
            true,
        ),
        (
            &[
                ("REQUEST_METHOD", "GET"),
                ("HTTP_PROXY", "http://x:1"),
                ("http_proxy", "http://y:1"),
            ],
            !cased,
        ),
        // Python strips and lowercases a bypass list with Unicode rules.
        (&[("NO_PROXY", "\u{a0}example.com")], true),
        (&[("NO_PROXY", "localhost"), ("no_proxy", "")], cased),
    ];
    let shared = files("");
    for (entries, python) in cases {
        let env = cli_core::SnapshotEnv::from_pairs(entries.iter().copied());
        let expected = python.then_some(PythonReason::NetworkSetting);
        for cp in [false, true] {
            let actual = effective_config::admit(&effective_config::Inputs {
                env: &env,
                shared_files: &shared,
                cli_profile: None,
                cli_error_format: None,
                transfers: cp,
                boto_config_credentials: false,
            });
            assert_eq!(actual, expected, "{entries:?} cp={cp}");
        }
    }
}
/// `http://127.0.0.1:1/` and a code unit that is not Unicode: a byte that is
/// not UTF-8, or on Windows, which holds its environment as UTF-16, a lone
/// surrogate.
#[cfg(unix)]
fn proxy_url_not_unicode() -> std::ffi::OsString {
    use std::os::unix::ffi::OsStringExt;
    std::ffi::OsString::from_vec(b"http://127.0.0.1:1/\xff".to_vec())
}
#[cfg(windows)]
fn proxy_url_not_unicode() -> std::ffi::OsString {
    use std::os::windows::ffi::OsStringExt;
    let units: Vec<u16> = "http://127.0.0.1:1/"
        .encode_utf16()
        .chain([0xdcff])
        .collect();
    std::ffi::OsString::from_wide(&units)
}
// Python keeps a proxy URL that is not Unicode, with surrogate escapes.
#[test]
fn proxy_urls_that_are_not_unicode_are_pythons() {
    let shared = files("");
    for name in ["HTTPS_PROXY", "HTTP_PROXY"] {
        let env = cli_core::SnapshotEnv::from_pairs([(name, proxy_url_not_unicode())]);
        for cp in [false, true] {
            let actual = effective_config::admit(&effective_config::Inputs {
                env: &env,
                shared_files: &shared,
                cli_profile: None,
                cli_error_format: None,
                transfers: cp,
                boto_config_credentials: false,
            });
            assert_eq!(actual, Some(PythonReason::NetworkSetting), "{name} cp={cp}");
        }
    }
}
#[test]
fn region_validation_applies_to_every_source_and_preserves_empty_flag_errors() {
    let shared = files("[profile bad]\nregion = bad!\n[profile fips]\nregion = fips-us-west-2\n");
    for command in [
        &["s3", "ls", "s3://bucket"][..],
        &["s3", "cp", "local", "s3://bucket/key"],
    ] {
        for (flag, value, native) in [
            ("--region", "bad!", false),
            ("--region", "123", false),
            ("--profile", "bad", false),
            ("--profile", "fips", true),
            ("--region", "us-west-2-fips", true),
            ("--region", "", false),
        ] {
            let arguments = [&[flag, value][..], command].concat();
            let result = evaluate(&arguments, &BTreeMap::new(), &shared);
            if native {
                assert!(matches!(result, Verdict::Native(_)));
            } else {
                assert_eq!(result, Verdict::Python(PythonReason::EndpointSetting));
            }
        }
        for variable in ["AWS_REGION", "AWS_DEFAULT_REGION"] {
            let env = BTreeMap::from([(variable.into(), "us_east_1".into())]);
            assert_eq!(
                evaluate(command, &env, &shared),
                Verdict::Python(PythonReason::EndpointSetting)
            );
        }
    }
}

#[test]
fn record_sources_and_command_scopes_survive_the_routing_boundary() {
    let configured = files(concat!(
        "[default]\nca_bundle = ignored-profile.pem\n",
        "request_checksum_calculation = when_required\ntcp_keepalive = true\n",
        "s3 =\n  multipart_chunksize = 16MB\n"
    ));
    let env = BTreeMap::from([
        ("AWS_CA_BUNDLE".into(), "testdata/ca.pem".into()),
        (
            "AWS_REQUEST_CHECKSUM_CALCULATION".into(),
            "WHEN_SUPPORTED".into(),
        ),
        ("AWS_CRT_S3_MEMORY_LIMIT_IN_MB".into(), "512".into()),
    ]);
    for command in [&["s3", "ls"][..], &["s3", "cp", "file", "s3://b/key"]] {
        let Verdict::Native(native) = evaluate(command, &env, &configured) else {
            panic!("valid resolved record")
        };
        assert_common_record(&native.client);
        assert_command_record(&native.client, command[1] == "cp");
    }
    let env = BTreeMap::from([("AWS_CRT_S3_MEMORY_LIMIT_IN_MB".into(), "255".into())]);
    assert!(matches!(
        evaluate(&["s3", "ls"], &env, &files("")),
        Verdict::Native(_)
    ));
    assert_eq!(
        evaluate(&["s3", "cp", "file", "s3://b/key"], &env, &files("")),
        Verdict::Python(PythonReason::TransferSetting)
    );
}

#[test]
fn nested_record_values_keep_their_configuration_fallback_reason() {
    for (key, reason) in [
        ("max_attempts", PythonReason::RetrySetting),
        ("retry_mode", PythonReason::RetrySetting),
        ("tcp_keepalive", PythonReason::NetworkSetting),
        ("ca_bundle", PythonReason::NetworkSetting),
        (
            "request_checksum_calculation",
            PythonReason::TransferSetting,
        ),
        (
            "response_checksum_validation",
            PythonReason::TransferSetting,
        ),
        ("sdk_ua_app_id", PythonReason::UserAgentSetting),
    ] {
        let configured = files(&format!("[default]\n{key} =\n  key = value\n"));
        for command in [&["s3", "ls"][..], &["s3", "cp", "file", "s3://b/key"]] {
            assert_eq!(
                evaluate(command, &BTreeMap::new(), &configured),
                Verdict::Python(reason)
            );
        }
    }
}

#[test]
fn copy_output_flags_retain_bound_values_and_integer_errors() {
    for (options, only_errors, progress, frequency, multiline) in [
        (vec![], false, true, 0, false),
        (vec!["--only-show-errors"], true, true, 0, false),
        (vec!["--no-progress"], false, false, 0, false),
        (vec!["--progress-frequency=1_0"], false, true, 10, false),
        (vec!["--progress-multiline"], false, true, 0, true),
        (
            vec![
                "--recursive",
                "--only-show-errors",
                "--no-progress",
                "--progress-frequency",
                "2",
                "--progress-multiline",
            ],
            true,
            false,
            2,
            true,
        ),
    ] {
        let argv = [&["s3", "cp"][..], &options, &["file", "s3://bucket/key"]].concat();
        let Verdict::Native(native) = evaluate(&argv, &BTreeMap::new(), &files("")) else {
            panic!("copy options {argv:?}")
        };
        let Command::S3Cp(args) = native.command else {
            panic!("copy command")
        };
        assert_eq!(
            (
                args.only_show_errors,
                args.progress,
                args.progress_frequency,
                args.progress_multiline
            ),
            (only_errors, progress, Some(frequency), multiline)
        );
    }
    let digits = "1".repeat(4301);
    for (value, reason) in [
        ("abc", "invalid_integer"),
        ("99999999999999999999", "integer_out_of_range"),
        (digits.as_str(), "integer_digit_limit"),
    ] {
        expect(
            &[
                "s3",
                "cp",
                "--progress-frequency",
                value,
                "file",
                "s3://bucket/key",
            ],
            Expected::Failure(reason),
        );
    }
}

#[test]
fn routing_modes_are_exact_and_unknown_values_are_automatic() {
    assert_eq!(routing_mode(Some("native")), RoutingMode::Native);
    assert_eq!(routing_mode(Some("python")), RoutingMode::Python);
    for value in [
        None,
        Some(""),
        Some("auto"),
        Some("Native"),
        Some("native "),
    ] {
        assert_eq!(routing_mode(value), RoutingMode::Auto);
    }
}

#[test]
fn transfer_and_endpoint_records_reject_invalid_values_in_their_command_scope() {
    for (key, value, reason, cp_only) in [
        (
            "multipart_threshold",
            "bad",
            PythonReason::TransferSetting,
            true,
        ),
        (
            "max_concurrent_requests",
            "0",
            PythonReason::TransferSetting,
            true,
        ),
        (
            "preferred_transfer_client",
            "classic",
            PythonReason::TransferSetting,
            true,
        ),
        (
            "addressing_style",
            "bogus",
            PythonReason::EndpointSetting,
            false,
        ),
        (
            "force_path_style",
            "true",
            PythonReason::EndpointSetting,
            false,
        ),
        ("accelerate", "true", PythonReason::EndpointSetting, false),
        (
            "disable_multi_region_access_points",
            "true",
            PythonReason::EndpointSetting,
            false,
        ),
    ] {
        let files = files(&format!("[default]\ns3 =\n  {key} = {value}\n"));
        let env = BTreeMap::new();
        assert_eq!(
            evaluate(&["s3", "cp", "file", "s3://b/key"], &env, &files),
            Verdict::Python(reason)
        );
        let listing = evaluate(&["s3", "ls"], &env, &files);
        if cp_only {
            assert!(matches!(listing, Verdict::Native(_)));
        } else {
            assert_eq!(listing, Verdict::Python(reason));
        }
    }
}

#[test]
fn client_record_retains_chain_and_nested_sources_after_routing() {
    use cli_core::client_config::{AddressingStyle, ChecksumMode, Source, Trust};
    let configured = files(
        "[default]\nca_bundle = testdata/ca.pem\nrequest_checksum_calculation = \
            when_required\ns3 =\n  addressing_style = path\n  max_concurrent_requests = 3\n",
    );
    let env = BTreeMap::from([(
        "AWS_REQUEST_CHECKSUM_CALCULATION".into(),
        "WHEN_SUPPORTED".into(),
    )]);
    let Verdict::Native(native) = evaluate(&["s3", "cp", "file", "s3://b/key"], &env, &configured)
    else {
        panic!("native record")
    };
    assert_eq!(
        native.client.trust.value,
        Trust::File(Path::new("testdata/ca.pem").to_owned())
    );
    assert_eq!(native.client.trust.source, Source::Profile("ca_bundle"));
    assert_eq!(
        native.client.request_checksum.value,
        ChecksumMode::WhenSupported
    );
    assert_eq!(
        native.client.request_checksum.source,
        Source::Env("AWS_REQUEST_CHECKSUM_CALCULATION")
    );
    assert_eq!(native.client.addressing_style.value, AddressingStyle::Path);
    assert_eq!(
        native.client.addressing_style.source,
        Source::S3("addressing_style")
    );
    assert_eq!(
        native
            .client
            .max_connections
            .as_ref()
            .map(|v| (v.value, v.source)),
        Some((3, Source::S3("max_concurrent_requests")))
    );
}

#[test]
fn new_global_support_binds_sources_and_checks_invalid_values() {
    for argv in [
        &["--no-sign-request", "s3", "ls"][..],
        &["s3", "cp", "a", "s3://b/k", "--no-sign-request"],
    ] {
        let Verdict::Native(native) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!("{argv:?}")
        };
        assert!(!native.client.signing.value);
        assert_eq!(
            native.client.signing.source,
            cli_core::client_config::Source::Flag("--no-sign-request")
        );
    }
    for (value, millis) in [("0", u32::MAX), ("5", 5000), ("4294968", u32::MAX)] {
        let argv = ["--cli-connect-timeout", value, "s3", "ls"];
        let Verdict::Native(native) = evaluate(&argv, &BTreeMap::new(), &files("")) else {
            panic!("{argv:?}")
        };
        assert_eq!(native.client.connect_timeout_ms.value, millis);
    }
    for value in ["-1", "9223372037"] {
        expect(
            &["s3", "ls", "--cli-connect-timeout", value],
            Expected::Python(PythonReason::PythonOnlyGlobal),
        );
    }
    expect(
        &["s3", "ls", "--cli-connect-timeout", "abc"],
        Expected::Failure("invalid_integer"),
    );
    expect(
        &["s3", "ls", "--ca-bundle", ""],
        Expected::Python(PythonReason::PythonOnlyGlobal),
    );
    expect(
        &["s3", "ls", "--ca-bundle", "testdata/ca.pem"],
        Expected::Native(false),
    );
    expect(
        &["s3", "ls", "--ca-bundle", "Cargo.toml"],
        Expected::Python(PythonReason::PythonOnlyGlobal),
    );
}
#[test]
fn output_globals_are_ignored_at_every_position_but_queries_are_python_s() {
    for command in [&["s3", "ls"][..], &["s3", "cp", "a", "s3://b/k"]] {
        for option in [
            &["--query", "Contents[].Key"][..],
            &["--query", "["],
            &["--color", "on"],
            &["--no-cli-pager"],
        ] {
            for position in 0..=2 {
                let mut argv = command.to_vec();
                argv.splice(position..position, option.iter().copied());
                if option[0] == "--query" {
                    expect(&argv, Expected::Python(PythonReason::PythonOnlyGlobal));
                } else {
                    expect(&argv, Expected::Native(command[1] == "cp"));
                }
            }
        }
    }
}
#[test]
fn aliases_replace_or_extend_s3_before_parameter_files_are_read() {
    for alias in [
        "[toplevel]\ns3 = !replacement\n",
        "[command s3]\ncustom = ls\n",
        "[command s3 cp]\nfoo = bar\n",
        "[command  s3\tcp]\nfoo = bar\n",
        "[command s3\u{1f}]\ncustom = ls\n",
        "[command \u{1c}s3\u{1d}cp\u{1e}]\nfoo = bar\n",
    ] {
        let shared = ParsedFiles::parse(awscli_config::Inputs {
            aliases: Some(awscli_config::Contents {
                source: "alias",
                bytes: alias.as_bytes(),
            }),
            ..Default::default()
        });
        for argv in [
            &["s3", "ls"][..],
            &["s3", "cp", "a", "s3://b/k"],
            &["s3", "ls", "file://missing"],
            &["s3", "sync", "a", "b"],
        ] {
            assert_eq!(
                evaluate(argv, &BTreeMap::new(), &shared),
                Verdict::Python(PythonReason::S3Alias),
                "{alias:?} {argv:?}"
            );
        }
    }
    for alias in [
        "[toplevel]\nec2 = describe\n",
        "[command S3]\nfoo = bar\n",
        "[command s3]\n",
        "[toplevel ]\ns3 = !replacement\n",
        "[command\u{1f}s3]\nfoo = bar\n",
    ] {
        let shared = ParsedFiles::parse(awscli_config::Inputs {
            aliases: Some(awscli_config::Contents {
                source: "alias",
                bytes: alias.as_bytes(),
            }),
            ..Default::default()
        });
        assert!(
            matches!(
                evaluate(&["s3", "ls"], &BTreeMap::new(), &shared),
                Verdict::Native(_)
            ),
            "{alias:?}"
        );
    }
}
#[test]
fn malformed_shared_files_obey_first_pass_auto_prompt_and_alias_precedence() {
    let malformed = awscli_config::Contents {
        source: "bad",
        bytes: b"missing header\n",
    };
    for shared in [
        ParsedFiles::parse(awscli_config::Inputs {
            config: Some(malformed),
            ..Default::default()
        }),
        ParsedFiles::parse(awscli_config::Inputs {
            credentials: Some(malformed),
            ..Default::default()
        }),
    ] {
        for argv in [
            &["--version"][..],
            &["s3", "ls"],
            &["ec2", "describe-instances"],
            &["--cli-auto-prompt", "--no-cli-auto-prompt", "s3", "ls"],
        ] {
            assert_eq!(
                evaluate(argv, &BTreeMap::new(), &shared),
                Verdict::Python(PythonReason::ConfigParseFailure)
            );
        }
        assert!(matches!(
            evaluate(&["s3", "ls", "--debug=1"], &BTreeMap::new(), &shared),
            Verdict::Failure(_)
        ));
    }
    let aliases = ParsedFiles::parse(awscli_config::Inputs {
        aliases: Some(malformed),
        ..Default::default()
    });
    assert!(matches!(
        evaluate(
            &["--cli-auto-prompt", "--no-cli-auto-prompt", "s3", "ls"],
            &BTreeMap::new(),
            &aliases
        ),
        Verdict::Failure(_)
    ));
    assert_eq!(
        evaluate(&["s3", "ls"], &BTreeMap::new(), &aliases),
        Verdict::Python(PythonReason::ConfigParseFailure)
    );
}
#[test]
fn configured_endpoint_inputs_and_output_encoding_keep_their_reasons() {
    for key in [
        "force_path_style",
        "accelerate",
        "disable_multi_region_access_points",
    ] {
        assert_eq!(
            evaluate(
                &["s3", "ls"],
                &BTreeMap::new(),
                &files(&format!("[default]\ns3 =\n  {key} = true\n"))
            ),
            Verdict::Python(PythonReason::EndpointSetting)
        );
    }
    for value in ["", "utf-8", "invalid-codec"] {
        assert_eq!(
            evaluate(
                &["s3", "ls"],
                &BTreeMap::from([("AWS_CLI_OUTPUT_ENCODING".into(), value.into())]),
                &files("")
            ),
            Verdict::Python(PythonReason::OutputEncoding)
        );
    }
    for region in ["123", "-bad", "bad_1", "bad."] {
        assert_eq!(
            evaluate(
                &[&format!("--region={region}"), "s3", "ls"],
                &BTreeMap::new(),
                &files("")
            ),
            Verdict::Python(PythonReason::EndpointSetting)
        );
        assert_eq!(
            evaluate(
                &["s3", "ls"],
                &BTreeMap::from([("AWS_REGION".into(), region.into())]),
                &files("")
            ),
            Verdict::Python(PythonReason::EndpointSetting)
        );
    }
}
#[test]
fn injected_platform_selects_tuned_transfer_persona() {
    let argv = ["s3", "cp", "a", "s3://b/k"].map(str::to_owned);
    let mut parsed = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    let env = BTreeMap::new();
    let files = files("");
    let verdict = route_with_platform(
        &mut parsed,
        &unpack::Environment {
            directory: Path::new("."),
            variables: &HashMap::new(),
            files: &unpack::FsParamfiles,
            preferred_encoding: unpack::PreferredEncoding::Locale,
        },
        &Configuration {
            env: &env,
            shared_files: &files,
            boto_config_credentials: false,
            embedded_trust: true,
        },
        cli_core::client_config::Platform {
            optimized: true,
            recommended_gbps: Some(100.0),
        },
    );
    let Verdict::Native(native) = verdict else {
        panic!("{verdict:?}")
    };
    assert_eq!(
        native.client.persona.map(|v| v.value),
        Some(cli_core::client_config::Persona::Tuned)
    );
    assert_eq!(native.client.target_gbps.value, 100.0);
    assert_eq!(native.client.part_size.value, 0);
}

#[test]
fn platform_probe_waits_for_route_and_transfer_admission() {
    for (argv, text, expected_calls) in [
        (&["s3", "ls"][..], "", 0),
        (&["ec2", "describe-instances"][..], "", 0),
        (&["s3", "cp", "a", "s3://b/k"][..], "", 1),
        (
            &["s3", "cp", "a", "s3://b/k"][..],
            "[default]\ns3 =\n  multipart_chunksize = bad\n",
            0,
        ),
        (
            &["s3", "cp", "a", "s3://b/k"][..],
            "[default]\ns3 =\n  preferred_transfer_client = crt\n  target_bandwidth = 10Gb/s\n",
            0,
        ),
    ] {
        let argv = argv
            .iter()
            .map(|value| (*value).to_owned())
            .collect::<Vec<_>>();
        let mut parsed =
            awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
        let env = BTreeMap::new();
        let shared = files(text);
        let calls = std::cell::Cell::new(0);
        let _ = route_with_probe(
            &mut parsed,
            &unpack::Environment {
                directory: Path::new("."),
                variables: &HashMap::new(),
                files: &unpack::FsParamfiles,
                preferred_encoding: unpack::PreferredEncoding::Locale,
            },
            &Configuration {
                env: &env,
                shared_files: &shared,
                boto_config_credentials: false,
                embedded_trust: true,
            },
            || {
                calls.set(calls.get() + 1);
                cli_core::client_config::Platform::default()
            },
        );
        assert_eq!(calls.get(), expected_calls, "{argv:?} {text:?}");
    }
}

fn assert_common_record(client: &cli_core::client_config::ClientConfig) {
    use cli_core::client_config::{ChecksumMode, Source};
    assert_eq!(client.trust.source, Source::Env("AWS_CA_BUNDLE"));
    assert_eq!(client.keep_alive.source, Source::Profile("tcp_keepalive"));
    assert!(client.keep_alive.value);
    assert_eq!(
        client.request_checksum.source,
        Source::Env("AWS_REQUEST_CHECKSUM_CALCULATION")
    );
    assert_eq!(client.request_checksum.value, ChecksumMode::WhenSupported);
}

fn assert_command_record(client: &cli_core::client_config::ClientConfig, copy: bool) {
    use cli_core::client_config::{MemoryLimit, Source};
    if copy {
        assert_eq!(client.part_size.value, 16 << 20);
        assert_eq!(client.part_size.source, Source::S3("multipart_chunksize"));
        assert_eq!(client.memory_limit.value, MemoryLimit::Override(512 << 20));
    } else {
        assert_eq!(client.part_size.value, 0);
        assert_eq!(client.memory_limit.value, MemoryLimit::Tier);
    }
}
