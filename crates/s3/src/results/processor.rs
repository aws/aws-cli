use super::{Event, Mode, Printer, PrinterConfig, Recorder, WriteErrors};
use std::{
    collections::VecDeque,
    io::{self, Write},
    sync::{
        Arc, Condvar, Mutex, MutexGuard,
        atomic::{AtomicBool, AtomicU64, Ordering},
    },
    thread::{Scope, ScopedJoinHandle},
    time::Instant,
};
#[derive(Debug)]
struct Entry {
    event: Option<Event>,
    progress_mark: u64,
}
#[derive(Debug, Default)]
struct Queue {
    entries: VecDeque<Entry>,
    closed: bool,
}
#[derive(Debug)]
struct Shared {
    queue: Mutex<Queue>,
    wake: Condvar,
    progress: AtomicU64,
    progress_pending: AtomicBool,
    wants_progress: bool,
}
impl Shared {
    fn lock(&self) -> MutexGuard<'_, Queue> {
        self.queue
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}
/// Producers hold the queue mutex only to append an owned event. Progress
/// bypasses the queue: it touches atomics, and at most one report per wake
/// of the drain loop takes the mutex, briefly, to wake it.
#[derive(Debug, Clone)]
pub struct Publisher(Arc<Shared>);
impl Publisher {
    pub fn publish(&self, event: Event) {
        let mut queue = self.0.lock();
        if queue.closed {
            return;
        }
        let progress_mark = self.0.progress.load(Ordering::SeqCst);
        queue.entries.push_back(Entry {
            event: Some(event),
            progress_mark,
        });
        self.0.wake.notify_one();
    }
    pub fn wants_progress(&self) -> bool {
        self.0.wants_progress
    }
    /// Records bytes a live source moved and wakes the drain loop. Never blocks
    /// for long: at most one report per wake takes the mutex, briefly. A report
    /// of no bytes changes nothing and wakes nobody.
    pub fn add_progress(&self, bytes: u64) {
        if bytes == 0 {
            return;
        }
        self.0.progress.fetch_add(bytes, Ordering::SeqCst);
        if self.0.progress_pending.swap(true, Ordering::SeqCst) {
            return;
        }
        // The drain loop checks the flag under the mutex before it waits,
        // so taking it here cannot lose this wake.
        let _queue = self.0.lock();
        self.0.wake.notify_one();
    }
    #[cfg(test)]
    pub(crate) fn take_events(&self) -> Vec<Event> {
        let mut queue = self.0.lock();
        std::mem::take(&mut queue.entries)
            .into_iter()
            .filter_map(|entry| entry.event)
            .collect()
    }
    pub fn close(&self) {
        let mut queue = self.0.lock();
        if queue.closed {
            return;
        }
        queue.closed = true;
        let progress_mark = self.0.progress.load(Ordering::SeqCst);
        queue.entries.push_back(Entry {
            event: None,
            progress_mark,
        });
        self.0.wake.notify_one();
    }
}
#[derive(Debug)]
pub struct Processor {
    publisher: Publisher,
    pub recorder: Recorder,
    printer: Option<Printer>,
    diagnostics: Option<RawDiagnostics>,
    folded: u64,
    enabled: bool,
}
impl Processor {
    pub fn new(config: Option<PrinterConfig>) -> Self {
        Self {
            publisher: Publisher(Arc::new(Shared {
                queue: Mutex::new(Queue::default()),
                wake: Condvar::new(),
                progress: AtomicU64::new(0),
                progress_pending: AtomicBool::new(false),
                wants_progress: config.is_some_and(|c| c.mode == Mode::Full),
            })),
            recorder: Recorder::default(),
            printer: config.map(Printer::new),
            diagnostics: None,
            folded: 0,
            enabled: true,
        }
    }
    /// Command diagnostics such as opt-in statistics are visible even with
    /// quiet transfer output. Without a printer, as under `--quiet`, they
    /// print as written.
    pub fn with_diagnostics(config: Option<PrinterConfig>) -> Self {
        let mut processor = Self::new(config);
        if config.is_none() {
            processor.diagnostics = Some(RawDiagnostics::default());
        }
        processor
    }
    pub fn publisher(&self) -> Publisher {
        self.publisher.clone()
    }
    /// Moves the processor onto its own thread in `scope`, built by
    /// `spawn_drain`, where it drains until `Running::stop`. The command's
    /// transfer stays on the caller's thread. A thread the system refuses is
    /// the error, and nothing was drained.
    pub fn start<'scope>(
        self,
        scope: &'scope Scope<'scope, '_>,
        stdout: &'scope mut (dyn Write + Send),
        stderr: &'scope mut (dyn Write + Send),
    ) -> io::Result<Running<'scope>> {
        self.start_with(scope, stdout, stderr, spawn_drain)
    }
    /// `start` with the thread `spawn` builds, which tests replace.
    pub fn start_with<'scope, 'env>(
        mut self,
        scope: &'scope Scope<'scope, 'env>,
        stdout: &'scope mut (dyn Write + Send),
        stderr: &'scope mut (dyn Write + Send),
        spawn: impl FnOnce(
            &'scope Scope<'scope, 'env>,
            Drain<'scope>,
        ) -> io::Result<DrainThread<'scope>>,
    ) -> io::Result<Running<'scope>> {
        let publisher = self.publisher();
        let thread = spawn(scope, Box::new(move || self.run(stdout, stderr)))?;
        Ok(Running {
            publisher,
            thread: Some(thread),
        })
    }
    pub fn run(
        &mut self,
        stdout: &mut dyn Write,
        stderr: &mut dyn Write,
    ) -> Result<(), WriteErrors> {
        let start = Instant::now();
        self.run_with_clock(stdout, stderr, || {
            start.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64
        })
    }
    pub fn run_with_clock(
        &mut self,
        stdout: &mut dyn Write,
        stderr: &mut dyn Write,
        mut clock: impl FnMut() -> u64,
    ) -> Result<(), WriteErrors> {
        loop {
            let (entries, progress) = self.take_batch();
            let now = clock();
            let mut closed = false;
            for entry in entries {
                let Some(event) = entry.event else {
                    closed = true;
                    break;
                };
                if event.redraws_progress() {
                    self.fold(entry.progress_mark, now, stdout, stderr);
                }
                self.handle(event, now, stdout, stderr);
            }
            if !closed {
                self.fold(progress, now, stdout, stderr);
            }
            if let Some(printer) = &mut self.printer {
                printer.flush(stdout, stderr);
            }
            if closed {
                return self.take_errors();
            }
        }
    }
    fn take_batch(&self) -> (VecDeque<Entry>, u64) {
        let shared = &self.publisher.0;
        let mut queue = shared.lock();
        while queue.entries.is_empty() && !shared.progress_pending.load(Ordering::SeqCst) {
            queue = shared
                .wake
                .wait(queue)
                .unwrap_or_else(std::sync::PoisonError::into_inner);
        }
        shared.progress_pending.store(false, Ordering::SeqCst);
        let progress = shared.progress.load(Ordering::SeqCst);
        (std::mem::take(&mut queue.entries), progress)
    }
    fn take_errors(&mut self) -> Result<(), WriteErrors> {
        let printed = self
            .printer
            .as_mut()
            .map(Printer::take_errors)
            .unwrap_or_default();
        let diagnostics = WriteErrors {
            stdout: None,
            stderr: self
                .diagnostics
                .as_mut()
                .and_then(|diagnostics| diagnostics.error.take()),
        };
        let errors = printed.or(diagnostics);
        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }
    fn handle(&mut self, event: Event, now: u64, stdout: &mut dyn Write, stderr: &mut dyn Write) {
        if !self.enabled && !matches!(event, Event::Diagnostic(_)) {
            return;
        }
        self.recorder.record(&event, now);
        if let Some(printer) = &mut self.printer {
            printer.handle(&self.recorder, &event, now, stdout, stderr);
        }
        if let Event::Diagnostic(text) = &event
            && let Some(diagnostics) = &mut self.diagnostics
        {
            diagnostics.write(text, stderr);
        }
        if event.ends_command() {
            self.enabled = false;
        }
    }
    fn fold(&mut self, mark: u64, now: u64, stdout: &mut dyn Write, stderr: &mut dyn Write) {
        if !self.enabled || mark <= self.folded {
            return;
        }
        let event = Event::Progress {
            key: None,
            bytes: mark - self.folded,
            total_size: None,
            timestamp_ns: now,
        };
        self.folded = mark;
        self.recorder.record(&event, now);
        if self.recorder.has_remaining_progress()
            && let Some(printer) = &mut self.printer
        {
            printer.handle(&self.recorder, &event, now, stdout, stderr);
        }
    }
}

/// The drain loop `Processor::start` moves onto its thread, which returns
/// the first write error of each stream.
pub type Drain<'scope> = Box<dyn FnOnce() -> Result<(), WriteErrors> + Send + 'scope>;
/// The thread a drain loop runs on, which `Running::stop` joins.
pub type DrainThread<'scope> = ScopedJoinHandle<'scope, Result<(), WriteErrors>>;
/// Spawns `drain` on a thread in `scope` with the stack every native
/// command thread runs on (`cli_core::thread::THREAD_STACK_BYTES`).
pub fn spawn_drain<'scope>(
    scope: &'scope Scope<'scope, '_>,
    drain: Drain<'scope>,
) -> io::Result<DrainThread<'scope>> {
    cli_core::thread::builder().spawn_scoped(scope, drain)
}
/// A processor draining on its own thread, between `Processor::start` and
/// `stop`. Dropped without `stop`, as when the caller unwinds, it closes the
/// queue, so the scope's join of the thread still returns.
#[derive(Debug)]
pub struct Running<'scope> {
    publisher: Publisher,
    thread: Option<DrainThread<'scope>>,
}
impl Running<'_> {
    /// Closes the queue behind everything published so far, waits for the
    /// thread to process it, and returns the printer's first write error of
    /// each stream. Results published later are never processed.
    pub fn stop(mut self) -> Result<(), WriteErrors> {
        self.publisher.close();
        let Some(thread) = self.thread.take() else {
            return Ok(());
        };
        thread
            .join()
            .unwrap_or_else(|payload| std::panic::resume_unwind(payload))
    }
}
impl Drop for Running<'_> {
    fn drop(&mut self) {
        self.publisher.close();
    }
}

#[derive(Debug, Default)]
struct RawDiagnostics {
    error: Option<io::Error>,
}
impl RawDiagnostics {
    fn write(&mut self, text: &[u8], stderr: &mut dyn Write) {
        if self.error.is_some() {
            return;
        }
        let line = [text, b"\n"].concat();
        if let Err(error) = stderr.write_all(&line).and_then(|()| stderr.flush()) {
            self.error = Some(error);
        }
    }
}

#[cfg(test)]
mod tests;
