use super::*;
use std::collections::BTreeMap;
fn resolved(
    text: &str,
    entries: &[(&str, &str)],
    command: Command,
) -> Result<ClientConfig, PythonReason> {
    let env = entries
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect::<BTreeMap<_, _>>();
    resolved_in(text, &env, command)
}
fn resolved_in(
    text: &str,
    env: &impl EnvMap,
    command: Command,
) -> Result<ClientConfig, PythonReason> {
    let files = ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: text.as_bytes(),
        }),
        ..Default::default()
    });
    resolve(&Inputs {
        env,
        files: &files,
        globals: &Globals::default(),
        command,
        directory: Path::new("."),
        platform: Platform::default(),
        embedded_trust: true,
    })
}
#[test]
fn retry_boundaries_and_persona_defaults() -> Result<(), PythonReason> {
    for command in [Command::Ls, Command::Cp] {
        assert_eq!(resolved("", &[], command)?.retry_attempts.value, Some(3));
        for count in ["", "0", "1", "65", "bad"] {
            assert_eq!(
                resolved("", &[("AWS_MAX_ATTEMPTS", count)], command),
                Err(PythonReason::RetrySetting)
            );
        }
        for count in [2, 64] {
            assert_eq!(
                resolved("", &[("AWS_MAX_ATTEMPTS", &count.to_string())], command)?
                    .retry_attempts
                    .value,
                Some(count)
            );
        }
    }
    let crt = "[default]\nretry_mode = adaptive\nmax_attempts = 1\ns3 =\n  \
        preferred_transfer_client = crt\n";
    let config = resolved(crt, &[], Command::Cp)?;
    assert!(config.ignored.retry_mode_adaptive);
    assert_eq!(config.ignored.max_attempts, Some(1));
    assert_eq!(config.retry_attempts.value, None);
    Ok(())
}
#[test]
fn transfer_coercions_sources_and_unsupported_values() -> Result<(), PythonReason> {
    let config = resolved(
        "[default]\ns3 =\n  multipart_chunksize = 16MB\n  max_concurrent_requests = 4\n  \
            target_bandwidth = 10Gb/s\n  should_stream = False\n",
        &[],
        Command::Cp,
    )?;
    assert_eq!(
        config.part_size,
        Resolved::new(16 << 20, Source::S3("multipart_chunksize"))
    );
    assert_eq!(config.max_connections.map(|v| v.value), Some(4));
    assert!(config.should_stream.is_some_and(|v| !v.value));
    let streaming = resolved(
        "[default]\ns3 =\n  should_stream = TRUE\n",
        &[],
        Command::Cp,
    )?;
    assert!(streaming.should_stream.is_some_and(|v| v.value));
    for line in [
        "multipart_chunksize = 0",
        "multipart_threshold = 8.5MB",
        "max_concurrent_requests = 4294967296",
        "max_queue_size = 0",
        "disk_throughput = 1b/s",
        "preferred_transfer_client = classic",
        "max_bandwidth = 1MB/s",
    ] {
        let text = format!("[default]\ns3 =\n  {line}\n");
        assert_eq!(
            resolved(&text, &[], Command::Cp),
            Err(PythonReason::TransferSetting),
            "{line}"
        );
        assert!(resolved(&text, &[], Command::Ls).is_ok());
    }
    Ok(())
}
#[test]
fn memory_overrides_and_part_boundaries() -> Result<(), PythonReason> {
    for (value, valid) in [
        ("", true),
        ("0", true),
        ("256", true),
        ("0256", true),
        ("255", false),
        ("+256", false),
        (" 256", false),
        ("2_56", false),
        ("17592186044416", false),
    ] {
        assert_eq!(
            resolved("", &[("AWS_CRT_S3_MEMORY_LIMIT_IN_MB", value)], Command::Cp).is_ok(),
            valid,
            "{value}"
        );
    }
    assert_eq!(
        resolved(
            "[default]\ns3 =\n  multipart_chunksize = 134217729\n",
            &[],
            Command::Cp
        ),
        Err(PythonReason::TransferSetting)
    );
    assert_eq!(
        resolved(
            "",
            &[
                ("AWS_CRT_S3_MEMORY_LIMIT_IN_MB", "0"),
                ("AWS_CRT_S3_MEMORY_LIMIT_IN_GIB", "6")
            ],
            Command::Cp
        )?
        .memory_bytes(),
        6 << 30
    );
    Ok(())
}
#[test]
fn checksum_and_user_agent_sources_are_bounded() -> Result<(), PythonReason> {
    let config = resolved(
        "[default]\nrequest_checksum_calculation = when_required\nsdk_ua_app_id = profile\n",
        &[("AWS_SDK_UA_APP_ID", ""), ("AWS_EXECUTION_ENV", "test env")],
        Command::Ls,
    )?;
    assert_eq!(config.request_checksum.value, ChecksumMode::WhenRequired);
    assert_eq!(config.app_id.map(|v| v.value), Some(Vec::new()));
    assert_eq!(
        resolved("", &[("AWS_EXECUTION_ENV", &"x".repeat(2049))], Command::Ls),
        Err(PythonReason::UserAgentSetting)
    );
    assert_eq!(
        resolved(
            "[default]\nrequest_checksum_calculation = invalid\n",
            &[],
            Command::Ls
        ),
        Err(PythonReason::TransferSetting)
    );
    Ok(())
}
#[test]
fn app_id_follows_the_chain_within_the_header_bound() -> Result<(), PythonReason> {
    use super::user_agent::SUPPLIED_BYTES_MAX;
    let text = "[default]\nsdk_ua_app_id = fromprofile\n\
        [profile nested]\nsdk_ua_app_id =\n  key = value\n";
    let nested = Globals {
        profile: Some("nested".into()),
        ..Globals::default()
    };
    let half = "a".repeat(SUPPLIED_BYTES_MAX / 2);
    let (over, rest) = (format!("{half}e"), "a".repeat(SUPPLIED_BYTES_MAX - 3));
    for command in [Command::Ls, Command::Cp] {
        let profile = resolved(text, &[], command)?;
        let from_profile = Resolved::new(b"fromprofile".to_vec(), Source::Profile("sdk_ua_app_id"));
        assert_eq!(profile.app_id, Some(from_profile));
        assert_eq!(profile.execution_env, None);
        let cleared = resolved(text, &[("AWS_SDK_UA_APP_ID", "")], command)?;
        let empty = Resolved::new(Vec::new(), Source::Env("AWS_SDK_UA_APP_ID"));
        assert_eq!(cleared.app_id, Some(empty));
        assert_eq!(
            customized(text, &[], command, &nested, Platform::default()),
            Err(PythonReason::UserAgentSetting)
        );
        for (app_id, execution_env, admitted) in [
            (&half, &half, true),
            (&half, &over, false),
            (&rest, &"env".to_owned(), true),
            (&rest, &"envs".to_owned(), false),
        ] {
            let entries = [
                ("AWS_SDK_UA_APP_ID", app_id.as_str()),
                ("AWS_EXECUTION_ENV", execution_env.as_str()),
            ];
            let bounded = resolved(text, &entries, command);
            if admitted {
                let value = bounded?.execution_env.map(|v| v.value);
                assert_eq!(value, Some(execution_env.as_bytes().to_vec()));
            } else {
                assert_eq!(bounded, Err(PythonReason::UserAgentSetting));
            }
        }
    }
    Ok(())
}
#[cfg(unix)]
#[test]
fn environment_values_that_are_not_unicode_are_present() -> Result<(), PythonReason> {
    use std::os::unix::ffi::OsStrExt;
    let env = |pairs: &[(&str, &[u8])]| {
        crate::SnapshotEnv::from_pairs(pairs.iter().map(|&(k, v)| (k, OsStr::from_bytes(v))))
    };
    let profile = "[default]\nretry_mode = standard\nmax_attempts = 3\n\
        request_checksum_calculation = when_required\n\
        response_checksum_validation = when_required\n";
    for (variable, reason) in [
        ("AWS_RETRY_MODE", PythonReason::RetrySetting),
        ("AWS_MAX_ATTEMPTS", PythonReason::RetrySetting),
        (
            "AWS_REQUEST_CHECKSUM_CALCULATION",
            PythonReason::TransferSetting,
        ),
        (
            "AWS_RESPONSE_CHECKSUM_VALIDATION",
            PythonReason::TransferSetting,
        ),
        (
            "AWS_CRT_S3_MEMORY_LIMIT_IN_MB",
            PythonReason::TransferSetting,
        ),
        (
            "AWS_CRT_S3_MEMORY_LIMIT_IN_GIB",
            PythonReason::TransferSetting,
        ),
    ] {
        assert_eq!(
            resolved_in(profile, &env(&[(variable, b"\xff")]), Command::Cp),
            Err(reason),
            "{variable}"
        );
    }
    let config = resolved_in(
        "[default]\nsdk_ua_app_id = fromprofile\n",
        &env(&[
            ("AWS_SDK_UA_APP_ID", b"\xff"),
            ("AWS_EXECUTION_ENV", b"ci\xff"),
        ]),
        Command::Ls,
    )?;
    assert_eq!(
        config.app_id,
        Some(Resolved::new(
            b"\xff".to_vec(),
            Source::Env("AWS_SDK_UA_APP_ID")
        ))
    );
    assert_eq!(
        config.execution_env.map(|v| v.value),
        Some(b"ci\xff".to_vec())
    );
    let long = |count| {
        let value = [0xff].repeat(count);
        env(&[("AWS_EXECUTION_ENV", &value)])
    };
    assert!(resolved_in("", &long(2048), Command::Ls).is_ok());
    assert_eq!(
        resolved_in("", &long(2049), Command::Ls),
        Err(PythonReason::UserAgentSetting)
    );
    Ok(())
}
#[test]
fn connect_timeout_reproduces_disabled_and_saturating_values() {
    assert_eq!(connect_timeout_milliseconds(None), Some(60_000));
    assert_eq!(connect_timeout_milliseconds(Some(0)), Some(u32::MAX));
    assert_eq!(connect_timeout_milliseconds(Some(12)), Some(12000));
    assert_eq!(connect_timeout_milliseconds(Some(-1)), None);
    assert_eq!(connect_timeout_milliseconds(Some(i64::MAX)), None);
}

mod coercion;
mod network;
mod user_agent;

fn customized(
    text: &str,
    entries: &[(&str, &str)],
    command: Command,
    globals: &Globals,
    platform: Platform,
) -> Result<ClientConfig, PythonReason> {
    let files = ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: text.as_bytes(),
        }),
        ..Default::default()
    });
    let env = crate::SnapshotEnv::from_pairs(entries.iter().copied());
    resolve(&Inputs {
        env: &env,
        files: &files,
        globals,
        command,
        directory: Path::new(env!("CARGO_MANIFEST_DIR")),
        platform,
        embedded_trust: true,
    })
}
#[test]
fn personas_preserve_default_parts_thresholds_and_recursive_caps() -> Result<(), PythonReason> {
    for (block, platform, persona, throughput, part, cap) in [
        (
            "",
            Platform::default(),
            Persona::NewlyEligible,
            4.0,
            8 << 20,
            Some(10),
        ),
        (
            "  preferred_transfer_client = crt\n",
            Platform::default(),
            Persona::CrtPreferred,
            10.0,
            0,
            None,
        ),
        (
            "",
            Platform {
                optimized: true,
                recommended_gbps: Some(100.0),
            },
            Persona::Tuned,
            100.0,
            0,
            None,
        ),
        (
            "",
            Platform {
                optimized: false,
                recommended_gbps: Some(1.25),
            },
            Persona::NewlyEligible,
            1.25,
            8 << 20,
            Some(10),
        ),
    ] {
        let text = if block.is_empty() {
            String::new()
        } else {
            format!("[default]\ns3 =\n{block}")
        };
        let config = customized(&text, &[], Command::Cp, &Globals::default(), platform)?;
        assert_eq!(config.persona.map(|v| v.value), Some(persona));
        assert_eq!(config.target_gbps.value, throughput);
        assert_eq!(config.part_size.value, part);
        assert_eq!(
            config.max_connections,
            cap.map(|value| Resolved::new(value, Source::Persona))
        );
    }
    let cap = resolved(
        "[default]\ns3 =\n  max_concurrent_requests = 4\n",
        &[],
        Command::Cp,
    )?;
    assert_eq!(
        cap.max_connections,
        Some(Resolved::new(4, Source::S3("max_concurrent_requests")))
    );
    Ok(())
}
#[test]
fn lazy_platform_probe_runs_only_after_configuration_requires_it() -> Result<(), PythonReason> {
    let env = BTreeMap::<String, String>::new();
    let mut probes = 0;
    for (text, command, expected) in [
        ("", Command::Ls, 0),
        (
            "[default]\ns3 =\n  preferred_transfer_client = crt\n  target_bandwidth = 5GB/s\n",
            Command::Cp,
            0,
        ),
        ("", Command::Cp, 1),
    ] {
        let files = ParsedFiles::parse(awscli_config::Inputs {
            config: Some(awscli_config::Contents {
                source: "config",
                bytes: text.as_bytes(),
            }),
            ..Default::default()
        });
        let globals = Globals::default();
        let inputs = Inputs {
            env: &env,
            files: &files,
            globals: &globals,
            command,
            directory: Path::new("."),
            platform: Platform::default(),
            embedded_trust: true,
        };
        let before = probes;
        resolve_with_probe(&inputs, || {
            probes += 1;
            Platform::default()
        })?;
        assert_eq!(probes - before, expected);
    }
    Ok(())
}
#[test]
fn ignored_settings_warning_is_ordered_and_empty_settings_are_silent() {
    let settings = IgnoredSettings {
        max_bandwidth: true,
        max_queue_size: true,
        io_chunksize: true,
        retry_mode_adaptive: true,
        max_attempts: Some(1),
    };
    assert_eq!(
        settings.to_string(),
        "warning: The following configuration values are not supported by the 'crt' s3 \
            transfer client and will be ignored: max_bandwidth, max_queue_size, \
            io_chunksize, retry_mode = adaptive, max_attempts = 1 (must be between 2 and 64).\n"
    );
    assert!(IgnoredSettings::default().to_string().is_empty());
}
#[test]
fn source_names_match_diagnostic_contract() {
    for (source, display, name) in [
        (Source::Default, "default", "default"),
        (Source::Persona, "persona", "persona"),
        (
            Source::Flag("--ca-bundle"),
            "flag --ca-bundle",
            "--ca-bundle",
        ),
        (
            Source::Env("AWS_CA_BUNDLE"),
            "environment variable AWS_CA_BUNDLE",
            "AWS_CA_BUNDLE",
        ),
        (
            Source::Profile("ca_bundle"),
            "profile key ca_bundle",
            "ca_bundle",
        ),
        (
            Source::S3("target_bandwidth"),
            "profile key s3.target_bandwidth",
            "target_bandwidth",
        ),
    ] {
        assert_eq!(source.to_string(), display);
        assert_eq!(source.setting_name(), name);
    }
}

#[test]
fn download_direct_io_requires_enabled_setting_and_page_aligned_parts() {
    let mut config = ClientConfig::new(Command::Cp);
    assert!(!config.download_direct_io(4096));
    config.direct_io = Some(Resolved::new(true, Source::S3("direct_io")));
    for (part_size, expected) in [(8 * 1024 * 1024, true), (5_000_000, false), (0, true)] {
        config.part_size.value = part_size;
        assert_eq!(config.download_direct_io(4096), expected);
    }
    config.direct_io = Some(Resolved::new(false, Source::S3("direct_io")));
    assert!(!config.download_direct_io(4096));
    assert!(!config.download_direct_io(0));
}

#[test]
fn proxy_inputs_survive_record_resolution_for_both_schemes() -> Result<(), PythonReason> {
    let env = crate::SnapshotEnv::from_pairs([
        ("HTTPS_PROXY", "http://upper:80"),
        ("http_proxy", "http://lower:80"),
    ]);
    let files = ParsedFiles::parse(Default::default());
    let globals = Globals::default();
    resolve(&Inputs {
        env: &env,
        files: &files,
        globals: &globals,
        command: Command::Cp,
        directory: Path::new("."),
        platform: Platform::default(),
        embedded_trust: true,
    })?;
    let environment = crate::proxy::Environment::from_map(&env);
    assert_eq!(environment.resolve("https://s3"), Some("http://upper:80"));
    assert_eq!(environment.resolve("http://s3"), Some("http://lower:80"));
    Ok(())
}

#[test]
fn every_transfer_key_reaches_the_record() {
    let keys = [
        ("multipart_threshold", "16MB"),
        ("multipart_chunksize", "16MB"),
        ("max_concurrent_requests", "4"),
        ("max_queue_size", "5"),
        ("max_bandwidth", "1MB/s"),
        ("preferred_transfer_client", "crt"),
        ("target_bandwidth", "1Gb/s"),
        ("io_chunksize", "1MB"),
        ("should_stream", "false"),
        ("disk_throughput", "1Gb/s"),
        ("direct_io", "false"),
    ];
    assert_eq!(keys.map(|(key, _)| key), coerce::TRANSFER_KEYS);
    let default = resolved("", &[], Command::Cp);
    assert!(default.is_ok());
    for (key, value) in keys {
        let text = format!("[default]\ns3 =\n  {key} = {value}\n");
        assert_ne!(resolved(&text, &[], Command::Cp), default, "{key}");
    }
    let unread = "[default]\ns3 =\n  not_a_transfer_key = 1\n";
    assert_eq!(resolved(unread, &[], Command::Cp), default);
}
fn trust_for(
    embedded_trust: bool,
    entries: &[(&str, &str)],
    globals: &Globals,
) -> Result<Resolved<Trust>, PythonReason> {
    let env = BTreeMap::from_iter(
        entries
            .iter()
            .map(|(key, value)| (key.to_string(), value.to_string())),
    );
    let files = ParsedFiles::parse(Default::default());
    let config = resolve(&Inputs {
        env: &env,
        files: &files,
        globals,
        command: Command::Ls,
        directory: Path::new(env!("CARGO_MANIFEST_DIR")),
        platform: Platform::default(),
        embedded_trust,
    })?;
    Ok(config.trust)
}
#[test]
fn default_trust_follows_the_payload_and_configured_bundles_win() -> Result<(), PythonReason> {
    let none = Globals::default();
    assert_eq!(
        trust_for(true, &[], &none)?,
        Resolved::new(Trust::Embedded, Source::Default)
    );
    let platform = trust_for(false, &[], &none)?;
    assert_eq!(platform, Resolved::new(Trust::Platform, Source::Default));
    let mut lines = Vec::new();
    ClientConfig {
        trust: platform,
        ..ClientConfig::new(Command::Ls)
    }
    .log_resolved(crate::proxy::Environment::default(), |line| {
        lines.push(String::from_utf8_lossy(line).into_owned());
    });
    assert!(lines.contains(&"TLS trust: platform store (from default)".to_owned()));
    let flag = Globals {
        ca_bundle: Some("testdata/ca.pem".into()),
        ..Default::default()
    };
    for embedded_trust in [false, true] {
        assert_eq!(
            trust_for(
                embedded_trust,
                &[("AWS_CA_BUNDLE", "testdata/ca.pem")],
                &none
            )?,
            Resolved::new(
                Trust::File("testdata/ca.pem".into()),
                Source::Env("AWS_CA_BUNDLE")
            )
        );
        assert_eq!(
            trust_for(embedded_trust, &[], &flag)?,
            Resolved::new(
                Trust::File("testdata/ca.pem".into()),
                Source::Flag("--ca-bundle")
            )
        );
    }
    Ok(())
}
type Retries = Option<(Option<u32>, IgnoredSettings, u64)>;
fn retries(config: Result<ClientConfig, PythonReason>) -> Retries {
    match config {
        Ok(config) => Some((
            config.retry_attempts.value,
            config.ignored.clone(),
            config.botocore_attempts(),
        )),
        Err(reason) => {
            assert_eq!(reason, PythonReason::RetrySetting);
            None
        }
    }
}
struct RetryCase {
    mode: Option<&'static str>,
    attempts: Option<&'static str>,
    ls: Retries,
    newly_eligible: Retries,
    crt: Retries,
}
fn retry_cases() -> [RetryCase; 8] {
    let native = |attempts, listing| Some((attempts, IgnoredSettings::default(), listing));
    let ignored = |adaptive, count, attempts, listing| {
        let ignored = IgnoredSettings {
            retry_mode_adaptive: adaptive,
            max_attempts: count,
            ..IgnoredSettings::default()
        };
        Some((attempts, ignored, listing))
    };
    let case = |mode, attempts, ls, newly_eligible, crt| RetryCase {
        mode,
        attempts,
        ls,
        newly_eligible,
        crt,
    };
    let everywhere = |count| native(Some(count), u64::from(count));
    [
        case(None, None, everywhere(3), everywhere(3), native(None, 3)),
        case(None, Some("2"), everywhere(2), everywhere(2), everywhere(2)),
        case(
            Some("standard"),
            Some("64"),
            everywhere(64),
            everywhere(64),
            everywhere(64),
        ),
        case(
            None,
            Some("1"),
            None,
            None,
            ignored(false, Some(1), None, 1),
        ),
        case(
            None,
            Some("65"),
            None,
            None,
            ignored(false, Some(65), None, 65),
        ),
        case(
            Some("adaptive"),
            None,
            None,
            None,
            ignored(true, None, None, 3),
        ),
        case(
            Some("adaptive"),
            Some("5"),
            None,
            None,
            ignored(true, None, Some(5), 5),
        ),
        case(
            Some("adaptive"),
            Some("100"),
            None,
            None,
            ignored(true, Some(100), None, 100),
        ),
    ]
}
#[test]
fn retries_follow_botocore_for_ls_and_the_persona_for_cp() {
    let tuned = Platform {
        optimized: true,
        recommended_gbps: Some(100.0),
    };
    let hosts = [
        ("", Platform::default(), false),
        (
            "s3 =\n  preferred_transfer_client = crt\n",
            Platform::default(),
            true,
        ),
        ("", tuned, true),
    ];
    let globals = Globals::default();
    for case in retry_cases() {
        let entries = [
            ("AWS_RETRY_MODE", case.mode),
            ("AWS_MAX_ATTEMPTS", case.attempts),
        ];
        let entries: Vec<_> = entries
            .into_iter()
            .filter_map(|(name, value)| Some((name, value?)))
            .collect();
        let label = format!("{:?} {:?}", case.mode, case.attempts);
        for (block, platform, crt_host) in hosts {
            let text = format!("[default]\n{block}");
            let cp = customized(&text, &entries, Command::Cp, &globals, platform);
            let expected = if crt_host {
                &case.crt
            } else {
                &case.newly_eligible
            };
            assert_eq!(&retries(cp), expected, "{label} {block:?}");
            let ls = customized(&text, &entries, Command::Ls, &globals, Platform::default());
            assert_eq!(retries(ls), case.ls, "{label} {block:?}");
        }
    }
}
