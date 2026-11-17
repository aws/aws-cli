use super::{
    super::{
        LocalityContext, PREFAULT_LOOKAHEAD, PREFAULT_THREADS_PER_SHARD, WriteError,
        platform::Platform, service::WorkerSpawner,
    },
    MinorFaults, Shared, lock, populate, wait,
};
use std::{
    collections::VecDeque,
    sync::{
        Arc, Condvar, Mutex,
        atomic::{AtomicUsize, Ordering},
    },
    thread::JoinHandle,
};

#[derive(Debug)]
struct Work {
    mapping: Arc<Shared>,
    window: usize,
    reserved: usize,
}
#[derive(Debug)]
struct State {
    ready: VecDeque<Arc<Shared>>,
    attached: usize,
    reserved: usize,
    lookahead: usize,
    startup_completed: usize,
    startup_error: Option<WriteError>,
    closed: bool,
}
#[derive(Debug)]
pub(crate) struct Pool {
    state: Mutex<State>,
    changed: Condvar,
    outstanding: AtomicUsize,
    locality: LocalityContext,
    platform: Arc<dyn Platform>,
}
impl Pool {
    pub(super) fn locality(&self) -> &LocalityContext {
        &self.locality
    }
    pub(super) fn platform(&self) -> &Arc<dyn Platform> {
        &self.platform
    }
    #[cfg(test)]
    pub(crate) fn scheduled(&self) -> (usize, usize) {
        let state = lock(&self.state);
        (state.ready.len(), state.attached)
    }
    pub(super) fn add_outstanding(&self, bytes: usize) {
        self.outstanding.fetch_add(bytes, Ordering::AcqRel);
    }
    pub(super) fn release_outstanding(&self, bytes: usize) {
        self.outstanding.fetch_sub(bytes, Ordering::AcqRel);
    }
    pub(super) fn wake(&self) {
        let _state = lock(&self.state);
        self.changed.notify_all();
    }
    pub(super) fn attach(&self, mapping: &Arc<Shared>) {
        let mut state = lock(&self.state);
        if state.closed {
            return;
        }
        let mut accounting = lock(&mapping.state);
        assert!(!accounting.link.registered, "a mapping attaches once");
        accounting.link.registered = true;
        accounting.link.unclaimed = accounting.window_count();
        state.attached += 1;
        if accounting.link.unclaimed != 0 {
            accounting.link.queued = true;
            state.ready.push_back(Arc::clone(mapping));
        }
        drop(accounting);
        self.changed.notify_all();
    }
    pub(super) fn detach(&self, mapping: &Arc<Shared>) {
        let mut state = lock(&self.state);
        let mut accounting = lock(&mapping.state);
        accounting.closed = true;
        mapping.wake.notify_all();
        if accounting.link.registered {
            if accounting.link.queued {
                accounting.link.queued = false;
                remove(&mut state.ready, mapping);
            }
            accounting.link.registered = false;
            state.attached -= 1;
        }
        drop(accounting);
        self.changed.notify_all();
        while lock(&mapping.state).link.active != 0 {
            state = wait(&self.changed, state);
        }
        let mut accounting = lock(&mapping.state);
        let remaining = accounting.clear_populated() * accounting.page_size;
        self.release_outstanding(remaining);
        drop(accounting);
        self.changed.notify_all();
    }
    fn claim(&self, shard: usize) -> Option<Work> {
        let mut state = lock(&self.state);
        loop {
            if state.closed {
                return None;
            }
            let used = self
                .outstanding
                .load(Ordering::Acquire)
                .saturating_add(state.reserved);
            let available = state.lookahead.saturating_sub(used);
            if let Some(work) = claim_ready(&mut state, shard, available) {
                return Some(work);
            }
            state = wait(&self.changed, state);
        }
    }
    fn finish(&self, work: Work) {
        let mut state = lock(&self.state);
        let mut accounting = lock(&work.mapping.state);
        accounting.link.active -= 1;
        if accounting.link.queued && accounting.disabled {
            accounting.link.queued = false;
            remove(&mut state.ready, &work.mapping);
        }
        drop(accounting);
        state.reserved -= work.reserved;
        self.changed.notify_all();
    }
}
fn claim_ready(state: &mut State, shard: usize, available: usize) -> Option<Work> {
    for index in 0..state.ready.len() {
        let mapping = &state.ready[index];
        let mut accounting = lock(&mapping.state);
        let Some((window, reserved)) =
            accounting.claim_shared_window(shard, available, &mapping.locality)
        else {
            continue;
        };
        accounting.link.active += 1;
        accounting.link.unclaimed -= 1;
        let requeue = accounting.link.unclaimed != 0;
        accounting.link.queued = requeue;
        drop(accounting);
        let mapping = state.ready.remove(index)?;
        if requeue {
            state.ready.push_back(Arc::clone(&mapping));
        }
        state.reserved += reserved;
        return Some(Work {
            mapping,
            window,
            reserved,
        });
    }
    None
}
fn remove(ready: &mut VecDeque<Arc<Shared>>, mapping: &Arc<Shared>) {
    let position = ready.iter().position(|queued| Arc::ptr_eq(queued, mapping));
    assert!(position.is_some(), "a queued mapping is scheduled");
    if let Some(position) = position {
        ready.remove(position);
    }
}
#[derive(Debug)]
pub(crate) struct PrefaultPool {
    pool: Arc<Pool>,
    threads: Vec<JoinHandle<()>>,
}
impl PrefaultPool {
    pub(crate) fn start(
        locality: &LocalityContext,
        platform: Arc<dyn Platform>,
        spawner: &dyn WorkerSpawner,
    ) -> Result<Self, WriteError> {
        let mut this = Self {
            pool: Arc::new(Pool {
                state: Mutex::new(State {
                    ready: VecDeque::new(),
                    attached: 0,
                    reserved: 0,
                    lookahead: PREFAULT_LOOKAHEAD,
                    startup_completed: 0,
                    startup_error: None,
                    closed: false,
                }),
                changed: Condvar::new(),
                outstanding: AtomicUsize::new(0),
                locality: locality.clone(),
                platform,
            }),
            threads: Vec::new(),
        };
        for index in 0..locality.shard_count() * PREFAULT_THREADS_PER_SHARD {
            let pool = Arc::clone(&this.pool);
            this.threads.push(spawner.spawn(
                format!("download-prefault-{index}"),
                Box::new(move || worker(&pool, index)),
            )?);
        }
        let mut state = lock(&this.pool.state);
        while state.startup_completed != this.threads.len() {
            state = wait(&this.pool.changed, state);
        }
        let failed = state.startup_error.take();
        drop(state);
        match failed {
            Some(error) => Err(error),
            None => Ok(this),
        }
    }
    pub(crate) fn pool(&self) -> &Arc<Pool> {
        &self.pool
    }
    pub(crate) fn worker_count(&self) -> usize {
        self.threads.len()
    }
}
impl Drop for PrefaultPool {
    fn drop(&mut self) {
        lock(&self.pool.state).closed = true;
        self.pool.changed.notify_all();
        for worker in self.threads.drain(..) {
            assert!(worker.join().is_ok(), "prefault pool worker panicked");
        }
    }
}
fn worker(pool: &Pool, index: usize) {
    let shard = index % pool.locality.shard_count();
    let placement = pool.locality.apply_to_shard(shard, pool.platform.as_ref());
    let mut state = lock(&pool.state);
    if let Err(error) = &placement {
        state.startup_error.get_or_insert_with(|| error.clone());
    }
    state.startup_completed += 1;
    drop(state);
    pool.changed.notify_all();
    if placement.is_err() {
        return;
    }
    while let Some(work) = pool.claim(shard) {
        let faults = MinorFaults::start(pool.platform.as_ref());
        populate(&work.mapping, work.window, Some(pool));
        faults.record(&work.mapping);
        pool.finish(work);
    }
}
#[cfg(test)]
mod tests;
