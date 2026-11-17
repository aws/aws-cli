use super::*;
use std::process::Command;

const ONE_HOLDER_CHILD: &str = "ZAWS_PROCESS_LOCK_CHILD";
const ONE_HOLDER_TEST: &str = "process_lock::tests::one_holder_at_a_time_even_within_one_process";

#[test]
fn one_holder_at_a_time_even_within_one_process() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::var_os(ONE_HOLDER_CHILD).is_none() {
        let output = Command::new(std::env::current_exe()?)
            .args(["--exact", ONE_HOLDER_TEST, "--nocapture"])
            .env(ONE_HOLDER_CHILD, "1")
            .output()?;
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        return Ok(());
    }
    const NAME: &str = "aws-cli-native-test";
    let first = ProcessLock::new();
    let second = ProcessLock::new();
    assert!(first.acquire(NAME));
    assert!(first.acquire(NAME));
    assert!(!second.acquire(NAME));
    assert!(lock(&second.held).is_none());
    first.release();
    assert!(lock(&first.held).is_none());
    assert!(second.acquire(NAME));
    assert!(!first.acquire(NAME));
    second.release();
    second.release();
    assert!(first.acquire(NAME));
    first.release();
    Ok(())
}

#[cfg(unix)]
fn descriptor_flags(fd: libc::c_int) -> std::io::Result<libc::c_int> {
    // SAFETY: F_GETFD only reads the descriptor table.
    match unsafe { libc::fcntl(fd, libc::F_GETFD) } {
        -1 => Err(std::io::Error::last_os_error()),
        flags => Ok(flags),
    }
}

#[cfg(unix)]
#[test]
fn make_non_inheritable_marks_the_lock_file_s_descriptor_close_on_exec()
-> Result<(), Box<dyn std::error::Error>> {
    use std::os::unix::fs::MetadataExt;
    const NAME: &str = "aws-cli-native-inheritance-test";
    let held = Held::try_acquire(NAME).ok_or("another holder has the test's lock")?;
    let fd = descriptor(held.0);
    // SAFETY: the lock keeps the descriptor open until `held` drops, after
    // the borrow's last use.
    let borrowed = unsafe { std::os::fd::BorrowedFd::borrow_raw(fd) };
    let open = std::fs::File::from(borrowed.try_clone_to_owned()?).metadata()?;
    let path = format!("/tmp/aws_crt_cross_process_lock/{NAME}.lock");
    let named = std::fs::metadata(path)?;
    assert_eq!((open.dev(), open.ino()), (named.dev(), named.ino()));
    assert_eq!(descriptor_flags(fd)? & libc::FD_CLOEXEC, 0);
    assert!(make_non_inheritable(held.0));
    assert_ne!(descriptor_flags(fd)? & libc::FD_CLOEXEC, 0);
    Ok(())
}
