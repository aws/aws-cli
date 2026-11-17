use super::{testing::*, *};

type TestResult = Result<(), Error>;
fn simple() -> Vec<u8> {
    minimal(b"a", b"b", flags::BYTECODE)
}
fn two() -> Vec<u8> {
    blob(
        &[
            entry(b"a", b"x", flags::BYTECODE),
            entry(b"b", b"y", flags::BYTECODE),
        ],
        false,
        2,
    )
}
fn reject(bytes: &[u8], error: Error) {
    assert_eq!(parse(bytes).err(), Some(error));
}
fn meta(bytes: &[u8]) -> usize {
    read_u64(bytes, 40) as usize
}
fn full_buckets(bytes: &[u8]) -> Vec<usize> {
    bytes[HEADER_SIZE..HEADER_SIZE + read_u32(bytes, 12) as usize]
        .iter()
        .enumerate()
        .filter_map(|(i, &c)| (c != EMPTY_CONTROL).then_some(i))
        .collect()
}
fn set_control(bytes: &mut [u8], bucket: usize, value: u8) {
    let buckets = read_u32(bytes, 12) as usize;
    bytes[HEADER_SIZE + bucket] = value;
    if bucket < GROUP_WIDTH {
        bytes[HEADER_SIZE + buckets + bucket] = value;
    }
}
#[test]
fn fnv1a64_has_stable_vectors() {
    assert_eq!(fnv1a64(b""), 0xcbf29ce484222325);
    assert_eq!(fnv1a64(b"a"), 0xaf63dc4c8601ec8c);
    assert_eq!(fnv1a64(b"awscli.clidriver"), 0x92e38053e7bc91aa);
}
#[test]
fn parses_triangular_probe_chains_past_second_group() -> TestResult {
    let bytes = collisions(false);
    let payload = parse(&bytes)?;
    assert_eq!(payload.summary.lookup.bucket_count, 64);
    assert!(payload.summary.lookup.max_probe_groups > 2);
    Ok(())
}
#[test]
fn rejects_old_linear_probe_chains_past_second_group() {
    reject(&collisions(true), Error::InvalidProbeChain);
}
#[test]
fn parses_minimal_valid_blob() -> TestResult {
    let bytes = minimal(b"awscli.clidriver", b"abc", flags::BYTECODE);
    let payload = parse(&bytes)?;
    assert_eq!(payload.entries.len(), 1);
    assert_eq!(payload.entries[0].name, b"awscli.clidriver");
    assert_eq!(payload.summary.bytecode_entries, 1);
    assert_eq!(payload.summary.raw_bytecode_bytes, 3);
    assert_eq!(payload.summary.lookup.bucket_count, 16);
    assert_eq!(payload.summary.lookup.index_width, 2);
    Ok(())
}
#[test]
fn rejects_bad_magic() {
    let mut bytes = simple();
    bytes[0] = b'X';
    reject(&bytes, Error::BadMagic);
}
#[test]
fn rejects_truncated_header() {
    reject(b"ZIPPY003abc", Error::TruncatedHeader);
}
#[test]
fn rejects_truncated_control() {
    reject(&simple()[..HEADER_SIZE + 1], Error::TruncatedControl);
}
#[test]
fn rejects_truncated_lookup_index() {
    let bytes = simple();
    reject(
        &bytes[..read_u64(&bytes, 32) as usize + 1],
        Error::TruncatedLookupIndex,
    );
}
#[test]
fn rejects_truncated_entry_metadata() {
    let bytes = simple();
    reject(&bytes[..meta(&bytes) + 1], Error::TruncatedEntryMeta);
}
#[test]
fn rejects_truncated_string_table() {
    let mut bytes = simple();
    let len = bytes.len();
    put64(&mut bytes, 56, len as u64 + 10);
    reject(&bytes, Error::TruncatedStringTable);
}
#[test]
fn fixed_section_layout_errors_take_precedence_over_truncation() {
    for at in [24, 32, 40, 48] {
        let mut bytes = simple();
        let len = bytes.len();
        put64(&mut bytes, at, len as u64 + 1);
        assert_eq!(sections(&bytes).err(), Some(Error::InvalidSectionLayout));
    }
}
#[test]
fn rejects_invalid_index_width() {
    let mut bytes = simple();
    put32(&mut bytes, 20, 1);
    reject(&bytes, Error::InvalidIndexWidth);
}
#[test]
fn rejects_invalid_bucket_counts() {
    for buckets in [0, 15, 24, 32] {
        let mut bytes = simple();
        if buckets == 32 {
            put32(&mut bytes, 8, 29);
        }
        put32(&mut bytes, 12, buckets);
        reject(&bytes, Error::InvalidBucketCount);
    }
}
#[test]
fn rejects_bad_control_tail() {
    let mut bytes = simple();
    bytes[HEADER_SIZE + 16] ^= 1;
    reject(&bytes, Error::BadControlTail);
}
#[test]
fn rejects_payload_offsets_outside_payload_extent() {
    let mut bytes = simple();
    let at = meta(&bytes);
    bytes[at + 8] = 2;
    reject(&bytes, Error::PayloadOutsideData);
}
#[test]
fn rejects_unknown_flags() {
    let mut bytes = simple();
    let at = meta(&bytes);
    bytes[at + 20] = 0x80;
    reject(&bytes, Error::UnknownFlags);
}
#[test]
fn rejects_invalid_raw_length_relationship() {
    let mut bytes = minimal(b"a", b"b", flags::RESOURCE);
    let at = meta(&bytes);
    bytes[at + 12] = 2;
    reject(&bytes, Error::InvalidCompressionLengths);
}
#[test]
fn rejects_compressed_entries_without_stored_frame_bytes() {
    let mut e = entry(b"a", b"", flags::RESOURCE | flags::COMPRESSED);
    e.raw_len = 1;
    reject(&blob(&[e], false, 2), Error::InvalidCompressionLengths);
}
#[test]
fn allows_compressed_stored_length_to_exceed_raw_length() -> TestResult {
    let mut e = entry(b"a", &[0; 20], flags::RESOURCE | flags::COMPRESSED);
    e.raw_len = 1;
    let bytes = blob(&[e], false, 2);
    let s = parse(&bytes)?.summary;
    assert_eq!(
        (
            s.compressed_entries,
            s.compressed_stored_bytes,
            s.compressed_uncompressed_bytes
        ),
        (1, 20, 1)
    );
    Ok(())
}
#[test]
fn rejects_trailing_payload_bytes() {
    let mut bytes = simple();
    bytes.push(0);
    reject(&bytes, Error::ExtraBytes);
}
#[test]
fn payload_extent_ignores_trailing_section_padding() -> TestResult {
    let mut bytes = simple();
    let len = bytes.len();
    bytes.resize(len + 16, 0);
    assert_eq!(payload_extent(&bytes)?, len);
    Ok(())
}
#[test]
fn rejects_hash_mismatch() {
    let mut bytes = simple();
    let bucket = full_buckets(&bytes)[0];
    let value = (bytes[HEADER_SIZE + bucket] + 1) & 0x7f;
    set_control(&mut bytes, bucket, value);
    reject(&bytes, Error::HashMismatch);
}
#[test]
fn rejects_unsorted_names() {
    let mut bytes = two();
    let at = meta(&bytes);
    for i in 0..ENTRY_META_SIZE {
        bytes.swap(at + i, at + ENTRY_META_SIZE + i);
    }
    reject(&bytes, Error::UnsortedNames);
}
#[test]
fn rejects_duplicate_names() {
    let e = entry(b"same", b"x", flags::BYTECODE);
    reject(&blob(&[e, e], false, 2), Error::DuplicateName);
}
#[test]
fn rejects_partial_data_overlap_while_allowing_alias_shaped_metadata() {
    let mut bytes = blob(
        &[
            entry(b"a", b"xx", flags::RESOURCE),
            entry(b"b", b"yy", flags::RESOURCE),
        ],
        false,
        2,
    );
    let at = meta(&bytes);
    put32(&mut bytes, at + ENTRY_META_SIZE + 8, 1);
    reject(&bytes, Error::OverlappingData);
}
#[test]
fn allows_exact_data_ranges_shared_by_aliases() -> TestResult {
    let mut bytes = blob(
        &[
            entry(b"a", b"xx", flags::RESOURCE),
            entry(b"alias-a", b"yy", flags::RESOURCE),
        ],
        false,
        2,
    );
    bytes.truncate(bytes.len() - 2);
    let at = meta(&bytes);
    put32(&mut bytes, at + ENTRY_META_SIZE + 8, 0);
    let payload = parse(&bytes)?;
    assert_eq!(payload.entries.len(), 2);
    assert_eq!(payload.entries[0].data_offset, 0);
    assert_eq!(payload.entries[1].data_offset, 0);
    Ok(())
}
#[test]
fn rejects_duplicate_lookup_index_entries() -> TestResult {
    let mut bytes = two();
    let full = full_buckets(&bytes);
    let at = read_u64(&bytes, 32) as usize;
    let first = read_index_bytes(&bytes[at..], 2, full[0])?;
    put16(&mut bytes, at + full[1] * 2, first as u16);
    reject(&bytes, Error::DuplicateIndex);
    Ok(())
}
#[test]
fn rejects_missing_lookup_index_entries() {
    let mut bytes = two();
    let bucket = full_buckets(&bytes)[0];
    let at = read_u64(&bytes, 32) as usize;
    set_control(&mut bytes, bucket, EMPTY_CONTROL);
    put16(&mut bytes, at + bucket * 2, 0);
    reject(&bytes, Error::MissingIndex);
}
#[test]
fn rejects_lookup_indexes_outside_the_entry_table() {
    let mut bytes = simple();
    let bucket = full_buckets(&bytes)[0];
    let at = read_u64(&bytes, 32) as usize;
    put16(&mut bytes, at + bucket * 2, 1);
    reject(&bytes, Error::InvalidIndex);
}
#[test]
fn parses_four_byte_lookup_indexes() -> TestResult {
    let bytes = blob(&[entry(b"a", b"payload", flags::RESOURCE)], false, 4);
    let payload = parse(&bytes)?;
    assert_eq!(payload.summary.lookup.index_width, 4);
    assert_eq!(payload.entries[0].name, b"a");
    Ok(())
}
#[test]
fn parses_empty_bytecode_and_resource_payloads() -> TestResult {
    let bytes = blob(
        &[
            entry(b"empty.pyc", b"", flags::BYTECODE),
            entry(b"empty.txt", b"", flags::RESOURCE),
        ],
        false,
        2,
    );
    let payload = parse(&bytes)?;
    assert_eq!(payload.entries.len(), 2);
    assert_eq!(payload.summary.raw_bytecode_bytes, 0);
    assert_eq!(payload.summary.raw_resource_bytes, 0);
    Ok(())
}
#[test]
fn checked_format_arithmetic_reports_overflow() {
    assert_eq!(add(usize::MAX, 1), Err(Error::Overflow));
    assert_eq!(read_index_bytes(&[], 4, usize::MAX), Err(Error::Overflow));
    let entry = Entry {
        name_hash: 0,
        name: b"",
        data_offset: u64::MAX,
        compressed_len: 1,
        uncompressed_len: 1,
        flags: flags::RESOURCE,
    };
    let bytes = simple();
    let view = crate::View::new(&bytes);
    assert_eq!(
        view.and_then(|view| view.stored_bytes(entry)),
        Err(Error::Overflow)
    );
}
#[test]
fn computes_summary_metrics() -> TestResult {
    let mut compressed = entry(b"c", &[0; 5], flags::RESOURCE | flags::COMPRESSED);
    compressed.raw_len = 30;
    let bytes = blob(
        &[
            entry(b"a", &[0; 10], flags::BYTECODE | flags::PACKAGE),
            entry(b"b", &[0; 20], flags::RESOURCE),
            compressed,
        ],
        false,
        2,
    );
    let s = parse(&bytes)?.summary;
    assert_eq!(
        (
            s.entries,
            s.bytecode_entries,
            s.resource_entries,
            s.package_entries,
            s.compressed_entries
        ),
        (3, 1, 2, 1, 1)
    );
    assert_eq!(
        (
            s.raw_bytecode_bytes,
            s.raw_resource_bytes,
            s.compressed_stored_bytes,
            s.compressed_uncompressed_bytes
        ),
        (10, 20, 5, 30)
    );
    assert!(s.lookup.max_probe_groups > 0);
    assert!(s.lookup.candidate_name_checks > 0);
    Ok(())
}

#[test]
fn checked_finder_fixture_builder_and_raw_frame_round_trip()
-> Result<(), Box<dyn std::error::Error>> {
    assert_eq!(build(&[]), Err(Error::EmptyEntryTable));
    assert_eq!(raw_zstd_frame(&[0; 256]), Err(InputTooLarge));
    for raw in [b"".as_slice(), b"finder resource"] {
        let compressed = raw_zstd_frame(raw)?;
        let mut decoded = vec![0; raw.len()];
        crate::decompress::decode(&compressed, &mut decoded)?;
        assert_eq!(decoded, raw);
        let mut fixture = entry(b"data", &compressed, flags::RESOURCE | flags::COMPRESSED);
        fixture.raw_len = raw.len() as u32;
        let bytes = build(&[fixture])?;
        assert_eq!(parse(&bytes)?.entries[0].uncompressed_len, raw.len() as u64);
    }
    Ok(())
}

#[test]
fn the_payload_the_build_embeds_parses_in_full() -> Result<(), Box<dyn std::error::Error>> {
    let Some(prefix) = std::env::var_os("AWS_NATIVE_FALLBACK_PREFIX") else {
        assert!(
            std::env::var_os("AWS_NATIVE_CRT_PREFIX").is_none(),
            "the prepared environment must name the payload"
        );
        return Ok(());
    };
    let bytes = std::fs::read(std::path::Path::new(&prefix).join("awscli-v2.blob"))?;
    let payload = parse(&bytes)?;
    assert!(
        payload
            .entries
            .iter()
            .any(|entry| entry.name == b"awscli.clidriver")
    );
    Ok(())
}
