use super::*;
use crate::SnapshotEnv;
#[test]
fn columns_follows_python_int_and_must_be_positive() {
    assert_eq!(columns_from_environment(&SnapshotEnv::default()), None);
    for value in ["0", "-5", "abc", "", "1.5", "1__2", "_2", "2_"] {
        assert_eq!(
            columns_from_environment(&SnapshotEnv::from_pairs([("COLUMNS", value)])),
            None
        );
    }
    for (value, columns) in [
        (" 1_20 ", 120),
        ("+001", 1),
        ("\t20\n", 20),
        ("\u{b}20", 20),
    ] {
        let env = SnapshotEnv::from_pairs([("COLUMNS", value)]);
        assert_eq!(columns_from_environment(&env), Some(columns));
        assert_eq!(formatter_width(&env, Some(300)), columns.saturating_sub(2));
    }
    assert_eq!(formatter_width(&SnapshotEnv::default(), Some(100)), 98);
    assert_eq!(formatter_width(&SnapshotEnv::default(), None), 78);
}
#[test]
fn columns_over_cpythons_digit_limit_is_unset() {
    let at_limit = format!("{}25", "0".repeat(4298));
    let env = SnapshotEnv::from_pairs([("COLUMNS", at_limit.as_str())]);
    assert_eq!(columns_from_environment(&env), Some(25));
    let over = format!("0{at_limit}");
    let env = SnapshotEnv::from_pairs([("COLUMNS", over.as_str())]);
    assert_eq!(columns_from_environment(&env), None);
    assert_eq!(formatter_width(&env, Some(100)), 98);
    assert_eq!(formatter_width(&env, None), 78);
}
#[test]
fn credential_diagnostics_follow_selection_without_secrets() {
    let files = awscli_config::ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: concat!(
                "[profile work]\naws_access_key_id = secret\n",
                "[profile process]\ncredential_process = cmd"
            )
            .as_bytes(),
        }),
        ..Default::default()
    });
    let env = SnapshotEnv::from_pairs([
        ("AWS_ACCESS_KEY_ID", "key"),
        ("AWS_SECRET_ACCESS_KEY", "secret"),
    ]);
    for (profile, source) in [
        (None, "environment"),
        (Some("work"), "shared profile"),
        (Some("process"), "credential_process"),
        (Some("missing"), "default provider chain"),
    ] {
        let globals = Globals {
            profile: profile.map(str::to_owned),
            ..Default::default()
        };
        let ctx = CommandContext {
            env: &env,
            shared_files: &files,
            globals: &globals,
            directory: Path::new("."),
            payload: &[],
            client: &crate::client_config::ClientConfig::default(),
        };
        assert_eq!(credential_source(&ctx), source);
    }
}
#[test]
fn argv_drops_the_program_name() {
    assert_eq!(command_argv(&["aws", "s3", "ls"]), &["s3", "ls"]);
    assert_eq!(command_argv::<&str>(&[]), &[] as &[&str]);
    assert_eq!(command_argv(&["aws"]), &[] as &[&str]);
}
