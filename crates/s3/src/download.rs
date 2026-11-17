//! Bounded positional, mapped, and direct download writers behind one
//! command-wide writer service.
mod config;
mod diagnostics;
mod error;
mod io;
mod locality;
pub mod memory;
mod output;
mod pages;
mod prefault;
mod service;

pub mod platform;
pub mod range;
pub mod stream_copy;
#[cfg(any(test, feature = "testing"))]
pub mod testing;

#[doc(inline)]
pub use config::{
    CHUNK_BYTES, EVICTION_BYTES, MAX_NODES, NumaConfig, NumaMode, NumaPoolMode, PREFAULT_LOOKAHEAD,
    PREFAULT_THREADS_PER_SHARD, PREFAULT_WINDOW, PrefaultMode, Requirement, STRIPE_BYTES,
    WriterConfig, WriterMode,
};
#[doc(inline)]
pub use error::{CloseError, WriteError};
#[doc(inline)]
pub use locality::{DownloadLocality, LocalityContext};
#[doc(inline)]
pub use output::{Body, WriterStats};
#[doc(inline)]
pub use service::{
    CUSTOM_WRITER_SIZE_MIN, OutputClass, OutputSlot, SharedConfig, SharedOutput,
    SharedWriterService, WORKER_COUNT_MAX, WorkerSpawner, queue_jobs_per_shard,
    shared_worker_count,
};
#[doc(inline)]
pub use stream_copy::CopyMode;
/// Whether the mapped writer's `nt` and `rep` copy modes run in this build:
/// the S3 settings default to `nt` and accept either only when they do.
pub const COPY_FAST_MODES_AVAILABLE: bool = stream_copy::FAST_MODES_AVAILABLE;

fn lock<T>(value: &std::sync::Mutex<T>) -> std::sync::MutexGuard<'_, T> {
    value
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}
fn wait<'a, T>(
    wake: &std::sync::Condvar,
    guard: std::sync::MutexGuard<'a, T>,
) -> std::sync::MutexGuard<'a, T> {
    wake.wait(guard)
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}
