use super::super::*;
use std::io::{self, Write};

struct Fixture {
    file: std::fs::File,
    path: std::path::PathBuf,
}
impl Fixture {
    fn new(bytes: &[u8]) -> io::Result<Self> {
        use std::sync::atomic::{AtomicUsize, Ordering};
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!(
            "aws-pyload-{}-{}",
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
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}
fn error(bytes: &[u8]) -> Result<Error, Box<dyn std::error::Error>> {
    let fixture = Fixture::new(bytes)?;
    match locate_file(&fixture.file) {
        Err(LocateFileError::Container(error)) => Ok(error),
        other => Err(format!("unexpected result: {other:?}").into()),
    }
}

#[test]
fn file_locator_matches_slice_in_every_endian_and_width() -> Result<(), Box<dyn std::error::Error>>
{
    for wide in [false, true] {
        for big in [false, true] {
            for bytes in [
                elf(wide, big, true, b"payload"),
                macho(wide, big, true, b"payload"),
            ] {
                let expected = locate(&bytes)?;
                let fixture = Fixture::new(&bytes)?;
                let location = locate_file(&fixture.file)?;
                assert_eq!(location.container, expected.container);
                assert_eq!(location.offset, expected.offset);
                assert_eq!(read_payload(&fixture.file, location)?, expected.bytes);
            }
        }
    }
    Ok(())
}

#[test]
fn pe_file_locator_reads_bounded_metadata_and_excludes_padding()
-> Result<(), Box<dyn std::error::Error>> {
    for wide in [false, true] {
        let fixture = Fixture::new(&pe::fixture(wide))?;
        let location = locate_file(&fixture.file)?;
        assert_eq!(location.container, "pe-section");
        assert_eq!(read_payload(&fixture.file, location)?, b"payload");
    }
    let mut bytes = pe::fixture(true);
    put16(&mut bytes, 0x86, 4097);
    assert_eq!(error(&bytes)?, Error::ContainerLimitExceeded);
    let mut bytes = pe::fixture(true);
    put32(&mut bytes, 60, u32::MAX);
    assert_eq!(error(&bytes)?, Error::UnexpectedEndOfFile);
    Ok(())
}

#[test]
fn sparse_artifacts_are_bounded_without_reading_code() -> Result<(), Box<dyn std::error::Error>> {
    let fixture = Fixture::new(&elf(true, false, true, b"payload"))?;
    fixture.file.set_len(ARTIFACT_BYTES_MAX + 1)?;
    assert!(matches!(
        locate_file(&fixture.file),
        Err(LocateFileError::Container(Error::ArtifactLimitExceeded))
    ));
    fixture.file.set_len(ARTIFACT_BYTES_MAX)?;
    assert_eq!(locate_file(&fixture.file)?.size, 7);
    Ok(())
}

#[test]
fn payload_read_rejects_oversized_sections_and_shortened_files()
-> Result<(), Box<dyn std::error::Error>> {
    let fixture = Fixture::new(b"prefixpayloadsuffix")?;
    let mut location = Location {
        container: "elf-section",
        name: ".pyload",
        offset: 6,
        size: 7,
    };
    assert_eq!(read_payload(&fixture.file, location)?, b"payload");
    fixture.file.set_len(12)?;
    assert!(matches!(
        read_payload(&fixture.file, location),
        Err(ReadPayloadError::Io(error)) if error.kind() == io::ErrorKind::UnexpectedEof
    ));
    location.size = crate::format::PAYLOAD_BYTES_MAX as u64 + 1;
    fixture.file.set_len(ARTIFACT_BYTES_MAX)?;
    assert!(matches!(
        read_payload(&fixture.file, location),
        Err(ReadPayloadError::Payload(
            crate::format::Error::PayloadLimitExceeded
        ))
    ));
    Ok(())
}

#[test]
fn failed_buffer_reservations_are_out_of_memory() {
    let error = crate::container::file::allocate(usize::MAX as u64).err();
    assert_eq!(
        error.as_ref().map(io::Error::kind),
        Some(io::ErrorKind::OutOfMemory)
    );
    assert_eq!(
        error.as_ref().map(crate::inspect::read_error_name),
        Some("OutOfMemory")
    );
}

#[test]
fn extended_section_zero_shortened_after_stat_is_truncated_elf()
-> Result<(), Box<dyn std::error::Error>> {
    let mut bytes = elf(true, false, true, b"payload");
    put16(&mut bytes, 60, 0);
    let table = bytes.len() as u64;
    put64(&mut bytes, 40, table);
    let fixture = Fixture::new(&bytes)?;
    let located = crate::container::file::elf(&fixture.file, &bytes[..64], table + 64);
    assert!(matches!(
        located,
        Err(LocateFileError::Container(Error::TruncatedElf))
    ));
    Ok(())
}

#[test]
fn extended_indices_are_resolved_without_unbounded_reads() -> Result<(), Box<dyn std::error::Error>>
{
    let mut bytes = elf(true, false, true, b"payload");
    put16(&mut bytes, 60, 0);
    put16(&mut bytes, 62, 0xffff);
    put64(&mut bytes, 0x180 + 32, 3);
    put32(&mut bytes, 0x180 + 40, 1);
    assert_eq!(locate_file(&Fixture::new(&bytes)?.file)?.size, 7);
    for (offset, expected) in [
        (u64::MAX, Error::Overflow),
        (u64::MAX - 64, Error::TruncatedElf),
        (1 << 63, Error::TruncatedElf),
        (bytes.len() as u64 - 63, Error::TruncatedElf),
    ] {
        put64(&mut bytes, 40, offset);
        assert_eq!(locate(&bytes), Err(expected));
        assert_eq!(error(&bytes)?, expected);
    }
    Ok(())
}

#[test]
fn metadata_counts_sizes_and_truncated_tables_fail_before_allocation()
-> Result<(), Box<dyn std::error::Error>> {
    let mut bytes = elf(true, false, true, b"payload");
    put16(&mut bytes, 60, 4097);
    assert_eq!(error(&bytes)?, Error::ContainerLimitExceeded);
    put16(&mut bytes, 60, 0);
    put64(&mut bytes, 0x180 + 32, u64::from(u32::MAX));
    assert_eq!(error(&bytes)?, Error::ContainerLimitExceeded);
    put16(&mut bytes, 60, 4096);
    put16(&mut bytes, 58, 4096);
    assert_eq!(error(&bytes)?, Error::ContainerLimitExceeded);
    let mut bytes = elf(true, false, true, b"payload");
    put64(&mut bytes, 0x180 + 64 + 32, METADATA_BYTES_MAX + 1);
    assert_eq!(error(&bytes)?, Error::ContainerLimitExceeded);
    let mut bytes = macho(true, false, true, b"payload");
    put32(&mut bytes, 16, u32::MAX);
    assert_eq!(error(&bytes)?, Error::ContainerLimitExceeded);
    put32(&mut bytes, 16, 1);
    put32(&mut bytes, 20, METADATA_BYTES_MAX as u32);
    assert_eq!(error(&bytes)?, Error::ContainerLimitExceeded);
    let bytes = elf(true, false, true, b"payload");
    assert_eq!(
        error(&bytes[..bytes.len() - 1])?,
        Error::UnexpectedEndOfFile
    );
    let bytes = macho(true, false, true, b"payload");
    assert_eq!(error(&bytes[..183])?, Error::UnexpectedEndOfFile);
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn header_read_ignores_a_stat_size_smaller_than_the_content()
-> Result<(), Box<dyn std::error::Error>> {
    let file = std::fs::File::open("/proc/self/mem")?;
    assert_eq!(file.metadata()?.len(), 0);
    match locate_file(&file) {
        Err(LocateFileError::Io(error)) => {
            assert_eq!(crate::inspect::read_error_name(&error), "InputOutput");
        }
        other => return Err(format!("unexpected result: {other:?}").into()),
    }
    let fixture = Fixture::new(b"\x7fELF")?;
    assert!(matches!(
        locate_file(&fixture.file),
        Err(LocateFileError::Container(Error::TruncatedElf))
    ));
    Ok(())
}
