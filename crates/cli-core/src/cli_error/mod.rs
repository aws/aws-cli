//! AWS handler framing and stage-aware error disposition.
use crate::{EnvMap, aws_profile, shared_config};
use awscli_argparse::{
    ParseResult,
    chain::Stage,
    failure::{Color, Failure, FailureClass},
};
use awscli_config::ParsedFiles;
use std::io::{self, Write};

mod disposition;
mod stdout_flush;
pub use disposition::{Environment, command_failure_format, dispose_failure, dispose_native};
pub use stdout_flush::{
    FLUSH_FAILURE_STATUS, NO_STDOUT_MESSAGE, StandardStream, StdoutFailure, Termination,
    UNREPORTED_FAILURE_STATUS, WRITE_FAILED_MESSAGE, flush_pending_stdout, flush_streams_at_exit,
    forget_unkept_stderr, os_error_text, report_stdout_flush_failure, stdout_write_failure_message,
    stream_buffer_len,
};

pub const BROKEN_PIPE_MESSAGE: &str = "[Errno 32] Broken pipe";

/// Why an invocation, or the rendering of its failure, belongs to Python.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PythonReason {
    /// AWS_CLI_NATIVE_ROUTER=python in the environment.
    EnvOverride,
    /// The main parser's version action ran.
    VersionRequested,
    /// A command parser matched its `help` sentinel.
    HelpRequested,
    /// The command is not `s3`, or a main-parse failure came after a
    /// command other than `s3` was consumed.
    UnsupportedCommand,
    /// An `s3` subcommand without a native handler, whatever its outcome.
    UnsupportedSubcommand,
    /// A global option the native handlers do not implement (`--no-verify-ssl`,
    /// `--cli-read-timeout`, `--cli-binary-format`, the auto-prompt switches,
    /// and the output globals where the command does not ignore them), or a
    /// value of one they implement only in part: a structured
    /// `--cli-error-format`, a `--cli-connect-timeout` botocore rejects, or a
    /// `--ca-bundle` that is blank, names no regular readable file, or holds
    /// anything but well-formed certificates where upstream loads it with
    /// OpenSSL.
    PythonOnlyGlobal,
    /// A subcommand option outside the handler's native surface.
    UnsupportedOption,
    /// A value the native handler cannot carry, such as a page size outside
    /// the listing request's range, or one of its options whose value needs
    /// processing the native unpack loop does not implement, such as
    /// `fileb://` contents on a string option or a parameter file that is a
    /// pipe or a device, whose bytes a native read would consume before
    /// Python read the same URI, or a loaded value with a NUL in it, which
    /// the handler's C strings would end at; or an argument that is not
    /// Unicode where native needs its text (a global's value or a typed
    /// option's value that no failure quotes first), which Python decodes
    /// with surrogate escapes.
    UnsupportedValue,
    /// An operand shape or target the native handler does not implement.
    UnsupportedOperand,
    /// The resolved auto-prompt mode would prompt; decided from the literal
    /// argv by cli_error after routing.
    AutoPrompt,
    /// The resolved `cli_error_format` is one of Python's structured
    /// formats, whether it frames a failure or a native verdict's errors.
    StructuredErrorFormat,
    /// The selected profile has no section in either shared file, which is
    /// botocore's ProfileNotFound; for a failure, the profile whose
    /// configuration selects the framing is the one missing.
    ProfileLookup,
    /// `AWS_CONFIG_FILE` or `AWS_SHARED_CREDENTIALS_FILE` holds a `$`, which
    /// botocore may expand as a variable reference and the native reader of
    /// the same files does not.
    SharedFilePath,
    /// The selected profile or the environment configures a credential
    /// source the native chain does not implement: assume-role, web
    /// identity, SSO, login, or the boto-era credential files; or a value
    /// its providers do not read as botocore's do: a credential variable
    /// that is not Unicode, or an environment expiry in a form only
    /// dateutil reads.
    CredentialForm,
    /// A retry setting botocore's client rejects (a `retry_mode` other than
    /// `standard` or `adaptive`, a `max_attempts` that is not an integer of at
    /// least 1, or a nested block for either) or that native cannot honor:
    /// for `s3 ls` and `s3 cp`'s newly eligible persona, the adaptive mode or
    /// a count the CRT's standard strategy
    /// cannot express (1, or more than 64), which only botocore's own retries
    /// honor there.
    RetrySetting,
    /// A CA bundle setting that is blank, which botocore rejects, that names no
    /// regular readable file, whose error only upstream renders, that holds
    /// anything but well-formed certificates where upstream loads it with
    /// OpenSSL, that is `s3 cp`'s `REQUESTS_CA_BUNDLE`, which upstream's CRT
    /// client ignores for botocore's own bundle, or that is a nested block of
    /// the profile; a nested `tcp_keepalive`; a proxy environment the native
    /// reader cannot reproduce: a mixed-case spelling, a CGI `REQUEST_METHOD`
    /// with only `HTTP_PROXY`, an empty lowercase override of a nonempty
    /// uppercase value, or a bypass list with a non-ASCII byte in it or in a
    /// configured endpoint; or the profile's `proxy_client_cert`.
    NetworkSetting,
    /// The selected profile's `s3` key is a string rather than a block, which
    /// botocore's S3 client fails on; its `addressing_style` is not exactly
    /// `auto`, `virtual`, or `path`, which botocore's `Config` rejects; it
    /// names a client context parameter of the S3 endpoint rules, which
    /// botocore passes to the rules as a string they reject; the region a
    /// setting names is empty or no valid host label, which botocore's session
    /// refuses when it creates the command's client; the configured endpoint
    /// names a services section that is missing or empty, or the selected
    /// endpoint URL has no valid host, which client creation rejects; or the
    /// selected endpoint URL has a scheme other than `http` or `https` as
    /// spelled, a port `urlsplit` cannot read, more than one `@` in its
    /// authority, a path botocore's endpoint rules quote or normalize, a
    /// query, or a fragment, which the native resolver reads differently, or
    /// an empty port or one naming the scheme's default, which native keeps
    /// in the Host header.
    EndpointSetting,
    /// A standard S3 transfer setting the native transfer path does not read
    /// is configured, the `s3` block selects the classic transfer client,
    /// upstream's transfer configuration rejects a value the native path
    /// reads, or botocore's client rejects a checksum setting (a value other
    /// than `when_supported` or `when_required` in any case, or a nested
    /// block).
    TransferSetting,
    /// `s3 cp` would run the CRT client under `auto`, but another AWS CLI
    /// process holds the CRT process lock, so upstream resolves `auto` to its
    /// classic client (`_resolve_transfer_client_type_for_system`), which
    /// only the fallback implements.
    CrtClientRunning,
    /// The user agent's app id is a nested block of the profile, or it and
    /// `AWS_EXECUTION_ENV` together are longer than the native header holds;
    /// upstream sends both whole.
    UserAgentSetting,
    /// `cli_history` is enabled and Python records every invocation that
    /// reaches its command, parse failures included, while native records no
    /// history.
    HistoryEnabled,
    /// A shared config, credentials, or alias file exists but the native
    /// parser could not use it, because its grammar is invalid, which
    /// botocore reports as `ConfigParseError` before any command is parsed,
    /// or because it exceeds the native size limit; or the alias path is a
    /// directory, which AliasLoader opens anyway and botocore refuses.
    ConfigParseFailure,
    /// The alias file names `s3` in its `toplevel` section or defines aliases
    /// under the `s3` command tree, which replace or extend the pinned `s3`
    /// grammar before Python parses it.
    S3Alias,
    /// The config file has a `[plugins]` section, whose
    /// `cli_legacy_plugin_path` loads plugins that can replace or extend any
    /// command, or hook any stage, before Python parses argv.
    Plugins,
    /// `AWS_CLI_OUTPUT_ENCODING` is set, so Python re-encodes every stream
    /// through its codec registry and validates the codec name after the
    /// top-level args; the native renderer writes UTF-8 and does neither.
    OutputEncoding,
}
impl PythonReason {
    pub const fn name(self) -> &'static str {
        match self {
            Self::EnvOverride => "env_override",
            Self::VersionRequested => "version_requested",
            Self::HelpRequested => "help_requested",
            Self::UnsupportedCommand => "unsupported_command",
            Self::UnsupportedSubcommand => "unsupported_subcommand",
            Self::PythonOnlyGlobal => "python_only_global",
            Self::UnsupportedOption => "unsupported_option",
            Self::UnsupportedValue => "unsupported_value",
            Self::UnsupportedOperand => "unsupported_operand",
            Self::AutoPrompt => "auto_prompt",
            Self::StructuredErrorFormat => "structured_error_format",
            Self::ProfileLookup => "profile_lookup",
            Self::SharedFilePath => "shared_file_path",
            Self::CredentialForm => "credential_form",
            Self::RetrySetting => "retry_setting",
            Self::NetworkSetting => "network_setting",
            Self::EndpointSetting => "endpoint_setting",
            Self::TransferSetting => "transfer_setting",
            Self::CrtClientRunning => "crt_client_running",
            Self::UserAgentSetting => "user_agent_setting",
            Self::HistoryEnabled => "history_enabled",
            Self::ConfigParseFailure => "config_parse_failure",
            Self::S3Alias => "s3_alias",
            Self::Plugins => "plugins",
            Self::OutputEncoding => "output_encoding",
        }
    }
}

/// Native failure formats; structured formats belong to Python.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum ErrorFormat {
    #[default]
    Enhanced,
    Legacy,
}
impl ErrorFormat {
    pub fn from_name(value: &str) -> Option<Self> {
        match value {
            "enhanced" => Some(Self::Enhanced),
            "legacy" => Some(Self::Legacy),
            _ => None,
        }
    }
}

/// The handlers of `construct_cli_error_handlers_chain` that a native
/// command can reach. The handler that claims a failure fixes its framing and
/// its exit status, so every failure states its category.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Category {
    /// ParamValidationErrorsHandler and UnknownArgumentErrorHandler: 252.
    ParamValidation,
    /// ConfigurationErrorHandler, and the NoRegion and Pager handlers that
    /// share its status: 253.
    Configuration,
    /// NoCredentialsErrorHandler: 253, with its own sentence.
    NoCredentials,
    /// ClientErrorHandler: 254, a service error response.
    ClientError,
    /// GeneralExceptionHandler: 255, anything else.
    General,
    /// InterruptExceptionHandler: 130, a Ctrl-C that escaped the command.
    Interrupt,
}
impl Category {
    /// The handler a parser failure class belongs to.
    pub const fn from_class(class: FailureClass) -> Self {
        match class {
            FailureClass::ParamValidation | FailureClass::UnknownArgument => Self::ParamValidation,
            FailureClass::General => Self::General,
        }
    }
}
pub fn exit_status(category: Category) -> u8 {
    match category {
        Category::ParamValidation => 252,
        Category::Configuration | Category::NoCredentials => 253,
        Category::ClientError => 254,
        Category::General => 255,
        Category::Interrupt => crate::interrupt::EXIT_STATUS,
    }
}

/// A native command's failure after parsing, carrying what the error-handler
/// chain reads from the exception: the handler that claims it, the service
/// error's code, message, and operation when a response supplied them, and
/// the CRT error the request finished with. Its fields are owned, so it
/// remains valid after its CRT runtime shuts down.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommandFailure {
    /// The handler that claims the failure, which fixes its framing and its
    /// exit status.
    pub category: Category,
    /// The service error code from the response body, or the HTTP status
    /// number when the body carried none; empty when no request failed.
    pub code: String,
    /// `str(exception)`: the service message, the sentence a handler
    /// composes, or the name of an escaped internal error.
    pub message: Vec<u8>,
    /// The operation that failed, `ListObjectsV2` for example; empty when no
    /// request failed.
    pub operation: String,
    /// The CRT error code the request finished with; zero when none did.
    pub crt_code: i32,
    /// The CRT error name for `crt_code`, resolved while the library was
    /// live; empty when none.
    pub crt_name: String,
    /// The HTTP status of the final response, or zero when none arrived.
    pub http_status: i32,
    /// The retries botocore made before its attempts ran out, which a
    /// ClientError names after the operation; `None` when it names none.
    /// A `u32` keeps the failure small enough to return, and no listing
    /// makes more retries than it holds.
    pub retries_exhausted: Option<u32>,
}
impl CommandFailure {
    /// A failure `category` claims, with every other field empty.
    pub const fn new(category: Category) -> Self {
        Self {
            category,
            code: String::new(),
            message: Vec::new(),
            operation: String::new(),
            crt_code: 0,
            crt_name: String::new(),
            http_status: 0,
            retries_exhausted: None,
        }
    }
}
impl std::fmt::Display for CommandFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&String::from_utf8_lossy(&self.message))
    }
}
impl std::error::Error for CommandFailure {}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Rendering {
    pub format: ErrorFormat,
    pub color: Color,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Disposition {
    Render(Rendering),
    Python(PythonReason),
}

pub fn is_structured_format(value: &str) -> bool {
    matches!(
        value.to_ascii_lowercase().as_str(),
        "json" | "yaml" | "text" | "table"
    )
}
fn classify_format(value: &str) -> Result<ErrorFormat, PythonReason> {
    if is_structured_format(value) {
        return Err(PythonReason::StructuredErrorFormat);
    }
    Ok(ErrorFormat::from_name(&value.to_ascii_lowercase()).unwrap_or_default())
}
fn trim(value: &str) -> &str {
    value.trim_matches([' ', '\t', '\n', '\u{b}', '\u{c}', '\r'])
}
fn trim_bytes(value: &[u8]) -> &[u8] {
    let retained = |byte: &u8| !matches!(byte, b' ' | b'\t' | b'\n' | 0x0b | 0x0c | b'\r');
    let Some(start) = value.iter().position(retained) else {
        return &[];
    };
    let end = value.iter().rposition(retained).unwrap_or(start);
    &value[start..=end]
}

pub fn render(writer: &mut dyn Write, failure: &Failure, rendering: Rendering) -> io::Result<()> {
    let text = failure.error_text(rendering.color);
    match failure.class {
        FailureClass::UnknownArgument => {
            writeln!(writer, "\nusage: {}", awscli_argparse::tables::USAGE)?;
            write_error(writer, trim(&text).as_bytes())
        }
        FailureClass::General => write_error(writer, trim(&text).as_bytes()),
        FailureClass::ParamValidation => match rendering.format {
            ErrorFormat::Legacy => write_error(writer, trim(&text).as_bytes()),
            // format_error_message strips the whole message before prefixing
            // it, so the enhanced framing keeps any leading whitespace.
            ErrorFormat::Enhanced => writeln!(
                writer,
                "\naws: [ERROR]: An error occurred (ParamValidation): {}",
                text.trim_end_matches([' ', '\t', '\n', '\u{b}', '\u{c}', '\r'])
            ),
        },
    }
}

/// Write the framed command failure as its handler would, without the exit.
/// A handler that extracts a code frames the enhanced format as
/// `An error occurred (Code): message` and the legacy format as the bare
/// message; a service error is `str(ClientError)` in both; the general
/// handler never consults the format and renders without allocating.
pub fn render_command_failure(
    writer: &mut dyn Write,
    failure: &CommandFailure,
    format: ErrorFormat,
) -> io::Result<()> {
    if failure.category == Category::General {
        return write_error(writer, trim_bytes(&failure.message));
    }
    let mut text = Vec::new();
    write_command_failure_text(&mut text, failure, format);
    // format_error_message strips the composed text, so a message keeps its
    // leading whitespace behind a code and its trailing whitespace ahead of
    // a handler's suffix.
    write_error(writer, trim_bytes(&text))
}
#[expect(
    clippy::unreachable,
    reason = "the general category renders before composing text, and no caller builds an \
              interrupt failure"
)]
fn write_command_failure_text(text: &mut Vec<u8>, failure: &CommandFailure, format: ErrorFormat) {
    match failure.category {
        Category::ClientError => {
            text.extend_from_slice(
                format!(
                    "An error occurred ({}) when calling the {} operation",
                    failure.code, failure.operation
                )
                .as_bytes(),
            );
            if let Some(retries) = failure.retries_exhausted {
                text.extend_from_slice(format!(" (reached max retries: {retries})").as_bytes());
            }
            text.extend_from_slice(b": ");
            text.extend_from_slice(&failure.message);
        }
        Category::ParamValidation => write_coded_text(text, format, "ParamValidation", failure, ""),
        Category::Configuration => write_coded_text(text, format, "Configuration", failure, ""),
        Category::NoCredentials => write_coded_text(
            text,
            format,
            "NoCredentials",
            failure,
            ". You can configure credentials by running \"aws login\".",
        ),
        Category::General => unreachable!(),
        Category::Interrupt => unreachable!(),
    }
}
fn write_coded_text(
    text: &mut Vec<u8>,
    format: ErrorFormat,
    code: &str,
    failure: &CommandFailure,
    suffix: &str,
) {
    if format == ErrorFormat::Enhanced {
        text.extend_from_slice(format!("An error occurred ({code}): ").as_bytes());
    }
    text.extend_from_slice(&failure.message);
    text.extend_from_slice(suffix.as_bytes());
}
fn write_error(writer: &mut dyn Write, stripped: &[u8]) -> io::Result<()> {
    writer.write_all(b"\naws: [ERROR]:")?;
    if !stripped.is_empty() {
        writer.write_all(b" ")?;
        writer.write_all(stripped)?;
    }
    writer.write_all(b"\n")
}
#[cfg(test)]
mod tests;
