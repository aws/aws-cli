//! Allocation-free view into an embedded payload with lazy entry decoding.
#![forbid(unsafe_code)]
use crate::format::{self, Entry, Error, Sections};

#[derive(Clone, Copy, Debug)]
pub struct View<'a> {
    sections: Sections<'a>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ViewEntry<'a> {
    pub index: usize,
    pub entry: Entry<'a>,
}
impl<'a> View<'a> {
    pub fn new(bytes: &'a [u8]) -> Result<Self, Error> {
        Ok(Self {
            sections: format::sections(bytes)?,
        })
    }
    pub const fn entry_count(self) -> usize {
        self.sections.header.entry_count as usize
    }
    pub fn find(self, name: &[u8]) -> Result<Option<ViewEntry<'a>>, Error> {
        format::lookup_entry_index(self.sections, name)?
            .map(|result| {
                let meta = self.sections.metadata(result.entry_index)?;
                let name = format::entry_name(
                    self.sections.string_table,
                    meta.name_offset,
                    meta.name_len,
                )?;
                Ok(ViewEntry {
                    index: result.entry_index,
                    entry: format::entry_from_meta(name, meta),
                })
            })
            .transpose()
    }
    pub fn entry_at(self, index: usize) -> Result<ViewEntry<'a>, Error> {
        let meta = self.sections.metadata(index)?;
        format::validate_entry_shape(meta)?;
        let name = format::entry_name(self.sections.string_table, meta.name_offset, meta.name_len)?;
        Ok(ViewEntry {
            index,
            entry: format::entry_from_meta(name, meta),
        })
    }
    pub fn first_name_at_least(self, name: &[u8]) -> Result<usize, Error> {
        let (mut start, mut end) = (0, self.entry_count());
        while start < end {
            let middle = start + (end - start) / 2;
            if self.entry_name_at(middle)? < name {
                start = middle + 1;
            } else {
                end = middle;
            }
        }
        Ok(start)
    }
    pub fn entry_name_at(self, index: usize) -> Result<&'a [u8], Error> {
        let meta = self.sections.metadata(index)?;
        format::entry_name(self.sections.string_table, meta.name_offset, meta.name_len)
    }
    pub fn stored_bytes(self, entry: Entry<'_>) -> Result<&'a [u8], Error> {
        let start = format::offset(entry.data_offset)?;
        let end = format::add(start, format::offset(entry.compressed_len)?)?;
        self.sections
            .data
            .get(start..end)
            .ok_or(Error::PayloadOutsideData)
    }
}

#[cfg(test)]
mod tests;
