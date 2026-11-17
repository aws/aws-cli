//! Bounded greedy matching of argparse's argument, option, and separator patterns.
use crate::{Argument, Nargs, POSITIONAL_COUNT_MAX};
/// Token classification before positional matching.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Argument,
    Option,
    Separator,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Bounds {
    min: usize,
    max: usize,
}
/// Longest prefix accepted by an argument's nargs pattern.
pub fn match_argument(arg: Argument, kinds: &[Kind]) -> Option<usize> {
    get_bounds(arg, kinds).map(|span| span.max)
}
/// Greedy positional matching with trailing empty-match deferral.
/// Counts are token spans, including any separator consumed by a positional.
pub fn match_arguments_partial(arguments: &[Argument], kinds: &[Kind]) -> Vec<usize> {
    assert!(arguments.len() <= POSITIONAL_COUNT_MAX);
    for len in (1..=arguments.len()).rev() {
        let mut counts = vec![0; len];
        if match_arguments_partial_group(&arguments[..len], kinds, &mut counts, 0) {
            let total: usize = counts.iter().sum();
            if kinds.get(total) == Some(&Kind::Option) {
                while counts.last() == Some(&0) {
                    counts.pop();
                }
            }
            return counts;
        }
    }
    Vec::new()
}
fn get_bounds(arg: Argument, kinds: &[Kind]) -> Option<Bounds> {
    let limits = get_bounds_limits(arg, kinds.len());
    let (mut count, mut end) = (0, 0);
    let mut shortest = if limits.min == 0 { Some(0) } else { None };
    for kind in kinds {
        if *kind == Kind::Separator && arg.positional {
            end += 1;
        } else {
            if count == limits.max || !get_bounds_accepts(arg, *kind) {
                break;
            }
            count += 1;
            end += 1;
        }
        if shortest.is_none() && count >= limits.min {
            shortest = Some(end);
        }
    }
    if count < limits.min {
        return None;
    }
    assert!(shortest.is_some());
    shortest.map(|min| Bounds { min, max: end })
}
fn get_bounds_limits(arg: Argument, token_count: usize) -> Bounds {
    let (min, max) = match arg.arity() {
        None => (1, 1),
        Some(Nargs::Optional) => (0, 1),
        Some(Nargs::ZeroOrMore) => (0, token_count),
        Some(Nargs::OneOrMore) => (1, token_count),
        Some(Nargs::Count(n)) => (usize::from(n), usize::from(n)),
    };
    Bounds { min, max }
}
fn get_bounds_accepts(arg: Argument, kind: Kind) -> bool {
    match kind {
        Kind::Argument => true,
        Kind::Option => matches!(arg.arity(), Some(Nargs::Count(_))) && !arg.positional,
        Kind::Separator => false,
    }
}
fn match_arguments_partial_group(
    arguments: &[Argument],
    kinds: &[Kind],
    counts: &mut [usize],
    depth: usize,
) -> bool {
    assert!(depth <= POSITIONAL_COUNT_MAX);
    let Some((first, rest)) = arguments.split_first() else {
        return true;
    };
    let Some(span) = get_bounds(*first, kinds) else {
        return false;
    };
    for len in (span.min..=span.max).rev() {
        if match_argument(*first, &kinds[..len]).is_none() {
            continue;
        }
        counts[0] = len;
        if match_arguments_partial_group(rest, &kinds[len..], &mut counts[1..], depth + 1) {
            return true;
        }
    }
    false
}
#[cfg(test)]
mod tests;
