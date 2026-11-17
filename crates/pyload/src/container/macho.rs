use super::*;

pub(super) fn magic(bytes: &[u8]) -> Option<(bool, Endian)> {
    match bytes.get(..4)? {
        b"\xce\xfa\xed\xfe" => Some((false, Endian::Little)),
        b"\xcf\xfa\xed\xfe" => Some((true, Endian::Little)),
        b"\xfe\xed\xfa\xce" => Some((false, Endian::Big)),
        b"\xfe\xed\xfa\xcf" => Some((true, Endian::Big)),
        _ => None,
    }
}

#[derive(Clone, Copy)]
pub(super) struct Header {
    endian: Endian,
    pub command_offset: u64,
    pub command_size: u64,
    pub command_count: u64,
}

pub(super) fn header(bytes: &[u8]) -> Result<Header, Error> {
    let (wide, endian) = magic(bytes).ok_or(Error::NotExecutable)?;
    let size = if wide { 32 } else { 28 };
    if bytes.len() < size {
        return Err(Error::TruncatedMachO);
    }
    Ok(Header {
        endian,
        command_offset: size as u64,
        command_size: endian.read(bytes, 20, 4),
        command_count: endian.read(bytes, 16, 4),
    })
}

pub(super) fn locate(bytes: &[u8], file_size: u64) -> Result<Location, Error> {
    let header = header(bytes)?;
    let end = add(header.command_offset, header.command_size)?;
    if end > bytes.len() as u64 {
        return Err(Error::TruncatedMachO);
    }
    let commands = &bytes[..end as usize];
    let mut offset = header.command_offset;
    let mut found = None;
    for _ in 0..header.command_count {
        let command = command(commands, header.endian, offset)?;
        if matches!(command.kind, LC_SEGMENT | LC_SEGMENT_64)
            && let Some(section) = segment(
                file_size,
                command.bytes,
                command.kind == LC_SEGMENT_64,
                header.endian,
            )?
        {
            if found.is_some() {
                return Err(Error::DuplicatePayloadSection);
            }
            found = Some(section);
        }
        offset = command.end;
    }
    found.ok_or(Error::MissingPayloadSection)
}

struct Command<'a> {
    kind: u64,
    bytes: &'a [u8],
    end: u64,
}

fn command(commands: &[u8], endian: Endian, offset: u64) -> Result<Command<'_>, Error> {
    let header = range(commands, offset, 8, Error::TruncatedMachO)?;
    let kind = endian.read(header, 0, 4);
    let size = endian.read(header, 4, 4);
    if size < 8 {
        return Err(Error::UnsupportedMachO);
    }
    Ok(Command {
        kind,
        bytes: range(commands, offset, size, Error::TruncatedMachO)?,
        end: add(offset, size)?,
    })
}

fn segment(
    file_size: u64,
    bytes: &[u8],
    wide: bool,
    endian: Endian,
) -> Result<Option<Location>, Error> {
    let (header, size, count_offset) = if wide { (72, 80, 64) } else { (56, 68, 48) };
    if bytes.len() < header {
        return Err(Error::UnsupportedMachO);
    }
    let count = endian.read(bytes, count_offset, 4);
    let table_end = add(
        header as u64,
        count.checked_mul(size as u64).ok_or(Error::Overflow)?,
    )?;
    if table_end > bytes.len() as u64 {
        return Err(Error::TruncatedMachO);
    }
    let mut found = None;
    for index in 0..count as usize {
        let section = &bytes[header + index * size..header + (index + 1) * size];
        if !fixed_name(&section[..16], MACHO_PAYLOAD_SECTION_NAME.as_bytes())
            || !fixed_name(&section[16..32], MACHO_PAYLOAD_SEGMENT_NAME.as_bytes())
        {
            continue;
        }
        if found.is_some() {
            return Err(Error::DuplicatePayloadSection);
        }
        let (offset_at, size_at, width) = if wide { (48, 40, 8) } else { (40, 36, 4) };
        let offset = endian.read(section, offset_at, 4);
        let len = endian.read(section, size_at, width);
        found = Some(
            Location {
                container: "mach-o-section",
                name: MACHO_PAYLOAD_CONTAINER_NAME,
                offset,
                size: len,
            }
            .in_file(file_size)?,
        );
    }
    Ok(found)
}

fn fixed_name(field: &[u8], expected: &[u8]) -> bool {
    field.starts_with(expected) && (field.len() == expected.len() || field[expected.len()] == 0)
}
