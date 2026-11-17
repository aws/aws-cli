#![expect(
    clippy::unwrap_used,
    clippy::panic,
    reason = "pinned test fixtures and assertions"
)]
use super::*;
use crate::failure::{Color, FailureClass};
use crate::tables::CommandKind;
use std::collections::HashMap;
use std::path::Path;
fn corpus() -> String {
    std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/testdata/awscli/cases.jsonl"
    ))
    .unwrap()
}
fn argv(value: &Value) -> Vec<String> {
    value
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap().into())
        .collect()
}
fn fixture_environment<'a>(
    vars: &'a HashMap<String, std::ffi::OsString>,
    files: &'a unpack::FsParamfiles,
) -> Environment<'a> {
    Environment {
        directory: Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/src/testdata/awscli")),
        variables: vars,
        files,
        preferred_encoding: unpack::PreferredEncoding::Locale,
    }
}

#[cfg(unix)]
mod os {
    use super::*;
    use crate::bind::BindField;
    use std::ffi::{OsStr, OsString};
    use std::os::unix::ffi::OsStringExt;

    fn raw(value: &[u8]) -> OsString {
        OsString::from_vec(value.to_vec())
    }

    fn complete_os(arguments: &[OsString]) -> (ParseResult, bool) {
        let mut result = parse_os(arguments, &Options::default(), &tables::TABLES_DEFAULT);
        let unsupported = if result.outcome == Outcome::Parsed {
            complete(
                &mut result,
                &fixture_environment(&HashMap::new(), &unpack::FsParamfiles),
            )
        } else {
            false
        };
        (result, unsupported)
    }

    #[test]
    fn local_operands_keep_bytes_through_every_parser_stage_and_binding() {
        let local = raw(b"local-\xff");
        for arguments in [
            vec![
                "s3".into(),
                "cp".into(),
                local.clone(),
                "s3://bucket/key".into(),
            ],
            vec![
                "--region".into(),
                "us-west-2".into(),
                "s3".into(),
                "cp".into(),
                "--recursive".into(),
                "s3://bucket/key".into(),
                local.clone(),
            ],
            vec![
                "s3".into(),
                "cp".into(),
                "--".into(),
                raw(b"-local-\xff"),
                "s3://bucket/key".into(),
            ],
            vec![
                "s3".into(),
                "cp".into(),
                raw(b"file://literal-\xff"),
                "s3://bucket/key".into(),
                "--no-sign-request".into(),
            ],
        ] {
            let originals: Vec<_> = arguments
                .iter()
                .enumerate()
                .filter(|(_, argument)| argument.to_str().is_none())
                .map(|(index, argument)| (index, argument.clone()))
                .collect();
            let (result, unsupported) = complete_os(&arguments);
            assert!(!unsupported);
            assert_eq!(result.outcome, Outcome::Parsed, "{arguments:?}");
            assert_eq!(result.stage, Stage::Leftover);
            let paths = <[OsString; 2]>::bind(&result.values, "paths").unwrap();
            for (index, argument) in originals {
                assert!(paths.contains(&argument));
                assert!(
                    result
                        .globals
                        .remaining
                        .iter()
                        .any(|token| { token.original_index == index && token.value == argument })
                );
            }
        }
    }

    #[test]
    fn other_os_values_defer_without_silent_defaults() {
        let (result, unsupported) = complete_os(&[
            "s3".into(),
            "cp".into(),
            "local".into(),
            "s3://bucket/key".into(),
            raw(b"--region=region-\xff"),
        ]);
        assert!(!unsupported);
        assert_eq!(result.outcome, Outcome::UnsupportedOsValue);
        assert_eq!(result.stage, Stage::TopLevel);
        let (result, unsupported) =
            complete_os(&["s3".into(), "ls".into(), raw(b"file://target-\xff")]);
        assert!(unsupported);
        assert_eq!(result.stopped_dest.as_deref(), Some("paths"));
    }

    #[test]
    fn listing_targets_and_filters_keep_their_bytes() {
        let (result, unsupported) = complete_os(&[
            "s3".into(),
            "ls".into(),
            raw(b"s3://bucket/\xff"),
            "--bucket-name-prefix".into(),
            raw(b"pre-\xfe"),
            raw(b"--bucket-region=region-\xfd"),
        ]);
        assert!(!unsupported);
        assert_eq!(result.outcome, Outcome::Parsed);
        for (dest, value) in [
            ("paths", raw(b"s3://bucket/\xff")),
            ("bucket_name_prefix", raw(b"pre-\xfe")),
            ("bucket_region", raw(b"region-\xfd")),
        ] {
            assert_eq!(result.values.os_string(dest), Some(value.as_os_str()));
        }
    }

    #[test]
    fn os_integers_fail_as_int_does() {
        let (result, unsupported) = complete_os(&[
            "s3".into(),
            "cp".into(),
            "local".into(),
            "s3://bucket/key".into(),
            raw(b"--cli-connect-timeout=1\xff"),
        ]);
        assert!(!unsupported);
        assert_eq!(result.stage, Stage::TopLevel);
        assert_eq!(result.stopped_dest.as_deref(), Some("connect_timeout"));
        assert_eq!(
            result.outcome,
            Outcome::Failure(Failure::new(FailureKind::InvalidInteger(raw(b"1\xff"))))
        );
        let (result, unsupported) = complete_os(&[
            "s3".into(),
            "cp".into(),
            raw(b"local-\xff"),
            "s3://bucket/key".into(),
            "--page-size".into(),
            raw(b"1\xfe"),
        ]);
        assert!(!unsupported);
        assert_eq!(result.stopped_dest.as_deref(), Some("page_size"));
        assert_eq!(
            result.outcome,
            Outcome::Failure(Failure::new(FailureKind::InvalidInteger(raw(b"1\xfe"))))
        );
    }

    #[test]
    fn a_command_line_endpoint_url_with_a_scheme_passes_global_resolution_as_given() {
        let url = raw(b"http://\xff");
        let (result, unsupported) = complete_os(&[
            "--endpoint-url".into(),
            url.clone(),
            "s3".into(),
            "ls".into(),
        ]);
        assert!(!unsupported);
        assert_eq!(result.outcome, Outcome::Parsed);
        assert_eq!(
            result.globals.namespace.os_string("endpoint_url"),
            Some(url.as_os_str())
        );
        let (result, _) = complete_os(&[
            "--endpoint-url".into(),
            raw(b"\xff"),
            "s3".into(),
            "ls".into(),
        ]);
        assert_eq!(result.stage, Stage::TopLevel);
        let Outcome::Failure(failure) = &result.outcome else {
            panic!("expected a failure: {:?}", result.outcome);
        };
        assert_eq!(failure.kind, FailureKind::EndpointUrlScheme(raw(b"\xff")));
        assert!(
            failure
                .error_text(Color::default())
                .starts_with("Bad value for --endpoint-url \"\\udcff\": scheme is missing.")
        );
    }

    // A zone is any text to `ipaddress`, so one that is not Unicode is
    // taken with the address it follows. A host `urlparse` raises for is
    // named with a surrogate escape for each such byte.
    #[test]
    fn an_endpoint_url_s_bracketed_host_need_not_be_unicode() {
        let parsed = |url: &[u8]| {
            complete_os(&["--endpoint-url".into(), raw(url), "s3".into(), "ls".into()]).0
        };
        for url in [
            &b"http://[::1%\xff]"[..],
            b"http://[::1%25\xff]",
            b"http://[v1.\xff]",
        ] {
            assert_eq!(parsed(url).outcome, Outcome::Parsed, "{url:?}");
        }
        for (url, host) in [
            (&b"http://[::1%\xff%]"[..], "'::1%\\udcff%'"),
            (b"http://[\xff%x]", "'\\udcff%x'"),
            (b"http://[::\xff]", "'::\\udcff'"),
            (b"http://[1.2.3.4%\xff]", "'1.2.3.4%\\udcff'"),
        ] {
            let result = parsed(url);
            assert_eq!(result.stage, Stage::TopLevel, "{url:?}");
            let Outcome::Failure(failure) = result.outcome else {
                panic!("{url:?}: failure expected")
            };
            assert_eq!(
                failure.error_text(Color::default()),
                format!("{host} does not appear to be an IPv4 or IPv6 address"),
                "{url:?}"
            );
        }
    }

    #[test]
    fn raw_unknown_options_retain_their_original_invocation_index() {
        let unknown = raw(b"--unknown-\xff");
        let (result, unsupported) = complete_os(&[
            "s3".into(),
            "cp".into(),
            "local".into(),
            "s3://bucket/key".into(),
            unknown.clone(),
        ]);
        assert!(!unsupported);
        assert_eq!(result.args.remaining.len(), 1);
        assert_eq!(result.args.remaining[0].original_index, 4);
        assert_eq!(result.args.remaining[0].as_os_str(), OsStr::new(&unknown));
        let Outcome::Failure(failure) = &result.outcome else {
            panic!("expected a failure: {:?}", result.outcome);
        };
        assert_eq!(failure.kind, "unknown_options");
        assert_eq!(
            failure.error_text(Color::default()),
            "Unknown options: --unknown-\\udcff"
        );
    }
}

#[test]
#[cfg(windows)]
fn local_surrogate_operands_survive_completion_and_binding() {
    use crate::bind::BindField;
    use std::ffi::OsString;
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    let wide: Vec<_> = "C:\\local-".encode_utf16().chain([0xd800]).collect();
    let local = OsString::from_wide(&wide);
    let mut result = parse_os(
        &["s3".into(), "cp".into(), local, "s3://bucket/key".into()],
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    assert!(!complete(
        &mut result,
        &fixture_environment(&HashMap::new(), &unpack::FsParamfiles)
    ));
    assert_eq!(result.outcome, Outcome::Parsed);
    let paths = <[OsString; 2]>::bind(&result.values, "paths").unwrap();
    assert_eq!(paths[0].encode_wide().collect::<Vec<_>>(), wide);
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "checks every captured corpus case in one loop"
)]
fn captured_chain_outcomes_provenance_and_values() {
    let vars = HashMap::from([
        ("ARGPARSE_FIXTURES".into(), "paramfile".into()),
        ("LC_ALL".into(), "C.UTF-8".into()),
    ]);
    let files = unpack::FsParamfiles;
    let env = fixture_environment(&vars, &files);
    let mut count = 0;
    for line in corpus().lines() {
        let original: Value = crate::json::parse(line.as_bytes()).unwrap();
        let expected = original.get("native_expectation").unwrap_or(&original);
        let args = argv(&original["argv"]);
        let mut result = parse(&args, &Options::default(), &tables::TABLES_DEFAULT);
        let unsupported = if result.outcome == Outcome::Parsed {
            complete(&mut result, &env)
        } else {
            false
        };
        let actual =
            crate::tool::result_json(&result, unsupported, original["color"].as_bool().unwrap());
        for key in [
            "outcome",
            "stage",
            "lineage",
            "first_pass",
            "first_pass_seen",
            "globals",
            "globals_seen",
            "args",
            "args_seen",
            "remaining",
            "skipped",
            "values",
            "unsupported",
        ] {
            let expected = expected.get(key).cloned().unwrap_or(Value::Null);
            if key == "values" {
                assert_eq!(
                    actual[key].to_string(),
                    expected.to_string(),
                    "case {count} {args:?} field {key}"
                );
            } else {
                assert_eq!(actual[key], expected, "case {count} {args:?} field {key}");
            }
        }
        if let Outcome::Failure(_) = &result.outcome {
            let case = format!("case {count} {args:?}");
            assert_corpus_failure(&actual["error"], &expected["error"], &case);
        }
        for level in [&result.first_pass, &result.globals, &result.args] {
            for entry in &level.namespace.entries {
                if entry.dest == "help" {
                    continue;
                }
                assert_eq!(
                    entry.explicit,
                    level
                        .table
                        .iter()
                        .zip(&level.seen)
                        .any(|(a, s)| a.matches_dest(&entry.dest) && *s)
                );
            }
        }
        count += 1;
    }
    assert_eq!(count, 205);
}

fn assert_corpus_failure(actual: &Value, error: &Value, case: &str) {
    assert_eq!(actual["class"], error["class"], "{case}");
    assert_eq!(actual["text"], *corpus_failure_text(error), "{case}");
    let dest = error.get("dest").cloned().unwrap_or(Value::Null);
    assert_eq!(actual["dest"], dest, "{case}");
    if let Some(parameter) = error.get("parameter") {
        assert_eq!(actual["parameter"], *parameter, "{case}");
    }
}
fn corpus_failure_text(error: &Value) -> &Value {
    #[cfg(windows)]
    if let Some(text) = error.get("windows_native_text") {
        return text;
    }
    error.get("native_text").unwrap_or(&error["text"])
}
fn level_table(case: &Value, level: &Value) -> Vec<Argument> {
    match level["parser"].as_str().unwrap() {
        "FirstPassGlobalArgParser" => tables::FIRST_PASS.to_vec(),
        "MainArgParser" if level["help_mode"].as_bool().unwrap() => {
            help_mode_table(main_table(&tables::TABLES_DEFAULT))
        }
        "MainArgParser" => main_table(&tables::TABLES_DEFAULT),
        "SubCommandArgParser" => command_table(&tables::S3),
        "ArgTableArgParser" => {
            let command = case["lineage"]
                .as_array()
                .unwrap()
                .iter()
                .skip(1)
                .fold(&tables::S3, |command, name| {
                    command.subcommand(name.as_str().unwrap()).unwrap()
                });
            command_table(command)
        }
        _ => panic!("unknown parser"),
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "checks every captured parser level in one loop"
)]
fn captured_per_level_namespace_seen_extras_errors() {
    let mut count = 0;
    for line in corpus().lines() {
        let case: Value = crate::json::parse(line.as_bytes()).unwrap();
        for level in case["levels"].as_array().unwrap() {
            let name = level["parser"].as_str().unwrap();
            let table = level_table(&case, level);
            let mut options = parser::Options::new(level["usage"].as_str().unwrap());
            options.colored_usage = level["colored_usage"].as_str().map(str::to_owned);
            options.help_sentinel = matches!(name, "SubCommandArgParser" | "ArgTableArgParser");
            options.ignore_required = name == "SubCommandArgParser";
            options.command_choices = Some(
                tables::S3
                    .subcommands
                    .unwrap()
                    .iter()
                    .map(|c| c.name)
                    .collect(),
            );
            let parser = Parser::new(&table, options).unwrap();
            match parser.parse_known_args(&argv(&level["argv"])) {
                Ok(parsed) => {
                    assert!(level["error"].is_null(), "case {count}");
                    assert_eq!(parsed.version, level["version"].as_bool().unwrap());
                    if !level["namespace"].is_null() {
                        assert_eq!(parsed.namespace.json(), level["namespace"]);
                    }
                    let seen: Vec<_> = parser
                        .arguments
                        .iter()
                        .zip(&parsed.seen)
                        .filter_map(|(a, s)| s.then_some(a.name))
                        .collect();
                    assert_eq!(Value::from(seen), level["seen"]);
                    if !parsed.version {
                        assert_eq!(Value::from(parsed.remaining), level["remaining"]);
                    }
                }
                Err(rejected) => {
                    assert_eq!(
                        rejected.failure.error_text(Color {
                            force_color: case["color"].as_bool().unwrap(),
                            ..Color::default()
                        }),
                        level["error"]["native_text"].as_str().unwrap(),
                        "case {count}"
                    );
                }
            }
            count += 1;
        }
    }
    assert!(count > 600);
}
#[test]
fn unknown_options_suggest_close_command_and_global_options() {
    let ls = tables::S3.subcommand("ls").unwrap();
    let suggestions = unknown_option_suggestions(
        &[
            "--recurisve",
            "us-west-2",
            "--regoin=x",
            "--recurisve",
            "--bogus",
            "-recurisve",
        ]
        .map(std::ffi::OsStr::new),
        ls.arguments,
    );
    assert_eq!(
        suggestions,
        [
            Suggestion {
                matched: "recursive".into(),
                name: "recurisve".into(),
            },
            Suggestion {
                matched: "region".into(),
                name: "regoin".into(),
            },
        ]
    );
}
#[test]
fn raw_boundary_and_owned_results() {
    let result = parse(
        &["s3", "ls", "--page-size", "abc", "--bogus"].map(str::to_owned),
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    assert_eq!(result.outcome, Outcome::Parsed);
    assert_eq!(result.args.namespace.string("page_size"), Some("abc"));
    assert_eq!(result.args.remaining, ["--bogus"]);
    assert!(result.args.was_supplied("page-size"));
}
#[test]
fn failed_level_retains_namespace_before_failure() {
    for (args, command) in [
        (vec!["s3", "--output", "bogus"], Some("s3")),
        (vec!["ec2", "--output", "bogus"], Some("ec2")),
        (vec!["--output", "bogus", "ec2"], None),
        (vec![], None),
    ] {
        let parsed = parse(
            &args.iter().map(|s| (*s).into()).collect::<Vec<_>>(),
            &Options::default(),
            &tables::TABLES_DEFAULT,
        );
        assert_eq!(parsed.stage, Stage::Main);
        assert_eq!(parsed.failed.unwrap().string("command"), command);
    }
    assert!(
        parse(
            &["s3".into(), "ls".into()],
            &Options::default(),
            &tables::TABLES_DEFAULT
        )
        .failed
        .is_none()
    );
}
#[test]
fn global_timeouts_over_the_digit_limit_stop_at_their_destination() {
    let over = "1".repeat(unpack::PYTHON_INT_MAX_STR_DIGITS + 1);
    for (option, dest) in [
        ("--cli-read-timeout", "read_timeout"),
        ("--cli-connect-timeout", "connect_timeout"),
    ] {
        let result = parse(
            &["s3", "ls", option, over.as_str()].map(str::to_owned),
            &Options::default(),
            &tables::TABLES_DEFAULT,
        );
        assert_eq!(result.stopped_dest.as_deref(), Some(dest));
        let Outcome::Failure(failure) = result.outcome else {
            panic!("failure expected")
        };
        assert_eq!(failure.kind, FailureKind::IntegerDigitLimit(4301));
        assert_eq!(failure.class, FailureClass::General);
    }
}
// `urlparse` raises for the brackets of an endpoint URL's authority before
// `resolve_types` looks for a scheme: a ValueError, which the general
// handler renders.
#[test]
fn an_endpoint_url_s_brackets_fail_as_urlparse_raises() {
    const INVALID: &str = "Invalid IPv6 URL";
    const IPV4: &str = "An IPv4 address cannot be in brackets";
    const FUTURE: &str = "IPvFuture address is invalid";
    for (url, raised) in [
        ("http://[", INVALID),
        ("http://]", INVALID),
        ("http://[::1", INVALID),
        ("http://a[::1]", INVALID),
        ("http://[::1]x", INVALID),
        ("http://[::1]]", INVALID),
        ("http://[[::1]]", INVALID),
        ("//[", INVALID),
        (" HT\tTP://[", INVALID),
        ("http://[1.2.3.4]", IPV4),
        ("http://[vz]", FUTURE),
        ("http://[v1.]", FUTURE),
        (
            "http://[zz]",
            "'zz' does not appear to be an IPv4 or IPv6 address",
        ),
        (
            "http://[]:80",
            "'' does not appear to be an IPv4 or IPv6 address",
        ),
        (
            "http://[::1%]",
            "'::1%' does not appear to be an IPv4 or IPv6 address",
        ),
        (
            "http://u[x]@h:80",
            "'h' does not appear to be an IPv4 or IPv6 address",
        ),
        (
            "http://[::1%a%b]",
            "'::1%a%b' does not appear to be an IPv4 or IPv6 address",
        ),
        (
            "http://[\u{e9}]",
            "'\u{e9}' does not appear to be an IPv4 or IPv6 address",
        ),
        (
            "http://[::\u{661}]",
            "'::\u{661}' does not appear to be an IPv4 or IPv6 address",
        ),
    ] {
        let result = parse(
            &["--endpoint-url", url, "s3", "ls"].map(str::to_owned),
            &Options::default(),
            &tables::TABLES_DEFAULT,
        );
        assert_eq!(result.stage, Stage::TopLevel, "{url}");
        let Outcome::Failure(failure) = result.outcome else {
            panic!("{url}: failure expected")
        };
        assert_eq!(failure.class, FailureClass::General, "{url}");
        assert_eq!(failure.error_text(Color::default()), raised, "{url}");
    }
}
// What `urlparse` takes: an IPv6 address with any zone, an IPvFuture
// address, and a bracket outside the authority or in its userinfo alone.
#[test]
fn an_endpoint_url_s_bracketed_address_passes_global_resolution() {
    for url in [
        "http://[::1]",
        "http://[::1]:8080/x",
        "http://u@[::FFFF:1.2.3.4]",
        "http://[fe80::1%eth0]",
        "http://[::1%\u{e9}]",
        "http://[::1%\u{a0}]",
        "http://[v1.x]",
        "http://u]@[::1",
        "http://h/[",
        "http://h?[",
        "http://h#]",
        "http:[",
    ] {
        let result = parse(
            &["--endpoint-url", url, "s3", "ls"].map(str::to_owned),
            &Options::default(),
            &tables::TABLES_DEFAULT,
        );
        assert_eq!(result.outcome, Outcome::Parsed, "{url}");
    }
}
#[test]
fn first_pass_errors_precede_main_and_own_diagnostics() {
    let result = parse(
        &["s3", "ls", "--debug=1"].map(str::to_owned),
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    assert_eq!(result.stage, Stage::FirstPass);
    let Outcome::Failure(failure) = result.outcome else {
        panic!("failure expected")
    };
    assert_eq!(
        failure.error_text(Color::default()),
        "argument --debug: ignored explicit argument '1'\n\nusage: aws [--profile PROFILE] \
    [--debug]\n"
    );
}
#[test]
fn first_pass_usage_wraps_whole_options_at_formatter_boundaries() {
    for (width, prog, first, second) in [
        (0, "aws", "\n       ", "\n       "),
        (13, "aws", "\n       ", "\n       "),
        (14, "aws", "\n           ", "\n           "),
        (22, "aws", "\n           ", "\n           "),
        (29, "aws", "\n           ", "\n           "),
        (30, "aws", " ", "\n           "),
        (39, "aws", " ", "\n           "),
        (40, "aws", " ", " "),
        (78, "aws", " ", " "),
        (
            22,
            "/bin/a-very-long-program-name",
            "\n       ",
            "\n       ",
        ),
        (37, "a-very-long-program-name", "\n       ", " "),
        (22, "ééé", "\n           ", "\n           "),
    ] {
        let options = Options {
            prog: prog.into(),
            formatter_width: width,
        };
        let name = prog.rsplit('/').next().unwrap();
        assert_eq!(
            first_pass_usage(&options, false),
            format!("{name}{first}[--profile PROFILE]{second}[--debug]")
        );
        assert_eq!(
            first_pass_usage(&options, true),
            format!(
                "\x1b[1;34musage: \x1b[0m\x1b[1;35m{name}\x1b[0m{first}[\x1b[36m--profile \
    \x1b[33mPROFILE\x1b[0m]{second}[\x1b[36m--debug\x1b[0m]\n"
            )
        );
    }
}
#[test]
fn first_pass_usage_names_the_basename_as_os_path_splits_it() {
    let windows = cfg!(windows);
    for (prog, expected) in [
        ("/usr/bin/aws", "aws"),
        (
            r"D:\a\target\aws.exe",
            if windows {
                "aws.exe"
            } else {
                r"D:\a\target\aws.exe"
            },
        ),
        (
            r"bin\aws.exe",
            if windows { "aws.exe" } else { r"bin\aws.exe" },
        ),
        ("bin/aws.exe", "aws.exe"),
        ("C:aws.exe", if windows { "aws.exe" } else { "C:aws.exe" }),
    ] {
        let options = Options {
            prog: prog.into(),
            formatter_width: 78,
        };
        assert_eq!(
            first_pass_usage(&options, false),
            format!("{expected} [--profile PROFILE] [--debug]"),
            "{prog}"
        );
    }
}
#[test]
#[cfg(unix)]
fn first_pass_usage_writes_undecodable_prog_bytes_as_escaped_surrogates() {
    use std::os::unix::ffi::OsStrExt;
    let indent = format!("\n{}", " ".repeat(12));
    for (prog, width, expected) in [
        (
            &b"aws\xff"[..],
            78,
            "aws\\udcff [--profile PROFILE] [--debug]".into(),
        ),
        (
            b"/d\xfe/aws\xe2\x82",
            78,
            "aws\\udce2\\udc82 [--profile PROFILE] [--debug]".into(),
        ),
        (
            b"aws\xff",
            15,
            format!("aws\\udcff{indent}[--profile PROFILE]{indent}[--debug]"),
        ),
        // Python counts each byte outside a valid UTF-8 sequence as one code
        // point, so this prog wraps as `ééé` does.
        (
            b"\xc3\xa9\xff\x80",
            22,
            format!(
                "é\\udcff\\udc80{0}[--profile PROFILE]{0}[--debug]",
                "\n           "
            ),
        ),
    ] {
        let options = Options {
            prog: std::ffi::OsStr::from_bytes(prog).into(),
            formatter_width: width,
        };
        assert_eq!(first_pass_usage(&options, false), expected);
    }
}
#[test]
fn leftover_and_usage_failures_keep_handler_class_and_separator() {
    static OPERATION: Command = Command {
        name: "operation",
        kind: CommandKind::Operation,
        usage: None,
        arguments: &[],
        subcommands: None,
    };
    static ROOT: Command = Command {
        name: "s3",
        kind: CommandKind::Basic,
        usage: None,
        arguments: &[],
        subcommands: Some(&[OPERATION]),
    };
    let tables = Tables {
        globals: tables::GLOBALS,
        s3: &ROOT,
    };
    let vars = HashMap::new();
    let files = unpack::FsParamfiles;
    let environment = fixture_environment(&vars, &files);
    for (args, kind, class, text) in [
        (
            vec!["s3", "operation", "--bogus", "x"],
            "unknown_options",
            FailureClass::UnknownArgument,
            "Unknown options: --bogus, x",
        ),
        (
            vec!["s3"],
            "too_few_arguments",
            FailureClass::ParamValidation,
            "usage: aws [options] s3 <subcommand> [parameters]\naws: [ERROR]: too few arguments",
        ),
    ] {
        let argv = args.into_iter().map(str::to_owned).collect::<Vec<_>>();
        let mut result = parse(&argv, &Options::default(), &tables);
        assert!(!complete(&mut result, &environment));
        let Outcome::Failure(failure) = result.outcome else {
            panic!("failure required")
        };
        assert_eq!(failure.kind, kind);
        assert_eq!(failure.class, class);
        assert_eq!(failure.error_text(Color::default()), text);
    }
    let mut basic = parse(
        &["s3", "ls", "--bogus", "x", "y"].map(str::to_owned),
        &Options::default(),
        &tables::TABLES_DEFAULT,
    );
    assert!(!complete(&mut basic, &environment));
    let Outcome::Failure(failure) = basic.outcome else {
        panic!("failure required")
    };
    assert_eq!(failure.class, FailureClass::ParamValidation);
    assert_eq!(
        failure.error_text(Color::default()),
        "Unknown options: --bogus, y"
    );
}
