#![expect(clippy::unwrap_used, reason = "fixed parity fixtures and assertions")]
use super::*;
#[test]
fn exact_opt_in_only() {
    for (value, expected) in [("", false), ("true", false), ("1", true)] {
        assert_eq!(
            enabled(&cli_core::SnapshotEnv::from_pairs([(
                "ZS3_TRANSFER_STATS",
                value
            )])),
            expected
        );
    }
}
#[test]
fn formats_complete_stats_line() {
    let mut stats = ListStats {
        pages: 2,
        entries: 2000,
        total_ns: 200_000_000,
        body_bytes: 800_000,
        chunks: 52,
        first_chunk_bytes: 32768,
        token_pages: 1,
        resolved_chunk1: 2,
        token_offset_sum: 187,
        probe_ns: 2_500_000,
        ..ListStats::default()
    };
    stats.ttfb = ListPhaseStats {
        count: 2,
        sum_ns: 160_000_000,
        ns_min: 70_000_000,
        ns_max: 90_400_000,
        ..ListPhaseStats::default()
    };
    stats.ttfb.histogram[7] = 2;
    let mut out = Vec::new();
    write(&mut out, &stats).unwrap();
    assert_eq!(
        String::from_utf8(out).unwrap(),
        concat!(
            "zs3-list-stats: pages=2 keys=2000 elapsed_ms=200 keys_per_s=10000",
            " cycle_ms=100.0 overhead_ms=20.0 ttfb_ms=avg:80.0/p95:128/max:90",
            " transfer_ms=avg:0/p95:0/max:0 shutdown_ms=avg:0/p95:0/max:0",
            " parse_emit_ms=avg:0/p95:0/max:0 on_entry_ms=avg:0/p95:0/max:0",
            " gap_ms=avg:0/p95:0/max:0 token_ms=avg:0/p95:0/max:0",
            " body_bytes=avg:400000 chunks=avg:26 first_chunk=avg:16384 token_chunk1=2/2",
            " token_offset=avg:187 token_unresolved=0 token_mismatch=0 probe_ms=2\n"
        )
    );
}
#[test]
fn overlapping_prefetch_overhead_is_zero() {
    let mut stats = ListStats {
        pages: 2,
        total_ns: 100_000_000,
        ..ListStats::default()
    };
    stats.ttfb.sum_ns = 120_000_000;
    assert_eq!(overhead_ms(&stats), 0.0);
}
#[test]
fn zero_aggregate_never_divides_by_zero() {
    let mut out = Vec::new();
    write(&mut out, &ListStats::default()).unwrap();
    assert!(out.starts_with(b"zs3-list-stats: pages=0 keys=0"));
}
#[test]
fn percentile_selects_upper_bucket_bound() {
    let mut phase = ListPhaseStats {
        count: 100,
        ..ListPhaseStats::default()
    };
    phase.histogram[0] = 94;
    phase.histogram[7] = 6;
    assert_eq!(p95_ms(&phase), 128);
    phase.histogram[0] = 95;
    phase.histogram[7] = 5;
    assert_eq!(p95_ms(&phase), 1);
}
#[test]
fn prefetch_is_disabled_only_by_exact_zero() {
    for value in [None, Some(""), Some("false"), Some("0"), Some("1")] {
        let env: std::collections::BTreeMap<String, String> = value
            .map(|value| ("ZS3_LIST_PIPELINE".into(), value.into()))
            .into_iter()
            .collect();
        assert_eq!(prefetch_enabled(&env), value != Some("0"));
    }
}
#[test]
fn decimals_round_the_shortest_digits_half_up() {
    for (value, precision, expected) in [
        (0.15, 1, "0.2"),
        (0.25, 1, "0.3"),
        (0.05, 1, "0.1"),
        (9.95, 1, "10.0"),
        (100.0, 1, "100.0"),
        (0.0625, 3, "0.063"),
        (0.0, 1, "0.0"),
        (0.04, 1, "0.0"),
        (0.149, 1, "0.1"),
        (80.0, 1, "80.0"),
        (2.0, 3, "2.000"),
        (217.6, 3, "217.600"),
        (1234.5678, 0, "1235"),
        (0.0004, 3, "0.000"),
        (0.0006, 3, "0.001"),
        (0.95, 1, "1.0"),
        (1e21, 1, "1000000000000000000000.0"),
        (1.5e-7, 1, "0.0"),
        (-0.15, 1, "-0.2"),
        (1.0005, 3, "1.001"),
        (2.6665, 3, "2.667"),
    ] {
        assert_eq!(
            format_shortest_half_up(value, precision),
            expected,
            "{value} {precision}"
        );
    }
    assert_eq!(format!("{:.1}", 0.15), "0.1");
}
#[test]
fn phase_average_rounds_the_shortest_digits_half_up() {
    let mut stats = ListStats {
        pages: 1,
        ..ListStats::default()
    };
    stats.ttfb = ListPhaseStats {
        count: 1,
        sum_ns: 150_000,
        ns_min: 150_000,
        ns_max: 150_000,
        ..ListPhaseStats::default()
    };
    stats.ttfb.histogram[0] = 1;
    let mut out = Vec::new();
    write(&mut out, &stats).unwrap();
    let line = String::from_utf8(out).unwrap();
    assert!(line.contains(" ttfb_ms=avg:0.2/p95:1/max:0 "), "{line}");
}
