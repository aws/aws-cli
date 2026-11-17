use super::*;
use crate::format::{flags, testing::*};
fn fixture() -> Vec<u8> {
    blob(
        &[
            entry(b"awscli", b"\0", flags::BYTECODE | flags::PACKAGE),
            entry(b"awscli.clidriver", b"\0", flags::BYTECODE),
            entry(b"awscli/data/config.json", b"{}", flags::RESOURCE),
        ],
        false,
        2,
    )
}
#[test]
fn runtime_view_initializes_and_finds_entries() -> Result<(), Error> {
    let bytes = fixture();
    let view = View::new(&bytes)?;
    assert_eq!(view.entry_count(), 3);
    let pkg = view.find(b"awscli")?.ok_or(Error::MissingIndex)?.entry;
    assert!(pkg.is_package());
    assert!(pkg.is_bytecode());
    let data = view
        .find(b"awscli/data/config.json")?
        .ok_or(Error::MissingIndex)?
        .entry;
    assert!(data.is_resource());
    assert_eq!(view.stored_bytes(data)?, b"{}");
    assert_eq!(view.find(b"missing")?, None);
    Ok(())
}
#[test]
fn runtime_lookup_uses_cloned_control_tail() -> Result<(), Error> {
    let bytes = minimal(b"tail6", b"\0", flags::BYTECODE);
    assert_eq!(format::fnv1a64(b"tail6") & 15, 15);
    assert_eq!(format::fnv1a64(b"tail-missing18") & 15, 15);
    let view = View::new(&bytes)?;
    assert!(view.find(b"tail6")?.is_some());
    assert_eq!(view.find(b"tail-missing18")?, None);
    Ok(())
}
#[test]
fn runtime_lookup_follows_triangular_probe_chain_past_second_group() -> Result<(), Error> {
    let bytes = collisions(false);
    assert_eq!(format::read_u32(&bytes, 12), 64);
    let view = View::new(&bytes)?;
    for name in COLLISION_NAMES {
        assert_eq!(format::fnv1a64(name) & 63, 50);
        assert!(view.find(name)?.is_some());
    }
    Ok(())
}
#[test]
fn runtime_view_supports_prefix_scans_through_sorted_entries() -> Result<(), Error> {
    let bytes = fixture();
    let view = View::new(&bytes)?;
    let mut matches = 0;
    for i in view.first_name_at_least(b"awscli")?..view.entry_count() {
        if !view.entry_name_at(i)?.starts_with(b"awscli") {
            break;
        }
        matches += 1;
    }
    assert_eq!(matches, 3);
    Ok(())
}
#[test]
fn runtime_view_leaves_full_payload_validation_to_format_parser() -> Result<(), Error> {
    let mut bytes = fixture();
    let buckets = format::read_u32(&bytes, 12) as usize;
    bytes[format::HEADER_SIZE + buckets] ^= 1;
    assert_eq!(format::parse(&bytes).err(), Some(Error::BadControlTail));
    assert_eq!(View::new(&bytes)?.entry_count(), 3);
    Ok(())
}
#[test]
fn runtime_view_reports_malformed_entry_metadata_during_prefix_scan() -> Result<(), Error> {
    let mut bytes = fixture();
    let meta = format::read_u64(&bytes, 40) as usize;
    put32(&mut bytes, meta + format::ENTRY_META_SIZE + 4, u32::MAX);
    assert_eq!(
        View::new(&bytes)?.first_name_at_least(b"awscli"),
        Err(Error::NameOutsideStringTable)
    );
    Ok(())
}
#[test]
fn runtime_lookup_bounds_malformed_full_control_table() -> Result<(), Error> {
    let mut bytes = fixture();
    let buckets = format::read_u32(&bytes, 12) as usize;
    bytes[format::HEADER_SIZE..format::HEADER_SIZE + buckets + format::GROUP_WIDTH].fill(0);
    assert_eq!(
        View::new(&bytes)?.find(b"missing"),
        Err(Error::InvalidProbeChain)
    );
    Ok(())
}

#[test]
fn lookup_retains_lazy_shape_validation() -> Result<(), Error> {
    let mut bytes = fixture();
    let at = format::read_u64(&bytes, 40) as usize;
    put16(&mut bytes, at + 20, 0x80);
    let view = View::new(&bytes)?;
    assert!(view.find(b"awscli")?.is_some());
    assert_eq!(view.entry_at(0), Err(Error::UnknownFlags));
    Ok(())
}

#[test]
fn runtime_lookup_skips_a_corrupt_candidate_of_another_length() -> Result<(), Error> {
    let (other_length, target) = (&b"awscli.c5003"[..], &b"awscli.target"[..]);
    let (same_length, sibling) = (&b"awscli.e10000"[..], &b"awscli.e10013"[..]);
    for (first, second) in [(other_length, target), (same_length, sibling)] {
        let (first, second) = (format::fnv1a64(first), format::fnv1a64(second));
        assert_eq!(
            (first & 15, format::h2(first)),
            (second & 15, format::h2(second))
        );
    }
    let names = [other_length, same_length, sibling, target];
    let entries = names.map(|name| entry(name, b"\0", flags::BYTECODE));
    let mut bytes = blob(&entries, false, 2);
    for name in [target, sibling] {
        let found = format::lookup_entry_index(format::sections(&bytes)?, name)?;
        assert_eq!(found.map(|found| found.candidate_checks), Some(2));
    }
    let meta = format::read_u64(&bytes, 40) as usize;
    for index in [0, 1] {
        put32(&mut bytes, meta + index * format::ENTRY_META_SIZE, u32::MAX);
    }
    let view = View::new(&bytes)?;
    assert_eq!(
        view.find(target)?.map(|found| found.entry.name),
        Some(target)
    );
    assert_eq!(view.find(sibling), Err(Error::NameOutsideStringTable));
    assert_eq!(view.find(same_length), Err(Error::NameOutsideStringTable));
    assert_eq!(
        format::parse(&bytes).err(),
        Some(Error::NameOutsideStringTable)
    );
    Ok(())
}
#[test]
fn runtime_lookup_reports_a_candidate_name_outside_the_string_table() -> Result<(), Error> {
    let mut bytes = fixture();
    let meta = format::read_u64(&bytes, 40) as usize;
    let table_len = format::read_u64(&bytes, 56) - format::read_u64(&bytes, 48);
    let inside = u32::try_from(table_len - 3).map_err(|_| Error::NameOutsideStringTable)?;
    for offset in [inside, u32::MAX] {
        put32(&mut bytes, meta, offset);
        let view = View::new(&bytes)?;
        assert_eq!(view.find(b"awscli"), Err(Error::NameOutsideStringTable));
    }
    put32(&mut bytes, meta + 4, u32::MAX);
    assert_eq!(View::new(&bytes)?.find(b"awscli")?, None);
    Ok(())
}
