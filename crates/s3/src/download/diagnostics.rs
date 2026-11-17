use super::{
    NumaMode, PREFAULT_LOOKAHEAD, PREFAULT_WINDOW, Requirement, STRIPE_BYTES, WriteError,
    WriterMode,
    io::{DirectAlignment, IoStats},
    memory::MemorySnapshot,
    platform::Preallocation,
    stream_copy::CopyMode,
};
use crate::cp::backstop::SetupError;
use std::io::{IsTerminal, Write};
use std::sync::OnceLock;
use std::time::Instant;

pub(crate) const ENABLED: bool = cfg!(feature = "download-writer-debug");

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct Traced<T> {
    #[cfg(feature = "download-writer-debug")]
    value: T,
    #[cfg(not(feature = "download-writer-debug"))]
    value: std::marker::PhantomData<T>,
}
impl<T> Traced<T> {
    pub(crate) fn new(value: T) -> Self {
        #[cfg(feature = "download-writer-debug")]
        return Self { value };
        #[cfg(not(feature = "download-writer-debug"))]
        {
            drop(value);
            Self {
                value: std::marker::PhantomData,
            }
        }
    }
    pub(crate) fn update(&mut self, update: impl FnOnce(&mut T)) {
        #[cfg(feature = "download-writer-debug")]
        update(&mut self.value);
        #[cfg(not(feature = "download-writer-debug"))]
        drop(update);
    }
    pub(crate) fn get(&self) -> Option<&T> {
        #[cfg(feature = "download-writer-debug")]
        return Some(&self.value);
        #[cfg(not(feature = "download-writer-debug"))]
        None
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct OutputStats {
    pub chunk_count: u64,
    pub chunk_len_min: usize,
    pub chunk_len_max: usize,
    pub first_body_rel_ns: u64,
    pub last_body_rel_ns: u64,
    pub finish_rel_ns: u64,
    pub callback_ns_total: u64,
    pub callback_ns_max: u64,
    pub write_ns_total: u64,
    pub write_ns_max: u64,
    pub write_ns_min: u64,
    pub write_failed_count: u64,
    pub pwrite_syscall_count: u64,
    pub pwrite_syscall_ns_total: u64,
    pub pwrite_syscall_ns_max: u64,
    pub pwrite_short_write_count: u64,
    pub pwrite_interrupted_count: u64,
    pub active_writer_mode: &'static str,
    pub direct_active: bool,
    pub mmap_madvise_count: u64,
    pub mmap_madvise_ns_total: u64,
    pub mmap_madvise_ns_max: u64,
    pub mmap_evicted_bytes: u64,
    pub direct_bounce_count: u64,
    pub direct_bounce_bytes: u64,
    pub direct_padded_tail_bytes: u64,
}
impl OutputStats {
    pub(crate) fn chunk(&mut self, len: usize, start_rel_ns: Option<u64>, callback_ns: u64) {
        self.chunk_count += 1;
        if self.chunk_count == 1 || len < self.chunk_len_min {
            self.chunk_len_min = len;
        }
        self.chunk_len_max = self.chunk_len_max.max(len);
        if let Some(start_rel_ns) = start_rel_ns {
            if self.chunk_count == 1 {
                self.first_body_rel_ns = start_rel_ns;
            }
            self.last_body_rel_ns = start_rel_ns;
        }
        self.callback_ns_total = self.callback_ns_total.saturating_add(callback_ns);
        self.callback_ns_max = self.callback_ns_max.max(callback_ns);
    }
    pub(crate) fn write_attempted(&mut self, write_ns: u64, io: Result<&IoStats, &WriteError>) {
        self.write_ns_total = self.write_ns_total.saturating_add(write_ns);
        self.write_ns_max = self.write_ns_max.max(write_ns);
        if self.write_ns_min == 0 || write_ns < self.write_ns_min {
            self.write_ns_min = write_ns;
        }
        let Ok(io) = io else {
            self.write_failed_count += 1;
            return;
        };
        self.pwrite_syscall_count += io.calls;
        self.pwrite_syscall_ns_total = self
            .pwrite_syscall_ns_total
            .saturating_add(io.syscall_ns_total);
        self.pwrite_syscall_ns_max = self.pwrite_syscall_ns_max.max(io.syscall_ns_max);
        self.pwrite_short_write_count += io.short_writes;
        self.pwrite_interrupted_count += io.interrupted;
        self.evicted(io);
        self.direct_bounce_count += io.direct_bounce_count;
        self.direct_bounce_bytes = self.direct_bounce_bytes.saturating_add(io.bounce_bytes);
        self.direct_padded_tail_bytes = self
            .direct_padded_tail_bytes
            .saturating_add(io.padded_bytes);
    }
    pub(crate) fn evicted(&mut self, io: &IoStats) {
        self.mmap_madvise_count += io.madvise_count;
        self.mmap_madvise_ns_total = self
            .mmap_madvise_ns_total
            .saturating_add(io.madvise_ns_total);
        self.mmap_madvise_ns_max = self.mmap_madvise_ns_max.max(io.madvise_ns_max);
        self.mmap_evicted_bytes = self
            .mmap_evicted_bytes
            .saturating_add(io.mmap_evicted_bytes);
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct OutputCounters {
    pub bytes_enqueued: u64,
    pub bytes_written: u64,
    pub write_job_count: u64,
    pub requested_writer_mode: &'static str,
    pub requested_writer_requirement: &'static str,
    pub copy_mode: &'static str,
    pub copy_requested_bytes: u64,
    pub copy_fallback_bytes: u64,
    pub concurrent_callbacks_max: usize,
    pub callbacks_after_first_error: u64,
    pub callbacks_after_input_closed: u64,
    pub tickets_seen: u64,
    pub tickets_enqueued: u64,
    pub tickets_released_by_writer: u64,
    pub tickets_failed_pre_enqueue: u64,
    pub numa_active: bool,
    pub shard_count: usize,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct OutputSummary {
    pub stats: OutputStats,
    pub counters: OutputCounters,
}

pub(crate) fn output_summary_lines(summary: &OutputSummary) -> Vec<String> {
    let mut lines = vec![output_callbacks_line(summary), output_writes_line(summary)];
    let stats = &summary.stats;
    if stats.direct_active {
        lines.push(format!(
            "direct bounce_count={} bounce_bytes={} padded_tail_bytes={}",
            stats.direct_bounce_count, stats.direct_bounce_bytes, stats.direct_padded_tail_bytes,
        ));
    }
    let counters = &summary.counters;
    lines.push(format!(
        "mmap madvise_calls={} madvise_total_ms={} madvise_max_us={} evicted_bytes={} \
         copy_mode={} copy_mode_bytes={} copy_fallback_bytes={}",
        stats.mmap_madvise_count,
        ms(stats.mmap_madvise_ns_total),
        us(stats.mmap_madvise_ns_max),
        stats.mmap_evicted_bytes,
        counters.copy_mode,
        counters.copy_requested_bytes,
        counters.copy_fallback_bytes,
    ));
    lines.push(format!(
        "producer max_concurrent_callbacks={} after_first_error={} after_input_closed={}",
        counters.concurrent_callbacks_max,
        counters.callbacks_after_first_error,
        counters.callbacks_after_input_closed,
    ));
    lines.push(format!(
        "tickets seen={} enqueued={} released_by_writer={} failed_pre_enqueue={}",
        counters.tickets_seen,
        counters.tickets_enqueued,
        counters.tickets_released_by_writer,
        counters.tickets_failed_pre_enqueue,
    ));
    lines.push(format!(
        "locality numa_active={} shards={}",
        counters.numa_active, counters.shard_count
    ));
    lines
}

fn output_callbacks_line(summary: &OutputSummary) -> String {
    let stats = &summary.stats;
    let bytes = summary.counters.bytes_enqueued;
    let (chunk_avg, callback_avg_us) = match stats.chunk_count {
        0 => (0, 0),
        count => (bytes / count, us(stats.callback_ns_total / count)),
    };
    format!(
        "callbacks count={} bytes={bytes} chunk_min={} chunk_max={} chunk_avg={chunk_avg} \
         first_body_ms={} last_body_ms={} finish_ms={} callback_total_ms={} \
         callback_avg_us={callback_avg_us} callback_max_us={}",
        stats.chunk_count,
        stats.chunk_len_min,
        stats.chunk_len_max,
        ms(stats.first_body_rel_ns),
        ms(stats.last_body_rel_ns),
        ms(stats.finish_rel_ns),
        ms(stats.callback_ns_total),
        us(stats.callback_ns_max),
    )
}

fn output_writes_line(summary: &OutputSummary) -> String {
    let stats = &summary.stats;
    let counters = &summary.counters;
    let count = counters.write_job_count;
    let write_avg_us = stats.write_ns_total.checked_div(count).map_or(0, us);
    format!(
        "writes requested_mode={} requirement={} active_mode={} count={count} failed={} \
         bytes={} write_total_ms={} write_avg_us={write_avg_us} write_min_us={} \
         write_max_ms={} pwrite_calls={} pwrite_total_ms={} pwrite_max_us={} pwrite_short={} \
         pwrite_intr={}",
        counters.requested_writer_mode,
        counters.requested_writer_requirement,
        stats.active_writer_mode,
        stats.write_failed_count,
        counters.bytes_written,
        ms(stats.write_ns_total),
        us(stats.write_ns_min),
        ms(stats.write_ns_max),
        stats.pwrite_syscall_count,
        ms(stats.pwrite_syscall_ns_total),
        us(stats.pwrite_syscall_ns_max),
        stats.pwrite_short_write_count,
        stats.pwrite_interrupted_count,
    )
}

pub(crate) fn log_output_summary(summary: &OutputSummary) {
    if ENABLED {
        for line in output_summary_lines(summary) {
            log("download_diagnostics", &line);
        }
    }
}

pub(crate) fn memory_snapshot_line(
    label: &str,
    snapshot: &std::io::Result<Option<MemorySnapshot>>,
) -> Option<String> {
    match snapshot {
        Ok(snapshot) => snapshot.map(|value| {
            format!(
                "memory label={label} rss_kib={} dirty_kib={} writeback_kib={}",
                value.rss_kib, value.dirty_kib, value.writeback_kib
            )
        }),
        Err(error) => {
            let name = if error.kind() == std::io::ErrorKind::InvalidData {
                crate::local_error::STREAM_TOO_LONG
            } else {
                crate::cp::io_error_name(error)
            };
            Some(format!("memory label={label} read_error={name}"))
        }
    }
}

pub(crate) fn log_memory_snapshot(label: &str, page_size: usize) {
    if ENABLED && let Some(line) = memory_snapshot_line(label, &MemorySnapshot::read(page_size)) {
        log("download_diagnostics", &line);
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct ObjectPhases {
    pub total_ns: u64,
    pub file_prepare_ns: u64,
    pub file_create_ns: u64,
    pub preallocate_ns: u64,
    pub set_length_ns: u64,
    pub drain_ns: u64,
}

pub(crate) fn object_phases_line(phases: &ObjectPhases) -> String {
    format!(
        "phases total_ms={} file_prepare_ms={} file_create_ms={} preallocate_ms={} \
         set_length_ms={} drain_ms={}",
        ms(phases.total_ns),
        ms(phases.file_prepare_ns),
        ms(phases.file_create_ns),
        ms(phases.preallocate_ns),
        ms(phases.set_length_ns),
        ms(phases.drain_ns),
    )
}

pub(crate) fn log_object_phases(phases: &ObjectPhases) {
    if ENABLED {
        log("download_diagnostics", &object_phases_line(phases));
    }
}

pub(crate) fn shared_prefault_line(workers: Option<usize>) -> String {
    format!(
        "shared_prefault enabled={} workers={}",
        workers.is_some(),
        workers.unwrap_or(0)
    )
}

pub(crate) fn shared_prefault_unavailable_line(error: &WriteError) -> String {
    format!(
        "shared mmap prefault unavailable err={}",
        SetupError::write(error)
    )
}

pub(crate) fn log_shared_prefault(workers: Option<usize>, unavailable: Option<&WriteError>) {
    if ENABLED {
        if let Some(error) = unavailable {
            log(
                "download_shared_service",
                &shared_prefault_unavailable_line(error),
            );
        }
        log("download_shared_service", &shared_prefault_line(workers));
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct SharedServiceSummary {
    pub worker_count: usize,
    pub shard_count: usize,
    pub queue_capacity: usize,
    pub active_outputs_max: usize,
    pub pending_jobs_hwm: usize,
    pub shard_full_wait_count: u64,
    pub shard_full_wait_ns: u64,
    pub shard_full_wait_ns_max: u64,
    pub jobs_enqueued: u64,
    pub jobs_written: u64,
}

pub(crate) fn shared_service_summary_line(summary: &SharedServiceSummary) -> String {
    format!(
        "shared_writer workers={} shards={} queue_capacity={} max_active_outputs={} \
         pending_hwm={} shard_full_waits={} shard_full_wait_ms={} shard_full_wait_max_ms={} \
         jobs_enqueued={} jobs_written={}",
        summary.worker_count,
        summary.shard_count,
        summary.queue_capacity,
        summary.active_outputs_max,
        summary.pending_jobs_hwm,
        summary.shard_full_wait_count,
        ms(summary.shard_full_wait_ns),
        ms(summary.shard_full_wait_ns_max),
        summary.jobs_enqueued,
        summary.jobs_written,
    )
}

pub(crate) fn log_shared_service_summary(summary: &SharedServiceSummary) {
    if ENABLED {
        log(
            "download_diagnostics",
            &shared_service_summary_line(summary),
        );
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct PrefaultSummary {
    pub windows_populated: u64,
    pub windows_skipped: u64,
    pub windows_populated_clean: u64,
    pub windows_populated_partial: u64,
    pub gate_wait_count: u64,
    pub gate_wait_ns_total: u64,
    pub gate_wait_ns_max: u64,
    pub populate_ns_total: u64,
    pub populate_ns_max: u64,
    pub populated_bytes: u64,
    pub minor_faults: u64,
}
impl PrefaultSummary {
    pub(crate) fn gate_waited(&mut self, ns: u64) {
        self.gate_wait_count += 1;
        self.gate_wait_ns_total = self.gate_wait_ns_total.saturating_add(ns);
        self.gate_wait_ns_max = self.gate_wait_ns_max.max(ns);
    }
}

pub(crate) fn prefault_summary_lines(summary: &PrefaultSummary) -> [String; 2] {
    [
        format!(
            "mmap prefault stopped windows_populated={} windows_skipped={} windows_clean={} \
             windows_partial={}",
            summary.windows_populated,
            summary.windows_skipped,
            summary.windows_populated_clean,
            summary.windows_populated_partial,
        ),
        format!(
            "mmap prefault gate_waits={} gate_wait_total_ms={} gate_wait_max_ms={} \
             populate_total_ms={} populate_max_us={} populated_bytes={} minflt={}",
            summary.gate_wait_count,
            ms(summary.gate_wait_ns_total),
            ms(summary.gate_wait_ns_max),
            ms(summary.populate_ns_total),
            us(summary.populate_ns_max),
            summary.populated_bytes,
            summary.minor_faults,
        ),
    ]
}

pub(crate) fn log_prefault_summary(summary: &PrefaultSummary) {
    if ENABLED {
        for line in prefault_summary_lines(summary) {
            log("download_diagnostics", &line);
        }
    }
}

pub(crate) fn prefault_disabled_line(error: &str) -> String {
    format!("mmap prefault disabled err={error}")
}

pub(crate) fn log_prefault_disabled(error: &str) {
    if ENABLED {
        log("download_mmap_prefaulter", &prefault_disabled_line(error));
    }
}

pub(crate) fn prefault_spawn_failed_line(index: usize, error: &std::io::Error) -> String {
    format!(
        "mmap prefault thread spawn failed index={index} err={}",
        SetupError::spawn(error).name()
    )
}

pub(crate) fn log_prefault_spawn_failed(index: usize, error: &std::io::Error) {
    if ENABLED {
        log(
            "download_mmap_prefaulter",
            &prefault_spawn_failed_line(index, error),
        );
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct MmapWriterSetup {
    pub size: usize,
    pub page_size: usize,
    pub page_count: usize,
    pub eviction_batch_pages: usize,
    pub prefault_threads: usize,
    pub prefault_shared: bool,
    pub numa_active: bool,
    pub copy_mode: CopyMode,
}

pub(crate) fn mmap_writer_enabled_line(setup: &MmapWriterSetup) -> String {
    format!(
        "mmap writer enabled size={} page_size={} page_count={} eviction_batch_pages={} \
         prefault_threads={} prefault_window_bytes={} prefault_lookahead_bytes={} \
         prefault_shared={} numa_active={} copy_mode={}",
        setup.size,
        setup.page_size,
        setup.page_count,
        setup.eviction_batch_pages,
        setup.prefault_threads,
        PREFAULT_WINDOW,
        PREFAULT_LOOKAHEAD,
        setup.prefault_shared,
        setup.numa_active,
        copy_mode_name(setup.copy_mode),
    )
}

pub(crate) fn log_mmap_writer(setup: &MmapWriterSetup, prefault_unavailable: Option<&str>) {
    if ENABLED {
        if let Some(error) = prefault_unavailable {
            log(
                "download_mmap_writer",
                &format!("mmap prefault unavailable err={error}"),
            );
        }
        log("download_mmap_writer", &mmap_writer_enabled_line(setup));
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum MmapUnavailableReason<'a> {
    Os(&'a str),
    Preallocation(Preallocation),
    TooLarge(u64),
    MmapFailed(&'a str),
    EvictProbeFailed(&'a str),
}

pub(crate) fn mmap_unavailable_line(reason: MmapUnavailableReason<'_>) -> String {
    let reason = match reason {
        MmapUnavailableReason::Os(os) => format!("os={os}"),
        MmapUnavailableReason::Preallocation(status) => {
            format!("preallocation_status={}", preallocation_name(status))
        }
        MmapUnavailableReason::TooLarge(size) => {
            format!("object too large for address space size={size}")
        }
        MmapUnavailableReason::MmapFailed(error) => format!("mmap failed err={error}"),
        MmapUnavailableReason::EvictProbeFailed(error) => {
            format!("MADV_DONTNEED probe failed err={error}")
        }
    };
    format!("mmap writer unavailable: {reason}")
}

pub(crate) fn log_mmap_unavailable(reason: MmapUnavailableReason<'_>) {
    if ENABLED {
        log("download_mmap_writer", &mmap_unavailable_line(reason));
    }
}

pub(crate) fn mmap_evict_failed_line(start: usize, len: usize, error: &str) -> String {
    format!("mmap eviction failed start={start} len={len} err={error}")
}

pub(crate) fn log_mmap_evict_failed(start: usize, len: usize, error: &str) {
    if ENABLED {
        log(
            "download_mmap_writer",
            &mmap_evict_failed_line(start, len, error),
        );
    }
}

pub(crate) fn direct_writer_enabled_line(alignment: DirectAlignment) -> String {
    format!(
        "direct writer enabled memory_alignment={} offset_alignment={}",
        alignment.memory, alignment.offset
    )
}

pub(crate) fn log_direct_writer(alignment: DirectAlignment) {
    if ENABLED {
        log(
            "download_direct_writer",
            &direct_writer_enabled_line(alignment),
        );
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum DirectFallback<'a> {
    Unavailable(&'a str),
    Rejected(&'a str),
}

pub(crate) fn direct_fallback_line(fallback: DirectFallback<'_>) -> String {
    match fallback {
        DirectFallback::Unavailable(error) => {
            format!("preferred direct writer unavailable err={error}")
        }
        DirectFallback::Rejected(error) => {
            format!("preferred direct writer rejected by the file err={error}")
        }
    }
}

pub(crate) fn log_direct_fallback(fallback: DirectFallback<'_>) {
    if ENABLED {
        log("download_output", &direct_fallback_line(fallback));
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum LocalityInactiveReason<'a> {
    Disabled,
    Unavailable(&'a str),
    Os(&'a str),
    SingleNode,
}

pub(crate) fn locality_inactive_line(reason: LocalityInactiveReason<'_>) -> String {
    let reason = match reason {
        LocalityInactiveReason::Disabled => "disabled".to_owned(),
        LocalityInactiveReason::Unavailable(error) => format!("unavailable err={error}"),
        LocalityInactiveReason::Os(os) => format!("os os={os}"),
        LocalityInactiveReason::SingleNode => "single-node".to_owned(),
    };
    format!("locality numa_active=false reason={reason}")
}

pub(crate) fn log_locality_inactive(reason: LocalityInactiveReason<'_>) {
    if ENABLED {
        log("download_locality_context", &locality_inactive_line(reason));
    }
}

pub(crate) fn locality_active_lines(mode: NumaMode, nodes: &[numa::NodeInfo]) -> Vec<String> {
    let mut lines = vec![format!(
        "locality numa_active=true mode={} shards={} stripe_bytes={STRIPE_BYTES}",
        numa_mode_name(mode),
        nodes.len(),
    )];
    lines.extend(nodes.iter().enumerate().map(|(shard, node)| {
        format!(
            "locality shard={shard} node={} cpus={} cpu_list={}",
            node.id,
            node.cpu_count,
            node.cpu_list()
        )
    }));
    lines
}

pub(crate) fn log_locality_active(mode: NumaMode, nodes: &[numa::NodeInfo]) {
    if ENABLED {
        for line in locality_active_lines(mode, nodes) {
            log("download_locality_context", &line);
        }
    }
}

pub(crate) fn locality_truncated_line(limit: usize, topology_nodes: usize) -> String {
    format!(
        "locality dropping nodes beyond shard limit limit={limit} topology_nodes={topology_nodes}"
    )
}

pub(crate) fn log_locality_truncated(limit: usize, topology_nodes: usize) {
    if ENABLED {
        log(
            "download_locality_context",
            &locality_truncated_line(limit, topology_nodes),
        );
    }
}

pub(crate) fn numa_mode_name(mode: NumaMode) -> &'static str {
    match mode {
        NumaMode::Disabled => "disabled",
        NumaMode::SameNode => "same_node",
        NumaMode::AllNodes => "all_nodes",
    }
}

pub(crate) fn preallocation_name(status: Preallocation) -> &'static str {
    match status {
        Preallocation::NotNeeded => "not_needed",
        Preallocation::Confirmed => "confirmed",
        Preallocation::Unsupported => "unsupported",
    }
}

pub(crate) fn copy_mode_name(mode: CopyMode) -> &'static str {
    match mode {
        CopyMode::Memcpy => "memcpy",
        CopyMode::Nt => "nt",
        CopyMode::RepMovsb => "rep_movsb",
    }
}

pub(crate) fn writer_mode_name(mode: WriterMode) -> &'static str {
    match mode {
        WriterMode::Pwrite => "pwrite",
        WriterMode::Mmap => "mmap",
        WriterMode::Direct => "direct",
        WriterMode::Crt => "crt",
    }
}

pub(crate) fn requirement_name(requirement: Requirement) -> &'static str {
    match requirement {
        Requirement::Preferred => "preferred",
        Requirement::Required => "required",
    }
}

pub(crate) fn debug_line(scope: &str, message: &str, color: bool) -> String {
    if color {
        format!("\x1b[35m\x1b[1mdebug\x1b[0m\x1b[2m\x1b[1m({scope}): \x1b[0m{message}\n")
    } else {
        format!("debug({scope}): {message}\n")
    }
}

pub(crate) fn terminal_color(no_color: bool, clicolor_force: bool, is_terminal: bool) -> bool {
    !no_color && (is_terminal || clicolor_force)
}

fn stderr_color() -> bool {
    static COLOR: OnceLock<bool> = OnceLock::new();
    *COLOR.get_or_init(|| {
        terminal_color(
            std::env::var_os("NO_COLOR").is_some(),
            std::env::var_os("CLICOLOR_FORCE").is_some(),
            std::io::stderr().is_terminal(),
        )
    })
}

#[cfg(all(test, feature = "download-writer-debug"))]
thread_local! {
    static CAPTURED: std::cell::RefCell<Option<Vec<String>>> =
        const { std::cell::RefCell::new(None) };
}

#[cfg(all(test, feature = "download-writer-debug"))]
pub(crate) fn capture(run: impl FnOnce()) -> Vec<String> {
    CAPTURED.with_borrow_mut(|captured| *captured = Some(Vec::new()));
    run();
    CAPTURED.with_borrow_mut(Option::take).unwrap_or_default()
}

#[cfg(all(test, feature = "download-writer-debug"))]
fn captured(scope: &str, message: &str) -> bool {
    CAPTURED.with_borrow_mut(|captured| match captured {
        Some(lines) => {
            lines.push(format!("debug({scope}): {message}"));
            true
        }
        None => false,
    })
}

fn log(scope: &str, message: &str) {
    #[cfg(all(test, feature = "download-writer-debug"))]
    if captured(scope, message) {
        return;
    }
    let line = debug_line(scope, message, stderr_color());
    let _ = std::io::stderr().lock().write_all(line.as_bytes());
}

pub(crate) fn start() -> Option<Instant> {
    ENABLED.then(Instant::now)
}

pub(crate) fn elapsed_ns(start: Option<Instant>) -> u64 {
    start.map_or(0, |start| {
        u64::try_from(start.elapsed().as_nanos()).unwrap_or(u64::MAX)
    })
}

pub(crate) fn ns_between(start: Instant, end: Instant) -> u64 {
    u64::try_from(end.saturating_duration_since(start).as_nanos()).unwrap_or(u64::MAX)
}

fn ms(ns: u64) -> u64 {
    ns / 1_000_000
}

fn us(ns: u64) -> u64 {
    ns / 1_000
}

#[cfg(test)]
mod tests;
