use super::*;
use crate::testing::{Script, replay_target, sweep};

/// Indices into `ROOTS`.
const DL: usize = 0;
const CURRENT: usize = 2;
const EMPTY_ROOT: usize = 3;
const PARENT_DL: usize = 4;
const ABSOLUTE: usize = 5;
/// Indices into `PIECES`.
const DOT: usize = 1;
const DOTS: usize = 2;
const A: usize = 3;
const BC: usize = 4;
const SLASH: usize = 5;
const BACKSLASH: usize = 6;
const DRIVE: usize = 7;

/// The key `pieces` spell under root `root`, each non-ASCII piece repeated
/// `repeats` times.
fn key(root: usize, pieces: &[usize], repeats: usize) -> Script {
    let script = Script::new()
        .index(ROOTS.len(), root)
        .range(0, PIECES_MAX, pieces.len());
    pieces.iter().fold(script, |script, &piece| {
        let script = script.index(PIECES.len(), piece);
        if piece == NON_ASCII {
            script.range(1, REPEATS_MAX, repeats)
        } else {
            script
        }
    })
}

fn scripts() -> [(&'static str, Script); 6] {
    [
        // `a/bc/` and a 300-byte name, which its temp name cuts.
        (
            "nested_long_name",
            key(DL, &[A, SLASH, BC, SLASH, NON_ASCII], REPEATS_MAX),
        ),
        // `a/../bc` under `../dl`, a root that starts above the current one.
        (
            "inner_parent",
            key(PARENT_DL, &[A, SLASH, DOTS, SLASH, BC], 1),
        ),
        // `..\a`, which escapes on Windows and is one name elsewhere.
        ("backslash_parent", key(DL, &[DOTS, BACKSLASH, A], 1)),
        // `C:/../..`: a drive prefix the parents cancel, naming `/srv`.
        (
            "drive_prefix",
            key(ABSOLUTE, &[DRIVE, SLASH, DOTS, SLASH, DOTS], 1),
        ),
        // `//a//./` under the empty root, which becomes `./`.
        (
            "empty_segments",
            key(EMPTY_ROOT, &[SLASH, SLASH, A, SLASH, SLASH, DOT, SLASH], 1),
        ),
        // `..` under `.`: the root's parent is itself `..`.
        ("root_parent", key(CURRENT, &[DOTS], 1)),
    ]
}

#[test]
fn path_containment_replays_its_scripts_and_a_seeded_sweep() {
    path_containment(&[]);
    replay_target("path_containment", &scripts(), |input| {
        path_containment_from(input);
    });
    sweep(64, path_containment);
}

/// Each named key takes the destination it is named for on this host.
#[test]
fn named_keys_take_their_destinations() {
    let backslash = if cfg!(windows) {
        Destination::Escapes
    } else {
        Destination::Resolved
    };
    let expected = [
        Destination::Resolved,
        Destination::Resolved,
        backslash,
        Destination::RootParent,
        Destination::Resolved,
        Destination::RootParent,
    ];
    for ((name, script), expected) in scripts().iter().zip(expected) {
        let mut taken = None;
        script.replay(|input| taken = Some(path_containment_from(input)));
        assert_eq!(taken, Some(expected), "{name}");
    }
}
