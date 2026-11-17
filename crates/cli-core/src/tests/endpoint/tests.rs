use super::*;
use std::ffi::{OsStr, OsString};

#[test]
fn every_endpoint_source_is_checked_even_when_shadowed() {
    let files = parsed(
        concat!(
            "[services local]\ns3 =\n  endpoint_url = http://Key.test\n",
            "[profile svc]\nservices = local\n",
            "[profile url]\nendpoint_url = http://é.test\n",
            "[profile missing]\nservices = absent\n"
        ),
        None,
    );
    for (profile, expected) in [
        (None, true),
        (Some("svc"), false),
        (Some("url"), false),
        (Some("missing"), true),
    ] {
        assert_eq!(
            endpoint_config::configured_endpoints_ascii(&env(&[]), &files, "s3", None, profile),
            expected
        );
    }
    assert!(!endpoint_config::configured_endpoints_ascii(
        &env(&[]),
        &files,
        "s3",
        Some("http://hé.test"),
        None
    ));
    for variable in ["AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"] {
        assert!(!endpoint_config::configured_endpoints_ascii(
            &env(&[(variable, "http://é.test")]),
            &files,
            "s3",
            Some("http://ascii"),
            None
        ));
    }
}

#[test]
fn endpoint_configured_matches_selection_without_forcing_services_errors()
-> Result<(), EndpointError> {
    let files = parsed(
        concat!(
            "[services local]\ns3 =\n  endpoint_url = http://service.test\n",
            "[profile svc]\nservices = local\n",
            "[profile url]\nendpoint_url = http://profile.test\n",
            "[profile empty]\nendpoint_url =\n",
            "[profile missing]\nservices = absent\n",
            "[profile ignoring]\nendpoint_url = http://profile.test\n",
            "ignore_configured_endpoint_urls = true\n"
        ),
        None,
    );
    for variable in [None, Some(""), Some("http://env.test")] {
        let env = SnapshotEnv::from_pairs(variable.map(|value| ("AWS_ENDPOINT_URL_S3", value)));
        for profile in [
            None,
            Some("svc"),
            Some("url"),
            Some("empty"),
            Some("missing"),
            Some("ignoring"),
        ] {
            for flag in [None, Some("http://cli.test")] {
                let configured =
                    endpoint_config::endpoint_configured(&env, &files, "s3", flag, profile);
                match endpoint_config::resolve(&env, &files, "s3", flag, profile) {
                    Ok(value) => assert_eq!(value.endpoint.is_some(), configured),
                    Err(endpoint_config::EndpointError::MissingServicesSection(_)) => {
                        assert!(!configured)
                    }
                    Err(error) => return Err(error),
                }
            }
        }
    }
    Ok(())
}
use crate::endpoint_config::{EndpointError, bool_value, resolve};
#[test]
fn profile_settings_and_service_endpoints_use_parsed_files() {
    let files = parsed(
        concat!(
            "[services local]\n",
            "lambda=\n",
            " endpoint_url=http://service:9000/base\n",
            "s3=\n",
            " endpoint_url=http://not-lambda\n",
            "[profile dev]\n",
            "services=local\n",
            "endpoint_url=https://profile\n",
            "use_fips_endpoint=TRUE\n",
        ),
        None,
    );
    assert!(bool_value(Some("TRUE")));
    assert!(!bool_value(Some("true ")));
    for (service, expected) in [
        ("lambda", "http://service:9000/base"),
        ("s3", "http://not-lambda"),
        ("sqs", "https://profile"),
    ] {
        assert_eq!(
            resolve(&env(&[]), &files, service, None, Some("dev"))
                .unwrap()
                .endpoint
                .as_deref(),
            Some(expected)
        );
    }
}
#[test]
fn colon_delimiters_are_top_level_only() {
    let files = parsed(
        concat!(
            "[services local]\n",
            "s3=\n",
            " endpoint_url=http://service:9000/base?mode=test\n",
            "[profile dev]\n",
            "services: local\n",
            "endpoint_url: http://profile:4566/base?mode=test\n",
            "use_fips_endpoint: true\n",
        ),
        None,
    );
    assert_eq!(
        resolve(&env(&[]), &files, "s3", None, Some("dev"))
            .unwrap()
            .endpoint
            .as_deref(),
        Some("http://service:9000/base?mode=test")
    );
    assert!(matches!(
        parsed(
            "[services local]\ns3=\n endpoint_url: http://service:9000/base\n",
            None
        )
        .config
        .status,
        awscli_config::Status::ParseFailure(_)
    ));
}
#[test]
fn selected_services_section_must_exist() {
    let files = parsed("[profile dev]\nservices=missing\n", None);
    assert_eq!(
        resolve(&env(&[]), &files, "lambda", None, Some("dev")),
        Err(EndpointError::MissingServicesSection("missing".into()))
    );
    assert!(
        resolve(&env(&[]), &files, "lambda", None, None)
            .unwrap()
            .endpoint
            .is_none()
    );
    assert!(
        resolve(
            &env(&[]),
            &parsed("[default]\nservices=\n", None),
            "lambda",
            None,
            None
        )
        .unwrap()
        .endpoint
        .is_none()
    );
}
#[test]
fn top_level_folds_case_and_nested_preserves_it() {
    let files = parsed(
        concat!(
            "[services local]\n",
            "LAMBDA=\n",
            " ENDPOINT_URL=http://service:9000/base\n",
            "S3=\n",
            " endpoint_url=http://s3.local\n",
            "[profile dev]\n",
            "SERVICES=local\n",
            "ENDPOINT_URL=https://profile\n",
            "USE_FIPS_ENDPOINT=TRUE\n",
        ),
        None,
    );
    assert_eq!(
        resolve(&env(&[]), &files, "lambda", None, Some("dev"))
            .unwrap()
            .endpoint
            .as_deref(),
        Some("https://profile")
    );
    assert_eq!(
        resolve(&env(&[]), &files, "s3", None, Some("dev"))
            .unwrap()
            .endpoint
            .as_deref(),
        Some("http://s3.local")
    );
}
#[test]
fn command_line_beats_environment_and_ignore_disables_configured() {
    let files = ParsedFiles::parse(Inputs::default());
    let env = env(&[
        ("AWS_ENDPOINT_URL", "https://global"),
        ("AWS_ENDPOINT_URL_LAMBDA", ""),
    ]);
    assert_eq!(
        resolve(&env, &files, "lambda", Some("http://cli:8000"), None)
            .unwrap()
            .endpoint
            .as_deref(),
        Some("http://cli:8000")
    );
    assert_eq!(
        resolve(&env, &files, "lambda", None, None)
            .unwrap()
            .endpoint
            .as_deref(),
        Some("https://global")
    );
    let env = super::env(&[
        ("AWS_ENDPOINT_URL", "https://global"),
        ("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true"),
    ]);
    assert!(
        resolve(&env, &files, "lambda", None, None)
            .unwrap()
            .endpoint
            .is_none()
    );
    assert_eq!(
        resolve(&env, &files, "lambda", Some(""), None)
            .unwrap()
            .endpoint
            .as_deref(),
        Some("")
    );
}
#[test]
fn service_specific_environment_names() {
    let env = env(&[
        ("AWS_ENDPOINT_URL_LAMBDA", "https://lambda.example"),
        ("AWS_ENDPOINT_URL_S3", "https://s3.example"),
        ("AWS_ENDPOINT_URL_FOO_BAR", "https://hyphen.example"),
    ]);
    for (service, url) in [
        ("lambda", "https://lambda.example"),
        ("s3", "https://s3.example"),
        ("foo-bar", "https://hyphen.example"),
    ] {
        assert_eq!(
            resolve(
                &env,
                &ParsedFiles::parse(Inputs::default()),
                service,
                None,
                None
            )
            .unwrap()
            .endpoint
            .as_deref(),
            Some(url)
        );
    }
    assert_eq!(
        resolve(
            &env,
            &ParsedFiles::parse(Inputs::default()),
            "bad_service",
            None,
            None
        ),
        Err(EndpointError::InvalidServiceName)
    );
}
#[test]
fn higher_priority_endpoints_defer_missing_services_validation() {
    let files = parsed("[profile dev]\nservices=missing\n", None);
    assert_eq!(
        resolve(
            &env(&[]),
            &files,
            "lambda",
            Some("http://cli:8000"),
            Some("dev")
        )
        .unwrap()
        .endpoint
        .as_deref(),
        Some("http://cli:8000")
    );
    for (key, url) in [
        ("AWS_ENDPOINT_URL_LAMBDA", "http://lambda:8001"),
        ("AWS_ENDPOINT_URL", "http://global:8002"),
    ] {
        assert_eq!(
            resolve(&env(&[(key, url)]), &files, "lambda", None, Some("dev"))
                .unwrap()
                .endpoint
                .as_deref(),
            Some(url)
        );
    }
    assert!(
        resolve(
            &env(&[("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true")]),
            &files,
            "lambda",
            None,
            Some("dev")
        )
        .unwrap()
        .endpoint
        .is_none()
    );
    assert!(matches!(
        resolve(&env(&[]), &files, "lambda", None, Some("dev")),
        Err(EndpointError::MissingServicesSection(_))
    ));
}
#[test]
fn service_endpoint_beats_profile_and_clears_flags() {
    let files = parsed(
        concat!(
            "[services local]\n",
            "lambda=\n",
            " endpoint_url=http://lambda.local:9000/base\n",
            "[profile dev]\n",
            "services=local\n",
            "endpoint_url=https://profile.example\n",
            "use_fips_endpoint=true\n",
            "use_dualstack_endpoint=true\n",
        ),
        None,
    );
    for (service, url) in [
        ("lambda", "http://lambda.local:9000/base"),
        ("s3", "https://profile.example"),
    ] {
        let value = resolve(&env(&[]), &files, service, None, Some("dev")).unwrap();
        assert_eq!(value.endpoint.as_deref(), Some(url));
        assert!(!value.use_fips);
        assert!(!value.use_dual_stack);
    }
}
#[test]
fn credentials_settings_beat_config() {
    let files = parsed(
        "[profile dev]\nendpoint_url=https://config\nuse_dualstack_endpoint=true\n",
        Some("[dev]\nuse_fips_endpoint=true\nuse_dualstack_endpoint=false\n"),
    );
    let value = resolve(&env(&[]), &files, "s3", None, Some("dev")).unwrap();
    assert_eq!(value.endpoint.as_deref(), Some("https://config"));
    assert!(!value.use_fips);
    assert!(!value.use_dual_stack);
    let value = resolve(
        &env(&[("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true")]),
        &files,
        "s3",
        None,
        Some("dev"),
    )
    .unwrap();
    assert!(value.endpoint.is_none());
    assert!(value.use_fips);
    assert!(!value.use_dual_stack);
    let value = resolve(
        &env(&[
            ("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true"),
            ("AWS_USE_FIPS_ENDPOINT", ""),
        ]),
        &files,
        "s3",
        None,
        Some("dev"),
    )
    .unwrap();
    assert!(!value.use_fips);
}
#[test]
fn malformed_shared_file_defines_no_endpoint_settings() {
    let files = parsed(
        concat!(
            "[services local]\n",
            "s3=\n",
            " endpoint_url=http://s3.local\n",
            "[profile dev]\n",
            "services=local\n",
            "use_fips_endpoint=true\n",
            "line without a delimiter\n",
        ),
        None,
    );
    let value = resolve(&env(&[]), &files, "s3", None, Some("dev")).unwrap();
    assert!(value.endpoint.is_none());
    assert!(!value.use_fips);
}
#[test]
fn endpoint_urls_are_valid_as_botocore_s_client_creation_judges_them() {
    use crate::endpoint_config::is_valid_endpoint_url;
    let long = format!("http://{}", "a".repeat(64));
    for (url, valid) in [
        ("https://s3.example.com", true),
        ("http://localhost:4566/base", true),
        ("https://user:pw@Host.Example.:443/p?q#f", true),
        ("//host", true),
        (" http://host", true),
        ("http://[::1]:9000", true),
        ("not-a-url", false),
        ("localhost:4566", false),
        ("http://", false),
        ("http://a_b", false),
        ("http://-a", false),
        ("http://a..b", false),
        ("http://h\tost", false),
        ("http://[::1", false),
        (long.as_str(), false),
    ] {
        assert_eq!(is_valid_endpoint_url(url), valid, "{url:?}");
    }
}
#[test]
fn an_endpoint_url_s_path_is_the_one_urlsplit_finds() {
    for (url, path) in [
        ("http://h:1/a/b?q#f", "/a/b"),
        ("http://h:1#/f", ""),
        ("http://h:1?\u{e9}", ""),
        ("http://\u{e9}@h/p", "/p"),
        (" //h/\u{e9}", "/\u{e9}"),
        ("localhost:4566/p", "4566/p"),
        ("h/p", "h/p"),
    ] {
        assert_eq!(endpoint_config::url_path(url), path, "{url:?}");
    }
}
#[test]
fn selected_endpoint_urls_resolve_natively_where_both_parsers_read_them_alike() {
    use crate::endpoint_config::selected_endpoint_resolves_natively;
    let files = parsed("", None);
    for (url, native) in [
        ("https://user:pw@Host.Example.:8443/p", true),
        ("http://127.0.0.1:9", true),
        ("https://127.0.0.1:9/base/", true),
        ("https://127.0.0.1:00080", true),
        ("https://127.0.0.1:65535", true),
        ("https://127.0.0.1:9/?", true),
        ("http://[::1]:9000/", true),
        ("http://a_b", true),
        ("https://user:pw@Host.Example.:443/p", false),
        ("https://127.0.0.1:/", false),
        ("ftp://127.0.0.1:1", false),
        ("HTTPS://127.0.0.1:9", false),
        ("Http://127.0.0.1:9", false),
        (" http://127.0.0.1:9", false),
        ("//127.0.0.1:9", false),
        ("https:/127.0.0.1:9", false),
        ("https://127.0.0.1:9/?a=b", false),
        ("https://127.0.0.1:9?a=b", false),
        ("https://127.0.0.1:9/#f", false),
        ("https://127.0.0.1:9/?#f", false),
        ("https://127.0.0.1:abc", false),
        ("https://127.0.0.1:+80", false),
        ("https://127.0.0.1:70000", false),
        ("http://[::1]:x", false),
        ("https://user:pw@Host.Example.:443/p?q#f", false),
        ("http:x://127.0.0.1:9/p", false),
        ("not-a-url", false),
    ] {
        for (variables, flag) in [
            (env(&[("AWS_ENDPOINT_URL", url)]), None),
            (
                env(&[("AWS_ENDPOINT_URL", "http://127.0.0.1:1")]),
                Some(url),
            ),
        ] {
            assert_eq!(
                selected_endpoint_resolves_natively(&variables, &files, "s3", flag, None),
                native,
                "{url:?} {flag:?}"
            );
        }
    }
    let profile = parsed("[default]\nendpoint_url = ftp://127.0.0.1:1\n", None);
    assert!(!selected_endpoint_resolves_natively(
        &env(&[]),
        &profile,
        "s3",
        None,
        None
    ));
    let ignored = env(&[("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true")]);
    assert!(selected_endpoint_resolves_natively(
        &ignored, &profile, "s3", None, None
    ));
    assert!(!selected_endpoint_resolves_natively(
        &ignored,
        &profile,
        "s3",
        Some("HTTPS://127.0.0.1:9"),
        None
    ));
}
#[cfg(unix)]
#[test]
fn a_non_unicode_winning_endpoint_is_not_replaced_by_a_lower_priority_one() {
    use crate::endpoint_config::configured_endpoint_fails;
    use std::os::unix::ffi::OsStrExt;
    let fallback = (
        "AWS_ENDPOINT_URL",
        std::ffi::OsString::from("http://127.0.0.1:4566"),
    );
    let winner = std::ffi::OsStr::from_bytes(b"http://bad-\xff/").to_os_string();
    let files = parsed("", None);
    let valid = crate::SnapshotEnv::from_pairs([fallback.clone()]);
    assert!(!configured_endpoint_fails(&valid, &files, "s3", None, None));
    let shadowed = crate::SnapshotEnv::from_pairs([fallback, ("AWS_ENDPOINT_URL_S3", winner)]);
    assert!(configured_endpoint_fails(
        &shadowed, &files, "s3", None, None
    ));
}
#[test]
fn client_creation_fails_on_a_missing_or_empty_services_section() {
    use crate::endpoint_config::configured_endpoint_fails;
    let files = parsed(
        concat!(
            "[default]\nservices = absent\nendpoint_url = https://unused.example.com\n",
            "[profile empty]\nservices = blank\n[services blank]\n",
            "[profile bad]\nendpoint_url = not-a-url\n",
        ),
        None,
    );
    let none = env(&[]);
    assert!(configured_endpoint_fails(&none, &files, "s3", None, None));
    assert!(configured_endpoint_fails(
        &none,
        &files,
        "s3",
        None,
        Some("empty")
    ));
    assert!(configured_endpoint_fails(
        &none,
        &files,
        "s3",
        None,
        Some("bad")
    ));
    assert!(!configured_endpoint_fails(
        &none,
        &files,
        "s3",
        Some(OsStr::new("http://h:1")),
        None
    ));
    let local = env(&[("AWS_ENDPOINT_URL_S3", "http://localhost:4566")]);
    assert!(!configured_endpoint_fails(&local, &files, "s3", None, None));
    assert_eq!(
        resolve(&local, &files, "lambda", None, Some("empty")),
        Err(EndpointError::MissingServicesSection("blank".into()))
    );
}
#[cfg(unix)]
fn not_unicode_url() -> OsString {
    use std::os::unix::ffi::OsStrExt;
    OsStr::from_bytes(b"http://\xff").to_os_string()
}
#[cfg(windows)]
fn not_unicode_url() -> OsString {
    use std::os::windows::ffi::OsStringExt;
    let units: Vec<u16> = "http://".encode_utf16().chain([0xdcff]).collect();
    OsString::from_wide(&units)
}
#[test]
fn client_creation_judges_the_command_line_s_endpoint_url_first() {
    use crate::endpoint_config::configured_endpoint_fails;
    let files = parsed("[default]\nendpoint_url = not-a-url\n", None);
    for (url, fails) in [
        (OsString::from("x"), true),
        (OsString::from("http://a_b"), true),
        (not_unicode_url(), true),
        (OsString::from("http://h:1"), false),
    ] {
        assert_eq!(
            configured_endpoint_fails(&env(&[]), &files, "s3", Some(&url), None),
            fails,
            "{url:?}"
        );
    }
    let ignored = env(&[("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true")]);
    assert!(configured_endpoint_fails(
        &ignored,
        &files,
        "s3",
        Some(OsStr::new("x")),
        None
    ));
    assert!(!configured_endpoint_fails(
        &ignored, &files, "s3", None, None
    ));
}
#[test]
fn an_endpoint_url_s_port_is_the_one_urlsplit_finds() {
    for (url, port) in [
        ("http://h:1/p:2", Some("1")),
        ("http://u:2@h:1?q:3#f:4", Some("1")),
        ("http://u@v@h:1", Some("1")),
        ("http://h:1:2", Some("1:2")),
        ("http://[::1]:9000", Some("9000")),
        ("http://[::1]", None),
        ("http://h:", None),
        ("http://h", None),
        ("h:1", None),
    ] {
        assert_eq!(endpoint_config::url_port(url), port, "{url:?}");
    }
}
#[test]
fn a_port_is_what_urlsplit_reads_as_one() {
    for (text, port) in [
        ("1", true),
        ("0080", true),
        ("65535", true),
        ("65536", false),
        ("112351", false),
        ("+9", false),
        ("1_0", false),
        ("x9", false),
        ("9 ", false),
        ("1:2", false),
    ] {
        assert_eq!(endpoint_config::is_port(text), port, "{text:?}");
    }
}

#[cfg(unix)]
#[test]
fn switches_that_are_not_unicode_are_present() -> Result<(), EndpointError> {
    use std::os::unix::ffi::OsStrExt;
    let not_unicode = std::ffi::OsStr::from_bytes(b"\xff");
    let files = parsed(
        concat!(
            "[default]\nuse_fips_endpoint = true\nuse_dualstack_endpoint = true\n",
            "ignore_configured_endpoint_urls = true\n",
            "endpoint_url = http://profile.test\n"
        ),
        None,
    );
    let profile_only = endpoint_config::resolve(&env(&[]), &files, "s3", None, None)?;
    assert!(profile_only.use_fips && profile_only.use_dual_stack);
    assert!(profile_only.ignore_configured);
    for variable in [
        "AWS_USE_FIPS_ENDPOINT",
        "AWS_USE_DUALSTACK_ENDPOINT",
        "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS",
    ] {
        let env = SnapshotEnv::from_pairs([(variable, not_unicode)]);
        let values = endpoint_config::resolve(&env, &files, "s3", None, None)?;
        let ignored = variable == "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS";
        assert_eq!(values.ignore_configured, !ignored, "{variable}");
        assert_eq!(values.endpoint.is_some(), ignored, "{variable}");
        assert_eq!(
            endpoint_config::endpoint_configured(&env, &files, "s3", None, None),
            ignored,
            "{variable}"
        );
        if !ignored {
            let off = variable == "AWS_USE_FIPS_ENDPOINT";
            assert_eq!(values.use_fips, !off, "{variable}");
            assert_eq!(values.use_dual_stack, off, "{variable}");
        }
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn endpoint_urls_that_are_not_unicode_are_present() {
    use std::os::unix::ffi::OsStrExt;
    let not_unicode = std::ffi::OsStr::from_bytes(b"\xff");
    let empty = parsed("", None);
    for variable in ["AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"] {
        let env = SnapshotEnv::from_pairs([(variable, not_unicode)]);
        assert!(endpoint_config::endpoint_configured(
            &env, &empty, "s3", None, None
        ));
        assert!(!endpoint_config::configured_endpoints_ascii(
            &env,
            &empty,
            "s3",
            Some("http://ascii"),
            None
        ));
        assert!(endpoint_config::configured_endpoint_fails(
            &env, &empty, "s3", None, None
        ));
        assert!(!endpoint_config::selected_endpoint_resolves_natively(
            &env, &empty, "s3", None, None
        ));
    }
}
