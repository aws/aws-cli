use super::*;
use crate::InterruptHook;
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};
use std::time::{Duration, Instant};
#[derive(Debug, Default)]
struct Counter(AtomicUsize);
impl InterruptHook for Counter {
    fn cancel(&self) {
        self.0.fetch_add(1, Ordering::AcqRel);
    }
}
impl Counter {
    fn count(&self) -> usize {
        self.0.load(Ordering::Acquire)
    }
}
#[test]
fn registered_hooks_cancel_on_request() {
    let state = State::new();
    let first = Arc::new(Counter::default());
    let second = Arc::new(Counter::default());
    let mut first_registration = state.register(first.clone());
    let mut second_registration = state.register(second.clone());
    assert!(!state.is_requested());
    state.request();
    assert!(state.is_requested());
    assert_eq!(first.count(), 1);
    assert_eq!(second.count(), 1);
    first_registration.unregister();
    second_registration.unregister();
}
#[test]
fn unregistered_hooks_do_not_cancel() {
    let state = State::new();
    let gone = Arc::new(Counter::default());
    let kept = Arc::new(Counter::default());
    let mut gone_registration = state.register(gone.clone());
    let _kept_registration = state.register(kept.clone());
    gone_registration.unregister();
    state.request();
    assert_eq!(gone.count(), 0);
    assert_eq!(kept.count(), 1);
}
#[test]
fn each_registration_cancels_at_most_once() {
    let state = State::new();
    let early = Arc::new(Counter::default());
    let late = Arc::new(Counter::default());
    let _early_registration = state.register(early.clone());
    let _scope = Scope::enter(&state);
    assert_eq!(state.record_interrupt(), Signal::Canceled);
    let mut late_registration = state.register(late.clone());
    assert_eq!(early.count(), 0);
    assert_eq!(late.count(), 1);
    state.request();
    state.request();
    assert_eq!(early.count(), 1);
    assert_eq!(late.count(), 1);
    late_registration.unregister();
    let _new_registration = state.register(late.clone());
    assert_eq!(late.count(), 2);
}
#[test]
fn late_hooks_cancel_during_registration() {
    let state = State::new();
    state.request();
    let late = Arc::new(Counter::default());
    let _registration = state.register(late.clone());
    assert_eq!(late.count(), 1);
}
#[test]
fn interrupts_record_only_inside_scope_and_only_once() {
    let state = State::new();
    assert_eq!(state.record_interrupt(), Signal::Terminate);
    assert!(!state.is_requested());
    let mut scope = Scope::enter(&state);
    assert_eq!(state.record_interrupt(), Signal::Canceled);
    assert!(state.is_requested());
    assert_eq!(state.record_interrupt(), Signal::Terminate);
    assert!(scope.leave());
    assert!(scope.leave());
    assert_eq!(state.active_count(), 0);
    assert_eq!(state.record_interrupt(), Signal::Terminate);
}
#[test]
fn uninterrupted_scope_reports_none() {
    let state = State::new();
    let mut scope = Scope::enter(&state);
    assert_eq!(state.active_count(), 1);
    assert!(!scope.leave());
    assert_eq!(state.active_count(), 0);
}
#[test]
fn nested_scopes_remain_active_until_last_leave() {
    let state = State::new();
    let mut outer = Scope::enter(&state);
    let mut inner = Scope::enter(&state);
    assert!(!inner.leave());
    assert_eq!(state.record_interrupt(), Signal::Canceled);
    assert!(outer.leave());
}
#[test]
fn a_sleep_no_interrupt_cuts_short_runs_its_whole_duration() {
    let state = State::new();
    let start = Instant::now();
    assert_eq!(state.sleep(Duration::from_millis(20)), Ok(()));
    assert!(start.elapsed() >= Duration::from_millis(20));
    assert_eq!(state.hook_count(), 0);
}
#[test]
fn a_sleep_begun_after_the_interrupt_returns_at_once() {
    let state = State::new();
    state.request();
    assert_eq!(state.sleep(Duration::from_secs(10)), Err(Canceled));
    assert_eq!(state.hook_count(), 0);
}
#[test]
fn an_interrupt_during_a_sleep_cuts_it_short() {
    let state = State::new();
    std::thread::scope(|scope| {
        let interrupter = scope.spawn(|| interrupt_once_registered(&state));
        assert_eq!(state.sleep(Duration::from_secs(10)), Err(Canceled));
        interrupter
            .join()
            .unwrap_or_else(|panic| std::panic::resume_unwind(panic));
    });
    assert_eq!(state.hook_count(), 0);
}
fn interrupt_once_registered(state: &State) {
    for _ in 0..1000 {
        if state.hook_count() > 0 {
            break;
        }
        std::thread::sleep(Duration::from_millis(1));
    }
    state.request();
}
