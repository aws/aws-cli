use super::*;
#[test]
fn memory_snapshot_parsers_read_distinct_rss_dirty_writeback_values() {
    let memory = "MemTotal: 123456 kB\nDirty: 42 kB\nWriteback: 7 kB\n";
    assert_eq!(
        MemorySnapshot::parse("10 2 0 0 0 0 0\n", memory, 4096),
        MemorySnapshot {
            rss_kib: 8,
            dirty_kib: 42,
            writeback_kib: 7
        }
    );
    assert_eq!(
        MemorySnapshot::parse("invalid", "Dirty: bad", 4096),
        MemorySnapshot::default()
    );
}
#[test]
#[cfg_attr(miri, ignore = "reads the host's proc files")]
fn memory_snapshot_reads_the_proc_files_only_with_instrumentation() {
    let read = MemorySnapshot::read(4096).map(|snapshot| snapshot.is_some());
    assert_eq!(
        read.ok(),
        Some(cfg!(all(
            target_os = "linux",
            feature = "download-writer-debug"
        )))
    );
}
