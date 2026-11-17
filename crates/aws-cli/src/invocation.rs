use awscli_argparse::{Options, unpack};
use cli_core::output::{BufferedStream, TextStream};
use cli_core::startup::{CommandStdout, Descriptor};
use cli_core::{EnvMap, SnapshotEnv, cli_error, command, shared_config};
use cli_router::{Configuration, Verdict};
#[cfg(unix)]
use std::os::fd::AsFd;
use std::{
    collections::HashMap,
    ffi::OsString,
    io::{self, IsTerminal, Write},
};

const LISTING_STDOUT_BYTES: usize = 1024;
const REPORT_STDERR_BYTES: usize = 4096;

/// The User-Agent metadata that names why the router handed the invocation
/// to Python, `md/fallback#<reason>`, with the reason's name as forced native
/// routing's refusal prints it.
const FALLBACK_METADATA: &str = "fallback";

type CommandStreams = (BufferedStream<CommandStdout>, BufferedStream<Descriptor>);

enum Outcome {
    Status(crate::HostExitStatus),
    Python(cli_error::PythonReason),
}

pub fn run() -> io::Result<crate::HostExitStatus> {
    let env = SnapshotEnv::capture();
    crate::bootstrap::prepare(&env)?;
    let arguments: Vec<OsString> = std::env::args_os().collect();
    let outcome = match cli_router::forced_route(env.var(cli_router::ROUTING_ENV_VAR)) {
        Some(reason) => Outcome::Python(reason),
        None => route_and_dispatch(&env, &arguments)?,
    };
    match outcome {
        Outcome::Status(status) => Ok(status),
        Outcome::Python(reason) => run_python(&env, &arguments, reason),
    }
}
fn route_and_dispatch(env: &SnapshotEnv, arguments: &[OsString]) -> io::Result<Outcome> {
    let argv = command::command_argv(arguments);
    let stdout_is_tty = io::stdout().is_terminal();
    let columns = terminal_columns(stdout_is_tty);
    let options = Options {
        prog: arguments.first().cloned().unwrap_or_else(|| "aws".into()),
        formatter_width: command::formatter_width(env, columns),
    };
    let mut parsed =
        awscli_argparse::parse_os(argv, &options, &awscli_argparse::tables::TABLES_DEFAULT);
    let files = shared_config::load(&awscli_config::StdFs, env).map_err(io::Error::other)?;
    let boto_config_credentials =
        shared_config::boto_config_supplies_credentials(&awscli_config::StdFs, env)
            .map_err(io::Error::other)?;
    // Relative filesystem operations still work after the shell's cwd has been unlinked.
    let directory = std::env::current_dir().unwrap_or_else(|_| ".".into());
    let variables: HashMap<String, OsString> = env
        .names()
        .into_iter()
        .filter_map(|name| Some((name.to_owned(), env.var_os(name)?.to_owned())))
        .collect();
    let probe_platform = crt::runtime::platform;
    let acquire_process_lock = crt::process_lock::acquire;
    let verdict = cli_router::route_with_process_lock(
        &mut parsed,
        &unpack::Environment {
            directory: &directory,
            variables: &variables,
            files: &unpack::FsParamfiles,
            preferred_encoding: unpack::host_preferred_encoding(),
        },
        &Configuration {
            env,
            shared_files: &files,
            boto_config_credentials,
            embedded_trust: payload_embeds_trust(),
        },
        probe_platform,
        acquire_process_lock,
    );
    let environment = cli_error::Environment {
        argv,
        env,
        stdout_is_tty,
        shared_files: &files,
    };
    dispatch(verdict, &parsed, &environment, &directory)
}
fn terminal_columns(is_terminal: bool) -> Option<usize> {
    #[cfg(unix)]
    {
        is_terminal
            .then(|| command::terminal_columns(io::stdout().as_fd()))
            .flatten()
    }
    #[cfg(windows)]
    {
        let _ = is_terminal;
        command::terminal_columns()
    }
}
fn dispatch(
    verdict: Verdict,
    parsed: &awscli_argparse::ParseResult,
    environment: &cli_error::Environment<'_, SnapshotEnv>,
    directory: &std::path::Path,
) -> io::Result<Outcome> {
    match verdict {
        Verdict::Python(reason) => Ok(Outcome::Python(reason)),
        Verdict::Failure(failure) => {
            match cli_error::dispose_failure(environment, parsed, &failure) {
                cli_error::Disposition::Python(reason) => Ok(Outcome::Python(reason)),
                cli_error::Disposition::Render(rendering) => {
                    cli_error::render(
                        &mut TextStream::new(io::stderr().lock()),
                        &failure,
                        rendering,
                    )?;
                    Ok(Outcome::Status(
                        cli_error::exit_status(cli_error::Category::from_class(failure.class))
                            as crate::HostExitStatus,
                    ))
                }
            }
        }
        Verdict::Native(native) => {
            if let Some(reason) = cli_error::dispose_native(environment) {
                return Ok(Outcome::Python(reason));
            }
            let status = crate::bootstrap::run_after_preparation(
                || crate::bootstrap::prepare_native(environment.env),
                || Ok(run_admitted(&native, environment, parsed, directory)),
            )?;
            Ok(Outcome::Status(status as crate::HostExitStatus))
        }
    }
}

/// Hands the untouched argv to the embedded Python CLI, which reports the
/// native side's version and names `reason` in every request's User-Agent;
/// native-only mode rejects every fallback, including error rendering. A CRT
/// process lock routing took is released first: the embedded CLI takes it
/// itself, and would read this process holding it as another CLI running the
/// CRT client.
fn run_python(
    env: &SnapshotEnv,
    argv: &[OsString],
    reason: cli_error::PythonReason,
) -> io::Result<crate::HostExitStatus> {
    crt::process_lock::release();
    if cli_router::routing_mode(env.var(cli_router::ROUTING_ENV_VAR))
        == cli_router::RoutingMode::Native
    {
        let refusal = format!(
            "aws: AWS_CLI_NATIVE_ROUTER=native: native implementation unavailable ({}); \
             Python fallback disabled\n",
            reason.name(),
        );
        let _ = TextStream::new(io::stderr()).write_all(refusal.as_bytes());
        return Ok(255);
    }
    crate::python::run(
        python_fallback::Invocation::new(argv)
            .user_agent_version(cli_core::AWS_CLI_VERSION)
            .user_agent_metadata(FALLBACK_METADATA, reason.name()),
    )
}

fn run_admitted(
    native: &cli_router::Native,
    environment: &cli_error::Environment<'_, SnapshotEnv>,
    parsed: &awscli_argparse::ParseResult,
    directory: &std::path::Path,
) -> u8 {
    let format = cli_error::command_failure_format(environment, parsed);
    let context = command::CommandContext {
        env: environment.env,
        shared_files: environment.shared_files,
        globals: &native.globals,
        directory,
        payload: payload(),
        client: &native.client,
    };
    install_permanent_sigint_watcher();
    let mut streams = (
        command_stdout(&native.command),
        command_stderr(&native.command),
    );
    let outcome = run_with_debug(native, &context, environment.argv, &mut streams);
    cli_error::forget_unkept_stderr(&mut streams.1);
    let termination = match outcome {
        Ok(status) => cli_error::Termination::Exited(status),
        Err(failure) => report_command_failure(&mut streams.1, &failure, format),
    };
    cli_error::flush_streams_at_exit(&mut streams.0, &mut streams.1, termination)
}
fn command_stdout(command: &cli_router::Command) -> BufferedStream<CommandStdout> {
    match command {
        cli_router::Command::S3Ls(_) => {
            BufferedStream::new(CommandStdout::unlocked(), LISTING_STDOUT_BYTES)
        }
        cli_router::Command::S3Cp(_)
        | cli_router::Command::S3Mv(_)
        | cli_router::Command::S3Rm(_)
        | cli_router::Command::S3Sync(_) => BufferedStream::new(
            CommandStdout::open(),
            cli_error::stream_buffer_len(cli_error::StandardStream::Stdout),
        ),
    }
}
fn command_stderr(command: &cli_router::Command) -> BufferedStream<Descriptor> {
    let capacity = match command {
        cli_router::Command::S3Ls(_) => REPORT_STDERR_BYTES,
        cli_router::Command::S3Cp(_)
        | cli_router::Command::S3Mv(_)
        | cli_router::Command::S3Rm(_)
        | cli_router::Command::S3Sync(_) => {
            cli_error::stream_buffer_len(cli_error::StandardStream::Stderr)
        }
    };
    BufferedStream::new(Descriptor::stderr(), capacity)
}
fn report_command_failure(
    stderr: &mut BufferedStream<Descriptor>,
    failure: &cli_error::CommandFailure,
    format: cli_error::ErrorFormat,
) -> cli_error::Termination {
    let reported =
        cli_error::render_command_failure(&mut TextStream::new(&mut *stderr), failure, format)
            .and_then(|()| stderr.flush());
    match reported {
        Ok(()) => cli_error::Termination::Exited(cli_error::exit_status(failure.category)),
        Err(_) => cli_error::Termination::Unreported,
    }
}
fn payload() -> &'static [u8] {
    pyload::embedded()
}
fn payload_embeds_trust() -> bool {
    s3::command::embeds_trust_bundle(payload())
}
fn install_permanent_sigint_watcher() {
    if let Ok(watcher) = cli_core::interrupt::install_process_watcher() {
        std::mem::forget(watcher);
    }
}
fn run_with_debug(
    native: &cli_router::Native,
    context: &command::CommandContext<'_, SnapshotEnv>,
    argv: &[OsString],
    streams: &mut CommandStreams,
) -> Result<u8, cli_error::CommandFailure> {
    let logger = crt::debug::Logger::new(native.globals.debug);
    logger.record(
        "awscli.clidriver",
        &format!("CLI version: aws-cli/{} native", cli_core::AWS_CLI_VERSION),
    );
    logger.arguments(argv);
    if native.globals.debug {
        log_credential_source(&logger, native, context);
        native.client.log_resolved(
            cli_core::proxy::Environment::from_map(context.env),
            |line| {
                logger.record_bytes("awscli.native.config", line);
            },
        );
    }
    run_native(native, context, streams)
}
fn log_credential_source(
    logger: &crt::debug::Logger,
    native: &cli_router::Native,
    context: &command::CommandContext<'_, SnapshotEnv>,
) {
    let signing = &native.client.signing;
    let credentials = if signing.value {
        let profile = cli_core::aws_profile::select_or_default(
            context.env,
            context.globals.profile.as_deref(),
        );
        format!(
            "Credential source: {} (profile: {})",
            command::credential_source(context),
            profile.display()
        )
    } else {
        format!(
            "Credential source: none, requests are unsigned ({})",
            signing.source
        )
    };
    logger.record("awscli.native.credentials", &credentials);
}
fn run_native(
    native: &cli_router::Native,
    context: &command::CommandContext<'_, SnapshotEnv>,
    (stdout, stderr): &mut CommandStreams,
) -> Result<u8, cli_error::CommandFailure> {
    let mut stdout = TextStream::new(stdout);
    match &native.command {
        // A listing writes its own stderr straight to descriptor 2, so a
        // stderr open without write access fails the write the standard
        // library's stderr would report as written.
        cli_router::Command::S3Ls(args) => s3::ls::run(
            context,
            args,
            &mut stdout,
            &mut TextStream::new(Descriptor::stderr()),
        ),
        cli_router::Command::S3Cp(args) => {
            s3::cp::run(context, args, &mut stdout, &mut TextStream::new(stderr))
        }
        cli_router::Command::S3Mv(args) => {
            s3::mv::run(context, args, &mut stdout, &mut TextStream::new(stderr))
        }
        cli_router::Command::S3Rm(args) => {
            s3::rm::run(context, args, &mut stdout, &mut TextStream::new(stderr))
        }
        cli_router::Command::S3Sync(args) => {
            s3::sync::run(context, args, &mut stdout, &mut TextStream::new(stderr))
        }
    }
}
