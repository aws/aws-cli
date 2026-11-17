use super::*;
#[test]
fn group_match_reports_no_matches() {
    assert_eq!(match_h2(&[1; WIDTH], 0, 2), 0);
    assert!(!any_empty(&[1; WIDTH], 0, 0x80));
}
#[test]
fn group_match_reports_single_and_multiple_h2_matches() {
    let control = [0x7f, 1, 2, 0x7f, 3, 4, 0x7f, 5, 6, 7, 8, 9, 10, 11, 12, 13];
    assert_eq!(match_h2(&control, 0, 0x7f), 0x49);
    assert_eq!(match_h2(&control, 0, 1), 2);
}
#[test]
fn group_match_handles_h2_boundary_values_and_empty_bytes() {
    let control = [
        0, 0x80, 0x7f, 0x80, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0, 0x7f, 0x80, 1, 2,
    ];
    assert_eq!(match_h2(&control, 0, 0), 0x801);
    assert_eq!(match_h2(&control, 0, 0x7f), 0x1004);
    assert!(any_empty(&control, 0, 0x80));
}
#[test]
fn group_match_loads_from_runtime_bucket_offset() {
    let control = [
        1, 2, 3, 4, 0xaa, 0xbb, 0xaa, 0xcc, 0xdd, 0xaa, 0xee, 0xff, 0xaa, 16, 17, 18, 19, 20, 21,
        22,
    ];
    assert_eq!(match_h2(&control, 4, 0xaa), 0x125);
}
#[test]
fn group_mask_bit_order_maps_lane_zero_to_bit_zero() {
    let control = [0xaa, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 0xaa];
    assert_eq!(match_h2(&control, 0, 0xaa), 0x8001);
    for needle in 0..=255 {
        assert_eq!(
            match_h2(&control, 0, needle),
            scalar_match(&control, needle)
        );
        assert_eq!(
            any_empty(&control, 0, needle),
            scalar_match(&control, needle) != 0
        );
    }
}
fn scalar_match(group: &[u8], needle: u8) -> u16 {
    group[..WIDTH]
        .iter()
        .enumerate()
        .fold(0, |mask, (lane, &byte)| {
            mask | (u16::from(byte == needle) << lane)
        })
}
#[test]
fn probe_sequence_uses_triangular_group_steps() {
    let mut probe = ProbeSeq::new(3, 63);
    for bucket in [3, 19, 51, 35] {
        assert_eq!(probe.bucket, bucket);
        probe.advance();
    }
}
#[test]
fn probe_sequence_visits_every_group_before_repeating() {
    let mut seen = [false; 16];
    let mut probe = ProbeSeq::new(7, 255);
    for _ in 0..16 {
        assert!(!seen[probe.bucket / WIDTH]);
        seen[probe.bucket / WIDTH] = true;
        probe.advance();
    }
    assert!(seen.into_iter().all(|visited| visited));
}
