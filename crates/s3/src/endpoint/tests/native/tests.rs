use super::*;

type TestResult = Result<(), Box<dyn std::error::Error>>;

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn client_endpoint_hosts_ignore_bucket_and_acceleration() -> TestResult {
    let accelerate = Options {
        accelerate: true,
        ..Options::default()
    };
    check_client_hosts(&[
        (
            "us-west-2",
            Some("bucket"),
            ClientNetloc::ConfiguredRegion,
            Options::default(),
            "https://bucket.s3.us-west-2.amazonaws.com",
            "s3.us-west-2.amazonaws.com",
        ),
        (
            "us-west-2",
            None,
            ClientNetloc::ConfiguredRegion,
            Options::default(),
            "https://s3.us-west-2.amazonaws.com",
            "s3.us-west-2.amazonaws.com",
        ),
        (
            "us-west-2",
            Some("bucket"),
            ClientNetloc::ConfiguredRegion,
            accelerate,
            "https://bucket.s3-accelerate.amazonaws.com",
            "s3.us-west-2.amazonaws.com",
        ),
        (
            "us-east-1",
            Some("bucket"),
            ClientNetloc::DefaultRegion,
            accelerate,
            "https://bucket.s3-accelerate.amazonaws.com",
            "s3.amazonaws.com",
        ),
        (
            "us-west-2",
            Some("bucket"),
            ClientNetloc::ConfiguredRegion,
            Options {
                use_dual_stack: true,
                ..accelerate
            },
            "https://bucket.s3-accelerate.dualstack.amazonaws.com",
            "s3.dualstack.us-west-2.amazonaws.com",
        ),
    ])
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn client_endpoint_hosts_follow_the_client_region_and_variants() -> TestResult {
    check_client_hosts(&[
        (
            "us-west-2",
            Some("bucket"),
            ClientNetloc::ConfiguredRegion,
            Options {
                use_fips: true,
                ..Options::default()
            },
            "https://bucket.s3-fips.us-west-2.amazonaws.com",
            "s3-fips.us-west-2.amazonaws.com",
        ),
        (
            "aws-global",
            Some("bucket"),
            ClientNetloc::ConfiguredRegion,
            Options::default(),
            "https://bucket.s3.amazonaws.com",
            "s3.amazonaws.com",
        ),
        (
            "us-east-1",
            Some("bucket"),
            ClientNetloc::DefaultRegion,
            Options::default(),
            "https://bucket.s3.us-east-1.amazonaws.com",
            "s3.amazonaws.com",
        ),
        (
            "us-east-1",
            None,
            ClientNetloc::DefaultRegion,
            Options::default(),
            "https://s3.us-east-1.amazonaws.com",
            "s3.amazonaws.com",
        ),
        (
            "us-east-1",
            Some("bucket"),
            ClientNetloc::DefaultRegion,
            Options {
                use_dual_stack: true,
                ..Options::default()
            },
            "https://bucket.s3.dualstack.us-east-1.amazonaws.com",
            "s3.dualstack.us-east-1.amazonaws.com",
        ),
    ])
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn custom_endpoints_preserve_client_authority_with_virtual_requests() -> TestResult {
    check_client_hosts(&[
        (
            "us-west-2",
            Some("bucket"),
            ClientNetloc::ConfiguredRegion,
            Options {
                endpoint: Some("http://LocalHost:4566/base"),
                ..Options::default()
            },
            "http://LocalHost:4566/base/bucket",
            "LocalHost:4566",
        ),
        (
            "us-west-2",
            Some("bucket"),
            ClientNetloc::ConfiguredRegion,
            Options {
                endpoint: Some("http://localhost:4566"),
                addressing_style: AddressingStyle::Virtual,
                ..Options::default()
            },
            "http://bucket.localhost:4566",
            "localhost:4566",
        ),
    ])
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn legacy_external_region_client_host_keeps_its_hostname_override() -> TestResult {
    let external = |bucket, options, url, client| {
        (
            "s3-external-1",
            bucket,
            ClientNetloc::ConfiguredRegion,
            options,
            url,
            client,
        )
    };
    let fips = Options {
        use_fips: true,
        ..Options::default()
    };
    let dual_stack = Options {
        use_dual_stack: true,
        ..Options::default()
    };
    check_client_hosts(&[
        external(
            None,
            Options::default(),
            "https://s3.s3-external-1.amazonaws.com",
            "s3-external-1.amazonaws.com",
        ),
        external(
            Some("bucket"),
            fips,
            "https://bucket.s3-fips.s3-external-1.amazonaws.com",
            "s3-fips.s3-external-1.amazonaws.com",
        ),
        external(
            Some("bucket"),
            dual_stack,
            "https://bucket.s3.dualstack.s3-external-1.amazonaws.com",
            "s3.dualstack.s3-external-1.amazonaws.com",
        ),
        external(
            Some("bucket"),
            Options {
                use_fips: true,
                ..dual_stack
            },
            "https://bucket.s3-fips.dualstack.s3-external-1.amazonaws.com",
            "s3-fips.dualstack.s3-external-1.amazonaws.com",
        ),
        external(
            Some("bucket"),
            Options {
                endpoint: Some("http://localhost:4566"),
                ..Options::default()
            },
            "http://localhost:4566/bucket",
            "localhost:4566",
        ),
        external(
            Some("bucket"),
            Options {
                accelerate: true,
                ..Options::default()
            },
            "https://bucket.s3-accelerate.amazonaws.com",
            "s3-external-1.amazonaws.com",
        ),
    ])
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn proxy_bypass_uses_the_legacy_external_region_client_host() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let environment = cli_core::proxy::Environment {
        https: cli_core::proxy::Pair {
            upper: Some("http://proxy:8080"),
            lower: None,
        },
        no_proxy: cli_core::proxy::Pair {
            upper: Some("s3.s3-external-1.amazonaws.com,s3.us-west-2.amazonaws.com"),
            lower: None,
        },
        ..Default::default()
    };
    for bucket in [None, Some("bucket")] {
        for region in ["s3-external-1", "us-west-2"] {
            let endpoint = test_resolve(
                view,
                region,
                bucket,
                Options {
                    client_netloc: ClientNetloc::ConfiguredRegion,
                    ..Options::default()
                },
            )?;
            let client = endpoint
                .client_netloc
                .as_deref()
                .ok_or("no client netloc")?;
            let selected = environment.resolve_for(std::str::from_utf8(&endpoint.url)?, client);
            if region == "s3-external-1" {
                assert_eq!(client, "s3-external-1.amazonaws.com");
                assert_eq!(selected, Some("http://proxy:8080"));
            } else {
                assert_eq!(selected, None);
            }
        }
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn refused_requests_retain_the_independent_client_endpoint() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let cases = [
        (
            "us-west-2",
            "bucket.with.dots",
            Options {
                accelerate: true,
                ..Options::default()
            },
            "https://s3.us-west-2.amazonaws.com",
        ),
        (
            "us-west-2",
            "bucket.with.dots",
            Options {
                accelerate: true,
                client_netloc: ClientNetloc::DefaultRegion,
                ..Options::default()
            },
            "https://s3.us-west-2.amazonaws.com",
        ),
        (
            "us-west-2",
            "bucket.with.dots",
            Options {
                accelerate: true,
                endpoint: Some("http://localhost:4566/base"),
                ..Options::default()
            },
            "http://localhost:4566/base",
        ),
        (
            "cn-north-1",
            "bucket",
            Options {
                use_fips: true,
                ..Options::default()
            },
            "https://s3.cn-north-1.amazonaws.com.cn",
        ),
    ];
    for (region, bucket, options, url) in cases {
        let error = expect_rule_error(resolve(view, region, Some(bucket), options)?)?;
        assert_eq!(error.client_url.as_deref(), Some(url));
    }
    Ok(())
}

type ClientHostCase<'a> = (
    &'a str,
    Option<&'a str>,
    ClientNetloc,
    Options<'a>,
    &'a str,
    &'a str,
);

fn check_client_hosts(cases: &[ClientHostCase<'_>]) -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    for &(region, bucket, selection, options, request, client) in cases {
        let resolved = test_resolve(
            view,
            region,
            bucket,
            Options {
                client_netloc: selection,
                ..options
            },
        )?;
        assert_eq!(String::from_utf8_lossy(&resolved.url), request);
        assert_eq!(resolved.client_netloc.as_deref(), Some(client), "{request}");
        let plain = test_resolve(view, region, bucket, options)?;
        assert_eq!(plain.url, resolved.url);
        assert_eq!(plain.client_netloc, None, "{request}");
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn pseudo_regions_normalize_request_and_client_hosts() -> TestResult {
    let dual_stack = Options {
        use_dual_stack: true,
        ..Options::default()
    };
    let local = Options {
        endpoint: Some("http://localhost:4566"),
        ..Options::default()
    };
    let default_client = |region, options, request, client| {
        (
            region,
            Some("bucket"),
            ClientNetloc::DefaultRegion,
            options,
            request,
            client,
        )
    };
    check_client_hosts(&[
        default_client(
            "fips-us-east-1",
            Options::default(),
            "https://bucket.s3-fips.us-east-1.amazonaws.com",
            "s3-fips.us-east-1.amazonaws.com",
        ),
        default_client(
            "us-west-2-fips",
            Options::default(),
            "https://bucket.s3-fips.us-west-2.amazonaws.com",
            "s3-fips.us-west-2.amazonaws.com",
        ),
        default_client(
            "fips-us-east-1",
            dual_stack,
            "https://bucket.s3-fips.dualstack.us-east-1.amazonaws.com",
            "s3-fips.dualstack.us-east-1.amazonaws.com",
        ),
        default_client(
            "us-west-2-fips",
            local,
            "http://localhost:4566/bucket",
            "localhost:4566",
        ),
    ])
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn configured_pseudo_regions_normalize_request_and_client_hosts() -> TestResult {
    let configured = |region, bucket, options, request, client| {
        (
            region,
            bucket,
            ClientNetloc::ConfiguredRegion,
            options,
            request,
            client,
        )
    };
    check_client_hosts(&[
        configured(
            "fips-us-east-1",
            Some("bucket"),
            Options::default(),
            "https://bucket.s3-fips.us-east-1.amazonaws.com",
            "s3-fips.us-east-1.amazonaws.com",
        ),
        configured(
            "us-west-2-fips",
            None,
            Options::default(),
            "https://s3-fips.us-west-2.amazonaws.com",
            "s3-fips.us-west-2.amazonaws.com",
        ),
        configured(
            "fips-us-east-1",
            Some("bucket"),
            Options {
                use_dual_stack: true,
                ..Options::default()
            },
            "https://bucket.s3-fips.dualstack.us-east-1.amazonaws.com",
            "s3-fips.dualstack.us-east-1.amazonaws.com",
        ),
        configured(
            "us-west-2-fips",
            Some("bucket"),
            Options {
                endpoint: Some("http://localhost:4566"),
                ..Options::default()
            },
            "http://localhost:4566/bucket",
            "localhost:4566",
        ),
    ])
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn configured_endpoint_validation_precedes_request_rule_errors() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    for (region, bucket, options) in [
        ("bad!", "bucket", Options::default()),
        (
            "bad!",
            "a.b",
            Options {
                accelerate: true,
                ..Options::default()
            },
        ),
        (
            "us-east-1",
            "b",
            Options {
                endpoint: Some("not-a-url"),
                ..Options::default()
            },
        ),
        (
            "us-east-1",
            "b",
            Options {
                endpoint: Some("not-a-url"),
                accelerate: true,
                ..Options::default()
            },
        ),
    ] {
        assert!(matches!(
            resolve(view, region, Some(bucket), options),
            Err(EndpointError::InvalidEndpoint)
        ));
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn request_rule_errors_keep_the_target_translation_and_precedence() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    for (options, expected) in [
        (
            Options {
                accelerate: true,
                ..Options::default()
            },
            "Path-style addressing cannot be used with S3 Accelerate",
        ),
        (
            Options {
                accelerate: true,
                use_fips: true,
                ..Options::default()
            },
            "Unsupported configuration when using S3: Accelerate cannot be used with FIPS",
        ),
        (
            Options {
                accelerate: true,
                endpoint: Some("http://localhost:4566"),
                ..Options::default()
            },
            "A custom endpoint cannot be combined with S3 Accelerate",
        ),
    ] {
        let resolved = resolve(view, "us-east-1", Some("bucket.with.dots"), options)?;
        assert_eq!(expect_rule_error(resolved)?.message, expected);
    }
    Ok(())
}

fn configured_endpoint(
    view: pyload::View<'_>,
    region: &str,
    bucket: Option<&str>,
    endpoint: Option<&str>,
    client: &cli_core::client_config::ClientConfig,
    env: &[(&str, &str)],
) -> Result<Endpoint, Box<dyn std::error::Error>> {
    expect_endpoint(configured_resolution(
        view, region, bucket, endpoint, client, env,
    )?)
}

fn configured_resolution(
    view: pyload::View<'_>,
    region: &str,
    bucket: Option<&str>,
    endpoint: Option<&str>,
    client: &cli_core::client_config::ClientConfig,
    env: &[(&str, &str)],
) -> Result<Resolved, EndpointError> {
    let env: std::collections::BTreeMap<String, String> = env
        .iter()
        .map(|(key, value)| (key.to_string(), value.to_string()))
        .collect();
    let files = awscli_config::ParsedFiles::parse(Default::default());
    resolve_configured(
        view,
        &env,
        &files,
        region,
        bucket,
        ConfiguredInput {
            endpoint,
            region_configured: true,
            s3_block: client.s3_block(),
            ..Default::default()
        },
        Vec::new(),
    )
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn configured_addressing_modes_cover_custom_hosts_and_bucket_forms() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    for &(bucket, endpoint, style, expected) in CONFIGURED_ADDRESSING_CASES {
        let mut client =
            cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Ls);
        client.addressing_style.value = style;
        let result = configured_endpoint(view, "us-east-1", Some(bucket), endpoint, &client, &[])?;
        assert_eq!(result.url, expected.as_bytes());
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn configured_pseudo_regions_follow_fips_for_each_addressing_style() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let local = Some("http://localhost:4566");
    for (region, bucket, endpoint, style, expected) in [
        (
            "fips-us-west-2",
            "bucket",
            None,
            Auto,
            "https://bucket.s3-fips.us-west-2.amazonaws.com",
        ),
        (
            "us-west-2-fips",
            "bucket",
            None,
            Path,
            "https://s3-fips.us-west-2.amazonaws.com/bucket",
        ),
        (
            "fips-us-west-2",
            "bucket.with.dots",
            None,
            Auto,
            "https://s3-fips.us-west-2.amazonaws.com/bucket.with.dots",
        ),
        (
            "us-gov-west-1-fips",
            "bucket",
            local,
            Auto,
            "http://localhost:4566/bucket",
        ),
        (
            "fips-us-gov-west-1",
            "bucket",
            local,
            Virtual,
            "http://bucket.localhost:4566",
        ),
    ] {
        let mut client =
            cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Ls);
        client.addressing_style.value = style;
        let result = configured_endpoint(view, region, Some(bucket), endpoint, &client, &[])?;
        assert_eq!(String::from_utf8_lossy(&result.url), expected);
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn configured_acceleration_preserves_bucketless_and_refused_request_rules() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let mut client =
        cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Ls);
    client.use_accelerate_endpoint.value = true;
    for style in [AddressingStyle::Auto, AddressingStyle::Path] {
        client.addressing_style.value = style;
        for region in ["us-east-1", "us-west-2"] {
            assert_eq!(
                configured_endpoint(view, region, Some("bucket"), None, &client, &[])?.url,
                b"https://bucket.s3-accelerate.amazonaws.com"
            );
        }
    }
    assert_eq!(
        configured_endpoint(view, "us-east-1", None, None, &client, &[])?.url,
        b"https://s3.us-east-1.amazonaws.com"
    );
    assert_eq!(
        configured_endpoint(
            view,
            "us-east-1",
            Some("bucket"),
            None,
            &client,
            &[("AWS_USE_DUALSTACK_ENDPOINT", "true")]
        )?
        .url,
        b"https://bucket.s3-accelerate.dualstack.amazonaws.com"
    );
    check_acceleration_refusals(view, &client)?;
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn configured_block_dualstack_adds_to_environment_and_custom_endpoints_suppress_it() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let mut client =
        cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Ls);
    for (env, block, dual) in [
        (Some("false"), true, true),
        (Some("true"), false, true),
        (None, true, true),
        (Some("false"), false, false),
    ] {
        client.use_dualstack_endpoint.value = block;
        let env: Vec<_> = env
            .map(|value| ("AWS_USE_DUALSTACK_ENDPOINT", value))
            .into_iter()
            .collect();
        let endpoint = configured_endpoint(view, "us-east-1", Some("bucket"), None, &client, &env)?;
        assert_eq!(
            String::from_utf8(endpoint.url)?.contains("s3.dualstack."),
            dual
        );
    }
    client.use_dualstack_endpoint.value = true;
    for (bucket, style, env, expected) in [
        (
            Some("bucket"),
            AddressingStyle::Auto,
            &[][..],
            "https://bucket.s3.dualstack.us-east-1.amazonaws.com",
        ),
        (
            Some("bucket"),
            AddressingStyle::Path,
            &[][..],
            "https://s3.dualstack.us-east-1.amazonaws.com/bucket",
        ),
        (
            None,
            AddressingStyle::Auto,
            &[][..],
            "https://s3.dualstack.us-east-1.amazonaws.com",
        ),
        (
            Some("bucket"),
            AddressingStyle::Auto,
            &[("AWS_USE_FIPS_ENDPOINT", "true")][..],
            "https://bucket.s3-fips.dualstack.us-east-1.amazonaws.com",
        ),
    ] {
        client.addressing_style.value = style;
        assert_eq!(
            configured_endpoint(view, "us-east-1", bucket, None, &client, env)?.url,
            expected.as_bytes()
        );
    }
    client.addressing_style.value = AddressingStyle::Auto;
    assert_eq!(
        configured_endpoint(
            view,
            "us-east-1",
            Some("bucket"),
            Some("http://localhost:4566"),
            &client,
            &[]
        )?
        .url,
        b"http://localhost:4566/bucket"
    );
    Ok(())
}

use AddressingStyle::{Auto, Path, Virtual};
type AddressingCase = (
    &'static str,
    Option<&'static str>,
    AddressingStyle,
    &'static str,
);
const CONFIGURED_ADDRESSING_CASES: &[AddressingCase] = &[
    (
        "bucket",
        None,
        Auto,
        "https://bucket.s3.us-east-1.amazonaws.com",
    ),
    (
        "bucket",
        None,
        Virtual,
        "https://bucket.s3.us-east-1.amazonaws.com",
    ),
    (
        "bucket",
        None,
        Path,
        "https://s3.us-east-1.amazonaws.com/bucket",
    ),
    (
        "bucket",
        Some("http://localhost:4566"),
        Auto,
        "http://localhost:4566/bucket",
    ),
    (
        "bucket",
        Some("http://localhost:4566"),
        Virtual,
        "http://bucket.localhost:4566",
    ),
    (
        "bucket",
        Some("http://127.0.0.1:4566"),
        Virtual,
        "http://127.0.0.1:4566/bucket",
    ),
    (
        "bucket.with.dots",
        Some("https://example.com"),
        Virtual,
        "https://example.com/bucket.with.dots",
    ),
    (
        "bucket.with.dots",
        Some("http://example.com"),
        Virtual,
        "http://bucket.with.dots.example.com",
    ),
    (
        "Bucket_Name",
        None,
        Virtual,
        "https://s3.us-east-1.amazonaws.com/Bucket_Name",
    ),
    (
        "bucket",
        Some("https://s3-accelerate.amazonaws.com"),
        Auto,
        "https://bucket.s3-accelerate.amazonaws.com",
    ),
    (
        "bucket",
        Some("https://s3-accelerate.amazonaws.com"),
        Path,
        "https://s3-accelerate.amazonaws.com/bucket",
    ),
];

fn check_acceleration_refusals(
    view: pyload::View<'_>,
    client: &cli_core::client_config::ClientConfig,
) -> TestResult {
    for bucket in ["bucket.with.dots", "a.b", "Bucket_1"] {
        let result = configured_resolution(view, "us-east-1", Some(bucket), None, client, &[])?;
        assert_eq!(
            expect_rule_error(result)?.message,
            "Path-style addressing cannot be used with S3 Accelerate"
        );
    }
    const FIPS_ERROR: &str = concat!(
        "Unsupported configuration when using S3: ",
        "Accelerate cannot be used with FIPS"
    );
    for region in ["us-west-2-fips", "fips-us-west-2"] {
        let result = configured_resolution(view, region, Some("bucket"), None, client, &[])?;
        assert_eq!(expect_rule_error(result)?.message, FIPS_ERROR);
    }
    Ok(())
}

type GlobalCase<'a> = (
    Option<&'a str>,
    Option<&'a str>,
    &'a [(&'a str, &'a str)],
    bool,
    &'a str,
);

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn no_configured_region_resolves_botocore_s_global_endpoint() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let files = awscli_config::ParsedFiles::parse(Default::default());
    let client = cli_core::client_config::ClientConfig::new(cli_core::client_config::Command::Ls);
    let local = "http://localhost:4566";
    let cases: &[GlobalCase<'_>] = &[
        (
            Some("bucket"),
            None,
            &[],
            false,
            "https://bucket.s3.amazonaws.com",
        ),
        (None, None, &[], false, "https://s3.amazonaws.com"),
        (
            Some("bucket"),
            None,
            &[("AWS_USE_FIPS_ENDPOINT", "true")],
            false,
            "https://bucket.s3-fips.us-east-1.amazonaws.com",
        ),
        (
            Some("bucket"),
            None,
            &[("AWS_USE_DUALSTACK_ENDPOINT", "true")],
            false,
            "https://bucket.s3.dualstack.us-east-1.amazonaws.com",
        ),
        (
            Some("bucket"),
            Some(local),
            &[],
            false,
            "http://localhost:4566/bucket",
        ),
        (
            Some("bucket"),
            None,
            &[],
            true,
            "https://bucket.s3.us-east-1.amazonaws.com",
        ),
    ];
    for &(bucket, endpoint, env, region_configured, expected) in cases {
        let env: std::collections::BTreeMap<String, String> = env
            .iter()
            .map(|(key, value)| ((*key).to_owned(), (*value).to_owned()))
            .collect();
        let resolved = expect_endpoint(resolve_configured(
            view,
            &env,
            &files,
            "us-east-1",
            bucket,
            ConfiguredInput {
                endpoint,
                region_configured,
                s3_block: client.s3_block(),
                ..Default::default()
            },
            Vec::new(),
        )?)?;
        assert_eq!(String::from_utf8_lossy(&resolved.url), expected);
        assert_eq!(resolved.signing_region.as_deref(), Some("us-east-1"));
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn redirect_recipes_preserve_normalized_fips_and_the_original_override() -> TestResult {
    use crt::redirect::Resolver;
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    for (region, options, expected, netloc) in [
        (
            "fips-us-east-1",
            Options {
                use_dual_stack: true,
                ..Options::default()
            },
            "https://bucket.s3-fips.dualstack.us-west-2.amazonaws.com",
            "s3-fips.dualstack.us-east-1.amazonaws.com",
        ),
        (
            "us-east-1",
            Options {
                endpoint: Some("http://localhost:4566/base"),
                addressing_style: Path,
                ..Options::default()
            },
            "http://localhost:4566/base/bucket",
            "localhost:4566",
        ),
    ] {
        let endpoint = test_resolve(
            view,
            region,
            Some("bucket"),
            Options {
                client_netloc: ClientNetloc::ConfiguredRegion,
                ..options
            },
        )?;
        let recipe = endpoint.recipe.as_ref().ok_or("missing recipe")?;
        assert_eq!(recipe.bucket(), "bucket");
        assert_eq!(recipe.client_region(), "us-east-1");
        let redirected = recipe
            .resolve("us-west-2")
            .map_err(|error| format!("{error:?}"))?;
        assert_eq!(redirected.url, expected);
        assert_eq!(redirected.signing_region.as_deref(), Some("us-west-2"));
        assert_eq!(endpoint.client_netloc.as_deref(), Some(netloc));
    }
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn redirect_global_client_identity_is_not_its_signing_region() -> TestResult {
    use crt::redirect::Resolver;
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let endpoint = test_resolve(view, "aws-global", Some("bucket"), Options::default())?;
    let recipe = endpoint.recipe.as_ref().ok_or("missing recipe")?;
    assert_eq!(recipe.client_region(), "aws-global");
    assert_eq!(endpoint.signing_region.as_deref(), Some("us-east-1"));
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn redirect_recipes_exist_only_for_supported_buckets() -> TestResult {
    let bytes = payload()?;
    let view = pyload::View::new(&bytes)?;
    let local = Options {
        endpoint: Some("http://localhost:4566"),
        ..Options::default()
    };
    assert!(
        test_resolve(view, "us-east-1", None, local)?
            .recipe
            .is_none()
    );
    for bucket in [
        "bucket--usw2-az1--x-s3",
        "arn:aws:s3:us-west-2:123456789012:accesspoint/ap",
    ] {
        let resolved = resolve(view, "us-west-2", Some(bucket), Options::default());
        assert!(
            !matches!(
                resolved,
                Ok(Resolved::Endpoint(Endpoint {
                    recipe: Some(_),
                    ..
                }))
            ),
            "{bucket}"
        );
    }
    Ok(())
}
