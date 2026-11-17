//! S3 request outcomes, ownership protocols, message construction, and listing.
use std::fmt;

#[cfg(test)]
pub(crate) use listing::{Action, NextActionInputs, next_action};
pub use listing::{EntryKind, LastModified, ListEntry, ListOptions, ListPhaseStats, ListStats};
pub use listing::{ProbeState, TokenProbe, parse_list_date};
pub(crate) mod botocore_retry;
pub mod error_body;
mod listing;

pub const CRT_ERROR_NAME_MAX: usize = 96;
pub const CRT_ERROR_MESSAGE_MAX: usize = 256;
pub const SERVICE_ERROR_CODE_MAX: usize = 64;
pub const OPERATION_NAME_MAX: usize = 32;
/// A region is a single DNS label.
pub const REGION_MAX: usize = 63;
/// S3 ETags are a quoted MD5 hex digest, with a part count for multipart
/// objects; the bound leaves room for any other quoted opaque value.
pub const ETAG_MAX: usize = 256;
/// Room for any endpoint the S3 rules name: a scheme, a host of at most 255
/// bytes, a port, and a bucket path. Only a configured endpoint can be
/// longer, and a failure names the caller's whole copy of it.
pub const ENDPOINT_URL_MAX: usize = 4096;
pub const CANCELED_ERROR_CODE: i32 = crt_sys::AWS_ERROR_S3_CANCELED;
/// The CRT's code for an error response it does not retry, whatever its
/// status: one aws-c-s3 neither recognizes as a server error nor finds a
/// recoverable error code in.
pub const INVALID_RESPONSE_STATUS_ERROR_CODE: i32 = crt_sys::AWS_ERROR_S3_INVALID_RESPONSE_STATUS;
pub const CHECKSUM_MISMATCH_ERROR_CODE: i32 = crt_sys::AWS_ERROR_S3_RESPONSE_CHECKSUM_MISMATCH;
/// The error code a GET finishes with when its response reports another
/// length than `RequestOptions::check_object_size` expects, or none: the
/// CRT's own code for an object that changed while it was downloaded.
pub const SIZE_CHANGED_ERROR_CODE: i32 = crt_sys::AWS_ERROR_S3_OBJECT_MODIFIED;
pub const UNKNOWN_ERROR_CODE: i32 = 3;
pub const INVALID_ARGUMENT_ERROR_CODE: i32 = 34;
/// `AWS_ERROR_FILE_INVALID_PATH`.
pub const FILE_INVALID_PATH_ERROR_CODE: i32 = crt_sys::AWS_ERROR_FILE_INVALID_PATH;
/// The signer found no credentials: botocore's NoCredentialsError.
pub const NO_CREDENTIALS_ERROR_CODE: i32 = crt_sys::AWS_AUTH_SIGNING_NO_CREDENTIALS;
/// `AWS_IO_SOCKET_CONNECTION_REFUSED`, the connection error a closed local
/// port reports.
pub const CONNECTION_REFUSED_ERROR_CODE: i32 = crt_sys::AWS_IO_SOCKET_CONNECTION_REFUSED;

/// Whether the request failed to reach its connection peer: the connection
/// was refused, the host could not be routed to or resolved, or the network
/// was down. A timeout or a TLS failure is not one; botocore names those
/// differently.
pub fn is_connection_error(error_code: i32) -> bool {
    matches!(
        error_code,
        crt_sys::AWS_IO_SOCKET_CONNECTION_REFUSED
            | crt_sys::AWS_IO_SOCKET_NO_ROUTE_TO_HOST
            | crt_sys::AWS_IO_SOCKET_NETWORK_DOWN
            | crt_sys::AWS_IO_SOCKET_CONNECT_ABORTED
            | crt_sys::AWS_IO_DNS_QUERY_FAILED
            | crt_sys::AWS_IO_DNS_INVALID_NAME
            | crt_sys::AWS_IO_DNS_NO_ADDRESS_FOR_HOST
    )
}

/// An owned, byte-preserving diagnostic truncated to its fixed capacity.
///
/// Presence distinguishes absent metadata from an explicitly empty value, and
/// the truncation flag keeps a shortened value from being routed silently.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundedText<const N: usize> {
    bytes: [u8; N],
    len: usize,
    present: bool,
    truncated: bool,
}
impl<const N: usize> Default for BoundedText<N> {
    fn default() -> Self {
        Self {
            bytes: [0; N],
            len: 0,
            present: false,
            truncated: false,
        }
    }
}
impl<const N: usize> BoundedText<N> {
    /// A present copy of `bytes`, truncated to `N` bytes.
    pub fn new(bytes: impl AsRef<[u8]>) -> Self {
        let mut value = Self::default();
        value.set(bytes.as_ref());
        value
    }
    /// Replaces the copy, marking it present and recording truncation.
    pub fn set(&mut self, bytes: &[u8]) {
        self.set_prefix(bytes, bytes.len());
    }
    pub(crate) fn set_prefix(&mut self, prefix: &[u8], full_len: usize) {
        self.len = prefix.len().min(N);
        self.bytes[..self.len].copy_from_slice(&prefix[..self.len]);
        self.present = true;
        self.truncated = full_len > N;
    }
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes[..self.len]
    }
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
    /// Whether a value, possibly empty, was recorded.
    pub fn is_present(&self) -> bool {
        self.present
    }
    /// Whether the recorded value was longer than `N` bytes.
    pub fn is_truncated(&self) -> bool {
        self.truncated
    }
}
/// S3 error details retained after the callback and CRT library are released.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ServiceError {
    pub code: BoundedText<SERVICE_ERROR_CODE_MAX>,
    /// `<Message>` from the body with its XML entities decoded, kept whole:
    /// the failure prints all of it, and an AccessDenied message names a
    /// whole resource ARN. Empty when there is none.
    pub message: Vec<u8>,
    pub operation: BoundedText<OPERATION_NAME_MAX>,
    /// The response's `x-amz-bucket-region`, owned past the callback.
    pub region_header: BoundedText<REGION_MAX>,
    /// The error document's `<Region>`, retained apart so header precedence is explicit.
    pub region_body: BoundedText<REGION_MAX>,
    /// Malformed XML is not absent routing metadata, even if extraction failed.
    pub region_body_invalid: bool,
}
/// Completion result, including the reason this request owner canceled it.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TransferResult {
    /// The client region of the runtime that submitted the request.
    pub request_region: BoundedText<REGION_MAX>,
    /// The endpoint URL of the runtime that submitted the request.
    pub endpoint_url: BoundedText<ENDPOINT_URL_MAX>,
    /// All CRT progress bytes, whether or not a UI progress hook is installed.
    pub bytes_transferred: u64,
    /// A body consumer was invoked, even if it rejected the body.
    pub body_delivered: bool,
    pub error_code: i32,
    pub response_status: i32,
    /// The GET failed with `SIZE_CHANGED_ERROR_CODE` because its response
    /// reported another length than it was submitted with, or none
    /// (`RequestOptions::check_object_size`), before any body was delivered.
    /// The code alone says less: the CRT raises it for other changes too.
    pub size_changed: bool,
    pub canceled_by_interrupt: bool,
    pub crt_name: BoundedText<CRT_ERROR_NAME_MAX>,
    pub crt_message: BoundedText<CRT_ERROR_MESSAGE_MAX>,
    pub proxy_url: BoundedText<4096>,
    pub service_error: ServiceError,
    /// The retries botocore made before its attempts ran out, which its
    /// error names after the operation; `None` when it names none.
    pub retries_exhausted: Option<u64>,
}
impl fmt::Display for TransferResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "CRT {} ({}): {}",
            self.error_code,
            String::from_utf8_lossy(self.crt_name.as_bytes()),
            String::from_utf8_lossy(self.crt_message.as_bytes())
        )
    }
}
impl std::error::Error for TransferResult {}
/// Listing completion with failed-page context and entry-callback status.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ListResult {
    pub transfer: TransferResult,
    pub callback_error: i32,
    /// The failed page's request path with its query string, which names the
    /// request URL in a connection failure; empty when no page failed. Kept
    /// whole, because the sentence names all of it.
    pub request_path: Vec<u8>,
    pub local_error: Option<ListLocalError>,
    /// Present when a page named the continuation token it was requested
    /// with, which stopped the run as botocore's paginator stops; the
    /// response itself succeeded.
    pub repeated_token: Option<Vec<u8>>,
}
/// A local listing failure retains its origin separately from CRT's overlapping error codes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ListLocalError {
    UnexpectedRoot,
    InvalidNumber,
    CrtFailure,
    PageBodyTooLarge,
    PageLimitExceeded,
    /// A page body, or a name its XML decodes to, that is not UTF-8. Botocore
    /// reads the body as UTF-8 and rejects such a page as not well-formed.
    InvalidUtf8,
    /// A UTF-8 page body that holds a character XML 1.0 does not allow, raw
    /// or by reference, or a reference XML does not read: a C0 control
    /// character other than tab, newline and carriage return, U+FFFE or
    /// U+FFFF, `&#XD800;`, `&nbsp;`, or a bare `&`. Botocore's expat parser
    /// rejects such a page as not well-formed, though the CRT's parser
    /// accepts it.
    InvalidXmlText,
    /// The CRT's parser rejected the document, or the CRT's decoding the
    /// text of a field. Like a page that is not UTF-8 or holds text XML
    /// forbids, botocore's parser rejects it too, so the listing retries the
    /// page and never reports this.
    MalformedXml,
    /// Ctrl-C cancelled a retry in its backoff, so no further attempt was
    /// sent.
    Canceled,
}
/// What the Glacier rule reads from an object's storage class and restore
/// status, shared by a HeadObject's headers and a listing's objects.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ArchiveState {
    /// The storage class is GLACIER or DEEP_ARCHIVE. GLACIER_IR and every
    /// other class are readable.
    pub archived: bool,
    /// The restore value reports a finished restore, `ongoing-request="false"`;
    /// one still in progress reads `ongoing-request="true"`.
    pub restored: bool,
}
impl ArchiveState {
    /// The state of a listed object, which upstream never asks for restore
    /// status, so it is never restored.
    pub fn from_storage_class(storage_class: &[u8]) -> Self {
        Self {
            archived: storage_class == b"GLACIER" || storage_class == b"DEEP_ARCHIVE",
            restored: false,
        }
    }
    /// The state HeadObject's `x-amz-storage-class` and `x-amz-restore`
    /// values report; an absent header is an empty value.
    pub fn from_headers(storage_class: &[u8], restore: &[u8]) -> Self {
        const FINISHED: &[u8] = b"ongoing-request=\"false\"";
        Self {
            restored: restore
                .windows(FINISHED.len())
                .any(|value| value == FINISHED),
            ..Self::from_storage_class(storage_class)
        }
    }
    /// Whether a download can read the object: upstream's
    /// `is_glacier_compatible`.
    pub fn readable(self) -> bool {
        !self.archived || self.restored
    }
}
/// Header-derived object size and exact service timestamp.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct HeadObjectResult {
    pub transfer: TransferResult,
    pub content_length: Option<u64>,
    pub last_modified_epoch_seconds: Option<i64>,
    /// The response's `ETag`, absent when it carried none.
    pub etag: BoundedText<ETAG_MAX>,
    /// What the Glacier rule reads from the response headers.
    pub archive: ArchiveState,
    /// What the response's checksum headers say of the object's full-object
    /// checksum.
    pub full_object_checksum: FullObjectChecksum,
}
/// What a download knows of its object's full-object checksum before its
/// first GET, from the HeadObject or the listing entry that found the object.
/// A validating multipart download gives the CRT what it knows, as upstream
/// does (s3handler.py `_add_full_object_checksum_subscriber`, s3transfer/crt.py
/// `_configure_full_object_checksum_validation`), and saves the HeadObject the
/// CRT would send to learn the checksum unless the object may have one that
/// went unreported.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub enum FullObjectChecksum {
    /// The object may have one, which the CRT looks up itself.
    #[default]
    Unknown,
    /// The object has none, so each response is validated against its own
    /// checksum alone.
    Unavailable,
    /// The object's checksum, which the download is validated against.
    Known {
        algorithm: ChecksumAlgorithm,
        /// The base64 the response reported, as reported. Only a HeadObject
        /// reports one, so the boxed copy keeps the listing's many entries
        /// small.
        value: Box<[u8]>,
    },
}
impl FullObjectChecksum {
    /// What a HeadObject's checksum headers say: `checksum_type` is its
    /// `x-amz-checksum-type`, None when absent; `crc32`, `crc32c`, and
    /// `crc64nvme` are those algorithms' checksum headers, empty when absent;
    /// and `any_value` says whether any checksum header has a value. A
    /// full-object type with a CRC value is that checksum
    /// (s3transfer/checksums.py `resolve_full_object_checksum`), in that order
    /// of algorithms.
    pub fn from_head(
        checksum_type: Option<&[u8]>,
        crc32: &[u8],
        crc32c: &[u8],
        crc64nvme: &[u8],
        any_value: bool,
    ) -> Self {
        if checksum_type.is_some_and(is_full_object_type) {
            let values = [
                (ChecksumAlgorithm::Crc32, crc32),
                (ChecksumAlgorithm::Crc32c, crc32c),
                (ChecksumAlgorithm::Crc64Nvme, crc64nvme),
            ];
            if let Some((algorithm, value)) = values.into_iter().find(|(_, v)| !v.is_empty()) {
                return Self::Known {
                    algorithm,
                    value: value.into(),
                };
            }
        }
        Self::unless_possible(checksum_type, any_value)
    }
    /// What a listing entry says, which names a checksum's type and
    /// algorithms but never its value: `checksum_type` is its
    /// `<ChecksumType>`, None when absent, and `algorithm_listed` says
    /// whether it had a `<ChecksumAlgorithm>`.
    pub fn from_listing(checksum_type: Option<&[u8]>, algorithm_listed: bool) -> Self {
        Self::unless_possible(checksum_type, algorithm_listed)
    }
    fn unless_possible(checksum_type: Option<&[u8]>, reported: bool) -> Self {
        let possible = checksum_type.map_or(reported, is_full_object_type);
        if possible {
            Self::Unknown
        } else {
            Self::Unavailable
        }
    }
}
/// What a download's GETs are conditioned on: the ETag the object's
/// HeadObject or listing entry reported, and what that response said of the
/// object's full-object checksum.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DownloadCondition<'a> {
    pub etag: &'a [u8],
    pub full_object_checksum: &'a FullObjectChecksum,
}
fn is_full_object_type(checksum_type: &[u8]) -> bool {
    checksum_type.eq_ignore_ascii_case(b"FULL_OBJECT")
}
/// Whether a GET of a `size`-byte object is one unranged request: a known
/// size no larger than the single-request threshold. The one copy of the
/// rule: a submission passes its answer to the shim, which picks the DEFAULT
/// GetObject by it, and the body callbacks read the same answer to accept
/// ticketless bodies.
pub fn single_request(threshold: Option<u64>, size: Option<u64>) -> bool {
    threshold
        .zip(size)
        .is_some_and(|(limit, size)| size <= limit)
}
/// The condition a GET sends, `If-Match` its ETag, and whose full-object
/// checksum a validating GET hands the CRT: the download's, unless it is one
/// unranged request. Upstream's CRT transfer manager conditions every GET of
/// a download the CRT splits into parts and sends a single-request download
/// unconditioned (s3transfer/crt.py `_get_make_request_args_get_object`).
pub fn download_condition(
    threshold: Option<u64>,
    size: Option<u64>,
    condition: Option<DownloadCondition<'_>>,
) -> Option<DownloadCondition<'_>> {
    if single_request(threshold, size) {
        None
    } else {
        condition
    }
}
/// A header an object request sends after the ones it builds itself.
///
/// A transfer sends the same headers with every attempt of every object, so
/// each is owned. `Debug` hides the value of the customer key header.
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct Header {
    pub name: Vec<u8>,
    pub value: Vec<u8>,
}
impl Header {
    /// The header `name` with `value`.
    pub fn new(name: impl Into<Vec<u8>>, value: impl Into<Vec<u8>>) -> Self {
        Self {
            name: name.into(),
            value: value.into(),
        }
    }
}
const CUSTOMER_KEY_HEADER: &[u8] = b"x-amz-server-side-encryption-customer-key";
impl fmt::Debug for Header {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let name = String::from_utf8_lossy(&self.name);
        let mut header = f.debug_struct("Header");
        header.field("name", &name);
        if self.name.eq_ignore_ascii_case(CUSTOMER_KEY_HEADER) {
            header.field("value", &"<redacted>")
        } else {
            header.field("value", &String::from_utf8_lossy(&self.value))
        }
        .finish()
    }
}
/// The algorithm of the checksum a PUT sends in its trailer, or that a
/// download is validated against.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(i32)]
pub enum ChecksumAlgorithm {
    Crc32c = 1,
    Crc32 = 2,
    Sha1 = 3,
    Sha256 = 4,
    Crc64Nvme = 5,
    Sha512 = 6,
    Xxhash64 = 7,
    Xxhash3 = 8,
    Xxhash128 = 9,
}
/// Applies botocore's credential masking to a diagnostic proxy URL.
pub fn masked_proxy(url: &str) -> BoundedText<4096> {
    if url.is_empty() {
        return BoundedText::default();
    }
    BoundedText::new(cli_core::proxy::DisplayUrl::new(url).as_str())
}
mod ownership;
#[doc(inline)]
pub use ownership::{
    BodyDelivery, BodyTicketOps, MetaRequestOps, OfferedBody, Submission, forward_body,
};
mod native;
#[doc(inline)]
pub use native::{
    BodyChunk, CallbackBody, CallbackBodyFn, CallbackRequest, CrtMetaRequestOps, HeadObject,
    HttpMessage, MetaRequestHandle, Request, RequestCallbacks, RequestKind, RequestOptions,
    TransferHeaders, error_message, error_name, parse_http_date_epoch_seconds,
    parse_service_error_body, transfer_result,
};
#[cfg(test)]
mod tests;
pub(crate) use native::{record_outcome, result_from_view};
#[cfg(test)]
mod native_testing;
