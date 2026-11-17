use super::*;
use crate::tests::{TestResult, Time, files};
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};

/// A stand-in process that prints each of `outputs` in turn, then fails,
/// and records the command it was run with.
fn printing(outputs: &[&str]) -> (Runner, Arc<Mutex<Vec<Vec<String>>>>) {
    let outputs: Vec<String> = outputs.iter().map(|&output| output.to_owned()).collect();
    let commands = Arc::new(Mutex::new(Vec::new()));
    let seen = Arc::clone(&commands);
    let runs = AtomicUsize::new(0);
    let runner = Runner::new(move |command| {
        seen.lock()
            .map_err(|_| io::Error::other("poisoned"))?
            .push(command.to_vec());
        let run = runs.fetch_add(1, Ordering::SeqCst);
        Ok(match outputs.get(run) {
            Some(stdout) => ProcessOutput {
                success: true,
                stdout: stdout.clone().into_bytes(),
                stderr: Vec::new(),
            },
            None => ProcessOutput {
                success: false,
                stdout: Vec::new(),
                stderr: b"the token has expired\n".to_vec(),
            },
        })
    });
    (runner, commands)
}

const CONFIG: &str = "[default]\ncredential_process = fetch-credentials --role \"my role\"\n";

/// What the `default` profile's process provider loads.
fn load(config: &str, outputs: &[&str]) -> Result<Option<Loaded>, LoadError> {
    let (runner, _) = printing(outputs);
    ProcessProvider::new_with_runner(&files(config, ""), "default", runner).load()
}

fn message(result: Result<Option<Loaded>, LoadError>) -> Result<(), String> {
    result.map(|_| ()).map_err(|error| error.to_string())
}

#[test]
fn a_profile_without_a_credential_process_has_no_credentials() -> TestResult {
    let (runner, commands) = printing(&[]);
    let parsed = files("[default]\nregion = us-west-2\n", "");
    let provider = ProcessProvider::new_with_runner(&parsed, "default", runner);
    assert!(provider.load()?.is_none());
    assert!(commands.lock().map_err(|_| "poisoned")?.is_empty());
    Ok(())
}

#[test]
fn output_without_an_expiration_is_static() -> TestResult {
    let (runner, commands) = printing(&[
        r#"{"Version": 1, "AccessKeyId": "AKIDPROCESS", "SecretAccessKey": "process-secret",
            "SessionToken": "process-token", "AccountId": "123456789012"}"#,
    ]);
    let parsed = files(CONFIG, "");
    let found = ProcessProvider::new_with_runner(&parsed, "default", runner).load()?;
    let Some(Loaded::Static(found)) = found else {
        return Err(format!("expected static credentials, found {found:?}").into());
    };
    assert_eq!(found.method(), "custom-process");
    assert_eq!(found.access_key_id(), "AKIDPROCESS");
    assert_eq!(found.secret_access_key(), "process-secret");
    assert_eq!(found.session_token(), Some("process-token"));
    assert_eq!(found.account_id(), Some("123456789012"));
    assert_eq!(
        *commands.lock().map_err(|_| "poisoned")?,
        [["fetch-credentials", "--role", "my role"]]
    );
    Ok(())
}

#[test]
fn an_expiration_makes_the_output_refreshable_by_running_the_command_again() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let (runner, commands) = printing(&[
        r#"{"Version": 1, "AccessKeyId": "AKIDFIRST", "SecretAccessKey": "s",
            "Expiration": "2037-10-21T08:00:00Z"}"#,
        r#"{"Version": 1, "AccessKeyId": "AKIDSECOND", "SecretAccessKey": "s",
            "Expiration": "2037-10-21T09:00:00Z"}"#,
    ]);
    // The profile's account stands in for one the output leaves out.
    let config = format!("{CONFIG}aws_account_id = 999999999999\n");
    let parsed = files(&config, "");
    let found = ProcessProvider::new_with_runner(&parsed, "default", runner).load()?;
    let Some(Loaded::Refreshable(found)) = found else {
        return Err(format!("expected refreshable credentials, found {found:?}").into());
    };
    let found = found.with_clock(time.clock());
    assert_eq!(found.frozen()?.access_key_id(), "AKIDFIRST");
    assert_eq!(found.frozen()?.account_id(), Some("999999999999"));
    time.advance(55 * 60);
    assert_eq!(found.frozen()?.access_key_id(), "AKIDSECOND");
    // The third run fails, with nine minutes left: the mandatory window.
    time.advance(56 * 60);
    assert_eq!(
        found.frozen().map_err(|error| error.to_string()),
        Err(
            "Error when retrieving credentials from custom-process: the token has expired\n".into()
        )
    );
    let command = ["fetch-credentials", "--role", "my role"];
    assert_eq!(
        *commands.lock().map_err(|_| "poisoned")?,
        [command, command, command]
    );
    Ok(())
}

#[test]
fn refreshed_output_that_drops_its_expiration_is_an_error() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let (runner, _) = printing(&[
        r#"{"Version": 1, "AccessKeyId": "AKIDFIRST", "SecretAccessKey": "s",
            "Expiration": "2037-10-21T08:00:00Z"}"#,
        r#"{"Version": 1, "AccessKeyId": "AKIDSECOND", "SecretAccessKey": "s"}"#,
    ]);
    let parsed = files(CONFIG, "");
    let found = ProcessProvider::new_with_runner(&parsed, "default", runner)
        .load()?
        .ok_or("the provider found nothing")?
        .with_clock(time.clock());
    // The advisory window, where a provider's own failure would be forgiven.
    time.advance(46 * 60);
    assert_eq!(
        found.frozen(),
        Err(crate::RefreshError::MissingExpiry {
            provider: "custom-process"
        })
    );
    Ok(())
}

const FIRST: &str = r#"{"Version": 1, "AccessKeyId": "AKIDFIRST", "SecretAccessKey": "s",
    "Expiration": "2037-10-21T08:00:00Z"}"#;

/// What a caller gets fourteen minutes before `FIRST` expires, in the
/// advisory window, when the refresh prints `output`.
fn advisory_refresh(
    output: &str,
) -> Result<Result<Credentials, crate::RefreshError>, Box<dyn std::error::Error>> {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    let (runner, _) = printing(&[FIRST, output]);
    let parsed = files(CONFIG, "");
    let found = ProcessProvider::new_with_runner(&parsed, "default", runner)
        .load()?
        .ok_or("the provider found nothing")?
        .with_clock(time.clock());
    time.advance(46 * 60);
    Ok(found.frozen())
}

/// botocore raises these inside the refresh callable, where the advisory
/// window forgives them and the current credentials stay in use.
#[test]
fn a_process_that_fails_an_advisory_refresh_is_forgiven() -> TestResult {
    for output in [
        "not json",
        "[1]",
        r#"{"Version": 2, "AccessKeyId": "AKIDSECOND", "SecretAccessKey": "s",
            "Expiration": "2037-10-21T09:00:00Z"}"#,
        r#"{"Version": 1, "SecretAccessKey": "s", "Expiration": "2037-10-21T09:00:00Z"}"#,
        r#"{"Version": 1, "AccessKeyId": "AKIDSECOND", "Expiration": "2037-10-21T09:00:00Z"}"#,
        // A required key that is absent is found before any value is
        // looked at, so the values beside it do not matter.
        r#"{"Version": 1, "AccessKeyId": null, "Expiration": "2037-10-21T09:00:00Z"}"#,
        r#"{"Version": 1, "AccessKeyId": 7, "SessionToken": ["t"], "Expiration": 123}"#,
        r#"{"Version": 1, "SecretAccessKey": null, "Expiration": "tomorrow"}"#,
    ] {
        let found = advisory_refresh(output)?;
        assert_eq!(
            found.map(|found| found.access_key_id().to_owned()),
            Ok("AKIDFIRST".to_owned()),
            "{output}"
        );
    }
    Ok(())
}

/// botocore returns these values from the refresh callable as they are
/// and fails on them afterwards, where no window forgives.
#[test]
fn output_of_the_wrong_type_fails_an_advisory_refresh() -> TestResult {
    let expiry = |value: &str| {
        crate::RefreshError::Metadata(LoadError::Expiry {
            provider: "custom-process",
            value: value.to_owned(),
        })
    };
    let not_text = |key| {
        crate::RefreshError::Metadata(LoadError::Metadata {
            provider: "custom-process",
            key,
        })
    };
    let output = |members: &str| format!(r#"{{"Version": 1, {members}}}"#);
    let keys = r#""AccessKeyId": "AKIDSECOND", "SecretAccessKey": "s""#;
    let later = r#""Expiration": "2037-10-21T09:00:00Z""#;
    for (members, error) in [
        (format!(r#"{keys}, "Expiration": 123"#), expiry("123")),
        (format!(r#"{keys}, "Expiration": true"#), expiry("true")),
        (format!(r#"{keys}, "Expiration": """#), expiry("")),
        (
            format!(r#"{keys}, "Expiration": "tomorrow""#),
            expiry("tomorrow"),
        ),
        (
            format!(r#""AccessKeyId": null, "SecretAccessKey": "s", {later}"#),
            not_text("AccessKeyId"),
        ),
        (
            format!(r#""AccessKeyId": "AKIDSECOND", "SecretAccessKey": 7, {later}"#),
            not_text("SecretAccessKey"),
        ),
        (
            format!(r#"{keys}, "SessionToken": ["t"], {later}"#),
            not_text("SessionToken"),
        ),
        (
            format!(r#"{keys}, "SessionToken": true, {later}"#),
            not_text("SessionToken"),
        ),
        (
            format!(r#"{keys}, "SessionToken": 7, {later}"#),
            not_text("SessionToken"),
        ),
        (
            format!(r#"{keys}, "SessionToken": {{"a": 1}}, {later}"#),
            not_text("SessionToken"),
        ),
        // botocore parses the expiry as the refresh ends, and meets the
        // other values only when it signs.
        (
            r#""AccessKeyId": 7, "SecretAccessKey": "s", "Expiration": 123"#.to_owned(),
            expiry("123"),
        ),
    ] {
        assert_eq!(
            advisory_refresh(&output(&members))?,
            Err(error),
            "{members}"
        );
    }
    assert_eq!(
        advisory_refresh(&output(&format!(r#"{keys}, "Expiration": null"#)))?,
        Err(crate::RefreshError::MissingExpiry {
            provider: "custom-process"
        })
    );
    Ok(())
}

/// botocore keeps whatever token the output holds and leaves the header
/// out when Python counts the token as false, on the first
/// load and on a refresh alike.
#[test]
fn a_token_python_counts_as_false_is_no_token() -> TestResult {
    let time = Time::at("2037-10-21T07:00:00Z")?;
    for token in ["null", "false", "0", "0.0", r#""""#, "[]", "{}"] {
        let keys = format!(
            r#""Version": 1, "AccessKeyId": "AKIDSECOND", "SecretAccessKey": "s",
                "SessionToken": {token}"#
        );
        let lasting = format!("{{{keys}}}");
        let expiring = format!(r#"{{{keys}, "Expiration": "2037-10-21T09:00:00Z"}}"#);
        for output in [&lasting, &expiring] {
            let found = load(CONFIG, &[output])?
                .ok_or("the provider found nothing")?
                .with_clock(time.clock())
                .frozen()?;
            assert_eq!(
                (found.access_key_id(), found.session_token()),
                ("AKIDSECOND", None),
                "{output}"
            );
        }
        let refreshed = advisory_refresh(&expiring)??;
        assert_eq!(
            (refreshed.access_key_id(), refreshed.session_token()),
            ("AKIDSECOND", None),
            "{expiring}"
        );
    }
    assert_eq!(
        message(load(
            CONFIG,
            &[
                r#"{"Version": 1, "AccessKeyId": "AKID", "SecretAccessKey": "s",
                "SessionToken": true}"#
            ]
        )),
        Err("SessionToken from custom-process is not a string".into())
    );
    Ok(())
}

/// The profile's account stands in for an `AccountId` Python counts as
/// false; any other value is the output's own.
#[test]
fn the_profiles_account_replaces_one_the_output_leaves_empty() -> TestResult {
    let config = format!(
        "{CONFIG}aws_account_id = 999999999999
"
    );
    for (account_id, expected) in [
        (r#""123456789012""#, Some("123456789012")),
        (r#""""#, Some("999999999999")),
        ("null", Some("999999999999")),
        ("0", Some("999999999999")),
        ("false", Some("999999999999")),
        ("[]", Some("999999999999")),
        // botocore would carry the number; these credentials cannot.
        ("123456789012", None),
    ] {
        let output = format!(
            r#"{{"Version": 1, "AccessKeyId": "AKID", "SecretAccessKey": "s",
                "AccountId": {account_id}}}"#
        );
        let found = load(&config, &[&output])?.ok_or("the provider found nothing")?;
        assert_eq!(found.frozen()?.account_id(), expected, "{account_id}");
    }
    Ok(())
}

#[test]
fn the_credentials_files_command_replaces_the_config_files() -> TestResult {
    let (runner, commands) = printing(&[]);
    let parsed = files(CONFIG, "[default]\ncredential_process = other-command\n");
    let _ = ProcessProvider::new_with_runner(&parsed, "default", runner).load();
    assert_eq!(
        *commands.lock().map_err(|_| "poisoned")?,
        [["other-command"]]
    );
    Ok(())
}

#[test]
fn a_failure_reports_botocores_message() {
    assert_eq!(
        message(load(CONFIG, &[])),
        Err(
            "Error when retrieving credentials from custom-process: the token has expired\n".into()
        )
    );
    assert_eq!(
        message(load(
            CONFIG,
            &[r#"{"AccessKeyId": "AKID", "SecretAccessKey": "s"}"#]
        )),
        Err(
            "Error when retrieving credentials from custom-process: Unsupported version \
             '<Version key not provided>' for credential process provider, \
             supported versions: 1"
                .into()
        )
    );
    assert_eq!(
        message(load(
            CONFIG,
            &[r#"{"Version": "1", "AccessKeyId": "AKID", "SecretAccessKey": "s"}"#]
        )),
        Err(
            "Error when retrieving credentials from custom-process: Unsupported version \
             '1' for credential process provider, supported versions: 1"
                .into()
        )
    );
    // A missing key is reported before a value of the wrong type is.
    for output in [
        r#"{"Version": 1, "AccessKeyId": "AKID"}"#,
        r#"{"Version": 1, "AccessKeyId": null, "Expiration": 123}"#,
    ] {
        assert_eq!(
            message(load(CONFIG, &[output])),
            Err("Error when retrieving credentials from custom-process: \
                 Missing required key in response: 'SecretAccessKey'"
                .into())
        );
    }
}

#[test]
fn output_or_a_command_that_cannot_be_read_is_an_error() {
    for (config, output) in [
        (CONFIG, "not json"),
        (CONFIG, "[1]"),
        // Unclosed under Windows' rules and `shlex`'s alike.
        ("[default]\ncredential_process = fetch \"unclosed\n", "{}"),
    ] {
        let result = load(config, &[output]);
        assert!(
            matches!(result, Err(LoadError::CredentialProcess { .. })),
            "{output}: {result:?}"
        );
    }
    assert_eq!(
        message(load(
            CONFIG,
            &[r#"{"Version": 1, "AccessKeyId": 7, "SecretAccessKey": "s"}"#]
        )),
        Err("AccessKeyId from custom-process is not a string".into())
    );
    assert_eq!(
        message(load(
            CONFIG,
            &[
                r#"{"Version": 1, "AccessKeyId": "AKID", "SecretAccessKey": "s",
                "Expiration": "tomorrow"}"#
            ]
        )),
        Err(
            "credential expiry from custom-process is not an ISO 8601 time with a zone: tomorrow"
                .into()
        )
    );
}

#[test]
fn a_file_that_does_not_parse_is_an_error() {
    let (runner, _) = printing(&[]);
    let parsed = files(CONFIG, "not a section\n");
    assert_eq!(
        ProcessProvider::new_with_runner(&parsed, "default", runner)
            .load()
            .map(|_| ()),
        Err(LoadError::ConfigParse {
            path: "/home/.aws/credentials".into()
        })
    );
}

/// The words Python's `shlex.split` gives for the same commands.
#[test]
fn a_command_is_split_as_shlex_splits_it() {
    let cases: [(&str, &[&str]); 9] = [
        ("a b", &["a", "b"]),
        ("a 'b c' d", &["a", "b c", "d"]),
        (r#"a "b \" c" d"#, &["a", "b \" c", "d"]),
        (r"a\ b c", &["a b", "c"]),
        ("a '' b", &["a", "", "b"]),
        (r#"a "b\nc""#, &["a", r"b\nc"]),
        ("x'y'z", &["xyz"]),
        (
            r#"sh -c 'echo "{\"V\": 1}"'"#,
            &["sh", "-c", r#"echo "{\"V\": 1}""#],
        ),
        ("  ", &[]),
    ];
    for (command, words) in cases {
        assert_eq!(
            shell_split(command).as_deref(),
            Ok(words
                .iter()
                .map(|&word| word.to_owned())
                .collect::<Vec<_>>()
                .as_slice()),
            "{command}"
        );
    }
    assert_eq!(shell_split("a \"b"), Err("No closing quotation"));
    assert_eq!(shell_split("a\\"), Err("No escaped character"));
}

/// The words botocore's `_windows_shell_split` gives for each command.
fn assert_windows_splits(cases: &[(&str, &[&str])]) {
    for &(command, words) in cases {
        assert_eq!(
            windows_shell_split(command),
            Ok(words.iter().map(|&word| word.to_owned()).collect()),
            "{command}"
        );
    }
}

/// botocore's own cases (`get_windows_test_cases` in its compat tests), the
/// last four from Microsoft's documentation of the C runtime's rules.
#[test]
fn a_command_is_split_as_botocore_splits_it_on_windows() {
    assert_windows_splits(&[
        ("", &[]),
        (r"spam \\", &["spam", r"\\"]),
        ("spam ", &["spam"]),
        (" spam", &["spam"]),
        ("spam eggs", &["spam", "eggs"]),
        ("spam\teggs", &["spam", "eggs"]),
        ("spam\neggs", &["spam\neggs"]),
        (r#""""#, &[""]),
        (r#"" ""#, &[" "]),
        ("\"\t\"", &["\t"]),
        (r"\\", &[r"\\"]),
        (r"\\ ", &[r"\\"]),
        ("\\\\\t", &[r"\\"]),
        (r#"\""#, &["\""]),
        (r#""abc" d e"#, &["abc", "d", "e"]),
        (r#"a\\b d"e f"g h"#, &[r"a\\b", "de fg", "h"]),
        (r#"a\\\"b c d"#, &[r#"a\"b"#, "c", "d"]),
        (r#"a\\\\"b c" d e"#, &[r"a\\b c", "d", "e"]),
    ]);
    assert_eq!(
        windows_shell_split("\""),
        Err("No closing quotation in string: \"".to_owned())
    );
}

/// Command lines as people write them on Windows: a path keeps its
/// backslashes, and quotes hold spaces.
#[test]
fn a_windows_command_line_keeps_its_paths() {
    assert_windows_splits(&[
        (
            r"C:\tools\creds.exe --profile dev",
            &[r"C:\tools\creds.exe", "--profile", "dev"],
        ),
        (
            r#""C:\Program Files\Tool\tool.exe" --arg "value with spaces""#,
            &[
                r"C:\Program Files\Tool\tool.exe",
                "--arg",
                "value with spaces",
            ],
        ),
        (
            "aws-vault exec dev --json",
            &["aws-vault", "exec", "dev", "--json"],
        ),
        (
            r"python C:\scripts\creds.py",
            &["python", r"C:\scripts\creds.py"],
        ),
        (
            r"cmd /c C:\scripts\creds.cmd",
            &["cmd", "/c", r"C:\scripts\creds.cmd"],
        ),
        (
            r#"creds.exe --name "say \"hi\"""#,
            &["creds.exe", "--name", r#"say "hi""#],
        ),
        // A quoted path ends in a backslash by doubling it.
        (
            r#"creds.exe --dir "C:\out\\""#,
            &["creds.exe", "--dir", r"C:\out\"],
        ),
    ]);
    // A lone backslash escapes the closing quote instead.
    assert_eq!(
        windows_shell_split(r#"creds.exe --dir "C:\out\""#),
        Err(r#"No closing quotation in string: creds.exe --dir "C:\out\""#.to_owned())
    );
}

/// The real runner: a child process whose output is read and whose exit
/// status is checked.
#[cfg(unix)]
#[test]
fn the_system_runner_runs_the_command() -> TestResult {
    let parsed = files(
        "[default]\ncredential_process = sh -c 'echo \"{\\\"Version\\\": 1, \
         \\\"AccessKeyId\\\": \\\"AKIDSHELL\\\", \\\"SecretAccessKey\\\": \\\"s\\\"}\"'\n\
         [profile failing]\ncredential_process = sh -c 'echo denied >&2; exit 3'\n",
        "",
    );
    let found = ProcessProvider::new(&parsed, "default")
        .load()?
        .ok_or("the provider found nothing")?;
    assert_eq!(found.frozen()?.access_key_id(), "AKIDSHELL");
    assert_eq!(
        message(ProcessProvider::new(&parsed, "failing").load()),
        Err("Error when retrieving credentials from custom-process: denied\n".into())
    );
    Ok(())
}

/// A directory of this test's own, with one `helper` in each of `p1`, `p2`
/// and `p3`: the first is not executable, the second runs, and the third
/// is executable but is not a program the kernel can start.
#[cfg(unix)]
fn helpers(name: &str) -> std::io::Result<std::path::PathBuf> {
    use std::os::unix::fs::PermissionsExt;
    let root = std::env::temp_dir().join(format!("{name}-{}", std::process::id()));
    for (directory, text, mode) in [
        ("p1", "#!/bin/sh\necho p1\n", 0o644),
        ("p2", "#!/bin/sh\necho p2 \"$1\"\n", 0o755),
        ("p3", "echo p3\n", 0o755),
    ] {
        let directory = root.join(directory);
        std::fs::create_dir_all(&directory)?;
        let helper = directory.join("helper");
        std::fs::write(&helper, text)?;
        std::fs::set_permissions(&helper, std::fs::Permissions::from_mode(mode))?;
    }
    Ok(root)
}

/// CPython's `subprocess` tries every directory of `PATH` until a
/// candidate starts (`_posixsubprocess`'s `child_exec`), where the C library
/// stops at one that is not executable code.
#[cfg(unix)]
#[test]
fn the_search_moves_past_a_candidate_that_cannot_be_run() -> TestResult {
    let root = helpers("credential-process-search")?;
    let joined = |directories: &[&str]| {
        std::env::join_paths(directories.iter().map(|directory| root.join(directory)))
    };
    let arguments = ["argument".to_owned()];
    for first in ["p1", "p3", "missing"] {
        let output = searched(&joined(&[first, "p2"])?, "helper", &arguments)?;
        assert_eq!(output.stdout, b"p2 argument\n", "{first}");
    }
    // The first failure that is not a missing file is the one reported.
    let refused = searched(&joined(&["missing", "p1", "p3"])?, "helper", &arguments);
    assert_eq!(
        refused.map_err(|error| error.kind()).err(),
        Some(std::io::ErrorKind::PermissionDenied)
    );
    let missing = searched(&joined(&["missing"])?, "helper", &arguments);
    assert_eq!(
        missing.map_err(|error| error.kind()).err(),
        Some(std::io::ErrorKind::NotFound)
    );
    std::fs::remove_dir_all(root)?;
    Ok(())
}
