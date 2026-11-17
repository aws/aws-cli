use super::*;
use pyload::format::{flags, testing};
#[test]
fn lexically_latest_rules_and_service_validation() -> Result<(), Box<dyn std::error::Error>> {
    let blob = testing::blob(
        &[
            testing::entry(
                b"awscli/botocore/data/s3/2006-03-01/endpoint-rule-set-1.json",
                b"old",
                flags::RESOURCE,
            ),
            testing::entry(
                b"awscli/botocore/data/s3/2099-01-01/endpoint-rule-set-1.json",
                b"new",
                flags::RESOURCE,
            ),
            testing::entry(
                b"awscli/botocore/data/s3/9999/other.json",
                b"ignore",
                flags::RESOURCE,
            ),
        ],
        false,
        2,
    );
    let view = View::new(&blob)?;
    let name = versioned_resource_name(view, "s3", "endpoint-rule-set-1")?;
    assert_eq!(
        name,
        b"awscli/botocore/data/s3/2099-01-01/endpoint-rule-set-1.json"
    );
    assert_eq!(load_resource(view, name)?, b"new");
    for service in ["", "s3/../ec2", "s3_", "s3."] {
        assert!(matches!(
            versioned_resource_name(view, service, "endpoint-rule-set-1"),
            Err(RulesError::InvalidServiceName)
        ));
    }
    assert!(matches!(
        versioned_resource_name(view, "ec2", "endpoint-rule-set-1"),
        Err(RulesError::MissingEndpointRules)
    ));
    Ok(())
}
#[test]
fn compressed_rules_decode_through_the_reserved_scratch() -> Result<(), Box<dyn std::error::Error>>
{
    let rules = br#"{"version":"1.0"}"#;
    let frame = testing::raw_zstd_frame(rules)?;
    let mut compressed = testing::entry(
        b"awscli/botocore/data/s3/2006-03-01/endpoint-rule-set-1.json",
        &frame,
        flags::RESOURCE | flags::COMPRESSED,
    );
    compressed.raw_len = u32::try_from(rules.len())?;
    let mut corrupt = testing::entry(
        b"awscli/botocore/data/s3/2006-03-01/endpoint-tests-1.json",
        &frame,
        flags::RESOURCE | flags::COMPRESSED,
    );
    corrupt.raw_len = compressed.raw_len + 1;
    let blob = testing::blob(&[compressed, corrupt], false, 2);
    let view = View::new(&blob)?;
    let name = versioned_resource_name(view, "s3", "endpoint-rule-set-1")?;
    assert_eq!(load_resource(view, name)?, rules);
    assert!(matches!(
        load_resource(
            view,
            b"awscli/botocore/data/s3/2006-03-01/endpoint-tests-1.json"
        ),
        Err(RulesError::Decode(pyload::decompress::Error::DecodeFailed))
    ));
    Ok(())
}
#[test]
fn compressed_rule_decode_failures_keep_the_decoder_error_names()
-> Result<(), Box<dyn std::error::Error>> {
    let rules = br#"{"version":"1.0"}"#;
    let frame = testing::raw_zstd_frame(rules)?;
    let corrupt_name = b"awscli/botocore/data/s3/2006-03-01/endpoint-rule-set-1.json";
    let mut corrupt = testing::entry(
        corrupt_name,
        b"not a zstd frame",
        flags::RESOURCE | flags::COMPRESSED,
    );
    corrupt.raw_len = u32::try_from(rules.len())?;
    let over_long_name = b"awscli/botocore/data/s3/2099-01-01/endpoint-rule-set-1.json";
    let mut over_long = testing::entry(over_long_name, &frame, flags::RESOURCE | flags::COMPRESSED);
    over_long.raw_len = u32::try_from(rules.len() - 1)?;
    let blob = testing::blob(&[corrupt, over_long], false, 2);
    let view = View::new(&blob)?;
    for (name, expected, text) in [
        (
            &corrupt_name[..],
            pyload::decompress::Error::DecodeFailed,
            "DecodeFailed",
        ),
        (
            &over_long_name[..],
            pyload::decompress::Error::OutputLengthMismatch,
            "OutputLengthMismatch",
        ),
    ] {
        let error = load_resource(view, name)
            .err()
            .ok_or("a corrupt compressed rule set loaded")?;
        assert!(
            matches!(&error, RulesError::Decode(actual) if *actual == expected),
            "{error:?}"
        );
        assert_eq!(error.to_string(), text);
    }
    assert!(matches!(
        Rules::load(view, "s3"),
        Err(RulesError::Decode(
            pyload::decompress::Error::OutputLengthMismatch
        ))
    ));
    Ok(())
}
pub(crate) fn payload() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let prefix = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX")
        .ok_or("AWS_NATIVE_FALLBACK_PREFIX must name the fallback payload prefix")?;
    Ok(std::fs::read(
        std::path::PathBuf::from(prefix).join("awscli-v2.blob"),
    )?)
}
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn embedded_s3_bucket_partition_endpoint_variants() -> Result<(), Box<dyn std::error::Error>> {
    let payload = payload()?;
    let view = View::new(&payload)?;
    for (region, bucket, url) in [
        (
            "us-west-2",
            Some("plain-bucket"),
            "https://plain-bucket.s3.us-west-2.amazonaws.com",
        ),
        (
            "us-east-1",
            Some("bucket.with.dots"),
            "https://s3.us-east-1.amazonaws.com/bucket.with.dots",
        ),
        ("cn-north-1", None, "https://s3.cn-north-1.amazonaws.com.cn"),
        ("us-east-1", None, "https://s3.us-east-1.amazonaws.com"),
    ] {
        let parameters = crt::endpoints::Parameters {
            region,
            bucket,
            force_path_style: Some(false),
            accelerate: Some(false),
            use_global_endpoint: Some(false),
            disable_multi_region_access_points: Some(false),
            ..Default::default()
        };
        let resolved = resolve(view, "s3", parameters)?;
        assert!(
            matches!(
                &resolved,
                crt::endpoints::Resolved::Endpoint { url: actual, .. } if actual == url.as_bytes()
            ),
            "{resolved:?}"
        );
    }
    Ok(())
}
#[test]
#[cfg_attr(miri, ignore = "calls the CRT, which Miri cannot run")]
fn resolutions_survive_runtime_libraries_released_around_them()
-> Result<(), Box<dyn std::error::Error>> {
    let payload = payload()?;
    let rules = Rules::load(View::new(&payload)?, "s3")?;
    let parameters = crt::endpoints::Parameters {
        region: "us-west-2",
        bucket: Some("plain-bucket"),
        force_path_style: Some(false),
        accelerate: Some(false),
        use_global_endpoint: Some(false),
        disable_multi_region_access_points: Some(false),
        ..Default::default()
    };
    std::thread::scope(|scope| {
        let resolving: Vec<_> = (0..2)
            .map(|_| {
                scope.spawn(|| {
                    (0..50).all(|_| {
                        matches!(
                            rules.resolve(parameters),
                            Ok(crt::endpoints::Resolved::Endpoint { .. })
                        )
                    })
                })
            })
            .collect();
        for _ in 0..2 {
            scope.spawn(|| {
                for _ in 0..50 {
                    drop(crt::runtime::Library::acquire());
                }
            });
        }
        for resolver in resolving {
            assert!(matches!(resolver.join(), Ok(true)));
        }
    });
    Ok(())
}
