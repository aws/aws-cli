#![allow(
    clippy::expect_used,
    clippy::panic,
    reason = "a listed destination never fails unless the test makes it"
)]
use super::*;
use std::collections::VecDeque;

#[derive(Debug, Default)]
struct Listed {
    entries: VecDeque<Entry<Vec<u8>>>,
    pulls: usize,
    failing: Option<usize>,
}
impl Listed {
    fn new(entries: &[(&str, u64, i64)]) -> Self {
        Self {
            entries: entries
                .iter()
                .map(|&(name, size, seconds)| Entry {
                    name: name.as_bytes().to_vec(),
                    size,
                    modified: Modified::from_epoch_seconds(seconds),
                })
                .collect(),
            ..Self::default()
        }
    }
}
impl Destination for Listed {
    type Name = Vec<u8>;
    type Error = &'static str;
    fn next_entry(&mut self) -> Result<Option<Entry<Vec<u8>>>, &'static str> {
        self.pulls += 1;
        if self.failing == Some(self.pulls) {
            return Err("destination failed");
        }
        Ok(self.entries.pop_front())
    }
}

fn keep(_: Entry<Vec<u8>>) -> ControlFlow<()> {
    ControlFlow::Continue(())
}

fn transfers(pairing: Pairing) -> bool {
    match pairing {
        Pairing::Both(transfers) => transfers,
        Pairing::SourceOnly => true,
        Pairing::Stopped => panic!("no remover stops a kept destination"),
    }
}

fn source(name: &str, size: u64, seconds: i64) -> Entry<&[u8]> {
    Entry {
        name: name.as_bytes(),
        size,
        modified: Modified::from_epoch_seconds(seconds),
    }
}

fn pair_all(
    local: LocalSide,
    destination: &[(&str, u64, i64)],
    sources: &[(&str, u64, i64)],
) -> Vec<bool> {
    let mut comparator = Comparator::new(Strategies::default(), local, Listed::new(destination));
    let decisions = sources
        .iter()
        .map(|&(name, size, seconds)| {
            comparator
                .pair(&source(name, size, seconds), &mut keep)
                .map(transfers)
                .expect("listed destination")
        })
        .collect();
    assert!(
        comparator
            .finish(&mut keep)
            .expect("listed destination")
            .is_continue()
    );
    assert!(comparator.into_destination().entries.is_empty());
    decisions
}

#[test]
fn mtimes_round_as_python_reads_st_mtime() {
    // `datetime.fromtimestamp(seconds + nanoseconds * 1e-9, timezone.utc)`
    // in CPython 3.14, as microseconds since the epoch.
    let mut cases = vec![
        ((1_767_323_045, 0), 1_767_323_045_000_000),
        ((1_767_323_045, 400), 1_767_323_045_000_000),
        ((1_767_323_045, 600), 1_767_323_045_000_001),
        ((1_767_323_045, 500), 1_767_323_045_000_000),
        ((1_767_323_045, 500_000_000), 1_767_323_045_500_000),
        ((1_767_323_045, 999_999_999), 1_767_323_046_000_000),
        ((1_767_323_045, 999_999_500), 1_767_323_046_000_000),
        ((0, 1), 0),
        ((0, 499), 0),
        ((0, 500), 1),
        ((0, 501), 1),
        ((0, 1500), 2),
        ((0, 2500), 2),
        ((-1, 999_999_999), 0),
    ];
    // Windows reads no time before the epoch.
    if cfg!(not(windows)) {
        cases.extend([
            ((-1, 500_000_000), -500_000),
            ((-2, 999_999_999), -1_000_000),
        ]);
    }
    for ((seconds, nanoseconds), micros) in cases {
        assert_eq!(
            Modified::from_mtime(seconds, nanoseconds),
            Some(Modified(micros)),
            "{seconds} {nanoseconds}"
        );
    }
}

/// The first and last mtimes upstream reads in UTC, to the microsecond it
/// rounds each to, from CPython 3.14 with dateutil 2.9.0 off Windows, and
/// from the UCRT's bounds on Windows.
#[test]
fn mtimes_upstream_cannot_read_are_none() {
    let (first, last) = if cfg!(windows) {
        (0, 32_536_799_999)
    } else {
        (-62_135_596_800, 253_402_300_799)
    };
    for ((seconds, nanoseconds), micros) in [
        ((first, 0), Some(first * 1_000_000)),
        ((first - 1, 0), None),
        ((first - 1, 499_999_999), None),
        ((last, 0), Some(last * 1_000_000)),
        ((last, 999_999_999), None),
        ((last + 1, 0), None),
        ((i64::MAX, 0), None),
        ((i64::MIN, 0), None),
    ] {
        assert_eq!(
            Modified::from_mtime(seconds, nanoseconds),
            micros.map(Modified),
            "{seconds} {nanoseconds}"
        );
    }
}

#[test]
fn a_system_time_splits_as_st_mtime_does() {
    use std::time::{Duration, UNIX_EPOCH};
    // Each time is a whole number of the 100 nanoseconds Windows counts in.
    for (time, split) in [
        (UNIX_EPOCH + Duration::new(5, 700), (5, 700)),
        (UNIX_EPOCH - Duration::new(1, 0), (-1, 0)),
        (
            UNIX_EPOCH - Duration::new(1, 500_000_000),
            (-2, 500_000_000),
        ),
    ] {
        assert_eq!(split_system_time(time), Some(split), "{time:?}");
    }
}

#[test]
fn names_compare_by_code_point_with_surrogate_escapes() {
    use Ordering::Less;
    for (a, b, order) in [
        (&b"a-b.txt"[..], &b"a.txt"[..], Less),
        (b"a.txt", b"a/b.txt", Less),
        (b"a/b.txt", b"a0.txt", Less),
        (b"a", b"a/", Less),
        // A byte outside UTF-8 decodes to U+DC80 through U+DCFF, which sort
        // before U+E000 and every supplementary character, as their bytes
        // do not.
        (b"\xf0", "\u{e000}".as_bytes(), Less),
        (b"\xff", "\u{10000}".as_bytes(), Less),
        ("é".as_bytes(), b"\xe9", Less),
    ] {
        assert_eq!(compare_names(a, b), order, "{a:?} {b:?}");
        assert_eq!(compare_names(b, a), order.reverse(), "{b:?} {a:?}");
    }
    assert_eq!(compare_names(b"same", b"same"), Ordering::Equal);
}

#[test]
fn an_upload_transfers_new_and_resized_files_and_files_newer_than_their_objects() {
    let destination = [
        ("a.txt", 4, 100),
        ("b.txt", 4, 100),
        ("c.txt", 4, 100),
        ("d.txt", 4, 100),
        ("only-remote.txt", 4, 100),
        ("z.txt", 4, 100),
    ];
    let sources = [
        ("a.txt", 4, 50),
        ("b.txt", 4, 100),
        ("c.txt", 4, 101),
        ("d.txt", 5, 50),
        ("e.txt", 4, 50),
        ("z.txt", 4, 50),
    ];
    assert_eq!(
        pair_all(LocalSide::Source, &destination, &sources),
        [false, false, true, true, true, false]
    );
}

#[test]
fn a_download_transfers_objects_newer_files_hold_or_resized_ones() {
    let destination = [
        ("a.txt", 4, 50),
        ("b.txt", 4, 100),
        ("c.txt", 4, 101),
        ("d.txt", 5, 50),
    ];
    let sources = [
        ("a.txt", 4, 100),
        ("b.txt", 4, 100),
        ("c.txt", 4, 100),
        ("d.txt", 4, 100),
        ("e.txt", 4, 100),
    ];
    assert_eq!(
        pair_all(LocalSide::Destination, &destination, &sources),
        [false, false, true, true, true]
    );
}

#[test]
fn the_destination_is_pulled_only_as_far_as_each_source_needs() {
    let destination = Listed::new(&[("a", 1, 0), ("b", 1, 0), ("c", 1, 0), ("d", 1, 0)]);
    let mut comparator = Comparator::new(Strategies::default(), LocalSide::Source, destination);
    for (name, pairing, pulls) in [
        ("a", Pairing::Both(false), 1),
        ("a0", Pairing::SourceOnly, 2),
        ("c", Pairing::Both(false), 3),
    ] {
        assert_eq!(comparator.pair(&source(name, 1, 0), &mut keep), Ok(pairing));
        assert_eq!(comparator.destination.pulls, pulls, "{name}");
    }
    for _ in 0..2 {
        assert_eq!(comparator.finish(&mut keep), Ok(ControlFlow::Continue(())));
        assert_eq!(comparator.destination.pulls, 5);
    }
}

#[test]
fn an_empty_source_still_pulls_every_destination_entry() {
    let mut comparator = Comparator::new(
        Strategies::default(),
        LocalSide::Destination,
        Listed::new(&[("a", 1, 0), ("b", 1, 0)]),
    );
    assert!(comparator.finish(&mut keep).expect("listed").is_continue());
    assert_eq!(comparator.into_destination().pulls, 3);
}

#[test]
fn an_unordered_side_pairs_as_upstream_s_merge_does() {
    assert_eq!(
        pair_all(
            LocalSide::Source,
            &[("a", 1, 100), ("b", 1, 100)],
            &[("b", 1, 50), ("a", 1, 50)]
        ),
        [false, true]
    );
}

#[test]
fn a_destination_failure_ends_the_pairing() {
    let mut destination = Listed::new(&[("a", 1, 0), ("b", 1, 0)]);
    destination.failing = Some(2);
    let mut comparator = Comparator::new(Strategies::default(), LocalSide::Source, destination);
    assert_eq!(
        comparator.pair(&source("a", 1, 0), &mut keep),
        Ok(Pairing::Both(false))
    );
    assert_eq!(
        comparator.pair(&source("b", 1, 0), &mut keep),
        Err("destination failed")
    );

    let mut destination = Listed::new(&[("a", 1, 0)]);
    destination.failing = Some(2);
    let mut comparator = Comparator::new(Strategies::default(), LocalSide::Source, destination);
    assert_eq!(
        comparator.pair(&source("0", 1, 0), &mut keep),
        Ok(Pairing::SourceOnly)
    );
    assert_eq!(comparator.finish(&mut keep), Err("destination failed"));
}

#[test]
fn a_local_name_separates_its_components_with_a_slash() {
    let relative = Path::new("a").join("b.txt");
    assert_eq!(&*local_name(&relative), b"a/b.txt");
    let name = LocalName::from_relative_path(relative.clone());
    assert_eq!(name.as_bytes(), b"a/b.txt");
    assert_eq!(name.into_relative_path(), relative);
}

fn decides(both: BothSides, sizes: (u64, u64), local: i64, remote: i64) -> [bool; 2] {
    let strategies = Strategies {
        both,
        ..Strategies::default()
    };
    [
        (LocalSide::Source, (sizes.0, local), (sizes.1, remote)),
        (LocalSide::Destination, (sizes.1, remote), (sizes.0, local)),
    ]
    .map(|(side, (source_size, source_time), (size, time))| {
        let destination = Listed::new(&[("a", size, time)]);
        let mut comparator = Comparator::new(strategies, side, destination);
        comparator
            .pair(&source("a", source_size, source_time), &mut keep)
            .map(transfers)
            .expect("listed")
    })
}

#[test]
fn each_strategy_decides_a_name_both_sides_hold_as_upstream_s_does() {
    use BothSides::*;
    for (both, cases) in [
        (
            SizeAndLastModified,
            [[false, false], [true, true], [true, true], [false, false]],
        ),
        (
            SizeOnly,
            [[false, false], [true, true], [false, false], [false, false]],
        ),
        (
            ExactTimestamps,
            [[false, false], [true, true], [true, true], [false, true]],
        ),
        (Never, [[false, false]; 4]),
        (Always, [[true, true]; 4]),
    ] {
        let pairs = [((4, 4), 100), ((5, 4), 100), ((4, 4), 101), ((4, 4), 99)];
        for ((sizes, local), expected) in pairs.into_iter().zip(cases) {
            assert_eq!(
                decides(both, sizes, local, 100),
                expected,
                "{both:?} {sizes:?} {local}"
            );
        }
    }
}

#[test]
fn delete_removes_each_name_only_the_destination_holds_as_it_passes_it() {
    let strategies = Strategies {
        destination_only: DestinationOnly::Delete,
        ..Strategies::default()
    };
    let destination = Listed::new(&[("a", 1, 0), ("b", 1, 0), ("c", 1, 0), ("e", 1, 0)]);
    let mut comparator = Comparator::new(strategies, LocalSide::Source, destination);
    let mut removed = Vec::new();
    let mut remove = |entry: Entry<Vec<u8>>| {
        removed.push(entry.name);
        ControlFlow::Continue(())
    };
    assert_eq!(
        comparator.pair(&source("b", 1, 0), &mut remove),
        Ok(Pairing::Both(false))
    );
    assert_eq!(
        comparator.pair(&source("d", 1, 0), &mut remove),
        Ok(Pairing::SourceOnly)
    );
    assert_eq!(
        comparator.finish(&mut remove),
        Ok(ControlFlow::Continue(()))
    );
    assert_eq!(removed, [b"a", b"c", b"e"]);
}

#[test]
fn a_remover_that_breaks_stops_the_comparator() {
    let strategies = Strategies {
        destination_only: DestinationOnly::Delete,
        ..Strategies::default()
    };
    let destination = Listed::new(&[("a", 1, 0), ("b", 1, 0), ("c", 1, 0)]);
    let mut comparator = Comparator::new(strategies, LocalSide::Source, destination);
    let mut stop = |_: Entry<Vec<u8>>| ControlFlow::Break(());
    assert_eq!(
        comparator.pair(&source("b", 1, 0), &mut stop),
        Ok(Pairing::Stopped)
    );
    assert_eq!(comparator.finish(&mut stop), Ok(ControlFlow::Break(())));
    assert_eq!(comparator.into_destination().pulls, 2);
}
