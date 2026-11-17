use std::{
    ffi::OsString,
    io,
    os::unix::ffi::{OsStrExt, OsStringExt},
    path::{Path, PathBuf},
    process::Command,
};

struct Directory(PathBuf);

impl Drop for Directory {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn directory() -> io::Result<Directory> {
    static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    let path = std::env::temp_dir().join(format!(
        "aws-cli-raw-argv-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    std::fs::create_dir(&path)?;
    Ok(Directory(path))
}

fn command(directory: &Path) -> Command {
    let mut command = Command::new(env!("CARGO_BIN_EXE_aws"));
    for (name, _) in std::env::vars_os() {
        if name != "HOME" {
            command.env_remove(name);
        }
    }
    command.current_dir(directory).envs([
        ("AWS_CONFIG_FILE", "/nonexistent/aws-cli-native/config"),
        (
            "AWS_SHARED_CREDENTIALS_FILE",
            "/nonexistent/aws-cli-native/credentials",
        ),
        ("AWS_ACCESS_KEY_ID", "local-test"),
        ("AWS_SECRET_ACCESS_KEY", "local-test"),
        ("AWS_EC2_METADATA_DISABLED", "true"),
        ("AWS_CLI_NATIVE_ROUTER", "native"),
        ("AWS_CLI_AUTO_PROMPT", "off"),
        ("AWS_CLI_ERROR_FORMAT", "enhanced"),
        ("AWS_REGION", "us-east-1"),
    ]);
    command
}

#[test]
fn missing_local_source_keeps_original_argument_and_diagnostic_bytes() -> io::Result<()> {
    let directory = directory()?;
    for name in [b"missing-\xff".as_slice(), b"quote'\xfe\nname"] {
        let path = directory.0.join(OsString::from_vec(name.to_vec()));
        let output = command(&directory.0)
            .args(["s3", "cp"])
            .arg(&path)
            .args([
                "s3://bucket/key",
                "--no-sign-request",
                "--endpoint-url",
                "http://127.0.0.1:9",
            ])
            .output()?;
        assert_eq!(output.status.code(), Some(255));
        assert!(output.stdout.is_empty());
        let mut expected = b"\naws: [ERROR]: The user-provided path ".to_vec();
        expected.extend_from_slice(path.as_os_str().as_bytes());
        expected.extend_from_slice(b" does not exist.\n");
        assert_eq!(output.stderr, expected);
    }
    Ok(())
}

const SEQUENTIAL_PARTS: &str = "AWS_CRT_S3_FORCE_SEQUENTIAL_REQUESTS";

#[test]
fn native_commands_request_sequential_parts_before_any_client() -> io::Result<()> {
    let directory = directory()?;
    for initial in [None, Some("")] {
        let mut command = command(&directory.0);
        match initial {
            Some(value) => command.env(SEQUENTIAL_PARTS, value),
            None => command.env_remove(SEQUENTIAL_PARTS),
        };
        let output = command
            .args([
                "s3",
                "ls",
                "s3://bucket",
                "--debug",
                "--no-sign-request",
                "--endpoint-url",
                "http://127.0.0.1:9",
            ])
            .env("AWS_MAX_ATTEMPTS", "2")
            .output()?;
        assert_ne!(output.status.code(), Some(0));
        let expected: &[u8] = b"AWS_CRT_S3_FORCE_SEQUENTIAL_REQUESTS is set, so downloads \
            request their parts in object order.";
        assert!(
            output
                .stderr
                .windows(expected.len())
                .any(|window| window == expected),
            "{initial:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    Ok(())
}

#[test]
fn python_routed_commands_leave_sequential_parts_alone() -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    let directory = directory()?;
    let seen = directory.0.join("seen");
    let script = directory.0.join("credentials.sh");
    std::fs::write(
        &script,
        format!(
            "#!/bin/sh\nprintf '%s' \"${{{SEQUENTIAL_PARTS}-unset}}\" > '{}'\n\
             printf '%s' '{{\"Version\": 1, \"AccessKeyId\": \"local\", \
             \"SecretAccessKey\": \"local\"}}'\n",
            seen.display()
        ),
    )?;
    std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o700))?;
    let config = directory.0.join("config");
    std::fs::write(
        &config,
        format!("[default]\ncredential_process = {}\n", script.display()),
    )?;
    for (initial, expected) in [(None, "unset"), (Some(""), ""), (Some("0"), "0")] {
        let _ = std::fs::remove_file(&seen);
        let mut command = command(&directory.0);
        match initial {
            Some(value) => command.env(SEQUENTIAL_PARTS, value),
            None => command.env_remove(SEQUENTIAL_PARTS),
        };
        let output = command
            .args([
                "s3api",
                "list-buckets",
                "--endpoint-url",
                "http://127.0.0.1:9",
            ])
            .env("AWS_CONFIG_FILE", &config)
            .env("AWS_MAX_ATTEMPTS", "1")
            .env_remove("AWS_CLI_NATIVE_ROUTER")
            .env_remove("AWS_ACCESS_KEY_ID")
            .env_remove("AWS_SECRET_ACCESS_KEY")
            .output()?;
        assert_ne!(output.status.code(), Some(0));
        assert_eq!(
            std::fs::read_to_string(&seen)?,
            expected,
            "{initial:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    Ok(())
}
