//! Resolve one invocation's client settings and preserve their configuration sources.
use crate::command::{CredentialSource, Globals};
pub use crate::endpoint_config::AddressingStyle;
use crate::endpoint_config::S3Block;
use crate::{EnvMap, aws_profile, cli_error::PythonReason, shared_config};
use awscli_config::ParsedFiles;
use std::ffi::OsStr;
use std::path::{Path, PathBuf};
mod ca_bundle;
pub mod coerce;
mod diagnostics;
mod transfer;
pub mod user_agent;

const TARGET_GBPS_LIST: f64 = 10.0;
/// The floor upstream applies when `crt` is preferred
/// (`MINIMUM_TARGET_THROUGHPUT_GBPS`).
const TARGET_GBPS_CRT_PREFERRED_MIN: f64 = 10.0;
/// The target upstream gives a newly eligible host the CRT has no estimate
/// for (`UNTUNED_TARGET_THROUGHPUT_GBPS`): the 256 MiB tier.
const TARGET_GBPS_UNTUNED: f64 = 4.0;
/// The target s3transfer falls back to when the CRT has no recommendation
/// (`_get_crt_throughput_target_gbps`).
const TARGET_GBPS_UNRECOMMENDED: f64 = 10.0;
const CONNECT_TIMEOUT_SECONDS_MAX: i64 = i64::MAX / 1_000_000_000;
/// The connect timeout when `--cli-connect-timeout` is unset: botocore's
/// `DEFAULT_TIMEOUT` of 60 s, which globalargs.py `_resolve_timeout` applies.
const CONNECT_TIMEOUT_MS_DEFAULT: u32 = 60_000;
const ATTEMPTS_DEFAULT: u32 = 3;
const PART_SIZE_DEFAULT: u64 = 8 << 20;
const MULTIPART_THRESHOLD_DEFAULT: u64 = 8 << 20;
const CONNECTIONS_DEFAULT: u32 = 10;
const MEMORY_LIMIT_MIB: u64 = 1 << 20;
const MEMORY_LIMIT_GIB: u64 = 1 << 30;
/// The smallest buffer pool aws-c-s3 builds; a smaller one fails the client.
/// Every throughput tier is at least this.
const MEMORY_LIMIT_BYTES_MIN: u64 = 256 * MEMORY_LIMIT_MIB;
const TRUST_PATH_BYTES_MAX: usize = if cfg!(target_vendor = "apple") {
    1024
} else {
    4096
};
/// The payload entry that holds botocore's CA bundle, as `_zippy_finder.get_data`
/// names it in crates/python-fallback/python/runtime.py. The s3 crate borrows it
/// from the payload, and the trust record names it.
pub const CACERT_ENTRY_NAME: &str = "awscli/botocore/cacert.pem";
/// The largest part aws-c-s3 accepts whatever its memory limit
/// (`g_default_max_part_size`, s3_util.c).
pub const PART_SIZE_MAX: u64 = 5 << 30;
/// The fewest attempts the CRT's standard strategy can express: it reads zero
/// retries as its default of three.
pub const RETRY_ATTEMPTS_MIN: u32 = 2;
/// The most attempts it can express: its exponential backoff rejects more than
/// 63 retries.
pub const RETRY_ATTEMPTS_MAX: u32 = 64;
const _: () = {
    assert!(RETRY_ATTEMPTS_MIN < RETRY_ATTEMPTS_MAX);
    assert!(TRUST_PATH_BYTES_MAX > 1);
    assert!(TARGET_GBPS_UNTUNED < TARGET_GBPS_CRT_PREFERRED_MIN);
    assert!(TARGET_GBPS_LIST > 0.0);
    assert!(TARGET_GBPS_UNRECOMMENDED > 0.0);
    assert!(ATTEMPTS_DEFAULT >= RETRY_ATTEMPTS_MIN);
    assert!(ATTEMPTS_DEFAULT <= RETRY_ATTEMPTS_MAX);
    assert!(PART_SIZE_DEFAULT <= part_size_max(MEMORY_LIMIT_BYTES_MIN));
    assert!(MULTIPART_THRESHOLD_DEFAULT >= PART_SIZE_DEFAULT);
    assert!(CONNECT_TIMEOUT_SECONDS_MAX <= i64::MAX / 1000);
    assert!(CONNECT_TIMEOUT_SECONDS_MAX * 1000 > u32::MAX as i64);
};

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum Command {
    #[default]
    Ls,
    Cp,
    Mv,
    Rm,
    Sync,
}
impl Command {
    /// Whether the command builds a transfer manager.
    ///
    /// `s3 cp`, `s3 mv`, `s3 rm`, and `s3 sync` build one and `s3 ls` does not.
    /// The commands that build one resolve the same persona and transfer
    /// configuration.
    pub const fn transfers(self) -> bool {
        matches!(self, Self::Cp | Self::Mv | Self::Rm | Self::Sync)
    }
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum Source {
    #[default]
    Default,
    Persona,
    Flag(&'static str),
    Env(&'static str),
    Profile(&'static str),
    S3(&'static str),
}
impl Source {
    pub fn setting_name(self) -> &'static str {
        match self {
            Self::Default => "default",
            Self::Persona => "persona",
            Self::Flag(v) | Self::Env(v) | Self::Profile(v) | Self::S3(v) => v,
        }
    }
}
impl std::fmt::Display for Source {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Default => f.write_str("default"),
            Self::Persona => f.write_str("persona"),
            Self::Flag(v) => write!(f, "flag {v}"),
            Self::Env(v) => write!(f, "environment variable {v}"),
            Self::Profile(v) => write!(f, "profile key {v}"),
            Self::S3(v) => write!(f, "profile key s3.{v}"),
        }
    }
}
/// The record inputs the decision table's honored rows feed. Every honored row
/// of cli-router's table that this record consumes names one of them. This
/// crate sits below the router and cannot see the table, so each reader
/// consults the names [`Field::settings`] lists, and cli-router's tests hold
/// the two in step: every field has an honored row, and the rows naming a field
/// are exactly its settings, in its precedence order. [`resolve`] reads the
/// fields in declaration order and stops at the first value only Python can
/// report, which follows upstream's phases: the botocore client's arguments and
/// its `Config` (`ClientArgsCreator.get_client_args`), then its endpoint and CA
/// bundle, then the transfer configuration, then the CRT client, whose buffer
/// pool checks the part size.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Field {
    /// The `s3` block's endpoint rule inputs: `addressing_style`,
    /// `use_accelerate_endpoint`, and `use_dualstack_endpoint`.
    S3Endpoint,
    /// `AWS_MAX_ATTEMPTS`, then the profile's `max_attempts`.
    MaxAttempts,
    /// `AWS_REQUEST_CHECKSUM_CALCULATION`, then the profile's
    /// `request_checksum_calculation`.
    RequestChecksumCalculation,
    /// `AWS_RESPONSE_CHECKSUM_VALIDATION`, then the profile's
    /// `response_checksum_validation`.
    ResponseChecksumValidation,
    /// `AWS_RETRY_MODE`, then the profile's `retry_mode`.
    RetryMode,
    /// The profile's `tcp_keepalive`.
    TcpKeepalive,
    /// The CA bundle path: `AWS_CA_BUNDLE`, then the profile's `ca_bundle`,
    /// then `REQUESTS_CA_BUNDLE`.
    CaBundle,
    /// The proxy variables of both destination schemes and the bypass list,
    /// which `proxy::Environment::from_map` reads.
    Proxy,
    /// The `s3` block's transfer keys, coerced in upstream's pipeline order.
    Transfer,
    /// The CRT's memory-limit variables, which size the buffer pool a
    /// configured part size must fit when upstream's CRT client is built.
    MemoryLimit,
    /// `AWS_SDK_UA_APP_ID`, then the profile's `sdk_ua_app_id`, which
    /// botocore reads when it builds each request's user agent and never
    /// rejects.
    AppId,
    /// `AWS_EXECUTION_ENV`, which the user agent reports.
    ExecutionEnv,
}
const S3_ENDPOINT_KEYS: [&str; 3] = [
    "addressing_style",
    "use_accelerate_endpoint",
    "use_dualstack_endpoint",
];
const MEMORY_LIMIT_VARIABLES: [(&str, u64); 2] = [
    ("AWS_CRT_S3_MEMORY_LIMIT_IN_MB", MEMORY_LIMIT_MIB),
    ("AWS_CRT_S3_MEMORY_LIMIT_IN_GIB", MEMORY_LIMIT_GIB),
];
const S3_ENDPOINT_SETTINGS: [Source; 3] = s3_sources(S3_ENDPOINT_KEYS);
const TRANSFER_SETTINGS: [Source; 11] = s3_sources(coerce::TRANSFER_KEYS);
const PROXY_SETTINGS: [Source; 6] = env_sources(crate::proxy::VARIABLES);
const MEMORY_LIMIT_SETTINGS: [Source; 2] =
    env_sources([MEMORY_LIMIT_VARIABLES[0].0, MEMORY_LIMIT_VARIABLES[1].0]);
impl Field {
    /// Every field, in declaration order, which is the order [`resolve`]
    /// reads them.
    pub const ALL: [Self; 12] = [
        Self::S3Endpoint,
        Self::MaxAttempts,
        Self::RequestChecksumCalculation,
        Self::ResponseChecksumValidation,
        Self::RetryMode,
        Self::TcpKeepalive,
        Self::CaBundle,
        Self::Proxy,
        Self::Transfer,
        Self::MemoryLimit,
        Self::AppId,
        Self::ExecutionEnv,
    ];
    /// The names the field's reader consults, in its precedence order: a
    /// variable, a key of the selected profile, or a key of its `s3` block,
    /// with botocore's chain as its variable then its key. The transfer keys,
    /// which do not override each other, are read in [`coerce::TRANSFER_KEYS`]
    /// order, and the proxy variables are [`crate::proxy::VARIABLES`].
    pub const fn settings(self) -> &'static [Source] {
        match self {
            Self::S3Endpoint => &S3_ENDPOINT_SETTINGS,
            Self::MaxAttempts => &[
                Source::Env("AWS_MAX_ATTEMPTS"),
                Source::Profile("max_attempts"),
            ],
            Self::RequestChecksumCalculation => &[
                Source::Env("AWS_REQUEST_CHECKSUM_CALCULATION"),
                Source::Profile("request_checksum_calculation"),
            ],
            Self::ResponseChecksumValidation => &[
                Source::Env("AWS_RESPONSE_CHECKSUM_VALIDATION"),
                Source::Profile("response_checksum_validation"),
            ],
            Self::RetryMode => &[Source::Env("AWS_RETRY_MODE"), Source::Profile("retry_mode")],
            Self::TcpKeepalive => &[Source::Profile("tcp_keepalive")],
            Self::CaBundle => &[
                Source::Env("AWS_CA_BUNDLE"),
                Source::Profile("ca_bundle"),
                Source::Env("REQUESTS_CA_BUNDLE"),
            ],
            Self::Proxy => &PROXY_SETTINGS,
            Self::Transfer => &TRANSFER_SETTINGS,
            Self::MemoryLimit => &MEMORY_LIMIT_SETTINGS,
            Self::AppId => &[
                Source::Env("AWS_SDK_UA_APP_ID"),
                Source::Profile("sdk_ua_app_id"),
            ],
            Self::ExecutionEnv => &[Source::Env("AWS_EXECUTION_ENV")],
        }
    }
    /// The reason a value of the field upstream rejects routes to Python
    /// with: the group the field's settings belong to.
    pub const fn reason(self) -> PythonReason {
        match self {
            Self::S3Endpoint => PythonReason::EndpointSetting,
            Self::MaxAttempts | Self::RetryMode => PythonReason::RetrySetting,
            Self::TcpKeepalive | Self::CaBundle | Self::Proxy => PythonReason::NetworkSetting,
            Self::Transfer
            | Self::MemoryLimit
            | Self::RequestChecksumCalculation
            | Self::ResponseChecksumValidation => PythonReason::TransferSetting,
            Self::AppId | Self::ExecutionEnv => PythonReason::UserAgentSetting,
        }
    }
}
const fn env_sources<const N: usize>(names: [&'static str; N]) -> [Source; N] {
    let mut sources = [Source::Default; N];
    let mut index = 0;
    while index < N {
        sources[index] = Source::Env(names[index]);
        index += 1;
    }
    sources
}
const fn s3_sources<const N: usize>(keys: [&'static str; N]) -> [Source; N] {
    let mut sources = [Source::Default; N];
    let mut index = 0;
    while index < N {
        sources[index] = Source::S3(keys[index]);
        index += 1;
    }
    sources
}
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Resolved<T> {
    pub value: T,
    pub source: Source,
}
impl<T> Resolved<T> {
    pub const fn new(value: T, source: Source) -> Self {
        Self { value, source }
    }
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum RetryMode {
    #[default]
    Standard,
    Adaptive,
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum ChecksumMode {
    #[default]
    WhenSupported,
    WhenRequired,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Persona {
    CrtPreferred,
    Tuned,
    NewlyEligible,
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum MemoryLimit {
    #[default]
    Tier,
    Override(u64),
}
/// The trust store TLS verifies peers against. The default is the bundle a
/// default build's payload embeds; resolution picks `Platform` when
/// [`Inputs::embedded_trust`] says the payload has none.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub enum Trust {
    /// The CRT's default trust store: the payload embeds no bundle.
    Platform,
    /// botocore's `cacert.pem` from the embedded payload
    /// ([`CACERT_ENTRY_NAME`]), the default of every Python route in the
    /// binary.
    #[default]
    Embedded,
    /// The PEM file at the path, as the user wrote it.
    File(PathBuf),
}
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct Platform {
    pub optimized: bool,
    pub recommended_gbps: Option<f64>,
}
/// The settings `s3 cp`'s CRT persona does not support and runs without, which
/// upstream names in one warning when it builds the transfer manager, before
/// any transfer starts (`warn_unsupported_settings`). The record collects them
/// while it resolves; `s3 cp` prints the warning once per command, straight to
/// stderr and whatever the output flags, and the command's status does not
/// change.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct IgnoredSettings {
    /// `max_bandwidth`, which the CRT client has no knob for.
    pub max_bandwidth: bool,
    /// `max_queue_size`, a classic transfer manager setting.
    pub max_queue_size: bool,
    /// `io_chunksize`, a classic transfer manager setting.
    pub io_chunksize: bool,
    /// `retry_mode = adaptive`, which the CRT client runs as its standard
    /// strategy.
    pub retry_mode_adaptive: bool,
    /// A `max_attempts` the CRT's standard strategy cannot express, which
    /// then keeps its own default.
    pub max_attempts: Option<u64>,
}
/// Upstream's warning, one line, with the settings in upstream's order: the
/// transfer keys in `UNSUPPORTED_OPTIONS` order, then the retry mode, then the
/// attempt count. Nothing is written when no setting is ignored.
impl std::fmt::Display for IgnoredSettings {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let mut values = Vec::new();
        for (set, name) in [
            (self.max_bandwidth, "max_bandwidth"),
            (self.max_queue_size, "max_queue_size"),
            (self.io_chunksize, "io_chunksize"),
            (self.retry_mode_adaptive, "retry_mode = adaptive"),
        ] {
            if set {
                values.push(name.to_owned());
            }
        }
        if let Some(attempts) = self.max_attempts {
            debug_assert!(crt_attempts(attempts).is_none());
            values.push(format!(
                "max_attempts = {attempts} (must be between {RETRY_ATTEMPTS_MIN} and \
                    {RETRY_ATTEMPTS_MAX})"
            ));
        }
        if values.is_empty() {
            return Ok(());
        }
        writeln!(
            f,
            "warning: The following configuration values are not supported by the 'crt' s3 \
                transfer client and will be ignored: {}.",
            values.join(", ")
        )
    }
}
#[derive(Debug, Clone, PartialEq)]
pub struct ClientConfig {
    pub command: Command,
    pub trust: Resolved<Trust>,
    pub signing: Resolved<bool>,
    pub retry_mode: Resolved<RetryMode>,
    pub max_attempts: Option<Resolved<u64>>,
    pub retry_attempts: Resolved<Option<u32>>,
    pub request_checksum: Resolved<ChecksumMode>,
    pub response_checksum: Resolved<ChecksumMode>,
    pub keep_alive: Resolved<bool>,
    pub connect_timeout_ms: Resolved<u32>,
    pub addressing_style: Resolved<AddressingStyle>,
    pub use_accelerate_endpoint: Resolved<bool>,
    pub use_dualstack_endpoint: Resolved<bool>,
    pub persona: Option<Resolved<Persona>>,
    pub target_gbps: Resolved<f64>,
    pub part_size: Resolved<u64>,
    pub multipart_threshold: Option<Resolved<u64>>,
    pub max_connections: Option<Resolved<u32>>,
    pub should_stream: Option<Resolved<bool>>,
    pub disk_throughput_gbps: Option<Resolved<f64>>,
    pub direct_io: Option<Resolved<bool>>,
    pub memory_limit: Resolved<MemoryLimit>,
    pub ignored: IgnoredSettings,
    /// The values the user agent reports as given, kept as bytes: one from
    /// the environment need not be Unicode.
    pub app_id: Option<Resolved<Vec<u8>>>,
    pub execution_env: Option<Resolved<Vec<u8>>>,
    pub endpoint_override: bool,
    pub agentic_callers: user_agent::Features,
    /// The provider the credential chain answers from, which `s3 ls`'s user
    /// agent names.
    pub credential_source: CredentialSource,
}
impl Default for ClientConfig {
    fn default() -> Self {
        Self::new(Command::Ls)
    }
}
impl ClientConfig {
    pub fn new(command: Command) -> Self {
        let cp = command.transfers();
        Self {
            command,
            trust: Resolved::default(),
            signing: Resolved::new(true, Source::Default),
            retry_mode: Resolved::default(),
            max_attempts: None,
            retry_attempts: Resolved::new(
                Some(ATTEMPTS_DEFAULT),
                if cp { Source::Persona } else { Source::Default },
            ),
            request_checksum: Resolved::default(),
            response_checksum: Resolved::default(),
            keep_alive: Resolved::default(),
            connect_timeout_ms: Resolved::new(CONNECT_TIMEOUT_MS_DEFAULT, Source::Default),
            addressing_style: Resolved::default(),
            use_accelerate_endpoint: Resolved::default(),
            use_dualstack_endpoint: Resolved::default(),
            persona: cp.then_some(Resolved::new(Persona::NewlyEligible, Source::Default)),
            target_gbps: Resolved::new(
                if cp {
                    TARGET_GBPS_UNTUNED
                } else {
                    TARGET_GBPS_LIST
                },
                if cp { Source::Persona } else { Source::Default },
            ),
            part_size: Resolved::new(
                if cp { PART_SIZE_DEFAULT } else { 0 },
                if cp { Source::Persona } else { Source::Default },
            ),
            multipart_threshold: cp
                .then_some(Resolved::new(MULTIPART_THRESHOLD_DEFAULT, Source::Persona)),
            max_connections: cp.then_some(Resolved::new(CONNECTIONS_DEFAULT, Source::Persona)),
            should_stream: None,
            disk_throughput_gbps: None,
            direct_io: None,
            memory_limit: Resolved::default(),
            ignored: IgnoredSettings::default(),
            app_id: None,
            execution_env: None,
            endpoint_override: false,
            agentic_callers: user_agent::Features::default(),
            credential_source: CredentialSource::DefaultChain,
        }
    }
    /// The `s3` block's endpoint rule inputs, which the S3 endpoint resolver
    /// combines with the endpoint settings `endpoint_config` reads.
    pub fn s3_block(&self) -> S3Block {
        S3Block {
            addressing_style: self.addressing_style.value,
            use_accelerate_endpoint: self.use_accelerate_endpoint.value,
            use_dualstack_endpoint: self.use_dualstack_endpoint.value,
        }
    }
    /// The CRT buffers unaligned parts even when direct file I/O was requested.
    pub fn download_direct_io(&self, page_size: u64) -> bool {
        self.direct_io.as_ref().is_some_and(|setting| setting.value)
            && page_size != 0
            && self.part_size.value.is_multiple_of(page_size)
    }
    pub fn memory_bytes(&self) -> u64 {
        match self.memory_limit.value {
            MemoryLimit::Tier => memory_limit_for_throughput(self.target_gbps.value),
            MemoryLimit::Override(bytes) => bytes,
        }
    }
    /// The attempts botocore's standard retries make per request of a botocore
    /// client: the configured count, or its default. `s3 cp` lists, heads a
    /// single download, and deletes a moved object with a botocore client
    /// whatever client runs its transfers, so its CRT persona makes those with
    /// the count it ignores for the transfers.
    pub fn botocore_attempts(&self) -> u64 {
        self.max_attempts
            .as_ref()
            .map_or(u64::from(ATTEMPTS_DEFAULT), |configured| configured.value)
    }
    /// The user agent's inputs for the record and whether the command
    /// uploads, besides the host facts and versions [`user_agent::render`]
    /// takes.
    pub fn user_agent_inputs(&self, uploads: bool) -> user_agent::Inputs<'_> {
        user_agent::Inputs {
            execution_env: self.execution_env.as_ref().map(|v| v.value.as_slice()),
            features: self.user_agent_features(uploads),
            retry_mode: self.retry_mode.value,
            app_id: self.app_id.as_ref().map(|v| v.value.as_slice()),
            extras: user_agent::Extras {
                installer: "other",
                prompt: "off",
                command: match self.command {
                    Command::Ls => "s3.ls",
                    Command::Cp => "s3.cp",
                    Command::Mv => "s3.mv",
                    Command::Rm => "s3.rm",
                    Command::Sync => "s3.sync",
                },
            },
        }
    }
    /// The feature ids upstream's requests of the same command register that
    /// native can know, besides the retry mode's: the checksum settings for
    /// both commands; for `s3 ls` the paginator and the credential provider;
    /// for the transfer commands the transfer, its CRT client, and CRC64NVME on
    /// uploads that calculate checksums; a configured endpoint; and the agentic
    /// callers. Whether the command uploads is the one fact the record cannot
    /// know.
    pub fn user_agent_features(&self, uploads: bool) -> user_agent::Features {
        use user_agent::Feature;
        let mut features = self.agentic_callers;
        if self.endpoint_override {
            features.insert(Feature::EndpointOverride);
        }
        features.insert(match self.request_checksum.value {
            ChecksumMode::WhenSupported => Feature::FlexibleChecksumsReqWhenSupported,
            ChecksumMode::WhenRequired => Feature::FlexibleChecksumsReqWhenRequired,
        });
        features.insert(match self.response_checksum.value {
            ChecksumMode::WhenSupported => Feature::FlexibleChecksumsResWhenSupported,
            ChecksumMode::WhenRequired => Feature::FlexibleChecksumsResWhenRequired,
        });
        match self.command {
            Command::Ls => {
                debug_assert!(!uploads, "a listing uploads nothing");
                features.insert(Feature::Paginator);
                features.extend(self.credential_features().iter().copied());
            }
            Command::Cp | Command::Mv | Command::Rm | Command::Sync => {
                features.extend(self.transfer_features(uploads).iter());
            }
        }
        features
    }
    fn credential_features(&self) -> &'static [user_agent::Feature] {
        use user_agent::Feature;
        if !self.signing.value {
            return &[];
        }
        match self.credential_source {
            CredentialSource::Environment => &[Feature::CredentialsEnvVars],
            CredentialSource::SharedProfile => &[Feature::CredentialsProfile],
            CredentialSource::Process => &[
                Feature::CredentialsProfileProcess,
                Feature::CredentialsProcess,
            ],
            CredentialSource::Container => &[Feature::CredentialsHttp],
            CredentialSource::DefaultChain => &[],
        }
    }
    fn transfer_features(&self, uploads: bool) -> user_agent::Features {
        use user_agent::Feature;
        let mut features = user_agent::Features::default();
        features.insert(Feature::S3Transfer);
        if let Some(persona) = &self.persona {
            features.insert(match persona.value {
                Persona::CrtPreferred => Feature::S3TransferCrtExplicit,
                Persona::Tuned | Persona::NewlyEligible => Feature::S3TransferCrtAuto,
            });
        }
        if uploads && self.request_checksum.value == ChecksumMode::WhenSupported {
            features.insert(Feature::FlexibleChecksumsReqCrc64);
        }
        features
    }
}
#[derive(Debug)]
pub struct Inputs<'a, E: EnvMap> {
    pub env: &'a E,
    pub files: &'a ParsedFiles,
    pub globals: &'a Globals,
    pub command: Command,
    pub directory: &'a Path,
    pub platform: Platform,
    /// Whether the payload embeds botocore's bundle ([`CACERT_ENTRY_NAME`]).
    /// The trust store nothing configures is that bundle when it does, and
    /// the CRT's platform store when it does not, as in a system-payload
    /// build, which packs only the endpoint models. The caller that holds the
    /// payload answers, so this crate never reads the payload.
    pub embedded_trust: bool,
}
impl<E: EnvMap> Inputs<'_, E> {
    fn profile(&self) -> &OsStr {
        aws_profile::select_or_default(self.env, self.globals.profile.as_deref())
    }
    fn property(&self, key: &str) -> Option<&str> {
        shared_config::profile_property(self.files, self.profile(), key)
    }
    fn nested(&self, key: &str) -> Option<&str> {
        shared_config::profile_nested_property(self.files, self.profile(), "s3", key)
    }
    fn first_os(&self, field: Field) -> Result<Option<Resolved<&OsStr>>, PythonReason> {
        for &source in field.settings() {
            let value = match source {
                Source::Env(name) => self.env.var_os(name),
                Source::Profile(key) => {
                    if shared_config::profile_property_is_block(self.files, self.profile(), key) {
                        return Err(field.reason());
                    }
                    self.property(key).map(OsStr::new)
                }
                Source::S3(key) => self.nested(key).map(OsStr::new),
                Source::Default | Source::Persona | Source::Flag(_) => None,
            };
            if let Some(value) = value {
                return Ok(Some(Resolved::new(value, source)));
            }
        }
        Ok(None)
    }
    fn first(&self, field: Field) -> Result<Option<Resolved<&str>>, PythonReason> {
        let Some(v) = self.first_os(field)? else {
            return Ok(None);
        };
        let value = v.value.to_str().ok_or(field.reason())?;
        Ok(Some(Resolved::new(value, v.source)))
    }
}
/// Resolve supported values before any native request or filesystem mutation.
pub fn resolve<E: EnvMap>(inputs: &Inputs<'_, E>) -> Result<ClientConfig, PythonReason> {
    resolve_with_probe(inputs, || inputs.platform)
}
/// Defers the platform probe until validated transfer settings require it.
/// Settings resolve in the order upstream raises their errors, so the first
/// value only Python can use names the reason: botocore's client converts and
/// validates the retry settings and the keepalive switch while it computes its
/// arguments, then the CA bundle when it builds its endpoint, all before the
/// transfer configuration is built. The field readers run in [`Field::ALL`]
/// order. `s3 cp`'s CRT persona then decides which retry settings its client
/// honors, and validates the bundle chain once more for its request serializer.
/// The bundle's contents come last, once the persona that decides who loads
/// them is known.
pub fn resolve_with_probe<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    probe: impl FnOnce() -> Platform,
) -> Result<ClientConfig, PythonReason> {
    let mut config = ClientConfig::new(inputs.command);
    config.credential_source =
        CredentialSource::select(inputs.env, inputs.files, inputs.globals.profile.as_deref());
    resolve_globals(&mut config, inputs.globals)?;
    resolve_endpoint(inputs, &mut config)?;
    resolve_max_attempts(inputs, &mut config)?;
    resolve_checksum(
        inputs,
        Field::RequestChecksumCalculation,
        &mut config.request_checksum,
    )?;
    resolve_checksum(
        inputs,
        Field::ResponseChecksumValidation,
        &mut config.response_checksum,
    )?;
    resolve_retry_mode(inputs, &mut config)?;
    resolve_keep_alive(inputs, &mut config)?;
    resolve_trust(inputs, &mut config)?;
    resolve_proxy(inputs)?;
    transfer::resolve(inputs, &mut config, probe)?;
    transfer::memory(inputs, &mut config)?;
    user_agent::resolve(inputs, &mut config)?;
    resolve_retry_attempts(&mut config)?;
    if inputs.command.transfers() {
        resolve_serializer_trust(inputs)?;
    }
    resolve_trust_contents(inputs, &config)?;
    Ok(config)
}
fn resolve_globals(config: &mut ClientConfig, globals: &Globals) -> Result<(), PythonReason> {
    if globals.no_sign_request {
        config.signing = Resolved::new(false, Source::Flag("--no-sign-request"));
    }
    let timeout_ms = connect_timeout_milliseconds(globals.connect_timeout)
        .ok_or(PythonReason::PythonOnlyGlobal)?;
    config.connect_timeout_ms = Resolved::new(
        timeout_ms,
        if globals.connect_timeout.is_some() {
            Source::Flag("--cli-connect-timeout")
        } else {
            Source::Default
        },
    );
    Ok(())
}
fn resolve_endpoint<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
) -> Result<(), PythonReason> {
    let reason = Field::S3Endpoint.reason();
    if inputs.property("s3").is_some() {
        return Err(reason);
    }
    let [style_key, accelerate_key, dualstack_key] = S3_ENDPOINT_KEYS;
    if let Some(value) = inputs.nested(style_key) {
        let style = match value {
            "auto" => AddressingStyle::Auto,
            "virtual" => AddressingStyle::Virtual,
            "path" => AddressingStyle::Path,
            _ => return Err(reason),
        };
        config.addressing_style = Resolved::new(style, Source::S3(style_key));
    }
    for (key, output) in [
        (accelerate_key, &mut config.use_accelerate_endpoint),
        (dualstack_key, &mut config.use_dualstack_endpoint),
    ] {
        if let Some(value) = inputs.nested(key) {
            *output = Resolved::new(coerce::boolean(value), Source::S3(key));
        }
    }
    Ok(())
}
fn resolve_max_attempts<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
) -> Result<(), PythonReason> {
    let Some(v) = inputs.first(Field::MaxAttempts)? else {
        return Ok(());
    };
    let attempts = coerce::integer(v.value)
        .and_then(|v| u64::try_from(v).ok())
        .filter(|v| *v > 0)
        .ok_or(PythonReason::RetrySetting)?;
    config.max_attempts = Some(Resolved::new(attempts, v.source));
    Ok(())
}
/// A checksum setting as botocore's client validates it for every command: the
/// value lowercased must be `when_supported` or `when_required`
/// (`_handle_checksum_config`), so any other value, an empty one, and a nested
/// block are Python's InvalidChecksumConfigError. An ASCII case fold is exact
/// here: the one non-ASCII character Python lowercases to an ASCII letter, the
/// Kelvin sign, folds to a `k`, which neither value holds.
fn resolve_checksum<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    field: Field,
    output: &mut Resolved<ChecksumMode>,
) -> Result<(), PythonReason> {
    if let Some(v) = inputs.first(field)? {
        let mode = checksum_mode(v.value).ok_or(field.reason())?;
        *output = Resolved::new(mode, v.source);
    }
    Ok(())
}
fn checksum_mode(value: &str) -> Option<ChecksumMode> {
    [
        ("when_supported", ChecksumMode::WhenSupported),
        ("when_required", ChecksumMode::WhenRequired),
    ]
    .into_iter()
    .find_map(|(name, mode)| value.eq_ignore_ascii_case(name).then_some(mode))
}
fn resolve_retry_mode<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
) -> Result<(), PythonReason> {
    let Some(v) = inputs.first(Field::RetryMode)? else {
        return Ok(());
    };
    let mode = match v.value {
        "standard" => RetryMode::Standard,
        "adaptive" => RetryMode::Adaptive,
        _ => return Err(PythonReason::RetrySetting),
    };
    config.retry_mode = Resolved::new(mode, v.source);
    Ok(())
}
/// TCP keepalive when the selected profile's `tcp_keepalive` is `true` in any
/// case (botocore's `_compute_socket_options`); no value is an error, and a
/// nested block, which botocore lowercases as a string, is Python's.
fn resolve_keep_alive<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
) -> Result<(), PythonReason> {
    if let Some(v) = inputs.first(Field::TcpKeepalive)? {
        config.keep_alive = Resolved::new(coerce::boolean(v.value), v.source);
    }
    Ok(())
}
fn resolve_trust<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
) -> Result<(), PythonReason> {
    config.trust = Resolved::new(default_trust(inputs.embedded_trust), Source::Default);
    let selected = if let Some(flag) = &inputs.globals.ca_bundle {
        Some(Resolved::new(OsStr::new(flag), Source::Flag("--ca-bundle")))
    } else {
        inputs.first_os(Field::CaBundle)?
    };
    let Some(value) = selected else {
        return Ok(());
    };
    if is_blank_path(value.value) {
        return Err(reject_blank(&value));
    }
    resolve_trust_file(inputs, config, &value)
}
const fn default_trust(embedded_trust: bool) -> Trust {
    if embedded_trust {
        Trust::Embedded
    } else {
        Trust::Platform
    }
}
fn resolve_trust_file<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
    value: &Resolved<&OsStr>,
) -> Result<(), PythonReason> {
    let reason = if matches!(value.source, Source::Flag(_)) {
        PythonReason::PythonOnlyGlobal
    } else {
        PythonReason::NetworkSetting
    };
    let bytes = value.value.as_encoded_bytes();
    if bytes.len() >= TRUST_PATH_BYTES_MAX || bytes.contains(&0) {
        return Err(reason);
    }
    if open_regular_file(inputs.directory, Path::new(value.value)).is_none() {
        return Err(reason);
    }
    config.trust = Resolved::new(Trust::File(PathBuf::from(value.value)), value.source);
    Ok(())
}
fn reject_blank(value: &Resolved<&OsStr>) -> PythonReason {
    debug_assert!(is_blank_path(value.value));
    if matches!(value.source, Source::Flag(_)) {
        PythonReason::PythonOnlyGlobal
    } else {
        PythonReason::NetworkSetting
    }
}
fn resolve_serializer_trust<E: EnvMap>(inputs: &Inputs<'_, E>) -> Result<(), PythonReason> {
    debug_assert!(inputs.command.transfers());
    if inputs.globals.ca_bundle.is_none() {
        return Ok(());
    }
    let Ok(Some(value)) = inputs.first_os(Field::CaBundle) else {
        return Ok(());
    };
    if !is_blank_path(value.value) {
        return Ok(());
    }
    Err(reject_blank(&value))
}
fn resolve_trust_contents<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &ClientConfig,
) -> Result<(), PythonReason> {
    let Trust::File(path) = &config.trust.value else {
        return Ok(());
    };
    let source = config.trust.source;
    debug_assert!(
        !matches!(source, Source::Default | Source::Persona),
        "a trust file always has a supplier"
    );
    debug_assert!(config.command == Command::Ls || config.persona.is_some());
    if let Some(persona) = &config.persona {
        if !crt_loads_trust(source) {
            return Err(PythonReason::NetworkSetting);
        }
        if persona.value == Persona::CrtPreferred {
            return Ok(());
        }
    }
    if holds_only_certificates(inputs.directory, path) {
        return Ok(());
    }
    Err(if matches!(source, Source::Flag(_)) {
        PythonReason::PythonOnlyGlobal
    } else {
        PythonReason::NetworkSetting
    })
}
fn crt_loads_trust(source: Source) -> bool {
    match source {
        Source::Flag(_) | Source::Profile(_) => true,
        Source::Env(name) => name == "AWS_CA_BUNDLE",
        Source::S3(_) | Source::Default | Source::Persona => false,
    }
}
fn holds_only_certificates(directory: &Path, path: &Path) -> bool {
    open_regular_file(directory, path).is_some_and(|file| {
        let reader = std::io::BufReader::with_capacity(ca_bundle::LINE_BUFFER_BYTES, file);
        ca_bundle::holds_only_certificates(reader)
    })
}
#[cfg(any(target_os = "linux", target_os = "android"))]
fn open_regular_file(directory: &Path, path: &Path) -> Option<std::fs::File> {
    use std::os::fd::{AsRawFd, FromRawFd, OwnedFd};
    use std::os::unix::ffi::OsStrExt;
    use std::os::unix::fs::OpenOptionsExt;
    let base = if path.is_absolute() {
        None
    } else {
        let mut options = std::fs::OpenOptions::new();
        options
            .read(true)
            .custom_flags(libc::O_PATH | libc::O_DIRECTORY);
        Some(options.open(directory).ok()?)
    };
    let at = base.as_ref().map_or(libc::AT_FDCWD, AsRawFd::as_raw_fd);
    let name = std::ffi::CString::new(path.as_os_str().as_bytes()).ok()?;
    let open = |flags: libc::c_int| {
        // SAFETY: `name` is a NUL-terminated string that outlives the call,
        // and `at` is `AT_FDCWD` or a descriptor `base` keeps open.
        let fd = unsafe { libc::openat(at, name.as_ptr(), flags | libc::O_CLOEXEC) };
        // SAFETY: a nonnegative `fd` is a new descriptor nothing else owns.
        (fd >= 0).then(|| std::fs::File::from(unsafe { OwnedFd::from_raw_fd(fd) }))
    };
    let probe = open(libc::O_PATH)?;
    if !probe.metadata().ok()?.is_file() {
        return None;
    }
    drop(probe);
    let file = open(libc::O_RDONLY | libc::O_NOCTTY | libc::O_NONBLOCK)?;
    file.metadata().ok()?.is_file().then_some(file)
}
#[cfg(not(any(target_os = "linux", target_os = "android")))]
fn open_regular_file(directory: &Path, path: &Path) -> Option<std::fs::File> {
    let mut options = std::fs::OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NONBLOCK);
    }
    let file = options.open(directory.join(path)).ok()?;
    file.metadata().ok()?.is_file().then_some(file)
}
fn is_blank_path(path: &OsStr) -> bool {
    path.to_str().is_some_and(is_blank)
}
/// Whether `text.strip()` leaves nothing in Python, whose `str.isspace()`
/// counts the separators U+001C to U+001F as spaces.
fn is_blank(text: &str) -> bool {
    text.chars().all(awscli_config::is_space)
}
fn resolve_retry_attempts(config: &mut ClientConfig) -> Result<(), PythonReason> {
    match config.persona.as_ref().map(|persona| persona.value) {
        None => resolve_botocore_attempts(config, Source::Default),
        Some(Persona::NewlyEligible) => resolve_botocore_attempts(config, Source::Persona),
        Some(Persona::CrtPreferred | Persona::Tuned) => {
            resolve_crt_persona_attempts(config);
            Ok(())
        }
    }
}
fn resolve_botocore_attempts(
    config: &mut ClientConfig,
    default_source: Source,
) -> Result<(), PythonReason> {
    if config.retry_mode.value == RetryMode::Adaptive {
        return Err(PythonReason::RetrySetting);
    }
    let Some(configured) = &config.max_attempts else {
        config.retry_attempts = Resolved::new(Some(ATTEMPTS_DEFAULT), default_source);
        return Ok(());
    };
    let attempts = crt_attempts(configured.value).ok_or(PythonReason::RetrySetting)?;
    config.retry_attempts = Resolved::new(Some(attempts), configured.source);
    Ok(())
}
fn resolve_crt_persona_attempts(config: &mut ClientConfig) {
    config.ignored.retry_mode_adaptive = config.retry_mode.value == RetryMode::Adaptive;
    let Some(configured) = &config.max_attempts else {
        config.retry_attempts = Resolved::new(None, Source::Default);
        return;
    };
    if let Some(attempts) = crt_attempts(configured.value) {
        config.retry_attempts = Resolved::new(Some(attempts), configured.source);
    } else {
        config.ignored.max_attempts = Some(configured.value);
        config.retry_attempts = Resolved::new(None, Source::Persona);
    }
}
fn crt_attempts(attempts: u64) -> Option<u32> {
    u32::try_from(attempts)
        .ok()
        .filter(|attempts| (RETRY_ATTEMPTS_MIN..=RETRY_ATTEMPTS_MAX).contains(attempts))
}
fn resolve_proxy<E: EnvMap>(inputs: &Inputs<'_, E>) -> Result<(), PythonReason> {
    let proxy = crate::proxy::Environment::from_map(inputs.env);
    if proxy.requires_python() {
        return Err(PythonReason::NetworkSetting);
    }
    if proxy.has_bypass_list()
        && !crate::endpoint_config::configured_endpoints_ascii(
            inputs.env,
            inputs.files,
            "s3",
            inputs.globals.endpoint_url.as_deref(),
            inputs.globals.profile.as_deref(),
        )
    {
        return Err(PythonReason::NetworkSetting);
    }
    Ok(())
}
/// `--cli-connect-timeout` as the CRT's `connect_timeout_ms`, or `None` for a
/// value botocore rejects: negative seconds (urllib3's "Attempted to set
/// connect timeout to ...") and seconds past `CONNECT_TIMEOUT_SECONDS_MAX`.
/// Unset is botocore's 60 s, which upstream gives its CRT client as well
/// (factory.py `_to_crt_connect_timeout_ms`); an explicit 0, botocore's "no
/// timeout", is the longest wait the CRT can express, which longer timeouts
/// saturate at.
pub fn connect_timeout_milliseconds(seconds: Option<i64>) -> Option<u32> {
    match seconds {
        None => Some(CONNECT_TIMEOUT_MS_DEFAULT),
        Some(0) => Some(u32::MAX),
        Some(seconds) if (1..=CONNECT_TIMEOUT_SECONDS_MAX).contains(&seconds) => {
            Some(u32::try_from(seconds * 1000).unwrap_or(u32::MAX))
        }
        _ => None,
    }
}
const fn part_size_max(pool_bytes: u64) -> u64 {
    let half = pool_bytes / 2;
    if half < PART_SIZE_MAX {
        half
    } else {
        PART_SIZE_MAX
    }
}
/// The buffer-pool size aws-c-s3 picks for a throughput target when no limit is
/// configured: the 64-bit tiers of `s_get_default_mem_limit_from_throughput`
/// (s3_client.c). cli-core links no CRT, so the table is copied here, and crt's
/// `memory_limits_match_the_linked_crt_at_every_tier_boundary` test compares it
/// with `aws_s3_default_memory_limit_for_throughput` around each boundary, so a
/// CRT pin that retunes the tiers fails that test. A target of zero or less
/// maps to 2 GiB here, where the CRT would consult its platform detection.
pub fn memory_limit_for_throughput(gbps: f64) -> u64 {
    if gbps >= 200.0 {
        24 << 30
    } else if gbps >= 100.0 {
        16 << 30
    } else if gbps >= 75.0 {
        8 << 30
    } else if gbps >= 25.0 {
        4 << 30
    } else if gbps >= 10.0 || gbps <= 0.0 {
        2 << 30
    } else if gbps >= 5.0 {
        512 << 20
    } else {
        256 << 20
    }
}
#[cfg(test)]
mod tests;
