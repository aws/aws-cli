//! Sorted callback ranges reject duplicate writes and coalesce adjacency.
use super::WriteError;
use std::ops::Range;

#[derive(Clone, Debug, Default)]
pub struct CallbackRangeTracker {
    ranges: Vec<Range<u64>>,
}
impl CallbackRangeTracker {
    pub fn add(&mut self, size: u64, start: u64, len: usize) -> Result<(), WriteError> {
        if len == 0 {
            return Ok(());
        }
        let end = start
            .checked_add(len as u64)
            .filter(|&end| end <= size)
            .ok_or(WriteError::OutOfBounds)?;
        let index = self.ranges.partition_point(|range| range.end <= start);
        if self
            .ranges
            .get(index)
            .is_some_and(|range| range.start < end)
        {
            return Err(WriteError::Overlap);
        }
        let previous = index > 0 && self.ranges[index - 1].end == start;
        let next = self
            .ranges
            .get(index)
            .is_some_and(|range| range.start == end);
        match (previous, next) {
            (true, true) => self.ranges[index - 1].end = self.ranges.remove(index).end,
            (true, false) => self.ranges[index - 1].end = end,
            (false, true) => self.ranges[index].start = start,
            (false, false) => self.ranges.insert(index, start..end),
        }
        Ok(())
    }
    /// Whether the accepted ranges cover exactly `0..size`.
    pub fn is_complete(&self, size: u64) -> bool {
        let complete = self.ranges.len() == 1 && self.ranges[0] == (0..size);
        (size == 0 && self.ranges.is_empty()) || complete
    }
    pub fn ranges(&self) -> &[Range<u64>] {
        &self.ranges
    }
}
#[cfg(test)]
mod tests;
