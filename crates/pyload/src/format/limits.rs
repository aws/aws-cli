use super::*;
#[cfg(test)]
mod tests;

pub(super) type DataRange = (usize, usize);
const ALLOCATION_BYTES_PER_ENTRY: usize =
    size_of::<DataRange>() + size_of::<bool>() + size_of::<Entry<'static>>();

#[derive(Clone, Copy)]
pub(super) struct Limits {
    pub entries: usize,
    pub buckets: usize,
    pub allocation_bytes: usize,
    pub name_bytes: usize,
    pub name_length: usize,
    pub compressed_entry_bytes: u64,
    pub decompressed_bytes: u64,
    pub probe_groups_per_entry: u32,
    pub probe_groups: u64,
    pub comparison_bytes: u64,
}
impl Limits {
    pub const DEFAULT: Self = Self {
        entries: 65_536,
        buckets: 131_072,
        allocation_bytes: 8 * 1024 * 1024,
        name_bytes: 16 * 1024 * 1024,
        name_length: 1024,
        compressed_entry_bytes: 64 * 1024 * 1024,
        decompressed_bytes: 256 * 1024 * 1024,
        probe_groups_per_entry: 64,
        probe_groups: 1024 * 1024,
        comparison_bytes: 128 * 1024 * 1024,
    };
}
impl Default for Limits {
    fn default() -> Self {
        Self::DEFAULT
    }
}
const _: () = {
    let limits = Limits::DEFAULT;
    assert!(limits.entries * ALLOCATION_BYTES_PER_ENTRY <= limits.allocation_bytes);
    assert!(limits.entries < limits.buckets);
    assert!(limits.compressed_entry_bytes <= limits.decompressed_bytes);
};

pub(super) fn bounded_sections(bytes: &[u8], limits: Limits) -> Result<Sections<'_>, Error> {
    if bytes.len() > PAYLOAD_BYTES_MAX {
        return Err(Error::PayloadLimitExceeded);
    }
    let header = read_header(bytes)?;
    if header.entry_count as usize > limits.entries {
        return Err(Error::EntryLimitExceeded);
    }
    if header.bucket_count as usize > limits.buckets {
        return Err(Error::BucketLimitExceeded);
    }
    let allocation = (header.entry_count as usize)
        .checked_mul(ALLOCATION_BYTES_PER_ENTRY)
        .ok_or(Error::Overflow)?;
    if allocation > limits.allocation_bytes {
        return Err(Error::AllocationLimitExceeded);
    }
    let sections = sections(bytes)?;
    check_metadata(sections, limits)?;
    Ok(sections)
}

fn check_metadata(sections: Sections<'_>, limits: Limits) -> Result<(), Error> {
    let mut names = 0;
    let mut decompressed = 0_u64;
    for index in 0..sections.header.entry_count as usize {
        let entry = sections.metadata(index)?;
        if entry.name_len as usize > limits.name_length {
            return Err(Error::NameLimitExceeded);
        }
        names = add(names, entry.name_len as usize)?;
        if names > limits.name_bytes {
            return Err(Error::NameLimitExceeded);
        }
        if u32::from(entry.flags) & flags::COMPRESSED != 0 {
            let raw = u64::from(entry.raw_len);
            if raw > limits.compressed_entry_bytes {
                return Err(Error::DecompressedLimitExceeded);
            }
            decompressed = decompressed.checked_add(raw).ok_or(Error::Overflow)?;
            if decompressed > limits.decompressed_bytes {
                return Err(Error::DecompressedLimitExceeded);
            }
        }
    }
    Ok(())
}

pub(super) struct LookupBudget {
    groups_left: u64,
    comparison_bytes_left: u64,
    groups_per_entry: u32,
}
impl LookupBudget {
    pub fn new(limits: Limits) -> Self {
        Self {
            groups_left: limits.probe_groups,
            comparison_bytes_left: limits.comparison_bytes,
            groups_per_entry: limits.probe_groups_per_entry,
        }
    }
    pub fn visit(&mut self, groups: u32) -> Result<(), Error> {
        if groups > self.groups_per_entry || self.groups_left == 0 {
            return Err(Error::ProbeLimitExceeded);
        }
        self.groups_left -= 1;
        Ok(())
    }
    pub fn compare(&mut self, name: &[u8], candidate: &[u8]) -> Result<(), Error> {
        if candidate.len() == name.len() {
            self.comparison_bytes_left = self
                .comparison_bytes_left
                .checked_sub(name.len() as u64)
                .ok_or(Error::ComparisonLimitExceeded)?;
        }
        Ok(())
    }
}

pub(super) fn capacity<T>(count: usize) -> Result<Vec<T>, Error> {
    let mut values = Vec::new();
    values
        .try_reserve_exact(count)
        .map_err(|_| Error::OutOfMemory)?;
    Ok(values)
}
