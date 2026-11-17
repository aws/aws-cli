//! Payload fixture writer used by reader tests and endpoint model fixtures.
use super::*;
use crate::swiss_group::ProbeSeq;

pub const COLLISION_NAMES: [&[u8]; 33] = [
    b"probe7",
    b"probe49",
    b"probe74",
    b"probe120",
    b"probe173",
    b"probe241",
    b"probe366",
    b"probe447",
    b"probe458",
    b"probe494",
    b"probe502",
    b"probe656",
    b"probe735",
    b"probe744",
    b"probe779",
    b"probe788",
    b"probe797",
    b"probe872",
    b"probe890",
    b"probe951",
    b"probe1110",
    b"probe1143",
    b"probe1204",
    b"probe1239",
    b"probe1275",
    b"probe1396",
    b"probe1411",
    b"probe1532",
    b"probe1583",
    b"probe1600",
    b"probe1653",
    b"probe1709",
    b"probe1734",
];
#[derive(Clone, Copy, Debug)]
pub struct TestEntry<'a> {
    pub name: &'a [u8],
    pub payload: &'a [u8],
    pub raw_len: u32,
    pub flags: u16,
}
pub fn entry<'a>(name: &'a [u8], payload: &'a [u8], flags: u32) -> TestEntry<'a> {
    TestEntry {
        name,
        payload,
        raw_len: payload.len() as u32,
        flags: flags as u16,
    }
}
pub fn minimal(name: &[u8], payload: &[u8], flags: u32) -> Vec<u8> {
    blob(&[entry(name, payload, flags)], false, 2)
}
pub fn collisions(linear: bool) -> Vec<u8> {
    let entries: Vec<_> = COLLISION_NAMES
        .iter()
        .map(|name| entry(name, b"\0", flags::BYTECODE))
        .collect();
    blob(&entries, linear, 2)
}
pub fn blob(entries: &[TestEntry<'_>], linear: bool, width: usize) -> Vec<u8> {
    blob_in_order(entries, linear, width, Order::Sorted)
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Order {
    Sorted,
    Given,
}
fn blob_in_order(entries: &[TestEntry<'_>], linear: bool, width: usize, order: Order) -> Vec<u8> {
    let mut entries = entries.to_vec();
    if order == Order::Sorted {
        entries.sort_by_key(|entry| entry.name);
    }
    let mut buckets = GROUP_WIDTH;
    while entries.len() * 8 > buckets * 7 {
        buckets *= 2;
    }
    let index = HEADER_SIZE + buckets + GROUP_WIDTH;
    let meta = index + buckets * width;
    let strings = meta + entries.len() * ENTRY_META_SIZE;
    let data = strings + entries.iter().map(|entry| entry.name.len()).sum::<usize>();
    let len = data
        + entries
            .iter()
            .map(|entry| entry.payload.len())
            .sum::<usize>();
    let mut bytes = vec![0; len];
    bytes[..8].copy_from_slice(MAGIC);
    put32(&mut bytes, 8, entries.len() as u32);
    put32(&mut bytes, 12, buckets as u32);
    put32(&mut bytes, 20, width as u32);
    for (at, value) in [
        (24, HEADER_SIZE),
        (32, index),
        (40, meta),
        (48, strings),
        (56, data),
    ] {
        put64(&mut bytes, at, value as u64);
    }
    bytes[HEADER_SIZE..index].fill(EMPTY_CONTROL);
    write_entries(&mut bytes, &entries, (meta, strings, data));
    write_lookup(&mut bytes, &entries, (buckets, index, width), linear);
    bytes.copy_within(
        HEADER_SIZE..HEADER_SIZE + GROUP_WIDTH,
        HEADER_SIZE + buckets,
    );
    bytes
}
fn write_entries(bytes: &mut [u8], entries: &[TestEntry<'_>], offsets: (usize, usize, usize)) {
    let (meta, strings, data) = offsets;
    let (mut name_offset, mut data_offset) = (0, 0);
    for (index, entry) in entries.iter().enumerate() {
        let start = meta + index * ENTRY_META_SIZE;
        for (at, value) in [
            (0, name_offset),
            (4, entry.name.len()),
            (8, data_offset),
            (12, entry.payload.len()),
            (16, entry.raw_len as usize),
        ] {
            put32(bytes, start + at, value as u32);
        }
        put16(bytes, start + 20, entry.flags);
        bytes[strings + name_offset..strings + name_offset + entry.name.len()]
            .copy_from_slice(entry.name);
        bytes[data + data_offset..data + data_offset + entry.payload.len()]
            .copy_from_slice(entry.payload);
        name_offset += entry.name.len();
        data_offset += entry.payload.len();
    }
}
fn write_lookup(
    bytes: &mut [u8],
    entries: &[TestEntry<'_>],
    table: (usize, usize, usize),
    linear: bool,
) {
    let (buckets, index_offset, width) = table;
    for (index, entry) in entries.iter().enumerate() {
        let hash = fnv1a64(entry.name);
        let mut probe = ProbeSeq::new(hash as usize & (buckets - 1), buckets - 1);
        for _ in 0..buckets / GROUP_WIDTH {
            let empty = (0..GROUP_WIDTH)
                .map(|lane| (probe.bucket + lane) & (buckets - 1))
                .find(|&bucket| bytes[HEADER_SIZE + bucket] == EMPTY_CONTROL);
            if let Some(bucket) = empty {
                bytes[HEADER_SIZE + bucket] = h2(hash);
                let encoded = (index as u32).to_le_bytes();
                bytes[index_offset + bucket * width..index_offset + (bucket + 1) * width]
                    .copy_from_slice(&encoded[..width]);
                break;
            }
            if linear {
                probe.bucket = (probe.bucket + GROUP_WIDTH) & (buckets - 1);
            } else {
                probe.advance();
            }
        }
    }
}
pub fn put16(bytes: &mut [u8], at: usize, value: u16) {
    bytes[at..at + 2].copy_from_slice(&value.to_le_bytes());
}
pub fn put32(bytes: &mut [u8], at: usize, value: u32) {
    bytes[at..at + 4].copy_from_slice(&value.to_le_bytes());
}
pub fn put64(bytes: &mut [u8], at: usize, value: u64) {
    bytes[at..at + 8].copy_from_slice(&value.to_le_bytes());
}

/// Build a checked fixture with the same automatic index width as the Python finder tests.
pub fn build(entries: &[TestEntry<'_>]) -> Result<Vec<u8>, Error> {
    build_in_order(entries, Order::Sorted)
}
/// [`build`] keeping the entries' given order, which may leave the name table unsorted: a
/// payload the packer never emits but the runtime view still accepts.
pub fn build_unsorted(entries: &[TestEntry<'_>]) -> Result<Vec<u8>, Error> {
    build_in_order(entries, Order::Given)
}
fn build_in_order(entries: &[TestEntry<'_>], order: Order) -> Result<Vec<u8>, Error> {
    if entries.is_empty() {
        return Err(Error::EmptyEntryTable);
    }
    u32::try_from(entries.len()).map_err(|_| Error::Overflow)?;
    let mut names = 0usize;
    let mut data = 0usize;
    for entry in entries {
        names = add(names, entry.name.len())?;
        data = add(data, entry.payload.len())?;
        u32::try_from(names).map_err(|_| Error::Overflow)?;
        u32::try_from(data).map_err(|_| Error::Overflow)?;
    }
    let width = if entries.len() <= u16::MAX as usize {
        2
    } else {
        4
    };
    Ok(blob_in_order(entries, false, width, order))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InputTooLarge;
impl std::fmt::Display for InputTooLarge {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("InputTooLarge")
    }
}
impl std::error::Error for InputTooLarge {}

/// Encode a single raw Zstandard block for a small deterministic test resource.
pub fn raw_zstd_frame(raw: &[u8]) -> Result<Vec<u8>, InputTooLarge> {
    let size = u8::try_from(raw.len()).map_err(|_| InputTooLarge)?;
    let header = ((raw.len() as u32) << 3) | 1;
    let mut bytes = vec![0x28, 0xb5, 0x2f, 0xfd, 0x20, size];
    bytes.extend_from_slice(&header.to_le_bytes()[..3]);
    bytes.extend_from_slice(raw);
    Ok(bytes)
}
