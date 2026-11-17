use super::*;

const TEST_CANARY: u8 = 0xaa;
const TEST_CACHE_LINE_LEN: usize = 64;

struct Aligned {
    bytes: Vec<u8>,
    start: usize,
    len: usize,
}
impl Aligned {
    fn new(len: usize) -> Self {
        let bytes = vec![0; len + TEST_CACHE_LINE_LEN];
        let start = bytes.as_ptr().addr().wrapping_neg() & (TEST_CACHE_LINE_LEN - 1);
        Self { bytes, start, len }
    }
    fn get(&self) -> &[u8] {
        &self.bytes[self.start..][..self.len]
    }
    fn get_mut(&mut self) -> &mut [u8] {
        &mut self.bytes[self.start..][..self.len]
    }
}
fn fill_pattern(bytes: &mut [u8], seed: u8) {
    for (index, byte) in bytes.iter_mut().enumerate() {
        *byte = seed.wrapping_add(index.wrapping_mul(31) as u8);
    }
}
fn expect_copy_matches_source(
    mode: CopyMode,
    buffer: &mut [u8],
    source: &[u8],
    offset: usize,
    len: usize,
) {
    buffer.fill(TEST_CANARY);
    fast_copy(mode, &mut buffer[offset..][..len], &source[..len]);
    assert!(buffer[..offset].iter().all(|&byte| byte == TEST_CANARY));
    assert_eq!(&buffer[offset..][..len], &source[..len]);
    assert!(
        buffer[offset + len..]
            .iter()
            .all(|&byte| byte == TEST_CANARY)
    );
}
#[test]
fn nt_and_rep_movsb_copies_match_the_source_across_alignments_and_lengths() {
    let lengths = [
        0,
        1,
        15,
        16,
        17,
        63,
        64,
        65,
        127,
        128,
        4095,
        4096,
        4097,
        65536 + 17,
    ];
    let max_len = 65536 + 17;
    let margin = 2 * TEST_CACHE_LINE_LEN;
    let mut destination = Aligned::new(max_len + 2 * margin);
    let mut source = Aligned::new(max_len + margin);
    fill_pattern(source.get_mut(), 0x5c);
    assert_eq!(
        destination.get()[margin..].as_ptr().addr() % TEST_CACHE_LINE_LEN,
        0
    );
    for mode in [CopyMode::Nt, CopyMode::RepMovsb] {
        for len in lengths {
            if cfg!(miri) && len > 4097 {
                continue;
            }
            for offset in [0, 1, 8, 33, 63] {
                for source_offset in [0, 3, 32] {
                    expect_copy_matches_source(
                        mode,
                        &mut destination.get_mut()[..margin + len + margin],
                        &source.get()[source_offset..],
                        margin + offset,
                        len,
                    );
                }
            }
        }
    }
}
#[test]
fn copy_dispatches_every_mode_and_reports_the_path_taken() {
    let big_len = FAST_MODE_MIN_LEN + 65;
    let mut destination = Aligned::new(big_len);
    let mut source = Aligned::new(big_len);
    fill_pattern(source.get_mut(), 0xd1);
    let fast_path = if FAST_MODES_AVAILABLE {
        CopyPath::Requested
    } else {
        CopyPath::MemcpyFallback
    };
    for (mode, len, path) in [
        (CopyMode::Memcpy, big_len, CopyPath::Requested),
        (CopyMode::Memcpy, 100, CopyPath::Requested),
        (CopyMode::Nt, big_len, fast_path),
        (
            CopyMode::Nt,
            FAST_MODE_MIN_LEN - 1,
            CopyPath::MemcpyFallback,
        ),
        (CopyMode::Nt, 100, CopyPath::MemcpyFallback),
        (CopyMode::RepMovsb, big_len, fast_path),
        (
            CopyMode::RepMovsb,
            FAST_MODE_MIN_LEN - 1,
            CopyPath::MemcpyFallback,
        ),
        (CopyMode::RepMovsb, 100, CopyPath::MemcpyFallback),
    ] {
        destination.get_mut().fill(0);
        let copied = copy(
            mode,
            &mut destination.get_mut()[..len],
            &source.get()[..len],
        );
        assert_eq!(copied, path, "{mode:?} {len}");
        assert_eq!(&destination.get()[..len], &source.get()[..len]);
    }
}
