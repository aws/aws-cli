use super::*;

#[test]
fn pe32_and_pe32_plus_exclude_raw_section_padding() -> Result<(), Error> {
    for wide in [false, true] {
        let bytes = fixture(wide);
        let located = locate(&bytes)?;
        assert_eq!(located.container, "pe-section");
        assert_eq!(located.name, ".pyload");
        assert_eq!(located.offset, 0x400);
        assert_eq!(located.bytes, b"payload");
    }
    Ok(())
}

#[test]
fn pe_rejects_invalid_headers_and_truncated_tables() {
    let bytes = fixture(true);
    for cutoff in [2, 63, 0x80, 0x97, 0x187, 0x1af] {
        assert_eq!(locate(&bytes[..cutoff]), Err(Error::TruncatedPe));
    }
    for (offset, value) in [(60, 32), (0x80, 0), (0x98, 0)] {
        let mut bytes = fixture(true);
        put32(&mut bytes, offset, value);
        assert_eq!(locate(&bytes), Err(Error::UnsupportedPe));
    }
    let mut bytes = fixture(true);
    put16(&mut bytes, 0x86, 4097);
    assert_eq!(locate(&bytes), Err(Error::ContainerLimitExceeded));
}

#[test]
fn pe_rejects_writable_unreadable_or_unbacked_payloads() {
    for (offset, value, error) in [
        (36, 0xc000_0040, Error::PayloadSectionWritable),
        (36, 0x40, Error::PayloadSectionNotAllocated),
        (8, 0x201, Error::InvalidPayloadSection),
        (8, 0, Error::InvalidPayloadSection),
        (16, 0x201, Error::InvalidPayloadSection),
        (20, u32::MAX, Error::InvalidPayloadSection),
    ] {
        let mut bytes = fixture(true);
        put32(&mut bytes, 0x188 + offset, value);
        assert_eq!(locate(&bytes), Err(error));
    }
}

#[test]
fn pe_requires_exactly_one_payload_section() {
    let mut bytes = fixture(true);
    bytes[0x188] = b'_';
    assert_eq!(locate(&bytes), Err(Error::MissingPayloadSection));
    let mut bytes = fixture(true);
    put16(&mut bytes, 0x86, 2);
    bytes.copy_within(0x188..0x1b0, 0x1b0);
    assert_eq!(locate(&bytes), Err(Error::DuplicatePayloadSection));
}
