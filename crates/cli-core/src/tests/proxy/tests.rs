use super::*;
use crate::proxy::{
    DisplayUrl, Environment, Forward, ForwardProxy, NAMES_HAVE_CASE, NotUnicode, Pair, Spellings,
};
use std::collections::BTreeMap;

fn cased(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
    pairs
        .iter()
        .map(|&(name, value)| (name.to_owned(), value.to_owned()))
        .collect()
}
struct Uncased(BTreeMap<String, String>);
impl Uncased {
    fn new(pairs: &[(&str, &str)]) -> Self {
        Self(crate::snapshot_env::collect(
            pairs
                .iter()
                .map(|&(name, value)| (name.to_owned(), value.to_owned())),
            str::eq_ignore_ascii_case,
        ))
    }
}
impl crate::EnvMap for Uncased {
    fn var(&self, name: &str) -> Option<&str> {
        crate::snapshot_env::get(&self.0, name, str::eq_ignore_ascii_case).map(String::as_str)
    }
    fn names(&self) -> Vec<&str> {
        self.0.keys().map(String::as_str).collect()
    }
}
struct Resolution {
    entries: &'static [(&'static str, &'static str)],
    http: Option<&'static str>,
    https: Option<&'static str>,
    no: Option<&'static str>,
    python: bool,
}
const fn case(entries: &'static [(&'static str, &'static str)]) -> Resolution {
    Resolution {
        entries,
        http: None,
        https: None,
        no: None,
        python: false,
    }
}
fn expect_resolution(case: &Resolution, env: Environment<'_>) {
    let entries = case.entries;
    assert_eq!(env.resolve("http://bucket"), case.http, "{entries:?}");
    assert_eq!(env.resolve("https://bucket"), case.https, "{entries:?}");
    assert_eq!(env.no_proxy.resolve(), case.no, "{entries:?}");
    assert_eq!(env.requires_python(), case.python, "{entries:?}");
}

#[test]
fn from_map_retains_every_proxy_input_independently() {
    let env = cased(&[
        ("HTTP_PROXY", "upper-http"),
        ("http_proxy", "lower-http"),
        ("HTTPS_PROXY", "upper-https"),
        ("https_proxy", "lower-https"),
        ("NO_PROXY", "upper-bypass"),
        ("no_proxy", "lower-bypass"),
        ("REQUEST_METHOD", "GET"),
    ]);
    let actual = Environment::from_map_with(&env, true);
    assert_eq!(
        actual.http,
        Pair {
            upper: Some("upper-http"),
            lower: Some("lower-http")
        }
    );
    assert_eq!(
        actual.https,
        Pair {
            upper: Some("upper-https"),
            lower: Some("lower-https")
        }
    );
    assert_eq!(
        actual.no_proxy,
        Pair {
            upper: Some("upper-bypass"),
            lower: Some("lower-bypass")
        }
    );
    assert!(actual.request_method);
    assert!(!actual.mixed_case);
    assert_eq!(actual.not_unicode, NotUnicode::default());
}
#[test]
fn from_map_reads_every_variable_the_decision_table_names() {
    let variables = [
        "HTTPS_PROXY",
        "https_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "NO_PROXY",
        "no_proxy",
    ];
    for (index, name) in variables.into_iter().enumerate() {
        let entries = [(name, "http://p:1")];
        let (sensitive, insensitive, host) =
            (cased(&entries), Uncased::new(&entries), env(&entries));
        for (names_have_case, env) in [
            (true, Environment::from_map_with(&sensitive, true)),
            (false, Environment::from_map_with(&insensitive, false)),
            (NAMES_HAVE_CASE, Environment::from_map(&host)),
        ] {
            let pair = [env.https, env.http, env.no_proxy][index / 2];
            let read = if index % 2 == 0 || !names_have_case {
                pair.upper
            } else {
                pair.lower
            };
            assert_eq!(read, Some("http://p:1"), "{name} {names_have_case}");
            assert!(!env.mixed_case);
        }
    }
}
const POSIX_RESOLUTIONS: [Resolution; 16] = [
    Resolution {
        no: Some("a"),
        ..case(&[("NO_PROXY", "a")])
    },
    Resolution {
        no: Some("b"),
        ..case(&[("no_proxy", "b")])
    },
    Resolution {
        no: Some("b"),
        ..case(&[("NO_PROXY", "a"), ("no_proxy", "b")])
    },
    Resolution {
        no: Some("b"),
        ..case(&[("no_proxy", "b"), ("NO_PROXY", "a")])
    },
    Resolution {
        python: true,
        ..case(&[("NO_PROXY", "a"), ("no_proxy", "")])
    },
    Resolution {
        no: Some("b"),
        ..case(&[("NO_PROXY", ""), ("no_proxy", "b")])
    },
    case(&[("NO_PROXY", "")]),
    case(&[("no_proxy", "")]),
    Resolution {
        python: true,
        ..case(&[("REQUEST_METHOD", "GET"), ("HTTP_PROXY", "http://u:1")])
    },
    Resolution {
        python: true,
        ..case(&[("REQUEST_METHOD", ""), ("HTTP_PROXY", "http://u:1")])
    },
    Resolution {
        http: Some("http://l:1"),
        ..case(&[("REQUEST_METHOD", "GET"), ("http_proxy", "http://l:1")])
    },
    Resolution {
        http: Some("http://l:1"),
        ..case(&[
            ("REQUEST_METHOD", "GET"),
            ("HTTP_PROXY", "http://u:1"),
            ("http_proxy", "http://l:1"),
        ])
    },
    Resolution {
        python: true,
        ..case(&[
            ("REQUEST_METHOD", "GET"),
            ("HTTP_PROXY", "http://u:1"),
            ("http_proxy", ""),
        ])
    },
    Resolution {
        https: Some("http://s:1"),
        no: Some("a"),
        ..case(&[
            ("REQUEST_METHOD", "GET"),
            ("HTTPS_PROXY", "http://s:1"),
            ("NO_PROXY", "a"),
        ])
    },
    Resolution {
        http: Some("http://u:1"),
        ..case(&[("request_method", "GET"), ("HTTP_PROXY", "http://u:1")])
    },
    Resolution {
        http: Some("http://u:1"),
        ..case(&[("HTTP_PROXY", "http://u:1")])
    },
];
#[test]
fn environment_resolution_matches_urllib_getproxies_environment() {
    for case in &POSIX_RESOLUTIONS {
        expect_resolution(case, Environment::from_map_with(&cased(case.entries), true));
    }
}
const WINDOWS_RESOLUTIONS: [Resolution; 8] = [
    Resolution {
        no: Some("b"),
        ..case(&[("no_proxy", "b")])
    },
    Resolution {
        no: Some("b"),
        ..case(&[("No_Proxy", "b")])
    },
    Resolution {
        no: Some("a"),
        ..case(&[("no_proxy", "b"), ("NO_PROXY", "a")])
    },
    case(&[("NO_PROXY", "a"), ("no_proxy", "")]),
    Resolution {
        https: Some("http://m:1"),
        ..case(&[("Https_Proxy", "http://m:1")])
    },
    Resolution {
        python: true,
        ..case(&[("REQUEST_METHOD", "GET"), ("http_proxy", "http://l:1")])
    },
    Resolution {
        python: true,
        ..case(&[("request_method", "GET"), ("HTTP_PROXY", "http://u:1")])
    },
    Resolution {
        https: Some("http://s:1"),
        no: Some("a"),
        ..case(&[
            ("REQUEST_METHOD", "GET"),
            ("HTTPS_PROXY", "http://s:1"),
            ("NO_PROXY", "a"),
        ])
    },
];
#[test]
fn environment_resolution_without_name_case_matches_urllib_on_windows() {
    for case in &WINDOWS_RESOLUTIONS {
        let env = Uncased::new(case.entries);
        expect_resolution(case, Environment::from_map_with(&env, false));
    }
}
#[test]
fn mixed_case_proxy_variables_require_python_only_where_names_have_case() {
    let cases: [(&[(&str, &str)], bool); 10] = [
        (&[("NO_PROXY", "a"), ("No_Proxy", "b")], true),
        (&[("No_Proxy", "b")], true),
        (&[("NO_proxy", "b"), ("NO_PROXY", "a")], true),
        (&[("NO_PROXY", "a"), ("NO_proxy", "")], true),
        (&[("Https_Proxy", "http://m:1")], true),
        (&[("http_PROXY", "")], true),
        (
            &[("HTTP_proxy", "http://m:1"), ("REQUEST_METHOD", "GET")],
            true,
        ),
        (&[("Xno_Proxy", "a")], false),
        (&[("No_Proxy_", "a")], false),
        (&[("All_Proxy", "http://m:1")], false),
    ];
    for (entries, python) in cases {
        let values = cased(entries);
        let env = Environment::from_map_with(&values, true);
        assert_eq!(env.mixed_case, python, "{entries:?}");
        assert_eq!(env.requires_python(), python, "{entries:?}");
        assert!(!Environment::from_map_with(&Uncased::new(entries), false).mixed_case);
    }
}
#[test]
fn lowercase_presence_controls_proxy_precedence() {
    for (upper, lower, expected, python) in [
        (None, None, None, false),
        (Some(""), None, None, false),
        (None, Some(""), None, false),
        (Some(""), Some(""), None, false),
        (
            Some("http://upper:80"),
            None,
            Some("http://upper:80"),
            false,
        ),
        (Some("http://upper:80"), Some(""), None, true),
        (
            None,
            Some("http://lower:80"),
            Some("http://lower:80"),
            false,
        ),
        (
            Some("http://upper:80"),
            Some("http://lower:80"),
            Some("http://lower:80"),
            false,
        ),
    ] {
        let pair = Pair { upper, lower };
        assert_eq!(pair.resolve(), expected);
        assert_eq!(pair.requires_python(), python);
    }
    let env = cased(&[
        ("HTTP_PROXY", "http://clear:80"),
        ("HTTPS_PROXY", "http://secure:80"),
        ("https_proxy", ""),
    ]);
    let proxies = Environment::from_map_with(&env, true);
    assert_eq!(proxies.resolve("http://bucket"), Some("http://clear:80"));
    assert_eq!(proxies.resolve("HTTPS://bucket"), None);
    assert!(proxies.requires_python());
}
#[test]
fn diagnostic_urls_preserve_masking_and_own_bytes() {
    for (url, expected) in [
        ("proxy:80", "http://proxy:80"),
        ("//proxy:80", "http://proxy:80"),
        ("https://proxy:443", "https://proxy:443"),
        ("http://user:secret@proxy:80", "http://***:***@proxy:80"),
        ("http://u:z@[::1]:80", "http://***:***@[::1]:80"),
        ("http://user@proxy:80", "http://***@proxy:80"),
        ("http://:secret@proxy:80", "http://:***@proxy:80"),
        ("http://user:@proxy:80", "http://***:@proxy:80"),
        ("http://http:secret@proxy", "***://http:***@proxy"),
        ("http://same:same@proxy", "http://***:***@proxy"),
    ] {
        assert_eq!(DisplayUrl::new(url).as_str(), expected);
    }
    let mut source = String::from("http://user:secret@proxy");
    let display = DisplayUrl::new(&source);
    source.clear();
    assert_eq!(display.as_str(), "http://***:***@proxy");
    assert_eq!(DisplayUrl::new(&"x".repeat(4097)).as_str(), "***");
}

const URLLIB_BYPASSES: [(&str, &str, bool); 55] = [
    ("*", "s3.amazonaws.com", true),
    ("*", "", true),
    (" *", "s3.amazonaws.com", false),
    ("* ", "s3.amazonaws.com", false),
    ("*,x", "s3.amazonaws.com", false),
    ("*,x", "x", true),
    ("x, *", "s3.amazonaws.com", false),
    ("x, *", "*", true),
    (".amazonaws.com", "s3.amazonaws.com", true),
    ("..amazonaws.com", "amazonaws.com", true),
    ("amazonaws.com.", "s3.amazonaws.com", false),
    ("amazonaws.com", "s3.amazonaws.com.", false),
    (".", "s3.amazonaws.com.", true),
    (".", "s3.amazonaws.com", false),
    (".", ":443", true),
    ("localhost", "localhost:8443", true),
    ("localhost:8443", "localhost:8443", true),
    ("localhost:8443", "localhost:9000", false),
    ("localhost:8443", "localhost", false),
    ("host:8443", "a.host:8443", true),
    ("LOCALHOST:8443", "localhost:8443", true),
    ("localhost", "LocalHost:8443", true),
    ("EXAMPLE.com", "s3.Example.COM", true),
    (" example.com \t", "example.com", true),
    ("\t.example.com\n", "a.example.com", true),
    ("\x0bexample.com\x0c\r", "example.com", true),
    ("\x1cexample.com\x1f", "example.com", true),
    ("\x1dexample.com\x1e", "example.com", true),
    (",,example.com,", "example.com", true),
    (", ,", "example.com", false),
    ("exa mple.com", "exa mple.com", true),
    ("[::1]", "[::1]:443", true),
    ("[::1]", "[::1]", true),
    ("::1", "[::1]:443", false),
    ("::1", "[::1]", false),
    ("1]", "[::1]", false),
    ("example.com", "badexample.com", false),
    ("example.com", "example.com.evil.test", false),
    ("example.com", "a.b.example.com:443", true),
    ("h", "h:", true),
    ("h:", "h:", true),
    ("0.0.1", "10.0.0.1", true),
    ("10.0.0.0/8", "10.0.0.1", false),
    ("amazonaws.com", "s3.amazonaws.com:abc", false),
    ("com:abc", "s3.amazonaws.com:abc", true),
    ("host", "user@host:80", false),
    ("user@host", "user@host:80", true),
    ("a:1:2", "a:1:2", true),
    ("a", "a:1:2", false),
    ("a:1", "a:1:2", true),
    ("x", "", false),
    ("x", ":", false),
    ("x,\x0b127.0.0.1\x0b", "127.0.0.1:8080", true),
    ("\x0bexample.com\x0c", "example.com", true),
    ("localhost", "LOCALHOST:8443", true),
];
#[test]
fn urllib_bypass_is_literal_case_insensitive_and_label_bounded() {
    for (list, netloc, expected) in URLLIB_BYPASSES {
        let proxies = Environment {
            no_proxy: Pair {
                upper: Some(list),
                lower: None,
            },
            ..Default::default()
        };
        assert_eq!(proxies.bypass(netloc), expected, "{list:?} {netloc:?}");
        assert!(!proxies.requires_python_for(netloc), "{list:?} {netloc:?}");
        let proxied = Environment {
            https: Pair {
                upper: Some("http://secure:80"),
                lower: None,
            },
            no_proxy: Pair {
                upper: None,
                lower: Some(list),
            },
            ..Default::default()
        };
        let url = proxied.resolve_for("https://endpoint", netloc);
        assert_eq!(url.is_none(), expected, "{list:?} {netloc:?}");
    }
    let unset = Environment {
        no_proxy: Pair {
            upper: Some("*"),
            lower: Some(""),
        },
        ..Default::default()
    };
    assert!(!unset.bypass("s3.amazonaws.com"));
    assert!(unset.requires_python());
}
#[test]
fn cgi_mixed_case_and_unicode_proxy_policies_remain_separate() {
    for entries in [
        vec![("HTTP_PROXY", "http://proxy:80"), ("REQUEST_METHOD", "")],
        vec![("hTtP_pRoXy", "http://proxy:80")],
        vec![("NO_PROXY", "\u{a0}example.com")],
        vec![("NO_PROXY", "example.com"), ("no_proxy", "")],
    ] {
        assert!(Environment::from_map_with(&cased(&entries), true).requires_python());
    }
    let values = cased(&[
        ("HTTP_PROXY", "http://upper:80"),
        ("http_proxy", "http://lower:80"),
        ("REQUEST_METHOD", "GET"),
    ]);
    let proxies = Environment::from_map_with(&values, true);
    assert_eq!(
        proxies.resolve("http://example.com"),
        Some("http://lower:80")
    );
    assert!(!proxies.requires_python());
    let values = env(&[("NO_PROXY", "key.test")]);
    assert!(Environment::from_map(&values).requires_python_for("Key.test"));
    assert!(!Environment::default().requires_python_for("Key.test"));
}
#[test]
fn non_ascii_bypass_lists_and_netlocs_require_python() {
    for (list, netloc, list_python) in [
        ("\u{a0}example.com", "example.com", true),
        ("\u{212a}ey.test", "key.test", true),
        ("key.test", "\u{212a}ey.test", false),
        ("\u{e9}.test", "\u{c9}.test", true),
    ] {
        let proxies = Environment {
            no_proxy: Pair {
                upper: Some(list),
                lower: None,
            },
            ..Default::default()
        };
        assert_eq!(proxies.requires_python(), list_python, "{list:?}");
        assert!(proxies.requires_python_for(netloc), "{list:?} {netloc:?}");
    }
    let overridden = Environment {
        no_proxy: Pair {
            upper: Some("\u{e9}"),
            lower: Some("x"),
        },
        ..Default::default()
    };
    assert!(!overridden.requires_python());
    let unlisted = Environment {
        no_proxy: Pair {
            upper: Some(""),
            lower: None,
        },
        ..Default::default()
    };
    assert!(!unlisted.requires_python_for("\u{c9}.test"));
}
#[test]
fn proxy_urls_that_are_not_unicode_require_python() {
    let pair = |upper, lower| Pair { upper, lower };
    let none = Spellings::default();
    let upper = Spellings {
        upper: true,
        lower: false,
    };
    let lower = Spellings {
        upper: false,
        lower: true,
    };
    let cases = [
        (pair(None, None), pair(None, None), none, upper, false, true),
        (pair(None, None), pair(None, None), upper, none, false, true),
        (
            pair(Some("http://u:1"), None),
            pair(None, None),
            lower,
            none,
            false,
            true,
        ),
        (
            pair(None, None),
            pair(None, Some("http://l:1")),
            none,
            upper,
            false,
            false,
        ),
        (
            pair(None, Some("http://l:1")),
            pair(None, None),
            upper,
            none,
            true,
            false,
        ),
    ];
    for (http, https, http_not_unicode, https_not_unicode, request_method, python) in cases {
        let environment = Environment {
            http,
            https,
            request_method,
            not_unicode: NotUnicode {
                http: http_not_unicode,
                https: https_not_unicode,
                ..NotUnicode::default()
            },
            ..Environment::default()
        };
        assert_eq!(environment.requires_python(), python, "{environment:?}");
    }
}
#[cfg(unix)]
#[test]
fn proxy_values_that_are_not_unicode_require_python() {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let not_unicode = OsStr::from_bytes(b"127.0.0.1,\xff");
    for name in [
        "HTTPS_PROXY",
        "https_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "NO_PROXY",
        "no_proxy",
    ] {
        let values = SnapshotEnv::from_pairs([(name, not_unicode)]);
        let proxies = Environment::from_map_with(&values, true);
        assert_ne!(proxies.not_unicode, NotUnicode::default(), "{name}");
        assert!(proxies.requires_python(), "{name}");
        assert_eq!(proxies.resolve("http://bucket"), None, "{name}");
        assert_eq!(proxies.resolve("https://bucket"), None, "{name}");
        assert_eq!(proxies.no_proxy.resolve(), None, "{name}");
        let uncased = Environment::from_map_with(&values, false);
        let upper = name.bytes().all(|c| !c.is_ascii_lowercase());
        assert_eq!(
            uncased.not_unicode != NotUnicode::default(),
            upper,
            "{name}"
        );
    }
}
#[cfg(unix)]
#[test]
fn a_lowercase_spelling_decides_over_an_uppercase_value_that_is_not_unicode() {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let not_unicode = OsStr::from_bytes(b"http://127.0.0.1:1/\xff");
    let values = SnapshotEnv::from_pairs([
        ("HTTPS_PROXY", not_unicode),
        ("https_proxy", OsStr::new("http://lower:1")),
    ]);
    let proxies = Environment::from_map_with(&values, true);
    assert!(proxies.not_unicode.https.upper);
    assert!(!proxies.requires_python());
    assert_eq!(proxies.resolve("https://bucket"), Some("http://lower:1"));
    for name in ["HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY"] {
        let lower = name.to_ascii_lowercase();
        let values =
            SnapshotEnv::from_pairs([(name, not_unicode), (lower.as_str(), OsStr::new(""))]);
        assert!(
            Environment::from_map_with(&values, true).requires_python(),
            "{name}"
        );
    }
}
#[cfg(unix)]
#[test]
fn request_method_that_is_not_unicode_marks_a_cgi_process() {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let not_unicode = OsStr::from_bytes(b"\xff");
    let values = SnapshotEnv::from_pairs([
        ("REQUEST_METHOD", not_unicode),
        ("HTTP_PROXY", OsStr::new("http://upper:1")),
    ]);
    let proxies = Environment::from_map_with(&values, true);
    assert!(proxies.request_method);
    assert_eq!(proxies.not_unicode, NotUnicode::default());
    assert!(proxies.requires_python());
    assert_eq!(proxies.resolve("http://bucket"), None);
    for name in ["ALL_PROXY", "all_proxy", "request_method"] {
        let values = SnapshotEnv::from_pairs([(name, not_unicode)]);
        let proxies = Environment::from_map_with(&values, true);
        assert_eq!(proxies, Environment::default(), "{name}");
    }
}
#[test]
fn netloc_requires_a_double_slash_after_the_first_colon() {
    for (url, expected) in [
        ("http://h:1/p", "h:1"),
        ("https://h:1/p?q", "h:1"),
        ("http://h#f", "h"),
        ("http://", ""),
        ("//h:80/x://y", ""),
        ("http:x://y", ""),
        ("http:/x://y", ""),
        ("h:1", ""),
        ("h", ""),
    ] {
        assert_eq!(crate::proxy::netloc(url), expected, "{url}");
    }
}
#[test]
fn proxy_bypass_uses_the_client_endpoint_instead_of_each_bucket_host() {
    let values = env(&[
        ("HTTPS_PROXY", "http://proxy:80"),
        ("NO_PROXY", "bucket.s3.amazonaws.com"),
    ]);
    let proxies = Environment::from_map(&values);
    assert_eq!(
        proxies.resolve_for("https://bucket.s3.amazonaws.com", "s3.amazonaws.com"),
        Some("http://proxy:80")
    );
    assert_eq!(
        proxies.resolve_for("https://bucket.s3.amazonaws.com", "bucket.s3.amazonaws.com"),
        None
    );
}
/// botocore's fetcher builds its session with `get_environ_proxies` of its
/// own URL, so the bypass list is tested against that URL's netloc and the
/// proxy is the one of its scheme.
#[test]
fn a_cleartext_request_leaves_for_the_proxy_botocore_picks() {
    const IMDS: &str = "http://169.254.169.254/";
    let forward = |entries: &[(&str, &str)], url: &str| {
        let env = crate::SnapshotEnv::from_pairs(entries.iter().copied());
        Environment::from_map(&env).forward(url)
    };
    let proxy = |host: &str, port: u16, url: &str| {
        Forward::Proxy(ForwardProxy {
            host: host.into(),
            port,
            url: url.into(),
        })
    };
    for direct in [
        &[][..],
        &[("HTTPS_PROXY", "http://p:1")],
        &[("HTTP_PROXY", "")],
        &[
            ("HTTP_PROXY", "http://p:1"),
            ("NO_PROXY", "169.254.169.254"),
        ],
        &[("HTTP_PROXY", "http://p:1"), ("NO_PROXY", "*")],
        &[("HTTP_PROXY", "http://p:1"), ("NO_PROXY", ".254")],
    ] {
        assert_eq!(forward(direct, IMDS), Forward::Direct, "{direct:?}");
    }
    // urllib compares names, so a network in CIDR form bypasses nothing.
    let cidr = [("HTTP_PROXY", "http://p:1"), ("NO_PROXY", "169.254.0.0/16")];
    assert_eq!(forward(&cidr, IMDS), proxy("p", 1, "http://p:1"));
    // The list is tested against the endpoint that is used.
    let named = [("HTTP_PROXY", "http://p:1"), ("NO_PROXY", "imds.invalid")];
    assert_eq!(forward(&named, IMDS), proxy("p", 1, "http://p:1"));
    assert_eq!(forward(&named, "http://imds.invalid/p"), Forward::Direct);
    assert_eq!(forward(&named, "http://imds.invalid:8080"), Forward::Direct);
    for (value, expected) in [
        (
            "http://127.0.0.1:3128",
            proxy("127.0.0.1", 3128, "http://127.0.0.1:3128"),
        ),
        (
            "http://proxy.example/",
            proxy("proxy.example", 80, "http://proxy.example/"),
        ),
        // `_fix_proxy_url` gives a proxy without a scheme one.
        ("127.0.0.1:1", proxy("127.0.0.1", 1, "http://127.0.0.1:1")),
        ("//p:8080", proxy("p", 8080, "http://p:8080")),
        ("https://p:1", Forward::Unsupported),
        ("http://user:secret@p:1", Forward::Unsupported),
        ("http://[::1]:1", Forward::Unsupported),
        ("http://p:0", Forward::Unsupported),
        ("http://p:x", Forward::Unsupported),
        ("http://p:1/path", Forward::Unsupported),
        ("HTTP://p:1", Forward::Unsupported),
        ("socks5://p:1", Forward::Unsupported),
    ] {
        assert_eq!(forward(&[("HTTP_PROXY", value)], IMDS), expected, "{value}");
    }
}
