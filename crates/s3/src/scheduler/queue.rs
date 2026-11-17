use super::*;
use std::{collections::VecDeque, sync::mpsc, thread::JoinHandle};
#[derive(Debug)]
enum Entry {
    Listed {
        key: String,
        size: u64,
        modified: Option<i64>,
        archive: Archive,
        case_name: Option<String>,
        condition: ObjectCondition,
    },
    LocalDelete {
        local_path: PathBuf,
        handled: mpsc::SyncSender<()>,
    },
}
#[derive(Debug, Default)]
struct QueueState {
    jobs: VecDeque<Entry>,
    closed: bool,
    failed: bool,
}
#[derive(Debug)]
struct Shared {
    scheduler: Arc<Scheduler>,
    capacity: usize,
    state: Mutex<QueueState>,
    ready: Condvar,
    space: Condvar,
}
#[derive(Debug)]
pub struct SubmitQueue {
    shared: Arc<Shared>,
    worker: Option<JoinHandle<()>>,
}
impl SubmitQueue {
    pub fn new(scheduler: Arc<Scheduler>, capacity: usize) -> io::Result<Self> {
        assert!(capacity > 0);
        let shared = Arc::new(Shared {
            scheduler,
            capacity,
            state: Mutex::new(QueueState::default()),
            ready: Condvar::new(),
            space: Condvar::new(),
        });
        let worker = Arc::clone(&shared);
        let worker = cli_core::thread::builder()
            .name("s3-submit".into())
            .spawn(move || worker.run())?;
        Ok(Self {
            shared,
            worker: Some(worker),
        })
    }
    pub fn push(&self, key: String, size: u64, modified: Option<i64>) -> Result<(), Error> {
        self.push_with_archive(key, size, modified, Archive::default())
    }
    pub fn push_with_archive(
        &self,
        key: String,
        size: u64,
        modified: Option<i64>,
        archive: Archive,
    ) -> Result<(), Error> {
        self.push_case_named(
            key,
            size,
            modified,
            archive,
            None,
            ObjectCondition::default(),
        )
    }
    /// Queues a listed object as `push_with_archive` does, with the
    /// case-folded name a sync download took for it and what the listing
    /// conditions a download of it on.
    pub fn push_case_named(
        &self,
        key: String,
        size: u64,
        modified: Option<i64>,
        archive: Archive,
        case_name: Option<String>,
        condition: ObjectCondition,
    ) -> Result<(), Error> {
        self.push_entry(Entry::Listed {
            key,
            size,
            modified,
            archive,
            case_name,
            condition,
        })
    }
    /// Removes `local_path`, a file only a sync download's destination
    /// holds, behind every entry queued before it, and returns once the
    /// submitter removed it, or reported it under a dry run.
    ///
    /// # Errors
    ///
    /// [`Error::QueueClosed`] when the queue refused the removal, or the
    /// submitter dropped it: it stopped on an entry's error.
    pub fn delete_local_file(&self, local_path: PathBuf) -> Result<(), Error> {
        let (handled, done) = mpsc::sync_channel(1);
        self.push_entry(Entry::LocalDelete {
            local_path,
            handled,
        })?;
        done.recv().map_err(|_| Error::QueueClosed)
    }
    fn push_entry(&self, entry: Entry) -> Result<(), Error> {
        let scheduler = &self.shared.scheduler;
        if scheduler.interrupted() {
            return Err(Error::QueueClosed);
        }
        let mut state = lock(&self.shared.state);
        let start = Instant::now();
        let stalled = state.jobs.len() == self.shared.capacity;
        while state.jobs.len() == self.shared.capacity && !state.closed && !state.failed {
            state = wait(&self.shared.space, state);
        }
        if state.closed || state.failed {
            return Err(Error::QueueClosed);
        }
        state.jobs.push_back(entry);
        if scheduler.request.collect_stats {
            let mut stats = lock(&scheduler.state);
            stats.stats.queue_hwm = stats.stats.queue_hwm.max(state.jobs.len() as u64);
            if stalled {
                stats.stats.producer_wait_count += 1;
                stats.stats.producer_wait_ns += ns(start.elapsed());
            }
        }
        self.shared.ready.notify_one();
        Ok(())
    }
    /// Whether the submitter stopped on an entry's error, which the
    /// scheduler recorded. After `close_and_join`, a listing that succeeded
    /// still left its submissions unfinished when this is true.
    pub fn is_failed(&self) -> bool {
        lock(&self.shared.state).failed
    }
    pub fn close(&self) {
        lock(&self.shared.state).closed = true;
        self.shared.ready.notify_all();
        self.shared.space.notify_all();
    }
    pub fn close_and_join(&mut self) {
        self.close();
        if let Some(worker) = self.worker.take() {
            assert!(worker.join().is_ok(), "submit worker panicked");
        }
    }
}
impl Drop for SubmitQueue {
    fn drop(&mut self) {
        self.close_and_join();
    }
}
impl Shared {
    fn run(&self) {
        loop {
            let mut state = lock(&self.state);
            while state.jobs.is_empty() && !state.closed {
                state = wait(&self.ready, state);
            }
            let Some(entry) = state.jobs.pop_front() else {
                return;
            };
            self.space.notify_all();
            if state.failed {
                continue;
            }
            drop(state);
            let handled = match entry {
                Entry::Listed {
                    key,
                    size,
                    modified,
                    archive,
                    case_name,
                    condition,
                } => self
                    .scheduler
                    .handle_listed_entry(&key, size, modified, archive, case_name, condition),
                Entry::LocalDelete {
                    local_path,
                    handled,
                } => {
                    let deleted = self.scheduler.delete_local_file(&local_path);
                    if deleted.is_ok() {
                        let _ = handled.send(());
                    }
                    deleted
                }
            };
            if let Err(error) = handled {
                self.scheduler.record_fatal(error);
                lock(&self.state).failed = true;
                self.space.notify_all();
            }
        }
    }
}
