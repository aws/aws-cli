#![expect(
    clippy::panic,
    reason = "unexpected fixture outcomes must fail the test"
)]
use super::*;
use awscli_argparse::{Options, tables};
use std::{
    collections::{BTreeMap, HashMap},
    path::Path,
};
#[derive(Debug)]
enum Expected {
    Native(bool),
    Python(PythonReason),
    Failure(&'static str),
}
fn files(text: &str) -> ParsedFiles {
    ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: text.as_bytes(),
        }),
        ..Default::default()
    })
}
fn evaluate(args: &[&str], env: &impl EnvMap, files: &ParsedFiles) -> Verdict {
    let argv = args.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>();
    let mut result = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    let vars = env
        .names()
        .into_iter()
        .filter_map(|name| Some((name.to_owned(), env.var_os(name)?.to_owned())))
        .collect();
    route(
        &mut result,
        &unpack::Environment {
            directory: Path::new("."),
            variables: &vars,
            files: &unpack::FsParamfiles,
            preferred_encoding: unpack::PreferredEncoding::Locale,
        },
        &Configuration {
            env,
            shared_files: files,
            boto_config_credentials: false,
            embedded_trust: true,
        },
    )
}
fn expect(args: &[&str], expected: Expected) {
    let result = evaluate(args, &BTreeMap::new(), &files(""));
    match (result, expected) {
        (Verdict::Native(native), Expected::Native(cp)) => {
            assert_eq!(matches!(native.command, Command::S3Cp(_)), cp);
        }
        (Verdict::Python(a), Expected::Python(b)) => assert_eq!(a, b, "{args:?}"),
        (Verdict::Failure(a), Expected::Failure(b)) => assert_eq!(a.kind, b, "{args:?}"),
        (actual, expected) => panic!("{args:?}: {actual:?}, expected {expected:?}"),
    }
}

#[cfg(unix)]
mod os {
    use super::*;
    use std::ffi::OsString;
    use std::os::unix::ffi::OsStringExt;

    fn evaluate_os(arguments: &[OsString]) -> Verdict {
        evaluate_prog_os(&Options::default(), arguments)
    }

    fn evaluate_prog_os(options: &Options, arguments: &[OsString]) -> Verdict {
        let mut result = awscli_argparse::parse_os(arguments, options, &tables::TABLES_DEFAULT);
        route(
            &mut result,
            &unpack::Environment {
                directory: Path::new("."),
                variables: &HashMap::new(),
                files: &unpack::FsParamfiles,
                preferred_encoding: unpack::PreferredEncoding::Locale,
            },
            &Configuration {
                env: &BTreeMap::new(),
                shared_files: &files(""),
                boto_config_credentials: false,
                embedded_trust: true,
            },
        )
    }

    #[test]
    fn raw_local_copy_operands_reach_native_admission_losslessly() {
        let local = OsString::from_vec(b"local-\xff".to_vec());
        for paths in [
            [local.clone(), "s3://bucket/key".into()],
            ["s3://bucket/key".into(), local.clone()],
        ] {
            let arguments = ["s3".into(), "cp".into(), "--no-sign-request".into()]
                .into_iter()
                .chain(paths.clone())
                .collect::<Vec<_>>();
            let Verdict::Native(native) = evaluate_os(&arguments) else {
                panic!("raw local operands must remain native");
            };
            let Command::S3Cp(args) = native.command else {
                panic!("copy invocation must bind copy arguments");
            };
            assert_eq!(args.paths, paths);
        }
    }

    #[test]
    fn raw_remote_keys_are_native_and_raw_buckets_and_globals_are_python_s() {
        let raw = |value: &[u8]| OsString::from_vec(value.to_vec());
        let paths = ["local".into(), raw(b"s3://bucket/key-\xff")];
        let arguments = ["s3".into(), "cp".into()].into_iter().chain(paths.clone());
        let Verdict::Native(native) = evaluate_os(&arguments.collect::<Vec<_>>()) else {
            panic!("a raw remote key must remain native");
        };
        let Command::S3Cp(args) = native.command else {
            panic!("copy invocation must bind copy arguments");
        };
        assert_eq!(args.paths, paths);
        let target = raw(b"s3://bucket/prefix-\xff");
        let Verdict::Native(native) = evaluate_os(&["s3".into(), "ls".into(), target.clone()])
        else {
            panic!("a raw listing prefix must remain native");
        };
        let Command::S3Ls(args) = native.command else {
            panic!("listing invocation must bind listing arguments");
        };
        assert_eq!(args.paths, target);
        for paths in ["s3://", "s3://bucket"] {
            let arguments = [
                "s3".into(),
                "ls".into(),
                paths.into(),
                "--bucket-name-prefix".into(),
                raw(b"pre-\xff"),
                "--bucket-region".into(),
                raw(b"region-\xff"),
            ];
            let Verdict::Native(native) = evaluate_os(&arguments) else {
                panic!("raw bucket filters must remain native");
            };
            let Command::S3Ls(args) = native.command else {
                panic!("listing invocation must bind listing arguments");
            };
            assert_eq!(args.bucket_name_prefix, Some(raw(b"pre-\xff")));
            assert_eq!(args.bucket_region, Some(raw(b"region-\xff")));
        }
        for arguments in [
            vec![
                "s3".into(),
                "cp".into(),
                "local".into(),
                raw(b"s3://bucket-\xff/key"),
            ],
            vec!["s3".into(), "ls".into(), raw(b"s3://bucket-\xff/prefix")],
        ] {
            assert_eq!(
                evaluate_os(&arguments),
                Verdict::Python(PythonReason::UnsupportedOperand),
                "{arguments:?}"
            );
        }
        assert_eq!(
            evaluate_os(&[
                "s3".into(),
                "cp".into(),
                "local".into(),
                "s3://bucket/key".into(),
                "--region".into(),
                OsString::from_vec(b"region-\xff".to_vec()),
            ]),
            Verdict::Python(PythonReason::UnsupportedValue)
        );
    }

    #[test]
    fn raw_filter_patterns_are_python_s() {
        assert_eq!(
            evaluate_os(&[
                "s3".into(),
                "cp".into(),
                "local".into(),
                "s3://bucket/key".into(),
                "--exclude".into(),
                OsString::from_vec(b"pattern-\xff".to_vec()),
            ]),
            Verdict::Python(PythonReason::UnsupportedValue)
        );
    }

    #[test]
    fn raw_values_a_failure_quotes_fail_natively() {
        for (arguments, kind) in [
            (
                vec![
                    "s3".into(),
                    "ls".into(),
                    "s3://bucket/".into(),
                    OsString::from_vec(b"\xff".to_vec()),
                ],
                "unknown_options",
            ),
            (
                vec![
                    "s3".into(),
                    "cp".into(),
                    "local".into(),
                    "s3://bucket/key".into(),
                    "--page-size".into(),
                    OsString::from_vec(b"1\xff".to_vec()),
                ],
                "invalid_integer",
            ),
        ] {
            let Verdict::Failure(failure) = evaluate_os(&arguments) else {
                panic!("{arguments:?} must fail natively");
            };
            assert_eq!(failure.kind, kind, "{arguments:?}");
        }
    }

    fn surrogate_escape_cases() -> Vec<(OsString, Vec<OsString>, String)> {
        let raw = |value: &[u8]| OsString::from_vec(value.to_vec());
        let prefix = "\naws: [ERROR]: An error occurred (ParamValidation): ";
        let usage = format!("\n\nusage: {}", tables::USAGE);
        let ls =
            |argument: OsString| vec!["s3".into(), "ls".into(), "s3://bucket/".into(), argument];
        vec![
            (
                "aws".into(),
                vec![
                    "--output".into(),
                    raw(b"js\xffon"),
                    "s3".into(),
                    "ls".into(),
                ],
                format!(
                    "{prefix}argument --output: Found invalid choice 'js\\udcffon'\n\n\
                     Maybe you meant:\n\n  * json{usage}"
                ),
            ),
            (
                "aws".into(),
                vec!["s3".into(), "ls".into(), raw(b"--recursive=\xff")],
                format!("{prefix}argument --recursive: ignored explicit argument '\\udcff'{usage}"),
            ),
            (
                "aws".into(),
                ls(raw(b"--bucket-=\xff")),
                format!(
                    "{prefix}ambiguous option: --bucket-=\\udcff could match \
                     --bucket-name-prefix, --bucket-region{usage}"
                ),
            ),
            (
                "aws".into(),
                vec![
                    "s3".into(),
                    "cp".into(),
                    "a.txt".into(),
                    "s3://bucket/key".into(),
                    raw(b"--unknown-\xff"),
                ],
                format!("{prefix}Unknown options: --unknown-\\udcff\n"),
            ),
            (
                "aws".into(),
                vec![
                    "s3".into(),
                    "ls".into(),
                    "--page-size".into(),
                    raw(b"1\xff"),
                ],
                "\naws: [ERROR]: invalid literal for int() with base 10: '1\\udcff'\n".into(),
            ),
            (
                raw(b"/bin/aws\xff"),
                vec!["--profile".into()],
                format!(
                    "{prefix}argument --profile: expected one argument\n\n\
                     usage: aws\\udcff [--profile PROFILE] [--debug]\n"
                ),
            ),
        ]
    }

    #[test]
    fn argv_bytes_that_are_not_utf8_render_as_python_s_surrogate_escapes() -> std::io::Result<()> {
        for (prog, arguments, expected) in surrogate_escape_cases() {
            let options = Options {
                prog,
                ..Options::default()
            };
            let Verdict::Failure(failure) = evaluate_prog_os(&options, &arguments) else {
                panic!("{arguments:?} must fail natively");
            };
            let mut written = Vec::new();
            let rendering = cli_core::cli_error::Rendering {
                format: ErrorFormat::Enhanced,
                color: Default::default(),
            };
            cli_core::cli_error::render(&mut written, &failure, rendering)?;
            assert_eq!(String::from_utf8_lossy(&written), expected, "{arguments:?}");
        }
        Ok(())
    }

    #[test]
    fn metadata_json_that_is_not_utf8_is_python_s() {
        assert_eq!(
            evaluate_os(&[
                "s3".into(),
                "cp".into(),
                "--metadata".into(),
                OsString::from_vec(b"{\"x\": \"\xff\"}".to_vec()),
                "./a".into(),
                "s3://b/k".into(),
                "--bogus".into(),
            ]),
            Verdict::Python(PythonReason::UnsupportedValue)
        );
    }

    #[test]
    fn a_command_line_endpoint_url_that_is_not_unicode_is_python_s() {
        for command in [
            &["s3", "ls", "s3://bucket"][..],
            &["s3", "cp", "a", "s3://b/k"],
        ] {
            let mut arguments = vec![
                OsString::from("--endpoint-url"),
                OsString::from_vec(b"http://\xff".to_vec()),
            ];
            arguments.extend(command.iter().map(OsString::from));
            assert_eq!(
                evaluate_os(&arguments),
                Verdict::Python(PythonReason::EndpointSetting),
                "{command:?}"
            );
        }
    }
}
#[test]
fn complete_native_invocations_route_to_their_handler_with_bound_values() {
    for (argv, expected) in [
        (&["s3", "ls"][..], Expected::Native(false)),
        (&["s3", "ls", "s3://bucket"][..], Expected::Native(false)),
        (
            &["s3", "ls", "s3://bucket", "--page-size", "10"][..],
            Expected::Native(false),
        ),
        (
            &["s3", "ls", "--recursive", "--summarize", "--human-readable"][..],
            Expected::Native(false),
        ),
        (
            &["s3", "ls", "bucket/prefix", "--page-size", "1_0"][..],
            Expected::Native(false),
        ),
        (
            &["s3", "cp", "s3://bucket/key", "local"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--recursive", "s3://bucket/prefix", "dir"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--", "local", "s3://bucket/key"][..],
            Expected::Native(true),
        ),
        (
            &["--region", "us-west-2", "s3", "ls"][..],
            Expected::Native(false),
        ),
        (
            &["s3", "ls", "--region", "us-west-2"][..],
            Expected::Native(false),
        ),
        (
            &["--endpoint-url", "http://localhost:4566", "s3", "ls"][..],
            Expected::Native(false),
        ),
        (
            &["s3", "ls", "--endpoint-url=http://localhost:4566"][..],
            Expected::Native(false),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn other_commands_go_to_python_untouched() {
    for (argv, expected) in [
        (
            &["ec2", "describe-instances"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["s3api", "get-object"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["lambda", "list-functions"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["help"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["configure", "list"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["--region", "s3", "ls"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn main_parse_failures_are_native_only_when_no_other_command_was_consumed_first() {
    for (argv, expected) in [
        (
            &["ec2", "--output", "bogus"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["lambda", "invoke", "--region"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["--output", "bogus", "ec2"][..],
            Expected::Failure("parse"),
        ),
        (
            &["--region", "--debug", "ec2"][..],
            Expected::Failure("parse"),
        ),
        (&["s3", "--output", "bogus"][..], Expected::Failure("parse")),
        (
            &["s3", "ls", "--output=bogus"][..],
            Expected::Failure("parse"),
        ),
        (&["s3", "ls", "--=value"][..], Expected::Failure("parse")),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn first_pass_and_auto_prompt_failures_are_command_independent() {
    for (argv, expected) in [
        (&["s3", "ls", "--debug=1"][..], Expected::Failure("parse")),
        (
            &["lambda", "invoke", "--function-name", "--profile"][..],
            Expected::Failure("parse"),
        ),
        (
            &["--cli-auto-prompt", "--no-cli-auto-prompt", "s3", "ls"][..],
            Expected::Failure("auto_prompt_conflict"),
        ),
        (
            &["ec2", "--cli-auto-prompt", "--no-cli-auto-prompt"][..],
            Expected::Failure("auto_prompt_conflict"),
        ),
    ] {
        expect(argv, expected);
    }
}
fn native_rm(args: &[&str]) -> s3::rm::Args {
    match evaluate(args, &BTreeMap::new(), &files("")) {
        Verdict::Native(native) => {
            assert_eq!(
                native.client.command,
                client_config::Command::Rm,
                "{args:?}"
            );
            assert!(native.client.persona.is_some(), "{args:?}");
            match native.command {
                Command::S3Rm(rm) => rm,
                command => panic!("{args:?}: {command:?}"),
            }
        }
        verdict => panic!("{args:?}: {verdict:?}"),
    }
}
#[test]
fn s3_rm_routes_natively_with_its_bound_arguments() {
    let rm = native_rm(&["s3", "rm", "s3://bucket/key"]);
    assert_eq!(rm.paths, [std::ffi::OsString::from("s3://bucket/key")]);
    assert!(!rm.dir_op && !rm.dryrun && !rm.quiet && !rm.only_show_errors);
    assert_eq!((rm.page_size, rm.request_payer), (None, None));
    let rm = native_rm(&[
        "s3",
        "rm",
        "s3://bucket/prefix/",
        "--recursive",
        "--dryrun",
        "--quiet",
        "--only-show-errors",
        "--page-size",
        "5",
        "--request-payer",
        "--exclude",
        "*",
        "--include",
        "*.txt",
    ]);
    assert!(rm.dir_op && rm.dryrun && rm.quiet && rm.only_show_errors);
    assert_eq!(rm.page_size, Some(5));
    assert_eq!(rm.request_payer.as_deref(), Some("requester"));
    assert_eq!(
        rm.filters,
        [
            (s3::filter::FilterKind::Exclude, "*".to_owned()),
            (s3::filter::FilterKind::Include, "*.txt".to_owned()),
        ]
    );
    native_rm(&["--color", "on", "--no-cli-pager", "s3", "rm", "s3://b/k"]);
}
#[test]
fn s3_rm_leaves_operands_and_values_it_cannot_take_to_python() {
    for (argv, reason) in [
        (
            &["s3", "rm", "local.txt"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "rm", "s3://bucket-s3alias/key"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "rm", "s3://bucket/key", "--page-size", "0"][..],
            PythonReason::UnsupportedValue,
        ),
    ] {
        expect(argv, Expected::Python(reason));
    }
}
fn native_sync(args: &[&str]) -> s3::sync::Args {
    match evaluate(args, &BTreeMap::new(), &files("")) {
        Verdict::Native(native) => {
            assert_eq!(
                native.client.command,
                client_config::Command::Sync,
                "{args:?}"
            );
            assert!(native.client.persona.is_some(), "{args:?}");
            match native.command {
                Command::S3Sync(sync) => *sync,
                command => panic!("{args:?}: {command:?}"),
            }
        }
        verdict => panic!("{args:?}: {verdict:?}"),
    }
}
#[test]
fn s3_sync_routes_natively_between_a_local_directory_and_s3() {
    let sync = native_sync(&["s3", "sync", "site", "s3://bucket/www/"]);
    assert_eq!(sync.paths, ["site", "s3://bucket/www/"]);
    let sync = native_sync(&["s3", "sync", "s3://bucket", "."]);
    assert_eq!(sync.paths, ["s3://bucket", "."]);
    let sync = native_sync(&[
        "s3",
        "sync",
        "s3://b/p",
        ".",
        "--delete",
        "--size-only",
        "--exact-timestamps",
        "--no-overwrite",
        "--case-conflict",
        "warn",
        "--exclude",
        "*",
        "--dryrun",
        "--no-progress",
    ]);
    assert!(sync.delete && sync.size_only && sync.exact_timestamps && sync.no_overwrite);
    assert_eq!(sync.case_conflict, s3::sync::OnCaseConflict::Warn);
    let sync = native_sync(&[
        "s3",
        "sync",
        "site",
        "s3://bucket/www/",
        "--grants",
        "read=id=x",
        "full=id=y",
        "--no-guess-mime-type",
    ]);
    assert_eq!(sync.grants, ["read=id=x", "full=id=y"]);
    assert!(!sync.guess_mime_type);
    let sync = native_sync(&["s3", "sync", "s3://b/p", ".", "--grants", "everyone"]);
    assert_eq!(sync.grants, ["everyone"]);
    native_sync(&[
        "--color",
        "on",
        "--no-cli-pager",
        "s3",
        "sync",
        "s3://b/p",
        ".",
    ]);
}
#[test]
fn s3_sync_leaves_every_option_and_operands_it_cannot_take_to_python() {
    for (argv, reason) in [
        (
            &["s3", "sync", "a", "b"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "sync", "s3://bucket/a/", "s3://bucket/b/"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "sync", "-", "s3://bucket/a/"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "sync", "dir", "s3://bucket--usw2-az1--x-s3/a/"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &[
                "s3",
                "sync",
                "dir",
                "s3://bucket/a/",
                "--grants",
                "everyone",
            ][..],
            PythonReason::UnsupportedValue,
        ),
        (
            &[
                "s3",
                "sync",
                "s3://bucket/a/",
                "dir",
                "--source-region",
                "x",
            ][..],
            PythonReason::UnsupportedOption,
        ),
    ] {
        expect(argv, Expected::Python(reason));
    }
}
#[test]
fn s3_sync_parse_failures_render_natively() {
    for argv in [
        &["s3", "sync", "--bogus", "a", "s3://b/"][..],
        &["s3", "sync", "--exact-timestamps=1", "a", "s3://b/"],
        &["s3", "sync", "a", "s3://b/", "--recursive"],
        &["s3", "sync", "a"],
    ] {
        assert!(
            matches!(
                evaluate(argv, &BTreeMap::new(), &files("")),
                Verdict::Failure(_)
            ),
            "{argv:?}"
        );
    }
}
fn native_mv(args: &[&str]) -> s3::mv::Args {
    match evaluate(args, &BTreeMap::new(), &files("")) {
        Verdict::Native(native) => {
            assert_eq!(
                native.client.command,
                client_config::Command::Mv,
                "{args:?}"
            );
            assert!(native.client.persona.is_some(), "{args:?}");
            match native.command {
                Command::S3Mv(mv) => mv,
                command => panic!("{args:?}: {command:?}"),
            }
        }
        verdict => panic!("{args:?}: {verdict:?}"),
    }
}
#[test]
fn s3_mv_routes_natively_with_its_bound_arguments() {
    let mv = native_mv(&["s3", "mv", "local.txt", "s3://bucket/key"]);
    assert_eq!(mv.paths, ["local.txt", "s3://bucket/key"]);
    assert!(!mv.dir_op && !mv.dryrun && !mv.quiet && !mv.only_show_errors);
    assert!(mv.progress && !mv.validate_same_s3_paths);
    let mv = native_mv(&[
        "s3",
        "mv",
        "s3://bucket/prefix/",
        "dir",
        "--recursive",
        "--dryrun",
        "--quiet",
        "--no-progress",
        "--no-overwrite",
        "--page-size",
        "5",
        "--validate-same-s3-paths",
        "--exclude",
        "*",
        "--include",
        "*.txt",
        "--case-conflict",
        "error",
    ]);
    assert!(mv.dir_op && mv.dryrun && mv.quiet && mv.no_overwrite);
    assert_eq!(mv.case_conflict, s3::sync::OnCaseConflict::Error);
    assert!(!mv.progress && mv.validate_same_s3_paths);
    assert_eq!(mv.page_size, Some(5));
    assert_eq!(
        mv.filters,
        [
            (s3::filter::FilterKind::Exclude, "*".to_owned()),
            (s3::filter::FilterKind::Include, "*.txt".to_owned()),
        ]
    );
    native_mv(&[
        "--color",
        "on",
        "--no-cli-pager",
        "s3",
        "mv",
        "s3://b/k",
        ".",
    ]);
}
#[test]
fn s3_transfers_bind_the_symlink_flags_natively() {
    for (flags, follows) in [
        (&[][..], true),
        (&["--follow-symlinks"][..], true),
        (&["--no-follow-symlinks"][..], false),
        (&["--follow-symlinks", "--no-follow-symlinks"][..], false),
        (&["--no-follow-symlinks", "--follow-symlinks"][..], true),
    ] {
        let argv = |command: &'static str, paths: [&'static str; 2]| {
            [&["s3", command][..], &paths, flags].concat()
        };
        match evaluate(&argv("cp", ["a", "s3://b/k"]), &BTreeMap::new(), &files("")) {
            Verdict::Native(native) => match native.command {
                Command::S3Cp(cp) => assert_eq!(cp.follow_symlinks, follows, "{flags:?}"),
                command => panic!("{flags:?}: {command:?}"),
            },
            verdict => panic!("{flags:?}: {verdict:?}"),
        }
        let mv = native_mv(&argv("mv", ["s3://b/k", "a"]));
        assert_eq!(mv.follow_symlinks, follows, "{flags:?}");
        let sync = native_sync(&argv("sync", ["dir", "s3://b/p/"]));
        assert_eq!(sync.follow_symlinks, follows, "{flags:?}");
    }
}
#[test]
fn s3_mv_leaves_operands_options_and_values_it_cannot_take_to_python() {
    for (argv, reason) in [
        (
            &["s3", "mv", "a", "b"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "mv", "s3://bucket/key", "s3://bucket/other"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "mv", "-", "s3://bucket/key"][..],
            PythonReason::UnsupportedOperand,
        ),
        (
            &["s3", "mv", "s3://bucket/key", "out", "--request-payer"][..],
            PythonReason::UnsupportedOption,
        ),
        (
            &[
                "s3",
                "mv",
                "local.txt",
                "s3://bucket/key",
                "--sse",
                "AES256",
            ][..],
            PythonReason::UnsupportedOption,
        ),
        (
            &[
                "s3",
                "mv",
                "s3://b/p",
                "dir",
                "--recursive",
                "--page-size",
                "0",
            ][..],
            PythonReason::UnsupportedValue,
        ),
    ] {
        expect(argv, Expected::Python(reason));
    }
}
#[test]
fn s3_subcommands_without_a_native_handler_go_to_python_whatever_their_outcome() {
    for (argv, expected) in [
        (
            &["s3", "mb", "s3://bucket"][..],
            Expected::Python(PythonReason::UnsupportedSubcommand),
        ),
        (
            &["s3", "rb", "s3://bucket"][..],
            Expected::Python(PythonReason::UnsupportedSubcommand),
        ),
        (
            &["s3", "presign", "s3://bucket/key"][..],
            Expected::Python(PythonReason::UnsupportedSubcommand),
        ),
        (
            &["s3", "website", "s3://bucket"][..],
            Expected::Python(PythonReason::UnsupportedSubcommand),
        ),
        (
            &["s3", "mb", "--bogus", "s3://bucket"][..],
            Expected::Python(PythonReason::UnsupportedSubcommand),
        ),
        (
            &["s3", "rb", "--force=1", "s3://bucket"][..],
            Expected::Python(PythonReason::UnsupportedSubcommand),
        ),
        (
            &["s3", "presign", "--expires-in", "abc", "s3://b/k"][..],
            Expected::Python(PythonReason::UnsupportedSubcommand),
        ),
        (
            &["s3", "mb", "help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn query_is_python_s_because_upstream_compiles_it_before_other_validation() {
    for argv in [
        &["--query", "Contents", "s3", "ls"][..],
        &["--query=Contents", "s3", "ls"],
        &["--query", "Contents", "s3", "ls", "--bogus"],
        &["s3", "ls", "--query", "[", "--page-size", "1"],
    ] {
        expect(argv, Expected::Python(PythonReason::PythonOnlyGlobal));
    }
}
#[test]
fn aws_cli_ignored_s3_ls_globals_route_native_at_any_position() {
    for (argv, expected) in [
        (
            &["s3", "ls", "--output", "json"][..],
            Expected::Native(false),
        ),
        (
            &["s3", "cp", "source", "s3://bucket/key", "--output", "json"][..],
            Expected::Python(PythonReason::PythonOnlyGlobal),
        ),
        (
            &["s3", "cp", "source", "s3://bucket/key", "--no-paginate"][..],
            Expected::Python(PythonReason::PythonOnlyGlobal),
        ),
        (
            &["s3", "--output", "json"][..],
            Expected::Python(PythonReason::PythonOnlyGlobal),
        ),
        (
            &["--output", "definitely-invalid", "s3", "ls"][..],
            Expected::Failure("parse"),
        ),
        (&["s3", "ls", "--output="][..], Expected::Failure("parse")),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn the_error_format_is_native_for_the_framings_the_renderer_implements() {
    for (argv, expected) in [
        (
            &["--cli-error-format", "legacy", "s3", "ls"][..],
            Expected::Native(false),
        ),
        (
            &["s3", "ls", "--cli-error-format", "enhanced"][..],
            Expected::Native(false),
        ),
        (
            &["--cli-error-format", "json", "s3", "ls"][..],
            Expected::Python(PythonReason::PythonOnlyGlobal),
        ),
        (
            &["s3", "ls", "--cli-error-format=table"][..],
            Expected::Python(PythonReason::PythonOnlyGlobal),
        ),
        (
            &["s3", "ls", "--cli-error-format", "LEGACY"][..],
            Expected::Failure("parse"),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn option_values_are_consumed_by_argparse_arity() {
    for (argv, expected) in [
        (&["--region", "s3", "s3", "ls"][..], Expected::Native(false)),
        (&["--region=s3", "s3", "ls"][..], Expected::Native(false)),
        (
            &["--region=", "s3", "ls"][..],
            Expected::Python(PythonReason::EndpointSetting),
        ),
        (&["--debug", "s3", "ls"][..], Expected::Native(false)),
        (&["s3", "--debug", "ls"][..], Expected::Native(false)),
        (
            &["s3", "cp", "--debug", "source", "s3://bucket/key"][..],
            Expected::Native(true),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn missing_option_values_are_the_parser_s_failure_at_the_level_that_owns_them() {
    for (argv, expected) in [
        (
            &["s3", "cp", "--page-size", "--version"][..],
            Expected::Python(PythonReason::VersionRequested),
        ),
        (
            &["s3", "--region", "--debug", "ls"][..],
            Expected::Failure("parse"),
        ),
        (
            &["s3", "ls", "--region", "--debug"][..],
            Expected::Failure("parse"),
        ),
        (
            &["s3", "ls", "--region", "--"][..],
            Expected::Failure("parse"),
        ),
        (&["s3", "ls", "--region"][..], Expected::Failure("parse")),
        (
            &["s3", "cp", "--page-size", "--debug"][..],
            Expected::Failure("parse"),
        ),
        (
            &["s3", "cp", "--page-size", "--recursive"][..],
            Expected::Failure("parse"),
        ),
        (
            &["s3", "cp", "--page-size", "--"][..],
            Expected::Failure("parse"),
        ),
        (&["s3", "cp", "--page-size"][..], Expected::Failure("parse")),
        (
            &["s3", "cp", "only-one-path"][..],
            Expected::Failure("parse"),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn leftover_tokens_are_the_command_s_unknown_options_failure() {
    for (argv, expected) in [
        (
            &["--throughput-target-gbps", "5", "s3", "ls"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (&["s3", "cp", "-h"][..], Expected::Failure("parse")),
        (&["s3", "cp", "-x", "b"][..], Expected::Failure("parse")),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn help_and_version_outcomes_are_python_s() {
    for (argv, expected) in [
        (
            &["s3", "help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "ls", "help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "cp", "help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["--help", "s3", "ls"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "--help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "ls", "s3://bucket", "--help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "cp", "s3://one/key", "s3://two/key", "--help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "cp", "--page-size", "--help"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "--region", "--help", "ls"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["s3", "ls", "--bogus", "--hel"][..],
            Expected::Python(PythonReason::HelpRequested),
        ),
        (
            &["--help"][..],
            Expected::Python(PythonReason::UnsupportedCommand),
        ),
        (
            &["--region", "--version", "s3", "ls"][..],
            Expected::Python(PythonReason::VersionRequested),
        ),
        (
            &["--version"][..],
            Expected::Python(PythonReason::VersionRequested),
        ),
        (
            &["s3", "ls", "--version"][..],
            Expected::Python(PythonReason::VersionRequested),
        ),
        (
            &["lambda", "invoke", "--function-name", "--version"][..],
            Expected::Python(PythonReason::VersionRequested),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn copy_grants_route_natively_unless_an_upload_would_refuse_them() {
    for (argv, expected) in [
        (
            &[
                "s3",
                "cp",
                "a",
                "s3://b/k",
                "--grants",
                "read=id=x",
                "full=id=y",
            ][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "a", "s3://b/k", "--no-guess-mime-type"][..],
            Expected::Native(true),
        ),
        (
            &[
                "s3",
                "cp",
                "a",
                "s3://b/k",
                "--grants",
                "read=id=x",
                "everyone",
            ][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &[
                "s3",
                "cp",
                "a",
                "s3://b/",
                "--recursive",
                "--grants",
                "write=id=x",
            ][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "cp", "a", "s3://b/k", "--grants", "read=id=\u{7}"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "cp", "s3://b/k", "a", "--grants", "everyone"][..],
            Expected::Native(true),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn an_explicit_tags_option_routes_to_python() {
    for argv in [
        &["s3", "cp", "a", "s3://b/k", "--tags", "k", "v"][..],
        &["s3", "mv", "a", "s3://b/k", "--tags", "k", "v"][..],
        &["s3", "sync", "a", "s3://b", "--tags", "k", "v"][..],
    ] {
        expect(argv, Expected::Python(PythonReason::UnsupportedOption));
    }
}
#[test]
fn options_outside_the_native_surface_route_to_python() {
    for (argv, expected) in [
        (
            &["s3", "cp", "a", "s3://b/k", "--sse-c-copy-source"][..],
            Expected::Python(PythonReason::UnsupportedOption),
        ),
        (
            &[
                "s3",
                "cp",
                "--exclude",
                "x",
                "a",
                "s3://b/k",
                "--include",
                "y",
            ][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--no-progress", "a", "s3://b/k"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--dryrun", "s3://b/k", "a", "--recursive"][..],
            Expected::Native(true),
        ),
        (
            &[
                "s3",
                "cp",
                "s3://b/p/",
                "a",
                "--recursive",
                "--case-conflict",
                "skip",
            ][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--expected-size", "5", "a", "s3://b/k"][..],
            Expected::Python(PythonReason::UnsupportedOption),
        ),
        (
            &["s3", "cp", "--page-size", "abc", "a", "s3://b/k", "--sse"][..],
            Expected::Failure("invalid_integer"),
        ),
        (
            &[
                "s3",
                "cp",
                "--metadata",
                "a=b",
                "./a",
                "s3://b/k",
                "--bogus",
            ][..],
            Expected::Failure("unknown_options"),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn object_settings_route_to_native_cp() {
    for (argv, expected) in [
        (
            &["s3", "cp", "--sse", "aws:kms", "a", "s3://b/k"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "a", "s3://b/k", "--sse"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--metadata", "a=b", "a", "s3://b/k"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--metadata", "{\"a\": \"b\"}", "a", "s3://b/k"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--sse-c", "--sse-c-key", "k", "s3://b/k", "a"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--sse-c-key", "k", "a", "s3://b/k"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--cache-control", "a\nb", "a", "s3://b/k"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "cp", "--cache-control", "a\nb", "s3://b/k", "a"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--metadata", "k=caf\u{e9}", "a", "s3://b/k"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &[
                "s3",
                "cp",
                "--expires",
                "2037-10-21T07:28:00Z",
                "a",
                "s3://b/k",
            ][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--expires", "90", "a", "s3://b/k"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "cp", "--expires", "tomorrow", "s3://b/k", "a"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn checksum_settings_route_to_native_cp() {
    for (argv, expected) in [
        (
            &[
                "s3",
                "cp",
                "--checksum-algorithm",
                "SHA256",
                "a",
                "s3://b/k",
            ][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--checksum-mode", "ENABLED", "s3://b/k", "a"][..],
            Expected::Native(true),
        ),
        (
            &["s3", "cp", "--checksum-mode", "ENABLED", "a", "s3://b/k"][..],
            Expected::Native(true),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn value_processing_precedes_the_leftover_check() {
    let digits = "1".repeat(4301);
    for (argv, expected) in [
        (
            &["s3", "ls", "--page-size", "0"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "ls", "--page-size", "-1"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "cp", "--page-size", "4294967296", "a", "s3://b/k"][..],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "ls", "--page-size", "99999999999999999999"][..],
            Expected::Failure("integer_out_of_range"),
        ),
        (
            &["s3", "cp", "--page-size", "abc", "file://a", "s3://b/k"][..],
            Expected::Failure("invalid_integer"),
        ),
        (
            &["s3", "ls", "--page-size", digits.as_str()][..],
            Expected::Failure("integer_digit_limit"),
        ),
        (
            &["s3", "ls", "--bucket-region", "file://region"][..],
            Expected::Failure("paramfile_load"),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn unsupported_s3_operands_route_to_python_after_the_checks_that_precede_them() {
    for (argv, expected) in [
        (
            &["s3", "ls", "--request-payer", "bogus"][..],
            Expected::Failure("parse"),
        ),
        (
            &["s3", "ls", "--request-payer", "s3://bucket"][..],
            Expected::Failure("parse"),
        ),
    ] {
        expect(argv, expected);
    }
}
#[test]
fn exact_router_override() {
    assert_eq!(
        forced_route(Some("python")),
        Some(PythonReason::EnvOverride)
    );
    for value in [
        None,
        Some(""),
        Some("Python"),
        Some("python "),
        Some("native"),
    ] {
        assert_eq!(forced_route(value), None);
    }
}
#[test]
fn empty_lowercase_proxy_overrides_use_python_for_both_commands() {
    for (upper, lower) in [("HTTP_PROXY", "http_proxy"), ("HTTPS_PROXY", "https_proxy")] {
        let env = cli_core::SnapshotEnv::from_pairs([(upper, "http://proxy:80"), (lower, "")]);
        for argv in [&["s3", "ls"][..], &["s3", "cp", "a", "s3://b/k"]] {
            let actual = evaluate(argv, &env, &files(""));
            if cli_core::proxy::NAMES_HAVE_CASE {
                assert_eq!(actual, Verdict::Python(PythonReason::NetworkSetting));
            } else {
                assert!(matches!(actual, Verdict::Native(_)), "{actual:?}");
            }
        }
    }
}
#[test]
fn missing_command_is_the_main_parsers_own_failure() {
    for argv in [&[][..], &["--region", "us-west-2"], &["--debug"], &["--"]] {
        let Verdict::Failure(failure) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!()
        };
        assert_eq!(
            failure.error_text(Default::default()),
            format!(
                "the following arguments are required: command\n\nusage: {}",
                tables::USAGE
            )
        );
    }
}
#[test]
fn bare_s3_is_the_root_commands_usage_failure() {
    for argv in [
        &["s3"][..],
        &["s3", "--region", "us-west-2"],
        &["--debug", "s3"],
    ] {
        let Verdict::Failure(failure) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!()
        };
        assert_eq!(
            failure.error_text(Default::default()),
            "usage: aws [options] s3 <subcommand> [parameters]\naws: [ERROR]: too few arguments"
        );
    }
}
#[test]
fn bound_values_preserve_raw_namespace() {
    let argv = [
        "s3",
        "--region",
        "eu-west-1",
        "cp",
        "--page-size",
        "1_0",
        "--quiet",
        "s3://bucket/key",
        "out",
    ]
    .map(str::to_owned);
    let mut result = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    let Verdict::Native(native) = route(
        &mut result,
        &unpack::Environment {
            directory: Path::new("."),
            variables: &HashMap::new(),
            files: &unpack::FsParamfiles,
            preferred_encoding: unpack::PreferredEncoding::Locale,
        },
        &Configuration {
            env: &BTreeMap::new(),
            shared_files: &files(""),
            boto_config_credentials: false,
            embedded_trust: true,
        },
    ) else {
        panic!()
    };
    assert_eq!(native.globals.region.as_deref(), Some("eu-west-1"));
    let Command::S3Cp(args) = native.command else {
        panic!()
    };
    assert_eq!(args.page_size, Some(10));
    assert!(args.quiet);
    assert!(!args.dir_op);
    assert_eq!(args.paths, ["s3://bucket/key", "out"]);
    assert_eq!(result.values.integer("page_size"), Some(10));
    assert_eq!(result.args.namespace.string("page_size"), Some("1_0"));
}
#[test]
fn every_native_field_is_an_upstream_destination() {
    for (names, table) in [
        (s3::ls::DESTINATIONS, tables::LS_ARGUMENTS),
        (s3::cp_args::DESTINATIONS, tables::CP_ARGUMENTS),
        (s3::mv::DESTINATIONS, tables::MV_ARGUMENTS),
        (s3::rm::DESTINATIONS, tables::RM_ARGUMENTS),
    ] {
        for name in names {
            assert!(table.iter().any(|a| a.destination() == *name));
        }
    }
    for argument in tables::LS_ARGUMENTS {
        assert!(s3::ls::DESTINATIONS.contains(&argument.destination().as_str()));
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "exhaustive cross-product preserves all source variants"
)]
fn decision_table_routes_every_setting_from_every_source() {
    use effective_config::{Match, SETTINGS, Scope, Source, Support};
    assert_eq!(SETTINGS.len(), 105);
    for setting in SETTINGS {
        let value = effective_config::sample::sample_value(setting);
        let (env_name, config) = match setting.source {
            Source::Env(name) => (Some(name), String::new()),
            Source::Profile("services") => (
                None,
                format!("[default]\nservices = {value}\n[services {value}]\nx = y\n"),
            ),
            Source::Profile(key) => (None, format!("[default]\n{key} = {value}\n")),
            Source::Chain(env, key) => (Some(env), format!("[default]\n{key} = {value}\n")),
            Source::S3(key) => (None, format!("[default]\ns3 =\n  {key} = {value}\n")),
            Source::ErrorFormat => (
                Some("AWS_CLI_ERROR_FORMAT"),
                format!("[default]\ncli_error_format = {value}\n"),
            ),
        };
        for variant in 0..3 {
            if (variant == 0 && env_name.is_none()) || (variant == 1 && config.is_empty()) {
                continue;
            }
            let mut env = BTreeMap::new();
            if variant != 1
                && let Some(name) = env_name
            {
                env.insert(name.into(), value.into());
            }
            if setting.source == Source::Env("AWS_ACCESS_KEY_ID") {
                env.insert("AWS_SECRET_ACCESS_KEY".into(), "secret".into());
            }
            let files = files(if variant == 0 { "" } else { &config });
            for cp in [false, true] {
                let argv = if cp {
                    &["s3", "cp", "a", "s3://b/k"][..]
                } else {
                    &["s3", "ls"]
                };
                let actual = evaluate(argv, &env, &files);
                match setting.support {
                    Support::Honored(_) if cp && setting.source == Source::S3("max_bandwidth") => {
                        assert_eq!(actual, Verdict::Python(PythonReason::TransferSetting));
                    }
                    Support::Honored(_)
                        if cp && setting.source == Source::Env("REQUESTS_CA_BUNDLE") =>
                    {
                        assert_eq!(actual, Verdict::Python(PythonReason::NetworkSetting));
                    }
                    Support::Unsupported(reason) if cp || setting.scope != Scope::Transfer => {
                        assert_eq!(
                            actual,
                            Verdict::Python(reason),
                            "{setting:?} variant {variant}"
                        );
                    }
                    _ => assert!(
                        matches!(actual, Verdict::Native(_)),
                        "{setting:?}: {actual:?}"
                    ),
                }
            }
        }
        assert!(effective_config::matches(setting.matching, value));
        if setting.matching == Match::HistoryEnabled {
            assert!(!effective_config::matches(setting.matching, "Enabled"));
        }
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "ordered assertions cover each selection priority"
)]
fn profile_selection_and_settings_precedence() {
    let files = files("[default]\n[profile work]\n[profile history]\ncli_history = enabled\n");
    let mut env = BTreeMap::new();
    assert!(matches!(
        evaluate(&["s3", "ls"], &env, &files),
        Verdict::Native(_)
    ));
    assert_eq!(
        evaluate(&["--profile", "missing", "s3", "ls"], &env, &files),
        Verdict::Python(PythonReason::ProfileLookup)
    );
    assert!(matches!(
        evaluate(&["--profile", "", "s3", "ls"], &env, &files),
        Verdict::Native(_)
    ));
    env.insert("AWS_DEFAULT_PROFILE".into(), "missing".into());
    assert_eq!(
        evaluate(&["s3", "ls"], &env, &files),
        Verdict::Python(PythonReason::ProfileLookup)
    );
    assert!(matches!(
        evaluate(&["--profile", "work", "s3", "ls"], &env, &files),
        Verdict::Native(_)
    ));
    env.insert("AWS_DEFAULT_PROFILE".into(), "history".into());
    assert_eq!(
        evaluate(&["s3", "ls"], &env, &files),
        Verdict::Python(PythonReason::HistoryEnabled)
    );
    env.insert("AWS_PROFILE".into(), "work".into());
    assert!(matches!(
        evaluate(&["s3", "ls"], &env, &files),
        Verdict::Native(_)
    ));
    env.insert("AWS_PROFILE".into(), "".into());
    assert_eq!(
        evaluate(&["s3", "ls"], &env, &files),
        Verdict::Python(PythonReason::ProfileLookup)
    );
    assert!(matches!(
        evaluate(&["--profile", "work", "s3", "ls"], &env, &files),
        Verdict::Native(_)
    ));
}
#[test]
fn environment_overrides_profile_even_when_empty() {
    let files = files("[default]\ncli_error_format = json\n");
    let structured = Some(PythonReason::StructuredErrorFormat);
    for argv in [&["s3", "ls"][..], &["s3", "cp", "a", "s3://b/k"]] {
        let unset = evaluate(argv, &BTreeMap::new(), &files);
        assert_eq!(python_reason(unset), structured);
        for (value, expected) in [
            ("legacy", None),
            ("", None),
            ("YAML", structured),
            ("nonsense", None),
        ] {
            let env = BTreeMap::from([("AWS_CLI_ERROR_FORMAT".into(), value.into())]);
            let actual = python_reason(evaluate(argv, &env, &files));
            assert_eq!(actual, expected, "{value}");
            let flagged = [argv, &["--cli-error-format", "legacy"]].concat();
            assert!(matches!(
                evaluate(&flagged, &env, &files),
                Verdict::Native(_)
            ));
        }
    }
}
fn python_reason(verdict: Verdict) -> Option<PythonReason> {
    match verdict {
        Verdict::Native(_) => None,
        Verdict::Python(reason) => Some(reason),
        verdict => panic!("{verdict:?}"),
    }
}
#[test]
fn the_retired_new_retries_variable_is_admitted() {
    let files = files("[default]\n");
    for value in ["false", "True", "true"] {
        let env = BTreeMap::from([("AWS_NEW_RETRIES_2026".into(), value.into())]);
        for argv in [&["s3", "ls"][..], &["s3", "cp", "a", "s3://b/k"]] {
            assert_eq!(python_reason(evaluate(argv, &env, &files)), None, "{value}");
        }
    }
}
#[cfg(unix)]
#[test]
fn environment_values_that_are_not_unicode_are_present() {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let not_unicode = OsStr::from_bytes(b"\xff");
    let files = files("[default]\n");
    let env = |pairs: &[(&str, &OsStr)]| cli_core::SnapshotEnv::from_pairs(pairs.iter().copied());
    let args = ["s3", "ls", "s3://bucket/"];
    assert!(matches!(
        evaluate(&args, &env(&[]), &files),
        Verdict::Native(_)
    ));
    for (variable, reason) in [
        ("AWS_PROFILE", PythonReason::ProfileLookup),
        ("AWS_DEFAULT_PROFILE", PythonReason::ProfileLookup),
        ("AWS_RETRY_MODE", PythonReason::RetrySetting),
        ("AWS_MAX_ATTEMPTS", PythonReason::RetrySetting),
        (
            "AWS_REQUEST_CHECKSUM_CALCULATION",
            PythonReason::TransferSetting,
        ),
        (
            "AWS_RESPONSE_CHECKSUM_VALIDATION",
            PythonReason::TransferSetting,
        ),
    ] {
        assert_eq!(
            evaluate(&args, &env(&[(variable, not_unicode)]), &files),
            Verdict::Python(reason),
            "{variable}"
        );
    }
    let shadowed = env(&[
        ("AWS_PROFILE", not_unicode),
        ("AWS_DEFAULT_PROFILE", OsStr::new("default")),
    ]);
    assert_eq!(
        evaluate(&args, &shadowed, &files),
        Verdict::Python(PythonReason::ProfileLookup)
    );
}
#[test]
fn configured_fallback_preserves_original_argv() {
    let argv = ["s3", "cp", "--recursive", "local", "s3://bucket/prefix"].map(str::to_owned);
    let original = argv.clone();
    let mut parsed = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    assert_eq!(
        route(
            &mut parsed,
            &unpack::Environment {
                directory: Path::new("."),
                variables: &HashMap::new(),
                files: &unpack::FsParamfiles,
                preferred_encoding: unpack::PreferredEncoding::Locale,
            },
            &Configuration {
                env: &BTreeMap::new(),
                shared_files: &files("[default]\ncli_history = enabled\n"),
                boto_config_credentials: false,
                embedded_trust: true,
            }
        ),
        Verdict::Python(PythonReason::HistoryEnabled)
    );
    assert_eq!(argv, original);
}
#[test]
fn global_surface_is_classified_at_each_position() {
    for argument in tables::GLOBALS {
        if argument.action == awscli_argparse::Action::Version {
            continue;
        }
        if [
            "debug",
            "endpoint-url",
            "profile",
            "region",
            "no-paginate",
            "output",
            "cli-error-format",
            "query",
            "color",
            "no-cli-pager",
            "no-sign-request",
            "cli-connect-timeout",
        ]
        .contains(&argument.name)
        {
            continue;
        }
        let flag = format!("--{}", argument.name);
        let value = match argument.name {
            "color" => "on",
            "cli-binary-format" => "base64",
            "cli-read-timeout" | "cli-connect-timeout" => "5",
            _ => "value",
        };
        for position in 0..3 {
            let mut args = vec!["s3", "ls"];
            args.insert(position, &flag);
            if argument.action == awscli_argparse::Action::Store {
                args.insert(position + 1, value);
            }
            let reason = if argument.name == "help" {
                PythonReason::HelpRequested
            } else {
                PythonReason::PythonOnlyGlobal
            };
            expect(&args, Expected::Python(reason));
        }
    }
    for format in ["json", "text", "table", "yaml", "yaml-stream", "off"] {
        expect(&["s3", "ls", "--output", format], Expected::Native(false));
    }
}
#[test]
fn parameter_files_load_before_option_and_operand_admission() {
    #[derive(Debug)]
    struct Files;
    impl unpack::Paramfiles for Files {
        fn kind(&self, path: &Path) -> std::io::Result<unpack::FileKind> {
            Ok(if path.file_name() == Some("device".as_ref()) {
                unpack::FileKind::Stream
            } else {
                unpack::FileKind::File
            })
        }
        fn read(&self, path: &Path, _: usize) -> std::io::Result<Vec<u8>> {
            Ok(match path.file_name().and_then(|s| s.to_str()) {
                Some("ten") => b"1_0\n".to_vec(),
                // Not `nul`, which Windows reserves for its null device.
                Some("nul-byte") => b"s3://b/p\0q".to_vec(),
                Some("map") => b"a=b\n".to_vec(),
                Some("target") => b"s3://b/p".to_vec(),
                _ => b"abc".to_vec(),
            })
        }
    }
    for (argv, expected) in [
        (
            &["s3", "ls", "--page-size", "file://ten"][..],
            Expected::Native(false),
        ),
        (&["s3", "ls", "file://target"], Expected::Native(false)),
        (
            &["s3", "rm", "file://target", "--dryrun"],
            Expected::Native(false),
        ),
        (
            &["s3", "rm", "file://nul-byte"],
            Expected::Python(PythonReason::UnsupportedOperand),
        ),
        (
            &["s3", "ls", "file://nul-byte"],
            Expected::Python(PythonReason::UnsupportedOperand),
        ),
        (
            &["s3", "ls", "--page-size", "file://device", "--bogus"],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "ls", "--page-size", "fileb://ten"],
            Expected::Python(PythonReason::UnsupportedValue),
        ),
        (
            &["s3", "cp", "a", "s3://b/k", "--metadata", "file://map"],
            Expected::Native(true),
        ),
        (
            &[
                "s3",
                "cp",
                "a",
                "s3://b/k",
                "--sse-c",
                "--sse-c-key",
                "fileb://key",
            ],
            Expected::Native(true),
        ),
        (
            &["s3", "ls", "--page-size", "file://abc", "--bogus"],
            Expected::Failure("invalid_integer"),
        ),
    ] {
        expect_with_paramfiles(&Files, argv, expected);
    }
}
fn expect_with_paramfiles(paramfiles: &dyn unpack::Paramfiles, argv: &[&str], expected: Expected) {
    let argv = argv.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>();
    let mut parsed = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    let verdict = route(
        &mut parsed,
        &unpack::Environment {
            directory: Path::new("."),
            variables: &HashMap::new(),
            files: paramfiles,
            preferred_encoding: unpack::PreferredEncoding::Locale,
        },
        &Configuration {
            env: &BTreeMap::new(),
            shared_files: &files(""),
            boto_config_credentials: false,
            embedded_trust: true,
        },
    );
    match expected {
        Expected::Native(_) => assert!(matches!(verdict, Verdict::Native(_))),
        Expected::Python(reason) => assert_eq!(verdict, Verdict::Python(reason)),
        Expected::Failure(kind) => {
            let Verdict::Failure(failure) = verdict else {
                panic!()
            };
            assert_eq!(failure.kind, kind);
        }
    }
}
#[test]
fn operand_admission_follows_prior_argv_failures() {
    for argv in [
        &["s3", "cp", "s3://a/k", "s3://b/k"][..],
        &["s3", "cp", "a", "b"],
        &["s3", "cp", "-", "s3://b/k"],
        &[
            "s3",
            "ls",
            "arn:aws:s3:us-east-1:123456789012:accesspoint/example",
        ],
        &["s3", "ls", "s3://example.mrap/p"],
        &["s3", "ls", "bucket name"],
    ] {
        expect(argv, Expected::Python(PythonReason::UnsupportedOperand));
        let mut unknown = argv.to_vec();
        unknown.push("--bogus");
        expect(&unknown, Expected::Failure("unknown_options"));
    }
}
#[test]
fn configured_fallback_runs_after_all_argv_rules() {
    let config = files("[default]\ncli_history = enabled\n");
    let env = BTreeMap::new();
    for argv in [
        &["s3", "ls", "--bogus"][..],
        &["s3"],
        &["s3", "ls", "--page-size", "abc"],
        &["s3", "ls", "--output", "bogus"],
        &["s3", "ls", "file://missing"],
    ] {
        assert!(
            matches!(evaluate(argv, &env, &config), Verdict::Failure(_)),
            "{argv:?}"
        );
    }
    for (argv, reason) in [
        (
            &["s3", "mb", "s3://b"][..],
            PythonReason::UnsupportedSubcommand,
        ),
        (
            &["ec2", "describe-instances"],
            PythonReason::UnsupportedCommand,
        ),
        (
            &["--no-sign-request", "s3", "ls"],
            PythonReason::HistoryEnabled,
        ),
        (&["--color", "on", "s3", "ls"], PythonReason::HistoryEnabled),
        (
            &["s3", "cp", "--metadata-directive", "COPY", "a", "s3://b/k"],
            PythonReason::UnsupportedOption,
        ),
        (
            &["s3", "ls", "--page-size", "0"],
            PythonReason::UnsupportedValue,
        ),
        (
            &["s3", "cp", "s3://a/k", "s3://b/k"],
            PythonReason::UnsupportedOperand,
        ),
    ] {
        assert_eq!(evaluate(argv, &env, &config), Verdict::Python(reason));
    }
}
#[test]
fn configuration_value_matches_and_command_scopes() {
    let cases = [
        ("cli_history = Enabled", false, None),
        (
            "cli_history = enabled",
            false,
            Some(PythonReason::HistoryEnabled),
        ),
        ("s3 =\n  preferred_transfer_client = crt", true, None),
        ("s3 =\n  preferred_transfer_client = auto", true, None),
        ("s3 =\n  preferred_transfer_client = default", true, None),
        ("s3 =\n  preferred_transfer_client = default", false, None),
        ("s3 =\n  multipart_threshold = 64MB", true, None),
        ("s3 =\n  multipart_threshold = 64MB", false, None),
    ];
    for (text, cp, expected) in cases {
        assert_eq!(
            effective_config::admit(&effective_config::Inputs {
                env: &BTreeMap::new(),
                shared_files: &files(&format!("[default]\n{text}\n")),
                cli_profile: None,
                cli_error_format: None,
                transfers: cp,
                boto_config_credentials: false,
            }),
            expected
        );
    }
}
#[test]
fn merged_credentials_and_malformed_files_define_effective_settings() {
    let config = b"[profile work]\nregion = us-west-2\n";
    for (credentials, expected) in [
        (
            &b"[work]\nrole_arn = arn:aws:iam::1:role/r\n"[..],
            PythonReason::CredentialForm,
        ),
        (&b"no section header\n"[..], PythonReason::ProfileLookup),
    ] {
        let files = ParsedFiles::parse(awscli_config::Inputs {
            config: Some(awscli_config::Contents {
                source: "config",
                bytes: config,
            }),
            credentials: Some(awscli_config::Contents {
                source: "credentials",
                bytes: credentials,
            }),
            ..Default::default()
        });
        assert_eq!(
            effective_config::admit(&effective_config::Inputs {
                env: &BTreeMap::new(),
                shared_files: &files,
                cli_profile: Some("work"),
                cli_error_format: None,
                transfers: true,
                boto_config_credentials: false,
            }),
            Some(expected)
        );
        assert_eq!(
            effective_config::admit(&effective_config::Inputs {
                env: &BTreeMap::new(),
                shared_files: &files,
                cli_profile: None,
                cli_error_format: None,
                transfers: true,
                boto_config_credentials: false,
            }),
            None
        );
    }
}
#[test]
fn unsupported_rows_carry_configuration_reasons() {
    for setting in effective_config::SETTINGS {
        if let effective_config::Support::Unsupported(reason) = setting.support {
            assert!(matches!(
                reason,
                PythonReason::CredentialForm
                    | PythonReason::SharedFilePath
                    | PythonReason::RetrySetting
                    | PythonReason::NetworkSetting
                    | PythonReason::EndpointSetting
                    | PythonReason::TransferSetting
                    | PythonReason::HistoryEnabled
                    | PythonReason::StructuredErrorFormat
                    | PythonReason::OutputEncoding
            ));
        }
    }
}

#[test]
fn exact_failure_text_0() {
    for (argv, expected) in [
    (&[
"ec2",
"describe-instances",
"--profile"
][..], &[
"argument --profile: expected one argument\n\nusage: aws [--profile PROFILE] [--debug]\n"
].concat()),
    (&[
"s3",
"sycn"
][..], &[
"argument subcommand: Found invalid choice 'sycn'\n\n\nusage: ",
tables::USAGE
].concat()),
    (&[
"--output",
"jsn",
"s3",
"ls"
][..], &[
"argument --output: Found invalid choice 'jsn'\n\nMaybe you meant:\n\n  * json",
"\n\nusage: ",
tables::USAGE
].concat()),
    (&[
"--region",
"--endpoint-url",
"s3",
"ls"
][..], &[
"argument --region: expected one argument\n\nusage: ",
tables::USAGE
].concat()),
    (&[
"--bogus",
"s3",
"ls"
][..], &[
"Unknown options: --bogus"
].concat()),
    (&[
"s3",
"--bogus",
"ls"
][..], &[
"Unknown options: --bogus"
].concat()),
    (&[
"s3",
"ls",
"--bogus"
][..], &[
"Unknown options: --bogus"
].concat()),
    ] {
        let Verdict::Failure(failure) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!()
        };
        assert_eq!(failure.error_text(Default::default()), *expected, "{argv:?}");
    }
}

#[test]
fn exact_failure_text_1() {
    for (argv, expected) in [
        (
            &["s3", "--bogus"][..],
            &["Unknown options: --bogus"].concat(),
        ),
        (&["s3", "-h"][..], &["Unknown options: -h"].concat()),
        (&["s3", "ls", "-h"][..], &["Unknown options: -h"].concat()),
        (
            &["s3", "ls", "s3://bucket", "-h"][..],
            &["Unknown options: -h"].concat(),
        ),
    ] {
        let Verdict::Failure(failure) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!()
        };
        assert_eq!(
            failure.error_text(Default::default()),
            *expected,
            "{argv:?}"
        );
    }
}

#[test]
fn exact_failure_text_2() {
    for (argv, expected) in [
        (
            &["s3", "cp", "./a", "./b", "./c"][..],
            &["Unknown options: ./c"].concat(),
        ),
        (
            &["s3", "ls", "a", "b"][..],
            &["Unknown options: b"].concat(),
        ),
        (
            &["s3", "cp", "./a", "./b", "--", "--recursive"][..],
            &[
                "Unknown options: --recursive\n\nMaybe you meant:\n",
                "  * --recursive (instead of --recursive)",
            ]
            .concat(),
        ),
        (
            &["s3", "ls", "help", "--bogus"][..],
            &["Unknown options: --bogus"].concat(),
        ),
        (
            &["s3", "ls", "--sse", "aws:kms"][..],
            &["Unknown options: --sse"].concat(),
        ),
        (
            &["s3", "cp", "--download-writer", "mmap", "a", "b"][..],
            &["Unknown options: --download-writer, b"].concat(),
        ),
        (
            &["s3", "cp", "--io-workers", "4", "a", "b"][..],
            &["Unknown options: --io-workers, b"].concat(),
        ),
    ] {
        let Verdict::Failure(failure) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!()
        };
        assert_eq!(
            failure.error_text(Default::default()),
            *expected,
            "{argv:?}"
        );
    }
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "literal source diagnostics retain their complete context"
)]
fn exact_failure_text_3() {
    for (argv, expected) in [
    (&[
"s3",
"cp",
"s3://one/key",
"s3://two/key",
"-h"
][..], &[
"Unknown options: -h"
].concat()),
    (&[
"s3",
"cp",
"-",
"s3://bucket/key",
"-h"
][..], &[
"Unknown options: -h"
].concat()),
    (&[
"s3",
"cp",
"--metadata",
"a==b",
"./a",
"s3://b/k",
"--bogus"
][..], &[
"Error parsing parameter '--metadata': Expected: ',', received: '=' for input:\n",
" a==b\n  ^"
].concat()),
    (&[
"s3",
"cp",
"--metadata",
"[1]",
"./a",
"s3://b/k",
"--bogus"
][..], &[
"Error parsing parameter '--metadata': Invalid JSON:\n[1]"
].concat()),
    (&[
"s3",
"cp",
"--metadata",
"{bad",
"./a",
"s3://b/k",
"--bogus"
][..], &[
"Error parsing parameter '--metadata': Invalid JSON: syntax error: line 1 column 2 ",
"(byte 1)\nJSON received: {bad"
].concat()),
    (&[
"s3",
"cp",
"--metadata",
"{\"x\": 1}",
"./a",
"s3://b/k",
"--bogus"
][..], &[
"Parameter validation failed:\nInvalid type for parameter x, value: 1, ",
"type: <class 'int'>, valid types: <class 'str'>"
].concat()),
    (&[
"s3",
"cp",
"--sse-c-key",
"fileb://missing",
"./a",
"s3://b/k",
"--bogus"
][..], &[
"Error parsing parameter '--sse-c-key': Unable to load paramfile fileb://missing: ",
"[Errno 2] No such file or directory: 'missing'"
].concat()),
    ] {
        let Verdict::Failure(failure) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!()
        };
        assert_eq!(failure.error_text(Default::default()), *expected, "{argv:?}");
    }
}

#[test]
fn exact_failure_text_4() {
    for (argv, expected) in [
        (
            &["s3", "ls", "--page-size", "abc"][..],
            &["invalid literal for int() with base 10: 'abc'"].concat(),
        ),
        (
            &["s3", "ls", "--page-size", "abc", "--bogus"][..],
            &["invalid literal for int() with base 10: 'abc'"].concat(),
        ),
        (
            &["s3", "cp", "--page-size=", "a", "b"][..],
            &["invalid literal for int() with base 10: ''"].concat(),
        ),
        (
            &["s3", "ls", "file://missingfile"][..],
            &[
                "Error parsing parameter 'paths': Unable to load paramfile file://missingfile: ",
                "[Errno 2] No such file or directory: 'missingfile'",
            ]
            .concat(),
        ),
        (
            &["s3", "ls", "--page-size", "file://size", "--bogus"][..],
            &[
                "Error parsing parameter '--page-size': Unable to load paramfile file://size: ",
                "[Errno 2] No such file or directory: 'size'",
            ]
            .concat(),
        ),
        (
            &["s3", "cp", "fileb://key", "s3://bucket/key", "--bogus"][..],
            &["Unknown options: --bogus"].concat(),
        ),
    ] {
        let Verdict::Failure(failure) = evaluate(argv, &BTreeMap::new(), &files("")) else {
            panic!()
        };
        assert_eq!(
            failure.error_text(Default::default()),
            *expected,
            "{argv:?}"
        );
    }
}
#[test]
fn absent_settings_admit_both_commands_and_explicit_default_must_exist() {
    let config = files("[profile work]\nregion = us-west-2\n");
    let env = BTreeMap::new();
    for argv in [&["s3", "ls"][..], &["s3", "cp", "a", "s3://b/k"]] {
        assert!(matches!(evaluate(argv, &env, &config), Verdict::Native(_)));
        let mut named = vec!["--profile", "default"];
        named.extend_from_slice(argv);
        assert_eq!(
            evaluate(&named, &env, &config),
            Verdict::Python(PythonReason::ProfileLookup)
        );
    }
}
#[test]
fn endpoint_urls_only_python_reports_as_botocore_does_route_before_execution() {
    for (url, native) in [
        ("http://127.0.0.1:9", true),
        ("https://127.0.0.1:9/base", true),
        ("http:x://127.0.0.1:9/p", false),
        ("ftp://127.0.0.1:1", false),
        ("https://127.0.0.1:9/?a=b", false),
        ("HTTPS://127.0.0.1:9", false),
    ] {
        let config = files(&format!("[profile url]\nendpoint_url = {url}\n"));
        let variable = BTreeMap::from([("AWS_ENDPOINT_URL_S3".to_owned(), url.to_owned())]);
        for argv in [&["s3", "ls"][..], &["s3", "cp", "a", "s3://b/k"]] {
            let flag = [argv, &["--endpoint-url", url][..]].concat();
            let profile = [argv, &["--profile", "url"][..]].concat();
            for actual in [
                evaluate(&flag, &BTreeMap::new(), &files("")),
                evaluate(argv, &variable, &files("")),
                evaluate(&profile, &BTreeMap::new(), &config),
            ] {
                if native {
                    assert!(matches!(actual, Verdict::Native(_)), "{url}: {actual:?}");
                } else {
                    assert_eq!(
                        actual,
                        Verdict::Python(PythonReason::EndpointSetting),
                        "{url} {argv:?}"
                    );
                }
            }
        }
    }
}

fn evaluate_locked(
    args: &[&str],
    files: &ParsedFiles,
    platform: cli_core::client_config::Platform,
    acquire_process_lock: impl FnOnce() -> bool,
) -> Verdict {
    let argv = args.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>();
    let mut result = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    route_with_process_lock(
        &mut result,
        &unpack::Environment {
            directory: Path::new("."),
            variables: &HashMap::new(),
            files: &unpack::FsParamfiles,
            preferred_encoding: unpack::PreferredEncoding::Locale,
        },
        &Configuration {
            env: &BTreeMap::new(),
            shared_files: files,
            boto_config_credentials: false,
            embedded_trust: true,
        },
        || platform,
        acquire_process_lock,
    )
}

#[track_caller]
fn assert_native_command(verdict: &Verdict, cp: bool) {
    let Verdict::Native(native) = verdict else {
        panic!("{verdict:?}")
    };
    assert_eq!(matches!(native.command, Command::S3Cp(_)), cp);
}

#[test]
fn a_crt_process_lock_another_cli_holds_sends_cp_s_auto_personas_to_python() {
    let config = files(concat!(
        "[profile crt]\ns3 =\n  preferred_transfer_client = crt\n",
        "[profile limited]\ns3 =\n  max_bandwidth = 1MB/s\n",
    ));
    let tuned = cli_core::client_config::Platform {
        optimized: true,
        recommended_gbps: Some(100.0),
    };
    let held = |args: &[&str], platform| evaluate_locked(args, &config, platform, || false);
    let running = Verdict::Python(PythonReason::CrtClientRunning);
    for platform in [cli_core::client_config::Platform::default(), tuned] {
        for argv in [
            &["s3", "cp", "a", "s3://b/k"][..],
            &["s3", "cp", "s3://b/k", "a"],
            &["s3", "cp", "s3://b/p", "a", "--recursive"],
        ] {
            assert_eq!(held(argv, platform), running, "{argv:?}");
        }
        let preferred = ["--profile", "crt", "s3", "cp", "a", "s3://b/k"];
        assert_native_command(&held(&preferred, platform), true);
        assert_native_command(&held(&["s3", "ls"], platform), false);
    }
    let limited = ["--profile", "limited", "s3", "cp", "a", "s3://b/k"];
    assert_eq!(
        held(&limited, cli_core::client_config::Platform::default()),
        Verdict::Python(PythonReason::TransferSetting)
    );
    assert_eq!(held(&limited, tuned), running);
    let uncontended = evaluate(&["s3", "cp", "a", "s3://b/k"], &BTreeMap::new(), &config);
    assert_native_command(&uncontended, true);
}

#[test]
fn only_a_transfer_the_native_crt_client_runs_takes_the_crt_process_lock() {
    let config = files(concat!(
        "[profile crt]\ns3 =\n  preferred_transfer_client = crt\n",
        "[profile classic]\ns3 =\n  preferred_transfer_client = classic\n",
    ));
    let acquisitions = std::cell::Cell::new(0);
    let counted = |args: &[&str]| {
        let platform = cli_core::client_config::Platform::default();
        evaluate_locked(args, &config, platform, || {
            acquisitions.set(acquisitions.get() + 1);
            true
        })
    };
    assert_native_command(&counted(&["s3", "ls"]), false);
    for (argv, reason) in [
        (
            &["--profile", "classic", "s3", "cp", "a", "s3://b/k"][..],
            PythonReason::TransferSetting,
        ),
        (
            &["s3", "cp", "s3://b/k", "s3://c/k"],
            PythonReason::UnsupportedOperand,
        ),
        (&["s3", "mb", "s3://b"], PythonReason::UnsupportedSubcommand),
    ] {
        assert_eq!(counted(argv), Verdict::Python(reason), "{argv:?}");
    }
    assert_eq!(acquisitions.get(), 0);
    assert_native_command(&counted(&["s3", "cp", "a", "s3://b/k"]), true);
    assert_eq!(acquisitions.get(), 1);
    let preferred = ["--profile", "crt", "s3", "cp", "a", "s3://b/k"];
    assert_native_command(&counted(&preferred), true);
    assert_eq!(acquisitions.get(), 2);
    assert_native_command(&counted(&["s3", "sync", "a", "s3://b"]), false);
    assert_eq!(acquisitions.get(), 3);
}

mod credentials;
mod endpoint;
mod session;
mod target;
