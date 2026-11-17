//! Bulk copy primitives for the download write path.

pub const FAST_MODES_AVAILABLE: bool =
    cfg!(target_arch = "x86_64") && cfg!(aws_optimized) && !cfg!(miri);

/// Copies shorter than this use memcpy regardless of mode: the alignment
/// prologue and sfence cost more than streaming saves, and short copies only
/// come from final-part tails where throughput does not matter.
pub const FAST_MODE_MIN_LEN: usize = 32 * 1024;

#[cfg(all(target_arch = "x86_64", not(miri)))]
const CACHE_LINE_LEN: usize = 64;
#[cfg(all(target_arch = "x86_64", not(miri)))]
const PREFETCH_DISTANCE: usize = 512;

/// Copy implementation used to move response bodies into mappings.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CopyMode {
    Memcpy,
    Nt,
    RepMovsb,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CopyPath {
    /// The copy ran in the requested mode.
    Requested,
    /// A fast mode was requested but the copy used memcpy instead.
    MemcpyFallback,
}
pub fn copy(mode: CopyMode, destination: &mut [u8], source: &[u8]) -> CopyPath {
    assert_eq!(destination.len(), source.len());
    if mode == CopyMode::Memcpy {
        destination.copy_from_slice(source);
        return CopyPath::Requested;
    }
    if !FAST_MODES_AVAILABLE || source.len() < FAST_MODE_MIN_LEN {
        destination.copy_from_slice(source);
        return CopyPath::MemcpyFallback;
    }
    fast_copy(mode, destination, source);
    CopyPath::Requested
}
#[cfg(all(target_arch = "x86_64", not(miri)))]
fn fast_copy(mode: CopyMode, destination: &mut [u8], source: &[u8]) {
    if mode == CopyMode::Nt {
        copy_nt(destination, source);
    } else {
        copy_rep_movsb(destination, source);
    }
}
#[cfg(any(not(target_arch = "x86_64"), miri))]
fn fast_copy(_: CopyMode, destination: &mut [u8], source: &[u8]) {
    destination.copy_from_slice(source);
}
#[cfg(all(target_arch = "x86_64", not(miri)))]
fn copy_nt(destination: &mut [u8], source: &[u8]) {
    let misalignment = destination.as_ptr().addr() & (CACHE_LINE_LEN - 1);
    let head = if misalignment == 0 {
        0
    } else {
        (CACHE_LINE_LEN - misalignment).min(source.len())
    };
    destination[..head].copy_from_slice(&source[..head]);
    let body_end = head + ((source.len() - head) & !(CACHE_LINE_LEN - 1));
    if body_end != head {
        nt_store_body(&mut destination[head..body_end], &source[head..body_end]);
    }
    destination[body_end..].copy_from_slice(&source[body_end..]);
    // SAFETY: SSE is baseline x86_64; the fence orders the streaming stores
    // before the caller's completion stores.
    unsafe {
        core::arch::x86_64::_mm_sfence();
    }
}
#[cfg(all(target_arch = "x86_64", not(miri)))]
fn nt_store_body(destination: &mut [u8], source: &[u8]) {
    use core::arch::x86_64::{
        __m128i, _MM_HINT_NTA, _mm_loadu_si128, _mm_prefetch, _mm_stream_si128,
    };
    assert_eq!(destination.as_ptr().addr() & (CACHE_LINE_LEN - 1), 0);
    assert!(!destination.is_empty() && destination.len().is_multiple_of(CACHE_LINE_LEN));
    assert_eq!(destination.len(), source.len());
    let from = source.as_ptr();
    let to = destination.as_mut_ptr();
    for offset in (0..source.len()).step_by(CACHE_LINE_LEN) {
        // SAFETY: SSE2 is baseline x86_64. A prefetch is a hint that never
        // faults, so its address may pass the end of the source; wrapping_add
        // keeps computing it defined. The asserts above make both slices the
        // same multiple of 64 bytes, so each 64-byte step lies within both, and
        // the asserted destination alignment keeps every 16-byte streaming
        // store aligned.
        unsafe {
            _mm_prefetch::<_MM_HINT_NTA>(from.wrapping_add(offset + PREFETCH_DISTANCE).cast());
            let first = _mm_loadu_si128(from.add(offset).cast::<__m128i>());
            let second = _mm_loadu_si128(from.add(offset + 16).cast::<__m128i>());
            let third = _mm_loadu_si128(from.add(offset + 32).cast::<__m128i>());
            let fourth = _mm_loadu_si128(from.add(offset + 48).cast::<__m128i>());
            _mm_stream_si128(to.add(offset).cast::<__m128i>(), first);
            _mm_stream_si128(to.add(offset + 16).cast::<__m128i>(), second);
            _mm_stream_si128(to.add(offset + 32).cast::<__m128i>(), third);
            _mm_stream_si128(to.add(offset + 48).cast::<__m128i>(), fourth);
        }
    }
}
/// On ERMS/FSRM cores the microcoded fast-string path avoids RFOs for large
/// copies and handles alignment itself. Fast-string stores order with later
/// stores at retirement, so no fence is needed. The System V ABI guarantees
/// the direction flag is clear on entry, so this copies forward.
#[cfg(all(target_arch = "x86_64", not(miri)))]
fn copy_rep_movsb(destination: &mut [u8], source: &[u8]) {
    assert_eq!(destination.len(), source.len());
    // SAFETY: disjoint equal-length Rust slices cover all bytes copied. The ABI
    // keeps the direction flag clear; rep movsb does not access bytes outside them.
    unsafe {
        core::arch::asm!("rep movsb", inout("rdi") destination.as_mut_ptr() => _,
            inout("rsi") source.as_ptr() => _, inout("rcx") source.len() => _,
            options(nostack, preserves_flags));
    }
}
#[cfg(test)]
mod tests;
