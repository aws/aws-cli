use super::*;

#[test]
fn dropping_guard_releases_lock_with_an_inherited_descriptor() -> io::Result<()> {
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(io::Error::other)?
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "awscli-inherited-lock-{}-{stamp}",
        std::process::id()
    ));
    let guard = FileLock::lock(&path)?;
    // A duplicate shares the same open file description as an inherited
    // descriptor in another thread's child between fork and exec.
    let inherited = guard.file.try_clone()?;
    let observer = open(&path)?;
    assert!(matches!(observer.try_lock(), Err(TryLockError::WouldBlock)));
    drop(guard);
    observer.try_lock().map_err(io::Error::other)?;
    drop(inherited);
    assert!(matches!(
        FileLock::try_lock(&path),
        Err(TryLockError::WouldBlock)
    ));
    observer.unlock()?;
    drop(observer);
    std::fs::remove_file(path)?;
    Ok(())
}
