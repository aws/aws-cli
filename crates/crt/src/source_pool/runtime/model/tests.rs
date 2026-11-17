use super::*;
use crate::testing::{Script, replay_target, sweep};

/// A claim of `size` bytes on `shard`'s first free slot.
fn claim(script: Script, shard: usize, size: usize) -> Script {
    script.index(3, shard).flag(false).range(1, 33, size)
}
/// An abort of whatever claim holds `slot` on `shard`.
fn abort(script: Script, shard: usize, slot: usize) -> Script {
    script.index(3, shard).flag(true).index(4, slot)
}
/// Claims and aborts on all three shards: the 32-byte budget refuses a claim
/// one byte over it and another larger than it, a full shard refuses a claim
/// the budget would fund, freed slots are claimed again, and the last claim
/// fits the budget exactly.
fn interleaved_claims() -> Script {
    let script = claim(Script::new(), 0, 31);
    let script = claim(script, 1, 1);
    let script = claim(script, 2, 1);
    let script = abort(script, 0, 0);
    let script = claim(script, 2, 4);
    let script = claim(script, 1, 8);
    let script = claim(script, 2, 16);
    let script = abort(script, 1, 0);
    let script = claim(script, 0, 33);
    let script = claim(script, 1, 1);
    let script = claim(script, 2, 1);
    let script = claim(script, 2, 1);
    let script = claim(script, 2, 1);
    let script = claim(script, 0, 1);
    let script = abort(script, 2, 3);
    abort(script, 1, 3)
}
#[test]
fn reservation_claims_replay_their_scripts_and_a_seeded_sweep() {
    reservations(&[]);
    replay_target(
        "pool_reservations",
        &[("interleaved_claims", interleaved_claims())],
        reservations_from,
    );
    sweep(384, reservations);
}

/// The full-width budget checks: an exact fit and one byte over at small
/// sizes and at the top of the range, and reserved bytes that overflow a
/// usize sum.
#[test]
fn byte_budget_replays_full_width_boundaries_and_a_seeded_sweep() {
    let maximum = usize::MAX;
    for words in [
        [32, 7, 11, 14],
        [32, 7, 11, 15],
        [maximum, maximum, 1, 0],
        [maximum, maximum - 8, 3, 5],
        [maximum, maximum - 8, 3, 6],
    ] {
        let script = words
            .into_iter()
            .fold(Script::new(), |script, word| script.range(0, maximum, word));
        script.replay(byte_budget_from);
    }
    sweep(32, byte_budget);
}

/// Four requests of 1 through 4 bytes; the second is canceled with
/// `AWS_ERROR_S3_CANCELED`. The first ticket takes two extra references, and
/// its release fails the third request's ticket allocation, so the fourth
/// receives the buffer.
fn cancel_fail_fifo() -> Script {
    Script::new()
        .range(2, 9, 4)
        .range(1, 4096, 1)
        .range(1, 4096, 2)
        .range(1, 4096, 3)
        .range(1, 4096, 4)
        .flag(true)
        .flag(false)
        .flag(false)
        .flag(false)
        .range(1, 4, 2)
        .flag(true)
}
fn two_capacities() -> Script {
    Script::new()
        .range(2, 9, 2)
        .range(1, 4096, 100)
        .range(1, 4096, 3000)
}
#[test]
fn ticket_lifetimes_replay_their_scripts_and_a_seeded_sweep() {
    ownership(&[]);
    replay_target(
        "pool_ownership",
        &[
            ("cancel_fail_fifo", cancel_fail_fifo()),
            ("two_capacities", two_capacities()),
        ],
        ownership_from,
    );
    sweep(192, ownership);
}
#[test]
fn ticket_lifetime_request_sizes_span_one_page() {
    let script = [1, 100, 3000, 4096]
        .into_iter()
        .fold(Script::new(), |script, size| script.range(1, 4096, size));
    let mut input = Choices::new(script.encoded());
    let sizes: Vec<_> = (0..5).map(|_| ownership_request_size(&mut input)).collect();
    // Past the script, a size reads its minimum.
    assert_eq!(sizes, [1, 100, 3000, 4096, 1]);
}

#[test]
fn concurrent_reserve_release_cancel_and_trim() {
    let harness = Arc::new(Harness::new(vec![0, 1, 2, 3], 32, 8));
    let ops = Arc::clone(&harness.ops);
    std::thread::scope(|scope| {
        for worker in 0..4 {
            let harness = Arc::clone(&harness);
            scope.spawn(move || {
                for step in 0..128 {
                    let future = harness.reserve((worker + step) % 8 + 1, step % 3 == 0);
                    if !future.done() {
                        future.cancel(ffi::AWS_ERROR_S3_CANCELED);
                    }
                    if let Ok(ticket) = future.take() {
                        let retained = ticket.acquire();
                        drop(ticket);
                        assert!(retained.capacity() > 0);
                        drop(retained);
                    }
                    if step % 7 == 0 {
                        harness.trim();
                    }
                }
            });
        }
    });
    drop(harness);
    assert_eq!(ops.live.load(Ordering::SeqCst), 0);
    assert_eq!(ops.mappings.load(Ordering::SeqCst), 0);
}

#[test]
fn concurrent_fresh_claims_do_not_queue_behind_inflight_mapping() {
    let harness = Arc::new(Harness::new(vec![0], 16, 8));
    let entered = Arc::new(std::sync::Barrier::new(2));
    let resume = Arc::new(std::sync::Barrier::new(2));
    let entered_hook = Arc::clone(&entered);
    let resume_hook = Arc::clone(&resume);
    *harness.ops.on_map.lock().expect("model hook lock") = Some(Box::new(move || {
        entered_hook.wait();
        resume_hook.wait();
    }));
    std::thread::scope(|scope| {
        let first_pool = Arc::clone(&harness);
        scope.spawn(move || {
            let first = first_pool.reserve(8, false);
            assert!(first.done());
            drop(first.take().expect("first allocation grants a ticket"));
        });
        entered.wait();
        let second = harness.reserve(8, false);
        let ready = second.done();
        let snapshot = {
            let state = harness.pool().state.lock();
            (
                state.allocated_bytes,
                state.reserved_bytes,
                state.pending_head.is_null(),
            )
        };
        resume.wait();
        assert!(ready);
        assert_eq!(snapshot, (8, 8, true));
        drop(
            second
                .take()
                .expect("independent capacity funds the second reserve"),
        );
    });
}
