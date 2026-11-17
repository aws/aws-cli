#![expect(
    clippy::unwrap_used,
    clippy::panic,
    reason = "test fixtures require successful expected operations"
)]
use super::test_support::{FakeOps, Future, FutureAddress, PoolAddress, TestPool};
use super::*;

const CONCURRENT_POOL_OPERATIONS: usize = if cfg!(miri) { 8 } else { 512 };

#[test]
fn concurrent_pool_reservations_cancellation_and_release_keep_ticket_storage_exclusive() {
    let pool = TestPool::new(&[0, 1], 128, 64);
    let ops = Arc::clone(&pool.ops);
    ops.lock_probe.store(ptr::null_mut(), Ordering::Release);
    let start = std::sync::Barrier::new(4);
    std::thread::scope(|scope| {
        for worker in 0..4 {
            let address = PoolAddress(pool.pointer);
            let start = &start;
            scope.spawn(move || exercise_concurrent_pool(address, worker, start));
        }
    });
    pool.trim();
    assert_eq!(pool.queue_len(), 0);
    assert_eq!(pool.pool().state.lock().pending_len, 0);
    assert_eq!(pool.accounting(), (0, 0, 0));
    assert_eq!(pool.pool().refs.load(Ordering::Acquire), 1);
    assert!(
        pool.pool()
            .diagnostics
            .peak_allocated_bytes
            .load(Ordering::Acquire)
            <= 128
    );
    drop(pool);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
    assert_eq!(ops.mappings.load(Ordering::Acquire), 0);
}

fn exercise_concurrent_pool(address: PoolAddress, worker: u8, start: &std::sync::Barrier) {
    start.wait();
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(30);
    for operation in 0..CONCURRENT_POOL_OPERATIONS {
        let interface = (&raw const address.get().interface).cast_mut();
        // SAFETY: the scoped parent retains its pool reference until every worker joins.
        let future = Future(unsafe {
            pool_reserve(
                interface,
                ffi::AwsS3BufferPoolReserveMeta {
                    size: 64,
                    can_block: operation % 11 == 0,
                    local_offset: 0,
                    client: ptr::null_mut(),
                    meta_request: ptr::null_mut(),
                },
            )
        });
        assert!(!future.0.is_null());
        if operation % 5 == 0 {
            future.cancel(ffi::AWS_ERROR_S3_CANCELED);
        }
        while !future.done() {
            assert!(
                std::time::Instant::now() < deadline,
                "pool reservation stalled"
            );
            std::thread::yield_now();
        }
        match future.take() {
            Ok(ticket) => {
                assert_eq!(ticket.capacity(), 64);
                let extra = ticket.acquire();
                drop(ticket);
                // SAFETY: this retained ticket uniquely owns its entire claimed body buffer.
                let bytes = unsafe { std::slice::from_raw_parts_mut(extra.buffer(), 64) };
                bytes.fill(worker);
                std::thread::yield_now();
                assert!(bytes.iter().all(|byte| *byte == worker));
            }
            Err(error) => assert_eq!(error, ffi::AWS_ERROR_S3_CANCELED),
        }
    }
}

#[test]
fn factory_and_ticket_lifetimes() {
    let ops = Arc::new(FakeOps::default());
    let pool = TestPool::with_ops(&[0], 16, 8, ops.clone()).unwrap();
    assert_eq!(pool.pool().budget_bytes, 16);
    let future = pool.reserve(8, false);
    assert!(future.done());
    let ticket = future.take().unwrap();
    assert_eq!(ticket.capacity(), 8);
    assert_eq!(ticket.node(), 0);
    let other = ticket.acquire();
    drop(ticket);
    drop(pool);
    assert!(ops.live.load(Ordering::Acquire) > 0);
    drop(other);
    drop(future);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
    assert_eq!(ops.mappings.load(Ordering::Acquire), 0);
}
#[test]
fn factory_failures_roll_back() {
    for fail in 1..=4 {
        let ops = Arc::new(FakeOps::default());
        ops.fail_at.store(fail, Ordering::Release);
        assert!(TestPool::with_ops(&[0, 1], 32, 8, ops.clone()).is_none());
        assert_eq!(ops.live.load(Ordering::Acquire), 0);
        assert_eq!(ffi::fake::last_error(), ffi::AWS_ERROR_OOM);
    }
}
#[test]
fn reserve_and_trim_smoke() {
    let pool = TestPool::new(&[0], 8, 8);
    let future = pool.reserve(8, false);
    let ticket = future.take().unwrap();
    let waiting = pool.reserve(8, false);
    assert!(!waiting.done());
    drop(ticket);
    assert!(waiting.done());
    drop(waiting.take().unwrap());
    pool.trim();
    assert_eq!(pool.ops.mappings.load(Ordering::Acquire), 0);
}
#[test]
fn cancellation_preserves_prior_error() {
    let pool = TestPool::new(&[0], 8, 8);
    let first = pool.reserve(8, false).take().unwrap();
    let pending = pool.reserve(8, false);
    pending.cancel(77);
    drop(first);
    assert_eq!(pending.take().unwrap_err(), 77);
}

#[test]
fn derives_reservable_dynamic_size() {
    let pool = TestPool::new(&[0], 128, 8);
    // SAFETY: the fixture retains the live pool interface.
    let derived = unsafe { pool_derive_aligned_buffer_size(pool.interface(), 28) } as usize;
    assert!(derived >= 28);
    assert!(derived > pool.pool().part_size);
    assert!(derived <= pool.pool().max_buffer_size);
    assert!(supported_size(pool.pool(), derived));
}

#[test]
fn accepts_only_reservable_special_sizes() {
    let pool = TestPool::new(&[0], 32, 8);
    // SAFETY: the fixture retains the live pool interface across each callback.
    unsafe {
        assert_eq!(pool_add_special_size(pool.interface(), 28), 0);
        assert_eq!(pool.pool().state.lock().special_size_count, 1);
        assert_eq!(pool_add_special_size(pool.interface(), 64), -1);
    }
}

#[test]
fn reuses_smallest_idle_buffer() {
    let pool = TestPool::new(&[0], 128, 8);
    let large = pool.seed_idle(0, 32);
    let small = pool.seed_idle(0, 8);
    let first = pool.reserve(4, false).take().unwrap();
    assert_eq!(first.buffer(), small);
    drop(first);
    let held = pool.reserve(8, false).take().unwrap();
    let second = pool.reserve(28, false).take().unwrap();
    assert_eq!(second.buffer(), large);
    drop((held, second));
}

#[test]
fn allocation_claim_reserves_slot_and_budget() {
    let pool = TestPool::new(&[0], 32, 8);
    let address = PoolAddress(pool.pointer);
    *pool.ops.on_map.lock().unwrap() = Some(Box::new(move || {
        let state = address.get().state.lock();
        assert_eq!(state.reserved_bytes, 8);
        assert_eq!(state.allocated_bytes, 0);
        assert!(slot_state(&state, 0, 0) == BufferState::Allocating);
    }));
    pool.ops.fail_mmap.store(true, Ordering::Release);
    let future = pool.reserve(8, false);
    assert_eq!(
        future.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.accounting(), (0, 0, 0));
    let state = pool.pool().state.lock();
    // SAFETY: the fixture inspects this slot only while its state lock is held.
    let slot = unsafe { &*state.shards[0].slots.as_ref().unwrap()[0].get() };
    assert!(slot.state == BufferState::Empty);
    assert!(slot.mapping.is_none());
}

#[test]
fn no_slot_or_trim_candidate_preserves_accounting() {
    let pool = TestPool::new(&[0], 32, 8);
    let slots = HeapSlice::new(&pool.pool().ops, AllocationKind::Slots, 1, |_| {
        UnsafeCell::new(Buffer {
            state: BufferState::Empty,
            mapping: None,
            node: 0,
            node_index: 0,
        })
    })
    .unwrap();
    let previous = pool.pool().state.lock().shards[0].slots.replace(slots);
    drop(previous);
    let ticket = pool.reserve(8, false).take().unwrap();
    let waiting = pool.reserve(8, false);
    assert!(!waiting.done());
    assert_eq!(pool.accounting(), (8, 0, 0));
    assert_eq!(pool.queue_len(), 1);
    let state = pool.pool().state.lock();
    assert!(slot_state(&state, 0, 0) == BufferState::InUse);
    drop(state);
    waiting.cancel(77);
    drop(ticket);
}

#[test]
fn installed_mapping_moves_reserved_to_allocated() {
    let pool = TestPool::new(&[0], 32, 8);
    let address = PoolAddress(pool.pointer);
    *pool.ops.on_complete.lock().unwrap() = Some(Box::new(move || {
        let state = address.get().state.lock();
        assert_eq!(state.reserved_bytes, 0);
        assert_eq!(state.allocated_bytes, 8);
        assert!(slot_state(&state, 0, 0) == BufferState::InUse);
    }));
    let ticket = pool.reserve(8, false).take().unwrap();
    assert_eq!(pool.ops.mappings.load(Ordering::Acquire), 1);
    assert_eq!(ticket.capacity(), 8);
}

#[test]
fn allocating_pending_head_cannot_be_overtaken() {
    let pool = TestPool::new(&[0], 32, 8);
    let first = pool.queued(8, 0, true);
    let second = pool.queued(8, 0, false);
    let mut completions = PendingCompletionBatch::new();
    assert!(matches!(
        serve_pending_head_locked(
            pool.pool(),
            &mut pool.pool().state.lock(),
            None,
            &mut completions
        ),
        PendingAction::None
    ));
    assert_eq!(pool.queue_len(), 2);
    assert!(!first.done());
    assert!(!second.done());
    first.cancel(77);
    let mut completions = PendingCompletionBatch::new();
    assert!(matches!(
        serve_pending_head_locked(
            pool.pool(),
            &mut pool.pool().state.lock(),
            None,
            &mut completions
        ),
        PendingAction::None
    ));
    // SAFETY: the test controls this fixture claim and restores it under its exclusive lock.
    unsafe {
        (*pool.pool().state.lock().pending_head).allocating = false;
    }
}

#[test]
fn oversized_pending_remains_queued_after_return() {
    let pool = TestPool::new(&[0], 16, 8);
    let first = pool.reserve(8, false).take().unwrap();
    let held = pool.reserve(8, false).take().unwrap();
    let pending = pool.reserve(16, false);
    drop(first);
    assert!(!pending.done());
    assert_eq!(pool.queue_len(), 1);
    assert_eq!(pool.accounting(), (8, 0, 0));
    assert_eq!(pool.ops.mappings.load(Ordering::Acquire), 1);
    pending.cancel(ffi::AWS_ERROR_S3_CANCELED);
    drop(held);
}

#[test]
fn stages_pending_completion_until_after_unlock() {
    let pool = TestPool::new(&[0], 8, 8);
    pool.seed_idle(0, 8);
    let slot = lend_idle(&pool, 0, 8);
    let pending = pool.queued(8, 0, false);
    let mut completions = PendingCompletionBatch::new();
    complete_pending_queues(pool.pointer, Some(0), Some(slot), &mut completions);
    assert!(!completions.is_empty());
    assert!(!pending.done());
    assert!(pool.pool().state.lock().pending_head.is_null());
    let future = FutureAddress(pending.0);
    let address = PoolAddress(pool.pointer);
    *pool.ops.on_complete.lock().unwrap() = Some(Box::new(move || {
        assert!(!future.done());
        assert!(address.get().state.lock().pending_head.is_null());
    }));
    completions.drain(pool.pool());
    assert!(pending.done());
    assert_eq!(pending.take().unwrap().capacity(), 8);
}

#[test]
fn cancellation_during_staged_completion_releases_ticket() {
    let pool = TestPool::new(&[0], 8, 8);
    let held = pool.reserve(8, false).take().unwrap();
    let pending = pool.reserve(8, false);
    let future = FutureAddress(pending.0);
    *pool.ops.on_complete.lock().unwrap() = Some(Box::new(move || {
        assert!(!future.done());
        future.cancel(ffi::AWS_ERROR_S3_CANCELED);
    }));
    drop(held);
    assert!(pending.done());
    assert_eq!(pending.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
}

#[test]
fn multiple_completions_keep_fifo_buffer_order() {
    let pool = TestPool::new(&[0], 16, 8);
    let first = pool.seed_idle(0, 8);
    let second = pool.seed_idle(0, 8);
    let older = pool.queued(8, 0, false);
    let younger = pool.queued(8, 0, false);
    pool.complete_any_pending();
    assert_eq!(pool.queue_len(), 0);
    let one = older.take().unwrap();
    let two = younger.take().unwrap();
    assert_eq!(one.buffer(), first);
    assert_eq!(two.buffer(), second);
}

#[test]
fn ticket_failure_hands_returned_buffer_to_pending() {
    let pool = TestPool::new(&[0], 8, 8);
    let pointer = pool.seed_idle(0, 8);
    let failed = pool.queued(8, 0, false);
    let pending = pool.queued(8, 0, false);
    pool.ops.fail_at.store(
        pool.ops.calls.load(Ordering::Acquire) + 1,
        Ordering::Release,
    );
    pool.complete_any_pending();
    assert_eq!(failed.take().unwrap_err(), ffi::AWS_ERROR_OOM);
    assert_eq!(pool.queue_len(), 0);
    assert!(pending.done());
    assert_eq!(pending.take().unwrap().buffer(), pointer);
}

#[test]
fn mapping_failure_redrives_other_pending() {
    let pool = TestPool::new(&[0, 1], 16, 8);
    let pointer = pool.seed_idle(1, 8);
    let failed = pool.queued(8, 0, false);
    let pending = pool.queued(8, 1, false);
    pool.ops.fail_mmap.store(true, Ordering::Release);
    pool.complete_any_pending();
    assert_eq!(
        failed.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert!(pending.done());
    assert_eq!(pool.queue_len(), 0);
    assert_eq!(pending.take().unwrap().buffer(), pointer);
    assert_eq!(pool.accounting(), (8, 0, 0));
}

#[test]
fn reserve_failure_hands_returned_buffer_to_pending_reserve() {
    let pool = TestPool::new(&[0], 8, 8);
    let pointer = pool.seed_idle(0, 8);
    let slot = lend_idle(&pool, 0, 8);
    let failed = new_future(&pool);
    let pending = pool.queued(8, 0, false);
    let returned = Claim::in_use(pool.pointer, failed.0, slot, 8).fail(ffi::AWS_ERROR_OOM);
    assert_eq!(returned, failed.0);
    assert!(failed.done());
    assert_eq!(failed.take().unwrap_err(), ffi::AWS_ERROR_OOM);
    assert_eq!(pool.queue_len(), 0);
    assert!(pending.done());
    assert_eq!(pending.take().unwrap().buffer(), pointer);
}

#[test]
fn reserve_failure_without_returned_buffer_redrives_pending_reserves() {
    let pool = TestPool::new(&[0], 16, 8);
    let pointer = pool.seed_idle(0, 8);
    let failed = new_future(&pool);
    let pending = pool.queued(8, 0, false);
    let returned = pool
        .claim_allocating(&failed, 0, 8)
        .fail(ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
    assert_eq!(returned, failed.0);
    assert!(failed.done());
    assert_eq!(
        failed.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.queue_len(), 0);
    assert!(pending.done());
    assert_eq!(pending.take().unwrap().buffer(), pointer);
    assert_eq!(pool.accounting(), (8, 0, 0));
}

#[test]
fn staged_errors_complete_outside_lock() {
    let pool = TestPool::new(&[0], 8, 8);
    pool.seed_idle(0, 8);
    let pending = pool.queued(8, 0, false);
    let future = FutureAddress(pending.0);
    *pool.ops.on_complete.lock().unwrap() = Some(Box::new(move || assert!(!future.done())));
    *pool.ops.fail_kind.lock().unwrap() = Some(AllocationKind::Ticket);
    pool.complete_any_pending();
    assert!(pending.done());
    assert_eq!(pending.take().unwrap_err(), ffi::AWS_ERROR_OOM);
    assert!(pool.ops.completions.load(Ordering::Acquire) > 0);
}

#[test]
fn config_copies_node_order() {
    let config = Config::new(vec![0, 2, 3], 32).unwrap();
    assert_eq!(config.nodes, [0, 2, 3]);
    assert_eq!(Config::new(vec![7], 8).unwrap().nodes, [7]);
}

#[test]
fn config_rejects_invalid_node_counts() {
    assert!(Config::new(vec![], 8).is_err());
    assert!(Config::new(vec![0; MAX_NODES + 1], 8).is_err());
}

#[test]
fn shard_selection_prefers_node_then_round_robins() {
    let pool = TestPool::new(&[0, 1], 32, 8);
    let mut state = pool.pool().state.lock();
    assert_eq!(select_shard(&mut state, Some(1)), 1);
    assert_eq!(select_shard(&mut state, None), 0);
    assert_eq!(select_shard(&mut state, None), 1);
    assert_eq!(select_shard(&mut state, None), 0);
    assert_eq!(select_shard(&mut state, Some(9)), 1);
    assert_eq!(state.shards[1].current_node_hit_count, 1);
    assert_eq!(state.shards[0].fallback_reserve_count, 2);
    assert_eq!(state.shards[1].fallback_reserve_count, 2);
}

#[test]
fn reserve_steals_remote_idle_buffer() {
    let pool = TestPool::new(&[1000, 1001], 32, 8);
    let slots = pool.pool().state.lock().shards[0].slots.take();
    let pointer = pool.seed_idle(1, 8);
    let ticket = pool.reserve(8, false).take().unwrap();
    assert_eq!(pool.pool().state.lock().cross_shard_steal_count, 1);
    assert_eq!(ticket.node(), 1001);
    assert_eq!(ticket.buffer(), pointer);
    assert!(slot_state(&pool.pool().state.lock(), 1, 0) == BufferState::InUse);
    drop(ticket);
    assert!(slot_state(&pool.pool().state.lock(), 1, 0) == BufferState::Idle);
    pool.pool().state.lock().shards[0].slots = slots;
}

#[test]
fn release_funds_remote_pending() {
    let pool = TestPool::new(&[0, 1], 8, 8);
    pool.ops.node.store(1, Ordering::Release);
    let held = pool.reserve(8, false).take().unwrap();
    pool.ops.node.store(0, Ordering::Release);
    let pending = pool.reserve(8, false);
    drop(held);
    assert_eq!(pool.queue_len(), 0);
    assert!(pending.done());
    assert_eq!(pool.pool().state.lock().cross_shard_steal_count, 1);
    let ticket = pending.take().unwrap();
    assert_eq!(ticket.node(), 1);
    drop(ticket);
    assert!(slot_state(&pool.pool().state.lock(), 1, 0) == BufferState::Idle);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Asserts every step of one ownership transition sequence in one test"
)]
fn release_funds_oldest_before_owner_shard_waiter() {
    let pool = TestPool::new(&[0, 1], 8, 8);
    pool.ops.node.store(1, Ordering::Release);
    let held = pool.reserve(8, false).take().unwrap();
    pool.ops.node.store(0, Ordering::Release);
    let older = pool.reserve(8, false);
    pool.ops.node.store(1, Ordering::Release);
    let younger = pool.reserve(8, false);
    drop(held);
    assert!(older.done());
    assert!(!younger.done());
    assert_eq!(pool.queue_len(), 1);
    assert_eq!(pool.pool().state.lock().cross_shard_steal_count, 1);
    let ticket = older.take().unwrap();
    assert_eq!(ticket.node(), 1);
    drop(ticket);
    assert!(younger.done());
    assert_eq!(pool.queue_len(), 0);
    assert_eq!(pool.pool().state.lock().cross_shard_steal_count, 1);
    let ticket = younger.take().unwrap();
    assert_eq!(ticket.node(), 1);
    drop(ticket);
    assert!(slot_state(&pool.pool().state.lock(), 1, 0) == BufferState::Idle);
}

#[test]
fn normal_reserve_does_not_overtake_unfundable_head() {
    let pool = TestPool::new(&[1000, 1001], 8, 8);
    pool.seed_idle(1, 8);
    let older = pool.queued(16, 0, false);
    let younger = pool.reserve(8, false);
    assert!(!older.done());
    assert!(!younger.done());
    assert_eq!(pool.queue_len(), 2);
    assert_eq!(pool.pool().state.lock().cross_shard_steal_count, 0);
    assert!(slot_state(&pool.pool().state.lock(), 1, 0) == BufferState::Idle);
}

#[test]
fn cancelled_head_is_swept_by_new_reserve() {
    let pool = TestPool::new(&[0], 8, 8);
    pool.seed_idle(0, 8);
    let dead = pool.queued(16, 0, false);
    dead.cancel(ffi::AWS_ERROR_S3_CANCELED);
    let future = pool.reserve(8, false);
    assert!(future.done());
    assert_eq!(pool.queue_len(), 0);
    let ticket = future.take().unwrap();
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::InUse);
    drop(ticket);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Asserts every step of one ownership transition sequence in one test"
)]
fn can_block_forces_without_touching_older_queue() {
    let pool = TestPool::new(&[0], 8, 8);
    let held = pool.reserve(8, false).take().unwrap();
    let older = pool.queued(16, 0, false);
    let future = pool.reserve(8, true);
    assert!(future.done());
    let ticket = future.take().unwrap();
    assert_eq!(pool.queue_len(), 1);
    assert!(!older.done());
    assert_eq!(pool.accounting(), (8, 0, 8));
    assert_eq!(pool.pool().state.lock().forced_reserve_count, 1);
    assert_eq!(ticket.node(), 0);
    assert_eq!(ticket.capacity(), 8);
    assert_ne!(ticket.buffer(), held.buffer());
    drop(ticket);
    assert_eq!(pool.accounting(), (8, 0, 0));
    assert_eq!(pool.queue_len(), 1);
    older.cancel(77);
    drop(held);
}

#[test]
fn can_block_forces_when_exhausted() {
    let pool = TestPool::new(&[0], 8, 8);
    let held = pool.reserve(8, false).take().unwrap();
    let future = pool.reserve(8, true);
    assert!(future.done());
    assert_eq!(pool.queue_len(), 0);
    assert_eq!(pool.pool().state.lock().forced_reserve_count, 1);
    assert_eq!(pool.accounting(), (8, 0, 8));
    drop(future.take().unwrap());
    assert_eq!(pool.accounting(), (8, 0, 0));
    assert_eq!(held.capacity(), 8);
}

#[test]
fn can_block_reuses_pooled_fast_path() {
    let pool = TestPool::new(&[0], 32, 8);
    let pointer = pool.seed_idle(0, 8);
    let future = pool.reserve(8, true);
    assert!(future.done());
    assert_eq!(pool.pool().state.lock().forced_reserve_count, 0);
    assert_eq!(pool.accounting(), (8, 0, 0));
    let ticket = future.take().unwrap();
    assert_eq!(ticket.buffer(), pointer);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::InUse);
    drop(ticket);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
}

#[test]
fn forced_mapping_error_completes_without_queueing() {
    let pool = TestPool::new(&[0], 8, 8);
    let held = pool.reserve(8, false).take().unwrap();
    pool.ops.fail_mmap.store(true, Ordering::Release);
    let future = pool.reserve(8, true);
    assert!(future.done());
    assert_eq!(
        future.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.queue_len(), 0);
    assert_eq!(pool.pool().state.lock().forced_reserve_count, 1);
    assert_eq!(pool.accounting(), (8, 0, 0));
    drop(held);
}

#[test]
fn forced_ticket_failure_rolls_back_mapping() {
    let pool = TestPool::new(&[0], 8, 8);
    let held = pool.reserve(8, false).take().unwrap();
    let calls = pool.ops.calls.load(Ordering::Acquire);
    let live = pool.ops.live.load(Ordering::Acquire);
    pool.ops.fail_at.store(calls + 2, Ordering::Release);
    let future = pool.reserve(8, true);
    assert!(future.done());
    assert_eq!(future.take().unwrap_err(), ffi::AWS_ERROR_OOM);
    assert_eq!(pool.pool().state.lock().forced_reserve_count, 1);
    assert_eq!(pool.ops.calls.load(Ordering::Acquire), calls + 2);
    assert_eq!(pool.ops.live.load(Ordering::Acquire), live);
    assert_eq!(pool.ops.mappings.load(Ordering::Acquire), 1);
    assert_eq!(pool.accounting(), (8, 0, 0));
    drop(held);
}

#[test]
fn cross_shard_trim_precedes_larger_pending_allocation() {
    let pool = TestPool::new(&[0, 1], 16, 8);
    let pointer = pool.seed_idle(1, 8);
    let pending = pool.queued(16, 0, false);
    let mut completions = PendingCompletionBatch::new();
    let PendingAction::Trim(mapping) = serve_pending_head_locked(
        pool.pool(),
        &mut pool.pool().state.lock(),
        Some(1),
        &mut completions,
    ) else {
        panic!("expected remote idle trim");
    };
    assert_eq!(mapping.as_ptr(), pointer);
    assert_eq!(mapping.len(), 8);
    assert_eq!(pool.accounting(), (0, 0, 0));
    assert!(slot_state(&pool.pool().state.lock(), 1, 0) == BufferState::Empty);
    assert_eq!(pool.queue_len(), 1);
    drop(mapping);
    let address = PoolAddress(pool.pointer);
    let future = FutureAddress(pending.0);
    *pool.ops.on_map.lock().unwrap() = Some(Box::new(move || {
        let state = address.get().state.lock();
        assert_eq!(state.reserved_bytes, 16);
        assert!(slot_state(&state, 0, 0) == BufferState::Allocating);
        // SAFETY: the queue still owns this allocation's pending node under the state lock.
        assert!(unsafe { (*state.pending_head).allocating });
        drop(state);
        future.cancel(ffi::AWS_ERROR_S3_CANCELED);
    }));
    pool.ops.fail_mmap.store(true, Ordering::Release);
    pool.complete_any_pending();
    assert!(pending.done());
    assert_eq!(pending.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    assert_eq!(pool.accounting(), (0, 0, 0));
}

#[test]
fn pending_ticket_reports_buffer_owner_node() {
    let pool = TestPool::new(&[1000, 1001], 8, 8);
    let pointer = pool.seed_idle(0, 8);
    let pending = pool.queued(8, 1, false);
    complete_pending_or_free(pool.pointer, Some(0), None);
    assert!(pending.done());
    let ticket = pending.take().unwrap();
    assert_eq!(ticket.node(), 1000);
    assert_eq!(ticket.buffer(), pointer);
    drop(ticket);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
}

#[test]
fn every_factory_allocation_failure_rolls_back() {
    for failed_call in 1..=5 {
        let ops = Arc::new(FakeOps::default());
        ops.fail_at.store(failed_call, Ordering::Release);
        assert!(TestPool::with_ops(&[0, 1, 2], 6, 1, ops.clone()).is_none());
        assert_eq!(ops.calls.load(Ordering::Acquire), failed_call);
        assert_eq!(ops.released.load(Ordering::Acquire), failed_call - 1);
        assert_eq!(ops.live.load(Ordering::Acquire), 0);
    }
    let pool = TestPool::new(&[0, 1, 2], 6, 1);
    let ops = pool.ops.clone();
    assert_eq!(ops.calls.load(Ordering::Acquire), 5);
    assert_eq!(ops.live.load(Ordering::Acquire), 5);
    drop(pool);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
    assert_eq!(ops.released.load(Ordering::Acquire), 5);
}

#[test]
fn invalid_factory_inputs_allocate_nothing() {
    let ops = Arc::new(FakeOps::default());
    for (nodes, part) in [(vec![], 8), (vec![0; MAX_NODES + 1], 8), (vec![0], 0)] {
        assert!(TestPool::with_ops(&nodes, 16, part, ops.clone()).is_none());
        assert_eq!(ffi::fake::last_error(), ffi::AWS_ERROR_INVALID_ARGUMENT);
    }
    let config = FactoryConfig::new(Config::new(vec![0], 16).unwrap());
    let crt_config = ffi::AwsS3BufferPoolConfig {
        client: ptr::null_mut(),
        part_size: 8,
        max_part_size: 8,
        memory_limit: 16,
    };
    assert!(
        factory_with_ops(
            ptr::null_mut(),
            crt_config,
            &config,
            ops.clone(),
            &FAKE_POOL_VTABLE
        )
        .is_null()
    );
    assert_eq!(ops.calls.load(Ordering::Acquire), 0);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
}

#[test]
fn factory_rejects_part_size_above_budget() {
    let ops = Arc::new(FakeOps::default());
    assert!(TestPool::with_ops(&[0], 8, 16, ops.clone()).is_none());
    assert_eq!(
        ffi::fake::last_error(),
        ffi::AWS_ERROR_S3_PART_SIZE_EXCEEDS_MEMORY_LIMIT
    );
    assert_eq!(ops.calls.load(Ordering::Acquire), 0);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
}

#[test]
fn factory_accepts_part_size_equal_to_budget() {
    let pool = TestPool::new(&[0], 16, 16);
    let future = pool.reserve(16, false);
    assert!(future.done());
    assert_eq!(future.take().unwrap().capacity(), 16);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Asserts every step of one ownership transition sequence in one test"
)]
fn mapping_pending_and_ticket_failures_preserve_pool() {
    let pool = TestPool::new(&[0], 16, 8);
    pool.ops.fail_mmap.store(true, Ordering::Release);
    let failure = pool.reserve(8, false);
    assert!(failure.done());
    assert_eq!(
        failure.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.accounting(), (0, 0, 0));
    {
        let state = pool.pool().state.lock();
        for cell in state.shards[0].slots.as_ref().unwrap().iter() {
            // SAFETY: slot inspection holds the exclusive pool lock.
            let slot = unsafe { &*cell.get() };
            assert!(slot.state == BufferState::Empty);
            assert!(slot.mapping.is_none());
        }
    }
    pool.ops.fail_mmap.store(false, Ordering::Release);
    pool.seed_idle(0, 8);
    for offset in [1, 2] {
        pool.ops.fail_at.store(
            pool.ops.calls.load(Ordering::Acquire) + offset,
            Ordering::Release,
        );
        let future = pool.reserve(8, false);
        assert!(future.done());
        assert_eq!(future.take().unwrap_err(), ffi::AWS_ERROR_OOM);
        assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
        assert_eq!(pool.accounting(), (8, 0, 0));
        assert_eq!(pool.pool().refs.load(Ordering::Acquire), 1);
    }
    let ops = pool.ops.clone();
    drop(pool);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Asserts every step of one ownership transition sequence in one test"
)]
fn pool_and_ticket_reference_counts_preserve_ownership() {
    let pool = TestPool::new(&[0], 16, 8);
    assert_eq!(pool.pool().refs.load(Ordering::Acquire), 1);
    // SAFETY: the fixture owns a live pool; the extra reference is immediately balanced.
    unsafe {
        assert_eq!(pool_acquire(pool.interface()), pool.interface());
        assert_eq!(pool.pool().refs.load(Ordering::Acquire), 2);
        pool_release(pool.interface());
    }
    assert_eq!(pool.pool().refs.load(Ordering::Acquire), 1);
    let ticket = pool.reserve(8, false).take().unwrap();
    let raw = ticket_from_interface(ticket.0).unwrap();
    assert_eq!(pool.pool().refs.load(Ordering::Acquire), 2);
    // SAFETY: the live ticket wrapper retains the inspected pinned object.
    assert_eq!(unsafe { (*raw).refs.load(Ordering::Acquire) }, 1);
    let extra = ticket.acquire();
    assert_eq!(extra.0, ticket.0);
    // SAFETY: both wrappers retain the inspected pinned object.
    assert_eq!(unsafe { (*raw).refs.load(Ordering::Acquire) }, 2);
    drop(extra);
    // SAFETY: the first wrapper still retains the inspected pinned object.
    assert_eq!(unsafe { (*raw).refs.load(Ordering::Acquire) }, 1);
    assert_eq!(pool.pool().refs.load(Ordering::Acquire), 2);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::InUse);
    drop(ticket);
    assert_eq!(pool.pool().refs.load(Ordering::Acquire), 1);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
    let ops = pool.ops.clone();
    drop(pool);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Asserts every step of one ownership transition sequence in one test"
)]
fn byte_budget_exact_fits_and_underflow_boundaries() {
    let pool = TestPool::new(&[0], 16, 8);
    assert!(!supported_size(pool.pool(), 0));
    assert!(supported_size(pool.pool(), 16));
    assert!(!supported_size(pool.pool(), 17));
    assert!(can_allocate(0, 0, 16, 16));
    assert!(!can_allocate(0, 0, 17, 16));
    let address = PoolAddress(pool.pointer);
    *pool.ops.on_map.lock().unwrap() = Some(Box::new(move || {
        let state = address.get().state.lock();
        assert_eq!(state.reserved_bytes, 16);
        assert!(!can_allocate(
            state.allocated_bytes,
            state.reserved_bytes,
            1,
            16
        ));
    }));
    pool.ops.fail_mmap.store(true, Ordering::Release);
    assert!(pool.reserve(16, false).take().is_err());
    assert_eq!(pool.accounting(), (0, 0, 0));
    assert!(can_allocate(15, 0, 1, 16));
    assert!(!can_allocate(15, 0, 2, 16));
    assert!(!can_allocate(17, 0, 1, 16));
    assert!(!can_allocate(8, 16, 1, 16));
}

#[test]
fn fallback_selection_is_fair_across_shards() {
    let pool = TestPool::new(&[0, 1, 2, 3], 8, 1);
    let mut state = pool.pool().state.lock();
    for index in 0..12 {
        assert_eq!(select_shard(&mut state, Some(1000)), index % 4);
    }
    for shard in state.shards.iter() {
        assert_eq!(shard.fallback_reserve_count, 3);
    }
    for _ in 0..5 {
        assert_eq!(select_shard(&mut state, Some(2)), 2);
    }
    assert_eq!(state.shards[2].current_node_hit_count, 5);
    assert_eq!(select_shard(&mut state, None), 0);
    assert_eq!(state.shards[0].fallback_reserve_count, 4);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "Asserts every step of one ownership transition sequence in one test"
)]
fn destroy_cancels_pending_once_preserving_prior_errors() {
    let pool = TestPool::new(&[0], 16, 8);
    let slots = pool.pool().state.lock().shards[0].slots.take();
    let canceled = pool.reserve(8, false);
    let already = pool.reserve(8, false);
    already.cancel(ffi::AWS_ERROR_S3_CANCELED);
    let failed = pool.reserve(8, false);
    failed.cancel(ffi::AWS_ERROR_OOM);
    pool.pool().state.lock().shards[0].slots = slots;
    {
        let state = pool.pool().state.lock();
        assert_eq!(state.reserve_count, 3);
        assert_eq!(state.shards[0].reserve_count, 3);
        assert_eq!(state.pending_reserve_count, 3);
        assert_eq!(state.shards[0].pending_reserve_count, 3);
    }
    assert!(!canceled.done());
    let ops = pool.ops.clone();
    drop(pool);
    assert!(canceled.done());
    assert!(already.done());
    assert!(failed.done());
    assert_eq!(canceled.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    assert_eq!(already.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    assert_eq!(failed.take().unwrap_err(), ffi::AWS_ERROR_OOM);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
}

#[test]
fn destroy_runs_every_backend_call_outside_the_probed_pool_lock() {
    let pool = TestPool::new(&[0], 16, 8);
    let ops = Arc::clone(&pool.ops);
    pool.seed_idle(0, 8);
    let first = pool.queued(8, 0, false);
    let second = pool.queued(8, 0, false);
    let address = PoolAddress(pool.pointer);
    let queued_at_cancel = Arc::new(AtomicUsize::new(usize::MAX));
    let observed = Arc::clone(&queued_at_cancel);
    *ops.on_complete.lock().unwrap() = Some(Box::new(move || {
        let state = address.get().state.lock();
        observed.store(state.pending_len, Ordering::Release);
    }));
    let probed = ops.probed.load(Ordering::Acquire);
    let released = ops.released.load(Ordering::Acquire);
    drop(pool);
    assert_eq!(queued_at_cancel.load(Ordering::Acquire), 0);
    assert_eq!(first.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    assert_eq!(second.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    let destruction_calls = 3 + ops.released.load(Ordering::Acquire) - released;
    assert_eq!(
        ops.probed.load(Ordering::Acquire) - probed,
        destruction_calls
    );
    assert!(ops.lock_probe.load(Ordering::Acquire).is_null());
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
    assert_eq!(ops.mappings.load(Ordering::Acquire), 0);
}

#[test]
fn trim_redrives_pending_allocation() {
    let pool = TestPool::new(&[0, 1], 16, 8);
    pool.seed_idle(1, 8);
    let pending = pool.queued(16, 0, false);
    pool.trim();
    assert!(slot_state(&pool.pool().state.lock(), 1, 0) == BufferState::Empty);
    assert!(pending.done());
    let ticket = pending.take().unwrap();
    assert_eq!(ticket.node(), 0);
    assert_eq!(ticket.capacity(), 16);
    drop(ticket);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
}

#[test]
fn reserves_dynamic_buffer_above_initial_part_size() {
    let pool = TestPool::new(&[0], 128, 8);
    // SAFETY: the fixture retains the pool interface through this pure size callback.
    let requested = unsafe { pool_derive_aligned_buffer_size(pool.interface(), 28) } as usize;
    let future = pool.reserve(requested, false);
    assert!(future.done());
    let ticket = future.take().unwrap();
    assert_eq!(ticket.capacity(), requested);
}

fn lend_idle(pool: &TestPool, shard: usize, size: usize) -> *mut Buffer {
    let mut state = pool.pool().state.lock();
    let slot = idle_for(pool.pool(), &mut state, shard, size).unwrap();
    // SAFETY: the fixture marks this idle slot under the exclusive lock.
    unsafe {
        (*slot).state = BufferState::InUse;
    }
    slot
}

fn slot_state(state: &State, shard: usize, index: usize) -> BufferState {
    // SAFETY: every caller holds the exclusive pool state lock throughout this read.
    unsafe { (*state.shards[shard].slots.as_ref().unwrap()[index].get()).state }
}

#[test]
fn receive_mappings_offer_huge_pages_outside_the_pool_lock_without_affecting_ownership() {
    let pool = TestPool::new(&[0], 128, 64);
    let ops = Arc::clone(&pool.ops);
    let ticket = pool.reserve(64, false).take().unwrap();
    assert_eq!(ops.huge_page_hints.load(Ordering::Acquire), 1);
    drop(ticket);
    let reused = pool.reserve(64, false).take().unwrap();
    assert_eq!(ops.huge_page_hints.load(Ordering::Acquire), 1);
    drop(reused);
    pool.trim();
    assert_eq!(ops.mappings.load(Ordering::Acquire), 0);
    drop(pool);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
}

struct ChurnMapper {
    pool: PoolAddress,
    churn: Arc<AtomicUsize>,
    calls: Arc<AtomicUsize>,
    waiter: Arc<std::sync::Mutex<Option<FutureAddress>>>,
}

impl ChurnMapper {
    fn install(pool: &TestPool, churn: usize) -> Self {
        let mapper = Self {
            pool: PoolAddress(pool.pointer),
            churn: Arc::new(AtomicUsize::new(churn)),
            calls: Arc::default(),
            waiter: Arc::default(),
        };
        let hook = Self {
            pool: PoolAddress(pool.pointer),
            churn: Arc::clone(&mapper.churn),
            calls: Arc::clone(&mapper.calls),
            waiter: Arc::clone(&mapper.waiter),
        };
        *pool.ops.map_hook.lock().unwrap() = Some(Box::new(move || hook.map()));
        mapper
    }

    fn map(&self) -> bool {
        let call = self.calls.fetch_add(1, Ordering::AcqRel) + 1;
        if call > self.churn.load(Ordering::Acquire) {
            return true;
        }
        let interface = (&raw const self.pool.get().interface).cast_mut();
        // SAFETY: the test retains its pool for as long as the hook is installed.
        let future = unsafe {
            pool_reserve(
                interface,
                ffi::AwsS3BufferPoolReserveMeta {
                    size: 8,
                    can_block: false,
                    local_offset: 0,
                    client: ptr::null_mut(),
                    meta_request: ptr::null_mut(),
                },
            )
        };
        let previous = self.waiter.lock().unwrap().replace(FutureAddress(future));
        if let Some(previous) = previous {
            drop(Future(previous.0));
        }
        false
    }

    fn calls(&self) -> usize {
        self.calls.load(Ordering::Acquire)
    }

    fn take_waiter(&self) -> Future {
        Future(self.waiter.lock().unwrap().take().unwrap().0)
    }
}

#[test]
#[cfg_attr(miri, ignore = "drives tens of thousands of fake reservations")]
fn drive_past_handoff_continues_until_a_redrive_is_certain() {
    let pool = TestPool::new(&[0], 8, 8);
    let mapper = ChurnMapper::install(&pool, PENDING_DRIVE_STEPS_HANDOFF);
    let first = pool.queued(8, 0, false);
    pool.complete_any_pending();
    assert_eq!(mapper.calls(), PENDING_DRIVE_STEPS_HANDOFF + 1);
    assert_eq!(
        first.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.queue_len(), 0);
    let waiter = mapper.take_waiter();
    assert!(waiter.done());
    drop(waiter.take().unwrap());
    *pool.ops.map_hook.lock().unwrap() = None;
}

#[test]
#[cfg_attr(miri, ignore = "drives tens of thousands of fake reservations")]
fn drive_hands_off_at_its_handoff_step_while_a_ticket_is_held() {
    let pool = TestPool::new(&[0], 16, 8);
    let mapper = ChurnMapper::install(&pool, 0);
    let held = pool.reserve(8, false).take().unwrap();
    mapper.churn.store(
        mapper.calls() + PENDING_DRIVE_STEPS_HANDOFF,
        Ordering::Release,
    );
    let first = pool.queued(8, 0, false);
    pool.complete_any_pending();
    assert_eq!(mapper.calls(), mapper.churn.load(Ordering::Acquire));
    assert_eq!(
        first.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    let waiter = mapper.take_waiter();
    assert_eq!(pool.queue_len(), 1);
    assert!(!waiter.done());
    drop(held);
    assert_eq!(pool.queue_len(), 0);
    assert!(waiter.done());
    drop(waiter.take().unwrap());
    *pool.ops.map_hook.lock().unwrap() = None;
}

#[test]
#[cfg_attr(miri, ignore = "drives tens of thousands of fake reservations")]
fn exhausted_drive_fails_the_queue_without_a_certain_redrive() {
    let pool = TestPool::new(&[0], 8, 8);
    let mapper = ChurnMapper::install(&pool, PENDING_DRIVE_STEPS_MAX);
    let first = pool.queued(8, 0, false);
    pool.complete_any_pending();
    assert_eq!(mapper.calls(), PENDING_DRIVE_STEPS_MAX);
    assert_eq!(
        first.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.queue_len(), 0);
    assert_eq!(pool.pool().state.lock().pending_len, 0);
    let waiter = mapper.take_waiter();
    assert_eq!(
        waiter.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.accounting(), (0, 0, 0));
    *pool.ops.map_hook.lock().unwrap() = None;
}

#[test]
fn full_pending_queue_fails_a_new_reservation() {
    let pool = TestPool::new(&[0], 8, 8);
    let held = pool.reserve(8, false).take().unwrap();
    let older = pool.queued(16, 0, false);
    let queued_before = pool.pool().state.lock().pending_reserve_count;
    pool.pool().state.lock().pending_len = PENDING_RESERVES_MAX;
    let future = pool.reserve(8, false);
    assert!(future.done());
    assert_eq!(
        future.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    {
        let state = pool.pool().state.lock();
        assert_eq!(state.pending_tail, state.pending_head);
        assert_eq!(state.pending_reserve_count, queued_before);
    }
    pool.pool().state.lock().pending_len = 1;
    assert!(!older.done());
    drop(held);
    let ops = Arc::clone(&pool.ops);
    drop(pool);
    assert_eq!(older.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    assert_eq!(ops.live.load(Ordering::Acquire), 0);
}

#[test]
fn source_pool_bounds_match_the_crt_ceilings() {
    assert_eq!(PENDING_RESERVES_MAX, 40_000);
    assert_eq!(RESERVE_PASSES_MAX, SOURCE_POOL_BUFFERS_MAX + 1);
    assert_eq!(PENDING_DRIVE_STEPS_HANDOFF, 84_097);
    assert_eq!(PENDING_DRIVE_STEPS_MAX, 168_194);
}

const MIB: usize = 1024 * 1024;
const GIB: usize = 1024 * MIB;

fn pool_config(part_size: usize, max_part_size: usize) -> ffi::AwsS3BufferPoolConfig {
    ffi::AwsS3BufferPoolConfig {
        client: ptr::null_mut(),
        part_size,
        max_part_size,
        memory_limit: 0,
    }
}

#[test]
fn sizing_uses_override_then_crt_limit_then_the_default_budget() {
    assert_eq!(effective_budget_bytes(7 * GIB, 24 * GIB), 7 * GIB);
    assert_eq!(effective_budget_bytes(0, 24 * GIB), 24 * GIB);
    assert_eq!(
        effective_budget_bytes(0, 0),
        SOURCE_POOL_BUDGET_BYTES_DEFAULT
    );
}

#[test]
fn sizing_counts_slots_by_budget_with_a_per_node_floor_and_a_cap() {
    assert_eq!(total_source_buffer_count(24 * GIB, 8 * MIB, 1), 3072);
    assert_eq!(
        total_source_buffer_count(64 * GIB, 8 * MIB, 1),
        SOURCE_POOL_BUFFERS_MAX
    );
    assert_eq!(total_source_buffer_count(8 * MIB, 8 * MIB, 4), 8);
}

#[test]
fn sizing_bounds_the_max_buffer_by_budget_and_part_size() {
    assert_eq!(
        effective_max_buffer_size(pool_config(8 * MIB, 0), 2 * GIB),
        2 * GIB
    );
    assert_eq!(
        effective_max_buffer_size(pool_config(8 * MIB, 32 * MIB), 2 * GIB),
        32 * MIB
    );
    assert_eq!(
        effective_max_buffer_size(pool_config(8 * MIB, 4 * MIB), 2 * GIB),
        8 * MIB
    );
    assert_eq!(
        effective_max_buffer_size(pool_config(16 * MIB, 32 * MIB), 8 * MIB),
        8 * MIB
    );
}

fn reserve_meta(size: usize) -> ffi::AwsS3BufferPoolReserveMeta {
    ffi::AwsS3BufferPoolReserveMeta {
        size,
        can_block: false,
        local_offset: 0,
        client: ptr::null_mut(),
        meta_request: ptr::null_mut(),
    }
}

fn new_future(pool: &TestPool) -> Future {
    // SAFETY: the test allocator is opaque to the fake future implementation.
    Future(unsafe { ffi::fake::FakeFutures.new_future(pool.pool().allocator) })
}

#[test]
fn reserve_ticket_failure_funds_waiter_from_the_failed_shard() {
    let pool = TestPool::new(&[0, 1], 16, 8);
    let held = pool.reserve(8, false).take().unwrap();
    let pointer = pool.seed_idle(1, 8);
    let action = {
        let mut state = pool.pool().state.lock();
        reserve_deliver(idle_for(pool.pool(), &mut state, 1, 8).unwrap())
    };
    let waiter = pool.queued(8, 0, false);
    pool.ops.fail_at.store(
        pool.ops.calls.load(Ordering::Acquire) + 1,
        Ordering::Release,
    );
    let failed = new_future(&pool);
    let returned = finish_reserve_action(pool.pointer, failed.0, reserve_meta(8), action);
    assert_eq!(returned, Some(failed.0));
    assert_eq!(failed.take().unwrap_err(), ffi::AWS_ERROR_OOM);
    assert_eq!(pool.queue_len(), 0);
    let ticket = waiter.take().unwrap();
    assert_eq!(ticket.node(), 1);
    assert_eq!(ticket.buffer(), pointer);
    assert_eq!(pool.pool().diagnostics.trims.load(Ordering::Acquire), 0);
    assert_eq!(pool.pool().state.lock().cross_shard_steal_count, 1);
    drop((ticket, held));
}

#[test]
fn reserve_mapping_failure_funds_waiter_from_the_failed_shard() {
    let pool = TestPool::new(&[0, 1], 24, 8);
    let pointer = pool.seed_idle(1, 8);
    let TakeBufferAction::Allocate {
        slot,
        size,
        node,
        node_index,
    } = take_buffer_or_claim_locked(pool.pool(), &mut pool.pool().state.lock(), 1, 16)
    else {
        panic!("expected an allocation claim on shard 1");
    };
    let waiter = pool.queued(8, 0, false);
    pool.ops.fail_mmap.store(true, Ordering::Release);
    let failed = new_future(&pool);
    let action = ReserveAction::Allocate {
        slot,
        size,
        node,
        node_index,
    };
    let returned = finish_reserve_action(pool.pointer, failed.0, reserve_meta(16), action);
    assert_eq!(returned, Some(failed.0));
    assert_eq!(
        failed.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert_eq!(pool.queue_len(), 0);
    let ticket = waiter.take().unwrap();
    assert_eq!(ticket.node(), 1);
    assert_eq!(ticket.buffer(), pointer);
    assert_eq!(pool.accounting(), (8, 0, 0));
}

#[test]
fn reserve_queued_on_an_empty_queue_does_not_drive() {
    let pool = TestPool::new(&[0], 8, 8);
    let held = pool.reserve(8, false).take().unwrap();
    let before = ffi::fake::is_done_calls();
    let waiting = pool.reserve(8, false);
    assert_eq!(ffi::fake::is_done_calls(), before);
    assert_eq!(pool.queue_len(), 1);
    let behind = pool.reserve(8, false);
    assert!(ffi::fake::is_done_calls() > before);
    assert_eq!(pool.queue_len(), 2);
    assert!(!waiting.done());
    drop(held);
    assert!(waiting.done());
    assert!(!behind.done());
    drop(waiting.take().unwrap());
    assert!(behind.done());
}

#[test]
fn single_shard_reservations_skip_the_current_node_lookup() {
    for (nodes, lookups) in [(&[0][..], 0), (&[0, 1][..], 3)] {
        let pool = TestPool::new(nodes, 64, 8);
        let tickets: Vec<_> = (0..3)
            .map(|_| pool.reserve(8, false).take().unwrap())
            .collect();
        assert_eq!(pool.ops.current_node_calls.load(Ordering::Acquire), lookups);
        drop(tickets);
    }
}

#[test]
fn null_pool_interface_raises_invalid_argument() {
    // SAFETY: an all-zero interface is a valid C value with a null implementation.
    let mut interface: ffi::AwsS3BufferPool = unsafe { std::mem::zeroed() };
    interface.vtable = ptr::from_ref(&FAKE_POOL_VTABLE)
        .cast::<ffi::AwsS3BufferPoolVtable>()
        .cast_mut();
    ffi::fake::FakeFutures.raise_error(0);
    // SAFETY: each callback only reads the null implementation and the
    // vtable, and sets the thread-local error.
    unsafe {
        assert!(pool_reserve(&mut interface, reserve_meta(8)).is_null());
    }
    assert_eq!(ffi::fake::last_error(), ffi::AWS_ERROR_INVALID_ARGUMENT);
    ffi::fake::FakeFutures.raise_error(0);
    // SAFETY: as above.
    unsafe {
        assert_eq!(pool_add_special_size(&mut interface, 8), -1);
    }
    assert_eq!(ffi::fake::last_error(), ffi::AWS_ERROR_INVALID_ARGUMENT);
}

#[test]
fn ticket_node_reports_no_node_for_null_or_foreign_tickets() {
    static FOREIGN_VTABLE: ffi::AwsS3BufferTicketVtable = ffi::AwsS3BufferTicketVtable {
        claim: None,
        acquire: None,
        release: None,
    };
    // SAFETY: a null interface is rejected before any read.
    assert_eq!(unsafe { ticket_node(ptr::null_mut()) }, None);
    // SAFETY: an all-zero ticket is a valid C value with a null vtable.
    let mut zeroed: ffi::AwsS3BufferTicket = unsafe { std::mem::zeroed() };
    // SAFETY: the ticket is live for the call, which reads only its vtable.
    assert_eq!(unsafe { ticket_node(&raw mut zeroed) }, None);
    // SAFETY: an all-zero ticket is a valid C value; only its vtable is set.
    let mut foreign: ffi::AwsS3BufferTicket = unsafe { std::mem::zeroed() };
    foreign.vtable = (&raw const FOREIGN_VTABLE).cast_mut();
    // SAFETY: the ticket is live for the call, which reads only its vtable.
    assert_eq!(unsafe { ticket_node(&raw mut foreign) }, None);
}

#[test]
fn failed_mapping_raises_buffer_allocation_failed() {
    let pool = TestPool::new(&[0], 16, 8);
    for (mmap, mbind) in [(true, false), (false, true)] {
        ffi::fake::FakeFutures.raise_error(0);
        pool.ops.fail_mmap.store(mmap, Ordering::Release);
        pool.ops.fail_mbind.store(mbind, Ordering::Release);
        let future = pool.reserve(8, false);
        assert_eq!(
            future.take().unwrap_err(),
            ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
        );
        assert_eq!(
            ffi::fake::last_error(),
            ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
        );
    }
    assert_eq!(pool.ops.mappings.load(Ordering::Acquire), 0);
}

#[test]
fn cancelled_waiter_ticket_is_released_after_the_drive() {
    let pool = TestPool::new(&[0], 16, 8);
    let idle = pool.seed_idle(0, 8);
    let first = pool.queued(8, 0, false);
    let second = pool.queued(8, 0, false);
    let future = FutureAddress(first.0);
    *pool.ops.on_complete.lock().unwrap() = Some(Box::new(move || {
        future.cancel(ffi::AWS_ERROR_S3_CANCELED);
    }));
    pool.complete_any_pending();
    assert_eq!(pool.queue_len(), 0);
    assert_eq!(first.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    let ticket = second.take().unwrap();
    assert_ne!(ticket.buffer(), idle);
    assert_eq!(pool.ops.mappings.load(Ordering::Acquire), 2);
    assert!(slot_state(&pool.pool().state.lock(), 0, 0) == BufferState::Idle);
}

#[test]
fn drive_sweeps_done_heads_in_one_step() {
    let pool = TestPool::new(&[0], 8, 8);
    let pointer = pool.seed_idle(0, 8);
    let dead: Vec<_> = (0..3).map(|_| pool.queued(8, 0, false)).collect();
    for future in &dead {
        future.cancel(ffi::AWS_ERROR_S3_CANCELED);
    }
    let waiter = pool.queued(8, 0, false);
    let released = pool.ops.released.load(Ordering::Acquire);
    let mut completions = PendingCompletionBatch::new();
    let action = serve_pending_head_locked(
        pool.pool(),
        &mut pool.pool().state.lock(),
        None,
        &mut completions,
    );
    let PendingAction::Deliver { pending, slot } = action else {
        panic!("the first drive step should fund the live waiter");
    };
    // SAFETY: the detached node is exclusively owned by this action.
    assert_eq!(unsafe { (*pending).future }, waiter.0);
    assert_eq!(slot_pointer(slot), pointer);
    assert_eq!(pool.queue_len(), 0);
    assert!(!completions.is_empty());
    assert_eq!(pool.ops.released.load(Ordering::Acquire), released);
    assert!(fulfill_pending(pool.pointer, pending, slot, &mut completions).is_none());
    drain_swept(&pool, completions, released, &dead);
    assert_eq!(waiter.take().unwrap().buffer(), pointer);
}

fn drain_swept(
    pool: &TestPool,
    mut completions: PendingCompletionBatch,
    released: usize,
    dead: &[Future],
) {
    completions.drain(pool.pool());
    assert_eq!(
        pool.ops.released.load(Ordering::Acquire),
        released + dead.len() + 1
    );
    for future in dead {
        assert_eq!(future.take().unwrap_err(), ffi::AWS_ERROR_S3_CANCELED);
    }
}

const RELEASE_TRIM_ROUNDS: usize = if cfg!(miri) { 2 } else { 2000 };

#[test]
fn a_released_buffer_reaches_the_waiter_before_a_concurrent_trim() {
    for _ in 0..RELEASE_TRIM_ROUNDS {
        let pool = TestPool::new(&[0], 8, 8);
        pool.ops
            .lock_probe
            .store(ptr::null_mut(), Ordering::Release);
        let held = pool.reserve(8, false).take().unwrap();
        let waiter = pool.reserve(8, false);
        assert!(!waiter.done());
        pool.ops.fail_mmap.store(true, Ordering::Release);
        let released = AtomicBool::new(false);
        let start = std::sync::Barrier::new(2);
        std::thread::scope(|scope| {
            let address = PoolAddress(pool.pointer);
            let (released, start) = (&released, &start);
            scope.spawn(move || {
                start.wait();
                while !released.load(Ordering::Acquire) {
                    let interface = (&raw const address.get().interface).cast_mut();
                    // SAFETY: the scoped parent retains its pool reference until this thread joins.
                    unsafe { pool_trim(interface) };
                }
            });
            start.wait();
            drop(held);
            released.store(true, Ordering::Release);
        });
        waiter.take().unwrap();
    }
}

fn race_a_waiter_behind_a_paused_mapping(
    pool: &TestPool,
    while_paused: impl FnOnce(),
) -> (Future, Future) {
    let mapping = Arc::new(std::sync::Barrier::new(2));
    let resume = Arc::new(std::sync::Barrier::new(2));
    let (mapped, resumed) = (Arc::clone(&mapping), Arc::clone(&resume));
    *pool.ops.on_map.lock().unwrap() = Some(Box::new(move || {
        mapped.wait();
        resumed.wait();
    }));
    std::thread::scope(|scope| {
        let address = PoolAddress(pool.pointer);
        let claimant = scope.spawn(move || {
            let interface = (&raw const address.get().interface).cast_mut();
            // SAFETY: the scoped parent retains its pool reference until this thread joins.
            FutureAddress(unsafe { pool_reserve(interface, reserve_meta(8)) })
        });
        mapping.wait();
        let waiter = pool.reserve(8, false);
        assert_eq!(pool.queue_len(), 1);
        assert!(!waiter.done());
        while_paused();
        resume.wait();
        (Future(claimant.join().unwrap().0), waiter)
    })
}

#[test]
fn a_failed_mapping_funds_the_waiter_queued_behind_it() {
    let pool = TestPool::new(&[0], 8, 8);
    let mut failed = false;
    *pool.ops.map_hook.lock().unwrap() =
        Some(Box::new(move || std::mem::replace(&mut failed, true)));
    let (claimant, waiter) = race_a_waiter_behind_a_paused_mapping(&pool, || {});
    assert_eq!(
        claimant.take().unwrap_err(),
        ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED
    );
    assert!(waiter.done());
    assert_eq!(pool.queue_len(), 0);
    drop(waiter.take().unwrap());
    assert_eq!(pool.accounting(), (8, 0, 0));
}

#[test]
fn a_failed_ticket_after_mapping_funds_the_waiter_queued_behind_it() {
    let pool = TestPool::new(&[0], 8, 8);
    let ops = Arc::clone(&pool.ops);
    let (claimant, waiter) = race_a_waiter_behind_a_paused_mapping(&pool, || {
        ops.fail_at
            .store(ops.calls.load(Ordering::Acquire) + 1, Ordering::Release);
    });
    assert_eq!(claimant.take().unwrap_err(), ffi::AWS_ERROR_OOM);
    assert!(waiter.done());
    assert_eq!(pool.queue_len(), 0);
    drop(waiter.take().unwrap());
    assert_eq!(pool.accounting(), (8, 0, 0));
}
