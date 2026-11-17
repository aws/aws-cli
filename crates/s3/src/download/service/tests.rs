#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::*;
use crate::download::{
    lock,
    output::DropCounter,
    platform::Advice,
    testing::fakes::{self, FakePlatform, Fault},
};
use std::sync::atomic::{AtomicUsize, Ordering};
mod queues;
mod reentry;
fn service(platform: Arc<FakePlatform>) -> SharedWriterService {
    writer_service(WriterMode::Pwrite, platform)
}
fn writer_service(mode: WriterMode, platform: Arc<FakePlatform>) -> SharedWriterService {
    SharedWriterService::start_with(
        SharedConfig {
            writer: fakes::config(mode),
            custom_writer_required: true,
            in_flight_max: 8,
            ..SharedConfig::default()
        },
        platform,
        Arc::new(ThreadSpawner),
    )
    .unwrap()
}
fn prepare(service: &SharedWriterService, size: u64) -> (OutputSlot, SharedOutput) {
    let slot = service.acquire_output_slot(size).unwrap();
    let output = service.prepare(&slot, fakes::file(), size).unwrap();
    (slot, output)
}
#[test]
fn shared_recursive_writer_uses_one_command_wide_worker_set_for_multiple_files() {
    let platform = Arc::new(FakePlatform::default());
    let service = service(platform);
    assert_eq!(service.worker_count(), 2);
    let (_first_slot, first) = prepare(&service, 4);
    let (_second_slot, second) = prepare(&service, 4);
    first.enqueue(Body::owned(0, vec![1; 4])).unwrap();
    second.enqueue(Body::owned(0, vec![2; 4])).unwrap();
    assert_eq!(first.finish(true).unwrap().written_bytes, 4);
    assert_eq!(second.finish(true).unwrap().written_bytes, 4);
    service.close_and_join();
    assert_eq!(service.shared.jobs_enqueued.load(Ordering::SeqCst), 2);
    assert_eq!(service.shared.jobs_written.load(Ordering::SeqCst), 2);
    assert_eq!(service.worker_count(), 0);
    let closed = service.acquire_output_slot(0).unwrap_err();
    assert_eq!(closed, WriteError::SharedWriterClosed);
    assert_eq!(closed.to_string(), "DownloadSharedWriterClosed");
}
#[test]
#[cfg_attr(miri, ignore = "real files and positional writes are covered natively")]
fn one_command_writer_serves_two_interleaved_files() {
    let directory = std::env::temp_dir().join(format!(
        "rust-shared-writer-{}-{:?}",
        std::process::id(),
        std::thread::current().id()
    ));
    std::fs::create_dir_all(&directory).unwrap();
    let service = SharedWriterService::start_with(
        SharedConfig {
            writer: WriterConfig {
                workers: Some(1),
                ..fakes::config(WriterMode::Pwrite)
            },
            custom_writer_required: true,
            in_flight_max: 2,
            ..SharedConfig::default()
        },
        Arc::new(NativePlatform),
        Arc::new(ThreadSpawner),
    )
    .unwrap();
    assert_eq!(service.worker_count(), 1);
    let (first_path, second_path) = (directory.join("first.bin"), directory.join("second.bin"));
    let first_slot = service.acquire_output_slot(11).unwrap();
    let first = service.prepare_path(&first_slot, &first_path, 11).unwrap();
    let second_slot = service.acquire_output_slot(6).unwrap();
    let second = service.prepare_path(&second_slot, &second_path, 6).unwrap();
    assert_eq!(service.active_outputs(), 2);
    first.enqueue(Body::owned(6, b"world".to_vec())).unwrap();
    second.enqueue(Body::owned(0, b"second".to_vec())).unwrap();
    first.enqueue(Body::owned(0, b"hello ".to_vec())).unwrap();
    assert_eq!(first.finish(true).unwrap().written_bytes, 11);
    assert_eq!(second.finish(true).unwrap().written_bytes, 6);
    first.close_file().unwrap();
    second.close_file().unwrap();
    service.close_and_join();
    assert_eq!(std::fs::read(&first_path).unwrap(), b"hello world");
    assert_eq!(std::fs::read(&second_path).unwrap(), b"second");
    let summary = service.summary();
    assert_eq!((summary.jobs_enqueued, summary.jobs_written), (3, 3));
    std::fs::remove_dir_all(&directory).unwrap();
}
#[test]
fn releases_a_jobs_ticket_after_writing_it() {
    let platform = Arc::new(FakePlatform::default());
    let service = service(Arc::clone(&platform));
    let (_slot, output) = prepare(&service, 1);
    let released = Arc::new(AtomicUsize::new(0));
    output
        .enqueue(Body::tracked(
            0,
            vec![b'x'],
            DropCounter(Arc::clone(&released)),
        ))
        .unwrap();
    let probe = output.clone();
    assert_eq!(output.finish(true).unwrap().written_bytes, 1);
    assert_eq!(released.load(Ordering::SeqCst), 1);
    assert_eq!(probe.prepared.output.pending_jobs(), 0);
    assert_eq!(probe.prepared.output.pending_jobs_hwm(), 1);
    assert_eq!(&lock(&platform.disk)[..1], b"x");
    service.close_and_join();
}
#[test]
fn a_failed_write_refuses_the_objects_next_body() {
    let platform = Arc::new(FakePlatform::default());
    lock(&platform.faults).push_back(Fault::Failed);
    let service = service(platform);
    let (_slot, output) = prepare(&service, 2);
    let released = Arc::new(AtomicUsize::new(0));
    output
        .enqueue(Body::tracked(
            0,
            vec![1],
            DropCounter(Arc::clone(&released)),
        ))
        .unwrap();
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while output.prepared.output.pending_jobs() != 0 {
        assert!(
            std::time::Instant::now() < deadline,
            "the write never completed"
        );
        std::thread::yield_now();
    }
    let failed = output.prepared.output.error().unwrap();
    assert!(matches!(failed, WriteError::Io { .. }), "{failed:?}");
    let refused = Arc::new(AtomicUsize::new(0));
    assert_eq!(
        output.enqueue(Body::tracked(1, vec![2], DropCounter(Arc::clone(&refused)))),
        Err(failed.clone())
    );
    assert_eq!(output.prepared.output.pending_jobs(), 0);
    assert_eq!(output.finish(true), Err(failed));
    assert_eq!(released.load(Ordering::SeqCst), 1);
    assert_eq!(refused.load(Ordering::SeqCst), 1);
    service.close_and_join();
}
#[test]
fn small_admission_bypasses_the_large_budget_and_blocked_slots_wake_or_close() {
    for large_waiter in [false, true] {
        for close_waiter in [false, true] {
            admit_past_a_full_budget(large_waiter, close_waiter);
        }
    }
}
fn admit_past_a_full_budget(large_waiter: bool, close_waiter: bool) {
    let service = Arc::new(
        SharedWriterService::start_with(
            SharedConfig {
                writer: WriterConfig {
                    workers: Some(1),
                    ..fakes::config(WriterMode::Pwrite)
                },
                custom_writer_required: true,
                in_flight_max: 3,
                ..SharedConfig::default()
            },
            Arc::new(FakePlatform::default()),
            Arc::new(ThreadSpawner),
        )
        .unwrap(),
    );
    let small = || {
        service
            .acquire_output_slot(CUSTOM_WRITER_SIZE_MIN - 1)
            .unwrap()
    };
    let mut held = vec![
        service.acquire_output_slot(CUSTOM_WRITER_SIZE_MIN).unwrap(),
        service.acquire_output_slot(1).unwrap(),
    ];
    if !large_waiter {
        held.push(small());
    }
    let size = if large_waiter {
        CUSTOM_WRITER_SIZE_MIN
    } else {
        1
    };
    let waiter = {
        let service = Arc::clone(&service);
        std::thread::spawn(move || service.acquire_output_slot(size))
    };
    wait_for(|| lock(&service.shared.slots).waiters == 1);
    if large_waiter {
        held.push(small());
    }
    end_the_wait(&service, held, OutputClass::of(size), close_waiter, waiter);
}
fn end_the_wait(
    service: &SharedWriterService,
    mut held: Vec<OutputSlot>,
    class: OutputClass,
    close_waiter: bool,
    waiter: std::thread::JoinHandle<Result<OutputSlot, WriteError>>,
) {
    if close_waiter {
        service.shared.close();
    } else {
        let position = held.iter().position(|slot| slot.class() == class).unwrap();
        drop(held.swap_remove(position));
    }
    match waiter.join().unwrap() {
        Ok(slot) => held.push(slot),
        Err(error) => assert!(close_waiter && error == WriteError::SharedWriterClosed),
    }
    assert_eq!(lock(&service.shared.slots).active, 3);
    assert_eq!(lock(&service.shared.slots).active_large, 1);
    drop(held);
    assert_eq!(lock(&service.shared.slots).active, 0);
    assert_eq!(lock(&service.shared.slots).active_large, 0);
    service.close_and_join();
}
fn wait_for(condition: impl Fn() -> bool) {
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    while !condition() {
        assert!(std::time::Instant::now() < deadline, "never observed");
        std::thread::yield_now();
    }
}

#[test]
fn writes_a_single_request_body_before_its_callback_returns() {
    let platform = Arc::new(FakePlatform::default());
    let service = service(platform.clone());
    let body = b"one request";
    let (_slot, output) = prepare(&service, body.len() as u64);
    let mut lent = *body;
    output.write_now(&lent, 0).unwrap();
    lent.fill(0);
    assert_eq!(output.prepared.output.pending_jobs(), 0);
    assert_eq!(output.prepared.output.pending_jobs_hwm(), 0);
    let late = output.clone();
    assert_eq!(
        output.finish(true).unwrap().written_bytes,
        body.len() as u64
    );
    assert_eq!(&lock(&platform.disk)[..body.len()], body);
    assert_eq!(late.write_now(&lent, 0), Err(WriteError::Closed));
    service.close_and_join();
}

#[test]
fn a_failed_single_request_write_refuses_the_objects_next_body() {
    let platform = Arc::new(FakePlatform::default());
    lock(&platform.faults).push_back(Fault::Failed);
    let service = service(platform);
    let (_slot, output) = prepare(&service, 8);
    output.write_now(&[], 0).unwrap();
    let failed = output.write_now(&[1; 4], 0).unwrap_err();
    assert_eq!(output.write_now(&[2; 4], 4), Err(failed.clone()));
    assert_eq!(output.finish(true), Err(failed));
    service.close_and_join();
}

#[test]
fn the_writer_count_is_resolved_once_per_command() {
    for (workers, shards, cpus, expected) in [
        (None, 1, 2, 2),
        (None, 1, 64, WORKER_COUNT_MAX),
        (None, 16, 64, 16),
        (None, 0, 1, 1),
        (Some(7), 1, 2, 7),
        (Some(0), 1, 2, 1),
        (Some(1), 16, 2, 16),
        (Some(12), 2, 64, 12),
    ] {
        assert_eq!(
            shared_worker_count_with_cpus(workers, shards, cpus),
            expected,
            "{workers:?} {shards} {cpus}"
        );
    }
}

#[cfg(target_os = "linux")]
#[test]
#[cfg_attr(miri, ignore = "the affinity syscalls are covered natively")]
fn the_automatic_writer_count_counts_the_threads_affinity_mask() {
    let mask = affinity_mask();
    // SAFETY: the mask was initialized by sched_getaffinity.
    let cpus = usize::try_from(unsafe { libc::CPU_COUNT(&mask) }).unwrap();
    assert!(cpus > 0);
    assert_eq!(numa::cpu_count(), cpus);
    assert_eq!(shared_worker_count(None, 1), WORKER_COUNT_MAX.min(cpus));
    let first = (0..libc::CPU_SETSIZE as usize)
        // SAFETY: cpu is below CPU_SETSIZE and the mask is initialized.
        .find(|&cpu| unsafe { libc::CPU_ISSET(cpu, &mask) })
        .unwrap();
    let narrowed = std::thread::spawn(move || {
        // SAFETY: zero initialization is valid for cpu_set_t's integer storage.
        let mut one: libc::cpu_set_t = unsafe { std::mem::zeroed() };
        // SAFETY: first is below CPU_SETSIZE and one is initialized.
        unsafe { libc::CPU_SET(first, &mut one) };
        // SAFETY: one is initialized; pid zero narrows only this thread.
        let set = unsafe { libc::sched_setaffinity(0, std::mem::size_of_val(&one), &one) };
        assert_eq!(set, 0);
        (numa::cpu_count(), shared_worker_count(None, 1))
    });
    assert_eq!(narrowed.join().unwrap(), (1, 1));
}
#[test]
fn a_discarded_output_writes_its_accepted_bodies_without_concluding() {
    let platform = Arc::new(FakePlatform::default());
    let service = writer_service(WriterMode::Mmap, Arc::clone(&platform));
    let (_slot, output) = prepare(&service, 4096);
    assert_eq!(output.mode(), WriterMode::Mmap);
    output.enqueue(Body::owned(0, vec![7; 4096])).unwrap();
    output.discard();
    let written = &output.prepared.output;
    assert!(output.is_closed());
    assert_eq!((written.error(), written.pending_jobs()), (None, 0));
    assert_eq!(written.observed_stats().written_bytes, 4096);
    assert!(!lock(&platform.advice).contains(&Advice::Evict));
    assert_eq!(output.close_file(), Ok(()));
    assert!(a_conclusion_evicts_the_page(&service, &platform));
    assert_eq!(platform.closes.load(Ordering::SeqCst), 2);
    service.close_and_join();
}
fn a_conclusion_evicts_the_page(service: &SharedWriterService, platform: &FakePlatform) -> bool {
    let (_slot, concluded) = prepare(service, 4096);
    concluded.enqueue(Body::owned(0, vec![7; 4096])).unwrap();
    concluded.finish(false).unwrap();
    concluded.close_file().unwrap();
    lock(&platform.advice).contains(&Advice::Evict)
}
#[derive(Debug, Default)]
struct PlacementSpawner {
    placed: Placements,
    spawned: AtomicUsize,
}
type Placements = Arc<Mutex<Vec<(usize, Option<u32>)>>>;
impl WorkerSpawner for PlacementSpawner {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> std::io::Result<JoinHandle<()>> {
        let index = self.spawned.fetch_add(1, Ordering::SeqCst);
        let placed = Arc::clone(&self.placed);
        ThreadSpawner.spawn(
            name,
            Box::new(move || {
                worker();
                lock(&placed).push((index, fakes::placed_node()));
            }),
        )
    }
}
#[test]
fn a_crt_service_starts_no_writer_and_reports_the_resolved_count() {
    let spawner = Arc::new(PlacementSpawner::default());
    let service = SharedWriterService::start_with(
        SharedConfig {
            writer: WriterConfig {
                workers: None,
                prefault: PrefaultMode::Enabled,
                ..fakes::config(WriterMode::Crt)
            },
            custom_writer_required: true,
            in_flight_max: 8,
            ..SharedConfig::default()
        },
        Arc::new(FakePlatform::default()),
        Arc::clone(&spawner) as Arc<dyn WorkerSpawner>,
    )
    .unwrap();
    assert_eq!(spawner.spawned.load(Ordering::SeqCst), 0);
    assert_eq!(service.worker_count(), 0);
    assert!(service.prefault_pool.is_none());
    for size in [0, CUSTOM_WRITER_SIZE_MIN, u64::MAX] {
        assert!(!service.should_use_custom_writer(size), "{size}");
    }
    service.close_and_join();
    assert_eq!(
        service.summary(),
        diagnostics::SharedServiceSummary {
            worker_count: shared_worker_count(None, 1),
            shard_count: 1,
            queue_capacity: SharedConfig::default().queue_jobs_per_shard,
            active_outputs_max: 8,
            ..diagnostics::SharedServiceSummary::default()
        }
    );
    assert_eq!(spawner.spawned.load(Ordering::SeqCst), 0);
}

#[test]
fn writers_take_their_shards_round_robin() {
    let spawner = Arc::new(PlacementSpawner::default());
    let service = SharedWriterService::start_resolved(
        SharedConfig {
            writer: WriterConfig {
                workers: Some(4),
                ..fakes::config(WriterMode::Pwrite)
            },
            custom_writer_required: true,
            in_flight_max: 4,
            ..SharedConfig::default()
        },
        Arc::new(FakePlatform::default()),
        Arc::clone(&spawner) as Arc<dyn WorkerSpawner>,
        LocalityContext {
            nodes: (0..3)
                .map(|id| numa::NodeInfo::new(id, numa::CpuSet::default(), ""))
                .collect(),
        },
    )
    .unwrap();
    assert_eq!(service.summary().shard_count, 3);
    assert_eq!(service.worker_count(), 4);
    let (slot, output) = prepare(&service, 11);
    assert_eq!(service.active_outputs(), 1);
    output.discard();
    output.close_file().unwrap();
    assert_eq!(service.active_outputs(), 1);
    drop(slot);
    service.close_and_join();
    let mut placed = lock(&spawner.placed).clone();
    placed.sort_unstable();
    let nodes: Vec<_> = placed.into_iter().map(|(_, node)| node).collect();
    assert_eq!(nodes, [Some(0), Some(1), Some(2), Some(0)]);
}
#[cfg(target_os = "linux")]
fn affinity_mask() -> libc::cpu_set_t {
    // SAFETY: zero initialization is valid for cpu_set_t's integer storage.
    let mut mask: libc::cpu_set_t = unsafe { std::mem::zeroed() };
    // SAFETY: mask is writable storage of the advertised size.
    let read = unsafe { libc::sched_getaffinity(0, std::mem::size_of_val(&mask), &mut mask) };
    assert_eq!(read, 0);
    mask
}

#[test]
fn an_object_takes_a_native_writer_by_the_requirement_or_its_size() {
    for (mode, required, size, custom) in [
        (WriterMode::Pwrite, false, CUSTOM_WRITER_SIZE_MIN - 1, false),
        (WriterMode::Pwrite, false, CUSTOM_WRITER_SIZE_MIN, true),
        (WriterMode::Crt, true, CUSTOM_WRITER_SIZE_MIN - 1, false),
        (WriterMode::Crt, true, CUSTOM_WRITER_SIZE_MIN, false),
        (WriterMode::Pwrite, true, CUSTOM_WRITER_SIZE_MIN - 1, true),
        (WriterMode::Pwrite, true, CUSTOM_WRITER_SIZE_MIN, true),
        (WriterMode::Mmap, true, 0, true),
    ] {
        let config = SharedConfig {
            writer: fakes::config(mode),
            custom_writer_required: required,
            ..SharedConfig::default()
        };
        assert_eq!(
            config.should_use_custom_writer(size),
            custom,
            "{mode:?} {required} {size}"
        );
    }
}

fn mapped_service(in_flight_max: usize, spawner: Arc<dyn WorkerSpawner>) -> SharedWriterService {
    SharedWriterService::start_with(
        SharedConfig {
            writer: WriterConfig {
                workers: Some(1),
                prefault: PrefaultMode::Enabled,
                ..fakes::config(WriterMode::Mmap)
            },
            custom_writer_required: true,
            in_flight_max,
            ..SharedConfig::default()
        },
        Arc::new(FakePlatform::default()),
        spawner,
    )
    .unwrap()
}

#[test]
fn small_mapped_files_reuse_command_prefault_workers_through_teardown() {
    let service = mapped_service(2, Arc::new(ThreadSpawner));
    let pool = service.prefault_pool.as_ref().unwrap();
    assert_eq!(pool.worker_count(), PREFAULT_THREADS_PER_SHARD);
    assert!(matches!(
        service.prefault_source(CUSTOM_WRITER_SIZE_MIN),
        PrefaultSource::Private
    ));
    let body = b"pooled output";
    for _ in 0..2 {
        let (slot, output) = prepare(&service, body.len() as u64);
        assert_eq!(output.prepared.output.prefault(), Some(Some(true)));
        output.enqueue(Body::owned(0, body.to_vec())).unwrap();
        assert_eq!(
            output.finish(true).unwrap().written_bytes,
            body.len() as u64
        );
        drop(slot);
        assert_eq!(pool.pool().scheduled(), (0, 0));
        assert_eq!(pool.worker_count(), PREFAULT_THREADS_PER_SHARD);
        assert_eq!(lock(&service.shared.slots).active, 0);
    }
    service.close_and_join();
}

#[derive(Debug)]
struct WritersOnly(usize, AtomicUsize);
impl WorkerSpawner for WritersOnly {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> std::io::Result<JoinHandle<()>> {
        if self.1.fetch_add(1, Ordering::SeqCst) >= self.0 {
            return Err(std::io::ErrorKind::WouldBlock.into());
        }
        ThreadSpawner.spawn(name, worker)
    }
}

#[test]
fn failed_pool_start_disables_only_small_file_prefaulting() {
    let service = mapped_service(2, Arc::new(WritersOnly(1, AtomicUsize::new(0))));
    assert_eq!(service.worker_count(), 1);
    assert!(service.prefault_pool.is_none());
    assert!(matches!(
        service.prefault_source(CUSTOM_WRITER_SIZE_MIN - 1),
        PrefaultSource::Disabled
    ));
    assert!(matches!(
        service.prefault_source(CUSTOM_WRITER_SIZE_MIN),
        PrefaultSource::Private
    ));
    let (_slot, output) = prepare(&service, 1);
    assert_eq!(output.prepared.output.prefault(), Some(None));
    output.finish(true).unwrap_err();
    service.close_and_join();
}

#[test]
fn a_refused_private_prefault_spawn_costs_only_the_prefaulter() {
    for (started, prefaulter) in [(1, None), (2, Some(false))] {
        let spawner = Arc::new(WritersOnly(started, AtomicUsize::new(0)));
        let service = mapped_service(1, Arc::clone(&spawner) as Arc<dyn WorkerSpawner>);
        let (slot, output) = prepare(&service, 4);
        assert_eq!(spawner.1.load(Ordering::SeqCst), started + 1, "{started}");
        assert_eq!(output.mode(), WriterMode::Mmap, "{started}");
        let prefault = output.prepared.output.prefault();
        assert_eq!(prefault, Some(prefaulter), "{started}");
        output.enqueue(Body::owned(0, b"data".to_vec())).unwrap();
        assert_eq!(output.finish(true).unwrap().written_bytes, 4);
        output.close_file().unwrap();
        drop(slot);
        service.close_and_join();
    }
}
#[test]
#[cfg(feature = "download-writer-debug")]
fn a_refused_private_prefault_spawn_logs_as_mains_writer_does() {
    for (started, refused) in [
        (
            1,
            "debug(download_mmap_writer): mmap prefault unavailable \
             err=Insufficient system resources",
        ),
        (
            2,
            "debug(download_mmap_prefaulter): mmap prefault thread spawn failed index=1 \
             err=Insufficient system resources",
        ),
    ] {
        let service = mapped_service(1, Arc::new(WritersOnly(started, AtomicUsize::new(0))));
        let mut prepared = None;
        let lines = diagnostics::capture(|| prepared = Some(prepare(&service, 4)));
        assert_eq!(lines[0], refused);
        let enabled = "debug(download_mmap_writer): mmap writer enabled size=4 ";
        let threads = format!(" prefault_threads={} ", started - 1);
        assert!(
            lines[1].starts_with(enabled) && lines[1].contains(&threads),
            "{}",
            lines[1]
        );
        assert_eq!(lines.len(), 2);
        let (slot, output) = prepared.unwrap();
        output.discard();
        output.close_file().unwrap();
        drop(slot);
        service.close_and_join();
    }
}

#[test]
fn the_prefault_pool_starts_only_for_a_window_of_forced_mapped_outputs() {
    let writer = |mode, requirement, prefault| WriterConfig {
        requirement,
        prefault,
        ..fakes::config(mode)
    };
    use {PrefaultMode::*, Requirement::*, WriterMode::*};
    for (writer, required, window, pooled) in [
        (writer(Mmap, Required, Enabled), true, 2, true),
        (writer(Mmap, Preferred, Enabled), true, 2, true),
        (writer(Direct, Preferred, Enabled), true, 2, true),
        (writer(Mmap, Required, Enabled), true, 1, false),
        (writer(Mmap, Required, Enabled), false, 2, false),
        (writer(Direct, Required, Enabled), true, 2, false),
        (writer(Pwrite, Required, Enabled), true, 2, false),
        (writer(Mmap, Required, Disabled), true, 2, false),
    ] {
        let label = format!("{writer:?} {required} {window}");
        let service = SharedWriterService::start_with(
            SharedConfig {
                writer,
                custom_writer_required: required,
                in_flight_max: window,
                ..SharedConfig::default()
            },
            Arc::new(FakePlatform::default()),
            Arc::new(ThreadSpawner),
        )
        .unwrap();
        assert_eq!(service.prefault_pool.is_some(), pooled, "{label}");
        let small = service.prefault_source(1);
        assert_eq!(
            matches!(small, PrefaultSource::Pooled(_)),
            pooled,
            "{label}"
        );
        service.close_and_join();
    }
}

#[test]
fn close_failure_still_consumes_the_mapping_and_file_once() {
    let platform = Arc::new(FakePlatform::default());
    *lock(&platform.close_failure) = Some(CloseError::InputOutput);
    let service = SharedWriterService::start_with(
        SharedConfig {
            writer: fakes::config(WriterMode::Mmap),
            custom_writer_required: true,
            in_flight_max: 1,
            ..SharedConfig::default()
        },
        Arc::clone(&platform) as Arc<dyn Platform>,
        Arc::new(ThreadSpawner),
    )
    .unwrap();
    let (_slot, output) = prepare(&service, 4);
    assert_eq!(output.mode(), WriterMode::Mmap);
    output.enqueue(Body::owned(0, b"data".to_vec())).unwrap();
    let request = output.clone();
    assert_eq!(output.finish(true).unwrap().written_bytes, 4);
    assert_eq!(platform.closes.load(Ordering::SeqCst), 0);
    assert_eq!(output.close_file(), Err(CloseError::InputOutput));
    assert_eq!(platform.closes.load(Ordering::SeqCst), 1);
    assert_eq!(platform.closes_while_mapped.load(Ordering::SeqCst), 0);
    assert_eq!(
        request.enqueue(Body::owned(0, b"late".to_vec())),
        Err(WriteError::Closed)
    );
    assert_eq!(request.close_file(), Ok(()));
    assert_eq!(platform.closes.load(Ordering::SeqCst), 1);
    service.close_and_join();
}
#[test]
fn preparation_failure_closes_the_file_once_despite_a_close_error() {
    let platform = Arc::new(FakePlatform::default());
    *lock(&platform.close_failure) = Some(CloseError::InputOutput);
    let service = service(Arc::clone(&platform));
    let slot = service.acquire_output_slot(u64::MAX).unwrap();
    assert_eq!(
        service.prepare(&slot, fakes::file(), u64::MAX).unwrap_err(),
        WriteError::FileTooBig
    );
    assert_eq!(platform.closes.load(Ordering::SeqCst), 1);
    assert_eq!(lock(&service.shared.slots).active, 1);
    drop(slot);
    assert_eq!(lock(&service.shared.slots).active, 0);
    service.close_and_join();
}

#[test]
fn creating_a_temp_file_over_a_directory_reports_is_dir() {
    use std::io::{Error, ErrorKind};
    let mapped = super::directory_create_error(ErrorKind::PermissionDenied.into(), || true);
    assert_eq!(mapped.kind(), ErrorKind::IsADirectory);
    let denied = super::directory_create_error(ErrorKind::PermissionDenied.into(), || false);
    assert_eq!(denied.kind(), ErrorKind::PermissionDenied);
    let other = super::directory_create_error(Error::from(ErrorKind::NotFound), || true);
    assert_eq!(other.kind(), ErrorKind::NotFound);
    let directory = Path::new(env!("CARGO_MANIFEST_DIR"));
    let error = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(true)
        .open(directory)
        .map_err(|error| super::create_error(error, directory))
        .unwrap_err();
    assert_eq!(error.kind(), ErrorKind::IsADirectory);
}

#[cfg(unix)]
#[test]
fn only_a_direct_output_sets_its_length_at_conclusion() {
    for mode in [WriterMode::Pwrite, WriterMode::Mmap, WriterMode::Direct] {
        let platform = Arc::new(FakePlatform::default());
        let service = writer_service(mode, Arc::clone(&platform));
        let (_slot, output) = prepare(&service, 4);
        assert_eq!(output.prepared.output.mode(), mode);
        output.enqueue(Body::owned(0, vec![7; 4])).unwrap();
        let prepared = platform.set_lengths.load(Ordering::SeqCst);
        assert!(prepared > 0, "{mode:?} preparation sizes the file");
        *lock(&platform.set_length_failure) = Some(libc::EIO);
        let concluded = output.finish(true);
        let set_lengths = platform.set_lengths.load(Ordering::SeqCst) - prepared;
        if mode == WriterMode::Direct {
            assert_eq!(set_lengths, 1);
            let error = concluded.unwrap_err();
            assert_eq!(crate::cp::write_error_name(&error), "Input/output error");
        } else {
            assert_eq!(set_lengths, 0, "{mode:?}");
            assert_eq!(concluded.unwrap().written_bytes, 4, "{mode:?}");
        }
        service.close_and_join();
    }
}
#[test]
fn a_direct_output_concludes_at_its_exact_length() {
    let platform = Arc::new(FakePlatform::default());
    let service = writer_service(WriterMode::Direct, Arc::clone(&platform));
    let (_slot, output) = prepare(&service, 4);
    output.enqueue(Body::owned(0, vec![7; 4])).unwrap();
    assert_eq!(output.finish(true).unwrap().written_bytes, 4);
    assert_eq!(*lock(&platform.disk), vec![7; 4]);
    service.close_and_join();
}
#[cfg(unix)]
#[test]
fn a_temp_file_that_cannot_be_created_is_named_by_its_errno() {
    let platform = Arc::new(FakePlatform::default());
    let service = service(platform);
    let slot = service.acquire_output_slot(4).unwrap();
    let directory = std::env::temp_dir();
    for (path, name) in [
        (directory.join("a".repeat(300)), "File name too long"),
        (directory.clone(), "Is a directory"),
        (
            directory
                .join(format!("missing-parent-{}", std::process::id()))
                .join("out.bin"),
            "No such file or directory",
        ),
    ] {
        let error = service.prepare_path(&slot, &path, 4).unwrap_err();
        assert_eq!(crate::cp::write_error_name(&error), name, "{path:?}");
    }
    drop(slot);
    service.close_and_join();
}
fn requirement_service(
    mode: WriterMode,
    requirement: Requirement,
    platform: Arc<FakePlatform>,
) -> SharedWriterService {
    SharedWriterService::start_with(
        SharedConfig {
            writer: WriterConfig {
                requirement,
                ..fakes::config(mode)
            },
            custom_writer_required: true,
            in_flight_max: 8,
            ..SharedConfig::default()
        },
        platform,
        Arc::new(ThreadSpawner),
    )
    .unwrap()
}
#[test]
fn unsupported_direct_fails_before_preallocation_or_sizing() {
    let platform = Arc::new(FakePlatform::default());
    platform.direct_unavailable.store(true, Ordering::Relaxed);
    let service = writer_service(WriterMode::Direct, Arc::clone(&platform));
    let slot = service.acquire_output_slot(4).unwrap();
    let error = service.prepare(&slot, fakes::file(), 4).unwrap_err();
    assert_eq!(error, WriteError::DirectUnsupportedOperatingSystem);
    assert_eq!(
        crate::cp::write_error_name(&error),
        "DownloadDirectUnsupportedOperatingSystem"
    );
    assert_eq!(platform.preallocations.load(Ordering::Relaxed), 0);
    assert_eq!(platform.set_lengths.load(Ordering::Relaxed), 0);
    assert_eq!(platform.closes.load(Ordering::Relaxed), 1);
    drop(slot);
    service.close_and_join();
}
#[test]
fn required_mmap_fails_when_unavailable_and_preferred_mmap_falls_back() {
    let refusals: [fn(&FakePlatform); 2] = [
        |platform| platform.map_unavailable.store(true, Ordering::Relaxed),
        |platform| {
            platform
                .unsupported_preallocation
                .store(true, Ordering::Relaxed);
        },
    ];
    for (index, refuse) in refusals.into_iter().enumerate() {
        let platform = Arc::new(FakePlatform::default());
        refuse(&platform);
        let required = writer_service(WriterMode::Mmap, Arc::clone(&platform));
        let slot = required.acquire_output_slot(11).unwrap();
        let error = required.prepare(&slot, fakes::file(), 11).unwrap_err();
        assert_eq!(error, WriteError::MmapUnavailable, "{index}");
        assert_eq!(
            crate::cp::write_error_name(&error),
            "DownloadMmapWriterUnavailable"
        );
        drop(slot);
        required.close_and_join();
        let preferred = requirement_service(
            WriterMode::Mmap,
            Requirement::Preferred,
            Arc::clone(&platform),
        );
        let (_slot, output) = prepare(&preferred, 11);
        assert_eq!(output.prepared.output.mode(), WriterMode::Pwrite, "{index}");
        output
            .enqueue(Body::owned(0, b"hello world".to_vec()))
            .unwrap();
        assert_eq!(output.finish(true).unwrap().written_bytes, 11);
        assert_eq!(*lock(&platform.disk), b"hello world");
        assert!(lock(&platform.mapping).is_none(), "{index}");
        preferred.close_and_join();
    }
}
#[test]
fn producer_guard_accepts_one_thread() {
    let mut guard = ProducerGuard::default();
    guard.check().unwrap();
    guard.check().unwrap();
    let other = std::thread::spawn(move || guard.check()).join().unwrap();
    assert_eq!(other, Err(WriteError::MultipleProducers));
}
