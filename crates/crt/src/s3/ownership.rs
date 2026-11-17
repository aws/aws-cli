//! Injected ownership protocols shared by native callbacks and deterministic tests.
use super::{CANCELED_ERROR_CODE, INVALID_ARGUMENT_ERROR_CODE, TransferResult};
use crate::signal::{lock, wait};
use cli_core::interrupt::{Registration, State};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Condvar, Mutex};

/// Operations on the one request reference a submission owns.
pub trait MetaRequestOps {
    type Handle: Copy + Eq + std::fmt::Debug;
    fn cancel(&mut self, handle: Self::Handle);
    fn release(&mut self, handle: Self::Handle);
}
#[derive(Debug)]
struct SubmissionState<O: MetaRequestOps> {
    handle: Option<O::Handle>,
    finished: bool,
    shutdown: bool,
    interrupted: bool,
    result: TransferResult,
}
/// Owns one adopted reference until finish, then waits for final shutdown.
#[derive(Debug)]
pub struct Submission<O: MetaRequestOps> {
    state: Mutex<SubmissionState<O>>,
    ops: Mutex<O>,
    wake: Condvar,
}
impl<O: MetaRequestOps> Submission<O> {
    pub fn new(ops: O) -> Self {
        Self {
            ops: Mutex::new(ops),
            state: Mutex::new(SubmissionState {
                handle: None,
                finished: false,
                shutdown: false,
                interrupted: false,
                result: TransferResult::default(),
            }),
            wake: Condvar::new(),
        }
    }
    pub fn cancel_for_interrupt(&self) {
        let mut s = lock(&self.state);
        if let Some(handle) = s.handle {
            s.interrupted = true;
            lock(&self.ops).cancel(handle);
        }
    }
    pub fn finish(&self, result: TransferResult) {
        let mut s = lock(&self.state);
        s.result = result;
        s.finished = true;
        self.wake.notify_all();
    }
    pub fn shutdown(&self) {
        lock(&self.state).shutdown = true;
        self.wake.notify_all();
    }
    pub fn wait(&self) -> TransferResult {
        self.wait_with_unregister(|| {})
    }
    /// Removes cancellation registration after finish and before releasing.
    pub fn wait_with_unregister(&self, unregister: impl FnOnce()) -> TransferResult {
        let mut s = lock(&self.state);
        while !s.finished {
            s = wait(&self.wake, s);
        }
        let handle = s.handle.take();
        let mut result = s.result.clone();
        result.canceled_by_interrupt = s.interrupted && result.error_code == CANCELED_ERROR_CODE;
        // Release outside the state mutex: a final release may synchronously
        // invoke shutdown. Keep the ops separately locked for that operation.
        drop(s);
        unregister();
        if let Some(handle) = handle {
            self.release_handle(handle);
        }
        let mut s = lock(&self.state);
        while !s.shutdown {
            s = wait(&self.wake, s);
        }
        result
    }
    fn release_handle(&self, handle: O::Handle) {
        // Shutdown may reenter the state mutex while release is executing.
        lock(&self.ops).release(handle);
    }
    pub fn with_ops<T>(&self, read: impl FnOnce(&O) -> T) -> T {
        read(&lock(&self.ops))
    }
}
impl<O: MetaRequestOps + Send> cli_core::InterruptHook for Submission<O>
where
    O::Handle: Send,
{
    fn cancel(&self) {
        self.cancel_for_interrupt();
    }
}
impl<O: MetaRequestOps + Send + 'static> Submission<O>
where
    O::Handle: Send + 'static,
{
    /// Takes ownership of the caller's reference and registers this
    /// submission's hook with `interrupt`, so Ctrl-C can cancel the request
    /// until the returned registration is dropped, which `wait_with_unregister`
    /// does before the release. A Ctrl-C `interrupt` has already recorded
    /// cancels the request at once.
    pub fn adopt<'s>(
        self: &Arc<Self>,
        handle: O::Handle,
        interrupt: &'s State,
    ) -> Registration<'s> {
        {
            let mut state = lock(&self.state);
            assert!(state.handle.is_none(), "submission already adopted");
            state.handle = Some(handle);
        }
        let hook: Arc<Self> = Arc::clone(self);
        interrupt.register(hook)
    }
}
/// Acquires the buffer ticket of a part a GET's body callback receives.
pub trait BodyTicketOps {
    type Ticket: Copy;
    /// A new reference to `ticket`, or None when it cannot be acquired.
    fn acquire(&mut self, ticket: Self::Ticket) -> Option<Self::Ticket>;
}
/// One body as the CRT offers it to a GET's body callback: `storage` is
/// the cursor's bytes, None for a null pointer, and `ticket` the part's
/// buffer ticket, None when the CRT offers none.
#[derive(Debug, Clone, Copy)]
pub struct OfferedBody<B, T> {
    pub len: usize,
    pub storage: Option<B>,
    pub ticket: Option<T>,
}
/// How [`forward_body`] hands one body to its consumer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BodyDelivery<B, T> {
    /// A body with no bytes, which needs neither storage nor a ticket.
    Empty,
    /// A nonempty body whose bytes the CRT did not supply; nothing is
    /// acquired. The consumer fails its output with `DownloadBodyMissing`.
    Missing,
    /// A single-request GET's ticketless bytes, lent until the callback
    /// returns.
    Lent(B),
    /// A part's bytes and the reference acquired on its ticket. The consumer
    /// owns that reference whether it accepts the body or not.
    Ticketed(B, T),
}
/// The one routine every GET body passes through. A nonempty body acquires
/// its offered ticket; one without a ticket is accepted only from a
/// single-request GET, since every part of a ranged GET lives in a pool
/// buffer. A ranged part without a ticket, or a ticket `ops` cannot acquire,
/// fails with `AWS_ERROR_INVALID_ARGUMENT` before the consumer runs. Every
/// other body marks `delivered`, even one the consumer then rejects with its
/// own error.
pub fn forward_body<O: BodyTicketOps, B>(
    ops: &mut O,
    body: OfferedBody<B, O::Ticket>,
    single_request: bool,
    delivered: &AtomicBool,
    consume: impl FnOnce(BodyDelivery<B, O::Ticket>) -> Result<(), i32>,
) -> Result<(), i32> {
    let delivery = match (body.len, body.storage, body.ticket) {
        (0, _, _) => BodyDelivery::Empty,
        (_, None, _) => BodyDelivery::Missing,
        (_, Some(storage), Some(offered)) => {
            let acquired = ops.acquire(offered).ok_or(INVALID_ARGUMENT_ERROR_CODE)?;
            BodyDelivery::Ticketed(storage, acquired)
        }
        (_, Some(storage), None) if single_request => BodyDelivery::Lent(storage),
        (_, Some(_), None) => return Err(INVALID_ARGUMENT_ERROR_CODE),
    };
    delivered.store(true, Ordering::Release);
    consume(delivery)
}
