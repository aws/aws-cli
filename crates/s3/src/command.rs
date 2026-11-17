//! Shared endpoint and credential inputs for admitted native S3 commands.
mod cacert;

use crate::credentials::Chain;
use cli_core::cli_error::{Category, CommandFailure};
use cli_core::command::CommandContext;
use cli_core::{EnvMap, aws_profile, region};
use crt::redirect::Resolver;
use crt::runtime::RuntimeOptions;
use std::sync::Arc;

/// Captures runtime options before starting any CRT worker threads.
pub fn runtime_options(
    context: &CommandContext<'_, impl EnvMap>,
    bucket: Option<&str>,
    uploads: bool,
) -> Result<RuntimeOptions, CommandFailure> {
    bucket_runtime_options(context, bucket, uploads).map(|prepared| prepared.options)
}

/// Captures runtime options and the bucket's redirect recipe; a refused
/// request is the command's failure.
pub fn bucket_runtime_options(
    context: &CommandContext<'_, impl EnvMap>,
    bucket: Option<&str>,
    uploads: bool,
) -> Result<PreparedRuntime, CommandFailure> {
    let prepared = copy_runtime_options(context, bucket, uploads)?;
    if let Some(refusal) = prepared.refusal {
        return Err(failure(refusal.message));
    }
    Ok(prepared)
}

#[derive(Debug)]
pub struct PreparedRuntime {
    pub options: RuntimeOptions,
    pub refusal: Option<crate::endpoint::RuleError>,
    /// Re-resolves the bucket after a region redirect; None for a refused
    /// request and for a bucket the redirect policy does not support.
    pub resolver: Option<Arc<dyn Resolver>>,
}

pub fn copy_runtime_options(
    context: &CommandContext<'_, impl EnvMap>,
    bucket: Option<&str>,
    uploads: bool,
) -> Result<PreparedRuntime, CommandFailure> {
    let globals = context.globals;
    let region = region::resolve_region(
        context.env,
        context.shared_files,
        globals.region.as_deref(),
        globals.profile.as_deref(),
    )
    .map_err(|_| failure("error: --region must not be empty"))?;
    let credentials = signing_credentials(context)?;
    let proxies = cli_core::proxy::Environment::from_map(context.env);
    let endpoint = match resolve_endpoint(context, proxies, region, bucket)? {
        crate::endpoint::Resolved::Endpoint(endpoint) => endpoint,
        crate::endpoint::Resolved::RuleError(refusal) => {
            let mut refused = refused_runtime(context, region, uploads, refusal);
            refused.options.credentials = credentials;
            return Ok(refused);
        }
    };
    let resolver = endpoint
        .recipe
        .map(|recipe| Arc::new(recipe) as Arc<dyn Resolver>);
    let endpoint_url = String::from_utf8(endpoint.url).map_err(|e| failure(e.to_string()))?;
    let mut options = client_options(context.client, uploads);
    let netloc = endpoint
        .client_netloc
        .as_deref()
        .unwrap_or_else(|| crate::endpoint::netloc(&endpoint_url));
    options.proxy_url = proxies
        .resolve_for(&endpoint_url, netloc)
        .map(str::to_owned);
    options.proxy_bypass_netloc = proxies.bypass(netloc).then(|| netloc.to_owned());
    options.region = region.to_owned();
    options.signing_region = endpoint.signing_region;
    options.endpoint_url = endpoint_url;
    options.credentials = credentials;
    embedded_ca(context, &mut options);
    Ok(PreparedRuntime {
        options,
        refusal: None,
        resolver,
    })
}

/// What the client signs with: the command's credential chain, walked as
/// botocore's `Session.create_client` walks its own, and nothing for an
/// unsigned client, which asks no provider.
///
/// A provider that fails here is the command's failure, raised before any
/// request, which the general handler reports with status 255.
fn signing_credentials(
    context: &CommandContext<'_, impl EnvMap>,
) -> Result<crt::credentials::Source, CommandFailure> {
    if !context.client.signing.value {
        return Ok(crt::credentials::Source::default());
    }
    let selected = context.globals.profile.as_deref();
    // The router admits a selected profile only when it has a section, so
    // its name is Unicode.
    let name = aws_profile::select_or_default(context.env, selected)
        .to_str()
        .unwrap_or("default");
    let profile = if aws_profile::is_explicit(selected) {
        ::credentials::Profile::Explicit(name)
    } else {
        ::credentials::Profile::Ambient(name)
    };
    Chain::walk(context.env, context.shared_files, profile)
        .map(|chain| chain.source())
        .map_err(|error| failure(error.to_string()))
}

fn resolve_endpoint(
    context: &CommandContext<'_, impl EnvMap>,
    proxies: cli_core::proxy::Environment<'_>,
    region: &str,
    bucket: Option<&str>,
) -> Result<crate::endpoint::Resolved, CommandFailure> {
    let globals = context.globals;
    let view = pyload::View::new(context.payload).map_err(|e| failure(e.to_string()))?;
    let region_configured = region::is_configured(
        context.env,
        context.shared_files,
        globals.region.as_deref(),
        globals.profile.as_deref(),
    );
    let mut diagnostic = Vec::new();
    crate::endpoint::resolve_configured(
        view,
        context.env,
        context.shared_files,
        region,
        bucket,
        crate::endpoint::ConfiguredInput {
            endpoint: globals.endpoint_url.as_deref(),
            region_configured,
            profile: globals.profile.as_deref(),
            s3_block: context.client.s3_block(),
            client_netloc: crate::endpoint::ClientNetloc::select(
                proxies.has_bypass_list(),
                region_configured,
            ),
        },
        &mut diagnostic,
    )
    .map_err(|error| endpoint_failure(error, &diagnostic))
}

fn refused_runtime(
    context: &CommandContext<'_, impl EnvMap>,
    region: &str,
    uploads: bool,
    refusal: crate::endpoint::RuleError,
) -> PreparedRuntime {
    let mut options = client_options(context.client, uploads);
    options.region = region.to_owned();
    embedded_ca(context, &mut options);
    PreparedRuntime {
        options,
        refusal: Some(refusal),
        resolver: None,
    }
}

/// Whether the payload embeds botocore's CA bundle, which a native client
/// trusts when nothing configures another. The entrypoint, which holds the
/// payload, tells the router (`cli_router::Configuration::embedded_trust`).
pub fn embeds_trust_bundle(payload: &[u8]) -> bool {
    cacert::find(payload).is_some()
}

fn embedded_ca(context: &CommandContext<'_, impl EnvMap>, options: &mut RuntimeOptions) {
    let embedded = matches!(
        context.client.trust.value,
        cli_core::client_config::Trust::Embedded
    );
    if let Some(pem) = embedded.then(|| cacert::find(context.payload)).flatten() {
        options.trust = crt::runtime::Trust::Pem(pem.to_vec());
    }
}

/// A refused request still has a regional client. Build and release that
/// client without submitting anything, so its setup failures precede the
/// request's rule error, or a key botocore cannot encode, and any source
/// skip (`TransferManagerFactory._create_crt_client`). Upstream's CRT client
/// resolves proxies only for a request's endpoint, so this one resolves none.
/// `endpoint_url` is the client's own for a rule error, else the refused
/// request's, which shares its scheme.
pub fn validate_refused_client(
    options: &RuntimeOptions,
    endpoint_url: &str,
    debug: bool,
) -> Result<(), CommandFailure> {
    let options = RuntimeOptions {
        endpoint_url: endpoint_url.to_owned(),
        proxy_url: None,
        proxy_bypass_netloc: None,
        ..options.clone()
    };
    let credentials = options.credentials.clone();
    crt::runtime::Runtime::new_with_logger(options, crt::debug::Logger::new(debug))
        .map(drop)
        .map_err(|result| client_failure(&result, &credentials))
}

/// A client that could not be built, which the general handler reports
/// with status 255: one the CRT could not build, or one whose credential
/// chain failed as the client was created, with the error botocore raises
/// there (`Session.create_client`). `credentials` is what the client was to
/// sign with, which holds that error.
pub fn client_failure(
    result: &crt::s3::TransferResult,
    credentials: &crt::credentials::Source,
) -> CommandFailure {
    if result.error_code == crt::s3::NO_CREDENTIALS_ERROR_CODE
        && let Some(reason) = credentials.failure()
    {
        return failure(reason);
    }
    failure(crate::cp::backstop::client_failure_message(result))
}

fn endpoint_failure(error: crate::endpoint::EndpointError, diagnostic: &[u8]) -> CommandFailure {
    if !diagnostic.is_empty() {
        return failure(diagnostic.trim_ascii_end());
    }
    failure(match error {
        crate::endpoint::EndpointError::InvalidEndpoint => {
            "error: failed to resolve the S3 endpoint".to_owned()
        }
        _ => error.to_string(),
    })
}

pub fn failure(message: impl Into<Vec<u8>>) -> CommandFailure {
    CommandFailure {
        message: message.into(),
        ..CommandFailure::new(Category::General)
    }
}

/// Translate the resolved invocation exactly once into CRT constructor inputs.
pub fn client_options(
    client: &cli_core::client_config::ClientConfig,
    uploads: bool,
) -> RuntimeOptions {
    use cli_core::client_config::{ChecksumMode, Trust, user_agent};
    let checksum = |mode| match mode {
        ChecksumMode::WhenSupported => crt::runtime::ChecksumMode::WhenSupported,
        ChecksumMode::WhenRequired => crt::runtime::ChecksumMode::WhenRequired,
    };
    RuntimeOptions {
        // The payload's bundle replaces the platform store of an embedded
        // trust in copy_runtime_options.
        trust: match &client.trust.value {
            Trust::File(path) => crt::runtime::Trust::File {
                path: path.clone(),
                setting: client.trust.source.setting_name(),
            },
            Trust::Platform | Trust::Embedded => crt::runtime::Trust::Platform,
        },
        no_sign_request: !client.signing.value,
        keep_alive: client.keep_alive.value,
        connect_timeout_ms: client.connect_timeout_ms.value,
        max_attempts: client.retry_attempts.value,
        botocore_attempts: client.botocore_attempts(),
        part_size: client.part_size.value,
        multipart_upload_threshold: client.multipart_threshold.as_ref().map(|v| v.value),
        single_request_threshold: client.multipart_threshold.as_ref().map(|v| v.value),
        max_active_connections_override: client.max_connections.as_ref().map_or(0, |v| v.value),
        throughput_target_gbps: client.target_gbps.value,
        memory_limit_in_bytes: if client.command == cli_core::client_config::Command::Ls {
            client.memory_bytes()
        } else {
            0
        },
        file_io: (client.should_stream.is_some()
            || client.disk_throughput_gbps.is_some()
            || client.direct_io.is_some())
        .then(|| crt::runtime::FileIoOptions {
            should_stream: client.should_stream.as_ref().is_some_and(|v| v.value),
            disk_throughput_gbps: client
                .disk_throughput_gbps
                .as_ref()
                .map_or(0.0, |v| v.value),
            direct_io: client.direct_io.as_ref().is_some_and(|v| v.value),
        }),
        request_checksum_calculation: checksum(client.request_checksum.value),
        response_checksum_validation: checksum(client.response_checksum.value),
        user_agent: user_agent::assemble(
            client,
            &user_agent::host(),
            user_agent::distribution().as_ref(),
            user_agent_versions(),
            uploads,
        ),
        ..Default::default()
    }
}

/// The `user-agent` a transfer command's listing sends.
///
/// It is the record's with the paginator's feature id. Upstream lists
/// through its source client's paginator, which registers the id for the
/// pages it requests (botocore/paginate.py), and transfers through a client
/// that never registers it.
pub fn listing_user_agent(client: &cli_core::client_config::ClientConfig) -> String {
    use cli_core::client_config::user_agent;
    let mut inputs = client.user_agent_inputs(false);
    inputs.features.insert(user_agent::Feature::Paginator);
    user_agent::render(
        &inputs,
        &user_agent::host(),
        user_agent::distribution().as_ref(),
        user_agent_versions(),
    )
}

/// The `user-agent` a move's DeleteObject of each source object sends.
///
/// It is the record's without the CRT transfer client's feature id.
/// Upstream deletes through its source client, which kept the ids the
/// command had registered when it was created, before the transfer client
/// registered its own (`Session.create_client`), and sends each delete from the
/// CRT's done callback, outside the command's context
/// (`DeleteSourceSubscriber`).
pub fn source_delete_user_agent(client: &cli_core::client_config::ClientConfig) -> String {
    use cli_core::client_config::user_agent;
    let mut inputs = client.user_agent_inputs(false);
    inputs
        .features
        .remove(user_agent::Feature::S3TransferCrtAuto);
    inputs
        .features
        .remove(user_agent::Feature::S3TransferCrtExplicit);
    user_agent::render(
        &inputs,
        &user_agent::host(),
        user_agent::distribution().as_ref(),
        user_agent_versions(),
    )
}

fn user_agent_versions() -> cli_core::client_config::user_agent::Versions<'static> {
    cli_core::client_config::user_agent::Versions {
        cli: cli_core::AWS_CLI_VERSION,
        crt: env!("AWSCRT_VERSION"),
        rust: env!("RUST_VERSION"),
    }
}

#[cfg(test)]
mod tests;
