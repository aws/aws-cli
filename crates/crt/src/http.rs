//! Requests over aws-c-http on a runtime's bootstrap, outside the S3 client.
//!
//! This is the path a call to any service other than S3 takes: a
//! credential provider's own request to its service, unsigned, or one the
//! runtime's credentials sign. A [`Client`] sends one request per
//! connection, in plaintext or over TLS ([`Request::tls`]), and reads the
//! process environment for nothing: a caller with a proxy connects to it
//! and sends an absolute target.
//!
//! # Bounds
//!
//! [`Client::send`] waits on the calling thread, so it must not run on a
//! CRT thread; the CRT's threads only store what arrives and never wait.
//! The CRT bounds the connect ([`Request::connect_timeout`]), and with
//! the same time again the TLS handshake that follows it. Of a
//! response aws-c-http bounds the first byte, and has for the rest only a
//! throughput monitor that counts in whole seconds, so the waiting thread
//! bounds every silence itself: when nothing arrives for
//! [`Request::read_timeout`] it closes the connection and returns at once.
//!
//! The runtime's bootstrap stage waits for every connection, so the
//! credentials stage's release, which precedes it, refuses new requests and
//! closes the connection of each one in flight. A connect in progress
//! cannot be interrupted, nor can a handshake, and their timeouts bound
//! that wait.
//!
//! A handshake that fails ends its request at once. s2n, the CRT's TLS on
//! Linux, would hold such a connection open for its blinding delay, ten to
//! thirty seconds, with the request and the runtime's release waiting on
//! it; the shim shuts the connection down without that delay, which
//! covered only how long this client took to refuse a server.
use crate::Runtime;
use crate::crt_error::check_pointer;
use crate::signal::lock;
use crt_sys::{self as ffi, native as c};
use std::ffi::{c_int, c_void};
use std::ptr::NonNull;
use std::sync::{Arc, Condvar, Mutex, PoisonError};
use std::time::{Duration, Instant};

/// One request without a body.
#[derive(Clone, Copy)]
pub struct Request<'a> {
    /// Where to connect: a name or an address, without brackets.
    pub host: &'a str,
    pub port: u16,
    /// Connects with TLS, on the trust and the peer verification of the
    /// client's runtime, to a server whose certificate names `host`.
    pub tls: bool,
    pub method: &'a str,
    /// The request target as sent: a path, or an absolute URL for a proxy.
    pub target: &'a str,
    /// The headers as sent, in order, the Host header among them.
    pub headers: &'a [(&'a str, &'a str)],
    /// Signs the request with the runtime's credentials; `None` sends it
    /// as it is.
    pub signing: Option<Signing<'a>>,
    /// How long the connect may take.
    pub connect_timeout: Duration,
    /// How long the response may stay silent once the connection is up:
    /// before its first byte and between any two that follow.
    pub read_timeout: Duration,
}

/// Names the headers and gives the target's length: a header's value may
/// be a session token, and a target may name credentials.
impl std::fmt::Debug for Request<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let names: Vec<&str> = self.headers.iter().map(|(name, _)| *name).collect();
        f.debug_struct("Request")
            .field("host", &self.host)
            .field("port", &self.port)
            .field("tls", &self.tls)
            .field("method", &self.method)
            .field("target_len", &self.target.len())
            .field("headers", &names)
            .field("signing", &self.signing)
            .field("connect_timeout", &self.connect_timeout)
            .field("read_timeout", &self.read_timeout)
            .finish()
    }
}

/// A request's SigV4 scope.
#[derive(Debug, Clone, Copy)]
pub struct Signing<'a> {
    pub region: &'a str,
    pub service: &'a str,
}

/// A response, read whole.
#[derive(Clone, Default, PartialEq, Eq)]
pub struct Response {
    pub status: u16,
    pub body: Vec<u8>,
}

/// Gives the body's length: the body may be a session token or a
/// document of credentials.
impl std::fmt::Debug for Response {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Response")
            .field("status", &self.status)
            .field("body_len", &self.body.len())
            .finish()
    }
}

/// Why a request has no response.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum Error {
    /// The client's runtime is closing or gone.
    Closed,
    /// The request could not be signed or started, no connection came up,
    /// or aws-c-http refused to send the request on it: the CRT's error
    /// code, [`SOCKET_TIMEOUT_ERROR_CODE`] for a connect that took too
    /// long, [`TLS_TIMEOUT_ERROR_CODE`] for a handshake that did, and one
    /// for which [`is_refusal`] holds for a request
    /// aws-c-http would not send.
    Connect(i32),
    /// The connection came up and the response did not arrive whole: the
    /// CRT's error code.
    Response(i32),
    /// The response stayed silent for the request's read timeout.
    ReadTimeout,
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Closed => f.write_str("the runtime is closing"),
            Self::Connect(code) => write!(f, "no connection: CRT error {code}"),
            Self::Response(code) => write!(f, "no response: CRT error {code}"),
            Self::ReadTimeout => f.write_str("the response timed out"),
        }
    }
}

impl std::error::Error for Error {}

/// Whether `code` is one of aws-c-http's own, which before a connection
/// carries a request is its refusal of the request: a header value it will
/// not send, for one. A connection that fails has aws-c-io's codes.
pub fn is_refusal(code: i32) -> bool {
    (HTTP_ERROR_CODES_BEGIN..HTTP_ERROR_CODES_END).contains(&code)
}

/// aws-c-http's error codes: the range of its package, the third
/// (`AWS_C_HTTP_PACKAGE_ID` is 2, and a package holds 1024 codes).
const HTTP_ERROR_CODES_BEGIN: i32 = 2 * 1024;
const HTTP_ERROR_CODES_END: i32 = 3 * 1024;

/// `AWS_IO_SOCKET_TIMEOUT`: a connect that outlasted its timeout.
pub const SOCKET_TIMEOUT_ERROR_CODE: i32 = ffi::AWS_IO_SOCKET_TIMEOUT;

/// `AWS_IO_TLS_NEGOTIATION_TIMEOUT`: a TLS handshake that outlasted the
/// connect timeout, which bounds it as well.
pub const TLS_TIMEOUT_ERROR_CODE: i32 = ffi::AWS_IO_TLS_NEGOTIATION_TIMEOUT;

/// Sends requests on the runtime it came from, for as long as that runtime
/// has not begun to close. Clones share the runtime.
#[derive(Debug, Clone)]
pub struct Client(Arc<Shared>);

/// What a runtime and the clients it handed out share.
#[derive(Debug)]
pub(crate) struct Shared {
    state: Mutex<State>,
}

#[derive(Debug)]
struct State {
    /// `None` once the runtime's credentials stage has begun its release.
    runtime: Option<NonNull<c::Runtime>>,
    /// The calls in flight, each for as long as its sender holds it.
    calls: Vec<NonNull<c::HttpCall>>,
}

// SAFETY: the pointers are only used under the lock: the runtime's until
// its stage clears it, and each call's until its sender, which owns a
// reference, removes it.
unsafe impl Send for Shared {}
// SAFETY: as above.
unsafe impl Sync for Shared {}

impl Shared {
    pub(crate) fn new(runtime: NonNull<c::Runtime>) -> Self {
        Self {
            state: Mutex::new(State {
                runtime: Some(runtime),
                calls: Vec::new(),
            }),
        }
    }
    /// Refuses new requests and closes the connection of each one in
    /// flight, so the runtime's bootstrap stage does not wait for a
    /// response.
    pub(crate) fn close(&self) {
        let mut state = lock(&self.state);
        state.runtime = None;
        for call in &state.calls {
            // SAFETY: a call is listed only while its sender holds its
            // reference, and the sender unlists it under this lock.
            unsafe { c::zaws_http_cancel(call.as_ptr()) };
        }
    }
    /// Starts `request` and lists its call.
    fn start(
        &self,
        request: &Request<'_>,
        exchange: &Arc<Exchange>,
    ) -> Result<NonNull<c::HttpCall>, Error> {
        let cursor = |text: &str| ffi::AwsByteCursor::from_bytes(text.as_bytes());
        let headers: Vec<c::Header> = request
            .headers
            .iter()
            .map(|(name, value)| c::Header {
                name: cursor(name),
                value: cursor(value),
            })
            .collect();
        let signing = request.signing.unwrap_or(Signing {
            region: "",
            service: "",
        });
        let options = c::HttpOptions {
            host: cursor(request.host),
            method: cursor(request.method),
            target: cursor(request.target),
            region: cursor(signing.region),
            service: cursor(signing.service),
            headers: headers.as_ptr(),
            header_count: headers.len(),
            port: u32::from(request.port),
            connect_timeout_ms: milliseconds(request.connect_timeout),
            tls: request.tls,
        };
        let mut state = lock(&self.state);
        let runtime = state.runtime.ok_or(Error::Closed)?;
        let data = Arc::into_raw(Arc::clone(exchange));
        // SAFETY: the lock keeps the runtime's stages from releasing while
        // the call starts, and the shim copies the options before it
        // returns. A started call runs `on_finish` exactly once, which
        // takes the reference `data` holds; the events before it borrow it.
        let started = check_pointer(unsafe {
            c::zaws_http_request(
                runtime.as_ptr(),
                &options,
                Some(on_event),
                Some(on_finish),
                data.cast_mut().cast(),
            )
        });
        let call = match started {
            Ok(call) => call,
            Err(code) => {
                // SAFETY: nothing started, so no callback takes the reference.
                drop(unsafe { Arc::from_raw(data) });
                return Err(Error::Connect(code));
            }
        };
        state.calls.push(call);
        Ok(call)
    }
    /// Unlists `call` and gives up its sender's reference.
    fn finish(&self, call: NonNull<c::HttpCall>) {
        lock(&self.state).calls.retain(|listed| *listed != call);
        // SAFETY: the sender's one reference, which nothing reaches now.
        unsafe { c::zaws_http_release(call.as_ptr()) };
    }
}

/// A timeout as the CRT's milliseconds: never zero, which the CRT reads as
/// no time at all, and the longest it holds for one that is longer.
fn milliseconds(timeout: Duration) -> u32 {
    u32::try_from(timeout.as_millis())
        .unwrap_or(u32::MAX)
        .max(1)
}

/// What one call's callbacks leave for the thread that waits.
#[derive(Default)]
struct Exchange {
    progress: Mutex<Progress>,
    wake: Condvar,
}

#[derive(Default)]
struct Progress {
    /// The connection came up.
    connected: bool,
    /// How many times something arrived.
    events: u64,
    body: Vec<u8>,
    /// The CRT's error code, then the response's status.
    finished: Option<(c_int, c_int)>,
}

/// Runs on a CRT thread, where a panic aborts the process and a wait
/// stalls every connection of the event loop: it stores and returns.
unsafe extern "C" fn on_event(event: c_int, body: ffi::AwsByteCursor, data: *mut c_void) {
    // SAFETY: the reference `Shared::start` gave the call is live until
    // `on_finish`, which follows every event.
    let exchange = unsafe { &*data.cast::<Exchange>() };
    let mut progress = lock(&exchange.progress);
    progress.events += 1;
    if event == c::HTTP_CONNECTED {
        progress.connected = true;
    }
    if event == c::HTTP_BODY && body.len != 0 {
        // SAFETY: a body event's cursor points at `len` bytes that are
        // live for this call.
        let bytes = unsafe { std::slice::from_raw_parts(body.ptr, body.len) };
        progress.body.extend_from_slice(bytes);
    }
    exchange.wake.notify_all();
    drop(progress);
}

/// Runs once, on the starting thread or a CRT thread.
unsafe extern "C" fn on_finish(error_code: c_int, status: c_int, data: *mut c_void) {
    // SAFETY: this takes the reference `Shared::start` gave the call.
    let exchange = unsafe { Arc::from_raw(data.cast_const().cast::<Exchange>()) };
    let mut progress = lock(&exchange.progress);
    progress.finished = Some((error_code, status));
    exchange.wake.notify_all();
    drop(progress);
}

impl Exchange {
    /// Waits for the call's end, or for a silence of `read_timeout` once
    /// the connection is up, which is `None`.
    fn wait(&self, read_timeout: Duration) -> Option<Result<Response, Error>> {
        let mut progress = lock(&self.progress);
        let mut seen = progress.events;
        let mut deadline = Instant::now() + read_timeout;
        loop {
            if let Some((error_code, status)) = progress.finished {
                let connected = progress.connected;
                let body = std::mem::take(&mut progress.body);
                return Some(outcome(error_code, status, connected, body));
            }
            if !progress.connected {
                // The CRT bounds the connect.
                progress = crate::signal::wait(&self.wake, progress);
                continue;
            }
            if progress.events != seen {
                seen = progress.events;
                deadline = Instant::now() + read_timeout;
            }
            // `None` here is the silence that outlasted the timeout.
            let left = deadline
                .checked_duration_since(Instant::now())
                .filter(|left| !left.is_zero())?;
            progress = self
                .wake
                .wait_timeout(progress, left)
                .unwrap_or_else(PoisonError::into_inner)
                .0;
        }
    }
}

fn outcome(
    error_code: c_int,
    status: c_int,
    connected: bool,
    body: Vec<u8>,
) -> Result<Response, Error> {
    match (error_code, u16::try_from(status)) {
        (0, Ok(status)) => Ok(Response { status, body }),
        (0, Err(_)) => Err(Error::Response(UNKNOWN_ERROR_CODE)),
        (code, _) if connected => Err(Error::Response(code)),
        (code, _) => Err(Error::Connect(code)),
    }
}

/// `AWS_ERROR_UNKNOWN`, for a status no HTTP response has.
const UNKNOWN_ERROR_CODE: i32 = 3;

impl Runtime {
    /// A client that sends on this runtime's bootstrap until the runtime
    /// begins to close.
    pub fn http_client(&self) -> Client {
        Client(self.http())
    }
}

impl Client {
    /// Sends `request` and waits for its response, so this must not run on
    /// a CRT thread. See the module's notes on what bounds the wait.
    ///
    /// # Errors
    /// See [`Error`]. A request signed by a delegate that fails its query
    /// gives `Connect` with `AWS_AUTH_SIGNING_NO_CREDENTIALS`.
    pub fn send(&self, request: &Request<'_>) -> Result<Response, Error> {
        let exchange = Arc::new(Exchange::default());
        let call = self.0.start(request, &exchange)?;
        let result = exchange.wait(request.read_timeout).unwrap_or_else(|| {
            // The close ends the call on the CRT's threads, which keep
            // what they need of it; nothing here waits for that.
            // SAFETY: this sender's reference is live until `finish`.
            unsafe { c::zaws_http_cancel(call.as_ptr()) };
            Err(Error::ReadTimeout)
        });
        self.0.finish(call);
        result
    }
}

#[cfg(test)]
mod tests;
