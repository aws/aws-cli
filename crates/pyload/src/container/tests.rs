use super::*;
mod file;
mod pe;
use crate::format::testing::{put16, put32, put64};
const NAMES: &[u8] = b"\0.shstrtab\0.pyload\0";
fn write(bytes: &mut [u8], at: usize, value: u64, width: usize, big: bool) {
    for i in 0..width {
        bytes[at + i] = (value >> (if big { width - 1 - i } else { i } * 8)) as u8;
    }
}
fn elf(wide: bool, big: bool, present: bool, payload: &[u8]) -> Vec<u8> {
    let size = if wide { 64 } else { 40 };
    let count = if present { 3 } else { 2 };
    let mut bytes = vec![0; 0x180 + count * size];
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
    write(&mut bytes, count_at, count as u64, 2, big);
    write(&mut bytes, strings_at, 1, 2, big);
    bytes[0x80..0x80 + NAMES.len()].copy_from_slice(NAMES);
    let (offset_at, size_at, width) = if wide { (24, 32, 8) } else { (16, 20, 4) };
    write(&mut bytes, 0x180 + size, 1, 4, big);
    write(&mut bytes, 0x180 + size + offset_at, 0x80, width, big);
    write(
        &mut bytes,
        0x180 + size + size_at,
        NAMES.len() as u64,
        width,
        big,
    );
    if present {
        let at = 0x180 + 2 * size;
        write(&mut bytes, at, 11, 4, big);
        write(&mut bytes, at + 8, 2, width, big);
        write(
            &mut bytes,
            at + offset_at,
            (0x80 + NAMES.len()) as u64,
            width,
            big,
        );
        write(&mut bytes, at + size_at, payload.len() as u64, width, big);
        bytes[0x80 + NAMES.len()..0x80 + NAMES.len() + payload.len()].copy_from_slice(payload);
    }
    bytes
}
fn macho(wide: bool, big: bool, present: bool, payload: &[u8]) -> Vec<u8> {
    let (header, segment, section, offset) = if wide {
        (32, 72, 80, 0x200)
    } else {
        (28, 56, 68, 0x180)
    };
    let command = segment + usize::from(present) * section;
    let mut bytes = vec![
        0;
        if present {
            offset + payload.len()
        } else {
            header + command
        }
    ];
    write(
        &mut bytes,
        0,
        if wide { 0xfeedfacf } else { 0xfeedface },
        4,
        big,
    );
    write(&mut bytes, 16, 1, 4, big);
    write(&mut bytes, 20, command as u64, 4, big);
    write(&mut bytes, header, if wide { 0x19 } else { 1 }, 4, big);
    write(&mut bytes, header + 4, command as u64, 4, big);
    write(
        &mut bytes,
        header + if wide { 64 } else { 48 },
        u64::from(present),
        4,
        big,
    );
    if present {
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
        write(
            &mut bytes,
            at + if wide { 40 } else { 36 },
            payload.len() as u64,
            if wide { 8 } else { 4 },
            big,
        );
        bytes[offset..].copy_from_slice(payload);
    }
    bytes
}
#[test]
fn finds_payload_section_and_reports_offset_and_length() -> Result<(), Error> {
    let bytes = elf(true, false, true, b"ZIPPY003payload");
    let found = locate(&bytes)?;
    assert_eq!(found.container, "elf-section");
    assert_eq!(found.name, ".pyload");
    assert_eq!(found.offset, (0x80 + NAMES.len()) as u64);
    assert_eq!(found.bytes, b"ZIPPY003payload");
    Ok(())
}
#[test]
fn rejects_executable_with_no_payload_section() {
    assert_eq!(
        locate(&elf(true, false, false, b"")),
        Err(Error::MissingPayloadSection)
    );
}
#[test]
fn rejects_payload_section_outside_executable() {
    let mut bytes = elf(true, false, true, b"ZIPPY003payload");
    put64(&mut bytes, 0x180 + 128 + 32, 1024);
    assert_eq!(locate(&bytes), Err(Error::InvalidPayloadSection));
}
#[test]
fn rejects_writable_or_unallocated_payload_sections() {
    for (flags, error) in [
        (3, Error::PayloadSectionWritable),
        (0, Error::PayloadSectionNotAllocated),
    ] {
        let mut bytes = elf(true, false, true, b"payload");
        put64(&mut bytes, 0x180 + 128 + 8, flags);
        assert_eq!(locate(&bytes), Err(error));
    }
}
#[test]
fn finds_elf32_little_and_big_endian_payload_sections() -> Result<(), Error> {
    for big in [false, true] {
        let bytes = elf(false, big, true, b"ZIPPY003elf32");
        let found = locate(&bytes)?;
        assert_eq!(found.container, "elf-section");
        assert_eq!(found.bytes, b"ZIPPY003elf32");
    }
    Ok(())
}
#[test]
fn supports_extended_elf_section_counts_and_string_indexes() -> Result<(), Error> {
    let mut bytes = elf(true, false, true, b"ZIPPY003extended");
    put16(&mut bytes, 60, 0);
    put16(&mut bytes, 62, 0xffff);
    put64(&mut bytes, 0x180 + 32, 3);
    put32(&mut bytes, 0x180 + 40, 1);
    assert_eq!(locate(&bytes)?.bytes, b"ZIPPY003extended");
    Ok(())
}
#[test]
fn rejects_invalid_elf_section_indexes_and_truncated_string_tables() {
    let mut bytes = elf(true, false, true, b"payload");
    put16(&mut bytes, 62, 3);
    assert_eq!(locate(&bytes), Err(Error::UnsupportedElf));
    let mut bytes = elf(true, false, true, b"payload");
    put16(&mut bytes, 60, 0);
    put64(&mut bytes, 0x180 + 32, 0);
    assert_eq!(locate(&bytes), Err(Error::UnsupportedElf));
    let mut bytes = elf(true, false, true, b"payload");
    put64(&mut bytes, 0x180 + 64 + 32, u64::MAX);
    assert_eq!(locate(&bytes), Err(Error::TruncatedElf));
}
#[test]
fn rejects_duplicate_elf_payload_sections() {
    let mut bytes = elf(true, false, true, b"payload");
    let duplicate = bytes[0x180 + 128..0x180 + 192].to_vec();
    bytes.extend_from_slice(&duplicate);
    put16(&mut bytes, 60, 4);
    assert_eq!(locate(&bytes), Err(Error::DuplicatePayloadSection));
}
#[test]
fn elf_payload_size_excludes_section_padding() -> Result<(), Error> {
    let mut bytes = elf(true, false, true, b"ZIPPY003padded");
    bytes[0x80 + NAMES.len() + b"ZIPPY003padded".len()..0x180].fill(0xa5);
    assert_eq!(locate(&bytes)?.bytes, b"ZIPPY003padded");
    Ok(())
}
#[test]
fn located_payload_section_can_be_rejected_as_invalid_zippy003() -> Result<(), Error> {
    let bytes = elf(true, false, true, b"not-zippy");
    assert_eq!(
        crate::parse(locate(&bytes)?.bytes).err(),
        Some(crate::Error::BadMagic)
    );
    Ok(())
}
#[test]
fn finds_macho_payload_section_and_reports_offset_and_length() -> Result<(), Error> {
    let bytes = macho(true, false, true, b"ZIPPY003payload");
    let found = locate(&bytes)?;
    assert_eq!(found.container, "mach-o-section");
    assert_eq!(found.name, MACHO_PAYLOAD_CONTAINER_NAME);
    assert_eq!(found.offset, 0x200);
    assert_eq!(found.bytes, b"ZIPPY003payload");
    Ok(())
}
#[test]
fn rejects_macho_executable_with_no_payload_section() {
    assert_eq!(
        locate(&macho(true, false, false, b"")),
        Err(Error::MissingPayloadSection)
    );
}
#[test]
fn rejects_macho_payload_section_outside_executable() {
    let mut bytes = macho(true, false, true, b"ZIPPY003payload");
    put64(&mut bytes, 32 + 72 + 40, 1024);
    assert_eq!(locate(&bytes), Err(Error::InvalidPayloadSection));
}
#[test]
fn finds_macho32_payload_sections() -> Result<(), Error> {
    for big in [false, true] {
        let bytes = macho(false, big, true, b"ZIPPY003macho32");
        let found = locate(&bytes)?;
        assert_eq!(found.offset, 0x180);
        assert_eq!(found.bytes, b"ZIPPY003macho32");
    }
    Ok(())
}
#[test]
fn rejects_malformed_macho_load_commands_and_section_tables() {
    for (at, value, error) in [
        (36, 4, Error::UnsupportedMachO),
        (20, 8, Error::TruncatedMachO),
        (96, 1, Error::TruncatedMachO),
    ] {
        let mut bytes = macho(true, false, false, b"");
        put32(&mut bytes, at, value);
        assert_eq!(locate(&bytes), Err(error));
    }
}
#[test]
fn rejects_duplicate_macho_payload_sections() {
    let mut bytes = macho(true, false, true, b"ZIPPY003duplicate");
    bytes.copy_within(104..184, 184);
    put32(&mut bytes, 20, 232);
    put32(&mut bytes, 36, 232);
    put32(&mut bytes, 96, 2);
    assert_eq!(locate(&bytes), Err(Error::DuplicatePayloadSection));
}
#[test]
fn macho_payload_size_excludes_trailing_file_padding() -> Result<(), Error> {
    let mut bytes = macho(true, false, true, b"ZIPPY003padded");
    bytes.resize(bytes.len() + 32, 0xa5);
    assert_eq!(locate(&bytes)?.bytes, b"ZIPPY003padded");
    Ok(())
}
