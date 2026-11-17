//! Choice scripts, curated corpus files and seeded sweeps for replay tests.
#![expect(
    clippy::expect_used,
    reason = "a replay test stops at the first unreadable curated file"
)]
use super::{Choices, SplitMix64};
use std::path::{Path, PathBuf};

/// Seeded cases each sweep runs: fewer under Miri, which interprets every
/// step of every case.
pub(crate) const SWEEP_CASES: u64 = if cfg!(miri) { 8 } else { 256 };
/// Set in the environment to rewrite each script's curated file from the
/// script, after a model change alters its choices.
const UPDATE_VARIABLE: &str = "UPDATE_FUZZ_SEEDS";

/// One choice a model made, or a script encodes.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum Step {
    /// A number from `minimum` through `maximum`; a flag is 0 through 1.
    Number {
        minimum: u64,
        maximum: u64,
        value: u64,
    },
    /// The bytes a [`Choices::bytes`] call returned after its length.
    Bytes(Vec<u8>),
}

/// A named seed written as the values it means.
///
/// Each value is encoded in the bytes [`Choices`] reads for its range, so a
/// script states the trace a model takes, not a byte string whose meaning
/// depends on the reader. Its replay checks that the model asks for exactly
/// these choices first: a model change that inserts or reorders a choice
/// fails the script instead of silently changing what it means. Choices after
/// the script's last read their minimum.
#[derive(Clone, Debug, Default)]
pub(crate) struct Script {
    bytes: Vec<u8>,
    steps: Vec<Step>,
}
impl Script {
    pub(crate) fn new() -> Self {
        Self::default()
    }
    /// `value`, chosen from `minimum` through `maximum`.
    pub(crate) fn range(self, minimum: usize, maximum: usize, value: usize) -> Self {
        self.number(minimum as u64, maximum as u64, value as u64)
    }
    /// `value`, chosen as an index below `len`.
    pub(crate) fn index(self, len: usize, value: usize) -> Self {
        self.range(0, len.saturating_sub(1), value)
    }
    pub(crate) fn flag(self, value: bool) -> Self {
        self.number(0, 1, u64::from(value))
    }
    pub(crate) fn word(self, value: u64) -> Self {
        self.number(0, u64::MAX, value)
    }
    /// `value`, read as a length from 0 through `maximum` and its bytes.
    pub(crate) fn bytes(self, maximum: usize, value: &[u8]) -> Self {
        let mut script = self.range(0, maximum, value.len());
        script.bytes.extend_from_slice(value);
        script.steps.push(Step::Bytes(value.to_vec()));
        script
    }
    /// `count` repetitions of `step`.
    pub(crate) fn repeat(self, count: usize, step: impl Fn(Self) -> Self) -> Self {
        (0..count).fold(self, |script, _| step(script))
    }
    /// The bytes a fuzz target receives for this script.
    pub(crate) fn encoded(&self) -> &[u8] {
        &self.bytes
    }
    /// Runs `model` over the script's bytes and checks that its first
    /// choices are the script's.
    pub(crate) fn replay(&self, model: impl FnOnce(&mut Choices<'_>)) {
        let mut choices = Choices::new(&self.bytes);
        model(&mut choices);
        let trace = choices.trace();
        for (index, step) in self.steps.iter().enumerate() {
            assert_eq!(
                trace.get(index),
                Some(step),
                "choice {index} is not the script's"
            );
        }
    }
    /// The offset from `minimum` in the bytes `int_in_range` reads for the
    /// range: the fewest that cover its span, most significant first.
    fn number(mut self, minimum: u64, maximum: u64, value: u64) -> Self {
        if maximum > minimum {
            assert!(
                (minimum..=maximum).contains(&value),
                "{value} is outside {minimum}..={maximum}"
            );
            let span = maximum - minimum;
            let width = (u64::BITS - span.leading_zeros()).div_ceil(8) as usize;
            let offset = (value - minimum).to_be_bytes();
            self.bytes
                .extend_from_slice(&offset[offset.len() - width..]);
        } else {
            assert_eq!(value, minimum, "a range of one value reads its minimum");
        }
        self.steps.push(Step::Number {
            minimum,
            maximum,
            value,
        });
        self
    }
}

/// Runs `model` over [`SWEEP_CASES`] inputs of `length` bytes, each filled
/// from SplitMix64 seeded with its case number, so every case is a distinct
/// trace. A failing case prints its seed and bytes, which a fuzz target
/// replays as this sweep does.
pub(crate) fn sweep(length: usize, mut model: impl FnMut(&[u8])) {
    for seed in 0..SWEEP_CASES {
        let mut generator = SplitMix64::new(seed);
        let bytes: Vec<u8> = (0..length.div_ceil(8))
            .flat_map(|_| generator.next_word().to_le_bytes())
            .take(length)
            .collect();
        let _case = Case {
            seed,
            bytes: &bytes,
        };
        model(&bytes);
    }
}
/// Names the sweep case a panic interrupted.
struct Case<'a> {
    seed: u64,
    bytes: &'a [u8],
}
impl Drop for Case<'_> {
    #[expect(
        clippy::print_stderr,
        reason = "libtest shows a failing test's captured output"
    )]
    fn drop(&mut self) {
        if std::thread::panicking() {
            eprintln!("sweep case {} failed; bytes {:02x?}", self.seed, self.bytes);
        }
    }
}

/// Replays a fuzz target's scripts and curated inputs. Each script must
/// have a curated file under `fuzz/corpus/<target>/` named for it and
/// holding its bytes, which campaigns start from; the directory's other
/// files are replayed as they are.
pub(crate) fn replay_target(
    target: &str,
    scripts: &[(&str, Script)],
    model: impl Fn(&mut Choices<'_>),
) {
    let directory = curated_directory(target);
    let update = std::env::var_os(UPDATE_VARIABLE).is_some();
    for (name, script) in scripts {
        script.replay(&model);
        let path = directory.join(name);
        if update {
            std::fs::create_dir_all(&directory).expect("curated directory");
            std::fs::write(&path, script.encoded()).expect("curated file");
        }
        let curated = std::fs::read(&path).unwrap_or_default();
        assert!(
            curated == script.encoded(),
            "{} does not hold its script's bytes; rerun with {UPDATE_VARIABLE}=1 to rewrite it",
            path.display()
        );
    }
    for (name, bytes) in curated_files(&directory) {
        if scripts.iter().all(|(script, _)| *script != name) {
            model(&mut Choices::new(&bytes));
        }
    }
}
/// A target's curated inputs, which `cargo xtask fuzz` passes to libFuzzer
/// as a corpus directory after the campaign's own.
fn curated_directory(target: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../fuzz/corpus")
        .join(target)
}
/// Every file in `directory` by name, in name order.
fn curated_files(directory: &Path) -> Vec<(String, Vec<u8>)> {
    let mut files: Vec<_> = std::fs::read_dir(directory)
        .expect("curated directory")
        .map(|entry| {
            let entry = entry.expect("curated entry");
            let name = entry.file_name().to_string_lossy().into_owned();
            (name, std::fs::read(entry.path()).expect("curated file"))
        })
        .collect();
    files.sort();
    files
}
