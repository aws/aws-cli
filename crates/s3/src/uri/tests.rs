#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
#[test]
fn parses_object_uri() {
    assert_eq!(
        parse_s3_uri(b"s3://bucket/path/file").unwrap(),
        S3Uri {
            bucket: "bucket",
            key: b"path/file"
        }
    );
}
#[test]
fn resource_aliases_require_python() {
    for suffix in [
        "-s3alias",
        "--ol-s3",
        ".mrap",
        "--x-s3",
        "--table-s3",
        "--op-s3",
    ] {
        assert!(!supports_native_bucket(&format!("bucket{suffix}")));
    }
    for bucket in ["B", "a_b", "192.168.0.1", "bucket-name"] {
        assert!(supports_native_bucket(bucket));
    }
}
#[test]
fn bucket_syntax_matches_cli() {
    for bucket in ["", "bad space", "a:b", "ä", "a/b", "a\0b"] {
        assert!(!supports_native_bucket(bucket));
    }
    assert!(supports_native_bucket(&"a".repeat(255)));
    assert!(!supports_native_bucket(&"a".repeat(256)));
}
#[test]
fn rejects_non_s3() {
    assert_eq!(parse_s3_uri(b"local"), Err(S3UriParseError::NotS3Uri));
}
#[test]
fn requires_object_key() {
    for value in ["s3://bucket", "s3://bucket/"] {
        assert_eq!(
            parse_s3_uri(value.as_bytes()),
            Err(S3UriParseError::MissingS3ObjectKey)
        );
    }
}
#[test]
fn requires_bucket() {
    for value in ["s3://", "s3:///key"] {
        assert_eq!(
            parse_s3_uri(value.as_bytes()),
            Err(S3UriParseError::MissingS3Bucket)
        );
    }
}
#[test]
fn rejects_malformed_scheme() {
    for value in ["s3:", "s3:/a", "s3:a/b"] {
        assert_eq!(
            parse_s3_uri(value.as_bytes()),
            Err(S3UriParseError::InvalidS3UriScheme)
        );
    }
}
#[test]
fn schemes_are_case_sensitive() {
    for value in ["S3://b/k", "S3:/k", "S3:b/k"] {
        assert_eq!(
            parse_s3_uri(value.as_bytes()),
            Err(S3UriParseError::NotS3Uri)
        );
    }
}
#[test]
fn preserves_key_slashes() {
    for key in ["/", "/a//b", "a///", "a/../b"] {
        let value = format!("s3://b/{key}");
        assert_eq!(parse_s3_uri(value.as_bytes()).unwrap().key, key.as_bytes());
    }
}
#[test]
fn parses_recursive_prefix() {
    for (value, prefix) in [("s3://b", ""), ("s3://b/", ""), ("s3://b/a//", "a//")] {
        assert_eq!(
            parse_s3_prefix_uri(value.as_bytes()).unwrap(),
            S3PrefixUri {
                bucket: "b",
                prefix: prefix.as_bytes()
            }
        );
    }
}
#[test]
fn prefix_requires_bucket() {
    for value in ["s3://", "s3:///prefix"] {
        assert_eq!(
            parse_s3_prefix_uri(value.as_bytes()),
            Err(S3PrefixUriParseError::MissingS3Bucket)
        );
    }
}
#[test]
fn each_parser_reports_its_own_error_kind() {
    use S3ListTargetParseError as List;
    use S3PrefixUriParseError as Prefix;
    use S3UriParseError as Object;
    for (value, object, prefix, list) in [
        (
            "s3:bucket",
            Object::InvalidS3UriScheme,
            Prefix::InvalidS3UriScheme,
            Some(List::InvalidS3UriScheme),
        ),
        (
            "s3://",
            Object::MissingS3Bucket,
            Prefix::MissingS3Bucket,
            None,
        ),
        (
            "s3:///p",
            Object::MissingS3Bucket,
            Prefix::MissingS3Bucket,
            Some(List::MissingS3Bucket),
        ),
        (
            "https://b",
            Object::NotS3Uri,
            Prefix::NotS3Uri,
            Some(List::InvalidS3UriScheme),
        ),
        (
            "S3://bucket",
            Object::NotS3Uri,
            Prefix::NotS3Uri,
            Some(List::InvalidS3UriScheme),
        ),
        (
            "s3:////",
            Object::MissingS3Bucket,
            Prefix::MissingS3Bucket,
            Some(List::MissingS3Bucket),
        ),
    ] {
        assert_eq!(parse_s3_uri(value.as_bytes()), Err(object), "{value}");
        assert_eq!(
            parse_s3_prefix_uri(value.as_bytes()),
            Err(prefix),
            "{value}"
        );
        match list {
            Some(list) => assert_eq!(
                parse_s3_list_target(Some(value.as_bytes())),
                Err(list),
                "{value}"
            ),
            None => assert_eq!(
                parse_s3_list_target(Some(value.as_bytes())).unwrap().bucket,
                None
            ),
        }
    }
}
#[test]
fn prefix_errors_map_to_their_object_uri_kinds() {
    for (prefix, object) in [
        (S3PrefixUriParseError::NotS3Uri, S3UriParseError::NotS3Uri),
        (
            S3PrefixUriParseError::InvalidS3UriScheme,
            S3UriParseError::InvalidS3UriScheme,
        ),
        (
            S3PrefixUriParseError::MissingS3Bucket,
            S3UriParseError::MissingS3Bucket,
        ),
        (
            S3PrefixUriParseError::BucketNotUtf8,
            S3UriParseError::BucketNotUtf8,
        ),
    ] {
        assert_eq!(S3UriParseError::from(prefix), object);
    }
}
#[test]
fn keys_keep_bytes_that_are_not_utf8_and_buckets_must_be_utf8() {
    assert_eq!(
        parse_s3_uri(b"s3://b/key-\xff"),
        Ok(S3Uri {
            bucket: "b",
            key: b"key-\xff"
        })
    );
    assert_eq!(
        parse_s3_prefix_uri(b"s3://b/prefix-\xff/"),
        Ok(S3PrefixUri {
            bucket: "b",
            prefix: b"prefix-\xff/"
        })
    );
    for value in [b"s3://b/prefix-\xff".as_slice(), b"b/prefix-\xff"] {
        let target = parse_s3_list_target(Some(value)).unwrap();
        assert_eq!(
            (target.bucket, target.prefix),
            (Some("b"), b"prefix-\xff".as_slice())
        );
    }
    assert_eq!(
        parse_s3_uri(b"s3://b-\xff/key"),
        Err(S3UriParseError::BucketNotUtf8)
    );
    assert_eq!(
        parse_s3_prefix_uri(b"s3://b-\xff"),
        Err(S3PrefixUriParseError::BucketNotUtf8)
    );
    assert_eq!(
        parse_s3_list_target(Some(b"b-\xff/prefix")),
        Err(S3ListTargetParseError::BucketNotUtf8)
    );
}
#[test]
fn normalizes_directory_prefix() {
    for (input, output) in [("", ""), ("a", "a/"), ("a/", "a/"), ("a//", "a//")] {
        assert_eq!(
            normalize_recursive_s3_prefix(input.as_bytes()),
            output.as_bytes()
        );
    }
}
#[test]
fn encodes_request_path() {
    assert_eq!(encode_s3_request_path_key("a b/x+y?#"), "a%20b/x%2By%3F%23");
}
#[test]
fn encodes_all_reserved_ascii() {
    for byte in 0..=127u8 {
        let value = char::from(byte).to_string();
        let expected = if byte.is_ascii_alphanumeric() || b"-_.~/".contains(&byte) {
            value.clone()
        } else {
            format!("%{byte:02X}")
        };
        assert_eq!(encode_s3_request_path_key(&value), expected);
    }
}
#[test]
fn encoded_path_retains_empty_components() {
    assert_eq!(encode_s3_request_path_key("//a///b/"), "//a///b/");
}
#[test]
fn encoding_is_utf8_and_not_idempotent() {
    assert_eq!(encode_s3_request_path_key("é/%20"), "%C3%A9/%2520");
}
#[test]
fn lexical_parent_escape_detection() {
    for (key, escapes) in [
        ("../file.txt", true),
        ("../../file.txt", true),
        ("../..", true),
        ("logs/../../file.txt", true),
        ("/../file.txt", true),
        ("./../file.txt", true),
        ("logs//../../file.txt", true),
        ("..", false),
        ("../", false),
        ("./../", false),
        ("logs/../..", false),
        ("", false),
        (".", false),
        ("./", false),
        ("/", false),
        ("logs/../file.txt", false),
        ("logs/subdir/../..", false),
        ("logs//file.txt", false),
        ("./logs/./file.txt", false),
        ("logs/.../file.txt", false),
    ] {
        assert_eq!(relative_key_escapes_root(key), escapes, "{key}");
    }
}
#[test]
fn root_parent_detection() {
    for (key, root_parent) in [
        ("..", true),
        ("../", true),
        ("logs/../..", true),
        ("../outside/..", true),
        ("./..", true),
        ("../..", false),
        ("../file.txt", false),
        ("logs/..", false),
        ("logs/../file.txt", false),
        ("", false),
        ("...", false),
    ] {
        assert_eq!(relative_key_names_root_parent(key), root_parent, "{key}");
    }
    assert!(relative_key_names_root_parent_with(r"logs\..\..", true));
    assert!(!relative_key_names_root_parent_with(r"logs\..\..", false));
}
#[test]
fn parent_references_use_injected_windows_and_posix_separators() {
    for (key, escapes) in [
        (r"..\escaped.txt", true),
        (r"..\..\escaped.txt", true),
        (r"logs\..\..\escaped.txt", true),
        (r"logs/..\..\escaped.txt", true),
        (r"logs\../..\escaped.txt", true),
        (r"\..\escaped.txt", true),
        (r".\..\escaped.txt", true),
        (r"logs\\..\..\escaped.txt", true),
        (r"logs\..", false),
        (r"logs\..\file.txt", false),
        (r"logs\subdir\..\..", false),
        (r"logs\file.txt", false),
        (r".. \file.txt", false),
        (r"...\file.txt", false),
        (r"..file\file.txt", false),
    ] {
        assert_eq!(relative_key_escapes_root_with(key, true), escapes, "{key}");
    }
    for key in [r"..\escaped.txt", r"logs\..\..\escaped.txt", r"..\.."] {
        assert!(!relative_key_escapes_root_with(key, false));
    }
    assert_eq!(relative_key_escapes_root(r"..\escaped.txt"), cfg!(windows));
}
