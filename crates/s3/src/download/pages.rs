use super::WriteError;
use std::{collections::HashMap, ops::Range};

#[derive(Debug)]
pub(crate) struct Bits {
    words: Vec<u64>,
    length: usize,
}
impl Bits {
    pub(crate) fn new(length: usize) -> Self {
        Self {
            words: vec![0; length.div_ceil(64)],
            length,
        }
    }
    pub(crate) fn contains(&self, bit: usize) -> bool {
        assert!(bit < self.length);
        self.words[bit / 64] & (1 << (bit % 64)) != 0
    }
    pub(crate) fn set(&mut self, bit: usize) {
        assert!(bit < self.length);
        self.words[bit / 64] |= 1 << (bit % 64);
    }
    pub(crate) fn first(&self, range: Range<usize>) -> Option<usize> {
        assert!(range.end <= self.length);
        if range.is_empty() {
            return None;
        }
        for index in range.start / 64..=(range.end - 1) / 64 {
            let matching = self.words[index] & word_mask(&range, index);
            if matching != 0 {
                return Some(index * 64 + matching.trailing_zeros() as usize);
            }
        }
        None
    }
    pub(crate) fn set_range(&mut self, range: Range<usize>) {
        assert!(range.end <= self.length);
        if range.is_empty() {
            return;
        }
        for index in range.start / 64..=(range.end - 1) / 64 {
            self.words[index] |= word_mask(&range, index);
        }
    }
}
fn word_mask(range: &Range<usize>, index: usize) -> u64 {
    let start = range.start.saturating_sub(index * 64);
    let end = (range.end - index * 64).min(64);
    let high = if end == 64 {
        u64::MAX
    } else {
        (1u64 << end) - 1
    };
    (u64::MAX << start) & high
}
#[derive(Debug)]
pub(crate) struct PageCompletionTracker {
    size: usize,
    page_size: usize,
    partial: HashMap<usize, usize>,
    completed: Bits,
    evicted: Bits,
    pending_eviction_ranges: Vec<Range<usize>>,
    completed_unevicted_pages: usize,
    eviction_batch_pages: usize,
}
impl PageCompletionTracker {
    pub(crate) fn new(size: usize, page_size: usize, batch_bytes: usize) -> Self {
        assert!(page_size > 0);
        let count = size.div_ceil(page_size);
        Self {
            size,
            page_size,
            partial: HashMap::new(),
            completed: Bits::new(count),
            evicted: Bits::new(count),
            pending_eviction_ranges: Vec::new(),
            completed_unevicted_pages: 0,
            eviction_batch_pages: batch_bytes.div_ceil(page_size).max(1),
        }
    }
    pub(crate) fn page_count(&self) -> usize {
        self.size.div_ceil(self.page_size)
    }
    pub(crate) fn eviction_batch_pages(&self) -> usize {
        self.eviction_batch_pages
    }
    pub(crate) fn complete_range(&mut self, offset: u64, len: usize) -> Result<(), WriteError> {
        let Some(range) = page_range(self.size, self.page_size, offset, len)? else {
            return Ok(());
        };
        let start = offset as usize;
        let end = start + len;
        if self.complete_range_has_whole_pages(start, end) {
            return self.complete_range_full_pages(range);
        }
        for page in range.clone() {
            self.completed_bytes(page, start, end)?;
        }
        for page in range {
            let count = self.completed_bytes(page, start, end)?;
            if count == self.page_len(page) {
                self.partial.remove(&page);
                self.completed.set(page);
                self.completed_unevicted_pages += 1;
                self.queue_completed_run(page..page + 1);
            } else {
                self.partial.insert(page, count);
            }
        }
        Ok(())
    }
    fn complete_range_has_whole_pages(&self, start: usize, end: usize) -> bool {
        start.is_multiple_of(self.page_size)
            && end.is_multiple_of(self.page_size)
            && self.partial.is_empty()
    }
    fn complete_range_full_pages(&mut self, range: Range<usize>) -> Result<(), WriteError> {
        assert!(!range.is_empty() && range.end <= self.page_count());
        debug_assert!(self.partial.is_empty());
        let evicted = self.evicted.first(range.clone());
        let completed = self.completed.first(range.clone());
        if evicted.is_some_and(|page| completed.is_none_or(|other| page <= other)) {
            return Err(WriteError::PageAlreadyEvicted);
        }
        if completed.is_some() {
            return Err(WriteError::PageCompletedTwice);
        }
        self.completed.set_range(range.clone());
        self.completed_unevicted_pages += range.len();
        self.queue_completed_run(range);
        Ok(())
    }
    fn queue_completed_run(&mut self, range: Range<usize>) {
        if let Some(last) = self
            .pending_eviction_ranges
            .last_mut()
            .filter(|last| last.end == range.start)
        {
            last.end = range.end;
        } else {
            self.pending_eviction_ranges.push(range);
        }
    }
    fn page_len(&self, page: usize) -> usize {
        (self.size - page * self.page_size).min(self.page_size)
    }
    #[cfg(any(test, feature = "testing"))]
    pub(crate) fn is_completed(&self, page: usize) -> bool {
        self.completed.contains(page)
    }
    fn completed_bytes(&self, page: usize, start: usize, end: usize) -> Result<usize, WriteError> {
        if self.evicted.contains(page) {
            return Err(WriteError::PageAlreadyEvicted);
        }
        if self.completed.contains(page) {
            return Err(WriteError::PageCompletedTwice);
        }
        let page_start = page * self.page_size;
        let count = end.min(page_start + self.page_len(page)) - start.max(page_start);
        let total = self.partial.get(&page).copied().unwrap_or(0) + count;
        if total > self.page_len(page) {
            Err(WriteError::PageCompletedTwice)
        } else {
            Ok(total)
        }
    }
    pub(crate) fn take_pending_eviction_ranges(&mut self, force: bool) -> Vec<Range<usize>> {
        if !force && self.completed_unevicted_pages < self.eviction_batch_pages {
            return Vec::new();
        }
        let mut ranges = std::mem::take(&mut self.pending_eviction_ranges);
        coalesce(&mut ranges);
        for range in &ranges {
            self.evicted.set_range(range.clone());
            self.completed_unevicted_pages -= range.len();
        }
        ranges
    }
}
pub(crate) fn page_range(
    size: usize,
    page_size: usize,
    offset: u64,
    len: usize,
) -> Result<Option<Range<usize>>, WriteError> {
    assert!(page_size > 0);
    if len == 0 {
        return Ok(None);
    }
    let start = usize::try_from(offset).map_err(|_| WriteError::OutOfBounds)?;
    let end = start
        .checked_add(len)
        .filter(|&end| end <= size)
        .ok_or(WriteError::OutOfBounds)?;
    Ok(Some(start / page_size..end.div_ceil(page_size)))
}
pub(crate) fn coalesce(ranges: &mut Vec<Range<usize>>) {
    ranges.sort_unstable_by_key(|range| range.start);
    let mut write = 0;
    for read in 0..ranges.len() {
        if write != 0 && ranges[write - 1].end == ranges[read].start {
            ranges[write - 1].end = ranges[read].end;
        } else {
            assert!(write == 0 || ranges[write - 1].end <= ranges[read].start);
            ranges[write] = ranges[read].clone();
            write += 1;
        }
    }
    ranges.truncate(write);
}
#[cfg(test)]
mod tests;
