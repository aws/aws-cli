//! The client sizing of a cp or rm command: its throughput target, buffer
//! pool, single-request budget, and connection cap, resolved once from the
//! shape of the command and the settings the invocation resolved.
use crate::download::WriterMode;
use crate::transfer::Direction;
use cli_core::client_config::{MemoryLimit, Resolved, Source, memory_limit_for_throughput};

/// Extra CRT connections beyond the scheduler window. The single synchronous
/// paginator needs one listing request alongside GETs; 32 leaves 31 slots of
/// tuning headroom for connection turnover (6.25% of the default window). It
/// is not a measured minimum or a reservation: CRT scheduling and multipart
/// GETs can still cause connection waits.
pub const RECURSIVE_DOWNLOAD_CONNECTION_SLACK: u32 = 32;

/// Mirror of aws-c-s3's `s_throughput_per_connection_gbps` (100.0 / 250):
/// the client derives `ideal_connection_count = ceil(target / 0.4)`.
const CRT_CONNECTION_GBPS: f64 = 0.4;

/// The least range the CRT picks for itself when the part size is dynamic
/// (`g_default_part_size_fallback`).
const DYNAMIC_PART_SIZE_MIN: u64 = 8 << 20;

/// The receive buffers a download holds ahead of its writers, whatever its
/// shape: the bytes it needs at a given throughput do not depend on how many
/// objects carry them. Retained receive buffers reduce memory available to
/// dirty file pages; 4 GiB still admits 512 nominal 8-MiB parts.
const DOWNLOAD_MEMORY_LIMIT_BYTES_BUDGET: u64 = 512 * (8 << 20);

/// Whether the platform has the mmap writer the download pool rule budgets
/// for: Linux and macOS.
const MMAP_AVAILABLE: bool = cfg!(any(target_os = "linux", target_os = "macos"));

const _: () = {
    assert!(RECURSIVE_DOWNLOAD_CONNECTION_SLACK > 0);
    assert!(RECURSIVE_DOWNLOAD_CONNECTION_SLACK < crate::constants::IN_FLIGHT_MAX_DEFAULT);
    assert!(CRT_CONNECTION_GBPS.is_finite());
    assert!(CRT_CONNECTION_GBPS > 0.0);
};

/// How many objects a command moves, which decides the client sizing and the
/// writer service. Decided from the plan, before the runtime exists.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Shape {
    OneObject,
    ManyObjects,
}

/// Everything the runtime and the writers are sized from, resolved once.
/// The default sizes nothing, for requests whose scheduler never sends a
/// single-request body.
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct ClientSizing {
    /// The throughput target the client is built with, in gigabits per second.
    pub throughput_target_gbps: f64,
    /// Explicit CRT buffer-pool limit; zero delegates to the CRT and its
    /// memory-limit environment variables.
    pub memory_limit_in_bytes: u64,
    /// The pool the writers plan around: the explicit limit, else the
    /// memory-limit variable's value, else the target's tier. Always positive.
    pub source_pool_bytes: u64,
    /// The bytes a download's single-request bodies in flight may hold
    /// together: the pool the CRT would size itself, the memory-limit
    /// variable's value or the tier of the configured target, whatever
    /// explicit limit the pool takes. A whole body stays in memory for as long
    /// as its GET runs, so what these GETs need grows with how many run at
    /// once, not with the throughput. Always positive.
    pub single_request_bytes_max: u64,
    /// The connection cap the client is built with; zero keeps the count the
    /// throughput target gives.
    pub max_connections: u32,
}

/// What `resolve_client_sizing` sizes a client from: the shape of the
/// command and the settings the invocation resolved.
#[derive(Debug, Clone, PartialEq)]
pub struct SizingInputs {
    /// The command's direction.
    pub direction: Direction,
    /// How many objects the command moves.
    pub shape: Shape,
    /// The configured target. A many-object download raises it to its
    /// connection floor and keeps this value for the pool tier.
    pub target_gbps: f64,
    /// The buffer pool the invocation resolved, memory-limit variables
    /// included; the command never reads those variables itself.
    pub memory_limit: MemoryLimit,
    /// The configured part size; zero for the CRT's dynamic one.
    pub part_size: u64,
    /// The resolved connection cap with its source. A many-object download
    /// keeps only an explicit cap.
    pub max_connections: Option<Resolved<u32>>,
    /// The scheduler's transfer window.
    pub in_flight_max: u32,
    /// The configured writer, which decides whether the download pool rule
    /// applies. The effective writer can differ, because `direct_io` prefers
    /// the direct writer.
    pub configured_writer: Option<WriterMode>,
}

/// The client sizing of a command in `inputs.direction` moving
/// `inputs.shape`. Callers must supply a finite, positive target and a
/// nonzero transfer window.
pub fn resolve_client_sizing(inputs: &SizingInputs) -> ClientSizing {
    resolve_client_sizing_with_mmap(inputs, MMAP_AVAILABLE)
}

/// `resolve_client_sizing` on a platform that has mmap or not.
fn resolve_client_sizing_with_mmap(inputs: &SizingInputs, mmap_available: bool) -> ClientSizing {
    assert!(inputs.target_gbps.is_finite() && inputs.target_gbps > 0.0);
    assert!(inputs.in_flight_max > 0);
    let sizing = match (inputs.direction, inputs.shape) {
        // Uploads are sized the same in both shapes: the configured target,
        // the CRT's own pool, and the resolved connection cap. A delete moves
        // no body, and upstream builds its CRT client from the same transfer
        // configuration (`TransferManagerFactory.create_transfer_manager`).
        (Direction::Upload | Direction::Delete, _) => ClientSizing {
            throughput_target_gbps: inputs.target_gbps,
            memory_limit_in_bytes: 0,
            source_pool_bytes: delegated_pool_bytes(inputs),
            single_request_bytes_max: delegated_pool_bytes(inputs),
            max_connections: resolved_connections(inputs.max_connections.as_ref()),
        },
        (Direction::Download, Shape::OneObject) => {
            one_object_download_sizing(inputs, mmap_available)
        }
        (Direction::Download, Shape::ManyObjects) => {
            many_objects_download_sizing(inputs, mmap_available)
        }
    };
    debug_assert!(
        sizing.throughput_target_gbps.is_finite()
            && sizing.throughput_target_gbps >= inputs.target_gbps
            && sizing.source_pool_bytes > 0
            && sizing.single_request_bytes_max > 0
    );
    sizing
}

/// The part size a download's source pool lends its buffers in: the
/// configured one, or the CRT's least when a zero part size leaves the CRT
/// to pick one, which bounds from above the buffers its pool can lend.
pub fn buffer_part_size(part_size: u64) -> u64 {
    if part_size == 0 {
        DYNAMIC_PART_SIZE_MIN
    } else {
        part_size
    }
}

/// The pool the CRT sizes when no explicit limit reaches it: a memory-limit
/// variable's value, else the tier of the configured target.
fn delegated_pool_bytes(inputs: &SizingInputs) -> u64 {
    match inputs.memory_limit {
        MemoryLimit::Tier => memory_limit_for_throughput(inputs.target_gbps),
        MemoryLimit::Override(bytes) => bytes,
    }
}

/// The resolved connection cap whatever its source; zero without one.
fn resolved_connections(cap: Option<&Resolved<u32>>) -> u32 {
    cap.map_or(0, |cap| cap.value)
}

/// The single command's download: the configured target, the download pool,
/// and the resolved connection cap.
fn one_object_download_sizing(inputs: &SizingInputs, mmap_available: bool) -> ClientSizing {
    let memory_limit_in_bytes = download_memory_limit_bytes(inputs, mmap_available);
    ClientSizing {
        throughput_target_gbps: inputs.target_gbps,
        memory_limit_in_bytes,
        source_pool_bytes: download_source_pool_bytes(inputs, memory_limit_in_bytes),
        single_request_bytes_max: delegated_pool_bytes(inputs),
        max_connections: resolved_connections(inputs.max_connections.as_ref()),
    }
}

/// A recursive download: the connection floor of its window, the download
/// pool, and only an explicit connection cap.
fn many_objects_download_sizing(inputs: &SizingInputs, mmap_available: bool) -> ClientSizing {
    let memory_limit_in_bytes = download_memory_limit_bytes(inputs, mmap_available);
    let max_connections = many_objects_download_connections(inputs.max_connections.as_ref());
    ClientSizing {
        throughput_target_gbps: many_objects_download_target_gbps(
            inputs.target_gbps,
            inputs.in_flight_max,
            max_connections,
        ),
        memory_limit_in_bytes,
        source_pool_bytes: download_source_pool_bytes(inputs, memory_limit_in_bytes),
        single_request_bytes_max: delegated_pool_bytes(inputs),
        max_connections,
    }
}

/// The explicit buffer-pool limit of a download of either shape, from the
/// engine's window: one object for the single command, the scheduler's
/// window for a listing. With an mmap, `pwrite`, or `crt` writer on a platform
/// with mmap, the pool is the download budget, raised as far as twice the part
/// size and one part for each object in the window, and never above the tier
/// of the configured target:
///
/// ```text
/// min(tier, max(4 GiB, 2 * part size, window * part size))
/// ```
///
/// The CRT refuses a part larger than half its pool, and the tier accepts
/// every part size the command's configuration let through, so the pool
/// never undercuts twice the part size. The window term gives every object
/// in the window a part-size buffer, which the NUMA source pool's slots and
/// the CRT's pool without checksum validation require; for one object it
/// never exceeds twice the part. The `pwrite` and `crt` writers keep the rule,
/// so choosing either of them over mmap changes nothing about the receive
/// budget.
///
/// Zero delegates to the CRT where the rule does not apply: a memory-limit
/// variable the CRT reads itself, including its errors, or for the single
/// command a `direct` writer or a platform without mmap. A listing in those
/// last cases passes the tier of its configured target explicitly instead,
/// because the CRT would size its pool from the raised connection target.
fn download_memory_limit_bytes(inputs: &SizingInputs, mmap_available: bool) -> u64 {
    debug_assert_eq!(inputs.direction, Direction::Download);
    if let MemoryLimit::Override(_) = inputs.memory_limit {
        return 0;
    }
    let tier = memory_limit_for_throughput(inputs.target_gbps);
    if !pool_rule_applies(inputs, mmap_available) {
        return match inputs.shape {
            Shape::OneObject => 0,
            Shape::ManyObjects => tier,
        };
    }
    let window = match inputs.shape {
        Shape::OneObject => 1,
        Shape::ManyObjects => u64::from(inputs.in_flight_max),
    };
    let part_size = buffer_part_size(inputs.part_size);
    let limit = tier.min(
        DOWNLOAD_MEMORY_LIMIT_BYTES_BUDGET
            .max(part_size.saturating_mul(2))
            .max(window.saturating_mul(part_size)),
    );
    debug_assert!(limit > 0);
    debug_assert!(part_size > tier / 2 || part_size <= limit / 2);
    limit
}

/// Whether the download pool rule sizes the pool: an mmap, `pwrite`, or `crt`
/// writer, configured or by default, on a platform with mmap.
fn pool_rule_applies(inputs: &SizingInputs, mmap_available: bool) -> bool {
    mmap_available
        && matches!(
            inputs.configured_writer.unwrap_or(WriterMode::Mmap),
            WriterMode::Mmap | WriterMode::Pwrite | WriterMode::Crt
        )
}

/// The pool a download's writers plan around: its explicit limit, else the
/// one the CRT sizes itself.
fn download_source_pool_bytes(inputs: &SizingInputs, memory_limit_in_bytes: u64) -> u64 {
    if memory_limit_in_bytes == 0 {
        delegated_pool_bytes(inputs)
    } else {
        memory_limit_in_bytes
    }
}

/// Recursive downloads are bound by object rate, not bandwidth. The CRT
/// sizes its connection pool for bandwidth-bound transfers (0.4 Gbps per
/// connection), but a small object holds a connection for a full round
/// trip while delivering a fraction of that, so the pool must instead be
/// large enough that the connection gate never undercuts the scheduler
/// window. Encode the desired connection count in the CRT's own units; the
/// pool follows the user's configured target, so the raised target changes
/// nothing except the connection count.
///
/// An explicit `max_concurrent_requests` (`max_connections`, nonzero) bounds
/// the floor: the extra target would open no connection past the cap, but it
/// would still shrink the range size the CRT picks under a dynamic part size,
/// since aws-c-s3 divides the pool by the target's connection count
/// (`aws_s3_calculate_client_optimal_range_size`).
fn many_objects_download_target_gbps(
    target_gbps: f64,
    in_flight_max: u32,
    max_connections: u32,
) -> f64 {
    // Both terms are below 2^33, so the sum and the cap are exact in f64.
    let floor = f64::from(in_flight_max) + f64::from(RECURSIVE_DOWNLOAD_CONNECTION_SLACK);
    let connections = if max_connections == 0 {
        floor
    } else {
        floor.min(f64::from(max_connections))
    };
    let raised = target_gbps.max(CRT_CONNECTION_GBPS * connections);
    debug_assert!(raised.is_finite());
    debug_assert!((raised / CRT_CONNECTION_GBPS).ceil() >= connections);
    raised
}

/// The connection cap of a recursive download: only an explicit
/// `max_concurrent_requests`, which wins over the recursive connection floor.
/// The newly eligible persona's default cap applies to every other transfer;
/// zero keeps the count the throughput target gives.
fn many_objects_download_connections(cap: Option<&Resolved<u32>>) -> u32 {
    match cap {
        None => 0,
        Some(cap) if cap.source == Source::Persona => 0,
        Some(cap) => cap.value,
    }
}

#[cfg(test)]
mod tests;
