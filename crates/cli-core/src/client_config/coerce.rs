//! Bounded versions of upstream's integer, size, and transfer-rate conversions,
//! and the order the S3 transfer configuration runs them in ([`transfer`]).
//! Each function accepts what the pinned AWS CLI accepts, with the value it
//! produces, and rejects every other value, so the caller can hand the
//! invocation to the Python fallback, which renders upstream's own message in
//! upstream's order. A rejection is always safe: it only costs the native
//! route. The conversions read ASCII only: text Python reads through Unicode
//! tables, any non-ASCII byte or the separators 0x1c-0x1f that `str.strip`
//! and `int()` treat as whitespace, is Python's. Citations name lines of
//! `aws-cli/awscli/customizations/s3/transferconfig.py` and
//! `aws-cli/awscli/customizations/s3/utils.py`, and of
//! `aws-cli/awscli/botocore/utils.py`.
use crate::cli_error::PythonReason;

/// Python's `int(text)` in base 10, bounded to the signed 64-bit range;
/// `None` for text `int()` rejects, including a literal over CPython's digit
/// limit (`awscli_argparse::unpack::PYTHON_INT_MAX_STR_DIGITS`), and for a
/// value only Python's unbounded integers carry.
pub fn integer(text: &str) -> Option<i64> {
    if text.len() > awscli_argparse::ARG_LEN_MAX
        || !text.is_ascii()
        || text.bytes().any(|c| (0x1c..=0x1f).contains(&c))
    {
        return None;
    }
    awscli_argparse::unpack::parse_int(text).ok()
}
/// `human_readable_to_int`: an integer count of bytes, optionally followed by
/// one of the binary suffixes of `SIZE_SUFFIX` in any case. The count before a
/// suffix goes through `int()` unguarded, so its failure is Python's raw
/// ValueError. Non-ASCII text is Python's: `str.lower` folds KELVIN SIGN
/// (U+212A) to `k`, the one non-ASCII character that can complete a suffix, and
/// `int()` reads Unicode digits and whitespace.
pub fn size(text: &str) -> Option<i64> {
    if !text.is_ascii() {
        return None;
    }
    for (suffix, shift) in [
        ("kib", 10),
        ("mib", 20),
        ("gib", 30),
        ("tib", 40),
        ("kb", 10),
        ("mb", 20),
        ("gb", 30),
        ("tb", 40),
    ] {
        if text.len() >= suffix.len()
            && text[text.len() - suffix.len()..].eq_ignore_ascii_case(suffix)
        {
            return integer(&text[..text.len() - suffix.len()])?.checked_mul(1 << shift);
        }
    }
    integer(text)
}
/// A rate in bytes per second (`_convert_human_readable_rates`): a size
/// followed by a case-sensitive `B/s`, a size of bits followed by `b/s`,
/// converted with `int(bits / 8)`, or a bare integer. The size before the unit
/// is `_human_readable_rate_to_int`'s: the text without its three-byte unit
/// when that is an integer, else the text without `/s` read as a size. True
/// division rounds the quotient of bits to the nearest double, which dividing
/// the nearest double by eight does exactly, and `int()` truncates it toward
/// zero.
#[expect(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    reason = "Python true division then int truncates the rounded double"
)]
pub fn rate(text: &str) -> Option<i64> {
    if !text.is_ascii() {
        return None;
    }
    let bits = text.ends_with("b/s");
    if bits || text.ends_with("B/s") {
        let unit_free = &text[..text.len() - 3];
        let count = if integer(unit_free).is_some() {
            size(unit_free)?
        } else {
            size(&text[..text.len() - 2])?
        };
        return Some(if bits {
            (count as f64 / 8.0) as i64
        } else {
            count
        });
    }
    integer(text)
}
/// The positive-integer check (`_validate_positive_integers`): the converted
/// value must be greater than zero; a value no conversion produced fails it
/// too.
pub fn positive(value: Option<i64>) -> Result<u64, PythonReason> {
    value
        .and_then(|v| u64::try_from(v).ok())
        .filter(|v| *v > 0)
        .ok_or(PythonReason::TransferSetting)
}
/// botocore's `ensure_boolean` for a string: true exactly when the lowercased
/// text is `true`. It never rejects a value. No non-ASCII character lowercases
/// into those four letters, so an ASCII comparison is exact.
pub fn boolean(text: &str) -> bool {
    text.eq_ignore_ascii_case("true")
}
/// The transfer clients `preferred_transfer_client` chooses between
/// (`RuntimeConfig.SUPPORTED_CHOICES`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum TransferClient {
    /// The default: the CRT where it is eligible.
    #[default]
    Auto,
    /// s3transfer's own client, which only the Python fallback implements.
    Classic,
    /// The CRT.
    Crt,
}
/// The choice alias (`CHOICE_ALIASES`): exactly `default` selects `classic`;
/// every other value passes through unchanged.
pub fn transfer_client_alias(text: &str) -> &str {
    if text == "default" { "classic" } else { text }
}
/// The choice check (`_validate_choices`): an exact, case-sensitive match
/// against the supported values, after the alias.
pub fn transfer_client(text: &str) -> Option<TransferClient> {
    match text {
        "auto" => Some(TransferClient::Auto),
        "classic" => Some(TransferClient::Classic),
        "crt" => Some(TransferClient::Crt),
        _ => None,
    }
}
/// A count as aws-c-s3 reads `AWS_CRT_S3_MEMORY_LIMIT_IN_MB` and
/// `AWS_CRT_S3_MEMORY_LIMIT_IN_GIB`: ASCII decimal digits only, with no sign
/// or whitespace, within 64 bits.
pub fn unsigned(text: &str) -> Option<u64> {
    if text.is_empty() || !text.bytes().all(|c| c.is_ascii_digit()) {
        return None;
    }
    text.parse().ok()
}
/// `target_throughput * 8 / 1_000_000_000` (s3transfer's
/// `_get_crt_throughput_target_gbps`), from bytes per second to the CRT's
/// gigabits per second.
#[expect(
    clippy::cast_precision_loss,
    reason = "matches s3transfer double throughput conversion"
)]
pub fn bytes_to_gbps(bytes: u64) -> f64 {
    (u128::from(bytes) * 8) as f64 / 1_000_000_000.0
}

/// The raw values of the selected profile's `s3` block as upstream's
/// `build_config` receives them; `None` where the block does not set the key.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct TransferInputs<'a> {
    /// Size above which uploads and downloads split into parts.
    pub multipart_threshold: Option<&'a str>,
    /// The part size.
    pub multipart_chunksize: Option<&'a str>,
    /// The classic client's concurrency, and the CRT connection cap.
    pub max_concurrent_requests: Option<&'a str>,
    /// The classic client's task queue bound.
    pub max_queue_size: Option<&'a str>,
    /// The classic client's bandwidth limit.
    pub max_bandwidth: Option<&'a str>,
    /// Which transfer client to prefer.
    pub preferred_transfer_client: Option<&'a str>,
    /// The CRT throughput target.
    pub target_bandwidth: Option<&'a str>,
    /// The classic client's read size.
    pub io_chunksize: Option<&'a str>,
    /// The CRT's streaming file I/O switch.
    pub should_stream: Option<&'a str>,
    /// The CRT's disk throughput hint.
    pub disk_throughput: Option<&'a str>,
    /// The CRT's direct I/O switch.
    pub direct_io: Option<&'a str>,
}
impl<'a> TransferInputs<'a> {
    /// The block whose key [`TRANSFER_KEYS`] names `lookup` answers, asked
    /// once per key in that order.
    pub fn read(mut lookup: impl FnMut(&'static str) -> Option<&'a str>) -> Self {
        Self {
            multipart_threshold: lookup("multipart_threshold"),
            multipart_chunksize: lookup("multipart_chunksize"),
            max_concurrent_requests: lookup("max_concurrent_requests"),
            max_queue_size: lookup("max_queue_size"),
            max_bandwidth: lookup("max_bandwidth"),
            preferred_transfer_client: lookup("preferred_transfer_client"),
            target_bandwidth: lookup("target_bandwidth"),
            io_chunksize: lookup("io_chunksize"),
            should_stream: lookup("should_stream"),
            disk_throughput: lookup("disk_throughput"),
            direct_io: lookup("direct_io"),
        }
    }
}
/// The coerced `s3` block; `None` where the block does not set the key,
/// since the defaults a key falls back to depend on the transfer client.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Transfer {
    /// Bytes.
    pub multipart_threshold: Option<u64>,
    /// Bytes.
    pub multipart_chunksize: Option<u64>,
    /// Requests.
    pub max_concurrent_requests: Option<u64>,
    /// Tasks.
    pub max_queue_size: Option<u64>,
    /// Bytes per second.
    pub max_bandwidth: Option<u64>,
    /// The chosen client after the alias; `auto` when unset.
    pub preferred_transfer_client: TransferClient,
    /// Bytes per second.
    pub target_bandwidth: Option<u64>,
    /// Bytes.
    pub io_chunksize: Option<u64>,
    /// botocore's boolean.
    pub should_stream: Option<bool>,
    /// Bytes per second.
    pub disk_throughput: Option<u64>,
    /// botocore's boolean.
    pub direct_io: Option<bool>,
}
/// Every `s3` block key the transfer configuration reads, in the order of
/// [`TransferInputs`]' fields.
pub const TRANSFER_KEYS: [&str; 11] = [
    "multipart_threshold",
    "multipart_chunksize",
    "max_concurrent_requests",
    "max_queue_size",
    "max_bandwidth",
    "preferred_transfer_client",
    "target_bandwidth",
    "io_chunksize",
    "should_stream",
    "disk_throughput",
    "direct_io",
];
/// `HUMAN_READABLE_SIZES`.
pub const SIZE_KEYS: [&str; 3] = ["multipart_chunksize", "multipart_threshold", "io_chunksize"];
/// `HUMAN_READABLE_RATES`.
pub const RATE_KEYS: [&str; 3] = ["max_bandwidth", "target_bandwidth", "disk_throughput"];
/// `BOOLEANS`.
pub const BOOLEAN_KEYS: [&str; 2] = ["should_stream", "direct_io"];
/// `POSITIVE_INTEGERS`, in the order they are checked.
pub const POSITIVE_KEYS: [&str; 8] = [
    "multipart_chunksize",
    "multipart_threshold",
    "max_concurrent_requests",
    "max_queue_size",
    "max_bandwidth",
    "target_bandwidth",
    "io_chunksize",
    "disk_throughput",
];
const CHOICE_KEY: &str = "preferred_transfer_client";
const _: () = {
    assert!(all_listed(&SIZE_KEYS, &POSITIVE_KEYS));
    assert!(all_listed(&RATE_KEYS, &POSITIVE_KEYS));
    assert!(distinct(&TRANSFER_KEYS) && distinct(&POSITIVE_KEYS) && distinct(&BOOLEAN_KEYS));
    assert!(all_listed(&POSITIVE_KEYS, &TRANSFER_KEYS));
    assert!(all_listed(&BOOLEAN_KEYS, &TRANSFER_KEYS));
    assert!(listed(CHOICE_KEY, &TRANSFER_KEYS));
    assert!(!listed(CHOICE_KEY, &POSITIVE_KEYS) && !listed(CHOICE_KEY, &BOOLEAN_KEYS));
    assert!(!any_listed(&BOOLEAN_KEYS, &POSITIVE_KEYS));
    assert!(TRANSFER_KEYS.len() == POSITIVE_KEYS.len() + BOOLEAN_KEYS.len() + 1);
};
const fn listed(key: &str, list: &[&str]) -> bool {
    let mut index = 0;
    while index < list.len() {
        let other = list[index].as_bytes();
        if key.len() == other.len() {
            let mut byte = 0;
            while byte < other.len() && key.as_bytes()[byte] == other[byte] {
                byte += 1;
            }
            if byte == other.len() {
                return true;
            }
        }
        index += 1;
    }
    false
}
const fn all_listed(keys: &[&str], list: &[&str]) -> bool {
    let mut index = 0;
    while index < keys.len() {
        if !listed(keys[index], list) {
            return false;
        }
        index += 1;
    }
    true
}
const fn any_listed(keys: &[&str], list: &[&str]) -> bool {
    let mut index = 0;
    while index < keys.len() {
        if listed(keys[index], list) {
            return true;
        }
        index += 1;
    }
    false
}
const fn distinct(keys: &[&str]) -> bool {
    let mut index = 0;
    while index < keys.len() {
        if let Some((_, later)) = keys.split_at_checked(index + 1)
            && listed(keys[index], later)
        {
            return false;
        }
        index += 1;
    }
    true
}

/// The stage of [`transfer`] that rejected the block. Upstream raises the
/// first failure in stage order, and only Python renders it, so every stage's
/// failure is [`PythonReason::TransferSetting`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stage {
    /// `human_readable_to_int` of a size key.
    Size,
    /// The rate conversion of a rate key (`_convert_human_readable_rates`).
    Rate,
    /// The positive-integer check (`_validate_positive_integers`).
    Positive,
    /// The choice check (`_validate_choices`).
    Choice,
}
impl From<Stage> for PythonReason {
    fn from(_: Stage) -> Self {
        Self::TransferSetting
    }
}
/// `RuntimeConfig.build_config`: sizes, rates, booleans, the choice alias, the
/// positive integers, then the choices. The first failure in that order is the
/// one upstream raises.
pub fn transfer(inputs: &TransferInputs<'_>) -> Result<Transfer, Stage> {
    let mut converted = Converted::default();
    transfer_sizes(inputs, &mut converted)?;
    transfer_rates(inputs, &mut converted)?;
    let mut result = Transfer {
        should_stream: inputs.should_stream.map(boolean),
        direct_io: inputs.direct_io.map(boolean),
        ..Transfer::default()
    };
    let client = transfer_client_alias(inputs.preferred_transfer_client.unwrap_or("auto"));
    transfer_positives(inputs, &converted, &mut result)?;
    result.preferred_transfer_client = transfer_client(client).ok_or(Stage::Choice)?;
    Ok(result)
}
#[derive(Debug, Default)]
struct Converted {
    multipart_chunksize: Option<i64>,
    multipart_threshold: Option<i64>,
    io_chunksize: Option<i64>,
    max_bandwidth: Option<i64>,
    target_bandwidth: Option<i64>,
    disk_throughput: Option<i64>,
}
fn transfer_sizes(inputs: &TransferInputs<'_>, converted: &mut Converted) -> Result<(), Stage> {
    let convert = |text: Option<&str>| text.map(|text| size(text).ok_or(Stage::Size)).transpose();
    converted.multipart_chunksize = convert(inputs.multipart_chunksize)?;
    converted.multipart_threshold = convert(inputs.multipart_threshold)?;
    converted.io_chunksize = convert(inputs.io_chunksize)?;
    Ok(())
}
fn transfer_rates(inputs: &TransferInputs<'_>, converted: &mut Converted) -> Result<(), Stage> {
    let convert = |text: Option<&str>| text.map(|text| rate(text).ok_or(Stage::Rate)).transpose();
    converted.max_bandwidth = convert(inputs.max_bandwidth)?;
    converted.target_bandwidth = convert(inputs.target_bandwidth)?;
    converted.disk_throughput = convert(inputs.disk_throughput)?;
    Ok(())
}
fn transfer_positives(
    inputs: &TransferInputs<'_>,
    converted: &Converted,
    result: &mut Transfer,
) -> Result<(), Stage> {
    let check = |value: Option<i64>| {
        value
            .map(|value| positive(Some(value)).map_err(|_| Stage::Positive))
            .transpose()
    };
    let count = |text: Option<&str>| {
        text.map(|text| positive(integer(text)).map_err(|_| Stage::Positive))
            .transpose()
    };
    result.multipart_chunksize = check(converted.multipart_chunksize)?;
    result.multipart_threshold = check(converted.multipart_threshold)?;
    result.max_concurrent_requests = count(inputs.max_concurrent_requests)?;
    result.max_queue_size = count(inputs.max_queue_size)?;
    result.max_bandwidth = check(converted.max_bandwidth)?;
    result.target_bandwidth = check(converted.target_bandwidth)?;
    result.io_chunksize = check(converted.io_chunksize)?;
    result.disk_throughput = check(converted.disk_throughput)?;
    Ok(())
}
