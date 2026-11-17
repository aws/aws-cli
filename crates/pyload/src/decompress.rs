//! Bounded, pure-Rust Zstandard decoding for payload resources.
#![forbid(unsafe_code)]
use std::io::Read;
use std::mem::MaybeUninit;

const WINDOW_LEN: usize = 8 * 1024 * 1024;
const BLOCK_SIZE_MAX: usize = 128 * 1024;
pub const ZSTD_BUFFER_LEN: usize = WINDOW_LEN + BLOCK_SIZE_MAX;

const FRAME_MAGIC: [u8; 4] = [0x28, 0xb5, 0x2f, 0xfd];
const BLOCK_HEADER_LEN: usize = 3;
const CHECKSUM_LEN: usize = 4;
const DICTIONARY_ID_FLAG: u8 = 0x03;
const CONTENT_CHECKSUM_FLAG: u8 = 0x04;
const RESERVED_BIT: u8 = 0x08;
const SINGLE_SEGMENT_FLAG: u8 = 0x20;
const RAW_BLOCK: u32 = 0;
const RLE_BLOCK: u32 = 1;
const COMPRESSED_BLOCK: u32 = 2;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    DecodeFailed,
    OutputLengthMismatch,
}
impl std::fmt::Display for Error {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{self:?}")
    }
}
impl std::error::Error for Error {}

/// Decode a resource into `out`: the caller supplies at least `ZSTD_BUFFER_LEN` bytes of scratch.
pub fn decode_zstd(
    stored: &[u8],
    out: &mut [u8],
    scratch: &mut [MaybeUninit<u8>],
) -> Result<(), Error> {
    if scratch.len() < ZSTD_BUFFER_LEN {
        return Err(Error::DecodeFailed);
    }
    decode(stored, out)
}

/// Decode all frames of a resource without requiring caller-owned scratch memory.
pub fn decode(mut stored: &[u8], out: &mut [u8]) -> Result<(), Error> {
    let mut excess = [0; 4096];
    let mut extra = false;
    let mut written = 0;
    while !stored.is_empty() {
        if let Some(rest) = skip_frame(stored)? {
            stored = rest;
            continue;
        }
        let header = frame_header(stored)?;
        let (frame, rest) = stored
            .split_at_checked(frame_len(stored, &header)?)
            .ok_or(Error::DecodeFailed)?;
        let mut decoder =
            ruzstd::decoding::StreamingDecoder::new_with_max_window_size(frame, WINDOW_LEN as u64)
                .map_err(|_| Error::DecodeFailed)?;
        let mut produced = 0_u64;
        loop {
            let remaining = &mut out[written..];
            let target = if remaining.is_empty() {
                &mut excess
            } else {
                remaining
            };
            let count = decoder.read(target).map_err(|_| Error::DecodeFailed)?;
            if count == 0 {
                break;
            }
            produced += count as u64;
            if written == out.len() {
                extra = true;
            } else {
                written += count;
            }
        }
        // ruzstd never compares the output with Frame_Content_Size.
        if header.content_size.is_some_and(|size| size != produced) {
            return Err(Error::DecodeFailed);
        }
        stored = rest;
    }
    if written != out.len() {
        return Err(Error::DecodeFailed);
    }
    if extra {
        return Err(Error::OutputLengthMismatch);
    }
    Ok(())
}

struct FrameHeader {
    len: usize,
    window_size: u64,
    content_size: Option<u64>,
    has_checksum: bool,
}

fn frame_header(stored: &[u8]) -> Result<FrameHeader, Error> {
    if stored.get(..FRAME_MAGIC.len()) != Some(&FRAME_MAGIC[..]) {
        return Err(Error::DecodeFailed);
    }
    let descriptor = *stored.get(4).ok_or(Error::DecodeFailed)?;
    if descriptor & (RESERVED_BIT | DICTIONARY_ID_FLAG) != 0 {
        return Err(Error::DecodeFailed);
    }
    let single_segment = descriptor & SINGLE_SEGMENT_FLAG != 0;
    let mut len = 5;
    let window_descriptor = if single_segment {
        None
    } else {
        len += 1;
        Some(*stored.get(len - 1).ok_or(Error::DecodeFailed)?)
    };
    let content_size_flag = descriptor >> 6;
    let content_size = if single_segment || content_size_flag > 0 {
        let field_len = 1 << content_size_flag;
        let field = stored
            .get(len..len + field_len)
            .ok_or(Error::DecodeFailed)?;
        len += field_len;
        let mut value = [0; 8];
        value[..field_len].copy_from_slice(field);
        let value = u64::from_le_bytes(value);
        Some(if field_len == 2 { value + 256 } else { value })
    } else {
        None
    };
    // A single-segment frame's window is its content size, which it always declares.
    let window_size = match window_descriptor {
        Some(byte) => window_from_descriptor(byte),
        None => content_size.ok_or(Error::DecodeFailed)?,
    };
    if window_size > WINDOW_LEN as u64 {
        return Err(Error::DecodeFailed);
    }
    Ok(FrameHeader {
        len,
        window_size,
        content_size,
        has_checksum: descriptor & CONTENT_CHECKSUM_FLAG != 0,
    })
}

fn window_from_descriptor(descriptor: u8) -> u64 {
    let base = 1_u64 << (10 + (descriptor >> 3));
    base + (base / 8) * u64::from(descriptor & 7)
}

fn frame_len(stored: &[u8], header: &FrameHeader) -> Result<usize, Error> {
    let block_size_max = header.window_size.min(BLOCK_SIZE_MAX as u64);
    let mut offset = header.len;
    loop {
        let block = stored
            .get(offset..offset + BLOCK_HEADER_LEN)
            .ok_or(Error::DecodeFailed)?;
        let block = u32::from_le_bytes([block[0], block[1], block[2], 0]);
        let size = block >> 3;
        if u64::from(size) > block_size_max {
            return Err(Error::DecodeFailed);
        }
        let body = match (block >> 1) & 3 {
            RAW_BLOCK | COMPRESSED_BLOCK => size as usize,
            RLE_BLOCK => 1,
            _ => return Err(Error::DecodeFailed),
        };
        offset += BLOCK_HEADER_LEN + body;
        if block & 1 != 0 {
            break;
        }
    }
    if header.has_checksum {
        offset += CHECKSUM_LEN;
    }
    if offset > stored.len() {
        return Err(Error::DecodeFailed);
    }
    Ok(offset)
}

fn skip_frame(stored: &[u8]) -> Result<Option<&[u8]>, Error> {
    let magic = stored.get(..4).ok_or(Error::DecodeFailed)?;
    // The Zstandard format reserves sixteen magic values for opaque skippable frames.
    if !(0x50..=0x5f).contains(&magic[0]) || magic[1..] != [0x2a, 0x4d, 0x18] {
        return Ok(None);
    }
    let length = stored.get(4..8).ok_or(Error::DecodeFailed)?;
    let length = u32::from_le_bytes([length[0], length[1], length[2], length[3]]) as usize;
    let end = 8_usize.checked_add(length).ok_or(Error::DecodeFailed)?;
    stored.get(end..).map(Some).ok_or(Error::DecodeFailed)
}

#[cfg(test)]
mod tests;
