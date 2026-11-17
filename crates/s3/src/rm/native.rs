use super::{Args, DeletePlan, Selection, make_delete_filter, make_delete_plan};
use crate::cp::recursive::{
    ChecksumSettings, DeleteOptions, RequestHeaders, SingleObject, TransferRequest,
};
use crate::transfer::{Direction, GlacierPolicy};
use crate::{command, config, cp, list_stats, results};
use cli_core::EnvMap;
use cli_core::cli_error::CommandFailure;
use cli_core::command::CommandContext;
use crt::runtime::RuntimeOptions;
use std::io::Write;
use std::path::PathBuf;

/// Runs `s3 rm` for an invocation the router admitted.
///
/// It loads the settings, then the bucket's client inputs, then builds the
/// client a refused request still builds, then runs the deletes, whose
/// results the command's printer reports. The status is 1 when a setting,
/// the region, or the profile fails with a native diagnostic on `stderr`,
/// and otherwise the deletes' own.
///
/// # Errors
/// Returns the [`CommandFailure`] the general handler reports: client inputs
/// only it renders, a diagnostic or result line that cannot be written, a
/// client the refused request cannot build, or a result printer that cannot
/// start.
pub fn run(
    context: &CommandContext<'_, impl EnvMap>,
    args: &Args,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let plan = make_delete_plan(args);
    let Some(settings) = cp::load_settings(context, config::Operation::Other, stderr)? else {
        return Ok(1);
    };
    let Some(prepared) = cp::prepare_runtime(context, plan.bucket, Direction::Delete, stderr)?
    else {
        return Ok(1);
    };
    let sizing = client_sizing(context, &plan, &settings);
    validate_refused_client(context, &prepared, &sizing)?;
    let request = TransferRequest {
        direction: Direction::Delete,
        bucket: plan.bucket.into(),
        prefix: match plan.selection {
            Selection::Prefix => plan.listing_prefix(),
            Selection::Object | Selection::FolderMarkers => Vec::new(),
        },
        local_root: PathBuf::new(),
        runtime: prepared.options,
        quiet: args.quiet,
        dryrun: args.dryrun,
        no_overwrite: false,
        glacier: GlacierPolicy::Transfer,
        content_types: None,
        refusal: prepared.refusal.map(|refusal| refusal.message),
        page_size: plan.page_size,
        max_in_flight: settings.resolve_in_flight_max(),
        collect_stats: list_stats::enabled(context.env),
        prefetch: list_stats::prefetch_enabled(context.env),
        sizing,
        download: None,
        object: (plan.selection == Selection::Object).then(|| SingleObject {
            key: plan.key.to_vec(),
            ..SingleObject::default()
        }),
        filter: make_delete_filter(args, &plan),
        headers: RequestHeaders {
            request_payer: plan.request_payer,
            object: Vec::new(),
        },
        checksums: ChecksumSettings::default(),
        delete: delete_options(&plan),
        sources: Default::default(),
        sync: None,
        listing_user_agent: (plan.selection != Selection::Object)
            .then(|| command::listing_user_agent(context.client)),
        links: Default::default(),
    };
    cp::run_request(
        context,
        prepared.resolver,
        request,
        &args.paths[0],
        printer(args),
        stdout,
        stderr,
    )
}

fn validate_refused_client(
    context: &CommandContext<'_, impl EnvMap>,
    prepared: &command::PreparedRuntime,
    sizing: &config::ClientSizing,
) -> Result<(), CommandFailure> {
    let Some(refusal) = &prepared.refusal else {
        return Ok(());
    };
    let client = RuntimeOptions {
        max_active_connections_override: sizing.max_connections,
        ..prepared.options.clone()
    };
    let endpoint_url = refusal.client_url.as_deref().unwrap_or_default();
    command::validate_refused_client(&client, endpoint_url, context.globals.debug)
}
fn delete_options(plan: &DeletePlan<'_>) -> DeleteOptions {
    DeleteOptions {
        folder_markers_only: plan.selection == Selection::FolderMarkers,
    }
}

fn printer(args: &Args) -> Option<results::PrinterConfig> {
    results::Flags {
        quiet: args.quiet,
        only_show_errors: args.only_show_errors,
        progress: false,
        ..results::Flags::default()
    }
    .select()
}

fn client_sizing(
    context: &CommandContext<'_, impl EnvMap>,
    plan: &DeletePlan<'_>,
    settings: &config::Settings,
) -> config::ClientSizing {
    let client = context.client;
    config::resolve_client_sizing(&config::SizingInputs {
        direction: Direction::Delete,
        shape: match plan.selection {
            Selection::Object => config::Shape::OneObject,
            Selection::Prefix | Selection::FolderMarkers => config::Shape::ManyObjects,
        },
        target_gbps: client.target_gbps.value,
        memory_limit: client.memory_limit.value,
        part_size: client.part_size.value,
        max_connections: client.max_connections.clone(),
        in_flight_max: settings.resolve_in_flight_max(),
        configured_writer: None,
    })
}
