use super::*;
use crate::constants::IN_FLIGHT_MAX_DEFAULT;

const MIB: u64 = 1 << 20;
const GIB: u64 = 1 << 30;
/// The configured writers the download pool rule sizes: none, which is mmap
/// by default, and an explicit mmap, pwrite, or crt writer.
const POOL_RULE_WRITERS: [Option<WriterMode>; 4] = [
    None,
    Some(WriterMode::Mmap),
    Some(WriterMode::Pwrite),
    Some(WriterMode::Crt),
];

/// The sizing inputs of an untuned invocation at `target_gbps`.
fn inputs(direction: Direction, shape: Shape, target_gbps: f64) -> SizingInputs {
    SizingInputs {
        direction,
        shape,
        target_gbps,
        memory_limit: MemoryLimit::Tier,
        part_size: 0,
        max_connections: None,
        in_flight_max: IN_FLIGHT_MAX_DEFAULT,
        configured_writer: None,
    }
}

fn assert_approx(expected: f64, actual: f64) {
    assert!(
        (expected - actual).abs() <= 0.0001,
        "expected {expected}, got {actual}"
    );
}

// Pins the sizing constants: the connection slack, the CRT's per-connection
// throughput, its dynamic part-size fallback, the 4 GiB download budget, and
// the CRT's memory tiers.
#[test]
fn sizing_constants_match_the_crt() {
    assert_eq!(RECURSIVE_DOWNLOAD_CONNECTION_SLACK, 32);
    assert_eq!(CRT_CONNECTION_GBPS, 100.0 / 250.0);
    assert_eq!(DYNAMIC_PART_SIZE_MIN, 8 * MIB);
    assert_eq!(DOWNLOAD_MEMORY_LIMIT_BYTES_BUDGET, 512 * 8 * MIB);
    assert_eq!(DOWNLOAD_MEMORY_LIMIT_BYTES_BUDGET, 4 * GIB);
    assert_eq!(buffer_part_size(0), 8 * MIB);
    assert_eq!(buffer_part_size(5 * MIB), 5 * MIB);
    for (target, tier) in [
        (0.001, 256 * MIB),
        (4.999, 256 * MIB),
        (5.0, 512 * MIB),
        (9.999, 512 * MIB),
        (10.0, 2 * GIB),
        (24.999, 2 * GIB),
        (25.0, 4 * GIB),
        (74.999, 4 * GIB),
        (75.0, 8 * GIB),
        (99.999, 8 * GIB),
        (100.0, 16 * GIB),
        (199.999, 16 * GIB),
        (200.0, 24 * GIB),
        (1000.0, 24 * GIB),
    ] {
        assert_eq!(memory_limit_for_throughput(target), tier, "{target}");
    }
}

#[test]
fn a_one_object_mmap_download_caps_only_the_default_memory_tier() {
    // (target, memory-limit variable, part size, expected explicit limit;
    // zero delegates to the CRT).
    let cases: [(f64, Option<u64>, u64, u64); 19] = [
        (1.0, None, 0, 256 * MIB),
        (4.9, None, 0, 256 * MIB),
        (5.0, None, 0, 512 * MIB),
        (9.9, None, 0, 512 * MIB),
        (10.0, None, 0, 2 * GIB),
        (24.9, None, 0, 2 * GIB),
        (25.0, None, 0, 4 * GIB),
        (75.0, None, 0, 4 * GIB),
        (100.0, None, 0, 4 * GIB),
        (200.0, None, 0, 4 * GIB),
        (1.0, Some(6 * GIB), 0, 0),
        (100.0, Some(256 * MIB), 3 * GIB, 0),
        // A part size the tier accepts is never refused by the cap: the
        // pool grows to twice the part, up to the tier.
        (4.0, None, 128 * MIB, 256 * MIB),
        (10.0, None, GIB, 2 * GIB),
        (25.0, None, 2 * GIB, 4 * GIB),
        (75.0, None, 3 * GIB, 6 * GIB),
        (100.0, None, 5 * GIB, 10 * GIB),
        (200.0, None, 5 * GIB, 10 * GIB),
        (100.0, None, 16 * MIB, 4 * GIB),
    ];
    for (target, variable, part_size, expected) in cases {
        // An explicit mmap writer is still mmap, and the pwrite and crt
        // writers keep the same budget, so choosing who writes changes no
        // sizing.
        for mode in POOL_RULE_WRITERS {
            let mut inputs = inputs(Direction::Download, Shape::OneObject, target);
            if let Some(bytes) = variable {
                inputs.memory_limit = MemoryLimit::Override(bytes);
            }
            inputs.part_size = part_size;
            inputs.configured_writer = mode;
            let delegated = variable.unwrap_or_else(|| memory_limit_for_throughput(target));
            assert_one_object_sizing(&inputs, expected, delegated);
        }
    }
    assert_one_object_sizing_delegates_without_the_rule();
}
/// One object of `inputs` takes the `expected` explicit limit where mmap is
/// available, and `delegated` is the pool the CRT would size itself.
fn assert_one_object_sizing(inputs: &SizingInputs, expected: u64, delegated: u64) {
    let sizing = resolve_client_sizing_with_mmap(inputs, true);
    assert_eq!(sizing.memory_limit_in_bytes, expected, "{inputs:?}");
    if sizing.memory_limit_in_bytes != 0 {
        assert!(inputs.part_size <= sizing.memory_limit_in_bytes / 2);
    }
    // The writers plan around the capped pool, or else the one the CRT sizes
    // itself.
    let pool = if expected == 0 { delegated } else { expected };
    assert_eq!(sizing.source_pool_bytes, pool);
    assert_eq!(sizing.throughput_target_gbps, inputs.target_gbps);
    // Single-request bodies keep the pool the CRT would size itself.
    assert_eq!(sizing.single_request_bytes_max, delegated);

    // A platform without mmap leaves the pool to the CRT.
    let unmapped = resolve_client_sizing_with_mmap(inputs, false);
    assert_eq!(unmapped.memory_limit_in_bytes, 0);
    assert_eq!(unmapped.source_pool_bytes, delegated);
}
fn assert_one_object_sizing_delegates_without_the_rule() {
    // A configured direct writer leaves the pool to the CRT, even where the
    // `direct_io` preference would have picked the direct writer anyway.
    let mut direct = inputs(Direction::Download, Shape::OneObject, 100.0);
    direct.configured_writer = Some(WriterMode::Direct);
    let sizing = resolve_client_sizing_with_mmap(&direct, true);
    assert_eq!(sizing.memory_limit_in_bytes, 0);
    assert_eq!(sizing.source_pool_bytes, 16 * GIB);
    // The native platform's mmap decides the public resolver.
    let native = resolve_client_sizing(&inputs(Direction::Download, Shape::OneObject, 100.0));
    let mapped = cfg!(any(target_os = "linux", target_os = "macos"));
    assert_eq!(
        native.memory_limit_in_bytes,
        if mapped { 4 * GIB } else { 0 }
    );
}

#[test]
fn many_object_download_sizing_raises_the_connection_gate_above_the_window() {
    // Default window 512 + 32 slack -> 217.6 Gbps -> 544 connections.
    let sizing = resolve_client_sizing(&inputs(Direction::Download, Shape::ManyObjects, 10.0));
    assert_approx(217.6, sizing.throughput_target_gbps);
    // Memory stays at the tier the user's 10 Gbps target selects.
    assert_eq!(sizing.memory_limit_in_bytes, 2 * GIB);
    assert_eq!(sizing.source_pool_bytes, 2 * GIB);
    // The untuned persona's 4 Gbps keeps the connection floor and the
    // 256 MiB tier.
    let untuned = resolve_client_sizing(&inputs(Direction::Download, Shape::ManyObjects, 4.0));
    assert_approx(217.6, untuned.throughput_target_gbps);
    assert_eq!(untuned.memory_limit_in_bytes, 256 * MIB);
}

// An explicit `max_concurrent_requests` bounds the recursive connection
// floor, so the raised target buys no connection the cap refuses. Without
// one, or with a cap above the floor, the target still covers the window.
// The pool follows the configured target either way.
#[test]
fn an_explicit_connection_cap_bounds_the_recursive_connection_floor() {
    let explicit = Source::S3("max_concurrent_requests");
    // (resolved cap, expected target, expected connection cap).
    let cases = [
        // Window 512 + 32 slack -> 217.6 Gbps -> 544 connections.
        (None, 217.6, 0),
        // The persona's default cap is not an explicit one.
        (Some(Resolved::new(10, Source::Persona)), 217.6, 0),
        // Ten connections need only 4 Gbps, below the configured 10.
        (Some(Resolved::new(10, explicit)), 10.0, 10),
        // A cap above the floor leaves the floor.
        (Some(Resolved::new(1000, explicit)), 217.6, 1000),
        // A cap between them raises the target only as far as the cap.
        (
            Some(Resolved::new(
                100,
                Source::Flag("--max-concurrent-requests"),
            )),
            40.0,
            100,
        ),
    ];
    for (cap, target, connections) in cases {
        let mut inputs = inputs(Direction::Download, Shape::ManyObjects, 10.0);
        inputs.max_connections = cap.clone();
        let sizing = resolve_client_sizing(&inputs);
        assert_approx(target, sizing.throughput_target_gbps);
        assert_eq!(sizing.max_connections, connections);
        assert_eq!(sizing.source_pool_bytes, 2 * GIB);
        // The single command keeps its configured target and the resolved cap.
        inputs.shape = Shape::OneObject;
        let single = resolve_client_sizing(&inputs);
        assert_eq!(single.throughput_target_gbps, 10.0);
        assert_eq!(single.max_connections, cap.map_or(0, |cap| cap.value));
    }
}

#[test]
fn many_object_download_sizing_never_lowers_an_explicit_target() {
    let inputs = inputs(Direction::Download, Shape::ManyObjects, 250.0);
    let sizing = resolve_client_sizing_with_mmap(&inputs, true);
    assert_eq!(sizing.throughput_target_gbps, 250.0);
    assert_eq!(sizing.memory_limit_in_bytes, 4 * GIB);
    let unmapped = resolve_client_sizing_with_mmap(&inputs, false);
    assert_eq!(unmapped.memory_limit_in_bytes, 24 * GIB);
}

#[test]
fn many_object_download_sizing_scales_with_the_configured_window() {
    // 1024 + 32 slack -> 422.4 Gbps -> 1056 connections.
    let mut inputs = inputs(Direction::Download, Shape::ManyObjects, 107.3741824);
    inputs.in_flight_max = 1024;
    let sizing = resolve_client_sizing_with_mmap(&inputs, true);
    assert_approx(422.4, sizing.throughput_target_gbps);
    // A part-size buffer for each of 1024 objects, below the 16 GiB tier.
    assert_eq!(sizing.memory_limit_in_bytes, 8 * GIB);
}

#[test]
fn many_object_download_sizing_accepts_minimum_and_maximum_scheduler_windows() {
    let mut inputs = inputs(Direction::Download, Shape::ManyObjects, 0.001);
    inputs.in_flight_max = 1;
    let smallest = resolve_client_sizing(&inputs);
    assert_approx(13.2, smallest.throughput_target_gbps);

    // Adding connection slack to the largest u32 window must not overflow.
    inputs.in_flight_max = u32::MAX;
    let largest = resolve_client_sizing(&inputs);
    assert_approx(1_717_986_930.8, largest.throughput_target_gbps);
    assert_eq!(
        smallest.memory_limit_in_bytes,
        largest.memory_limit_in_bytes
    );
}

#[test]
fn many_object_download_pool_follows_the_download_rule_at_every_tier() {
    // (target, the tier it selects, the pool under the download rule: at
    // most 4 GiB at the default window and part size).
    let cases = [
        (1.0, 256 * MIB, 256 * MIB),
        (4.9, 256 * MIB, 256 * MIB),
        (5.0, 512 * MIB, 512 * MIB),
        (9.9, 512 * MIB, 512 * MIB),
        (10.0, 2 * GIB, 2 * GIB),
        (24.9, 2 * GIB, 2 * GIB),
        (25.0, 4 * GIB, 4 * GIB),
        (74.9, 4 * GIB, 4 * GIB),
        (75.0, 8 * GIB, 4 * GIB),
        (107.3741824, 16 * GIB, 4 * GIB),
        (199.9, 16 * GIB, 4 * GIB),
        (200.0, 24 * GIB, 4 * GIB),
    ];
    for (target, tier, limit) in cases {
        let inputs = inputs(Direction::Download, Shape::ManyObjects, target);
        let sizing = resolve_client_sizing_with_mmap(&inputs, true);
        assert_eq!(sizing.memory_limit_in_bytes, limit, "{target}");
        assert_eq!(sizing.source_pool_bytes, limit);
        // Single-request bodies keep the tier of the configured target.
        assert_eq!(sizing.single_request_bytes_max, tier);
        // Without mmap the listing passes its configured target's tier.
        let unmapped = resolve_client_sizing_with_mmap(&inputs, false);
        assert_eq!(unmapped.memory_limit_in_bytes, tier);
        assert_eq!(unmapped.source_pool_bytes, tier);
        assert_eq!(unmapped.single_request_bytes_max, tier);
    }
}

// One rule sizes both shapes' pools from the engine's window: one object for
// the single command, the scheduler's window for a listing. The window term
// gives each object in it a part-size buffer, up to the tier, and never
// shrinks the pool below twice the part size.
#[test]
fn one_pool_rule_sizes_both_download_shapes_from_the_engines_window() {
    use Shape::{ManyObjects as Many, OneObject as One};
    let default = IN_FLIGHT_MAX_DEFAULT;
    // (shape, scheduler window, target, part size, expected explicit pool).
    let cases: [(Shape, u32, f64, u64, u64); 14] = [
        (One, default, 200.0, 0, 4 * GIB),
        (One, 1024, 200.0, 0, 4 * GIB),
        (One, default, 200.0, 16 * MIB, 4 * GIB),
        (One, default, 200.0, 3 * GIB, 6 * GIB),
        (Many, 1, 200.0, 0, 4 * GIB),
        (Many, 512, 200.0, 0, 4 * GIB),
        (Many, 1024, 200.0, 0, 8 * GIB),
        (Many, 1, 200.0, 16 * MIB, 4 * GIB),
        (Many, default, 200.0, 16 * MIB, 8 * GIB),
        (Many, 1024, 200.0, 16 * MIB, 16 * GIB),
        (Many, 1, 200.0, 3 * GIB, 6 * GIB),
        (Many, default, 200.0, 3 * GIB, 24 * GIB),
        // The tier caps the window term.
        (Many, 1024, 100.0, 32 * MIB, 16 * GIB),
        (Many, 1024, 10.0, 0, 2 * GIB),
    ];
    for (shape, window, target, part_size, limit) in cases {
        // An explicit mmap writer is still mmap, and the pwrite and crt
        // writers keep the rule.
        for mode in POOL_RULE_WRITERS {
            let mut inputs = inputs(Direction::Download, shape, target);
            inputs.in_flight_max = window;
            inputs.part_size = part_size;
            inputs.configured_writer = mode;
            let sizing = resolve_client_sizing_with_mmap(&inputs, true);
            assert_eq!(
                sizing.memory_limit_in_bytes, limit,
                "{shape:?} {window} {part_size}"
            );
            assert_eq!(sizing.source_pool_bytes, limit);
            assert!(buffer_part_size(part_size) <= limit / 2);
            assert_eq!(
                sizing.single_request_bytes_max,
                memory_limit_for_throughput(target)
            );
        }
    }
}

// Where the rule does not apply, the pool stays where it was: the CRT reads a
// memory-limit variable itself, and with a `direct` writer or without mmap
// the single command delegates while a listing passes the tier of its
// configured target, not of its raised one. The single-request bound of both
// commands is that same tier or the variable's value.
#[test]
fn a_download_keeps_the_tier_or_the_variable_where_the_pool_rule_does_not_apply() {
    for shape in [Shape::OneObject, Shape::ManyObjects] {
        let explicit_tier = match shape {
            Shape::OneObject => 0,
            Shape::ManyObjects => 24 * GIB,
        };
        let mut direct = inputs(Direction::Download, shape, 200.0);
        direct.configured_writer = Some(WriterMode::Direct);
        let sizing = resolve_client_sizing_with_mmap(&direct, true);
        assert_eq!(sizing.memory_limit_in_bytes, explicit_tier);
        assert_eq!(sizing.source_pool_bytes, 24 * GIB);
        assert_eq!(sizing.single_request_bytes_max, 24 * GIB);
        for mode in POOL_RULE_WRITERS {
            let mut inputs = inputs(Direction::Download, shape, 200.0);
            inputs.configured_writer = mode;
            assert_unmapped_and_overridden(inputs, explicit_tier);
        }
    }
}
/// Without mmap, `inputs` keep the `explicit_tier` and the 24 GiB pool; a
/// memory-limit variable delegates to the CRT whether mmap is available or
/// not.
fn assert_unmapped_and_overridden(mut inputs: SizingInputs, explicit_tier: u64) {
    let unmapped = resolve_client_sizing_with_mmap(&inputs, false);
    assert_eq!(unmapped.memory_limit_in_bytes, explicit_tier);
    assert_eq!(unmapped.source_pool_bytes, 24 * GIB);
    assert_eq!(unmapped.single_request_bytes_max, 24 * GIB);

    inputs.memory_limit = MemoryLimit::Override(6 * GIB);
    for mmap_available in [false, true] {
        let overridden = resolve_client_sizing_with_mmap(&inputs, mmap_available);
        assert_eq!(overridden.memory_limit_in_bytes, 0);
        assert_eq!(overridden.source_pool_bytes, 6 * GIB);
        assert_eq!(overridden.single_request_bytes_max, 6 * GIB);
    }
}

#[test]
fn a_many_object_download_defers_to_a_memory_limit_variable() {
    let mut inputs = inputs(Direction::Download, Shape::ManyObjects, 12.5);
    inputs.in_flight_max = 11;
    inputs.memory_limit = MemoryLimit::Override(6 * GIB);
    let sizing = resolve_client_sizing(&inputs);
    // Zero leaves the CRT free to read the variable; the writers plan
    // around the pool it then sizes.
    assert_eq!(sizing.memory_limit_in_bytes, 0);
    assert_eq!(sizing.source_pool_bytes, 6 * GIB);
    // The connection floor still follows the window: 11 + 32 slack.
    assert_approx(17.2, sizing.throughput_target_gbps);
}

#[test]
fn uploads_are_sized_the_same_in_both_shapes() {
    for shape in [Shape::OneObject, Shape::ManyObjects] {
        let mut inputs = inputs(Direction::Upload, shape, 12.5);
        inputs.in_flight_max = 11;
        inputs.configured_writer = Some(WriterMode::Mmap);
        let sizing = resolve_client_sizing(&inputs);
        // The configured target and the CRT's own pool.
        assert_eq!(sizing.throughput_target_gbps, 12.5);
        assert_eq!(sizing.memory_limit_in_bytes, 0);
        assert_eq!(sizing.source_pool_bytes, 2 * GIB);

        inputs.memory_limit = MemoryLimit::Override(6 * GIB);
        let overridden = resolve_client_sizing(&inputs);
        assert_eq!(overridden.memory_limit_in_bytes, 0);
        assert_eq!(overridden.source_pool_bytes, 6 * GIB);
    }
}

#[test]
fn only_a_many_object_download_sets_the_personas_connection_cap_aside() {
    let persona = Resolved::new(10, Source::Persona);
    let explicit = Resolved::new(3, Source::S3("max_concurrent_requests"));
    // (direction, shape, the cap the client keeps from the persona's default).
    let cases = [
        (Direction::Download, Shape::OneObject, 10),
        (Direction::Download, Shape::ManyObjects, 0),
        (Direction::Upload, Shape::OneObject, 10),
        (Direction::Upload, Shape::ManyObjects, 10),
    ];
    for (direction, shape, kept) in cases {
        let mut inputs = inputs(direction, shape, 10.0);
        assert_eq!(resolve_client_sizing(&inputs).max_connections, 0);
        inputs.max_connections = Some(persona.clone());
        assert_eq!(resolve_client_sizing(&inputs).max_connections, kept);
        // An explicit `max_concurrent_requests` caps every shape.
        inputs.max_connections = Some(explicit.clone());
        assert_eq!(resolve_client_sizing(&inputs).max_connections, 3);
    }
}
