//! Parseable listing instrumentation and bounded histogram percentiles,
//! over the CRT's own aggregate.
use cli_core::EnvMap;
use crt::s3::{ListPhaseStats, ListStats};
use std::io::{self, Write};

pub fn enabled(env: &impl EnvMap) -> bool {
    env.var("ZS3_TRANSFER_STATS") == Some("1")
}
pub fn prefetch_enabled(env: &impl EnvMap) -> bool {
    env.var("ZS3_LIST_PIPELINE") != Some("0")
}
/// One parseable stderr line. Phase values are milliseconds; `p95` is the
/// upper bound of the power-of-two histogram bucket containing the 95th
/// percentile, so it over-reports by at most 2x.
pub fn write(out: &mut impl Write, stats: &ListStats) -> io::Result<()> {
    write!(
        out,
        "zs3-list-stats: pages={} keys={} elapsed_ms={} keys_per_s={}",
        stats.pages,
        stats.entries,
        stats.total_ns / 1_000_000,
        keys_per_second(stats.entries, stats.total_ns)
    )?;
    write!(
        out,
        " cycle_ms={} overhead_ms={}",
        format_shortest_half_up(cycle_ms(stats), 1),
        format_shortest_half_up(overhead_ms(stats), 1)
    )?;
    for (name, phase) in [
        ("ttfb_ms", &stats.ttfb),
        ("transfer_ms", &stats.transfer),
        ("shutdown_ms", &stats.shutdown_wait),
        ("parse_emit_ms", &stats.parse_emit),
        ("on_entry_ms", &stats.on_entry),
        ("gap_ms", &stats.gap),
        ("token_ms", &stats.token_latency),
    ] {
        write_phase(out, name, phase)?;
    }
    writeln!(
        out,
        " body_bytes=avg:{} chunks=avg:{} first_chunk=avg:{} token_chunk1={}/{} \
        token_offset=avg:{} token_unresolved={} token_mismatch={} probe_ms={}",
        per_page(stats.body_bytes, stats.pages),
        per_page(stats.chunks, stats.pages),
        per_page(stats.first_chunk_bytes, stats.pages),
        stats.resolved_chunk1,
        stats.pages,
        per_page(stats.token_offset_sum, stats.token_pages),
        stats.token_unresolved,
        stats.token_mismatch,
        stats.probe_ns / 1_000_000
    )
}
fn write_phase(out: &mut impl Write, name: &str, phase: &ListPhaseStats) -> io::Result<()> {
    if phase.count == 0 {
        return write!(out, " {name}=avg:0/p95:0/max:0");
    }
    write!(
        out,
        " {name}=avg:{}/p95:{}/max:{}",
        format_shortest_half_up(phase.sum_ns as f64 / phase.count as f64 / 1_000_000.0, 1),
        p95_ms(phase),
        (phase.ns_max + 500_000) / 1_000_000
    )
}
pub fn p95_ms(phase: &ListPhaseStats) -> u64 {
    let mut cumulative = 0u128;
    for (index, count) in phase.histogram.iter().enumerate() {
        cumulative += u128::from(*count);
        if cumulative * 20 >= u128::from(phase.count) * 19 {
            return 1 << index;
        }
    }
    1 << 15
}
fn cycle_ms(stats: &ListStats) -> f64 {
    if stats.pages == 0 {
        0.0
    } else {
        stats.total_ns as f64 / stats.pages as f64 / 1_000_000.0
    }
}
fn overhead_ms(stats: &ListStats) -> f64 {
    if stats.pages == 0 {
        return 0.0;
    }
    (cycle_ms(stats)
        - (stats.ttfb.sum_ns as f64 + stats.transfer.sum_ns as f64)
            / stats.pages as f64
            / 1_000_000.0)
        .max(0.0)
}
fn keys_per_second(entries: u64, nanos: u64) -> u128 {
    if nanos == 0 {
        0
    } else {
        u128::from(entries) * 1_000_000_000 / u128::from(nanos)
    }
}
fn per_page(total: u64, count: u64) -> u64 {
    total.checked_div(count).unwrap_or(0)
}

pub(crate) fn format_shortest_half_up(value: f64, precision: usize) -> String {
    if !value.is_finite() {
        return if value.is_nan() {
            "nan".into()
        } else if value < 0.0 {
            "-inf".into()
        } else {
            "inf".into()
        };
    }
    // `{:e}` is the shortest round-trip form: `d[.ddd]e<exponent>`.
    let scientific = format!("{:e}", value.abs());
    let (mantissa, exponent) = scientific.split_once('e').unwrap_or((&scientific, "0"));
    let (whole, fraction) = mantissa.split_once('.').unwrap_or((mantissa, ""));
    let mut digits: Vec<u8> = whole
        .bytes()
        .chain(fraction.bytes())
        .map(|d| d - b'0')
        .collect();
    let mut exponent = exponent.parse::<i64>().unwrap_or(0) - fraction.len() as i64;
    if exponent < 0 {
        let kept = (digits.len() as i64 + exponent + precision as i64).max(0) as usize;
        if kept < digits.len() {
            exponent += (digits.len() - kept - 1) as i64;
            digits.truncate(kept + 1);
            if digits[kept] >= 5 {
                digits.truncate(kept);
                exponent += 1;
                increment(&mut digits);
            }
        }
    }
    render_fixed(value.is_sign_negative(), &digits, exponent, precision)
}
fn increment(digits: &mut Vec<u8>) {
    for digit in digits.iter_mut().rev() {
        if *digit < 9 {
            *digit += 1;
            return;
        }
        *digit = 0;
    }
    digits.insert(0, 1);
}
fn render_fixed(negative: bool, digits: &[u8], exponent: i64, precision: usize) -> String {
    let integer_len = digits.len() as i64 + exponent;
    let digit = |position: i64| {
        usize::try_from(position)
            .ok()
            .and_then(|position| digits.get(position))
            .map_or('0', |digit| char::from(b'0' + digit))
    };
    let mut out = String::new();
    if negative {
        out.push('-');
    }
    if integer_len <= 0 {
        out.push('0');
    }
    for position in 0..integer_len {
        out.push(digit(position));
    }
    if precision > 0 {
        out.push('.');
        for position in integer_len..integer_len + precision as i64 {
            out.push(digit(position));
        }
    }
    out
}
#[cfg(test)]
mod tests;
