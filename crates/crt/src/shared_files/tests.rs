use super::export_value;
use std::{ffi::OsStr, path::Path};

#[test]
fn explicit_empty_and_non_home_paths_remain_authoritative() {
    let resolved = Some(Path::new(r"D:\Users\jane\.aws\config"));
    for existing in ["", r"D:\configured\config", "local/config", "~jane/config"] {
        assert_eq!(export_value(Some(OsStr::new(existing)), resolved), None);
    }
}

#[test]
fn missing_and_home_relative_values_publish_only_resolved_paths() {
    let resolved = Some(Path::new(r"D:\Users\jane\.aws\credentials"));
    let windows_spelling = cfg!(windows).then_some(Some(r"~\.aws\credentials"));
    for existing in [None, Some("~"), Some("~/.aws/credentials")]
        .into_iter()
        .chain(windows_spelling)
    {
        assert_eq!(export_value(existing.map(OsStr::new), resolved), resolved);
        assert_eq!(export_value(existing.map(OsStr::new), None), None);
    }
}

#[cfg(not(windows))]
#[test]
fn backslash_after_tilde_is_literal_off_windows() {
    let resolved = Some(Path::new("/home/jane/.aws/credentials"));
    assert_eq!(
        export_value(Some(OsStr::new(r"~\.aws\credentials")), resolved),
        None
    );
}

#[cfg(unix)]
#[test]
fn non_unicode_paths_keep_explicit_and_home_relative_policy() {
    use std::os::unix::ffi::OsStrExt;
    let resolved = Some(Path::new(OsStr::from_bytes(b"/home/user/.aws/\xff")));
    for path in [
        b"/explicit/\xff".as_slice(),
        b"relative/\xff",
        b"~user/\xff",
        b"~\\.aws\\\xff",
    ] {
        assert_eq!(export_value(Some(OsStr::from_bytes(path)), resolved), None);
    }
    assert_eq!(
        export_value(Some(OsStr::from_bytes(b"~/.aws/\xff")), resolved),
        resolved
    );
}

#[cfg(windows)]
#[test]
fn wide_encoding_retains_unicode_and_unpaired_surrogates() -> std::io::Result<()> {
    use std::{ffi::OsString, os::windows::ffi::OsStringExt};
    for units in [
        vec![0x43, 0x3a, 0x5c, 0xe9, 0xd83d, 0xde00],
        vec![0x44, 0x3a, 0x5c, 0xd800, 0x61, 0xdc00],
    ] {
        let path = OsString::from_wide(&units);
        let mut expected = units;
        expected.push(0);
        assert_eq!(super::encode_value(&path)?, expected);
        assert_eq!(export_value(Some(&path), Some(Path::new("fallback"))), None);
    }
    let relative = OsString::from_wide(&[0x7e, 0x5c, 0xd800]);
    let resolved = Path::new("resolved");
    assert_eq!(
        export_value(Some(&relative), Some(resolved)),
        Some(resolved)
    );
    Ok(())
}

#[cfg(windows)]
#[test]
fn wide_encoding_rejects_nul_before_publication() -> std::io::Result<()> {
    use std::{ffi::OsString, os::windows::ffi::OsStringExt};
    for units in [vec![0], vec![0x43, 0, 0xd800], vec![0xd800, 0]] {
        let path = OsString::from_wide(&units);
        let error = super::encode_value(&path)
            .err()
            .ok_or_else(|| std::io::Error::other("NUL path encoding unexpectedly succeeded"))?;
        assert_eq!(error.kind(), std::io::ErrorKind::InvalidInput);
    }
    Ok(())
}

#[test]
fn publication_errors_preserve_errno_without_treating_it_as_a_win32_code() -> std::io::Result<()> {
    super::publication_result(0)?;
    for status in [12, 22] {
        let error = super::publication_result(status)
            .err()
            .ok_or_else(|| std::io::Error::other("publication unexpectedly succeeded"))?;
        assert_eq!(error.kind(), std::io::ErrorKind::Other);
        assert_eq!(error.raw_os_error(), None);
        assert_eq!(
            error.to_string(),
            format!("shared-file publication failed (C runtime error {status})")
        );
    }
    Ok(())
}
