#![expect(
    clippy::unwrap_used,
    reason = "fixture output is infallible and valid UTF-8"
)]
#![expect(
    clippy::panic,
    reason = "unexpected fixture outcomes must fail the test"
)]
use super::*;
use crate::SnapshotEnv;
use awscli_argparse::failure::{FailureKind, ParseFailureKind};
use awscli_argparse::tables::CommandKind;
use awscli_argparse::{Options, chain::Outcome, tables, unpack};

fn inputs(config: &str) -> ParsedFiles {
    ParsedFiles::parse(awscli_config::Inputs {
        config: Some(awscli_config::Contents {
            source: "config",
            bytes: config.as_bytes(),
        }),
        ..Default::default()
    })
}
fn parse(args: &[&str]) -> (Vec<std::ffi::OsString>, ParseResult) {
    let argv = args.iter().map(|v| (*v).to_owned()).collect::<Vec<_>>();
    let result = awscli_argparse::parse(&argv, &Options::default(), &tables::TABLES_DEFAULT);
    (argv.into_iter().map(Into::into).collect(), result)
}
fn class_failure(class: FailureClass) -> Failure {
    let tokens = vec!["--bogus".into()];
    Failure::new(match class {
        FailureClass::ParamValidation => FailureKind::UnknownOptions {
            tokens,
            kind: CommandKind::Basic,
            suggestions: vec![],
        },
        FailureClass::UnknownArgument => FailureKind::UnknownOptions {
            tokens,
            kind: CommandKind::Operation,
            suggestions: vec![],
        },
        FailureClass::General => FailureKind::InvalidInteger("abc".into()),
    })
}
fn formatted(failure: &CommandFailure, format: ErrorFormat) -> String {
    let mut output = Vec::new();
    render_command_failure(&mut output, failure, format).unwrap();
    String::from_utf8(output).unwrap()
}
fn test_dispose(files: &ParsedFiles, env: &SnapshotEnv, args: &[&str]) -> Disposition {
    let (argv, mut result) = parse(args);
    if result.outcome == Outcome::Parsed {
        let variables = std::collections::HashMap::new();
        let deferred = awscli_argparse::complete(
            &mut result,
            &unpack::Environment {
                directory: std::path::Path::new("."),
                variables: &variables,
                files: &unpack::FsParamfiles,
                preferred_encoding: unpack::PreferredEncoding::Locale,
            },
        );
        assert!(!deferred, "{args:?} deferred a value to Python");
    }
    let Outcome::Failure(failure) = &result.outcome else {
        panic!("{args:?} did not fail: {:?}", result.outcome)
    };
    let environment = Environment {
        argv: &argv,
        env,
        stdout_is_tty: false,
        shared_files: files,
    };
    dispose_failure(&environment, &result, failure)
}
fn expect_format(expected: ErrorFormat, files: &ParsedFiles, env: &SnapshotEnv, args: &[&str]) {
    match test_dispose(files, env, args) {
        Disposition::Render(rendering) => assert_eq!(rendering.format, expected, "{args:?}"),
        Disposition::Python(reason) => panic!("{args:?} went to Python: {reason:?}"),
    }
}
fn expect_python(expected: PythonReason, files: &ParsedFiles, env: &SnapshotEnv, args: &[&str]) {
    assert_eq!(
        test_dispose(files, env, args),
        Disposition::Python(expected),
        "{args:?}"
    );
}
#[test]
fn exit_statuses_follow_the_handler_chain() {
    for (category, status) in [
        (Category::ParamValidation, 252),
        (Category::Configuration, 253),
        (Category::NoCredentials, 253),
        (Category::ClientError, 254),
        (Category::General, 255),
        (Category::Interrupt, 130),
    ] {
        assert_eq!(exit_status(category), status);
    }
    for (class, status) in [
        (FailureClass::ParamValidation, 252),
        (FailureClass::UnknownArgument, 252),
        (FailureClass::General, 255),
    ] {
        assert_eq!(exit_status(Category::from_class(class)), status);
        assert_eq!(class_failure(class).class, class);
    }
}

#[test]
fn output_encoding_presence_hands_every_failure_stage_to_python() {
    let files = inputs("");
    let stages: &[&[&str]] = &[
        &["s3", "ls", "--profile"],
        &["--output", "bogus"],
        &["s3", "ls", "--bogus"],
    ];
    for encoding in ["", "utf-16"] {
        let env = SnapshotEnv::from_pairs([("AWS_CLI_OUTPUT_ENCODING", encoding)]);
        for args in stages {
            let (argv, result) = parse(args);
            let failure = class_failure(FailureClass::ParamValidation);
            assert_eq!(
                dispose_failure(
                    &Environment {
                        argv: &argv,
                        env: &env,
                        shared_files: &files,
                        stdout_is_tty: false
                    },
                    &result,
                    &failure
                ),
                Disposition::Python(PythonReason::OutputEncoding)
            );
        }
    }
    let env = SnapshotEnv::from_pairs([("PYTHONUTF8", "1")]);
    let (argv, result) = parse(stages[0]);
    assert!(matches!(
        dispose_failure(
            &Environment {
                argv: &argv,
                env: &env,
                shared_files: &files,
                stdout_is_tty: false
            },
            &result,
            &class_failure(FailureClass::ParamValidation)
        ),
        Disposition::Render(_)
    ));
}

#[test]
fn history_records_only_after_the_session_event_and_after_auto_prompt() {
    let files =
        inputs("[default]\ncli_history = enabled\n[profile quiet]\ncli_history = Enabled\n");
    for (args, reason) in [
        (
            &["s3", "ls", "--bogus"][..],
            Some(PythonReason::HistoryEnabled),
        ),
        (
            &["s3", "ls", "--page-size", "abc"],
            Some(PythonReason::HistoryEnabled),
        ),
        (
            &["s3", "cp", "a", "b", "c"],
            Some(PythonReason::HistoryEnabled),
        ),
        (&["--output", "bogus"], None),
        (&["s3", "ls", "--profile"], None),
        (&["s3", "--endpoint-url", "nope"], None),
        (&["--profile", "quiet", "s3", "ls", "--bogus"], None),
        (
            &["--profile", "missing", "s3", "ls", "--bogus"],
            Some(PythonReason::ProfileLookup),
        ),
    ] {
        let (argv, result) = parse(args);
        let failure = class_failure(FailureClass::ParamValidation);
        let env = SnapshotEnv::default();
        let disposition = dispose_failure(
            &Environment {
                argv: &argv,
                env: &env,
                shared_files: &files,
                stdout_is_tty: false,
            },
            &result,
            &failure,
        );
        assert_eq!(
            match disposition {
                Disposition::Python(reason) => Some(reason),
                Disposition::Render(_) => None,
            },
            reason,
            "{args:?}"
        );
    }
    let env = SnapshotEnv::from_pairs([("AWS_CLI_AUTO_PROMPT", "on")]);
    let (argv, result) = parse(&["s3", "ls", "--bogus"]);
    assert_eq!(
        dispose_failure(
            &Environment {
                argv: &argv,
                env: &env,
                shared_files: &files,
                stdout_is_tty: false
            },
            &result,
            &class_failure(FailureClass::ParamValidation)
        ),
        Disposition::Python(PythonReason::AutoPrompt)
    );
}
#[test]
fn history_follows_the_profile_the_environment_selects() {
    let named = inputs("[default]\n[profile on]\ncli_history = enabled\n");
    let env = SnapshotEnv::default();
    expect_format(
        ErrorFormat::Enhanced,
        &named,
        &env,
        &["s3", "ls", "--bogus"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_PROFILE", "on")]);
    expect_python(
        PythonReason::HistoryEnabled,
        &named,
        &env,
        &["s3", "ls", "--bogus"],
    );
}
#[test]
fn command_failures_frame_as_their_handlers_do() {
    for (category, code) in [
        (Category::ParamValidation, "ParamValidation"),
        (Category::Configuration, "Configuration"),
        (Category::NoCredentials, "NoCredentials"),
    ] {
        let failure = CommandFailure {
            message: " message \n".into(),
            ..CommandFailure::new(category)
        };
        let suffix = if category == Category::NoCredentials {
            ". You can configure credentials by running \"aws login\"."
        } else {
            ""
        };
        assert_eq!(
            formatted(&failure, ErrorFormat::Enhanced),
            format!(
                "\naws: [ERROR]: {}\n",
                trim(&format!("An error occurred ({code}):  message \n{suffix}"))
            )
        );
        assert_eq!(
            formatted(&failure, ErrorFormat::Legacy),
            format!(
                "\naws: [ERROR]: {}\n",
                trim(&format!(" message \n{suffix}"))
            )
        );
    }
    let service = CommandFailure {
        code: "NoSuchBucket".into(),
        operation: "ListObjectsV2".into(),
        message: "The specified bucket does not exist".into(),
        ..CommandFailure::new(Category::ClientError)
    };
    for format in [ErrorFormat::Enhanced, ErrorFormat::Legacy] {
        assert_eq!(
            formatted(&service, format),
            concat!(
                "\naws: [ERROR]: An error occurred ",
                "(NoSuchBucket) when calling the ListObjectsV2 operation: ",
                "The specified bucket does not exist\n"
            )
        );
    }
    let exhausted = CommandFailure {
        code: "500".into(),
        message: "Internal Server Error".into(),
        operation: "ListBuckets".into(),
        http_status: 500,
        retries_exhausted: Some(2),
        ..CommandFailure::new(Category::ClientError)
    };
    assert_eq!(
        formatted(&exhausted, ErrorFormat::Legacy),
        concat!(
            "\naws: [ERROR]: An error occurred (500) when calling the ",
            "ListBuckets operation (reached max retries: 2): Internal Server Error\n"
        )
    );
}

#[test]
fn closed_stdout_uses_python_broken_pipe_framing() {
    let failure = CommandFailure {
        message: BROKEN_PIPE_MESSAGE.into(),
        ..CommandFailure::new(Category::General)
    };
    for format in [ErrorFormat::Enhanced, ErrorFormat::Legacy] {
        assert_eq!(
            formatted(&failure, format),
            "\naws: [ERROR]: [Errno 32] Broken pipe\n"
        );
    }
    assert_eq!(exit_status(failure.category), 255);
}
#[test]
fn owned_failure_outlives_its_source() {
    let mut source = "service response".to_owned();
    let failure = CommandFailure {
        message: source.as_bytes().to_vec(),
        crt_code: 14361,
        http_status: 404,
        crt_name: "AWS_ERROR_S3_INVALID_RESPONSE_STATUS".into(),
        ..CommandFailure::new(Category::General)
    };
    source.clear();
    assert_eq!(failure.message, b"service response");
    assert_eq!(failure.crt_code, 14361);
    assert_eq!(failure.http_status, 404);
    assert_eq!(
        formatted(&failure, ErrorFormat::Legacy),
        "\naws: [ERROR]: service response\n"
    );
}

#[test]
fn command_failure_rendering_preserves_non_unicode_message_bytes() -> io::Result<()> {
    let failure = CommandFailure {
        message: b" \t\x0b\x0c/tmp/non-unicode-\xff\r\n\x0b\x0c".to_vec(),
        ..CommandFailure::new(Category::General)
    };
    for format in [ErrorFormat::Enhanced, ErrorFormat::Legacy] {
        let mut output = Vec::new();
        render_command_failure(&mut output, &failure, format)?;
        assert_eq!(output, b"\naws: [ERROR]: /tmp/non-unicode-\xff\n");
    }
    let failure = CommandFailure {
        code: "NoSuchKey".into(),
        operation: "HeadObject".into(),
        message: b"key-\xff\n\x0b".to_vec(),
        ..CommandFailure::new(Category::ClientError)
    };
    let mut output = Vec::new();
    render_command_failure(&mut output, &failure, ErrorFormat::Enhanced)?;
    assert_eq!(
        output,
        b"\naws: [ERROR]: An error occurred (NoSuchKey) when calling \
        the HeadObject operation: key-\xff\n"
    );
    Ok(())
}
#[test]
fn general_failure_uses_a_fixed_writer() {
    for (message, expected) in [
        ("OutOfMemory", "\naws: [ERROR]: OutOfMemory\n"),
        (" \tOutOfMemory\r\n", "\naws: [ERROR]: OutOfMemory\n"),
        ("", "\naws: [ERROR]:\n"),
        (" \t\r\n\u{b}\u{c}", "\naws: [ERROR]:\n"),
    ] {
        for format in [ErrorFormat::Enhanced, ErrorFormat::Legacy] {
            let failure = CommandFailure {
                message: message.into(),
                ..CommandFailure::new(Category::General)
            };
            let mut buffer = [0u8; 64];
            let mut writer = io::Cursor::new(buffer.as_mut_slice());
            render_command_failure(&mut writer, &failure, format).unwrap();
            let written = writer.position() as usize;
            assert_eq!(&buffer[..written], expected.as_bytes());
        }
    }
}
fn framing_cases() -> Vec<(FailureKind, ErrorFormat, String)> {
    let parse = awscli_argparse::failure::ParseFailure {
        argument_name: Some("--profile".into()),
        kind: Box::new(ParseFailureKind::ExpectedOneArgument),
        usage: "aws [--profile PROFILE] [--debug]\n".into(),
        colored_usage: None,
    };
    let unknown = |kind| FailureKind::UnknownOptions {
        tokens: vec!["--a".into(), "b".into()],
        kind,
        suggestions: vec![],
    };
    vec![
        (
            FailureKind::Parse(Box::new(parse)),
            ErrorFormat::Enhanced,
            "\naws: [ERROR]: An error occurred (ParamValidation): argument --profile: expected \
             one argument\n\nusage: aws [--profile PROFILE] [--debug]\n"
                .to_owned(),
        ),
        (
            unknown(CommandKind::Basic),
            ErrorFormat::Enhanced,
            "\naws: [ERROR]: An error occurred (ParamValidation): Unknown options: --a, b\n".into(),
        ),
        (
            unknown(CommandKind::Basic),
            ErrorFormat::Legacy,
            "\naws: [ERROR]: Unknown options: --a, b\n".into(),
        ),
        (
            FailureKind::TooFewArguments(vec!["s3"]),
            ErrorFormat::Enhanced,
            "\naws: [ERROR]: An error occurred (ParamValidation): usage: aws [options] s3 \
             <subcommand> [parameters]\naws: [ERROR]: too few arguments\n"
                .into(),
        ),
        (
            FailureKind::InvalidInteger("abc".into()),
            ErrorFormat::Enhanced,
            "\naws: [ERROR]: invalid literal for int() with base 10: 'abc'\n".into(),
        ),
        (
            unknown(CommandKind::Operation),
            ErrorFormat::Enhanced,
            format!(
                "\nusage: {}\n\naws: [ERROR]: Unknown options: --a, b\n",
                tables::USAGE
            ),
        ),
        (
            FailureKind::ParamfileDecode {
                name: "paths".into(),
                path: "a.bin".into(),
            },
            ErrorFormat::Legacy,
            "\naws: [ERROR]: Error parsing parameter 'paths': Unable to load paramfile (a.bin), \
             text contents could not be decoded.  If this is a binary file, please use the \
             fileb:// prefix instead of the file:// prefix.\n"
                .into(),
        ),
    ]
}
#[test]
fn parser_framings_match_errorhandler_for_every_class() {
    for (kind, format, expected) in framing_cases() {
        let mut out = Vec::new();
        render(
            &mut out,
            &Failure::new(kind),
            Rendering {
                format,
                color: Color::default(),
            },
        )
        .unwrap();
        assert_eq!(String::from_utf8(out).unwrap(), expected);
    }
}
#[test]
fn parser_usage_and_color_survive_framing() {
    let (_, result) = parse(&["s3", "ls", "--profile"]);
    let Outcome::Failure(failure) = result.outcome else {
        panic!()
    };
    let mut out = Vec::new();
    render(
        &mut out,
        &failure,
        Rendering {
            format: ErrorFormat::Enhanced,
            color: Color::default(),
        },
    )
    .unwrap();
    assert_eq!(
        String::from_utf8(out).unwrap(),
        concat!(
            "\naws: [ERROR]: An error occurred (ParamValidation): ",
            "argument --profile: expected one argument\n\n",
            "usage: aws [--profile PROFILE] [--debug]\n"
        )
    );
    let mut out = Vec::new();
    render(
        &mut out,
        &failure,
        Rendering {
            format: ErrorFormat::Legacy,
            color: Color {
                stdout_is_tty: true,
                ..Default::default()
            },
        },
    )
    .unwrap();
    assert!(out.windows(5).any(|s| s == b"\x1b[1;3"));
}
#[test]
fn command_format_uses_flag_environment_profile_precedence() {
    let files = inputs("[default]\ncli_error_format = legacy\n");
    let (argv, result) = parse(&["s3", "ls"]);
    let mut vars = std::collections::BTreeMap::new();
    let environment = Environment {
        argv: &argv,
        env: &vars,
        stdout_is_tty: false,
        shared_files: &files,
    };
    assert_eq!(
        command_failure_format(&environment, &result),
        ErrorFormat::Legacy
    );
    vars.insert("AWS_CLI_ERROR_FORMAT".into(), "enhanced".into());
    let environment = Environment {
        argv: &argv,
        env: &vars,
        stdout_is_tty: false,
        shared_files: &files,
    };
    assert_eq!(
        command_failure_format(&environment, &result),
        ErrorFormat::Enhanced
    );
    let (_, flagged) = parse(&["s3", "ls", "--cli-error-format", "legacy"]);
    assert_eq!(
        command_failure_format(&environment, &flagged),
        ErrorFormat::Legacy
    );
}
#[test]
fn first_pass_ignores_ambient_format_and_auto_prompt() {
    let files = inputs("[default]\ncli_error_format = json\ncli_auto_prompt = on\n");
    let env = SnapshotEnv::from_pairs([("AWS_CLI_ERROR_FORMAT", "table")]);
    let (argv, result) = parse(&["ec2", "--profile"]);
    let Outcome::Failure(failure) = &result.outcome else {
        panic!()
    };
    let result = dispose_failure(
        &Environment {
            argv: &argv,
            env: &env,
            shared_files: &files,
            stdout_is_tty: false,
        },
        &result,
        failure,
    );
    assert!(matches!(
        result,
        Disposition::Render(Rendering {
            format: ErrorFormat::Enhanced,
            ..
        })
    ));
}
#[test]
fn format_resolution_observes_parser_stage() {
    let files = inputs(concat!(
        "[default]\ncli_error_format = legacy\n",
        "[profile structured]\ncli_error_format = json\n"
    ));
    let env = SnapshotEnv::default();
    let (argv, mut result) = parse(&["--profile", "structured", "s3", "ls"]);
    let environment = Environment {
        argv: &argv,
        env: &env,
        shared_files: &files,
        stdout_is_tty: false,
    };
    let failure = class_failure(FailureClass::ParamValidation);
    for stage in [Stage::Main, Stage::TopLevel] {
        result.stage = stage;
        assert!(matches!(
            dispose_failure(&environment, &result, &failure),
            Disposition::Render(Rendering {
                format: ErrorFormat::Legacy,
                ..
            })
        ));
    }
    for stage in [Stage::Probe, Stage::Table, Stage::Unpack, Stage::Leftover] {
        result.stage = stage;
        assert_eq!(
            dispose_failure(&environment, &result, &failure),
            Disposition::Python(PythonReason::StructuredErrorFormat)
        );
    }
}
#[test]
fn the_flag_applies_after_the_main_parse_then_the_profile() {
    let files = inputs(concat!(
        "[default]\ncli_error_format = LEGACY\n",
        "[profile structured]\ncli_error_format = json\n",
        "[profile plain]\ncli_error_format = bogus\n",
    ));
    let env = SnapshotEnv::default();
    expect_format(ErrorFormat::Legacy, &files, &env, &["s3"]);
    expect_format(ErrorFormat::Legacy, &files, &env, &["s3", "ls", "--bogus"]);
    expect_format(ErrorFormat::Legacy, &files, &env, &["--output", "bogus"]);
    expect_format(
        ErrorFormat::Enhanced,
        &files,
        &env,
        &["s3", "ls", "--cli-error-format", "enhanced", "--bogus"],
    );
    expect_format(
        ErrorFormat::Legacy,
        &files,
        &env,
        &["s3", "--cli-error-format", "enhanced", "--output", "bogus"],
    );
    expect_python(
        PythonReason::StructuredErrorFormat,
        &files,
        &env,
        &["s3", "ls", "--cli-error-format", "json", "--page-size"],
    );
    expect_python(
        PythonReason::StructuredErrorFormat,
        &files,
        &env,
        &["--profile", "structured", "s3", "ls", "--bogus"],
    );
    expect_format(
        ErrorFormat::Enhanced,
        &files,
        &env,
        &["--profile", "plain", "s3", "ls", "--bogus"],
    );
    expect_python(
        PythonReason::ProfileLookup,
        &files,
        &env,
        &["--profile", "missing", "s3", "ls", "--bogus"],
    );
    expect_format(
        ErrorFormat::Legacy,
        &files,
        &env,
        &["--profile", "structured", "s3", "--endpoint-url", "nope"],
    );
    expect_format(
        ErrorFormat::Legacy,
        &files,
        &env,
        &["--profile", "structured", "s3", "ls", "--page-size", "abc"],
    );
}
#[test]
fn the_environment_applies_before_the_profile() {
    let files = inputs(concat!(
        "[default]\ncli_error_format = LEGACY\n",
        "[profile structured]\ncli_error_format = json\n",
    ));
    let env = SnapshotEnv::from_pairs([("AWS_CLI_ERROR_FORMAT", "Enhanced")]);
    expect_format(
        ErrorFormat::Enhanced,
        &files,
        &env,
        &["s3", "ls", "--bogus"],
    );
    expect_format(
        ErrorFormat::Enhanced,
        &files,
        &env,
        &["--profile", "missing", "s3", "ls", "--bogus"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_CLI_ERROR_FORMAT", "yaml")]);
    expect_python(
        PythonReason::StructuredErrorFormat,
        &files,
        &env,
        &["s3", "ls", "--bogus"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_PROFILE", "structured")]);
    expect_python(
        PythonReason::StructuredErrorFormat,
        &files,
        &env,
        &["s3", "ls", "--bogus"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_PROFILE", "missing")]);
    expect_python(
        PythonReason::ProfileLookup,
        &files,
        &env,
        &["s3", "ls", "--bogus"],
    );
}
#[test]
fn unpack_and_leftover_resolve_the_session_profile() {
    let files = inputs("[default]\ncli_error_format = legacy\n");
    let env = SnapshotEnv::default();
    for profile in ["default", "missing"] {
        let (argv, mut result) = parse(&["--profile", profile, "s3", "ls"]);
        let environment = Environment {
            argv: &argv,
            env: &env,
            shared_files: &files,
            stdout_is_tty: false,
        };
        for stage in [Stage::Unpack, Stage::Leftover] {
            result.stage = stage;
            let disposition = dispose_failure(
                &environment,
                &result,
                &class_failure(FailureClass::ParamValidation),
            );
            if profile == "missing" {
                assert_eq!(
                    disposition,
                    Disposition::Python(PythonReason::ProfileLookup)
                );
            } else {
                assert!(matches!(
                    disposition,
                    Disposition::Render(Rendering {
                        format: ErrorFormat::Legacy,
                        ..
                    })
                ));
            }
        }
    }
}
#[test]
fn auto_prompt_failure_disposition_uses_exit_class() {
    let files = inputs("");
    for (mode, class, python) in [
        ("on", FailureClass::General, true),
        ("on", FailureClass::ParamValidation, true),
        ("on-partial", FailureClass::ParamValidation, true),
        ("on-partial", FailureClass::UnknownArgument, true),
        ("on-partial", FailureClass::General, false),
        ("off", FailureClass::ParamValidation, false),
    ] {
        let env = SnapshotEnv::from_pairs([("AWS_CLI_AUTO_PROMPT", mode)]);
        let (argv, result) = parse(&["s3", "ls"]);
        let failure = class_failure(class);
        let got = dispose_failure(
            &Environment {
                argv: &argv,
                env: &env,
                shared_files: &files,
                stdout_is_tty: false,
            },
            &result,
            &failure,
        );
        assert_eq!(
            matches!(got, Disposition::Python(PythonReason::AutoPrompt)),
            python
        );
    }
}
#[test]
fn auto_prompt_hands_failures_to_python() {
    let files =
        inputs("[default]\ncli_auto_prompt = on-partial\n[profile prompt]\ncli_auto_prompt = On\n");
    let env = SnapshotEnv::default();
    for args in [
        &["s3", "ls", "--bogus"][..],
        &["--output", "bogus"],
        &["s3", "ls", "file://missing"],
    ] {
        expect_python(PythonReason::AutoPrompt, &files, &env, args);
    }
    expect_format(
        ErrorFormat::Legacy,
        &files,
        &env,
        &["s3", "ls", "--page-size", "abc"],
    );
    expect_format(
        ErrorFormat::Enhanced,
        &files,
        &env,
        &["s3", "ls", "--no-cli-auto-prompt", "--page-size"],
    );
    expect_format(
        ErrorFormat::Enhanced,
        &files,
        &env,
        &["s3", "ls", "--bucket-region", "help", "--bogus"],
    );
    expect_format(
        ErrorFormat::Legacy,
        &files,
        &env,
        &["--debug", "s3", "ls", "--page-size", "abc"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_CLI_AUTO_PROMPT", "off")]);
    expect_format(
        ErrorFormat::Enhanced,
        &files,
        &env,
        &["s3", "ls", "--bogus"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_CLI_AUTO_PROMPT", "ON")]);
    expect_python(
        PythonReason::AutoPrompt,
        &files,
        &env,
        &["s3", "ls", "--page-size", "abc"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_PROFILE", "prompt")]);
    expect_python(
        PythonReason::AutoPrompt,
        &files,
        &env,
        &["s3", "ls", "--bogus"],
    );
    let env = SnapshotEnv::from_pairs([("AWS_PROFILE", "missing")]);
    expect_python(
        PythonReason::ProfileLookup,
        &files,
        &env,
        &["s3", "ls", "--bogus"],
    );
}
#[test]
fn a_native_invocation_runs_under_python_only_when_auto_prompt_is_on() {
    let files =
        inputs("[default]\ncli_auto_prompt = on-partial\n[profile prompt]\ncli_auto_prompt = on\n");
    let dispose = |env: &SnapshotEnv, args: &[&str]| {
        let (argv, _) = parse(args);
        dispose_native(&Environment {
            argv: &argv,
            env,
            stdout_is_tty: false,
            shared_files: &files,
        })
    };
    assert_eq!(dispose(&SnapshotEnv::default(), &["s3", "ls"]), None);
    let prompt = SnapshotEnv::from_pairs([("AWS_PROFILE", "prompt")]);
    assert_eq!(
        dispose(&prompt, &["s3", "ls"]),
        Some(PythonReason::AutoPrompt)
    );
    assert_eq!(dispose(&prompt, &["s3", "ls", "--version"]), None);
    let empty = SnapshotEnv::from_pairs([("AWS_PROFILE", "prompt"), ("AWS_CLI_AUTO_PROMPT", "")]);
    assert_eq!(dispose(&empty, &["s3", "ls"]), None);
}
#[test]
fn native_auto_prompt_uses_literal_argv_and_environment_profile() {
    let files = inputs("[default]\ncli_auto_prompt = on\n[profile off]\ncli_auto_prompt = off\n");
    let env = SnapshotEnv::default();
    for (argv, python) in [
        (&["s3", "ls"][..], true),
        (&["--profile", "off", "s3", "ls"], true),
        (&["s3", "ls", "help"], false),
        (&["--version"], false),
        (&["--no-cli-auto-prompt"], false),
        (&["--cli-auto-prompt", "--no-cli-auto-prompt"], false),
        (&["--profile", "help", "s3", "ls"], false),
    ] {
        let (argv, _) = parse(argv);
        assert_eq!(
            dispose_native(&Environment {
                argv: &argv,
                env: &env,
                shared_files: &files,
                stdout_is_tty: false
            })
            .is_some(),
            python
        );
    }
    let (argv, _) = parse(&["s3", "ls"]);
    let env = SnapshotEnv::from_pairs([("AWS_CLI_AUTO_PROMPT", "on-partial")]);
    assert_eq!(
        dispose_native(&Environment {
            argv: &argv,
            env: &env,
            shared_files: &files,
            stdout_is_tty: false
        }),
        None
    );
}
#[test]
fn color_inputs_use_stdout_and_color_variables() {
    let files = inputs("");
    let (argv, result) = parse(&["s3", "ls", "--profile"]);
    let Outcome::Failure(failure) = &result.outcome else {
        panic!()
    };
    for (name, no_color, force_color, term_dumb) in [
        ("NO_COLOR", true, false, false),
        ("FORCE_COLOR", false, true, false),
        ("TERM", false, false, true),
        ("PYTHON_COLORS", false, false, false),
    ] {
        let env = SnapshotEnv::from_pairs([(name, if name == "TERM" { "dumb" } else { "1" })]);
        let got = dispose_failure(
            &Environment {
                argv: &argv,
                env: &env,
                shared_files: &files,
                stdout_is_tty: true,
            },
            &result,
            failure,
        );
        let Disposition::Render(rendering) = got else {
            panic!()
        };
        assert_eq!(
            rendering.color,
            Color {
                stdout_is_tty: true,
                no_color,
                force_color,
                term_dumb
            }
        );
    }
}
#[cfg(unix)]
#[test]
fn environment_values_that_are_not_unicode_are_present() {
    use std::ffi::OsStr;
    use std::os::unix::ffi::OsStrExt;
    let not_unicode = OsStr::from_bytes(b"\xff");
    let files = inputs("[default]\ncli_error_format = legacy\ncli_auto_prompt = on\n");
    let (argv, result) = parse(&["s3", "ls", "--bogus"]);
    let failure = class_failure(FailureClass::ParamValidation);
    let dispose = |names: &[&str]| {
        let env = SnapshotEnv::from_pairs(names.iter().map(|&name| (name, not_unicode)));
        dispose_failure(
            &Environment {
                argv: &argv,
                env: &env,
                shared_files: &files,
                stdout_is_tty: false,
            },
            &result,
            &failure,
        )
    };
    let render = |format, color| Disposition::Render(Rendering { format, color });
    assert_eq!(dispose(&[]), Disposition::Python(PythonReason::AutoPrompt));
    assert_eq!(
        dispose(&["AWS_CLI_AUTO_PROMPT"]),
        render(ErrorFormat::Legacy, Color::default())
    );
    assert_eq!(
        dispose(&["AWS_CLI_AUTO_PROMPT", "AWS_CLI_ERROR_FORMAT"]),
        render(ErrorFormat::Enhanced, Color::default())
    );
    assert_eq!(
        dispose(&["AWS_CLI_OUTPUT_ENCODING"]),
        Disposition::Python(PythonReason::OutputEncoding)
    );
    for variable in ["AWS_PROFILE", "AWS_DEFAULT_PROFILE"] {
        assert_eq!(
            dispose(&[variable]),
            Disposition::Python(PythonReason::ProfileLookup)
        );
    }
    assert_eq!(
        dispose(&["AWS_CLI_AUTO_PROMPT", "FORCE_COLOR", "NO_COLOR"]),
        render(
            ErrorFormat::Legacy,
            Color {
                no_color: true,
                force_color: true,
                ..Color::default()
            }
        )
    );
}
