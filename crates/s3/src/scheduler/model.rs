//! Bounded ownership traces using the runtime scheduler and fake request references.
use super::*;
use crate::testing::Choices;
/// The most steps one trace takes; a trace also ends with its input.
const STEP_COUNT_MAX: usize = 128;
/// The most requests a trace submits, one per step. A finish or shutdown
/// step names one by index modulo those outstanding.
const REQUEST_INDEX_COUNT: usize = STEP_COUNT_MAX;
#[derive(Debug, Default)]
struct Sink;
impl super::Sink for Sink {
    fn emit(&self, _: Event) -> Result<(), String> {
        Ok(())
    }
}
#[derive(Debug, Default)]
struct Ops {
    callbacks: Mutex<Vec<(Weak<dyn Completion>, bool)>>,
    releases: Arc<AtomicUsize>,
    shutdowns: Arc<Mutex<Vec<Arc<dyn Completion>>>>,
}
#[derive(Debug)]
struct Handle {
    callback: Arc<dyn Completion>,
    releases: Arc<AtomicUsize>,
    shutdowns: Arc<Mutex<Vec<Arc<dyn Completion>>>>,
}
impl OwnedRequest for Handle {
    fn cancel(&self) {}
}
impl Drop for Handle {
    fn drop(&mut self) {
        self.releases.fetch_add(1, Ordering::Relaxed);
        lock(&self.shutdowns).push(Arc::clone(&self.callback));
    }
}
impl Operations for Ops {
    fn create_parent(&self, _: &Path) -> io::Result<()> {
        Ok(())
    }
    fn exists(&self, _: &Path) -> bool {
        false
    }
    fn inspect_source(&self, _: &Path) -> crate::transfer::SourceInspection {
        crate::transfer::SourceInspection::Size(0)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        callback: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        lock(&self.callbacks).push((Arc::downgrade(&callback), job.raw_key.ends_with(b"1")));
        if job.raw_key.ends_with(b"1") {
            callback.finish(TransferResult::default());
        }
        Ok(Box::new(Handle {
            callback,
            releases: Arc::clone(&self.releases),
            shutdowns: Arc::clone(&self.shutdowns),
        }))
    }
    fn finalize(&self, _: &Job, result: &TransferResult) -> Finalize {
        if result.error_code == 0 {
            Finalize::Success
        } else {
            Finalize::Transfer(Box::new(result.clone()))
        }
    }
    fn delete_source(&self, _: &Job) -> Result<(), SourceDeleteError> {
        Ok(())
    }
    fn discard(&self, _: &Job) {}
}
/// Exercise submission, finish-before-adopt, interruption, and shutdown orderings.
pub fn ownership(bytes: &[u8]) {
    ownership_from(&mut Choices::new(bytes));
}
fn ownership_from(input: &mut Choices<'_>) {
    let operations = Arc::new(Ops::default());
    let pooled = input.flag();
    let direction = if pooled {
        transfer::Direction::Download
    } else {
        transfer::Direction::Upload
    };
    let request = trace_request(direction);
    let scheduler = Scheduler::new(request, "/".into(), operations.clone(), Arc::new(Sink));
    if pooled {
        let started = scheduler.start_finish_pool(1);
        assert!(started.is_ok(), "bounded model worker creation");
    }
    for index in 0..STEP_COUNT_MAX {
        if input.is_empty() {
            break;
        }
        step(&scheduler, &operations, index, input);
    }
    settle(&scheduler, &operations);
}
/// Finishes and shuts down everything outstanding, then checks the drained
/// scheduler's counts.
fn settle(scheduler: &Scheduler, operations: &Ops) {
    let len = lock(&operations.callbacks).len();
    for index in 0..len {
        finish_one(operations, index, false);
    }
    while !lock(&operations.shutdowns).is_empty() {
        shutdown_one(operations, 0);
    }
    scheduler.drain();
    let state = lock(&scheduler.state);
    assert_eq!(state.destroyed, state.stats.submitted);
    assert_eq!(
        operations.releases.load(Ordering::Relaxed) as u64,
        state.stats.submitted
    );
    assert_eq!(
        state.stats.submitted,
        state.stats.succeeded + state.stats.failed + state.canceled
    );
}
/// The request a trace runs: eight slots and no output.
fn trace_request(direction: transfer::Direction) -> TransferRequest {
    TransferRequest {
        direction,
        bucket: "bucket".into(),
        prefix: Vec::new(),
        local_root: "local".into(),
        runtime: Default::default(),
        quiet: true,
        dryrun: false,
        no_overwrite: false,
        glacier: crate::transfer::GlacierPolicy::Warn,
        content_types: None,
        refusal: None,
        page_size: 0,
        max_in_flight: 8,
        collect_stats: true,
        prefetch: true,
        sizing: Default::default(),
        download: None,
        object: None,
        filter: Default::default(),
        headers: Default::default(),
        checksums: Default::default(),
        delete: Default::default(),
        sources: Default::default(),
        sync: None,
        listing_user_agent: None,
        links: Default::default(),
    }
}
fn shutdown_one(operations: &Ops, index: usize) {
    let callback = {
        let mut shutdowns = lock(&operations.shutdowns);
        let len = shutdowns.len();
        if len == 0 {
            return;
        }
        shutdowns.swap_remove(index % len)
    };
    callback.shutdown();
}
fn finish_one(operations: &Ops, index: usize, fail: bool) {
    let callback = {
        let mut callbacks = lock(&operations.callbacks);
        if callbacks.is_empty() {
            return;
        }
        let len = callbacks.len();
        let (callback, finished) = &mut callbacks[index % len];
        if *finished {
            return;
        }
        *finished = true;
        callback.upgrade()
    };
    if let Some(callback) = callback {
        callback.finish(TransferResult {
            error_code: if fail {
                crt::s3::CANCELED_ERROR_CODE
            } else {
                0
            },
            ..Default::default()
        });
    }
}

fn step(scheduler: &Arc<Scheduler>, operations: &Ops, index: usize, input: &mut Choices<'_>) {
    use cli_core::InterruptHook;
    match input.index(5) {
        0 if lock(&scheduler.state).in_flight < 8 => {
            let name = index.to_string();
            let named = if scheduler.request.direction == transfer::Direction::Download {
                scheduler.handle_download_entry(&name, 1, None)
            } else {
                scheduler.handle_upload_entry(Path::new(&name), None)
            };
            assert!(named.is_ok());
        }
        1 | 2 => {
            let request = input.index(REQUEST_INDEX_COUNT);
            finish_one(operations, request, input.flag());
        }
        3 => scheduler.cancel(),
        4 => shutdown_one(operations, input.index(REQUEST_INDEX_COUNT)),
        _ => {}
    }
}

mod smith;
#[doc(inline)]
pub use smith::ownership as smith_ownership;
#[cfg(test)]
mod tests;
