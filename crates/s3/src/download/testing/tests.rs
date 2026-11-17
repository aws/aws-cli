use super::*;
use crate::testing::{Script, replay_target, sweep};

/// A 64-byte object: one empty range at offset 0, then one byte there.
fn single_byte() -> Script {
    Script::new()
        .range(0, 64, 64)
        .flag(false)
        .range(0, 65, 0)
        .range(0, 65, 1)
}
#[test]
fn callback_ranges_replay_their_scripts_and_a_seeded_sweep() {
    callback_ranges(&[]);
    replay_target(
        "writer_ranges",
        &[("single_byte", single_byte())],
        ranges::callback_ranges_from,
    );
    sweep(1024, callback_ranges);
}

/// A 173-byte object of 8-byte pages, evicted in batches of two pages, whose
/// one-byte chunks complete pages one byte at a time.
fn partial_pages() -> Script {
    Script::new()
        .range(1, 256, 173)
        .range(0, 6, 3)
        .range(1, 8, 2)
}
#[test]
fn page_completion_replays_its_scripts_and_a_seeded_sweep() {
    page_completion(&[]);
    replay_target(
        "writer_pages",
        &[("partial_pages", partial_pages())],
        ranges::page_completion_from,
    );
    sweep(1024, page_completion);
}

/// A direct write of a 100-byte object with 8-byte offsets, 16-byte memory
/// alignment and two retries, in chunks of 32, 40 and 28 bytes.
fn shuffled_direct_tail() -> Script {
    let script = Script::new().flag(true).range(0, 6, 3).range(0, 6, 4);
    let script = script.range(1, 256, 100).range(0, 8, 2).flag(false);
    let script = script.range(1, 13, 4).range(1, 9, 5).range(1, 4, 4);
    // The middle chunk first: a short write of one block, then an
    // interruption.
    let script = script.flag(false).index(3, 1);
    let script = script.flag(true).flag(true).range(1, 1, 1).flag(true);
    // A rejected unaligned non-final length, then the padded tail.
    let script = script.flag(true).index(4, 2).index(2, 1);
    // The head last.
    script.flag(false).index(1, 0)
}
#[test]
fn write_retries_replay_their_scripts_and_a_seeded_sweep() {
    write_retries(&[]);
    replay_target(
        "writer_retries",
        &[("shuffled_direct_tail", shuffled_direct_tail())],
        retries::write_retries_from,
    );
    sweep(2048, write_retries);
}

mod output {
    use super::super::composition::*;
    use super::*;
    use crate::download::{WriteError, WriterMode};

    const PWRITE: usize = 0;
    const DIRECT: usize = 1;
    const MMAP: usize = 2;
    const REQUIRED: usize = 0;
    const PREFERRED: usize = 1;
    const SALT: usize = 0x5a;

    /// An object of `size` bytes for writer `writer`, with offsets and
    /// memory aligned to `1 << offset` and `1 << memory`, a bounce capacity
    /// of `blocks` offset blocks and no setup switch, cut into pieces of
    /// `pieces` blocks with none withheld, with no write fault before
    /// preparation.
    fn object(
        [writer, requirement, size]: [usize; 3],
        [offset, memory, blocks]: [usize; 3],
        pieces: &[usize],
        added: &[fn(Script) -> Script],
    ) -> Script {
        let script = Script::new()
            .index(WRITERS.len(), writer)
            .index(2, requirement)
            .range(0, SIZE_MAX, size)
            .range(0, u8::MAX.into(), SALT)
            .range(0, 6, offset)
            .range(0, 6, memory)
            .range(1, BOUNCE_BLOCKS_MAX, blocks)
            .flag(false);
        let block = if writer == DIRECT { 1 << offset } else { 1 };
        let mut start = 0;
        let script = pieces
            .iter()
            .enumerate()
            .fold(script, |script, (index, &taken)| {
                let left = (size - start).div_ceil(block);
                start = (start + taken * block).min(size);
                if index + 1 == PIECES_MAX {
                    script
                } else {
                    script.range(0, left - 1, left - taken)
                }
            });
        let script = script.flag(false).range(0, ADDED_MAX, added.len());
        added
            .iter()
            .fold(script, |script, add| add(script))
            .flag(false)
    }
    /// Delivers body `pick` of `len` bodies and queued ones, on its callback
    /// or, with `queue`, onto a writer's queue.
    fn deliver(script: Script, [pick, len]: [usize; 2], queue: bool) -> Script {
        script.flag(false).index(len, pick).flag(queue)
    }
    /// Writes the queued body `pick` of `len` bodies and queued ones.
    fn write_queued(script: Script, [pick, len]: [usize; 2]) -> Script {
        script.flag(false).index(len, pick)
    }
    #[expect(clippy::expect_used, reason = "`INJECTED` lists every injection")]
    fn inject(script: Script, injected: Injected) -> Script {
        let index = INJECTED.iter().position(|kind| *kind == injected);
        script
            .flag(true)
            .index(INJECTED.len(), index.expect("an injection"))
    }
    fn reached(script: &Script) -> Outcome {
        let mut outcome = Outcome::default();
        script.replay(|input| outcome = output_composition_from(input));
        outcome
    }

    /// Positional writes of three pieces, the last queued first and written
    /// through an interruption and a short write.
    fn pwrite_shuffled() -> Script {
        let script = object([PWRITE, REQUIRED, 300], [0, 0, 1], &[100, 37, 163], &[]);
        let script = inject(script, Injected::Interrupted).index(3, 2).flag(true);
        let script = inject(script, Injected::Short).range(1, SHORT_STEPS_MAX, 2);
        let script = deliver(script.index(3, 2), [1, 2], false);
        let script = deliver(script, [0, 1], true);
        write_queued(script, [0, 1])
    }
    /// Direct writes with 16-byte offsets, 64-byte memory and a 16-byte
    /// bounce: the padded tail and the piece at offset 96 bounce in chunks.
    fn direct_shuffled_bounces() -> Script {
        let script = object([DIRECT, REQUIRED, 200], [4, 6, 1], &[6, 2, 5], &[]);
        let script = deliver(script, [2, 3], false);
        let script = deliver(script, [0, 2], false);
        deliver(script, [0, 1], false)
    }
    /// A preferred mapping of a page's first 512 bytes, with an empty body
    /// past its end queued and written among them.
    fn mmap_shuffled() -> Script {
        let empty: fn(Script) -> Script = |script| {
            let script = script.index(ADDED.len(), 2);
            script.range(0, SIZE_MAX + PAST_MAX, SIZE_MAX + 8)
        };
        let script = object(
            [MMAP, PREFERRED, SIZE_MAX],
            [0, 0, 1],
            &[64, 200, 248],
            &[empty],
        );
        let script = deliver(script, [3, 4], true);
        let script = deliver(script, [1, 4], false);
        let script = write_queued(script, [2, 3]);
        let script = deliver(script, [1, 2], true);
        let script = deliver(script, [0, 2], false);
        write_queued(script, [0, 1])
    }
    /// A body of other bytes over the middle half, queued after the first
    /// half lands, is refused and fails the object.
    fn overlapping_body() -> Script {
        let overlapping: fn(Script) -> Script = |script| {
            let script = script.index(ADDED.len(), 0);
            script.range(0, 63, 16).range(1, 48, 32)
        };
        let script = object(
            [PWRITE, PREFERRED, 64],
            [0, 0, 1],
            &[32, 32],
            &[overlapping],
        );
        let script = deliver(script, [0, 3], false);
        let script = deliver(script, [1, 2], true);
        deliver(script, [0, 1], false)
    }
    /// A body whose end overflows a mapped object's queued piece; the
    /// failure refuses the piece's write.
    fn out_of_bounds_body() -> Script {
        let overflowing: fn(Script) -> Script = |script| {
            let script = script.index(ADDED.len(), 1).flag(true);
            script.range(0, PAST_MAX, 3).range(1, PAST_MAX, 8)
        };
        let script = object([MMAP, REQUIRED, 100], [0, 0, 1], &[100], &[overflowing]);
        let script = deliver(script, [0, 2], true);
        let script = deliver(script, [0, 2], false);
        write_queued(script, [0, 1])
    }
    /// `ENOSPC` takes the queued tail of a direct object; its head is then
    /// refused.
    fn terminal_fault_mid_object() -> Script {
        let script = object([DIRECT, PREFERRED, 256], [3, 3, 8], &[8, 8, 16], &[]);
        let script = deliver(script, [1, 3], false);
        let script = inject(script, Injected::NoSpace).index(2, 1).flag(true);
        let script = write_queued(script, [1, 2]);
        deliver(script, [0, 1], false)
    }
    fn output_scripts() -> [(&'static str, Script); 6] {
        [
            ("pwrite_shuffled", pwrite_shuffled()),
            ("direct_shuffled_bounces", direct_shuffled_bounces()),
            ("mmap_shuffled", mmap_shuffled()),
            ("overlapping_body", overlapping_body()),
            ("out_of_bounds_body", out_of_bounds_body()),
            ("terminal_fault_mid_object", terminal_fault_mid_object()),
        ]
    }

    #[test]
    fn output_composition_replays_its_scripts_and_a_seeded_sweep() {
        output_composition(&[]);
        replay_target("writer_output", &output_scripts(), |input| {
            output_composition_from(input);
        });
        sweep(128, output_composition);
    }

    /// Each named script reaches the writer, refusals, write calls and
    /// conclusion it is named for.
    #[test]
    #[cfg_attr(miri, ignore = "the replay test runs the same scripts under Miri")]
    fn named_output_scripts_reach_their_outcomes() {
        let no_space = |result: &Result<(), WriteError>| match result {
            Err(WriteError::Io { kind, .. }) => *kind == std::io::ErrorKind::StorageFull,
            _ => false,
        };
        let expected = [
            (WriterMode::Pwrite, 0, 5, Ok(())),
            (WriterMode::Direct, 0, 8, Ok(())),
            (WriterMode::Mmap, 0, 0, Ok(())),
            (WriterMode::Pwrite, 1, 1, Err(WriteError::Overlap)),
            (WriterMode::Mmap, 1, 0, Err(WriteError::OutOfBounds)),
        ];
        let scripts = output_scripts();
        for ((name, script), (mode, refused, writes, concluded)) in scripts.iter().zip(expected) {
            let outcome = Outcome {
                mode: Some(mode),
                refused,
                writes,
                concluded: Some(concluded),
            };
            assert_eq!(reached(script), outcome, "{name}");
        }
        let outcome = reached(&scripts[5].1);
        assert_eq!(
            (outcome.mode, outcome.writes),
            (Some(WriterMode::Direct), 2)
        );
        assert!(outcome.concluded.as_ref().is_some_and(no_space));
    }
}
