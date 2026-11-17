use super::{Counts, counted};
use pyload::container::{
    ARTIFACT_BYTES_MAX, Error as ContainerError, LocateFileError, Location, ReadPayloadError,
    locate_file, read_payload,
};
use pyload::format::{
    EMPTY_CONTROL, ENTRY_META_SIZE, Error, GROUP_WIDTH, HEADER_SIZE, MAGIC, PAYLOAD_BYTES_MAX,
    flags,
};
use std::io::{self, Write};

type TestResult = Result<(), Box<dyn std::error::Error>>;

fn assert_unallocated<T: std::fmt::Debug, E: std::fmt::Debug>(
    run: impl FnOnce() -> Result<T, E>,
    expected: &str,
) {
    let (result, counts) = counted(run);
    let error = result.err().map(|error| format!("{error:?}"));
    assert_eq!(error.as_deref(), Some(expected));
    assert_eq!(counts, Counts::ZERO, "{expected}");
}

fn put16(bytes: &mut [u8], at: usize, value: u16) {
    bytes[at..at + 2].copy_from_slice(&value.to_le_bytes());
}

fn put32(bytes: &mut [u8], at: usize, value: u32) {
    bytes[at..at + 4].copy_from_slice(&value.to_le_bytes());
}

fn put64(bytes: &mut [u8], at: usize, value: u64) {
    bytes[at..at + 8].copy_from_slice(&value.to_le_bytes());
}

fn read_u64(bytes: &[u8], at: usize) -> u64 {
    let mut word = [0; 8];
    word.copy_from_slice(&bytes[at..at + 8]);
    u64::from_le_bytes(word)
}

#[derive(Clone, Copy)]
struct Spec<'a> {
    name: &'a [u8],
    raw_len: u32,
    flags: u32,
}

fn resource(name: &[u8]) -> Spec<'_> {
    Spec {
        name,
        raw_len: 1,
        flags: flags::RESOURCE,
    }
}

fn compressed(name: &[u8], raw_len: u32) -> Spec<'_> {
    Spec {
        name,
        raw_len,
        flags: flags::RESOURCE | flags::COMPRESSED,
    }
}

fn payload(entries: &[Spec<'_>]) -> Vec<u8> {
    let mut buckets = GROUP_WIDTH;
    while entries.len() * 8 > buckets * 7 {
        buckets *= 2;
    }
    let index = HEADER_SIZE + buckets + GROUP_WIDTH;
    let meta = index + buckets * 2;
    let strings = meta + entries.len() * ENTRY_META_SIZE;
    let data = strings + entries.iter().map(|entry| entry.name.len()).sum::<usize>();
    let mut bytes = vec![0; data + entries.len()];
    bytes[..8].copy_from_slice(MAGIC);
    put32(&mut bytes, 8, entries.len() as u32);
    put32(&mut bytes, 12, buckets as u32);
    put32(&mut bytes, 20, 2);
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
    let mut name_offset = 0;
    for (number, entry) in entries.iter().enumerate() {
        let at = meta + number * ENTRY_META_SIZE;
        let fields = [
            name_offset,
            entry.name.len(),
            number,
            1,
            entry.raw_len as usize,
        ];
        for (field, value) in fields.into_iter().enumerate() {
            put32(&mut bytes, at + field * 4, value as u32);
        }
        put16(&mut bytes, at + 20, entry.flags as u16);
        let name = strings + name_offset;
        bytes[name..name + entry.name.len()].copy_from_slice(entry.name);
        name_offset += entry.name.len();
    }
    bytes
}

#[test]
fn payload_count_limits_fail_before_allocation() {
    let mut bytes = payload(&[resource(b"module")]);
    put32(&mut bytes, 8, 0x7000_0000);
    put32(&mut bytes, 12, 0x8000_0000);
    put32(&mut bytes, 20, 4);
    assert_unallocated(|| pyload::parse(&bytes), "EntryLimitExceeded");
    put32(&mut bytes, 8, 1);
    assert_unallocated(|| pyload::parse(&bytes), "BucketLimitExceeded");
    assert_unallocated(|| pyload::payload_extent(&bytes), "BucketLimitExceeded");
    let oversized = vec![0; PAYLOAD_BYTES_MAX + 1];
    assert_unallocated(|| pyload::parse(&oversized), "PayloadLimitExceeded");
}

#[test]
fn payload_name_and_decompression_limits_fail_before_allocation() {
    let long = [b'n'; 1025];
    let bytes = payload(&[resource(&long)]);
    assert_unallocated(|| pyload::parse(&bytes), "NameLimitExceeded");
    let names: Vec<Vec<u8>> = (0..16_385)
        .map(|number| format!("{number:01024}").into_bytes())
        .collect();
    let entries: Vec<_> = names.iter().map(|name| resource(name)).collect();
    let bytes = payload(&entries);
    assert_unallocated(|| pyload::parse(&bytes), "NameLimitExceeded");
    let bytes = payload(&[compressed(b"a", 64 * 1024 * 1024 + 1)]);
    assert_unallocated(|| pyload::parse(&bytes), "DecompressedLimitExceeded");
    let names = [b"a", b"b", b"c", b"d", b"e"];
    let bytes = payload(&names.map(|name| compressed(name, 64 * 1024 * 1024)));
    assert_unallocated(|| pyload::parse(&bytes), "DecompressedLimitExceeded");
}

#[test]
fn truncated_payload_tables_fail_without_allocation() {
    let bytes = payload(&[resource(b"module")]);
    for (field, expected) in [
        (32, Error::TruncatedControl),
        (40, Error::TruncatedLookupIndex),
        (48, Error::TruncatedEntryMeta),
    ] {
        let cutoff = read_u64(&bytes, field) as usize;
        let truncated = &bytes[..cutoff - 1];
        assert_unallocated(|| pyload::parse(truncated), &format!("{expected:?}"));
    }
}

struct Fixture {
    file: std::fs::File,
    path: std::path::PathBuf,
}

impl Fixture {
    fn new(bytes: &[u8]) -> io::Result<Self> {
        use std::sync::atomic::{AtomicUsize, Ordering};
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!(
            "aws-pyload-allocation-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        let mut file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(&path)?;
        file.write_all(bytes)?;
        Ok(Self { file, path })
    }

    fn locate(&self) -> Result<Location, LocateFileError> {
        locate_file(&self.file)
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}

fn container(error: ContainerError) -> String {
    format!("{:?}", LocateFileError::Container(error))
}

const NAMES: &[u8] = b"\0.shstrtab\0.pyload\0";

fn write(bytes: &mut [u8], at: usize, value: u64, width: usize, big: bool) {
    for index in 0..width {
        let shift = if big { width - 1 - index } else { index } * 8;
        bytes[at + index] = (value >> shift) as u8;
    }
}

fn elf(wide: bool, big: bool, payload: &[u8]) -> Vec<u8> {
    let size = if wide { 64 } else { 40 };
    let mut bytes = vec![0; 0x180 + 3 * size];
    bytes[..4].copy_from_slice(b"\x7fELF");
    bytes[4] = if wide { 2 } else { 1 };
    bytes[5] = if big { 2 } else { 1 };
    bytes[6] = 1;
    let (shoff, entsize, count_at, strings_at) = if wide {
        (40, 58, 60, 62)
    } else {
        (32, 46, 48, 50)
    };
    write(&mut bytes, shoff, 0x180, if wide { 8 } else { 4 }, big);
    write(&mut bytes, entsize, size as u64, 2, big);
    write(&mut bytes, count_at, 3, 2, big);
    write(&mut bytes, strings_at, 1, 2, big);
    bytes[0x80..0x80 + NAMES.len()].copy_from_slice(NAMES);
    let (offset_at, size_at, width) = if wide { (24, 32, 8) } else { (16, 20, 4) };
    let strings = 0x180 + size;
    write(&mut bytes, strings, 1, 4, big);
    write(&mut bytes, strings + offset_at, 0x80, width, big);
    write(
        &mut bytes,
        strings + size_at,
        NAMES.len() as u64,
        width,
        big,
    );
    let section = 0x180 + 2 * size;
    let data = 0x80 + NAMES.len();
    write(&mut bytes, section, 11, 4, big);
    write(&mut bytes, section + 8, 2, width, big);
    write(&mut bytes, section + offset_at, data as u64, width, big);
    write(
        &mut bytes,
        section + size_at,
        payload.len() as u64,
        width,
        big,
    );
    bytes[data..data + payload.len()].copy_from_slice(payload);
    bytes
}

fn macho(wide: bool, big: bool, payload: &[u8]) -> Vec<u8> {
    let (header, segment, section, offset) = if wide {
        (32, 72, 80, 0x200)
    } else {
        (28, 56, 68, 0x180)
    };
    let command = segment + section;
    let mut bytes = vec![0; offset + payload.len()];
    let magic = if wide { 0xfeed_facf } else { 0xfeed_face };
    write(&mut bytes, 0, magic, 4, big);
    write(&mut bytes, 16, 1, 4, big);
    write(&mut bytes, 20, command as u64, 4, big);
    write(&mut bytes, header, if wide { 0x19 } else { 1 }, 4, big);
    write(&mut bytes, header + 4, command as u64, 4, big);
    write(&mut bytes, header + if wide { 64 } else { 48 }, 1, 4, big);
    let at = header + segment;
    bytes[at..at + 8].copy_from_slice(b"__pyload");
    bytes[at + 16..at + 28].copy_from_slice(b"__DATA_CONST");
    write(
        &mut bytes,
        at + if wide { 48 } else { 40 },
        offset as u64,
        4,
        big,
    );
    let (size_at, width) = if wide { (40, 8) } else { (36, 4) };
    write(&mut bytes, at + size_at, payload.len() as u64, width, big);
    bytes[offset..].copy_from_slice(payload);
    bytes
}

#[test]
fn file_locator_metadata_buffers_stay_bounded() -> TestResult {
    let mut extended = elf(true, false, b"ZIPPY003section");
    put16(&mut extended, 60, 0);
    put16(&mut extended, 62, 0xffff);
    put64(&mut extended, 0x180 + 32, 3);
    put32(&mut extended, 0x180 + 40, 1);
    for bytes in [
        extended,
        elf(false, false, b"ZIPPY003section"),
        elf(false, true, b"ZIPPY003section"),
        macho(true, false, b"ZIPPY003section"),
        macho(false, false, b"ZIPPY003section"),
        macho(false, true, b"ZIPPY003section"),
    ] {
        let fixture = Fixture::new(&bytes)?;
        let (location, counts) = counted(|| fixture.locate());
        assert_eq!(location?.size, 15);
        assert!(counts.peak <= 512, "{counts:?}");
        assert_eq!(counts.live, 0, "{counts:?}");
    }
    Ok(())
}

#[test]
fn sparse_oversized_artifacts_fail_without_allocation() -> TestResult {
    let fixture = Fixture::new(b"")?;
    fixture.file.set_len(ARTIFACT_BYTES_MAX + 1)?;
    let expected = container(ContainerError::ArtifactLimitExceeded);
    assert_unallocated(|| fixture.locate(), &expected);
    fixture.file.set_len(ARTIFACT_BYTES_MAX)?;
    let expected = container(ContainerError::NotExecutable);
    assert_unallocated(|| fixture.locate(), &expected);
    Ok(())
}

fn assert_locate_unallocated(bytes: &[u8], expected: ContainerError) -> io::Result<()> {
    let fixture = Fixture::new(bytes)?;
    assert_unallocated(|| fixture.locate(), &container(expected));
    Ok(())
}

#[test]
fn file_metadata_counts_and_byte_sizes_fail_before_allocation() -> TestResult {
    let limit = ContainerError::ContainerLimitExceeded;
    let mut bytes = elf(true, false, b"payload");
    put16(&mut bytes, 60, 4097);
    assert_locate_unallocated(&bytes, limit)?;
    put16(&mut bytes, 60, 0);
    put64(&mut bytes, 0x180 + 32, u64::from(u32::MAX));
    assert_locate_unallocated(&bytes, limit)?;
    put16(&mut bytes, 60, 4096);
    put16(&mut bytes, 58, 4096);
    assert_locate_unallocated(&bytes, limit)?;
    let mut bytes = macho(true, false, b"payload");
    put32(&mut bytes, 16, u32::MAX);
    assert_locate_unallocated(&bytes, limit)?;
    put32(&mut bytes, 16, 1);
    put32(&mut bytes, 20, 1024 * 1024);
    assert_locate_unallocated(&bytes, limit)?;
    Ok(())
}

#[test]
fn file_locator_rejects_truncated_tables_before_allocation() -> TestResult {
    let end = ContainerError::UnexpectedEndOfFile;
    let bytes = elf(true, false, b"payload");
    assert_locate_unallocated(&bytes[..bytes.len() - 1], end)?;
    let bytes = macho(true, false, b"payload");
    assert_locate_unallocated(&bytes[..32 + 72 + 80 - 1], end)?;
    Ok(())
}

#[test]
fn file_locator_rejects_out_of_range_extended_elf_headers_before_allocation() -> TestResult {
    let mut bytes = elf(true, false, b"payload");
    put16(&mut bytes, 60, 0);
    for (offset, expected) in [
        (u64::MAX, ContainerError::Overflow),
        (u64::MAX - 64, ContainerError::TruncatedElf),
        (1 << 63, ContainerError::TruncatedElf),
        (bytes.len() as u64 - 63, ContainerError::TruncatedElf),
    ] {
        put64(&mut bytes, 40, offset);
        assert_locate_unallocated(&bytes, expected)?;
    }
    Ok(())
}

const SECTION: Location = Location {
    container: "elf-section",
    name: ".pyload",
    offset: 128,
    size: 3,
};

#[test]
fn section_reads_reject_oversized_sparse_payloads_before_allocation() -> TestResult {
    let location = Location {
        size: PAYLOAD_BYTES_MAX as u64 + 1,
        ..SECTION
    };
    let fixture = Fixture::new(b"")?;
    fixture.file.set_len(location.offset + location.size)?;
    let expected = format!(
        "{:?}",
        ReadPayloadError::Payload(Error::PayloadLimitExceeded)
    );
    assert_unallocated(|| read_payload(&fixture.file, location), &expected);
    Ok(())
}

#[test]
fn section_reads_allocate_only_the_section_and_free_it_on_failure() -> TestResult {
    let fixture = Fixture::new(b"")?;
    fixture.file.set_len(ARTIFACT_BYTES_MAX)?;
    {
        use std::io::Seek;
        let mut file = &fixture.file;
        file.seek(io::SeekFrom::Start(SECTION.offset))?;
        file.write_all(b"abc")?;
    }
    let (bytes, counts) = counted(|| read_payload(&fixture.file, SECTION));
    assert_eq!(bytes?, b"abc");
    assert_eq!((counts.allocations, counts.requested), (1, 3), "{counts:?}");
    fixture.file.set_len(SECTION.offset + 2)?;
    let (shortened, counts) = counted(|| {
        matches!(
            read_payload(&fixture.file, SECTION),
            Err(ReadPayloadError::Io(error)) if error.kind() == io::ErrorKind::UnexpectedEof
        )
    });
    assert!(shortened);
    assert_eq!(counts.live, 0, "{counts:?}");
    Ok(())
}

#[test]
fn counts_cover_only_this_threads_allocations() -> TestResult {
    let (bytes, counts) = counted(|| vec![0_u8; 7]);
    assert_eq!(
        (counts.allocations, counts.requested, counts.live),
        (1, 7, 7)
    );
    let (_, counts) = counted(|| drop(bytes));
    assert_eq!((counts.allocations, counts.live), (0, -7));
    let (joined, counts) = counted(|| std::thread::spawn(|| vec![0_u8; 1 << 20]).join());
    assert_eq!(joined.map(|bytes| bytes.len()).ok(), Some(1 << 20));
    assert!(counts.requested < 1 << 20, "{counts:?}");
    Ok(())
}
