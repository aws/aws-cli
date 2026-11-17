use super::*;
use std::fs::File;

#[test]
fn cli_suites_hold_an_exclusive_lock_until_the_guard_is_dropped() -> Result<(), TaskError> {
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(io::Error::other)?
        .as_nanos();
    let root =
        std::env::temp_dir().join(format!("awscli-suite-lock-{}-{stamp}", std::process::id()));
    let guard = cli_test_guard(&root)?;
    let observer = File::options()
        .read(true)
        .write(true)
        .open(root.join("target/cli-tests.lock"))?;
    assert!(matches!(
        observer.try_lock(),
        Err(std::fs::TryLockError::WouldBlock)
    ));
    drop(guard);
    observer.try_lock().map_err(io::Error::other)?;
    drop(observer);
    fs::remove_dir_all(root)?;
    Ok(())
}

#[test]
fn accepts_built_binaries_and_compilers() {
    for path in ["target/release-safe/aws", "clang", "cargo"] {
        assert!(validate(&Command::new(path)).is_ok());
    }
}

#[test]
fn rejects_home_mutation() {
    assert!(validate(Command::new("cargo").env("HOME", "/tmp/fake")).is_err());
    assert!(validate(Command::new("cargo").env_remove("HOME")).is_err());
}
