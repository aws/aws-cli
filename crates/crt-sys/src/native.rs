//! Opaque runtime and stable value transfers owned by the C shim.
use crate::{
    AwsAllocator, AwsByteBuf, AwsByteCursor, AwsHttpHeaders, AwsS3BufferTicket, AwsS3MetaRequest,
    CredentialsDelegateFn, GetCredentialsCallback, PoolFactoryFn, ShutdownFn,
};
use std::ffi::{c_char, c_int, c_void};

#[repr(C)]
#[derive(Debug)]
pub struct Runtime {
    _private: [u8; 0],
}
#[repr(C)]
#[derive(Debug, Default, Clone, Copy)]
pub struct RuntimeSnapshot {
    pub part_size: u64,
    pub max_part_size: u64,
    pub multipart_threshold: u64,
    pub memory_limit: u64,
    pub throughput_gbps: f64,
    pub disk_gbps: f64,
    pub max_connections: u32,
    pub connect_timeout_ms: u32,
    pub max_retries: u32,
    pub anonymous: bool,
    pub shared_tls: bool,
    pub verify_peer: bool,
    pub keep_alive: bool,
    pub file_io: bool,
    pub stream: bool,
    pub direct: bool,
    pub request_checksum: bool,
    pub response_checksum: bool,
}
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct SigningSnapshot {
    pub region: AwsByteCursor,
    pub service: AwsByteCursor,
    pub body: AwsByteCursor,
    pub validation: c_int,
    pub chain: bool,
    pub provider: bool,
    pub anonymous: bool,
    pub same_credentials: bool,
}
/// What the credentials stage built: a provider that asks the caller's
/// delegate for a signed runtime, and none for an unsigned one.
#[repr(C)]
#[derive(Debug, Default, Clone, Copy)]
pub struct CredentialsSnapshot {
    /// The provider asks the caller's delegate.
    pub delegate: bool,
}
#[repr(C)]
#[derive(Debug)]
pub struct HttpMessage {
    _private: [u8; 0],
}
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct RuntimeOptions {
    pub endpoint: AwsByteCursor,
    pub region: AwsByteCursor,
    pub signing_region: AwsByteCursor,
    pub proxy_url: AwsByteCursor,
    pub ca_bundle: *const c_char,
    pub throughput_target_gbps: f64,
    pub memory_limit: u64,
    pub max_connections: u32,
    pub event_loop_count: u16,
    pub pool_factory: Option<PoolFactoryFn>,
    pub pool_data: *mut c_void,
    pub ca_pem: AwsByteCursor,
    pub user_agent: AwsByteCursor,
    pub part_size: u64,
    pub multipart_upload_threshold: u64,
    pub disk_throughput_gbps: f64,
    pub max_attempts: u32,
    pub connect_timeout_ms: u32,
    pub verify_peer: bool,
    pub no_sign_request: bool,
    pub keep_alive: bool,
    pub has_file_io: bool,
    pub file_should_stream: bool,
    pub file_direct_io: bool,
    pub request_checksum: bool,
    pub response_checksum: bool,
    /// The CLI's own credentials, which the CRT calls for every request it
    /// signs, on its own threads. A signed runtime needs one.
    pub credentials_delegate: Option<CredentialsDelegateFn>,
    /// Valid until the credentials stage's shutdown callback.
    pub credentials_delegate_data: *mut c_void,
}
/// `struct zaws_credentials_view`: credentials a delegate answers a query
/// with, borrowed for the call. An empty session token or account id is
/// absent.
#[repr(C)]
#[derive(Clone, Copy)]
#[expect(
    missing_debug_implementations,
    reason = "the cursors point at a secret key"
)]
pub struct CredentialsView {
    pub access_key_id: AwsByteCursor,
    pub secret_access_key: AwsByteCursor,
    pub session_token: AwsByteCursor,
    pub account_id: AwsByteCursor,
    /// Seconds since the epoch, or `u64::MAX` for credentials that never
    /// expire.
    pub expiration_timepoint_seconds: u64,
}
/// `struct zaws_http_options`: one request over aws-c-http, outside the S3
/// client, borrowed for the call. `host` and `port` are where to connect,
/// in plaintext; `method`, `target` and `headers` are the request as sent,
/// the Host header included. A nonempty `service` signs it for that service
/// in `region`.
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct HttpOptions {
    pub host: AwsByteCursor,
    pub method: AwsByteCursor,
    pub target: AwsByteCursor,
    pub region: AwsByteCursor,
    pub service: AwsByteCursor,
    pub headers: *const Header,
    pub header_count: usize,
    pub port: u32,
    /// Bounds the connect, and again the TLS handshake of a call with
    /// `tls`; nothing bounds the response.
    pub connect_timeout_ms: u32,
    /// Connects with TLS, on the runtime's trust, to the server named
    /// `host`.
    pub tls: bool,
}
/// `ZAWS_HTTP_CONNECTED`: the connection is up and aws-c-http has taken
/// the request to send.
pub const HTTP_CONNECTED: c_int = 0;
/// `ZAWS_HTTP_HEADERS`: some of the response's headers arrived.
pub const HTTP_HEADERS: c_int = 1;
/// `ZAWS_HTTP_BODY`: some of the response's body arrived, in the cursor.
pub const HTTP_BODY: c_int = 2;
/// An event of a call in flight, on a CRT thread: the `HTTP_` kind, and the
/// bytes of a body event, borrowed for the callback.
pub type HttpEventFn = unsafe extern "C" fn(c_int, AwsByteCursor, *mut c_void);
/// The error code, then the response's status when the code is 0.
pub type HttpFinishFn = unsafe extern "C" fn(c_int, c_int, *mut c_void);
/// `struct zaws_http_call`: one request in flight.
#[repr(C)]
#[derive(Debug)]
pub struct HttpCall {
    _private: [u8; 0],
}
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct ResultView {
    pub error_code: c_int,
    pub response_status: c_int,
    pub body: AwsByteCursor,
    pub operation: AwsByteCursor,
    /// The error response's `x-amz-bucket-region`, valid when present.
    pub region_header: AwsByteCursor,
    /// A present header may be empty.
    pub region_header_present: bool,
}
/// `struct zaws_header`: a header a request adds after the shim's own.
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct Header {
    pub name: AwsByteCursor,
    pub value: AwsByteCursor,
}
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct RequestOptions {
    /// One of the `REQUEST_KIND_*` values.
    pub kind: c_int,
    /// A PUT's trailing checksum algorithm, an `aws_s3_checksum_algorithm`,
    /// which it sends whatever the runtime's request checksum mode; 0,
    /// `AWS_SCA_NONE`, leaves the mode's.
    pub checksum_algorithm: c_int,
    pub key: AwsByteCursor,
    pub filepath: AwsByteCursor,
    /// The caller's decision that a GET is one unranged DEFAULT request; the
    /// shim takes it as given.
    pub single_request: bool,
    pub has_body_callback: bool,
    pub if_none_match: bool,
    /// Registers the headers callback on a GET whose body reaches its body
    /// callback, which checks the response's length before any body.
    pub check_object_size: bool,
    /// Validates a GET's response checksum whatever the runtime's response
    /// checksum mode.
    pub validate_checksum: bool,
    pub content_type: AwsByteCursor,
    /// Sent as `If-Match` when nonempty.
    pub if_match: AwsByteCursor,
    /// Sent as `x-amz-request-payer` when nonempty.
    pub request_payer: AwsByteCursor,
    /// Sent in place of the runtime's `user-agent` when nonempty.
    pub user_agent: AwsByteCursor,
    /// `header_count` headers, sent in order after the shim's own; borrowed
    /// for the synchronous submit.
    pub headers: *const Header,
    pub header_count: usize,
    /// A validating GET's expected full-object checksum, the base64 of an
    /// `expected_checksum_algorithm` digest, validated in place of the one
    /// the CRT would look up; borrowed for the synchronous submit.
    pub expected_checksum: AwsByteCursor,
    pub expected_checksum_algorithm: c_int,
    /// Validates each response of a validating GET with no expected checksum
    /// against its own checksum alone.
    pub checksum_unavailable: bool,
}
/// `enum zaws_request_kind`: the request [`zaws_submit`] sends.
pub const REQUEST_KIND_GET: c_int = 0;
pub const REQUEST_KIND_HEAD: c_int = 1;
pub const REQUEST_KIND_PUT: c_int = 2;
/// A HeadBucket, sent to the endpoint path, or `/` when it is empty.
pub const REQUEST_KIND_HEAD_BUCKET: c_int = 3;
/// A DeleteObject, sent as one DEFAULT request.
pub const REQUEST_KIND_DELETE: c_int = 4;
/// `enum aws_s3_checksum_validation_mode`: a validating GET checks its whole
/// download by default, or each response alone, which sigcheck.c pins.
pub const VALIDATION_MODE_DEFAULT: c_int = 0;
pub const VALIDATION_MODE_REQUEST_ONLY: c_int = 1;
/// A HEAD's response headers, or a size-checked GET's, borrowed for one
/// callback; an absent header is empty.
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct HeadHeaders {
    pub length: AwsByteCursor,
    pub modified: AwsByteCursor,
    pub storage_class: AwsByteCursor,
    pub restore: AwsByteCursor,
    pub etag: AwsByteCursor,
    pub region: AwsByteCursor,
    /// `x-amz-checksum-type` and the three CRC checksum headers a
    /// full-object checksum can be.
    pub checksum_type: AwsByteCursor,
    pub checksum_crc32: AwsByteCursor,
    pub checksum_crc32c: AwsByteCursor,
    pub checksum_crc64nvme: AwsByteCursor,
    /// A present region header, or checksum type header, may be empty.
    pub region_present: bool,
    pub checksum_type_present: bool,
    /// Whether any of the response's checksum headers has a value.
    pub checksum_reported: bool,
}
#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct Date {
    pub fields: [c_int; 6],
    pub epoch_seconds: i64,
}
#[repr(C)]
#[derive(Debug)]
pub struct XmlNode {
    _private: [u8; 0],
}
pub type XmlNodeFn = unsafe extern "C" fn(*mut XmlNode, *mut c_void) -> c_int;
pub type TelemetryFn = unsafe extern "C" fn(c_int, *mut c_void);
pub type HeadersFn = unsafe extern "C" fn(*const HeadHeaders, c_int, *mut c_void) -> c_int;
pub type BodyFn = unsafe extern "C" fn(
    *mut AwsS3MetaRequest,
    AwsByteCursor,
    u64,
    *mut AwsS3BufferTicket,
    *mut c_void,
) -> c_int;
pub type FinishFn = unsafe extern "C" fn(*const ResultView, *mut c_void);
pub type ProgressFn = unsafe extern "C" fn(u64, *mut c_void);
/// `enum zaws_runtime_stage`: the runtime's construction stages in
/// acquisition order, released in reverse.
pub const STAGE_ENDPOINT: u32 = 0;
pub const STAGE_REGION: u32 = 1;
pub const STAGE_EVENT_LOOP: u32 = 2;
pub const STAGE_RESOLVER: u32 = 3;
pub const STAGE_BOOTSTRAP: u32 = 4;
pub const STAGE_TLS: u32 = 5;
pub const STAGE_CREDENTIALS: u32 = 6;
pub const STAGE_CLIENT: u32 = 7;
/// [`zaws_runtime_start_stage`]'s failure when the TLS stage cannot load its
/// CA file into the trust store; the CRT's last error says why.
pub const TRUST_FILE_REJECTED: c_int = 1;
/// [`zaws_runtime_start_stage`]'s failure when the client stage fails once
/// its proxy is configured, the only construction failure that names the
/// proxy; the CRT's last error says why.
pub const CLIENT_FAILED_WITH_PROXY: c_int = 2;
// SAFETY: the C shim consumes the pinned-header structs and transfers only these
// layout-asserted records. Callers must retain pointees for each documented call.
c_functions! {
    pub fn zaws_runtime_snapshot(runtime: *mut Runtime, snapshot: *mut RuntimeSnapshot);
    pub fn zaws_runtime_signing_snapshot(runtime: *mut Runtime, snapshot: *mut SigningSnapshot);
    pub fn zaws_credentials_snapshot(runtime: *mut Runtime, snapshot: *mut CredentialsSnapshot);
    /// Answers one query a delegate received, exactly once, from any thread.
    /// A null view, or one the CRT refuses, reports a failure.
    pub fn zaws_credentials_complete(
        callback: Option<GetCredentialsCallback>,
        callback_data: *mut c_void,
        view: *const CredentialsView,
    );
    /// Starts one request over aws-c-http. Null, with the CRT's error
    /// raised and no callback, when it could not start. Otherwise `finish`
    /// runs exactly once, after every event, on the calling thread or a CRT
    /// thread and possibly before this returns, and the caller owns one
    /// reference to the call.
    pub fn zaws_http_request(
        runtime: *mut Runtime,
        options: *const HttpOptions,
        event: Option<HttpEventFn>,
        finish: Option<HttpFinishFn>,
        data: *mut c_void,
    ) -> *mut HttpCall;
    /// Abandons the call from any thread by closing its connection, now or
    /// as soon as it is up; `finish` still runs.
    pub fn zaws_http_cancel(call: *mut HttpCall);
    /// Gives up the caller's reference.
    pub fn zaws_http_release(call: *mut HttpCall);
    pub fn zaws_platform(recommended_gbps: *mut f64) -> bool;
    /// The buffer-pool size aws-c-s3 picks for a throughput target when no
    /// limit is configured; a zero target consults the platform detection,
    /// which needs the S3 library initialized.
    pub fn aws_s3_default_memory_limit_for_throughput(throughput_target_gbps: f64) -> usize;
    pub fn zaws_runtime_allocate() -> *mut Runtime;
    /// `stage` is one of the `STAGE_*` values.
    pub fn zaws_runtime_start_stage(
        runtime: *mut Runtime,
        stage: u32,
        options: *const RuntimeOptions,
        callback: Option<ShutdownFn>,
        data: *mut c_void,
    ) -> c_int;
    pub fn zaws_runtime_release_stage(runtime: *mut Runtime, stage: u32);
    pub fn zaws_runtime_destroy(runtime: *mut Runtime);
    pub fn zaws_submit(
        runtime: *mut Runtime,
        options: *const RequestOptions,
        headers: Option<HeadersFn>,
        body: Option<BodyFn>,
        finish: Option<FinishFn>,
        progress: Option<ProgressFn>,
        shutdown: Option<ShutdownFn>,
        data: *mut c_void,
    ) -> *mut AwsS3MetaRequest;
    pub fn zaws_runtime_endpoint(
        runtime: *mut Runtime,
        authority: *mut AwsByteCursor,
        path: *mut AwsByteCursor,
    );
    pub fn zaws_message_add_header(
        message: *mut HttpMessage,
        name: AwsByteCursor,
        value: AwsByteCursor,
    ) -> c_int;
    pub fn aws_http_message_new_request(allocator: *mut AwsAllocator) -> *mut HttpMessage;
    pub fn aws_http_message_set_request_method(
        message: *mut HttpMessage,
        method: AwsByteCursor,
    ) -> c_int;
    pub fn aws_http_message_set_request_path(
        message: *mut HttpMessage,
        path: AwsByteCursor,
    ) -> c_int;
    /// Sends `message` as built, its user agent included; aws-c-s3 re-sets
    /// the user agent on every request it sends, which moves it last.
    pub fn zaws_submit_message(
        runtime: *mut Runtime,
        message: *mut HttpMessage,
        operation: AwsByteCursor,
        body: Option<BodyFn>,
        finish: Option<FinishFn>,
        telemetry: Option<TelemetryFn>,
        shutdown: Option<ShutdownFn>,
        data: *mut c_void,
    ) -> *mut AwsS3MetaRequest;
    /// Host and accept, a PUT's length and content type, the conditions,
    /// the request payer, the `header_count` caller `headers`, then
    /// `user_agent`, in wire order.
    pub fn zaws_message_new(
        host: AwsByteCursor,
        path: AwsByteCursor,
        method: AwsByteCursor,
        length: *const u64,
        content_type: AwsByteCursor,
        conditional: bool,
        if_match: AwsByteCursor,
        request_payer: AwsByteCursor,
        headers: *const Header,
        header_count: usize,
        user_agent: AwsByteCursor,
    ) -> *mut HttpMessage;
    pub fn zaws_message_field(
        message: *const HttpMessage,
        index: u32,
        name: *mut AwsByteCursor,
        value: *mut AwsByteCursor,
    ) -> c_int;
    pub fn aws_http_message_release(message: *mut HttpMessage) -> *mut HttpMessage;
    pub fn aws_http_message_get_headers(message: *const HttpMessage) -> *mut AwsHttpHeaders;
    pub fn aws_http_message_get_header_count(message: *const HttpMessage) -> usize;
    pub fn zaws_parse_http_date(value: AwsByteCursor, result: *mut i64) -> c_int;
    pub fn zaws_parse_date(value: AwsByteCursor, date: *mut Date) -> c_int;
    pub fn zaws_xml_parse(body: AwsByteCursor, root: Option<XmlNodeFn>, data: *mut c_void)
    -> c_int;
    pub fn aws_xml_node_get_name(node: *mut XmlNode) -> AwsByteCursor;
    pub fn aws_xml_node_as_body(node: *mut XmlNode, body: *mut AwsByteCursor) -> c_int;
    pub fn aws_xml_node_traverse(
        node: *mut XmlNode,
        callback: Option<XmlNodeFn>,
        data: *mut c_void,
    ) -> c_int;
    /// Writes `text` with its XML entities decoded to `out`, which holds
    /// `text.len` bytes.
    pub fn zaws_xml_unescape(text: AwsByteCursor, out: *mut u8, out_len: *mut usize) -> c_int;
    pub fn zaws_listing_error(kind: u32) -> c_int;
    pub fn aws_reset_error();
    pub fn aws_mem_calloc(allocator: *mut AwsAllocator, count: usize, size: usize) -> *mut c_void;
    /// Allocates zeroed storage without replacing the allocator's own failure policy.
    ///
    /// # Safety
    /// The allocator must remain live through release and provide a calloc or acquire callback.
    /// Count and size must be nonzero; release returned storage through the same allocator.
    pub fn zaws_allocate_zeroed(
        allocator: *mut AwsAllocator,
        count: usize,
        size: usize,
    ) -> *mut c_void;
    pub fn aws_mem_release(allocator: *mut AwsAllocator, ptr: *mut c_void);
    pub fn zaws_allocator_new(
        acquire: unsafe extern "C" fn(*mut c_void, usize) -> *mut c_void,
        release: unsafe extern "C" fn(*mut c_void, *mut c_void),
        data: *mut c_void,
    ) -> *mut AwsAllocator;
    pub fn zaws_allocator_destroy(allocator: *mut AwsAllocator);
    pub fn zaws_logger_new() -> *mut c_void;
    pub fn zaws_logger_destroy(logger: *mut c_void);
    pub fn zaws_debug_emit(logger: AwsByteCursor, message: *const c_char);
}
const _: () = {
    assert!(std::mem::size_of::<Date>() == 32);
    assert!(std::mem::offset_of!(Date, epoch_seconds) == 24);
    assert!(std::mem::size_of::<RuntimeOptions>() == 200);
    assert!(std::mem::offset_of!(RuntimeOptions, credentials_delegate) == 184);
    assert!(std::mem::size_of::<CredentialsView>() == 72);
    assert!(std::mem::offset_of!(CredentialsView, expiration_timepoint_seconds) == 64);
    assert!(std::mem::size_of::<HttpOptions>() == 112);
    assert!(std::mem::offset_of!(HttpOptions, tls) == 104);
    assert!(std::mem::offset_of!(HttpOptions, headers) == 80);
    assert!(std::mem::offset_of!(HttpOptions, port) == 96);
    assert!(std::mem::offset_of!(HttpOptions, connect_timeout_ms) == 100);
    assert!(std::mem::offset_of!(RuntimeOptions, pool_factory) == 96);
    assert!(std::mem::offset_of!(RuntimeOptions, verify_peer) == 176);
    assert!(std::mem::size_of::<RequestOptions>() == 152);
    assert!(std::mem::offset_of!(RequestOptions, checksum_algorithm) == 4);
    assert!(std::mem::offset_of!(RequestOptions, single_request) == 40);
    assert!(std::mem::offset_of!(RequestOptions, check_object_size) == 43);
    assert!(std::mem::offset_of!(RequestOptions, validate_checksum) == 44);
    assert!(std::mem::offset_of!(RequestOptions, content_type) == 48);
    assert!(std::mem::offset_of!(RequestOptions, if_match) == 64);
    assert!(std::mem::offset_of!(RequestOptions, request_payer) == 80);
    assert!(std::mem::offset_of!(RequestOptions, user_agent) == 96);
    assert!(std::mem::offset_of!(RequestOptions, headers) == 112);
    assert!(std::mem::offset_of!(RequestOptions, header_count) == 120);
    assert!(std::mem::offset_of!(RequestOptions, expected_checksum) == 128);
    assert!(std::mem::offset_of!(RequestOptions, expected_checksum_algorithm) == 144);
    assert!(std::mem::offset_of!(RequestOptions, checksum_unavailable) == 148);
    assert!(std::mem::size_of::<Header>() == 32);
    assert!(std::mem::offset_of!(Header, value) == 16);
    assert!(std::mem::size_of::<HeadHeaders>() == 168);
    assert!(std::mem::offset_of!(HeadHeaders, region_present) == 160);
    assert!(std::mem::size_of::<RuntimeSnapshot>() == 72);
    assert!(std::mem::size_of::<SigningSnapshot>() == 56);
    assert!(std::mem::size_of::<CredentialsSnapshot>() == 1);
    assert!(std::mem::size_of::<ResultView>() == 64);
    assert!(std::mem::offset_of!(ResultView, region_header_present) == 56);
};

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct OptionSnapshot {
    pub kind: c_int,
    /// The request's `out_of_order_delivery`, an `aws_tribool`.
    pub out_of_order: c_int,
    pub has_hint: bool,
    pub body: bool,
    pub recv_delete: bool,
    pub progress: bool,
    /// Whether the request reads its response headers in a callback.
    pub headers: bool,
    pub hint: u64,
    pub operation: AwsByteCursor,
    pub recv_path: AwsByteCursor,
    pub send_path: AwsByteCursor,
}
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct ProxySnapshot {
    pub host: AwsByteCursor,
    pub port: u32,
    pub connection_type: c_int,
    pub strategy: bool,
    pub tls: bool,
    pub env_disabled: bool,
    /// False for a direct connection, whose S3 client gets no proxy options.
    pub configured: bool,
}
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct ConfiguredSnapshot {
    pub meta: OptionSnapshot,
    pub checksum_location: c_int,
    pub checksum_algorithm: c_int,
    pub has_checksum: bool,
    pub validate_response: bool,
    pub validation_algorithms_null: bool,
    pub owns_checksum: bool,
    pub full_object_callback_null: bool,
    /// The response validation mode, an `aws_s3_checksum_validation_mode`.
    pub validation_mode: c_int,
    pub expected_checksum_algorithm: c_int,
    pub expected_checksum: AwsByteCursor,
}
// SAFETY: snapshots borrow live input storage/runtime synchronously.
c_functions! {
    pub fn zaws_request_option_snapshot(options: *const RequestOptions, out: *mut OptionSnapshot);
    pub fn zaws_configured_request_snapshot(
        runtime: *mut Runtime,
        options: *const RequestOptions,
        progress: bool,
        out: *mut ConfiguredSnapshot,
    );
    pub fn zaws_proxy_snapshot(runtime: *mut Runtime, out: *mut ProxySnapshot);
    /// Runs the submission header and finish callbacks over CRT-owned headers
    /// built from `count` name/value pairs, then releases those headers.
    pub fn zaws_callback_capture(
        names: *const AwsByteCursor,
        values: *const AwsByteCursor,
        count: usize,
        status: c_int,
        error_code: c_int,
        headers: Option<HeadersFn>,
        finish: Option<FinishFn>,
        data: *mut c_void,
    ) -> c_int;
}
/// `struct aws_input_stream`, which only the file-length ops handle.
#[repr(C)]
#[derive(Debug)]
pub struct InputStream {
    _private: [u8; 0],
}
/// `struct zaws_file_length_ops`: the file-stream operations an upload
/// length lookup opens, measures and releases its source through.
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct FileLengthOps {
    pub open: Option<
        unsafe extern "C" fn(*mut c_void, *mut AwsAllocator, *const c_char) -> *mut InputStream,
    >,
    pub get_length: Option<unsafe extern "C" fn(*mut c_void, *mut InputStream, *mut i64) -> c_int>,
    pub release: Option<unsafe extern "C" fn(*mut c_void, *mut InputStream)>,
    /// Passed to each operation.
    pub data: *mut c_void,
}
// SAFETY: the helpers read their cursors synchronously; `out` must be
// writable, and a successfully built buffer is the caller's to clean up.
c_functions! {
    /// The request path [`zaws_submit`] sends: an object request appends its
    /// already encoded key to `base`, the endpoint path, with a separator
    /// unless `base` ends in one; a [`REQUEST_KIND_HEAD_BUCKET`] sends `base`
    /// as is, or `/` when it is empty.
    pub fn zaws_endpoint_request_path(
        allocator: *mut AwsAllocator,
        base: AwsByteCursor,
        key: AwsByteCursor,
        kind: c_int,
        out: *mut AwsByteBuf,
    ) -> c_int;
    pub fn aws_byte_buf_clean_up(buffer: *mut AwsByteBuf);
    /// The byte length of the file at `path` through `ops`; a negative length
    /// raises `AWS_ERROR_INVALID_ARGUMENT` whether or not the lookup failed.
    pub fn zaws_upload_length_with_ops(
        allocator: *mut AwsAllocator,
        path: AwsByteCursor,
        ops: *const FileLengthOps,
        out: *mut u64,
    ) -> c_int;
    /// The length a PUT [`zaws_submit`] builds sends, through the CRT's
    /// file stream.
    pub fn zaws_upload_length(
        allocator: *mut AwsAllocator,
        path: AwsByteCursor,
        out: *mut u64,
    ) -> c_int;
}
const _: () = {
    assert!(std::mem::size_of::<OptionSnapshot>() == 72);
    assert!(std::mem::offset_of!(OptionSnapshot, headers) == 12);
    assert!(std::mem::offset_of!(OptionSnapshot, hint) == 16);
    assert!(std::mem::size_of::<FileLengthOps>() == 32);
    assert!(std::mem::offset_of!(FileLengthOps, data) == 24);
    assert!(std::mem::size_of::<ConfiguredSnapshot>() == 112);
    assert!(std::mem::offset_of!(ConfiguredSnapshot, expected_checksum) == 96);
    assert!(std::mem::size_of::<ProxySnapshot>() == 32);
};
// SAFETY: the runtime pointer must remain alive for the synchronous query.
c_functions! {
    pub fn zaws_runtime_has_custom_tls(runtime: *mut Runtime) -> bool;
}
