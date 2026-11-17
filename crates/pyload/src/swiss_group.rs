//! Sixteen-byte Swiss-table groups compared with the target's baseline SIMD.

use fearless_simd::{Level, Simd, dispatch, mask8x16, prelude::*, u8x16};

pub const WIDTH: usize = 16;

/// Lanes of the group at `bucket` equal to `h2`, with lane 0 in bit 0.
pub fn match_h2(control: &[u8], bucket: usize, h2: u8) -> u16 {
    dispatch!(Level::baseline(), simd => match_vec(simd, control, bucket, h2).to_bitmask() as u16)
}

pub fn any_empty(control: &[u8], bucket: usize, empty: u8) -> bool {
    dispatch!(Level::baseline(), simd => match_vec(simd, control, bucket, empty).any_true())
}

#[inline(always)]
fn match_vec<S: Simd>(simd: S, control: &[u8], bucket: usize, byte: u8) -> mask8x16<S> {
    u8x16::from_slice(simd, &control[bucket..bucket + WIDTH]).simd_eq(byte)
}

#[derive(Clone, Copy, Debug)]
pub struct ProbeSeq {
    pub bucket: usize,
    mask: usize,
    stride: usize,
}
impl ProbeSeq {
    pub const fn new(bucket: usize, mask: usize) -> Self {
        Self {
            bucket,
            mask,
            stride: 0,
        }
    }
    pub fn advance(&mut self) {
        self.stride = (self.stride + WIDTH) & self.mask;
        self.bucket = (self.bucket + self.stride) & self.mask;
    }
}

#[cfg(test)]
mod tests;
