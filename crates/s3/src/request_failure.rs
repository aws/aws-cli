//! The sentence the AWS CLI prints for a request the CRT failed, read from
//! what the CRT reported: `str(ClientError)` for an error response, the
//! NoCredentialsError, EndpointConnectionError, and ProxyConnectionError
//! messages for a request that never got one, `str(AwsCrtError)` for a
//! download whose checksum did not match, and the CRT's own sentence for
//! anything else. The ls command hands the classification to the
//! error-handler chain; the cp result lines print the sentence after the
//! transfer location.
use crt::s3::TransferResult;
use std::fmt;

/// The message of the NoCredentialsError.
pub const NO_CREDENTIALS_MESSAGE: &str = "Unable to locate credentials";
pub use crt::s3::NO_CREDENTIALS_ERROR_CODE;
/// `str(PaginationError)` for a listing page that named the continuation
/// token it was requested with. Both listing operations call their input
/// token `ContinuationToken`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RepeatedToken<'a> {
    /// The token, as the page's parse decoded it.
    pub token: &'a [u8],
}
impl RepeatedToken<'_> {
    /// `str(PaginationError)` for the token as owned bytes, for a caller that
    /// hands it on.
    pub fn to_vec(&self) -> Vec<u8> {
        let mut sentence = b"Error during pagination: The same next token was received twice: \
              {'ContinuationToken': "
            .to_vec();
        sentence.extend_from_slice(&crate::mime::repr(self.token));
        sentence.push(b'}');
        sentence
    }
}
/// The URL botocore names in a connection error: the request's own.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RequestUrl<'a> {
    /// An object request: the endpoint URL, which carries the bucket in its
    /// host or its path, then the percent-encoded key.
    Object {
        endpoint_url: &'a str,
        request_key: &'a str,
    },
    /// A listing request: the endpoint's origin, then the path the listing
    /// built from the endpoint's path, query string included.
    Listing {
        endpoint_url: &'a str,
        request_path: &'a str,
    },
}
impl fmt::Display for RequestUrl<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Object {
                endpoint_url,
                request_key,
            } => write!(
                f,
                "{endpoint_url}{}{request_key}",
                if endpoint_url.ends_with('/') { "" } else { "/" }
            ),
            Self::Listing {
                endpoint_url,
                request_path,
            } => write!(f, "{}{request_path}", endpoint_origin(endpoint_url)),
        }
    }
}
/// `scheme://authority` of an endpoint URL: everything before its path.
pub fn endpoint_origin(endpoint: &str) -> &str {
    let Some((scheme, _)) = endpoint.split_once("://") else {
        return endpoint;
    };
    let start = scheme.len() + 3;
    endpoint[start..]
        .find('/')
        .map_or(endpoint, |end| &endpoint[..start + end])
}
/// The exception botocore raised for the failure.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind<'a> {
    /// ClientError from an error response body.
    ServiceError {
        code: &'a [u8],
        message: &'a [u8],
        operation: &'a [u8],
        /// See [`TransferResult::retries_exhausted`].
        retries_exhausted: Option<u64>,
    },
    /// ClientError from an error status without a body, as a HEAD answers:
    /// the code is the status number and the message its reason phrase.
    HttpStatus {
        status: i32,
        operation: &'a [u8],
        /// See [`TransferResult::retries_exhausted`].
        retries_exhausted: Option<u64>,
    },
    /// NoCredentialsError: the signer found no credentials.
    NoCredentials,
    /// EndpointConnectionError: the endpoint could not be reached.
    EndpointConnection,
    /// ProxyConnectionError: the proxy the request goes through could not
    /// be reached, which the CRT reports with the same codes. The URL is the
    /// one the result stored, already masked as botocore masks it.
    ProxyConnection(&'a [u8]),
    /// The AwsCrtError upstream's CRT transfer client raises for a response
    /// checksum mismatch, whose `str` is the error's name, a colon, and its
    /// message (awscrt/exceptions.py).
    ChecksumMismatch { name: &'a [u8], message: &'a [u8] },
    /// Any other CRT failure, with the CRT's own sentence.
    Crt { code: i32, message: &'a [u8] },
}
/// Reads the failure the way botocore's error parser and the CRT's finish
/// would: an error body wins, then an error status, then the CRT code and
/// the runtime's snapshot of the connection it configured.
pub fn classify(result: &TransferResult) -> Kind<'_> {
    let service = &result.service_error;
    if !service.code.is_empty() {
        return Kind::ServiceError {
            code: service.code.as_bytes(),
            message: &service.message,
            operation: service.operation.as_bytes(),
            retries_exhausted: result.retries_exhausted,
        };
    }
    // botocore raises ClientError for any status from 300 up. A request the
    // CRT failed after a success status failed on the client side; one it
    // did not fail is a listing that answered with an unexpected status.
    if result.response_status >= 300 || (result.error_code == 0 && result.response_status != 0) {
        return Kind::HttpStatus {
            status: result.response_status,
            operation: service.operation.as_bytes(),
            retries_exhausted: result.retries_exhausted,
        };
    }
    if result.error_code == NO_CREDENTIALS_ERROR_CODE {
        return Kind::NoCredentials;
    }
    if crt::s3::is_connection_error(result.error_code) {
        return if result.proxy_url.is_empty() {
            Kind::EndpointConnection
        } else {
            Kind::ProxyConnection(result.proxy_url.as_bytes())
        };
    }
    if result.error_code == crt::s3::CHECKSUM_MISMATCH_ERROR_CODE {
        return Kind::ChecksumMismatch {
            name: result.crt_name.as_bytes(),
            message: result.crt_message.as_bytes(),
        };
    }
    Kind::Crt {
        code: result.error_code,
        message: result.crt_message.as_bytes(),
    }
}
/// The failure with what its sentence names: the request URL, and for the
/// HeadObject that validates a download source, the key filegenerator.py
/// quotes when the object is missing.
#[derive(Debug, Clone, Copy)]
pub struct Reason<'a> {
    pub result: &'a TransferResult,
    pub url: RequestUrl<'a>,
    /// Set for the source validation: a 404 becomes `Key "k" does not exist`.
    pub missing_key: Option<&'a str>,
}
impl<'a> Reason<'a> {
    fn request_url(&self) -> RequestUrl<'a> {
        match self.url {
            RequestUrl::Object {
                endpoint_url,
                request_key,
            } => RequestUrl::Object {
                endpoint_url: self.attempt_endpoint(endpoint_url),
                request_key,
            },
            RequestUrl::Listing {
                endpoint_url,
                request_path,
            } => RequestUrl::Listing {
                endpoint_url: self.attempt_endpoint(endpoint_url),
                request_path,
            },
        }
    }
    fn attempt_endpoint(&self, requested: &'a str) -> &'a str {
        let result: &'a TransferResult = self.result;
        let captured = &result.endpoint_url;
        if captured.as_bytes().is_empty() {
            return requested;
        }
        if captured.is_truncated() && requested.as_bytes().starts_with(captured.as_bytes()) {
            return requested;
        }
        std::str::from_utf8(captured.as_bytes()).unwrap_or(requested)
    }
}
/// [`sentence_bytes`] for a request upstream sends through its botocore
/// client: a HeadObject, a listing, a move's DeleteObject. One the signer
/// failed for want of credentials reads as botocore raises it there: with
/// the error of the refresh the request waited for, which `credentials`
/// holds, and as NoCredentialsError when the chain found none. A transfer
/// the CRT client sends keeps the one sentence for both, as upstream's
/// does.
pub fn client_sentence_bytes(
    reason: Reason<'_>,
    credentials: &crt::credentials::Source,
) -> Vec<u8> {
    if matches!(classify(reason.result), Kind::NoCredentials)
        && let Some(failure) = credentials.failure()
    {
        return failure.into_bytes();
    }
    sentence_bytes(reason)
}
/// `str(exception)` for the failure, written as its bytes: a service
/// message keeps the bytes the error body carried, and the proxy URL is the
/// masked text the result stored.
pub fn sentence_bytes(reason: Reason<'_>) -> Vec<u8> {
    let mut out = Vec::new();
    match classify(reason.result) {
        Kind::ServiceError {
            code,
            message,
            operation,
            retries_exhausted,
        } => {
            out.extend_from_slice(b"An error occurred (");
            out.extend_from_slice(code);
            out.extend_from_slice(b") when calling the ");
            out.extend_from_slice(operation_name(operation));
            out.extend_from_slice(
                format!(" operation{}: ", RetryNote { retries_exhausted }).as_bytes(),
            );
            out.extend_from_slice(message);
        }
        Kind::HttpStatus {
            status,
            operation,
            retries_exhausted,
        } => {
            out.extend_from_slice(
                format!("An error occurred ({status}) when calling the ").as_bytes(),
            );
            out.extend_from_slice(operation_name(operation));
            out.extend_from_slice(
                format!(" operation{}: ", RetryNote { retries_exhausted }).as_bytes(),
            );
            if let Some(key) = reason.missing_key.filter(|_| status == 404) {
                out.extend_from_slice(format!("Key \"{key}\" does not exist").as_bytes());
            } else {
                out.extend_from_slice(http_reason_phrase(status).as_bytes());
            }
        }
        Kind::NoCredentials => out.extend_from_slice(NO_CREDENTIALS_MESSAGE.as_bytes()),
        Kind::EndpointConnection => out.extend_from_slice(
            format!(
                "Could not connect to the endpoint URL: \"{}\"",
                reason.request_url()
            )
            .as_bytes(),
        ),
        Kind::ProxyConnection(proxy) => {
            out.extend_from_slice(b"Failed to connect to proxy URL: \"");
            out.extend_from_slice(proxy);
            out.extend_from_slice(b"\"");
        }
        Kind::ChecksumMismatch { name, message } => {
            out.extend_from_slice(name);
            out.extend_from_slice(b": ");
            out.extend_from_slice(message);
        }
        Kind::Crt { code, message: [] } => {
            out.extend_from_slice(format!("CRT error {code}").as_bytes())
        }
        Kind::Crt { message, .. } => out.extend_from_slice(message),
    }
    out
}
/// Returns `str(exception)` for a failed transfer the CRT client ran.
///
/// Upstream's CRT transfer manager translates only an error response into
/// botocore's exception
/// (`BotocoreCRTRequestSerializer.translate_crt_exception`), and raises any
/// other CRT failure as the AwsCrtError itself, whose `str` is the error's
/// name, a colon, and its message (awscrt/exceptions.py). Every other failure
/// reads as [`sentence_bytes`] reads it.
pub fn transfer_sentence_bytes(reason: Reason<'_>) -> Vec<u8> {
    let name = reason.result.crt_name.as_bytes();
    match classify(reason.result) {
        Kind::Crt { message, .. } if !name.is_empty() && !message.is_empty() => {
            let mut out = Vec::new();
            out.extend_from_slice(name);
            out.extend_from_slice(b": ");
            out.extend_from_slice(message);
            out
        }
        _ => sentence_bytes(reason),
    }
}
/// What ClientError adds after the operation once botocore's attempts ran
/// out (exceptions.py `ClientError._get_retry_info`); nothing otherwise.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RetryNote {
    /// See [`TransferResult::retries_exhausted`].
    pub retries_exhausted: Option<u64>,
}
impl fmt::Display for RetryNote {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.retries_exhausted {
            Some(retries) => write!(f, " (reached max retries: {retries})"),
            None => Ok(()),
        }
    }
}
#[cfg(test)]
pub fn sentence(reason: Reason<'_>) -> String {
    String::from_utf8_lossy(&sentence_bytes(reason)).into_owned()
}
/// botocore always knows the operation it called; a capture that lost it
/// is spelled the way botocore spells a missing code.
pub fn operation_name(operation: &[u8]) -> &[u8] {
    if operation.is_empty() {
        b"Unknown"
    } else {
        operation
    }
}
/// `http.client.responses`, which botocore's parser reads for a bodiless
/// error response; empty for a status it does not list.
pub fn http_reason_phrase(status: i32) -> &'static str {
    HTTP_REASON_PHRASES
        .iter()
        .find(|(code, _)| *code == status)
        .map_or("", |(_, text)| text)
}
/// CPython's `http.HTTPStatus` table, in its order.
const HTTP_REASON_PHRASES: &[(i32, &str)] = &[
    (100, "Continue"),
    (101, "Switching Protocols"),
    (102, "Processing"),
    (103, "Early Hints"),
    (200, "OK"),
    (201, "Created"),
    (202, "Accepted"),
    (203, "Non-Authoritative Information"),
    (204, "No Content"),
    (205, "Reset Content"),
    (206, "Partial Content"),
    (207, "Multi-Status"),
    (208, "Already Reported"),
    (226, "IM Used"),
    (300, "Multiple Choices"),
    (301, "Moved Permanently"),
    (302, "Found"),
    (303, "See Other"),
    (304, "Not Modified"),
    (305, "Use Proxy"),
    (307, "Temporary Redirect"),
    (308, "Permanent Redirect"),
    (400, "Bad Request"),
    (401, "Unauthorized"),
    (402, "Payment Required"),
    (403, "Forbidden"),
    (404, "Not Found"),
    (405, "Method Not Allowed"),
    (406, "Not Acceptable"),
    (407, "Proxy Authentication Required"),
    (408, "Request Timeout"),
    (409, "Conflict"),
    (410, "Gone"),
    (411, "Length Required"),
    (412, "Precondition Failed"),
    (413, "Content Too Large"),
    (414, "URI Too Long"),
    (415, "Unsupported Media Type"),
    (416, "Range Not Satisfiable"),
    (417, "Expectation Failed"),
    (418, "I'm a Teapot"),
    (421, "Misdirected Request"),
    (422, "Unprocessable Content"),
    (423, "Locked"),
    (424, "Failed Dependency"),
    (425, "Too Early"),
    (426, "Upgrade Required"),
    (428, "Precondition Required"),
    (429, "Too Many Requests"),
    (431, "Request Header Fields Too Large"),
    (451, "Unavailable For Legal Reasons"),
    (500, "Internal Server Error"),
    (501, "Not Implemented"),
    (502, "Bad Gateway"),
    (503, "Service Unavailable"),
    (504, "Gateway Timeout"),
    (505, "HTTP Version Not Supported"),
    (506, "Variant Also Negotiates"),
    (507, "Insufficient Storage"),
    (508, "Loop Detected"),
    (510, "Not Extended"),
    (511, "Network Authentication Required"),
];
#[cfg(test)]
mod tests;
