use super::*;
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ReplayReason {
    Redirect,
    SizeChanged,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FinishOn {
    Pool,
    Callback,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AttemptOrigin {
    Queued,
    Direct,
}
#[derive(Debug)]
pub(super) struct CompletionState {
    owner: lifetime::Held<Arc<Scheduler>>,
    pub job: Arc<Job>,
    this: Weak<Self>,
    id: u64,
    finished: AtomicBool,
    progress_bytes: Arc<AtomicU64>,
    single_request_bytes: u64,
    finish_on: FinishOn,
    refs: AtomicUsize,
    canceled: Arc<AtomicBool>,
    result: Mutex<Option<TransferResult>>,
    redirected: bool,
    replayed: bool,
    owns_job: AtomicBool,
    shut_down: Mutex<bool>,
    shutdown_wake: Condvar,
}
impl Scheduler {
    pub(super) fn submit(self: &Arc<Self>, job: Job) -> Result<(), Error> {
        let single_request_bytes = self.single_request_bytes(job.direction, job.size);
        let Some(id) = self.queue_job(&job, single_request_bytes)? else {
            return Ok(());
        };
        let completion = CompletionState::new(
            self,
            Arc::new(job),
            id,
            single_request_bytes,
            Arc::default(),
            false,
            false,
        );
        let prepare_pool = lock(&self.prepare_pool);
        let Some(pool) = prepare_pool.as_ref() else {
            drop(prepare_pool);
            completion.attempt(AttemptOrigin::Direct);
            return Ok(());
        };
        let pushed = pool.try_push(Arc::clone(&completion));
        drop(prepare_pool);
        if pushed.is_err() {
            self.record_fatal(crate::cp::backstop::WRITE_POOL_CLOSED);
            completion.rejected(SubmitError::Local(
                crate::cp::backstop::WRITE_POOL_CLOSED.into(),
            ));
        }
        Ok(())
    }
    pub(super) fn queue_job(
        &self,
        job: &Job,
        single_request_bytes: u64,
    ) -> Result<Option<u64>, Error> {
        self.reserve(single_request_bytes);
        if self.raised.load(Ordering::Acquire) {
            self.release_slot(single_request_bytes);
            return Ok(None);
        }
        // Callbacks can run before `operations.submit` returns, so the queued
        // result goes first, and no request follows one that was lost.
        let id = self.sequence.fetch_add(1, Ordering::Relaxed);
        if let Err(error) = self.publish_queued(id, job.size) {
            self.record_fatal(&error);
            self.unreserve(single_request_bytes);
            return Err(Error::Output(error));
        }
        lock(&self.state).stats.submitted += 1;
        Ok(Some(id))
    }
    fn publish_queued(&self, id: u64, size: Option<u64>) -> Result<(), String> {
        let quiet = self.request.quiet;
        self.sink
            .publish(crate::results::Event::Queued { key: id, size }, quiet)?;
        if self.request.object.is_some() {
            assert_eq!(id, 0, "one object is queued once");
            self.sink
                .publish(crate::results::Event::FinalTotal(1), quiet)?;
        }
        Ok(())
    }
    fn note_download_accepted(&self, job: &Job) {
        if job.direction != transfer::Direction::Download || job.sent_without_output() {
            return;
        }
        let custom = job.custom_writer.load(Ordering::Acquire);
        let mut state = lock(&self.state);
        if custom {
            state.stats.custom_writer_requests += 1;
        } else {
            state.stats.recv_file_requests += 1;
        }
    }
}
pub(super) fn prepare_pool(
    workers: usize,
    capacity: usize,
) -> crate::write_pool::WritePool<Arc<CompletionState>> {
    crate::write_pool::WritePool::new(workers, capacity, |state: Arc<CompletionState>| {
        state.attempt(AttemptOrigin::Queued);
    })
    .named("s3-prepare")
}
impl CompletionState {
    fn new(
        owner: &Arc<Scheduler>,
        job: Arc<Job>,
        id: u64,
        single_request_bytes: u64,
        progress_bytes: Arc<AtomicU64>,
        redirected: bool,
        replayed: bool,
    ) -> Arc<Self> {
        let finish_on = if owner.finishes_on_pool() {
            FinishOn::Pool
        } else {
            FinishOn::Callback
        };
        Arc::new_cyclic(|this| Self {
            owner: owner.callbacks.hold(Arc::clone(owner)),
            job,
            this: this.clone(),
            id,
            finished: AtomicBool::new(false),
            progress_bytes,
            single_request_bytes,
            finish_on,
            refs: AtomicUsize::new(match finish_on {
                FinishOn::Pool => 2,
                FinishOn::Callback => 1,
            }),
            canceled: Arc::new(AtomicBool::new(false)),
            result: Mutex::new(None),
            redirected,
            replayed,
            owns_job: AtomicBool::new(true),
            shut_down: Mutex::new(false),
            shutdown_wake: Condvar::new(),
        })
    }
    fn attempt(self: &Arc<Self>, origin: AttemptOrigin) {
        if (origin == AttemptOrigin::Queued || self.replayed) && self.owner.stopped() {
            self.dropped_before_request();
            return;
        }
        let callbacks: Arc<dyn Completion> = self.clone();
        match self
            .owner
            .operations
            .submit(Arc::clone(&self.job), callbacks)
        {
            Ok(request) => {
                self.owner.note_download_accepted(&self.job);
                self.adopt(request);
            }
            Err(error) => self.rejected(error),
        }
    }
    fn dropped_before_request(&self) {
        self.owner.operations.discard(&self.job);
        self.transfer_failed(&TransferResult {
            error_code: crt::s3::CANCELED_ERROR_CODE,
            canceled_by_interrupt: true,
            ..TransferResult::default()
        });
        self.refs.store(0, Ordering::Release);
        self.owner.retire(&self.job, self.single_request_bytes);
    }
    fn adopt(&self, request: Box<dyn OwnedRequest>) {
        let mut state = lock(&self.owner.state);
        if self.finished.load(Ordering::Acquire) {
            drop(state);
            drop(request);
            return;
        }
        if self.owner.stopped() {
            self.canceled.store(true, Ordering::Release);
            request.cancel();
        }
        assert!(
            state
                .requests
                .insert(self.id, (request, Arc::clone(&self.canceled)))
                .is_none()
        );
    }
    fn rejected(&self, error: SubmitError) {
        self.owner.operations.discard(&self.job);
        lock(&self.owner.state).stats.failed += 1;
        let event = match error {
            SubmitError::Transfer(result) => self.owner.transfer_failure(&self.job, &result),
            SubmitError::Local(error) => self.owner.local_failure(&self.job, &error),
            SubmitError::RawLocal(exception) => render::Failure {
                exception,
                text: None,
            },
        };
        self.publish_failure(event);
        self.refs.store(0, Ordering::Release);
        self.owner.retire(&self.job, self.single_request_bytes);
    }
    fn unref(&self) {
        let refs = self.refs.fetch_sub(1, Ordering::AcqRel);
        assert!(refs > 0, "completion ownership released twice");
        if refs == 1 && self.owns_job.load(Ordering::Acquire) {
            self.owner.retire(&self.job, self.single_request_bytes);
        }
    }
    pub(super) fn execute_finish(&self) {
        let result = lock(&self.result).clone();
        assert!(result.is_some(), "finish work lacks result");
        let Some(result) = result else {
            return;
        };
        if self.redirect_candidate(&result) {
            self.replay(&result, ReplayReason::Redirect);
            self.unref();
            return;
        }
        if self.size_changed_candidate(&result) {
            self.job.size_changed.store(true, Ordering::Release);
            self.replay(&result, ReplayReason::SizeChanged);
            self.unref();
            return;
        }
        let finalized = self.owner.operations.finalize(&self.job, &result);
        if result.canceled_by_interrupt {
            lock(&self.owner.state).canceled += 1;
            self.owner.publish(crate::results::Event::CtrlC);
        } else {
            self.apply(finalized);
        }
        self.unref();
    }
    fn apply(&self, outcome: Finalize) {
        let event = match outcome {
            Finalize::Success => None,
            Finalize::Mtime(error) => {
                lock(&self.owner.state).warned += 1;
                Some(self.owner.mtime_warning(&self.job, &error))
            }
            Finalize::Transfer(result) => {
                self.report_failure(self.owner.transfer_failure(&self.job, &result));
                return;
            }
            Finalize::Commit(failure) => {
                self.report_failure(self.owner.commit_failure(&self.job, failure));
                return;
            }
            Finalize::Write(error) => {
                self.report_failure(self.owner.local_failure(&self.job, &error));
                return;
            }
        };
        if let Some(event) = event {
            self.owner.publish(crate::results::Event::Warning(event));
        }
        // A move deletes the source before the transfer reports, and a
        // deletion that fails fails the transfer (`DeleteSourceSubscriber`).
        let moves = matches!(
            self.owner.request.sources,
            transfer::SourceDisposition::Delete { .. }
        );
        if moves && let Err(error) = self.owner.operations.delete_source(&self.job) {
            match error {
                SourceDeleteError::Request(result) if result.canceled_by_interrupt => {
                    lock(&self.owner.state).canceled += 1;
                    self.owner.publish(crate::results::Event::CtrlC);
                }
                error => {
                    self.report_failure(self.owner.source_delete_failure(&self.job, &error));
                }
            }
            return;
        }
        lock(&self.owner.state).stats.succeeded += 1;
        self.owner.publish(crate::results::Event::Success {
            key: self.id,
            line: self.owner.line(&self.job),
        });
    }
    fn report_failure(&self, event: render::Failure) {
        lock(&self.owner.state).stats.failed += 1;
        self.publish_failure(event);
    }
    fn publish_failure(&self, event: render::Failure) {
        self.owner.publish(crate::results::Event::Failure {
            key: self.id,
            line: self.owner.line(&self.job),
            exception: event.exception,
            transferred: Some(self.progress_bytes.load(Ordering::Relaxed)),
            text: event.text,
        });
    }
    fn transfer_failed(&self, result: &TransferResult) {
        let mut state = lock(&self.owner.state);
        if self.job.direction == transfer::Direction::Upload
            && self.owner.request.no_overwrite
            && result.response_status == 412
        {
            state.stats.skipped += 1;
            drop(state);
            self.owner
                .publish(crate::results::Event::Skip { key: self.id });
            return;
        }
        if result.canceled_by_interrupt {
            state.canceled += 1;
            drop(state);
            self.owner.publish(crate::results::Event::CtrlC);
            return;
        }
        state.stats.failed += 1;
        drop(state);
        self.publish_failure(self.owner.transfer_failure(&self.job, result));
    }

    fn redirect_candidate(&self, result: &TransferResult) -> bool {
        !self.redirected && crt::redirect::is_candidate(&self.owner.request.bucket, result, true)
    }
    fn size_changed_candidate(&self, result: &TransferResult) -> bool {
        result.size_changed
            && self.job.size_listed
            && !self.job.size_changed.load(Ordering::Acquire)
    }
    fn requires_worker(&self, result: &TransferResult) -> bool {
        (self.job.direction == transfer::Direction::Download && result.error_code == 0)
            || self.job.custom_writer.load(Ordering::Acquire)
            || self.redirect_candidate(result)
    }
    fn await_shutdown(&self) {
        let mut shut_down = lock(&self.shut_down);
        while !*shut_down {
            shut_down = wait(&self.shutdown_wake, shut_down);
        }
    }
    fn replay(&self, result: &TransferResult, reason: ReplayReason) {
        let operations = &self.owner.operations;
        if let Some(error) = operations.retire_attempt(&self.job, result, &|| self.await_shutdown())
        {
            operations.discard(&self.job);
            self.apply(Finalize::Write(error));
            return;
        }
        let recovery = if self.owner.stopped() {
            crt::redirect::Outcome::Canceled
        } else {
            match reason {
                ReplayReason::Redirect => operations.recover_region(result),
                ReplayReason::SizeChanged => crt::redirect::Outcome::Ready,
            }
        };
        match recovery {
            crt::redirect::Outcome::Unavailable => {
                operations.discard(&self.job);
                self.transfer_failed(result);
            }
            crt::redirect::Outcome::Canceled => {
                operations.discard(&self.job);
                self.transfer_failed(&TransferResult {
                    error_code: crt::s3::CANCELED_ERROR_CODE,
                    canceled_by_interrupt: true,
                    ..TransferResult::default()
                });
            }
            crt::redirect::Outcome::Ready => {
                let replay = Self::new(
                    &self.owner,
                    Arc::clone(&self.job),
                    self.id,
                    self.single_request_bytes,
                    Arc::clone(&self.progress_bytes),
                    self.redirected || reason == ReplayReason::Redirect,
                    true,
                );
                // The replay's callbacks can finish before its submission
                // returns; it owns the job from here, and this attempt
                // touches the job no more.
                self.owns_job.store(false, Ordering::Release);
                replay.attempt(AttemptOrigin::Direct);
            }
        }
    }
    fn note_download_finish(&self) {
        if cfg!(feature = "download-writer-debug")
            && let Some(output) = lock(&self.job.output).prepared.as_ref()
        {
            output.note_finish();
        }
    }
    fn queue_finish(&self) {
        let this = self.this.upgrade();
        assert!(this.is_some(), "callback owner remains live");
        let Some(this) = this else {
            return;
        };
        let pool = lock(&self.owner.pool);
        let pushed = pool
            .as_ref()
            .is_some_and(|pool| pool.try_push(this).is_ok());
        if pushed {
            return;
        }
        drop(pool);
        self.owner
            .record_fatal(crate::cp::backstop::WRITE_POOL_CLOSED);
        self.owner.operations.discard(&self.job);
        lock(&self.owner.state).stats.failed += 1;
        self.unref();
    }
}
impl Completion for CompletionState {
    fn progress(&self, bytes: u64) {
        self.progress_bytes.fetch_add(bytes, Ordering::Relaxed);
        self.owner.sink.progress(bytes);
    }
    fn wants_progress_hook(&self) -> bool {
        self.owner.wants_progress_hook()
    }
    fn finish(&self, mut result: TransferResult) {
        // Before the reclaim, so the shutdown callback, which cannot run
        // until the request's reference is released, never precedes it.
        self.note_download_finish();
        let owned = {
            let mut state = lock(&self.owner.state);
            assert!(
                !self.finished.swap(true, Ordering::AcqRel),
                "request finished twice"
            );
            state.requests.remove(&self.id)
        };
        result.canceled_by_interrupt = self.canceled.load(Ordering::Acquire)
            && result.error_code == crt::s3::CANCELED_ERROR_CODE;
        *lock(&self.result) = Some(result.clone());
        let pooled = self.finish_on == FinishOn::Pool;
        if pooled && self.requires_worker(&result) {
            self.queue_finish();
        } else {
            if result.error_code != 0 {
                self.owner.operations.discard(&self.job);
                match self.job.output_failure_result(&result) {
                    Some(failure) => self.apply(failure),
                    None => self.transfer_failed(&result),
                }
            } else {
                self.apply(self.owner.operations.finalize(&self.job, &result));
            }
            if pooled {
                self.unref();
            }
        }
        // CRT shutdown may run here and release the final slot; no job work follows.
        drop(owned);
    }
    fn shutdown(&self) {
        *lock(&self.shut_down) = true;
        self.shutdown_wake.notify_all();
        self.unref();
    }
}
