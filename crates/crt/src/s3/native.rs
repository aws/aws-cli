use super::*;
mod callbacks;
use crate::crt_error::check_pointer;
use crate::runtime::{Library, Runtime};
use crate::signal::lock;
pub use callbacks::{CallbackBody, CallbackBodyFn, CallbackRequest, RequestCallbacks};
use crt_sys::{self as ffi, native as c};
use std::ffi::{CStr, c_void};
use std::path::Path;
use std::ptr::NonNull;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

pub(crate) fn cursor(bytes: &[u8]) -> ffi::AwsByteCursor {
    ffi::AwsByteCursor::from_bytes(bytes)
}
unsafe fn bytes<'a>(value: ffi::AwsByteCursor) -> &'a [u8] {
    if value.len == 0 {
        return &[];
    }
    // SAFETY: callers supply a live CRT cursor and constrain its returned borrow.
    unsafe { std::slice::from_raw_parts(value.ptr, value.len) }
}
fn copy_c_string(pointer: *const std::ffi::c_char) -> Vec<u8> {
    if pointer.is_null() {
        return Vec::new();
    }
    // SAFETY: CRT lookup returns a static NUL-terminated string while initialized.
    unsafe { CStr::from_ptr(pointer).to_bytes().to_vec() }
}
/// The CRT's name for `code`, `AWS_ERROR_OOM` for example; empty for a code
/// the CRT does not recognize.
pub fn error_name(code: i32) -> Vec<u8> {
    let _library = Library::acquire();
    // SAFETY: CRT accepts any integer error code.
    copy_c_string(unsafe { ffi::rust_crt_error_name(code) })
}
/// The CRT's sentence for `code`; empty for a code the CRT does not
/// recognize. Holds its own `Library` reference, as [`error_name`] does.
pub fn error_message(code: i32) -> Vec<u8> {
    let _library = Library::acquire();
    // SAFETY: CRT accepts any integer error code.
    copy_c_string(unsafe { ffi::rust_crt_error_message(code) })
}
impl TransferResult {
    pub fn from_crt_error(code: i32) -> Self {
        let mut result = Self {
            error_code: code,
            ..Self::default()
        };
        if code != 0 {
            result.crt_name.set(&error_name(code));
            result.crt_message.set(&error_message(code));
        }
        result
    }
    pub fn invalid_argument() -> Self {
        Self::from_crt_error(INVALID_ARGUMENT_ERROR_CODE)
    }
}
/// Reads `<Error><Code>` and `<Message>` out of an S3 error response body
/// as botocore reads them ([`error_body`]), which reports the HTTP status
/// instead when the body is not UTF-8 or not well-formed XML, so such a body
/// leaves both empty. The message is copied whole, as botocore keeps it.
/// The region and whether it can be trusted still come from the CRT's
/// parser, whose reading redirects have always used: a body whose fields
/// it cannot decode leaves the region untrusted.
pub fn parse_service_error_body(body: &[u8], error: &mut ServiceError) {
    if body.is_empty() {
        return;
    }
    let mut region = BoundedText::default();
    error.region_body_invalid = crt_error_scan(body, &mut region).is_err();
    error.region_body = region;
    let Some(fields) = error_body::read(body) else {
        return;
    };
    if let Some(code) = fields.code {
        error.code.set(&code.text());
    }
    if let Some(message) = fields.message {
        error.message = message.text();
    }
}
fn crt_error_scan(body: &[u8], region: &mut BoundedText<REGION_MAX>) -> Result<(), i32> {
    listing::parse_document(body, &mut |root| {
        if root.name() != b"Error" {
            return Ok(());
        }
        root.children(&mut |child| {
            match child.name().as_slice() {
                b"Code" | b"Message" => {
                    listing::xml_text(&child.body()?)?;
                }
                b"Region" => region.set(&listing::xml_text(&child.body()?)?),
                _ => {}
            }
            Ok(())
        })
    })
}
/// # Safety
/// `raw` must be the view the shim passed to the running finish callback.
pub(crate) unsafe fn result_from_view(raw: &c::ResultView, proxy: &str) -> TransferResult {
    // SAFETY: the caller guarantees callback-lifetime cursors, copied here.
    let mut result = unsafe {
        transfer_result(
            raw.error_code,
            raw.response_status,
            bytes(raw.body),
            bytes(raw.operation),
            proxy,
        )
    };
    if raw.error_code != 0 && raw.region_header_present {
        // SAFETY: as above.
        result
            .service_error
            .region_header
            .set(unsafe { bytes(raw.region_header) });
    }
    result
}
pub fn transfer_result(
    code: i32,
    status: i32,
    body: &[u8],
    operation: &[u8],
    proxy: &str,
) -> TransferResult {
    let mut result = TransferResult::from_crt_error(code);
    result.response_status = status;
    if code == 0 {
        return result;
    }
    result.service_error.operation.set(operation);
    parse_service_error_body(body, &mut result.service_error);
    if result.service_error.code.as_bytes() == b"PreconditionFailed" {
        result.response_status = 412;
    }
    result.proxy_url = masked_proxy(proxy);
    result
}
pub fn parse_http_date_epoch_seconds(value: &[u8]) -> Option<i64> {
    let mut result = 0;
    // SAFETY: the parser consumes the input cursor synchronously.
    (unsafe { c::zaws_parse_http_date(cursor(value), &mut result) } == 0).then_some(result)
}
/// The headers a GET, HEAD or PUT message carries after its host.
#[derive(Debug, Clone, Copy)]
pub struct TransferHeaders<'a> {
    /// Sent as `content-length` when set.
    pub content_length: Option<u64>,
    /// Sent as `Content-Type` when set.
    pub content_type: Option<&'a [u8]>,
    /// Send `If-None-Match: *`.
    pub if_none_match: bool,
    /// Sent as `If-Match` when set.
    pub if_match: Option<&'a [u8]>,
    /// Sent as `x-amz-request-payer` when set.
    pub request_payer: Option<&'a [u8]>,
    /// Sent in order after the request payer.
    pub headers: &'a [super::Header],
    /// The `user-agent` value, the runtime's for a submitted request.
    pub user_agent: &'a [u8],
}
/// A real CRT request message whose borrowed header bytes never escape its owner.
#[derive(Debug)]
pub struct HttpMessage {
    pointer: NonNull<c::HttpMessage>,
    _library: Library,
}
impl HttpMessage {
    /// The message `zaws_submit` builds.
    pub fn new(
        host: &[u8],
        path: &[u8],
        method: &[u8],
        headers: TransferHeaders<'_>,
    ) -> Result<Self, Box<TransferResult>> {
        let library = Library::acquire();
        let extra = raw_headers(headers.headers);
        // SAFETY: CRT copies the cursors, `extra`'s among them, during
        // construction.
        let pointer = unsafe {
            c::zaws_message_new(
                cursor(host),
                cursor(path),
                cursor(method),
                headers
                    .content_length
                    .as_ref()
                    .map_or(std::ptr::null(), |v| v),
                cursor(headers.content_type.unwrap_or_default()),
                headers.if_none_match,
                cursor(headers.if_match.unwrap_or_default()),
                cursor(headers.request_payer.unwrap_or_default()),
                extra.as_ptr(),
                extra.len(),
                cursor(headers.user_agent),
            )
        };
        Ok(Self {
            pointer: check_pointer(pointer).map_err(TransferResult::from_crt_error)?,
            _library: library,
        })
    }
    fn field(&self, index: u32) -> Option<(Vec<u8>, Vec<u8>)> {
        let mut name = cursor(&[]);
        let mut value = cursor(&[]);
        // SAFETY: self owns the live message, and outputs are copied before return.
        if unsafe { c::zaws_message_field(self.pointer.as_ptr(), index, &mut name, &mut value) }
            != 0
        {
            return None;
        }
        // SAFETY: cursors borrow this still-live message.
        Some(unsafe { (bytes(name).to_vec(), bytes(value).to_vec()) })
    }
    pub fn method(&self) -> Vec<u8> {
        self.field(0).map_or_else(Vec::new, |field| field.1)
    }
    pub fn path(&self) -> Vec<u8> {
        self.field(1).map_or_else(Vec::new, |field| field.1)
    }
    pub fn headers(&self) -> Vec<(Vec<u8>, Vec<u8>)> {
        // SAFETY: self owns a live message.
        let count = unsafe { c::aws_http_message_get_header_count(self.pointer.as_ptr()) };
        (0..count)
            .filter_map(|index| self.field(index as u32 + 2))
            .collect()
    }
}
impl Drop for HttpMessage {
    fn drop(&mut self) {
        // SAFETY: this owner releases its sole reference before its library guard.
        unsafe {
            c::aws_http_message_release(self.pointer.as_ptr());
        }
    }
}

/// The request a submission sends; each discriminant is the shim's
/// `enum zaws_request_kind` value.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(i32)]
pub enum RequestKind {
    /// A GetObject, configured by the shim's `s_get_object_meta_options`.
    Get,
    /// A HeadObject, configured by the shim's `s_head_object_meta_options`.
    Head,
    /// A PutObject, configured by the shim's `s_put_object_meta_options`.
    Put,
    /// A HEAD of the bucket itself, sent to the endpoint path verbatim.
    HeadBucket,
    /// A DeleteObject, one DEFAULT meta request.
    Delete,
}
const _: () = {
    assert!(RequestKind::Get as i32 == c::REQUEST_KIND_GET);
    assert!(RequestKind::Head as i32 == c::REQUEST_KIND_HEAD);
    assert!(RequestKind::Put as i32 == c::REQUEST_KIND_PUT);
    assert!(RequestKind::HeadBucket as i32 == c::REQUEST_KIND_HEAD_BUCKET);
    assert!(RequestKind::Delete as i32 == c::REQUEST_KIND_DELETE);
};
impl RequestKind {
    fn raw(self) -> i32 {
        self as i32
    }
    fn head_operation(self) -> &'static [u8] {
        match self {
            Self::Head => b"HeadObject",
            Self::HeadBucket => b"HeadBucket",
            Self::Get | Self::Put | Self::Delete => b"",
        }
    }
}
#[derive(Debug, Clone, Copy)]
pub struct RequestOptions<'a> {
    pub kind: RequestKind,
    pub key: &'a [u8],
    pub filepath: Option<&'a Path>,
    pub object_size_hint: Option<u64>,
    pub if_none_match: bool,
    pub content_type: Option<&'a [u8]>,
    /// A download's condition, which a GET sends as `download_condition`
    /// decides; never sent by other requests.
    pub condition: Option<DownloadCondition<'a>>,
    /// Fails a GET whose body reaches a callback when its response reports a
    /// length other than `object_size_hint`, or none, before any of its body
    /// reaches the callback, and marks its result `size_changed`. For a
    /// listing's size, which can be older than the object the GET fetches. A
    /// GET the CRT writes to its file is not checked: that file takes
    /// whatever length the response has.
    pub check_object_size: bool,
    /// Sent as `x-amz-request-payer`: `--request-payer`, which every object
    /// request of a transfer confirms.
    pub request_payer: Option<&'a [u8]>,
    /// Sent as `user-agent` in place of the runtime's; None sends the
    /// runtime's.
    pub user_agent: Option<&'a [u8]>,
    /// Sent in order after the request's own headers, before `user-agent`.
    pub headers: &'a [super::Header],
    /// A PUT's trailing checksum algorithm, which it sends whatever the
    /// runtime's request checksum mode; None sends the mode's CRC64NVME, or
    /// nothing. Other requests send no checksum of their own.
    pub checksum_algorithm: Option<super::ChecksumAlgorithm>,
    /// Validates a GET's response checksum whatever the runtime's response
    /// checksum mode; other requests validate nothing.
    pub validate_checksum: bool,
}
impl<'a> RequestOptions<'a> {
    fn checked_filepath(&self, has_body_callback: bool) -> Result<&'a [u8], i32> {
        let filepath = self
            .filepath
            .map_or(&[][..], |p| p.as_os_str().as_encoded_bytes());
        let opened = match self.kind {
            RequestKind::Get => !has_body_callback,
            RequestKind::Put => true,
            RequestKind::Head | RequestKind::HeadBucket | RequestKind::Delete => false,
        };
        if opened && filepath.contains(&0) {
            return Err(FILE_INVALID_PATH_ERROR_CODE);
        }
        Ok(filepath)
    }
    fn single_request(&self, threshold: Option<u64>) -> bool {
        super::single_request(threshold, self.object_size_hint)
    }
    fn expected_size(&self, has_body_callback: bool) -> Option<u64> {
        let checked = self.kind == RequestKind::Get && has_body_callback && self.check_object_size;
        self.object_size_hint.filter(|_| checked)
    }
    fn raw(
        &self,
        filepath: &[u8],
        has_body_callback: bool,
        threshold: Option<u64>,
        headers: &[c::Header],
    ) -> c::RequestOptions {
        let condition = match self.kind {
            RequestKind::Get => {
                super::download_condition(threshold, self.object_size_hint, self.condition)
            }
            RequestKind::Head
            | RequestKind::Put
            | RequestKind::HeadBucket
            | RequestKind::Delete => None,
        };
        let checksum = condition.map(|condition| condition.full_object_checksum);
        let (expected_checksum, expected_checksum_algorithm) = match checksum {
            Some(FullObjectChecksum::Known { algorithm, value }) => (&value[..], *algorithm as i32),
            Some(FullObjectChecksum::Unknown | FullObjectChecksum::Unavailable) | None => {
                (&[][..], 0)
            }
        };
        c::RequestOptions {
            kind: self.kind.raw(),
            checksum_algorithm: self
                .checksum_algorithm
                .map_or(0, |algorithm| algorithm as i32),
            key: cursor(self.key),
            filepath: cursor(filepath),
            single_request: self.single_request(threshold),
            has_body_callback,
            if_none_match: self.if_none_match,
            check_object_size: self.expected_size(has_body_callback).is_some(),
            validate_checksum: self.validate_checksum,
            content_type: cursor(self.content_type.unwrap_or_default()),
            if_match: cursor(condition.map_or(&[][..], |condition| condition.etag)),
            request_payer: cursor(self.request_payer.unwrap_or_default()),
            user_agent: cursor(self.user_agent.unwrap_or_default()),
            headers: headers.as_ptr(),
            header_count: headers.len(),
            expected_checksum: cursor(expected_checksum),
            expected_checksum_algorithm,
            checksum_unavailable: checksum == Some(&FullObjectChecksum::Unavailable),
        }
    }
}
/// A ticketed GET part's CRT pool storage; its acquired ticket reference
/// remains owned until the chunk is dropped.
#[derive(Debug)]
pub struct BodyChunk {
    ticket: NonNull<ffi::AwsS3BufferTicket>,
    pointer: NonNull<u8>,
    len: usize,
    pub range_start: u64,
    _keep_library_alive: Library,
}
// SAFETY: the acquired ticket keeps immutable receive bytes alive across threads.
unsafe impl Send for BodyChunk {}
// SAFETY: only immutable access to acquired receive bytes is exposed.
unsafe impl Sync for BodyChunk {}
impl BodyChunk {
    /// NUMA node of a custom source-pool ticket, if the request used one.
    pub fn source_node(&self) -> Option<u32> {
        // SAFETY: this chunk retains the ticket; the pool checks its vtable
        // before interpreting custom metadata and keeps its node immutable.
        unsafe { crate::source_pool::ticket_node(self.ticket.as_ptr()) }
    }
    pub fn as_bytes(&self) -> &[u8] {
        // SAFETY: pointer/len originated in a CRT callback and the acquired
        // ticket retains those immutable bytes.
        unsafe { std::slice::from_raw_parts(self.pointer.as_ptr(), self.len) }
    }
}
impl Drop for BodyChunk {
    fn drop(&mut self) {
        // SAFETY: this chunk owns exactly one acquired reference.
        unsafe {
            ffi::aws_s3_buffer_ticket_release(self.ticket.as_ptr());
        }
    }
}
struct RequestState {
    inner: Mutex<RequestInner>,
    submission: Arc<Submission<CrtMetaRequestOps>>,
    proxy: String,
    logger: Option<Arc<crate::debug::Logger>>,
    progress: Option<Arc<dyn Fn(u64) + Send + Sync>>,
    operation: &'static [u8],
    bytes_transferred: AtomicU64,
}
#[derive(Debug, Default)]
struct RequestInner {
    head: HeadObjectResult,
}
impl fmt::Debug for RequestState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RequestState")
            .field("inner", &self.inner)
            .finish_non_exhaustive()
    }
}
/// One asynchronous reference borrowing the runtime until final callback shutdown.
#[derive(Debug)]
pub struct Request<'a> {
    runtime: &'a Runtime,
    state: Arc<RequestState>,
    meta: Option<NonNull<ffi::AwsS3MetaRequest>>,
    registration: Option<cli_core::interrupt::Registration<'a>>,
}
impl Runtime {
    /// Submits a request that Ctrl-C through `interrupt` can cancel from
    /// the moment it is adopted until it finishes. A GET's body reaches no
    /// consumer here: it goes to the request's file, or nowhere without one.
    pub fn submit<'a>(
        &'a self,
        options: RequestOptions<'_>,
        interrupt: &'a cli_core::interrupt::State,
    ) -> Result<Request<'a>, Box<TransferResult>> {
        self.submit_with_progress(options, None, interrupt)
    }
    /// Supplies the command's progress recorder before any network callback can run.
    pub fn submit_with_progress<'a>(
        &'a self,
        options: RequestOptions<'_>,
        progress: Option<Arc<dyn Fn(u64) + Send + Sync>>,
        interrupt: &'a cli_core::interrupt::State,
    ) -> Result<Request<'a>, Box<TransferResult>> {
        let filepath = options
            .checked_filepath(false)
            .map_err(|code| self.refused(code))?;
        let threshold = self.options().single_request_threshold;
        let headers = raw_headers(options.headers);
        let raw_options = options.raw(filepath, false, threshold, &headers);
        let state = Arc::new(RequestState {
            inner: Mutex::new(RequestInner::default()),
            submission: Arc::new(Submission::new(CrtMetaRequestOps)),
            proxy: self.options().proxy_url.clone().unwrap_or_default(),
            logger: self.logger(),
            progress,
            operation: options.kind.head_operation(),
            bytes_transferred: AtomicU64::new(0),
        });
        let callback_state = Arc::into_raw(Arc::clone(&state)).cast_mut().cast();
        // SAFETY: the callback owns one Arc until shutdown, the returned Request
        // borrows the runtime, and the shim copies request metadata synchronously.
        let submitted = check_pointer(unsafe {
            c::zaws_submit(
                self.pointer(),
                &raw_options,
                Some(on_headers),
                None,
                Some(on_finish),
                Some(on_progress),
                Some(on_shutdown),
                callback_state,
            )
        });
        let meta = match submitted {
            Ok(meta) => meta,
            Err(code) => {
                // SAFETY: failed submit guarantees no callbacks and retains no Arc.
                drop(unsafe { Arc::from_raw(callback_state.cast::<RequestState>()) });
                return Err(self.refused(code));
            }
        };
        let registration = state.submission.adopt(MetaRequestHandle(meta), interrupt);
        Ok(Request {
            runtime: self,
            state,
            meta: Some(meta),
            registration: Some(registration),
        })
    }
    /// The HeadObject `head` describes on this runtime's endpoint,
    /// cancellable by `state`.
    pub fn head_object(
        &self,
        head: HeadObject<'_>,
        state: &cli_core::interrupt::State,
    ) -> Result<HeadObjectResult, Box<TransferResult>> {
        let options = RequestOptions {
            request_payer: head.request_payer,
            headers: head.headers,
            ..head_options(RequestKind::Head, head.key)
        };
        Ok(self.submit(options, state)?.wait())
    }
    /// A HeadBucket on this runtime's endpoint, cancellable by `state`; it
    /// reports the response's region header whatever its status.
    pub fn head_bucket(
        &self,
        state: &cli_core::interrupt::State,
    ) -> Result<HeadObjectResult, Box<TransferResult>> {
        self.head_with_interrupt(RequestKind::HeadBucket, b"", state)
    }
    fn head_with_interrupt(
        &self,
        kind: RequestKind,
        key: &[u8],
        state: &cli_core::interrupt::State,
    ) -> Result<HeadObjectResult, Box<TransferResult>> {
        Ok(self.submit(head_options(kind, key), state)?.wait())
    }
    pub(crate) fn refused(&self, code: i32) -> Box<TransferResult> {
        self.record_outcome(code, 0);
        Box::new(TransferResult::from_crt_error(code))
    }
    /// The client-region identity requests carry as provenance.
    pub fn client_region(&self) -> &str {
        &self.options().region
    }
    pub(crate) fn stamp(&self, result: &mut TransferResult) {
        result.request_region.set(self.client_region().as_bytes());
        result
            .endpoint_url
            .set(self.options().endpoint_url.as_bytes());
    }
}
fn raw_headers(headers: &[super::Header]) -> Vec<c::Header> {
    headers
        .iter()
        .map(|header| c::Header {
            name: cursor(&header.name),
            value: cursor(&header.value),
        })
        .collect()
}
/// A HeadObject's key and what it sends besides: a download's request payer
/// and its headers, the customer key among them.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct HeadObject<'a> {
    pub key: &'a [u8],
    pub request_payer: Option<&'a [u8]>,
    pub headers: &'a [super::Header],
}
fn head_options(kind: RequestKind, key: &[u8]) -> RequestOptions<'_> {
    RequestOptions {
        kind,
        key,
        filepath: None,
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
    }
}
impl Request<'_> {
    pub fn cancel(&self) {
        if let Some(meta) = self.meta {
            // SAFETY: self owns a counted meta-request reference.
            unsafe {
                ffi::aws_s3_meta_request_cancel(meta.as_ptr());
            }
        }
    }
    pub fn wait(mut self) -> HeadObjectResult {
        self.wait_inner()
    }
    fn wait_inner(&mut self) -> HeadObjectResult {
        let transfer = self.state.submission.wait_with_unregister(|| {
            self.registration.take();
        });
        self.meta = None;
        let mut result = merge_transfer_falling_back_to_head_status(
            lock(&self.state.inner).head.clone(),
            transfer,
        );
        self.runtime.stamp(&mut result.transfer);
        result.transfer.bytes_transferred = self.state.bytes_transferred.load(Ordering::Acquire);
        result
    }
    pub fn runtime(&self) -> &Runtime {
        self.runtime
    }
}
fn merge_transfer_falling_back_to_head_status(
    mut head: HeadObjectResult,
    transfer: TransferResult,
) -> HeadObjectResult {
    let header_status = head.transfer.response_status;
    head.transfer = transfer;
    if head.transfer.response_status == 0 {
        head.transfer.response_status = header_status;
    }
    head
}
impl Drop for Request<'_> {
    fn drop(&mut self) {
        if self.meta.is_some() {
            self.cancel();
            self.wait_inner();
        }
    }
}
unsafe extern "C" fn on_headers(
    headers: *const c::HeadHeaders,
    status: i32,
    data: *mut c_void,
) -> i32 {
    // SAFETY: the callback Arc and the borrowed header view are valid for this call.
    let (state, headers) = unsafe { (&*data.cast::<RequestState>(), &*headers) };
    // SAFETY: every cursor borrows CRT headers that outlive this callback.
    let (length, modified, storage_class, restore, etag, region) = unsafe {
        (
            bytes(headers.length),
            bytes(headers.modified),
            bytes(headers.storage_class),
            bytes(headers.restore),
            bytes(headers.etag),
            bytes(headers.region),
        )
    };
    // SAFETY: as above.
    let (checksum_type, crc32, crc32c, crc64nvme) = unsafe {
        (
            bytes(headers.checksum_type),
            bytes(headers.checksum_crc32),
            bytes(headers.checksum_crc32c),
            bytes(headers.checksum_crc64nvme),
        )
    };
    let mut inner = lock(&state.inner);
    inner.head.transfer.response_status = status;
    if headers.region_present {
        inner.head.transfer.service_error.region_header.set(region);
    }
    inner.head.content_length = std::str::from_utf8(length)
        .ok()
        .and_then(|value| value.parse().ok());
    inner.head.last_modified_epoch_seconds = parse_http_date_epoch_seconds(modified);
    if !etag.is_empty() {
        inner.head.etag.set(etag);
    }
    inner.head.archive = ArchiveState::from_headers(storage_class, restore);
    inner.head.full_object_checksum = FullObjectChecksum::from_head(
        headers.checksum_type_present.then_some(checksum_type),
        crc32,
        crc32c,
        crc64nvme,
        headers.checksum_reported,
    );
    0
}
unsafe extern "C" fn on_progress(bytes: u64, data: *mut c_void) {
    // SAFETY: the request callback reference remains owned until shutdown.
    let state = unsafe { &*data.cast::<RequestState>() };
    state.bytes_transferred.fetch_add(bytes, Ordering::Relaxed);
    if let Some(progress) = &state.progress {
        progress(bytes);
    }
}
unsafe extern "C" fn on_finish(result: *const c::ResultView, data: *mut c_void) {
    // SAFETY: C forwards a stack view with callback-lifetime cursors.
    let (state, result) = unsafe { (&*data.cast::<RequestState>(), &*result) };
    // SAFETY: strings are copied before this callback returns.
    let mut transfer = unsafe { result_from_view(result, &state.proxy) };
    {
        let inner = lock(&state.inner);
        let service = &mut transfer.service_error;
        if !service.region_header.is_present() {
            service.region_header = inner.head.transfer.service_error.region_header.clone();
        }
        if result.error_code != 0 && service.operation.is_empty() && !state.operation.is_empty() {
            service.operation.set(state.operation);
        }
    }
    if let Some(logger) = &state.logger {
        record_outcome(logger, result.error_code, result.response_status);
    }
    state.submission.finish(transfer);
}
unsafe extern "C" fn on_shutdown(data: *mut c_void) {
    // SAFETY: this is the final callback and consumes the single callback Arc.
    let state = unsafe { Arc::from_raw(data.cast::<RequestState>()) };
    state.submission.shutdown();
}

/// An opaque counted request identity used by the injected ownership protocol.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MetaRequestHandle(NonNull<ffi::AwsS3MetaRequest>);
// SAFETY: CRT counted meta-request references support calls across threads.
unsafe impl Send for MetaRequestHandle {}
// SAFETY: handle operations go through CRT synchronized reference APIs.
unsafe impl Sync for MetaRequestHandle {}
#[derive(Debug, Default)]
pub struct CrtMetaRequestOps;
impl MetaRequestOps for CrtMetaRequestOps {
    type Handle = MetaRequestHandle;
    fn cancel(&mut self, handle: Self::Handle) {
        // SAFETY: submission retains its reference until after finish.
        unsafe {
            ffi::aws_s3_meta_request_cancel(handle.0.as_ptr());
        }
    }
    fn release(&mut self, handle: Self::Handle) {
        // SAFETY: submission releases exactly the reference it adopted.
        unsafe {
            ffi::aws_s3_meta_request_release(handle.0.as_ptr());
        }
    }
}

#[cfg(test)]
mod tests;

pub(crate) fn record_outcome(logger: &crate::debug::Logger, code: i32, status: i32) {
    logger.record(
        "awscli.native.request",
        &format!(
            "Request outcome: HTTP {status}, CRT {code} ({}): {}",
            String::from_utf8_lossy(&error_name(code)),
            String::from_utf8_lossy(&error_message(code))
        ),
    );
}
