//! Bounded differential models for the actual pool state and ownership transitions.
#![expect(
    clippy::expect_used,
    reason = "fuzz assertions stop at the first violated invariant"
)]
use super::*;
use crate::testing::Choices;
mod operations;
mod support;
#[doc(inline)]
pub use operations::operations;
use support::Harness;
#[cfg(test)]
mod tests;

/// Checks full-width accounting against wider addition, including overflow boundaries.
pub fn byte_budget(bytes: &[u8]) {
    byte_budget_from(&mut Choices::new(bytes));
}
fn byte_budget_from(input: &mut Choices<'_>) {
    let budget = input.range(0, usize::MAX);
    let allocated = input.range(0, usize::MAX);
    let reserved = input.range(0, usize::MAX);
    let requested = input.range(0, usize::MAX);
    let total = allocated as u128 + reserved as u128 + requested as u128;
    assert_eq!(
        can_allocate(allocated, reserved, requested, budget),
        total <= budget as u128
    );
}

/// Exercises 128 claim/abort choices against independent per-shard reserved sizes.
pub fn reservations(bytes: &[u8]) {
    reservations_from(&mut Choices::new(bytes));
}
fn reservations_from(input: &mut Choices<'_>) {
    let harness = Harness::new(vec![0, 1, 2], 32, 1);
    install_four_slots(&harness);
    let mut expected = [[0_usize; 4]; 3];
    {
        let pool = harness.pool();
        let mut state = pool.state.lock();
        let TakeBufferAction::Allocate { slot, size, .. } =
            take_buffer_or_claim_locked(pool, &mut state, 0, 32)
        else {
            panic_claim()
        };
        assert!(matches!(
            take_buffer_or_claim_locked(pool, &mut state, 1, 1),
            TakeBufferAction::None
        ));
        abort_allocation(&mut state, slot, size);
        assert_eq!(state.reserved_bytes, 0);
    }
    for _ in 0..128 {
        reservation_step(&harness, &mut expected, input);
    }
    let mut state = harness.pool().state.lock();
    for (shard, sizes) in expected.into_iter().enumerate() {
        for (index, size) in sizes.into_iter().enumerate().filter(|(_, size)| *size != 0) {
            let slot = state.shards[shard]
                .slots
                .as_ref()
                .expect("initialized slots")[index]
                .get();
            abort_allocation(&mut state, slot, size);
        }
    }
    assert_eq!(state.reserved_bytes, 0);
}

#[expect(
    clippy::panic,
    reason = "a missing exact-fit claim is a fuzz invariant failure"
)]
fn panic_claim() -> ! {
    panic!("missing exact-fit allocation claim")
}

fn install_four_slots(harness: &Harness) {
    for shard in 0..3 {
        let replacement = HeapSlice::new(&harness.pool().ops, AllocationKind::Slots, 4, |_| {
            UnsafeCell::new(Buffer {
                state: BufferState::Empty,
                mapping: None,
                node: shard as u32,
                node_index: shard,
            })
        })
        .expect("bounded model slots");
        let old = harness.pool().state.lock().shards[shard]
            .slots
            .replace(replacement);
        drop(old);
    }
}

fn reservation_step(harness: &Harness, expected: &mut [[usize; 4]; 3], input: &mut Choices<'_>) {
    let shard = input.index(3);
    let pool = harness.pool();
    let mut state = pool.state.lock();
    let reserved: usize = expected.iter().flatten().sum();
    if input.index(2) != 0 {
        let index = input.index(4);
        if expected[shard][index] != 0 {
            let slot = state.shards[shard]
                .slots
                .as_ref()
                .expect("initialized slots")[index]
                .get();
            abort_allocation(&mut state, slot, expected[shard][index]);
            expected[shard][index] = 0;
        }
    } else {
        let requested = input.range(1, 33);
        let free = expected[shard].iter().position(|size| *size == 0);
        let allowed = free.is_some() && reserved + requested <= 32;
        let action = take_buffer_or_claim_locked(pool, &mut state, shard, requested);
        assert_eq!(matches!(action, TakeBufferAction::Allocate { .. }), allowed);
        if let TakeBufferAction::Allocate { slot, size, .. } = action {
            assert_eq!(size, requested);
            let index = free.expect("independent model permits a slot");
            assert_eq!(
                slot,
                state.shards[shard].slots.as_ref().expect("slots")[index].get()
            );
            expected[shard][index] = requested;
        }
    }
    verify_reservations(&state, expected);
}

fn verify_reservations(state: &State, expected: &[[usize; 4]; 3]) {
    for (shard, sizes) in expected.iter().enumerate() {
        for (index, size) in sizes.iter().enumerate() {
            // SAFETY: the caller retains the exclusive state lock.
            let slot = unsafe { &*state.shards[shard].slots.as_ref().expect("slots")[index].get() };
            assert_eq!(slot.state == BufferState::Allocating, *size != 0);
            assert!(slot.mapping.is_none());
            assert_eq!(slot.node_index, shard);
        }
    }
    assert_eq!(state.reserved_bytes, expected.iter().flatten().sum());
    assert_eq!(state.allocated_bytes, 0);
}

const OWNERSHIP_BUFFER_BYTES: usize = 4096;

/// Exercises real futures and ticket references across three bounded FIFO/trim rounds.
pub fn ownership(bytes: &[u8]) {
    ownership_from(&mut Choices::new(bytes));
}
fn ownership_from(input: &mut Choices<'_>) {
    let harness = Harness::new(vec![0], OWNERSHIP_BUFFER_BYTES, OWNERSHIP_BUFFER_BYTES);
    let ops = Arc::clone(&harness.ops);
    let storage = ops.live.load(Ordering::SeqCst);
    for _ in 0..3 {
        harness.ops.fail_mapping.store(false, Ordering::SeqCst);
        ownership_round(&harness, input);
        assert_eq!(ops.live.load(Ordering::SeqCst), storage);
        assert_settled(harness.pool());
        harness.trim();
        assert_trimmed(harness.pool());
        assert_eq!(ops.mappings.load(Ordering::SeqCst), 0);
    }
    drop(harness);
    assert_eq!(ops.live.load(Ordering::SeqCst), 0);
}

fn assert_settled(pool: &Pool) {
    assert_eq!(pool.refs.load(Ordering::Acquire), 1);
    let state = pool.state.lock();
    assert!(state.pending_head.is_null());
    assert!(state.pending_tail.is_null());
    assert_eq!(state.pending_len, 0);
}

fn assert_trimmed(pool: &Pool) {
    let state = pool.state.lock();
    let slot = ownership_slot(&state);
    assert!(slot.state == BufferState::Empty);
    assert!(slot.mapping.is_none());
    assert_eq!(state.allocated_bytes, 0);
}

fn ownership_slot(state: &State) -> &Buffer {
    let slots = state.shards[0].slots.as_ref().expect("initialized slots");
    for cell in slots.iter().skip(1) {
        // SAFETY: the caller retains the exclusive state lock.
        let spare = unsafe { &*cell.get() };
        assert!(spare.state == BufferState::Empty && spare.mapping.is_none());
    }
    // SAFETY: the caller retains the exclusive state lock for the returned borrow.
    unsafe { &*slots[0].get() }
}

fn ownership_request_size(input: &mut Choices<'_>) -> usize {
    input.range(1, OWNERSHIP_BUFFER_BYTES)
}

struct Request {
    future: support::Future,
    size: usize,
    error: i32,
}
fn ownership_round(harness: &Harness, input: &mut Choices<'_>) {
    let requests = input.range(2, 9);
    let mut queue = Vec::new();
    for index in 0..requests {
        let size = ownership_request_size(input);
        let future = harness.reserve(size, false);
        assert_eq!(future.done(), index == 0);
        queue.push(Request {
            future,
            size,
            error: 0,
        });
    }
    harness.ops.fail_mapping.store(true, Ordering::SeqCst);
    let forced = harness.reserve(1, true);
    assert!(forced.done());
    assert_eq!(
        forced.take().expect_err("modeled error completion"),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(harness.pool().state.lock().forced_bytes, 0);
    for request in queue.iter_mut().skip(1) {
        if input.index(2) != 0 {
            request.error = if input.index(2) != 0 {
                ffi::AWS_ERROR_OOM
            } else {
                ffi::AWS_ERROR_S3_CANCELED
            };
            request.future.cancel(request.error);
        }
    }
    drain_requests(harness, input, &mut queue);
    assert_round_idle(harness.pool());
}

fn assert_round_idle(pool: &Pool) {
    let state = pool.state.lock();
    assert!(ownership_slot(&state).state == BufferState::Idle);
    assert_eq!(state.allocated_bytes, OWNERSHIP_BUFFER_BYTES);
}

fn drain_requests(harness: &Harness, input: &mut Choices<'_>, queue: &mut [Request]) {
    for index in 0..queue.len() {
        assert!(queue[index].future.done());
        let result = queue[index].future.take();
        if queue[index].error != 0 {
            assert_eq!(
                result.expect_err("modeled error completion"),
                queue[index].error
            );
            continue;
        }
        let ticket = result.expect("oldest uncancelled request receives capacity");
        assert_eq!(ticket.capacity(), queue[index].size);
        release_nonfinal(harness, input, &ticket, &queue[index + 1..]);
        if input.index(2) != 0
            && let Some(younger) = queue
                .iter_mut()
                .skip(index + 1)
                .find(|request| request.error == 0)
        {
            younger.error = ffi::AWS_ERROR_OOM;
            harness.ops.fail_ticket.store(true, Ordering::SeqCst);
        }
        drop(ticket);
    }
    assert_eq!(harness.pool().state.lock().reserved_bytes, 0);
}

fn release_nonfinal(
    harness: &Harness,
    input: &mut Choices<'_>,
    ticket: &support::Ticket,
    younger: &[Request],
) {
    let pool = harness.pool();
    assert_ticket_slot(pool, ticket);
    let copies: Vec<_> = (0..input.range(1, 4)).map(|_| ticket.acquire()).collect();
    let count = copies.len();
    assert_eq!(pool.refs.load(Ordering::Acquire), 2);
    {
        let mut state = pool.state.lock();
        assert!(detach_trim_candidate_from_pool_locked(&mut state, 0).is_none());
    }
    for (released, copy) in copies.into_iter().enumerate() {
        drop(copy);
        assert_eq!(ticket.refs(), count - released);
        assert_eq!(pool.refs.load(Ordering::Acquire), 2);
        assert_ticket_slot(pool, ticket);
        for request in younger {
            assert_eq!(request.future.done(), request.error != 0);
        }
    }
}

fn assert_ticket_slot(pool: &Pool, ticket: &support::Ticket) {
    let buffer = ticket.buffer();
    let state = pool.state.lock();
    let slot = ownership_slot(&state);
    assert!(slot.state == BufferState::InUse);
    assert_eq!(slot.mapping.as_ref().map(Mapping::as_ptr), Some(buffer));
}
