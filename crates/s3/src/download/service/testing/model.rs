use super::*;

struct Outcome {
    written: usize,
    failed: bool,
}

impl Round {
    pub(super) fn run(self: &Arc<Self>) {
        self.emit(0);
        self.writing[0].wait();
        let producer = Arc::clone(self);
        let thread = std::thread::spawn(move || {
            producer.emit(1);
            producer.producer_done.open();
        });
        assert_eq!(self.output(0).prepared.output.pending_jobs(), 1);
        self.allowed[0].open();
        self.released[0].wait();
        self.writing[2].wait();
        self.allowed[2].open();
        self.released[2].wait();
        self.writing[1].wait();
        self.allowed[1].open();
        self.producer_done.wait();
        thread.join().unwrap();
        self.conclude();
        self.state().service.close_and_join();
    }
    fn emit(self: &Arc<Self>, index: usize) {
        let bytes = lock(&self.ledger).entries[index].expected.clone();
        let owner = Arc::downgrade(self);
        let body = Body::observed(
            0,
            bytes,
            Box::new(move || owner.upgrade().unwrap().release(index)),
        );
        self.output(index).enqueue(body).unwrap();
        lock(&self.ledger).entries[index].accepted = true;
    }
    fn release(self: &Arc<Self>, index: usize) {
        assert_eq!(self.output(index).prepared.output.pending_jobs(), 1);
        {
            let mut ledger = lock(&self.ledger);
            let entry = &mut ledger.entries[index];
            assert_eq!(entry.releases, 0);
            assert_eq!(entry.writes, 1);
            entry.releases += 1;
        }
        if index == 0 {
            self.emit(2);
        }
        self.released[index].open();
    }
    fn conclude(&self) {
        for index in 0..3 {
            let output = self.output(index);
            let expected = self.outcome(index);
            let result = output.finish(true);
            if expected.failed {
                assert!(matches!(
                    result,
                    Err(WriteError::Io {
                        kind: std::io::ErrorKind::StorageFull,
                        ..
                    })
                ));
            } else {
                assert_eq!(result.unwrap().written_bytes, expected.written as u64);
            }
        }
    }
    pub(super) fn verify(&self) {
        for index in 0..3 {
            self.verify_output(index);
        }
        assert!(self.state().service.shared.queues.is_empty());
        let outputs = lock(&self.state().outputs).take().unwrap();
        let weak = outputs
            .each_ref()
            .map(|output| Arc::downgrade(&output.prepared.output));
        drop(outputs);
        assert!(weak.iter().all(|output| output.upgrade().is_none()));
        assert_eq!(lock(&self.state().service.shared.slots).active, 3);
        drop(lock(&self.state().slots).take());
        assert_eq!(lock(&self.state().service.shared.slots).active, 0);
    }
    fn verify_output(&self, index: usize) {
        let output = self.output(index);
        let expected = self.outcome(index);
        assert_eq!(output.prepared.output.pending_jobs(), 0);
        let stats = output.prepared.output.observed_stats();
        assert_eq!(stats.written_bytes, expected.written as u64);
        assert_eq!(stats.enqueued_bytes, self.choices.sizes[index] as u64);
        let ledger = lock(&self.ledger);
        let entry = &ledger.entries[index];
        assert!(entry.accepted);
        assert_eq!(entry.releases, 1);
        assert_eq!(entry.writes, 1);
        assert_eq!(
            &entry.image[..expected.written],
            &entry.expected[..expected.written]
        );
        assert!(
            entry.image[expected.written..]
                .iter()
                .all(|byte| *byte == 0)
        );
    }
    fn outcome(&self, index: usize) -> Outcome {
        let failed = index == 0 && self.choices.terminal == Terminal::WriteFailure;
        Outcome {
            written: if failed { 0 } else { self.choices.sizes[index] },
            failed,
        }
    }
}
