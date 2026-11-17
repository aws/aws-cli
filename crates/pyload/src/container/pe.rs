// Layout: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
use super::*;

pub(super) const HEADER_SIZE: u64 = 24;
pub(super) const SECTION_SIZE: u64 = 40;

#[derive(Clone, Copy, Debug)]
pub(super) struct Header {
    pub count: u64,
    pub optional_size: u64,
}

pub(super) fn offset(dos: &[u8]) -> Result<u64, Error> {
    if dos.len() < 64 {
        return Err(Error::TruncatedPe);
    }
    let offset = Endian::Little.read(dos, 60, 4);
    if offset < 64 {
        return Err(Error::UnsupportedPe);
    }
    Ok(offset)
}

pub(super) fn header(bytes: &[u8]) -> Result<Header, Error> {
    if bytes.len() < HEADER_SIZE as usize {
        return Err(Error::TruncatedPe);
    }
    if !bytes.starts_with(b"PE\0\0") {
        return Err(Error::UnsupportedPe);
    }
    let header = Header {
        count: Endian::Little.read(bytes, 6, 2),
        optional_size: Endian::Little.read(bytes, 20, 2),
    };
    if header.count == 0 || header.optional_size < 2 {
        return Err(Error::UnsupportedPe);
    }
    if header.count > METADATA_ITEMS_MAX {
        return Err(Error::ContainerLimitExceeded);
    }
    Ok(header)
}

pub(super) fn optional(bytes: &[u8]) -> Result<(), Error> {
    if bytes.len() < 2 {
        return Err(Error::TruncatedPe);
    }
    let minimum = match Endian::Little.read(bytes, 0, 2) {
        0x10b => 96,
        0x20b => 112,
        _ => return Err(Error::UnsupportedPe),
    };
    if bytes.len() < minimum {
        return Err(Error::TruncatedPe);
    }
    Ok(())
}

pub(super) fn sections(bytes: &[u8], count: u64, file_size: u64) -> Result<Location, Error> {
    let table = range(bytes, 0, count * SECTION_SIZE, Error::TruncatedPe)?;
    let mut found = None;
    for section in table.chunks_exact(SECTION_SIZE as usize) {
        if &section[..8] != b".pyload\0" {
            continue;
        }
        if found.is_some() {
            return Err(Error::DuplicatePayloadSection);
        }
        let flags = Endian::Little.read(section, 36, 4);
        if flags & 0x8000_0000 != 0 {
            return Err(Error::PayloadSectionWritable);
        }
        if flags & 0x4000_0000 == 0 {
            return Err(Error::PayloadSectionNotAllocated);
        }
        let size = Endian::Little.read(section, 8, 4);
        let raw_size = Endian::Little.read(section, 16, 4);
        let offset = Endian::Little.read(section, 20, 4);
        if size == 0 || size > raw_size || add(offset, raw_size)? > file_size {
            return Err(Error::InvalidPayloadSection);
        }
        found = Some(Location {
            container: "pe-section",
            name: PAYLOAD_SECTION_NAME,
            offset,
            size,
        });
    }
    found.ok_or(Error::MissingPayloadSection)
}

pub(super) fn locate(bytes: &[u8]) -> Result<Location, Error> {
    let offset = offset(bytes)?;
    let header = header(range(bytes, offset, HEADER_SIZE, Error::TruncatedPe)?)?;
    let optional_start = add(offset, HEADER_SIZE)?;
    optional(range(
        bytes,
        optional_start,
        header.optional_size,
        Error::TruncatedPe,
    )?)?;
    let table = range(
        bytes,
        add(optional_start, header.optional_size)?,
        header.count * SECTION_SIZE,
        Error::TruncatedPe,
    )?;
    sections(table, header.count, bytes.len() as u64)
}
