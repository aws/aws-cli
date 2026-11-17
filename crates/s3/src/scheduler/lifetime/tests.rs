use super::*;

#[derive(Debug)]
struct Probe {
    lifetimes: Arc<Lifetimes>,
    live_at_drop: Arc<Mutex<Option<usize>>>,
}
impl Drop for Probe {
    fn drop(&mut self) {
        *lock(&self.live_at_drop) = Some(*lock(&self.lifetimes.count));
    }
}

#[test]
fn held_value_drops_before_drain_is_released() {
    let lifetimes = Arc::new(Lifetimes::default());
    let live_at_drop = Arc::new(Mutex::new(None));
    let held = lifetimes.hold(Probe {
        lifetimes: Arc::clone(&lifetimes),
        live_at_drop: Arc::clone(&live_at_drop),
    });
    drop(held);
    assert_eq!(*lock(&live_at_drop), Some(1));
    assert_eq!(*lock(&lifetimes.count), 0);
    lifetimes.drain();
}
