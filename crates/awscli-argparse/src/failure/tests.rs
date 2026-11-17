#![expect(clippy::unwrap_used, reason = "pinned corpus fixtures and assertions")]
use super::*;
#[test]
fn invalid_choices_list_difflib_suggestions_as_upstream_spells_them() {
    let failure = ParseFailure {
        argument_name: Some("--output".into()),
        kind: Box::new(ParseFailureKind::InvalidChoice {
            value: "bogus".into(),
            suggestions: vec![],
        }),
        usage: "aws\n".into(),
        colored_usage: None,
    };
    assert_eq!(
        failure.error_text(Color::default()),
        "argument --output: Found invalid choice 'bogus'\n\n\nusage: aws\n"
    );
    let failure = ParseFailure {
        kind: Box::new(ParseFailureKind::InvalidChoice {
            value: "jsn".into(),
            suggestions: vec!["json".into(), "yaml".into()],
        }),
        ..failure
    };
    assert_eq!(
        failure.error_text(Color::default()),
        "argument --output: Found invalid choice 'jsn'\n\nMaybe you meant:\n\n  * json\n  * \
    yaml\n\nusage: aws\n"
    );
}
#[test]
fn integer_failure_precision_and_handler_class() {
    for (text, error, prefix) in [
        (
            "abc".to_owned(),
            ParseIntError::InvalidLiteral,
            "invalid literal for int() with base 10: ",
        ),
        (
            "99999999999999999999".to_owned(),
            ParseIntError::OutOfRange,
            "integer outside the 64-bit range of the native command: ",
        ),
        (
            "x".repeat(250),
            ParseIntError::InvalidLiteral,
            "invalid literal for int() with base 10: ",
        ),
        (
            "1".repeat(250),
            ParseIntError::OutOfRange,
            "integer outside the 64-bit range of the native command: ",
        ),
    ] {
        let failure = Failure::integer(&text, error);
        assert_eq!(failure.class, FailureClass::General);
        assert_eq!(
            failure.error_text(Color::default()),
            format!("{prefix}{}", pyrepr::limited(&text, 200))
        );
    }
}
#[test]
fn integer_digit_limit_names_the_digit_count_not_the_literal() {
    let text = format!(" +{}5", "0_".repeat(4300));
    let failure = Failure::integer(&text, ParseIntError::DigitLimit(4301));
    assert_eq!(failure.kind, FailureKind::IntegerDigitLimit(4301));
    assert_eq!(failure.kind, "integer_digit_limit");
    assert_eq!(failure.class, FailureClass::General);
    assert_eq!(failure.parameter(), None);
    assert_eq!(
        failure.error_text(Color::default()),
        "Exceeds the limit (4300 digits) for integer string conversion: value has 4301 digits; \
         use sys.set_int_max_str_digits() to increase the limit"
    );
}
fn awscli_cases() -> Vec<(FailureKind, FailureClass, String)> {
    let parse = ParseFailure {
        argument_name: Some("--profile".into()),
        kind: Box::new(ParseFailureKind::ExpectedOneArgument),
        usage: "aws [--profile PROFILE] [--debug]".into(),
        colored_usage: None,
    };
    vec![
        (
            FailureKind::Parse(Box::new(parse)),
            FailureClass::ParamValidation,
            "argument --profile: expected one argument\n\nusage: aws [--profile PROFILE] \
             [--debug]\n"
                .into(),
        ),
        (
            FailureKind::AutoPromptConflict,
            FailureClass::ParamValidation,
            "Both --cli-auto-prompt and --no-cli-auto-prompt cannot be specified at the same \
             time."
                .into(),
        ),
        (
            FailureKind::EndpointUrlScheme("nope".into()),
            FailureClass::ParamValidation,
            "Bad value for --endpoint-url \"nope\": scheme is missing.  Must be of the form \
             http://<hostname>/ or https://<hostname>/"
                .into(),
        ),
        (
            FailureKind::TooFewArguments(vec!["s3"]),
            FailureClass::ParamValidation,
            "usage: aws [options] s3 <subcommand> [parameters]\naws: [ERROR]: too few arguments"
                .into(),
        ),
        (
            FailureKind::TooFewArguments(vec!["s3", "child"]),
            FailureClass::ParamValidation,
            "usage: aws [options] s3 child <subcommand> [parameters]\naws: [ERROR]: too few \
             arguments"
                .into(),
        ),
    ]
}
fn awscli_unknown_options_cases() -> Vec<(FailureKind, FailureClass, String)> {
    let unknown = |kind| FailureKind::UnknownOptions {
        tokens: vec!["--bogus".into(), "x".into()],
        kind,
        suggestions: vec![],
    };
    let suggest = |matched: &str, name: &str| Suggestion {
        matched: matched.into(),
        name: name.into(),
    };
    vec![
        (
            unknown(CommandKind::Basic),
            FailureClass::ParamValidation,
            "Unknown options: --bogus, x".into(),
        ),
        (
            FailureKind::UnknownOptions {
                tokens: vec!["--regoin".into(), "x".into(), "--recurisve".into()],
                kind: CommandKind::Basic,
                suggestions: vec![
                    suggest("region", "regoin"),
                    suggest("recursive", "recurisve"),
                ],
            },
            FailureClass::ParamValidation,
            "Unknown options: --regoin, x, --recurisve\n\nMaybe you meant:\n  * --region \
             (instead of --regoin)\n  * --recursive (instead of --recurisve)"
                .into(),
        ),
        (
            unknown(CommandKind::Service),
            FailureClass::ParamValidation,
            "Unknown options: --bogus, x".into(),
        ),
        (
            unknown(CommandKind::Operation),
            FailureClass::UnknownArgument,
            "Unknown options: --bogus, x".into(),
        ),
    ]
}
fn awscli_integer_cases() -> Vec<(FailureKind, FailureClass, String)> {
    vec![
        (
            FailureKind::IntegerOutOfRange("99999999999999999999".into()),
            FailureClass::General,
            "integer outside the 64-bit range of the native command: '99999999999999999999'".into(),
        ),
        (
            FailureKind::InvalidInteger("abc".into()),
            FailureClass::General,
            "invalid literal for int() with base 10: 'abc'".into(),
        ),
        (
            FailureKind::IntegerDigitLimit(5001),
            FailureClass::General,
            "Exceeds the limit (4300 digits) for integer string conversion: value has 5001 \
             digits; use sys.set_int_max_str_digits() to increase the limit"
                .into(),
        ),
        (
            FailureKind::InvalidInteger("x".repeat(250).into()),
            FailureClass::General,
            format!(
                "invalid literal for int() with base 10: '{}",
                "x".repeat(199)
            ),
        ),
        (
            FailureKind::IntegerOutOfRange("1".repeat(250)),
            FailureClass::General,
            format!(
                "integer outside the 64-bit range of the native command: '{}",
                "1".repeat(199)
            ),
        ),
    ]
}
fn awscli_value_cases() -> Vec<(FailureKind, FailureClass, String)> {
    let schema = "Invalid type for parameter x, value: 1, type: <class 'int'>, valid types: \
                  <class 'str'>\nInvalid type for parameter y, value: None, type: <class \
                  'NoneType'>, valid types: <class 'str'>";
    vec![
        (
            FailureKind::ParamfileLoad {
                name: "--sse-c-key".into(),
                uri: "fileb://missing".into(),
                errno_text: "[Errno 2] No such file or directory: 'missing'".into(),
            },
            FailureClass::ParamValidation,
            "Error parsing parameter '--sse-c-key': Unable to load paramfile fileb://missing: \
             [Errno 2] No such file or directory: 'missing'"
                .into(),
        ),
        (
            FailureKind::ParamfileDecode {
                name: "paths".into(),
                path: "/bin/ls".into(),
            },
            FailureClass::ParamValidation,
            "Error parsing parameter 'paths': Unable to load paramfile (/bin/ls), text contents \
             could not be decoded.  If this is a binary file, please use the fileb:// prefix \
             instead of the file:// prefix."
                .into(),
        ),
        (
            FailureKind::Shorthand {
                name: "--metadata".into(),
                text: "Expected: ',', received: '=' for input:\n a==b\n  ^".into(),
            },
            FailureClass::ParamValidation,
            "Error parsing parameter '--metadata': Expected: ',', received: '=' for input:\n \
             a==b\n  ^"
                .into(),
        ),
        (
            FailureKind::InvalidJson {
                name: "--metadata".into(),
                decoder_text: "syntax error: line 1 column 2 (byte 1)".into(),
                value: "{bad".into(),
            },
            FailureClass::ParamValidation,
            "Error parsing parameter '--metadata': Invalid JSON: syntax error: line 1 column 2 \
             (byte 1)\nJSON received: {bad"
                .into(),
        ),
        (
            FailureKind::NotJsonObject {
                name: "--metadata".into(),
                value: "[1]".into(),
            },
            FailureClass::ParamValidation,
            "Error parsing parameter '--metadata': Invalid JSON:\n[1]".into(),
        ),
        (
            FailureKind::SchemaValidation {
                report: schema.into(),
            },
            FailureClass::ParamValidation,
            format!("Parameter validation failed:\n{schema}"),
        ),
    ]
}
#[test]
fn awscli_failures_render_their_upstream_text_and_handler_class() {
    let mut cases = awscli_cases();
    cases.extend(awscli_unknown_options_cases());
    cases.extend(awscli_integer_cases());
    cases.extend(awscli_value_cases());
    let names: std::collections::BTreeSet<_> =
        cases.iter().map(|(kind, _, _)| kind.name()).collect();
    assert_eq!(names.len(), 14, "one case per kind: {names:?}");
    for (kind, class, text) in cases {
        let failure = Failure::new(kind.clone());
        assert_eq!(kind.class(), class, "{kind:?}");
        assert_eq!(failure.class, class, "{kind:?}");
        assert_eq!(failure.kind, kind.name());
        assert_eq!(failure.error_text(Color::default()), text, "{kind:?}");
        let parameter = match &kind {
            FailureKind::ParamfileLoad { name, .. }
            | FailureKind::ParamfileDecode { name, .. }
            | FailureKind::Shorthand { name, .. }
            | FailureKind::InvalidJson { name, .. }
            | FailureKind::NotJsonObject { name, .. } => Some(name.as_str()),
            _ => None,
        };
        assert_eq!(failure.parameter(), parameter, "{kind:?}");
    }
}
#[test]
fn every_corpus_failure_class_is_its_kind_class() {
    let corpus = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/testdata/awscli/cases.jsonl"
    ))
    .unwrap();
    let tables = &crate::tables::TABLES_DEFAULT;
    let vars = std::collections::HashMap::from([
        ("ARGPARSE_FIXTURES".into(), "paramfile".into()),
        ("LC_ALL".into(), "C.UTF-8".into()),
    ]);
    let files = crate::unpack::FsParamfiles;
    let environment = crate::unpack::Environment {
        directory: std::path::Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/src/testdata/awscli"
        )),
        variables: &vars,
        files: &files,
        preferred_encoding: crate::unpack::PreferredEncoding::Locale,
    };
    let mut kinds = std::collections::BTreeSet::new();
    for line in corpus.lines() {
        let case = crate::json::parse(line.as_bytes()).unwrap();
        let expected = case.get("native_expectation").unwrap_or(&case);
        let argv: Vec<String> = case["argv"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().unwrap().into())
            .collect();
        let mut result = crate::parse(&argv, &crate::Options::default(), tables);
        if result.outcome == crate::chain::Outcome::Parsed {
            crate::complete(&mut result, &environment);
        }
        let crate::chain::Outcome::Failure(failure) = &result.outcome else {
            continue;
        };
        assert_eq!(failure.class, failure.kind.class(), "{argv:?}");
        assert_eq!(
            expected["error"]["class"].as_str(),
            Some(failure.class.name()),
            "{argv:?}"
        );
        kinds.insert(failure.kind.name());
    }
    assert_eq!(kinds.len(), 13, "{kinds:?}");
}
