#![expect(clippy::unwrap_used, reason = "pinned fixtures and assertion tables")]
use super::*;
use crate::failure::{Color, FailureClass};
use crate::{Action, DefaultValue, Nargs};
use std::cell::Cell;
use std::ffi::OsString;
const TABLE: &[Argument] = &[
    Argument {
        positional: true,
        nargs: Some(Nargs::Optional),
        default: DefaultValue::String("s3://"),
        ..Argument::new("paths")
    },
    Argument {
        cli_type: Some(CliType::Integer),
        ..Argument::new("page-size")
    },
    Argument {
        cli_type: Some(CliType::Blob),
        ..Argument::new("sse-c-key")
    },
    Argument {
        cli_type: Some(CliType::Map),
        ..Argument::new("metadata")
    },
    Argument::new("bucket-region"),
    Argument {
        action: Action::StoreTrue,
        dest: Some("dir_op"),
        ..Argument::new("recursive")
    },
    Argument {
        cli_type: Some(CliType::Integer),
        default: DefaultValue::Integer(3600),
        ..Argument::new("expires-in")
    },
    Argument {
        action: Action::AppendNamed,
        nargs: Some(Nargs::Count(1)),
        dest: Some("filters"),
        ..Argument::new("include")
    },
];
#[derive(Default)]
struct FakeFiles {
    files: HashMap<PathBuf, Vec<u8>>,
    kinds: HashMap<PathBuf, FileKind>,
    errors: HashMap<PathBuf, i32>,
    reads: Cell<usize>,
}
impl FakeFiles {
    fn fixtures() -> Self {
        Self {
            files: HashMap::from([
                (PathBuf::from("ten.txt"), b" 1_0\r\n".to_vec()),
                ("text.txt".into(), b"a\r\nb\rc\n".to_vec()),
                ("binary.bin".into(), b"\xff\0k".to_vec()),
                ("surrogate.txt".into(), b"\xed\xa0\x80".to_vec()),
                ("sub/home.txt".into(), b"home".to_vec()),
                ("map.json".into(), b"{\"a\":\"b\",\n\"c\":\"d\"}\n".to_vec()),
                ("map.txt".into(), b"e=f\r\n".to_vec()),
            ]),
            ..Self::default()
        }
    }
}
impl Paramfiles for FakeFiles {
    fn kind(&self, path: &Path) -> std::io::Result<FileKind> {
        Ok(self.kinds.get(path).copied().unwrap_or(FileKind::File))
    }
    fn read(&self, path: &Path, _limit: usize) -> std::io::Result<Vec<u8>> {
        self.reads.set(self.reads.get() + 1);
        if let Some(errno) = self.errors.get(path) {
            #[cfg(windows)]
            let errno = &match errno {
                13 | 21 => 5,
                20 => 267,
                code => *code,
            };
            return Err(std::io::Error::from_raw_os_error(*errno));
        }
        self.files
            .get(path)
            .cloned()
            .ok_or_else(|| std::io::Error::from_raw_os_error(2))
    }
}
fn variables() -> HashMap<String, OsString> {
    HashMap::from([
        ("HOME".into(), "sub".into()),
        ("USERPROFILE".into(), "sub".into()),
        ("FIXTURE".into(), "ten.txt".into()),
    ])
}
fn environment<'a>(vars: &'a HashMap<String, OsString>, files: &'a FakeFiles) -> Environment<'a> {
    Environment {
        directory: Path::new(""),
        variables: vars,
        files,
        preferred_encoding: PreferredEncoding::Locale,
    }
}
fn expand_user_text(path: &str, env: &HashMap<String, OsString>) -> Option<String> {
    expand_user(path.as_bytes(), env).map(|bytes| String::from_utf8(bytes).unwrap())
}
fn expand_vars_text(path: &str, env: &HashMap<String, OsString>) -> Option<String> {
    expand_vars(path.as_bytes(), env).map(|bytes| String::from_utf8(bytes).unwrap())
}
fn one(dest: &str, value: impl Into<Value>) -> Namespace {
    let mut ns = Namespace::default();
    ns.put(dest, value.into(), true);
    ns
}
#[test]
fn parse_int_accepts_int_ascii_policy() {
    for (text, expected) in [
        ("10", 10),
        (" \t10\n", 10),
        ("\u{b}10\u{c}\r", 10),
        ("+10", 10),
        ("-10", -10),
        ("1_0", 10),
        ("1_000_000", 1000000),
        ("000", 0),
        ("-0", 0),
        ("9223372036854775807", i64::MAX),
        ("-9223372036854775808", i64::MIN),
    ] {
        assert_eq!(parse_int(text), Ok(expected));
    }
    for text in [
        "", " ", "+", "-", "_1", "1_", "1__0", "+_1", "abc", "1a", "1 0", "0x10", "1.0", "１",
        "\u{1c}10", "10\u{1f}",
    ] {
        assert_eq!(parse_int(text), Err(ParseIntError::InvalidLiteral));
    }
    for text in [
        "9223372036854775808",
        "-9223372036854775809",
        "99999999999999999999",
    ] {
        assert_eq!(parse_int(text), Err(ParseIntError::OutOfRange));
    }
    let text = format!("{}7", " ".repeat(PARAMFILE_BYTES_MAX - 1));
    assert_eq!(parse_int(&text), Ok(7));
}
#[test]
fn parse_int_applies_cpythons_digit_limit_after_the_syntax() {
    let limit = PYTHON_INT_MAX_STR_DIGITS;
    let at_limit = format!("{}5", "0".repeat(limit - 1));
    for (text, expected) in [
        (at_limit.clone(), Ok(5)),
        (format!(" \t-{}5\n", "0_".repeat(limit - 1)), Ok(-5)),
        (
            format!("-{}", "1".repeat(limit)),
            Err(ParseIntError::OutOfRange),
        ),
        (
            format!("0{at_limit}"),
            Err(ParseIntError::DigitLimit(limit + 1)),
        ),
        (
            "1".repeat(limit + 1),
            Err(ParseIntError::DigitLimit(limit + 1)),
        ),
        (
            format!(" +{}1\u{b}", "1_".repeat(limit + 1)),
            Err(ParseIntError::DigitLimit(limit + 2)),
        ),
        (
            format!("-{}", "9".repeat(5000)),
            Err(ParseIntError::DigitLimit(5000)),
        ),
    ] {
        assert_eq!(parse_int(&text), expected, "{}", text.len());
    }
    let over = "1".repeat(limit + 1);
    for text in [
        format!("{over}x"),
        format!("{over} 1"),
        format!("{over}_"),
        format!("_{over}"),
        format!("{over}__1"),
        format!("--{over}"),
        format!("{over}\u{1c}"),
        "99999999999999999999x".to_owned(),
    ] {
        assert_eq!(parse_int(&text), Err(ParseIntError::InvalidLiteral));
    }
}
#[test]
fn paramfile_uri_matches_strings_and_singleton_lists() {
    for text in ["file://x", "fileb://x", "file://"] {
        assert_eq!(paramfile_uri(&text.into()), Some(text));
        assert_eq!(paramfile_uri(&vec![text].into()), Some(text));
    }
    for value in [
        Value::from("File://x"),
        "s3://file://x".into(),
        "".into(),
        Value::Null,
        true.into(),
        1.into(),
        vec!["file://x", "y"].into(),
        Value::Array(vec![vec!["file://x"].into()]),
        Vec::<Value>::new().into(),
    ] {
        assert!(paramfile_uri(&value).is_none());
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "checks every expanduser case in one test"
)]
fn expand_user_uses_injected_home() {
    let mut env = HashMap::new();
    assert_eq!(expand_user_text("~", &env), None);
    assert_eq!(expand_user_text("~/x", &env), None);
    assert_eq!(expand_user_text("x/~", &env), Some("x/~".into()));
    env.insert("HOME".into(), "/home/me//".into());
    for (path, expected) in [
        ("~", "/home/me"),
        ("~/x", "/home/me/x"),
        ("~//x", "/home/me//x"),
    ] {
        assert_eq!(expand_user_text(path, &env).as_deref(), Some(expected));
    }
    assert_eq!(expand_user_text("~me/x", &env), None);
    assert_eq!(expand_user_text("~me", &env), None);
    for home in ["", "///"] {
        env.insert("HOME".into(), home.into());
        assert_eq!(expand_user_text("~", &env), Some("/".into()));
        assert_eq!(expand_user_text("~/x", &env), Some("/x".into()));
    }
}
#[test]
fn expand_vars_matches_posix_ascii_pattern() {
    let env = HashMap::from([("A".into(), "value".into()), ("B_2".into(), "$A".into())]);
    for (path, expected) in [
        ("plain", "plain"),
        ("$A", "value"),
        ("x/$A/y", "x/value/y"),
        ("${A}", "value"),
        ("${A}b", "valueb"),
        ("$Ab", "$Ab"),
        ("$B_2", "$A"),
        ("$B_2$A", "$Avalue"),
        ("$UNSET/x", "$UNSET/x"),
        ("${UNSET}", "${UNSET}"),
        ("${}", "${}"),
        ("${A", "${A"),
        ("$", "$"),
        ("$/", "$/"),
        ("$$A", "$value"),
        ("${A}}", "value}"),
        ("${A\n}", "${A\n}"),
        ("$é", "$é"),
    ] {
        assert_eq!(expand_vars_text(path, &env).as_deref(), Some(expected));
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "checks every expansion length bound in one test"
)]
fn expansion_accepts_byte_limit_and_refuses_growth() {
    let full = "a".repeat(EXPANDED_PATH_BYTES_MAX);
    let wide = format!("{full}a");
    let mut env = HashMap::new();
    assert_eq!(expand_vars_text(&full, &env), Some(full.clone()));
    assert_eq!(expand_vars_text(&wide, &env), None);
    env.insert("A".into(), full.clone().into());
    assert_eq!(expand_vars_text("$A", &env), Some(full.clone()));
    for path in ["$A/", "$A${UNSET}"] {
        assert_eq!(expand_vars_text(path, &env), None);
    }
    env.insert("A".into(), wide.clone().into());
    assert_eq!(expand_vars_text("$A", &env), None);
    env.insert("A".into(), full[..EXPANDED_PATH_BYTES_MAX / 2].into());
    assert_eq!(expand_vars_text("$A$A", &env), Some(full.clone()));
    env.insert("A".into(), full[..EXPANDED_PATH_BYTES_MAX / 2 + 1].into());
    assert_eq!(expand_vars_text("$A$A", &env), None);
    let unset = format!("${}", &full[1..]);
    assert_eq!(expand_vars_text(&unset, &env), Some(unset));
    env.insert("HOME".into(), full.clone().into());
    assert_eq!(expand_user_text("~", &env), Some(full));
    assert_eq!(expand_user_text("~/x", &env), None);
    assert_eq!(expand_user_text(&wide, &env), None);
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "checks every locale and codec case in one test"
)]
fn encoding_gate_follows_preferred_encoding() {
    let mut env = HashMap::new();
    assert!(text_encoding_is_utf8(&env));
    for locale in [
        "C",
        "POSIX",
        "C.UTF-8",
        "C.utf8",
        "en_US.UTF-8",
        "de_DE.utf8@euro",
        "",
    ] {
        env.insert("LANG".into(), locale.into());
        assert!(text_encoding_is_utf8(&env));
    }
    for locale in ["en_US", "en_US.ISO-8859-1", "ja_JP.eucJP", "C.latin1"] {
        env.insert("LANG".into(), locale.into());
        assert!(!text_encoding_is_utf8(&env));
    }
    env.insert("LC_CTYPE".into(), "C.UTF-8".into());
    assert!(text_encoding_is_utf8(&env));
    env.insert("LC_ALL".into(), "en_US.ISO-8859-1".into());
    assert!(!text_encoding_is_utf8(&env));
    env.insert("LC_ALL".into(), "".into());
    assert!(text_encoding_is_utf8(&env));
    for codec in ["UTF-8", "utf8", "utf_8", "U8", "  utf---8 ", "cp65001"] {
        env.insert("AWS_CLI_FILE_ENCODING".into(), codec.into());
        assert!(text_encoding_is_utf8(&env));
    }
    for codec in ["latin-1", "utf-8-sig", "utf-16", "", &"x".repeat(40)] {
        env.insert("AWS_CLI_FILE_ENCODING".into(), codec.into());
        assert!(!text_encoding_is_utf8(&env));
    }
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "preserve modeled value source assertions"
)]
fn loads_parameter_files_and_converts_modeled_scalars() {
    let files = FakeFiles::fixtures();
    let vars = variables();
    let env = environment(&vars, &files);
    let mut ns = one("paths", "file://text.txt");
    ns.put("page_size", "file://$FIXTURE".into(), true);
    ns.put("sse_c_key", "fileb://binary.bin".into(), true);
    ns.put("metadata", Value::Null, false);
    ns.put("bucket_region", vec!["file://~/home.txt"].into(), true);
    ns.put("dir_op", true.into(), true);
    ns.put("expires_in", 3600.into(), false);
    ns.put(
        "filters",
        vec![Value::from(vec!["--include", "file://x"])].into(),
        true,
    );
    ns.put("subcommand", Value::Null, false);
    let values = unpack(TABLE, &ns, &env).unwrap();
    assert_eq!(
        values.json().to_string(),
        concat!(
            "{\"paths\":\"a\\nb\\nc\\n\",\"page_size\":10,",
            "\"sse_c_key\":{\"$bytes\":\"/wBr\"},\"metadata\":null,",
            "\"bucket_region\":\"home\",\"dir_op\":true,\"expires_in\":3600,",
            "\"filters\":[[\"--include\",\"file://x\"]],\"subcommand\":null}"
        )
    );
    assert_eq!(
        values.value("sse_c_key"),
        Some(&Value::Bytes(b"\xff\0k".to_vec()))
    );
    assert_eq!(values.integer("page_size"), Some(10));
    assert_eq!(values.string("bucket_region"), Some("home"));
    assert!(values.boolean("dir_op"));
    assert!(!values.boolean("paths"));
    assert_eq!(values.string("page_size"), None);
    assert_eq!(values.value("missing"), None);
    assert_eq!(values.entries.len(), 9);
    assert_eq!(ns.string("page_size"), Some("file://$FIXTURE"));
}
#[test]
fn integer_parameter_file_can_exceed_argument_length() {
    let mut files = FakeFiles::fixtures();
    files.files.insert(
        "wide.txt".into(),
        format!("{}10", " ".repeat(crate::ARG_LEN_MAX - 1)).into_bytes(),
    );
    let vars = variables();
    let values = unpack(
        TABLE,
        &one("page_size", "file://wide.txt"),
        &environment(&vars, &files),
    )
    .unwrap();
    assert_eq!(values.integer("page_size"), Some(10));
}
#[test]
fn integer_values_over_the_digit_limit_fail_from_argv_and_parameter_files() {
    let mut files = FakeFiles::fixtures();
    files.files.insert(
        "n.txt".into(),
        format!("{}7\n", "0".repeat(5000)).into_bytes(),
    );
    let vars = variables();
    for (value, digits) in [
        ("1".repeat(PYTHON_INT_MAX_STR_DIGITS + 1), 4301),
        ("file://n.txt".to_owned(), 5001),
    ] {
        let error =
            unpack(TABLE, &one("page_size", value), &environment(&vars, &files)).unwrap_err();
        assert_eq!(error.dest, "page_size");
        assert_eq!(
            error.failure.unwrap().kind,
            FailureKind::IntegerDigitLimit(digits)
        );
    }
}
#[test]
fn maps_convert_shorthand_and_json() {
    let files = FakeFiles::fixtures();
    let vars = variables();
    for (input, expected) in [
        ("a=b,c=d", r#"{"a":"b","c":"d"}"#),
        ("a='x,y',b=", r#"{"a":"x,y","b":""}"#),
        ("=b", r#"{"":"b"}"#),
        (r#"{"x":1,"x":"ok"}"#, r#"{"x":"ok"}"#),
        (" {\"k\": \"v\"}\n", r#"{"k":"v"}"#),
        ("{}", "{}"),
        ("file://map.json", r#"{"a":"b","c":"d"}"#),
        ("file://map.txt", r#"{"e":"f"}"#),
    ] {
        let values = unpack(TABLE, &one("metadata", input), &environment(&vars, &files)).unwrap();
        assert_eq!(values.value("metadata").unwrap().to_string(), expected);
    }
    let text = format!("{{\"a\":\"{}\"}}", "[".repeat(40));
    assert!(unpack(TABLE, &one("metadata", text), &environment(&vars, &files)).is_ok());
    let error = unpack(
        TABLE,
        &one("metadata", r#"{"x":NaN,"x":"ok","x":Infinity,"x":"y"}"#),
        &environment(&vars, &files),
    )
    .unwrap_err();
    assert_eq!(error.failure.unwrap().kind, "invalid_json");
}
#[test]
fn integer_tokens_keep_any_length_and_original_spelling() {
    let files = FakeFiles::fixtures();
    let vars = variables();
    let digits = format!("1{}", "0".repeat(4400));
    let text = format!("{{\"x\":{digits},\"x\":\"ok\"}}");
    let values = unpack(TABLE, &one("metadata", text), &environment(&vars, &files)).unwrap();
    assert_eq!(
        values.value("metadata").unwrap().to_string(),
        r#"{"x":"ok"}"#
    );
    let text = format!("{{\"x\":[{digits}]}}");
    let error = unpack(TABLE, &one("metadata", text), &environment(&vars, &files)).unwrap_err();
    assert_eq!(
        error.failure.unwrap().error_text(Color::default()),
        format!(
            "Parameter validation failed:\nInvalid type for parameter x, value: [{digits}], \
    type: <class 'list'>, valid types: <class 'str'>"
        )
    );
}
#[test]
#[cfg(unix)]
fn argv_values_that_are_not_unicode_fail_integers_and_defer_json() {
    use std::os::unix::ffi::OsStringExt;
    let raw = |value: &[u8]| OsString::from_vec(value.to_vec());
    let files = FakeFiles::fixtures();
    let vars = variables();
    let error = unpack(
        TABLE,
        &one("page_size", raw(b"1\xff")),
        &environment(&vars, &files),
    )
    .unwrap_err();
    assert_eq!(error.dest, "page_size");
    let failure = error.failure.unwrap();
    assert_eq!(failure.class, FailureClass::General);
    assert_eq!(
        failure.error_text(Color::default()),
        "invalid literal for int() with base 10: '1\\udcff'"
    );
    for (dest, value) in [
        ("metadata", &b"{\"x\": \"\xff\"}"[..]),
        ("page_size", b"file://\xff"),
        ("page_size", b"fileb://\xff"),
    ] {
        let error = unpack(TABLE, &one(dest, raw(value)), &environment(&vars, &files)).unwrap_err();
        assert_eq!(error.dest, dest);
        assert_eq!(error.failure, None);
    }
}
#[test]
fn unsupported_values_stop_at_their_destination() {
    let mut files = FakeFiles::fixtures();
    files.kinds.insert("/dev/null".into(), FileKind::Stream);
    let vars = variables();
    let deep = format!("a={}x{}", "[".repeat(33), "]".repeat(33));
    let json = format!("{{\"a\":{}{}}}", "[".repeat(33), "]".repeat(33));
    for (dest, input) in [
        ("metadata", "a@=b"),
        ("metadata", "a=b,c @= file://ten.txt"),
        ("metadata", &deep),
        ("metadata", &json),
        ("page_size", "fileb://ten.txt"),
        ("bucket_region", "fileb://ten.txt"),
        ("paths", "fileb://ten.txt"),
        ("paths", "file://~someone/x"),
        ("subcommand", "file://text.txt"),
        ("paths", "file:///dev/null"),
        ("page_size", "file:///dev/null"),
    ] {
        let error = unpack(TABLE, &one(dest, input), &environment(&vars, &files)).unwrap_err();
        assert_eq!(error.dest, dest);
        assert_eq!(error.failure, None);
    }
    for (key, value) in [
        ("HOME", ""),
        ("LC_ALL", "en_US.ISO-8859-1"),
        ("AWS_CLI_FILE_ENCODING", "latin-1"),
    ] {
        let mut vars = vars.clone();
        if key == "HOME" {
            vars.remove(key);
            vars.remove("USERPROFILE");
        } else {
            vars.insert(key.into(), value.into());
        }
        let uri = if key == "HOME" {
            "file://~/x"
        } else {
            "file://text.txt"
        };
        assert!(
            unpack(TABLE, &one("paths", uri), &environment(&vars, &files))
                .unwrap_err()
                .failure
                .is_none()
        );
    }
}
#[test]
fn streams_are_classified_without_opening() {
    let mut files = FakeFiles::fixtures();
    files.kinds.insert("fifo".into(), FileKind::Stream);
    let vars = variables();
    let error = unpack(
        TABLE,
        &one("paths", "file://fifo"),
        &environment(&vars, &files),
    )
    .unwrap_err();
    assert_eq!(error.failure, None);
    assert_eq!(files.reads.get(), 0);
}
#[test]
fn unreadable_parameter_file_reports_eacces() {
    let mut files = FakeFiles::fixtures();
    files.errors.insert("denied".into(), 13);
    let vars = variables();
    let error = unpack(
        TABLE,
        &one("paths", "file://denied"),
        &environment(&vars, &files),
    )
    .unwrap_err();
    assert_eq!(
        error.failure.unwrap().error_text(Color::default()),
        "Error parsing parameter 'paths': Unable to load paramfile file://denied: [Errno 13] \
    Permission denied: 'denied'"
    );
}
#[test]
fn universal_newlines_and_file_size_bound() {
    let mut files = FakeFiles::fixtures();
    let vars = variables();
    for (input, expected) in [
        (b"a\r\nb\rc\n\r\r\n".to_vec(), "a\nb\nc\n\n\n".into()),
        (vec![], String::new()),
        (
            vec![b'\r'; PARAMFILE_BYTES_MAX - 1],
            "\n".repeat(PARAMFILE_BYTES_MAX - 1),
        ),
    ] {
        files.files.insert("newlines".into(), input);
        let values = unpack(
            TABLE,
            &one("paths", "file://newlines"),
            &environment(&vars, &files),
        )
        .unwrap();
        assert_eq!(values.string("paths"), Some(expected.as_str()));
    }
    for len in [PARAMFILE_BYTES_MAX, PARAMFILE_BYTES_MAX + 1] {
        files.files.insert("too-long".into(), vec![b'x'; len]);
        assert!(
            unpack(
                TABLE,
                &one("paths", "file://too-long"),
                &environment(&vars, &files)
            )
            .unwrap_err()
            .failure
            .is_none(),
            "{len}"
        );
    }
}
#[test]
fn first_failing_destination_preserves_all_source_diagnostics() {
    let mut files = FakeFiles::fixtures();
    files.errors.insert("sub".into(), 21);
    files.errors.insert("ten.txt/x".into(), 20);
    let vars = variables();
    assert_failure_corpus(&environment(&vars, &files));
}
fn assert_failure_corpus(environment: &Environment<'_>) {
    let cases = crate::json::parse(include_bytes!("../testdata/unpack-failures.json")).unwrap();
    for case in cases.as_array().unwrap() {
        let dest = case["dest"].as_str().unwrap();
        let bytes = case["value"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_u64().unwrap() as u8)
            .collect::<Vec<_>>();
        let expected = case["text"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_u64().unwrap() as u8)
            .collect::<Vec<_>>();
        let Ok(value) = String::from_utf8(bytes.clone()) else {
            assert_eq!(
                crate::json::parse(&bytes),
                Err(crate::json::JsonError::Syntax {
                    offset: 7,
                    incomplete: false
                })
            );
            continue;
        };
        let mut ns = one("paths", "s3://");
        ns.put("page_size", Value::Null, false);
        ns.put("sse_c_key", Value::Null, false);
        ns.put(dest, value.clone().into(), true);
        ns.put("bucket_region", "file://missing-too".into(), true);
        let error = unpack(TABLE, &ns, environment).unwrap_err();
        assert_eq!(error.dest, dest);
        let failure = error.failure.unwrap();
        let expected = String::from_utf8(expected).unwrap();
        #[cfg(windows)]
        let expected =
            expected.replace("[Errno 21] Is a directory", "[Errno 13] Permission denied");
        assert_eq!(
            failure.error_text(Color::default()),
            expected,
            "{dest}: {value}"
        );
        let general =
            expected.starts_with("invalid literal") || expected.starts_with("integer outside");
        assert_eq!(
            failure.class,
            if general {
                FailureClass::General
            } else {
                FailureClass::ParamValidation
            }
        );
    }
}
#[test]
#[cfg(all(unix, not(miri)))]
fn filesystem_named_pipe_is_never_opened() {
    let directory =
        std::env::temp_dir().join(format!("awscli-argparse-fifo-{}", std::process::id()));
    std::fs::create_dir_all(&directory).unwrap();
    let fifo = directory.join("fifo");
    let created = std::process::Command::new("mkfifo")
        .arg(&fifo)
        .status()
        .unwrap();
    assert!(created.success());
    let variables = HashMap::new();
    let files = FsParamfiles;
    let environment = Environment {
        directory: &directory,
        variables: &variables,
        files: &files,
        preferred_encoding: PreferredEncoding::Locale,
    };
    let error = unpack(TABLE, &one("paths", "file://fifo"), &environment).unwrap_err();
    assert_eq!(error.failure, None);
    std::fs::remove_file(fifo).unwrap();
    std::fs::remove_dir(directory).unwrap();
}
#[cfg(not(miri))]
struct ScratchDir(PathBuf);
#[cfg(not(miri))]
impl ScratchDir {
    fn new(name: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("awscli-argparse-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&path);
        std::fs::create_dir_all(&path).unwrap();
        Self(path)
    }
    #[cfg(unix)]
    fn with_fixtures(name: &str) -> Self {
        let scratch = Self::new(name);
        std::fs::create_dir(scratch.0.join("sub")).unwrap();
        for (path, bytes) in FakeFiles::fixtures().files {
            std::fs::write(scratch.0.join(path), bytes).unwrap();
        }
        scratch
    }
    fn environment<'a>(&'a self, vars: &'a HashMap<String, OsString>) -> Environment<'a> {
        Environment {
            directory: &self.0,
            variables: vars,
            files: &FsParamfiles,
            preferred_encoding: PreferredEncoding::Locale,
        }
    }
}
#[cfg(not(miri))]
impl Drop for ScratchDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
#[test]
#[cfg(all(unix, not(miri)))]
fn filesystem_failure_corpus_reports_os_errors() {
    let scratch = ScratchDir::with_fixtures("corpus");
    let vars = variables();
    assert_failure_corpus(&scratch.environment(&vars));
}
#[test]
#[cfg(all(unix, not(miri)))]
fn filesystem_unreadable_parameter_file_reports_eacces() {
    use std::os::unix::fs::PermissionsExt;
    let scratch = ScratchDir::new("eacces");
    let secret = scratch.0.join("secret.txt");
    std::fs::write(&secret, b"k").unwrap();
    std::fs::set_permissions(&secret, std::fs::Permissions::from_mode(0o000)).unwrap();
    // Root reads every file, so the permission bits prove nothing there.
    if std::fs::read(&secret).is_ok() {
        return;
    }
    let vars = variables();
    let error = unpack(
        TABLE,
        &one("sse_c_key", "fileb://secret.txt"),
        &scratch.environment(&vars),
    )
    .unwrap_err();
    assert_eq!(error.dest, "sse_c_key");
    assert_eq!(
        error.failure.unwrap().error_text(Color::default()),
        "Error parsing parameter '--sse-c-key': Unable to load paramfile fileb://secret.txt: \
    [Errno 13] Permission denied: 'secret.txt'"
    );
}
#[test]
#[cfg(not(miri))]
fn filesystem_file_size_bound_is_exclusive() {
    let scratch = ScratchDir::new("limit");
    let vars = variables();
    let environment = scratch.environment(&vars);
    std::fs::write(scratch.0.join("under"), vec![b'x'; PARAMFILE_BYTES_MAX - 1]).unwrap();
    let values = unpack(TABLE, &one("paths", "file://under"), &environment).unwrap();
    assert_eq!(
        values.string("paths").map(str::len),
        Some(PARAMFILE_BYTES_MAX - 1)
    );
    for len in [PARAMFILE_BYTES_MAX, PARAMFILE_BYTES_MAX + 1] {
        std::fs::write(scratch.0.join("limit"), vec![b'x'; len]).unwrap();
        let error = unpack(TABLE, &one("paths", "file://limit"), &environment).unwrap_err();
        assert_eq!(
            (error.dest.as_str(), error.failure),
            ("paths", None),
            "{len}"
        );
    }
}
#[test]
fn binary_files_load_under_a_foreign_text_encoding() {
    let files = FakeFiles::fixtures();
    let mut vars = variables();
    vars.insert("LC_ALL".into(), "en_US.ISO-8859-1".into());
    let values = unpack(
        TABLE,
        &one("sse_c_key", "fileb://binary.bin"),
        &environment(&vars, &files),
    )
    .unwrap();
    assert_eq!(
        values.json().to_string(),
        r#"{"sse_c_key":{"$bytes":"/wBr"}}"#
    );
}
fn retained_bytes(value: &Value) -> usize {
    match value {
        Value::Null | Value::Bool(_) => 0,
        Value::Number(text) | Value::String(text) => text.capacity(),
        Value::OsString(text) => text.capacity(),
        Value::Bytes(bytes) => bytes.capacity(),
        Value::Array(items) => {
            items.capacity() * size_of::<Value>() + items.iter().map(retained_bytes).sum::<usize>()
        }
        Value::Object(pairs) => pairs
            .iter()
            .map(|(key, value)| {
                size_of::<(String, Value)>()
                    + size_of::<(String, usize)>()
                    + 2 * key.capacity()
                    + retained_bytes(value)
            })
            .sum(),
    }
}
#[test]
fn speculative_csv_failures_retain_linear_memory() {
    const PAIR_COUNT: usize = 4000;
    let input = (0..PAIR_COUNT)
        .map(|i| format!("k{i}=v"))
        .collect::<Vec<_>>()
        .join(",");
    let files = FakeFiles::fixtures();
    let vars = variables();
    let values = unpack(TABLE, &one("metadata", input), &environment(&vars, &files)).unwrap();
    let value = values.value("metadata").unwrap();
    assert_eq!(value.as_object().unwrap().len(), PAIR_COUNT);
    assert!(retained_bytes(value) < PAIR_COUNT * 1024);
}
#[cfg(unix)]
mod os {
    use super::*;
    use std::os::unix::ffi::OsStringExt;

    fn raw(bytes: &[u8]) -> OsString {
        OsString::from_vec(bytes.to_vec())
    }

    #[test]
    fn expansion_substitutes_values_that_are_not_unicode() {
        let env = HashMap::from([
            ("D".into(), raw(b"d\xff")),
            ("HOME".into(), raw(b"h\xff//")),
        ]);
        for (path, expected) in [
            ("$D/n.txt", b"d\xff/n.txt".as_slice()),
            ("${D}/n.txt", b"d\xff/n.txt"),
            ("x$D$D", b"xd\xffd\xff"),
        ] {
            assert_eq!(
                expand_vars(path.as_bytes(), &env).as_deref(),
                Some(expected)
            );
        }
        assert_eq!(
            expand_user(b"~/n.txt", &env).as_deref(),
            Some(b"h\xff/n.txt".as_slice())
        );
        assert_eq!(
            expand_vars(b"${\xff}", &env).as_deref(),
            Some(b"${\xff}".as_slice())
        );
    }

    #[test]
    fn paths_that_are_not_unicode_load_and_report_surrogate_escapes() {
        let mut files = FakeFiles::fixtures();
        files
            .files
            .insert(raw(b"d\xff/n.txt").into(), b"10".to_vec());
        files
            .files
            .insert(raw(b"d\xff/l.txt").into(), b"\xe9".to_vec());
        let mut vars = variables();
        vars.insert("D".into(), raw(b"d\xff"));
        let env = environment(&vars, &files);
        let values = unpack(TABLE, &one("page_size", "file://$D/n.txt"), &env).unwrap();
        assert_eq!(values.integer("page_size"), Some(10));
        for (uri, text) in [
            (
                "file://$D/missing",
                "Error parsing parameter '--page-size': Unable to load paramfile \
    file://$D/missing: [Errno 2] No such file or directory: 'd\\udcff/missing'",
            ),
            (
                "file://$D/l.txt",
                "Error parsing parameter '--page-size': Unable to load paramfile \
    (d\\udcff/l.txt), text contents could not be decoded.  If this is a binary file, \
    please use the fileb:// prefix instead of the file:// prefix.",
            ),
        ] {
            let error = unpack(TABLE, &one("page_size", uri), &env).unwrap_err();
            assert_eq!(
                error.failure.unwrap().error_text(Color::default()),
                text,
                "{uri}"
            );
        }
    }

    #[test]
    fn encoding_gate_reads_unicode_views() {
        let mut env = HashMap::from([("LANG".into(), OsString::from("C.UTF-8"))]);
        env.insert("LC_ALL".into(), raw(b"en_US.\xff"));
        assert!(text_encoding_is_utf8(&env));
        env.insert("LANG".into(), "en_US.ISO-8859-1".into());
        assert!(!text_encoding_is_utf8(&env));
        env.insert("AWS_CLI_FILE_ENCODING".into(), raw(b"utf-8\xff"));
        assert!(!text_encoding_is_utf8(&env));
    }

    #[test]
    fn os_string_values_stop_at_their_destination() {
        let files = FakeFiles::fixtures();
        let vars = variables();
        let error = unpack(
            TABLE,
            &one("metadata", Value::OsString(raw(b"a=\xffb"))),
            &environment(&vars, &files),
        )
        .unwrap_err();
        assert_eq!((error.dest.as_str(), error.failure), ("metadata", None));
    }
}
