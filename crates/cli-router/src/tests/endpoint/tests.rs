use super::*;
use std::ffi::OsStr;

fn assert_native(argv: &[&str], env: &impl EnvMap, config: &ParsedFiles) {
    let verdict = evaluate(argv, env, config);
    let Verdict::Native(native) = &verdict else {
        panic!("{argv:?}: {verdict:?}")
    };
    let cp = argv.contains(&"cp");
    assert_eq!(matches!(native.command, Command::S3Cp(_)), cp, "{argv:?}");
}

fn assert_python(argv: &[&str], env: &impl EnvMap, config: &ParsedFiles) {
    assert_eq!(
        evaluate(argv, env, config),
        Verdict::Python(PythonReason::EndpointSetting),
        "{argv:?}"
    );
}

fn assert_route(native: bool, argv: &[&str], env: &impl EnvMap, config: &ParsedFiles) {
    if native {
        assert_native(argv, env, config);
    } else {
        assert_python(argv, env, config);
    }
}

fn assert_flag_routes(native: bool, url: &str, env: &impl EnvMap, config: &ParsedFiles) {
    let ls = ["--endpoint-url", url, "s3", "ls", "s3://bucket"];
    assert_route(native, &ls, env, config);
    let cp = ["--endpoint-url", url, "s3", "cp", "a", "s3://b/k"];
    assert_route(native, &cp, env, config);
}

fn set(env: &mut BTreeMap<String, String>, name: &str, value: &str) {
    env.insert(name.to_owned(), value.to_owned());
}

#[cfg(any(unix, windows))]
fn assert_not_unicode_endpoints_are_python_s(global: &OsStr, service: &OsStr) {
    let config = files("");
    let ls = ["s3", "ls", "s3://bucket"];
    let env = cli_core::SnapshotEnv::from_pairs([("AWS_ENDPOINT_URL", global)]);
    assert_python(&ls, &env, &config);
    assert_python(&["s3", "cp", "local", "s3://bucket/key"], &env, &config);
    assert_native(&["--endpoint-url", "http://h:1", "s3", "ls"], &env, &config);
    let overridden = cli_core::SnapshotEnv::from_pairs([
        ("AWS_ENDPOINT_URL", global),
        ("AWS_ENDPOINT_URL_S3", OsStr::new("http://h:1")),
    ]);
    assert_native(&ls, &overridden, &config);
    let shadowing = cli_core::SnapshotEnv::from_pairs([
        ("AWS_ENDPOINT_URL", global),
        ("AWS_ENDPOINT_URL_S3", service),
    ]);
    assert_python(&ls, &shadowing, &config);
}

#[cfg(unix)]
#[test]
fn an_environment_endpoint_url_that_is_not_unicode_is_python_s() {
    use std::os::unix::ffi::OsStrExt;
    // A lone surrogate's bytes, as Windows can hold one, are not UTF-8 either.
    assert_not_unicode_endpoints_are_python_s(
        OsStr::from_bytes(b"http://h:1/\xff"),
        OsStr::from_bytes(b"http://h:1/\xed\xb3\xbf"),
    );
}

// Windows holds its environment as UTF-16, where only a lone surrogate is
// not Unicode.
#[cfg(windows)]
#[test]
fn an_environment_endpoint_url_with_a_lone_surrogate_is_python_s() {
    use std::os::windows::ffi::OsStringExt;
    let units: Vec<u16> = "http://h:1/".encode_utf16().chain([0xdcff]).collect();
    let url = std::ffi::OsString::from_wide(&units);
    assert_not_unicode_endpoints_are_python_s(&url, &url);
}

#[test]
fn a_selected_endpoint_url_with_a_non_ascii_path_is_python_s() {
    let url = "http://h:1/\u{e9}";
    let config = files(&format!(
        "[profile url]\nendpoint_url = {url}\n[profile svc]\nservices = svc\n\
         [services svc]\ns3 =\n  endpoint_url = {url}\n"
    ));
    let ls = ["s3", "ls", "s3://bucket"];
    let flag = ["--endpoint-url", url, "s3", "ls"];
    let mut env = BTreeMap::new();
    assert_python(&flag, &env, &config);
    let cp = ["--endpoint-url", url, "s3", "cp", "a", "s3://b/k"];
    assert_python(&cp, &env, &config);
    assert_python(&["--profile", "url", "s3", "ls"], &env, &config);
    assert_python(&["--profile", "svc", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL", url);
    assert_python(&ls, &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://h:1");
    assert_native(&ls, &env, &config);
    assert_native(&["--profile", "url", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", url);
    assert_python(&ls, &env, &config);
    assert_native(&["--endpoint-url", "http://h:1", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true");
    assert_native(&ls, &env, &config);
    assert_python(&flag, &env, &config);
}

#[test]
fn a_selected_endpoint_url_botocore_s_rules_rewrite_or_refuse_is_python_s() {
    let config = files("[profile url]\nendpoint_url = http://h:1/%C3%A9\n");
    let mut env = BTreeMap::new();
    for (suffix, native) in [
        // `quote` escapes an existing escape's `%`, without decoding it.
        ("/%C3%A9", false),
        ("/%2F", false),
        ("/%ZZ", false),
        ("/a b", false),
        // `urlparse` ends the last segment's path at a `;`.
        ("/a;b", false),
        // `normalize_url_path` removes empty, `.`, and `..` segments.
        ("//", false),
        ("//a", false),
        ("/a//b", false),
        ("/a/./b", false),
        ("/a/../b", false),
        ("/./", false),
        ("/..", false),
        ("/a/.", false),
        ("/#f", false),
        ("/p#", false),
        ("/?a=b", false),
        ("", true),
        ("/", true),
        ("/?", true),
        ("/base", true),
        ("/a-b_c.d~e/", true),
        ("/A1/.../", true),
    ] {
        let url = format!("http://h:1{suffix}");
        let argv = ["--endpoint-url", &url, "s3", "ls", "s3://bucket"];
        assert_route(native, &argv, &env, &config);
    }
    for byte in "!$&'()*+,:;=@".chars() {
        let url = format!("http://h:1/a{byte}b/c");
        assert_python(&["--endpoint-url", &url, "s3", "ls"], &env, &config);
    }
    assert_python(&["--profile", "url", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://h:1/a//b");
    assert_python(&["s3", "cp", "a", "s3://b/k"], &env, &config);
}

#[test]
fn a_command_line_endpoint_url_botocore_s_client_creation_rejects_is_python_s() {
    let config = files("");
    let mut env = BTreeMap::new();
    for url in [
        "http:",
        "https:///p",
        "http://a_b:1",
        "http://-a:1",
        "http://h\t:1",
    ] {
        assert_python(&["--endpoint-url", url, "s3", "ls"], &env, &config);
        let cp = ["--endpoint-url", url, "s3", "cp", "a", "s3://b/k"];
        assert_python(&cp, &env, &config);
    }
    set(&mut env, "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true");
    let ls = ["--endpoint-url", "http://a_b:1", "s3", "ls"];
    assert_python(&ls, &env, &config);
    set(&mut env, "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "false");
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://h:1");
    assert_python(&ls, &env, &config);
    assert_native(&["--endpoint-url", "http://h:2", "s3", "ls"], &env, &config);
}

#[test]
fn a_selected_endpoint_url_whose_scheme_or_port_the_crt_reads_differently_is_python_s() {
    let config = files("[profile url]\nendpoint_url = HTTP://h:1\n");
    let mut env = BTreeMap::new();
    for (url, native) in [
        // botocore lowercases the scheme and strips leading spaces first.
        ("HTTP://h:1", false),
        ("Https://h:1", false),
        (" http://h:1", false),
        ("ftp://h:1", false),
        ("http+x://h:1", false),
        // `urlsplit` reads ASCII digits up to 65535 as a port, the CRT any
        // number up to 2^32 - 1.
        ("http://h:65536", false),
        ("http://h:4294967295", false),
        ("http://h:x9", false),
        ("http://h:+9", false),
        ("http://h:1:2", false),
        ("http://[::1]:65536", false),
        ("http://h", true),
        ("https://h:8443/", true),
        ("http://h:0065535", true),
        ("http://[::1]:9000", true),
    ] {
        let argv = ["--endpoint-url", url, "s3", "ls", "s3://bucket"];
        assert_route(native, &argv, &env, &config);
    }
    let cp = ["s3", "cp", "a", "s3://b/k"];
    assert_python(&["--profile", "url", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL", "ftp://h:1");
    assert_python(&cp, &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL", "//h:1");
    assert_python(&cp, &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://h:99999");
    assert_python(&cp, &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://h:1");
    assert_native(&cp, &env, &config);
}

#[test]
fn a_selected_endpoint_url_whose_authority_has_several_at_signs_is_python_s() {
    let url = "http://u@v@h:1";
    let config = files(&format!(
        "[profile url]\nendpoint_url = {url}\n[profile svc]\nservices = svc\n\
         [services svc]\ns3 =\n  endpoint_url = http://u@v:1@h:1\n"
    ));
    let mut env = BTreeMap::new();
    for (case, native) in [
        // The CRT ends userinfo at the first `@`, `urlsplit` at the last.
        ("http://u@v@h:1", false),
        ("http://u@v:1@h:1", false),
        ("http://u@@h:1", false),
        ("https://u@v@h", false),
        ("https://u@v@h:443/", false),
        ("http://u@v@[::1]:9000", false),
        ("http://h:1", true),
        ("http://u@h:1", true),
        ("http://u:p@h", true),
        ("https://u@h:8443/", true),
        ("http://u@[::1]:9000", true),
        ("http://u%40v@h:1", true),
    ] {
        assert_flag_routes(native, case, &env, &config);
    }
    let ls = ["s3", "ls", "s3://bucket"];
    assert_python(&["--profile", "url", "s3", "ls"], &env, &config);
    assert_python(&["--profile", "svc", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL", url);
    assert_python(&ls, &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://u@h:1");
    assert_native(&ls, &env, &config);
    assert_native(&["--profile", "url", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", url);
    assert_python(&ls, &env, &config);
    assert_native(&["--endpoint-url", "http://h:1", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true");
    assert_native(&ls, &env, &config);
    let svc_cp = ["--profile", "svc", "s3", "cp", "a", "s3://b/k"];
    assert_native(&svc_cp, &env, &config);
    assert_python(&["--endpoint-url", url, "s3", "ls"], &env, &config);
}

#[test]
fn a_selected_endpoint_url_with_an_empty_port_is_python_s() {
    let url = "http://h:";
    let config = files(concat!(
        "[profile url]\nendpoint_url = http://h:/base\n[profile svc]\nservices = svc\n",
        "[services svc]\ns3 =\n  endpoint_url = https://[::1]:\n",
    ));
    let mut env = BTreeMap::new();
    for (case, native) in [
        // `urlsplit` reads an empty port as none, and native would send the
        // colon in the Host header.
        ("http://h:", false),
        ("http://h:/", false),
        ("http://h:/base", false),
        ("http://h:?", false),
        ("https://h:", false),
        ("http://[::1]:", false),
        ("https://[::1]:/base", false),
        ("http://u:p@h:", false),
        ("http://h", true),
        ("http://h/", true),
        ("http://h:1", true),
        ("https://h:8443/base", true),
        ("http://[::1]", true),
        ("http://[::1]:9000", true),
        ("http://u:@h", true),
        ("http://u:@h:1/", true),
    ] {
        assert_flag_routes(native, case, &env, &config);
    }
    let ls = ["s3", "ls", "s3://bucket"];
    assert_python(&["--profile", "url", "s3", "ls"], &env, &config);
    assert_python(&["--profile", "svc", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL", url);
    assert_python(&ls, &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://h:1");
    assert_native(&ls, &env, &config);
    assert_native(&["--profile", "url", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", url);
    assert_python(&ls, &env, &config);
    assert_native(&["--endpoint-url", "http://h", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true");
    assert_native(&ls, &env, &config);
    let svc_cp = ["--profile", "svc", "s3", "cp", "a", "s3://b/k"];
    assert_native(&svc_cp, &env, &config);
    assert_python(&["--endpoint-url", url, "s3", "ls"], &env, &config);
}

#[test]
fn a_selected_endpoint_url_naming_its_scheme_s_default_port_is_python_s() {
    let url = "https://h:443";
    let config = files(concat!(
        "[profile url]\nendpoint_url = https://h:0443/base\n[profile svc]\nservices = svc\n",
        "[services svc]\ns3 =\n  endpoint_url = http://[::1]:80\n",
    ));
    let mut env = BTreeMap::new();
    for (case, native) in [
        // `http.client` leaves the scheme's default port out of the Host
        // header, where native sends it as spelled.
        ("https://h:443", false),
        ("https://h:443/base", false),
        ("https://h:0443", false),
        ("https://h:000443/", false),
        ("http://h:80", false),
        ("http://h:080/base", false),
        ("https://[::1]:443", false),
        ("http://[::1]:0080/", false),
        ("https://u:p@h:443", false),
        ("https://h", true),
        ("http://h/", true),
        ("https://[::1]", true),
        ("https://h:80", true),
        ("http://h:443", true),
        ("https://h:4430", true),
        ("https://h:8443/base", true),
        ("http://h:8080", true),
        ("http://[::1]:9000", true),
        ("https://u:443@h", true),
    ] {
        assert_flag_routes(native, case, &env, &config);
    }
    let ls = ["s3", "ls", "s3://bucket"];
    assert_python(&["--profile", "url", "s3", "ls"], &env, &config);
    assert_python(&["--profile", "svc", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL", url);
    assert_python(&ls, &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "https://h:8443");
    assert_native(&ls, &env, &config);
    assert_native(&["--profile", "url", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_ENDPOINT_URL_S3", "http://h:80");
    assert_python(&ls, &env, &config);
    assert_native(&["--endpoint-url", "https://h", "s3", "ls"], &env, &config);
    set(&mut env, "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", "true");
    assert_native(&ls, &env, &config);
    let svc_cp = ["--profile", "svc", "s3", "cp", "a", "s3://b/k"];
    assert_native(&svc_cp, &env, &config);
    assert_python(&["--endpoint-url", url, "s3", "ls"], &env, &config);
}
