//! Owned global overrides and immutable command inputs.
use crate::EnvMap;
use awscli_config::ParsedFiles;
use std::path::Path;
mod platform;
pub use platform::terminal_columns;

/// Borrow process arguments after the optional program name.
pub fn command_argv<T>(arguments: &[T]) -> &[T] {
    &arguments[usize::from(!arguments.is_empty())..]
}

const TERMINAL_COLUMNS_FALLBACK: usize = 80;
const FORMATTER_MARGIN: usize = 2;

/// Python's positive COLUMNS value, terminal columns, or
/// `TERMINAL_COLUMNS_FALLBACK`, minus argparse's `FORMATTER_MARGIN`.
pub fn formatter_width(env: &impl EnvMap, terminal: Option<usize>) -> usize {
    columns_from_environment(env)
        .or(terminal)
        .unwrap_or(TERMINAL_COLUMNS_FALLBACK)
        .saturating_sub(FORMATTER_MARGIN)
}
/// COLUMNS as `shutil.get_terminal_size` reads it: `int()` of the value, with
/// any ValueError, a literal over CPython's digit limit included, read as
/// unset, as is a value that is not positive.
pub fn columns_from_environment(env: &impl EnvMap) -> Option<usize> {
    let value = awscli_argparse::unpack::parse_int(env.var("COLUMNS")?).ok()?;
    (value > 0).then(|| usize::try_from(value).unwrap_or(usize::MAX))
}

/// Describe selected credential inputs without including their secret values.
pub fn credential_source<'a, E: EnvMap>(context: &CommandContext<'a, E>) -> &'static str {
    CredentialSource::select(
        context.env,
        context.shared_files,
        context.globals.profile.as_deref(),
    )
    .describe()
}

/// The provider of the CLI's credential chain that answers for the selected
/// inputs, with credentials or with an error that stops the chain. The
/// chain is botocore's (`create_credential_resolver`) without the providers
/// admission sends to Python, so on the native path botocore's chain
/// answers from the same one.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum CredentialSource {
    /// A nonempty `AWS_ACCESS_KEY_ID`, which the chain reads first unless
    /// `--profile` names a profile.
    Environment,
    /// The selected profile's `aws_access_key_id`, in the shared
    /// credentials file's section or, after `credential_process`, the config
    /// file's.
    SharedProfile,
    /// The selected profile's `credential_process`.
    Process,
    /// Either container endpoint variable, even empty, with none of the
    /// above: the container provider, which answers or fails.
    Container,
    /// None of the above: the chain's last provider, instance metadata.
    #[default]
    DefaultChain,
}
impl CredentialSource {
    /// The source for `env`, the shared files and the `--profile` value. An
    /// access key selects its provider whatever its value, and whatever
    /// the provider then finds missing.
    pub fn select<E: EnvMap>(env: &E, files: &ParsedFiles, cli_profile: Option<&str>) -> Self {
        let nonempty = |name| env.var_os(name).is_some_and(|s| !s.is_empty());
        if !crate::aws_profile::is_explicit(cli_profile) && nonempty("AWS_ACCESS_KEY_ID") {
            return Self::Environment;
        }
        // The shared files are UTF-8, so another name has no section.
        let Some(profile) = crate::aws_profile::select_or_default(env, cli_profile).to_str() else {
            return Self::DefaultChain;
        };
        let has = |sections: &awscli_config::Sections, key| {
            sections
                .get(profile)
                .is_some_and(|entries| entries.contains_key(key))
        };
        if has(&files.credentials.sections, "aws_access_key_id") {
            return Self::SharedProfile;
        }
        if files
            .profiles
            .as_ref()
            .is_some_and(|merged| has(merged, "credential_process"))
        {
            return Self::Process;
        }
        if has(&files.organized.profiles, "aws_access_key_id") {
            return Self::SharedProfile;
        }
        let container = [
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        ];
        if container.into_iter().any(|name| env.var_os(name).is_some()) {
            return Self::Container;
        }
        Self::DefaultChain
    }
    /// The name `--debug` reports for the source.
    pub fn describe(self) -> &'static str {
        match self {
            Self::Environment => "environment",
            Self::SharedProfile => "shared profile",
            Self::Process => "credential_process",
            Self::Container => "container provider",
            Self::DefaultChain => "default provider chain",
        }
    }
}

/// The global option values the native handlers receive, including explicit
/// empty strings. The main parser keeps the last occurrence at any command
/// position, as the AWS CLI does.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Globals {
    /// Enable native diagnostics and the CRT debug logger on stderr.
    pub debug: bool,
    /// Explicit region override; None leaves resolution to the handler.
    pub region: Option<String>,
    /// Explicit profile selection; None preserves environment and default
    /// selection.
    pub profile: Option<String>,
    /// Explicit endpoint override; None uses the resolved AWS endpoint.
    pub endpoint_url: Option<String>,
    /// `--ca-bundle`, which outranks the environment and the profile; None
    /// when absent.
    pub ca_bundle: Option<String>,
    /// True under `--no-sign-request`.
    pub no_sign_request: bool,
    /// `--cli-connect-timeout` as global resolution leaves it
    /// (customizations/globalargs.py `_resolve_timeout`): None when the
    /// command line did not set it, so botocore's 60-second default applies;
    /// `Some(0)` for an explicit 0, which disables the timeout; and any other
    /// count of seconds as given, negative values included.
    pub connect_timeout: Option<i64>,
}

/// Inputs captured once by the executable and borrowed by native commands.
#[derive(Debug)]
pub struct CommandContext<'a, E: EnvMap> {
    pub env: &'a E,
    pub shared_files: &'a ParsedFiles,
    pub globals: &'a Globals,
    pub directory: &'a Path,
    pub payload: &'a [u8],
    pub client: &'a crate::client_config::ClientConfig,
}

#[cfg(test)]
mod tests;
