//! Construction and reverse teardown of the CRT dependency graph.
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum ChecksumMode {
    WhenSupported,
    #[default]
    WhenRequired,
}
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct FileIoOptions {
    pub should_stream: bool,
    pub disk_throughput_gbps: f64,
    pub direct_io: bool,
}
/// The trust store every TLS connection of a runtime verifies peers
/// against: one source at a time.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub enum Trust {
    /// The platform's default trust store.
    #[default]
    Platform,
    /// PEM certificates held in memory, such as the payload's bundle.
    Pem(Vec<u8>),
    /// A CA file the CRT reads as `ca_file`.
    File {
        path: PathBuf,
        /// The setting that named `path`, as the user spelled it, which the
        /// diagnostic for a file the CRT cannot load names.
        setting: &'static str,
    },
}

/// botocore's attempts per request when none are configured
/// (retries/standard.py `DEFAULT_MAX_ATTEMPTS`).
pub const BOTOCORE_ATTEMPTS_DEFAULT: u64 = 3;
/// Explicit configuration captured before any CRT worker thread starts.
#[derive(Debug, Clone, PartialEq)]
pub struct RuntimeOptions {
    pub region: String,
    pub signing_region: Option<String>,
    pub endpoint_url: String,
    /// What a signed runtime signs with.
    pub credentials: crate::credentials::Source,
    pub trust: Trust,
    pub verify_peer: bool,
    pub no_sign_request: bool,
    pub keep_alive: bool,
    pub connect_timeout_ms: u32,
    /// Attempts per request, first included, from `RETRY_ATTEMPTS_MIN` to
    /// `RETRY_ATTEMPTS_MAX`; `None` keeps the CRT's standard strategy with its
    /// own default.
    pub max_attempts: Option<u32>,
    /// Attempts per request, first included, of the requests the AWS CLI
    /// sends through botocore, whatever client the transfers run on: listing
    /// pages, a single download's HeadObject, and a move's source
    /// DeleteObject. They take them where botocore retries what the CRT does
    /// not (`s3::botocore_retry`): a listing page botocore's parser rejects, and a 429
    /// the CRT gave up on.
    pub botocore_attempts: u64,
    pub part_size: u64,
    pub multipart_upload_threshold: Option<u64>,
    pub single_request_threshold: Option<u64>,
    pub file_io: Option<FileIoOptions>,
    pub request_checksum_calculation: ChecksumMode,
    pub response_checksum_validation: ChecksumMode,
    pub user_agent: String,
    pub proxy_url: Option<String>,
    /// The client endpoint's netloc when the NO_PROXY list bypasses it, which
    /// `--debug` names as the client starts; None for a client that resolved
    /// its proxy or has no list to match.
    pub proxy_bypass_netloc: Option<String>,
    pub event_loop_count: u16,
    pub throughput_target_gbps: f64,
    pub memory_limit_in_bytes: u64,
    pub max_active_connections_override: u32,
    pub numa_source_pool_config: Option<crate::source_pool::Config>,
}
impl Default for RuntimeOptions {
    fn default() -> Self {
        Self {
            region: "us-east-1".into(),
            signing_region: None,
            endpoint_url: String::new(),
            credentials: crate::credentials::Source::Missing,
            trust: Trust::Platform,
            verify_peer: true,
            no_sign_request: false,
            keep_alive: false,
            connect_timeout_ms: 0,
            max_attempts: None,
            botocore_attempts: BOTOCORE_ATTEMPTS_DEFAULT,
            part_size: 0,
            multipart_upload_threshold: None,
            single_request_threshold: None,
            file_io: None,
            request_checksum_calculation: ChecksumMode::WhenRequired,
            response_checksum_validation: ChecksumMode::WhenRequired,
            user_agent: "aws-cli-native".into(),
            proxy_url: None,
            proxy_bypass_netloc: None,
            event_loop_count: 0,
            throughput_target_gbps: 10.0,
            memory_limit_in_bytes: 0,
            max_active_connections_override: 0,
            numa_source_pool_config: None,
        }
    }
}
/// Removes the prefix and suffix used for FIPS pseudo regions.
pub fn normalize_fips_pseudo_region(region: &str) -> &str {
    let region = region.strip_prefix("fips-").unwrap_or(region);
    region.strip_suffix("-fips").unwrap_or(region)
}
/// Chooses an endpoint-provided signing region before the normalized fallback.
pub fn effective_signing_region(options: &RuntimeOptions) -> &str {
    options
        .signing_region
        .as_deref()
        .unwrap_or_else(|| normalize_fips_pseudo_region(&options.region))
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum Stage {
    Endpoint,
    Region,
    EventLoop,
    Resolver,
    Bootstrap,
    Tls,
    Credentials,
    Client,
}
const _: () = {
    use crt_sys::native as c;
    assert!(Stage::Endpoint as u32 == c::STAGE_ENDPOINT);
    assert!(Stage::Region as u32 == c::STAGE_REGION);
    assert!(Stage::EventLoop as u32 == c::STAGE_EVENT_LOOP);
    assert!(Stage::Resolver as u32 == c::STAGE_RESOLVER);
    assert!(Stage::Bootstrap as u32 == c::STAGE_BOOTSTRAP);
    assert!(Stage::Tls as u32 == c::STAGE_TLS);
    assert!(Stage::Credentials as u32 == c::STAGE_CREDENTIALS);
    assert!(Stage::Client as u32 == c::STAGE_CLIENT);
};
const STAGES: [Stage; 8] = [
    Stage::Endpoint,
    Stage::Region,
    Stage::EventLoop,
    Stage::Resolver,
    Stage::Bootstrap,
    Stage::Tls,
    Stage::Credentials,
    Stage::Client,
];
/// Socket-free seam exercising the same acquisition and release order as CRT.
pub trait RuntimeLifecycleOps {
    type Error;
    fn acquire_library(&mut self);
    fn release_library(&mut self);
    fn start(&mut self, stage: Stage, options: &RuntimeOptions) -> Result<(), Self::Error>;
    fn release(&mut self, stage: Stage);
}
/// Executes the dependency graph; failed stages clean their own partial work.
#[derive(Debug)]
pub struct Lifecycle<O: RuntimeLifecycleOps> {
    ops: O,
    completed: usize,
    library: bool,
}
impl<O: RuntimeLifecycleOps> Lifecycle<O> {
    /// Initializes in order and cleans every completed stage on failure.
    pub fn new(mut ops: O, options: &RuntimeOptions) -> Result<Self, O::Error> {
        ops.acquire_library();
        let mut lifecycle = Self {
            ops,
            completed: 0,
            library: true,
        };
        for stage in STAGES {
            lifecycle.ops.start(stage, options)?;
            lifecycle.completed += 1;
        }
        Ok(lifecycle)
    }
    /// Returns the injected implementation for read-only diagnostics.
    pub fn ops(&self) -> &O {
        &self.ops
    }
    /// Releases resources once, in exact reverse order.
    pub fn close(&mut self) {
        while self.completed > 0 {
            self.completed -= 1;
            self.ops.release(STAGES[self.completed]);
        }
        if self.library {
            self.library = false;
            self.ops.release_library();
        }
    }
}
impl<O: RuntimeLifecycleOps> Drop for Lifecycle<O> {
    fn drop(&mut self) {
        self.close();
    }
}
mod bucket;
mod native;
#[doc(inline)]
pub use bucket::BucketRuntime;
#[doc(inline)]
pub use native::{Library, Runtime, SdkutilsLibrary};
pub fn platform() -> cli_core::client_config::Platform {
    static PLATFORM: std::sync::OnceLock<cli_core::client_config::Platform> =
        std::sync::OnceLock::new();
    *PLATFORM.get_or_init(|| {
        let _library = Library::acquire();
        let mut recommended = 0.0;
        // SAFETY: the shim writes one stack scalar while CRT library state is retained.
        let optimized = unsafe { crt_sys::native::zaws_platform(&mut recommended) };
        platform_from_info(recommended, optimized)
    })
}
fn platform_from_info(recommended: f64, optimized: bool) -> cli_core::client_config::Platform {
    cli_core::client_config::Platform {
        optimized,
        recommended_gbps: (recommended.is_finite() && recommended > 0.0).then_some(recommended),
    }
}
#[cfg(test)]
mod tests;
