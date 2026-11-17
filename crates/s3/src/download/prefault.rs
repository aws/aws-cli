use super::{
    LocalityContext, PREFAULT_LOOKAHEAD, PREFAULT_THREADS_PER_SHARD, PREFAULT_WINDOW, lock, wait,
};
use super::{
    diagnostics::{self, PrefaultSummary},
    pages::{Bits, page_range},
    platform::{Advice, MappedFile, Platform},
    service::WorkerSpawner,
};
use std::{
    ops::Range,
    sync::{Arc, Condvar, Mutex},
    thread::JoinHandle,
};

mod pool;
pub(crate) use pool::{Pool, PrefaultPool};

#[derive(Clone, Debug)]
pub(crate) enum PrefaultSource {
    Disabled,
    Private,
    Pooled(Arc<Pool>),
}
#[derive(Debug, Default)]
pub(crate) struct PoolLink {
    registered: bool,
    queued: bool,
    unclaimed: usize,
    active: usize,
}
#[derive(Debug)]
pub(crate) struct Accounting {
    size: usize,
    page_size: usize,
    window_bytes: usize,
    next_window_by_shard: Vec<usize>,
    completed: Bits,
    populated: Bits,
    pub(crate) outstanding: usize,
    pub(crate) outstanding_pages_max: usize,
    pub(crate) closed: bool,
    pub(crate) disabled: bool,
    pub(crate) summary: PrefaultSummary,
    pub(crate) link: PoolLink,
}
#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct Advised {
    pub(crate) trimmed: bool,
    pub(crate) ns: u64,
    pub(crate) bytes: usize,
}
impl Accounting {
    pub(crate) fn new(size: usize, page_size: usize, shards: usize) -> Self {
        let count = size.div_ceil(page_size);
        Self {
            size,
            page_size,
            window_bytes: PREFAULT_WINDOW,
            next_window_by_shard: vec![0; shards],
            completed: Bits::new(count),
            populated: Bits::new(count),
            outstanding: 0,
            outstanding_pages_max: PREFAULT_LOOKAHEAD.div_ceil(page_size).max(1),
            closed: false,
            disabled: false,
            summary: PrefaultSummary::default(),
            link: PoolLink::default(),
        }
    }
    fn window_count(&self) -> usize {
        self.size.div_ceil(self.window_bytes)
    }
    pub(crate) fn claim(&mut self, shard: usize, locality: &LocalityContext) -> Option<usize> {
        if self.closed || self.disabled {
            return None;
        }
        let window = self.next_unclaimed(shard, locality)?;
        if self.outstanding >= self.outstanding_pages_max {
            return None;
        }
        self.next_window_by_shard[shard] = window + 1;
        Some(window)
    }
    fn next_unclaimed(&mut self, shard: usize, locality: &LocalityContext) -> Option<usize> {
        let window = self.next_window(shard, locality);
        self.next_window_by_shard[shard] = window;
        (window < self.window_count()).then_some(window)
    }
    fn next_window(&self, shard: usize, locality: &LocalityContext) -> usize {
        debug_assert_eq!(self.next_window_by_shard.len(), locality.shard_count());
        let count = self.window_count();
        let mut window = self.next_window_by_shard[shard];
        while window < count
            && locality.shard_for_offset(window as u64 * self.window_bytes as u64) != shard
        {
            window += 1;
        }
        window
    }
    pub(crate) fn claim_shared_window(
        &mut self,
        shard: usize,
        available: usize,
        locality: &LocalityContext,
    ) -> Option<(usize, usize)> {
        if self.closed || self.disabled || self.outstanding >= self.outstanding_pages_max {
            return None;
        }
        let window = self.next_window(shard, locality);
        if window >= self.window_count() {
            return None;
        }
        let bytes = self
            .window_bytes
            .min(self.size - window * self.window_bytes);
        let reserved = bytes.div_ceil(self.page_size) * self.page_size;
        if reserved > available {
            return None;
        }
        self.next_window_by_shard[shard] = window + 1;
        Some((window, reserved))
    }
    pub(crate) fn pending(&mut self, window: usize) -> Option<Range<usize>> {
        let byte_start = window.checked_mul(self.window_bytes)?;
        let byte_end = byte_start.saturating_add(self.window_bytes).min(self.size);
        if byte_start >= byte_end {
            return None;
        }
        let mut range = byte_start / self.page_size..byte_end.div_ceil(self.page_size);
        while range.start < range.end && self.completed.contains(range.start) {
            range.start += 1;
        }
        while range.end > range.start && self.completed.contains(range.end - 1) {
            range.end -= 1;
        }
        if range.is_empty() {
            if diagnostics::ENABLED {
                self.summary.windows_skipped += 1;
            }
            return None;
        }
        Some(range)
    }
    pub(crate) fn populated(&mut self, pages: Range<usize>, advised: Advised) -> usize {
        let mut partial = advised.trimmed;
        let mut added = 0;
        for page in pages {
            if self.completed.contains(page) {
                partial = true;
            } else if !self.populated.contains(page) {
                self.populated.set(page);
                added += 1;
            }
        }
        self.outstanding += added;
        if diagnostics::ENABLED {
            let summary = &mut self.summary;
            summary.windows_populated += 1;
            if partial {
                summary.windows_populated_partial += 1;
            } else {
                summary.windows_populated_clean += 1;
            }
            summary.populate_ns_total = summary.populate_ns_total.saturating_add(advised.ns);
            summary.populate_ns_max = summary.populate_ns_max.max(advised.ns);
            summary.populated_bytes = summary.populated_bytes.saturating_add(advised.bytes as u64);
        }
        added
    }
    pub(crate) fn mark_copied_page(&mut self, page: usize) -> bool {
        if self.completed.contains(page) {
            return false;
        }
        self.completed.set(page);
        let released = self.populated.contains(page);
        if released {
            self.outstanding -= 1;
        }
        released
    }
    fn clear_populated(&mut self) -> usize {
        self.populated = Bits::new(self.size.div_ceil(self.page_size));
        std::mem::take(&mut self.outstanding)
    }
}
#[derive(Debug)]
struct Shared {
    state: Mutex<Accounting>,
    wake: Condvar,
    mapping: Arc<dyn MappedFile>,
    locality: LocalityContext,
    platform: Arc<dyn Platform>,
}
#[derive(Debug)]
pub(crate) struct Prefaulter {
    shared: Arc<Shared>,
    threads: Vec<JoinHandle<()>>,
    pool: Option<Arc<Pool>>,
}
impl Prefaulter {
    pub(crate) fn start_with(
        mapping: Arc<dyn MappedFile>,
        locality: LocalityContext,
        platform: Arc<dyn Platform>,
        spawner: &dyn WorkerSpawner,
    ) -> std::io::Result<Self> {
        let shards = locality.shard_count();
        let state = Accounting::new(mapping.len(), platform.page_size(), shards);
        let shared = Arc::new(Shared {
            state: Mutex::new(state),
            wake: Condvar::new(),
            mapping,
            locality,
            platform,
        });
        let mut this = Self {
            shared,
            threads: Vec::new(),
            pool: None,
        };
        for index in 0..shards * PREFAULT_THREADS_PER_SHARD {
            let shard = index % shards;
            let shared = Arc::clone(&this.shared);
            let spawned = spawner.spawn(
                "download-prefault".into(),
                Box::new(move || worker(shared, shard)),
            );
            match spawned {
                Ok(thread) => this.threads.push(thread),
                Err(error) if index == 0 => return Err(error),
                Err(error) => {
                    diagnostics::log_prefault_spawn_failed(index, &error);
                    break;
                }
            }
        }
        Ok(this)
    }
    pub(crate) fn attach(
        mapping: Arc<dyn MappedFile>,
        pool: Arc<Pool>,
        platform: &dyn Platform,
    ) -> Self {
        Self::attach_windows(mapping, pool, platform, PREFAULT_WINDOW)
    }
    fn attach_windows(
        mapping: Arc<dyn MappedFile>,
        pool: Arc<Pool>,
        platform: &dyn Platform,
        window_bytes: usize,
    ) -> Self {
        let locality = pool.locality().clone();
        let mut state =
            Accounting::new(mapping.len(), platform.page_size(), locality.shard_count());
        state.window_bytes = window_bytes;
        let shared = Arc::new(Shared {
            state: Mutex::new(state),
            wake: Condvar::new(),
            mapping,
            locality,
            platform: Arc::clone(pool.platform()),
        });
        pool.attach(&shared);
        Self {
            shared,
            threads: Vec::new(),
            pool: Some(pool),
        }
    }
    pub(crate) fn is_pooled(&self) -> bool {
        self.pool.is_some()
    }
    pub(crate) fn thread_count(&self) -> usize {
        self.threads.len()
    }
    pub(crate) fn mark_copied_range(&self, offset: u64, len: usize) {
        let mut state = lock(&self.shared.state);
        let Ok(Some(pages)) = page_range(state.size, state.page_size, offset, len) else {
            return;
        };
        let released = pages.filter(|page| state.mark_copied_page(*page)).count();
        if released == 0 {
            return;
        }
        if let Some(pool) = &self.pool {
            pool.release_outstanding(released * state.page_size);
        }
        self.shared.wake.notify_all();
        drop(state);
        if let Some(pool) = &self.pool {
            pool.wake();
        }
    }
    pub(crate) fn stop(&mut self) {
        let pooled = self.pool.is_some();
        if let Some(pool) = self.pool.take() {
            pool.detach(&self.shared);
        }
        lock(&self.shared.state).closed = true;
        self.shared.wake.notify_all();
        let joined = self.threads.len();
        for worker in self.threads.drain(..) {
            assert!(worker.join().is_ok(), "prefault worker panicked");
        }
        if diagnostics::ENABLED && (joined > 0 || pooled) {
            diagnostics::log_prefault_summary(&self.summary());
        }
    }
    #[cfg(test)]
    pub(crate) fn page_completed(&self, page: usize) -> bool {
        lock(&self.shared.state).completed.contains(page)
    }
    pub(crate) fn summary(&self) -> PrefaultSummary {
        lock(&self.shared.state).summary
    }
}
impl Drop for Prefaulter {
    fn drop(&mut self) {
        self.stop();
    }
}
fn worker(shared: Arc<Shared>, shard: usize) {
    let faults = MinorFaults::start(shared.platform.as_ref());
    match shared
        .locality
        .apply_to_shard(shard, shared.platform.as_ref())
    {
        Ok(()) => {
            while let Some(window) = claim_wait(&shared, shard) {
                populate(&shared, window, None);
            }
        }
        Err(error) => disable(&shared, &error.to_string()),
    }
    faults.record(&shared);
}
struct MinorFaults(Option<u64>);
impl MinorFaults {
    fn start(platform: &dyn Platform) -> Self {
        Self(diagnostics::ENABLED.then(|| platform.thread_minor_faults()))
    }
    fn record(self, shared: &Shared) {
        if let Some(start) = self.0 {
            let faults = shared.platform.thread_minor_faults().saturating_sub(start);
            let mut state = lock(&shared.state);
            state.summary.minor_faults = state.summary.minor_faults.saturating_add(faults);
        }
    }
}
fn claim_wait(shared: &Shared, shard: usize) -> Option<usize> {
    let mut state = lock(&shared.state);
    loop {
        if state.closed || state.disabled {
            return None;
        }
        state.next_unclaimed(shard, &shared.locality)?;
        if state.outstanding < state.outstanding_pages_max {
            return state.claim(shard, &shared.locality);
        }
        let start = diagnostics::start();
        state = wait(&shared.wake, state);
        if diagnostics::ENABLED {
            state.summary.gate_waited(diagnostics::elapsed_ns(start));
        }
    }
}
fn populate(shared: &Shared, window: usize, pool: Option<&Pool>) {
    let (pages, page_size, trimmed) = {
        let mut state = lock(&shared.state);
        let Some(pages) = state.pending(window) else {
            return;
        };
        let start = window * state.window_bytes / state.page_size;
        let end = ((window + 1) * state.window_bytes)
            .min(state.size)
            .div_ceil(state.page_size);
        let trimmed = pages.start != start || pages.end != end;
        (pages, state.page_size, trimmed)
    };
    let bytes = pages.start * page_size..(pages.end * page_size).min(shared.mapping.len());
    let advised = Advised {
        trimmed,
        ns: 0,
        bytes: bytes.len(),
    };
    let start = diagnostics::start();
    match shared.mapping.advise(bytes, Advice::Populate) {
        Ok(()) => {
            let advised = Advised {
                ns: diagnostics::elapsed_ns(start),
                ..advised
            };
            let mut state = lock(&shared.state);
            let added = state.populated(pages, advised);
            if let Some(pool) = pool {
                pool.add_outstanding(added * page_size);
            }
        }
        Err(error) => disable(shared, advise_error_name(&error)),
    }
}
fn advise_error_name(error: &std::io::Error) -> &'static str {
    if error.kind() == std::io::ErrorKind::Unsupported {
        crate::local_error::UNSUPPORTED
    } else {
        crate::local_error::ADVISE_FAILED
    }
}
fn disable(shared: &Shared, error: &str) {
    lock(&shared.state).disabled = true;
    shared.wake.notify_all();
    diagnostics::log_prefault_disabled(error);
}
#[cfg(test)]
mod tests;
