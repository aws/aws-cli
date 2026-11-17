use super::*;
use crate::swiss_group::{self, ProbeSeq};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LookupResult {
    pub entry_index: usize,
    pub probe_groups: u32,
    pub candidate_checks: u32,
}

pub fn lookup_entry_index(
    sections: Sections<'_>,
    name: &[u8],
) -> Result<Option<LookupResult>, Error> {
    lookup_with_budget(sections, name, None)
}

pub(super) fn lookup_with_budget(
    sections: Sections<'_>,
    name: &[u8],
    mut budget: Option<&mut limits::LookupBudget>,
) -> Result<Option<LookupResult>, Error> {
    let hash = fnv1a64(name);
    let mask = sections.header.bucket_count as usize - 1;
    let mut probe = ProbeSeq::new(hash as usize & mask, mask);
    let mut candidate_checks = 0;
    for probe_groups in 1..=sections.header.bucket_count / GROUP_WIDTH as u32 {
        if let Some(budget) = &mut budget {
            budget.visit(probe_groups)?;
        }
        let mut matches = swiss_group::match_h2(sections.control, probe.bucket, h2(hash));
        while matches != 0 {
            candidate_checks += 1;
            let bucket = (probe.bucket + matches.trailing_zeros() as usize) & mask;
            let entry_index =
                read_index_bytes(sections.lookup_index, sections.header.index_width, bucket)?
                    as usize;
            let meta = sections.metadata(entry_index)?;
            if budget.is_none() && meta.name_len as usize != name.len() {
                matches &= matches - 1;
                continue;
            }
            let candidate = entry_name(sections.string_table, meta.name_offset, meta.name_len)?;
            if let Some(budget) = &mut budget {
                budget.compare(name, candidate)?;
            }
            if candidate == name {
                return Ok(Some(LookupResult {
                    entry_index,
                    probe_groups,
                    candidate_checks,
                }));
            }
            matches &= matches - 1;
        }
        if swiss_group::any_empty(sections.control, probe.bucket, EMPTY_CONTROL) {
            return Ok(None);
        }
        probe.advance();
    }
    Err(Error::InvalidProbeChain)
}

pub(super) fn validate_lookup(sections: Sections<'_>) -> Result<(), Error> {
    let count = sections.header.entry_count as usize;
    let mut seen = limits::capacity(count)?;
    seen.resize(count, false);
    let mut full = 0;
    for (bucket, &control) in sections.control[..sections.header.bucket_count as usize]
        .iter()
        .enumerate()
    {
        let index = read_index_bytes(sections.lookup_index, sections.header.index_width, bucket)?;
        if control == EMPTY_CONTROL {
            if index != 0 {
                return Err(Error::InvalidIndex);
            }
            continue;
        }
        if control > 0x7f {
            return Err(Error::BadControlByte);
        }
        let visited = seen.get_mut(index as usize).ok_or(Error::InvalidIndex)?;
        if *visited {
            return Err(Error::DuplicateIndex);
        }
        *visited = true;
        full += 1;
        let meta = sections.metadata(index as usize)?;
        let name = entry_name(sections.string_table, meta.name_offset, meta.name_len)?;
        if control != h2(fnv1a64(name)) {
            return Err(Error::HashMismatch);
        }
    }
    if full != count {
        return Err(Error::MissingIndex);
    }
    Ok(())
}
