use super::*;

fn getpwuid_home() -> Option<PathBuf> {
    // SAFETY: the returned entry is read before any other passwd call on this
    // thread, and its strings are copied out at once.
    unsafe {
        let entry = libc::getpwuid(libc::getuid());
        if entry.is_null() || (*entry).pw_dir.is_null() {
            return None;
        }
        let home = CStr::from_ptr((*entry).pw_dir).to_bytes();
        (!home.is_empty()).then(|| PathBuf::from(OsStr::from_bytes(home)))
    }
}

#[test]
#[cfg_attr(
    miri,
    ignore = "Miri's passwd shim answers from HOME, not the database"
)]
fn the_passwd_home_matches_the_database_through_every_buffer_size() {
    let expected = getpwuid_home();
    assert_eq!(home_directory(), expected);
    assert_eq!(home_directory_from(1), expected);
    assert_eq!(home_directory_from(BUFFER_BYTES_MAX * 2), None);
    if let Some(home) = expected {
        assert!(home.is_absolute(), "{}", home.display());
    }
}
