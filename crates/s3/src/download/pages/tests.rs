#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::*;

#[test]
fn tracking_and_eviction_storage_retains_partial_pages_until_completion() {
    let mut tracker = PageCompletionTracker::new(8192 + 17, 4096, 4096);
    tracker.complete_range(4096, 1024).unwrap();
    assert_eq!(tracker.partial.get(&1), Some(&1024));
    assert_eq!(tracker.completed_unevicted_pages, 0);
    assert!(tracker.pending_eviction_ranges.is_empty());
    tracker.complete_range(0, 4096).unwrap();
    tracker.complete_range(5120, 3072 + 17).unwrap();
    assert!(tracker.partial.is_empty());
    assert_eq!(tracker.completed_unevicted_pages, 3);
    assert_eq!(tracker.take_pending_eviction_ranges(true), vec![0..3]);
    assert_eq!(tracker.completed_unevicted_pages, 0);
    assert!((0..3).all(|page| tracker.evicted.contains(page)));
}
#[test]
fn page_range_handles_zero_length_file_end_and_arithmetic_overflow() {
    assert_eq!(page_range(0, 4096, u64::MAX, 0), Ok(None));
    assert_eq!(page_range(4097, 4096, 4096, 1), Ok(Some(1..2)));
    assert_eq!(
        page_range(4097, 4096, 4097, 1),
        Err(WriteError::OutOfBounds)
    );
    assert_eq!(
        page_range(usize::MAX, 4096, u64::MAX, 1),
        Err(WriteError::OutOfBounds)
    );
}
#[test]
fn page_completion_tracker_waits_for_shared_boundary_pages() {
    let mut tracker = PageCompletionTracker::new(12, 4, 4);
    tracker.complete_range(0, 6).unwrap();
    assert_eq!(tracker.take_pending_eviction_ranges(false), vec![0..1]);
    tracker.complete_range(6, 6).unwrap();
    assert_eq!(tracker.take_pending_eviction_ranges(false), vec![1..3]);
}
#[test]
fn page_completion_tracker_rejects_duplicate_completed_bytes() {
    let mut tracker = PageCompletionTracker::new(8, 4, 8);
    tracker.complete_range(0, 4).unwrap();
    assert_eq!(
        tracker.complete_range(0, 1),
        Err(WriteError::PageCompletedTwice)
    );
    tracker.take_pending_eviction_ranges(true);
    assert_eq!(
        tracker.complete_range(0, 1),
        Err(WriteError::PageAlreadyEvicted)
    );
    tracker.complete_range(4, 3).unwrap();
    assert_eq!(
        tracker.complete_range(6, 2),
        Err(WriteError::PageCompletedTwice)
    );
}
#[test]
fn page_completion_tracker_handles_shuffled_aligned_full_page_ranges() {
    let mut tracker = PageCompletionTracker::new(16, 4, 16);
    tracker.complete_range(12, 4).unwrap();
    tracker.complete_range(4, 4).unwrap();
    tracker.complete_range(0, 4).unwrap();
    tracker.complete_range(8, 4).unwrap();
    assert_eq!(tracker.completed_unevicted_pages, 4);
    assert!(tracker.partial.is_empty());
    assert_eq!(
        tracker.complete_range(0, 8),
        Err(WriteError::PageCompletedTwice)
    );
    assert_eq!(tracker.take_pending_eviction_ranges(false), vec![0..4]);
    assert_eq!(
        tracker.complete_range(0, 8),
        Err(WriteError::PageAlreadyEvicted)
    );
}
#[test]
fn whole_page_completion_reports_the_first_rejected_page() {
    let mut tracker = PageCompletionTracker::new(16, 4, 64);
    tracker.complete_range(4, 4).unwrap();
    tracker.take_pending_eviction_ranges(true);
    tracker.complete_range(12, 4).unwrap();
    assert_eq!(
        tracker.complete_range(0, 16),
        Err(WriteError::PageAlreadyEvicted)
    );
    let mut tracker = PageCompletionTracker::new(16, 4, 64);
    tracker.complete_range(8, 4).unwrap();
    tracker.take_pending_eviction_ranges(true);
    tracker.complete_range(0, 4).unwrap();
    assert_eq!(
        tracker.complete_range(0, 16),
        Err(WriteError::PageCompletedTwice)
    );
    assert_eq!(tracker.completed_unevicted_pages, 1);
    assert_eq!(tracker.pending_eviction_ranges, vec![0..1]);
    assert!(!tracker.is_completed(1) && !tracker.is_completed(3));
}
#[test]
fn page_completion_tracker_reports_the_first_failing_page_in_page_order() {
    let mut tracker = PageCompletionTracker::new(12, 4, 12);
    tracker.complete_range(0, 2).unwrap();
    tracker.complete_range(4, 4).unwrap();
    assert_eq!(tracker.take_pending_eviction_ranges(true), vec![1..2]);
    assert_eq!(
        tracker.complete_range(1, 4),
        Err(WriteError::PageCompletedTwice)
    );
    assert_eq!(tracker.partial.get(&0), Some(&2));
}
#[test]
fn whole_page_completion_matches_the_per_page_path() {
    const PAGES: usize = 2048;
    let page = 4096;
    let mut whole = PageCompletionTracker::new((PAGES + 1) * page, page, 8 * 1024 * 1024);
    whole.complete_range(0, PAGES * page).unwrap();
    whole.complete_range((PAGES * page) as u64, 1).unwrap();
    let mut walked = PageCompletionTracker::new((PAGES + 1) * page, page, 8 * 1024 * 1024);
    walked.complete_range((PAGES * page) as u64, 1).unwrap();
    walked.complete_range(0, PAGES * page).unwrap();
    for tracker in [&whole, &walked] {
        assert_eq!(tracker.pending_eviction_ranges, vec![0..PAGES]);
        assert_eq!(tracker.completed_unevicted_pages, PAGES);
        assert_eq!(tracker.partial.get(&PAGES), Some(&1));
        assert!((0..PAGES).all(|index| tracker.is_completed(index)));
        assert!(!tracker.is_completed(PAGES));
    }
    assert_eq!(whole.completed.words, walked.completed.words);
    assert_eq!(
        whole.take_pending_eviction_ranges(false),
        walked.take_pending_eviction_ranges(false)
    );
    assert_eq!(whole.evicted.words, walked.evicted.words);
}
#[test]
fn page_completion_tracker_retains_partial_page_fallback_for_aligned_ranges() {
    let mut tracker = PageCompletionTracker::new(12, 4, 12);
    tracker.complete_range(0, 2).unwrap();
    tracker.complete_range(4, 4).unwrap();
    assert_eq!(tracker.take_pending_eviction_ranges(true), vec![1..2]);
    tracker.complete_range(2, 2).unwrap();
    tracker.complete_range(8, 4).unwrap();
    assert_eq!(tracker.take_pending_eviction_ranges(true), vec![0..1, 2..3]);
}
#[test]
fn first_set_bit_range_scan_masks_boundary_words() {
    let mut bits = Bits::new(200);
    for bit in [0, 63, 64, 127, 128, 199] {
        bits.set(bit);
    }
    assert_eq!(bits.first(1..63), None);
    assert_eq!(bits.first(1..64), Some(63));
    assert_eq!(bits.first(64..65), Some(64));
    assert_eq!(bits.first(65..128), Some(127));
    assert_eq!(bits.first(129..199), None);
    assert_eq!(bits.first(129..200), Some(199));
}
#[test]
fn set_range_matches_setting_each_bit_across_word_boundaries() {
    for range in [63..130, 0..64, 64..128, 1..2, 0..200, 130..130, 127..129] {
        let mut ranged = Bits::new(200);
        ranged.set_range(range.clone());
        let mut each = Bits::new(200);
        for bit in range.clone() {
            each.set(bit);
        }
        assert_eq!(ranged.words, each.words, "{range:?}");
    }
}
#[test]
fn page_completion_tracker_coalesces_adjacent_eviction_ranges() {
    let mut tracker = PageCompletionTracker::new(12, 4, 12);
    tracker.complete_range(0, 4).unwrap();
    tracker.complete_range(4, 4).unwrap();
    tracker.complete_range(8, 4).unwrap();
    assert_eq!(tracker.take_pending_eviction_ranges(false), vec![0..3]);
}
#[test]
fn page_completion_tracker_drains_out_of_order_eviction_ranges() {
    let mut tracker = PageCompletionTracker::new(16, 4, 8);
    tracker.complete_range(8, 4).unwrap();
    assert!(tracker.take_pending_eviction_ranges(false).is_empty());
    assert_eq!(tracker.pending_eviction_ranges, vec![2..3]);
    tracker.complete_range(0, 4).unwrap();
    assert_eq!(tracker.pending_eviction_ranges, vec![2..3, 0..1]);
    assert_eq!(
        tracker.take_pending_eviction_ranges(false),
        vec![0..1, 2..3]
    );
    assert_eq!(tracker.completed_unevicted_pages, 0);
    let evicted: Vec<_> = (0..4).map(|page| tracker.evicted.contains(page)).collect();
    assert_eq!(evicted, [true, false, true, false]);
}
#[test]
fn page_completion_tracker_coalesces_out_of_order_adjacent_ranges_before_eviction() {
    let mut ranges = vec![4..6, 0..2, 2..4, 8..9];
    coalesce(&mut ranges);
    assert_eq!(ranges, vec![0..6, 8..9]);
}
#[test]
fn page_completion_tracker_force_drains_below_eviction_threshold() {
    let mut tracker = PageCompletionTracker::new(16, 4, 100);
    tracker.complete_range(4, 4).unwrap();
    assert!(tracker.take_pending_eviction_ranges(false).is_empty());
    assert_eq!(tracker.take_pending_eviction_ranges(true), vec![1..2]);
    assert!(tracker.take_pending_eviction_ranges(true).is_empty());
}
#[test]
fn page_count_and_eviction_batch_round_up_to_whole_pages() {
    let tracker = PageCompletionTracker::new(1_048_577, 4096, 512 * 1024 * 1024);
    assert_eq!(
        (tracker.page_count(), tracker.eviction_batch_pages()),
        (257, 131_072)
    );
    let tracker = PageCompletionTracker::new(4096, 4096, 1);
    assert_eq!(
        (tracker.page_count(), tracker.eviction_batch_pages()),
        (1, 1)
    );
}
