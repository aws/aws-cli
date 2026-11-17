use super::listing::{execute_to_file, invalid_target_failure};
use super::{Args, Backend, Entry, ListExecutionOptions, Request};
use crate::{
    command::{self, PreparedRuntime},
    endpoint::RuleError,
    list_stats, transfer, uri,
};
use cli_core::{
    EnvMap,
    cli_error::{Category, CommandFailure},
    client_config::ClientConfig,
    command::CommandContext,
    interrupt,
    output::EntryDate,
    region,
};
use crt::{
    credentials::Source,
    debug::Logger,
    redirect::Resolver,
    runtime::{BucketRuntime, RuntimeOptions},
    s3::{ListOptions, ListResult, ListStats, TransferResult},
};
use std::{io::Write, sync::Arc};

const EMPTY_REGION_MESSAGE: &str = "error: --region must not be empty";

pub(super) struct CrtBackend {
    options: RuntimeOptions,
    resolver: Option<Arc<dyn Resolver>>,
    logger: Option<Arc<Logger>>,
    pub(super) prefetch: bool,
}
impl CrtBackend {
    pub(super) fn new(
        prepared: PreparedRuntime,
        logger: Option<Arc<Logger>>,
        env: &impl EnvMap,
    ) -> Self {
        Self {
            options: prepared.options,
            resolver: prepared.resolver,
            logger,
            prefetch: list_stats::prefetch_enabled(env),
        }
    }
}
pub(super) fn runtime_failure(failure: TransferResult) -> ListResult {
    ListResult {
        transfer: TransferResult {
            response_status: 0,
            ..failure
        },
        ..ListResult::default()
    }
}
pub(super) fn list_entry(entry: crt::s3::ListEntry) -> Entry {
    Entry {
        kind: entry.kind,
        name: entry.name,
        size: entry.size,
        date: entry
            .date
            .map_or_else(EntryDate::default, |date| EntryDate {
                present: true,
                year: date.year,
                month: date.month,
                day: date.day,
                hour: date.hour,
                minute: date.minute,
                second: date.second,
            }),
    }
}
impl Backend for CrtBackend {
    fn list(
        &mut self,
        request: Request<'_>,
        callback: &mut dyn FnMut(Entry) -> i32,
        stats: Option<&mut ListStats>,
    ) -> ListResult {
        let runtime = match BucketRuntime::new(
            self.options.clone(),
            self.resolver.clone(),
            self.logger.clone(),
        ) {
            Ok(runtime) => runtime,
            Err(failure) => return runtime_failure(*failure),
        };
        let mut emit = |entry: crt::s3::ListEntry| callback(list_entry(entry));
        if let Some(bucket) = request.target.bucket {
            runtime.list_objects(
                ListOptions {
                    bucket: bucket.as_bytes(),
                    prefetch: self.prefetch,
                    prefix: request.target.prefix,
                    recursive: request.recursive,
                    page_size: request.page_size,
                    request_payer: request.request_payer.unwrap_or("").as_bytes(),
                    user_agent: None,
                    object_conditions: false,
                },
                stats,
                &mut emit,
                interrupt::process_state(),
            )
        } else {
            runtime.original().list_buckets(
                request.bucket_name_prefix.unwrap_or("").as_bytes(),
                request.bucket_region.unwrap_or("").as_bytes(),
                request.page_size,
                &mut emit,
            )
        }
    }
}
/// Runs `s3 ls` for an invocation the router admitted: the region first,
/// then the target, then the endpoint of its bucket, then the listing. A
/// listing request that fails is the command's failure, which the AWS CLI's
/// error-handler chain frames.
pub fn run(
    context: &CommandContext<'_, impl EnvMap>,
    args: &Args,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
) -> Result<u8, CommandFailure> {
    region(context)?;
    let target = uri::parse_s3_list_target(Some(args.paths.as_encoded_bytes()))
        .map_err(invalid_target_failure)?;
    let mut prepared = endpoint(context, target.bucket)?;
    // Botocore resolves the endpoint before it encodes the request.
    encode(target, args)?;
    prepared.options = list_runtime_options(context.client, prepared.options);
    let endpoint_url = prepared.options.endpoint_url.clone();
    let credentials = prepared.options.credentials.clone();
    let logger = Some(Logger::new(context.globals.debug));
    let mut backend = CrtBackend::new(prepared, logger, context.env);
    let options = ListExecutionOptions::new(args, target, list_stats::enabled(context.env));
    execute_to_file(&mut backend, options, stdout, stderr, &endpoint_url)
        .map_err(|failure| refresh_failure(failure, &credentials))
}
/// A listing the signer failed for want of credentials, as botocore fails
/// it: with the error of the refresh the request waited for, which the
/// general handler reports, when the chain's credentials were due one, and
/// with `failure`, its NoCredentialsError, when the chain found none. The
/// signer reports both as one code.
pub(super) fn refresh_failure(failure: CommandFailure, credentials: &Source) -> CommandFailure {
    if failure.category != Category::NoCredentials {
        return failure;
    }
    match credentials.failure() {
        Some(error) => command::failure(error),
        None => failure,
    }
}
fn region<'c>(context: &CommandContext<'c, impl EnvMap>) -> Result<&'c str, CommandFailure> {
    let globals = context.globals;
    region::resolve_region(
        context.env,
        context.shared_files,
        globals.region.as_deref(),
        globals.profile.as_deref(),
    )
    .map_err(|_| command::failure(EMPTY_REGION_MESSAGE))
}
fn endpoint(
    context: &CommandContext<'_, impl EnvMap>,
    bucket: Option<&str>,
) -> Result<PreparedRuntime, CommandFailure> {
    let mut prepared = command::copy_runtime_options(context, bucket, false)?;
    match prepared.refusal.take() {
        Some(rule_error) => Err(rule_command_failure(rule_error)),
        None => Ok(prepared),
    }
}
pub(super) fn encode(target: uri::S3ListTarget<'_>, args: &Args) -> Result<(), CommandFailure> {
    let values = if target.bucket.is_some() {
        vec![target.prefix]
    } else {
        [&args.bucket_name_prefix, &args.bucket_region]
            .into_iter()
            .flatten()
            .map(|value| value.as_encoded_bytes())
            .collect()
    };
    match values.into_iter().find_map(transfer::key_encode_refusal) {
        Some(refusal) => Err(command::failure(refusal)),
        None => Ok(()),
    }
}
fn rule_command_failure(rule_error: RuleError) -> CommandFailure {
    command::failure(rule_error.message)
}
pub(super) fn list_runtime_options(
    client: &ClientConfig,
    options: RuntimeOptions,
) -> RuntimeOptions {
    RuntimeOptions {
        throughput_target_gbps: client.target_gbps.value,
        memory_limit_in_bytes: client.memory_bytes(),
        ..options
    }
}
