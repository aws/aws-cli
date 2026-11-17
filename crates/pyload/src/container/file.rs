use super::*;
use std::fs::File;
use std::io;

#[derive(Debug)]
pub enum LocateFileError {
    Container(Error),
    Io(io::Error),
}
impl std::fmt::Display for LocateFileError {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Container(error) => error.fmt(out),
            Self::Io(error) => error.fmt(out),
        }
    }
}
impl std::error::Error for LocateFileError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(match self {
            Self::Container(error) => error,
            Self::Io(error) => error,
        })
    }
}
impl From<Error> for LocateFileError {
    fn from(error: Error) -> Self {
        Self::Container(error)
    }
}
impl From<io::Error> for LocateFileError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

#[derive(Debug)]
pub enum ReadPayloadError {
    /// `PayloadLimitExceeded` or `OutOfMemory` for the section buffer.
    Payload(crate::format::Error),
    Io(io::Error),
}
impl std::fmt::Display for ReadPayloadError {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Payload(error) => error.fmt(out),
            Self::Io(error) => error.fmt(out),
        }
    }
}
impl std::error::Error for ReadPayloadError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(match self {
            Self::Payload(error) => error,
            Self::Io(error) => error,
        })
    }
}

/// Locate a section without moving the caller's file position or reading payload bytes.
pub fn locate_file(file: &File) -> Result<Location, LocateFileError> {
    let metadata = file.metadata()?;
    if !metadata.is_file() {
        return Err(Error::NotRegularFile.into());
    }
    let size = metadata.len();
    if size > ARTIFACT_BYTES_MAX {
        return Err(Error::ArtifactLimitExceeded.into());
    }
    let mut header = [0; 64];
    let length = read_positional_all(file, &mut header, 0)?;
    let bytes = &header[..length];
    if bytes.starts_with(b"\x7fELF") {
        return elf(file, bytes, size);
    }
    if bytes.starts_with(b"MZ") {
        return pe(file, bytes, size);
    }
    let header = macho::header(bytes)?;
    if header.command_count > METADATA_ITEMS_MAX {
        return Err(Error::ContainerLimitExceeded.into());
    }
    let length = add(header.command_offset, header.command_size)?;
    let commands = read_metadata(file, 0, length, size)?;
    Ok(macho::locate(&commands, size)?)
}

fn pe(file: &File, bytes: &[u8], size: u64) -> Result<Location, LocateFileError> {
    let offset = pe::offset(bytes)?;
    let header = pe::header(&read_metadata(file, offset, pe::HEADER_SIZE, size)?)?;
    let optional_start = add(offset, pe::HEADER_SIZE)?;
    pe::optional(&read_metadata(
        file,
        optional_start,
        header.optional_size,
        size,
    )?)?;
    let table = read_metadata(
        file,
        add(optional_start, header.optional_size)?,
        header.count * pe::SECTION_SIZE,
        size,
    )?;
    Ok(pe::sections(&table, header.count, size)?)
}

pub(super) fn elf(file: &File, bytes: &[u8], size: u64) -> Result<Location, LocateFileError> {
    let mut header = elf::header(bytes)?;
    let table_offset = header.offset;
    if header.count == 0 || header.strings == 0xffff {
        let length = if bytes[4] == 2 { 64 } else { 40 };
        if add(table_offset, length)? > size {
            return Err(Error::TruncatedElf.into());
        }
        let mut zero = [0; 64];
        read_exact_at(file, &mut zero[..length as usize], table_offset).map_err(
            |error| match error.kind() {
                io::ErrorKind::UnexpectedEof => Error::TruncatedElf.into(),
                _ => LocateFileError::Io(error),
            },
        )?;
        header.offset = 0;
        elf::resolve_extended(&zero[..length as usize], &mut header)?;
    }
    if header.count > METADATA_ITEMS_MAX {
        return Err(Error::ContainerLimitExceeded.into());
    }
    if header.count == 0 || header.strings >= header.count {
        return Err(Error::UnsupportedElf.into());
    }
    let length = header
        .count
        .checked_mul(header.size)
        .ok_or(Error::Overflow)?;
    let table = read_metadata(file, table_offset, length, size)?;
    header.offset = 0;
    let strings = elf::section(&table, header, header.strings)?;
    let names = read_metadata(file, strings.offset, strings.size, size)?;
    Ok(elf::sections(&table, header, &names, size)?)
}

fn read_metadata(
    file: &File,
    offset: u64,
    length: u64,
    size: u64,
) -> Result<Vec<u8>, LocateFileError> {
    if length > METADATA_BYTES_MAX {
        return Err(Error::ContainerLimitExceeded.into());
    }
    if add(offset, length)? > size {
        return Err(Error::UnexpectedEndOfFile.into());
    }
    let mut bytes = allocate(length)?;
    read_exact_at(file, &mut bytes, offset)?;
    Ok(bytes)
}

/// Read the validated payload extent under the payload format's allocation bound.
pub fn read_payload(file: &File, location: Location) -> Result<Vec<u8>, ReadPayloadError> {
    use crate::format::{Error, PAYLOAD_BYTES_MAX};
    if location.size > PAYLOAD_BYTES_MAX as u64 {
        return Err(ReadPayloadError::Payload(Error::PayloadLimitExceeded));
    }
    let mut bytes =
        allocate(location.size).map_err(|_| ReadPayloadError::Payload(Error::OutOfMemory))?;
    read_exact_at(file, &mut bytes, location.offset).map_err(ReadPayloadError::Io)?;
    Ok(bytes)
}

pub(super) fn allocate(length: u64) -> io::Result<Vec<u8>> {
    let length = usize::try_from(length).map_err(|_| io::Error::other("Overflow"))?;
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(length)
        .map_err(|_| io::Error::from(io::ErrorKind::OutOfMemory))?;
    bytes.resize(length, 0);
    Ok(bytes)
}

fn read_exact_at(file: &File, bytes: &mut [u8], offset: u64) -> io::Result<()> {
    let length = bytes.len();
    if read_positional_all(file, bytes, offset)? != length {
        return Err(io::Error::new(
            io::ErrorKind::UnexpectedEof,
            "UnexpectedEndOfFile",
        ));
    }
    Ok(())
}

fn read_positional_all(file: &File, mut bytes: &mut [u8], mut offset: u64) -> io::Result<usize> {
    #[cfg(unix)]
    use std::os::unix::fs::FileExt;
    #[cfg(windows)]
    use std::os::windows::fs::FileExt;
    let length = bytes.len();
    while !bytes.is_empty() {
        #[cfg(unix)]
        let result = file.read_at(bytes, offset);
        #[cfg(windows)]
        let result = file.seek_read(bytes, offset);
        match result {
            Ok(0) => break,
            Ok(count) => {
                offset += count as u64;
                bytes = &mut bytes[count..];
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
            Err(error) => return Err(error),
        }
    }
    Ok(length - bytes.len())
}
