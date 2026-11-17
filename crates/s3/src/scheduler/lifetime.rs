use super::*;
use std::{mem::ManuallyDrop, ops::Deref};
#[derive(Debug, Default)]
pub(super) struct Lifetimes {
    count: Mutex<usize>,
    wake: Condvar,
}
#[derive(Debug)]
pub(super) struct Held<T> {
    value: ManuallyDrop<T>,
    lifetimes: Arc<Lifetimes>,
}
impl Lifetimes {
    pub fn hold<T>(self: &Arc<Self>, value: T) -> Held<T> {
        *lock(&self.count) += 1;
        Held {
            value: ManuallyDrop::new(value),
            lifetimes: Arc::clone(self),
        }
    }
    pub fn drain(&self) {
        let mut count = lock(&self.count);
        while *count != 0 {
            count = wait(&self.wake, count);
        }
    }
}
impl<T> Deref for Held<T> {
    type Target = T;
    fn deref(&self) -> &T {
        &self.value
    }
}
impl<T> Drop for Held<T> {
    fn drop(&mut self) {
        // SAFETY: `value` is never used again; this is its only drop.
        unsafe { ManuallyDrop::drop(&mut self.value) };
        let mut count = lock(&self.lifetimes.count);
        assert!(*count > 0);
        *count -= 1;
        self.lifetimes.wake.notify_all();
    }
}

#[cfg(test)]
mod tests;
