use super::*;

#[test]
fn supported_hosts_keep_linux_pgo_and_windows_architecture_restrictions() {
    for (os, arch, linux_only, expected) in [
        ("linux", "x86_64", true, true),
        ("linux", "aarch64", true, true),
        ("linux", "aarch64", false, true),
        ("linux", "riscv64", false, false),
        ("macos", "aarch64", false, true),
        ("macos", "aarch64", true, false),
        ("windows", "x86_64", false, true),
        ("windows", "x86_64", true, false),
        ("windows", "x86", false, false),
    ] {
        assert_eq!(supported_host(os, arch, linux_only), expected);
    }
}

#[test]
fn native_abis_pin_static_linux_and_windows_and_isolate_system_mode() -> Result<()> {
    assert_eq!(
        target("linux", "x86_64", false)?,
        "x86_64-unknown-linux-musl"
    );
    assert_eq!(
        target("windows", "x86_64", false)?,
        "x86_64-pc-windows-msvc"
    );
    assert_eq!(
        target("linux", "aarch64", true)?,
        "aarch64-unknown-linux-gnu"
    );
    assert!(target("windows", "x86_64", true).is_err());
    assert!(target("macos", "aarch64", true).is_err());
    // Static builds keep the pinned architectures; system targets for other
    // Linux architectures come from product::options.
    assert!(target("linux", "riscv64", false).is_err());
    Ok(())
}

#[test]
fn openssl_configurations_cover_static_native_abis_and_reject_mixed_abis() {
    for (triple, expected) in [
        ("x86_64-linux-musl", Some("linux-x86_64")),
        ("aarch64-linux-musl", Some("linux-aarch64")),
        ("aarch64-macos", Some("darwin64-arm64-cc")),
        ("aarch64-macos.14.0-none", Some("darwin64-arm64-cc")),
        ("x86_64-macos", Some("darwin64-x86_64-cc")),
        ("x86_64-windows-msvc", Some("VC-WIN64A")),
        ("x86_64-linux-gnu", None),
        ("aarch64-linux-gnu", None),
        ("x86_64-windows-gnu", None),
    ] {
        assert_eq!(openssl_target(triple), expected);
    }
}

#[test]
fn only_visual_c_openssl_configurations_use_nmake() {
    assert!(uses_nmake("VC-WIN64A"));
    assert!(!uses_nmake("linux-x86_64"));
    assert!(!uses_nmake("darwin64-arm64-cc"));
}

#[test]
fn windows_omits_only_s2n_from_the_complete_archive_inventory() -> Result<()> {
    let root = crate::deps::tests::test_root()?;
    let inventory = std::fs::read_to_string(root.join("deps/crt-libraries.txt"))?;
    for name in inventory
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
    {
        assert_eq!(includes_library("windows", name), name != "s2n");
        assert!(includes_library("linux", name));
        assert!(includes_library("macos", name));
    }
    Ok(())
}

#[test]
fn static_archive_names_match_native_linker_conventions() {
    assert_eq!(archive_name("linux", "aws-c-s3"), "libaws-c-s3.a");
    assert_eq!(archive_name("windows", "aws-c-s3"), "aws-c-s3.lib");
    assert_eq!(archive_name("macos", "zstd"), "libzstd.a");
    for library in ["sqlite3", "bz2", "ffi", "zstd"] {
        assert_eq!(archive_name("linux", library), format!("lib{library}.a"));
        assert_eq!(archive_name("windows", library), format!("{library}.lib"));
    }
}
