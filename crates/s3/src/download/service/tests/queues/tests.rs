#![expect(
    clippy::unwrap_used,
    reason = "test barriers and injected success paths must complete"
)]
use super::*;
use crate::cp::backstop::SetupError;
use std::time::{Duration, Instant};

const POOL_BYTES: u64 = 4 << 30;
const PART_SIZE: u64 = 8 << 20;
const PARTS_PER_POOL: usize = (POOL_BYTES / PART_SIZE) as usize;
const QUEUE_WAIT_MAX: Duration = Duration::from_secs(10);

#[test]
fn every_shard_holds_every_buffer_the_commands_pools_can_lend() {
    const GIB: u64 = 1 << 30;
    const MIB: u64 = 1 << 20;
    for (pool, part, window, jobs) in [
        (4 * GIB, 8 * MIB, 512, 1536),
        (4 * GIB, 8 * MIB, 1, 1025),
        (24 * GIB, 8 * MIB, 512, 6656),
        (8 * MIB + 1, 8 * MIB, 1, 5),
        (1, 8 * MIB, 1, 3),
        (u64::MAX, 1, u32::MAX, usize::MAX),
    ] {
        assert_eq!(
            queue_jobs_per_shard(pool, part, window),
            jobs,
            "{pool} {part} {window}"
        );
    }
    let service = SharedWriterService::start_resolved(
        SharedConfig {
            writer: WriterConfig {
                workers: Some(16),
                ..fakes::config(WriterMode::Pwrite)
            },
            custom_writer_required: true,
            in_flight_max: 512,
            queue_jobs_per_shard: 1536,
        },
        Arc::new(FakePlatform::default()),
        Arc::new(ThreadSpawner),
        sharded(3),
    )
    .unwrap();
    let summary = service.summary();
    assert_eq!(summary.shard_count, 3);
    assert_eq!(summary.queue_capacity, 3 * 1536);
    assert_eq!(service.shared.queues.capacity, 1536);
    for queue in &service.shared.queues.shards {
        assert!(lock(&queue.state).jobs.capacity() >= 1536);
    }
    service.close_and_join();
}

#[test]
fn a_queue_too_large_to_reserve_fails_the_services_start() {
    let error = SharedWriterService::start_with(
        SharedConfig {
            writer: fakes::config(WriterMode::Pwrite),
            queue_jobs_per_shard: queue_jobs_per_shard(u64::MAX, 1, u32::MAX),
            ..SharedConfig::default()
        },
        Arc::new(FakePlatform::default()),
        Arc::new(ThreadSpawner),
    )
    .unwrap_err();
    assert!(
        matches!(
            error,
            WriteError::Io {
                kind: std::io::ErrorKind::OutOfMemory,
                ..
            }
        ),
        "{error:?}"
    );
    assert_eq!(SetupError::write(&error).name(), "Out of memory");
}

#[test]
fn a_shard_at_capacity_takes_every_ticket_two_pools_lend_without_a_wait() {
    let window = 3;
    let capacity = queue_jobs_per_shard(POOL_BYTES, PART_SIZE, window);
    assert_eq!(capacity, 2 * PARTS_PER_POOL + window as usize);
    let service = unstarted(sharded(2), window, capacity);
    let parts = 2 * PARTS_PER_POOL;
    let objects = Objects::prepare(&service, &[parts + 1, 1, 1]);
    deliver(&objects);
    {
        let queues = &service.shared.queues;
        assert_eq!(lock(&queues.shards[0].state).jobs.len(), capacity);
        assert!(queues.shards[1].is_empty());
        assert_eq!(queues.full_waits(), FullWaits::default());
    }
    assert_eq!(run_queued_jobs(&service), capacity);
    for output in &objects.outputs {
        output.clone().finish(true).unwrap();
    }
    assert_eq!(objects.released(), capacity);
}

#[test]
fn one_object_queues_every_buffer_its_pool_lends_alongside_other_objects() {
    let window = 3;
    let service = unstarted(
        LocalityContext::default(),
        window,
        queue_jobs_per_shard(POOL_BYTES, PART_SIZE, window),
    );
    let objects = Objects::prepare(&service, &[PARTS_PER_POOL, 1, 1]);
    deliver(&objects);
    let first = &objects.outputs[0].prepared.output;
    assert_eq!(first.pending_jobs(), PARTS_PER_POOL);
    assert_eq!(first.pending_jobs_hwm(), PARTS_PER_POOL);
    assert_eq!(full_waits(&service), 0);
    assert_eq!(run_queued_jobs(&service), PARTS_PER_POOL + 2);
    for output in &objects.outputs {
        output.clone().finish(true).unwrap();
    }
    assert_eq!(objects.released(), PARTS_PER_POOL + 2);
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum End {
    Close,
    Cancel,
    Fail,
}

#[test]
fn an_object_ending_with_queued_jobs_releases_every_ticket_and_slot() {
    for end in [End::Close, End::Cancel, End::Fail] {
        let window = 2;
        let service = unstarted(
            LocalityContext::default(),
            window,
            queue_jobs_per_shard(POOL_BYTES, PART_SIZE, window),
        );
        let objects = Objects::prepare(&service, &[PARTS_PER_POOL, 1]);
        deliver(&objects);
        let output = objects.outputs[0].clone();
        let full = WriteError::from(std::io::Error::from(std::io::ErrorKind::StorageFull));
        if end == End::Fail {
            output.fail(full.clone());
        }
        let probe = Arc::clone(&output.prepared.output);
        let ending = std::thread::spawn(move || match end {
            End::Close => {
                output.discard();
                None
            }
            End::Cancel => output.finish(false).err(),
            End::Fail => output.finish(true).err(),
        });
        wait_for(|| probe.is_closed() && probe.drain_waiters() == 1);
        assert_eq!(run_queued_jobs(&service), PARTS_PER_POOL + 1);
        let local_error = ending.join().unwrap();
        assert_eq!(local_error, (end == End::Fail).then_some(full), "{end:?}");
        assert_eq!(probe.pending_jobs(), 0);
        assert_eq!(objects.released(), PARTS_PER_POOL + 1);
        assert_eq!(service.active_outputs(), window as usize);
        drop(objects);
        assert_eq!(service.active_outputs(), 0);
    }
}

#[test]
fn a_full_shard_blocks_the_callback_and_counts_the_wait() {
    let service = unstarted(LocalityContext::default(), 1, 1);
    let objects = Objects::prepare(&service, &[2]);
    let (output, released) = (objects.outputs[0].clone(), Arc::clone(&objects.released[0]));
    let producer = std::thread::spawn(move || {
        for (offset, byte) in [b'a', b'b'].into_iter().enumerate() {
            let ticket = DropCounter(Arc::clone(&released));
            output.enqueue(Body::tracked(offset as u64, vec![byte], ticket))?;
        }
        Ok::<(), WriteError>(())
    });
    wait_for(|| full_waits(&service) == 1);
    assert_eq!(objects.outputs[0].prepared.output.pending_jobs(), 2);
    let first = service.shared.queues.shards[0].pop().unwrap();
    service.shared.write_job(first);
    producer.join().unwrap().unwrap();
    assert_eq!(run_queued_jobs(&service), 1);
    objects.outputs[0].clone().finish(true).unwrap();
    let summary = service.summary();
    assert_eq!(summary.shard_full_wait_count, 1);
    assert_eq!(summary.queue_capacity, 1);
    assert_eq!(
        summary.pending_jobs_hwm,
        if diagnostics::ENABLED { 2 } else { 0 }
    );
    assert_eq!((summary.jobs_enqueued, summary.jobs_written), (2, 2));
}

#[test]
fn a_body_for_a_closed_queue_reports_the_closed_writer_service() {
    let service = unstarted(LocalityContext::default(), 1, 4);
    let objects = Objects::prepare(&service, &[1]);
    service.shared.queues.close();
    let output = objects.outputs[0].clone();
    let counter = DropCounter(Arc::clone(&objects.released[0]));
    let refused = output.enqueue(Body::tracked(0, vec![1], counter));
    assert_eq!(refused, Err(WriteError::SharedWriterClosed));
    assert_eq!(
        refused.unwrap_err().to_string(),
        "DownloadSharedWriterClosed"
    );
    assert_eq!(objects.released(), 1);
    assert_eq!(output.prepared.output.pending_jobs(), 0);
    assert_eq!(output.finish(true), Err(WriteError::SharedWriterClosed));
}

#[test]
fn a_full_shard_blocks_only_its_own_pushes() {
    let service = unstarted(sharded(2), 2, 1);
    let objects = Objects::prepare(&service, &[2, 1]);
    let output = objects.outputs[0].clone();
    let producer = std::thread::spawn(move || {
        output.enqueue(on_shard(0, 1))?;
        output.enqueue(on_shard(1, 1))
    });
    wait_for(|| full_waits(&service) == 1);
    objects.outputs[1].enqueue(on_shard(0, 0)).unwrap();
    let queues = &service.shared.queues;
    assert_eq!(lock(&queues.shards[0].state).jobs.len(), 1);
    assert_eq!(
        lock(&queues.shards[0].state).full_waits,
        FullWaits::default()
    );
    assert_eq!(lock(&queues.shards[1].state).full_waits.count, 1);
    service.shared.write_job(queues.shards[1].pop().unwrap());
    producer.join().unwrap().unwrap();
    assert_eq!(run_queued_jobs(&service), 2);
    for output in &objects.outputs {
        output.clone().finish(true).unwrap();
    }
}

#[test]
fn each_queued_job_posts_one_wake_and_is_taken_once() {
    let service = unstarted(sharded(2), 1, 4);
    let objects = Objects::prepare(&service, &[4]);
    let (output, shared) = (&objects.outputs[0], &service.shared);
    let wake = &shared.queues.wake;
    std::thread::scope(|scope| {
        let writer = scope.spawn(|| {
            let job = shared.queues.pop(0).unwrap();
            let offset = job.body.offset;
            shared.write_job(job);
            offset
        });
        wait_for(|| lock(&wake.state).waiters == 1);
        output.enqueue(on_shard(0, 1)).unwrap();
        assert_eq!(writer.join().unwrap(), 0);
    });
    assert_eq!(lock(&wake.state).permits, 0);
    for (offset, node) in [(1, 0), (2, 1), (3, 0)] {
        output.enqueue(on_shard(offset, node)).unwrap();
    }
    assert_eq!(lock(&wake.state).permits, 3);
    let taken: Vec<_> = (0..3)
        .map(|_| {
            let job = shared.queues.pop(1).unwrap();
            let offset = job.body.offset;
            shared.write_job(job);
            offset
        })
        .collect();
    assert_eq!(taken, [2, 1, 3]);
    shared.queues.close();
    assert!(shared.queues.pop(0).is_none());
    assert_eq!(output.clone().finish(true).unwrap().written_bytes, 4);
}

#[test]
fn closing_wakes_every_idle_writer() {
    let service = Arc::new(
        SharedWriterService::start_with(
            SharedConfig {
                writer: WriterConfig {
                    workers: Some(3),
                    ..fakes::config(WriterMode::Pwrite)
                },
                ..SharedConfig::default()
            },
            Arc::new(FakePlatform::default()),
            Arc::new(ThreadSpawner),
        )
        .unwrap(),
    );
    assert_eq!(service.worker_count(), 3);
    wait_for(|| lock(&service.shared.queues.wake.state).waiters == 3);
    let (sender, receiver) = std::sync::mpsc::channel();
    let closer = Arc::clone(&service);
    std::thread::spawn(move || {
        closer.close_and_join();
        sender.send(()).unwrap();
    });
    receiver.recv_timeout(QUEUE_WAIT_MAX).unwrap();
    assert_eq!(service.worker_count(), 0);
    assert_eq!(lock(&service.shared.queues.wake.state).waiters, 0);
}

fn on_shard(offset: u64, node: u32) -> Body {
    let mut body = Body::owned(offset, vec![b'x']);
    body.source_node = Some(node);
    body
}

fn sharded(count: u32) -> LocalityContext {
    LocalityContext {
        nodes: (0..count)
            .map(|id| numa::NodeInfo::new(id, numa::CpuSet::default(), ""))
            .collect(),
    }
}

fn unstarted(locality: LocalityContext, window: u32, capacity: usize) -> SharedWriterService {
    let config = SharedConfig {
        writer: WriterConfig {
            workers: Some(1),
            ..fakes::config(WriterMode::Pwrite)
        },
        custom_writer_required: true,
        in_flight_max: window as usize,
        queue_jobs_per_shard: capacity,
    };
    SharedWriterService {
        shared: Arc::new(Shared {
            max_outputs: config.in_flight_max,
            max_large_outputs: 1,
            queues: Queues::new(locality.shard_count(), capacity).unwrap(),
            config,
            platform: Arc::new(FakePlatform::default()),
            spawner: Arc::new(ThreadSpawner),
            locality,
            slots: Mutex::new(OutputSlots::default()),
            available: Condvar::new(),
            pending_jobs_hwm: AtomicUsize::new(0),
            jobs_enqueued: AtomicU64::new(0),
            jobs_written: AtomicU64::new(0),
        }),
        workers: Mutex::new(Vec::new()),
        prefault_pool: None,
    }
}

struct Objects {
    outputs: Vec<SharedOutput>,
    released: Vec<Arc<AtomicUsize>>,
    slots: Vec<OutputSlot>,
}
impl Objects {
    fn prepare(service: &SharedWriterService, sizes: &[usize]) -> Self {
        let mut objects = Self {
            outputs: Vec::new(),
            released: Vec::new(),
            slots: Vec::new(),
        };
        for &size in sizes {
            let slot = service.acquire_output_slot(size as u64).unwrap();
            objects
                .outputs
                .push(service.prepare(&slot, fakes::file(), size as u64).unwrap());
            objects.released.push(Arc::new(AtomicUsize::new(0)));
            objects.slots.push(slot);
        }
        objects
    }
    fn released(&self) -> usize {
        self.released
            .iter()
            .map(|count| count.load(Ordering::SeqCst))
            .sum()
    }
}

fn deliver(objects: &Objects) {
    let (sender, receiver) = std::sync::mpsc::channel();
    for (output, released) in objects.outputs.iter().zip(&objects.released) {
        let (output, released, sender) = (output.clone(), Arc::clone(released), sender.clone());
        std::thread::spawn(move || {
            let size = output.prepared.output.size;
            for offset in 0..size {
                let ticket = DropCounter(Arc::clone(&released));
                output
                    .enqueue(Body::tracked(offset, vec![b'x'], ticket))
                    .unwrap();
            }
            sender.send(()).unwrap();
        });
    }
    drop(sender);
    let deadline = Instant::now() + QUEUE_WAIT_MAX;
    for _ in &objects.outputs {
        let left = deadline.saturating_duration_since(Instant::now());
        assert!(
            receiver.recv_timeout(left).is_ok(),
            "a body callback waited for the writer queue"
        );
    }
}

fn run_queued_jobs(service: &SharedWriterService) -> usize {
    let mut count = 0;
    loop {
        let job = service
            .shared
            .queues
            .shards
            .iter()
            .find_map(ShardQueue::pop);
        let Some(job) = job else {
            return count;
        };
        service.shared.write_job(job);
        count += 1;
    }
}

fn full_waits(service: &SharedWriterService) -> u64 {
    service.shared.queues.full_waits().count
}

fn wait_for(condition: impl Fn() -> bool) {
    let deadline = Instant::now() + QUEUE_WAIT_MAX;
    while !condition() {
        assert!(Instant::now() < deadline, "never observed");
        std::thread::yield_now();
    }
}
