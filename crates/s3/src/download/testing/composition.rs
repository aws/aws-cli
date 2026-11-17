//! One object's bodies composed into its file through the real `Output`.
//!
//! The input picks a writer and requirement, an object of up to 512 bytes,
//! the switches `FakePlatform` fails setup with, and a partition of the
//! object into bodies, one of which it may withhold, and to which it adds
//! overlapping, out-of-bounds and empty bodies. It then picks the order the
//! bodies arrive in, whether each is written on its callback or queued for a
//! writer, when a queued one is written, and the faults injected between
//! them. As the writer service does, the model fails the object when
//! `Output` refuses a body.
//!
//! The reference is the bytes each accepted body carried and the ranges
//! accepted so far. The partition's bodies carry the object's bytes, a
//! pattern the input salts that does not repeat every 256 bytes; the added
//! bodies carry those bytes with every bit flipped, so a refused body that
//! reached written bytes would change them.
use super::super::{
    LocalityContext, Requirement, WriteError, WriterConfig, WriterMode,
    diagnostics::ObjectPhases,
    io::{BOUNCE_BYTES, DirectAlignment},
    lock,
    output::{Body, Output, Policy},
    platform::{Advice, Platform},
    prefault::PrefaultSource,
    service::ThreadSpawner,
};
use super::{
    fakes::{self, FakePlatform, Fault},
    ranges::expected_range,
};
use crate::testing::{Choices, SplitMix64};
use std::{
    collections::VecDeque,
    ops::Range,
    sync::{Arc, atomic::AtomicBool, atomic::Ordering},
};

/// The largest object, which stays within one page of the fake's mapping.
pub(super) const SIZE_MAX: usize = 512;
/// The most bodies a partition has; the last takes the rest of the object.
pub(super) const PIECES_MAX: usize = 6;
pub(super) const ADDED_MAX: usize = 3;
/// How far an out-of-bounds body reaches past the object's end.
pub(super) const PAST_MAX: usize = 16;
pub(super) const WRITERS: [WriterMode; 3] =
    [WriterMode::Pwrite, WriterMode::Direct, WriterMode::Mmap];
/// The setup switches, one bit each in the input's mask.
const SWITCHES: [fn(&FakePlatform) -> &AtomicBool; 6] = [
    |platform| &platform.direct_refused,
    |platform| &platform.alignment_error,
    |platform| &platform.disable_error,
    |platform| &platform.map_unavailable,
    |platform| &platform.map_error,
    |platform| &platform.unsupported_preallocation,
];
pub(super) const MASK_MAX: usize = (1 << SWITCHES.len()) - 1;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Added {
    Overlapping,
    OutOfBounds,
    Empty,
}
pub(super) const ADDED: [Added; 3] = [Added::Overlapping, Added::OutOfBounds, Added::Empty];
/// A fault injected before a step: one the next write call takes, or a
/// switch that fails every later eviction or length change.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Injected {
    Interrupted,
    /// A short write of whole alignment steps, which the loop retries.
    Short,
    Zero,
    NoSpace,
    /// A count past the bytes offered.
    Rejected,
    Evict,
    Truncate,
}
pub(super) const INJECTED: [Injected; 7] = [
    Injected::Interrupted,
    Injected::Short,
    Injected::Zero,
    Injected::NoSpace,
    Injected::Rejected,
    Injected::Evict,
    Injected::Truncate,
];
/// The most alignment steps a short write takes.
pub(super) const SHORT_STEPS_MAX: usize = 4;
/// The most alignment blocks the bounce capacity holds.
pub(super) const BOUNCE_BLOCKS_MAX: usize = 8;

/// The object's bytes and the added bodies' other bytes, aligned so a body's
/// address alignment is its offset's.
#[repr(align(64))]
struct Pattern([u8; SIZE_MAX + PAST_MAX]);
impl Pattern {
    fn new(salt: u64) -> Self {
        Self(std::array::from_fn(|index| {
            SplitMix64::new(((index as u64) << 9) | salt).next_word() as u8
        }))
    }
}
struct Piece<'p> {
    offset: u64,
    bytes: &'p [u8],
}

/// What a run reached, for the named scripts' tests.
#[derive(Debug, Default, PartialEq, Eq)]
pub(super) struct Outcome {
    /// The prepared output's writer, or None if preparation failed.
    pub(super) mode: Option<WriterMode>,
    /// Bodies the range rules refused.
    pub(super) refused: usize,
    /// Write calls after preparation.
    pub(super) writes: usize,
    pub(super) concluded: Option<Result<(), WriteError>>,
}

/// Checks the file a prepared output composes from shuffled bodies against
/// the bytes it accepted.
pub fn output_composition(bytes: &[u8]) {
    output_composition_from(&mut Choices::new(bytes));
}
pub(super) fn output_composition_from(input: &mut Choices<'_>) -> Outcome {
    let writer = WRITERS[input.index(WRITERS.len())];
    let requirement = [Requirement::Required, Requirement::Preferred][input.index(2)];
    let size = input.range(0, SIZE_MAX);
    let salt = input.range(0, u8::MAX.into()) as u64;
    let alignment = DirectAlignment {
        offset: 1 << input.range(0, 6),
        memory: 1 << input.range(0, 6),
    };
    let previous = BOUNCE_BYTES.replace(alignment.offset * input.range(1, BOUNCE_BLOCKS_MAX));
    let mask = if input.flag() {
        input.range(1, MASK_MAX)
    } else {
        0
    };
    let source = Pattern::new(salt);
    let other = Pattern(source.0.map(|byte| !byte));
    let direct = writer == WriterMode::Direct;
    let block = if direct { alignment.offset } else { 1 };
    let mut pieces = partition(size, block, input);
    // Only added bodies can fill a withheld piece, with their bytes.
    let mut expected = source.0[..size].to_vec();
    if !pieces.is_empty() && input.flag() {
        let withheld = pieces.remove(input.index(pieces.len()));
        expected[withheld.clone()].copy_from_slice(&other.0[withheld]);
    }
    let mut bodies = pieces
        .into_iter()
        .map(|range| Piece {
            offset: range.start as u64,
            bytes: &source.0[range],
        })
        .collect::<Vec<_>>();
    for _ in 0..input.range(0, ADDED_MAX) {
        bodies.push(added(size, block, &other.0, input));
    }
    let platform = Arc::new(FakePlatform::default());
    *lock(&platform.alignment) = Some(alignment);
    for (bit, switch) in SWITCHES.iter().enumerate() {
        switch(&platform).store(mask & (1 << bit) != 0, Ordering::Relaxed);
    }
    let step = alignment.offset.max(alignment.memory);
    let mut faults = Faults {
        step,
        ..Faults::default()
    };
    // A write fault now reaches the direct writer's probe write.
    if input.flag() {
        faults.inject(&platform, input);
    }
    let model = Model::prepare(writer, requirement, size, faults, &platform);
    let outcome = model.map(|model| model.run(bodies, &expected, input));
    BOUNCE_BYTES.set(previous);
    outcome.unwrap_or_default()
}

/// Cuts the object into at most `PIECES_MAX` pieces of whole blocks, the
/// last ending at the object's end; spent input leaves one piece.
fn partition(size: usize, block: usize, input: &mut Choices<'_>) -> Vec<Range<usize>> {
    let mut pieces = Vec::new();
    let mut start = 0;
    while start < size {
        let blocks = (size - start).div_ceil(block);
        let taken = if pieces.len() + 1 == PIECES_MAX {
            blocks
        } else {
            blocks - input.range(0, blocks - 1)
        };
        let end = (start + taken * block).min(size);
        pieces.push(start..end);
        start = end;
    }
    pieces
}
/// A body of other bytes over whole blocks of the object, past its end, or
/// empty.
fn added<'p>(size: usize, block: usize, other: &'p [u8], input: &mut Choices<'_>) -> Piece<'p> {
    match ADDED[input.index(ADDED.len())] {
        Added::Overlapping if size > 0 => {
            let blocks = size.div_ceil(block);
            let first = input.range(0, blocks - 1);
            let start = first * block;
            let end = ((first + input.range(1, blocks - first)) * block).min(size);
            Piece {
                offset: start as u64,
                bytes: &other[start..end],
            }
        }
        Added::OutOfBounds => {
            // Near the largest offset, or reaching past the object's end.
            let (offset, len) = if input.flag() {
                let offset = u64::MAX - input.range(0, PAST_MAX) as u64;
                (offset, input.range(1, PAST_MAX))
            } else {
                let start = input.range(0, size);
                (start as u64, size - start + input.range(1, PAST_MAX))
            };
            Piece {
                offset,
                bytes: &other[..len],
            }
        }
        Added::Overlapping | Added::Empty => Piece {
            offset: input.range(0, size + PAST_MAX) as u64,
            bytes: &[],
        },
    }
}

#[derive(Debug, Default)]
struct Faults {
    /// Whether each write fault the fake still queues is terminal.
    queued: VecDeque<bool>,
    /// The evictions made before evictions began to fail, if they did.
    evictions_refused_after: Option<usize>,
    /// Whether length changes fail.
    truncate: bool,
    /// The direct writer's alignment step, which a short write keeps to.
    step: usize,
}
impl Faults {
    fn inject(&mut self, platform: &FakePlatform, input: &mut Choices<'_>) {
        let fault = match INJECTED[input.index(INJECTED.len())] {
            Injected::Interrupted => Fault::Interrupted,
            Injected::Short => Fault::Short(self.step * input.range(1, SHORT_STEPS_MAX)),
            Injected::Zero => Fault::Zero,
            Injected::NoSpace => Fault::Failed,
            Injected::Rejected => Fault::Rejected,
            Injected::Evict => {
                platform.evict_error.store(true, Ordering::Relaxed);
                let made = evictions(platform);
                self.evictions_refused_after.get_or_insert(made);
                return;
            }
            Injected::Truncate => {
                *lock(&platform.set_length_failure) = Some(libc::EIO);
                self.truncate = true;
                return;
            }
        };
        let terminal = matches!(fault, Fault::Zero | Fault::Failed | Fault::Rejected);
        self.queued.push_back(terminal);
        lock(&platform.faults).push_back(fault);
    }
    /// Whether a write fault taken since the last call was terminal.
    fn taken(&mut self, platform: &FakePlatform) -> bool {
        let taken = self.queued.len() - lock(&platform.faults).len();
        self.queued.drain(..taken).any(|terminal| terminal)
    }
    /// The evictions the mapping made and did not refuse.
    fn evictions(&self, platform: &FakePlatform) -> usize {
        let made = evictions(platform);
        self.evictions_refused_after
            .map_or(made, |before| before.min(made))
    }
    /// Whether a switch fails the finish of an output of `mode`: a
    /// mapping's final eviction, or a direct output's length change.
    fn fail_finish(&self, mode: WriterMode) -> bool {
        match mode {
            WriterMode::Mmap => self.evictions_refused_after.is_some(),
            WriterMode::Direct => self.truncate,
            WriterMode::Pwrite | WriterMode::Crt => false,
        }
    }
}

#[derive(Debug)]
struct Model<'p> {
    platform: &'p FakePlatform,
    output: Arc<Output>,
    faults: Faults,
    /// What each accepted body carried; zero where none landed.
    image: Vec<u8>,
    accepted: Vec<bool>,
    /// Whether a refusal or a failed write failed the object.
    failed: bool,
    refused: usize,
    /// The write calls and evictions preparation made.
    writes: usize,
    evictions: usize,
}
impl<'p> Model<'p> {
    fn prepare(
        writer: WriterMode,
        requirement: Requirement,
        size: usize,
        mut faults: Faults,
        platform: &'p Arc<FakePlatform>,
    ) -> Option<Self> {
        let config = WriterConfig {
            requirement,
            ..fakes::config(writer)
        };
        let policy = Policy {
            config: &config,
            prefault: PrefaultSource::Disabled,
            spawner: &ThreadSpawner,
        };
        let shared = Arc::clone(platform) as Arc<dyn Platform>;
        let locality = LocalityContext::default();
        let phases = &mut ObjectPhases::default();
        let file = fakes::file();
        let output = Output::prepare(file, size as u64, policy, shared, &locality, phases).ok()?;
        // A required writer is the one prepared, but an empty object is
        // never mapped.
        if requirement == Requirement::Required {
            let empty = writer == WriterMode::Mmap && size == 0;
            let expected = if empty { WriterMode::Pwrite } else { writer };
            assert_eq!(output.mode(), expected, "a required writer fell back");
        }
        faults.taken(platform);
        Some(Self {
            platform: platform.as_ref(),
            evictions: faults.evictions(platform),
            output,
            faults,
            image: vec![0; size],
            accepted: vec![false; size],
            failed: false,
            refused: 0,
            writes: lock(&platform.write_sizes).len(),
        })
    }
    fn run(
        mut self,
        mut bodies: Vec<Piece<'_>>,
        expected: &[u8],
        input: &mut Choices<'_>,
    ) -> Outcome {
        let mut queued = Vec::new();
        while !bodies.is_empty() || !queued.is_empty() {
            if input.flag() {
                self.faults.inject(self.platform, input);
            }
            let pick = input.index(bodies.len() + queued.len());
            if pick >= bodies.len() {
                self.write_queued(queued.swap_remove(pick - bodies.len()));
            } else if input.flag() {
                self.queue(bodies.remove(pick), &mut queued);
            } else {
                self.write_now(&bodies.remove(pick));
            }
            self.check_file();
        }
        self.conclude(expected)
    }
    /// The admission `Output` owes a body: a refusal once the object
    /// failed, else the range rules' result, whose range is then taken.
    fn admission(&mut self, piece: &Piece<'_>) -> Option<Result<(), WriteError>> {
        let (offset, len) = (piece.offset, piece.bytes.len());
        let end = u128::from(offset) + len as u128;
        let rule = (!self.failed).then(|| expected_range(&mut self.accepted, offset, len, end));
        self.refused += usize::from(rule.as_ref().is_some_and(Result::is_err));
        rule
    }
    /// A body written on its callback, as a single-request GET's is; the
    /// service passes no empty one on.
    fn write_now(&mut self, piece: &Piece<'_>) {
        if piece.bytes.is_empty() {
            return;
        }
        let expected = self.admission(piece);
        let (file, calls) = (self.file(), self.calls());
        let written = self.output.write_now(piece.offset, piece.bytes);
        if expected == Some(Ok(())) {
            self.wrote(piece, &file, written.is_ok());
        } else {
            assert!(written.is_err(), "a refused body was written");
            assert_eq!(self.calls(), calls, "a refused body's write");
            if let Some(rule) = expected {
                assert_eq!(written, rule, "{}+{}", piece.offset, piece.bytes.len());
            }
        }
        if let Err(error) = written {
            self.fail(error);
        }
    }
    /// A body accepted onto a writer's queue, counted as enqueued.
    fn queue(&mut self, piece: Piece<'_>, queued: &mut Vec<Body>) {
        let expected = self.admission(&piece);
        let body = Body::owned(piece.offset, piece.bytes.to_vec());
        let accepted = self.output.accept(&body);
        let len = piece.bytes.len();
        match expected {
            Some(rule) => assert_eq!(accepted, rule, "{}+{len}", piece.offset),
            None => assert!(accepted.is_err(), "a failed object accepted a body"),
        }
        match accepted {
            Ok(()) => {
                self.output.enqueued(len);
                queued.push(body);
            }
            Err(error) => self.fail(error),
        }
    }
    /// A queued body's write, which an object that failed refuses.
    fn write_queued(&mut self, body: Body) {
        let (file, calls) = (self.file(), self.calls());
        let written = self.output.write(&body);
        let piece = Piece {
            offset: body.offset,
            bytes: body.as_bytes(),
        };
        if self.failed {
            let refused = written.is_err() && self.calls() == calls;
            assert!(refused, "a failed object wrote a body");
        } else {
            self.wrote(&piece, &file, written.is_ok());
        }
        self.failed |= written.is_err();
        self.output.complete(piece.bytes.len(), written);
    }
    fn fail(&mut self, error: WriteError) {
        self.output.fail(error);
        self.failed = true;
    }
    /// Checks the write of a body admitted to a live object: it fails
    /// exactly when it took a terminal fault. Its bytes then join the
    /// reference; a failed write may have left each as the body's or as the
    /// file held it.
    fn wrote(&mut self, piece: &Piece<'_>, before: &[u8], written: bool) {
        let terminal = self.faults.taken(self.platform);
        assert_eq!(!written, terminal, "a write's result is its faults'");
        let start = piece.offset as usize;
        let after = self.file();
        for (index, &byte) in piece.bytes.iter().enumerate() {
            let at = start + index;
            assert!(
                written || after[at] == byte || after[at] == before[at],
                "a failed write left a foreign byte at {at}"
            );
            self.image[at] = if written { byte } else { after[at] };
        }
    }
    /// The file holds the reference, zeros past the object's end, and the
    /// received bytes are the accepted ones.
    fn check_file(&self) {
        let file = self.file();
        assert!(file.len() >= self.image.len(), "the file is short");
        let (object, past) = file.split_at(self.image.len());
        assert_eq!(object, self.image, "the file differs from its bodies");
        assert!(past.iter().all(|&byte| byte == 0), "bytes past the end");
        let accepted = self.accepted.iter().filter(|&&bit| bit).count();
        let received = self.output.observed_stats().received_bytes;
        assert_eq!(received, accepted as u64, "received bytes");
    }
    /// The object's bytes as its writer left them: the mapping's, or the
    /// disk's and any past its end.
    fn file(&self) -> Vec<u8> {
        if self.output.mode() == WriterMode::Mmap {
            let mapping = lock(&self.platform.mapping);
            lock(&mapping.as_ref().unwrap().bytes).clone()
        } else {
            lock(&self.platform.disk).clone()
        }
    }
    /// The write calls the fake took.
    fn calls(&self) -> usize {
        lock(&self.platform.write_sizes).len()
    }
    /// An object whose bodies all wrote succeeds unless a switch fails its
    /// writer's finish; one that failed or is incomplete fails. Success
    /// leaves the expected bytes in a file of the object's length and each
    /// page evicted once, and no page is evicted twice.
    fn conclude(self, expected: &[u8]) -> Outcome {
        let concluded = self.output.conclude(true).map(|_| ());
        let complete = self.accepted.iter().all(|&bit| bit);
        let unfinished = self.faults.fail_finish(self.output.mode());
        if self.failed || !complete || unfinished {
            assert!(concluded.is_err(), "an unfinished object succeeded");
        } else {
            assert_eq!(concluded, Ok(()), "a written object failed");
        }
        let mapped = self.output.mode() == WriterMode::Mmap;
        let evicted = self.faults.evictions(self.platform) - self.evictions;
        assert!(evicted <= usize::from(mapped), "a page was evicted twice");
        if concluded.is_ok() {
            assert_eq!(self.image, expected, "a success with other bytes");
            assert_eq!(self.file(), expected, "a success's file");
            let length = lock(&self.platform.disk).len();
            assert_eq!(length, expected.len(), "a success's file length");
            assert_eq!(evicted, usize::from(mapped), "a success left a page");
        }
        Outcome {
            mode: Some(self.output.mode()),
            refused: self.refused,
            writes: self.calls() - self.writes,
            concluded: Some(concluded),
        }
    }
}
/// The eviction advice the mapping took, refused or not.
fn evictions(platform: &FakePlatform) -> usize {
    let advice = lock(&platform.advice);
    advice
        .iter()
        .filter(|&&advice| advice == Advice::Evict)
        .count()
}
