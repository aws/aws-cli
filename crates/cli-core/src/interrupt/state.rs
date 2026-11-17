use crate::{InterruptHook, InterruptState};
use std::sync::{
    Arc, Condvar, Mutex, MutexGuard, PoisonError,
    atomic::{AtomicU32, Ordering},
};
use std::time::{Duration, Instant};
const REQUESTED_BIT: u32 = 1 << 31;
const ACTIVE_MASK: u32 = REQUESTED_BIT - 1;
const RECORD_RETRY_COUNT_MAX: usize = 16;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Signal {
    Canceled,
    Terminate,
}
struct Registered {
    id: u64,
    hook: Arc<dyn InterruptHook>,
    canceled: bool,
}
impl std::fmt::Debug for Registered {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.debug_struct("Registered")
            .field("id", &self.id)
            .field("canceled", &self.canceled)
            .finish_non_exhaustive()
    }
}
#[derive(Debug, Default)]
struct Hooks {
    next_id: u64,
    entries: Vec<Registered>,
}
#[derive(Debug, Default)]
pub struct State {
    word: AtomicU32,
    hooks: Mutex<Hooks>,
}
impl State {
    pub const fn new() -> Self {
        Self {
            word: AtomicU32::new(0),
            hooks: Mutex::new(Hooks {
                next_id: 0,
                entries: Vec::new(),
            }),
        }
    }
    pub fn is_requested(&self) -> bool {
        self.word.load(Ordering::Acquire) & REQUESTED_BIT != 0
    }
    /// Records only the first interrupt during active work, using bounded CAS.
    pub fn record_interrupt(&self) -> Signal {
        let mut current = self.word.load(Ordering::Acquire);
        for _ in 0..RECORD_RETRY_COUNT_MAX {
            if current & REQUESTED_BIT != 0 || current & ACTIVE_MASK == 0 {
                return Signal::Terminate;
            }
            match self.word.compare_exchange(
                current,
                current | REQUESTED_BIT,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => return Signal::Canceled,
                Err(value) => current = value,
            }
        }
        Signal::Terminate
    }
    /// Requests cancellation and runs pending hooks under the registration lock.
    pub fn request(&self) {
        let mut hooks = self.lock_hooks();
        self.word.fetch_or(REQUESTED_BIT, Ordering::AcqRel);
        for registered in hooks.entries.iter_mut().rev() {
            cancel(registered);
        }
    }
    /// Registers a hook; dropping its guard waits for concurrent cancellation.
    pub fn register(&self, hook: Arc<dyn InterruptHook>) -> Registration<'_> {
        let mut hooks = self.lock_hooks();
        let id = hooks.next_id;
        hooks.next_id = hooks.next_id.wrapping_add(1);
        let mut registered = Registered {
            id,
            hook,
            canceled: false,
        };
        if self.is_requested() {
            cancel(&mut registered);
        }
        hooks.entries.push(registered);
        Registration {
            state: self,
            id,
            linked: true,
        }
    }
    fn unregister(&self, id: u64) {
        self.lock_hooks().entries.retain(|hook| hook.id != id);
    }
    /// Waits out `duration` unless an interrupt is requested before the wait
    /// ends, which returns [`Canceled`] at once, as does one already
    /// requested: whatever the caller would do next is cancelled work. It is
    /// for a wait inside transfer work, which Ctrl-C must not have to outlast.
    pub fn sleep(&self, duration: Duration) -> Result<(), Canceled> {
        let sleeper = Arc::new(Sleeper::default());
        let mut registration = self.register(sleeper.clone());
        sleeper.wait(Instant::now().checked_add(duration));
        registration.unregister();
        if self.is_requested() {
            Err(Canceled)
        } else {
            Ok(())
        }
    }
    #[cfg(test)]
    pub(crate) fn hook_count(&self) -> usize {
        self.lock_hooks().entries.len()
    }
    fn enter(&self) {
        let previous = self.word.fetch_add(1, Ordering::AcqRel);
        debug_assert_ne!(previous & ACTIVE_MASK, ACTIVE_MASK);
    }
    fn leave(&self) -> bool {
        let previous = self.word.fetch_sub(1, Ordering::AcqRel);
        debug_assert_ne!(previous & ACTIVE_MASK, 0);
        previous & REQUESTED_BIT != 0
    }
    pub fn active_count(&self) -> u32 {
        self.word.load(Ordering::Acquire) & ACTIVE_MASK
    }
    #[expect(
        clippy::expect_used,
        reason = "a panicking hook poisons an invariant and cannot be recovered"
    )]
    fn lock_hooks(&self) -> MutexGuard<'_, Hooks> {
        self.hooks.lock().expect("interrupt hook lock poisoned")
    }
}
impl InterruptState for State {
    fn is_requested(&self) -> bool {
        self.is_requested()
    }
}
fn cancel(registered: &mut Registered) {
    if !registered.canceled {
        registered.canceled = true;
        registered.hook.cancel();
    }
}
/// A [`State::sleep`] an interrupt cut short.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Canceled;
#[derive(Debug, Default)]
struct Sleeper {
    woken: Mutex<bool>,
    changed: Condvar,
}
impl InterruptHook for Sleeper {
    fn cancel(&self) {
        *self.woken.lock().unwrap_or_else(PoisonError::into_inner) = true;
        self.changed.notify_all();
    }
}
impl Sleeper {
    fn wait(&self, deadline: Option<Instant>) {
        let mut woken = self.woken.lock().unwrap_or_else(PoisonError::into_inner);
        while !*woken {
            let Some(deadline) = deadline else {
                woken = self
                    .changed
                    .wait(woken)
                    .unwrap_or_else(PoisonError::into_inner);
                continue;
            };
            let Some(left) = deadline.checked_duration_since(Instant::now()) else {
                break;
            };
            if left.is_zero() {
                break;
            }
            woken = self
                .changed
                .wait_timeout(woken, left)
                .unwrap_or_else(PoisonError::into_inner)
                .0;
        }
    }
}
/// Cancels the registration on drop only after any running callback has finished.
#[derive(Debug)]
pub struct Registration<'a> {
    state: &'a State,
    id: u64,
    linked: bool,
}
impl Registration<'_> {
    pub fn unregister(&mut self) {
        if self.linked {
            self.state.unregister(self.id);
            self.linked = false;
        }
    }
}
impl Drop for Registration<'_> {
    fn drop(&mut self) {
        self.unregister();
    }
}
/// One active transfer interval, reporting interrupts atomically at its boundary.
#[derive(Debug)]
pub struct Scope<'a> {
    state: &'a State,
    active: bool,
    interrupted: bool,
}
impl<'a> Scope<'a> {
    pub fn enter(state: &'a State) -> Self {
        state.enter();
        Self {
            state,
            active: true,
            interrupted: false,
        }
    }
    pub fn leave(&mut self) -> bool {
        if self.active {
            self.active = false;
            self.interrupted = self.state.leave();
        }
        self.interrupted
    }
}
impl Drop for Scope<'_> {
    fn drop(&mut self) {
        self.leave();
    }
}
