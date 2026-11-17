//! Completion notifications retained until CRT shutdown callbacks finish.
use std::sync::{Condvar, Mutex, MutexGuard};

pub(crate) fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}
pub(crate) fn wait<'a, T>(wake: &Condvar, guard: MutexGuard<'a, T>) -> MutexGuard<'a, T> {
    wake.wait(guard)
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

/// A sticky notification supporting completion before any waiter arrives.
#[derive(Debug, Default)]
pub struct ShutdownSignal {
    complete: Mutex<bool>,
    wake: Condvar,
}
impl ShutdownSignal {
    /// Creates an incomplete signal.
    pub fn new() -> Self {
        Self::default()
    }
    /// Waits until completion, including repeated waits after completion.
    pub fn wait(&self) {
        self.wait_notifying(|| ());
    }
    fn wait_notifying(&self, started: impl FnOnce()) {
        let mut complete = lock(&self.complete);
        started();
        while !*complete {
            complete = wait(&self.wake, complete);
        }
    }
    /// Completes the signal and wakes its waiter.
    pub fn complete(&self) {
        let mut complete = lock(&self.complete);
        *complete = true;
        self.wake.notify_all();
        drop(complete);
    }
    /// Reports whether completion has arrived.
    pub fn is_complete(&self) -> bool {
        *lock(&self.complete)
    }
}
#[cfg(test)]
mod tests;
