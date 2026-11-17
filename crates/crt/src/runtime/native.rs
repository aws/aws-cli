use super::{
    Lifecycle, RuntimeLifecycleOps, RuntimeOptions, Stage, Trust, effective_signing_region,
};
use crate::crt_error::{check_keeping_status, check_pointer};
use crate::s3::TransferResult;
use crate::signal::{ShutdownSignal, lock};
use cli_core::client_config::{RETRY_ATTEMPTS_MAX, RETRY_ATTEMPTS_MIN};
use crt_sys::{self as ffi, native as c};
use std::ffi::{CString, c_int, c_void};
use std::ptr::NonNull;
use std::sync::{Arc, Mutex};

/// Holders of the CRT libraries. aws-c-common records its initialization in
/// one flag that aws-c-io's clean-up clears, so no clean-up may run while any
/// holder of either kind remains.
#[derive(Debug)]
struct LibraryState {
    full: usize,
    sdkutils: usize,
    full_live: bool,
    sdkutils_live: bool,
}
trait LibraryOps {
    fn library_init(&mut self);
    fn library_clean_up(&mut self);
    fn sdkutils_init(&mut self);
    fn sdkutils_clean_up(&mut self);
}
#[derive(Debug)]
struct CrtLibraryOps;
impl LibraryOps for CrtLibraryOps {
    fn library_init(&mut self) {
        // SAFETY: the state lock serializes library initialization; the
        // allocator is process-lifetime.
        unsafe { ffi::rust_crt_library_init(ffi::rust_crt_allocator()) };
    }
    fn library_clean_up(&mut self) {
        // SAFETY: no holder remains, and every holder drains its CRT
        // resources before releasing.
        unsafe { ffi::rust_crt_library_clean_up() };
    }
    fn sdkutils_init(&mut self) {
        // SAFETY: the state lock serializes every CRT library counter; the
        // allocator is process-lifetime.
        unsafe { crt_sys::endpoints::aws_sdkutils_library_init(ffi::rust_crt_allocator()) };
    }
    fn sdkutils_clean_up(&mut self) {
        // SAFETY: pairs with the sdkutils-only initialization; no holder
        // remains.
        unsafe { crt_sys::endpoints::aws_sdkutils_library_clean_up() };
    }
}
impl LibraryState {
    const fn new() -> Self {
        Self {
            full: 0,
            sdkutils: 0,
            full_live: false,
            sdkutils_live: false,
        }
    }
    fn acquire_full(&mut self, ops: &mut impl LibraryOps) {
        if !self.full_live {
            ops.library_init();
            self.full_live = true;
        }
        self.full += 1;
    }
    /// Initializes sdkutils alone unless a live S3 library, which
    /// initializes it through aws-c-auth, or an earlier holder already has.
    fn acquire_sdkutils(&mut self, ops: &mut impl LibraryOps) {
        if !self.full_live && !self.sdkutils_live {
            ops.sdkutils_init();
            self.sdkutils_live = true;
        }
        self.sdkutils += 1;
    }
    fn release_full(&mut self, ops: &mut impl LibraryOps) {
        self.full -= 1;
        self.settle(ops);
    }
    fn release_sdkutils(&mut self, ops: &mut impl LibraryOps) {
        self.sdkutils -= 1;
        self.settle(ops);
    }
    fn settle(&mut self, ops: &mut impl LibraryOps) {
        if self.full != 0 || self.sdkutils != 0 {
            return;
        }
        if std::mem::take(&mut self.full_live) {
            ops.library_clean_up();
        }
        if std::mem::take(&mut self.sdkutils_live) {
            ops.sdkutils_clean_up();
        }
    }
}
static LIBRARY_STATE: Mutex<LibraryState> = Mutex::new(LibraryState::new());

fn ca_bundle(options: &RuntimeOptions) -> Result<Option<CString>, Box<TransferResult>> {
    let Trust::File { path, .. } = &options.trust else {
        return Ok(None);
    };
    CString::new(path.as_os_str().as_encoded_bytes())
        .map(Some)
        .map_err(|_| Box::new(TransferResult::invalid_argument()))
}
fn ca_pem(options: &RuntimeOptions) -> &[u8] {
    match &options.trust {
        Trust::Pem(pem) => pem,
        Trust::Platform | Trust::File { .. } => &[],
    }
}

/// A reference to the CRT error tables and process-global library state.
#[derive(Debug)]
pub struct Library {
    _private: (),
}
impl Library {
    /// Initializes on the first reference, preserving concurrent runtimes.
    pub fn acquire() -> Self {
        lock(&LIBRARY_STATE).acquire_full(&mut CrtLibraryOps);
        Self { _private: () }
    }
}
impl Drop for Library {
    fn drop(&mut self) {
        lock(&LIBRARY_STATE).release_full(&mut CrtLibraryOps);
    }
}
/// aws-c-sdkutils alone, for endpoint rule evaluation, which needs no I/O,
/// TLS, or S3 library. It shares [`Library`]'s state: a live S3 library
/// already holds sdkutils, and neither kind cleans up while the other is
/// held.
#[derive(Debug)]
pub struct SdkutilsLibrary {
    _private: (),
}
impl SdkutilsLibrary {
    pub fn acquire() -> Self {
        lock(&LIBRARY_STATE).acquire_sdkutils(&mut CrtLibraryOps);
        Self { _private: () }
    }
}
impl Drop for SdkutilsLibrary {
    fn drop(&mut self) {
        lock(&LIBRARY_STATE).release_sdkutils(&mut CrtLibraryOps);
    }
}
#[derive(Debug)]
struct NativeOps {
    pointer: NonNull<c::Runtime>,
    signals: [Arc<ShutdownSignal>; 8],
    library: Option<Library>,
    pool: Option<Box<crate::source_pool::FactoryConfig>>,
    /// The CLI's own credentials, which the CRT's delegate provider calls
    /// until the credentials stage's shutdown.
    delegate: crate::credentials::native::Pinned,
    /// The requests sent over aws-c-http on this runtime's bootstrap, which
    /// the credentials stage's release closes so that the bootstrap's does
    /// not wait for a response.
    http: Arc<crate::http::Shared>,
    logger: Option<std::sync::Arc<crate::debug::Logger>>,
}
fn construction_failure(logger: Option<&crate::debug::Logger>, code: i32) -> Box<TransferResult> {
    if let Some(logger) = logger {
        crate::s3::record_outcome(logger, code, 0);
    }
    Box::new(TransferResult::from_crt_error(code))
}
impl NativeOps {
    fn new(
        options: &RuntimeOptions,
        logger: Option<std::sync::Arc<crate::debug::Logger>>,
    ) -> Result<Self, Box<TransferResult>> {
        // SAFETY: allocator query/allocation have no external pointer arguments.
        let pointer = check_pointer(unsafe { c::zaws_runtime_allocate() })
            .map_err(|code| construction_failure(logger.as_deref(), code))?;
        Ok(Self {
            pointer,
            signals: std::array::from_fn(|_| Arc::new(ShutdownSignal::new())),
            library: None,
            pool: options
                .numa_source_pool_config
                .clone()
                .map(crate::source_pool::FactoryConfig::new)
                .map(Box::new),
            delegate: Box::new(options.credentials.delegate()),
            http: Arc::new(crate::http::Shared::new(pointer)),
            logger,
        })
    }
    fn shim_options(&self, o: &RuntimeOptions, bundle: Option<&CString>) -> c::RuntimeOptions {
        c::RuntimeOptions {
            endpoint: ffi::AwsByteCursor::from_bytes(o.endpoint_url.as_bytes()),
            region: ffi::AwsByteCursor::from_bytes(o.region.as_bytes()),
            signing_region: ffi::AwsByteCursor::from_bytes(effective_signing_region(o).as_bytes()),
            proxy_url: ffi::AwsByteCursor::from_bytes(
                o.proxy_url.as_deref().unwrap_or("").as_bytes(),
            ),
            ca_bundle: bundle.map_or(std::ptr::null(), |v| v.as_ptr()),
            throughput_target_gbps: o.throughput_target_gbps,
            memory_limit: o.memory_limit_in_bytes,
            max_connections: o.max_active_connections_override,
            event_loop_count: o.event_loop_count,
            pool_factory: self
                .pool
                .as_ref()
                .map(|_| crate::source_pool::factory as ffi::PoolFactoryFn),
            pool_data: self.pool.as_deref().map_or(std::ptr::null_mut(), |pool| {
                (pool as *const crate::source_pool::FactoryConfig)
                    .cast_mut()
                    .cast()
            }),
            ca_pem: ffi::AwsByteCursor::from_bytes(ca_pem(o)),
            user_agent: ffi::AwsByteCursor::from_bytes(o.user_agent.as_bytes()),
            part_size: o.part_size,
            multipart_upload_threshold: o.multipart_upload_threshold.unwrap_or(0),
            disk_throughput_gbps: o.file_io.map_or(0.0, |v| v.disk_throughput_gbps),
            max_attempts: o.max_attempts.unwrap_or(0),
            connect_timeout_ms: o.connect_timeout_ms,
            verify_peer: o.verify_peer,
            no_sign_request: o.no_sign_request,
            keep_alive: o.keep_alive,
            has_file_io: o.file_io.is_some(),
            file_should_stream: o.file_io.is_some_and(|v| v.should_stream),
            file_direct_io: o.file_io.is_some_and(|v| v.direct_io),
            request_checksum: o.request_checksum_calculation == super::ChecksumMode::WhenSupported,
            response_checksum: o.response_checksum_validation == super::ChecksumMode::WhenSupported,
            credentials_delegate: Some(
                crate::credentials::native::on_query as ffi::CredentialsDelegateFn,
            ),
            credentials_delegate_data: crate::credentials::native::data(&self.delegate),
        }
    }
    fn record_start(&self, stage: Stage, o: &RuntimeOptions) {
        let Some(logger) = &self.logger else {
            return;
        };
        match (stage, &o.proxy_bypass_netloc) {
            (Stage::Endpoint, _) => logger.record(
                "awscli.native.endpoint",
                &format!("Endpoint URL: {}", o.endpoint_url),
            ),
            (Stage::Client, Some(netloc)) => logger.record(
                "awscli.native.proxy",
                &format!("Proxy bypassed for {netloc}: NO_PROXY matches"),
            ),
            _ => {}
        }
    }
    fn stage_failure(&self, rc: c_int, code: i32, o: &RuntimeOptions) -> Box<TransferResult> {
        if let (c::TRUST_FILE_REJECTED, Some(logger), Trust::File { path, setting }) =
            (rc, &self.logger, &o.trust)
        {
            let mut message = format!("CA bundle setting={setting} path=").into_bytes();
            message.extend_from_slice(path.as_os_str().as_encoded_bytes());
            logger.record_bytes("awscli.native.tls", &message);
        }
        let mut failure = construction_failure(self.logger.as_deref(), code);
        if rc == c::CLIENT_FAILED_WITH_PROXY {
            failure.proxy_url = crate::s3::masked_proxy(o.proxy_url.as_deref().unwrap_or(""));
        }
        failure
    }
}
impl RuntimeLifecycleOps for NativeOps {
    type Error = Box<TransferResult>;
    fn acquire_library(&mut self) {
        self.library = Some(Library::acquire());
    }
    fn release_library(&mut self) {
        self.library = None;
    }
    fn start(&mut self, stage: Stage, o: &RuntimeOptions) -> Result<(), Self::Error> {
        self.record_start(stage, o);
        let bundle = ca_bundle(o)?;
        let options = self.shim_options(o, bundle.as_ref());
        let signal = Arc::as_ptr(&self.signals[stage as usize]).cast_mut().cast();
        // SAFETY: C copies cursors needed after this call. A started stage's
        // signal stays alive until release has waited for its shutdown callback;
        // a stage that fails to start never receives one, because its CRT
        // constructor registers the callback only after its last failure point.
        let started = check_keeping_status(unsafe {
            c::zaws_runtime_start_stage(
                self.pointer.as_ptr(),
                stage as u32,
                &options,
                Some(on_shutdown),
                signal,
            )
        });
        let Err((rc, code)) = started else {
            return Ok(());
        };
        let failure = self.stage_failure(rc, code, o);
        if matches!(stage, Stage::Endpoint | Stage::Region | Stage::Tls) {
            // SAFETY: these synchronous stages permit partial-state cleanup.
            unsafe {
                c::zaws_runtime_release_stage(self.pointer.as_ptr(), stage as u32);
            }
        }
        Err(failure)
    }
    fn release(&mut self, stage: Stage) {
        if stage == Stage::Credentials {
            self.http.close();
        }
        // SAFETY: lifecycle releases a completed stage once, before dependencies.
        unsafe {
            c::zaws_runtime_release_stage(self.pointer.as_ptr(), stage as u32);
        }
        if matches!(
            stage,
            Stage::EventLoop
                | Stage::Resolver
                | Stage::Bootstrap
                | Stage::Credentials
                | Stage::Client
        ) {
            self.signals[stage as usize].wait();
        }
    }
}
impl Drop for NativeOps {
    fn drop(&mut self) {
        // SAFETY: Lifecycle has already drained every initialized resource.
        unsafe {
            c::zaws_runtime_destroy(self.pointer.as_ptr());
        }
    }
}
pub(crate) unsafe extern "C" fn on_shutdown(data: *mut c_void) {
    let pointer = data.cast::<ShutdownSignal>();
    // SAFETY: NativeOps retains this Arc until notification; acquire a callback
    // reference first so a waking waiter cannot free it before complete returns.
    unsafe {
        Arc::increment_strong_count(pointer);
    }
    // SAFETY: the increment above transferred one owned reference to this callback.
    let signal = unsafe { Arc::from_raw(pointer) };
    signal.complete();
}
#[cfg(test)]
mod tests;
/// A runtime whose signing and region storage remain pinned in its C holder.
#[derive(Debug)]
pub struct Runtime {
    lifecycle: Lifecycle<NativeOps>,
    options: RuntimeOptions,
    logger: Option<std::sync::Arc<crate::debug::Logger>>,
}
// SAFETY: CRT submission APIs are thread-safe and options remain immutable;
// exclusive drop waits for every callback and dependent resource shutdown.
unsafe impl Send for Runtime {}
// SAFETY: concurrent access only submits to the CRT's synchronized client.
unsafe impl Sync for Runtime {}
impl Runtime {
    /// Builds the runtime from explicitly captured process configuration.
    pub fn new(options: RuntimeOptions) -> Result<Self, Box<TransferResult>> {
        Self::build(options, None)
    }
    fn build(
        options: RuntimeOptions,
        logger: Option<std::sync::Arc<crate::debug::Logger>>,
    ) -> Result<Self, Box<TransferResult>> {
        if options
            .max_attempts
            .is_some_and(|attempts| !(RETRY_ATTEMPTS_MIN..=RETRY_ATTEMPTS_MAX).contains(&attempts))
        {
            return Err(Box::new(TransferResult::invalid_argument()));
        }
        let ops = NativeOps::new(&options, logger.clone())?;
        let lifecycle = Lifecycle::new(ops, &options)?;
        let runtime = Self {
            lifecycle,
            options,
            logger,
        };
        let attached = match &runtime.options.credentials {
            crate::credentials::Source::Delegate(delegate) => delegate.attach(&runtime),
            crate::credentials::Source::Missing => Ok(()),
        };
        if attached.is_err() {
            let logger = runtime.logger.clone();
            // Torn down before the failure is recorded, as a stage's is.
            drop(runtime);
            return Err(construction_failure(
                logger.as_deref(),
                crate::s3::NO_CREDENTIALS_ERROR_CODE,
            ));
        }
        Ok(runtime)
    }
    /// Retains the process logger throughout this runtime's shutdown.
    pub fn new_with_logger(
        options: RuntimeOptions,
        logger: std::sync::Arc<crate::debug::Logger>,
    ) -> Result<Self, Box<TransferResult>> {
        Self::build(options, Some(logger))
    }
    /// Returns immutable options used for this runtime.
    pub fn options(&self) -> &RuntimeOptions {
        &self.options
    }
    /// The process logger this runtime retains, which its credentials'
    /// delegate records to under `--debug`.
    pub fn logger(&self) -> Option<std::sync::Arc<crate::debug::Logger>> {
        self.logger.clone()
    }
    pub(crate) fn record_outcome(&self, code: i32, status: i32) {
        if let Some(logger) = &self.logger {
            super::super::s3::record_outcome(logger, code, status);
        }
    }
    pub(crate) fn pointer(&self) -> *mut c::Runtime {
        self.lifecycle.ops().pointer.as_ptr()
    }
    /// What this runtime's HTTP clients share with it.
    pub(crate) fn http(&self) -> Arc<crate::http::Shared> {
        Arc::clone(&self.lifecycle.ops().http)
    }
}
