//! The router's effective-configuration stage. The AWS CLI resolves every
//! behavior-affecting setting from the command line, the environment, and
//! the selected profile before it runs a command (`CLIDriver._update_config_chain`,
//! botocore's session variable table). This stage reads the same
//! environment map and the shared files the entry point parses once before
//! routing, and names the first setting whose resolved value selects behavior
//! the native `s3 ls` and `s3 cp` handlers do not implement, so the invocation
//! runs under Python instead of silently dropping the setting.
use crate::PythonReason;
use awscli_config::ParsedFiles;
use cli_core::client_config::Field;
use cli_core::{EnvMap, aws_profile, cli_error, proxy, shared_config};
use std::borrow::Cow;
use std::ffi::OsStr;

/// Where a setting's value comes from.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Source {
    /// An environment variable.
    Env(&'static str),
    /// A top-level key of the selected profile in the merged shared files.
    Profile(&'static str),
    /// botocore's chain: the environment variable when present, even when
    /// empty, else the profile key (`ConfigChainFactory.create_config_chain`).
    Chain(&'static str, &'static str),
    /// A key of the selected profile's nested `s3` block.
    S3(&'static str),
    /// `cli_error_format`: the flag once the main parse bound one, else
    /// AWS_CLI_ERROR_FORMAT, else the profile
    /// (`FilteredExceptionHandler._resolve_error_format`).
    ErrorFormat,
}
/// The values that engage a setting once its source supplies one.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Match {
    /// Any value, the empty string included, as botocore's providers return
    /// whatever the source holds.
    Present,
    /// A nonempty value; urllib's proxy lookup skips empty variables.
    Nonempty,
    /// The exact word `enabled` (`_should_enable_cli_history`).
    HistoryEnabled,
    /// A structured error format after lowercasing (`cli_core::cli_error`).
    StructuredErrorFormat,
    /// A value holding `$`, which `os.path.expandvars` may expand.
    VariableReference,
}
/// The native commands a setting reaches upstream.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Scope {
    /// Every native command.
    All,
    /// The commands that build a transfer manager, `s3 cp`, `s3 mv`, `s3 rm`,
    /// and `s3 sync`: `s3 ls` builds a client and no transfer manager
    /// (`ListCommand` against `S3TransferCommand`).
    Transfer,
}
/// The native module that reads an honored setting and applies it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Consumer {
    /// A `cli_core::client_config` field, whose reader consults the names
    /// [`Field::settings`] lists, except that `proxy::Environment::from_map`
    /// reads the [`Field::Proxy`] rows.
    Record(Field),
    /// `cli_core::region`.
    Region,
    /// `cli_core::endpoint_config`, through `s3::endpoint`.
    Endpoint,
    /// `cli_core::shared_config`.
    SharedFiles,
    /// The CLI's credential chain, the `credentials` crate, which
    /// `s3::credentials` walks for a command that signs.
    Credentials,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Support {
    /// The native path reads and applies the setting through its consumer.
    Honored(Consumer),
    /// The AWS CLI does not consult the setting for these commands, or
    /// consults it only for operands the native path routes to Python.
    Ignored,
    /// No native implementation; the invocation runs under Python.
    Unsupported(PythonReason),
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Setting {
    pub source: Source,
    pub support: Support,
    pub matching: Match,
    pub scope: Scope,
}
/// What the stage reads for one invocation.
#[derive(Debug)]
pub struct Inputs<'a, E: EnvMap> {
    pub env: &'a E,
    pub shared_files: &'a ParsedFiles,
    /// The `--profile` value the main parser bound, if any.
    pub cli_profile: Option<&'a str>,
    /// The `--cli-error-format` value the main parser bound, if any.
    pub cli_error_format: Option<&'a str>,
    /// Whether the command builds a transfer manager, as `s3 cp`, `s3 mv`,
    /// `s3 rm`, and `s3 sync` do and `s3 ls` does not.
    pub transfers: bool,
    /// Whether a boto config file supplies credentials botocore would read.
    pub boto_config_credentials: bool,
}
const REGION_ROW: Support = Support::Honored(Consumer::Region);
const ENDPOINT_ROW: Support = Support::Honored(Consumer::Endpoint);
const SHARED_FILES_ROW: Support = Support::Honored(Consumer::SharedFiles);
const CREDENTIALS_ROW: Support = Support::Honored(Consumer::Credentials);
const CA_BUNDLE_ROW: Support = record(Field::CaBundle);
const PROXY_ROW: Support = record(Field::Proxy);
const TCP_KEEPALIVE_ROW: Support = record(Field::TcpKeepalive);
const MAX_ATTEMPTS_ROW: Support = record(Field::MaxAttempts);
const RETRY_MODE_ROW: Support = record(Field::RetryMode);
const TRANSFER_ROW: Support = record(Field::Transfer);
const MEMORY_LIMIT_ROW: Support = record(Field::MemoryLimit);
const S3_ENDPOINT_ROW: Support = record(Field::S3Endpoint);
const REQUEST_CHECKSUM_ROW: Support = record(Field::RequestChecksumCalculation);
const RESPONSE_CHECKSUM_ROW: Support = record(Field::ResponseChecksumValidation);
const APP_ID_ROW: Support = record(Field::AppId);
const EXECUTION_ENV_ROW: Support = record(Field::ExecutionEnv);
const fn record(field: Field) -> Support {
    Support::Honored(Consumer::Record(field))
}
/// The decision table, in the order the stage checks it: the first
/// unsupported row that matches names the Python reason. Profile selection
/// itself (`--profile`, `AWS_PROFILE`, `AWS_DEFAULT_PROFILE`) is
/// `aws_profile::select`, and a selected profile that has no section is
/// checked before any row. Auto-prompt (`resolve_auto_prompt_mode`) is
/// resolved from the literal argv by `cli_error::dispose_native` after
/// routing, so it has no row either.
pub const SETTINGS: &[Setting] = &[
    Setting {
        source: Source::Env("AWS_REGION"),
        support: REGION_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_DEFAULT_REGION", "region"),
        support: REGION_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_ENDPOINT_URL_S3"),
        support: ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_ENDPOINT_URL", "endpoint_url"),
        support: ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("services"),
        support: ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_USE_FIPS_ENDPOINT", "use_fips_endpoint"),
        support: ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_USE_DUALSTACK_ENDPOINT", "use_dualstack_endpoint"),
        support: ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain(
            "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS",
            "ignore_configured_endpoint_urls",
        ),
        support: ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CONFIG_FILE"),
        support: SHARED_FILES_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_SHARED_CREDENTIALS_FILE"),
        support: SHARED_FILES_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    // botocore expands variable references in either path before `~`
    // (`raw_config_parse`); `cli_core::shared_config` expands only `~`.
    Setting {
        source: Source::Env("AWS_CONFIG_FILE"),
        support: Support::Unsupported(PythonReason::SharedFilePath),
        matching: Match::VariableReference,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_SHARED_CREDENTIALS_FILE"),
        support: Support::Unsupported(PythonReason::SharedFilePath),
        matching: Match::VariableReference,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CA_BUNDLE"),
        support: CA_BUNDLE_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("ca_bundle"),
        support: CA_BUNDLE_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("REQUESTS_CA_BUNDLE"),
        support: CA_BUNDLE_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("HTTPS_PROXY"),
        support: PROXY_ROW,
        matching: Match::Nonempty,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("https_proxy"),
        support: PROXY_ROW,
        matching: Match::Nonempty,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("HTTP_PROXY"),
        support: PROXY_ROW,
        matching: Match::Nonempty,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("http_proxy"),
        support: PROXY_ROW,
        matching: Match::Nonempty,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("NO_PROXY"),
        support: PROXY_ROW,
        matching: Match::Nonempty,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("no_proxy"),
        support: PROXY_ROW,
        matching: Match::Nonempty,
        scope: Scope::All,
    },
    // botocore maps these two keys into the config store's `proxies_config`,
    // but no CLI code reads that variable: the client args only copy a
    // programmatic Config's proxies_config (`ClientArgsCreator`), and the CLI
    // builds its Config without one.
    Setting {
        source: Source::Profile("proxy_ca_bundle"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("proxy_use_forwarding_for_https"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("proxy_client_cert"),
        support: Support::Unsupported(PythonReason::NetworkSetting),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("tcp_keepalive"),
        support: TCP_KEEPALIVE_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_RETRY_MODE", "retry_mode"),
        support: RETRY_MODE_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_MAX_ATTEMPTS", "max_attempts"),
        support: MAX_ATTEMPTS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_ACCESS_KEY_ID"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_SECRET_ACCESS_KEY"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_SESSION_TOKEN"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("aws_access_key_id"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("aws_secret_access_key"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("aws_session_token"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("credential_process"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CONTAINER_CREDENTIALS_FULL_URI"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CONTAINER_AUTHORIZATION_TOKEN"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    // botocore disables the instance provider only for `true`, in any case
    // (`IMDSFetcher`), as the native chain does.
    Setting {
        source: Source::Env("AWS_EC2_METADATA_DISABLED"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    // The environment's legacy token, which botocore reads before
    // AWS_SESSION_TOKEN, and its expiry, which makes the credentials
    // refreshable (`EnvProvider`).
    // `credentials_need_python` sends an expiry only dateutil reads to
    // Python.
    Setting {
        source: Source::Env("AWS_SECURITY_TOKEN"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CREDENTIAL_EXPIRATION"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    // The shared files' legacy token, which botocore prefers to
    // aws_session_token, as the native chain does. The original EC2 tools'
    // credential file (`OriginalEC2Provider`) is a provider the native chain
    // lacks.
    Setting {
        source: Source::Profile("aws_security_token"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_CREDENTIAL_FILE"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("role_arn"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("source_profile"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("credential_source"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("mfa_serial"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("external_id"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("role_session_name"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("duration_seconds"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("web_identity_token_file"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_ROLE_ARN"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_WEB_IDENTITY_TOKEN_FILE"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_ROLE_SESSION_NAME"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("sso_start_url"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("sso_region"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("sso_account_id"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("sso_role_name"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("sso_session"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("login_session"),
        support: Support::Unsupported(PythonReason::CredentialForm),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_METADATA_SERVICE_TIMEOUT", "metadata_service_timeout"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain(
            "AWS_METADATA_SERVICE_NUM_ATTEMPTS",
            "metadata_service_num_attempts",
        ),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain(
            "AWS_EC2_METADATA_SERVICE_ENDPOINT",
            "ec2_metadata_service_endpoint",
        ),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain(
            "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE",
            "ec2_metadata_service_endpoint_mode",
        ),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_EC2_METADATA_V1_DISABLED", "ec2_metadata_v1_disabled"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_IMDS_USE_IPV6", "imds_use_ipv6"),
        support: CREDENTIALS_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_DEFAULT_OUTPUT", "output"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::ErrorFormat,
        support: Support::Unsupported(PythonReason::StructuredErrorFormat),
        matching: Match::StructuredErrorFormat,
        scope: Scope::All,
    },
    // Output encoding: when the variable is present, even empty, Python
    // re-encodes every stream through its codec registry and validates the
    // codec name after the top-level args (`set_preferred_output_encoding`);
    // the native path writes UTF-8.
    Setting {
        source: Source::Env("AWS_CLI_OUTPUT_ENCODING"),
        support: Support::Unsupported(PythonReason::OutputEncoding),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("cli_help_output"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_PAGER"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("cli_pager"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("PAGER"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    // History: the recorder attaches when cli_history is exactly `enabled`
    // (`_should_enable_cli_history`); native records nothing.
    Setting {
        source: Source::Profile("cli_history"),
        support: Support::Unsupported(PythonReason::HistoryEnabled),
        matching: Match::HistoryEnabled,
        scope: Scope::All,
    },
    // Timestamps: `wire` leaves LastModified as the response string and
    // `iso8601` reformats it (`add_timestamp_parser`); ls parses either with
    // dateutil before printing (`ListCommand`).
    Setting {
        source: Source::Profile("cli_timestamp_format"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Profile("cli_binary_format"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_S3_USE_ARN_REGION", "s3_use_arn_region"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("use_arn_region"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_S3_DISABLE_MULTIREGION_ACCESS_POINTS"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("s3_disable_multiregion_access_points"),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain(
            "AWS_S3_DISABLE_EXPRESS_SESSION_AUTH",
            "s3_disable_express_session_auth",
        ),
        support: Support::Ignored,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("addressing_style"),
        support: S3_ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("use_accelerate_endpoint"),
        support: S3_ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("use_dualstack_endpoint"),
        support: S3_ENDPOINT_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    // Client context parameters: botocore hands the whole `s3` block to the
    // S3 endpoint rules as client context (`ClientArgsCreator._build_endpoint_resolver`),
    // where a key named after one of the model's clientContextParams
    // (`EndpointRulesetResolver._get_client_context_params`) replaces that
    // rule input with its raw string, which the rules reject as
    // the wrong type. `use_arn_region` arrives converted to a boolean, and
    // `disable_s3_express_session_auth` is always replaced by the resolved
    // top-level switch, so neither fails.
    Setting {
        source: Source::S3("force_path_style"),
        support: Support::Unsupported(PythonReason::EndpointSetting),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("accelerate"),
        support: Support::Unsupported(PythonReason::EndpointSetting),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("disable_multi_region_access_points"),
        support: Support::Unsupported(PythonReason::EndpointSetting),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("payload_signing_enabled"),
        support: Support::Unsupported(PythonReason::TransferSetting),
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::S3("target_bandwidth"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("preferred_transfer_client"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("multipart_threshold"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("multipart_chunksize"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("max_concurrent_requests"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("max_queue_size"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("max_bandwidth"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("io_chunksize"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("should_stream"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("disk_throughput"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::S3("direct_io"),
        support: TRANSFER_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::Env("AWS_CRT_S3_MEMORY_LIMIT_IN_MB"),
        support: MEMORY_LIMIT_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::Env("AWS_CRT_S3_MEMORY_LIMIT_IN_GIB"),
        support: MEMORY_LIMIT_ROW,
        matching: Match::Present,
        scope: Scope::Transfer,
    },
    Setting {
        source: Source::Chain(
            "AWS_REQUEST_CHECKSUM_CALCULATION",
            "request_checksum_calculation",
        ),
        support: REQUEST_CHECKSUM_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain(
            "AWS_RESPONSE_CHECKSUM_VALIDATION",
            "response_checksum_validation",
        ),
        support: RESPONSE_CHECKSUM_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Chain("AWS_SDK_UA_APP_ID", "sdk_ua_app_id"),
        support: APP_ID_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
    Setting {
        source: Source::Env("AWS_EXECUTION_ENV"),
        support: EXECUTION_ENV_ROW,
        matching: Match::Present,
        scope: Scope::All,
    },
];
/// The first setting, in table order, whose resolved value the handler for
/// the command cannot honor, once the selected profile is known to have a
/// section. `None` admits the invocation. A selected profile without a
/// section is botocore's ProfileNotFound, which Python raises itself.
pub fn admit<E: EnvMap>(inputs: &Inputs<'_, E>) -> Option<PythonReason> {
    let selected = aws_profile::select(inputs.env, inputs.cli_profile);
    if selected.is_some_and(|p| !aws_profile::explicit_profile_exists(inputs.shared_files, p)) {
        return Some(PythonReason::ProfileLookup);
    }
    let profile = selected.and_then(OsStr::to_str).unwrap_or("default");
    if proxy::Environment::from_map(inputs.env).requires_python() {
        return Some(PythonReason::NetworkSetting);
    }
    if credentials_need_python(inputs) {
        return Some(PythonReason::CredentialForm);
    }
    SETTINGS.iter().find_map(|setting| {
        let Support::Unsupported(reason) = setting.support else {
            return None;
        };
        if setting.scope == Scope::Transfer && !inputs.transfers {
            return None;
        }
        if let (Match::VariableReference, Source::Env(name)) = (setting.matching, setting.source) {
            let value = inputs.env.var_os(name)?;
            return value.as_encoded_bytes().contains(&b'$').then_some(reason);
        }
        let value = resolve(inputs, profile, setting.source)?;
        matches(setting.matching, &value).then_some(reason)
    })
}
fn credentials_need_python<E: EnvMap>(inputs: &Inputs<'_, E>) -> bool {
    let env = inputs.env;
    // botocore reads each variable as text with surrogate escapes; the
    // native providers read Unicode alone. The instance metadata service's
    // variables are apart: native refuses one that is not Unicode where
    // its text is needed, and a switch's is not `true`.
    credentials::text_variables().any(|name| env.var_os(name).is_some() && env.var(name).is_none())
        // botocore reads the expiry with dateutil, which guesses at more
        // forms than the native chain reads. An empty one is unset to both.
        || env
            .var("AWS_CREDENTIAL_EXPIRATION")
            .is_some_and(|expiry| !expiry.is_empty() && !credentials::reads_expiry(expiry))
        // botocore's boto provider reads `BOTO_CONFIG`, `/etc/boto.cfg`, and
        // `~/.boto`; a file that supplies no credentials changes nothing.
        || inputs.boto_config_credentials
}

fn resolve<'a, E: EnvMap>(
    inputs: &'a Inputs<'_, E>,
    profile: &str,
    source: Source,
) -> Option<Cow<'a, str>> {
    let property = |key| shared_config::profile_property(inputs.shared_files, profile, key);
    let env = |name| inputs.env.var_os(name).map(OsStr::to_string_lossy);
    match source {
        Source::Env(name) => env(name),
        Source::Profile(key) => property(key).map(Cow::Borrowed),
        Source::Chain(name, key) => env(name).or_else(|| property(key).map(Cow::Borrowed)),
        Source::S3(key) => {
            shared_config::profile_nested_property(inputs.shared_files, profile, "s3", key)
                .map(Cow::Borrowed)
        }
        Source::ErrorFormat => inputs
            .cli_error_format
            .map(Cow::Borrowed)
            .or_else(|| env("AWS_CLI_ERROR_FORMAT"))
            .or_else(|| property("cli_error_format").map(Cow::Borrowed)),
    }
}
/// The honored rows that name `field`, in table order, which is the order
/// its reader consults them ([`Field::settings`]).
pub fn record_rows(field: Field) -> impl Iterator<Item = &'static Setting> {
    SETTINGS
        .iter()
        .filter(move |setting| names_field(setting, field))
}
fn names_field(setting: &Setting, field: Field) -> bool {
    setting.support == record(field)
}
/// Whether `value` engages a setting whose match is `matching`.
pub fn matches(matching: Match, value: &str) -> bool {
    match matching {
        Match::Present => true,
        Match::Nonempty => !value.is_empty(),
        Match::HistoryEnabled => value == "enabled",
        Match::StructuredErrorFormat => cli_error::is_structured_format(value),
        Match::VariableReference => value.contains('$'),
    }
}
#[cfg(test)]
pub(crate) mod sample;
#[cfg(test)]
mod tests;
