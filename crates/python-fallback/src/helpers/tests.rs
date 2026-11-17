use super::*;

#[test]
fn host_status_width_matches_the_parent_process_convention() {
    assert_eq!(
        size_of::<HostExitStatus>(),
        if cfg!(windows) { 4 } else { 1 }
    );
}

#[test]
fn system_exit_codes_use_host_process_exit_status_conversion() {
    assert_eq!(normalize_system_exit_code(SystemExitValue::None), 0);
    assert_eq!(normalize_system_exit_code(SystemExitValue::Invalid), 1);
    for value in [0, 1, 254, 255] {
        assert_eq!(
            normalize_system_exit_code(SystemExitValue::Integer(value)),
            value as HostExitStatus
        );
    }
}

#[test]
#[cfg(not(windows))]
fn negative_system_exit_codes_wrap_instead_of_reporting_success() {
    for (value, expected) in [(-1, 255), (-9, 247), (-100, 156), (-255, 1), (-256, 0)] {
        assert_eq!(
            normalize_system_exit_code(SystemExitValue::Integer(value)),
            expected
        );
    }
}

#[test]
#[cfg(not(windows))]
fn system_exit_codes_above_255_wrap_instead_of_saturating() {
    for (value, expected) in [
        (256, 0),
        (300, 44),
        (1 << 31, 0),
        ((1 << 31) - 1, 255),
        ((1 << 33) + 300, 44),
        (i64::MIN, 0),
        (i64::MAX, 255),
    ] {
        assert_eq!(
            normalize_system_exit_code(SystemExitValue::Integer(value)),
            expected
        );
    }
}

#[test]
fn system_exit_codes_wider_than_a_c_long_long_exit_with_all_bits_set() {
    assert_eq!(
        normalize_system_exit_code(SystemExitValue::Overflow),
        HostExitStatus::MAX
    );
}

#[test]
fn windows_retains_all_c_integer_status_bits_on_every_test_host() {
    for (value, expected) in [
        (-1, u32::MAX),
        (-9, u32::MAX - 8),
        (-256, u32::MAX - 255),
        (256, 256),
        (300, 300),
        (1 << 31, 1 << 31),
        ((1 << 33) + 300, 300),
        (i64::MIN, 0),
        (i64::MAX, u32::MAX),
    ] {
        assert_eq!(exit_bits(SystemExitValue::Integer(value)), expected);
    }
    assert_eq!(exit_bits(SystemExitValue::Overflow), u32::MAX);
    assert_eq!(exit_bits(SystemExitValue::None), 0);
    assert_eq!(exit_bits(SystemExitValue::Invalid), 1);
}

#[test]
fn bytecode_magic_compatibility_only_matters_for_dynamic_python() {
    assert!(bytecode_magic_is_compatible(false, 1, 2));
    assert!(bytecode_magic_is_compatible(true, 1234, 1234));
    assert!(!bytecode_magic_is_compatible(true, 1234, 5678));
}

#[test]
fn python_size_conversion_accepts_representable_lengths_and_rejects_overflow() {
    assert_eq!(checked_python_size(0), Some(0));
    let largest = isize::MAX as usize;
    assert_eq!(checked_python_size(largest), Some(isize::MAX));
    assert_eq!(checked_python_size(largest + 1), None);
}

#[test]
fn standard_streams_pin_utf8_with_surrogateescape() {
    assert_eq!(STDIO_ENCODING.to_bytes(), b"utf-8");
    assert_eq!(STDIO_ERRORS.to_bytes(), b"surrogateescape");
}

#[test]
fn locale_names_that_are_utf8_decode() {
    for name in [
        &b"C"[..],
        b"POSIX",
        b"C.UTF-8",
        b"en_US.UTF-8",
        b"de_DE.ISO-8859-15@euro",
        b"",
        "fr_FR.utf8\u{e9}".as_bytes(),
    ] {
        assert!(locale_name_is_decodable(name), "{name:?}");
    }
}

#[test]
fn locale_names_that_are_not_utf8_do_not_decode() {
    for name in [
        &b"en_US.\xff"[..],
        b"en_US.\xe9",
        b"\xc3",
        b"\xc0\xaf",
        b"\xed\xa0\x80",
    ] {
        assert!(!locale_name_is_decodable(name), "{name:?}");
    }
}
