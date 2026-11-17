use super::*;
use crate::unpack::{PreferredEncoding, text_encoding_is_utf8_with};

#[test]
fn user_expansion_preserves_userprofile_and_defers_other_users() {
    let mut env = HashMap::from([("HOME".into(), "/home/me".into())]);
    for path in ["~", "~/x"] {
        assert_eq!(expand_user(path, &env), None);
    }
    assert_eq!(expand_user("x/~", &env).as_deref(), Some("x/~"));
    env.insert("USERPROFILE".into(), "C:\\Users\\me\\".into());
    for (path, expected) in [
        ("~", "C:\\Users\\me\\"),
        ("~/x", "C:\\Users\\me\\/x"),
        ("~\\x", "C:\\Users\\me\\\\x"),
    ] {
        assert_eq!(expand_user(path, &env).as_deref(), Some(expected));
    }
    for path in ["~me/x", "~me\\x", "~me"] {
        assert_eq!(expand_user(path, &env), None);
    }
}

#[test]
fn variables_match_ntpath_single_pass_and_quote_rules() {
    let env = HashMap::from([("A".into(), "value".into()), ("B-2".into(), "%A%".into())]);
    for (path, expected) in [
        ("plain", "plain"),
        ("é/%A%", "é/value"),
        ("%A%/q", "value/q"),
        ("%a%/q", "value/q"),
        ("$A/q", "value/q"),
        ("${A}b", "valueb"),
        ("%A%$A${A}", "valuevaluevalue"),
        ("%A%%A%", "valuevalue"),
        ("$B-2/%B-2%", "%A%/%A%"),
        ("%UNSET%/q", "%UNSET%/q"),
        ("$UNSET/q", "$UNSET/q"),
        ("${UNSET}/q", "${UNSET}/q"),
        ("$Ab", "$Ab"),
        ("%%A%%/q", "%A%/q"),
        ("%%/q", "%/q"),
        ("$$A/q", "$A/q"),
        ("%A/q", "%A/q"),
        ("${A/q", "${A/q"),
        ("${}", "${}"),
        ("$/q%", "$/q%"),
        ("$A$", "value$"),
        ("$Aé/q", "valueé/q"),
        ("'%A%'/$A/q", "'%A%'/value/q"),
        ("it's/%A%/q", "it's/%A%/q"),
    ] {
        assert_eq!(expand_vars(path, &env).as_deref(), Some(expected), "{path}");
    }
}

#[test]
fn expansion_accepts_exact_budget_and_rejects_larger_results() {
    let full = "a".repeat(EXPANDED_PATH_BYTES_MAX);
    let larger = format!("{full}a");
    let mut env = HashMap::new();
    assert_eq!(expand(&full, &env).as_deref(), Some(full.as_str()));
    assert_eq!(expand(&larger, &env), None);
    env.insert("A".into(), full.clone().into());
    assert_eq!(expand_vars("%A%", &env).as_deref(), Some(full.as_str()));
    for path in ["%A%/", "%A%%UNSET%"] {
        assert_eq!(expand_vars(path, &env), None);
    }
    let collapsed = format!("%%{}", &full[2..]);
    assert_eq!(
        expand_vars(&collapsed, &env).as_deref(),
        Some(&collapsed[1..])
    );
    env.insert("USERPROFILE".into(), full.clone().into());
    assert_eq!(expand_user("~", &env).as_deref(), Some(full.as_str()));
    assert_eq!(expand_user("~/x", &env), None);
    assert_eq!(expand_user(&larger, &env), None);
}

#[test]
fn reserved_devices_apply_only_to_the_final_component() {
    for path in [
        "NUL",
        "nul",
        "sub/NUL",
        "sub\\nul",
        "./NUL",
        "C:\\NUL",
        "C:NUL",
        "\\\\.\\NUL",
        "NUL ",
        "nul:",
        "NUL.txt",
        "nul .txt",
        "CON",
        "PRN",
        "AUX.tar.gz",
        "COM1",
        "lpt9",
        "COM¹",
        "CONIN$",
        "conout$",
        "missing/NUL",
    ] {
        assert!(reserved_device(path), "{path}");
    }
    for path in [
        "",
        "page.txt",
        "NULL",
        "nul_byte.txt",
        "NUL/x",
        "COM0",
        "COM10",
        "LPT",
        "CONIN",
        "xNUL",
        "C:",
        "sub/",
        "COM¹x",
        "éèà",
    ] {
        assert!(!reserved_device(path), "{path}");
    }
}

#[test]
fn namespace_and_pipe_prefixes_are_deferred_before_metadata() {
    for path in [
        "\\\\.\\pipe\\name",
        "//./pipe/name",
        "\\\\.\\PIPE\\sub\\name",
        "\\\\?\\pipe\\name",
        "\\\\.\\PhysicalDrive0",
        "\\\\?\\C:\\page.txt",
        "\\\\?\\UNC\\host\\pipe\\name",
        "\\\\host\\pipe\\name",
        "//host/PIPE/name",
        "\\\\host\\pipe",
    ] {
        assert!(device_namespace_or_pipe(path), "{path}");
    }
    for path in [
        "",
        "\\",
        "\\\\",
        "\\\\.",
        "pipe\\name",
        "\\pipe\\name",
        ".\\pipe\\name",
        "C:\\pipe\\name",
        "\\\\host\\share\\pipe",
        "\\\\host\\pipes\\name",
        "\\\\.x\\name",
    ] {
        assert!(!device_namespace_or_pipe(path), "{path}");
    }
}

#[test]
fn expanded_devices_are_deferred_without_rescanning_variables() {
    let env = HashMap::from([
        ("DEVICE".into(), "NUL".into()),
        ("USERPROFILE".into(), "home".into()),
        ("PIPES".into(), "\\\\.\\pipe".into()),
    ]);
    for path in [
        "NUL",
        "sub/%DEVICE%",
        "~/$DEVICE",
        "~other/page.txt",
        "\\\\.\\pipe\\name",
        "%PIPES%\\name",
    ] {
        assert_eq!(expand(path, &env), None, "{path}");
    }
    assert_eq!(
        expand("~/%UNSET%/page.txt", &env).as_deref(),
        Some("home/%UNSET%/page.txt")
    );
}

#[test]
fn ansi_code_page_ignores_locale_and_yields_to_explicit_codec() {
    let utf8 = PreferredEncoding::AnsiCodePage(65001);
    let western = PreferredEncoding::AnsiCodePage(1252);
    let mut env = HashMap::new();
    assert!(text_encoding_is_utf8_with(&env, utf8));
    assert!(!text_encoding_is_utf8_with(&env, western));
    env.insert("LC_ALL".into(), "C.UTF-8".into());
    assert!(!text_encoding_is_utf8_with(&env, western));
    env.insert("LC_ALL".into(), "en_US.ISO-8859-1".into());
    assert!(text_encoding_is_utf8_with(&env, utf8));
    env.insert("AWS_CLI_FILE_ENCODING".into(), "utf-8".into());
    assert!(text_encoding_is_utf8_with(&env, western));
    env.insert("AWS_CLI_FILE_ENCODING".into(), "latin-1".into());
    assert!(!text_encoding_is_utf8_with(&env, utf8));
}

#[test]
fn windows_io_errors_use_python_errno_numbers() {
    use std::io::{Error, ErrorKind};
    for (kind, expected) in [
        (ErrorKind::NotFound, 2),
        (ErrorKind::PermissionDenied, 13),
        (ErrorKind::IsADirectory, 13),
        (ErrorKind::NotADirectory, 20),
        (ErrorKind::WouldBlock, 11),
    ] {
        assert_eq!(errno(&Error::from(kind)), Some(expected));
    }
    assert_eq!(errno(&Error::from(ErrorKind::Other)), None);
}
