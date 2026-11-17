use super::*;
const FRAME: &[u8] = &[
    40, 181, 47, 253, 32, 9, 73, 0, 0, 104, 101, 108, 108, 111, 32, 114, 115, 116,
];
#[test]
fn decodes_frame_from_python_314_compression_zstd() -> Result<(), Error> {
    let mut out = [0; 9];
    let mut scratch = vec![MaybeUninit::uninit(); ZSTD_BUFFER_LEN];
    decode_zstd(FRAME, &mut out, &mut scratch)?;
    assert_eq!(&out, b"hello rst");
    Ok(())
}
#[test]
fn rejects_unexpected_extra_output() {
    assert_eq!(
        decode_zstd(
            FRAME,
            &mut [0; 5],
            &mut vec![MaybeUninit::uninit(); ZSTD_BUFFER_LEN]
        ),
        Err(Error::OutputLengthMismatch)
    );
}
#[test]
fn rejects_invalid_and_truncated_zstd_frames() {
    let mut scratch = vec![MaybeUninit::uninit(); ZSTD_BUFFER_LEN];
    for input in [&[0, 1, 2, 3, 4, 5][..], &FRAME[..FRAME.len() - 1]] {
        assert_eq!(
            decode_zstd(input, &mut [0; 9], &mut scratch),
            Err(Error::DecodeFailed)
        );
    }
}
#[test]
fn rejects_insufficient_scratch_and_oversized_output() {
    let mut scratch = vec![MaybeUninit::uninit(); ZSTD_BUFFER_LEN];
    assert_eq!(
        decode_zstd(FRAME, &mut [0; 9], &mut scratch[..ZSTD_BUFFER_LEN - 1]),
        Err(Error::DecodeFailed)
    );
    assert_eq!(
        decode_zstd(FRAME, &mut [0; 10], &mut scratch),
        Err(Error::DecodeFailed)
    );
}
#[test]
fn decodes_an_empty_zstd_frame() -> Result<(), Error> {
    decode_zstd(
        &[40, 181, 47, 253, 32, 0, 1, 0, 0],
        &mut [],
        &mut vec![MaybeUninit::uninit(); ZSTD_BUFFER_LEN],
    )
}

#[test]
fn decodes_concatenated_frames_and_checks_total_output() -> Result<(), Error> {
    let frames = [FRAME, FRAME].concat();
    let mut out = [0; 18];
    decode(&frames, &mut out)?;
    assert_eq!(&out, b"hello rsthello rst");
    assert_eq!(
        decode(&frames, &mut [0; 9]),
        Err(Error::OutputLengthMismatch)
    );
    assert_eq!(decode(&frames, &mut [0; 19]), Err(Error::DecodeFailed));
    Ok(())
}

#[test]
fn validates_trailing_frames_even_after_excess_output() {
    for tail in [&[1][..], &FRAME[..FRAME.len() - 1]] {
        let frames = [FRAME, tail].concat();
        assert_eq!(decode(&frames, &mut [0; 9]), Err(Error::DecodeFailed));
        assert_eq!(decode(&frames, &mut [0; 5]), Err(Error::DecodeFailed));
    }
}

#[test]
fn accepts_skippable_frames_and_empty_input() -> Result<(), Error> {
    let skip = &[0x50, 0x2a, 0x4d, 0x18, 3, 0, 0, 0, 1, 2, 3];
    let frames = [&skip[..], FRAME, &skip[..], FRAME, &skip[..]].concat();
    let mut out = [0; 18];
    decode(&frames, &mut out)?;
    assert_eq!(&out, b"hello rsthello rst");
    decode(skip, &mut [])?;
    decode(&[], &mut [])?;
    assert_eq!(decode(&skip[..10], &mut []), Err(Error::DecodeFailed));
    assert_eq!(decode(&[], &mut [0]), Err(Error::DecodeFailed));
    Ok(())
}

#[test]
fn rejects_a_frame_window_above_the_baseline_eight_mib_limit() {
    let frame = [0x28, 0xb5, 0x2f, 0xfd, 0, 14 << 3, 1, 0, 0];
    assert_eq!(decode(&frame, &mut []), Err(Error::DecodeFailed));
}

const MAGIC: [u8; 4] = [0x28, 0xb5, 0x2f, 0xfd];
const HELLO: &[u8] = b"hello rst";

fn frame(header: &[u8], kind: u32, size: u32, body: &[u8]) -> Vec<u8> {
    let block = (size << 3) | (kind << 1) | 1;
    [&MAGIC[..], header, &block.to_le_bytes()[..3], body].concat()
}

#[test]
fn rejects_a_frame_content_size_the_blocks_do_not_produce() -> Result<(), Error> {
    assert_eq!(
        decode(&frame(&[0x20, 10], 0, 9, HELLO), &mut [0; 9]),
        Err(Error::DecodeFailed)
    );
    assert_eq!(
        decode(&frame(&[0x20, 8], 0, 9, HELLO), &mut [0; 9]),
        Err(Error::DecodeFailed)
    );
    let raw = [7; 300];
    decode(&frame(&[0x60, 44, 0], 0, 300, &raw), &mut [0; 300])?;
    assert_eq!(
        decode(&frame(&[0x60, 45, 0], 0, 300, &raw), &mut [0; 300]),
        Err(Error::DecodeFailed)
    );
    let mut out = [0; 9];
    decode(&frame(&[0, 0], 0, 9, HELLO), &mut out)?;
    assert_eq!(&out, HELLO);
    Ok(())
}

#[test]
fn rejects_a_reserved_descriptor_bit_and_any_dictionary_id() {
    for header in [
        &[0x28, 9][..],
        &[0x21, 0, 9],
        &[0x22, 0, 0, 9],
        &[0x23, 0, 0, 0, 0, 9],
    ] {
        assert_eq!(
            decode(&frame(header, 0, 9, HELLO), &mut [0; 9]),
            Err(Error::DecodeFailed),
            "{header:?}"
        );
    }
}

#[test]
fn rejects_a_block_larger_than_a_small_window() -> Result<(), Error> {
    let raw = [7; 1025];
    decode(&frame(&[0, 0], 0, 1024, &raw[..1024]), &mut [0; 1024])?;
    decode(&frame(&[0, 0], 1, 1024, &[7]), &mut [0; 1024])?;
    for oversize in [frame(&[0, 0], 0, 1025, &raw), frame(&[0, 0], 1, 1025, &[7])] {
        assert_eq!(decode(&oversize, &mut [0; 1025]), Err(Error::DecodeFailed));
    }
    Ok(())
}

#[test]
fn rejects_the_reserved_block_type() {
    assert_eq!(
        decode(&frame(&[0x20, 9], 3, 9, HELLO), &mut [0; 9]),
        Err(Error::DecodeFailed)
    );
}

#[test]
fn steps_over_a_content_checksum_to_the_next_frame() -> Result<(), Error> {
    let checked = frame(&[0x24, 9], 0, 9, &[HELLO, &[1, 2, 3, 4]].concat());
    let mut out = [0; 18];
    decode(&[&checked[..], FRAME].concat(), &mut out)?;
    assert_eq!(&out, b"hello rsthello rst");
    assert_eq!(
        decode(&checked[..checked.len() - 1], &mut [0; 9]),
        Err(Error::DecodeFailed)
    );
    Ok(())
}
