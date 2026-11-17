#![expect(
    clippy::unwrap_used,
    reason = "test barriers and injected success paths must complete"
)]
use super::*;

#[test]
fn shared_copied_callback_body_survives_source_reuse_until_completion() {
    let platform = Arc::new(FakePlatform::default());
    let service = service(Arc::clone(&platform));
    let (_slot, output) = prepare(&service, 4);
    let mut lent = [1, 2, 3, 4];
    output.enqueue(Body::owned(0, lent.to_vec())).unwrap();
    lent.fill(0);
    assert_eq!(lent, [0; 4]);
    assert_eq!(output.finish(true).unwrap().written_bytes, 4);
    assert_eq!(*lock(&platform.disk), [1, 2, 3, 4]);
    service.close_and_join();
}

#[derive(Debug)]
struct FailingSpawner {
    fail_index: usize,
    attempts: AtomicUsize,
    joined: Arc<AtomicUsize>,
}
impl WorkerSpawner for FailingSpawner {
    fn spawn(
        &self,
        name: String,
        worker: Box<dyn FnOnce() + Send>,
    ) -> std::io::Result<JoinHandle<()>> {
        if self.attempts.fetch_add(1, Ordering::SeqCst) == self.fail_index {
            return Err(std::io::ErrorKind::ResourceBusy.into());
        }
        let joined = Arc::clone(&self.joined);
        ThreadSpawner.spawn(
            name,
            Box::new(move || {
                worker();
                joined.fetch_add(1, Ordering::SeqCst);
            }),
        )
    }
}

#[test]
fn shared_worker_spawn_failure_closes_queues_and_joins_partial_startup() {
    for fail_index in [0, 1] {
        let joined = Arc::new(AtomicUsize::new(0));
        let spawner = Arc::new(FailingSpawner {
            fail_index,
            attempts: AtomicUsize::new(0),
            joined: Arc::clone(&joined),
        });
        let result = SharedWriterService::start_with(
            SharedConfig {
                writer: fakes::config(WriterMode::Pwrite),
                ..SharedConfig::default()
            },
            Arc::new(FakePlatform::default()),
            Arc::clone(&spawner) as Arc<dyn WorkerSpawner>,
        );
        assert!(
            matches!(
                result,
                Err(WriteError::Io {
                    kind: std::io::ErrorKind::ResourceBusy,
                    ..
                })
            ),
            "{fail_index}"
        );
        assert_eq!(spawner.attempts.load(Ordering::SeqCst), fail_index + 1);
        assert_eq!(joined.load(Ordering::SeqCst), fail_index);
    }
}

#[test]
fn a_failed_preparation_leaves_the_output_slot_to_its_holder() {
    let platform = Arc::new(FakePlatform::default());
    lock(&platform.preallocation).push_back(std::io::ErrorKind::StorageFull);
    let service = service(platform);
    let slot = service.acquire_output_slot(4).unwrap();
    assert!(service.prepare(&slot, fakes::file(), 4).is_err());
    assert_eq!(lock(&service.shared.slots).active, 1);
    let output = service.prepare(&slot, fakes::file(), 4).unwrap();
    output.write_now(&[1; 4], 0).unwrap();
    output.finish(true).unwrap();
    assert_eq!(lock(&service.shared.slots).active, 1);
    drop(slot);
    assert_eq!(lock(&service.shared.slots).active, 0);
}
