//! Testing only: the choice reader the fuzz models decode their input with.
//!
//! Every model reads its choices through [`Choices`], a thin layer over
//! [`arbitrary::Unstructured`], so one byte string is one trace under
//! libFuzzer, `cargo test` and Miri. A choice never fails: once the bytes run
//! out, each choice reads as its minimum, so the empty input is the trace of
//! minimum choices. The fuzz targets pass libFuzzer's bytes straight to a
//! model, which builds its own reader. The replay tests write their named
//! seeds as choice scripts and sweep seeded byte strings through the same
//! reader (`script`, compiled for unit tests only).
use arbitrary::Unstructured;

#[cfg(test)]
mod script;
#[cfg(test)]
mod tests;
#[cfg(test)]
pub(crate) use script::{Script, Step, curated_inputs, replay_target, sweep};

/// A model's choices, read from the front of its input.
///
/// A range reads the fewest bytes that cover it, most significant first, and
/// reduces them modulo the range's size, as `Unstructured::int_in_range`
/// does. A flag reads one byte, and the bytes of [`Choices::bytes`] follow
/// their length.
#[derive(Debug)]
pub struct Choices<'a> {
    input: Unstructured<'a>,
    /// Every choice made so far, which a script's replay compares with the
    /// choices it encoded.
    #[cfg(test)]
    trace: Vec<Step>,
}
impl<'a> Choices<'a> {
    /// A reader over `bytes`.
    #[must_use]
    pub fn new(bytes: &'a [u8]) -> Self {
        Self {
            input: Unstructured::new(bytes),
            #[cfg(test)]
            trace: Vec::new(),
        }
    }
    /// A value from `minimum` through `maximum`, or `minimum` when the range
    /// holds one value or none.
    pub fn range(&mut self, minimum: usize, maximum: usize) -> usize {
        // `number` returns a value no larger than `maximum`, a usize.
        self.number(minimum as u64, maximum as u64) as usize
    }
    /// An index below `len`, or 0 when `len` is 0.
    pub fn index(&mut self, len: usize) -> usize {
        self.range(0, len.saturating_sub(1))
    }
    /// A flag: the low bit of one byte.
    pub fn flag(&mut self) -> bool {
        self.number(0, 1) == 1
    }
    /// A full-width word, read from eight bytes.
    pub fn word(&mut self) -> u64 {
        self.number(0, u64::MAX)
    }
    /// A length from 0 through `maximum`, then that many bytes, or as many
    /// as remain.
    pub fn bytes(&mut self, maximum: usize) -> &'a [u8] {
        let length = self.range(0, maximum).min(self.input.len());
        let bytes = self.input.bytes(length).unwrap_or_default();
        #[cfg(test)]
        self.trace.push(Step::Bytes(bytes.to_vec()));
        bytes
    }
    /// Whether every byte has been read.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.input.is_empty()
    }
    /// A generator seeded by one word, for code that consumes random words,
    /// such as the retry backoff sampler. Exhausted input reads as zeros, and
    /// that sampler never returns on a source stuck at zero, so such code
    /// must take its words from this generator rather than from the input.
    pub fn generator(&mut self) -> SplitMix64 {
        SplitMix64::new(self.word())
    }
    fn number(&mut self, minimum: u64, maximum: u64) -> u64 {
        let value = if maximum <= minimum {
            minimum
        } else {
            // `int_in_range` uses what bytes remain and never fails on a
            // nonempty range.
            self.input
                .int_in_range(minimum..=maximum)
                .unwrap_or(minimum)
        };
        #[cfg(test)]
        self.trace.push(Step::Number {
            minimum,
            maximum,
            value,
        });
        value
    }
    /// The choices made so far.
    #[cfg(test)]
    pub(crate) fn trace(&self) -> &[Step] {
        &self.trace
    }
}

/// SplitMix64 (Steele, Lea and Flood, 2014): a fixed sequence of uniform
/// words for each seed, which the replay sweeps turn into inputs.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SplitMix64(u64);
impl SplitMix64 {
    /// A generator whose first word depends on `seed` alone.
    #[must_use]
    pub fn new(seed: u64) -> Self {
        Self(seed)
    }
    /// The next word.
    pub fn next_word(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut value = self.0;
        value = (value ^ (value >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        value ^ (value >> 31)
    }
}
