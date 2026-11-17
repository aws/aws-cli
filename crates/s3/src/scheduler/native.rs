use super::*;
use crate::download::{Body, SharedOutput, SharedWriterService, WriteError};
use cli_core::interrupt;
use crt::{
    redirect::Outcome,
    runtime::BucketRuntime,
    s3::{
        CallbackBody, CallbackBodyFn, CallbackRequest, RequestCallbacks, RequestKind,
        RequestOptions,
    },
};
pub(super) trait RequestRuntime: Send + Sync + fmt::Debug {
    fn submit(
        &self,
        options: RequestOptions<'_>,
        body: Option<CallbackBodyFn>,
        callbacks: Arc<dyn RequestCallbacks>,
    ) -> Result<Box<dyn OwnedRequest>, Box<TransferResult>>;
    fn recover_region(&self, result: &TransferResult) -> Outcome;
    fn send(&self, options: RequestOptions<'_>) -> Result<TransferResult, Box<TransferResult>>;
}
#[derive(Debug)]
struct BucketRequests {
    runtime: Arc<BucketRuntime>,
    interrupt: &'static interrupt::State,
}
impl RequestRuntime for BucketRequests {
    fn submit(
        &self,
        options: RequestOptions<'_>,
        body: Option<CallbackBodyFn>,
        callbacks: Arc<dyn RequestCallbacks>,
    ) -> Result<Box<dyn OwnedRequest>, Box<TransferResult>> {
        self.runtime
            .selected()
            .submit_callbacks(options, body, callbacks)
            .map(|request| Box::new(request) as Box<dyn OwnedRequest>)
    }
    fn recover_region(&self, result: &TransferResult) -> Outcome {
        self.runtime.recover_region(result, true, self.interrupt)
    }
    fn send(&self, options: RequestOptions<'_>) -> Result<TransferResult, Box<TransferResult>> {
        self.runtime.send(options, self.interrupt)
    }
}
#[derive(Debug)]
struct CrtOperations {
    runtime: Option<Arc<dyn RequestRuntime>>,
    service: Option<Arc<SharedWriterService>>,
    request: TransferRequest,
    random: RandomId,
}
type RandomId = fn() -> std::io::Result<u64>;
#[derive(Debug)]
struct Callbacks {
    completion: Arc<dyn Completion>,
    progress: bool,
}
impl Callbacks {
    fn new(completion: Arc<dyn Completion>, progress: bool) -> Arc<Self> {
        Arc::new(Self {
            completion,
            progress,
        })
    }
    fn hooked(completion: Arc<dyn Completion>) -> Arc<Self> {
        let progress = completion.wants_progress_hook();
        Self::new(completion, progress)
    }
}
impl RequestCallbacks for Callbacks {
    fn finish(&self, result: TransferResult) {
        self.completion.finish(result);
    }
    fn progress(&self, bytes: u64) {
        if self.progress {
            self.completion.progress(bytes);
        }
    }
    fn shutdown(&self) {
        self.completion.shutdown();
    }
}
impl OwnedRequest for CallbackRequest {
    fn cancel(&self) {
        self.cancel();
    }
}
impl Scheduler {
    /// The scheduler of a command's CRT requests. Each download draws its temp
    /// name's random id once its parent directory exists, after the
    /// HeadObject of a single download.
    pub fn native(
        request: TransferRequest,
        cwd: PathBuf,
        runtime: Option<Arc<BucketRuntime>>,
        service: Option<Arc<SharedWriterService>>,
        sink: Arc<dyn Sink>,
    ) -> Arc<Self> {
        let runtime = runtime.map(|runtime| {
            Arc::new(BucketRequests {
                runtime,
                interrupt: interrupt::process_state(),
            }) as Arc<dyn RequestRuntime>
        });
        Self::with_request_runtime(request, cwd, runtime, service, sink, transfer::temp_name_id)
    }
    fn with_request_runtime(
        request: TransferRequest,
        cwd: PathBuf,
        runtime: Option<Arc<dyn RequestRuntime>>,
        service: Option<Arc<SharedWriterService>>,
        sink: Arc<dyn Sink>,
        random: RandomId,
    ) -> Arc<Self> {
        let operations = Arc::new(CrtOperations {
            runtime,
            service,
            request: request.clone(),
            random,
        });
        Self::new(request, cwd, operations, sink)
    }
}
impl Operations for CrtOperations {
    fn create_parent(&self, path: &Path) -> io::Result<()> {
        transfer::create_local_dir_path(path)
    }
    /// Upstream's `os.path.exists`: any failure, and a path holding a NUL,
    /// counts as absent.
    fn exists(&self, path: &Path) -> bool {
        !transfer::path_holds_nul(path) && path.try_exists().unwrap_or(false)
    }
    fn inspect_source(&self, path: &Path) -> transfer::SourceInspection {
        transfer::inspect_upload_source(path)
    }
    fn temp_path(&self, path: &Path) -> Result<PathBuf, TempPathError> {
        let id = (self.random)().map_err(|_| TempPathError::RandomUnavailable)?;
        entries::temp_path(path, id)
    }
    fn submit(
        &self,
        job: Arc<Job>,
        callbacks: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        let content_type = self.content_type(&job)?;
        if let Some(refusal) = &self.request.refusal {
            return Err(SubmitError::Local(refusal.clone()));
        }
        // Botocore resolves the endpoint before it validates the key, so the
        // command's refusal outranks the key's.
        if job.direction == transfer::Direction::Upload
            && let Some(refusal) = transfer::upload_key_refusal(&job.raw_key)
        {
            return Err(SubmitError::Local(refusal));
        }
        if let Some(failure) = self.directory_source_failure(&job) {
            return Err(SubmitError::RawLocal(failure));
        }
        let runtime = self
            .runtime
            .as_deref()
            .ok_or_else(|| SubmitError::Local("transfer runtime missing".into()))?;
        if job.direction == transfer::Direction::Download {
            return self.submit_download(runtime, &job, callbacks);
        }
        let options = request_options(&self.request, &job, None, content_type);
        runtime
            .submit(options, None, Callbacks::hooked(callbacks))
            .map_err(SubmitError::Transfer)
    }
    fn finalize(&self, job: &Job, result: &TransferResult) -> Finalize {
        output::finalize(job, result)
    }
    fn delete_source(&self, job: &Job) -> Result<(), SourceDeleteError> {
        let transfer::SourceDisposition::Delete { user_agent } = &self.request.sources else {
            return Ok(());
        };
        if self.request.direction == transfer::Direction::Upload {
            return std::fs::remove_file(&job.local_path).map_err(SourceDeleteError::Local);
        }
        let runtime = self.runtime.as_deref();
        assert!(runtime.is_some(), "a transfer that succeeded had a runtime");
        let Some(runtime) = runtime else {
            return Ok(());
        };
        let options = source_delete_options(job, user_agent);
        let result = runtime.send(options).map_err(SourceDeleteError::Request)?;
        if result.error_code == 0 {
            Ok(())
        } else {
            Err(SourceDeleteError::Request(Box::new(result)))
        }
    }
    fn discard(&self, job: &Job) {
        output::abandon(job);
    }
    fn retire_attempt(
        &self,
        job: &Job,
        result: &TransferResult,
        await_shutdown: &dyn Fn(),
    ) -> Option<String> {
        output::retire(job, result, await_shutdown)
    }
    fn recover_region(&self, result: &TransferResult) -> Outcome {
        self.runtime
            .as_ref()
            .map_or(Outcome::Unavailable, |runtime| {
                runtime.recover_region(result)
            })
    }
}

impl CrtOperations {
    fn submit_download(
        &self,
        runtime: &dyn RequestRuntime,
        job: &Job,
        callbacks: Arc<dyn Completion>,
    ) -> Result<Box<dyn OwnedRequest>, SubmitError> {
        let size = job
            .size
            .ok_or_else(|| SubmitError::Local("DownloadMissingContentLength".into()))?;
        let failure = match output::prepare(job, self.service.as_deref(), size) {
            Ok(output::Output::RecvFile(path)) => {
                let options = request_options(&self.request, job, Some(path), None);
                match runtime.submit(options, None, Callbacks::hooked(Arc::clone(&callbacks))) {
                    Ok(request) => return Ok(request),
                    Err(result) => OutputFailure::Crt(result),
                }
            }
            Ok(output::Output::Native(output)) => {
                // A finish can beat this call's return, and its worker may
                // already have destroyed the output, so nothing here touches
                // it again.
                let options = RequestOptions {
                    check_object_size: job.size_listed,
                    ..request_options(&self.request, job, None, None)
                };
                return runtime
                    .submit(
                        options,
                        Some(body_callback(output)),
                        Callbacks::hooked(callbacks),
                    )
                    .map_err(SubmitError::Transfer);
            }
            Err(name) => OutputFailure::Write(name),
        };
        submit_without_output(&self.request, runtime, job, failure, callbacks)
    }
    fn content_type(&self, job: &Job) -> Result<Option<&[u8]>, SubmitError> {
        if job.direction != transfer::Direction::Upload {
            return Ok(None);
        }
        self.request
            .content_types
            .as_ref()
            .map(|database| database.guess(&job.local_path))
            .transpose()
            .map_err(|error| SubmitError::RawLocal(error.as_bytes().to_vec()))
            .map(Option::flatten)
    }
    fn directory_source_failure(&self, job: &Job) -> Option<Vec<u8>> {
        let single_upload =
            self.request.direction == transfer::Direction::Upload && self.request.object.is_some();
        if !single_upload || !std::fs::metadata(&job.local_path).is_ok_and(|m| m.is_dir()) {
            return None;
        }
        Some(transfer::directory_source_failure(&job.local_path))
    }
}

fn submit_without_output(
    request: &TransferRequest,
    runtime: &dyn RequestRuntime,
    job: &Job,
    failure: OutputFailure,
    callbacks: Arc<dyn Completion>,
) -> Result<Box<dyn OwnedRequest>, SubmitError> {
    output::record_failure(job, Some(failure.clone()));
    let refuse: CallbackBodyFn = Box::new(|_| Err(crt::s3::UNKNOWN_ERROR_CODE));
    let options = request_options(request, job, None, None);
    match runtime.submit(options, Some(refuse), Callbacks::new(callbacks, false)) {
        Ok(owned) => Ok(owned),
        Err(_) => {
            output::record_failure(job, None);
            Err(match failure {
                OutputFailure::Write(name) => SubmitError::Local(name),
                OutputFailure::Crt(result) => SubmitError::Transfer(result),
            })
        }
    }
}

fn request_options<'a>(
    request: &'a TransferRequest,
    job: &'a Job,
    filepath: Option<&'a Path>,
    content_type: Option<&'a [u8]>,
) -> RequestOptions<'a> {
    let key = job.request_key.as_bytes();
    let request_payer = request.headers.request_payer_value();
    let headers = request.headers.object.as_slice();
    match job.direction {
        transfer::Direction::Download => RequestOptions {
            kind: RequestKind::Get,
            key,
            filepath,
            object_size_hint: job.size,
            if_none_match: false,
            content_type,
            condition: job.condition.download_condition(),
            check_object_size: false,
            request_payer,
            user_agent: None,
            headers,
            checksum_algorithm: None,
            validate_checksum: request.checksums.validate_downloads,
        },
        transfer::Direction::Upload => RequestOptions {
            kind: RequestKind::Put,
            key,
            filepath: Some(&job.local_path),
            object_size_hint: job.size,
            if_none_match: request.no_overwrite,
            content_type,
            condition: None,
            check_object_size: false,
            request_payer,
            user_agent: None,
            headers,
            checksum_algorithm: request.checksums.upload_algorithm,
            validate_checksum: false,
        },
        // A delete sends the payer alone (`map_delete_object_params`): a sync
        // upload's object settings are its uploads' own.
        transfer::Direction::Delete => RequestOptions {
            kind: RequestKind::Delete,
            key,
            filepath: None,
            object_size_hint: None,
            if_none_match: false,
            content_type: None,
            condition: None,
            check_object_size: false,
            request_payer,
            user_agent: None,
            headers: &[],
            checksum_algorithm: None,
            validate_checksum: false,
        },
    }
}

fn source_delete_options<'a>(job: &'a Job, user_agent: &'a str) -> RequestOptions<'a> {
    RequestOptions {
        kind: RequestKind::Delete,
        key: job.request_key.as_bytes(),
        filepath: None,
        object_size_hint: None,
        if_none_match: false,
        content_type: None,
        condition: None,
        check_object_size: false,
        request_payer: None,
        user_agent: Some(user_agent.as_bytes()),
        headers: &[],
        checksum_algorithm: None,
        validate_checksum: false,
    }
}

fn body_callback(output: SharedOutput) -> CallbackBodyFn {
    Box::new(move |body| {
        match body {
            CallbackBody::Ticketed(chunk) => output.enqueue(Body::from(chunk)),
            CallbackBody::Transient { bytes, range_start } => output.write_now(bytes, range_start),
            CallbackBody::Missing => {
                output.fail(WriteError::Missing);
                Err(WriteError::Missing)
            }
        }
        .map_err(|_| crt::s3::UNKNOWN_ERROR_CODE)
    })
}

#[cfg(test)]
mod tests;
