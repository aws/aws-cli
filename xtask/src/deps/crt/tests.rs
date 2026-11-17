use super::*;
#[test]
fn required_inventory_includes_python_crt_dependencies() {
    let libraries = include_str!("../../../../deps/crt-libraries.txt");
    let names = inventory(libraries);
    assert_eq!(names.len(), 16);
    assert!(names.contains(&"aws-c-mqtt"));
    assert!(names.contains(&"aws-c-event-stream"));
}

#[test]
fn library_inventory_preserves_unique_complete_link_groups() {
    let names = inventory(include_str!("../../../../deps/crt-libraries.txt"));
    let unique: std::collections::BTreeSet<_> = names.iter().copied().collect();
    assert_eq!(names.len(), unique.len());
    assert!(names.iter().all(|name| !name.is_empty()));
    assert_eq!(
        names.iter().filter(|name| name.starts_with("aws-")).count(),
        11
    );
    assert_eq!(
        names
            .iter()
            .filter(|name| ["s2n", "ssl", "crypto", "z"].contains(name))
            .count(),
        4
    );
    assert_eq!(names.iter().filter(|name| **name == "lzma").count(), 1);
    assert_eq!(names.len(), 16);
}

#[test]
fn detects_shared_library_names_and_preserves_static_files() -> Result<()> {
    let directory = super::super::tests::Directory::new()?;
    for name in ["libz.a", "z.lib", "pkgconfig"] {
        fs::write(directory.0.join(name), "")?;
    }
    shared_library_check(&directory.0)?;
    for name in ["libz.so", "libz.so.1.3.1", "libz.1.dylib", "zlib1.dll"] {
        let path = directory.0.join(name);
        fs::write(&path, "")?;
        assert!(shared_library_check(&directory.0).is_err());
        fs::remove_file(path)?;
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn archive_validation_rejects_sibling_and_external_symlinks() -> Result<()> {
    let root = super::super::tests::test_root()?;
    let directory = super::super::tests::Directory::new()?;
    let prefix = directory.0.join("install");
    fs::create_dir_all(prefix.join("lib"))?;
    let libraries = fs::read_to_string(root.join("deps/crt-libraries.txt"))?;
    for name in inventory(&libraries) {
        fs::write(prefix.join("lib").join(format!("lib{name}.a")), "")?;
    }
    validate(root, &prefix)?;
    let archive = prefix.join("lib/libz.a");
    for relative in ["install2/libz.a", "other/libz.a"] {
        let external = directory.0.join(relative);
        let parent = external
            .parent()
            .ok_or_else(|| error("missing archive parent"))?;
        fs::create_dir_all(parent)?;
        fs::write(&external, "")?;
        fs::remove_file(&archive)?;
        std::os::unix::fs::symlink(external, &archive)?;
        assert!(validate(root, &prefix).is_err());
    }
    Ok(())
}

#[test]
fn a_new_openssl_or_zlib_xz_key_changes_the_crt_key() {
    // The CRT keys on OpenSSL and zlib/xz only through these edges, so a
    // pin, code, or tool change of either must reach it here.
    let key = crt_key("toolchain", "openssl", "zlib-xz");
    assert_ne!(crt_key("toolchain", "openssl-2", "zlib-xz"), key);
    assert_ne!(crt_key("toolchain", "openssl", "zlib-xz-2"), key);
    assert_ne!(crt_key("toolchain-2", "openssl", "zlib-xz"), key);
}

#[test]
fn roots_name_the_crt_the_stages_it_links_and_their_scratch_trees() {
    let root = Path::new("/checkout");
    let stages = root.join("target/deps").join(TARGET);
    let (openssl, zlib_xz, crt) = (
        stages.join("openssl-1"),
        stages.join("zlib-xz-2"),
        stages.join("crt-3"),
    );
    let roots = stage_roots(root, &openssl, &zlib_xz, &crt);
    let mut expected = Roots::default();
    expected.insert("crt", crt);
    expected.insert("openssl", openssl);
    expected.insert("zlib-xz", zlib_xz);
    expected.insert("work/crt", stages.join("work/crt"));
    expected.insert("work/openssl", stages.join("work/openssl"));
    expected.insert("work/zlib-xz", stages.join("work/zlib-xz"));
    assert_eq!(roots, expected);
}

#[test]
fn prepared_libraries_are_the_crt_prefix_and_build_nothing() -> Result<()> {
    let root = super::super::tests::Directory::new()?;
    let crt = Path::new("/prepared/crt");
    let libraries = CpythonLibraries::prepared(crt);
    assert_eq!(libraries.openssl(), crt);
    assert_eq!(libraries.zlib_xz(), crt);
    let pins = Pins::load(super::super::tests::test_root()?)?;
    libraries.build(&root.0, &pins, &super::super::keying_toolchain())?;
    assert!(fs::read_dir(&root.0)?.next().is_none());
    Ok(())
}
