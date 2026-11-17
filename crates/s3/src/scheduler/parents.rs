use super::*;
use std::collections::BTreeSet;
pub(super) const PARENT_COUNT_MAX: usize = 4096;
pub(super) const PARENT_BYTES_MAX: usize = 1024 * 1024;
#[derive(Debug, Default)]
pub(super) struct ParentDirectoryCache {
    paths: BTreeSet<PathBuf>,
    bytes: usize,
}
impl ParentDirectoryCache {
    pub fn ensure(
        &mut self,
        operations: &dyn Operations,
        destination: &Path,
    ) -> Result<(), &'static str> {
        let Some(parent) = destination.parent() else {
            return Ok(());
        };
        if parent.as_os_str().is_empty() || parent == Path::new(".") || self.paths.contains(parent)
        {
            return Ok(());
        }
        // No directory can be created at a parent holding a NUL.
        if transfer::path_holds_nul(parent) {
            return Err(crate::local_error::BAD_PATH_NAME);
        }
        operations
            .create_parent(parent)
            .map_err(|error| transfer::create_dir_error_name(&error))?;
        self.remember(parent);
        Ok(())
    }
    pub fn remember(&mut self, parent: &Path) {
        let len = parent.as_os_str().len();
        if self.paths.len() == PARENT_COUNT_MAX || len > PARENT_BYTES_MAX - self.bytes {
            return;
        }
        if self.paths.insert(parent.to_path_buf()) {
            self.bytes += len;
        }
    }
}
