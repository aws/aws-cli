//! Standalone consumers of the prepared native dependency interfaces.

mod consumers;

use crate::TaskError;
use std::path::Path;

pub fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    match args {
        [command, args @ ..] if command == "consumers" => consumers::run(root, args),
        _ => Err(TaskError::Message("package consumers".into())),
    }
}
