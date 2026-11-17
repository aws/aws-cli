use super::sample::{sample_transfer_value, sample_value};
use super::*;
use cli_core::client_config;
use std::collections::BTreeMap;

fn files(text: &str) -> ParsedFiles {
    ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: text.as_bytes(),
        }),
        ..Default::default()
    })
}

fn admit_ls(env: &[(&str, &str)], config: &str) -> Option<PythonReason> {
    admit_with(env, config, false, None)
}

fn admit_with(
    env: &[(&str, &str)],
    config: &str,
    cp: bool,
    profile: Option<&str>,
) -> Option<PythonReason> {
    let env = env
        .iter()
        .map(|(name, value)| ((*name).to_owned(), (*value).to_owned()))
        .collect::<BTreeMap<_, _>>();
    admit(&Inputs {
        env: &env,
        shared_files: &files(config),
        cli_profile: profile,
        cli_error_format: None,
        transfers: cp,
        boto_config_credentials: false,
    })
}

const UNSUPPORTED_ROWS: &[(Source, PythonReason)] = &[
    (Source::Env("AWS_CONFIG_FILE"), PythonReason::SharedFilePath),
    (
        Source::Env("AWS_SHARED_CREDENTIALS_FILE"),
        PythonReason::SharedFilePath,
    ),
    (
        Source::Profile("proxy_client_cert"),
        PythonReason::NetworkSetting,
    ),
    (
        Source::Env("AWS_CREDENTIAL_FILE"),
        PythonReason::CredentialForm,
    ),
    (Source::Profile("role_arn"), PythonReason::CredentialForm),
    (
        Source::Profile("source_profile"),
        PythonReason::CredentialForm,
    ),
    (
        Source::Profile("credential_source"),
        PythonReason::CredentialForm,
    ),
    (Source::Profile("mfa_serial"), PythonReason::CredentialForm),
    (Source::Profile("external_id"), PythonReason::CredentialForm),
    (
        Source::Profile("role_session_name"),
        PythonReason::CredentialForm,
    ),
    (
        Source::Profile("duration_seconds"),
        PythonReason::CredentialForm,
    ),
    (
        Source::Profile("web_identity_token_file"),
        PythonReason::CredentialForm,
    ),
    (Source::Env("AWS_ROLE_ARN"), PythonReason::CredentialForm),
    (
        Source::Env("AWS_WEB_IDENTITY_TOKEN_FILE"),
        PythonReason::CredentialForm,
    ),
    (
        Source::Env("AWS_ROLE_SESSION_NAME"),
        PythonReason::CredentialForm,
    ),
    (
        Source::Profile("sso_start_url"),
        PythonReason::CredentialForm,
    ),
    (Source::Profile("sso_region"), PythonReason::CredentialForm),
    (
        Source::Profile("sso_account_id"),
        PythonReason::CredentialForm,
    ),
    (
        Source::Profile("sso_role_name"),
        PythonReason::CredentialForm,
    ),
    (Source::Profile("sso_session"), PythonReason::CredentialForm),
    (
        Source::Profile("login_session"),
        PythonReason::CredentialForm,
    ),
    (Source::ErrorFormat, PythonReason::StructuredErrorFormat),
    (
        Source::Env("AWS_CLI_OUTPUT_ENCODING"),
        PythonReason::OutputEncoding,
    ),
    (Source::Profile("cli_history"), PythonReason::HistoryEnabled),
    (
        Source::S3("force_path_style"),
        PythonReason::EndpointSetting,
    ),
    (Source::S3("accelerate"), PythonReason::EndpointSetting),
    (
        Source::S3("disable_multi_region_access_points"),
        PythonReason::EndpointSetting,
    ),
    (
        Source::S3("payload_signing_enabled"),
        PythonReason::TransferSetting,
    ),
];

#[test]
fn unsupported_rows_keep_their_order_in_the_settings_table() {
    let actual = SETTINGS
        .iter()
        .filter_map(|setting| match setting.support {
            Support::Unsupported(reason) => Some((setting.source, reason)),
            Support::Honored(_) | Support::Ignored => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(actual, UNSUPPORTED_ROWS);
}

#[test]
fn overlapping_unsupported_settings_name_the_earlier_row() {
    let encoding = [("AWS_CLI_OUTPUT_ENCODING", "utf-8")];
    for (env, config, expected) in [
        (
            &encoding[..],
            "[default]\ncli_history = enabled\n",
            PythonReason::OutputEncoding,
        ),
        (
            &[][..],
            "[default]\ns3 =\n  force_path_style = true\n  payload_signing_enabled = true\n",
            PythonReason::EndpointSetting,
        ),
        (
            &encoding[..],
            "[default]\ns3 =\n  payload_signing_enabled = true\n",
            PythonReason::OutputEncoding,
        ),
    ] {
        assert_eq!(admit_ls(env, config), Some(expected), "{config:?}");
    }
}

fn read_names(source: Source) -> Vec<client_config::Source> {
    use client_config::Source as Read;
    match source {
        Source::Env(name) => vec![Read::Env(name)],
        Source::Profile(key) => vec![Read::Profile(key)],
        Source::Chain(name, key) => vec![Read::Env(name), Read::Profile(key)],
        Source::S3(key) => vec![Read::S3(key)],
        Source::ErrorFormat => vec![
            Read::Flag("--cli-error-format"),
            Read::Env("AWS_CLI_ERROR_FORMAT"),
            Read::Profile("cli_error_format"),
        ],
    }
}

#[test]
fn every_record_field_has_an_honored_row() {
    for field in Field::ALL {
        assert!(
            record_rows(field).next().is_some(),
            "ClientConfig {field:?} has no honored row"
        );
    }
}

#[test]
fn every_record_field_reads_exactly_its_rows_in_table_order() {
    for field in Field::ALL {
        let mut rows = record_rows(field)
            .flat_map(|row| read_names(row.source))
            .collect::<Vec<_>>();
        let mut read = field.settings().to_vec();
        if field == Field::Transfer {
            rows.sort_by_key(|source| source.setting_name());
            read.sort_by_key(|source| source.setting_name());
        }
        assert_eq!(rows, read, "{field:?}");
    }
}

#[test]
fn the_proxy_rows_are_the_spellings_the_proxy_reader_reads() {
    let rows = record_rows(Field::Proxy).collect::<Vec<_>>();
    assert!(rows.iter().all(|row| row.scope == Scope::All));
    let names = rows.iter().map(|row| row.source).collect::<Vec<_>>();
    assert_eq!(names, proxy::VARIABLES.map(Source::Env));
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one assertion group per record field"
)]
fn every_record_field_reads_rows_of_one_kind_of_source() {
    for row in record_rows(Field::CaBundle) {
        assert_eq!(row.scope, Scope::All);
        assert!(matches!(row.source, Source::Env(_) | Source::Profile(_)));
    }
    for row in record_rows(Field::Proxy) {
        assert!(matches!(row.source, Source::Env(_)));
        assert_eq!(row.matching, Match::Nonempty);
    }
    assert_eq!(record_rows(Field::Proxy).count(), proxy::VARIABLES.len());
    for row in record_rows(Field::TcpKeepalive) {
        assert_eq!(row.source, Source::Profile("tcp_keepalive"));
    }
    for (field, key) in [
        (Field::MaxAttempts, "max_attempts"),
        (Field::RetryMode, "retry_mode"),
    ] {
        let rows = record_rows(field).collect::<Vec<_>>();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].scope, Scope::All);
        assert!(matches!(rows[0].source, Source::Chain(_, chain_key) if chain_key == key));
    }
    for row in record_rows(Field::Transfer) {
        assert_eq!(row.scope, Scope::Transfer);
        assert!(matches!(row.source, Source::S3(_)));
    }
}

#[test]
fn the_checksum_rows_are_the_record_s_for_both_commands() {
    for (field, source) in [
        (
            Field::RequestChecksumCalculation,
            Source::Chain(
                "AWS_REQUEST_CHECKSUM_CALCULATION",
                "request_checksum_calculation",
            ),
        ),
        (
            Field::ResponseChecksumValidation,
            Source::Chain(
                "AWS_RESPONSE_CHECKSUM_VALIDATION",
                "response_checksum_validation",
            ),
        ),
    ] {
        let rows = record_rows(field).collect::<Vec<_>>();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].source, source);
        assert_eq!(rows[0].scope, Scope::All);
    }
    let env = [("AWS_REQUEST_CHECKSUM_CALCULATION", "when_required")];
    let config = "[default]\nresponse_checksum_validation = never\n";
    for cp in [false, true] {
        assert_eq!(admit_with(&env, config, cp, None), None);
    }
}

#[test]
fn the_transfer_and_memory_limit_rows_are_the_record_s_cp_only() {
    let transfer = record_rows(Field::Transfer).collect::<Vec<_>>();
    assert_eq!(transfer.len(), 11);
    assert!(transfer.iter().all(|row| row.scope == Scope::Transfer));
    let memory = record_rows(Field::MemoryLimit).collect::<Vec<_>>();
    // aws-c-s3 reads the MiB variable first.
    assert_eq!(
        memory.iter().map(|row| row.source).collect::<Vec<_>>(),
        [
            Source::Env("AWS_CRT_S3_MEMORY_LIMIT_IN_MB"),
            Source::Env("AWS_CRT_S3_MEMORY_LIMIT_IN_GIB"),
        ]
    );
    assert!(memory.iter().all(|row| row.scope == Scope::Transfer));
    for setting in SETTINGS {
        if setting.source == Source::S3("payload_signing_enabled") {
            assert_eq!(
                setting.support,
                Support::Unsupported(PythonReason::TransferSetting)
            );
        }
    }
}

#[test]
fn the_s3_block_s_endpoint_rows_are_the_record_s_for_both_commands() {
    let rows = record_rows(Field::S3Endpoint).collect::<Vec<_>>();
    let keys = [
        "addressing_style",
        "use_accelerate_endpoint",
        "use_dualstack_endpoint",
    ];
    assert_eq!(rows.len(), keys.len());
    for (row, key) in rows.iter().zip(keys) {
        assert_eq!(row.source, Source::S3(key));
        assert_eq!(row.scope, Scope::All);
    }
    let config = "[default]\ns3 =\n  addressing_style = bogus\n  use_accelerate_endpoint = true\n\
                  [profile scalar]\ns3 = virtual\n[profile bare]\ns3 =\n";
    for cp in [false, true] {
        assert_eq!(admit_with(&[], config, cp, None), None);
    }
}

#[test]
fn the_ca_bundle_rows_are_the_record_s_environment_first() {
    let config = "[default]\nca_bundle = /profile/ca.pem\n\
                  [profile \"spaced name\"]\nca_bundle = /spaced/ca.pem\n";
    assert_eq!(admit_with(&[], config, false, None), None);
    assert_eq!(admit_with(&[], config, true, Some("spaced name")), None);
    assert_eq!(
        record_rows(Field::CaBundle)
            .map(|row| row.source)
            .collect::<Vec<_>>(),
        [
            Source::Env("AWS_CA_BUNDLE"),
            Source::Profile("ca_bundle"),
            Source::Env("REQUESTS_CA_BUNDLE"),
        ]
    );
}

#[test]
fn samples_follow_the_row_s_consumer() {
    let sample = |source| {
        let setting = SETTINGS.iter().find(|setting| setting.source == source);
        setting.map(sample_value)
    };
    for (source, expected) in [
        (Source::Env("NO_PROXY"), "http://proxy.test:3128"),
        (Source::Env("no_proxy"), "http://proxy.test:3128"),
        (
            Source::Chain("AWS_USE_DUALSTACK_ENDPOINT", "use_dualstack_endpoint"),
            "value",
        ),
        (Source::S3("use_dualstack_endpoint"), "true"),
        (Source::S3("max_queue_size"), "100"),
        (Source::S3("max_bandwidth"), "10MB/s"),
        (Source::S3("disk_throughput"), "500MB/s"),
        (
            Source::Chain("AWS_SDK_UA_APP_ID", "sdk_ua_app_id"),
            "sample",
        ),
        (Source::Env("AWS_EXECUTION_ENV"), "sample"),
        (Source::Env("AWS_ENDPOINT_URL_S3"), "http://localhost:4566"),
        (Source::Profile("services"), "value"),
    ] {
        assert_eq!(sample(source), Some(expected), "{source:?}");
    }
    for row in record_rows(Field::Transfer) {
        let key = match row.source {
            Source::S3(key) => Some(key),
            Source::Env(_) | Source::Profile(_) | Source::Chain(..) | Source::ErrorFormat => None,
        };
        assert!(key.and_then(sample_transfer_value).is_some(), "{row:?}");
    }
}
