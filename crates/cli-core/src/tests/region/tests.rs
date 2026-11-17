use super::*;
use crate::region::{DEFAULT_REGION, RegionError, resolve_region};
#[test]
fn command_line_beats_environment_and_profile() {
    assert_eq!(
        resolve_region(
            &env(&[("AWS_REGION", "us-west-2")]),
            &parsed("[default]\nregion=ap-south-1\n", None),
            Some("eu-west-1"),
            None
        ),
        Ok("eu-west-1")
    );
}
#[test]
fn aws_region_beats_default_region_and_profile() {
    assert_eq!(
        resolve_region(
            &env(&[
                ("AWS_REGION", "us-west-2"),
                ("AWS_DEFAULT_REGION", "us-east-2")
            ]),
            &parsed("[default]\nregion=ap-south-1\n", None),
            None,
            None
        ),
        Ok("us-west-2")
    );
}
#[test]
fn empty_aws_region_falls_back() {
    assert_eq!(
        resolve_region(
            &env(&[("AWS_REGION", ""), ("AWS_DEFAULT_REGION", "us-east-2")]),
            &ParsedFiles::parse(Inputs::default()),
            None,
            None
        ),
        Ok("us-east-2")
    );
}
#[test]
fn default_region_beats_shared_profile() {
    assert_eq!(
        resolve_region(
            &env(&[("AWS_DEFAULT_REGION", "eu-north-1")]),
            &parsed("[default]\nregion=ap-south-1\n", None),
            None,
            None
        ),
        Ok("eu-north-1")
    );
}
#[test]
fn empty_command_line_region_is_rejected() {
    assert_eq!(
        resolve_region(
            &env(&[]),
            &ParsedFiles::parse(Inputs::default()),
            Some(""),
            None
        ),
        Err(RegionError::EmptyRegion)
    );
}
#[test]
fn region_uses_profile_precedence() {
    let files = parsed(
        concat!(
            "[default]\n",
            "region=us-west-2\n",
            "[profile dev]\n",
            "region=eu-central-1\n",
            "[profile cli]\n",
            "region=ap-northeast-1\n",
            "[profile fallback]\n",
            "region=sa-east-1\n",
        ),
        None,
    );
    assert_eq!(
        resolve_region(&env(&[]), &files, None, None),
        Ok("us-west-2")
    );
    assert_eq!(
        resolve_region(
            &env(&[("AWS_DEFAULT_PROFILE", "fallback")]),
            &files,
            None,
            None
        ),
        Ok("sa-east-1")
    );
    let env = env(&[("AWS_DEFAULT_PROFILE", "fallback"), ("AWS_PROFILE", "dev")]);
    assert_eq!(resolve_region(&env, &files, None, None), Ok("eu-central-1"));
    assert_eq!(
        resolve_region(&env, &files, None, Some("cli")),
        Ok("ap-northeast-1")
    );
}
#[test]
fn credentials_region_wins() {
    let files = parsed(
        "[default]\nregion=us-west-2\n[profile work]\nregion=us-east-1\n",
        Some("[work]\nregion=eu-west-1\n[credentials-only]\nregion=sa-east-1\n"),
    );
    for (name, expected) in [
        ("default", "us-west-2"),
        ("work", "eu-west-1"),
        ("credentials-only", "sa-east-1"),
    ] {
        assert_eq!(
            resolve_region(&env(&[]), &files, None, Some(name)),
            Ok(expected)
        );
    }
}
#[test]
fn empty_or_missing_profile_region_uses_default() {
    let files = parsed(
        "[default]\nregion=\n[profile other]\nregion=us-west-1\n",
        None,
    );
    for profile in [None, Some("missing")] {
        assert_eq!(
            resolve_region(&env(&[]), &files, None, profile),
            Ok(DEFAULT_REGION)
        );
    }
}
#[test]
fn missing_or_omitted_shared_files_use_default() {
    let mut files = ParsedFiles::parse(Inputs::default());
    files.config.status = awscli_config::Status::Missing;
    assert_eq!(
        resolve_region(&env(&[]), &files, None, None),
        Ok(DEFAULT_REGION)
    );
}
#[test]
fn malformed_shared_file_defines_no_region() {
    assert_eq!(
        resolve_region(
            &env(&[]),
            &parsed(
                concat!(
                    "[profile ignored\r\n",
                    "region=should-not-match\r\n",
                    "[profile dev]\r\n",
                    "region=eu-central-2\r\n",
                ),
                None
            ),
            None,
            Some("dev")
        ),
        Ok(DEFAULT_REGION)
    );
}
#[test]
fn inline_comments_remain_region_text() {
    assert_eq!(
        resolve_region(
            &env(&[]),
            &parsed(
                concat!(
                    "[profile dev]\r\n",
                    "# comment\r\n",
                    "; other\r\n",
                    "unknown=value\r\n",
                    "region=eu-central-2 ; trailing comment\r\n",
                ),
                None
            ),
            None,
            Some("dev")
        ),
        Ok("eu-central-2 ; trailing comment")
    );
}

#[test]
fn region_names_reproduce_botocore_regex_boundaries() {
    for value in [
        "us-east-1",
        "fips-us-east-1",
        "US-EAST-1",
        "x",
        "a0",
        "",
        "us-east-1\n",
    ] {
        assert!(crate::region::is_valid_name(value), "{value:?}");
    }
    for value in [
        "123",
        "-us-east-1",
        "us-east-1-",
        "a.b",
        " a",
        "a_1",
        "é",
        "a\n\n",
    ] {
        assert!(!crate::region::is_valid_name(value), "{value:?}");
    }
    assert!(crate::region::is_valid_name(&"a".repeat(63)));
    assert!(!crate::region::is_valid_name(&"a".repeat(64)));
}

#[test]
fn configured_region_excludes_the_sdk_default_and_keeps_empty_flag_errors() {
    use crate::region::{configured_region, is_configured};
    let files = parsed(
        "[default]\nregion=\n[profile other]\nregion=us-west-1\n",
        None,
    );
    let mut environment = std::collections::BTreeMap::<String, String>::new();
    assert_eq!(
        configured_region(&environment, &files, None, None),
        Ok(None)
    );
    environment.insert("AWS_REGION".into(), String::new());
    assert_eq!(
        configured_region(&environment, &files, None, None),
        Ok(None)
    );
    assert_eq!(
        configured_region(&environment, &files, None, Some("other")),
        Ok(Some("us-west-1"))
    );
    environment.insert("AWS_DEFAULT_REGION".into(), "eu-west-1".into());
    assert_eq!(
        configured_region(&environment, &files, None, Some("other")),
        Ok(Some("eu-west-1"))
    );
    assert_eq!(
        configured_region(&environment, &files, Some("ap-south-1"), None),
        Ok(Some("ap-south-1"))
    );
    assert_eq!(
        configured_region(&environment, &files, Some(""), None),
        Err(RegionError::EmptyRegion)
    );
    assert!(is_configured(&environment, &files, Some(""), None));
    environment.remove("AWS_DEFAULT_REGION");
    assert!(!is_configured(&environment, &files, None, None));
    assert!(is_configured(&environment, &files, None, Some("other")));
}
