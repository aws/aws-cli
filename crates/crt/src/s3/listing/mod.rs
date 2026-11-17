mod driver;
mod message;
mod native;
mod page;
mod parse;
mod probe;
mod request;
mod stats;
#[cfg(test)]
mod tests;
use crt_sys::{self as ffi, native as c};
#[cfg(test)]
pub(crate) use driver::{Action, NextActionInputs, next_action};
pub(super) use parse::{parse_document, xml_text};
pub use probe::{ProbeState, TokenProbe};
pub use stats::{ListPhaseStats, ListStats};
use std::time::Instant;

const PAGE_BODY_BYTES_MAX: usize = 16 * 1024 * 1024;
const PAGE_COUNT_MAX: usize = 1_000_000;
/// Which element of the page an entry came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EntryKind {
    /// An object key returned by ListObjectsV2.
    Object,
    /// A prefix grouped by the requested delimiter.
    CommonPrefix,
    /// A bucket returned by ListBuckets.
    Bucket,
}
/// A parsed LastModified or CreationDate: the calendar fields in the local
/// timezone, as the AWS CLI renders them, and the exact service timestamp.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct LastModified {
    pub year: i32,
    /// 1 through 12.
    pub month: i32,
    pub day: i32,
    pub hour: i32,
    pub minute: i32,
    pub second: i32,
    /// Seconds since the Unix epoch, independent of the local timezone.
    pub epoch_seconds: i64,
}
/// One listed object, common prefix, or bucket, handed to the listing's sink
/// once the whole page is read. Consumers that must not depend on the local
/// timezone, such as downloaded-file mtime preservation, read the date's
/// `epoch_seconds`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ListEntry {
    /// Which element of the page the entry came from.
    pub kind: EntryKind,
    /// The object key or common prefix, URL-decoded, or the bucket name.
    pub name: Vec<u8>,
    /// The object size in bytes; zero for prefixes and buckets.
    pub size: u64,
    /// LastModified for objects and CreationDate for buckets; None when the
    /// page carried none.
    pub date: Option<LastModified>,
    /// What the Glacier rule reads from the object's StorageClass; a listing
    /// carries no restore state.
    pub archive: super::ArchiveState,
    /// The object's `ETag`, XML-decoded, when the listing records what a
    /// download is conditioned on ([`ListOptions::object_conditions`]) and
    /// the page carried one.
    pub etag: Option<Vec<u8>>,
    /// What the object's `ChecksumType` and `ChecksumAlgorithm` say of its
    /// full-object checksum, when the listing records it.
    pub full_object_checksum: super::FullObjectChecksum,
}
impl ListEntry {
    /// An empty entry of `kind`.
    pub fn new(kind: EntryKind) -> Self {
        Self {
            kind,
            name: Vec::new(),
            size: 0,
            date: None,
            archive: super::ArchiveState::default(),
            etag: None,
            full_object_checksum: super::FullObjectChecksum::default(),
        }
    }
}
#[derive(Debug, Clone, Copy)]
pub struct ListOptions<'a> {
    pub bucket: &'a [u8],
    pub prefix: &'a [u8],
    pub request_payer: &'a [u8],
    pub recursive: bool,
    pub page_size: u32,
    pub prefetch: bool,
    /// The `user-agent` every page sends; None sends the runtime's.
    pub user_agent: Option<&'a [u8]>,
    /// Records each object's `ETag` and checksum fields, which a download
    /// is conditioned on; other listings skip them.
    pub object_conditions: bool,
}
pub fn parse_list_date(value: &[u8]) -> Option<LastModified> {
    list_date_or_error(value).ok()
}
fn list_date_or_error(value: &[u8]) -> Result<LastModified, i32> {
    let mut date = c::Date::default();
    // SAFETY: the shim writes only its mirrored date record and consumes the cursor synchronously.
    crate::crt_error::check(unsafe {
        c::zaws_parse_date(ffi::AwsByteCursor::from_bytes(value), &mut date)
    })?;
    let [year, month, day, hour, minute, second] = date.fields;
    Ok(LastModified {
        year,
        month,
        day,
        hour,
        minute,
        second,
        epoch_seconds: date.epoch_seconds,
    })
}
fn elapsed(start: Instant) -> u64 {
    nanos(start.elapsed())
}
fn nanos(duration: std::time::Duration) -> u64 {
    duration.as_nanos().min(u128::from(u64::MAX)) as u64
}
