use std::ffi::{OsStr, OsString};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

type TestResult = Result<(), Box<dyn std::error::Error>>;

struct Directory(PathBuf);

impl Drop for Directory {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn directory() -> std::io::Result<Directory> {
    use std::sync::atomic::{AtomicUsize, Ordering};
    static NEXT: AtomicUsize = AtomicUsize::new(0);
    let path = std::env::temp_dir().join(format!(
        "aws-pyload-inspect-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::create_dir(&path)?;
    Ok(Directory(path))
}

fn inspector() -> Command {
    Command::new(env!("CARGO_BIN_EXE_aws-python-payload-inspect"))
}

fn child(path: &Path, name: &[u8]) -> PathBuf {
    path.join(OsString::from_vec(name.to_vec()))
}

fn bytes(path: &Path) -> &[u8] {
    path.as_os_str().as_bytes()
}

fn refuses_non_utf8_name(error: &std::io::Error) -> bool {
    cfg!(target_os = "macos") && error.raw_os_error() == Some(92)
}

fn assert_failure(output: &Output, code: i32, stderr: &[u8]) {
    assert_eq!(
        output.stderr.escape_ascii().to_string(),
        stderr.escape_ascii().to_string()
    );
    assert_eq!(output.status.code(), Some(code));
    assert!(output.stdout.is_empty());
}

fn open_failure(path: &Path, name: &str) -> Vec<u8> {
    [
        b"failed to open ",
        bytes(path),
        b": ",
        name.as_bytes(),
        b"\n",
    ]
    .concat()
}

fn payload() -> Vec<u8> {
    const NAME: &[u8] = b"awscli/botocore/data/partitions.json";
    let mut bytes = b"ZIPPY003".to_vec();
    for value in [1u32, 16, 0, 2] {
        bytes.extend(value.to_le_bytes());
    }
    for offset in [0x48u64, 0x68, 0x88, 0xa0, 0xc4, 0] {
        bytes.extend(offset.to_le_bytes());
    }
    let mut control = [0x80; 16];
    control[7] = 0x0c;
    bytes.extend(control);
    bytes.extend(control);
    bytes.extend([0; 32]);
    for value in [0, NAME.len() as u32, 0, 2, 2] {
        bytes.extend(value.to_le_bytes());
    }
    bytes.extend([4, 0, 0, 0]);
    bytes.extend(NAME);
    bytes.extend(b"{}");
    bytes
}

fn elf(payload: &[u8]) -> Vec<u8> {
    const NAMES: &[u8] = b"\0.shstrtab\0.pyload\0";
    const SECTION_SIZE: usize = 64;
    const SHF_ALLOC: u64 = 2;
    let names = 64;
    let data = names + NAMES.len();
    let table = (data + payload.len()).next_multiple_of(8);
    let mut bytes = vec![0; table + 3 * SECTION_SIZE];
    let mut put = |at: usize, value: u64, width: usize| {
        bytes[at..at + width].copy_from_slice(&value.to_le_bytes()[..width]);
    };
    put(40, table as u64, 8);
    put(58, SECTION_SIZE as u64, 2);
    put(60, 3, 2);
    put(62, 1, 2);
    for (index, name, flags, offset, size) in [
        (1, 1, 0, names, NAMES.len()),
        (2, 11, SHF_ALLOC, data, payload.len()),
    ] {
        let at = table + index * SECTION_SIZE;
        put(at, name, 4);
        put(at + 8, flags, 8);
        put(at + 24, offset as u64, 8);
        put(at + 32, size as u64, 8);
    }
    bytes[..7].copy_from_slice(b"\x7fELF\x02\x01\x01");
    bytes[names..data].copy_from_slice(NAMES);
    bytes[data..data + payload.len()].copy_from_slice(payload);
    bytes
}

fn executable(directory: &Directory) -> std::io::Result<PathBuf> {
    let path = directory.0.join("aws");
    std::fs::write(&path, elf(&payload()))?;
    Ok(path)
}

#[test]
fn fixture_executable_lists_its_payload_entry() -> TestResult {
    let directory = directory()?;
    let output = inspector()
        .arg(executable(&directory)?)
        .arg("--list")
        .output()?;
    assert_eq!(
        output.stdout.escape_ascii().to_string(),
        "awscli/botocore/data/partitions.json kind=resource package=false \
        compressed=false stored=2 raw=2\\n"
    );
    assert!(output.stderr.is_empty());
    assert_eq!(output.status.code(), Some(0));
    Ok(())
}

#[test]
fn missing_executable_reports_failed_to_open() -> TestResult {
    let directory = directory()?;
    let path = directory.0.join("missing");
    let output = inspector().arg(&path).output()?;
    assert_failure(&output, 1, &open_failure(&path, "FileNotFound"));
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn open_failures_report_openat_error_names_and_non_regular_files() -> TestResult {
    let directory = directory()?;
    let file = directory.0.join("file");
    std::fs::write(&file, b"")?;
    let looping = directory.0.join("loop");
    std::os::unix::fs::symlink("loop", &looping)?;
    let long = directory.0.join("a".repeat(5000));
    for (path, name) in [
        (file.join("x"), "NotDir"),
        (looping, "SymLinkLoop"),
        (long, "NameTooLong"),
    ] {
        let output = inspector().arg(&path).output()?;
        assert_failure(&output, 1, &open_failure(&path, name));
    }
    let output = inspector().arg(&directory.0).output()?;
    let message = [b"error: ", bytes(&directory.0), b" is not a regular file\n"].concat();
    assert_failure(&output, 1, &message);
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn unreadable_executable_reports_access_denied() -> TestResult {
    use std::os::unix::fs::PermissionsExt;
    let directory = directory()?;
    let path = directory.0.join("aws");
    std::fs::write(&path, b"")?;
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o000))?;
    // A privileged runner opens the file anyway; there is no EACCES to name.
    if std::fs::File::open(&path).is_ok() {
        return Ok(());
    }
    let output = inspector().arg(&path).output()?;
    assert_failure(&output, 1, &open_failure(&path, "AccessDenied"));
    Ok(())
}

#[test]
fn non_utf8_paths_are_reported_with_their_raw_bytes() -> TestResult {
    let directory = directory()?;
    let missing = child(&directory.0, b"\xff");
    let output = inspector().arg(&missing).output()?;
    assert_failure(&output, 1, &open_failure(&missing, "FileNotFound"));
    let script = child(&directory.0, b"caf\xe9");
    match std::fs::write(&script, b"#!/bin/sh\n") {
        Err(error) if refuses_non_utf8_name(&error) => return Ok(()),
        result => result?,
    }
    let output = inspector().arg(&script).output()?;
    let message = [
        b"error: ",
        bytes(&script),
        b" is not an ELF or Mach-O executable\n",
    ]
    .concat();
    assert_failure(&output, 1, &message);
    Ok(())
}

#[test]
fn non_utf8_arguments_select_modes_and_services_by_bytes() -> TestResult {
    let directory = directory()?;
    let executable = executable(&directory)?;
    let output = inspector()
        .arg(&executable)
        .arg(OsStr::from_bytes(b"--list\xff"))
        .output()?;
    assert_eq!(output.status.code(), Some(2));
    assert!(
        output
            .stderr
            .starts_with(b"usage: aws-python-payload-inspect")
    );
    let output = inspector()
        .arg(&executable)
        .arg("--expect-model-only")
        .arg(OsStr::from_bytes(b"s\xff3"))
        .output()?;
    assert_failure(
        &output,
        1,
        b"error: invalid expected service name: s\xff3\n",
    );
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn stdout_write_failure_reports_write_failed() -> TestResult {
    let directory = directory()?;
    let executable = executable(&directory)?;
    for mode in [None, Some("--list")] {
        let full = std::fs::OpenOptions::new().write(true).open("/dev/full")?;
        let output = inspector()
            .arg(&executable)
            .args(mode)
            .stdout(full)
            .output()?;
        assert_failure(&output, 1, b"error: WriteFailed\n");
    }
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn header_read_ignores_the_reported_size() -> TestResult {
    let output = inspector().arg("/proc/self/mem").output()?;
    assert_failure(
        &output,
        1,
        b"error: failed to read /proc/self/mem: InputOutput\n",
    );
    Ok(())
}
