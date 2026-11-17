use super::*;

#[test]
fn windows_errors_preserve_availability_and_resource_failures() {
    for (code, expected) in [
        (2, ReadError::FileNotFound),
        (3, ReadError::FileNotFound),
        (4, ReadError::ProcessFdQuotaExceeded),
        (5, ReadError::AccessDenied),
        (8, ReadError::SystemResources),
        (14, ReadError::SystemResources),
        (1450, ReadError::SystemResources),
        (123, ReadError::BadPathName),
        (161, ReadError::BadPathName),
        (267, ReadError::NotDir),
        (995, ReadError::Canceled),
        (1314, ReadError::PermissionDenied),
    ] {
        assert_eq!(
            windows_error(Some(code), std::io::ErrorKind::Other),
            expected
        );
    }
    assert_eq!(
        windows_error(Some(1), std::io::ErrorKind::Other),
        ReadError::Other {
            kind: std::io::ErrorKind::Other,
            raw_os_error: Some(1)
        }
    );
}

#[test]
#[cfg(target_os = "linux")]
fn linux_errors_classify_like_std_io() {
    for (code, expected) in [
        (1, ReadError::PermissionDenied),
        (2, ReadError::FileNotFound),
        (3, ReadError::FileNotFound),
        (5, ReadError::InputOutput),
        (12, ReadError::SystemResources),
        (13, ReadError::AccessDenied),
        (20, ReadError::NotDir),
        (21, ReadError::IsDir),
        (23, ReadError::SystemFdQuotaExceeded),
        (24, ReadError::ProcessFdQuotaExceeded),
        (40, ReadError::SymLinkLoop),
        (105, ReadError::SystemResources),
    ] {
        assert_eq!(
            ReadError::from(std::io::Error::from_raw_os_error(code)),
            expected,
            "errno {code}"
        );
    }
    for (code, kind) in [
        (4, std::io::ErrorKind::Interrupted),
        (110, std::io::ErrorKind::TimedOut),
    ] {
        assert_eq!(
            ReadError::from(std::io::Error::from_raw_os_error(code)),
            ReadError::Other {
                kind,
                raw_os_error: Some(code)
            }
        );
    }
}
