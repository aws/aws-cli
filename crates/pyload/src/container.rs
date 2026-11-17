//! Native executable section readers, including foreign-format data fixtures.
#![forbid(unsafe_code)]
mod elf;
mod file;
mod macho;
mod pe;
pub use file::{LocateFileError, ReadPayloadError, locate_file, read_payload};

pub const ARTIFACT_BYTES_MAX: u64 = 1024 * 1024 * 1024;
const METADATA_BYTES_MAX: u64 = 1024 * 1024;
const METADATA_ITEMS_MAX: u64 = 4096;

pub const PAYLOAD_SECTION_NAME: &str = ".pyload";
pub const MACHO_PAYLOAD_SEGMENT_NAME: &str = "__DATA_CONST";
pub const MACHO_PAYLOAD_SECTION_NAME: &str = "__pyload";
pub const MACHO_PAYLOAD_CONTAINER_NAME: &str = "__DATA_CONST,__pyload";
pub const PAYLOAD_SECTION_DESCRIPTION: &str = ".pyload or __DATA_CONST,__pyload";
const SHF_WRITE: u64 = 0x1;
const SHF_ALLOC: u64 = 0x2;
const LC_SEGMENT: u64 = 0x1;
const LC_SEGMENT_64: u64 = 0x19;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    NotExecutable,
    UnsupportedElf,
    TruncatedElf,
    UnsupportedMachO,
    TruncatedMachO,
    UnsupportedPe,
    TruncatedPe,
    MissingPayloadSection,
    InvalidPayloadSection,
    DuplicatePayloadSection,
    PayloadSectionWritable,
    PayloadSectionNotAllocated,
    Overflow,
    ArtifactLimitExceeded,
    ContainerLimitExceeded,
    NotRegularFile,
    UnexpectedEndOfFile,
}
impl std::fmt::Display for Error {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{self:?}")
    }
}
impl std::error::Error for Error {}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Located<'a> {
    pub container: &'static str,
    pub name: &'static str,
    pub offset: u64,
    pub bytes: &'a [u8],
}
/// Validated file extent, independent of temporary section metadata buffers.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Location {
    pub container: &'static str,
    pub name: &'static str,
    pub offset: u64,
    pub size: u64,
}
impl Location {
    fn in_file(self, size: u64) -> Result<Self, Error> {
        if add(self.offset, self.size)? > size {
            return Err(Error::InvalidPayloadSection);
        }
        Ok(self)
    }
}
#[derive(Clone, Copy, Debug)]
enum Endian {
    Little,
    Big,
}
impl Endian {
    fn read(self, bytes: &[u8], offset: usize, width: usize) -> u64 {
        let mut value = 0;
        for index in 0..width {
            let shift = match self {
                Self::Little => index,
                Self::Big => width - 1 - index,
            } * 8;
            value |= u64::from(bytes[offset + index]) << shift;
        }
        value
    }
}
pub fn locate(bytes: &[u8]) -> Result<Located<'_>, Error> {
    let location = if bytes.starts_with(b"\x7fELF") {
        elf::locate(bytes)?
    } else if macho::magic(bytes).is_some() {
        macho::locate(bytes, bytes.len() as u64)?
    } else if bytes.starts_with(b"MZ") {
        pe::locate(bytes)?
    } else {
        return Err(Error::NotExecutable);
    };
    Ok(Located {
        container: location.container,
        name: location.name,
        offset: location.offset,
        bytes: range(
            bytes,
            location.offset,
            location.size,
            Error::InvalidPayloadSection,
        )?,
    })
}
fn add(a: u64, b: u64) -> Result<u64, Error> {
    a.checked_add(b).ok_or(Error::Overflow)
}
fn range(bytes: &[u8], start: u64, len: u64, invalid: Error) -> Result<&[u8], Error> {
    let end = add(start, len)?;
    let start = usize::try_from(start).map_err(|_| Error::Overflow)?;
    let end = usize::try_from(end).map_err(|_| Error::Overflow)?;
    bytes.get(start..end).ok_or(invalid)
}

#[cfg(test)]
mod tests;
