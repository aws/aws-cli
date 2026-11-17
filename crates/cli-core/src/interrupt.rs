//! SIGINT recording in a bounded handler and cancellation on a watcher thread.
mod state;
#[cfg(unix)]
mod watcher;
#[cfg(windows)]
mod watcher_windows;
#[cfg(windows)]
use self::watcher_windows as watcher;

#[doc(inline)]
pub use state::{Canceled, Registration, Scope, Signal, State};
#[doc(inline)]
pub use watcher::{InstallError, Watcher, install_process_watcher, process_state};
/// High-level S3 cancellation message.
pub const MESSAGE: &str = "cancelled: ctrl-c received";
/// Status returned for an interrupt outside an active transfer: what a shell
/// reports for a command killed by SIGINT (128 + SIGINT), and what AWS CLI
/// v2's generic interrupt handler exits with.
pub const EXIT_STATUS: u8 = 130;

#[cfg(test)]
mod tests;

#[cfg(test)]
mod concurrency;
