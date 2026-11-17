#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
use awscli_argparse::tables;

const TEXT_KEY: &[u8] = b"0123456789abcdef0123456789abcdef";

fn pairs(headers: &[Header]) -> Vec<(String, String)> {
    headers
        .iter()
        .map(|header| {
            (
                String::from_utf8(header.name.clone()).unwrap(),
                String::from_utf8(header.value.clone()).unwrap(),
            )
        })
        .collect()
}

fn named(names: &[(&str, &str)]) -> Vec<(String, String)> {
    names
        .iter()
        .map(|(name, value)| ((*name).to_owned(), (*value).to_owned()))
        .collect()
}

#[test]
fn choices_convert_every_argparse_choice() {
    let choices = |name: &str| {
        tables::CP_ARGUMENTS
            .iter()
            .find(|argument| argument.name == name)
            .unwrap()
            .choices
    };
    for choice in choices("acl") {
        assert_eq!(
            CannedAcl::try_from(*choice).unwrap().header_value(),
            *choice
        );
    }
    for choice in choices("storage-class") {
        assert_eq!(
            StorageClass::try_from(*choice).unwrap().header_value(),
            *choice
        );
    }
    for choice in choices("sse") {
        assert_eq!(
            ServerSideEncryption::try_from(*choice)
                .unwrap()
                .header_value(),
            *choice
        );
    }
    for choice in choices("sse-c") {
        assert_eq!(
            CustomerAlgorithm::try_from(*choice).unwrap().header_value(),
            *choice
        );
    }
    assert_eq!(CannedAcl::try_from("Private"), Err(UnknownChoice));
}

#[test]
fn checksum_choices_convert_every_argparse_choice() {
    let choices = |name: &str| {
        tables::CP_ARGUMENTS
            .iter()
            .find(|argument| argument.name == name)
            .unwrap()
            .choices
    };
    for choice in choices("checksum-algorithm") {
        let algorithm = ChecksumAlgorithm::try_from(*choice).unwrap();
        assert_eq!(algorithm.header_value(), *choice);
        let crt = format!("{:?}", algorithm.crt()).to_ascii_uppercase();
        assert_eq!(crt, *choice);
    }
    for choice in choices("checksum-mode") {
        assert_eq!(
            ChecksumMode::try_from(*choice).unwrap().header_value(),
            *choice
        );
    }
}

#[test]
fn every_setting_maps_to_its_upload_header() {
    let metadata = vec![
        ("origin".to_owned(), "settings".to_owned()),
        ("Mixed-Case".to_owned(), String::new()),
    ];
    let grants = [
        "read=id=reader",
        "full=id=owner",
        "readacl=id=a,id=b",
        "writeacl=uri=x",
    ]
    .map(str::to_owned);
    let settings = ObjectSettings {
        content_type: Some("text/x-settings"),
        cache_control: Some("max-age=60"),
        content_disposition: Some("attachment"),
        content_encoding: Some("identity"),
        content_language: Some("en-US"),
        expires: Some("2037-10-21T07:28:00Z".parse().unwrap()),
        website_redirect: Some("/elsewhere.html"),
        metadata: &metadata,
        grants: &grants,
        acl: Some(CannedAcl::BucketOwnerFullControl),
        storage_class: Some(StorageClass::StandardIa),
        encryption: Some(ServerSideEncryption::AwsKms),
        kms_key_id: Some("alias/settings"),
        customer_algorithm: Some(CustomerAlgorithm::Aes256),
        customer_key: Some(CustomerKey::new(TEXT_KEY)),
        request_payer: Some(RequestPayer::Requester),
        checksum_algorithm: Some(ChecksumAlgorithm::Sha256),
        checksum_mode: Some(ChecksumMode::Enabled),
    };
    let customer_key = [
        ("x-amz-server-side-encryption-customer-algorithm", "AES256"),
        (
            "x-amz-server-side-encryption-customer-key",
            "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        ),
        (
            "x-amz-server-side-encryption-customer-key-MD5",
            "hRasmdxgYDKV3nvbahU1MA==",
        ),
    ];
    let mut expected = named(&[
        ("x-amz-acl", "bucket-owner-full-control"),
        ("x-amz-storage-class", "STANDARD_IA"),
        ("x-amz-website-redirect-location", "/elsewhere.html"),
        ("Content-Type", "text/x-settings"),
        ("Cache-Control", "max-age=60"),
        ("Content-Disposition", "attachment"),
        ("Content-Encoding", "identity"),
        ("Content-Language", "en-US"),
        ("Expires", "Wed, 21 Oct 2037 07:28:00 GMT"),
        ("x-amz-grant-read", "id=reader"),
        ("x-amz-grant-full-control", "id=owner"),
        ("x-amz-grant-read-acp", "id=a,id=b"),
        ("x-amz-grant-write-acp", "uri=x"),
        ("x-amz-meta-origin", "settings"),
        ("x-amz-meta-Mixed-Case", ""),
        ("x-amz-server-side-encryption", "aws:kms"),
        (
            "x-amz-server-side-encryption-aws-kms-key-id",
            "alias/settings",
        ),
    ]);
    expected.extend(named(&customer_key));
    assert_eq!(pairs(&settings.upload_headers()), expected);
    assert_eq!(pairs(&settings.download_headers()), named(&customer_key));
    assert_eq!(pairs(&ObjectSettings::default().upload_headers()), []);
}

#[test]
fn metadata_names_equal_but_for_case_send_one_header() {
    let metadata = named(&[
        ("Foo", "old"),
        ("bar", "kept"),
        ("foo", "new"),
        ("FOO", "newest"),
        ("Bar-", "distinct"),
    ]);
    let settings = ObjectSettings {
        metadata: &metadata,
        ..ObjectSettings::default()
    };
    assert_eq!(
        pairs(&settings.upload_headers()),
        named(&[
            ("x-amz-meta-Foo", "newest"),
            ("x-amz-meta-bar", "kept"),
            ("x-amz-meta-Bar-", "distinct"),
        ])
    );
}

#[test]
fn a_later_grant_of_a_permission_replaces_an_earlier_one() {
    let grants = ["read=id=first", "full=", "read=id=last=x"].map(str::to_owned);
    let settings = ObjectSettings {
        grants: &grants,
        ..ObjectSettings::default()
    };
    assert_eq!(
        pairs(&settings.upload_headers()),
        named(&[
            ("x-amz-grant-read", "id=last=x"),
            ("x-amz-grant-full-control", ""),
        ])
    );
    assert_eq!(settings.admit_upload(), None);
    assert_eq!(pairs(&settings.download_headers()), []);
}

#[test]
fn an_upload_with_a_grant_upstream_refuses_stays_with_python() {
    for (pair, permission) in [
        ("read=id=x", Some(GrantPermission::Read)),
        ("full=", Some(GrantPermission::FullControl)),
        ("readacl==", Some(GrantPermission::ReadAcp)),
        ("writeacl=id=x", Some(GrantPermission::WriteAcp)),
        ("everyone", None),
        ("", None),
        ("=id=x", None),
        ("write=id=x", None),
        ("READ=id=x", None),
        (" read=id=x", None),
    ] {
        assert_eq!(
            Grant::parse(pair).map(|grant| grant.permission),
            permission,
            "{pair:?}"
        );
        let grants = ["read=id=kept".to_owned(), pair.to_owned()];
        let settings = ObjectSettings {
            grants: &grants,
            ..ObjectSettings::default()
        };
        assert_eq!(
            settings.admit_upload().is_none(),
            permission.is_some(),
            "{pair:?}"
        );
    }
    for grantee in ["id=a\nb", "nul\0"] {
        let grants = [format!("read={grantee}")];
        let settings = ObjectSettings {
            grants: &grants,
            ..ObjectSettings::default()
        };
        assert_eq!(
            settings.admit_upload(),
            Some(AdmissionReason::UnsupportedValue),
            "{grantee:?}"
        );
    }
}

#[test]
fn a_customer_key_is_sent_base64_encoded_with_its_md5() {
    let key: Vec<u8> = (0x80..0xa0).collect();
    let settings = ObjectSettings {
        customer_algorithm: Some(CustomerAlgorithm::Aes256),
        customer_key: Some(CustomerKey::new(&key)),
        ..ObjectSettings::default()
    };
    assert_eq!(
        pairs(&settings.download_headers()),
        named(&[
            ("x-amz-server-side-encryption-customer-algorithm", "AES256"),
            (
                "x-amz-server-side-encryption-customer-key",
                "gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp8=",
            ),
            (
                "x-amz-server-side-encryption-customer-key-MD5",
                "FRo4d3RwI2sO74sjh747/w==",
            ),
        ])
    );
}

#[test]
fn base64_pads_as_python_does() {
    for (input, expected) in [
        ("", ""),
        ("f", "Zg=="),
        ("fo", "Zm8="),
        ("foo", "Zm9v"),
        ("foob", "Zm9vYg=="),
        ("fooba", "Zm9vYmE="),
        ("foobar", "Zm9vYmFy"),
    ] {
        assert_eq!(base64(input.as_bytes()), expected.as_bytes(), "{input:?}");
    }
}

#[test]
fn one_customer_key_setting_without_the_other_is_refused() {
    let refusal = |algorithm, key: Option<&'static [u8]>| {
        ObjectSettings {
            customer_algorithm: algorithm,
            customer_key: key.map(CustomerKey::new),
            ..ObjectSettings::default()
        }
        .customer_key_refusal()
    };
    let aes = Some(CustomerAlgorithm::Aes256);
    assert_eq!(refusal(None, None), None);
    assert_eq!(refusal(aes, Some(TEXT_KEY)), None);
    assert_eq!(refusal(aes, None), Some(CustomerKeyRefusal::MissingKey));
    assert_eq!(
        refusal(None, Some(TEXT_KEY)),
        Some(CustomerKeyRefusal::MissingAlgorithm)
    );
    assert_eq!(
        CustomerKeyRefusal::MissingKey.to_string(),
        "If --sse-c is specified, --sse-c-key must be specified as well."
    );
    assert_eq!(
        CustomerKeyRefusal::MissingAlgorithm.to_string(),
        "If --sse-c-key is specified, --sse-c must be specified as well."
    );
    for settings in [
        ObjectSettings {
            customer_algorithm: aes,
            ..ObjectSettings::default()
        },
        ObjectSettings {
            customer_key: Some(CustomerKey::new(TEXT_KEY)),
            ..ObjectSettings::default()
        },
    ] {
        assert_eq!(pairs(&settings.download_headers()), []);
    }
}

#[test]
fn a_checksum_setting_of_the_other_direction_is_refused() {
    let algorithm = ObjectSettings {
        checksum_algorithm: Some(ChecksumAlgorithm::Crc32),
        ..ObjectSettings::default()
    };
    let mode = ObjectSettings {
        checksum_mode: Some(ChecksumMode::Enabled),
        ..ObjectSettings::default()
    };
    let both = ObjectSettings {
        checksum_mode: mode.checksum_mode,
        ..algorithm
    };
    let none = ObjectSettings::default();
    let on_download = Some(ChecksumRefusal::AlgorithmOnDownload);
    let on_upload = Some(ChecksumRefusal::ModeOnUpload);
    for (settings, direction, expected) in [
        (none, Direction::Upload, None),
        (none, Direction::Download, None),
        (none, Direction::Delete, None),
        (algorithm, Direction::Upload, None),
        (algorithm, Direction::Download, on_download),
        (mode, Direction::Upload, on_upload),
        (mode, Direction::Download, None),
        (both, Direction::Upload, on_upload),
        (both, Direction::Download, on_download),
    ] {
        assert_eq!(
            settings.checksum_refusal(direction),
            expected,
            "{settings:?} {direction}"
        );
    }
}

#[test]
fn checksum_refusals_spell_upstreams_messages() {
    assert_eq!(
        ChecksumRefusal::AlgorithmOnDownload.to_string(),
        "Expected checksum-algorithm parameter to be used with one of following path formats: \
         <LocalPath> <S3Uri>, <S3Uri> <S3Uri>. Instead, received <S3Uri> <LocalPath>."
    );
    assert_eq!(
        ChecksumRefusal::ModeOnUpload.to_string(),
        "Expected checksum-mode parameter to be used with one of following path formats: \
         <S3Uri> <LocalPath>. Instead, received <LocalPath> <S3Uri>."
    );
}

#[test]
fn admission_keeps_what_the_crt_or_botocore_would_refuse() {
    let refused = |settings: ObjectSettings<'_>| settings.admit_upload().is_some();
    for value in ["a\nb", "a\rb", "nul\0", "del\x7f", "\x1b[0m"] {
        assert!(
            refused(ObjectSettings {
                cache_control: Some(value),
                ..ObjectSettings::default()
            }),
            "{value:?}"
        );
    }
    for value in ["max-age=60", "tab\there", "  padded  ", "na\u{ef}ve", "~!"] {
        assert!(
            !refused(ObjectSettings {
                content_disposition: Some(value),
                ..ObjectSettings::default()
            }),
            "{value:?}"
        );
    }
    let metadata = |key: &str, value: &str| vec![(key.to_owned(), value.to_owned())];
    for (pairs, admitted) in [
        (metadata("key", "value"), true),
        (metadata("", "value"), true),
        (metadata("odd!#$%&'*+-.^_`|~", "tab\tvalue"), true),
        (metadata("a b", "value"), false),
        (metadata("a:b", "value"), false),
        (metadata("na\u{ef}ve", "value"), false),
        (metadata("key", "na\u{ef}ve"), false),
        (metadata("key", "a\nb"), false),
    ] {
        let settings = ObjectSettings {
            metadata: &pairs,
            ..ObjectSettings::default()
        };
        assert_eq!(!refused(settings), admitted, "{pairs:?}");
    }
}

#[test]
fn debug_hides_the_customer_key() {
    let key = CustomerKey::new(TEXT_KEY);
    assert_eq!(format!("{key:?}"), "CustomerKey(<redacted>)");
    let settings = ObjectSettings {
        customer_key: Some(key),
        ..ObjectSettings::default()
    };
    assert!(!format!("{settings:?}").contains("0123456789abcdef"));
}
