use super::*;
use crate::tests::{TestResult, env, files};

/// Variables, the lines of the profile, and what is expected of them.
type Row<'a, T> = (&'a [(&'a str, &'a str)], &'a str, T);

fn settings(
    variables: &[(&str, &str)],
    config: &str,
) -> Result<InstanceMetadataSettings, LoadError> {
    InstanceMetadataSettings::resolve(&env(variables), &files(config, ""), "default")
}

/// The message botocore, or CPython, gives for settings it refuses, which
/// is the one it raises as the CLI's session starts.
fn refusal(variables: &[(&str, &str)], config: &str) -> Option<String> {
    let refused = settings(variables, config).err();
    let parsed = files(config, "");
    let raised = InstanceMetadataSettings::refusal(&env(variables), &parsed, "default");
    assert_eq!(raised, refused);
    refused.map(|error| error.to_string())
}

#[test]
fn settings_default_to_the_services_own_address_and_one_try_of_one_second() -> TestResult {
    assert_eq!(
        settings(&[], "")?,
        InstanceMetadataSettings {
            base_url: "http://169.254.169.254/".into(),
            timeout: Timeout::Within(Duration::from_secs(1)),
            num_attempts: 1,
            v1_disabled: false,
        }
    );
    Ok(())
}

const CONFIG: &str = "[default]\nec2_metadata_service_endpoint = http://config.test:8080\n\
    ec2_metadata_service_endpoint_mode = IPv6\nec2_metadata_v1_disabled = True\n\
    metadata_service_timeout = 5\nmetadata_service_num_attempts = 3\nimds_use_ipv6 = false\n";

#[test]
fn every_setting_is_read_from_its_variable_before_the_profile() -> TestResult {
    assert_eq!(
        settings(&[], CONFIG)?,
        InstanceMetadataSettings {
            base_url: "http://config.test:8080".into(),
            timeout: Timeout::Within(Duration::from_secs(5)),
            num_attempts: 3,
            v1_disabled: true,
        }
    );
    let variables = [
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT", "http://env.test/p"),
        ("AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE", "ipv4"),
        ("AWS_EC2_METADATA_V1_DISABLED", "false"),
        ("AWS_METADATA_SERVICE_TIMEOUT", "7"),
        ("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "2"),
    ];
    assert_eq!(
        settings(&variables, CONFIG)?,
        InstanceMetadataSettings {
            base_url: "http://env.test/p".into(),
            timeout: Timeout::Within(Duration::from_secs(7)),
            num_attempts: 2,
            v1_disabled: false,
        }
    );
    // A variable that is set and empty still hides the profile's value,
    // and an empty endpoint is no endpoint (`IMDSFetcher._select_base_url`).
    let hidden = settings(&[("AWS_EC2_METADATA_SERVICE_ENDPOINT", "")], CONFIG)?;
    assert_eq!(hidden.base_url, "http://[fd00:ec2::254]/");
    // An empty number is one `int()` refuses.
    assert_eq!(
        refusal(&[("AWS_METADATA_SERVICE_TIMEOUT", "")], CONFIG).as_deref(),
        Some("invalid literal for int() with base 10: ''")
    );
    Ok(())
}

/// The rows of the endpoint a request goes to: the mode before
/// `imds_use_ipv6`, and a configured endpoint before both.
#[test]
fn the_base_url_is_the_endpoint_else_the_address_of_the_family() -> TestResult {
    const MODE: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE";
    const ENDPOINT: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT";
    let ipv6 = "http://[fd00:ec2::254]/";
    let ipv4 = "http://169.254.169.254/";
    let rows: [Row<'_, &str>; 9] = [
        (&[(MODE, "IPv6")], "", ipv6),
        (&[("AWS_IMDS_USE_IPV6", "true")], "", ipv6),
        (&[], "imds_use_ipv6 = TRUE\n", ipv6),
        (&[(MODE, "ipv4")], "imds_use_ipv6 = true\n", ipv4),
        (
            &[(ENDPOINT, "http://imds.invalid/")],
            "",
            "http://imds.invalid/",
        ),
        (
            &[],
            "ec2_metadata_service_endpoint = http://imds.invalid\n",
            "http://imds.invalid",
        ),
        (
            &[(ENDPOINT, "http://imds.invalid/p")],
            "",
            "http://imds.invalid/p",
        ),
        (
            &[(MODE, "ipv6"), (ENDPOINT, "http://imds.invalid")],
            "",
            "http://imds.invalid",
        ),
        (&[(ENDPOINT, "")], "", ipv4),
    ];
    for (variables, config, base_url) in rows {
        let config = format!("[default]\n{config}");
        assert_eq!(
            settings(variables, &config)?.base_url,
            base_url,
            "{variables:?} {config:?}"
        );
    }
    Ok(())
}

/// botocore refuses these as it builds its chain, and the words are its
/// own, so they are read here.
#[test]
fn settings_botocore_refuses_are_refused_in_its_words() {
    const MODE: &str = "Invalid EC2 Instance Metadata endpoint mode: {} \
        Valid endpoint modes (case-insensitive): ('ipv4', 'ipv6').";
    const ENDPOINT: &str = "Invalid endpoint EC2 Instance Metadata endpoint: {}";
    let rows: [Row<'_, String>; 6] = [
        (
            &[],
            "ec2_metadata_service_endpoint_mode = IPv3\n",
            MODE.replace("{}", "IPv3"),
        ),
        (
            &[("AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE", "")],
            "",
            MODE.replace("{}", ""),
        ),
        (
            &[("AWS_EC2_METADATA_SERVICE_ENDPOINT", "not.a:valid:dom@in")],
            "",
            ENDPOINT.replace("{}", "not.a:valid:dom@in"),
        ),
        (
            &[],
            "ec2_metadata_service_endpoint = 127.0.0.1\n",
            ENDPOINT.replace("{}", "127.0.0.1"),
        ),
        (
            &[("AWS_EC2_METADATA_SERVICE_ENDPOINT", "http://bad_host/")],
            "",
            ENDPOINT.replace("{}", "http://bad_host/"),
        ),
        (
            &[("AWS_EC2_METADATA_SERVICE_ENDPOINT", "http://h\t")],
            "",
            ENDPOINT.replace("{}", "http://h\t"),
        ),
    ];
    for (variables, config, message) in rows {
        let config = format!("[default]\n{config}");
        assert_eq!(refusal(variables, &config), Some(message));
    }
}

#[test]
fn settings_refuse_shared_files_that_did_not_parse() {
    let unparsed = files("[default\n", "");
    let error = InstanceMetadataSettings::resolve(&env(&[]), &unparsed, "default");
    assert_eq!(
        error,
        Err(LoadError::ConfigParse {
            path: "/home/.aws/config".into()
        })
    );
    // botocore refuses such files before it reads a setting.
    let float = env(&[("AWS_METADATA_SERVICE_TIMEOUT", "1.5")]);
    assert_eq!(
        InstanceMetadataSettings::refusal(&float, &unparsed, "default"),
        None
    );
}

/// A key with a nested block for its value is refused where the setting
/// is text, and is not `true` where it is a switch.
#[test]
fn a_setting_whose_value_is_a_nested_block_is_refused_by_name() -> TestResult {
    let config = "[default]\nmetadata_service_timeout =\n  true = true\n";
    assert_eq!(
        refusal(&[], config).as_deref(),
        Some("metadata_service_timeout must be a value, not a nested block")
    );
    let switches = "[default]\nec2_metadata_v1_disabled =\n  a = b\nimds_use_ipv6 =\n  a = b\n";
    assert_eq!(settings(&[], switches)?, settings(&[], "")?);
    Ok(())
}

/// A number is ASCII digits with a sign and whitespace around it; anything
/// else is refused with `int()`'s error.
#[test]
fn numbers_are_ascii_digits_with_a_sign() -> TestResult {
    const ATTEMPTS: &str = "AWS_METADATA_SERVICE_NUM_ATTEMPTS";
    for (value, expected) in [
        ("3", 3),
        (" 3\t", 3),
        ("+3", 3),
        ("-1", -1),
        ("007", 7),
        ("9223372036854775808", i64::MAX),
        ("-9223372036854775809", i64::MIN),
    ] {
        let attempts = settings(&[(ATTEMPTS, value)], "")?.num_attempts;
        assert_eq!(attempts, expected, "{value:?}");
    }
    for (value, literal) in [
        ("1.5", "'1.5'"),
        ("1_0", "'1_0'"),
        ("+", "'+'"),
        ("it's", "\"it's\""),
        ("\u{ff11}", "'\u{ff11}'"),
    ] {
        assert_eq!(
            refusal(&[(ATTEMPTS, value)], ""),
            Some(format!("invalid literal for int() with base 10: {literal}")),
            "{value:?}"
        );
    }
    Ok(())
}

/// urllib3 refuses a timeout that is not positive; a longer one than
/// CPython's socket waits is the longest it waits.
#[test]
fn a_timeout_is_positive_and_at_most_the_longest_wait() -> TestResult {
    const TIMEOUT: &str = "AWS_METADATA_SERVICE_TIMEOUT";
    let not_positive = |number: &str| {
        Timeout::Refused(format!(
            "Attempted to set connect timeout to {number}, but the timeout cannot be set to a \
             value less than or equal to 0."
        ))
    };
    for (value, expected) in [
        ("1", Timeout::Within(Duration::from_secs(1))),
        ("2147483", Timeout::Within(Duration::from_secs(2_147_483))),
        ("2147484", Timeout::Within(WAIT_MAX)),
        ("99999999999999999999", Timeout::Within(WAIT_MAX)),
        ("0", not_positive("0")),
        ("-0", not_positive("0")),
        ("-5", not_positive("-5")),
    ] {
        assert_eq!(
            settings(&[(TIMEOUT, value)], "")?.timeout,
            expected,
            "{value}"
        );
    }
    Ok(())
}

/// `Valid` and `Invalid` are what botocore's `is_valid_uri` returns.
#[test]
fn an_endpoint_is_valid_when_botocore_finds_a_host_in_it() {
    use Form::{Invalid, Unsupported, Valid};
    let long_label = format!("http://{}/", "a".repeat(64));
    for (endpoint, expected) in [
        ("http://h", Valid),
        ("http://h:abc", Valid),
        ("http://h:/", Valid),
        ("http://h.", Valid),
        ("http://1.2.3.4:80/", Valid),
        ("HTTP://H.Example./p", Valid),
        ("ftp://h", Valid),
        ("http://h?x", Valid),
        ("http://user@h/", Valid),
        ("http://h/a b", Valid),
        ("http://h/\u{e9}#\x7f", Valid),
        ("http://[fd00:ec2::254]", Valid),
        ("http://[::ffff:1.2.3.4]:8080/", Valid),
        // No scheme, which urllib3 takes for `http`.
        ("//h", Valid),
        ("//h:8080/x", Valid),
        ("//user@h/", Valid),
        ("//[::1]:8080", Valid),
        ("//bad_host", Invalid),
        ("///x", Invalid),
        ("//", Invalid),
        ("not.a:valid:dom@in", Invalid),
        ("127.0.0.1", Invalid),
        ("localhost:8080", Invalid),
        ("a b", Invalid),
        ("http://bad_host/", Invalid),
        ("http://.", Invalid),
        ("http://-a/", Invalid),
        ("http://a-/", Invalid),
        ("http://:80/", Invalid),
        ("http:///x", Invalid),
        ("http://h\t", Invalid),
        ("http://h\u{e9}\n", Invalid),
        (long_label.as_str(), Invalid),
        ("//[zz]/", Unsupported),
        ("http://[zz]/", Unsupported),
        ("http://[::1", Unsupported),
        ("http://a[::1]/", Unsupported),
        ("http://[::1]x/", Unsupported),
        ("http://[fe80::1%25eth0]/", Unsupported),
        (" http://h", Unsupported),
        ("\x01http://h", Unsupported),
        ("http://h /", Unsupported),
        ("http://h\u{e9}/", Unsupported),
    ] {
        assert_eq!(form(endpoint), expected, "{endpoint:?}");
    }
}

/// botocore accepts each of these as it builds its chain, so none is
/// refused there. Only a form this crate does not read fails a fetch
/// before anything is sent; [`super::super::Location`] refuses the rest
/// that it cannot send to.
#[test]
fn an_endpoint_botocore_accepts_is_refused_only_by_a_fetch_that_cannot_send_to_it() -> TestResult {
    const ENDPOINT: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT";
    let unsupported = Some(UNSUPPORTED_ENDPOINT);
    for (endpoint, refusal) in [
        ("http://imds.invalid", None),
        ("http://IMDS.Invalid:8080/p/q_r-s.t~u/", None),
        ("https://imds.invalid:443", None),
        ("http://[::1]:8080/p", None),
        ("HTTP://imds.invalid", None),
        ("Https://imds.invalid", None),
        ("http://user:password@imds.invalid/", None),
        ("http://imds.invalid?x", None),
        ("http://imds.invalid/p?x#f", None),
        ("http://imds.invalid/p;x/%41/a b", None),
        ("http://imds.invalid:", None),
        ("http://imds.invalid:0", None),
        ("http://imds.invalid:080", None),
        ("http://imds.invalid:abc", None),
        ("http://imds.invalid:65536", None),
        ("http://[zz]/", unsupported),
        ("http://[fe80::1%eth0]/", unsupported),
        (" http://imds.invalid", unsupported),
        ("http://imds.invalid\u{e9}/", unsupported),
    ] {
        let found = settings(&[(ENDPOINT, endpoint)], "")?;
        assert_eq!(found.unsendable().as_deref(), refusal, "{endpoint:?}");
    }
    assert_eq!(settings(&[], "")?.unsendable(), None);
    let ipv6 = settings(&[("AWS_IMDS_USE_IPV6", "true")], "")?;
    assert_eq!(ipv6.unsendable(), None);
    Ok(())
}

/// botocore accepts an endpoint that names a user and a password
/// (`is_valid_endpoint_url`). The settings hold it without them, and an
/// endpoint botocore refuses is named without them.
#[test]
fn an_endpoint_s_user_and_password_are_never_kept_or_shown() -> TestResult {
    const ENDPOINT: &str = "AWS_EC2_METADATA_SERVICE_ENDPOINT";
    let endpoint = "http://MARKER-user:MARKER-password@imds.invalid/base@x";
    let found = settings(&[(ENDPOINT, endpoint)], "")?;
    assert_eq!(found.base_url, "http://imds.invalid/base@x");
    assert!(!format!("{found:?}").contains("MARKER"));
    assert_eq!(
        refusal(
            &[(ENDPOINT, "http://MARKER-user:MARKER-password@bad_host/p")],
            ""
        )
        .as_deref(),
        Some("Invalid endpoint EC2 Instance Metadata endpoint: http://***@bad_host/p")
    );
    for (url, shown) in [
        ("http://169.254.169.254/", "http://169.254.169.254/"),
        ("http://host/a@b", "http://host/a@b"),
        ("http://u@h:1?q@x", "http://***@h:1?q@x"),
        ("http://a@b@host", "http://***@host"),
        ("//u:p@host/***@x", "//***@host/***@x"),
        ("no-authority", "no-authority"),
    ] {
        assert_eq!(masked(url), shown, "{url}");
    }
    assert_eq!(without_credentials("//u:p@host/***@x"), "//host/***@x");
    Ok(())
}

/// A variable that is not Unicode is refused by name where the setting is
/// text, and never shown, since an endpoint's may hold a password. Where
/// the setting is a switch it is not `true`, and the profile's key still
/// gives way to it.
#[cfg(unix)]
#[test]
fn a_variable_that_is_not_unicode_is_refused_by_name_or_is_not_true() -> TestResult {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let raw = |name: &str, value: &[u8]| {
        cli_core::SnapshotEnv::from_pairs([(name, OsStr::from_bytes(value))])
    };
    let parsed = files("", "");
    for name in [TIMEOUT, NUM_ATTEMPTS, ENDPOINT_MODE, ENDPOINT] {
        let env = raw(name, b"http://user:MARKER\xff@imds.invalid/");
        let refused = InstanceMetadataSettings::refusal(&env, &parsed, "default");
        let text = refused.map(|error| error.to_string());
        assert_eq!(
            text,
            Some(format!("the value of {name} is not valid Unicode")),
            "{name}"
        );
    }
    let config = files(
        "[default]\nimds_use_ipv6 = true\nec2_metadata_v1_disabled = true\n",
        "",
    );
    let read = |name| {
        let env = raw(name, b"true\xff");
        InstanceMetadataSettings::resolve(&env, &config, "default")
    };
    let ipv4 = read(USE_IPV6)?;
    assert_eq!((ipv4.base_url.as_str(), ipv4.v1_disabled), (BASE_URL, true));
    let v1 = read(V1_DISABLED)?;
    assert_eq!(
        (v1.base_url.as_str(), v1.v1_disabled),
        (BASE_URL_IPV6, false)
    );
    Ok(())
}
