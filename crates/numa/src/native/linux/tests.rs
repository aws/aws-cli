#![expect(
    clippy::unwrap_used,
    reason = "test assertions require successful fixture setup"
)]
use super::*;
use crate::WORD_BITS;
use std::path::PathBuf;

struct Directory(PathBuf);
impl Directory {
    fn new() -> Self {
        static SEQUENCE: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        let sequence = SEQUENCE.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let path =
            std::env::temp_dir().join(format!("numa-linux-{}-{sequence}", std::process::id()));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn file(&self, name: &str, contents: &[u8]) -> String {
        let path = self.0.join(name);
        std::fs::write(&path, contents).unwrap();
        path.to_str().unwrap().to_owned()
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
#[test]
fn syscall_nodemasks_cover_node_boundaries() {
    let words = MAX_NODES / WORD_BITS;
    for (node, word, bit) in [
        (0, 0, 0),
        (WORD_BITS - 1, 0, WORD_BITS - 1),
        (WORD_BITS, 1, 0),
        (MAX_NODES - 1, words - 1, WORD_BITS - 1),
    ] {
        let mask = node_mask(node as u32).unwrap();
        for (index, value) in mask.words.iter().enumerate() {
            let expected = if index == word { 1 << bit } else { 0 };
            assert_eq!(*value, expected, "node {node} word {index}");
        }
    }
    assert_eq!(MAXNODE, words * WORD_BITS + 1);
    assert!(matches!(
        node_mask(MAX_NODES as u32),
        Err(NumaError::NodeOutsideMask)
    ));
}
#[test]
fn topology_reads_keep_raw_bytes_up_to_the_limit() {
    let directory = Directory::new();
    let status = directory.file("status", b"Name:\taws-native-caf\xC3\n");
    assert_eq!(
        read_virtual(&status, 64).unwrap(),
        b"Name:\taws-native-caf\xC3\n"
    );
    let exact = directory.file("exact", &[b'0'; 8]);
    assert_eq!(read_virtual(&exact, 8).unwrap().len(), 8);
    assert!(matches!(
        read_virtual(&exact, 7),
        Err(NumaError::StreamTooLong)
    ));
}
#[test]
fn affinity_query_reports_a_mask_narrower_than_the_kernels_as_an_error() {
    // SAFETY: zero initialization is valid for cpu_set_t's integer storage.
    let mut raw: libc::cpu_set_t = unsafe { std::mem::zeroed() };
    assert!(matches!(
        read_affinity(&mut raw, 0),
        Err(NumaError::CpuOutsideAffinityMask)
    ));
    assert!(!current_affinity().unwrap().is_empty());
}
fn failed_call(result: Result<Vec<u8>, NumaError>) -> Option<(NumaCall, i32)> {
    match result {
        Err(NumaError::Os { call, error }) => Some((call, error.raw_os_error()?)),
        _ => None,
    }
}
#[test]
fn topology_read_failures_name_the_failing_call() {
    let directory = Directory::new();
    let root = directory.0.to_str().unwrap().to_owned();
    assert_eq!(
        failed_call(read_virtual(&format!("{root}/missing"), 8)),
        Some((NumaCall::Open, libc::ENOENT))
    );
    let file = directory.file("file", b"");
    assert_eq!(
        failed_call(read_virtual(&format!("{file}/x"), 8)),
        Some((NumaCall::Open, libc::ENOTDIR))
    );
    assert_eq!(
        failed_call(read_virtual(&root, 8)),
        Some((NumaCall::Read, libc::EISDIR))
    );
}
