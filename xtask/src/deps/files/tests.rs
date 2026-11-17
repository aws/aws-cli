use super::*;
use crate::deps::tests::{Directory, test_root};

#[test]
fn copy_tree_replaces_stale_files_and_preserves_directories_and_links() -> Result<()> {
    let root = Directory::new()?;
    let source = root.0.join("source");
    let destination = root.0.join("destination");
    fs::create_dir_all(source.join("sub"))?;
    fs::write(source.join("sub/file.txt"), "hello")?;
    #[cfg(unix)]
    std::os::unix::fs::symlink("sub/file.txt", source.join("link.txt"))?;
    #[cfg(windows)]
    std::os::windows::fs::symlink_file(Path::new("sub").join("file.txt"), source.join("link.txt"))?;
    fs::create_dir_all(&destination)?;
    fs::write(destination.join("stale.txt"), "obsolete")?;
    copy_tree(&source, &destination, CopyMode::Replace)?;
    assert_eq!(
        fs::read_to_string(destination.join("sub/file.txt"))?,
        "hello"
    );
    assert_eq!(
        fs::read_link(destination.join("link.txt"))?,
        Path::new("sub").join("file.txt")
    );
    assert!(!destination.join("stale.txt").exists());
    assert!(source.join("sub/file.txt").is_file());
    Ok(())
}

#[cfg(unix)]
#[test]
fn copy_tree_merge_retains_existing_interpreter_files_and_replaces_links() -> Result<()> {
    let root = Directory::new()?;
    let source = root.0.join("support");
    let destination = root.0.join("interpreter");
    fs::create_dir_all(&source)?;
    fs::create_dir_all(&destination)?;
    fs::write(source.join("libffi.a"), "support archive")?;
    fs::write(destination.join("libpython.a"), "interpreter archive")?;
    let external = root.0.join("outside.a");
    fs::write(&external, "outside")?;
    std::os::unix::fs::symlink(&external, destination.join("libffi.a"))?;
    copy_tree(&source, &destination, CopyMode::Merge)?;
    assert_eq!(
        fs::read_to_string(destination.join("libpython.a"))?,
        "interpreter archive"
    );
    assert_eq!(
        fs::read_to_string(destination.join("libffi.a"))?,
        "support archive"
    );
    assert_eq!(fs::read_to_string(&external)?, "outside");
    assert!(!fs::symlink_metadata(destination.join("libffi.a"))?.is_symlink());
    Ok(())
}

#[test]
fn staged_install_merges_into_an_enclosing_prefix_but_not_into_itself() -> Result<()> {
    let root = Directory::new()?;
    let prefix = root.0.join("crt");
    let staged = prefix.join("work/openssl/install/usr/local/lib/aws-cli-native");
    fs::create_dir_all(staged.join("include/openssl"))?;
    fs::write(staged.join("include/openssl/ssl.h"), "header")?;
    fs::create_dir_all(prefix.join("lib"))?;
    fs::write(prefix.join("lib/libz.a"), "other project")?;
    install_staged(&staged, &prefix)?;
    assert_eq!(
        fs::read_to_string(prefix.join("include/openssl/ssl.h"))?,
        "header"
    );
    assert_eq!(
        fs::read_to_string(prefix.join("lib/libz.a"))?,
        "other project"
    );
    assert!(copy_tree(&staged, &prefix, CopyMode::Merge).is_err());
    assert!(install_staged(&prefix, &staged).is_err());
    Ok(())
}

#[test]
fn linked_trees_merge_and_replace_without_writing_through() -> Result<()> {
    let root = Directory::new()?;
    let openssl = root.0.join("openssl");
    let crt = root.0.join("crt");
    fs::create_dir_all(openssl.join("lib/pkgconfig"))?;
    fs::write(openssl.join("lib/libssl.a"), "ssl")?;
    fs::write(openssl.join("lib/pkgconfig/openssl.pc"), "pc")?;
    fs::create_dir_all(crt.join("lib"))?;
    fs::write(crt.join("lib/libz.a"), "other project")?;
    fs::write(crt.join("lib/libssl.a"), "stale")?;
    // A stale destination is replaced by the link, not overwritten in place:
    // a hard link to the stale file from elsewhere keeps its contents.
    let stale = root.0.join("stale-link");
    fs::hard_link(crt.join("lib/libssl.a"), &stale)?;
    link_tree(&openssl.join("lib"), &crt.join("lib"))?;
    assert_eq!(fs::read_to_string(crt.join("lib/libssl.a"))?, "ssl");
    assert_eq!(
        fs::read_to_string(crt.join("lib/pkgconfig/openssl.pc"))?,
        "pc"
    );
    assert_eq!(fs::read_to_string(crt.join("lib/libz.a"))?, "other project");
    assert_eq!(fs::read_to_string(&stale)?, "stale");
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        let linked = fs::metadata(crt.join("lib/libssl.a"))?;
        assert_eq!(
            linked.ino(),
            fs::metadata(openssl.join("lib/libssl.a"))?.ino()
        );
    }
    // Linking again, as a resumed build does, leaves the same tree.
    link_tree(&openssl.join("lib"), &crt.join("lib"))?;
    assert_eq!(fs::read_to_string(crt.join("lib/libssl.a"))?, "ssl");
    assert!(link_tree(&openssl, &openssl.join("lib/nested")).is_err());
    Ok(())
}

#[test]
fn tool_environment_keeps_injected_allowlist_and_pins_locale() -> Result<()> {
    let parent = [
        ("PATH", "/usr/bin"),
        ("HOME", "/home/build"),
        ("CPATH", "/opt/include"),
        ("CFLAGS", "-O3"),
        ("PYTHONPATH", "/tmp/site"),
        ("LANG", "en_US.UTF-8"),
        ("LC_ALL", "de_DE.UTF-8"),
    ]
    .map(|(name, value)| (OsString::from(name), OsString::from(value)));
    let allowlist = fs::read_to_string(test_root()?.join("deps/scripts/tool_environ.txt"))?;
    let result = tool_environment(parent, &allowlist);
    assert_eq!(result.len(), 3);
    for (name, value) in [
        ("PATH", "/usr/bin"),
        ("HOME", "/home/build"),
        ("LC_ALL", "C"),
    ] {
        assert_eq!(result.get(OsStr::new(name)), Some(&OsString::from(value)));
    }
    for dropped in ["CPATH", "CFLAGS", "PYTHONPATH", "LANG", "TMPDIR"] {
        assert!(!result.contains_key(OsStr::new(dropped)));
    }
    Ok(())
}

#[test]
#[cfg(unix)]
fn executable_search_checks_names_per_directory_and_requires_executable_files() -> Result<()> {
    let root = Directory::new()?;
    let first = root.0.join("first");
    let second = root.0.join("second");
    fs::create_dir_all(&first)?;
    fs::create_dir_all(&second)?;
    fs::write(first.join("ninja-build"), "not executable")?;
    crate::deps::write_executable(&second.join("ninja"), "#!/bin/sh\n")?;
    let search = std::env::join_paths([
        root.0.join("missing"),
        first.clone(),
        PathBuf::new(),
        second,
    ])
    .map_err(|failure| error(failure.to_string()))?;
    let names = ["ninja-build", "ninja"];
    assert_eq!(
        find_executable(&search, &names)?,
        Some(root.0.join("second/ninja"))
    );
    assert_eq!(find_executable(&search, &["samu"])?, None);
    assert_eq!(find_executable(OsStr::new(""), &names)?, None);
    crate::deps::write_executable(&first.join("ninja"), "#!/bin/sh\n")?;
    assert_eq!(find_executable(&search, &names)?, Some(first.join("ninja")));
    crate::deps::write_executable(&first.join("ninja-build"), "#!/bin/sh\n")?;
    assert_eq!(
        find_executable(&search, &names)?,
        Some(first.join("ninja-build"))
    );
    Ok(())
}

#[test]
#[cfg(windows)]
fn executable_search_resolves_native_windows_program_extension() -> Result<()> {
    let root = Directory::new()?;
    fs::write(root.0.join("ninja.exe"), b"native tool")?;
    assert_eq!(
        find_executable(root.0.as_os_str(), &["ninja"])?,
        Some(root.0.join("ninja.exe"))
    );
    Ok(())
}

#[test]
fn glob_matches_original_zlib_prune_patterns() {
    for (pattern, name, expected) in [
        ("libz.so*", "libz.so", true),
        ("libz.so*", "libz.so.1.3.1", true),
        ("libz.so*", "libz.a", false),
        ("libz*.dylib", "libz.1.dylib", true),
        ("libz*.dylib", "libz.dylib", true),
        ("libz*.dylib", "libz.dylib.bak", false),
        ("*", "", true),
        ("", "a", false),
    ] {
        assert_eq!(glob_matches(pattern, name), expected, "{pattern} / {name}");
    }
}

#[test]
fn scratch_prune_removes_matches_and_preserves_static_files_and_directories() -> Result<()> {
    let root = Directory::new()?;
    let directory = root.0.join("scratch");
    fs::create_dir_all(&directory)?;
    for name in ["libz.so", "libz.so.1", "libz.a", "libz.1.dylib"] {
        fs::write(directory.join(name), "")?;
    }
    fs::create_dir(directory.join("libz.so.directory"))?;
    prune_matching(&directory, "libz.so*")?;
    prune_matching(&directory, "libz*.dylib")?;
    prune_matching(&directory.join("missing"), "*")?;
    assert!(directory.join("libz.a").is_file());
    assert!(directory.join("libz.so.directory").is_dir());
    for name in ["libz.so", "libz.so.1", "libz.1.dylib"] {
        assert!(!directory.join(name).exists());
    }
    Ok(())
}

#[test]
fn windows_executable_policy_resolves_exe_without_permission_bits() -> Result<()> {
    let root = Directory::new()?;
    let binary = root.0.join("ninja.exe");
    fs::write(&binary, "")?;
    assert_eq!(
        find_executable_for_host(root.0.as_os_str(), &["ninja"], true)?,
        Some(binary),
    );
    Ok(())
}

#[test]
fn windows_executable_policy_prefers_exe_cmd_bat_then_extensionless() -> Result<()> {
    let root = Directory::new()?;
    let names = ["tool.exe", "tool.cmd", "tool.bat", "tool"];
    for name in names {
        fs::write(root.0.join(name), "")?;
    }
    for name in names {
        let path = root.0.join(name);
        assert_eq!(
            find_executable_for_host(root.0.as_os_str(), &["tool"], true)?,
            Some(path.clone()),
        );
        fs::remove_file(path)?;
    }
    assert!(find_executable_for_host(root.0.as_os_str(), &["tool"], true)?.is_none());
    Ok(())
}

#[test]
fn windows_environment_names_are_case_insensitive_without_compiler_injection() {
    let environment = tool_environment_for_host(
        [
            ("Path".into(), "native tools".into()),
            ("SYSTEMROOT".into(), "C:\\Windows".into()),
            ("INCLUDE".into(), "untrusted headers".into()),
            ("CL".into(), "untrusted flags".into()),
        ],
        "PATH\nSystemRoot\n",
        true,
    );
    assert_eq!(environment[OsStr::new("Path")], "native tools");
    assert_eq!(environment[OsStr::new("SYSTEMROOT")], "C:\\Windows");
    assert!(!environment.contains_key(OsStr::new("INCLUDE")));
    assert!(!environment.contains_key(OsStr::new("CL")));
    assert_eq!(environment[OsStr::new("LC_ALL")], "C");
}
