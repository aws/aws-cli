#![expect(
    clippy::single_range_in_vec_init,
    reason = "expected merged callback range"
)]
#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::*;
#[test]
fn download_callback_range_tracker_rejects_invalid_overlap_and_duplicate_ranges() {
    let mut ranges = CallbackRangeTracker::default();
    ranges.add(12, 8, 4).unwrap();
    ranges.add(12, 0, 4).unwrap();
    assert!(!ranges.is_complete(12));
    assert_eq!(ranges.add(12, 2, 6), Err(WriteError::Overlap));
    ranges.add(12, 4, 4).unwrap();
    assert!(ranges.is_complete(12));
    assert_eq!(ranges.ranges(), &[0..12]);
    assert_eq!(ranges.add(12, 0, 4), Err(WriteError::Overlap));
    assert_eq!(ranges.add(12, 12, 1), Err(WriteError::OutOfBounds));
    assert_eq!(
        ranges.add(u64::MAX, u64::MAX, 1),
        Err(WriteError::OutOfBounds)
    );
    ranges.add(12, u64::MAX, 0).unwrap();
}
