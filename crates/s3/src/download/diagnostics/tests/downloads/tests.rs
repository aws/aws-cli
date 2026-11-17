#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::*;
use crate::download::{
    Body, SharedConfig, SharedOutput, SharedWriterService,
    service::ThreadSpawner,
    testing::fakes::{self, FakePlatform},
};
use std::sync::Arc;

fn prepare(mode: WriterMode, size: u64) -> (SharedWriterService, SharedOutput) {
    let platform = Arc::new(FakePlatform::default());
    let service = SharedWriterService::start_with(
        SharedConfig {
            writer: fakes::config(mode),
            custom_writer_required: true,
            in_flight_max: 8,
            ..SharedConfig::default()
        },
        platform,
        Arc::new(ThreadSpawner),
    )
    .unwrap();
    let slot = service.acquire_output_slot(size).unwrap();
    let output = service.prepare(&slot, fakes::file(), size).unwrap();
    drop(slot);
    (service, output)
}

#[test]
fn a_download_of_two_parts_counts_its_bodies_tickets_and_writes() {
    let (service, output) = two_parts();
    if let Some(OutputSummary { stats, counters }) = output.summary() {
        assert_two_parts_stats(&stats);
        assert_eq!(
            counters,
            OutputCounters {
                bytes_enqueued: 8,
                bytes_written: 8,
                write_job_count: 2,
                requested_writer_mode: "pwrite",
                requested_writer_requirement: "required",
                copy_mode: "memcpy",
                concurrent_callbacks_max: 1,
                tickets_seen: 2,
                tickets_enqueued: 2,
                tickets_released_by_writer: 2,
                shard_count: 1,
                ..OutputCounters::default()
            }
        );
    }
    service.close_and_join();
}
fn two_parts() -> (SharedWriterService, SharedOutput) {
    let (service, output) = prepare(WriterMode::Pwrite, 8);
    output.enqueue(Body::owned(0, vec![1; 4])).unwrap();
    output.enqueue(Body::owned(4, vec![2; 4])).unwrap();
    output.note_finish();
    assert_eq!(output.finish(true).unwrap().written_bytes, 8);
    (service, output)
}
fn assert_two_parts_stats(stats: &OutputStats) {
    assert_eq!(
        (stats.chunk_count, stats.chunk_len_min, stats.chunk_len_max),
        (2, 4, 4)
    );
    assert!(stats.finish_rel_ns > 0);
    assert!(stats.first_body_rel_ns <= stats.last_body_rel_ns);
    assert!(stats.last_body_rel_ns <= stats.finish_rel_ns);
    assert_eq!(
        (stats.write_failed_count, stats.pwrite_syscall_count),
        (0, 2)
    );
    assert_eq!(
        (stats.active_writer_mode, stats.direct_active),
        ("pwrite", false)
    );
}

#[test]
fn late_bodies_count_as_refused_tickets() {
    let (service, output) = two_parts();
    assert!(output.enqueue(Body::owned(0, vec![3; 4])).is_err());
    assert!(output.enqueue(Body::owned(4, vec![4; 4])).is_err());
    if let Some(OutputSummary { counters, .. }) = output.summary() {
        assert_eq!(
            (
                counters.callbacks_after_input_closed,
                counters.callbacks_after_first_error,
            ),
            (1, 1)
        );
        assert_eq!(
            (counters.tickets_seen, counters.tickets_failed_pre_enqueue),
            (4, 2)
        );
    }
    service.close_and_join();
}

#[test]
fn a_single_request_body_counts_a_body_without_a_ticket() {
    let (service, output) = prepare(WriterMode::Pwrite, 5);
    output.write_now(b"hello", 0).unwrap();
    output.finish(true).unwrap();
    if let Some(OutputSummary { stats, counters }) = output.summary() {
        assert_eq!((stats.chunk_count, counters.write_job_count), (1, 1));
        assert_eq!((counters.tickets_seen, counters.tickets_enqueued), (0, 0));
        assert_eq!(counters.concurrent_callbacks_max, 1);
    }
    service.close_and_join();
}

#[test]
fn a_mapped_download_counts_its_eviction_advice() {
    let (service, output) = prepare(WriterMode::Mmap, 8192);
    output.enqueue(Body::owned(0, vec![1; 4096])).unwrap();
    output.enqueue(Body::owned(4096, vec![2; 4096])).unwrap();
    output.finish(true).unwrap();
    if let Some(OutputSummary { stats, counters }) = output.summary() {
        assert_eq!(stats.active_writer_mode, "mmap");
        assert_eq!(
            (stats.mmap_madvise_count, stats.mmap_evicted_bytes),
            (1, 8192)
        );
        assert_eq!(stats.pwrite_syscall_count, 0);
        assert_eq!(
            counters.copy_requested_bytes + counters.copy_fallback_bytes,
            8192
        );
    }
    service.close_and_join();
}

#[test]
fn a_direct_download_counts_its_bounced_tail() {
    let (service, output) = prepare(WriterMode::Direct, 20);
    output.enqueue(Body::owned(0, vec![1; 16])).unwrap();
    output.enqueue(Body::owned(16, vec![2; 4])).unwrap();
    output.finish(true).unwrap();
    if let Some(OutputSummary { stats, .. }) = output.summary() {
        assert_eq!(
            (stats.active_writer_mode, stats.direct_active),
            ("direct", true)
        );
        assert!(stats.direct_bounce_count >= 1);
        assert_eq!(stats.direct_padded_tail_bytes, 12);
    }
    service.close_and_join();
}
