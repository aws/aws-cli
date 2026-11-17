use super::recursive;
use crate::cp_args::{Args, CopyPlan, Operation};
use crate::download::platform::{NativePlatform, Platform};
use crate::object_settings::ChecksumAlgorithm;
use crate::scheduler::EntryLocal;
use crate::transfer::Direction;
use crate::{command, config, cp_args, transfer, uri};
use cli_core::cli_error::{Category, CommandFailure};
use cli_core::command::CommandContext;
use cli_core::{EnvMap, interrupt};
use crt::runtime::RuntimeOptions;
use std::ffi::{OsStr, OsString};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Arc;

mod crt_backend;

/// Runs `s3 cp` for an invocation the router admitted.
///
/// # Errors
/// Returns the [`CommandFailure`] the transfer returns.
pub fn run(
    context: &CommandContext<'_, impl EnvMap>,
    args: &Args,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let mode = CopyMode {
        sync: args.case_conflict_strategies(),
        ..CopyMode::default()
    };
    run_copy(context, args, mode, stdout, stderr)
}
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub(crate) struct CopyMode {
    pub(crate) sources: transfer::SourceDisposition,
    pub(crate) sync: Option<crate::sync::Strategies>,
}
pub(crate) fn run_copy(
    context: &CommandContext<'_, impl EnvMap>,
    args: &Args,
    mode: CopyMode,
    stdout: &mut (dyn Write + Send),
    mut stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let plan = cp_args::make_copy_plan_with_globals(args, context.globals);
    require_checksum_direction(&plan)?;
    require_upload_source(&plan)?;
    prepare_recursive_download_destination(&plan)?;
    require_customer_key_pair(&plan)?;
    let cwd = operand_working_directory(context.directory, &plan)?;
    let filter = cp_args::make_copy_filter(&plan, &cwd);
    let sync = mode.sync.map(|strategies| crate::sync::Plan {
        strategies,
        destination_filter: cp_args::make_sync_destination_filter(&plan, &cwd),
    });
    let local = normalize_local_operand(&cwd, &plan);
    let plan = if plan.operation.uploads() {
        CopyPlan {
            source: &local,
            ..plan
        }
    } else {
        CopyPlan {
            destination: &local,
            ..plan
        }
    };
    let Some(settings) = load_settings(context, config_operation(plan.operation), &mut stderr)?
    else {
        return Ok(1);
    };
    let Some(options) = prepare_runtime(
        context,
        bucket(plan.operation),
        plan.operation.direction(),
        &mut stderr,
    )?
    else {
        return Ok(1);
    };
    let sources = Sources { filter, mode, sync };
    dispatch(
        context,
        &plan,
        sources,
        &settings,
        options,
        stdout,
        &mut stderr,
    )
}
#[derive(Debug)]
struct Sources {
    filter: crate::filter::Filter,
    mode: CopyMode,
    sync: Option<crate::sync::Plan>,
}
pub(crate) fn load_settings(
    context: &CommandContext<'_, impl EnvMap>,
    operation: config::Operation,
    stderr: &mut (dyn Write + Send),
) -> Result<Option<config::Settings>, CommandFailure> {
    match config::load(
        context.env,
        context.shared_files,
        operation,
        context.globals.profile.as_deref(),
    ) {
        Ok(settings) => Ok(Some(settings)),
        Err(error) => {
            stderr
                .write_all(error.message.as_bytes())
                .and_then(|()| stderr.flush())
                .map_err(io_failure)?;
            Ok(None)
        }
    }
}
pub(crate) fn prepare_runtime(
    context: &CommandContext<'_, impl EnvMap>,
    bucket: &str,
    direction: Direction,
    stderr: &mut (dyn Write + Send),
) -> Result<Option<command::PreparedRuntime>, CommandFailure> {
    let uploads = direction == Direction::Upload;
    match command::copy_runtime_options(context, Some(bucket), uploads) {
        Ok(options) => Ok(Some(options)),
        Err(error)
            if error.message.starts_with(b"error:")
                || error.message.starts_with(b"The profile is configured") =>
        {
            stderr.write_all(&error.message).map_err(io_failure)?;
            stderr
                .write_all(b"\n")
                .and_then(|()| stderr.flush())
                .map_err(io_failure)?;
            Ok(None)
        }
        Err(error) => Err(error),
    }
}
pub(crate) fn run_request(
    context: &CommandContext<'_, impl EnvMap>,
    resolver: Option<Arc<dyn crt::redirect::Resolver>>,
    request: recursive::TransferRequest,
    operand: &OsStr,
    printer: Option<crate::results::PrinterConfig>,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let env = crt_backend::NativeEnv {
        cwd: context.directory,
        debug: context.globals.debug,
        resolver,
    };
    crt_backend::run(
        request,
        &env,
        operand,
        printer,
        &context.client.ignored.to_string(),
        stdout,
        stderr,
    )
}
fn validate_refused_client(
    context: &CommandContext<'_, impl EnvMap>,
    plan: &CopyPlan<'_>,
    sources: &Sources,
    settings: &config::Settings,
    prepared: &command::PreparedRuntime,
) -> Result<Option<String>, CommandFailure> {
    let syncs = sources.mode.sync.is_some();
    let (endpoint_url, key_refusal) = match &prepared.refusal {
        Some(refusal) => (refusal.client_url.as_deref().unwrap_or_default(), None),
        None => match generator_key_refusal(plan.operation, syncs) {
            Some(key_refusal) => (prepared.options.endpoint_url.as_str(), Some(key_refusal)),
            None => return Ok(None),
        },
    };
    let client = RuntimeOptions {
        max_active_connections_override: client_sizing(context, plan, settings).max_connections,
        ..prepared.options.clone()
    };
    command::validate_refused_client(&client, endpoint_url, context.globals.debug)?;
    Ok(key_refusal)
}
fn generator_key_refusal(operation: Operation<'_>, syncs: bool) -> Option<String> {
    match operation {
        Operation::SingleDownload(remote) => transfer::key_encode_refusal(remote.key),
        Operation::RecursiveDownload(remote) => {
            transfer::key_encode_refusal(&uri::normalize_recursive_s3_prefix(remote.prefix))
        }
        Operation::RecursiveUpload(remote) if syncs => {
            transfer::key_encode_refusal(&uri::normalize_recursive_s3_prefix(remote.prefix))
        }
        Operation::SingleUpload(_) | Operation::RecursiveUpload(_) => None,
    }
}
fn require_upload_source(plan: &CopyPlan<'_>) -> Result<(), CommandFailure> {
    if plan.operation.uploads() && !Path::new(plan.source).try_exists().unwrap_or(false) {
        return Err(command::failure(
            [
                b"The user-provided path ".as_slice(),
                plan.source.as_encoded_bytes(),
                b" does not exist.",
            ]
            .concat(),
        ));
    }
    Ok(())
}
fn require_checksum_direction(plan: &CopyPlan<'_>) -> Result<(), CommandFailure> {
    match plan.settings.checksum_refusal(plan.operation.direction()) {
        Some(refusal) => Err(CommandFailure {
            message: refusal.message().into(),
            ..CommandFailure::new(Category::ParamValidation)
        }),
        None => Ok(()),
    }
}
/// Upstream refuses one customer key setting without the other once it has
/// checked the paths, before any client (`CommandParameters.add_paths`).
fn require_customer_key_pair(plan: &CopyPlan<'_>) -> Result<(), CommandFailure> {
    match plan.settings.customer_key_refusal() {
        Some(refusal) => Err(CommandFailure {
            message: refusal.message().into(),
            ..CommandFailure::new(Category::ParamValidation)
        }),
        None => Ok(()),
    }
}
fn request_headers(plan: &CopyPlan<'_>) -> recursive::RequestHeaders {
    recursive::RequestHeaders {
        request_payer: plan.settings.request_payer,
        object: if plan.operation.uploads() {
            plan.settings.upload_headers()
        } else {
            plan.settings.download_headers()
        },
    }
}
fn checksum_settings(plan: &CopyPlan<'_>) -> recursive::ChecksumSettings {
    recursive::ChecksumSettings {
        upload_algorithm: plan.settings.checksum_algorithm.map(ChecksumAlgorithm::crt),
        validate_downloads: plan.settings.checksum_mode.is_some(),
    }
}
fn content_types(plan: &CopyPlan<'_>) -> Option<Arc<crate::mime::Database>> {
    (plan.operation.uploads() && plan.guess_mime_type && plan.settings.content_type.is_none())
        .then(|| Arc::new(crate::mime::Database::load()))
}
/// Upstream also prepares a missing recursive download destination before
/// abspath: normalization must not erase a failing raw directory component.
fn prepare_recursive_download_destination(plan: &CopyPlan<'_>) -> Result<(), CommandFailure> {
    if matches!(plan.operation, Operation::RecursiveDownload(_))
        && !Path::new(plan.destination).try_exists().unwrap_or(false)
    {
        transfer::create_local_dir_path(Path::new(plan.destination))
            .map_err(|error| command::failure(transfer::create_dir_error_name(&error)))?;
    }
    Ok(())
}
fn local_operand<'a>(plan: &CopyPlan<'a>) -> &'a Path {
    Path::new(if plan.operation.uploads() {
        plan.source
    } else {
        plan.destination
    })
}
fn operand_working_directory(
    directory: &Path,
    plan: &CopyPlan<'_>,
) -> Result<PathBuf, CommandFailure> {
    if local_operand(plan).is_absolute() {
        Ok(PathBuf::new())
    } else if directory.is_absolute() {
        Ok(directory.to_path_buf())
    } else {
        std::env::current_dir().map_err(|error| {
            command::failure(super::backstop::SetupError::current_dir(&error).name())
        })
    }
}
/// `FileFormat.local_format` applies `abspath` after the raw source existence
/// check, so the local operand resolves lexically, not through symlinks,
/// before any transfer work.
fn normalize_local_operand(cwd: &Path, plan: &CopyPlan<'_>) -> OsString {
    let original = local_operand(plan);
    let absolute = crate::local_path::absolute_path(cwd, original);
    let directory_intent = original
        .as_os_str()
        .as_encoded_bytes()
        .last()
        .is_some_and(|byte| *byte == b'/' || (cfg!(windows) && *byte == b'\\'));
    if directory_intent {
        transfer::normalize_local_directory_root(&absolute).into_os_string()
    } else {
        absolute.into_os_string()
    }
}
fn config_operation(operation: Operation<'_>) -> config::Operation {
    match operation {
        Operation::SingleDownload(_) => config::Operation::SingleDownload,
        Operation::SingleUpload(_) => config::Operation::SingleUpload,
        Operation::RecursiveDownload(_) => config::Operation::RecursiveDownload,
        Operation::RecursiveUpload(_) => config::Operation::RecursiveUpload,
    }
}
fn sizing_inputs(
    context: &CommandContext<'_, impl EnvMap>,
    operation: Operation<'_>,
    settings: &config::Settings,
) -> config::SizingInputs {
    let client = context.client;
    config::SizingInputs {
        direction: operation.direction(),
        shape: match operation {
            Operation::SingleDownload(_) | Operation::SingleUpload(_) => config::Shape::OneObject,
            Operation::RecursiveDownload(_) | Operation::RecursiveUpload(_) => {
                config::Shape::ManyObjects
            }
        },
        target_gbps: client.target_gbps.value,
        memory_limit: client.memory_limit.value,
        part_size: client.part_size.value,
        max_connections: client.max_connections.clone(),
        in_flight_max: settings.resolve_in_flight_max(),
        configured_writer: settings.download_writer,
    }
}
fn client_sizing(
    context: &CommandContext<'_, impl EnvMap>,
    plan: &CopyPlan<'_>,
    settings: &config::Settings,
) -> config::ClientSizing {
    config::resolve_client_sizing(&sizing_inputs(context, plan.operation, settings))
}
fn bucket(operation: Operation<'_>) -> &str {
    match operation {
        Operation::SingleDownload(uri) | Operation::SingleUpload(uri) => uri.bucket,
        Operation::RecursiveDownload(uri) | Operation::RecursiveUpload(uri) => uri.bucket,
    }
}
fn dispatch(
    context: &CommandContext<'_, impl EnvMap>,
    plan: &CopyPlan<'_>,
    sources: Sources,
    settings: &config::Settings,
    options: command::PreparedRuntime,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let key_refusal = validate_refused_client(context, plan, &sources, settings, &options)?;
    let env = crt_backend::NativeEnv {
        cwd: context.directory,
        debug: context.globals.debug,
        resolver: options.resolver.clone(),
    };
    let request = match plan.operation {
        Operation::SingleDownload(remote) => {
            let mut request = single_download_request(context, plan, remote, settings, options);
            request.refusal = request.refusal.or(key_refusal);
            request
        }
        Operation::SingleUpload(remote) => {
            single_upload_request(context, plan, remote, settings, options)
        }
        Operation::RecursiveDownload(remote) | Operation::RecursiveUpload(remote) => {
            let mut request = recursive_request(context, plan, remote, settings, options.options);
            request.refusal = options
                .refusal
                .map(|refusal| refusal.message)
                .or(key_refusal);
            request
        }
    };
    let request = recursive::TransferRequest {
        filter: sources.filter,
        sources: sources.mode.sources,
        // Upstream lists a sync's source or destination through a botocore
        // client's paginator (`CommandArchitecture.run`).
        listing_user_agent: sources
            .sync
            .as_ref()
            .map(|_| command::listing_user_agent(context.client)),
        sync: sources.sync,
        ..request
    };
    run_transfer(context, &env, plan, request, stdout, stderr)
}
/// Runs `request` on the shared runner with the command's output.
fn run_transfer(
    context: &CommandContext<'_, impl EnvMap>,
    env: &crt_backend::NativeEnv<'_>,
    plan: &CopyPlan<'_>,
    request: recursive::TransferRequest,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    crt_backend::run(
        request,
        env,
        plan.source,
        plan.printer,
        &context.client.ignored.to_string(),
        stdout,
        stderr,
    )
}
fn download_destination(destination: &OsStr, key: &[u8]) -> (PathBuf, EntryLocal) {
    let destination = Path::new(destination);
    let directory = std::fs::metadata(destination).is_ok_and(|metadata| metadata.is_dir());
    let trailing_separator = destination
        .as_os_str()
        .as_encoded_bytes()
        .last()
        .is_some_and(|&byte| std::path::is_separator(char::from(byte)));
    if !directory && !trailing_separator {
        return (destination.to_path_buf(), EntryLocal::Resolved);
    }
    let key = String::from_utf8_lossy(key);
    let basename = key.rsplit('/').next().unwrap_or_default();
    if uri::relative_key_escapes_root(basename) {
        return (
            destination.to_path_buf(),
            EntryLocal::ParentEscape(basename.into()),
        );
    }
    let path = destination.join(basename);
    if uri::relative_key_names_root_parent(basename) {
        (path, EntryLocal::RootParent)
    } else {
        (path, EntryLocal::Resolved)
    }
}
fn single_download_request(
    context: &CommandContext<'_, impl EnvMap>,
    plan: &CopyPlan<'_>,
    remote: uri::S3Uri<'_>,
    settings: &config::Settings,
    prepared: command::PreparedRuntime,
) -> recursive::TransferRequest {
    let (local_path, local) = download_destination(plan.destination, remote.key);
    recursive::TransferRequest {
        direction: Direction::Download,
        bucket: remote.bucket.into(),
        prefix: Vec::new(),
        local_root: PathBuf::new(),
        runtime: prepared.options,
        quiet: plan.quiet,
        dryrun: plan.dryrun,
        no_overwrite: plan.no_overwrite,
        glacier: transfer::GlacierPolicy::from_flags(
            plan.force_glacier_transfer,
            plan.ignore_glacier_warnings,
        ),
        content_types: None,
        refusal: prepared.refusal.map(|refusal| refusal.message),
        page_size: 0,
        max_in_flight: settings.resolve_in_flight_max(),
        collect_stats: crate::list_stats::enabled(context.env),
        prefetch: false,
        sizing: client_sizing(context, plan, settings),
        download: Some(
            settings.resolve_download().with_direct_io(
                context
                    .client
                    .download_direct_io(NativePlatform.page_size() as u64),
            ),
        ),
        object: Some(recursive::SingleObject {
            key: remote.key.to_vec(),
            local_path,
            local,
            remote: Some(plan.source.to_os_string()),
        }),
        delete: Default::default(),
        filter: crate::filter::Filter::default(),
        headers: request_headers(plan),
        checksums: checksum_settings(plan),
        sources: Default::default(),
        sync: None,
        listing_user_agent: None,
        links: link_policy(plan),
    }
}
fn single_upload_request(
    context: &CommandContext<'_, impl EnvMap>,
    plan: &CopyPlan<'_>,
    remote: uri::S3Uri<'_>,
    settings: &config::Settings,
    prepared: command::PreparedRuntime,
) -> recursive::TransferRequest {
    let local_path = single_upload_source_path(plan.source);
    let key = cp_args::resolve_single_upload_key(remote.key, &local_path);
    let remote_name = (key == remote.key).then(|| plan.destination.to_os_string());
    recursive::TransferRequest {
        direction: Direction::Upload,
        bucket: remote.bucket.into(),
        prefix: Vec::new(),
        local_root: PathBuf::new(),
        runtime: prepared.options,
        quiet: plan.quiet,
        dryrun: plan.dryrun,
        no_overwrite: plan.no_overwrite,
        glacier: transfer::GlacierPolicy::Warn,
        content_types: content_types(plan),
        refusal: prepared.refusal.map(|refusal| refusal.message),
        page_size: 0,
        max_in_flight: settings.resolve_in_flight_max(),
        collect_stats: crate::list_stats::enabled(context.env),
        prefetch: false,
        sizing: client_sizing(context, plan, settings),
        download: None,
        object: Some(recursive::SingleObject {
            key,
            local_path,
            local: EntryLocal::Resolved,
            remote: remote_name,
        }),
        delete: Default::default(),
        filter: crate::filter::Filter::default(),
        headers: request_headers(plan),
        checksums: checksum_settings(plan),
        sources: Default::default(),
        sync: None,
        listing_user_agent: None,
        links: link_policy(plan),
    }
}
/// The single upload's source as upstream's `local_format` spells it: an
/// existing directory, following symlinks, ends with a separator.
fn single_upload_source_path(source: &OsStr) -> PathBuf {
    let source = Path::new(source);
    if std::fs::metadata(source).is_ok_and(|metadata| metadata.is_dir()) {
        transfer::normalize_local_directory_root(source)
    } else {
        source.to_path_buf()
    }
}
fn recursive_request(
    context: &CommandContext<'_, impl EnvMap>,
    plan: &CopyPlan<'_>,
    remote: uri::S3PrefixUri<'_>,
    settings: &config::Settings,
    runtime: RuntimeOptions,
) -> recursive::TransferRequest {
    let download = matches!(plan.operation, Operation::RecursiveDownload(_));
    recursive::TransferRequest {
        direction: if download {
            Direction::Download
        } else {
            Direction::Upload
        },
        bucket: remote.bucket.into(),
        prefix: uri::normalize_recursive_s3_prefix(remote.prefix),
        local_root: transfer::normalize_local_directory_root(Path::new(if download {
            plan.destination
        } else {
            plan.source
        })),
        runtime,
        quiet: plan.quiet,
        dryrun: plan.dryrun,
        no_overwrite: plan.no_overwrite,
        glacier: transfer::GlacierPolicy::from_flags(
            plan.force_glacier_transfer,
            plan.ignore_glacier_warnings,
        ),
        content_types: content_types(plan),
        refusal: None,
        page_size: plan.page_size,
        max_in_flight: settings.resolve_in_flight_max(),
        collect_stats: crate::list_stats::enabled(context.env),
        prefetch: crate::list_stats::prefetch_enabled(context.env),
        sizing: client_sizing(context, plan, settings),
        download: download.then(|| {
            settings.resolve_download().with_direct_io(
                context
                    .client
                    .download_direct_io(NativePlatform.page_size() as u64),
            )
        }),
        object: None,
        delete: Default::default(),
        filter: crate::filter::Filter::default(),
        headers: request_headers(plan),
        checksums: checksum_settings(plan),
        sources: Default::default(),
        sync: None,
        listing_user_agent: None,
        links: link_policy(plan),
    }
}
fn link_policy(plan: &CopyPlan<'_>) -> transfer::LinkPolicy {
    transfer::LinkPolicy::from_flag(plan.follow_symlinks, local_operand(plan))
}
fn io_failure(error: std::io::Error) -> CommandFailure {
    if error.kind() == std::io::ErrorKind::BrokenPipe {
        return command::failure(cli_core::cli_error::BROKEN_PIPE_MESSAGE);
    }
    command::failure(super::io_error_name(&error))
}

#[cfg(test)]
mod tests;
