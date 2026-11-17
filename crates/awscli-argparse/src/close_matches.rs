//! difflib.get_close_matches as CLIArgParser._check_value calls it: the
//! SequenceMatcher ratio over Python's code-point elements with the default
//! autojunk heuristic, a 0.8 cutoff, and the three best candidates in
//! heapq.nlargest order.
use crate::SUGGESTION_COUNT_MAX;
use std::collections::{HashMap, HashSet};
const CUTOFF: f64 = 0.8;
/// SequenceMatcher applies its popular-element heuristic from this length.
const AUTOJUNK_LEN_MIN: usize = 200;
/// Python compares argv strings by code point, with each byte of an
/// invalid UTF-8 sequence its own surrogate-escaped element.
const SURROGATE_ESCAPE_BASE: u32 = 0xdc00;
#[derive(Debug, Clone, Copy)]
struct Match {
    a: usize,
    b: usize,
    size: usize,
}
#[derive(Debug, Clone, Copy)]
struct Range {
    alo: usize,
    ahi: usize,
    blo: usize,
    bhi: usize,
}
impl Range {
    fn split(self, found: Match) -> [Option<Self>; 2] {
        let before = (self.alo < found.a && self.blo < found.b).then_some(Self {
            ahi: found.a,
            bhi: found.b,
            ..self
        });
        let after =
            (found.a + found.size < self.ahi && found.b + found.size < self.bhi).then_some(Self {
                alo: found.a + found.size,
                blo: found.b + found.size,
                ..self
            });
        [before, after]
    }
}
#[derive(Debug, Clone, Copy)]
struct Candidate<'a> {
    ratio: f64,
    choice: &'a str,
}
#[derive(Debug)]
struct Matcher {
    a: Vec<u32>,
    b: Vec<u32>,
    popular: HashSet<u32>,
    prev: Vec<usize>,
    cur: Vec<usize>,
}
/// Decode argv bytes as Python's surrogateescape handler.
pub fn decode(text: &[u8]) -> Vec<u32> {
    let mut output = Vec::new();
    let mut remaining = text;
    while !remaining.is_empty() {
        match std::str::from_utf8(remaining) {
            Ok(s) => {
                output.extend(s.chars().map(u32::from));
                break;
            }
            Err(e) => {
                let valid = e.valid_up_to();
                if let Ok(s) = std::str::from_utf8(&remaining[..valid]) {
                    output.extend(s.chars().map(u32::from));
                }
                let end = valid + e.error_len().unwrap_or(remaining.len() - valid);
                output.extend(
                    remaining[valid..end]
                        .iter()
                        .map(|b| SURROGATE_ESCAPE_BASE + u32::from(*b)),
                );
                remaining = &remaining[end..];
            }
        }
    }
    output
}
/// The candidates from `choices` scoring at least the cutoff against
/// `word`, best first. `word` is the rejected value; the choices are the
/// table's spellings.
pub fn close_matches<'a>(word: &[u8], choices: &[&'a str]) -> Vec<&'a str> {
    // SequenceMatcher's b is the word; every choice is compared as a.
    let b = decode(word);
    let mut matcher = Matcher {
        a: Vec::new(),
        popular: popular_elements(&b),
        prev: vec![0; b.len() + 1],
        cur: vec![0; b.len() + 1],
        b,
    };
    let mut candidates = Vec::new();
    for &choice in choices {
        // SequenceMatcher.set_seq1: b and its index stay; only a changes.
        matcher.a = decode(choice.as_bytes());
        let matched = matcher.matching_total();
        let ratio = ratio_of(matched, matcher.a.len() + matcher.b.len());
        if ratio >= CUTOFF {
            candidates.push(Candidate { ratio, choice });
        }
    }
    // heapq.nlargest keeps the greatest (ratio, choice) tuples; a stable
    // descending sort of every candidate yields the same order.
    candidates.sort_by(|x, y| {
        y.ratio
            .total_cmp(&x.ratio)
            .then_with(|| y.choice.cmp(x.choice))
    });
    candidates
        .into_iter()
        .take(SUGGESTION_COUNT_MAX)
        .map(|candidate| candidate.choice)
        .collect()
}
/// SequenceMatcher.ratio: 2.0 * M / T, and 1.0 for two empty sequences.
/// `matched` is M, the elements in matching blocks; `total` is T, the
/// elements in both sequences together.
fn ratio_of(matched: usize, total: usize) -> f64 {
    debug_assert!(2 * matched <= total);
    if total == 0 {
        1.0
    } else {
        2.0 * matched as f64 / total as f64
    }
}
/// The autojunk heuristic: in a sequence of at least 200 elements, an
/// element occurring more than one percent of the time (plus one) is
/// dropped from the index so the longest-match search never starts on it.
fn popular_elements(b: &[u32]) -> HashSet<u32> {
    if b.len() < AUTOJUNK_LEN_MIN {
        return HashSet::new();
    }
    let threshold = b.len() / 100 + 1;
    let mut counts = HashMap::new();
    for element in b {
        *counts.entry(*element).or_insert(0usize) += 1;
    }
    counts
        .into_iter()
        .filter(|(_, count)| *count > threshold)
        .map(|(element, _)| element)
        .collect()
}
impl Matcher {
    fn matching_total(&mut self) -> usize {
        debug_assert!(self.prev.len() == self.b.len() + 1);
        debug_assert!(self.cur.len() == self.b.len() + 1);
        let mut queue = vec![Range {
            alo: 0,
            ahi: self.a.len(),
            blo: 0,
            bhi: self.b.len(),
        }];
        let mut total = 0;
        for _ in 0..=self.a.len() {
            let Some(range) = queue.pop() else {
                break;
            };
            let found = self.longest_match(range);
            if found.size == 0 {
                continue;
            }
            total += found.size;
            queue.extend(range.split(found).into_iter().flatten());
        }
        assert!(queue.is_empty());
        assert!(total <= self.a.len().min(self.b.len()));
        total
    }
    /// SequenceMatcher.find_longest_match with an empty junk set: the longest
    /// block of non-popular elements, earliest in a and then in b among ties,
    /// extended over equal elements on both ends.
    fn longest_match(&mut self, range: Range) -> Match {
        debug_assert!(range.alo <= range.ahi && range.ahi <= self.a.len());
        debug_assert!(range.blo <= range.bhi && range.bhi <= self.b.len());
        let mut best = Match {
            a: range.alo,
            b: range.blo,
            size: 0,
        };
        self.prev[range.blo..=range.bhi].fill(0);
        for i in range.alo..range.ahi {
            self.cur[range.blo..=range.bhi].fill(0);
            let element = self.a[i];
            if !self.popular.contains(&element) {
                for j in range.blo..range.bhi {
                    if self.b[j] != element {
                        continue;
                    }
                    let k = self.prev[j] + 1;
                    self.cur[j + 1] = k;
                    if k > best.size {
                        best = Match {
                            a: i + 1 - k,
                            b: j + 1 - k,
                            size: k,
                        };
                    }
                }
            }
            std::mem::swap(&mut self.prev, &mut self.cur);
        }
        self.longest_match_extend(range, best)
    }
    fn longest_match_extend(&self, range: Range, found: Match) -> Match {
        let (a, b) = (&self.a, &self.b);
        let mut best = found;
        debug_assert!(best.a + best.size <= range.ahi);
        debug_assert!(best.b + best.size <= range.bhi);
        while best.a > range.alo && best.b > range.blo && a[best.a - 1] == b[best.b - 1] {
            best = Match {
                a: best.a - 1,
                b: best.b - 1,
                size: best.size + 1,
            };
        }
        while best.a + best.size < range.ahi
            && best.b + best.size < range.bhi
            && a[best.a + best.size] == b[best.b + best.size]
        {
            best.size += 1;
        }
        best
    }
}
#[cfg(test)]
mod tests;
