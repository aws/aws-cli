use super::*;
#[test]
fn arguments_use_python_list_repr() -> io::Result<()> {
    let mut out = Vec::new();
    write_arguments(&mut out, &["s3", "it's", "line\n\\"])?;
    assert_eq!(
        out,
        b"Arguments entered to CLI: ['s3', \"it's\", 'line\\n\\\\']"
    );
    Ok(())
}

#[cfg(unix)]
#[test]
fn argument_repr_preserves_path_bytes_and_escapes_only_ascii() -> io::Result<()> {
    use std::{ffi::OsStr, os::unix::ffi::OsStrExt};
    let mut output = Vec::new();
    write_arguments(
        &mut output,
        &[
            OsStr::from_bytes(b"s3"),
            OsStr::from_bytes(b"/tmp/it's-\xff\n"),
            OsStr::from_bytes(b"\"\x01\x7f\xc2\x85"),
        ],
    )?;
    assert_eq!(
        output,
        b"Arguments entered to CLI: ['s3', \"/tmp/it's-\xff\\n\", '\"\\x01\\x7f\xc2\x85']"
    );
    Ok(())
}

#[cfg(windows)]
#[test]
fn argument_repr_preserves_windows_wtf8_path_units() -> io::Result<()> {
    use std::{ffi::OsString, os::windows::ffi::OsStringExt};
    let mut output = Vec::new();
    let value = OsString::from_wide(&[0x43, 0x3a, 0x5c, 0xd800, 0x61, 0xdc00]);
    write_arguments(&mut output, &[value])?;
    assert_eq!(
        output,
        b"Arguments entered to CLI: ['C:\\\\\xed\xa0\x80a\xed\xb0\x80']"
    );
    Ok(())
}
#[test]
fn native_records_match_normalized_python_framing() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::var_os("ZAWS_DEBUG_CHILD").is_some() {
        let logger = Logger::new(true);
        logger.arguments(&["--debug", "s3", "it's", "line\n\\"]);
        logger.record("awscli.native.endpoint", "Endpoint URL: http://127.0.0.1:9");
        logger.record_bytes(
            "awscli.native.config",
            b"User agent app id: ab\0cd (from profile key sdk_ua_app_id)",
        );
        #[cfg(unix)]
        {
            use std::{ffi::OsStr, os::unix::ffi::OsStrExt};
            logger.arguments(&[OsStr::from_bytes(b"path-\xff")]);
        }
        drop(logger);
        return Ok(());
    }
    let stderr = child_stderr("debug::tests::native_records_match_normalized_python_framing")?;
    #[cfg_attr(
        not(unix),
        expect(unused_mut, reason = "only Unix appends a raw path record")
    )]
    let mut expected: Vec<&[u8]> = vec![
        b" - awscli.clidriver - DEBUG - Arguments entered to CLI: ['--debug\
        ', 's3', \"it's\", 'line\\n\\\\']",
        b" - awscli.native.endpoint - DEBUG - Endpoint URL: http://127.0.0.1:9",
        b" - awscli.native.config - DEBUG - User agent app id: ab",
    ];
    #[cfg(unix)]
    expected.push(b" - awscli.clidriver - DEBUG - Arguments entered to CLI: ['path-\xff']");
    assert_eq!(untimestamped(&stderr)?, expected);
    Ok(())
}
#[test]
fn records_survive_a_failed_logger_installation() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::var_os("ZAWS_DEBUG_CHILD").is_some() {
        use std::sync::atomic::Ordering;
        super::native::FAIL_INSTALLATION.store(true, Ordering::Release);
        let logger = Logger::new(true);
        let retained = Logger::new(true);
        logger.arguments(&["--debug", "s3", "ls"]);
        retained.record("awscli.native.endpoint", "Endpoint URL: http://127.0.0.1:9");
        drop(retained);
        drop(logger);
        Logger::new(false).record("awscli.native", "after shutdown");
        Logger::new(true).record("awscli.native", "enabled again");
        return Ok(());
    }
    let stderr = child_stderr("debug::tests::records_survive_a_failed_logger_installation")?;
    let expected: Vec<&[u8]> = vec![
        b" - awscli.native - DEBUG - Unable to initialize CRT debug logger",
        b" - awscli.clidriver - DEBUG - Arguments entered to CLI: ['--debug', 's3', 'ls']",
        b" - awscli.native.endpoint - DEBUG - Endpoint URL: http://127.0.0.1:9",
        b" - awscli.native - DEBUG - enabled again",
    ];
    assert_eq!(untimestamped(&stderr)?, expected);
    Ok(())
}
fn child_stderr(test: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let output = std::process::Command::new(std::env::current_exe()?)
        .args(["--exact", test, "--nocapture"])
        .env("ZAWS_DEBUG_CHILD", "1")
        .output()?;
    assert!(output.status.success());
    Ok(output.stderr)
}
fn untimestamped(stderr: &[u8]) -> Result<Vec<&[u8]>, String> {
    const SHAPE: &[u8; 23] = b"0000-00-00 00:00:00,000";
    let mut records = Vec::new();
    for line in stderr.split(|&byte| byte == b'\n') {
        if line.is_empty() {
            continue;
        }
        let line = if cli_core::output::STREAMS_TRANSLATE_NEWLINES {
            line.strip_suffix(b"\r")
                .ok_or_else(|| format!("record without CRLF: {}", line.escape_ascii()))?
        } else {
            line
        };
        let shaped = line.split_at_checked(SHAPE.len()).filter(|(stamp, _)| {
            stamp.iter().zip(SHAPE).all(|(&byte, &shape)| {
                if shape == b'0' {
                    byte.is_ascii_digit()
                } else {
                    byte == shape
                }
            })
        });
        let Some((_, record)) = shaped else {
            return Err(format!("unframed record: {}", line.escape_ascii()));
        };
        records.push(record);
    }
    Ok(records)
}
