use super::*;
use crate::client_config::{Command, Resolved, Source};

fn records(config: &ClientConfig, environment: proxy::Environment<'_>) -> Vec<Vec<u8>> {
    let mut lines = Vec::new();
    config.log_resolved(environment, |line| lines.push(line.to_owned()));
    lines
}

fn messages(config: &ClientConfig, environment: proxy::Environment<'_>) -> Vec<String> {
    records(config, environment)
        .iter()
        .map(|line| String::from_utf8_lossy(line).into_owned())
        .collect()
}

#[cfg(unix)]
#[test]
fn trust_file_line_keeps_path_bytes() {
    use std::os::unix::ffi::OsStrExt;
    let config = ClientConfig {
        trust: Resolved::new(
            Trust::File(std::ffi::OsStr::from_bytes(b"ca\xff.pem").into()),
            Source::Env("AWS_CA_BUNDLE"),
        ),
        ..ClientConfig::new(Command::Ls)
    };
    let expected = b"TLS trust: ca\xff.pem (from environment variable AWS_CA_BUNDLE)";
    assert!(
        records(&config, proxy::Environment::default())
            .iter()
            .any(|line| line == expected)
    );
}

#[test]
fn default_listing_diagnostics_match_target() {
    assert_eq!(
        messages(
            &ClientConfig::new(Command::Ls),
            proxy::Environment::default()
        ),
        [
            "Throughput target: 10 Gbps (from default)",
            "TLS trust: embedded awscli/botocore/cacert.pem (from default)",
            "TCP keepalive: disabled (from default)",
            "Connect timeout: 60000 ms (from default)",
            "Request signing: signed (from default)",
            "Retry mode: standard (from default)",
            "Max attempts: 3 (from default)",
            "S3 addressing style: auto (from default)",
            "S3 accelerate endpoint: false (from default)",
            "S3 block dual-stack endpoint: false (from default)",
            "Proxy bypass list: none",
        ]
    );
}

#[test]
fn default_copy_diagnostics_include_transfer_sources() {
    let copy = messages(
        &ClientConfig::new(Command::Cp),
        proxy::Environment::default(),
    );
    assert_eq!(
        &copy[..9],
        [
            "Transfer persona: newly_eligible (from default)",
            "Throughput target: 4 Gbps (from persona)",
            "Part size: 8388608 bytes (from persona)",
            "Multipart threshold: 8388608 bytes (from persona)",
            "Connection cap: 10 (from persona)",
            "File I/O options: CRT default (from default)",
            "Memory limit: 268435456 bytes, the target's tier (from default)",
            "Request checksum calculation: when_supported (from default)",
            "Response checksum validation: when_supported (from default)",
        ]
    );
    assert!(
        copy.iter()
            .any(|line| line == "Max attempts: 3 (from persona)")
    );
}

fn configured() -> ClientConfig {
    ClientConfig {
        persona: Some(Resolved::new(
            Persona::CrtPreferred,
            Source::S3("preferred_transfer_client"),
        )),
        target_gbps: Resolved::new(10.5, Source::S3("target_bandwidth")),
        should_stream: Some(Resolved::new(false, Source::S3("should_stream"))),
        disk_throughput_gbps: Some(Resolved::new(1.5, Source::S3("disk_throughput"))),
        direct_io: Some(Resolved::new(true, Source::S3("direct_io"))),
        memory_limit: Resolved::new(
            MemoryLimit::Override(512 << 20),
            Source::Env("AWS_CRT_S3_MEMORY_LIMIT_IN_MB"),
        ),
        trust: Resolved::new(
            Trust::File("/tmp/trust.pem".into()),
            Source::Flag("--ca-bundle"),
        ),
        signing: Resolved::new(false, Source::Flag("--no-sign-request")),
        connect_timeout_ms: Resolved::new(5000, Source::Flag("--cli-connect-timeout")),
        retry_attempts: Resolved::new(None, Source::Default),
        app_id: Some(Resolved::new(
            "demo".into(),
            Source::Profile("sdk_ua_app_id"),
        )),
        execution_env: Some(Resolved::new(
            "runner".into(),
            Source::Env("AWS_EXECUTION_ENV"),
        )),
        ..ClientConfig::new(Command::Ls)
    }
}

#[test]
fn configured_diagnostics_preserve_sources_and_hide_proxy_contents() {
    let config = configured();
    let lines = messages(
        &config,
        proxy::Environment {
            https: proxy::Pair {
                upper: Some("https://user:secret@proxy"),
                lower: None,
            },
            no_proxy: proxy::Pair {
                upper: Some("upper-private-host"),
                lower: Some("private-host"),
            },
            ..Default::default()
        },
    );
    for expected in [
        "Part size: CRT dynamic (from default)",
        "Multipart threshold: CRT default (from default)",
        "Connection cap: none (from default)",
        "File I/O should_stream: false (from profile key s3.should_stream)",
        "File I/O disk throughput: 1.5 Gbps (from profile key s3.disk_throughput)",
        "File I/O direct_io: true (from profile key s3.direct_io)",
        "Memory limit: 536870912 bytes (from environment variable AWS_CRT_S3_MEMORY_LIMIT_IN_MB)",
        "TLS trust: /tmp/trust.pem (from flag --ca-bundle)",
        "Connect timeout: 5000 ms (from flag --cli-connect-timeout)",
        "Request signing: anonymous (from flag --no-sign-request)",
        "Max attempts: CRT default (from default)",
        "Proxy bypass list: set (from environment variable no_proxy)",
        "User agent app id: demo (from profile key sdk_ua_app_id)",
        "User agent execution environment: runner (from environment variable AWS_EXECUTION_ENV)",
    ] {
        assert!(
            lines.iter().any(|line| line == expected),
            "{expected}: {lines:?}"
        );
    }
    assert!(
        lines
            .iter()
            .all(|line| !line.contains("private-host") && !line.contains("secret"))
    );
    let empty = messages(
        &config,
        proxy::Environment {
            no_proxy: proxy::Pair {
                upper: Some("*"),
                lower: Some(""),
            },
            ..Default::default()
        },
    );
    assert!(empty.iter().any(|line| line == "Proxy bypass list: none"));
    let mut env = std::collections::BTreeMap::new();
    env.insert("NO_PROXY".to_owned(), "localhost".to_owned());
    let uppercase = messages(&config, proxy::Environment::from_map_with(&env, false));
    let expected = "Proxy bypass list: set (from environment variable NO_PROXY)";
    assert!(uppercase.iter().any(|line| line == expected));
}

#[test]
fn trust_line_names_the_platform_store_and_the_embedded_entry() {
    let platform = ClientConfig {
        trust: Resolved::new(Trust::Platform, Source::Default),
        ..ClientConfig::new(Command::Cp)
    };
    let lines = messages(&platform, proxy::Environment::default());
    assert!(
        lines
            .iter()
            .any(|line| line == "TLS trust: platform store (from default)"),
        "{lines:?}"
    );
    let embedded = messages(
        &ClientConfig::new(Command::Ls),
        proxy::Environment::default(),
    );
    let expected = format!("TLS trust: embedded {CACERT_ENTRY_NAME} (from default)");
    assert!(embedded.contains(&expected), "{embedded:?}");
}
