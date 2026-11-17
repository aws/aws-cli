//! Upstream's sync comparator, which pairs two key-ordered sides by name.
//!
//! Upstream lists a sync's source and destination in the same order, by the
//! name of each entry below its root, and walks both at once
//! (`Comparator.call`). A name both sides hold is decided by the
//! `file_at_src_and_dest` strategy, one only the source holds by
//! `file_not_at_dest`, and one only the destination holds by
//! `file_not_at_src`. [`Comparator`] runs the same walk: the source drives
//! it one entry at a time, and the comparator pulls the destination's
//! entries as it needs them, so neither side is ever held whole. It hands
//! each name only the destination holds that `--delete` removes to the
//! caller's [`Remover`] as it passes it, in upstream's order, and leaves a
//! name only the source holds to the caller, whose side knows whether a
//! case conflict matters.
//!
//! ```
//! use s3::sync::comparator::{Comparator, Destination, Entry, LocalSide, Modified, Pairing};
//! use s3::sync::{DestinationOnly, Strategies};
//! use std::convert::Infallible;
//! use std::ops::ControlFlow;
//!
//! // An upload's destination: the objects under the prefix, in key order.
//! struct Objects(std::vec::IntoIter<Entry<Vec<u8>>>);
//! impl Destination for Objects {
//!     type Name = Vec<u8>;
//!     type Error = Infallible;
//!     fn next_entry(&mut self) -> Result<Option<Entry<Vec<u8>>>, Infallible> {
//!         Ok(self.0.next())
//!     }
//! }
//! let object = |name: &str| Entry {
//!     name: name.as_bytes().to_vec(),
//!     size: 4,
//!     modified: Modified::from_epoch_seconds(100),
//! };
//! let objects = vec![object("a.txt"), object("b.txt"), object("old.txt")];
//! // `--delete`: an object no file names is removed.
//! let strategies = Strategies {
//!     destination_only: DestinationOnly::Delete,
//!     ..Strategies::default()
//! };
//! let objects = Objects(objects.into_iter());
//! let mut comparator = Comparator::new(strategies, LocalSide::Source, objects);
//! let mut removed = Vec::new();
//! let mut remove = |entry: Entry<Vec<u8>>| {
//!     removed.push(entry.name);
//!     ControlFlow::Continue(())
//! };
//! let file = |name: &'static str, size| Entry {
//!     name: name.as_bytes(),
//!     size,
//!     modified: Modified::from_epoch_seconds(50),
//! };
//! // The same size and older than its object: not uploaded.
//! assert_eq!(comparator.pair(&file("a.txt", 4), &mut remove)?, Pairing::Both(false));
//! // Another size: uploaded.
//! assert_eq!(comparator.pair(&file("b.txt", 5), &mut remove)?, Pairing::Both(true));
//! // A name the destination lacks, which its side's strategy decides.
//! assert_eq!(comparator.pair(&file("c.txt", 1), &mut remove)?, Pairing::SourceOnly);
//! assert_eq!(comparator.finish(&mut remove)?, ControlFlow::Continue(()));
//! assert_eq!(removed, [b"old.txt"]);
//! # Ok::<(), Infallible>(())
//! ```
use super::{BothSides, DestinationOnly, Strategies};
use std::borrow::Cow;
use std::cmp::Ordering;
use std::ops::ControlFlow;
use std::path::{Path, PathBuf};

const MICROS_PER_SECOND: i64 = 1_000_000;
/// The whole seconds of the first and last mtimes upstream reads in UTC,
/// with `datetime.fromtimestamp(st_mtime, tzlocal())`: 0001-01-01 and
/// 9999-12-31 23:59:59, the first and last a `datetime` holds. A zone's
/// offset and DST narrow both ends by hours.
#[cfg(not(windows))]
const READABLE_SECONDS: std::ops::RangeInclusive<i64> = -62_135_596_800..=253_402_300_799;
/// The whole seconds of the first and last mtimes upstream reads in UTC on
/// Windows: 1970-01-01 and 3001-01-19 07:59:59, the first and last the
/// UCRT's `localtime_s` takes (its `max_time_t`, corecrt_internal_time.h).
/// dateutil's `tzlocal` takes every time to `time.localtime` to learn
/// whether it is ambiguous, and CPython raises once `localtime_s` refuses
/// it. A zone's offset and DST narrow both ends by hours.
#[cfg(windows)]
const READABLE_SECONDS: std::ops::RangeInclusive<i64> = 0..=32_536_799_999;

/// A modification time as upstream compares it: microseconds since the epoch.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Modified(i64);
impl Modified {
    /// The Unix epoch.
    pub const EPOCH: Self = Self(0);
    /// An object's LastModified, in whole seconds since the epoch.
    pub fn from_epoch_seconds(seconds: i64) -> Self {
        Self(seconds.saturating_mul(MICROS_PER_SECOND))
    }
    /// A file's mtime, given as `st_mtime` and `st_mtime_nsec`, as upstream reads it.
    ///
    /// CPython reads `st_mtime` as the float `seconds + nanoseconds * 1e-9`
    /// (posixmodule.c `fill_time`), which `datetime.fromtimestamp` rounds
    /// half to even to the microsecond (pytime.c
    /// `_PyTime_DoubleToDenominator`), so mtimes less than a microsecond
    /// apart can compare equal. None for a time upstream cannot read, which
    /// it compares as the epoch after a warning (`get_file_stat`,
    /// `FileGenerator._safely_get_file_stats`): one outside the years
    /// `datetime` holds, or on Windows one before 1970 or after January 3001.
    pub fn from_mtime(seconds: i64, nanoseconds: u32) -> Option<Self> {
        let float = seconds as f64 + f64::from(nanoseconds) * 1e-9;
        let mut whole = float.trunc();
        let mut fraction = ((float - whole) * 1e6).round_ties_even();
        if fraction >= 1e6 {
            fraction -= 1e6;
            whole += 1.0;
        } else if fraction < 0.0 {
            fraction += 1e6;
            whole -= 1.0;
        }
        let whole = whole as i64;
        READABLE_SECONDS
            .contains(&whole)
            .then(|| Self(whole * MICROS_PER_SECOND + fraction as i64))
    }
    /// A file's mtime from its metadata, as [`Modified::from_mtime`] reads it.
    pub fn from_metadata(metadata: &std::fs::Metadata) -> Option<Self> {
        #[cfg(unix)]
        {
            use std::os::unix::fs::MetadataExt;
            let nanoseconds = u32::try_from(metadata.mtime_nsec()).ok()?;
            Self::from_mtime(metadata.mtime(), nanoseconds)
        }
        #[cfg(not(unix))]
        {
            let (seconds, nanoseconds) = split_system_time(metadata.modified().ok()?)?;
            Self::from_mtime(seconds, nanoseconds)
        }
    }
}
#[cfg(test)]
pub(crate) fn set_unreadable_mtime(path: &Path) -> bool {
    use std::time::{Duration, UNIX_EPOCH};
    let time = if cfg!(windows) {
        UNIX_EPOCH - Duration::from_secs(315_619_200)
    } else {
        UNIX_EPOCH + Duration::from_secs(253_402_387_200)
    };
    std::fs::File::options()
        .write(true)
        .open(path)
        .and_then(|file| file.set_modified(time))
        .is_ok()
        && std::fs::metadata(path)
            .and_then(|metadata| metadata.modified())
            .is_ok_and(|held| held == time)
}
#[cfg(any(not(unix), test))]
fn split_system_time(time: std::time::SystemTime) -> Option<(i64, u32)> {
    match time.duration_since(std::time::UNIX_EPOCH) {
        Ok(after) => Some((i64::try_from(after.as_secs()).ok()?, after.subsec_nanos())),
        Err(before) => {
            let before = before.duration();
            let seconds = i64::try_from(before.as_secs()).ok()?;
            Some(match before.subsec_nanos() {
                0 => (-seconds, 0),
                nanoseconds => (-seconds - 1, 1_000_000_000 - nanoseconds),
            })
        }
    }
}

/// One side's entry: its name below the side's root, its size, and its mtime.
///
/// A name is the comparator's key, upstream's `compare_key`: an object's
/// key past the prefix, or a file's path past the root with `/` between its
/// components (`find_dest_path_comp_key`).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Entry<N> {
    pub name: N,
    pub size: u64,
    pub modified: Modified,
}

/// Which side of a sync is local, which decides what "newer" compares.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LocalSide {
    /// An upload: the files are the source.
    Source,
    /// A download: the files are the destination.
    Destination,
}

/// A side whose entries the comparator pulls in name order.
pub trait Destination {
    /// How the side holds an entry's name: an object's key past the
    /// prefix, or a walked file's [`LocalName`].
    type Name: AsRef<[u8]>;
    /// Why the side could not name its next entry, which ends the sync.
    type Error;
    /// The next entry in name order, or None once every entry was named.
    ///
    /// # Errors
    /// Returns [`Destination::Error`] when the side cannot be read further.
    fn next_entry(&mut self) -> Result<Option<Entry<Self::Name>>, Self::Error>;
}

/// What removes a name only the destination holds, under `--delete`, from
/// a destination that holds names as `N`.
///
/// Breaking stops the comparator, as an exception raised by upstream's
/// delete submitter would stop its comparator.
pub trait Remover<N> {
    /// Removes `entry` from the destination, or schedules its removal.
    fn remove(&mut self, entry: Entry<N>) -> ControlFlow<()>;
}
impl<N, F: FnMut(Entry<N>) -> ControlFlow<()>> Remover<N> for F {
    fn remove(&mut self, entry: Entry<N>) -> ControlFlow<()> {
        self(entry)
    }
}

/// How the comparator paired one source entry.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Pairing {
    /// The destination holds the name too: whether the strategy for a name
    /// both sides hold transfers the source.
    Both(bool),
    /// Only the source holds the name. The caller decides it by the
    /// strategy for that case, [`super::SourceOnly`].
    SourceOnly,
    /// The remover stopped the comparator before it reached the source's
    /// name.
    Stopped,
}

/// Upstream's merge of a sync's two sides, driven by the source.
#[derive(Debug)]
pub struct Comparator<D: Destination> {
    strategies: Strategies,
    local: LocalSide,
    destination: D,
    pending: Option<Entry<D::Name>>,
    exhausted: bool,
}
impl<D: Destination> Comparator<D> {
    /// A comparator of the sources to come with every entry of `destination`.
    pub fn new(strategies: Strategies, local: LocalSide, destination: D) -> Self {
        Self {
            strategies,
            local,
            destination,
            pending: None,
            exhausted: false,
        }
    }
    /// Pairs the next source entry, in name order.
    ///
    /// Each destination entry that sorts before it holds a name only the
    /// destination has, which `remover` gets under `--delete`; the one of
    /// the same name, if any, is its pair.
    ///
    /// # Errors
    /// Returns the destination's error when it cannot name its next entry.
    pub fn pair(
        &mut self,
        source: &Entry<&[u8]>,
        remover: &mut impl Remover<D::Name>,
    ) -> Result<Pairing, D::Error> {
        while let Some(destination) = self.peek()? {
            match compare_names(source.name, destination.name.as_ref()) {
                Ordering::Less => break,
                Ordering::Equal => {
                    let destination = self.pending.take();
                    return Ok(Pairing::Both(
                        destination
                            .is_some_and(|destination| self.both_sides(source, &destination)),
                    ));
                }
                Ordering::Greater => {
                    let destination = self.pending.take();
                    if self.destination_only(destination, remover).is_break() {
                        return Ok(Pairing::Stopped);
                    }
                }
            }
        }
        Ok(Pairing::SourceOnly)
    }
    /// Pairs every destination entry no source named, once the source is
    /// done. Breaks when `remover` stopped it.
    ///
    /// # Errors
    /// Returns the destination's error when it cannot name its next entry.
    pub fn finish(
        &mut self,
        remover: &mut impl Remover<D::Name>,
    ) -> Result<ControlFlow<()>, D::Error> {
        while self.peek()?.is_some() {
            let destination = self.pending.take();
            if self.destination_only(destination, remover).is_break() {
                return Ok(ControlFlow::Break(()));
            }
        }
        Ok(ControlFlow::Continue(()))
    }
    /// The destination, once the comparator is done with it.
    pub fn into_destination(self) -> D {
        self.destination
    }
    fn peek(&mut self) -> Result<Option<&Entry<D::Name>>, D::Error> {
        if self.pending.is_none() && !self.exhausted {
            self.pending = self.destination.next_entry()?;
            self.exhausted = self.pending.is_none();
        }
        Ok(self.pending.as_ref())
    }
    fn both_sides(&self, source: &Entry<&[u8]>, destination: &Entry<D::Name>) -> bool {
        let resized = source.size != destination.size;
        // `BaseSync.compare_time`: an upload's `delta` is the object's time
        // less the file's, and a download's the file's less the object's, so
        // either transfers once the file is newer.
        let local_is_newer = || match self.local {
            LocalSide::Source => source.modified > destination.modified,
            LocalSide::Destination => destination.modified > source.modified,
        };
        match self.strategies.both {
            BothSides::SizeAndLastModified => resized || local_is_newer(),
            BothSides::SizeOnly => resized,
            BothSides::ExactTimestamps => match self.local {
                LocalSide::Source => resized || local_is_newer(),
                LocalSide::Destination => resized || source.modified != destination.modified,
            },
            BothSides::Never => false,
            BothSides::Always => true,
        }
    }
    fn destination_only(
        &self,
        destination: Option<Entry<D::Name>>,
        remover: &mut impl Remover<D::Name>,
    ) -> ControlFlow<()> {
        match (self.strategies.destination_only, destination) {
            (DestinationOnly::Delete, Some(destination)) => remover.remove(destination),
            (DestinationOnly::Keep, _) | (_, None) => ControlFlow::Continue(()),
        }
    }
}

/// The order upstream's comparator takes two names in: Python's `str` order.
///
/// That is the order of their code points, a local name's decoded with
/// surrogate escapes. An S3 listing names keys in the same order, as UTF-8
/// bytes, and a local walk lists each directory so (`transfer::listing_order`).
pub fn compare_names(a: &[u8], b: &[u8]) -> Ordering {
    crate::transfer::python_code_points(a).cmp(crate::transfer::python_code_points(b))
}

/// The name a walked file at `relative` is paired on, with `/` between components.
pub fn local_name(relative: &Path) -> Cow<'_, [u8]> {
    let bytes = relative.as_os_str().as_encoded_bytes();
    if cfg!(windows) && bytes.contains(&b'\\') {
        Cow::Owned(bytes.iter().map(|&byte| slash(byte)).collect())
    } else {
        Cow::Borrowed(bytes)
    }
}
/// A walked file's name, as [`local_name`] spells it, which turns back into
/// the path below its root that it names.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct LocalName {
    name: Vec<u8>,
    /// The path itself, which bytes alone cannot safely rebuild where the
    /// encoding is not the OS's own.
    #[cfg(not(unix))]
    relative: PathBuf,
}
impl LocalName {
    /// The name of the walked file at `relative`, its path below its root.
    pub fn from_relative_path(relative: PathBuf) -> Self {
        #[cfg(unix)]
        {
            Self {
                name: relative.into_os_string().into_encoded_bytes(),
            }
        }
        #[cfg(not(unix))]
        {
            Self {
                name: local_name(&relative).into_owned(),
                relative,
            }
        }
    }
    /// The name the comparator pairs the file on.
    pub fn as_bytes(&self) -> &[u8] {
        &self.name
    }
    /// The path below its root of the file this names.
    pub fn into_relative_path(self) -> PathBuf {
        #[cfg(unix)]
        {
            use std::os::unix::ffi::OsStringExt;
            PathBuf::from(std::ffi::OsString::from_vec(self.name))
        }
        #[cfg(not(unix))]
        {
            self.relative
        }
    }
}
impl AsRef<[u8]> for LocalName {
    fn as_ref(&self) -> &[u8] {
        self.as_bytes()
    }
}
fn slash(byte: u8) -> u8 {
    if cfg!(windows) && byte == b'\\' {
        b'/'
    } else {
        byte
    }
}

#[cfg(test)]
mod tests;
