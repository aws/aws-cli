use super::*;
use crate::testing::{Script, replay_target, sweep};

/// A submission with the shape flags it draws: rejected, then (if not)
/// finished inside the runtime call, then (before Ctrl-C) whether Ctrl-C
/// lands inside the runtime call.
fn submit(script: Script, shape: &[bool]) -> Script {
    shape
        .iter()
        .fold(script.index(4, 0), |script, flag| script.flag(*flag))
}
/// Finishes request `index` with the outcome at `outcome` in
/// [`FinishOutcome::ALL`].
fn finish(script: Script, index: usize, outcome: usize) -> Script {
    script
        .index(4, 1)
        .index(REQUEST_COUNT_MAX, index)
        .index(FinishOutcome::ALL.len(), outcome)
}
fn shutdown(script: Script, index: usize) -> Script {
    script.index(4, 2).index(REQUEST_COUNT_MAX, index)
}
fn mixed_submissions() -> Script {
    let script = submit(Script::new().flag(false), &[false, false, false]);
    let script = submit(script, &[false, true, false]);
    let script = submit(script, &[true, false]);
    let script = submit(script, &[false, false, true]);
    let script = finish(finish(script, 0, 2), 3, 0);
    submit(shutdown(script, 0), &[false, false])
}
#[test]
fn named_mixed_submission_script_replays() {
    mixed_submissions().replay(|input| {
        assert_eq!(
            replay(input),
            ExpectedCounts {
                succeeded: 2,
                failed: 1,
                canceled: 1,
                destroyed: 4,
                deleted: 2,
                in_flight: 0,
            }
        );
    });
    assert_eq!(
        replay(&mut Choices::new(&[])),
        ExpectedCounts {
            succeeded: REQUEST_COUNT_MAX as u64,
            destroyed: REQUEST_COUNT_MAX as u64,
            ..ExpectedCounts::default()
        }
    );
}
#[test]
fn request_phases_replay_their_scripts_and_a_seeded_sweep() {
    replay_target(
        "scheduler_phases",
        &[("mixed_submissions", mixed_submissions())],
        |input| {
            replay(input);
        },
    );
    sweep(128, ownership);
}
