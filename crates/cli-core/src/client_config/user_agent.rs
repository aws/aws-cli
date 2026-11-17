//! Deterministic native user-agent assembly with the Rust implementation identity.
//!
//! The header reproduces botocore's `UserAgentString.to_string` component
//! sequence followed by the session extras the AWS CLI appends, so both legs of
//! the binary send the same shape. [`render`] is pure: it borrows every input,
//! and the host facts come from the separate [`host`] and [`distribution`]
//! helpers, so tests pin every input. The CRT appends its own
//! `CRTS3NativeClient/<version> platform/<type>` suffix to every meta request;
//! that suffix is not part of this module's output.
//!
//! What native leaves out, because it cannot know it: the `lang/python` and
//! `md/pyimpl` components (native sends `lang/rust`), the telemetry session id
//! `sid/`, which needs upstream's session database, and the credential-provider
//! feature ids of the providers admission sends to Python, or of the instance
//! provider, which answers after the record is resolved (`0`, and the other
//! `CREDENTIALS_*` codes). The `m/` list is one per command, so the
//! ListObjectsV2 pages of a recursive `s3 cp` omit the paginator id upstream's
//! listing requests carry.
use super::*;

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Host {
    pub system: String,
    pub release: String,
    pub machine: String,
}
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Distribution {
    pub id: String,
    pub version_major: String,
}
#[derive(Debug, Clone, Copy)]
pub struct Versions<'a> {
    pub cli: &'a str,
    pub crt: &'a str,
    pub rust: &'a str,
}
const FEATURES_BYTES_MAX: usize = 1024;
/// Bytes of os-release read in one bounded read. Distribution files are a few
/// hundred bytes (Ubuntu's is about 400), so one page leaves ample headroom.
pub const OS_RELEASE_BYTES_MAX: usize = 4096;
/// The most bytes `AWS_EXECUTION_ENV` and the app id take together. Upstream
/// sends both whole, and sanitizing writes one byte per code point, never more
/// than the value's own bytes. 2 KiB is forty times the app id length botocore
/// warns past (`_compute_user_agent_appid_config`); the router sends longer
/// values to the fallback, which sends them whole.
pub const SUPPLIED_BYTES_MAX: usize = 2048;

/// Feature ids the native commands can legitimately claim, each mapped to the
/// code botocore registers for the same behavior
/// (`_USERAGENT_FEATURE_MAPPINGS`). Declaration order follows that table and is
/// the order of the `m/` list; upstream joins a Python set, whose order is
/// unspecified.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Feature {
    /// `PAGINATOR` (C): `s3 ls` pages ListObjectsV2 and ListBuckets (`PageIterator`).
    Paginator,
    /// `RETRY_MODE_STANDARD` (E): the client's retry mode (`_register_retries`).
    /// [`render`] derives it from [`Inputs::retry_mode`].
    RetryModeStandard,
    /// `RETRY_MODE_ADAPTIVE` (F): as `RetryModeStandard`.
    RetryModeAdaptive,
    /// `S3_TRANSFER` (G): a transfer command (`S3TransferCommand._run_main`
    /// and both transfer managers' `_submit_transfer`).
    S3Transfer,
    /// `ENDPOINT_OVERRIDE` (N): a configured endpoint URL (`compute_client_args`).
    EndpointOverride,
    /// `FLEXIBLE_CHECKSUMS_REQ_CRC64` (W): a CRC64NVME upload checksum
    /// (`_register_checksum_algorithm_feature_id`).
    FlexibleChecksumsReqCrc64,
    /// `FLEXIBLE_CHECKSUMS_REQ_WHEN_SUPPORTED` (Z): request checksum setting
    /// (`_register_checksum_config_feature_ids`).
    FlexibleChecksumsReqWhenSupported,
    /// `FLEXIBLE_CHECKSUMS_REQ_WHEN_REQUIRED` (a): request checksum setting
    /// (`_register_checksum_config_feature_ids`).
    FlexibleChecksumsReqWhenRequired,
    /// `FLEXIBLE_CHECKSUMS_RES_WHEN_SUPPORTED` (b): response validation setting
    /// (`_register_checksum_config_feature_ids`).
    FlexibleChecksumsResWhenSupported,
    /// `FLEXIBLE_CHECKSUMS_RES_WHEN_REQUIRED` (c): response validation setting
    /// (`_register_checksum_config_feature_ids`).
    FlexibleChecksumsResWhenRequired,
    /// `CREDENTIALS_ENV_VARS` (g): the environment provider answered
    /// (credentials.py `EnvProvider.load`).
    CredentialsEnvVars,
    /// `CREDENTIALS_PROFILE_PROCESS` (v): the profile names a
    /// `credential_process` (credentials.py `ProcessProvider.load`).
    CredentialsProfileProcess,
    /// `CREDENTIALS_PROCESS` (w): that process answered.
    CredentialsProcess,
    /// `CREDENTIALS_PROFILE` (n): a profile's static keys in either shared
    /// file answered (`SharedCredentialProvider`, `ConfigProvider`).
    CredentialsProfile,
    /// `CREDENTIALS_HTTP` (z): the container provider answered
    /// (credentials.py `ContainerProvider`).
    CredentialsHttp,
    /// `AGENTIC_CALLER_CLAUDE_CODE` (AN): see [`agentic_caller_features`].
    AgenticCallerClaudeCode,
    /// `AGENTIC_CALLER_GEMINI_CLI` (AO): see [`agentic_caller_features`].
    AgenticCallerGeminiCli,
    /// `AGENTIC_CALLER_CODEX` (AP): see [`agentic_caller_features`].
    AgenticCallerCodex,
    /// `AGENTIC_CALLER_KIRO` (AQ): see [`agentic_caller_features`].
    AgenticCallerKiro,
    /// `AGENTIC_CALLER_OPENCODE` (AR): see [`agentic_caller_features`].
    AgenticCallerOpencode,
    /// `AGENTIC_CALLER_ANTIGRAVITY` (AS): see [`agentic_caller_features`].
    AgenticCallerAntigravity,
    /// `AGENTIC_CALLER_AMP` (AT): see [`agentic_caller_features`].
    AgenticCallerAmp,
    /// `AGENTIC_CALLER_PI` (AU): see [`agentic_caller_features`].
    AgenticCallerPi,
    /// `AGENTIC_CALLER_COPILOT_CLI` (AV): see [`agentic_caller_features`].
    AgenticCallerCopilotCli,
    /// `AGENTIC_CALLER_CURSOR` (AW): see [`agentic_caller_features`].
    AgenticCallerCursor,
    /// `S3_TRANSFER_CRT_EXPLICIT` (Ae): `preferred_transfer_client = crt`
    /// (`_register_transfer_client_feature_id`).
    S3TransferCrtExplicit,
    /// `S3_TRANSFER_CRT_AUTO` (Ag): `auto` resolved to the CRT
    /// (`_register_transfer_client_feature_id`).
    S3TransferCrtAuto,
}
impl Feature {
    /// Every feature in declaration order, which is the `m/` order.
    pub const ALL: [Self; 27] = [
        Self::Paginator,
        Self::RetryModeStandard,
        Self::RetryModeAdaptive,
        Self::S3Transfer,
        Self::EndpointOverride,
        Self::FlexibleChecksumsReqCrc64,
        Self::FlexibleChecksumsReqWhenSupported,
        Self::FlexibleChecksumsReqWhenRequired,
        Self::FlexibleChecksumsResWhenSupported,
        Self::FlexibleChecksumsResWhenRequired,
        Self::CredentialsEnvVars,
        Self::CredentialsProfileProcess,
        Self::CredentialsProcess,
        Self::CredentialsProfile,
        Self::CredentialsHttp,
        Self::AgenticCallerClaudeCode,
        Self::AgenticCallerGeminiCli,
        Self::AgenticCallerCodex,
        Self::AgenticCallerKiro,
        Self::AgenticCallerOpencode,
        Self::AgenticCallerAntigravity,
        Self::AgenticCallerAmp,
        Self::AgenticCallerPi,
        Self::AgenticCallerCopilotCli,
        Self::AgenticCallerCursor,
        Self::S3TransferCrtExplicit,
        Self::S3TransferCrtAuto,
    ];
    /// The upstream code for the feature, as it appears in the `m/` component.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Paginator => "C",
            Self::RetryModeStandard => "E",
            Self::RetryModeAdaptive => "F",
            Self::S3Transfer => "G",
            Self::EndpointOverride => "N",
            Self::FlexibleChecksumsReqCrc64 => "W",
            Self::FlexibleChecksumsReqWhenSupported => "Z",
            Self::FlexibleChecksumsReqWhenRequired => "a",
            Self::FlexibleChecksumsResWhenSupported => "b",
            Self::FlexibleChecksumsResWhenRequired => "c",
            Self::CredentialsEnvVars => "g",
            Self::CredentialsProfileProcess => "v",
            Self::CredentialsProcess => "w",
            Self::CredentialsProfile => "n",
            Self::CredentialsHttp => "z",
            Self::AgenticCallerClaudeCode => "AN",
            Self::AgenticCallerGeminiCli => "AO",
            Self::AgenticCallerCodex => "AP",
            Self::AgenticCallerKiro => "AQ",
            Self::AgenticCallerOpencode => "AR",
            Self::AgenticCallerAntigravity => "AS",
            Self::AgenticCallerAmp => "AT",
            Self::AgenticCallerPi => "AU",
            Self::AgenticCallerCopilotCli => "AV",
            Self::AgenticCallerCursor => "AW",
            Self::S3TransferCrtExplicit => "Ae",
            Self::S3TransferCrtAuto => "Ag",
        }
    }
    const fn bit(self) -> u32 {
        1 << self as u32
    }
}
/// Feature pairs upstream never registers together: one retry mode per client,
/// one value per checksum setting, one transfer client per command, and one
/// credential provider per session (credentials.py `CredentialResolver`).
pub const EXCLUSIVE_PAIRS: [[Feature; 2]; 10] = [
    [Feature::RetryModeStandard, Feature::RetryModeAdaptive],
    [
        Feature::FlexibleChecksumsReqWhenSupported,
        Feature::FlexibleChecksumsReqWhenRequired,
    ],
    [
        Feature::FlexibleChecksumsResWhenSupported,
        Feature::FlexibleChecksumsResWhenRequired,
    ],
    [Feature::S3TransferCrtExplicit, Feature::S3TransferCrtAuto],
    [Feature::CredentialsEnvVars, Feature::CredentialsProfile],
    [Feature::CredentialsEnvVars, Feature::CredentialsProcess],
    [Feature::CredentialsProfile, Feature::CredentialsProcess],
    [Feature::CredentialsEnvVars, Feature::CredentialsHttp],
    [Feature::CredentialsProfile, Feature::CredentialsHttp],
    [Feature::CredentialsProcess, Feature::CredentialsHttp],
];
const _: () = {
    let mut index = 0;
    while index < Feature::ALL.len() {
        assert!(Feature::ALL[index] as usize == index);
        index += 1;
    }
    assert!(Feature::ALL.len() == Feature::S3TransferCrtAuto as usize + 1);
    assert!(Feature::ALL.len() <= u32::BITS as usize);
    assert!(codes_are_unique_tokens());
    assert!(features_bytes_all() <= FEATURES_BYTES_MAX);
};
const fn codes_are_unique_tokens() -> bool {
    let mut index = 0;
    while index < Feature::ALL.len() {
        let code = Feature::ALL[index].code().as_bytes();
        if !is_alphanumeric_token(code) {
            return false;
        }
        let mut other = index + 1;
        while other < Feature::ALL.len() {
            if same_bytes(code, Feature::ALL[other].code().as_bytes()) {
                return false;
            }
            other += 1;
        }
        index += 1;
    }
    true
}
const fn is_alphanumeric_token(code: &[u8]) -> bool {
    let mut index = 0;
    while index < code.len() {
        if !code[index].is_ascii_alphanumeric() {
            return false;
        }
        index += 1;
    }
    !code.is_empty()
}
const fn same_bytes(left: &[u8], right: &[u8]) -> bool {
    if left.len() != right.len() {
        return false;
    }
    let mut index = 0;
    while index < left.len() {
        if left[index] != right[index] {
            return false;
        }
        index += 1;
    }
    true
}
const fn features_bytes_all() -> usize {
    let mut bytes = "m/".len();
    let mut index = 0;
    while index < Feature::ALL.len() {
        bytes += Feature::ALL[index].code().len() + 1;
        index += 1;
    }
    bytes
}
/// A set of features for the `m/` component, iterated in declaration order.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Features(u32);
impl Features {
    pub fn insert(&mut self, feature: Feature) {
        self.0 |= feature.bit();
    }
    pub fn remove(&mut self, feature: Feature) {
        self.0 &= !feature.bit();
    }
    pub fn contains(self, feature: Feature) -> bool {
        self.0 & feature.bit() != 0
    }
    /// The features in the set, in declaration order.
    pub fn iter(self) -> impl Iterator<Item = Feature> {
        Feature::ALL
            .into_iter()
            .filter(move |feature| self.contains(*feature))
    }
    /// The codes of the features in the set, in declaration order.
    pub fn codes(self) -> impl Iterator<Item = &'static str> {
        self.iter().map(Feature::code)
    }
}
impl Extend<Feature> for Features {
    fn extend<I: IntoIterator<Item = Feature>>(&mut self, features: I) {
        for feature in features {
            self.insert(feature);
        }
    }
}
impl FromIterator<Feature> for Features {
    fn from_iter<I: IntoIterator<Item = Feature>>(features: I) -> Self {
        let mut set = Self::default();
        set.extend(features);
        set
    }
}

struct AgenticCaller {
    variable: &'static str,
    feature: Feature,
    value: Option<&'static str>,
}
const AGENTIC_CALLERS: [AgenticCaller; 10] = [
    agentic("CLAUDECODE", Feature::AgenticCallerClaudeCode, Some("1")),
    agentic("GEMINI_CLI", Feature::AgenticCallerGeminiCli, Some("1")),
    agentic("CODEX_THREAD_ID", Feature::AgenticCallerCodex, None),
    agentic("KIRO_SESSION_ID", Feature::AgenticCallerKiro, None),
    agentic("OPENCODE", Feature::AgenticCallerOpencode, None),
    agentic("ANTIGRAVITY_AGENT", Feature::AgenticCallerAntigravity, None),
    agentic("AMP_CURRENT_THREAD_ID", Feature::AgenticCallerAmp, None),
    agentic("PI_CODING_AGENT", Feature::AgenticCallerPi, Some("true")),
    agentic("COPILOT_CLI", Feature::AgenticCallerCopilotCli, Some("1")),
    agentic("CURSOR_AGENT", Feature::AgenticCallerCursor, Some("1")),
];
const fn agentic(
    variable: &'static str,
    feature: Feature,
    value: Option<&'static str>,
) -> AgenticCaller {
    AgenticCaller {
        variable,
        feature,
        value,
    }
}
/// The agentic-caller features botocore registers from the environment on every
/// header build (`_register_agentic_caller_env_features`). A value that is not
/// Unicode is present and matches only an any-value variable.
pub fn agentic_caller_features<E: EnvMap>(env: &E) -> Features {
    AGENTIC_CALLERS
        .iter()
        .filter(|caller| {
            env.var_os(caller.variable).is_some_and(|value| {
                caller
                    .value
                    .map_or(!value.is_empty(), |expected| value == expected)
            })
        })
        .map(|caller| caller.feature)
        .collect()
}

/// The session-level components the AWS CLI appends to `user_agent_extra`.
/// Native sends no `sid/` telemetry session id: upstream inserts one right
/// after the installer, from a session database native does not keep, and omits
/// it under `AWS_CLI_SESSION_ID_DISABLED`. The distribution, which upstream
/// appends after the installer, is [`render`]'s own argument.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Extras {
    /// `md/installer#<source>`: `get_distribution_source()`, which is `other`
    /// when no install metadata file exists.
    pub installer: &'static str,
    /// `md/prompt#<mode>`: the mode the driver runs under. Native runs only
    /// when the resolved auto-prompt mode is `off` or `on-partial`, and
    /// upstream's first `on-partial` pass reports `off` too, so native always
    /// sends `off`.
    pub prompt: &'static str,
    /// `md/command#<lineage>`: the dotted command lineage, such as `s3.cp`
    /// (`add_command_lineage_to_user_agent_extra`).
    pub command: &'static str,
}
/// Everything the header states besides the host facts, the distribution and
/// the versions, borrowed for one assembly.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Inputs<'a> {
    /// `AWS_EXECUTION_ENV`; `None` or empty omits `exec-env/`.
    pub execution_env: Option<&'a [u8]>,
    /// The `m/` features besides the retry mode's, which [`render`] adds.
    pub features: Features,
    /// The resolved retry mode for `cfg/retry-mode#` and its feature id.
    pub retry_mode: RetryMode,
    /// `user_agent_appid`, from `AWS_SDK_UA_APP_ID` or the profile's
    /// `sdk_ua_app_id`; `None` or empty omits `app/`.
    pub app_id: Option<&'a [u8]>,
    /// The session-level components that end the header.
    pub extras: Extras,
}

pub(super) fn resolve<E: EnvMap>(
    inputs: &super::Inputs<'_, E>,
    config: &mut ClientConfig,
) -> Result<(), PythonReason> {
    let bytes = |v: Resolved<&OsStr>| Resolved::new(v.value.as_encoded_bytes().to_vec(), v.source);
    config.app_id = inputs.first_os(Field::AppId)?.map(bytes);
    config.execution_env = inputs.first_os(Field::ExecutionEnv)?.map(bytes);
    let supplied = config.app_id.as_ref().map_or(0, |v| v.value.len())
        + config.execution_env.as_ref().map_or(0, |v| v.value.len());
    if supplied > SUPPLIED_BYTES_MAX {
        return Err(PythonReason::UserAgentSetting);
    }
    config.endpoint_override = crate::endpoint_config::endpoint_configured(
        inputs.env,
        inputs.files,
        "s3",
        inputs.globals.endpoint_url.as_deref(),
        inputs.globals.profile.as_deref(),
    );
    config.agentic_callers = agentic_caller_features(inputs.env);
    Ok(())
}
pub fn sanitize(value: &str, allow_hash: bool) -> String {
    sanitize_bytes(value.as_bytes(), allow_hash)
}
/// [`sanitize`] for bytes that need not be UTF-8. Python decodes each byte
/// of an invalid sequence to its own surrogate escape, so each byte becomes
/// one `-`, as each disallowed code point does.
pub fn sanitize_bytes(value: &[u8], allow_hash: bool) -> String {
    value
        .utf8_chunks()
        .flat_map(|chunk| {
            let valid = chunk.valid().chars().map(move |c| {
                if c.is_ascii_alphanumeric()
                    || "!$%&'*+-.^_`|~,".contains(c)
                    || (allow_hash && c == '#')
                {
                    c
                } else {
                    '-'
                }
            });
            valid.chain(std::iter::repeat_n('-', chunk.invalid().len()))
        })
        .collect()
}
/// The header every request of `config`'s command sends ahead of the CRT's
/// own suffix: [`render`] of [`ClientConfig::user_agent_inputs`]. The caller
/// reads the host facts once, with [`host`] and [`distribution`].
pub fn assemble(
    config: &ClientConfig,
    host: &Host,
    distribution: Option<&Distribution>,
    versions: Versions<'_>,
    uploads: bool,
) -> String {
    render(
        &config.user_agent_inputs(uploads),
        host,
        distribution,
        versions,
    )
}
/// The user-agent header for `inputs`. Component order follows
/// `UserAgentString.to_string`, then the session extras in the order the AWS
/// CLI appends them.
pub fn render(
    inputs: &Inputs<'_>,
    host: &Host,
    distribution: Option<&Distribution>,
    versions: Versions<'_>,
) -> String {
    let features = features_with_retry_mode(inputs.features, inputs.retry_mode);
    let mut parts = vec![
        format!("aws-cli/{}", sanitize(versions.cli, false)),
        format!("md/awscrt#{}", sanitize(versions.crt, true)),
        "ua/2.1".into(),
    ];
    append_host(&mut parts, host);
    parts.push(component("lang", "rust", Some(versions.rust)));
    if let Some(execution_env) = non_empty(inputs.execution_env) {
        parts.push(format!("exec-env/{}", sanitize_bytes(execution_env, false)));
    }
    parts.push(format!(
        "m/{}",
        features.codes().collect::<Vec<_>>().join(",")
    ));
    parts.push(component(
        "cfg",
        "retry-mode",
        Some(retry_mode_name(inputs.retry_mode)),
    ));
    if let Some(app_id) = non_empty(inputs.app_id) {
        parts.push(format!("app/{}", sanitize_bytes(app_id, true)));
    }
    append_extras(&mut parts, &inputs.extras, distribution);
    parts.join(" ")
}
fn features_with_retry_mode(features: Features, retry_mode: RetryMode) -> Features {
    debug_assert!(!features.contains(Feature::RetryModeStandard));
    debug_assert!(!features.contains(Feature::RetryModeAdaptive));
    let mut all = features;
    all.insert(match retry_mode {
        RetryMode::Standard => Feature::RetryModeStandard,
        RetryMode::Adaptive => Feature::RetryModeAdaptive,
    });
    debug_assert!(
        EXCLUSIVE_PAIRS
            .iter()
            .all(|[first, second]| !(all.contains(*first) && all.contains(*second)))
    );
    all
}
fn retry_mode_name(retry_mode: RetryMode) -> &'static str {
    match retry_mode {
        RetryMode::Standard => "standard",
        RetryMode::Adaptive => "adaptive",
    }
}
fn non_empty(value: Option<&[u8]>) -> Option<&[u8]> {
    value.filter(|value| !value.is_empty())
}
fn append_extras(parts: &mut Vec<String>, extras: &Extras, distribution: Option<&Distribution>) {
    parts.push(component("md", "installer", Some(extras.installer)));
    if let Some(distro) = distribution.filter(|d| !d.id.is_empty() || !d.version_major.is_empty()) {
        let version = if distro.version_major.is_empty() {
            String::new()
        } else {
            format!(".{}", sanitize(&distro.version_major, true))
        };
        parts.push(format!(
            "md/distrib#{}{version}",
            sanitize(&distro.id, true)
        ));
    }
    parts.push(component("md", "prompt", Some(extras.prompt)));
    parts.push(component("md", "command", Some(extras.command)));
}
fn append_host(parts: &mut Vec<String>, host: &Host) {
    let system = host.system.to_ascii_lowercase();
    let family = match system.as_str() {
        "darwin" => Some("macos"),
        "linux" | "windows" | "macos" | "android" | "ios" | "watchos" | "tvos" | "other" => {
            Some(system.as_str())
        }
        _ => None,
    };
    if let Some(family) = family {
        parts.push(component("os", family, Some(&host.release)));
    } else {
        parts.push(component("os", "other", None));
        parts.push(component("md", &host.system, Some(&host.release)));
    }
    if !host.machine.is_empty() {
        parts.push(component(
            "md",
            "arch",
            Some(&host.machine.to_ascii_lowercase()),
        ));
    }
}
fn component(prefix: &str, name: &str, value: Option<&str>) -> String {
    let name = sanitize(name, false);
    match value.filter(|v| !v.is_empty()) {
        Some(v) => format!("{prefix}/{name}#{}", sanitize(v, true)),
        None => format!("{prefix}/{name}"),
    }
}
#[cfg(unix)]
pub fn host() -> Host {
    let mut info = std::mem::MaybeUninit::<libc::utsname>::zeroed();
    // SAFETY: the pointer covers a writable utsname; on failure it is never read.
    if unsafe { libc::uname(info.as_mut_ptr()) } != 0 {
        return Host::default();
    }
    // SAFETY: every byte was zeroed, and the successful call above wrote each
    // field's string and its terminating NUL.
    let info = unsafe { info.assume_init() };
    let text = |value: &[libc::c_char]| {
        // SAFETY: utsname fields are terminated C strings and remain live for this conversion.
        unsafe { std::ffi::CStr::from_ptr(value.as_ptr()) }
            .to_string_lossy()
            .into_owned()
    };
    Host {
        system: text(&info.sysname),
        release: text(&info.release),
        machine: text(&info.machine),
    }
}
#[cfg(any(windows, test))]
mod windows_host;
#[cfg(windows)]
pub fn host() -> Host {
    windows_host::host()
}
pub fn distribution() -> Option<Distribution> {
    if !cfg!(target_os = "linux") {
        return None;
    }
    Some(read_distribution(&[
        Path::new("/etc/os-release"),
        Path::new("/usr/lib/os-release"),
    ]))
}
/// The distribution the first regular file of `paths` describes, as `distro`
/// reads os-release: a path that is not a regular file once symlinks are
/// followed is skipped (`os.path.isfile`), a file that cannot be read is
/// `unknown` (`_get_linux_distribution`), and with no file the id is empty and
/// the component is omitted, since the sources `distro` falls back to are not
/// ported.
pub fn read_distribution(paths: &[&Path]) -> Distribution {
    use std::io::Read;
    for path in paths {
        if !std::fs::metadata(path).is_ok_and(|m| m.is_file()) {
            continue;
        }
        let mut options = std::fs::OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.custom_flags(libc::O_NONBLOCK);
        }
        let mut bytes = Vec::new();
        let loaded = options.open(path).and_then(|file| {
            file.take(OS_RELEASE_BYTES_MAX as u64)
                .read_to_end(&mut bytes)
        });
        if loaded.is_err() {
            return unknown_distribution();
        }
        let extent = if bytes.len() == OS_RELEASE_BYTES_MAX {
            bytes.truncate(bytes.iter().rposition(|byte| *byte == b'\n').unwrap_or(0));
            OsReleaseExtent::Truncated
        } else {
            OsReleaseExtent::Whole
        };
        return match std::str::from_utf8(&bytes) {
            Ok(text) => parse_os_release(text, extent),
            Err(_) => unknown_distribution(),
        };
    }
    Distribution::default()
}
/// How much of the os-release file [`parse_os_release`] is given.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OsReleaseExtent {
    /// The whole file, where a quote or escape left open at the end is
    /// malformed.
    Whole,
    /// The complete lines before the bounded read stopped, where a quote or
    /// escape left open at the end may close past the cut.
    Truncated,
}
/// `distro.id()` and `distro.major_version()` from os-release content, read as
/// `distro` reads the file (`_parse_os_release_content`). Python's universal
/// newlines turn `\r\n` and `\r` into `\n`; `shlex` in POSIX mode with
/// `whitespace_split` tokenizes the whole content, so a quoted value may span
/// lines, a backslash escapes the next character (inside double quotes only `"`
/// and `\`), and a `#` outside quotes, at a token's start or inside a word,
/// comments out the rest of the line; and each token holding `=` assigns the
/// value after its first `=` to its lowercased key, the last assignment
/// winning. A quote or escape the content leaves open raises in `shlex`, which
/// the CLI reports as `unknown` (`_get_linux_distribution`), as it does content
/// that is not UTF-8. `id()` lowercases the `ID` value, turns blanks into
/// underscores and applies `NORMALIZED_OS_ID`; the major version is the leading
/// digit run of `VERSION_ID`. Simplifications, none of which changes the result
/// for an os-release that sets both: ASCII digits only, and no fallback
/// sources: `distro` reads the version from `PRETTY_NAME`, lsb_release, the
/// distro-release file and the kernel release when `VERSION_ID` is empty, and
/// the id from lsb_release and the distro-release file when `ID` is. A
/// truncated text instead ends before such a token, keeping the assignments
/// ahead of it.
pub fn parse_os_release(text: &str, extent: OsReleaseExtent) -> Distribution {
    let (tokens, raised) = shlex_split(&text.replace("\r\n", "\n").replace('\r', "\n"));
    if raised && extent == OsReleaseExtent::Whole {
        return unknown_distribution();
    }
    let (mut id, mut version) = ("", "");
    for (key, value) in tokens.iter().filter_map(|token| token.split_once('=')) {
        if key.eq_ignore_ascii_case("id") {
            id = value;
        }
        if key.eq_ignore_ascii_case("version_id") {
            version = value;
        }
    }
    let id = id.to_lowercase().replace(' ', "_");
    Distribution {
        id: match id.as_str() {
            "ol" => "oracle".into(),
            "opensuse-leap" => "opensuse".into(),
            _ => id,
        },
        version_major: version.chars().take_while(char::is_ascii_digit).collect(),
    }
}
fn unknown_distribution() -> Distribution {
    Distribution {
        id: "unknown".into(),
        version_major: String::new(),
    }
}
fn shlex_split(text: &str) -> (Vec<String>, bool) {
    let mut lexer = Shlex {
        chars: text.chars(),
    };
    let mut tokens = Vec::new();
    while let Some(next) = lexer.token() {
        let Some(token) = next else {
            return (tokens, false);
        };
        tokens.push(token);
    }
    (tokens, true)
}
struct Shlex<'a> {
    chars: std::str::Chars<'a>,
}
#[derive(Debug, Clone, Copy)]
enum ShlexState {
    Between,
    Word,
    Quote(char),
    Escape(Option<char>),
}
enum ShlexStep {
    Next(ShlexState),
    Emit,
    End,
}
impl Shlex<'_> {
    fn token(&mut self) -> Option<Option<String>> {
        let mut token = String::new();
        let mut quoted = false;
        let mut state = ShlexState::Between;
        loop {
            let next = self.chars.next();
            let step = match state {
                ShlexState::Between => self.between(next, &mut token),
                ShlexState::Word => self.word(next, &mut token),
                ShlexState::Quote(quote) => {
                    quoted = true;
                    quote_step(quote, next?, &mut token)
                }
                ShlexState::Escape(quote) => escape_step(quote, next?, &mut token),
            };
            match step {
                ShlexStep::Next(following) => state = following,
                ShlexStep::Emit if token.is_empty() && !quoted => state = ShlexState::Between,
                ShlexStep::Emit => return Some(Some(token)),
                ShlexStep::End => return Some(None),
            }
        }
    }
    fn between(&mut self, next: Option<char>, token: &mut String) -> ShlexStep {
        match next {
            None => ShlexStep::End,
            Some(' ' | '\t' | '\r' | '\n') => ShlexStep::Next(ShlexState::Between),
            Some('#') => {
                self.skip_line();
                ShlexStep::Next(ShlexState::Between)
            }
            Some('\\') => ShlexStep::Next(ShlexState::Escape(None)),
            Some(quote @ ('\'' | '"')) => ShlexStep::Next(ShlexState::Quote(quote)),
            Some(c) => {
                token.push(c);
                ShlexStep::Next(ShlexState::Word)
            }
        }
    }
    fn word(&mut self, next: Option<char>, token: &mut String) -> ShlexStep {
        match next {
            None | Some(' ' | '\t' | '\r' | '\n') => ShlexStep::Emit,
            Some('#') => {
                self.skip_line();
                ShlexStep::Emit
            }
            Some('\\') => ShlexStep::Next(ShlexState::Escape(None)),
            Some(quote @ ('\'' | '"')) => ShlexStep::Next(ShlexState::Quote(quote)),
            Some(c) => {
                token.push(c);
                ShlexStep::Next(ShlexState::Word)
            }
        }
    }
    fn skip_line(&mut self) {
        for c in self.chars.by_ref() {
            if c == '\n' {
                break;
            }
        }
    }
}
fn quote_step(quote: char, next: char, token: &mut String) -> ShlexStep {
    match next {
        c if c == quote => ShlexStep::Next(ShlexState::Word),
        '\\' if quote == '"' => ShlexStep::Next(ShlexState::Escape(Some(quote))),
        c => {
            token.push(c);
            ShlexStep::Next(ShlexState::Quote(quote))
        }
    }
}
fn escape_step(quote: Option<char>, next: char, token: &mut String) -> ShlexStep {
    if let Some(quote) = quote
        && next != '\\'
        && next != quote
    {
        token.push('\\');
    }
    token.push(next);
    ShlexStep::Next(quote.map_or(ShlexState::Word, ShlexState::Quote))
}
