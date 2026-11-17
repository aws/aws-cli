use super::*;
#[derive(Clone, Copy)]
pub(super) struct Header {
    wide: bool,
    endian: Endian,
    pub offset: u64,
    pub size: u64,
    pub count: u64,
    pub strings: u64,
}
#[derive(Clone, Copy)]
pub(super) struct Section {
    name: u64,
    flags: u64,
    pub offset: u64,
    pub size: u64,
    pub link: u64,
}

pub(super) fn locate(bytes: &[u8]) -> Result<Location, Error> {
    let mut header = header(bytes)?;
    resolve_extended(bytes, &mut header)?;
    if header.count == 0 || header.strings >= header.count {
        return Err(Error::UnsupportedElf);
    }
    let strings = section(bytes, header, header.strings)?;
    let strings = range(bytes, strings.offset, strings.size, Error::TruncatedElf)
        .map_err(|_| Error::TruncatedElf)?;
    sections(bytes, header, strings, bytes.len() as u64)
}

pub(super) fn resolve_extended(bytes: &[u8], header: &mut Header) -> Result<(), Error> {
    if header.count == 0 || header.strings == 0xffff {
        let zero = section(bytes, *header, 0)?;
        if header.count == 0 {
            header.count = u64::from(u32::try_from(zero.size).map_err(|_| Error::UnsupportedElf)?);
        }
        if header.strings == 0xffff {
            header.strings = zero.link;
        }
    }
    Ok(())
}

pub(super) fn sections(
    bytes: &[u8],
    header: Header,
    strings: &[u8],
    file_size: u64,
) -> Result<Location, Error> {
    let last_nul = strings
        .iter()
        .rposition(|&byte| byte == 0)
        .ok_or(Error::TruncatedElf)?;
    let strings = &strings[..=last_nul];
    let mut found = None;
    for index in 0..header.count {
        let section = section(bytes, header, index)?;
        let suffix = strings
            .get(section.name as usize..)
            .ok_or(Error::TruncatedElf)?;
        if suffix.is_empty() {
            return Err(Error::TruncatedElf);
        }
        if !is_payload_name(suffix) {
            continue;
        }
        if section.flags & SHF_ALLOC == 0 {
            return Err(Error::PayloadSectionNotAllocated);
        }
        if section.flags & SHF_WRITE != 0 {
            return Err(Error::PayloadSectionWritable);
        }
        if found.is_some() {
            return Err(Error::DuplicatePayloadSection);
        }
        found = Some(
            Location {
                container: "elf-section",
                name: PAYLOAD_SECTION_NAME,
                offset: section.offset,
                size: section.size,
            }
            .in_file(file_size)?,
        );
    }
    found.ok_or(Error::MissingPayloadSection)
}

fn is_payload_name(names: &[u8]) -> bool {
    names
        .strip_prefix(PAYLOAD_SECTION_NAME.as_bytes())
        .is_some_and(|rest| rest.first() == Some(&0))
}

pub(super) fn header(bytes: &[u8]) -> Result<Header, Error> {
    if bytes.len() < 16 {
        return Err(Error::TruncatedElf);
    }
    let wide = match bytes[4] {
        1 => false,
        2 => true,
        _ => return Err(Error::UnsupportedElf),
    };
    let endian = match bytes[5] {
        1 => Endian::Little,
        2 => Endian::Big,
        _ => return Err(Error::UnsupportedElf),
    };
    if bytes.len() < if wide { 64 } else { 52 } {
        return Err(Error::TruncatedElf);
    }
    let (offset, size, count, strings) = if wide {
        (40, 58, 60, 62)
    } else {
        (32, 46, 48, 50)
    };
    Ok(Header {
        wide,
        endian,
        offset: endian.read(bytes, offset, if wide { 8 } else { 4 }),
        size: endian.read(bytes, size, 2),
        count: endian.read(bytes, count, 2),
        strings: endian.read(bytes, strings, 2),
    })
}

pub(super) fn section(bytes: &[u8], header: Header, index: u64) -> Result<Section, Error> {
    let min = if header.wide { 64 } else { 40 };
    if header.size < min {
        return Err(Error::UnsupportedElf);
    }
    let offset = add(
        header.offset,
        header.size.checked_mul(index).ok_or(Error::Overflow)?,
    )?;
    let bytes = range(bytes, offset, min, Error::TruncatedElf)?;
    let read = |offset, width| header.endian.read(bytes, offset, width);
    Ok(if header.wide {
        Section {
            name: read(0, 4),
            flags: read(8, 8),
            offset: read(24, 8),
            size: read(32, 8),
            link: read(40, 4),
        }
    } else {
        Section {
            name: read(0, 4),
            flags: read(8, 4),
            offset: read(16, 4),
            size: read(20, 4),
            link: read(24, 4),
        }
    })
}
