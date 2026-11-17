use super::*;
use std::time::{Duration, Instant};

#[derive(Debug, Default)]
pub(crate) struct Gate {
    opened: Mutex<bool>,
    changed: Condvar,
}
impl Gate {
    pub(crate) fn open(&self) {
        *lock(&self.opened) = true;
        self.changed.notify_all();
    }
    pub(crate) fn wait(&self) {
        let deadline = Instant::now() + Duration::from_secs(30);
        let mut opened = lock(&self.opened);
        while !*opened {
            let remaining = deadline.saturating_duration_since(Instant::now());
            assert!(
                !remaining.is_zero(),
                "shared writer actor missed a milestone"
            );
            opened = self.changed.wait_timeout(opened, remaining).unwrap().0;
        }
    }
}

pub(super) struct Cleanup(pub(super) Arc<Round>);
impl Drop for Cleanup {
    fn drop(&mut self) {
        for gate in &self.0.allowed {
            gate.open();
        }
        self.0.state().service.close_and_join();
    }
}
