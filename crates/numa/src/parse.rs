use crate::{CpuSet, MAX_CPUS, MAX_NODES, NodeMask, NumaError};
fn range(text: &str) -> Result<std::ops::RangeInclusive<usize>, NumaError> {
    let text = text.trim_matches([' ', '\t', '\r', '\n']);
    if let Some((start, end)) = text.split_once('-') {
        let start = number(start)?;
        let end = number(end)?;
        if end < start {
            return Err(NumaError::InvalidList);
        }
        Ok(start..=end)
    } else {
        let value = number(text)?;
        Ok(value..=value)
    }
}
/// Parses a fixed-width affinity list, rejecting empty list components.
///
/// # Errors
/// Reports malformed text or out-of-range CPUs.
pub fn parse_cpu_list(text: &str) -> Result<CpuSet, NumaError> {
    let mut set = CpuSet::default();
    let text = text.trim_matches([' ', '\t', '\r', '\n']);
    if text.is_empty() {
        return Ok(set);
    }
    for part in text.split(',') {
        let values = range(part)?;
        if *values.end() >= MAX_CPUS {
            return Err(NumaError::CpuOutsideAffinityMask);
        }
        for cpu in values {
            set.set(cpu)?;
        }
    }
    Ok(set)
}
/// Parses allowed memory nodes within the explicit 1024-node mask.
///
/// # Errors
/// Reports empty or malformed node lists.
pub fn parse_node_mask(text: &str) -> Result<NodeMask, NumaError> {
    if text.is_empty() {
        return Err(NumaError::AllowedListUnavailable);
    }
    let mut mask = NodeMask::default();
    for part in text.split(',') {
        let values = range(part)?;
        if *values.end() >= MAX_NODES {
            return Err(NumaError::InvalidList);
        }
        for node in values {
            mask.set(node);
        }
    }
    Ok(mask)
}
/// Finds the process memory-node allowance without consulting global state.
///
/// # Errors
/// Reports unavailable or malformed node lists; a node list that is not
/// UTF-8 is malformed.
pub fn parse_allowed_node_mask(status: &[u8]) -> Result<NodeMask, NumaError> {
    let value = status
        .split(|&byte| byte == b'\n')
        .find_map(|line| line.strip_prefix(b"Mems_allowed_list:"))
        .ok_or(NumaError::AllowedListUnavailable)?;
    let value = std::str::from_utf8(value).map_err(|_| NumaError::InvalidList)?;
    parse_node_mask(value.trim_matches([' ', '\t', '\r', '\n']))
}

fn number(text: &str) -> Result<usize, NumaError> {
    if text.is_empty() || text.starts_with('_') || text.ends_with('_') {
        return Err(NumaError::InvalidList);
    }
    let mut value = 0_usize;
    for byte in text.bytes() {
        if byte == b'_' {
            continue;
        }
        if !byte.is_ascii_digit() {
            return Err(NumaError::InvalidList);
        }
        value = value
            .checked_mul(10)
            .and_then(|value| value.checked_add(usize::from(byte - b'0')))
            .ok_or(NumaError::InvalidList)?;
    }
    Ok(value)
}
