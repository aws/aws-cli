use super::super::{WriteError, pages::PageCompletionTracker, range::CallbackRangeTracker};
use crate::testing::Choices;

/// Compares callback acceptance and coalescing against byte occupancy, including u64 overflow.
pub fn callback_ranges(bytes: &[u8]) {
    callback_ranges_from(&mut Choices::new(bytes));
}
pub(super) fn callback_ranges_from(input: &mut Choices<'_>) {
    let size = input.range(0, 64);
    let mut occupied = vec![false; size];
    let mut ranges = CallbackRangeTracker::default();
    for _ in 0..128 {
        let start = if input.flag() {
            input.word()
        } else {
            input.range(0, size + 1) as u64
        };
        let length = input.range(0, size + 1);
        let result = ranges.add(size as u64, start, length);
        let end = u128::from(start) + length as u128;
        let expected = expected_range(&mut occupied, start, length, end);
        assert_eq!(result, expected);
        let mut actual = vec![false; size];
        for range in ranges.ranges() {
            assert!(range.start < range.end && range.end <= size as u64);
            actual[range.start as usize..range.end as usize].fill(true);
        }
        assert_eq!(actual, occupied);
        assert!(
            ranges
                .ranges()
                .windows(2)
                .all(|pair| pair[0].end < pair[1].start)
        );
    }
}

/// The result `CallbackRangeTracker::add` gives a range over the `occupied`
/// bytes, which an accepted range then occupies.
pub(super) fn expected_range(
    occupied: &mut [bool],
    start: u64,
    length: usize,
    end: u128,
) -> Result<(), WriteError> {
    if length == 0 {
        return Ok(());
    }
    if end > occupied.len() as u128 {
        return Err(WriteError::OutOfBounds);
    }
    if occupied[start as usize..end as usize]
        .iter()
        .any(|&bit| bit)
    {
        return Err(WriteError::Overlap);
    }
    occupied[start as usize..end as usize].fill(true);
    Ok(())
}

/// Checks shuffled partial-page completions and exact batch/forced eviction against bitmaps.
pub fn page_completion(bytes: &[u8]) {
    page_completion_from(&mut Choices::new(bytes));
}
pub(super) fn page_completion_from(input: &mut Choices<'_>) {
    let size = input.range(1, 256);
    let page = 1usize << input.range(0, 6);
    let batch = input.range(1, 8);
    let mut chunks = Vec::new();
    let mut start = 0;
    while start < size {
        let length = if input.flag() {
            page.min(size - start)
        } else {
            input.range(1, 64.min(size - start))
        };
        chunks.push(start..start + length);
        start += length;
    }
    let mut tracker = PageCompletionTracker::new(size, page, page * batch);
    let mut written = vec![false; size];
    let mut evicted = vec![false; size.div_ceil(page)];
    while !chunks.is_empty() {
        let chunk = chunks.swap_remove(input.index(chunks.len()));
        tracker
            .complete_range(chunk.start as u64, chunk.len())
            .unwrap();
        written[chunk].fill(true);
        check_evictions(
            &mut tracker,
            &written,
            &mut evicted,
            page,
            batch,
            input.flag(),
        );
    }
    check_evictions(&mut tracker, &written, &mut evicted, page, batch, true);
    assert!(evicted.iter().all(|&bit| bit));
}

fn check_evictions(
    tracker: &mut PageCompletionTracker,
    written: &[bool],
    evicted: &mut [bool],
    page: usize,
    batch: usize,
    force: bool,
) {
    let completed: Vec<_> = written
        .chunks(page)
        .map(|bytes| bytes.iter().all(|&bit| bit))
        .collect();
    let pending = completed
        .iter()
        .zip(evicted.iter())
        .filter(|(done, evicted)| **done && !**evicted)
        .count();
    let actual_complete: Vec<_> = (0..completed.len())
        .filter(|&index| tracker.is_completed(index))
        .collect();
    assert_eq!(
        actual_complete,
        completed
            .iter()
            .enumerate()
            .filter_map(|(i, done)| done.then_some(i))
            .collect::<Vec<_>>()
    );
    let mut returned = vec![false; evicted.len()];
    let mut previous_end = None;
    for range in tracker.take_pending_eviction_ranges(force) {
        assert!(range.start < range.end && range.end <= evicted.len());
        assert!(previous_end.is_none_or(|end| end < range.start));
        previous_end = Some(range.end);
        returned[range].fill(true);
    }
    for index in 0..evicted.len() {
        assert_eq!(
            returned[index],
            (force || pending >= batch) && completed[index] && !evicted[index]
        );
        evicted[index] |= returned[index];
    }
}
