use crate::{
    InterruptHook,
    interrupt::{Scope, Signal, State},
};
use std::sync::{
    Arc, Barrier,
    atomic::{AtomicUsize, Ordering},
};

#[derive(Debug, Default)]
struct Counter(AtomicUsize);
impl InterruptHook for Counter {
    fn cancel(&self) {
        self.0.fetch_add(1, Ordering::Relaxed);
    }
}

#[test]
#[cfg_attr(
    miri,
    ignore = "native concurrency stress; pure transition tests run under Miri"
)]
fn concurrent_registration_cancels_each_hook_exactly_once() {
    let state = Arc::new(State::new());
    state.request();
    std::thread::scope(|scope| {
        for _ in 0..8 {
            let state = Arc::clone(&state);
            scope.spawn(move || {
                for _ in 0..20000 {
                    let hook = Arc::new(Counter::default());
                    let registration = state.register(hook.clone());
                    state.request();
                    drop(registration);
                    assert_eq!(hook.0.load(Ordering::Relaxed), 1);
                }
            });
        }
    });
}
#[test]
#[cfg_attr(
    miri,
    ignore = "native concurrency stress; pure transition tests run under Miri"
)]
fn concurrent_scope_word_records_one_interrupt_and_releases_all_scopes() {
    for _ in 0..128 {
        let state = Arc::new(State::new());
        let barrier = Arc::new(Barrier::new(8));
        let canceled = AtomicUsize::new(0);
        std::thread::scope(|threads| {
            for _ in 0..8 {
                let state = Arc::clone(&state);
                let barrier = Arc::clone(&barrier);
                let canceled = &canceled;
                threads.spawn(move || {
                    let _scope = Scope::enter(&state);
                    barrier.wait();
                    if state.record_interrupt() == Signal::Canceled {
                        canceled.fetch_add(1, Ordering::Relaxed);
                    }
                });
            }
        });
        assert_eq!(canceled.load(Ordering::Relaxed), 1);
        assert_eq!(state.active_count(), 0);
    }
}
