use super::*;
mod native;
#[test]
fn first_signing_scheme_and_optional_region() {
    assert_eq!(parse_signing_region(br#"{}"#).ok(), Some(None));
    assert_eq!(
        parse_signing_region(br#"{"authSchemes":[]}"#).ok(),
        Some(None)
    );
    assert_eq!(
        parse_signing_region(
            br#"{
            "authSchemes": [
                {"name":"sigv4","signingRegion":"us-east-1"},
                {"signingRegion":"ignored"}
            ]
        }"#
        )
        .ok(),
        Some(Some("us-east-1".into()))
    );
    assert!(parse_signing_region(br#"{"authSchemes":4}"#).is_err());
    assert!(parse_signing_region(br#"{"authSchemes":[{},4]}"#).is_err());
    assert!(parse_signing_region(br#"{"authSchemes":[{},{"signingRegion":4}]}"#).is_err());
}
#[test]
fn explicit_endpoint_presence_alone_forces_path_style() {
    assert_eq!(
        parameters("us-east-1", Some("b"), Options::default()).force_path_style,
        Some(false)
    );
    for endpoint in ["", "http://localhost:4566/base"] {
        let params = parameters(
            "us-east-1",
            Some("b"),
            Options {
                endpoint: Some(endpoint),
                ..Options::default()
            },
        );
        assert_eq!(params.force_path_style, Some(true));
        assert_eq!(params.endpoint, Some(endpoint));
    }
}
#[test]
fn client_netloc_is_selected_only_for_a_bypass_list() {
    assert_eq!(ClientNetloc::select(false, true), ClientNetloc::None);
    assert_eq!(ClientNetloc::select(false, false), ClientNetloc::None);
    assert_eq!(
        ClientNetloc::select(true, true),
        ClientNetloc::ConfiguredRegion
    );
    assert_eq!(
        ClientNetloc::select(true, false),
        ClientNetloc::DefaultRegion
    );
}
#[test]
fn configured_missing_services_diagnostic() {
    let files = awscli_config::ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: b"[profile dev]\nservices = missing\n",
        }),
        ..Default::default()
    });
    let env = std::collections::BTreeMap::<String, String>::new();
    let mut stderr = Vec::new();
    let result = configured_values(&env, &files, None, Some("dev"), &mut stderr);
    assert!(matches!(result, Err(EndpointError::UserVisibleFailure)));
    assert_eq!(
        stderr,
        b"The profile is configured to use the services section but the \"m\
            issing\" services configuration does not exist.\n"
    );
}
fn payload() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let prefix = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX")
        .ok_or("fallback payload prefix is required")?;
    Ok(std::fs::read(
        std::path::PathBuf::from(prefix).join("awscli-v2.blob"),
    )?)
}
fn expect_endpoint(resolved: Resolved) -> Result<Endpoint, Box<dyn std::error::Error>> {
    match resolved {
        Resolved::Endpoint(endpoint) => Ok(endpoint),
        Resolved::RuleError(error) => {
            Err(format!("unexpected rule error: {}", error.message).into())
        }
    }
}
fn expect_rule_error(resolved: Resolved) -> Result<RuleError, Box<dyn std::error::Error>> {
    match resolved {
        Resolved::RuleError(error) => Ok(error),
        Resolved::Endpoint(endpoint) => Err(format!(
            "expected a rule error, got {}",
            String::from_utf8_lossy(&endpoint.url)
        )
        .into()),
    }
}
fn test_resolve(
    view: pyload::View<'_>,
    region: &str,
    bucket: Option<&str>,
    options: Options<'_>,
) -> Result<Endpoint, Box<dyn std::error::Error>> {
    expect_endpoint(resolve(view, region, bucket, options)?)
}
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn s3_fips_dualstack_custom_endpoint() -> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    for (options, expected) in [
        (
            Options {
                use_fips: true,
                ..Default::default()
            },
            "https://bucket.s3-fips.us-east-1.amazonaws.com",
        ),
        (
            Options {
                use_dual_stack: true,
                ..Default::default()
            },
            "https://bucket.s3.dualstack.us-east-1.amazonaws.com",
        ),
        (
            Options {
                endpoint: Some("http://localhost:4566/base"),
                ..Default::default()
            },
            "http://localhost:4566/base/bucket",
        ),
    ] {
        let endpoint = test_resolve(view, "us-east-1", Some("bucket"), options)?;
        assert_eq!(endpoint.url, expected.as_bytes());
    }
    Ok(())
}
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn s3_endpoint_signing_region() -> Result<(), Box<dyn std::error::Error>> {
    let bytes = payload()?;
    let endpoint = test_resolve(
        pyload::View::new(&bytes)?,
        "aws-global",
        Some("bucket"),
        Options::default(),
    )?;
    assert_eq!(endpoint.url, b"https://bucket.s3.amazonaws.com");
    assert_eq!(endpoint.signing_region.as_deref(), Some("us-east-1"));
    Ok(())
}

#[test]
fn addressing_style_and_acceleration_follow_botocore() {
    use AddressingStyle::{Auto, Path, Virtual};
    let local = Some("http://localhost:4566");
    let accelerate = Some("https://s3-accelerate.amazonaws.com");
    for (style, accelerated, endpoint, expected) in [
        (Auto, false, None, false),
        (Virtual, false, None, false),
        (Path, false, None, true),
        (Path, true, None, false),
        (Auto, false, local, true),
        (Path, false, local, true),
        (Virtual, false, local, false),
        (Path, true, local, false),
        (Auto, false, accelerate, false),
        (Path, false, accelerate, true),
    ] {
        assert_eq!(
            force_path_style(style, accelerated, endpoint),
            expected,
            "{style:?} {accelerated} {endpoint:?}"
        );
    }
    for (url, expected) in [
        ("https://s3-accelerate.amazonaws.com", true),
        ("http://s3-accelerate.amazonaws.com/base", true),
        ("HTTPS://s3-accelerate.amazonaws.com", true),
        ("https://s3-accelerate.dualstack.amazonaws.com", true),
        ("http://s3-accelerate.dualstack.amazonaws.com/path", true),
        ("https://s3-accelerate.fooamazonaws.com", true),
        (
            "https://s3-accelerate.dualstack.dualstack.amazonaws.com",
            false,
        ),
        ("https://s3-accelerate.fips.amazonaws.com", false),
        ("https://s3-accelerate.foo.amazonaws.com", false),
        ("https://s3-accelerate.dualstack.foo.amazonaws.com", false),
        ("https://s3-accelerate.amazonaws.com:443", false),
        ("https://S3-Accelerate.amazonaws.com", false),
        ("https://S3-accelerate.amazonaws.com", false),
        ("https://bucket.s3-accelerate.amazonaws.com", false),
        ("ftp://s3-accelerate.amazonaws.com", false),
        ("https://s3.amazonaws.com", false),
        ("s3-accelerate.amazonaws.com", false),
        ("https:/x://s3-accelerate.amazonaws.com", false),
        ("http:x://s3-accelerate.amazonaws.com", false),
    ] {
        assert_eq!(is_s3_accelerate_url(url), expected, "{url}");
    }
}
#[test]
fn fips_pseudo_regions_and_netloc_keep_target_string_semantics() {
    assert_eq!(fips_pseudo_region("us-east-1"), None);
    assert_eq!(
        fips_pseudo_region("fips-us-east-1-fips"),
        Some("us-east-1".into())
    );
    for (url, expected) in [
        ("https://s3.amazonaws.com", "s3.amazonaws.com"),
        ("http://user:pw@host:80/base?x=1#y", "user:pw@host:80"),
        ("https://[::1]:8443", "[::1]:8443"),
        ("http://host?query", "host"),
        ("http://host#fragment", "host"),
        ("localhost:4566", ""),
        ("s3.amazonaws.com", ""),
        ("https://user@host:443/path?q", "user@host:443"),
        ("http://[::1]:9000/", "[::1]:9000"),
        ("https://h:1/p?q", "h:1"),
        ("host/path", ""),
        ("http:x://host/p", ""),
        ("https:/x://host", ""),
    ] {
        assert_eq!(netloc(url), expected, "{url}");
    }
}
#[test]
fn rule_messages_preserve_botocore_translations_and_preempted_errors()
-> Result<(), Box<dyn std::error::Error>> {
    const ACCELERATE_FIPS: &str =
        "Unsupported configuration when using S3: Accelerate cannot be used with FIPS";
    const LAMBDA_ACCELERATE: &str = concat!(
        "Unsupported configuration when using S3: ",
        "S3 Object Lambda does not support S3 Accelerate"
    );
    const MRAP_FIPS: &str = concat!(
        "Unsupported configuration when using S3 access-points: ",
        "S3 MRAP does not support FIPS"
    );
    const LAMBDA_FIPS: &str = concat!(
        "Unsupported configuration when using S3 access-points: ",
        "S3 Object Lambda does not support FIPS"
    );
    const INVALID_CONFIGURATION: &str = concat!(
        "Unsupported configuration when using S3 access-points: ",
        "Invalid configuration: detail"
    );
    let path_style = "Path-style addressing cannot be used with S3 Accelerate";
    let invalid_region = "Invalid region: region was not a valid DNS name.";
    for (rule, expected) in [
        (path_style, Some(path_style)),
        ("Accelerate cannot be used with FIPS", Some(ACCELERATE_FIPS)),
        (
            "S3 Object Lambda does not support S3 Accelerate",
            Some(LAMBDA_ACCELERATE),
        ),
        ("S3 Object Lambda does not support FIPS", Some(LAMBDA_FIPS)),
        ("S3 MRAP does not support FIPS", Some(MRAP_FIPS)),
        ("Invalid configuration: detail", Some(INVALID_CONFIGURATION)),
        (
            "Partition does not support FIPS",
            Some("Partition does not support FIPS"),
        ),
        (invalid_region, Some(invalid_region)),
        ("ordinary rule error", Some("ordinary rule error")),
        ("Custom endpoint `x` was not a valid URI", None),
        ("A region must be set when sending requests to S3.", None),
        ("Invalid region in ARN: `x` (invalid DNS name)", None),
        ("Invalid ARN: Missing account id", None),
        ("invalid arn: wrong", None),
    ] {
        match (rule_error(rule), expected) {
            (Ok(error), Some(expected)) => {
                assert_eq!(error.message, expected, "{rule}");
                assert_eq!(error.client_url, None, "{rule}");
            }
            (Err(EndpointError::InvalidEndpoint), None) => {}
            (result, _) => return Err(format!("{rule}: unexpected {result:?}").into()),
        }
    }
    Ok(())
}
