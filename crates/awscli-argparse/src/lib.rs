//! AWS CLI compatible argument parsing and deferred parameter conversion.
#![deny(unsafe_code)]
pub mod argument;
pub mod bind;
pub mod chain;
pub mod close_matches;
pub mod failure;
pub mod json;
pub mod namespace;
pub mod parser;
pub mod pattern;
pub mod pyrepr;
pub mod shorthand;
pub mod tables;
pub mod token;
#[doc(hidden)]
pub mod tool;
pub mod unpack;
#[doc(inline)]
pub use argument::{Action, Argument, CliType, DefaultValue, Nargs};
#[doc(inline)]
pub use chain::{Options, ParseResult, complete, parse, parse_os};
#[doc(inline)]
pub use namespace::{Namespace, Value};
#[doc(inline)]
pub use parser::Parser;
/// Linux ARG_MAX: the byte budget shared by argv and the environment.
const ARG_BYTES_MAX: usize = 2 * 1024 * 1024;
const ARG_BYTES_MIN: usize = 2;
/// Linux MAX_ARG_STRLEN: one argument spans at most 32 pages of 4 KiB.
const ARG_PAGE_COUNT_MAX: usize = 32;
const PAGE_BYTES: usize = 4096;
const OPERATION_ARGUMENT_COUNT_MAX: usize = 67;
const CUSTOM_ARGUMENT_COUNT_MAX: usize = 43;
/// The argv byte budget divided by the cheapest argument's cost.
pub const ARG_COUNT_MAX: usize = ARG_BYTES_MAX / ARG_BYTES_MIN;
/// The longest argument the host can pass.
pub const ARG_LEN_MAX: usize = ARG_PAGE_COUNT_MAX * PAGE_BYTES;
pub const ARGUMENT_COUNT_MAX: usize = 512;
pub const POSITIONAL_COUNT_MAX: usize = 4;
pub const VALUE_DEPTH_MAX: usize = 2;
pub const LINEAGE_DEPTH_MAX: usize = 4;
/// The longest text the shorthand grammar and the JSON decoder see: the
/// contents of a parameter file, which the unpack loop bounds at eight
/// maximum-size arguments. Longer input is refused before parsing.
pub const SHORTHAND_INPUT_BYTES_MAX: usize = 8 * ARG_LEN_MAX;
/// difflib.get_close_matches's `n` as CLIArgParser._check_value calls it:
/// at most three suggestions.
pub const SUGGESTION_COUNT_MAX: usize = 3;
/// Nested `[` and `{` levels a shorthand value or JSON document may open.
/// A map of strings needs one level and every deeper value fails its
/// schema; 32 keeps the recursive grammar's stack small and leaves deeper
/// input to Python, whose parsers recurse to their own limits.
pub const NESTED_VALUE_DEPTH_MAX: usize = 32;
const _: () = {
    assert!(ARG_BYTES_MAX.is_multiple_of(ARG_BYTES_MIN));
    assert!(ARG_COUNT_MAX == 1 << 20);
    assert!(ARG_LEN_MAX == 128 * 1024);
    assert!(ARG_LEN_MAX < ARG_BYTES_MAX);
    assert!(ARGUMENT_COUNT_MAX > 7 * OPERATION_ARGUMENT_COUNT_MAX);
    assert!(ARGUMENT_COUNT_MAX > CUSTOM_ARGUMENT_COUNT_MAX);
    assert!(ARGUMENT_COUNT_MAX < ARG_COUNT_MAX);
    assert!(POSITIONAL_COUNT_MAX < ARGUMENT_COUNT_MAX);
    assert!(SHORTHAND_INPUT_BYTES_MAX == 1024 * 1024);
    assert!(NESTED_VALUE_DEPTH_MAX > VALUE_DEPTH_MAX);
};
