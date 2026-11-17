use super::*;
use crate::SnapshotEnv;
use awscli_config::StdFs;
use std::sync::atomic::{AtomicUsize, Ordering};

struct Directory(PathBuf);

impl Directory {
    fn new() -> std::io::Result<Self> {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!(
            "aws-cli-raw-config-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&path)?;
        Ok(Self(path))
    }
}

impl Drop for Directory {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

const PLATFORM_HOME: &str = if cfg!(windows) { "USERPROFILE" } else { "HOME" };

#[test]
fn a_boto_config_supplies_credentials_only_with_an_access_key()
-> Result<(), Box<dyn std::error::Error>> {
    let directory = Directory::new()?;
    let boto = directory.0.join("boto");
    for (data, supplies) in [
        (None, false),
        (Some(""), false),
        (
            Some("[Credentials]\ngs_oauth2_refresh_token = token\n"),
            false,
        ),
        (Some("[Other]\naws_access_key_id = key\n"), false),
        (Some("[Credentials]\naws_access_key_id = key\n"), true),
        (Some("no section header\n"), true),
    ] {
        if let Some(data) = data {
            std::fs::write(&boto, data)?;
        }
        let env = SnapshotEnv::from_pairs([("BOTO_CONFIG", boto.clone().into_os_string())]);
        assert_eq!(
            boto_config_supplies_credentials(&StdFs, &env)?,
            supplies,
            "{data:?}"
        );
    }
    std::fs::write(
        directory.0.join(".boto"),
        "[Credentials]\naws_access_key_id = key\n",
    )?;
    let home = (PLATFORM_HOME, directory.0.clone().into_os_string());
    let env = SnapshotEnv::from_pairs([home.clone()]);
    assert!(boto_config_supplies_credentials(&StdFs, &env)?);
    let env = SnapshotEnv::from_pairs([home.clone(), ("BOTO_CONFIG", OsString::new())]);
    assert!(!boto_config_supplies_credentials(&StdFs, &env)?);
    std::fs::write(
        directory.0.join("legacy.cfg"),
        "[Credentials]\naws_access_key_id = key\n",
    )?;
    let env = SnapshotEnv::from_pairs([home, ("BOTO_CONFIG", OsString::from("~//legacy.cfg"))]);
    assert!(boto_config_supplies_credentials(&StdFs, &env)?);
    Ok(())
}

#[test]
fn the_alias_file_loads_without_contributing_a_profile() -> Result<(), Box<dyn std::error::Error>> {
    let directory = Directory::new()?;
    std::fs::create_dir_all(directory.0.join(".aws/cli"))?;
    std::fs::write(
        directory.0.join(".aws/cli/alias"),
        "[command s3]\nhello = !echo hi\n",
    )?;
    let missing = directory.0.join("missing");
    let env = SnapshotEnv::from_pairs([
        (PLATFORM_HOME, directory.0.clone().into_os_string()),
        ("AWS_CONFIG_FILE", missing.join("config").into_os_string()),
        (
            "AWS_SHARED_CREDENTIALS_FILE",
            missing.join("credentials").into_os_string(),
        ),
    ]);
    let files = load(&StdFs, &env)?;
    assert_eq!(files.aliases.status, Status::Loaded);
    assert_eq!(
        files
            .aliases
            .sections
            .get("command s3")
            .and_then(|entries| entries.get("hello"))
            .and_then(|entry| entry.value.as_str()),
        Some("!echo hi")
    );
    assert_eq!(
        files.profiles.as_ref().map(|profiles| profiles.len()),
        Some(0)
    );
    Ok(())
}

#[cfg(unix)]
mod posix {
    use super::*;
    use awscli_config::Status;
    use std::os::unix::ffi::{OsStrExt, OsStringExt};
    use std::path::Path;

    fn raw(value: &[u8]) -> OsString {
        OsString::from_vec(value.to_vec())
    }

    fn refuses_non_utf8_name(error: &std::io::Error) -> bool {
        error.raw_os_error() == Some(libc::EILSEQ)
    }

    fn write_shared_files(config: &Path, credentials: &Path) -> std::io::Result<()> {
        std::fs::write(config, "[default]\nregion=us-west-2\n")?;
        std::fs::write(credentials, "[default]\naws_access_key_id=fixture-key\n")
    }

    fn assert_loaded(env: &SnapshotEnv) -> Result<ParsedFiles, ReadError> {
        let files = load(&StdFs, env)?;
        assert_eq!(files.config.status, Status::Loaded);
        assert_eq!(files.credentials.status, Status::Loaded);
        assert_eq!(
            profile_property(&files, "default", "region"),
            Some("us-west-2")
        );
        assert_eq!(
            profile_property(&files, "default", "aws_access_key_id"),
            Some("fixture-key")
        );
        Ok(files)
    }

    #[test]
    fn snapshot_keeps_raw_values_out_of_string_accessors() {
        let path = raw(b"/raw/\xff/config");
        let env = SnapshotEnv::from_pairs([
            ("AWS_CONFIG_FILE", path.clone()),
            ("AWS_REGION", OsString::from("us-west-2")),
        ]);
        assert_eq!(env.var_os("AWS_CONFIG_FILE"), Some(path.as_os_str()));
        assert_eq!(env.var("AWS_CONFIG_FILE"), None);
        assert_eq!(
            env.iter().collect::<Vec<_>>(),
            [("AWS_REGION", "us-west-2")]
        );
        assert_eq!(env.var_os("MISSING"), None);
    }

    #[test]
    fn direct_raw_overrides_load_the_named_files() -> Result<(), Box<dyn std::error::Error>> {
        let directory = Directory::new()?;
        let config = directory.0.join(raw(b"config-\xff"));
        let credentials = directory.0.join(raw(b"credentials-\xfe"));
        match write_shared_files(&config, &credentials) {
            Err(error) if refuses_non_utf8_name(&error) => return Ok(()),
            result => result?,
        }
        let env = SnapshotEnv::from_pairs([
            ("AWS_CONFIG_FILE", config.into_os_string()),
            ("AWS_SHARED_CREDENTIALS_FILE", credentials.into_os_string()),
        ]);
        assert_loaded(&env)?;
        Ok(())
    }

    #[test]
    fn raw_home_loads_default_shared_files_and_aliases() -> Result<(), Box<dyn std::error::Error>> {
        let directory = Directory::new()?;
        let home = directory.0.join(raw(b"home-\xff"));
        let aws = home.join(".aws");
        match std::fs::create_dir_all(aws.join("cli")) {
            Err(error) if refuses_non_utf8_name(&error) => return Ok(()),
            result => result?,
        }
        write_shared_files(&aws.join("config"), &aws.join("credentials"))?;
        std::fs::write(aws.join("cli/alias"), "[toplevel]\nlist=s3 ls\n")?;
        let env = SnapshotEnv::from_pairs([("HOME", home.into_os_string())]);
        let files = assert_loaded(&env)?;
        assert_eq!(files.aliases.status, Status::Loaded);
        assert_eq!(
            files
                .aliases
                .sections
                .get("toplevel")
                .and_then(|entries| entries.get("list"))
                .and_then(|entry| entry.value.as_str()),
            Some("s3 ls")
        );
        Ok(())
    }

    #[test]
    fn raw_tilde_suffixes_load_files_without_normalizing_other_prefixes()
    -> Result<(), Box<dyn std::error::Error>> {
        let directory = Directory::new()?;
        for value in [b"~user/config-\xff".as_slice(), b"~\\config-\xff"] {
            let env = SnapshotEnv::from_pairs([("AWS_CONFIG_FILE", raw(value))]);
            assert_eq!(
                locate(&env, "AWS_CONFIG_FILE", "config"),
                Some(raw(value).into())
            );
        }
        let expanded = SnapshotEnv::from_pairs([
            ("HOME", directory.0.clone().into_os_string()),
            ("AWS_CONFIG_FILE", raw(b"~//absolute-\xff/")),
        ]);
        let path = locate(&expanded, "AWS_CONFIG_FILE", "config")
            .ok_or("tilde path requires the injected home")?;
        let mut expected = directory.0.clone().into_os_string().into_vec();
        expected.extend_from_slice(b"/absolute-\xff/");
        assert_eq!(path.as_os_str().as_bytes(), expected);
        let config = raw(b"config-\xff");
        let credentials = raw(b"credentials-\xfe");
        match write_shared_files(&directory.0.join(&config), &directory.0.join(&credentials)) {
            Err(error) if refuses_non_utf8_name(&error) => return Ok(()),
            result => result?,
        }
        let env = SnapshotEnv::from_pairs([
            ("HOME", directory.0.clone().into_os_string()),
            ("AWS_CONFIG_FILE", raw(b"~/config-\xff")),
            ("AWS_SHARED_CREDENTIALS_FILE", raw(b"~/credentials-\xfe")),
        ]);
        assert_loaded(&env)?;
        Ok(())
    }
}

#[cfg(windows)]
mod windows {
    use super::*;
    use std::os::windows::ffi::{OsStrExt, OsStringExt};

    fn with_surrogate(prefix: &str, suffix: &str) -> OsString {
        OsString::from_wide(
            &prefix
                .encode_utf16()
                .chain([0xd800])
                .chain(suffix.encode_utf16())
                .collect::<Vec<_>>(),
        )
    }

    #[test]
    fn raw_windows_overrides_preserve_surrogates_and_case_insensitive_names() {
        let path = with_surrogate("C:\\config-", "");
        let env = SnapshotEnv::from_pairs([
            ("AWS_CONFIG_FILE", OsString::from("old")),
            ("aws_config_file", path.clone()),
        ]);
        assert_eq!(env.var_os("Aws_Config_File"), Some(path.as_os_str()));
        assert_eq!(env.var("AWS_CONFIG_FILE"), None);
        assert_eq!(env.iter().count(), 0);
        assert_eq!(locate(&env, "AWS_CONFIG_FILE", "config"), Some(path.into()));
    }

    #[test]
    fn windows_home_precedence_retains_each_raw_source() {
        let home = with_surrogate("C:\\home-", "");
        let profile = with_surrogate("D:\\profile-", "");
        let drive = with_surrogate("E:", "");
        let path = with_surrogate("\\path-", "");
        let mut combined = drive.clone();
        combined.push(&path);
        for (profile_value, drive_value, expected) in [
            (
                profile,
                drive.clone(),
                PathBuf::from(with_surrogate("D:\\profile-", "")),
            ),
            (OsString::new(), drive, PathBuf::from(combined)),
            (OsString::new(), OsString::new(), PathBuf::from(&home)),
        ] {
            let env = SnapshotEnv::from_pairs([
                ("HOME", home.clone()),
                ("USERPROFILE", profile_value),
                ("HOMEDRIVE", drive_value),
                ("HOMEPATH", path.clone()),
            ]);
            assert_eq!(home_directory(&env), Some(expected.clone()));
            assert_eq!(
                locate(&env, "AWS_CONFIG_FILE", "config"),
                Some(expected.join(".aws").join("config"))
            );
        }
    }

    #[test]
    fn windows_tilde_expansion_preserves_home_and_suffix_surrogates() {
        let home = with_surrogate("C:\\home-", "");
        let suffix = with_surrogate("config-", "");
        for prefix in ["~/", "~\\"] {
            let mut value = OsString::from(prefix);
            value.push(&suffix);
            let env = SnapshotEnv::from_pairs([
                ("USERPROFILE", home.clone()),
                ("AWS_CONFIG_FILE", value),
            ]);
            let actual = locate(&env, "AWS_CONFIG_FILE", "config");
            let expected = PathBuf::from(&home).join(&suffix);
            assert_eq!(actual.as_deref(), Some(expected.as_path()));
            assert_eq!(
                actual.map(|path| path.as_os_str().encode_wide().collect::<Vec<_>>()),
                Some(expected.as_os_str().encode_wide().collect::<Vec<_>>())
            );
        }
    }
}
