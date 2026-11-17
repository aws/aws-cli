pub const MAGIC: &[u8; 8] = b"ZIPPY003";
pub const HEADER_SIZE: usize = 72;
pub const GROUP_WIDTH: usize = crate::swiss_group::WIDTH;
pub const EMPTY_CONTROL: u8 = 0x80;
pub const ENTRY_META_SIZE: usize = 24;

pub mod flags {
    pub const PACKAGE: u32 = 1;
    pub const BYTECODE: u32 = 2;
    pub const RESOURCE: u32 = 4;
    pub const COMPRESSED: u32 = 8;
    pub const KNOWN: u32 = 15;
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    BadMagic,
    TruncatedHeader,
    EmptyEntryTable,
    TruncatedControl,
    TruncatedLookupIndex,
    TruncatedEntryMeta,
    TruncatedStringTable,
    PayloadOutsideData,
    UnknownFlags,
    ReservedFieldSet,
    InvalidKindFlags,
    InvalidCompressionLengths,
    NameOutsideStringTable,
    HashMismatch,
    UnsortedNames,
    InvalidIndex,
    InvalidIndexWidth,
    InvalidBucketCount,
    BadControlByte,
    BadControlTail,
    DuplicateIndex,
    DuplicateName,
    OverlappingData,
    MissingIndex,
    InvalidProbeChain,
    ExtraBytes,
    InvalidSectionLayout,
    Overflow,
    OutOfMemory,
    PayloadLimitExceeded,
    EntryLimitExceeded,
    BucketLimitExceeded,
    AllocationLimitExceeded,
    NameLimitExceeded,
    DecompressedLimitExceeded,
    ProbeLimitExceeded,
    ComparisonLimitExceeded,
}

impl std::fmt::Display for Error {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{self:?}")
    }
}
impl std::error::Error for Error {}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Entry<'a> {
    pub name_hash: u64,
    pub name: &'a [u8],
    pub data_offset: u64,
    pub compressed_len: u64,
    pub uncompressed_len: u64,
    pub flags: u32,
}
impl Entry<'_> {
    pub const fn is_package(self) -> bool {
        self.flags & flags::PACKAGE != 0
    }
    pub const fn is_bytecode(self) -> bool {
        self.flags & flags::BYTECODE != 0
    }
    pub const fn is_resource(self) -> bool {
        self.flags & flags::RESOURCE != 0
    }
    pub const fn is_compressed(self) -> bool {
        self.flags & flags::COMPRESSED != 0
    }
    pub const fn kind(self) -> &'static str {
        if self.is_bytecode() {
            "bytecode"
        } else {
            "resource"
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct LookupSummary {
    pub bucket_count: u32,
    pub index_width: u32,
    pub control_bytes: usize,
    pub index_bytes: usize,
    pub max_probe_groups: u32,
    pub total_probe_groups: u64,
    pub candidate_name_checks: u64,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Summary {
    pub entries: usize,
    pub bytecode_entries: usize,
    pub resource_entries: usize,
    pub package_entries: usize,
    pub compressed_entries: usize,
    pub raw_bytecode_bytes: u64,
    pub raw_resource_bytes: u64,
    pub compressed_stored_bytes: u64,
    pub compressed_uncompressed_bytes: u64,
    pub lookup: LookupSummary,
}
#[derive(Debug)]
pub struct Payload<'a> {
    pub bytes: &'a [u8],
    pub entries: Vec<Entry<'a>>,
    pub summary: Summary,
}
#[derive(Clone, Copy, Debug, Default)]
pub struct Header {
    pub entry_count: u32,
    pub bucket_count: u32,
    pub flags: u32,
    pub index_width: u32,
    pub control_offset: u64,
    pub index_offset: u64,
    pub entry_meta_offset: u64,
    pub string_table_offset: u64,
    pub data_offset: u64,
    pub reserved: u64,
}
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
#[repr(C)]
pub struct EntryMeta {
    pub name_offset: u32,
    pub name_len: u32,
    pub data_offset: u32,
    pub stored_len: u32,
    pub raw_len: u32,
    pub flags: u16,
    pub reserved: u16,
}
const _: () = assert!(size_of::<EntryMeta>() == ENTRY_META_SIZE);
#[derive(Clone, Copy, Debug)]
pub struct Sections<'a> {
    pub header: Header,
    pub control: &'a [u8],
    pub lookup_index: &'a [u8],
    /// Wire bytes, decoded without alignment assumptions or allocation.
    pub entry_meta: &'a [u8],
    pub string_table: &'a [u8],
    pub data: &'a [u8],
}
impl Sections<'_> {
    pub fn metadata(self, index: usize) -> Result<EntryMeta, Error> {
        let start = index.checked_mul(ENTRY_META_SIZE).ok_or(Error::Overflow)?;
        let end = start.checked_add(ENTRY_META_SIZE).ok_or(Error::Overflow)?;
        let bytes = self.entry_meta.get(start..end).ok_or(Error::InvalidIndex)?;
        Ok(EntryMeta {
            name_offset: super::read_u32(bytes, 0),
            name_len: super::read_u32(bytes, 4),
            data_offset: super::read_u32(bytes, 8),
            stored_len: super::read_u32(bytes, 12),
            raw_len: super::read_u32(bytes, 16),
            flags: super::read_u16(bytes, 20),
            reserved: super::read_u16(bytes, 22),
        })
    }
}
