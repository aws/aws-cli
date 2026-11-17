//! Ordered value conversion for the native S3 settings table.
use super::{CopyMode, NumaMode, NumaPoolMode, ParseError, PrefaultMode, Settings, WriterMode};
use awscli_config::Nested;

/// A value outside its key's grammar. The per-key `settings_*` wrappers
/// name the key, so one value parser serves every key that shares it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InvalidValue;

/// Every key in parse order: the first invalid value wins, ahead of any
/// relationship between keys.
pub(super) fn download_settings(values: &Nested) -> Result<Settings, ParseError> {
    let in_flight = in_flight_settings(values)?;
    let value = |key| values.get(key).map(String::as_str);
    Ok(Settings {
        io_workers: value("io_workers").map(settings_io_workers).transpose()?,
        download_writer: value("download_writer")
            .map(settings_download_writer)
            .transpose()?,
        download_writer_copy: value("download_writer_copy")
            .map(download_writer_copy)
            .transpose()?,
        download_writer_prefault: value("download_writer_prefault")
            .map(settings_download_writer_prefault)
            .transpose()?,
        download_writer_numa: value("download_writer_numa")
            .map(settings_download_writer_numa)
            .transpose()?,
        download_writer_node: value("download_writer_node")
            .map(settings_download_writer_node)
            .transpose()?,
        download_numa_pool: value("download_numa_pool")
            .map(settings_download_numa_pool)
            .transpose()?,
        ..in_flight
    })
}
/// Only `max_in_flight`, which every operation reads.
pub(super) fn in_flight_settings(values: &Nested) -> Result<Settings, ParseError> {
    Ok(Settings {
        in_flight_max: values
            .get("max_in_flight")
            .map(String::as_str)
            .map(settings_in_flight_max)
            .transpose()?,
        ..Settings::default()
    })
}
fn settings_in_flight_max(value: &str) -> Result<u32, ParseError> {
    positive(value).map_err(|InvalidValue| ParseError::InvalidMaxInFlight)
}
fn settings_io_workers(value: &str) -> Result<usize, ParseError> {
    positive(value).map_err(|InvalidValue| ParseError::InvalidIoWorkers)
}
fn settings_download_writer(value: &str) -> Result<WriterMode, ParseError> {
    writer(value).map_err(|InvalidValue| ParseError::InvalidDownloadWriter)
}
fn settings_download_writer_prefault(value: &str) -> Result<PrefaultMode, ParseError> {
    prefault(value).map_err(|InvalidValue| ParseError::InvalidDownloadWriterPrefault)
}
fn settings_download_writer_numa(value: &str) -> Result<NumaMode, ParseError> {
    numa(value).map_err(|InvalidValue| ParseError::InvalidDownloadWriterNuma)
}
fn settings_download_writer_node(value: &str) -> Result<Vec<u32>, ParseError> {
    parse_node_selection(value).map_err(|InvalidValue| ParseError::InvalidDownloadWriterNode)
}
fn settings_download_numa_pool(value: &str) -> Result<NumaPoolMode, ParseError> {
    numa_pool(value).map_err(|InvalidValue| ParseError::InvalidDownloadNumaPool)
}
fn positive<T: TryFrom<u64> + Default + PartialEq>(value: &str) -> Result<T, InvalidValue> {
    let result = parse_unsigned::<T>(value.trim_matches([' ', '\t'])).ok_or(InvalidValue)?;
    if result == T::default() {
        Err(InvalidValue)
    } else {
        Ok(result)
    }
}
/// A base-10 unsigned `T`: ASCII digits with interior underscores skipped,
/// no sign, and no leading or trailing underscore.
fn parse_unsigned<T: TryFrom<u64>>(text: &str) -> Option<T> {
    if text.is_empty() || text.starts_with('_') || text.ends_with('_') {
        return None;
    }
    let mut value = 0_u64;
    for byte in text.bytes() {
        if byte == b'_' {
            continue;
        }
        if !byte.is_ascii_digit() {
            return None;
        }
        value = value
            .checked_mul(10)
            .and_then(|value| value.checked_add(u64::from(byte - b'0')))?;
    }
    T::try_from(value).ok()
}

fn writer(value: &str) -> Result<WriterMode, InvalidValue> {
    match value {
        "pwrite" => Ok(WriterMode::Pwrite),
        "mmap" => Ok(WriterMode::Mmap),
        "direct" => Ok(WriterMode::Direct),
        "crt" => Ok(WriterMode::Crt),
        _ => Err(InvalidValue),
    }
}
fn download_writer_copy(value: &str) -> Result<CopyMode, ParseError> {
    match value {
        "memcpy" => Ok(CopyMode::Memcpy),
        "nt" => Ok(CopyMode::Nt),
        "rep" => Ok(CopyMode::RepMovsb),
        _ => Err(ParseError::InvalidDownloadWriterCopy),
    }
}
fn prefault(value: &str) -> Result<PrefaultMode, InvalidValue> {
    match value {
        "enabled" => Ok(PrefaultMode::Enabled),
        "disabled" => Ok(PrefaultMode::Disabled),
        _ => Err(InvalidValue),
    }
}
fn numa(value: &str) -> Result<NumaMode, InvalidValue> {
    match value {
        "disabled" => Ok(NumaMode::Disabled),
        "same-node" => Ok(NumaMode::SameNode),
        "all-nodes" => Ok(NumaMode::AllNodes),
        _ => Err(InvalidValue),
    }
}
fn numa_pool(value: &str) -> Result<NumaPoolMode, InvalidValue> {
    match value {
        "enabled" => Ok(NumaPoolMode::Enabled),
        "disabled" => Ok(NumaPoolMode::Disabled),
        _ => Err(InvalidValue),
    }
}
pub fn parse_node_selection(value: &str) -> Result<Vec<u32>, InvalidValue> {
    if value == "auto" {
        return Ok(Vec::new());
    }
    let mut nodes = Vec::new();
    for part in value.split(',') {
        let part = part.trim_matches([' ', '\t']);
        let (first, last) = part.split_once('-').unwrap_or((part, part));
        let first = node_id(first).ok_or(InvalidValue)?;
        let last = node_id(last).ok_or(InvalidValue)?;
        if last < first {
            return Err(InvalidValue);
        }
        for node in first..=last {
            if nodes.contains(&node) {
                return Err(InvalidValue);
            }
            nodes.push(node);
        }
    }
    Ok(nodes)
}
fn node_id(value: &str) -> Option<u32> {
    // Node IDs are bounded by the nodes a placement or source pool can hold.
    parse_unsigned::<u32>(value).filter(|v| (*v as usize) < crate::download::MAX_NODES)
}
