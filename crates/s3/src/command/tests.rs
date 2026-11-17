use super::*;
use cli_core::client_config::{ClientConfig, Command, Resolved, Source};

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn listing_memory_is_explicit_while_transfers_delegate_the_environment() {
    let listing = ClientConfig::new(Command::Ls);
    let options = client_options(&listing, false);
    assert_eq!(options.throughput_target_gbps, 10.0);
    assert_eq!(options.memory_limit_in_bytes, 2 << 30);
    assert_eq!(
        client_options(&ClientConfig::new(Command::Cp), true).memory_limit_in_bytes,
        0
    );
}

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn client_record_preserves_transfer_socket_credentials_and_checksum_options() {
    use cli_core::client_config::{ChecksumMode, Trust};
    let client = ClientConfig {
        trust: Resolved::new(Trust::File("trust.pem".into()), Source::Flag("--ca-bundle")),
        signing: Resolved::new(false, Source::Flag("--no-sign-request")),
        keep_alive: Resolved::new(true, Source::Profile("tcp_keepalive")),
        connect_timeout_ms: Resolved::new(5000, Source::Flag("--cli-connect-timeout")),
        retry_attempts: Resolved::new(Some(4), Source::Env("AWS_MAX_ATTEMPTS")),
        target_gbps: Resolved::new(25.0, Source::S3("target_bandwidth")),
        part_size: Resolved::new(16 << 20, Source::S3("multipart_chunksize")),
        multipart_threshold: Some(Resolved::new(32 << 20, Source::S3("multipart_threshold"))),
        max_connections: Some(Resolved::new(3, Source::S3("max_concurrent_requests"))),
        direct_io: Some(Resolved::new(true, Source::S3("direct_io"))),
        request_checksum: Resolved::new(ChecksumMode::WhenRequired, Source::Default),
        response_checksum: Resolved::new(ChecksumMode::WhenRequired, Source::Default),
        ..ClientConfig::new(Command::Cp)
    };
    let options = client_options(&client, true);
    assert_client_identity_and_socket_options(&options);
    assert_client_transfer_options(&options);
}

#[cfg(unix)]
#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn client_record_preserves_non_unicode_trust_path_bytes() {
    use cli_core::client_config::Trust;
    use std::os::unix::ffi::OsStrExt;
    let path = std::path::Path::new(std::ffi::OsStr::from_bytes(b"ca\xff.pem"));
    let client = ClientConfig {
        trust: Resolved::new(Trust::File(path.into()), Source::Env("AWS_CA_BUNDLE")),
        ..ClientConfig::new(Command::Ls)
    };
    assert_eq!(
        client_options(&client, false).trust,
        crt::runtime::Trust::File {
            path: path.into(),
            setting: "AWS_CA_BUNDLE"
        }
    );
}

fn payload() -> std::io::Result<Vec<u8>> {
    let prefix = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX")
        .ok_or_else(|| std::io::Error::other("native payload prefix missing"))?;
    std::fs::read(std::path::PathBuf::from(prefix).join("awscli-v2.blob"))
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn proxy_inputs_reach_options_for_the_selected_endpoint_scheme()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let env = cli_core::SnapshotEnv::from_pairs([
        ("HTTPS_PROXY", "http://upper:80"),
        ("http_proxy", "http://lower:80"),
    ]);
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let client = ClientConfig::new(Command::Ls);
    for (endpoint, expected) in [
        ("http://localhost:4566", "http://lower:80"),
        ("https://localhost:4566", "http://upper:80"),
    ] {
        let globals = cli_core::command::Globals {
            endpoint_url: Some(endpoint.into()),
            ..Default::default()
        };
        let context = CommandContext {
            env: &env,
            shared_files: &files,
            globals: &globals,
            client: &client,
            directory: std::path::Path::new("/"),
            payload: &bytes,
        };
        let options = runtime_options(&context, Some("bucket"), false)?;
        assert_eq!(options.proxy_url.as_deref(), Some(expected));
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn listing_endpoint_rule_errors_reach_the_general_handler_without_a_request()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let env = std::collections::BTreeMap::<String, String>::new();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let mut client = ClientConfig::new(Command::Ls);
    client.use_accelerate_endpoint.value = true;
    for (bucket, region, endpoint, expected) in [
        (
            "bucket.with.dots",
            "us-east-1",
            None,
            "Path-style addressing cannot be used with S3 Accelerate",
        ),
        (
            "bucket",
            "us-east-1",
            Some("http://127.0.0.1:9"),
            "A custom endpoint cannot be combined with S3 Accelerate",
        ),
        (
            "bucket",
            "cn-north-1",
            None,
            "S3 Accelerate cannot be used in this region",
        ),
    ] {
        let globals = cli_core::command::Globals {
            region: Some(region.into()),
            endpoint_url: endpoint.map(str::to_owned),
            ..Default::default()
        };
        let context = CommandContext {
            env: &env,
            shared_files: &files,
            globals: &globals,
            client: &client,
            directory: std::path::Path::new("/"),
            payload: &bytes,
        };
        let result = runtime_options(&context, Some(bucket), false);
        let error = result.err().ok_or("expected endpoint rule failure")?;
        assert_eq!(error.category, Category::General);
        assert_eq!(error.message, expected.as_bytes());
    }
    Ok(())
}

fn refused_copy(
    env: &std::collections::BTreeMap<String, String>,
    bytes: &[u8],
) -> Result<PreparedRuntime, CommandFailure> {
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let mut client = ClientConfig::new(Command::Cp);
    client.use_accelerate_endpoint.value = true;
    let globals = cli_core::command::Globals {
        region: Some("us-west-2".into()),
        ..Default::default()
    };
    let context = CommandContext {
        env,
        shared_files: &files,
        globals: &globals,
        client: &client,
        directory: std::path::Path::new("/"),
        payload: bytes,
    };
    copy_runtime_options(&context, Some("bucket.with.dots"), false)
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn refused_endpoints_validate_the_client_before_returning_the_rule_error()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let mut prepared = refused_copy(&Default::default(), &bytes)?;
    let refusal = prepared.refusal.ok_or("expected an endpoint refusal")?;
    assert_eq!(
        refusal.message,
        "Path-style addressing cannot be used with S3 Accelerate"
    );
    assert_eq!(
        refusal.client_url.as_deref(),
        Some("https://s3.us-west-2.amazonaws.com")
    );
    prepared.options.trust = crt::runtime::Trust::Pem(b"not a certificate\n".to_vec());
    let endpoint_url = refusal.client_url.as_deref().unwrap_or_default();
    let error = validate_refused_client(&prepared.options, endpoint_url, false)
        .err()
        .ok_or("expected a client setup failure")?;
    assert_eq!(error.category, Category::General);
    assert_eq!(
        error.message,
        b"34 (AWS_ERROR_INVALID_ARGUMENT): An invalid argument was passed to a function."
    );
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn refused_endpoints_validate_the_client_without_resolving_a_proxy()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let env = std::collections::BTreeMap::from([(
        "HTTPS_PROXY".to_owned(),
        "http://proxy:bad".to_owned(),
    )]);
    let prepared = refused_copy(&env, &bytes)?;
    assert_eq!(prepared.options.proxy_url, None);
    let refusal = prepared.refusal.ok_or("expected an endpoint refusal")?;
    let endpoint_url = refusal.client_url.as_deref().unwrap_or_default();
    validate_refused_client(&prepared.options, endpoint_url, false)?;
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn bypass_resolution_distinguishes_configured_regions_from_the_sdk_default()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let client = ClientConfig::new(Command::Ls);
    for (flag, name, value, config, configured) in [
        (None, "AWS_REGION", "", "", false),
        (
            None,
            "AWS_DEFAULT_REGION",
            "",
            "[default]\nregion=\n",
            false,
        ),
        (Some("us-east-1"), "AWS_REGION", "", "", true),
        (None, "AWS_REGION", "us-east-1", "", true),
        (None, "AWS_DEFAULT_REGION", "us-east-1", "", true),
        (
            None,
            "AWS_REGION",
            "",
            "[default]\nregion=us-east-1\n",
            true,
        ),
    ] {
        let files = awscli_config::ParsedFiles::parse(awscli_config::Inputs {
            config: Some(awscli_config::Contents {
                bytes: config.as_bytes(),
                source: "config",
            }),
            ..Default::default()
        });
        let globals = cli_core::command::Globals {
            region: flag.map(str::to_owned),
            ..Default::default()
        };
        for bypass_list in [true, false] {
            let mut env = std::collections::BTreeMap::from([
                ("HTTPS_PROXY".to_owned(), "http://proxy:80".to_owned()),
                (name.into(), value.into()),
            ]);
            if bypass_list {
                env.insert("NO_PROXY".to_owned(), "s3.amazonaws.com".to_owned());
            }
            let context = CommandContext {
                env: &env,
                shared_files: &files,
                globals: &globals,
                client: &client,
                directory: std::path::Path::new("/"),
                payload: &bytes,
            };
            let options = runtime_options(&context, Some("bucket"), false)?;
            let bypassed = (bypass_list && !configured).then_some("s3.amazonaws.com");
            let proxy = bypassed.is_none().then_some("http://proxy:80");
            assert_eq!(options.proxy_bypass_netloc.as_deref(), bypassed, "{env:?}");
            assert_eq!(options.proxy_url.as_deref(), proxy, "{env:?}");
        }
    }
    Ok(())
}

fn assert_client_identity_and_socket_options(options: &RuntimeOptions) {
    assert!(options.no_sign_request);
    // An unsigned client asks no provider.
    assert_eq!(options.credentials, crt::credentials::Source::default());
    assert_eq!(
        options.trust,
        crt::runtime::Trust::File {
            path: "trust.pem".into(),
            setting: "--ca-bundle"
        }
    );
    assert!(options.keep_alive);
    assert_eq!(options.connect_timeout_ms, 5000);
    assert_eq!(options.max_attempts, Some(4));
}

fn assert_client_transfer_options(options: &RuntimeOptions) {
    assert_eq!(options.throughput_target_gbps, 25.0);
    assert_eq!(options.part_size, 16 << 20);
    assert_eq!(options.multipart_upload_threshold, Some(32 << 20));
    assert_eq!(options.single_request_threshold, Some(32 << 20));
    assert_eq!(options.max_active_connections_override, 3);
    assert!(options.file_io.is_some_and(|file_io| file_io.direct_io));
    assert_eq!(
        options.request_checksum_calculation,
        crt::runtime::ChecksumMode::WhenRequired
    );
    assert_eq!(
        options.response_checksum_validation,
        crt::runtime::ChecksumMode::WhenRequired
    );
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
#[expect(
    clippy::too_many_lines,
    reason = "one table keeps every scheme and proxy setting"
)]
fn client_proxy_bypass_uses_the_configured_client_host_for_each_scheme()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let mut client = ClientConfig::new(Command::Ls);
    client.addressing_style.value = cli_core::client_config::AddressingStyle::Virtual;
    for (endpoint, bucket, no_proxy, expected_url, expected_proxy, bypassed) in [
        (
            Some("http://localhost:9"),
            None,
            true,
            "http://localhost:9",
            None,
            Some("localhost:9"),
        ),
        (
            Some("https://s3.internal.test"),
            Some("bucket"),
            true,
            "https://bucket.s3.internal.test",
            None,
            Some("s3.internal.test"),
        ),
        (
            None,
            Some("bucket"),
            true,
            "https://bucket.s3.us-west-2.amazonaws.com",
            Some("http://secure:80"),
            None,
        ),
        (
            Some("http://s3.test"),
            None,
            true,
            "http://s3.test",
            Some("http://clear:80"),
            None,
        ),
        (
            Some("https://localhost"),
            None,
            false,
            "https://localhost",
            Some("http://secure:80"),
            None,
        ),
    ] {
        let mut pairs = vec![
            ("HTTP_PROXY", "http://clear:80"),
            ("HTTPS_PROXY", "http://secure:80"),
        ];
        if no_proxy {
            pairs.push(("no_proxy", "localhost, .internal.test"));
        }
        let env = cli_core::SnapshotEnv::from_pairs(pairs);
        let globals = cli_core::command::Globals {
            region: Some("us-west-2".into()),
            endpoint_url: endpoint.map(str::to_owned),
            ..Default::default()
        };
        let context = CommandContext {
            env: &env,
            shared_files: &files,
            globals: &globals,
            client: &client,
            directory: std::path::Path::new("/"),
            payload: &bytes,
        };
        let options = runtime_options(&context, bucket, false)?;
        assert_eq!(options.endpoint_url, expected_url);
        assert_eq!(options.proxy_url.as_deref(), expected_proxy);
        assert_eq!(options.proxy_bypass_netloc.as_deref(), bypassed);
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn proxy_no_verify_peer_variable_changes_no_runtime_option()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let client = ClientConfig::new(Command::Ls);
    let globals = cli_core::command::Globals {
        endpoint_url: Some("https://localhost:4566".into()),
        ..Default::default()
    };
    let options = |pairs: &[(&str, &str)]| {
        let env = cli_core::SnapshotEnv::from_pairs(pairs.iter().copied());
        let context = CommandContext {
            env: &env,
            shared_files: &files,
            globals: &globals,
            client: &client,
            directory: std::path::Path::new("/"),
            payload: &bytes,
        };
        // Each call walks a chain of its own, which is equal to no other.
        runtime_options(&context, Some("bucket"), false).map(|options| RuntimeOptions {
            credentials: crt::credentials::Source::default(),
            ..options
        })
    };
    let proxy = ("HTTPS_PROXY", "http://proxy:80");
    let verified = options(&[proxy])?;
    for value in ["1", "", "false"] {
        let unverified = options(&[proxy, ("AWS_PROXY_NO_VERIFY_PEER", value)])?;
        assert_eq!(unverified, verified);
        assert!(unverified.verify_peer);
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn refused_endpoints_name_no_bypassed_client() -> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let env = std::collections::BTreeMap::from([("NO_PROXY".to_owned(), "*".to_owned())]);
    let prepared = refused_copy(&env, &bytes)?;
    assert!(prepared.refusal.is_some());
    assert_eq!(prepared.options.proxy_bypass_netloc, None);
    Ok(())
}

#[test]
fn user_agent_reports_the_compiling_rustc_release() {
    let version = env!("RUST_VERSION");
    let release = version
        .split_once('-')
        .map_or(version, |(release, _)| release);
    let parts: Vec<&str> = release.split('.').collect();
    assert_eq!(parts.len(), 3, "{version}");
    assert!(
        parts
            .iter()
            .all(|part| !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_digit())),
        "{version}"
    );
}

#[test]
#[cfg_attr(
    miri,
    ignore = "opens a file without blocking, which Miri does not support"
)]
fn a_moves_source_delete_names_no_crt_transfer_feature() {
    use cli_core::client_config::Persona;
    let split = |agent: &str| {
        let (features, rest): (Vec<_>, Vec<_>) =
            agent.split(' ').partition(|part| part.starts_with("m/"));
        let codes: Vec<String> = features
            .iter()
            .flat_map(|part| part["m/".len()..].split(','))
            .map(str::to_owned)
            .collect();
        (codes, rest.join(" "))
    };
    for (persona, crt) in [(Persona::CrtPreferred, "Ae"), (Persona::Tuned, "Ag")] {
        let client = ClientConfig {
            persona: Some(Resolved::new(persona, Source::Default)),
            ..ClientConfig::new(Command::Mv)
        };
        let (record, record_rest) = split(&client_options(&client, false).user_agent);
        let (delete, delete_rest) = split(&source_delete_user_agent(&client));
        assert!(record.iter().any(|code| code == crt), "{record:?}");
        let expected: Vec<String> = record.into_iter().filter(|code| code != crt).collect();
        assert_eq!(delete, expected);
        assert!(delete.iter().any(|code| code == "G"), "{delete:?}");
        assert_eq!(delete_rest, record_rest);
        assert!(delete_rest.contains("md/command#s3.mv"), "{delete_rest}");
    }
}

// botocore walks its credential chain as it creates a signing client, so a
// provider that fails is the command's failure before any request, and an
// unsigned client asks no provider.
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn a_signing_client_walks_the_credential_chain_as_it_is_prepared()
-> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let globals = cli_core::command::Globals {
        endpoint_url: Some("http://localhost:4566".into()),
        ..Default::default()
    };
    let signed = ClientConfig::new(Command::Ls);
    let unsigned = ClientConfig {
        signing: Resolved::new(false, Source::Flag("--no-sign-request")),
        ..ClientConfig::new(Command::Ls)
    };
    let partial = cli_core::SnapshotEnv::from_pairs([("AWS_ACCESS_KEY_ID", "AKIDENV")]);
    let keys = cli_core::SnapshotEnv::from_pairs([
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "env-secret"),
    ]);
    let prepare = |env, client| {
        let context = CommandContext {
            env,
            shared_files: &files,
            globals: &globals,
            client,
            directory: std::path::Path::new("/"),
            payload: &bytes,
        };
        copy_runtime_options(&context, Some("bucket"), false)
    };
    let error = prepare(&partial, &signed)
        .err()
        .ok_or("a partial key pair must stop the chain")?;
    assert_eq!(error.category, Category::General);
    assert_eq!(
        String::from_utf8_lossy(&error.message),
        "Partial credentials found in env, missing: AWS_SECRET_ACCESS_KEY"
    );
    let prepared = prepare(&partial, &unsigned)?;
    assert_eq!(
        prepared.options.credentials,
        crt::credentials::Source::default()
    );
    let prepared = prepare(&keys, &signed)?;
    let crt::credentials::Source::Delegate(delegate) = prepared.options.credentials else {
        return Err("a signing client signs through its chain".into());
    };
    let (answered, answers) = std::sync::mpsc::channel();
    delegate.credentials(crt::credentials::Query::new(move |view| {
        let _ = answered.send(view.map(|view| view.access_key_id.to_owned()));
    }));
    assert_eq!(
        answers.recv_timeout(std::time::Duration::from_secs(10))?,
        Some("AKIDENV".into())
    );
    Ok(())
}
