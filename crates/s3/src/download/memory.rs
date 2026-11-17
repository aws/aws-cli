//! Bounded optional Linux memory diagnostics for writer instrumentation.
use std::io::{self, Read};
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct MemorySnapshot {
    pub rss_kib: u64,
    pub dirty_kib: u64,
    pub writeback_kib: u64,
}
impl MemorySnapshot {
    pub fn parse(statm: &str, meminfo: &str, page_size: usize) -> Self {
        Self {
            rss_kib: parse_statm(statm, page_size),
            dirty_kib: parse_meminfo(meminfo, "Dirty"),
            writeback_kib: parse_meminfo(meminfo, "Writeback"),
        }
    }
    pub fn read(page_size: usize) -> io::Result<Option<Self>> {
        if !cfg!(all(target_os = "linux", feature = "download-writer-debug")) {
            return Ok(None);
        }
        let statm = read_bounded("/proc/self/statm", 4096)?;
        let meminfo = read_bounded("/proc/meminfo", 64 * 1024)?;
        Ok(Some(Self::parse(&statm, &meminfo, page_size)))
    }
}
fn read_bounded(path: &str, maximum: usize) -> io::Result<String> {
    let mut contents = String::new();
    std::fs::File::open(path)?
        .take(maximum as u64 + 1)
        .read_to_string(&mut contents)?;
    if contents.len() > maximum {
        return Err(io::ErrorKind::InvalidData.into());
    }
    Ok(contents)
}
fn parse_statm(value: &str, page_size: usize) -> u64 {
    value
        .split_whitespace()
        .nth(1)
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(0)
        .saturating_mul(page_size as u64)
        / 1024
}
fn parse_meminfo(value: &str, key: &str) -> u64 {
    for line in value.lines() {
        let mut fields = line.split([':', ' ', '\t']).filter(|v| !v.is_empty());
        if fields.next() == Some(key) {
            return fields.next().and_then(|v| v.parse().ok()).unwrap_or(0);
        }
    }
    0
}
#[cfg(test)]
mod tests;
