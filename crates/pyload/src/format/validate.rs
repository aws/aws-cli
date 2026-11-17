use super::*;

pub fn parse(bytes: &[u8]) -> Result<Payload<'_>, Error> {
    parse_with_limits(bytes, limits::Limits::default())
}

pub(super) fn parse_with_limits(
    bytes: &[u8],
    limits: limits::Limits,
) -> Result<Payload<'_>, Error> {
    let sections = limits::bounded_sections(bytes, limits)?;
    let buckets = sections.header.bucket_count as usize;
    if sections.control[buckets..buckets + GROUP_WIDTH] != sections.control[..GROUP_WIDTH] {
        return Err(Error::BadControlTail);
    }
    let mut summary = Summary {
        entries: sections.header.entry_count as usize,
        lookup: LookupSummary {
            bucket_count: sections.header.bucket_count,
            index_width: sections.header.index_width,
            control_bytes: sections.control.len(),
            index_bytes: sections.lookup_index.len(),
            ..LookupSummary::default()
        },
        ..Summary::default()
    };
    let max_end = parse_entries(sections, &mut summary)?;
    if add(offset(sections.header.data_offset)?, max_end)? != bytes.len() {
        return Err(Error::ExtraBytes);
    }
    lookup::validate_lookup(sections)?;
    let entries = parse_entries_lookup(sections, &mut summary, limits)?;
    Ok(Payload {
        bytes,
        entries,
        summary,
    })
}

fn parse_entries_lookup<'a>(
    sections: Sections<'a>,
    summary: &mut Summary,
    limits: limits::Limits,
) -> Result<Vec<Entry<'a>>, Error> {
    let mut entries = limits::capacity(summary.entries)?;
    let mut budget = limits::LookupBudget::new(limits);
    for index in 0..summary.entries {
        let meta = sections.metadata(index)?;
        let name = entry_name(sections.string_table, meta.name_offset, meta.name_len)?;
        let found = lookup::lookup_with_budget(sections, name, Some(&mut budget))?
            .ok_or(Error::InvalidProbeChain)?;
        if found.entry_index != index {
            return Err(Error::InvalidProbeChain);
        }
        summary.lookup.max_probe_groups = summary.lookup.max_probe_groups.max(found.probe_groups);
        summary.lookup.total_probe_groups += u64::from(found.probe_groups);
        summary.lookup.candidate_name_checks += u64::from(found.candidate_checks);
        entries.push(entry_from_meta(name, meta));
    }
    Ok(entries)
}

fn parse_entries(sections: Sections<'_>, summary: &mut Summary) -> Result<usize, Error> {
    let mut ranges = limits::capacity(summary.entries)?;
    let mut previous = None;
    let mut max_end = 0;
    for index in 0..summary.entries {
        let meta = sections.metadata(index)?;
        validate_entry_shape(meta)?;
        let name = entry_name(sections.string_table, meta.name_offset, meta.name_len)?;
        match previous.map(|old: &[u8]| old.cmp(name)) {
            Some(std::cmp::Ordering::Greater) => return Err(Error::UnsortedNames),
            Some(std::cmp::Ordering::Equal) => return Err(Error::DuplicateName),
            _ => {}
        }
        previous = Some(name);
        let start = meta.data_offset as usize;
        let end = add(start, meta.stored_len as usize)?;
        if end > sections.data.len() {
            return Err(Error::PayloadOutsideData);
        }
        max_end = max_end.max(end);
        if end != start {
            ranges.push((start, end));
        }
        accumulate_summary(entry_from_meta(name, meta), summary)?;
    }
    check_ranges(&mut ranges)?;
    Ok(max_end)
}

fn check_ranges(ranges: &mut [limits::DataRange]) -> Result<(), Error> {
    ranges.sort_unstable();
    for pair in ranges.windows(2) {
        if pair[1].0 < pair[0].1 && pair[0] != pair[1] {
            return Err(Error::OverlappingData);
        }
    }
    Ok(())
}

fn accumulate_summary(entry: Entry<'_>, summary: &mut Summary) -> Result<(), Error> {
    summary.bytecode_entries += usize::from(entry.is_bytecode());
    summary.resource_entries += usize::from(entry.is_resource());
    summary.package_entries += usize::from(entry.is_package());
    summary.compressed_entries += usize::from(entry.is_compressed());
    if entry.is_compressed() {
        summary.compressed_stored_bytes = summary
            .compressed_stored_bytes
            .checked_add(entry.compressed_len)
            .ok_or(Error::Overflow)?;
        summary.compressed_uncompressed_bytes = summary
            .compressed_uncompressed_bytes
            .checked_add(entry.uncompressed_len)
            .ok_or(Error::Overflow)?;
    } else {
        let counter = if entry.is_bytecode() {
            &mut summary.raw_bytecode_bytes
        } else {
            &mut summary.raw_resource_bytes
        };
        *counter = counter
            .checked_add(entry.uncompressed_len)
            .ok_or(Error::Overflow)?;
    }
    Ok(())
}
