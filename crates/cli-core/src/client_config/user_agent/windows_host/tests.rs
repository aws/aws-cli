#[test]
fn client_releases_match_kernel_version_boundaries() {
    for (version, name) in [
        ((6, 0, 0), ""),
        ((6, 1, 7601), "7"),
        ((6, 3, 0), "8.1"),
        ((10, 0, 21999), "10"),
        ((10, 0, 22000), "11"),
        ((10, 1, 0), "post11"),
    ] {
        assert_eq!(
            super::release_name(version.0, version.1, version.2, true),
            name
        );
    }
}

#[test]
fn server_releases_use_cpython_server_names() {
    for (version, name) in [
        ((10, 0, 17763), "2019Server"),
        ((10, 0, 20348), "2022Server"),
        ((10, 0, 26100), "2025Server"),
        ((10, 1, 0), "post2025Server"),
        ((6, 4, 0), "2016Server"),
        ((4, 0, 0), ""),
    ] {
        assert_eq!(
            super::release_name(version.0, version.1, version.2, false),
            name
        );
    }
}
