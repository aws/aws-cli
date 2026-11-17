use super::*;

pub fn read_header(bytes: &[u8]) -> Result<Header, Error> {
    if bytes.len() < 8 {
        return Err(Error::TruncatedHeader);
    }
    if &bytes[..8] != MAGIC {
        return Err(Error::BadMagic);
    }
    if bytes.len() < HEADER_SIZE {
        return Err(Error::TruncatedHeader);
    }
    let header = Header {
        entry_count: read_u32(bytes, 8),
        bucket_count: read_u32(bytes, 12),
        flags: read_u32(bytes, 16),
        index_width: read_u32(bytes, 20),
        control_offset: read_u64(bytes, 24),
        index_offset: read_u64(bytes, 32),
        entry_meta_offset: read_u64(bytes, 40),
        string_table_offset: read_u64(bytes, 48),
        data_offset: read_u64(bytes, 56),
        reserved: read_u64(bytes, 64),
    };
    if header.entry_count == 0 {
        return Err(Error::EmptyEntryTable);
    }
    if header.flags != 0 || header.reserved != 0 {
        return Err(Error::ReservedFieldSet);
    }
    if !matches!(header.index_width, 2 | 4) {
        return Err(Error::InvalidIndexWidth);
    }
    validate_bucket_count(header.entry_count, header.bucket_count)?;
    Ok(header)
}

fn validate_bucket_count(entry_count: u32, bucket_count: u32) -> Result<(), Error> {
    if bucket_count < GROUP_WIDTH as u32
        || !bucket_count.is_power_of_two()
        || !bucket_count.is_multiple_of(GROUP_WIDTH as u32)
        || u64::from(entry_count) * 8 > u64::from(bucket_count) * 7
    {
        return Err(Error::InvalidBucketCount);
    }
    Ok(())
}

pub fn sections(bytes: &[u8]) -> Result<Sections<'_>, Error> {
    let header = read_header(bytes)?;
    let control = fixed_offset(
        bytes,
        header.control_offset,
        HEADER_SIZE,
        Error::TruncatedHeader,
    )?;
    let control_len = add(header.bucket_count as usize, GROUP_WIDTH)?;
    let index = fixed_offset(
        bytes,
        header.index_offset,
        add(control, control_len)?,
        Error::TruncatedControl,
    )?;
    let index_len = (header.bucket_count as usize)
        .checked_mul(header.index_width as usize)
        .ok_or(Error::Overflow)?;
    let meta = fixed_offset(
        bytes,
        header.entry_meta_offset,
        add(index, index_len)?,
        Error::TruncatedLookupIndex,
    )?;
    let meta_len = (header.entry_count as usize)
        .checked_mul(ENTRY_META_SIZE)
        .ok_or(Error::Overflow)?;
    let strings = fixed_offset(
        bytes,
        header.string_table_offset,
        add(meta, meta_len)?,
        Error::TruncatedEntryMeta,
    )?;
    let data = offset(header.data_offset)?;
    if data < strings {
        return Err(Error::InvalidSectionLayout);
    }
    if data > bytes.len() {
        return Err(Error::TruncatedStringTable);
    }
    Ok(Sections {
        header,
        control: &bytes[control..index],
        lookup_index: &bytes[index..meta],
        entry_meta: &bytes[meta..strings],
        string_table: &bytes[strings..data],
        data: &bytes[data..],
    })
}

fn fixed_offset(
    bytes: &[u8],
    value: u64,
    expected: usize,
    truncated: Error,
) -> Result<usize, Error> {
    let value = offset(value)?;
    if value != expected {
        return Err(Error::InvalidSectionLayout);
    }
    if value > bytes.len() {
        return Err(truncated);
    }
    Ok(value)
}

pub fn payload_extent(bytes: &[u8]) -> Result<usize, Error> {
    let sections = limits::bounded_sections(bytes, limits::Limits::default())?;
    let mut max_end = 0;
    for index in 0..sections.header.entry_count as usize {
        let meta = sections.metadata(index)?;
        validate_entry_shape(meta)?;
        entry_name(sections.string_table, meta.name_offset, meta.name_len)?;
        let end = add(meta.data_offset as usize, meta.stored_len as usize)?;
        if end > sections.data.len() {
            return Err(Error::PayloadOutsideData);
        }
        max_end = max_end.max(end);
    }
    add(offset(sections.header.data_offset)?, max_end)
}

pub fn entry_name(strings: &[u8], start: u32, len: u32) -> Result<&[u8], Error> {
    let end = add(start as usize, len as usize)?;
    strings
        .get(start as usize..end)
        .ok_or(Error::NameOutsideStringTable)
}

pub fn validate_entry_shape(meta: EntryMeta) -> Result<(), Error> {
    let bits = u32::from(meta.flags);
    if bits & !flags::KNOWN != 0 {
        return Err(Error::UnknownFlags);
    }
    if meta.reserved != 0 {
        return Err(Error::ReservedFieldSet);
    }
    if (bits & flags::BYTECODE != 0) == (bits & flags::RESOURCE != 0) {
        return Err(Error::InvalidKindFlags);
    }
    let compressed = bits & flags::COMPRESSED != 0;
    if (compressed && meta.stored_len == 0) || (!compressed && meta.stored_len != meta.raw_len) {
        return Err(Error::InvalidCompressionLengths);
    }
    Ok(())
}
