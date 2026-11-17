use super::*;
use crate::deps::tests::Directory;

fn environment(command: &Command, name: &str) -> Option<std::ffi::OsString> {
    command
        .get_envs()
        .find(|(key, _)| *key == name)
        .and_then(|(_, value)| value.map(ToOwned::to_owned))
}

#[test]
fn windows_openssl_names_clang_cl_through_the_search_path() -> Result<()> {
    let maps = ["-ffile-prefix-map=C:/w/=crt-work/".to_owned()];
    let existing = std::env::join_paths(["/system/bin", "/other/bin"])
        .map_err(|failure| error(failure.to_string()))?;
    let mut command = Command::new("perl");
    command
        .env("PATH", &existing)
        .env("AR", "/llvm/bin/llvm-ar");
    apply_openssl_compiler(
        &mut command,
        Path::new("/llvm install/bin/clang"),
        &maps,
        true,
    )?;
    // OpenSSL records CC in its build information; it names no directory.
    assert_eq!(environment(&command, "CC"), Some("clang-cl".into()));
    // The makefile passes lib's options to AR, which llvm-ar refuses.
    for name in ["AR", "RANLIB"] {
        assert!(
            command
                .get_envs()
                .any(|(key, value)| key == name && value.is_none()),
            "{name} is inherited"
        );
    }
    let path = environment(&command, "PATH").ok_or_else(|| error("PATH is unset"))?;
    assert_eq!(
        std::env::split_paths(&path).collect::<Vec<_>>(),
        [
            Path::new("/llvm install/bin"),
            Path::new("/system/bin"),
            Path::new("/other/bin")
        ]
    );
    assert_eq!(
        environment(&command, "_CL_"),
        Some(source_paths::clang_cl_variable(&maps).into())
    );
    assert_eq!(
        environment(&command, "SOURCE_DATE_EPOCH"),
        Some("946684800".into())
    );
    Ok(())
}

#[test]
fn posix_openssl_names_its_relative_map_wrapper() -> Result<()> {
    let mut command = Command::new("perl");
    apply_openssl_compiler(&mut command, Path::new("/llvm/bin/clang"), &[], false)?;
    assert_eq!(environment(&command, "CC"), Some("./native-cc".into()));
    assert_eq!(environment(&command, "_CL_"), None);
    Ok(())
}

/// Build information as `util/mkbuildinf.pl` writes it for `flags`.
fn build_information(flags: &str) -> String {
    let mut text = String::from("static const char compiler_flags[] = {\n");
    for character in format!("compiler: {}", flags.replace('\\', "\\\\")).chars() {
        match character {
            '\\' | '\'' => text.push_str(&format!("'\\{character}',")),
            _ => text.push_str(&format!("'{character}',")),
        }
    }
    text.push_str("'\\0'\n};\n");
    text
}

#[test]
fn recorded_openssl_flags_decode_mkbuildinf_escapes() -> Result<()> {
    let flags = "C:\\llvm\\bin\\clang-cl /MT -DX='y'";
    assert_eq!(
        recorded_compiler_flags(&build_information(flags))?,
        format!("compiler: {flags}")
    );
    assert!(recorded_compiler_flags("no flags").is_err());
    assert!(recorded_compiler_flags("compiler_flags[] = { 'a',").is_err());
    Ok(())
}

#[test]
fn openssl_build_information_rejects_physical_compiler_paths() -> Result<()> {
    let directory = std::env::temp_dir().join(format!("openssl-buildinf-{}", std::process::id()));
    fs::create_dir_all(directory.join("crypto"))?;
    let buildinf = directory.join("crypto/buildinf.h");
    let clang = Path::new("C:\\llvm install\\bin");
    let prefix = Path::new("/store/openssl");
    let posix_clang = Path::new("/tmp/a\\b/bin");
    let checks: [(&str, bool); 5] = [
        ("clang-cl /MT -O2", true),
        ("C:\\llvm install\\bin\\clang-cl.exe /MT", false),
        ("C:/llvm install/bin/clang-cl.exe /MT", false),
        ("./native-cc -I/store/openssl/include", false),
        ("/tmp/a\\b/bin/clang -O2", false),
    ];
    for (flags, accepted) in checks {
        fs::write(&buildinf, build_information(flags))?;
        assert_eq!(
            verify_openssl_build_information(&directory, &[prefix, clang, posix_clang]).is_ok(),
            accepted,
            "{flags}"
        );
    }
    fs::remove_dir_all(&directory)?;
    Ok(())
}

#[test]
fn a_prefix_validates_only_with_both_archives_and_the_headers() -> Result<()> {
    let directory = super::super::super::tests::Directory::new()?;
    let prefix = &directory.0;
    fs::create_dir_all(prefix.join("include/openssl"))?;
    fs::create_dir_all(prefix.join("lib"))?;
    let required = [
        prefix.join("include/openssl/ssl.h"),
        prefix
            .join("lib")
            .join(platform::archive_name(std::env::consts::OS, "ssl")),
        prefix
            .join("lib")
            .join(platform::archive_name(std::env::consts::OS, "crypto")),
    ];
    for path in &required {
        fs::write(path, "")?;
    }
    validate(prefix)?;
    for path in &required {
        fs::remove_file(path)?;
        assert!(validate(prefix).is_err(), "{}", path.display());
        fs::write(path, "")?;
    }
    Ok(())
}

/// Write the files `validate` requires into `prefix`.
fn install_outputs(prefix: &Path) -> Result<()> {
    fs::create_dir_all(prefix.join("include/openssl"))?;
    fs::write(prefix.join("include/openssl/ssl.h"), "")?;
    fs::create_dir_all(prefix.join("lib"))?;
    for name in ["ssl", "crypto"] {
        let archive = platform::archive_name(std::env::consts::OS, name);
        fs::write(prefix.join("lib").join(archive), "")?;
    }
    Ok(())
}

#[test]
fn a_complete_prefix_is_reused_once_validated() -> Result<()> {
    let directory = Directory::new()?;
    let prefix = directory.0.join("openssl-key");
    install_outputs(&prefix)?;
    fs::write(prefix.join(".complete"), "key")?;
    assert!(cached(&prefix)?);
    // A complete prefix that has lost an archive fails rather than rebuilds.
    fs::remove_file(
        prefix
            .join("lib")
            .join(platform::archive_name(std::env::consts::OS, "ssl")),
    )?;
    assert!(cached(&prefix).is_err());
    Ok(())
}

#[test]
fn a_partial_prefix_is_rebuilt_from_empty() -> Result<()> {
    let directory = Directory::new()?;
    let prefix = directory.0.join("openssl-key");
    install_outputs(&prefix)?;
    assert!(!cached(&prefix)?);
    reset(&prefix)?;
    assert_eq!(fs::read_dir(&prefix)?.count(), 0);
    Ok(())
}

#[test]
fn outputs_the_crt_would_not_publish_fail_validation() -> Result<()> {
    let directory = Directory::new()?;
    let prefix = directory.0.join("openssl-key");
    install_outputs(&prefix)?;
    validate(&prefix)?;
    fs::create_dir_all(prefix.join("share"))?;
    assert!(validate(&prefix).is_err());
    Ok(())
}
