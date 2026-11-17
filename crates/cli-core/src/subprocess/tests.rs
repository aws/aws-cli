use super::*;
use std::os::unix::fs::PermissionsExt;
use std::path::PathBuf;

type TestResult = Result<(), Box<dyn std::error::Error>>;

/// A directory of this test's own holding `refused`, which is not
/// executable; `unstartable`, which is executable but is not a program the
/// kernel can start; `runs`, a script that prints its first argument; and
/// `file`, which is not a directory.
fn helpers(name: &str) -> io::Result<PathBuf> {
    let root = std::env::temp_dir().join(format!("{name}-{}", std::process::id()));
    std::fs::create_dir_all(&root)?;
    for (helper, text, mode) in [
        ("refused", "#!/bin/sh\necho refused\n", 0o644),
        ("unstartable", "echo unstartable\n", 0o755),
        ("runs", "#!/bin/sh\necho runs \"$1\"\n", 0o755),
        ("file", "", 0o644),
    ] {
        let helper = root.join(helper);
        std::fs::write(&helper, text)?;
        std::fs::set_permissions(&helper, std::fs::Permissions::from_mode(mode))?;
    }
    Ok(root)
}

fn os_error(result: io::Result<Output>) -> Option<i32> {
    result.err().and_then(|error| error.raw_os_error())
}

#[test]
#[cfg_attr(miri, ignore)]
fn a_candidate_the_kernel_cannot_start_is_passed_over() -> TestResult {
    let root = helpers("subprocess-passed-over")?;
    let arguments = ["argument".to_owned()];
    for first in ["refused", "unstartable", "missing", "file/helper"] {
        let candidates = [root.join(first), root.join("runs")];
        let output = output(&candidates, "helper", &arguments)?;
        assert_eq!(output.stdout, b"runs argument\n", "{first}");
    }
    std::fs::remove_dir_all(root)?;
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore)]
fn the_first_failure_other_than_a_missing_file_is_reported() -> TestResult {
    let root = helpers("subprocess-first-failure")?;
    let failed = |names: &[&str]| {
        let candidates: Vec<_> = names.iter().map(|name| root.join(name)).collect();
        os_error(output(&candidates, "helper", &[]))
    };
    assert_eq!(
        failed(&["missing", "unstartable", "refused"]),
        Some(libc::ENOEXEC)
    );
    assert_eq!(
        failed(&["missing", "refused", "unstartable"]),
        Some(libc::EACCES)
    );
    // With only missing files, the last candidate's failure is reported.
    assert_eq!(failed(&["missing", "file/helper"]), Some(libc::ENOTDIR));
    assert_eq!(failed(&["file/helper", "missing"]), Some(libc::ENOENT));
    std::fs::remove_dir_all(root)?;
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore)]
fn the_output_and_exit_status_are_captured() -> TestResult {
    let script = "echo out; echo err >&2; exit 3".to_owned();
    let output = output(&["/bin/sh"], "sh", &["-c".to_owned(), script])?;
    assert_eq!(output.status.code(), Some(3));
    assert_eq!(output.stdout, b"out\n");
    assert_eq!(output.stderr, b"err\n");
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore)]
fn argv0_is_the_name_given() -> TestResult {
    // With no command name after the command string, `sh -c` sets `$0` to
    // its own `argv[0]`.
    let script = "echo \"$0\"".to_owned();
    let output = output(&["/bin/sh"], "named-shell", &["-c".to_owned(), script])?;
    assert_eq!(output.stdout, b"named-shell\n");
    Ok(())
}

#[test]
fn a_nul_byte_is_refused_before_anything_starts() {
    let refused = |result: io::Result<Output>| result.err().map(|error| error.kind());
    let invalid = Some(io::ErrorKind::InvalidInput);
    assert_eq!(refused(output(&["/bin/sh\0"], "sh", &[])), invalid);
    assert_eq!(refused(output(&["/bin/sh"], "s\0h", &[])), invalid);
    assert_eq!(
        refused(output(&["/bin/sh"], "sh", &["\0".to_owned()])),
        invalid
    );
}

#[test]
fn no_candidate_is_a_missing_file() {
    let none: [&str; 0] = [];
    assert_eq!(
        output(&none, "helper", &[]).err().map(|error| error.kind()),
        Some(io::ErrorKind::NotFound)
    );
}
