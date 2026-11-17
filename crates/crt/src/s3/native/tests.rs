use super::*;
use std::sync::Condvar;
use std::time::{Duration, Instant};
mod body;
mod configuration;
mod discovery;
mod options;

#[derive(Debug, Default)]
struct Completion {
    state: Mutex<(Option<TransferResult>, bool)>,
    wake: Condvar,
    progress: AtomicU64,
}
impl RequestCallbacks for Completion {
    fn finish(&self, result: TransferResult) {
        lock(&self.state).0 = Some(result);
        self.wake.notify_all();
    }
    fn shutdown(&self) {
        lock(&self.state).1 = true;
        self.wake.notify_all();
    }
    fn progress(&self, bytes: u64) {
        self.progress.fetch_add(bytes, Ordering::Relaxed);
    }
}
const COMPLETION_TIMEOUT: Duration = Duration::from_secs(20);
impl Completion {
    fn submit(
        runtime: &Arc<Runtime>,
        options: RequestOptions<'_>,
        body: CallbackBodyFn,
    ) -> Result<(Arc<Self>, CallbackRequest), Box<TransferResult>> {
        let completion = Arc::new(Self::default());
        let callbacks = Arc::clone(&completion) as Arc<dyn RequestCallbacks>;
        let request = runtime.submit_callbacks(options, Some(body), callbacks)?;
        Ok((completion, request))
    }
    fn wait(
        self: &Arc<Self>,
        runtime: &Arc<Runtime>,
        request: CallbackRequest,
    ) -> Result<TransferResult, String> {
        let deadline = Instant::now() + COMPLETION_TIMEOUT;
        let state = lock(&self.state);
        let timeout = deadline.saturating_duration_since(Instant::now());
        let (mut state, _) = self
            .wake
            .wait_timeout_while(state, timeout, |state| state.0.is_none())
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let Some(result) = state.0.take() else {
            drop(state);
            request.cancel();
            return Err(abandon(runtime, "finish"));
        };
        drop(state);
        drop(request);
        while Arc::strong_count(self) > 1 {
            if Instant::now() > deadline {
                return Err(abandon(runtime, "shut down"));
            }
            std::thread::sleep(Duration::from_millis(1));
        }
        lock(&self.state)
            .1
            .then_some(result)
            .ok_or_else(|| "the request's callbacks were released without a shutdown".into())
    }
}
fn abandon(runtime: &Arc<Runtime>, step: &str) -> String {
    std::mem::forget(Arc::clone(runtime));
    format!("the request did not {step} within {COMPLETION_TIMEOUT:?}; its runtime is kept alive")
}
fn transfer(
    runtime: &Arc<Runtime>,
    options: RequestOptions<'_>,
    body: CallbackBodyFn,
) -> Result<TransferResult, Box<dyn std::error::Error>> {
    let (completion, request) = Completion::submit(runtime, options, body)?;
    Ok(completion.wait(runtime, request)?)
}
fn collect(received: Arc<Mutex<Vec<u8>>>) -> CallbackBodyFn {
    Box::new(move |body| {
        match body {
            CallbackBody::Ticketed(chunk) => lock(&received).extend_from_slice(chunk.as_bytes()),
            CallbackBody::Transient { bytes, .. } => lock(&received).extend_from_slice(bytes),
            CallbackBody::Missing => return Err(INVALID_ARGUMENT_ERROR_CODE),
        }
        Ok(())
    })
}
#[test]
fn a_path_the_crt_would_open_is_refused_when_it_holds_a_nul() {
    let options = |kind, filepath: Option<&'static str>| RequestOptions {
        kind,
        key: b"object",
        filepath: filepath.map(Path::new),
        object_size_hint: None,
        if_none_match: false,
        content_type: None,
        condition: None,
        check_object_size: false,
        request_payer: None,
        user_agent: None,
        headers: &[],
        checksum_algorithm: None,
        validate_checksum: false,
    };
    for (kind, path, body, accepted) in [
        (RequestKind::Get, "destination.tmp", false, true),
        (RequestKind::Get, "report\0.backup.tmp", false, false),
        (RequestKind::Get, "ignored\0.tmp", true, true),
        (RequestKind::Put, "upload.bin", false, true),
        (RequestKind::Put, "upload\0.bin", false, false),
    ] {
        match options(kind, Some(path)).checked_filepath(body) {
            Ok(filepath) => {
                assert!(accepted, "{path:?}");
                assert_eq!(filepath, path.as_bytes());
            }
            Err(code) => {
                assert!(!accepted, "{path:?}");
                assert_eq!(code, FILE_INVALID_PATH_ERROR_CODE);
                assert_eq!(error_name(code), b"AWS_ERROR_FILE_INVALID_PATH");
            }
        }
    }
    let head = options(RequestKind::Head, None).checked_filepath(false);
    assert_eq!(head.ok(), Some(&[][..]));
}
#[test]
fn only_a_body_callbacks_get_of_a_known_size_checks_its_length() {
    let options = |kind, object_size_hint, check_object_size| RequestOptions {
        kind,
        key: b"object",
        filepath: None,
        object_size_hint,
        if_none_match: false,
        content_type: None,
        condition: None,
        check_object_size,
        request_payer: None,
        user_agent: None,
        headers: &[],
        checksum_algorithm: None,
        validate_checksum: false,
    };
    for (kind, hint, check, body, expected) in [
        (RequestKind::Get, Some(7), true, true, Some(7)),
        (RequestKind::Get, Some(7), true, false, None),
        (RequestKind::Get, Some(7), false, true, None),
        (RequestKind::Get, None, true, true, None),
        (RequestKind::Put, Some(7), true, true, None),
        (RequestKind::Head, Some(7), true, true, None),
    ] {
        let options = options(kind, hint, check);
        let case = format!("{kind:?} {hint:?} {check} {body}");
        assert_eq!(options.expected_size(body), expected, "{case}");
        let raw = options.raw(b"", body, None, &[]);
        assert_eq!(raw.check_object_size, expected.is_some(), "{case}");
    }
}
#[test]
fn a_finish_without_a_status_keeps_the_headers_status() {
    let headers = |status| {
        let mut head = HeadObjectResult::default();
        head.transfer.response_status = status;
        head.content_length = Some(17);
        head
    };
    let finish = |code, status| TransferResult {
        error_code: code,
        response_status: status,
        ..TransferResult::default()
    };
    for (header_status, code, finish_status, status) in [
        (200, 0, 0, 200),
        (200, 0, 404, 404),
        (200, CANCELED_ERROR_CODE, 0, 200),
        (0, CANCELED_ERROR_CODE, 0, 0),
    ] {
        let merged = merge_transfer_falling_back_to_head_status(
            headers(header_status),
            finish(code, finish_status),
        );
        assert_eq!(merged.transfer.response_status, status);
        assert_eq!(merged.transfer.error_code, code);
        assert_eq!(merged.content_length, Some(17));
    }
}
#[test]
fn finish_and_shutdown_forward_values_once() {
    for (code, status) in [
        (INVALID_ARGUMENT_ERROR_CODE, 418),
        (0, 204),
        (UNKNOWN_ERROR_CODE, 0),
    ] {
        let state = Arc::new(RequestState {
            inner: Mutex::new(RequestInner::default()),
            submission: Arc::new(Submission::new(CrtMetaRequestOps)),
            proxy: String::new(),
            logger: None,
            progress: None,
            operation: b"",
            bytes_transferred: AtomicU64::new(0),
        });
        let weak = Arc::downgrade(&state);
        let data = Arc::into_raw(Arc::clone(&state)).cast_mut().cast();
        let result = c::ResultView {
            error_code: code,
            response_status: status,
            body: cursor(&[]),
            operation: cursor(&[]),
            region_header: cursor(&[]),
            region_header_present: false,
        };
        // SAFETY: this test owns the callback Arc exactly as submit does; finish
        // reads but does not free it, and shutdown consumes it once.
        unsafe {
            on_finish(&result, data);
            assert_eq!(Arc::strong_count(&state), 2);
            on_shutdown(data);
        }
        assert_eq!(Arc::strong_count(&state), 1);
        let result = state.submission.wait();
        assert_eq!(result.error_code, code);
        assert_eq!(result.response_status, status);
        drop(state);
        assert!(weak.upgrade().is_none());
    }
}
fn head_state(operation: &'static [u8]) -> Arc<RequestState> {
    Arc::new(RequestState {
        inner: Mutex::new(RequestInner::default()),
        submission: Arc::new(Submission::new(CrtMetaRequestOps)),
        proxy: String::new(),
        logger: None,
        progress: None,
        operation,
        bytes_transferred: AtomicU64::new(0),
    })
}
fn capture(state: &Arc<RequestState>, headers: &[(&[u8], &[u8])], status: i32, code: i32) {
    let names = headers
        .iter()
        .map(|(name, _)| cursor(name))
        .collect::<Vec<_>>();
    let values = headers
        .iter()
        .map(|(_, value)| cursor(value))
        .collect::<Vec<_>>();
    // SAFETY: the cursors and the callback state outlive the synchronous
    // capture, which neither retains nor frees the state.
    let rc = unsafe {
        c::zaws_callback_capture(
            names.as_ptr(),
            values.as_ptr(),
            headers.len(),
            status,
            code,
            Some(on_headers),
            Some(on_finish),
            Arc::as_ptr(state).cast_mut().cast(),
        )
    };
    assert_eq!(rc, 0);
    state.submission.shutdown();
}
#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "one test follows the metadata through every callback"
)]
fn callbacks_own_region_metadata_after_the_headers_are_released() {
    let _library = Library::acquire();
    let failed = head_state(b"HeadBucket");
    capture(&failed, &[(b"x-amz-bucket-region", b"eu-west-1")], 301, 1);
    let result = failed.submission.wait();
    assert!(result.service_error.region_header.is_present());
    assert_eq!(result.service_error.region_header.as_bytes(), b"eu-west-1");
    assert_eq!(result.service_error.operation.as_bytes(), b"HeadBucket");
    let head = head_state(b"HeadObject");
    capture(
        &head,
        &[
            (b"x-amz-bucket-region", b"eu-west-1"),
            (b"ETag", b"\"etag-1\""),
        ],
        200,
        0,
    );
    let result = head.submission.wait();
    assert_eq!(result.error_code, 0);
    assert_eq!(result.service_error.region_header.as_bytes(), b"eu-west-1");
    assert_eq!(lock(&head.inner).head.etag.as_bytes(), b"\"etag-1\"");
    let empty = head_state(b"HeadObject");
    capture(&empty, &[(b"x-amz-bucket-region", b"")], 400, 1);
    let result = empty.submission.wait();
    assert!(result.service_error.region_header.is_present());
    assert_eq!(
        crate::redirect::target_region(&result.service_error),
        crate::redirect::Target::Invalid
    );
    let absent = head_state(b"HeadObject");
    capture(&absent, &[], 404, 1);
    let result = absent.submission.wait();
    assert!(!result.service_error.region_header.is_present());
    assert!(!lock(&absent.inner).head.etag.is_present());
}
