use super::*;
use crate::client_config::user_agent::{
    self, Distribution, Feature, Host, OsReleaseExtent, Versions,
};
use crate::command::CredentialSource;
fn header(config: &ClientConfig, uploads: bool) -> String {
    user_agent::assemble(
        config,
        &Host {
            system: "Linux".into(),
            release: "6.19.13-arch1-1".into(),
            machine: "x86_64".into(),
        },
        Some(&Distribution {
            id: "arch".into(),
            version_major: String::new(),
        }),
        Versions {
            cli: "2.37.2",
            crt: "0.37.0",
            rust: "1.96.0",
        },
        uploads,
    )
}
#[test]
fn listing_and_transfer_headers_preserve_component_and_feature_order() -> Result<(), PythonReason> {
    assert_eq!(
        header(&resolved("", &[], Command::Ls)?, false),
        "aws-cli/2.37.2 md/awscrt#0.37.0 ua/2.1 os/linux#6.19.13-arch1-1 md/arch#x86_64 \
            lang/rust#1.96.0 m/C,E,Z,b cfg/retry-mode#standard md/installer#other \
            md/distrib#arch md/prompt#off md/command#s3.ls"
    );
    let config = resolved(
        "",
        &[
            ("AWS_ENDPOINT_URL", "http://127.0.0.1:9"),
            ("AWS_EXECUTION_ENV", "test env"),
            ("CLAUDECODE", "1"),
        ],
        Command::Cp,
    )?;
    assert!(header(&config, true).contains(
        " lang/rust#1.96.0 exec-env/test-env m/E,G,N,W,Z,b,AN,Ag cfg/retry-mode#standard "
    ));
    assert!(header(&config, false).contains(" m/E,G,N,Z,b,AN,Ag "));
    let explicit = resolved(
        "[default]\nretry_mode = adaptive\nrequest_checksum_calculation = \
            when_required\nresponse_checksum_validation = when_required\nsdk_ua_app_id = \
            my app\ns3 =\n  preferred_transfer_client = crt\n",
        &[],
        Command::Cp,
    )?;
    assert!(header(&explicit, true).contains(" m/F,G,a,c,Ae cfg/retry-mode#adaptive app/my-app "));
    Ok(())
}
#[test]
fn bytes_that_are_not_utf8_sanitize_one_dash_each() {
    assert_eq!(user_agent::sanitize_bytes(b"ci\xff", false), "ci-");
    assert_eq!(
        user_agent::sanitize_bytes(b"\xe2\x82A\xc3\xa9#", true),
        "--A-#"
    );
    assert_eq!(
        user_agent::sanitize_bytes(b"\xed\xa0\x80\xff\xfe", false),
        "-----"
    );
    let bytes = ClientConfig {
        app_id: Some(Resolved::new(
            b"\xff".to_vec(),
            Source::Env("AWS_SDK_UA_APP_ID"),
        )),
        execution_env: Some(Resolved::new(
            b"ci\xff".to_vec(),
            Source::Env("AWS_EXECUTION_ENV"),
        )),
        ..ClientConfig::default()
    };
    let actual = header(&bytes, false);
    assert!(actual.contains(" exec-env/ci- m/"), "{actual}");
    assert!(actual.contains(" app/- md/installer#other "), "{actual}");
}
#[test]
fn sanitization_and_optional_components_follow_upstream() {
    assert_eq!(user_agent::sanitize("a b/c:d#eé🙂", false), "a-b-c-d-e--");
    assert_eq!(user_agent::sanitize("a#b", true), "a#b");
    let config = ClientConfig::default();
    let versions = Versions {
        cli: "test",
        crt: "test",
        rust: "test",
    };
    for (system, release, machine, expected) in [
        ("Darwin", "24.6", "ARM64", "os/macos#24.6 md/arch#arm64"),
        (
            "FreeBSD",
            "14.1",
            "amd64",
            "os/other md/FreeBSD#14.1 md/arch#amd64",
        ),
        ("Windows", "10", "", "os/windows#10 lang/rust#test"),
        ("other", "custom", "", "os/other#custom lang/rust#test"),
    ] {
        let actual = user_agent::assemble(
            &config,
            &Host {
                system: system.into(),
                release: release.into(),
                machine: machine.into(),
            },
            Some(&Distribution::default()),
            versions,
            false,
        );
        assert!(actual.contains(expected), "{actual}");
        assert!(!actual.contains("md/distrib"));
        assert!(!actual.contains("app/"));
        assert!(!actual.contains("exec-env/"));
        assert!(!actual.contains("md/pyimpl"));
    }
}

#[test]
fn maximum_inputs_and_all_available_features_stay_bounded() {
    let config = ClientConfig {
        app_id: Some(Resolved::new(b"s".repeat(1024), Source::Default)),
        execution_env: Some(Resolved::new(b"e".repeat(1024), Source::Default)),
        agentic_callers: [
            Feature::AgenticCallerClaudeCode,
            Feature::AgenticCallerGeminiCli,
            Feature::AgenticCallerCodex,
            Feature::AgenticCallerKiro,
            Feature::AgenticCallerOpencode,
            Feature::AgenticCallerAntigravity,
            Feature::AgenticCallerAmp,
            Feature::AgenticCallerPi,
            Feature::AgenticCallerCopilotCli,
            Feature::AgenticCallerCursor,
        ]
        .into_iter()
        .collect(),
        endpoint_override: true,
        ..ClientConfig::new(Command::Cp)
    };
    let actual = user_agent::assemble(
        &config,
        &Host {
            system: "x".repeat(256),
            release: "x".repeat(256),
            machine: "x".repeat(256),
        },
        Some(&Distribution {
            id: "7".into(),
            version_major: "7".repeat(4095),
        }),
        Versions {
            cli: &"9".repeat(32),
            crt: &"9".repeat(32),
            rust: &"9".repeat(32),
        },
        true,
    );
    assert!(actual.len() < 16 * 1024);
    assert!(actual.ends_with("md/command#s3.cp"));
    let feature = actual
        .split_whitespace()
        .find(|part| part.starts_with("m/"));
    assert_eq!(
        feature,
        Some("m/E,G,N,W,Z,b,AN,AO,AP,AQ,AR,AS,AT,AU,AV,AW,Ag")
    );
    assert!(feature.is_some_and(|part| part.len() < 1024));
    let version_only = user_agent::assemble(
        &ClientConfig::default(),
        &Host::default(),
        Some(&Distribution {
            id: String::new(),
            version_major: "8".into(),
        }),
        Versions {
            cli: "test",
            crt: "test",
            rust: "test",
        },
        false,
    );
    assert!(version_only.contains(" md/distrib#.8 md/prompt#off"));
}

#[cfg(unix)]
#[test]
fn native_uname_supplies_nonempty_host_facts() {
    let host = user_agent::host();
    assert!(!host.system.is_empty());
    assert!(!host.release.is_empty());
    assert!(!host.machine.is_empty());
}

#[test]
fn caller_features_use_exact_values_and_target_order() -> Result<(), PythonReason> {
    let config = resolved(
        "",
        &[
            ("CURSOR_AGENT", "1"),
            ("CLAUDECODE", "1"),
            ("GEMINI_CLI", "true"),
            ("CODEX_THREAD_ID", "abc"),
            ("KIRO_SESSION_ID", ""),
            ("PI_CODING_AGENT", "true"),
        ],
        Command::Ls,
    )?;
    assert!(config.agentic_callers.codes().eq(["AN", "AP", "AU", "AW"]));
    assert!(header(&config, false).contains("m/C,E,Z,b,AN,AP,AU,AW "));
    Ok(())
}
#[test]
fn os_release_parsing_normalizes_distribution_and_major_version() {
    for (text, id, version) in [
        ("ID=arch\n", "arch", ""),
        ("ID=ol\nVERSION_ID=9.4\n", "oracle", "9"),
        ("ID=opensuse-leap\nVERSION_ID=15.6\n", "opensuse", "15"),
        (
            " id='My Linux' # ignored\nversion_id=123.4 # ignored\n",
            "my_linux",
            "123",
        ),
        (
            "#ID=bad\nID=ubuntu\nVERSION_ID=\"24.04 LTS\"\n",
            "ubuntu",
            "24",
        ),
        ("NAME=x\nVERSION_ID=\"22.04\"\nID=ubuntu\n", "ubuntu", "22"),
        (
            "NAME=\"Arch Linux\"\nID=arch\nBUILD_ID=rolling\n",
            "arch",
            "",
        ),
        ("ID=\"ol\"\nVERSION_ID=\"9.4\"\n", "oracle", "9"),
        ("ID='opensuse-leap'\nVERSION_ID=15.6", "opensuse", "15"),
        ("ID=\"Ubuntu Core\"\r\nVERSION_ID=x1\r\n", "ubuntu_core", ""),
        (
            "# ID=wrong\n  ID=debian # trailing\nid=later\n",
            "later",
            "",
        ),
        ("VERSION_ID=v12\nID=fedora\nVERSION_ID=40\n", "fedora", "40"),
        ("ID=debian#x\n", "debian", ""),
        ("", "", ""),
    ] {
        let distro = user_agent::parse_os_release(text, OsReleaseExtent::Whole);
        assert_eq!(distro.id, id, "{text:?}");
        assert_eq!(distro.version_major, version, "{text:?}");
    }
}
#[test]
fn os_release_tokenizes_as_distros_shlex_does() {
    for (text, id, version) in [
        ("ID=\"x\r\n", "unknown", ""),
        ("ID=\"x\n", "unknown", ""),
        ("ID='x\n", "unknown", ""),
        ("ID=\"x\r\nVERSION_ID=\"7\"\r\n", "unknown", ""),
        ("ID=\"x\"\r\nVERSION_ID=\"7\"\r\n", "x", "7"),
        ("ID=x\\", "unknown", ""),
        ("ID=\"x\\", "unknown", ""),
        ("ID=\"multi\nline\"\nVERSION_ID=8\n", "multi\nline", "8"),
        ("ID=fe\"do\"ra\n", "fedora", ""),
        ("\"ID=quoted\"\n", "quoted", ""),
        ("ID=\"a\\\"b\\\\c\\d\"\n", "a\"b\\c\\d", ""),
        ("ID='a\\b'\n", "a\\b", ""),
        ("ID=a\\ b\n", "a_b", ""),
        ("# note\rID=centos\rVERSION_ID=7\r", "centos", "7"),
        ("ID=one ID=two\n", "two", ""),
        ("NAME='it''s'\nID=x=y\n", "x=y", ""),
        ("PRETTY_NAME=\"x # y\"\nID=arch # c\n", "arch", ""),
        ("ID=\n", "", ""),
        ("ID=\u{212A}\n", "k", ""),
        ("ID=x\nVERSION_ID=\"7\n", "unknown", ""),
        ("ID=\"a\r\nb\"\nVERSION_ID=9\n", "a\nb", "9"),
        ("ID=x\rVERSION_ID=8\r", "x", "8"),
        ("NAME=\"a\nID=wrong\"\nID=right\n", "right", ""),
        ("# \"open\nID=x\n", "x", ""),
        ("ID=ub\"untu\"\nVERSION_ID=2\"2.04\"\n", "ubuntu", "22"),
        ("ID=o\"l\"\n", "oracle", ""),
        ("ID=\"x\\\"y\\\\z\\w\"\n", "x\"y\\z\\w", ""),
        ("ID='x\\y'\n", "x\\y", ""),
        ("ID=x\\ y\\\nz\n", "x_y\nz", ""),
        ("ID=\"a#b\"\n", "a#b", ""),
        ("ID=\u{212A}\nVERSION_ID=1\n", "k", "1"),
        ("ID=\u{130}x\n", "i\u{307}x", ""),
    ] {
        let distro = user_agent::parse_os_release(text, OsReleaseExtent::Whole);
        assert_eq!(distro.id, id, "{text:?}");
        assert_eq!(distro.version_major, version, "{text:?}");
    }
}
#[test]
fn os_release_shlex_rejects_or_lowercases_reaches_the_header_as_written() {
    let header = |text| {
        user_agent::assemble(
            &ClientConfig::default(),
            &Host::default(),
            Some(&user_agent::parse_os_release(text, OsReleaseExtent::Whole)),
            Versions {
                cli: "test",
                crt: "test",
                rust: "test",
            },
            false,
        )
    };
    let unknown = header("ID=\"x\r\nVERSION_ID=\"7\"\r\n");
    assert!(
        unknown.contains(" md/installer#other md/distrib#unknown md/prompt#off "),
        "{unknown}"
    );
    let dotted = header("ID=\u{130}x\n");
    assert!(dotted.contains(" md/distrib#i-x "), "{dotted}");
}
#[test]
fn endpoint_feature_tracks_resolved_override_even_with_deferred_services_error()
-> Result<(), PythonReason> {
    assert!(!resolved("", &[], Command::Ls)?.endpoint_override);
    assert!(
        resolved(
            "",
            &[("AWS_ENDPOINT_URL_S3", "http://localhost")],
            Command::Ls
        )?
        .endpoint_override
    );
    assert!(
        !resolved(
            "",
            &[
                ("AWS_ENDPOINT_URL_S3", "http://localhost"),
                ("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true")
            ],
            Command::Ls
        )?
        .endpoint_override
    );
    assert!(
        resolved(
            "[default]\nservices = missing\nendpoint_url = http://localhost\n",
            &[],
            Command::Ls
        )?
        .endpoint_override
    );
    Ok(())
}
#[test]
fn feature_codes_are_unique_alphanumeric_tokens_in_table_order() {
    let codes: Vec<&str> = Feature::ALL.into_iter().map(Feature::code).collect();
    assert_eq!(
        codes.join(","),
        "C,E,F,G,N,W,Z,a,b,c,g,v,w,n,z,AN,AO,AP,AQ,AR,AS,AT,AU,AV,AW,Ae,Ag"
    );
    for (index, code) in codes.iter().enumerate() {
        assert!(!code.is_empty());
        assert!(
            code.bytes().all(|byte| byte.is_ascii_alphanumeric()),
            "{code}"
        );
        assert!(!codes[index + 1..].contains(code), "{code} repeats");
    }
    let all: user_agent::Features = Feature::ALL.into_iter().collect();
    assert!(all.iter().eq(Feature::ALL));
    assert!(format!("m/{}", codes.join(",")).len() <= 1024);
}
fn feature_matrix() -> Vec<(ClientConfig, bool)> {
    let mut configs = Vec::new();
    for source in [
        CredentialSource::Environment,
        CredentialSource::SharedProfile,
        CredentialSource::Process,
        CredentialSource::Container,
        CredentialSource::DefaultChain,
    ] {
        for (request, response) in [
            (ChecksumMode::WhenSupported, ChecksumMode::WhenRequired),
            (ChecksumMode::WhenRequired, ChecksumMode::WhenSupported),
        ] {
            let mut config = ClientConfig::new(Command::Ls);
            config.credential_source = source;
            config.request_checksum = Resolved::new(request, Source::Default);
            config.response_checksum = Resolved::new(response, Source::Default);
            configs.push((config.clone(), false));
            config.command = Command::Cp;
            for persona in [
                Persona::CrtPreferred,
                Persona::Tuned,
                Persona::NewlyEligible,
            ] {
                config.persona = Some(Resolved::new(persona, Source::Default));
                configs.push((config.clone(), false));
                configs.push((config.clone(), true));
            }
        }
    }
    configs
}
#[test]
fn record_features_never_claim_an_exclusive_pair() {
    for (config, uploads) in feature_matrix() {
        let features = config.user_agent_features(uploads);
        assert!(!features.contains(Feature::RetryModeStandard));
        assert!(!features.contains(Feature::RetryModeAdaptive));
        let claims_both =
            |[first, second]: [Feature; 2]| features.contains(first) && features.contains(second);
        assert!(
            !user_agent::EXCLUSIVE_PAIRS.into_iter().any(claims_both),
            "{config:?}"
        );
    }
}
#[test]
fn listing_features_name_the_credential_provider() -> Result<(), PythonReason> {
    let keys = [
        ("AWS_ACCESS_KEY_ID", "key"),
        ("AWS_SECRET_ACCESS_KEY", "secret"),
    ];
    let partial = [("AWS_ACCESS_KEY_ID", "key"), ("AWS_SECRET_ACCESS_KEY", "")];
    let profile = "[default]\naws_access_key_id = key\naws_secret_access_key = secret\n";
    let process = "[default]\ncredential_process = cmd\n";
    let container = [("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "/creds")];
    for (text, entries, source, features) in [
        (
            "",
            &keys[..],
            CredentialSource::Environment,
            " m/C,E,Z,b,g cfg/",
        ),
        (
            profile,
            &partial[..],
            CredentialSource::Environment,
            " m/C,E,Z,b,g cfg/",
        ),
        (
            profile,
            &[][..],
            CredentialSource::SharedProfile,
            " m/C,E,Z,b,n cfg/",
        ),
        (
            process,
            &[][..],
            CredentialSource::Process,
            " m/C,E,Z,b,v,w cfg/",
        ),
        // The container provider follows the profiles and precedes the
        // instance's.
        (
            "",
            &container[..],
            CredentialSource::Container,
            " m/C,E,Z,b,z cfg/",
        ),
        (
            profile,
            &container[..],
            CredentialSource::SharedProfile,
            " m/C,E,Z,b,n cfg/",
        ),
        (
            "",
            &[][..],
            CredentialSource::DefaultChain,
            " m/C,E,Z,b cfg/",
        ),
    ] {
        let config = resolved(text, entries, Command::Ls)?;
        assert_eq!(config.credential_source, source);
        assert!(header(&config, false).contains(features), "{source:?}");
    }
    let unsigned = ClientConfig {
        signing: Resolved::new(false, Source::Flag("--no-sign-request")),
        ..resolved("", &keys, Command::Ls)?
    };
    assert!(header(&unsigned, false).contains(" m/C,E,Z,b cfg/"));
    let transfer = resolved("", &keys, Command::Cp)?;
    assert_eq!(transfer.credential_source, CredentialSource::Environment);
    assert!(header(&transfer, true).contains(" m/E,G,W,Z,b,Ag cfg/"));
    Ok(())
}
struct ProviderCase {
    config: &'static str,
    credentials: &'static str,
    environment: bool,
    aws_profile: Option<&'static str>,
    cli_profile: Option<&'static str>,
}
fn provider_config(
    case: &ProviderCase,
    command: Command,
    no_sign_request: bool,
) -> Result<ClientConfig, PythonReason> {
    let files = ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: case.config.as_bytes(),
        }),
        credentials: Some(awscli_config::Contents {
            source: "credentials",
            bytes: case.credentials.as_bytes(),
        }),
        ..Default::default()
    });
    let mut entries = Vec::new();
    if case.environment {
        entries.extend([
            ("AWS_ACCESS_KEY_ID", "env-key"),
            ("AWS_SECRET_ACCESS_KEY", "env-secret"),
        ]);
    }
    if let Some(name) = case.aws_profile {
        entries.push(("AWS_PROFILE", name));
    }
    let env = crate::SnapshotEnv::from_pairs(entries.iter().copied());
    let globals = Globals {
        profile: case.cli_profile.map(Into::into),
        no_sign_request,
        ..Globals::default()
    };
    resolve(&Inputs {
        env: &env,
        files: &files,
        globals: &globals,
        command,
        directory: Path::new("."),
        platform: Platform::default(),
        embedded_trust: true,
    })
}
fn provider_cases() -> [(ProviderCase, CredentialSource, &'static str); 8] {
    const DEFAULT_PAIR: &str = concat!(
        "[default]\n",
        "aws_access_key_id = key\naws_secret_access_key = secret\n"
    );
    const WORK_PAIR: &str = concat!(
        "[profile work]\n",
        "aws_access_key_id = key\naws_secret_access_key = secret\n"
    );
    const PROCESS: &str = "[default]\ncredential_process = helper\n";
    let case = |config, credentials, environment, aws_profile, cli_profile| ProviderCase {
        config,
        credentials,
        environment,
        aws_profile,
        cli_profile,
    };
    use CredentialSource::{DefaultChain, Environment, Process, SharedProfile};
    [
        (case("", "", false, None, None), DefaultChain, " m/C,E,Z,b "),
        (
            case("", DEFAULT_PAIR, true, None, None),
            Environment,
            " m/C,E,Z,b,g ",
        ),
        (
            case("", DEFAULT_PAIR, false, None, None),
            SharedProfile,
            " m/C,E,Z,b,n ",
        ),
        (
            case(DEFAULT_PAIR, "", false, None, None),
            SharedProfile,
            " m/C,E,Z,b,n ",
        ),
        (
            case(PROCESS, "", false, None, None),
            Process,
            " m/C,E,Z,b,v,w ",
        ),
        (
            case(WORK_PAIR, "", true, Some("work"), None),
            Environment,
            " m/C,E,Z,b,g ",
        ),
        (
            case(WORK_PAIR, "", true, None, Some("work")),
            SharedProfile,
            " m/C,E,Z,b,n ",
        ),
        (
            case("[profile work]\n", "", true, None, Some("work")),
            DefaultChain,
            " m/C,E,Z,b ",
        ),
    ]
}
#[test]
fn a_signed_listing_s_user_agent_names_its_credential_provider() -> Result<(), PythonReason> {
    for (case, source, features) in provider_cases() {
        let listing = provider_config(&case, Command::Ls, false)?;
        assert_eq!(listing.credential_source, source);
        assert!(header(&listing, false).contains(features), "{source:?}");
        let unsigned = provider_config(&case, Command::Ls, true)?;
        assert!(
            header(&unsigned, false).contains(" m/C,E,Z,b "),
            "{source:?}"
        );
        let copy = provider_config(&case, Command::Cp, false)?;
        assert_eq!(copy.credential_source, source);
        assert!(
            header(&copy, false).contains(" m/E,G,Z,b,Ag "),
            "{source:?}"
        );
    }
    Ok(())
}
#[test]
fn sanitizer_replaces_each_disallowed_code_point_with_one_dash() {
    for (text, allow_hash, expected) in [
        (&b"a b#c/\xc3\xa9"[..], false, "a-b-c--"),
        (b"x y#z/\xc3\xa9,ok", true, "x-y#z--,ok"),
        (b"a\xffb\xe2\x82c\xc0\x80d", false, "a-b--c--d"),
        (b"\xed\xa0\x80x", true, "---x"),
        (b"\xf0\x9f\x98\x80x", true, "-x"),
        (b"\xf4\x90\x80\x80x", true, "----x"),
        (b"tab\there\x00\x7f", true, "tab-here--"),
        (b"!$%&'*+-.^_`|~,09AZaz", false, "!$%&'*+-.^_`|~,09AZaz"),
        (b"\"():;<=>?@[\\]{}", true, "---------------"),
        (b"\xc3\xa9", true, "-"),
        (b"\xc3", true, "-"),
        (b"", true, ""),
        (b"a#b", false, "a-b"),
        (b"a#b", true, "a#b"),
    ] {
        assert_eq!(
            user_agent::sanitize_bytes(text, allow_hash),
            expected,
            "{text:?}"
        );
        if let Ok(text) = std::str::from_utf8(text) {
            assert_eq!(user_agent::sanitize(text, allow_hash), expected);
        }
    }
}
#[test]
fn os_family_mapping_and_machine_lowercasing() {
    for (system, release, machine, expected) in [
        (
            "Darwin",
            "24.6.0",
            "arm64",
            "ua/2.1 os/macos#24.6.0 md/arch#arm64 lang/rust#",
        ),
        (
            "FreeBSD",
            "14.1-RELEASE",
            "AMD64",
            "ua/2.1 os/other md/FreeBSD#14.1-RELEASE md/arch#amd64 lang/rust#",
        ),
        ("Windows", "10", "", "ua/2.1 os/windows#10 lang/rust#"),
        (
            "LINUX",
            "",
            "x86_64",
            "ua/2.1 os/linux md/arch#x86_64 lang/rust#",
        ),
        (
            "Plan 9",
            "4#e",
            "x",
            "ua/2.1 os/other md/Plan-9#4#e md/arch#x lang/rust#",
        ),
    ] {
        let actual = user_agent::assemble(
            &ClientConfig::default(),
            &Host {
                system: system.into(),
                release: release.into(),
                machine: machine.into(),
            },
            None,
            Versions {
                cli: "2.37.2",
                crt: "0.37.0",
                rust: "1.96.0",
            },
            false,
        );
        assert!(actual.contains(expected), "{actual}");
    }
}
#[test]
fn empty_values_omit_exec_env_app_and_distrib() {
    let empty = ClientConfig {
        app_id: Some(Resolved::new(Vec::new(), Source::Env("AWS_SDK_UA_APP_ID"))),
        execution_env: Some(Resolved::new(Vec::new(), Source::Env("AWS_EXECUTION_ENV"))),
        ..ClientConfig::default()
    };
    let distribution = Distribution::default();
    let actual = header_with(&empty, Some(&distribution));
    assert_eq!(actual, header_with(&ClientConfig::default(), None));
    for absent in [" exec-env/", " app/", " md/distrib"] {
        assert!(!actual.contains(absent), "{actual}");
    }
    assert!(actual.contains(" lang/rust#1.96.0 m/"), "{actual}");
    assert!(
        actual.contains(" md/installer#other md/prompt#off "),
        "{actual}"
    );
}
fn header_with(config: &ClientConfig, distribution: Option<&Distribution>) -> String {
    user_agent::assemble(
        config,
        &Host {
            system: "Linux".into(),
            release: "6.19.13-arch1-1".into(),
            machine: "x86_64".into(),
        },
        distribution,
        Versions {
            cli: "2.37.2",
            crt: "Unknown",
            rust: "1.96.0",
        },
        false,
    )
}
#[test]
fn every_agentic_caller_variable_registers_only_its_own_code() -> Result<(), PythonReason> {
    let rows = [
        ("CLAUDECODE", Some("1"), "AN"),
        ("GEMINI_CLI", Some("1"), "AO"),
        ("CODEX_THREAD_ID", None, "AP"),
        ("KIRO_SESSION_ID", None, "AQ"),
        ("OPENCODE", None, "AR"),
        ("ANTIGRAVITY_AGENT", None, "AS"),
        ("AMP_CURRENT_THREAD_ID", None, "AT"),
        ("PI_CODING_AGENT", Some("true"), "AU"),
        ("COPILOT_CLI", Some("1"), "AV"),
        ("CURSOR_AGENT", Some("1"), "AW"),
    ];
    for (variable, value, code) in rows {
        let accepted = resolved("", &[(variable, value.unwrap_or("abc"))], Command::Ls)?;
        assert!(accepted.agentic_callers.codes().eq([code]), "{variable}");
        let ignored = value.map_or("", |_| "other");
        let rejected = resolved("", &[(variable, ignored)], Command::Ls)?;
        assert_eq!(rejected.agentic_callers.codes().count(), 0, "{variable}");
    }
    let agentic = Feature::ALL
        .into_iter()
        .filter(|feature| format!("{feature:?}").starts_with("AgenticCaller"))
        .map(Feature::code);
    assert!(agentic.eq(rows.map(|(_, _, code)| code)));
    Ok(())
}
