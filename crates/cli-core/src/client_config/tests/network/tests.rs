use super::*;
#[test]
fn trust_precedence_preserves_sources_and_serializer_validation() -> Result<(), PythonReason> {
    let profile = "[default]\nca_bundle = testdata/ca.pem\n";
    let globals = Globals {
        ca_bundle: Some("testdata/ca.pem".into()),
        ..Default::default()
    };
    for command in [Command::Ls, Command::Cp] {
        let config = customized(
            profile,
            &[("AWS_CA_BUNDLE", "missing")],
            command,
            &globals,
            Platform::default(),
        )?;
        assert_eq!(config.trust.source, Source::Flag("--ca-bundle"));
        assert!(matches!(config.trust.value, Trust::File(_)));
        let config = customized(
            profile,
            &[("AWS_CA_BUNDLE", "testdata/ca.pem")],
            command,
            &Globals::default(),
            Platform::default(),
        )?;
        assert_eq!(config.trust.source, Source::Env("AWS_CA_BUNDLE"));
        let config = customized(
            profile,
            &[("REQUESTS_CA_BUNDLE", "missing")],
            command,
            &Globals::default(),
            Platform::default(),
        )?;
        assert_eq!(config.trust.source, Source::Profile("ca_bundle"));
    }
    assert!(
        customized(
            "",
            &[("AWS_CA_BUNDLE", "")],
            Command::Ls,
            &globals,
            Platform::default()
        )
        .is_ok()
    );
    assert_eq!(
        customized(
            "",
            &[("AWS_CA_BUNDLE", "")],
            Command::Cp,
            &globals,
            Platform::default()
        ),
        Err(PythonReason::NetworkSetting)
    );
    Ok(())
}
#[test]
fn an_empty_chain_falls_back_to_requests_ca_bundle_which_s3_cp_leaves_to_python() {
    let requests = |command| {
        let env = [("REQUESTS_CA_BUNDLE", "testdata/ca.pem")];
        let config = customized("", &env, command, &Globals::default(), Platform::default());
        config.map(|config| config.trust.source)
    };
    assert_eq!(requests(Command::Ls), Ok(Source::Env("REQUESTS_CA_BUNDLE")));
    assert_eq!(requests(Command::Cp), Err(PythonReason::NetworkSetting));
}
#[test]
fn invalid_trust_files_keep_flag_and_setting_reasons_and_precedence() {
    for value in [
        "",
        " \t",
        "\u{a0}",
        "\u{1c}",
        "nonexistent-ca-bundle.pem",
        ".",
        "null\0path",
    ] {
        assert_eq!(
            customized(
                "",
                &[],
                Command::Ls,
                &Globals {
                    ca_bundle: Some(value.into()),
                    ..Default::default()
                },
                Platform::default()
            ),
            Err(PythonReason::PythonOnlyGlobal)
        );
        assert_eq!(
            resolved("", &[("AWS_CA_BUNDLE", value)], Command::Ls),
            Err(PythonReason::NetworkSetting)
        );
    }
    let bad_transfer = "[default]\ns3 =\n  multipart_threshold = invalid\n";
    assert_eq!(
        resolved(bad_transfer, &[("AWS_CA_BUNDLE", "")], Command::Cp),
        Err(PythonReason::NetworkSetting)
    );
    let globals = Globals {
        ca_bundle: Some("testdata/ca.pem".into()),
        ..Default::default()
    };
    assert_eq!(
        customized(
            bad_transfer,
            &[("AWS_CA_BUNDLE", "")],
            Command::Cp,
            &globals,
            Platform::default()
        ),
        Err(PythonReason::TransferSetting)
    );
}
#[test]
fn bypass_checks_shadowed_service_endpoints_for_non_ascii() {
    let text =
        "[default]\nservices = custom\n[services custom]\ns3 =\n  endpoint_url = http://é.test\n";
    assert!(resolved(text, &[], Command::Ls).is_ok());
    let entries = [
        ("NO_PROXY", "example.com"),
        ("AWS_ENDPOINT_URL_S3", "http://localhost:9000"),
    ];
    assert_eq!(
        resolved(text, &entries, Command::Ls),
        Err(PythonReason::NetworkSetting)
    );
}
#[test]
fn endpoint_and_keepalive_values_apply_with_source_provenance() -> Result<(), PythonReason> {
    let config = resolved(
        "[default]\ntcp_keepalive = TRUE\ns3 =\n  addressing_style = virtual\n  \
            use_accelerate_endpoint = true\n  use_dualstack_endpoint = true\n",
        &[],
        Command::Ls,
    )?;
    assert_eq!(
        config.keep_alive,
        Resolved::new(true, Source::Profile("tcp_keepalive"))
    );
    assert_eq!(config.addressing_style.value, AddressingStyle::Virtual);
    assert!(config.use_accelerate_endpoint.value);
    assert!(config.use_dualstack_endpoint.value);
    for style in ["Virtual", "", "unknown"] {
        assert_eq!(
            resolved(
                &format!("[default]\ns3 =\n  addressing_style = {style}\n"),
                &[],
                Command::Ls
            ),
            Err(PythonReason::EndpointSetting)
        );
    }
    Ok(())
}
struct Bundles {
    directory: PathBuf,
    files: ParsedFiles,
}
impl Bundles {
    fn new() -> std::io::Result<Self> {
        let bundles =
            Self::with_config("[default]\nca_bundle =\n[profile set]\nca_bundle = ca.pem\n")?;
        bundles.bundle("ca.pem")?;
        std::fs::write(bundles.directory.join("not-pem.txt"), "not a certificate\n")?;
        std::fs::create_dir(bundles.directory.join("directory.pem"))?;
        Ok(bundles)
    }
    fn with_config(config: &str) -> std::io::Result<Self> {
        static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        let directory = std::env::temp_dir().join(format!(
            "aws-cli-trust-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
        ));
        std::fs::create_dir(&directory)?;
        Ok(Self {
            directory,
            files: ParsedFiles::parse(awscli_config::Inputs {
                config: Some(awscli_config::Contents {
                    source: "config",
                    bytes: config.as_bytes(),
                }),
                ..Default::default()
            }),
        })
    }
    fn bundle(&self, name: impl AsRef<Path>) -> std::io::Result<()> {
        std::fs::write(self.directory.join(name), ca_bundle::TEST_CERTIFICATE_PEM)
    }
    fn resolve(
        &self,
        globals: &Globals,
        env: &[(&str, &OsStr)],
    ) -> Result<ClientConfig, PythonReason> {
        self.resolve_on(Command::Ls, globals, env, Platform::default())
    }
    fn trust(
        &self,
        command: Command,
        globals: &Globals,
        env: &[(&str, &str)],
        platform: Platform,
    ) -> Result<Resolved<Trust>, PythonReason> {
        let env = env
            .iter()
            .map(|&(name, value)| (name, OsStr::new(value)))
            .collect::<Vec<_>>();
        let config = self.resolve_on(command, globals, &env, platform)?;
        Ok(config.trust)
    }
    fn resolve_on(
        &self,
        command: Command,
        globals: &Globals,
        env: &[(&str, &OsStr)],
        platform: Platform,
    ) -> Result<ClientConfig, PythonReason> {
        resolve(&Inputs {
            env: &crate::SnapshotEnv::from_pairs(env.iter().copied()),
            files: &self.files,
            globals,
            command,
            directory: &self.directory,
            platform,
            embedded_trust: true,
        })
    }
}
impl Drop for Bundles {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.directory);
    }
}
fn profile(name: &str) -> Globals {
    Globals {
        profile: Some(name.into()),
        ..Default::default()
    }
}
fn flag(path: &str) -> Globals {
    Globals {
        ca_bundle: Some(path.into()),
        ..Default::default()
    }
}
fn file_trust(path: &str, source: Source) -> Result<Resolved<Trust>, PythonReason> {
    Ok(Resolved::new(Trust::File(path.into()), source))
}
const TUNED: Platform = Platform {
    optimized: true,
    recommended_gbps: Some(100.0),
};
#[test]
fn a_ca_bundle_upstream_rejects_or_native_cannot_pass_is_python() -> std::io::Result<()> {
    let bundles = Bundles::new()?;
    let set = profile("set");
    assert_eq!(
        bundles.resolve(&Globals::default(), &[]),
        Err(PythonReason::NetworkSetting)
    );
    let trust = Resolved::new(Trust::File("ca.pem".into()), Source::Profile("ca_bundle"));
    assert_eq!(bundles.resolve(&set, &[]).map(|c| c.trust), Ok(trust));
    let long = "a".repeat(4096);
    for value in [
        "",
        " ",
        "\t\n",
        "\u{3000}",
        "/ca\0.pem",
        "missing.pem",
        "directory.pem",
        "ca.pem/x",
        "not-pem.txt",
        &long,
        &long[..4095],
    ] {
        assert_eq!(
            bundles.resolve(&set, &[("AWS_CA_BUNDLE", OsStr::new(value))]),
            Err(PythonReason::NetworkSetting),
            "{value:?}"
        );
    }
    for flag in [" ", "missing.pem", "not-pem.txt"] {
        let globals = Globals {
            ca_bundle: Some(flag.into()),
            ..profile("set")
        };
        assert_eq!(
            bundles.resolve(&globals, &[]),
            Err(PythonReason::PythonOnlyGlobal)
        );
    }
    Ok(())
}
#[test]
fn a_ca_bundle_resolves_from_the_working_directory_as_a_regular_file() -> std::io::Result<()> {
    let bundles = Bundles::new()?;
    let set = profile("set");
    std::fs::create_dir(bundles.directory.join("sub"))?;
    bundles.bundle("sub/ca.pem")?;
    let absolute = bundles.directory.join("ca.pem");
    for value in [OsStr::new("sub/ca.pem"), absolute.as_os_str()] {
        let trust = Resolved::new(Trust::File(value.into()), Source::Env("AWS_CA_BUNDLE"));
        assert_eq!(
            bundles
                .resolve(&set, &[("AWS_CA_BUNDLE", value)])
                .map(|c| c.trust),
            Ok(trust)
        );
    }
    #[cfg(unix)]
    for device in ["/dev/null", "/dev/zero"] {
        assert_eq!(
            bundles.resolve(&set, &[("AWS_CA_BUNDLE", OsStr::new(device))]),
            Err(PythonReason::NetworkSetting),
            "{device}"
        );
    }
    Ok(())
}
#[cfg(unix)]
#[test]
fn non_unicode_environment_bundle_keeps_bytes_and_precedence() -> std::io::Result<()> {
    use std::os::unix::ffi::OsStrExt;
    let bundles = Bundles::new()?;
    let (set, unset) = (profile("set"), profile("unset"));
    let name = OsStr::from_bytes(b"\xff");
    assert!(!is_blank_path(name));
    let long = [0xff; 4096];
    for value in [b"\xff".as_slice(), b"\xff\0", &long, &long[..4095]] {
        let value = OsStr::from_bytes(value);
        for (globals, variable) in [(&set, "AWS_CA_BUNDLE"), (&unset, "REQUESTS_CA_BUNDLE")] {
            assert_eq!(
                bundles.resolve(globals, &[(variable, value)]),
                Err(PythonReason::NetworkSetting)
            );
        }
    }
    match bundles.bundle(name) {
        Ok(()) => {
            for (globals, variable) in [(&set, "AWS_CA_BUNDLE"), (&unset, "REQUESTS_CA_BUNDLE")] {
                let trust = Resolved::new(Trust::File(name.into()), Source::Env(variable));
                assert_eq!(
                    bundles
                        .resolve(globals, &[(variable, name)])
                        .map(|c| c.trust),
                    Ok(trust)
                );
            }
        }
        Err(error)
            if error.kind() == std::io::ErrorKind::PermissionDenied
                || error.raw_os_error() == Some(libc::EILSEQ) =>
        {
            assert_eq!(
                bundles.resolve(&set, &[("AWS_CA_BUNDLE", name)]),
                Err(PythonReason::NetworkSetting)
            );
        }
        Err(error) => return Err(error),
    }
    Ok(())
}
#[test]
fn a_bundle_of_more_than_certificates_is_python_s_unless_the_crt_loads_it() -> std::io::Result<()> {
    let bundles = Bundles::with_config(
        "[profile mixed]\nca_bundle = mixed.pem\n\
         [profile crt]\nca_bundle = mixed.pem\ns3 =\n  preferred_transfer_client = crt\n\
         [profile prefers-crt]\ns3 =\n  preferred_transfer_client = crt\n",
    )?;
    let certificate = ca_bundle::TEST_CERTIFICATE_PEM;
    let key = ca_bundle::TEST_KEY_PEM;
    for contents in [
        format!("{certificate}{key}"),
        key.to_owned(),
        format!(
            "{}\n{certificate}",
            "#".repeat(ca_bundle::LINE_BUFFER_BYTES)
        ),
    ] {
        std::fs::write(bundles.directory.join("mixed.pem"), contents)?;
        expect_more_than_certificates(&bundles);
    }
    bundles.bundle("mixed.pem")?;
    for command in [Command::Ls, Command::Cp] {
        assert_eq!(
            bundles.trust(command, &profile("mixed"), &[], Platform::default()),
            file_trust("mixed.pem", Source::Profile("ca_bundle"))
        );
    }
    Ok(())
}
fn expect_more_than_certificates(bundles: &Bundles) {
    let host = Platform::default();
    for command in [Command::Ls, Command::Cp] {
        let trust =
            |globals: &Globals, env: &[(&str, &str)]| bundles.trust(command, globals, env, host);
        let network = Err(PythonReason::NetworkSetting);
        assert_eq!(trust(&profile("mixed"), &[]), network);
        assert_eq!(
            trust(&Globals::default(), &[("AWS_CA_BUNDLE", "mixed.pem")]),
            network
        );
        let global = Err(PythonReason::PythonOnlyGlobal);
        assert_eq!(trust(&flag("mixed.pem"), &[]), global);
    }
    assert_eq!(
        bundles.trust(Command::Cp, &profile("mixed"), &[], TUNED),
        Err(PythonReason::NetworkSetting)
    );
    expect_crt_client_loads_more_than_certificates(bundles);
}
fn expect_crt_client_loads_more_than_certificates(bundles: &Bundles) {
    let host = Platform::default();
    let cp =
        |globals: &Globals, env: &[(&str, &str)]| bundles.trust(Command::Cp, globals, env, host);
    let crt_preferred = profile("crt");
    let from_profile = file_trust("mixed.pem", Source::Profile("ca_bundle"));
    assert_eq!(cp(&crt_preferred, &[]), from_profile);
    let flagged = Globals {
        ca_bundle: Some("mixed.pem".into()),
        ..crt_preferred
    };
    let from_flag = file_trust("mixed.pem", Source::Flag("--ca-bundle"));
    assert_eq!(cp(&flagged, &[]), from_flag);
    let prefers_crt = profile("prefers-crt");
    let from_env = file_trust("mixed.pem", Source::Env("AWS_CA_BUNDLE"));
    assert_eq!(
        cp(&prefers_crt, &[("AWS_CA_BUNDLE", "mixed.pem")]),
        from_env
    );
    assert_eq!(
        cp(&prefers_crt, &[("REQUESTS_CA_BUNDLE", "mixed.pem")]),
        Err(PythonReason::NetworkSetting)
    );
    assert_eq!(
        bundles.trust(Command::Ls, &profile("crt"), &[], host),
        Err(PythonReason::NetworkSetting)
    );
}
#[test]
fn every_persona_leaves_s3_cp_s_requests_ca_bundle_to_python() -> std::io::Result<()> {
    let crt_preferred = "[default]\ns3 =\n  preferred_transfer_client = crt\n";
    for (config, host) in [
        ("", Platform::default()),
        (crt_preferred, Platform::default()),
        ("", TUNED),
    ] {
        let bundles = Bundles::with_config(config)?;
        for name in ["requests.pem", "env.pem", "flag.pem"] {
            bundles.bundle(name)?;
        }
        let none = Globals::default();
        let requests = ("REQUESTS_CA_BUNDLE", "requests.pem");
        assert_eq!(
            bundles.trust(Command::Ls, &none, &[requests], host),
            file_trust("requests.pem", Source::Env("REQUESTS_CA_BUNDLE"))
        );
        let cp = |globals: &Globals, env: &[(&str, &str)]| {
            bundles.trust(Command::Cp, globals, env, host)
        };
        assert_eq!(cp(&none, &[requests]), Err(PythonReason::NetworkSetting));
        let chain = [requests, ("AWS_CA_BUNDLE", "env.pem")];
        assert_eq!(
            cp(&none, &chain),
            file_trust("env.pem", Source::Env("AWS_CA_BUNDLE"))
        );
        assert_eq!(
            cp(&flag("flag.pem"), &chain),
            file_trust("flag.pem", Source::Flag("--ca-bundle"))
        );
        assert_eq!(
            cp(&none, &[("REQUESTS_CA_BUNDLE", " ")]),
            Err(PythonReason::NetworkSetting)
        );
    }
    Ok(())
}
#[test]
fn s3_cp_that_may_run_the_crt_leaves_requests_ca_bundle_to_python() -> std::io::Result<()> {
    let bundles =
        Bundles::with_config("[profile prefers-crt]\ns3 =\n  preferred_transfer_client = crt\n")?;
    bundles.bundle("ca.pem")?;
    let host = Platform::default();
    let requests = [("REQUESTS_CA_BUNDLE", "ca.pem")];
    let prefers_crt = profile("prefers-crt");
    assert_eq!(
        bundles.trust(Command::Cp, &prefers_crt, &requests, host),
        Err(PythonReason::NetworkSetting)
    );
    assert_eq!(
        bundles.trust(Command::Cp, &Globals::default(), &requests, host),
        Err(PythonReason::NetworkSetting)
    );
    assert_eq!(
        bundles.trust(Command::Ls, &prefers_crt, &requests, host),
        file_trust("ca.pem", Source::Env("REQUESTS_CA_BUNDLE"))
    );
    assert_eq!(
        bundles.trust(
            Command::Cp,
            &prefers_crt,
            &[("AWS_CA_BUNDLE", "ca.pem")],
            host
        ),
        file_trust("ca.pem", Source::Env("AWS_CA_BUNDLE"))
    );
    Ok(())
}
