//! Embedded CPython startup, payload imports, and process exit handling.

pub mod helpers;

pub mod configuration;

#[cfg(all(test, aws_python_static, not(miri)))]
mod runtime_dependencies;

pub mod exit_status;
pub mod ffi;
pub mod finder;
mod lifecycle;
mod runner;
#[doc(inline)]
pub use runner::{Invocation, RunError};
