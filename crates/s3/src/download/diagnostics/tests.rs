use super::*;
#[cfg(feature = "download-writer-debug")]
use std::sync::Arc;

#[test]
fn the_phase_line_reports_whole_milliseconds_with_drain_ms() {
    let phases = ObjectPhases {
        total_ns: 9_999_999,
        file_prepare_ns: 3_000_000,
        file_create_ns: 1_000_001,
        preallocate_ns: 999_999,
        set_length_ns: 2_000_000,
        drain_ns: 4_500_000,
    };
    assert_eq!(
        object_phases_line(&phases),
        "phases total_ms=9 file_prepare_ms=3 file_create_ms=1 preallocate_ms=0 \
         set_length_ms=2 drain_ms=4"
    );
}

#[test]
fn nothing_is_measured_without_instrumentation() {
    assert_eq!(start().is_some(), ENABLED);
    assert_eq!(elapsed_ns(None), 0);
}

#[test]
fn the_shared_prefault_line_reports_the_pool_and_its_workers() {
    assert_eq!(
        shared_prefault_line(Some(4)),
        "shared_prefault enabled=true workers=4"
    );
    assert_eq!(
        shared_prefault_line(None),
        "shared_prefault enabled=false workers=0"
    );
}

#[test]
fn the_shared_prefault_unavailable_line_names_the_spawn_error() {
    for (kind, name) in [
        (
            std::io::ErrorKind::WouldBlock,
            "Insufficient system resources",
        ),
        (std::io::ErrorKind::OutOfMemory, "Out of memory"),
    ] {
        assert_eq!(
            shared_prefault_unavailable_line(&WriteError::from(std::io::Error::from(kind))),
            format!("shared mmap prefault unavailable err={name}")
        );
    }
}

#[test]
fn the_mmap_writer_line_reports_a_pooled_or_private_prefaulter() {
    let pooled = MmapWriterSetup {
        size: 1_048_577,
        page_size: 4096,
        page_count: 257,
        eviction_batch_pages: 131_072,
        prefault_threads: 0,
        prefault_shared: true,
        numa_active: false,
        copy_mode: CopyMode::RepMovsb,
    };
    assert_eq!(
        mmap_writer_enabled_line(&pooled),
        "mmap writer enabled size=1048577 page_size=4096 page_count=257 \
         eviction_batch_pages=131072 prefault_threads=0 prefault_window_bytes=8388608 \
         prefault_lookahead_bytes=268435456 prefault_shared=true numa_active=false \
         copy_mode=rep_movsb"
    );
    let private = MmapWriterSetup {
        prefault_threads: 4,
        prefault_shared: false,
        numa_active: true,
        copy_mode: CopyMode::Nt,
        ..pooled
    };
    assert!(mmap_writer_enabled_line(&private).ends_with(
        "prefault_threads=4 prefault_window_bytes=8388608 \
         prefault_lookahead_bytes=268435456 prefault_shared=false numa_active=true copy_mode=nt"
    ));
    assert_eq!(copy_mode_name(CopyMode::Memcpy), "memcpy");
}

#[test]
fn the_shared_writer_line_reports_full_shard_waits() {
    let summary = SharedServiceSummary {
        worker_count: 8,
        shard_count: 2,
        queue_capacity: 3072,
        active_outputs_max: 512,
        pending_jobs_hwm: 513,
        shard_full_wait_count: 3,
        shard_full_wait_ns: 7_999_999,
        shard_full_wait_ns_max: 2_000_000,
        jobs_enqueued: 1025,
        jobs_written: 1024,
    };
    assert_eq!(
        shared_service_summary_line(&summary),
        "shared_writer workers=8 shards=2 queue_capacity=3072 max_active_outputs=512 \
         pending_hwm=513 shard_full_waits=3 shard_full_wait_ms=7 shard_full_wait_max_ms=2 \
         jobs_enqueued=1025 jobs_written=1024"
    );
}

#[test]
fn the_prefault_lines_report_coverage_and_pacing() {
    let mut summary = PrefaultSummary {
        windows_populated: 5,
        windows_skipped: 2,
        windows_populated_clean: 3,
        windows_populated_partial: 2,
        populate_ns_total: 12_999_999,
        populate_ns_max: 4_567_891,
        populated_bytes: 41_943_040,
        minor_faults: 10_240,
        ..PrefaultSummary::default()
    };
    summary.gate_waited(1_500_000);
    summary.gate_waited(2_600_000);
    assert_eq!(
        prefault_summary_lines(&summary),
        [
            "mmap prefault stopped windows_populated=5 windows_skipped=2 windows_clean=3 \
             windows_partial=2",
            "mmap prefault gate_waits=2 gate_wait_total_ms=4 gate_wait_max_ms=2 \
             populate_total_ms=12 populate_max_us=4567 populated_bytes=41943040 minflt=10240",
        ]
    );
    assert_eq!(
        prefault_disabled_line("madvise failed"),
        "mmap prefault disabled err=madvise failed"
    );
}

fn direct_summary() -> OutputSummary {
    OutputSummary {
        stats: OutputStats {
            chunk_count: 3,
            chunk_len_min: 1024,
            chunk_len_max: 8_388_608,
            first_body_rel_ns: 12_345_678,
            last_body_rel_ns: 98_765_432,
            finish_rel_ns: 123_456_789,
            callback_ns_total: 9_000_000,
            callback_ns_max: 4_567_891,
            write_ns_total: 30_000_000,
            write_ns_max: 12_345_678,
            write_ns_min: 2_000_999,
            write_failed_count: 1,
            pwrite_syscall_count: 4,
            pwrite_syscall_ns_total: 25_999_999,
            pwrite_syscall_ns_max: 9_999_999,
            pwrite_short_write_count: 1,
            pwrite_interrupted_count: 2,
            active_writer_mode: "direct",
            direct_active: true,
            direct_bounce_count: 1,
            direct_bounce_bytes: 1023,
            direct_padded_tail_bytes: 1,
            ..OutputStats::default()
        },
        counters: OutputCounters {
            bytes_enqueued: 8_390_656,
            bytes_written: 8_390_655,
            write_job_count: 2,
            requested_writer_mode: "direct",
            requested_writer_requirement: "preferred",
            copy_mode: "memcpy",
            concurrent_callbacks_max: 1,
            callbacks_after_first_error: 2,
            callbacks_after_input_closed: 3,
            tickets_seen: 6,
            tickets_enqueued: 3,
            tickets_released_by_writer: 4,
            tickets_failed_pre_enqueue: 5,
            numa_active: true,
            shard_count: 2,
            ..OutputCounters::default()
        },
    }
}

#[test]
fn the_output_summary_lines_report_main_fields_in_order() {
    assert_eq!(
        output_summary_lines(&direct_summary()),
        [
            "callbacks count=3 bytes=8390656 chunk_min=1024 chunk_max=8388608 \
             chunk_avg=2796885 first_body_ms=12 last_body_ms=98 finish_ms=123 \
             callback_total_ms=9 callback_avg_us=3000 callback_max_us=4567",
            "writes requested_mode=direct requirement=preferred active_mode=direct count=2 \
             failed=1 bytes=8390655 write_total_ms=30 write_avg_us=15000 write_min_us=2000 \
             write_max_ms=12 pwrite_calls=4 pwrite_total_ms=25 pwrite_max_us=9999 \
             pwrite_short=1 pwrite_intr=2",
            "direct bounce_count=1 bounce_bytes=1023 padded_tail_bytes=1",
            "mmap madvise_calls=0 madvise_total_ms=0 madvise_max_us=0 evicted_bytes=0 \
             copy_mode=memcpy copy_mode_bytes=0 copy_fallback_bytes=0",
            "producer max_concurrent_callbacks=1 after_first_error=2 after_input_closed=3",
            "tickets seen=6 enqueued=3 released_by_writer=4 failed_pre_enqueue=5",
            "locality numa_active=true shards=2",
        ]
    );
}

#[test]
fn a_mapped_output_summary_has_no_direct_line_and_zero_averages() {
    let mut summary = OutputSummary::default();
    summary.stats.active_writer_mode = "mmap";
    summary.stats.mmap_madvise_count = 3;
    summary.stats.mmap_madvise_ns_total = 1_999_999;
    summary.stats.mmap_madvise_ns_max = 999_999;
    summary.stats.mmap_evicted_bytes = 12_288;
    summary.counters.bytes_enqueued = 7;
    summary.counters.copy_mode = "nt";
    summary.counters.copy_requested_bytes = 8192;
    summary.counters.copy_fallback_bytes = 4096;
    summary.counters.shard_count = 1;
    let lines = output_summary_lines(&summary);
    assert_eq!(lines.len(), 6);
    assert!(lines[0].contains(" bytes=7 chunk_min=0 chunk_max=0 chunk_avg=0 "));
    assert!(lines[0].contains(" callback_avg_us=0 "));
    assert!(lines[1].contains(" active_mode=mmap count=0 "));
    assert!(lines[1].contains(" write_avg_us=0 "));
    assert_eq!(
        lines[2],
        "mmap madvise_calls=3 madvise_total_ms=1 madvise_max_us=999 evicted_bytes=12288 \
         copy_mode=nt copy_mode_bytes=8192 copy_fallback_bytes=4096"
    );
    assert_eq!(lines[5], "locality numa_active=false shards=1");
}

#[test]
fn the_memory_line_reports_a_snapshot_or_names_the_read_error() {
    let snapshot = MemorySnapshot {
        rss_kib: 8,
        dirty_kib: 42,
        writeback_kib: 7,
    };
    assert_eq!(
        memory_snapshot_line("summary", &Ok(Some(snapshot))).as_deref(),
        Some("memory label=summary rss_kib=8 dirty_kib=42 writeback_kib=7")
    );
    assert_eq!(memory_snapshot_line("summary", &Ok(None)), None);
    for (error, name) in [
        (
            std::io::ErrorKind::NotFound.into(),
            "No such file or directory",
        ),
        (
            std::io::ErrorKind::PermissionDenied.into(),
            "Permission denied",
        ),
        (std::io::ErrorKind::InvalidData.into(), "Input too long"),
    ] {
        assert_eq!(
            memory_snapshot_line("summary", &Err(error)),
            Some(format!("memory label=summary read_error={name}"))
        );
    }
}

#[test]
fn traced_counters_exist_only_with_instrumentation() {
    let mut traced = Traced::new(OutputStats::default());
    traced.update(|stats| stats.chunk_count += 1);
    assert_eq!(
        traced.get().map(|stats| stats.chunk_count),
        ENABLED.then_some(1)
    );
    if !ENABLED {
        assert_eq!(std::mem::size_of::<Traced<OutputStats>>(), 0);
    }
}

#[test]
fn a_debug_line_is_plain_or_wrapped_in_ansi_colours() {
    assert_eq!(
        debug_line("download_output", "a b=1", false),
        "debug(download_output): a b=1\n"
    );
    assert_eq!(
        debug_line("download_output", "a b=1", true).as_bytes(),
        b"\x1b[35m\x1b[1mdebug\x1b[0m\x1b[2m\x1b[1m(download_output): \x1b[0ma b=1\n"
    );
}

#[test]
fn debug_line_colour_follows_no_color_clicolor_force_and_the_terminal() {
    for (no_color, force, terminal, color) in [
        (false, false, false, false),
        (false, false, true, true),
        (false, true, false, true),
        (false, true, true, true),
        (true, false, true, false),
        (true, true, false, false),
        (true, true, true, false),
    ] {
        assert_eq!(
            terminal_color(no_color, force, terminal),
            color,
            "NO_COLOR={no_color} CLICOLOR_FORCE={force} terminal={terminal}"
        );
    }
}

#[test]
fn the_mmap_unavailable_lines_name_each_reason() {
    use MmapUnavailableReason as Reason;
    for (reason, text) in [
        (Reason::Os("macos"), "os=macos"),
        (
            Reason::Preallocation(Preallocation::Unsupported),
            "preallocation_status=unsupported",
        ),
        (
            Reason::Preallocation(Preallocation::NotNeeded),
            "preallocation_status=not_needed",
        ),
        (
            Reason::TooLarge(u64::MAX),
            "object too large for address space size=18446744073709551615",
        ),
        (
            Reason::MmapFailed("Memory mapping not supported"),
            "mmap failed err=Memory mapping not supported",
        ),
        (
            Reason::EvictProbeFailed("madvise failed"),
            "MADV_DONTNEED probe failed err=madvise failed",
        ),
    ] {
        assert_eq!(
            mmap_unavailable_line(reason),
            format!("mmap writer unavailable: {text}")
        );
    }
    assert_eq!(preallocation_name(Preallocation::Confirmed), "confirmed");
    assert_eq!(
        mmap_evict_failed_line(8192, 4096, "madvise failed"),
        "mmap eviction failed start=8192 len=4096 err=madvise failed"
    );
}

#[test]
fn the_direct_writer_lines_report_alignment_and_fallbacks() {
    assert_eq!(
        direct_writer_enabled_line(DirectAlignment {
            memory: 512,
            offset: 4096
        }),
        "direct writer enabled memory_alignment=512 offset_alignment=4096"
    );
    assert_eq!(
        direct_fallback_line(DirectFallback::Unavailable(
            "DownloadDirectWriterUnavailable"
        )),
        "preferred direct writer unavailable err=DownloadDirectWriterUnavailable"
    );
    assert_eq!(
        direct_fallback_line(DirectFallback::Rejected("DownloadDirectInvalidAlignment")),
        "preferred direct writer rejected by the file err=DownloadDirectInvalidAlignment"
    );
}

#[test]
fn the_locality_lines_report_inactive_and_active_placement() {
    use LocalityInactiveReason as Reason;
    for (reason, text) in [
        (Reason::Disabled, "disabled"),
        (
            Reason::Unavailable("NumaUnsupported"),
            "unavailable err=NumaUnsupported",
        ),
        (Reason::Os("macos"), "os os=macos"),
        (Reason::SingleNode, "single-node"),
    ] {
        assert_eq!(
            locality_inactive_line(reason),
            format!("locality numa_active=false reason={text}")
        );
    }
    let mut cpus = numa::CpuSet::default();
    for cpu in [0, 1, 2, 3, 8] {
        assert!(cpus.set(cpu).is_ok());
    }
    let nodes = [
        numa::NodeInfo::new(1, cpus, "0-3,8"),
        numa::NodeInfo::new(3, cpus, "0-3,8"),
    ];
    assert_eq!(
        locality_active_lines(NumaMode::AllNodes, &nodes),
        [
            "locality numa_active=true mode=all_nodes shards=2 stripe_bytes=67108864",
            "locality shard=0 node=1 cpus=5 cpu_list=0-3,8",
            "locality shard=1 node=3 cpus=5 cpu_list=0-3,8",
        ]
    );
    assert!(locality_active_lines(NumaMode::SameNode, &nodes[..1])[0].contains(" mode=same_node "));
    assert_eq!(numa_mode_name(NumaMode::Disabled), "disabled");
    assert_eq!(
        locality_truncated_line(16, 17),
        "locality dropping nodes beyond shard limit limit=16 topology_nodes=17"
    );
}

#[test]
#[cfg(unix)]
fn failed_platform_calls_take_mains_names() {
    use super::super::platform::{advise_error_name, direct_io_error_name, mmap_error_name};
    use std::io::{Error, ErrorKind};
    for (errno, name) in [
        (libc::ENODEV, "Memory mapping not supported"),
        (libc::EACCES, "Permission denied"),
        (libc::ETXTBSY, "Permission denied"),
        (libc::EAGAIN, "Locked memory limit exceeded"),
        (libc::ENOMEM, "Out of memory"),
        (libc::EINVAL, "Unexpected error"),
    ] {
        assert_eq!(mmap_error_name(&Error::from_raw_os_error(errno)), name);
    }
    for (error, name) in [
        (
            Error::from_raw_os_error(libc::EINVAL),
            "DownloadDirectWriterUnavailable",
        ),
        (
            Error::from_raw_os_error(libc::EOPNOTSUPP),
            "DownloadDirectWriterUnavailable",
        ),
        (
            Error::from(ErrorKind::Unsupported),
            "DownloadDirectWriterUnavailable",
        ),
        (
            Error::from_raw_os_error(libc::EBADF),
            "File not open for writing",
        ),
        (Error::from_raw_os_error(libc::EIO), "Unexpected error"),
    ] {
        assert_eq!(direct_io_error_name(&error), name);
    }
    assert_eq!(
        advise_error_name(&Error::from_raw_os_error(libc::EINVAL)),
        "madvise failed"
    );
    assert_eq!(
        advise_error_name(&Error::from(ErrorKind::Unsupported)),
        "Operation not supported"
    );
}

#[cfg(feature = "download-writer-debug")]
fn prepare_lines(
    platform: &Arc<crate::download::testing::fakes::FakePlatform>,
    mode: WriterMode,
    requirement: Requirement,
    size: u64,
) -> Vec<String> {
    use crate::download::{
        LocalityContext, WriterConfig, output::Output, output::Policy, platform::Platform,
        prefault::PrefaultSource, service::ThreadSpawner, testing::fakes,
    };
    let config = WriterConfig {
        requirement,
        ..fakes::config(mode)
    };
    capture(|| {
        let output = Output::prepare(
            fakes::file(),
            size,
            Policy {
                config: &config,
                prefault: PrefaultSource::Disabled,
                spawner: &ThreadSpawner,
            },
            Arc::clone(platform) as Arc<dyn Platform>,
            &LocalityContext::default(),
            &mut ObjectPhases::default(),
        );
        if let Ok(output) = output {
            let _ = output.conclude(false);
            let _ = output.close_file();
        }
    })
}

#[test]
#[cfg(feature = "download-writer-debug")]
fn a_preferred_direct_writer_logs_why_it_is_unavailable() {
    use std::sync::atomic::Ordering;
    let cases: &[bool] = if cfg!(unix) { &[false, true] } else { &[false] };
    for &refused in cases {
        let platform = Arc::new(crate::download::testing::fakes::FakePlatform::default());
        if refused {
            platform.direct_refused.store(true, Ordering::Relaxed);
        } else {
            platform.direct_unavailable.store(true, Ordering::Relaxed);
        }
        let lines = prepare_lines(&platform, WriterMode::Direct, Requirement::Preferred, 4096);
        assert_eq!(
            lines[0],
            "debug(download_output): preferred direct writer unavailable \
             err=DownloadDirectWriterUnavailable"
        );
        assert!(
            lines[1].starts_with("debug(download_mmap_writer): mmap writer enabled size=4096 ")
        );
        assert_eq!(lines.len(), 2);
    }
}

#[test]
#[cfg(feature = "download-writer-debug")]
fn a_direct_writer_logs_its_alignment_or_its_rejection() {
    let platform = Arc::new(crate::download::testing::fakes::FakePlatform::default());
    *platform
        .alignment
        .lock()
        .unwrap_or_else(|error| error.into_inner()) = Some(DirectAlignment {
        memory: 3,
        offset: 512,
    });
    let lines = prepare_lines(&platform, WriterMode::Direct, Requirement::Preferred, 4096);
    assert_eq!(
        lines[0],
        "debug(download_output): preferred direct writer rejected by the file \
         err=DownloadDirectInvalidAlignment"
    );
    let platform = Arc::new(crate::download::testing::fakes::FakePlatform::default());
    assert_eq!(
        prepare_lines(&platform, WriterMode::Direct, Requirement::Required, 0),
        [
            "debug(download_direct_writer): direct writer enabled memory_alignment=16 \
          offset_alignment=16"
        ]
    );
}

#[test]
#[cfg(feature = "download-writer-debug")]
fn an_unavailable_mmap_writer_logs_each_reason() {
    use std::sync::atomic::{AtomicBool, Ordering};
    type Knob = fn(&crate::download::testing::fakes::FakePlatform) -> &AtomicBool;
    let os = format!("os={}", crate::download::platform::NAME);
    let knobs: [(Knob, &str); 3] = [
        (|platform| &platform.map_unavailable, os.as_str()),
        (
            |platform| &platform.unsupported_preallocation,
            "preallocation_status=unsupported",
        ),
        (
            |platform| &platform.evict_error,
            "MADV_DONTNEED probe failed err=Operation not supported",
        ),
    ];
    for (knob, reason) in knobs {
        let platform = Arc::new(crate::download::testing::fakes::FakePlatform::default());
        knob(&platform).store(true, Ordering::Relaxed);
        assert_eq!(
            prepare_lines(&platform, WriterMode::Mmap, Requirement::Preferred, 4096),
            [format!(
                "debug(download_mmap_writer): mmap writer unavailable: {reason}"
            )]
        );
    }
}

#[test]
#[cfg(feature = "download-writer-debug")]
fn a_failed_eviction_logs_its_byte_range() {
    use crate::download::{
        LocalityContext, output::Output, output::Policy, platform::Platform,
        prefault::PrefaultSource, service::ThreadSpawner, testing::fakes,
    };
    use std::sync::atomic::Ordering;
    let platform = Arc::new(fakes::FakePlatform::default());
    let config = fakes::config(WriterMode::Mmap);
    let output = Output::prepare(
        fakes::file(),
        10_000,
        Policy {
            config: &config,
            prefault: PrefaultSource::Disabled,
            spawner: &ThreadSpawner,
        },
        Arc::clone(&platform) as Arc<dyn Platform>,
        &LocalityContext::default(),
        &mut ObjectPhases::default(),
    );
    assert!(output.is_ok(), "a mapped output prepares");
    let Ok(output) = output else { return };
    platform.evict_error.store(true, Ordering::Relaxed);
    let lines = capture(|| {
        assert_eq!(output.write_now(0, &[1; 10_000]), Ok(()));
        assert_eq!(output.conclude(true), Err(WriteError::MmapEvictFailed));
    });
    assert_eq!(
        lines,
        [
            "debug(download_mmap_writer): mmap eviction failed start=0 len=10000 \
             err=Operation not supported"
        ]
    );
    let _ = output.close_file();
}

mod downloads;
