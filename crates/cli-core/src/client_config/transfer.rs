use super::*;
use coerce::TransferClient;

pub(super) fn resolve<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
    probe: impl FnOnce() -> Platform,
) -> Result<(), PythonReason> {
    if !inputs.command.transfers() {
        return Ok(());
    }
    let raw = coerce::TransferInputs::read(|key| inputs.nested(key));
    let block = coerce::transfer(&raw)?;
    let crt_preferred = match block.preferred_transfer_client {
        TransferClient::Classic => return Err(PythonReason::TransferSetting),
        TransferClient::Crt => true,
        TransferClient::Auto => false,
    };
    let platform = if !crt_preferred || block.target_bandwidth.is_none() {
        probe()
    } else {
        Platform::default()
    };
    let persona = if crt_preferred {
        Persona::CrtPreferred
    } else if platform.optimized {
        Persona::Tuned
    } else {
        Persona::NewlyEligible
    };
    config.persona = Some(Resolved::new(
        persona,
        if raw.preferred_transfer_client.is_some() {
            Source::S3("preferred_transfer_client")
        } else {
            Source::Default
        },
    ));
    config.target_gbps = throughput(persona, platform, block.target_bandwidth);
    resolve_transfer_keys(config, &block, persona)
}
fn resolve_transfer_keys(
    config: &mut ClientConfig,
    block: &coerce::Transfer,
    persona: Persona,
) -> Result<(), PythonReason> {
    let classic_defaults = persona == Persona::NewlyEligible;
    if block.max_bandwidth.is_some() {
        if classic_defaults {
            return Err(PythonReason::TransferSetting);
        }
        config.ignored.max_bandwidth = true;
    }
    config.ignored.max_queue_size = block.max_queue_size.is_some();
    config.ignored.io_chunksize = block.io_chunksize.is_some();
    resolve_parts(config, block, classic_defaults);
    config.max_connections = match block.max_concurrent_requests {
        Some(requests) => Some(Resolved::new(
            u32::try_from(requests).map_err(|_| PythonReason::TransferSetting)?,
            Source::S3("max_concurrent_requests"),
        )),
        None => classic_defaults.then_some(Resolved::new(CONNECTIONS_DEFAULT, Source::Persona)),
    };
    resolve_file_io(config, block);
    Ok(())
}
fn resolve_parts(config: &mut ClientConfig, block: &coerce::Transfer, classic_defaults: bool) {
    config.part_size = match block.multipart_chunksize {
        Some(bytes) => Resolved::new(bytes, Source::S3("multipart_chunksize")),
        None if classic_defaults => Resolved::new(PART_SIZE_DEFAULT, Source::Persona),
        None => Resolved::new(0, Source::Default),
    };
    config.multipart_threshold = match block.multipart_threshold {
        Some(bytes) => Some(Resolved::new(bytes, Source::S3("multipart_threshold"))),
        None => {
            classic_defaults.then_some(Resolved::new(MULTIPART_THRESHOLD_DEFAULT, Source::Persona))
        }
    };
}
fn resolve_file_io(config: &mut ClientConfig, block: &coerce::Transfer) {
    config.should_stream = block
        .should_stream
        .map(|value| Resolved::new(value, Source::S3("should_stream")));
    config.direct_io = block
        .direct_io
        .map(|value| Resolved::new(value, Source::S3("direct_io")));
    config.disk_throughput_gbps = block
        .disk_throughput
        .map(|bytes| Resolved::new(coerce::bytes_to_gbps(bytes), Source::S3("disk_throughput")));
}
fn throughput(persona: Persona, platform: Platform, configured: Option<u64>) -> Resolved<f64> {
    if let Some(bytes) = configured {
        return Resolved::new(coerce::bytes_to_gbps(bytes), Source::S3("target_bandwidth"));
    }
    let recommended = platform.recommended_gbps;
    Resolved::new(
        match persona {
            Persona::CrtPreferred => round_trip(
                recommended
                    .unwrap_or(0.0)
                    .max(TARGET_GBPS_CRT_PREFERRED_MIN),
            ),
            Persona::Tuned => recommended.unwrap_or(TARGET_GBPS_UNRECOMMENDED),
            Persona::NewlyEligible => recommended.unwrap_or(TARGET_GBPS_UNTUNED),
        },
        Source::Persona,
    )
}
#[expect(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    reason = "upstream truncates positive throughput to whole bytes per second"
)]
fn round_trip(gbps: f64) -> f64 {
    coerce::bytes_to_gbps((gbps * 1_000_000_000.0 / 8.0) as u64)
}
pub(super) fn memory<E: EnvMap>(
    inputs: &Inputs<'_, E>,
    config: &mut ClientConfig,
) -> Result<(), PythonReason> {
    if !inputs.command.transfers() {
        return Ok(());
    }
    for (name, unit) in MEMORY_LIMIT_VARIABLES {
        if let Some(text) = inputs.env.var_os(name).filter(|v| !v.is_empty()) {
            let bytes = text
                .to_str()
                .and_then(coerce::unsigned)
                .and_then(|count| count.checked_mul(unit))
                .ok_or(Field::MemoryLimit.reason())?;
            if bytes != 0 {
                config.memory_limit =
                    Resolved::new(MemoryLimit::Override(bytes), Source::Env(name));
                break;
            }
        }
    }
    let bytes = config.memory_bytes();
    if bytes < MEMORY_LIMIT_BYTES_MIN || config.part_size.value > part_size_max(bytes) {
        return Err(Field::MemoryLimit.reason());
    }
    Ok(())
}
