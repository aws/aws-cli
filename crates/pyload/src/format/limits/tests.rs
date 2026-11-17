use super::*;
use crate::counting::{Counts, counted};
use crate::format::testing::*;

#[test]
fn metadata_counts_are_rejected_before_section_allocation() {
    let mut bytes = minimal(b"name", b"payload", flags::RESOURCE);
    put32(&mut bytes, 8, 0x7000_0000);
    put32(&mut bytes, 12, 0x8000_0000);
    put32(&mut bytes, 20, 4);
    assert_eq!(parse(&bytes).err(), Some(Error::EntryLimitExceeded));
    put32(&mut bytes, 8, 1);
    assert_eq!(parse(&bytes).err(), Some(Error::BucketLimitExceeded));
    assert_eq!(payload_extent(&bytes), Err(Error::BucketLimitExceeded));
}

#[test]
fn allocations_and_names_are_bounded() -> Result<(), Error> {
    let bytes = minimal(b"name", b"payload", flags::RESOURCE);
    let allocation = size_of::<(usize, usize)>() + size_of::<bool>() + size_of::<Entry<'_>>();
    for (limits, expected) in [
        (
            Limits {
                allocation_bytes: allocation - 1,
                ..Limits::default()
            },
            Error::AllocationLimitExceeded,
        ),
        (
            Limits {
                name_length: 3,
                ..Limits::default()
            },
            Error::NameLimitExceeded,
        ),
        (
            Limits {
                name_bytes: 3,
                ..Limits::default()
            },
            Error::NameLimitExceeded,
        ),
    ] {
        let (error, counts) = counted(|| validate::parse_with_limits(&bytes, limits).err());
        assert_eq!(error, Some(expected));
        assert_eq!(counts, Counts::ZERO, "{expected:?}");
    }
    let parsed = validate::parse_with_limits(
        &bytes,
        Limits {
            allocation_bytes: allocation,
            name_length: 4,
            name_bytes: 4,
            ..Limits::default()
        },
    )?;
    assert_eq!(parsed.entries[0].name, b"name");
    Ok(())
}

#[test]
fn declared_decompression_counts_every_entry_before_allocation() -> Result<(), Error> {
    let entries = [
        TestEntry {
            name: b"a",
            payload: b"x",
            raw_len: 6,
            flags: (flags::RESOURCE | flags::COMPRESSED) as u16,
        },
        TestEntry {
            name: b"b",
            payload: b"y",
            raw_len: 9,
            flags: (flags::RESOURCE | flags::COMPRESSED) as u16,
        },
    ];
    let mut bytes = blob(&entries, false, 2);
    for limits in [
        Limits {
            compressed_entry_bytes: 8,
            ..Limits::default()
        },
        Limits {
            decompressed_bytes: 14,
            ..Limits::default()
        },
    ] {
        assert_eq!(
            validate::parse_with_limits(&bytes, limits).err(),
            Some(Error::DecompressedLimitExceeded)
        );
    }
    let parsed = validate::parse_with_limits(
        &bytes,
        Limits {
            compressed_entry_bytes: 9,
            decompressed_bytes: 15,
            ..Limits::default()
        },
    )?;
    assert_eq!(parsed.summary.compressed_uncompressed_bytes, 15);
    let meta = sections(&bytes)?.header.entry_meta_offset as usize;
    put32(&mut bytes, meta + 16, u32::MAX);
    assert_eq!(parse(&bytes).err(), Some(Error::DecompressedLimitExceeded));
    Ok(())
}

#[test]
fn collision_work_is_shared_and_charged_before_comparison() -> Result<(), Error> {
    let bytes = collisions(false);
    assert!(parse(&bytes).is_ok());
    for limits in [
        Limits {
            probe_groups_per_entry: 2,
            ..Limits::default()
        },
        Limits {
            probe_groups: 50,
            ..Limits::default()
        },
    ] {
        assert_eq!(
            validate::parse_with_limits(&bytes, limits).err(),
            Some(Error::ProbeLimitExceeded)
        );
    }
    let parsed = validate::parse_with_limits(
        &bytes,
        Limits {
            probe_groups_per_entry: 3,
            probe_groups: 51,
            ..Limits::default()
        },
    )?;
    assert_eq!(parsed.summary.lookup.max_probe_groups, 3);
    assert_eq!(parsed.summary.lookup.total_probe_groups, 51);
    let bytes = blob(
        &[
            entry(b"a", b"\0", flags::BYTECODE),
            entry(b"longer", b"\0", flags::BYTECODE),
        ],
        false,
        2,
    );
    let comparison = |comparison_bytes| {
        validate::parse_with_limits(
            &bytes,
            Limits {
                comparison_bytes,
                ..Limits::default()
            },
        )
    };
    assert_eq!(comparison(6).err(), Some(Error::ComparisonLimitExceeded));
    assert_eq!(comparison(7)?.summary.lookup.candidate_name_checks, 2);
    Ok(())
}

#[test]
fn truncated_tables_are_rejected_before_allocation() {
    let bytes = minimal(b"name", b"payload", flags::RESOURCE);
    for (field, expected) in [
        (32, Error::TruncatedControl),
        (40, Error::TruncatedLookupIndex),
        (48, Error::TruncatedEntryMeta),
    ] {
        let cutoff = read_u64(&bytes, field) as usize;
        assert_eq!(parse(&bytes[..cutoff - 1]).err(), Some(expected));
    }
}
