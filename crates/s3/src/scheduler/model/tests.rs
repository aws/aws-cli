use super::*;
use crate::testing::{Script, replay_target, sweep};

/// The direction: a download, whose finish work runs on the pool, or an
/// upload.
fn trace(pooled: bool) -> Script {
    Script::new().flag(pooled)
}
/// Submits the next entry, named for its step; an entry whose name ends in
/// `1` finishes inside the runtime call.
fn submit(script: Script) -> Script {
    script.index(5, 0)
}
/// Finishes the request at `request` modulo those submitted, unless it has
/// finished.
fn finish(script: Script, request: usize, fail: bool) -> Script {
    script
        .index(5, 1)
        .index(REQUEST_INDEX_COUNT, request)
        .flag(fail)
}
fn cancel(script: Script) -> Script {
    script.index(5, 3)
}
/// Shuts down the pending shutdown at `request` modulo those pending.
fn shutdown(script: Script, request: usize) -> Script {
    script.index(5, 4).index(REQUEST_INDEX_COUNT, request)
}

/// Two uploads, the second finished inside the runtime call, then a finish
/// of the request that already finished.
fn inline_adoption() -> Script {
    finish(submit(submit(trace(false))), 1, false)
}
/// Three uploads, a cancel, a failed finish and a second cancel.
fn interrupt() -> Script {
    let script = cancel(submit(submit(submit(trace(false)))));
    cancel(finish(script, 17, true))
}
/// A download trace, with its finish work on the pool: a finish before any
/// submission, two submissions (the first finished inside the runtime call),
/// two failed finishes and two cancels.
fn pooled() -> Script {
    let script = submit(submit(finish(trace(true), 1, false)));
    cancel(cancel(finish(finish(script, 16, true), 17, true)))
}
/// 128 upload steps whose kinds cycle through submit, two finishes, cancel
/// and shutdown, each naming the request of its step number.
fn out_of_order() -> Script {
    (0..REQUEST_INDEX_COUNT).fold(trace(false), |script, step| match step % 5 {
        0 => submit(script),
        1 | 2 => finish(script, step, step & 16 != 0),
        3 => cancel(script),
        _ => shutdown(script, step),
    })
}
#[test]
fn ownership_traces_replay_their_scripts_and_a_seeded_sweep() {
    ownership(&[]);
    replay_target(
        "scheduler_orderings",
        &[
            ("inline_adoption", inline_adoption()),
            ("interrupt", interrupt()),
            ("pooled", pooled()),
            ("out_of_order", out_of_order()),
        ],
        ownership_from,
    );
    for script in [
        finish(submit(trace(false)), 1, false),
        finish(
            finish(submit(submit(submit(trace(false)))), 1, false),
            2,
            false,
        ),
        cancel(finish(cancel(submit(submit(trace(false)))), 17, true)),
    ] {
        script.replay(ownership_from);
    }
    sweep(256, ownership);
}
