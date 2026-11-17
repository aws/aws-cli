#![expect(clippy::unwrap_used, reason = "test fixtures and assertions")]
use super::*;
use crate::download::{
    lock,
    platform::AlignedBuffer,
    testing::fakes::{self, FakePlatform, Fault},
};
const BLOCK: DirectAlignment = DirectAlignment {
    memory: 512,
    offset: 512,
};
fn aligned(len: usize, alignment: usize, byte: u8) -> AlignedBuffer {
    let mut buffer = AlignedBuffer::new(len, alignment).unwrap();
    buffer.as_mut_slice().fill(byte);
    buffer
}
#[test]
fn direct_write_planning_covers_alignment_tail_and_invalid_ranges() {
    let source = aligned(1024, 512, 1);
    let bytes = source.as_slice();
    let exact = direct_plan(bytes, 512, 1536, BLOCK).unwrap();
    assert_eq!(
        (exact.length, exact.bounce, exact.padding),
        (1024, false, 0)
    );
    let bounced = direct_plan(&bytes[1..513], 0, 512, BLOCK).unwrap();
    assert_eq!(
        (bounced.length, bounced.bounce, bounced.padding),
        (512, true, 0)
    );
    let tail = direct_plan(&bytes[..513], 512, 1025, BLOCK).unwrap();
    assert_eq!((tail.length, tail.bounce, tail.padding), (1024, true, 511));
    assert_eq!(
        direct_plan(&bytes[..512], 1, 513, BLOCK),
        Err(WriteError::DirectOffsetUnaligned)
    );
    assert_eq!(
        direct_plan(&bytes[..513], 0, 1024, BLOCK),
        Err(WriteError::DirectNonFinalLengthUnaligned)
    );
    assert_eq!(
        direct_plan(&bytes[..1], u64::MAX, u64::MAX, BLOCK),
        Err(WriteError::OutOfBounds)
    );
    let invalid = DirectAlignment {
        memory: 3,
        offset: 512,
    };
    assert_eq!(
        direct_plan(bytes, 0, 1024, invalid),
        Err(WriteError::DirectInvalidAlignment)
    );
}
#[test]
fn alignment_validates_both_dimensions_before_bounce_compatibility() {
    for (memory, offset) in [
        (0, 512),
        (512, 0),
        (3, 512),
        (512, 3),
        (BOUNCE_ALIGNMENT * 2, 0),
    ] {
        assert_eq!(
            DirectAlignment { memory, offset }.validate(),
            Err(WriteError::DirectInvalidAlignment),
            "{memory} {offset}"
        );
    }
    assert_eq!(
        DirectAlignment {
            memory: BOUNCE_ALIGNMENT * 2,
            offset: 512
        }
        .validate(),
        Err(WriteError::DirectMemoryAlignmentUnsupported)
    );
    assert_eq!(
        DirectAlignment {
            memory: BOUNCE_ALIGNMENT,
            offset: 512
        }
        .validate(),
        Ok(())
    );
}
#[test]
fn direct_writer_bounces_and_zero_pads_only_the_eof_tail() {
    let platform = FakePlatform::default();
    let file = fakes::file();
    let stats = write_direct(&platform, &file, b"tail", 512, 516, BLOCK).unwrap();
    assert_eq!(*lock(&platform.write_sizes), [512]);
    assert_eq!(*lock(&platform.write_offsets), [512]);
    assert_eq!(&lock(&platform.disk)[512..516], b"tail");
    assert_eq!(lock(&platform.disk)[516..], [0; 508]);
    if cfg!(feature = "download-writer-debug") {
        assert_eq!((stats.bounce_bytes, stats.padded_bytes), (4, 508));
    }
    let platform = FakePlatform::default();
    let bytes: Vec<_> = (0..49).collect();
    let a = DirectAlignment {
        memory: 16,
        offset: 16,
    };
    write_direct(&platform, &file, &bytes[1..33], 0, 49, a).unwrap();
    write_direct(&platform, &file, &bytes[33..], 32, 48, a).unwrap();
    assert_eq!(&lock(&platform.disk)[..], &bytes[1..]);
    write_direct(&platform, &file, &[9], 48, 49, a).unwrap();
    assert_eq!(
        &lock(&platform.disk)[48..],
        &[9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    );
}
#[test]
fn direct_positional_writer_preserves_aligned_retries_and_rejects_unusable_shorts() {
    let platform = FakePlatform::default();
    let file = fakes::file();
    let source = aligned(1024, 512, b'x');
    lock(&platform.faults).extend([Fault::Interrupted, Fault::Short(512)]);
    let stats = write_all(&platform, &file, source.as_slice(), 0, Some(BLOCK)).unwrap();
    assert_eq!(*lock(&platform.disk), [b'x'; 1024]);
    assert_eq!(*lock(&platform.write_offsets), [0, 0, 512]);
    if cfg!(feature = "download-writer-debug") {
        assert_eq!(
            (stats.interrupted, stats.short_writes, stats.calls),
            (1, 1, 3)
        );
    }
    lock(&platform.faults).push_back(Fault::Short(256));
    assert_eq!(
        write_all(&platform, &file, source.as_slice(), 0, Some(BLOCK)),
        Err(WriteError::DirectShortWriteUnaligned)
    );
}
#[test]
fn positional_writer_retries_interruptions_and_short_writes_and_preserves_failures() {
    let platform = FakePlatform::default();
    let file = fakes::file();
    lock(&platform.faults).extend([Fault::Interrupted, Fault::Short(2), Fault::Interrupted]);
    write_all(&platform, &file, &[1, 2, 3, 4], 0, None).unwrap();
    assert_eq!(*lock(&platform.disk), vec![1, 2, 3, 4]);
    for (fault, expected) in [
        (Fault::Zero, WriteError::WriteZero),
        (Fault::Rejected, WriteError::WriteRejected),
    ] {
        lock(&platform.faults).push_back(fault);
        assert_eq!(write_all(&platform, &file, &[1], 0, None), Err(expected));
    }
    lock(&platform.faults).push_back(Fault::Failed);
    assert!(matches!(
        write_all(&platform, &file, &[1], 0, None),
        Err(WriteError::Io {
            kind: std::io::ErrorKind::StorageFull,
            ..
        })
    ));
}

#[test]
fn large_misaligned_body_reuses_one_bounded_bounce_and_zeroes_only_its_tail() {
    let platform = FakePlatform::default();
    let file = fakes::file();
    let size = 2 * BOUNCE_BYTES_MAX + 3;
    let mut source = AlignedBuffer::new(size + 1, 512).unwrap();
    source
        .as_mut_slice()
        .iter_mut()
        .enumerate()
        .for_each(|(index, byte)| *byte = (index.wrapping_mul(7) + 1) as u8);
    let body = &source.as_slice()[1..];
    let stats = write_direct(&platform, &file, body, 0, size as u64, BLOCK).unwrap();
    assert_eq!(&*lock(&platform.bounce_sizes), &[BOUNCE_BYTES_MAX]);
    assert_eq!(
        &*lock(&platform.write_sizes),
        &[BOUNCE_BYTES_MAX, BOUNCE_BYTES_MAX, 512]
    );
    assert_eq!(
        *lock(&platform.write_offsets),
        [0, BOUNCE_BYTES_MAX as u64, 2 * BOUNCE_BYTES_MAX as u64]
    );
    let disk = lock(&platform.disk);
    assert_eq!(&disk[..size], body);
    assert_eq!(&disk[size..], &[0; 509]);
    if cfg!(feature = "download-writer-debug") {
        assert_eq!(stats.bounce_bytes, size as u64);
        assert_eq!(stats.padded_bytes, 509);
        assert_eq!(stats.calls, 3);
    }
}

#[test]
fn a_write_past_off_t_is_too_big_for_the_file() {
    let platform = FakePlatform::default();
    let file = fakes::file();
    for offset in [i64::MAX as u64 + 1, u64::MAX - 1] {
        assert_eq!(
            write_all(&platform, &file, &[1; 4], offset, None),
            Err(WriteError::FileTooBig),
            "{offset}"
        );
    }
    let offset = 1 << 63;
    assert_eq!(
        write_direct(&platform, &file, b"tail", offset, offset + 4, BLOCK),
        Err(WriteError::FileTooBig)
    );
    assert!(lock(&platform.write_sizes).is_empty());
}
