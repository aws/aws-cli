//! Completion workers with queue capacity equal to the scheduler's occupied slots.
use std::collections::VecDeque;
use std::io;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex, MutexGuard};
use std::thread::{self, JoinHandle};
use std::time::Instant;

struct Queue<T> {
    jobs: VecDeque<T>,
    closed: bool,
}
struct Shared<T> {
    queue: Mutex<Queue<T>>,
    capacity: usize,
    ready: Condvar,
    space: Condvar,
    execute: Box<dyn Fn(T) + Send + Sync>,
    high_water: AtomicU64,
    executed: AtomicU64,
    execute_ns: AtomicU64,
}
/// New work was rejected after the completion queue closed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Closed;
impl std::fmt::Display for Closed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("write pool closed")
    }
}
impl std::error::Error for Closed {}

pub struct WritePool<T> {
    shared: Arc<Shared<T>>,
    worker_count: usize,
    name: &'static str,
    threads: Vec<JoinHandle<()>>,
}
impl<T> std::fmt::Debug for WritePool<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("WritePool")
            .field("capacity", &self.shared.capacity)
            .field("workers", &self.threads.len())
            .finish_non_exhaustive()
    }
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Stats {
    pub queue_hwm: u64,
    pub executed: u64,
    pub execute_ns: u64,
}
impl<T: Send + 'static> WritePool<T> {
    pub fn new(
        worker_count: usize,
        capacity: usize,
        execute: impl Fn(T) + Send + Sync + 'static,
    ) -> Self {
        assert!(worker_count > 0 && capacity > 0);
        Self {
            shared: Arc::new(Shared {
                queue: Mutex::new(Queue {
                    jobs: VecDeque::new(),
                    closed: false,
                }),
                capacity,
                ready: Condvar::new(),
                space: Condvar::new(),
                execute: Box::new(execute),
                high_water: AtomicU64::new(0),
                executed: AtomicU64::new(0),
                execute_ns: AtomicU64::new(0),
            }),
            worker_count,
            name: "s3-finish",
            threads: Vec::with_capacity(worker_count),
        }
    }
    /// Names the workers `{name}-{index}` instead of after finish work.
    #[must_use]
    pub fn named(mut self, name: &'static str) -> Self {
        self.name = name;
        self
    }
    /// Reserves the whole ring, then starts the workers. A ring that cannot
    /// be reserved fails the start with `OutOfMemory` instead of aborting.
    pub fn start(&mut self) -> io::Result<()> {
        assert!(self.threads.is_empty());
        lock(&self.shared.queue)
            .jobs
            .try_reserve_exact(self.shared.capacity)
            .map_err(|_| io::Error::from(io::ErrorKind::OutOfMemory))?;
        for index in 0..self.worker_count {
            let shared = Arc::clone(&self.shared);
            let result = thread::Builder::new()
                .stack_size(cli_core::thread::THREAD_STACK_BYTES)
                .name(format!("{}-{index}", self.name))
                .spawn(move || run(&shared));
            match result {
                Ok(thread) => self.threads.push(thread),
                Err(error) => {
                    self.close();
                    self.join();
                    return Err(error);
                }
            }
        }
        Ok(())
    }
}
impl<T> WritePool<T> {
    pub fn try_push(&self, job: T) -> Result<(), Closed> {
        let mut queue = lock(&self.shared.queue);
        if queue.closed {
            return Err(Closed);
        }
        assert!(
            queue.jobs.len() < self.shared.capacity,
            "finish queue exceeded reserved slots"
        );
        queue.jobs.push_back(job);
        self.shared
            .high_water
            .fetch_max(queue.jobs.len() as u64, Ordering::Relaxed);
        self.shared.ready.notify_one();
        Ok(())
    }
    pub fn push(&self, job: T) -> Result<(), Closed> {
        let mut queue = lock(&self.shared.queue);
        while queue.jobs.len() == self.shared.capacity && !queue.closed {
            queue = self
                .shared
                .space
                .wait(queue)
                .unwrap_or_else(|e| e.into_inner());
        }
        if queue.closed {
            return Err(Closed);
        }
        queue.jobs.push_back(job);
        self.shared
            .high_water
            .fetch_max(queue.jobs.len() as u64, Ordering::Relaxed);
        self.shared.ready.notify_one();
        Ok(())
    }
    pub fn close(&self) {
        lock(&self.shared.queue).closed = true;
        self.shared.ready.notify_all();
        self.shared.space.notify_all();
    }
    pub fn join(&mut self) {
        for thread in self.threads.drain(..) {
            if let Err(payload) = thread.join() {
                std::panic::resume_unwind(payload);
            }
        }
    }
    pub fn stats(&self) -> Stats {
        Stats {
            queue_hwm: self.shared.high_water.load(Ordering::Relaxed),
            executed: self.shared.executed.load(Ordering::Relaxed),
            execute_ns: self.shared.execute_ns.load(Ordering::Relaxed),
        }
    }
}
impl<T> Drop for WritePool<T> {
    fn drop(&mut self) {
        self.close();
        self.join();
        assert!(
            lock(&self.shared.queue).jobs.is_empty(),
            "unexecuted finish jobs"
        );
    }
}
fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(|e| e.into_inner())
}
fn run<T>(shared: &Shared<T>) {
    loop {
        let mut queue = lock(&shared.queue);
        while queue.jobs.is_empty() && !queue.closed {
            queue = shared.ready.wait(queue).unwrap_or_else(|e| e.into_inner());
        }
        let Some(job) = queue.jobs.pop_front() else {
            return;
        };
        shared.space.notify_one();
        drop(queue);
        let start = Instant::now();
        (shared.execute)(job);
        let elapsed = u64::try_from(start.elapsed().as_nanos()).unwrap_or(u64::MAX);
        shared.execute_ns.fetch_add(elapsed, Ordering::Relaxed);
        shared.executed.fetch_add(1, Ordering::Relaxed);
    }
}

#[cfg(test)]
mod tests;
