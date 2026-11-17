//! Scoped file locks released independently of inherited child descriptors.

use std::fs::{File, TryLockError};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::SystemTime;

/// Release an acquired lock when its owning process drops this guard.
#[derive(Debug)]
#[must_use = "dropping the guard releases the file lock"]
pub struct FileLock {
    file: File,
    path: PathBuf,
    owner: u32,
}

impl FileLock {
    /// Open the lock file and wait until exclusive access is available.
    ///
    /// # Errors
    /// Returns file creation or lock acquisition errors.
    pub fn lock(path: &Path) -> io::Result<Self> {
        let file = open(path)?;
        file.lock()?;
        Ok(Self::from_locked_file(file, path))
    }

    /// Open the lock file and acquire exclusive access without waiting.
    ///
    /// # Errors
    /// Reports contention separately from file creation or locking errors.
    pub fn try_lock(path: &Path) -> Result<Self, TryLockError> {
        let file = open(path).map_err(TryLockError::Error)?;
        file.try_lock()?;
        Ok(Self::from_locked_file(file, path))
    }

    /// Open the lock file and wait until shared access is available.
    ///
    /// # Errors
    /// Returns file creation or lock acquisition errors.
    pub fn lock_shared(path: &Path) -> io::Result<Self> {
        let file = open(path)?;
        file.lock_shared()?;
        Ok(Self::from_locked_file(file, path))
    }

    /// Open the lock file and acquire shared access without waiting.
    ///
    /// # Errors
    /// Reports contention separately from file creation or locking errors.
    pub fn try_lock_shared(path: &Path) -> Result<Self, TryLockError> {
        let file = open(path).map_err(TryLockError::Error)?;
        file.try_lock_shared()?;
        Ok(Self::from_locked_file(file, path))
    }

    /// Set the lock file's modification time to now.
    ///
    /// # Errors
    /// Returns the error setting the time.
    pub fn touch(&self) -> io::Result<()> {
        self.file.set_modified(SystemTime::now())
    }

    fn from_locked_file(file: File, path: &Path) -> Self {
        Self {
            file,
            path: path.to_owned(),
            owner: std::process::id(),
        }
    }
}

impl Drop for FileLock {
    fn drop(&mut self) {
        if self.owner != std::process::id() {
            return;
        }
        // Closing our descriptor alone leaves flock held by a child between
        // fork and exec. Explicit unlock releases this owner's lock immediately.
        loop {
            match self.file.unlock() {
                Ok(()) => break,
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(error) => {
                    // Drop cannot return an error and must not panic while
                    // unwinding. The descriptor still closes after this report.
                    let _ = writeln!(
                        io::stderr().lock(),
                        "xtask: could not release {}: {error}",
                        self.path.display()
                    );
                    break;
                }
            }
        }
    }
}

fn open(path: &Path) -> io::Result<File> {
    File::options()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(path)
}

#[cfg(test)]
mod tests;
