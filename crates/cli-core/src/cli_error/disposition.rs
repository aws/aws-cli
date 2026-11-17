use super::*;
use std::ffi::OsStr;

/// Immutable facts used by the AWS error handler and auto-prompt resolver.
#[derive(Debug, Clone, Copy)]
pub struct Environment<'a, E: EnvMap> {
    pub argv: &'a [std::ffi::OsString],
    pub env: &'a E,
    pub stdout_is_tty: bool,
    pub shared_files: &'a ParsedFiles,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AutoPrompt {
    Off,
    On,
    OnPartial,
}

/// Whether a native invocation must run under Python because the resolved
/// auto-prompt mode is `on`, which prompts before any command runs.
pub fn dispose_native<E: EnvMap>(environment: &Environment<'_, E>) -> Option<PythonReason> {
    match auto_prompt_mode(environment) {
        AutoPrompt::On => Some(PythonReason::AutoPrompt),
        AutoPrompt::Off | AutoPrompt::OnPartial => None,
    }
}
/// How Python would present a failure the router settled natively, given
/// the stage it failed at. Rendering is native unless the configuration in
/// force makes Python do something the native path does not model.
pub fn dispose_failure<E: EnvMap>(
    environment: &Environment<'_, E>,
    result: &ParseResult,
    failure: &Failure,
) -> Disposition {
    // Every failure, first-pass ones included, is written through
    // get_stderr_text_writer, which re-encodes the stream whenever
    // AWS_CLI_OUTPUT_ENCODING is present, even empty.
    if environment.env.var_os("AWS_CLI_OUTPUT_ENCODING").is_some() {
        return Disposition::Python(PythonReason::OutputEncoding);
    }
    let color = color_inputs(environment);
    match result.stage {
        Stage::AutoPrompt | Stage::FirstPass => {
            return Disposition::Render(Rendering {
                format: ErrorFormat::Enhanced,
                color,
            });
        }
        Stage::Main
        | Stage::Dispatch
        | Stage::TopLevel
        | Stage::Probe
        | Stage::Table
        | Stage::Unpack
        | Stage::Leftover => {}
    }
    let mode = auto_prompt_mode(environment);
    if mode == AutoPrompt::On
        || (mode == AutoPrompt::OnPartial
            && exit_status(Category::from_class(failure.class)) == 252)
    {
        return Disposition::Python(PythonReason::AutoPrompt);
    }
    if history_enabled(environment, result) {
        return Disposition::Python(PythonReason::HistoryEnabled);
    }
    match failure.class {
        FailureClass::General | FailureClass::UnknownArgument => Disposition::Render(Rendering {
            format: ErrorFormat::Legacy,
            color,
        }),
        FailureClass::ParamValidation => match resolve_error_format(environment, result) {
            Ok(format) => Disposition::Render(Rendering { format, color }),
            Err(reason) => Disposition::Python(reason),
        },
    }
}
/// The format the handler chain frames a native command's failure in, from
/// the flag, then the environment, then the session profile. The router
/// already handed a structured format and a missing profile to Python, so
/// a resolution that still names Python here is a router gap; it is framed
/// as the default rather than failing the error path a second time.
pub fn command_failure_format<E: EnvMap>(
    environment: &Environment<'_, E>,
    result: &ParseResult,
) -> ErrorFormat {
    resolve_error_format(environment, result).unwrap_or_default()
}
fn resolve_error_format<E: EnvMap>(
    environment: &Environment<'_, E>,
    result: &ParseResult,
) -> Result<ErrorFormat, PythonReason> {
    if result.stage != Stage::Main
        && let Some(flag) = result.globals.namespace.string("cli_error_format")
    {
        return classify_format(flag);
    }
    if let Some(value) = environment.env.var_os("AWS_CLI_ERROR_FORMAT") {
        return classify_format(&value.to_string_lossy());
    }
    resolve_error_format_profile(environment, result)
}
fn resolve_error_format_profile<E: EnvMap>(
    environment: &Environment<'_, E>,
    result: &ParseResult,
) -> Result<ErrorFormat, PythonReason> {
    let named = session_profile(environment, result);
    if named.is_some_and(|profile| {
        !aws_profile::explicit_profile_exists(environment.shared_files, profile)
    }) {
        return Err(PythonReason::ProfileLookup);
    }
    classify_format(
        shared_config::profile_property(
            environment.shared_files,
            named.unwrap_or(OsStr::new("default")),
            "cli_error_format",
        )
        .unwrap_or("enhanced"),
    )
}
/// Whether the failure came after _handle_top_level_args applied --profile
/// to the session and _emit_session_event fired `session-initialized`. A
/// top-level failure is raised by the former.
const fn after_top_level(stage: Stage) -> bool {
    match stage {
        Stage::Probe | Stage::Table | Stage::Unpack | Stage::Leftover => true,
        Stage::AutoPrompt | Stage::FirstPass | Stage::Main | Stage::Dispatch | Stage::TopLevel => {
            false
        }
    }
}
fn session_profile<'a, E: EnvMap>(
    environment: &Environment<'a, E>,
    result: &'a ParseResult,
) -> Option<&'a OsStr> {
    let explicit = if after_top_level(result.stage) {
        result.globals.namespace.string("profile")
    } else {
        None
    };
    aws_profile::select(environment.env, explicit)
}
fn history_enabled<E: EnvMap>(environment: &Environment<'_, E>, result: &ParseResult) -> bool {
    if !after_top_level(result.stage) {
        return false;
    }
    let profile = session_profile(environment, result).unwrap_or(OsStr::new("default"));
    shared_config::profile_property(environment.shared_files, profile, "cli_history")
        == Some("enabled")
}
fn auto_prompt_mode<E: EnvMap>(environment: &Environment<'_, E>) -> AutoPrompt {
    if environment.argv.iter().any(|arg| {
        matches!(
            arg.to_str(),
            Some("help" | "--version" | "--no-cli-auto-prompt")
        )
    }) {
        return AutoPrompt::Off;
    }
    if environment
        .argv
        .iter()
        .any(|arg| arg == "--cli-auto-prompt")
    {
        return AutoPrompt::On;
    }
    if let Some(value) = environment.env.var_os("AWS_CLI_AUTO_PROMPT") {
        return auto_prompt_mode_from_name(&value.to_string_lossy());
    }
    // The mode is resolved before --profile is applied to the session, so
    // only the environment names the profile; a missing profile is
    // ProfileNotFound, which the resolver treats as off.
    let profile = aws_profile::select_or_default(environment.env, None);
    auto_prompt_mode_from_name(
        shared_config::profile_property(environment.shared_files, profile, "cli_auto_prompt")
            .unwrap_or("off"),
    )
}
fn auto_prompt_mode_from_name(value: &str) -> AutoPrompt {
    match value.to_ascii_lowercase().as_str() {
        "on" => AutoPrompt::On,
        "on-partial" => AutoPrompt::OnPartial,
        _ => AutoPrompt::Off,
    }
}
/// CPython's stdout color decision under an isolated interpreter, which
/// ignores PYTHON_COLORS.
fn color_inputs<E: EnvMap>(environment: &Environment<'_, E>) -> Color {
    let nonempty = |name| environment.env.var_os(name).is_some_and(|v| !v.is_empty());
    Color {
        stdout_is_tty: environment.stdout_is_tty,
        no_color: nonempty("NO_COLOR"),
        force_color: nonempty("FORCE_COLOR"),
        term_dumb: environment.env.var("TERM") == Some("dumb"),
    }
}
