use super::*;
use crate::testing::{Script, replay_target, sweep};

/// Indices into the reservation sizes: `Model::edges`, then the derived size.
const ONE: usize = 0;
const BELOW_PART: usize = 1;
const PART: usize = 2;
const ABOVE_PART: usize = 3;
const MAXIMUM: usize = 4;
const ABOVE_MAXIMUM: usize = 5;
const DERIVED: usize = 6;
/// Indices into `FAILURES` and `PAGE_SIZES`.
const PENDING: usize = 0;
const TICKET: usize = 1;
const MAPPING: usize = 2;
const PLACEMENT: usize = 3;
const PAGE_ONE: usize = 0;
const PAGE_EIGHT: usize = 1;
const PAGE_LARGE: usize = 2;

/// A pool whose shards take the nodes `picks` names, each an index into
/// what `NODES` has left, and whose budget, part size and maximum part size
/// are in units, ending in a drain or, with `destroy`, a destroy.
fn config(picks: &[usize], units: [usize; 3], page: usize, destroy: bool) -> Script {
    let [budget, part, maximum] = units;
    let script = Script::new().range(1, 4, picks.len());
    let script = picks
        .iter()
        .enumerate()
        .fold(script, |script, (taken, pick)| {
            script.index(NODES.len() - taken, *pick)
        });
    script
        .range(1, UNITS_MAX, budget)
        .range(1, budget, part)
        .range(1, UNITS_MAX, maximum)
        .index(PAGE_SIZES.len(), page)
        .flag(destroy)
}
/// A reservation of one of the edge sizes with no current node.
fn reserve(script: Script, size: usize, can_block: bool) -> Script {
    script
        .index(7, RESERVE)
        .index(7, size)
        .flag(can_block)
        .index(3, 0)
}
/// A reservation from the node of shard `shard` of `shards`.
fn reserve_on(script: Script, size: usize, can_block: bool, [shard, shards]: [usize; 2]) -> Script {
    script
        .index(7, RESERVE)
        .index(7, size)
        .flag(can_block)
        .index(3, 1)
        .index(shards, shard)
}
/// Releases reference `index` of the `held` the model holds.
fn release(script: Script, [index, held]: [usize; 2]) -> Script {
    script.index(7, RELEASE).index(held, index)
}
fn arm(script: Script, failure: usize) -> Script {
    script.index(7, ARM).index(FAILURES.len() + 1, failure)
}
/// Arms a re-entry, the choice past the failures.
fn reenter(script: Script) -> Script {
    script
        .index(7, ARM)
        .index(FAILURES.len() + 1, FAILURES.len())
}
/// Passes the operation's first backend call and nests `operation` in its
/// second.
fn nest_in_second_call(script: Script, operation: usize) -> Script {
    let nested = NESTED.iter().position(|nested| *nested == operation);
    let nested = nested.expect("an operation that can nest");
    script.flag(false).flag(true).index(NESTED.len(), nested)
}
fn reached(script: &Script) -> Reached {
    let mut reached = None;
    script.replay(|input| reached = Some(operations_from(input)));
    reached.expect("the script ran")
}

/// A released buffer goes idle, and a smaller reservation reuses it.
fn idle_reuse() -> Script {
    let script = reserve(config(&[2], [2, 1, 2], PAGE_ONE, false), PART, false);
    let script = release(script, [0, 1]);
    reserve(script, ONE, false)
}
/// A maximum reservation retires the idle buffer to fund its mapping; a
/// waiter rounded up to the 8-byte page then takes the maximum buffer.
fn trim_to_fund() -> Script {
    let script = reserve(config(&[1], [2, 1, 2], PAGE_EIGHT, false), PART, false);
    let script = release(script, [0, 1]);
    let script = reserve(script, MAXIMUM, false);
    let script = reserve(script, ABOVE_PART, false);
    release(script, [0, 1])
}
/// Two shards on nodes 8 and 4 fill their slots; a release on the second
/// shard serves a waiter of the first, and a full first shard then takes
/// the second's idle buffer. The 4096-byte page exceeds the 1 KiB limit, so
/// sizes stay unrounded.
fn cross_shard_reuse() -> Script {
    let script = config(&[3, 0], [4, 1, 1], PAGE_LARGE, false);
    let script = [0, 0, 1, 1, 0].into_iter().fold(script, |script, shard| {
        reserve_on(script, PART, false, [shard, 2])
    });
    let script = release(script, [2, 4]);
    let script = release(script, [3, 4]);
    reserve_on(script, ONE, false, [0, 2])
}
/// A blocking reservation behind a waiter is forced onto the current
/// node's shard and released; a blocking one past the maximum fails.
fn forced_grant() -> Script {
    let script = reserve(config(&[1, 2], [1, 1, 1], PAGE_ONE, false), PART, false);
    let script = reserve(script, PART, false);
    let script = reserve_on(script, PART, true, [1, 2]);
    let script = reserve(script, ABOVE_MAXIMUM, true);
    let script = release(script, [1, 2]);
    release(script, [0, 1])
}
/// Each one-shot failure on the direct path: the mapping, its placement,
/// the ticket of a new mapping, which then goes idle, and the queue node.
/// Every mapping rounds up to the 4096-byte page, the whole budget.
fn direct_failures() -> Script {
    let script = config(&[4], [4, 1, 4], PAGE_LARGE, false);
    let script = [MAPPING, PLACEMENT, TICKET, PENDING]
        .into_iter()
        .fold(script, |script, failure| {
            reserve(arm(script, failure), PART, false)
        });
    reserve(script, ONE, false)
}
/// A waiter's mapping fails after a release retires the idle buffer to fund
/// it, and then a second waiter's placement does.
fn queued_failures() -> Script {
    let script = config(&[3], [2, 1, 2], PAGE_ONE, false);
    [MAPPING, PLACEMENT]
        .into_iter()
        .fold(script, |script, failure| {
            let script = reserve(reserve(script, PART, false), MAXIMUM, false);
            release(arm(script, failure), [0, 1])
        })
}
/// Two waiters, the younger canceled, a ticket copy, a special size and a
/// derived-size waiter; the destroy releases the pool first, so the waiters
/// are served by the ticket releases and the last one destroys the pool.
fn destroy_with_waiters() -> Script {
    let script = reserve(config(&[2], [1, 1, 1], PAGE_EIGHT, true), PART, false);
    let script = reserve(reserve(script, ONE, false), BELOW_PART, false);
    let script = script.index(7, CANCEL).index(2, 1).flag(false);
    let script = script.index(7, ACQUIRE).index(1, 0);
    let script = script.index(7, SPECIAL_SIZE).index(6, PART).flag(true);
    script
        .index(7, RESERVE)
        .index(7, DERIVED)
        .index(6, MAXIMUM)
        .flag(false)
        .index(3, 0)
}

/// The last of three tickets is released while the queue head maps the
/// buffer a trim of the first funded; its buffer idles until the head's
/// grant drives the queue again.
fn release_during_head_mapping() -> Script {
    let script = config(&[0], [3, 1, 2], PAGE_ONE, false);
    let script = reserve(reserve(script, PART, false), PART, false);
    let script = reenter(reserve(script, MAXIMUM, false));
    nest_in_second_call(release(script, [0, 2]), RELEASE).index(1, 0)
}
/// The queue head is canceled while its mapping is made, so the new buffer
/// goes idle.
fn cancel_during_head_mapping() -> Script {
    let script = config(&[0], [2, 1, 2], PAGE_ONE, false);
    let script = reenter(reserve(reserve(script, PART, false), MAXIMUM, false));
    let script = nest_in_second_call(release(script, [0, 1]), CANCEL);
    script.index(1, 0).flag(false)
}
/// A trim, and the drive it ends with, while a blocking reservation behind
/// a waiter maps its forced buffer.
fn trim_during_forced_mapping() -> Script {
    let script = config(&[0], [1, 1, 1], PAGE_ONE, false);
    let script = reenter(reserve(reserve(script, PART, false), PART, false));
    nest_in_second_call(reserve(script, PART, true), TRIM)
}
/// A reservation made as a release completes the waiter it funded, which
/// finds the queue it was detached from empty and waits.
fn reserve_in_completion() -> Script {
    let script = config(&[0], [1, 1, 1], PAGE_ONE, false);
    let script = reenter(reserve(reserve(script, PART, false), PART, false));
    let script = nest_in_second_call(release(script, [0, 1]), RESERVE);
    script.index(7, PART).flag(false).index(3, 0)
}

fn scripts() -> Vec<(&'static str, Script)> {
    let scripts = [
        ("idle_reuse", idle_reuse()),
        ("trim_to_fund", trim_to_fund()),
        ("cross_shard_reuse", cross_shard_reuse()),
        ("forced_grant", forced_grant()),
        ("direct_failures", direct_failures()),
        ("queued_failures", queued_failures()),
        ("destroy_with_waiters", destroy_with_waiters()),
    ];
    scripts.into_iter().chain(reentrant_scripts()).collect()
}
fn reentrant_scripts() -> [(&'static str, Script); 4] {
    [
        ("release_during_head_mapping", release_during_head_mapping()),
        ("cancel_during_head_mapping", cancel_during_head_mapping()),
        ("trim_during_forced_mapping", trim_during_forced_mapping()),
        ("reserve_in_completion", reserve_in_completion()),
    ]
}

#[test]
fn pool_operations_replay_their_scripts_and_a_seeded_sweep() {
    operations(&[]);
    replay_target("pool_operations", &scripts(), |input| {
        operations_from(input);
    });
    // Miri runs eight cases; shorter ones keep its run near its old length.
    sweep(if cfg!(miri) { 96 } else { 256 }, operations);
}

/// Each named script reaches the pool path it is named for.
#[test]
#[cfg_attr(miri, ignore = "the replay test runs the same scripts under Miri")]
fn named_operation_scripts_reach_their_paths() {
    let expected = [
        [0, 0, 0, 0, 1, 2, 0],
        [1, 0, 0, 1, 2, 3, 0],
        [0, 2, 0, 1, 4, 6, 0],
        [0, 1, 1, 1, 2, 3, 0],
        [0, 0, 0, 0, 1, 1, 4],
        [2, 0, 0, 0, 2, 2, 2],
        [0, 0, 0, 0, 1, 1, 0],
    ];
    for ((name, script), expected) in scripts().iter().zip(expected) {
        let reached = reached(script);
        let counts = [
            reached.trims,
            reached.steals,
            reached.forced,
            reached.queued,
            reached.mappings,
            reached.grants,
            reached.failures as u64,
        ];
        assert_eq!(counts, expected, "{name}");
    }
}

/// Each re-entrant script nests its operation in the backend call it is
/// named for, the first two while the queue head's mapping is in flight.
#[test]
#[cfg_attr(miri, ignore = "the replay test runs the same scripts under Miri")]
fn reentrant_scripts_nest_their_operations() {
    let nested = |call, operation, head_allocating| Nested {
        call,
        operation,
        head_allocating,
    };
    let expected = [
        nested(Call::Mmap, RELEASE, true),
        nested(Call::Mmap, CANCEL, true),
        nested(Call::Mmap, TRIM, false),
        nested(Call::Completion, RESERVE, false),
    ];
    for ((name, script), expected) in reentrant_scripts().iter().zip(expected) {
        assert_eq!(reached(script).nested, [expected], "{name}");
    }
}
