use super::*;

fn shared_files(config: &str, credentials: &str) -> ParsedFiles {
    ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: config.as_bytes(),
        }),
        credentials: Some(awscli_config::Contents {
            source: "credentials",
            bytes: credentials.as_bytes(),
        }),
        ..Default::default()
    })
}

fn admit_with(
    env: &BTreeMap<String, String>,
    files: &ParsedFiles,
    cli_profile: Option<&str>,
    cp: bool,
) -> Option<PythonReason> {
    effective_config::admit(&effective_config::Inputs {
        env,
        shared_files: files,
        cli_profile,
        cli_error_format: None,
        transfers: cp,
        boto_config_credentials: false,
    })
}

const KEYS: &str = "aws_access_key_id = config-key\naws_secret_access_key = config-secret\n";
const PROCESS: &str = "credential_process = helper\n";

fn process_cases() -> Vec<(String, String)> {
    let both = format!("{KEYS}{PROCESS}");
    let pair = "[work]\naws_access_key_id = shared-key\naws_secret_access_key = shared-secret\n";
    vec![
        (KEYS.into(), String::new()),
        (PROCESS.into(), String::new()),
        (
            format!("aws_secret_access_key = stale-secret\n{PROCESS}"),
            String::new(),
        ),
        (
            format!("aws_access_key_id =\n  nested = key\n{PROCESS}"),
            String::new(),
        ),
        (
            format!("{KEYS}credential_process =\n  nested = helper\n"),
            String::new(),
        ),
        (both.clone(), String::new()),
        (both.clone(), format!("[other]\n{KEYS}")),
        (both.clone(), "[work]\naws_session_token = token\n".into()),
        (
            both.clone(),
            "[work]\naws_access_key_id = shared-key\n".into(),
        ),
        (both, pair.into()),
        (KEYS.into(), format!("[work]\n{PROCESS}")),
    ]
}

// The native chain asks the shared credentials file, the process, then the
// config file, as botocore's does, so no mix of them is Python's, Windows
// included: the provider splits the command line by that system's rules
// there, as botocore does.
#[test]
fn a_credential_process_beside_static_keys_stays_native() {
    for (config, credentials) in process_cases() {
        let files = shared_files(
            &format!("[profile work]\n{config}[default]\n{config}"),
            &credentials,
        );
        for cp in [false, true] {
            let mut env = BTreeMap::new();
            assert_eq!(admit_with(&env, &files, Some("work"), cp), None);
            for variable in ["AWS_PROFILE", "AWS_DEFAULT_PROFILE"] {
                env.insert(variable.into(), "work".into());
                assert_eq!(admit_with(&env, &files, None, cp), None);
                env.remove(variable);
            }
            assert_eq!(
                admit_with(&env, &files, None, cp),
                None,
                "{config:?} {credentials:?}"
            );
        }
    }
}

type StaticCase = (
    Option<&'static str>,
    Option<&'static str>,
    String,
    String,
    bool,
);

const PAIR: &str = "aws_access_key_id = key\naws_secret_access_key = secret\n";
const KEY: &str = "aws_access_key_id = key\n";
const SECRET: &str = "aws_secret_access_key = secret\n";
const TOKEN: &str = "aws_session_token = token\n";

fn static_cases() -> Vec<StaticCase> {
    let pair_token = format!("{PAIR}{TOKEN}");
    let case = |key, secret, credentials: &str, config: &str, explicit| {
        (key, secret, credentials.into(), config.into(), explicit)
    };
    vec![
        case(Some("key"), Some("secret"), "", "", false),
        case(None, None, &pair_token, PAIR, false),
        case(None, None, PAIR, "", false),
        case(None, None, "", &pair_token, false),
        // The environment answers first, whatever the files mix.
        case(Some("key"), Some("secret"), KEY, SECRET, false),
        // An environment key without its secret stops the chain.
        case(Some("key"), None, PAIR, "", false),
        case(Some("key"), Some(""), PAIR, "", false),
        case(Some(""), Some("secret"), PAIR, "", false),
        case(Some("key"), None, PAIR, "", true),
        case(None, None, KEY, PAIR, false),
        case(None, None, KEY, SECRET, false),
        case(None, None, PAIR, TOKEN, false),
        case(None, None, "aws_secret_access_key = other\n", PAIR, false),
        case(None, None, "aws_session_token = other\n", PAIR, false),
        case(None, None, "aws_session_token = other\n", "", false),
    ]
}

// The native providers read one source at a time and report a missing
// secret key, as botocore's do, so a split pair is no longer Python's.
#[test]
fn static_credentials_split_across_sources_stay_native() {
    for (key, secret, credentials, config, explicit) in static_cases() {
        let files = shared_files(
            &format!("[default]\n{config}"),
            &format!("[default]\n{credentials}"),
        );
        let mut env = BTreeMap::new();
        if let Some(value) = key {
            env.insert("AWS_ACCESS_KEY_ID".into(), value.into());
        }
        if let Some(value) = secret {
            env.insert("AWS_SECRET_ACCESS_KEY".into(), value.into());
        }
        let profile = explicit.then_some("default");
        for cp in [false, true] {
            assert_eq!(
                admit_with(&env, &files, profile, cp),
                None,
                "{key:?} {secret:?} {credentials:?} {config:?} {explicit}"
            );
        }
    }
}

// The native chain reads the profiles botocore's parser found, so a header
// only `shlex` reads is no longer Python's.
#[test]
fn a_profile_botocore_loads_stays_native_whatever_its_header() {
    let cases: &[(&str, &str, Option<&str>)] = &[
        ("[profile work]\n", "", Some("work")),
        ("[profile \t work ]\n", "", Some("work")),
        ("[profile a.b@c:d/e+f%g_h]\n", "", Some("a.b@c:d/e+f%g_h")),
        ("[default]\n", "", None),
        ("[profile default]\n", "", None),
        ("", "", None),
        ("[profile \"space name\"]\n", "", Some("space name")),
        ("[profile \"work\"]\n", "", Some("work")),
        ("[profile \"default\"]\n", "", None),
        ("[profile \"work\"]\n", "[work]\n", Some("work")),
        ("", "[space name]\n", Some("space name")),
    ];
    for (config, credentials, profile) in cases {
        let files = shared_files(config, credentials);
        assert_eq!(
            admit_with(&BTreeMap::new(), &files, *profile, false),
            None,
            "{config:?} {credentials:?}"
        );
    }
}

// botocore disables its instance provider for `true` alone, in any case,
// and so does the native chain: no value is Python's.
#[test]
fn every_metadata_disable_value_stays_native() {
    let files = shared_files("", "");
    for value in [
        None,
        Some("true"),
        Some("TrUe"),
        Some("false"),
        Some("FaLsE"),
        Some(""),
        Some("0"),
        Some("1"),
        Some("yes"),
        Some(" true"),
        Some("false "),
    ] {
        let mut env = BTreeMap::new();
        if let Some(value) = value {
            env.insert("AWS_EC2_METADATA_DISABLED".into(), value.into());
        }
        for cp in [false, true] {
            assert_eq!(admit_with(&env, &files, None, cp), None, "{value:?}");
        }
    }
}

// The environment's legacy token is the native provider's too. Its expiry
// is, in the one form that provider reads; dateutil reads others.
#[test]
fn an_environment_expiry_only_dateutil_reads_is_python_s() {
    let files = shared_files("", "");
    for (name, value, python) in [
        ("AWS_SECURITY_TOKEN", "token", false),
        ("AWS_CREDENTIAL_EXPIRATION", "", false),
        ("AWS_CREDENTIAL_EXPIRATION", "2037-10-21T07:28:00Z", false),
        (
            "AWS_CREDENTIAL_EXPIRATION",
            "2037-10-21T07:28:00.5+05:30",
            false,
        ),
        ("AWS_CREDENTIAL_EXPIRATION", "2037-10-21 07:28:00Z", false),
        ("AWS_CREDENTIAL_EXPIRATION", "2037-10-21T07:28:00 UTC", true),
        ("AWS_CREDENTIAL_EXPIRATION", "2037-10-21T07:28:00", true),
        ("AWS_CREDENTIAL_EXPIRATION", "Oct 21 2037", true),
        ("AWS_CREDENTIAL_EXPIRATION", "2139722880", true),
    ] {
        let env = BTreeMap::from([
            ("AWS_ACCESS_KEY_ID".to_owned(), "key".to_owned()),
            ("AWS_SECRET_ACCESS_KEY".to_owned(), "secret".to_owned()),
            (name.to_owned(), value.to_owned()),
        ]);
        for cp in [false, true] {
            assert_eq!(
                admit_with(&env, &files, None, cp),
                python.then_some(PythonReason::CredentialForm),
                "{name}={value}"
            );
        }
    }
}

#[test]
fn a_container_credentials_endpoint_is_native_even_empty() {
    let files = shared_files("", "");
    for variable in [
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    ] {
        for value in ["/creds", ""] {
            let mut env = BTreeMap::from([(
                "AWS_CONTAINER_AUTHORIZATION_TOKEN".to_owned(),
                "token".to_owned(),
            )]);
            assert_eq!(admit_with(&env, &files, None, false), None);
            env.insert(variable.into(), value.into());
            for cp in [false, true] {
                assert_eq!(admit_with(&env, &files, None, cp), None);
            }
        }
    }
}

#[test]
fn boto_era_credential_sources_are_python_s() {
    // The shared files' legacy token is the native providers' too.
    let files = shared_files("[profile legacy]\naws_security_token = token\n", "");
    let mut env = BTreeMap::new();
    assert_eq!(admit_with(&env, &files, None, false), None);
    assert_eq!(admit_with(&env, &files, Some("legacy"), false), None);
    let boto = effective_config::admit(&effective_config::Inputs {
        env: &env,
        shared_files: &files,
        cli_profile: None,
        cli_error_format: None,
        transfers: true,
        boto_config_credentials: true,
    });
    assert_eq!(boto, Some(PythonReason::CredentialForm));
    env.insert("BOTO_CONFIG".into(), "/missing/boto".into());
    assert_eq!(admit_with(&env, &files, None, true), None);
    env.insert("AWS_CREDENTIAL_FILE".into(), String::new());
    assert_eq!(
        admit_with(&env, &files, None, false),
        Some(PythonReason::CredentialForm)
    );
}

#[test]
fn the_entrypoint_s_boto_answer_reaches_admission() {
    let files = files("");
    let env = BTreeMap::new();
    let mut result = awscli_argparse::parse(
        &["s3".to_owned(), "ls".to_owned()],
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    let verdict = route(
        &mut result,
        &unpack::Environment {
            directory: Path::new("."),
            variables: &HashMap::new(),
            files: &unpack::FsParamfiles,
            preferred_encoding: unpack::PreferredEncoding::Locale,
        },
        &Configuration {
            env: &env,
            shared_files: &files,
            boto_config_credentials: true,
            embedded_trust: true,
        },
    );
    assert_eq!(verdict, Verdict::Python(PythonReason::CredentialForm));
}

#[cfg(unix)]
type RawCase<'a> = (
    Vec<(&'static str, std::ffi::OsString)>,
    &'a ParsedFiles,
    bool,
);

#[cfg(unix)]
#[test]
fn non_unicode_environment_values_are_python_s() {
    use std::os::unix::ffi::OsStrExt;
    let raw = std::ffi::OsStr::from_bytes(b"/legacy/\xff").to_os_string();
    let pair = "[default]\naws_access_key_id = shared-key\naws_secret_access_key = shared-secret\n";
    let complete = shared_files("", pair);
    let empty = shared_files("", "");
    let cases: Vec<RawCase<'_>> = vec![
        (vec![("AWS_CREDENTIAL_FILE", raw.clone())], &empty, true),
        // The container provider refuses such a value itself.
        (
            vec![("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", raw.clone())],
            &empty,
            false,
        ),
        (
            vec![("AWS_CONTAINER_CREDENTIALS_FULL_URI", raw.clone())],
            &empty,
            false,
        ),
        // The instance metadata service's variables are read natively
        // as botocore reads them, and this one is not `true`.
        (
            vec![("AWS_EC2_METADATA_DISABLED", raw.clone())],
            &empty,
            false,
        ),
        (vec![("AWS_ACCESS_KEY_ID", raw.clone())], &complete, true),
        (
            vec![
                ("AWS_ACCESS_KEY_ID", raw.clone()),
                ("AWS_SECRET_ACCESS_KEY", "secret".into()),
            ],
            &complete,
            true,
        ),
        (
            vec![
                ("AWS_ACCESS_KEY_ID", "key".into()),
                ("AWS_SECRET_ACCESS_KEY", "secret".into()),
                ("AWS_SESSION_TOKEN", raw.clone()),
            ],
            &empty,
            true,
        ),
        (
            vec![
                ("AWS_ACCESS_KEY_ID", "key".into()),
                ("AWS_SECRET_ACCESS_KEY", "secret".into()),
            ],
            &empty,
            false,
        ),
    ];
    for (pairs, files, python) in cases {
        let env = cli_core::SnapshotEnv::from_pairs(pairs.clone());
        let reason = effective_config::admit(&effective_config::Inputs {
            env: &env,
            shared_files: files,
            cli_profile: None,
            cli_error_format: None,
            transfers: false,
            boto_config_credentials: false,
        });
        assert_eq!(
            reason,
            python.then_some(PythonReason::CredentialForm),
            "{pairs:?}"
        );
    }
}

// No value of an instance metadata setting is Python's. The native chain
// reads what botocore accepts, and what botocore refuses is refused
// natively (below), so the configuration stage admits every value.
#[test]
fn no_instance_metadata_setting_value_is_python_s() {
    let files = shared_files("", "");
    let digits = "9".repeat(4301);
    for (name, value) in [
        ("AWS_METADATA_SERVICE_TIMEOUT", "5"),
        ("AWS_METADATA_SERVICE_TIMEOUT", "0"),
        ("AWS_METADATA_SERVICE_TIMEOUT", "1.5"),
        ("AWS_METADATA_SERVICE_TIMEOUT", ""),
        ("AWS_METADATA_SERVICE_TIMEOUT", "\u{663}"),
        ("AWS_METADATA_SERVICE_TIMEOUT", " 1\u{3000}"),
        ("AWS_METADATA_SERVICE_TIMEOUT", "4294968"),
        ("AWS_METADATA_SERVICE_TIMEOUT", "9223372036854775808"),
        ("AWS_METADATA_SERVICE_TIMEOUT", digits.as_str()),
        ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "0"),
        ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "-1"),
        ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "many"),
        ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "9223372036854775808"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", ""),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "http://imds.invalid/p"),
        (
            "AWS_EC2_METADATA_SERVICE_ENDPOINT",
            "http://[fd00:ec2::254]:8080",
        ),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "127.0.0.1"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "not.a:valid:dom@in"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "ftp://imds.invalid"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "HTTP://imds.invalid"),
        (
            "AWS_EC2_METADATA_SERVICE_ENDPOINT",
            "http://user:secret@imds.invalid:080/a b?q#f",
        ),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", " http://imds.invalid"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "http://[fe80::1%eth0]"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "http://[zz]/"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE", "IPv6"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE", "IPv3"),
        ("AWS_EC2_METADATA_V1_DISABLED", "TRUE"),
        ("AWS_EC2_METADATA_V1_DISABLED", "1"),
        ("AWS_IMDS_USE_IPV6", "yes"),
    ] {
        let env = BTreeMap::from([(name.to_owned(), value.to_owned())]);
        for cp in [false, true] {
            assert_eq!(admit_with(&env, &files, None, cp), None, "{name}={value}");
        }
        let routed = evaluate(&["s3", "ls"], &env, &files);
        assert!(!matches!(routed, Verdict::Python(_)), "{name}={value}");
    }
    // The profile's keys are read the same way.
    let profile = shared_files("[default]\nmetadata_service_timeout = soon\n", "");
    assert_eq!(admit_with(&BTreeMap::new(), &profile, None, false), None);
}

/// The text of the failure a command ends with before it runs, when what
/// ends it is raised as the AWS CLI's session starts.
fn session_failure(args: &[&str], env: &[(&str, &str)], files: &ParsedFiles) -> Option<String> {
    let env: BTreeMap<String, String> = env
        .iter()
        .map(|(name, value)| ((*name).to_owned(), (*value).to_owned()))
        .collect();
    session_text(evaluate(args, &env, files))
}

/// The text of `verdict`'s failure, when it is one raised as the AWS CLI's
/// session starts.
fn session_text(verdict: Verdict) -> Option<String> {
    match verdict {
        Verdict::Failure(failure) if failure.kind == "session_initialized" => {
            assert_eq!(
                failure.class,
                awscli_argparse::failure::FailureClass::General
            );
            Some(failure.error_text(awscli_argparse::failure::Color::default()))
        }
        _ => None,
    }
}

// botocore refuses the instance metadata settings it cannot read as the
// CLI's session starts (`create_credential_resolver`), in its own words and
// CPython's. What only CPython's `int()` reads is refused too.
#[test]
fn instance_metadata_settings_botocore_refuses_fail_in_its_words() {
    const TIMEOUT: &str = "AWS_METADATA_SERVICE_TIMEOUT";
    const INTEGER: &str = "invalid literal for int() with base 10: ";
    let files = shared_files("", "");
    for (name, value, text) in [
        (TIMEOUT, "1.5", format!("{INTEGER}'1.5'")),
        (TIMEOUT, "", format!("{INTEGER}''")),
        (TIMEOUT, "'\"", format!("{INTEGER}'\\'\"'")),
        (TIMEOUT, "\x1c1", format!("{INTEGER}'\\x1c1'")),
        (TIMEOUT, "1_0", format!("{INTEGER}'1_0'")),
        (
            "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE",
            "IPv3",
            "Invalid EC2 Instance Metadata endpoint mode: IPv3 Valid endpoint modes \
             (case-insensitive): ('ipv4', 'ipv6')."
                .to_owned(),
        ),
        (
            "AWS_EC2_METADATA_SERVICE_ENDPOINT",
            "127.0.0.1",
            "Invalid endpoint EC2 Instance Metadata endpoint: 127.0.0.1".to_owned(),
        ),
        // A username and a password are never shown.
        (
            "AWS_EC2_METADATA_SERVICE_ENDPOINT",
            "http://user:secret@bad_host",
            "Invalid endpoint EC2 Instance Metadata endpoint: http://***@bad_host".to_owned(),
        ),
    ] {
        assert_eq!(
            session_failure(&["s3", "ls"], &[(name, value)], &files),
            Some(text),
            "{name}={value:?}"
        );
    }
    // The profile's keys are refused the same way, and a variable wins.
    let profile = shared_files("[profile dev]\nmetadata_service_timeout = soon\n", "");
    let dev = ["--profile", "dev", "s3", "ls"];
    assert_eq!(
        session_failure(&dev, &[], &profile),
        Some(format!("{INTEGER}'soon'"))
    );
    assert_eq!(session_failure(&dev, &[(TIMEOUT, "2")], &profile), None);
    assert_eq!(session_failure(&["s3", "ls"], &[], &profile), None);
}

// The refusal is for every command: ahead of anything the command reports,
// whatever would have signed it, and for one that signs nothing.
#[test]
fn instance_metadata_settings_botocore_refuses_fail_every_command() {
    let files = shared_files("", "");
    let refused = [
        ("AWS_METADATA_SERVICE_TIMEOUT", "1.5"),
        ("AWS_ACCESS_KEY_ID", "AKIDENV"),
        ("AWS_SECRET_ACCESS_KEY", "secret"),
        ("AWS_EC2_METADATA_DISABLED", "true"),
    ];
    for args in [
        &["s3", "ls"][..],
        &["s3", "ls", "--no-sign-request"],
        &["s3", "cp", "a", "s3://bucket/key"],
        &["s3", "rm", "s3://bucket/key"],
        // Each of these fails in the command's own parse, which comes
        // after the session's start.
        &["s3", "ls", "--bogus"],
        &["s3", "ls", "--page-size", "x"],
        &["s3", "cp"],
        &["s3"],
    ] {
        for env in [&refused[..1], &refused[..]] {
            assert_eq!(
                session_failure(args, env, &files).as_deref(),
                Some("invalid literal for int() with base 10: '1.5'"),
                "{args:?}"
            );
        }
    }
}

// What the AWS CLI raises before its session starts comes first: a failure
// of the main parse, or of a top-level argument. What is Python's stays
// Python's, which refuses the settings itself.
#[test]
fn the_session_s_start_follows_the_top_level_arguments() {
    let files = shared_files("", "");
    let env = BTreeMap::from([("AWS_METADATA_SERVICE_TIMEOUT".to_owned(), "1.5".to_owned())]);
    for (args, kind) in [
        (&["--color", "bogus", "s3", "ls"][..], "parse"),
        (
            &["s3", "ls", "--endpoint-url", "noscheme"],
            "endpoint_url_scheme",
        ),
        (
            &["s3", "ls", "--cli-connect-timeout", "x"],
            "invalid_integer",
        ),
        // One the command's own parse would fail after it.
        (
            &["--endpoint-url", "noscheme", "s3", "cp"],
            "endpoint_url_scheme",
        ),
        (&["--cli-read-timeout", "x", "s3", "cp"], "invalid_integer"),
        // `urlparse` raises for the brackets of the endpoint URL's host.
        (
            &["--endpoint-url", "http://[", "s3", "cp"],
            "endpoint_url_brackets",
        ),
        (
            &["s3", "ls", "--endpoint-url", "http://[zz]"],
            "endpoint_url_brackets",
        ),
        (&["s3", "ls", "--bogus"], "session_initialized"),
    ] {
        match evaluate(args, &env, &files) {
            Verdict::Failure(failure) => assert_eq!(failure.kind, kind, "{args:?}"),
            other => panic!("{args:?}: {other:?}"),
        }
    }
    for args in [
        &["s3", "ls", "help"][..],
        &["--version"],
        &["s3", "presign", "s3://bucket/key"],
        &["sts", "get-caller-identity"],
    ] {
        let routed = evaluate(args, &env, &files);
        assert!(matches!(routed, Verdict::Python(_)), "{args:?}: {routed:?}");
    }
}

// The AWS CLI compiles `--query` as it handles the top-level arguments,
// ahead of its session's start (`resolve_types`), and
// nearly every expression compiles. The native chain does not compile
// JMESPath, so the session's start comes ahead of a command that fails in
// its own parse whatever the expression is: also for one that does not
// compile, which is what Python reports. A command that parses is
// Python's, which compiles the expression.
#[test]
fn the_session_s_start_precedes_a_failing_command_with_any_query() {
    let files = shared_files("", "");
    let unset = BTreeMap::new();
    let env = BTreeMap::from([("AWS_METADATA_SERVICE_TIMEOUT".to_owned(), "1.5".to_owned())]);
    for query in ["[", "Contents"] {
        for command in [&["s3", "cp"][..], &["s3", "bogus"], &["s3", "cp", "x"]] {
            let args = [&["--query", query], command].concat();
            match evaluate(&args, &env, &files) {
                Verdict::Failure(failure) => {
                    assert_eq!(failure.kind, "session_initialized", "{args:?}");
                }
                other => panic!("{args:?}: {other:?}"),
            }
            match evaluate(&args, &unset, &files) {
                Verdict::Failure(failure) => assert_eq!(failure.kind, "parse", "{args:?}"),
                other => panic!("{args:?}: {other:?}"),
            }
        }
        for command in [&["s3", "ls"][..], &["s3", "ls", "--bogus"]] {
            let args = [&["--query", query], command].concat();
            assert_eq!(
                evaluate(&args, &env, &files),
                Verdict::Python(PythonReason::PythonOnlyGlobal),
                "{args:?}"
            );
        }
    }
}

// A selected profile without a section is botocore's ProfileNotFound, and
// the settings are not refused for it: a command that would run is
// Python's, and one that fails in its own parse reports that failure.
#[test]
fn a_profile_without_a_section_is_not_refused() {
    const TIMEOUT: &str = "AWS_METADATA_SERVICE_TIMEOUT";
    let files = shared_files("", "");
    let args = ["--profile", "nope", "s3", "ls", "--page-size", "x"];
    assert_eq!(session_failure(&args, &[(TIMEOUT, "x")], &files), None);
    let named = [(TIMEOUT, "x"), ("AWS_PROFILE", "nope")];
    assert_eq!(session_failure(&args[2..], &named, &files), None);
    let env = BTreeMap::from([(TIMEOUT.to_owned(), "x".to_owned())]);
    assert_eq!(
        evaluate(&["--profile", "nope", "s3", "ls"], &env, &files),
        Verdict::Python(PythonReason::ProfileLookup)
    );
}

/// How `args` is routed with `name` set to `value`, which need not be
/// Unicode.
#[cfg(unix)]
fn route_with_bytes(args: &[&str], name: &str, value: &[u8]) -> Verdict {
    use std::os::unix::ffi::OsStrExt;
    let value = std::ffi::OsStr::from_bytes(value);
    let env = cli_core::SnapshotEnv::from_pairs([(name, value)]);
    evaluate(args, &env, &files(""))
}

// An instance metadata variable that is not Unicode is never Python's. A
// number, a mode or an endpoint with such a byte is refused by name for
// every command, and the value is not shown.
#[cfg(unix)]
#[test]
fn an_instance_metadata_variable_that_is_not_unicode_is_refused_by_name() {
    for name in [
        "AWS_METADATA_SERVICE_TIMEOUT",
        "AWS_METADATA_SERVICE_NUM_ATTEMPTS",
        "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE",
        "AWS_EC2_METADATA_SERVICE_ENDPOINT",
    ] {
        let text = format!("the value of {name} is not valid Unicode");
        for args in [&["s3", "ls"][..], &["s3", "ls", "--bogus"]] {
            let refused = session_text(route_with_bytes(args, name, b"http://\xff"));
            assert_eq!(refused.as_deref(), Some(text.as_str()), "{name} {args:?}");
        }
    }
}

// The switches' are text that is not `true`. A credential variable that is
// not Unicode stays Python's.
#[cfg(unix)]
#[test]
fn an_instance_metadata_switch_that_is_not_unicode_is_native() {
    for name in [
        "AWS_EC2_METADATA_DISABLED",
        "AWS_EC2_METADATA_V1_DISABLED",
        "AWS_IMDS_USE_IPV6",
    ] {
        let routed = route_with_bytes(&["s3", "ls"], name, b"true\xff");
        assert!(matches!(routed, Verdict::Native(_)), "{name}: {routed:?}");
        // The command's own failure is the one reported.
        let failed = route_with_bytes(&["s3", "ls", "--bogus"], name, b"true\xff");
        assert!(matches!(failed, Verdict::Failure(_)), "{name}: {failed:?}");
        assert_eq!(session_text(failed), None, "{name}");
    }
    assert_eq!(
        route_with_bytes(&["s3", "ls"], "AWS_ACCESS_KEY_ID", b"\xff"),
        Verdict::Python(PythonReason::CredentialForm)
    );
}

// A proxy for the service is not an AWS product, so none is a reason for
// Python. The native transport forwards a cleartext request through a
// proxy that takes no credentials; for a proxy that takes them or is
// spoken to over TLS, and for any proxy in front of an `https` endpoint,
// the fetch fails natively with an error that says so.
#[test]
fn a_proxy_for_the_instance_metadata_service_is_never_python_s() {
    const ENDPOINT: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT";
    let files = files("");
    let route = |pairs: &[(&str, &str)]| {
        let env: BTreeMap<String, String> = pairs
            .iter()
            .map(|(name, value)| ((*name).to_owned(), (*value).to_owned()))
            .collect();
        match evaluate(&["s3", "ls"], &env, &files) {
            Verdict::Python(reason) => Some(reason),
            _ => None,
        }
    };
    let https = (ENDPOINT, "https://imds.invalid");
    for native in [
        &[("HTTP_PROXY", "http://proxy:3128")][..],
        &[("HTTP_PROXY", "proxy")],
        &[("HTTP_PROXY", "https://proxy:1")],
        &[("HTTP_PROXY", "http://user:secret@proxy:1")],
        &[("HTTP_PROXY", "http://[::1]:1")],
        &[https],
        &[https, ("HTTP_PROXY", "http://proxy:3128")],
        &[https, ("HTTPS_PROXY", "http://proxy:3128")],
        &[https, ("HTTPS_PROXY", "https://proxy:1")],
        &[https, ("HTTPS_PROXY", "http://user:secret@proxy:1")],
    ] {
        assert_eq!(route(native), None, "{native:?}");
    }
}
