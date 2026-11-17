//! The stack every thread a native command spawns runs on.

/// The stack every native-command thread runs on, 16 MiB. A thread given
/// this size explicitly is not sized by `RUST_MIN_STACK`, which nothing in
/// the real CLI reads.
pub const THREAD_STACK_BYTES: usize = 16 * 1024 * 1024;

/// A builder for a thread with a `THREAD_STACK_BYTES` stack; the caller
/// names the thread.
pub fn builder() -> std::thread::Builder {
    std::thread::Builder::new().stack_size(THREAD_STACK_BYTES)
}
