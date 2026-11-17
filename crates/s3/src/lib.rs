//! Native S3 commands and bounded transfer scheduling.

pub mod command;
pub mod config;
pub mod constants;
pub mod cp;
pub mod cp_args;
pub mod credentials;
pub mod download;
pub mod endpoint;
pub mod endpoint_rules;
pub mod filter;
pub mod list_stats;
pub mod local_error;
pub mod local_path;
pub mod ls;
pub mod mime;
pub mod mv;
pub mod object_settings;
pub mod request_failure;
pub mod rm;
pub mod sync;
#[cfg(any(test, feature = "testing"))]
pub mod testing;
pub mod transfer;
pub mod uri;
pub mod write_pool;

/// An otherwise parsed invocation requires the Python implementation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdmissionReason {
    UnsupportedValue,
    UnsupportedOperand,
}

pub mod scheduler;

pub mod results;
