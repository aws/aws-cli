//! Upstream's `--include` and `--exclude` filter (customizations/s3/filters.py).
//!
//! `create_filter` joins each pattern to the source's root and to the
//! destination's with `os.path.join`, and the filter matches the path the
//! file generator names for each source against both joins with
//! `fnmatch.fnmatch`, in command-line order: the last pattern either join of
//! which matches includes or excludes the source, and a source no pattern
//! matches is included. Paths and patterns compare as Python's `str` holds
//! them, one code point at a time, and `fnmatch` first normalizes both as
//! `os.path.normcase` does, which only changes them on Windows.
//!
//! ```
//! use s3::filter::{Filter, FilterKind, Roots};
//!
//! // `cp s3://bucket/tree /out --recursive --exclude '*' --include '*.txt'`
//! let filters = [
//!     (FilterKind::Exclude, "*".to_owned()),
//!     (FilterKind::Include, "*.txt".to_owned()),
//! ];
//! let roots = Roots {
//!     source: b"bucket/tree",
//!     destination: b"/out",
//! };
//! // The file generator names each listed object after its bucket.
//! let filter = Filter::new(&filters, roots, b"bucket/");
//! assert!(filter.includes(b"tree/a.txt"));
//! assert!(!filter.includes(b"tree/a.bin"));
//! ```

use std::fmt;

#[cfg(any(not(windows), test))]
mod posix;
#[cfg(any(windows, test))]
mod windows;

/// One code point of a path or pattern as Python's `str` holds it: a
/// character, the surrogate escape `os.fsdecode` gives a POSIX byte that is
/// not UTF-8, or an unpaired surrogate a Windows name holds.
type Unit = u32;

const STAR: Unit = b'*' as Unit;
const QUESTION: Unit = b'?' as Unit;
const OPEN: Unit = b'[' as Unit;
const CLOSE: Unit = b']' as Unit;
const BANG: Unit = b'!' as Unit;
const HYPHEN: Unit = b'-' as Unit;

/// Whether the sources a pattern matches are transferred or left out.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FilterKind {
    Include,
    Exclude,
}

impl TryFrom<&str> for FilterKind {
    type Error = UnknownFilterOption;
    /// The kind of `option`, the full name argparse stores a filter under.
    fn try_from(option: &str) -> Result<Self, Self::Error> {
        match option {
            "--include" => Ok(Self::Include),
            "--exclude" => Ok(Self::Exclude),
            _ => Err(UnknownFilterOption),
        }
    }
}

/// An option name that is neither `--include` nor `--exclude`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct UnknownFilterOption;

impl fmt::Display for UnknownFilterOption {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("option is neither --include nor --exclude")
    }
}

impl std::error::Error for UnknownFilterOption {}

/// The roots `create_filter` joins every pattern to.
///
/// Each is an OS string's encoded bytes or an S3 path's.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Roots<'a> {
    pub source: &'a [u8],
    pub destination: &'a [u8],
}

/// The filters of one command, rooted at its source and destination.
///
/// With no filters, the default, every source is included.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub struct Filter {
    prefix: Vec<Unit>,
    rules: Vec<Rule>,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
struct Rule {
    kind: FilterKind,
    patterns: [Vec<Token>; 2],
}

impl Filter {
    /// Compiles `filters`, each kind and pattern in command-line order.
    ///
    /// Each pattern is joined to both of `roots`. A source is then named by
    /// `prefix`, an OS string's encoded bytes or an S3 path's, followed by
    /// the name its producer gives it.
    pub fn new(filters: &[(FilterKind, String)], roots: Roots<'_>, prefix: &[u8]) -> Self {
        let roots = [decode(roots.source), decode(roots.destination)];
        let rules = filters
            .iter()
            .map(|(kind, pattern)| {
                let pattern = decode(pattern.as_bytes());
                Rule {
                    kind: *kind,
                    patterns: roots
                        .each_ref()
                        .map(|root| compile(&normcase(join(root, &pattern)))),
                }
            })
            .collect();
        Self {
            prefix: decode(prefix),
            rules,
        }
    }
    /// Whether the source a producer names `name` is transferred.
    pub fn includes(&self, name: &[u8]) -> bool {
        if self.rules.is_empty() {
            return true;
        }
        let mut path = Vec::with_capacity(self.prefix.len() + name.len());
        path.extend_from_slice(&self.prefix);
        decode_into(name, &mut path);
        let path = normcase(path);
        self.rules
            .iter()
            .rev()
            .find(|rule| rule.patterns.iter().any(|pattern| matches(pattern, &path)))
            .is_none_or(|rule| rule.kind == FilterKind::Include)
    }
}

/// The code points of `bytes`, an OS string's encoded bytes or a key's, as
/// `os.fsdecode` gives them.
fn decode(bytes: &[u8]) -> Vec<Unit> {
    let mut units = Vec::with_capacity(bytes.len());
    decode_into(bytes, &mut units);
    units
}

fn decode_into(bytes: &[u8], units: &mut Vec<Unit>) {
    #[cfg(windows)]
    {
        windows::decode_into(bytes, units);
    }
    #[cfg(not(windows))]
    {
        posix::decode_into(bytes, units);
    }
}

/// `os.path.join(root, pattern)`.
fn join(root: &[Unit], pattern: &[Unit]) -> Vec<Unit> {
    #[cfg(windows)]
    {
        windows::join(root, pattern)
    }
    #[cfg(not(windows))]
    {
        posix::join(root, pattern)
    }
}

/// `os.path.normcase(path)`, which `fnmatch.fnmatch` applies to the path
/// and the pattern. On Windows its backslashes also stand in for the
/// separator `_match_pattern` swaps into the pattern for the source's side.
fn normcase(path: Vec<Unit>) -> Vec<Unit> {
    #[cfg(windows)]
    {
        windows::normcase(&path)
    }
    #[cfg(not(windows))]
    {
        path
    }
}

/// What `fnmatch.translate` makes of one code point or set of a pattern.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum Token {
    /// `*`: any run of code points, separators included.
    Star,
    /// `?`, or a negated set fnmatch emptied: any one code point.
    Any,
    Literal(Unit),
    Set {
        negated: bool,
        ranges: Vec<(Unit, Unit)>,
    },
    /// A set fnmatch emptied, which no code point matches.
    Never,
}

impl Token {
    fn matches(&self, unit: Unit) -> bool {
        match self {
            Self::Star | Self::Any => true,
            Self::Literal(literal) => *literal == unit,
            Self::Set { negated, ranges } => {
                ranges
                    .iter()
                    .any(|&(low, high)| (low..=high).contains(&unit))
                    != *negated
            }
            Self::Never => false,
        }
    }
}

/// `fnmatch._translate`: a `[` without a later `]` is itself, and a set
/// ends at the first `]` past a leading `!` and a leading `]`.
fn compile(pattern: &[Unit]) -> Vec<Token> {
    let mut tokens = Vec::new();
    let mut i = 0;
    while let Some(&unit) = pattern.get(i) {
        i += 1;
        match unit {
            STAR => {
                tokens.push(Token::Star);
                while pattern.get(i) == Some(&STAR) {
                    i += 1;
                }
            }
            QUESTION => tokens.push(Token::Any),
            OPEN => {
                let mut j = i;
                if pattern.get(j) == Some(&BANG) {
                    j += 1;
                }
                if pattern.get(j) == Some(&CLOSE) {
                    j += 1;
                }
                match pattern[j..].iter().position(|&unit| unit == CLOSE) {
                    Some(end) => {
                        tokens.push(set(&pattern[i..j + end]));
                        i = j + end + 1;
                    }
                    None => tokens.push(Token::Literal(OPEN)),
                }
            }
            unit => tokens.push(Token::Literal(unit)),
        }
    }
    tokens
}

/// The set fnmatch translates `stuff`, the code points between `[` and
/// `]`, to, as `re` compiles that translation. Where `stuff` holds a `-`,
/// fnmatch cuts it into chunks at each hyphen that can form a range, drops
/// each range whose ends are reversed, and joins the chunks with hyphens,
/// escaping every other hyphen and every backslash.
fn set(stuff: &[Unit]) -> Token {
    let atoms: Vec<(Unit, bool)> = if stuff.contains(&HYPHEN) {
        chunks(stuff)
            .iter()
            .enumerate()
            .flat_map(|(index, chunk)| {
                let joint = (index > 0).then_some((HYPHEN, true));
                joint
                    .into_iter()
                    .chain(chunk.iter().map(|&unit| (unit, false)))
            })
            .collect()
    } else {
        stuff.iter().map(|&unit| (unit, false)).collect()
    };
    let negated = atoms.first() == Some(&(BANG, false));
    match atoms.as_slice() {
        [] => return Token::Never,
        [(BANG, false)] => return Token::Any,
        _ => {}
    }
    // `re`'s class parser: a hyphen joining two code points makes a range,
    // and one at the end is itself.
    let mut ranges = Vec::new();
    let mut rest = &atoms[usize::from(negated)..];
    while let Some((&(low, _), tail)) = rest.split_first() {
        rest = match tail {
            [(_, true)] => {
                ranges.extend([(low, low), (HYPHEN, HYPHEN)]);
                &[]
            }
            // The translation dropped every reversed range, which `re`
            // would reject.
            [(_, true), (high, _), tail @ ..] => {
                ranges.push((low, *high));
                tail
            }
            _ => {
                ranges.push((low, low));
                tail
            }
        };
    }
    Token::Set { negated, ranges }
}

/// fnmatch's chunks of `stuff`: cut at each hyphen past the first code
/// point, after a leading `!`, with at least two code points between it
/// and the hyphen cut before it, and an empty last chunk's hyphen kept on
/// the one before; then from the end, each chunk whose first code point
/// sorts before the previous chunk's last is merged into that one, without
/// either.
fn chunks(stuff: &[Unit]) -> Vec<Vec<Unit>> {
    let mut chunks: Vec<Vec<Unit>> = Vec::new();
    let mut start = 0;
    let mut from = if stuff.first() == Some(&BANG) { 2 } else { 1 };
    while let Some(found) = stuff
        .get(from..)
        .and_then(|rest| rest.iter().position(|&unit| unit == HYPHEN))
    {
        let hyphen = from + found;
        chunks.push(stuff[start..hyphen].to_vec());
        start = hyphen + 1;
        from = hyphen + 3;
    }
    match (&stuff[start..], chunks.last_mut()) {
        ([], Some(last)) => last.push(HYPHEN),
        (chunk, _) => chunks.push(chunk.to_vec()),
    }
    for k in (1..chunks.len()).rev() {
        if chunks[k - 1].last() > chunks[k].first() {
            let next = chunks.remove(k);
            let previous = &mut chunks[k - 1];
            previous.pop();
            previous.extend_from_slice(next.get(1..).unwrap_or_default());
        }
    }
    chunks
}

/// Whether `path` matches all of `pattern`, as the anchored `re` pattern
/// fnmatch compiles does. Every token but `*` matches one code point, so a
/// failed match need only retry from the last `*`, which absorbs one more.
fn matches(pattern: &[Token], path: &[Unit]) -> bool {
    let (mut p, mut n) = (0, 0);
    let mut star = None;
    while let Some(&unit) = path.get(n) {
        match pattern.get(p) {
            Some(Token::Star) => {
                p += 1;
                star = Some((p, n));
                continue;
            }
            Some(token) if token.matches(unit) => {
                p += 1;
                n += 1;
                continue;
            }
            _ => {}
        }
        let Some((resume, absorbed)) = star else {
            return false;
        };
        star = Some((resume, absorbed + 1));
        p = resume;
        n = absorbed + 1;
    }
    pattern[p..].iter().all(|token| *token == Token::Star)
}

#[cfg(test)]
mod tests;
