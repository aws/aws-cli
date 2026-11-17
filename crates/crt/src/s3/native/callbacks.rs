use super::*;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};

/// Finish runs before shutdown; the request owner releases its reference after finish work.
pub trait RequestCallbacks: Send + Sync + fmt::Debug {
    fn finish(&self, result: TransferResult);
    fn shutdown(&self);
    fn progress(&self, _bytes: u64) {}
}
/// One body the CRT delivers to a scheduler-owned request.
#[derive(Debug)]
pub enum CallbackBody<'a> {
    /// A part whose buffer ticket keeps its bytes alive past the callback.
    Ticketed(BodyChunk),
    /// A single-request GET's response bytes, which no ticket keeps alive: they
    /// are valid only until the callback returns, so the consumer writes them
    /// before then. Empty for a body that carries no bytes.
    Transient { bytes: &'a [u8], range_start: u64 },
    /// A nonempty body whose bytes the CRT did not supply: its pointer is
    /// null. The consumer fails its output with `DownloadBodyMissing`, and
    /// the request fails.
    Missing,
}
/// Receives each body of a scheduler-owned request on the CRT's callback thread.
pub type CallbackBodyFn = Box<dyn for<'a> FnMut(CallbackBody<'a>) -> Result<(), i32> + Send>;
struct CallbackState {
    runtime: Arc<Runtime>,
    callbacks: Arc<dyn RequestCallbacks>,
    body: Mutex<Option<CallbackBodyFn>>,
    single_request: bool,
    bytes_transferred: AtomicU64,
    body_delivered: AtomicBool,
    expected_size: Option<u64>,
    size_changed: AtomicBool,
}
impl fmt::Debug for CallbackState {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        out.debug_struct("CallbackState")
            .field("callbacks", &self.callbacks)
            .finish_non_exhaustive()
    }
}
/// One counted CRT request reference. Drop releases it without waiting for shutdown.
#[derive(Debug)]
pub struct CallbackRequest {
    meta: NonNull<ffi::AwsS3MetaRequest>,
}
// SAFETY: CRT references and cancellation are thread-safe; the owner serializes release.
unsafe impl Send for CallbackRequest {}
// SAFETY: shared access can only cancel the live counted reference.
unsafe impl Sync for CallbackRequest {}
impl CallbackRequest {
    pub fn cancel(&self) {
        // SAFETY: self retains a counted reference throughout this call.
        unsafe {
            ffi::aws_s3_meta_request_cancel(self.meta.as_ptr());
        }
    }
}
impl Drop for CallbackRequest {
    fn drop(&mut self) {
        // SAFETY: this value owns exactly the initial reference returned by submit.
        unsafe {
            ffi::aws_s3_meta_request_release(self.meta.as_ptr());
        }
    }
}
impl Runtime {
    /// Submits without a waiting thread; callback state retains the runtime through shutdown.
    /// The caller must retain its runtime Arc until callback owners have dropped, so the
    /// runtime destructor joins CRT workers from the caller rather than a callback thread.
    pub fn submit_callbacks(
        self: &Arc<Self>,
        options: RequestOptions<'_>,
        body: Option<CallbackBodyFn>,
        callbacks: Arc<dyn RequestCallbacks>,
    ) -> Result<CallbackRequest, Box<TransferResult>> {
        let filepath = options
            .checked_filepath(body.is_some())
            .map_err(|code| self.refused(code))?;
        let threshold = self.options().single_request_threshold;
        let headers = raw_headers(options.headers);
        let raw = options.raw(filepath, body.is_some(), threshold, &headers);
        let expected_size = options.expected_size(body.is_some());
        let state = Arc::new(CallbackState {
            runtime: Arc::clone(self),
            callbacks,
            body: Mutex::new(body),
            single_request: raw.single_request,
            bytes_transferred: AtomicU64::new(0),
            body_delivered: AtomicBool::new(false),
            expected_size,
            size_changed: AtomicBool::new(false),
        });
        let raw_state = Arc::into_raw(state).cast_mut().cast();
        let headers = expected_size.map(|_| headers_callback as c::HeadersFn);
        // SAFETY: C copies options synchronously; its retained Arc is consumed only by shutdown.
        let submitted = check_pointer(unsafe {
            c::zaws_submit(
                self.pointer(),
                &raw,
                headers,
                Some(body_callback),
                Some(finish_callback),
                Some(progress_callback),
                Some(shutdown_callback),
                raw_state,
            )
        });
        let meta = match submitted {
            Ok(meta) => meta,
            Err(code) => {
                // SAFETY: rejected submissions retain no callback and cannot call shutdown.
                drop(unsafe { Arc::from_raw(raw_state.cast::<CallbackState>()) });
                return Err(self.refused(code));
            }
        };
        Ok(CallbackRequest { meta })
    }
}
/// The headers callback of a GET that checks its response's length
/// (`CallbackState::expected_size`). aws-c-s3 calls it once, before any
/// body is delivered: with a single request's response headers, or with a
/// ranged GET's discovery headers, whose Content-Length it rewrites to the
/// whole object's (s3_auto_ranged_get.c
/// `s_s3_auto_ranged_get_request_finished`). Failing it fails the meta
/// request, which then delivers no body.
unsafe extern "C" fn headers_callback(
    headers: *const c::HeadHeaders,
    status: i32,
    data: *mut c_void,
) -> i32 {
    // SAFETY: the callback Arc and the borrowed header view are valid for this call.
    let (state, headers) = unsafe { (&*data.cast::<CallbackState>(), &*headers) };
    let Some(expected) = state.expected_size else {
        return 0;
    };
    // SAFETY: the cursor borrows CRT headers that outlive this callback.
    let length = unsafe { bytes(headers.length) };
    if !response_length_differs(length, status, expected) {
        return 0;
    }
    state.size_changed.store(true, Ordering::Release);
    // SAFETY: this only writes the calling thread's CRT error code, which
    // aws-c-s3 reads as the meta request's error.
    unsafe { ffi::aws_raise_error(SIZE_CHANGED_ERROR_CODE) }
}
/// Whether a successful response's `length` may differ from `expected`: its
/// Content-Length is another, or it has none, as a chunked response can, so
/// its length is known only once its body has been written. An error
/// response, which aws-c-s3 also hands the headers callback, and a length
/// that does not parse are left to the checks that follow the body.
fn response_length_differs(length: &[u8], status: i32, expected: u64) -> bool {
    if status != 200 && status != 206 {
        return false;
    }
    if length.is_empty() {
        return true;
    }
    std::str::from_utf8(length)
        .ok()
        .and_then(|text| text.parse::<u64>().ok())
        .is_some_and(|length| length != expected)
}
unsafe extern "C" fn body_callback(
    _meta: *mut ffi::AwsS3MetaRequest,
    body: ffi::AwsByteCursor,
    offset: u64,
    ticket: *mut ffi::AwsS3BufferTicket,
    data: *mut c_void,
) -> i32 {
    // SAFETY: the callback Arc remains live until shutdown.
    let state = unsafe { &*data.cast::<CallbackState>() };
    let mut callback = lock(&state.body);
    let Some(callback) = callback.as_mut() else {
        return 0;
    };
    let offered = OfferedBody {
        len: body.len,
        storage: NonNull::new(body.ptr),
        ticket: NonNull::new(ticket),
    };
    let forwarded = forward_body(
        &mut CrtBodyTicketOps,
        offered,
        state.single_request,
        &state.body_delivered,
        // SAFETY: the CRT keeps the cursor's storage live until this
        // callback returns, and the consumer's borrow ends with it.
        |delivery| callback(unsafe { delivered_body(delivery, body.len, offset) }),
    );
    match forwarded {
        Ok(()) => 0,
        // SAFETY: this only writes the calling thread's CRT error code.
        Err(code) => unsafe { ffi::aws_raise_error(code) },
    }
}
#[derive(Debug)]
struct CrtBodyTicketOps;
impl BodyTicketOps for CrtBodyTicketOps {
    type Ticket = NonNull<ffi::AwsS3BufferTicket>;
    fn acquire(&mut self, ticket: Self::Ticket) -> Option<Self::Ticket> {
        // SAFETY: the CRT keeps the ticket it offers live for the callback.
        NonNull::new(unsafe { ffi::aws_s3_buffer_ticket_acquire(ticket.as_ptr()) })
    }
}
/// # Safety
/// `delivery` must come from the running body callback's cursor of `len`
/// bytes; the returned borrow must not outlive that callback.
unsafe fn delivered_body<'a>(
    delivery: BodyDelivery<NonNull<u8>, NonNull<ffi::AwsS3BufferTicket>>,
    len: usize,
    offset: u64,
) -> CallbackBody<'a> {
    match delivery {
        BodyDelivery::Empty => CallbackBody::Transient {
            bytes: &[],
            range_start: offset,
        },
        BodyDelivery::Missing => CallbackBody::Missing,
        BodyDelivery::Lent(pointer) => CallbackBody::Transient {
            // SAFETY: the caller supplies the nonnull pointer of a live
            // `len`-byte cursor.
            bytes: unsafe { std::slice::from_raw_parts(pointer.as_ptr(), len) },
            range_start: offset,
        },
        BodyDelivery::Ticketed(pointer, ticket) => CallbackBody::Ticketed(BodyChunk {
            ticket,
            pointer,
            len,
            range_start: offset,
            _keep_library_alive: Library::acquire(),
        }),
    }
}
unsafe extern "C" fn progress_callback(bytes: u64, data: *mut c_void) {
    // SAFETY: the callback Arc remains live until shutdown.
    let state = unsafe { &*data.cast::<CallbackState>() };
    state.bytes_transferred.fetch_add(bytes, Ordering::Relaxed);
    state.callbacks.progress(bytes);
}
unsafe extern "C" fn finish_callback(result: *const c::ResultView, data: *mut c_void) {
    // SAFETY: C supplies callback-lifetime result storage and a retained callback Arc.
    let (state, raw) = unsafe { (&*data.cast::<CallbackState>(), &*result) };
    // SAFETY: all cursors are copied before returning from this callback.
    let mut result = unsafe {
        result_from_view(
            raw,
            state.runtime.options().proxy_url.as_deref().unwrap_or(""),
        )
    };
    state.runtime.stamp(&mut result);
    result.bytes_transferred = state.bytes_transferred.load(Ordering::Acquire);
    result.body_delivered = state.body_delivered.load(Ordering::Acquire);
    // Only the failure the headers callback caused is a size change: another
    // error that finished the request first, or the CRT's own
    // OBJECT_MODIFIED, is reported as itself.
    result.size_changed =
        raw.error_code == SIZE_CHANGED_ERROR_CODE && state.size_changed.load(Ordering::Acquire);
    if let Some(logger) = state.runtime.logger() {
        record_outcome(&logger, raw.error_code, raw.response_status);
    }
    let callbacks = Arc::clone(&state.callbacks);
    callbacks.finish(result);
}
unsafe extern "C" fn shutdown_callback(data: *mut c_void) {
    // SAFETY: the final callback consumes the unique retained callback Arc.
    let state = unsafe { Arc::from_raw(data.cast::<CallbackState>()) };
    let Some(CallbackState {
        runtime,
        callbacks,
        body,
        ..
    }) = Arc::into_inner(state)
    else {
        std::process::abort()
    };
    drop(body);
    callbacks.shutdown();
    drop(runtime);
    drop(callbacks);
}

#[cfg(test)]
mod tests;
