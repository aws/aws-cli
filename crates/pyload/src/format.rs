//! Strict, allocation-bounded ZIPPY003 validation.
#![forbid(unsafe_code)]

mod layout;
mod limits;
mod lookup;
mod types;
mod validate;

pub use layout::{entry_name, payload_extent, read_header, sections, validate_entry_shape};
pub use lookup::{LookupResult, lookup_entry_index};
pub use types::{
    EMPTY_CONTROL, ENTRY_META_SIZE, Entry, EntryMeta, Error, GROUP_WIDTH, HEADER_SIZE, Header,
    LookupSummary, MAGIC, Payload, Sections, Summary, flags,
};
pub const PAYLOAD_BYTES_MAX: usize = 256 * 1024 * 1024;
pub use validate::parse;

pub fn fnv1a64(bytes: &[u8]) -> u64 {
    bytes.iter().fold(0xcbf2_9ce4_8422_2325, |hash, byte| {
        (hash ^ u64::from(*byte)).wrapping_mul(0x100_0000_01b3)
    })
}
pub const fn h2(hash: u64) -> u8 {
    (hash >> 57) as u8
}

pub(crate) fn read_u16(bytes: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes([bytes[offset], bytes[offset + 1]])
}
pub(crate) fn read_u32(bytes: &[u8], offset: usize) -> u32 {
    let mut value = [0; 4];
    value.copy_from_slice(&bytes[offset..offset + 4]);
    u32::from_le_bytes(value)
}
pub(crate) fn read_u64(bytes: &[u8], offset: usize) -> u64 {
    let mut value = [0; 8];
    value.copy_from_slice(&bytes[offset..offset + 8]);
    u64::from_le_bytes(value)
}
pub(crate) fn offset(value: u64) -> Result<usize, Error> {
    usize::try_from(value).map_err(|_| Error::Overflow)
}
pub(crate) fn add(a: usize, b: usize) -> Result<usize, Error> {
    a.checked_add(b).ok_or(Error::Overflow)
}
pub fn read_index_bytes(index: &[u8], width: u32, bucket: usize) -> Result<u32, Error> {
    if !matches!(width, 2 | 4) {
        return Err(Error::InvalidIndexWidth);
    }
    let start = bucket.checked_mul(width as usize).ok_or(Error::Overflow)?;
    let end = add(start, width as usize)?;
    let bytes = index.get(start..end).ok_or(Error::InvalidIndex)?;
    Ok(if width == 2 {
        u32::from(read_u16(bytes, 0))
    } else {
        read_u32(bytes, 0)
    })
}
pub fn entry_from_meta(name: &[u8], meta: EntryMeta) -> Entry<'_> {
    Entry {
        name_hash: fnv1a64(name),
        name,
        data_offset: u64::from(meta.data_offset),
        compressed_len: u64::from(meta.stored_len),
        uncompressed_len: u64::from(meta.raw_len),
        flags: u32::from(meta.flags),
    }
}

#[cfg(any(test, feature = "testing"))]
pub mod testing;
#[cfg(test)]
mod tests;
