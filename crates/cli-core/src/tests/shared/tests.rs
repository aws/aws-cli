use super::*;
use std::ffi::OsStr;
#[test]
fn profile_precedence() {
    assert_eq!(aws_profile::select(&env(&[]), None), None);
    assert_eq!(aws_profile::select_or_default(&env(&[]), None), "default");
    assert_eq!(
        aws_profile::select(&env(&[("AWS_DEFAULT_PROFILE", "fallback")]), None),
        Some(OsStr::new("fallback"))
    );
    let env = env(&[("AWS_DEFAULT_PROFILE", "fallback"), ("AWS_PROFILE", "env")]);
    assert_eq!(aws_profile::select(&env, None), Some(OsStr::new("env")));
    assert_eq!(aws_profile::select_or_default(&env, None), "env");
    assert_eq!(
        aws_profile::select(&env, Some("flag")),
        Some(OsStr::new("flag"))
    );
    assert_eq!(aws_profile::select_or_default(&env, Some("flag")), "flag");
    assert!(aws_profile::is_explicit(Some("flag")));
}
#[test]
fn profile_empty_flag_and_variable_differ() {
    assert_eq!(aws_profile::select(&env(&[]), Some("")), None);
    assert!(!aws_profile::is_explicit(Some("")));
    assert!(!aws_profile::is_explicit(None));
    let env = env(&[("AWS_PROFILE", ""), ("AWS_DEFAULT_PROFILE", "fallback")]);
    assert_eq!(aws_profile::select(&env, Some("")), Some(OsStr::new("")));
    assert_eq!(aws_profile::select_or_default(&env, None), "");
}
#[cfg(unix)]
#[test]
fn profile_variable_that_is_not_unicode_selects_no_profile() {
    use std::os::unix::ffi::OsStrExt;
    let name = OsStr::from_bytes(b"\xff");
    let files = parsed(
        "[default]\nregion = us-west-2\n[profile \u{fffd}]\nregion = eu-west-1\n",
        None,
    );
    for variable in ["AWS_PROFILE", "AWS_DEFAULT_PROFILE"] {
        let env = SnapshotEnv::from_pairs([(variable, name)]);
        assert_eq!(aws_profile::select(&env, None), Some(name));
        assert_eq!(aws_profile::select_or_default(&env, Some("")), name);
        assert_eq!(
            aws_profile::select(&env, Some("flag")),
            Some(OsStr::new("flag"))
        );
    }
    let env = SnapshotEnv::from_pairs([
        ("AWS_PROFILE", name),
        ("AWS_DEFAULT_PROFILE", OsStr::new("default")),
    ]);
    let selected = aws_profile::select_or_default(&env, None);
    assert_eq!(selected, name);
    assert!(!aws_profile::explicit_profile_exists(&files, selected));
    assert!(aws_profile::explicit_profile_exists(&files, "\u{fffd}"));
    assert_eq!(
        shared_config::profile_property(&files, selected, "region"),
        None
    );
    assert!(!shared_config::profile_property_is_block(
        &files, selected, "region"
    ));
}
#[test]
fn selected_profiles_exist_in_either_file() {
    let files = parsed(
        "[default]\n[profile config-only]\n",
        Some("[credentials-only]\n"),
    );
    for name in ["default", "config-only", "credentials-only"] {
        assert!(aws_profile::explicit_profile_exists(&files, name));
    }
    assert!(!aws_profile::explicit_profile_exists(&files, "missing"));
    assert!(!aws_profile::explicit_profile_exists(&files, ""));
}
#[test]
fn malformed_shared_file_hides_every_profile() {
    let files = parsed("[default]\n[profile config-only]\n", Some("missing header"));
    assert!(!aws_profile::explicit_profile_exists(&files, "default"));
    assert!(!aws_profile::explicit_profile_exists(&files, "config-only"));
}
#[test]
fn file_locations_follow_override_and_home() {
    for (value, home, expected) in [
        (
            Some("/etc/aws/config"),
            Some("/home/me"),
            Some("/etc/aws/config"),
        ),
        (
            Some("relative/config"),
            Some("/home/me"),
            Some("relative/config"),
        ),
        (Some(""), Some("/home/me"), None),
        (Some("~"), Some("/home/me"), Some("/home/me")),
        (
            Some("~/aws/config"),
            Some("/home/me"),
            Some("/home/me/aws/config"),
        ),
        (Some("~/aws/config"), Some(""), None),
        (Some("~me/config"), Some("/home/me"), Some("~me/config")),
        (None, Some("/home/me"), Some("/home/me/.aws/config")),
        (None, Some(""), None),
    ] {
        let pairs = value
            .map(|v| ("AWS_CONFIG_FILE", v))
            .into_iter()
            .chain(home.map(|v| ("HOME", v)))
            .chain(NO_WINDOWS_HOME);
        let result =
            shared_config::locate(&SnapshotEnv::from_pairs(pairs), "AWS_CONFIG_FILE", "config");
        assert_eq!(result.as_deref(), expected.map(std::path::Path::new));
    }
}

#[test]
fn platform_home_and_tilde_rules_apply_to_both_shared_files() {
    let variables = env(&[("HOME", "/home/test"), ("USERPROFILE", "C:\\Users\\test")]);
    let home = if cfg!(windows) {
        "C:\\Users\\test"
    } else {
        "/home/test"
    };
    assert_eq!(shared_config::home_directory(&variables), Some(home.into()));
    for (variable, name) in [
        ("AWS_CONFIG_FILE", "config"),
        ("AWS_SHARED_CREDENTIALS_FILE", "credentials"),
    ] {
        assert_eq!(
            shared_config::locate(&variables, variable, name),
            Some(std::path::Path::new(home).join(".aws").join(name))
        );
        assert_eq!(shared_config::locate(&env(&NO_HOME), variable, name), None);
        let expanded = env(&[
            ("HOME", "/home/test"),
            ("USERPROFILE", "C:\\Users\\test"),
            (variable, "~/.aws/alternate"),
        ]);
        assert_eq!(
            shared_config::locate(&expanded, variable, name),
            Some(std::path::Path::new(home).join(".aws/alternate"))
        );
    }
    for (input, expected) in [
        ("~", Some("")),
        ("~/", Some("")),
        ("~/.aws/alternate", Some(".aws/alternate")),
        ("", None),
        ("~user/.aws/config", None),
        ("/tmp/config", None),
        ("./~/config", None),
    ] {
        assert_eq!(
            shared_config::home_relative_suffix(OsStr::new(input)).as_deref(),
            expected.map(OsStr::new)
        );
    }
    assert_eq!(
        shared_config::home_relative_suffix(OsStr::new("~\\.aws\\alternate")).as_deref(),
        cfg!(windows).then_some(OsStr::new(".aws\\alternate"))
    );
}

const NO_HOME: [(&str, &str); 4] = [
    ("HOME", ""),
    ("USERPROFILE", ""),
    ("HOMEDRIVE", ""),
    ("HOMEPATH", ""),
];
const NO_WINDOWS_HOME: [(&str, &str); 3] =
    [("USERPROFILE", ""), ("HOMEDRIVE", ""), ("HOMEPATH", "")];

#[test]
fn home_resolution_follows_each_platform_s_expanduser() {
    use shared_config::{POSIX_HOME_SOURCES, WINDOWS_HOME_SOURCES, home_directory_from};
    type HomeCase<'a> = (&'a [(&'a str, &'a str)], Option<&'a str>, Option<&'a str>);
    let cases: &[HomeCase<'_>] = &[
        (&[], None, None),
        (&[("HOME", "/h/")], Some("/h/"), Some("/h/")),
        (
            &[("HOME", "/h/"), ("USERPROFILE", "D:\\Users\\jane")],
            Some("/h/"),
            Some("D:\\Users\\jane"),
        ),
        (
            &[
                ("HOME", "/h/"),
                ("HOMEDRIVE", "D:"),
                ("HOMEPATH", "\\Users\\jane"),
            ],
            Some("/h/"),
            Some("D:\\Users\\jane"),
        ),
        (
            &[("HOME", "/h/"), ("HOMEDRIVE", "D:")],
            Some("/h/"),
            Some("/h/"),
        ),
        (
            &[("HOME", "/h/"), ("HOMEPATH", "\\Users\\jane")],
            Some("/h/"),
            Some("/h/"),
        ),
        (&NO_HOME, None, None),
    ];
    for (variables, posix, windows) in cases {
        let variables = env(variables);
        for (sources, expected) in [(POSIX_HOME_SOURCES, posix), (WINDOWS_HOME_SOURCES, windows)] {
            assert_eq!(
                home_directory_from(&variables, sources, None),
                expected.map(Into::into)
            );
        }
    }
    let all = env(&[
        ("HOME", "/h/"),
        ("USERPROFILE", "D:\\Users\\jane"),
        ("HOMEDRIVE", "D:"),
        ("HOMEPATH", "\\Users\\jane"),
    ]);
    let host = if cfg!(windows) {
        "D:\\Users\\jane"
    } else {
        "/h/"
    };
    assert_eq!(shared_config::home_directory(&all), Some(host.into()));
}

fn fake_passwd_home() -> Option<std::path::PathBuf> {
    Some("/fake/home".into())
}
fn missing_passwd_home() -> Option<std::path::PathBuf> {
    None
}
#[expect(
    clippy::panic,
    reason = "a fallback that must not run fails the test if it does"
)]
fn unreachable_passwd_home() -> Option<std::path::PathBuf> {
    panic!("the passwd fallback ran while a home variable was set")
}

#[test]
fn an_unset_home_falls_back_to_the_passwd_entry() {
    use shared_config::{POSIX_HOME_SOURCES, WINDOWS_HOME_SOURCES, home_directory_from};
    let unset = env(&[]);
    assert_eq!(
        home_directory_from(&unset, POSIX_HOME_SOURCES, Some(fake_passwd_home)),
        Some("/fake/home".into())
    );
    assert_eq!(
        home_directory_from(&unset, POSIX_HOME_SOURCES, Some(missing_passwd_home)),
        None
    );
    for (home, expected) in [("/h/", Some("/h/")), ("", None)] {
        assert_eq!(
            home_directory_from(
                &env(&[("HOME", home)]),
                POSIX_HOME_SOURCES,
                Some(unreachable_passwd_home)
            ),
            expected.map(Into::into)
        );
    }
    assert_eq!(
        home_directory_from(
            &env(&[("HOMEPATH", "\\Users\\jane")]),
            WINDOWS_HOME_SOURCES,
            Some(unreachable_passwd_home)
        ),
        None
    );
}

#[test]
fn unset_home_variables_locate_the_shared_files_under_the_platform_fallback() {
    let fallback = if cfg!(windows) {
        None
    } else {
        shared_config::home_directory(&env(&[]))
    };
    #[cfg(unix)]
    assert_eq!(fallback, crate::passwd::home_directory());
    for (variable, name) in [
        ("AWS_CONFIG_FILE", "config"),
        ("AWS_SHARED_CREDENTIALS_FILE", "credentials"),
    ] {
        assert_eq!(
            shared_config::locate(&env(&[]), variable, name),
            fallback.as_ref().map(|home| home.join(".aws").join(name))
        );
        assert_eq!(
            shared_config::locate(&env(&[(variable, "~/alternate")]), variable, name),
            fallback.as_ref().map(|home| home.join("alternate"))
        );
    }
}
#[test]
fn runtime_load_probes_aliases_under_the_injected_home() -> Result<(), awscli_config::ReadError> {
    #[derive(Debug, Default)]
    struct RecordingFs(std::cell::RefCell<Vec<std::path::PathBuf>>);
    impl awscli_config::Fs for RecordingFs {
        type Handle = std::fs::File;
        fn metadata(
            &self,
            path: &std::path::Path,
        ) -> Result<awscli_config::Metadata, awscli_config::ReadError> {
            self.0.borrow_mut().push(path.to_owned());
            Err(awscli_config::ReadError::FileNotFound)
        }
        fn open(&self, _: &std::path::Path) -> Result<Self::Handle, awscli_config::ReadError> {
            Err(awscli_config::ReadError::FileNotFound)
        }
    }
    let filesystem = RecordingFs::default();
    let files = shared_config::load(
        &filesystem,
        &env(&[
            ("HOME", "/injected-home"),
            ("USERPROFILE", "/injected-home"),
            ("AWS_CONFIG_FILE", "/elsewhere/config"),
            ("AWS_SHARED_CREDENTIALS_FILE", ""),
        ]),
    )?;
    assert_eq!(files.aliases.status, awscli_config::Status::Missing);
    assert_eq!(
        filesystem.0.take(),
        [
            std::path::PathBuf::from("/elsewhere/config"),
            std::path::PathBuf::from("/injected-home/.aws/cli/alias")
        ]
    );
    let homeless = SnapshotEnv::from_pairs(
        [
            ("AWS_CONFIG_FILE", "/elsewhere/config"),
            ("AWS_SHARED_CREDENTIALS_FILE", ""),
        ]
        .into_iter()
        .chain(NO_HOME),
    );
    let files = shared_config::load(&filesystem, &homeless)?;
    assert_eq!(files.aliases.status, awscli_config::Status::Omitted);
    assert!(files.aliases.sections.is_empty());
    assert_eq!(
        filesystem.0.into_inner(),
        [std::path::PathBuf::from("/elsewhere/config")]
    );
    Ok(())
}
#[test]
fn credentials_override_configuration_per_key() {
    let files = parsed(
        concat!(
            "[default]\n",
            "cli_error_format=legacy\n",
            "[profile work]\n",
            "cli_error_format=json\n",
            "cli_auto_prompt=on-partial\n",
        ),
        Some("[work]\ncli_error_format=enhanced\n[credentials-only]\ncli_auto_prompt=on\n"),
    );
    for (profile, key, value) in [
        ("default", "cli_error_format", Some("legacy")),
        ("default", "cli_auto_prompt", None),
        ("work", "cli_error_format", Some("enhanced")),
        ("work", "cli_auto_prompt", Some("on-partial")),
        ("credentials-only", "cli_auto_prompt", Some("on")),
        ("missing", "cli_error_format", None),
    ] {
        assert_eq!(shared_config::profile_property(&files, profile, key), value);
    }
}
#[test]
fn absent_and_omitted_files_define_nothing() {
    #[derive(Debug)]
    struct Missing;
    impl awscli_config::Fs for Missing {
        type Handle = std::fs::File;
        fn metadata(
            &self,
            _: &std::path::Path,
        ) -> Result<awscli_config::Metadata, awscli_config::ReadError> {
            Err(awscli_config::ReadError::FileNotFound)
        }
        fn open(&self, _: &std::path::Path) -> Result<Self::Handle, awscli_config::ReadError> {
            Err(awscli_config::ReadError::FileNotFound)
        }
    }
    let files = shared_config::load(
        &Missing,
        &env(&[
            ("AWS_CONFIG_FILE", "/absent/config"),
            ("AWS_SHARED_CREDENTIALS_FILE", ""),
        ]),
    )
    .unwrap();
    assert_eq!(files.config.status, awscli_config::Status::Missing);
    assert_eq!(files.credentials.status, awscli_config::Status::Omitted);
    assert!(files.profiles.as_ref().unwrap().is_empty());
    assert_eq!(
        shared_config::profile_property(&files, "default", "cli_error_format"),
        None
    );
}
#[test]
fn nested_and_malformed_files_are_not_scalar_properties() {
    let files = parsed("[default]\ns3=\n max_in_flight=4\n", None);
    assert_eq!(
        shared_config::profile_property(&files, "default", "s3"),
        None
    );
    assert_eq!(
        shared_config::profile_property(&files, "default", "max_in_flight"),
        None
    );
    assert_eq!(
        shared_config::profile_nested_property(&files, "default", "s3", "max_in_flight"),
        Some("4")
    );
    for (profile, key, nested) in [
        ("default", "s3", "other"),
        ("missing", "s3", "other"),
        ("default", "max_in_flight", "x"),
    ] {
        assert_eq!(
            shared_config::profile_nested_property(&files, profile, key, nested),
            None
        );
    }
    for (profile, key, is_block) in [
        ("default", "s3", true),
        ("default", "max_in_flight", false),
        ("missing", "s3", false),
    ] {
        assert_eq!(
            shared_config::profile_property_is_block(&files, profile, key),
            is_block
        );
    }
    malformed_files_are_not_properties();
}
fn malformed_files_are_not_properties() {
    let files = parsed(
        "[default]\ncli_error_format=json\n",
        Some("no section header"),
    );
    assert!(files.profiles.is_none());
    assert_eq!(
        shared_config::profile_property(&files, "default", "cli_error_format"),
        None
    );
    assert_eq!(
        shared_config::profile_nested_property(&files, "default", "s3", "x"),
        None
    );
    assert!(!shared_config::profile_property_is_block(
        &files, "default", "s3"
    ));
}
