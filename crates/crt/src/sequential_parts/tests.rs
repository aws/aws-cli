use super::*;
use std::{ffi::OsStr, io::Write, process::Command};

const NAME: &str = "AWS_CRT_S3_FORCE_SEQUENTIAL_REQUESTS";
const CHILD: &str = "ZAWS_SEQUENTIAL_PARTS_CHILD";
const SEEN: &str = "sequential parts: ";

fn published(initial: Option<&str>) -> Result<Option<String>, Box<dyn std::error::Error>> {
    let mut command = Command::new(std::env::current_exe()?);
    command
        .args([
            "--exact",
            "sequential_parts::tests::the_setter_fills_only_an_unset_or_empty_value",
            "--nocapture",
            "--test-threads=1",
        ])
        .env(CHILD, "1");
    match initial {
        Some(value) => command.env(NAME, value),
        None => command.env_remove(NAME),
    };
    let output = command.output()?;
    assert!(output.status.success(), "{output:?}");
    let stdout = String::from_utf8(output.stdout)?;
    let line = stdout
        .lines()
        .find_map(|line| line.split_once(SEEN).map(|(_, value)| value))
        .ok_or_else(|| format!("the child reported nothing: {stdout}"))?;
    Ok(line.strip_prefix('=').map(str::to_owned))
}

#[test]
fn the_setter_fills_only_an_unset_or_empty_value() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::var_os(CHILD).is_some() {
        // SAFETY: this child runs only this test, on the harness's one test
        // thread, and nothing else in the process reads the environment.
        unsafe { request_sequential_parts() };
        let seen = std::env::var_os(NAME);
        let value = seen.as_deref().map(OsStr::to_string_lossy);
        writeln!(
            std::io::stdout(),
            "{SEEN}{}",
            value.map_or_else(|| "unset".into(), |value| format!("={value}"))
        )?;
        return Ok(());
    }
    for (initial, expected) in [
        (None, "1"),
        (Some(""), "1"),
        (Some("0"), "0"),
        (Some("1"), "1"),
        (Some("caller"), "caller"),
    ] {
        assert_eq!(
            published(initial)?.as_deref(),
            Some(expected),
            "{initial:?}"
        );
    }
    Ok(())
}
