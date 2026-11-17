#![expect(
    clippy::unwrap_used,
    reason = "test future lock poisoning is a test invariant failure"
)]
use super::{AwsAllocator, AwsFutureS3BufferTicket, AwsS3BufferTicket, FutureOps};
use std::{
    ffi::c_int,
    ptr,
    sync::{
        Mutex,
        atomic::{AtomicU64, AtomicUsize, Ordering},
    },
};
#[derive(Debug, Default)]
struct Value {
    done: bool,
    error: i32,
    ticket: *mut AwsS3BufferTicket,
    /// Every completion asked for, including those a done future ignores.
    completions: usize,
    /// When the future was done, from `SEQUENCE`.
    sequence: u64,
}
/// Numbers every future's first completion, across all fake futures.
static SEQUENCE: AtomicU64 = AtomicU64::new(1);
#[derive(Debug)]
struct Future {
    refs: AtomicUsize,
    value: Mutex<Value>,
}
thread_local! { static LAST_ERROR: std::cell::Cell<i32> = const { std::cell::Cell::new(0) }; }
thread_local! { static IS_DONE_CALLS: std::cell::Cell<usize> = const { std::cell::Cell::new(0) }; }

#[derive(Debug)]
pub(crate) struct FakeFutures;

// SAFETY: the futures count references atomically, complete once under a
// lock, and release a rejected or remaining ticket through its vtable.
unsafe impl FutureOps for FakeFutures {
    unsafe fn new_future(&self, _: *mut AwsAllocator) -> *mut AwsFutureS3BufferTicket {
        Box::into_raw(Box::new(Future {
            refs: AtomicUsize::new(1),
            value: Mutex::default(),
        }))
        .cast()
    }
    unsafe fn acquire(&self, future: *mut AwsFutureS3BufferTicket) -> *mut AwsFutureS3BufferTicket {
        // SAFETY: caller owns a live future reference while acquiring another.
        unsafe {
            (*future.cast::<Future>())
                .refs
                .fetch_add(1, Ordering::AcqRel);
        }
        future
    }
    unsafe fn release(&self, future: *mut AwsFutureS3BufferTicket) -> *mut AwsFutureS3BufferTicket {
        if future.is_null() {
            return ptr::null_mut();
        }
        // SAFETY: caller transfers one live reference.
        if unsafe {
            (*future.cast::<Future>())
                .refs
                .fetch_sub(1, Ordering::AcqRel)
        } == 1
        {
            // SAFETY: the last reference uniquely owns the original allocation.
            let future = unsafe { Box::from_raw(future.cast::<Future>()) };
            let ticket = future.value.lock().unwrap().ticket;
            if !ticket.is_null() {
                // SAFETY: the future owns one ticket reference to its matching live vtable.
                unsafe {
                    ((*(*ticket).vtable).release.unwrap())(ticket);
                }
            }
        }
        ptr::null_mut()
    }
    unsafe fn set_result_by_move(
        &self,
        future: *mut AwsFutureS3BufferTicket,
        ticket: *mut *mut AwsS3BufferTicket,
    ) {
        // SAFETY: caller provides a live future and a writable owned ticket pointer.
        let future = unsafe { &*future.cast::<Future>() };
        // SAFETY: ticket points to one owned ticket reference transferred by this function.
        let incoming = unsafe { ticket.replace(ptr::null_mut()) };
        let rejected = {
            let mut value = future.value.lock().unwrap();
            value.completions += 1;
            if value.done {
                incoming
            } else {
                value.done = true;
                value.sequence = SEQUENCE.fetch_add(1, Ordering::Relaxed);
                value.ticket = incoming;
                ptr::null_mut()
            }
        };
        if !rejected.is_null() {
            // SAFETY: rejected retains the moved ticket reference and releases it outside the
            // future lock.
            unsafe {
                ((*(*rejected).vtable).release.unwrap())(rejected);
            }
        }
    }
    unsafe fn set_error(&self, future: *mut AwsFutureS3BufferTicket, error: c_int) {
        // SAFETY: caller retains a live reference for this mutation.
        let mut value = unsafe { &*future.cast::<Future>() }.value.lock().unwrap();
        value.completions += 1;
        if !value.done {
            value.done = true;
            value.sequence = SEQUENCE.fetch_add(1, Ordering::Relaxed);
            value.error = error;
        }
    }
    unsafe fn is_done(&self, future: *const AwsFutureS3BufferTicket) -> bool {
        IS_DONE_CALLS.set(IS_DONE_CALLS.get() + 1);
        // SAFETY: caller retains a live reference for this query.
        unsafe { &*future.cast::<Future>() }
            .value
            .lock()
            .unwrap()
            .done
    }
    fn raise_error(&self, error: c_int) {
        LAST_ERROR.set(error);
    }
}

/// # Safety
/// `future` is a live `FakeFutures` future the caller holds a reference to.
pub(crate) unsafe fn take_result(
    future: *mut AwsFutureS3BufferTicket,
) -> Result<*mut AwsS3BufferTicket, i32> {
    // SAFETY: tests retain one reference through extraction.
    let mut value = unsafe { &*future.cast::<Future>() }.value.lock().unwrap();
    if !value.done {
        return Err(-999);
    }
    if value.error != 0 {
        return Err(value.error);
    }
    Ok(std::mem::replace(&mut value.ticket, ptr::null_mut()))
}
/// How many times a fake future was completed, counting any completion it
/// ignored because it was already done.
///
/// # Safety
/// `future` is a live `FakeFutures` future the caller holds a reference to.
pub(crate) unsafe fn completions(future: *const AwsFutureS3BufferTicket) -> usize {
    // SAFETY: the caller retains a reference for this query.
    unsafe { &*future.cast::<Future>() }
        .value
        .lock()
        .unwrap()
        .completions
}
/// The order a fake future was done in among all fake futures, or 0 while
/// it is not done.
///
/// # Safety
/// `future` is a live `FakeFutures` future the caller holds a reference to.
pub(crate) unsafe fn sequence(future: *const AwsFutureS3BufferTicket) -> u64 {
    // SAFETY: the caller retains a reference for this query.
    unsafe { &*future.cast::<Future>() }
        .value
        .lock()
        .unwrap()
        .sequence
}
/// # Safety
/// `future` is a live, completed `FakeFutures` future the caller holds a
/// reference to.
#[cfg(all(test, not(miri)))]
pub(crate) unsafe fn error(future: *const AwsFutureS3BufferTicket) -> i32 {
    // SAFETY: the caller retains a reference for this query.
    unsafe { &*future.cast::<Future>() }
        .value
        .lock()
        .unwrap()
        .error
}
#[cfg(test)]
pub(crate) fn last_error() -> i32 {
    LAST_ERROR.get()
}
#[cfg(test)]
pub(crate) fn is_done_calls() -> usize {
    IS_DONE_CALLS.get()
}
