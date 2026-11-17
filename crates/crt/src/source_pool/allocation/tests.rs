use super::*;
#[cfg(target_os = "linux")]
use crate::source_pool::{Config, FactoryConfig, factory};
use crt_sys::{self as ffi, native as c};
#[cfg(target_os = "linux")]
use std::ptr;

mod fixture;
use fixture::Allocator;
#[cfg(target_os = "linux")]
use fixture::Pool;

#[test]
fn native_storage_without_calloc_is_zeroed_and_released() -> Result<(), Box<dyn std::error::Error>>
{
    let allocator = Allocator::new(0)?;
    let ops = CrtAllocationOps::new(allocator.as_ptr());
    let layout = Layout::array::<u64>(4)?;
    let pointer = ops
        .allocate(AllocationKind::Slots, layout)
        .ok_or("storage allocation failed")?;
    // SAFETY: the allocator returned four aligned, initialized u64 values.
    unsafe {
        let values = std::slice::from_raw_parts(pointer.as_ptr().cast::<u64>(), 4);
        assert_eq!(values, &[0, 0, 0, 0]);
        ops.release(AllocationKind::Slots, pointer, layout);
    }
    assert_eq!(allocator.counts(), (1, 1, 0));
    Ok(())
}

#[test]
fn native_zeroing_rejects_overflow_before_calling_allocator() -> Result<(), &'static str> {
    let allocator = Allocator::new(0)?;
    // SAFETY: the live allocator and nonzero sizes are valid; their product is checked by the shim.
    let pointer = unsafe { c::zaws_allocate_zeroed(allocator.as_ptr(), usize::MAX, 2) };
    assert!(pointer.is_null());
    assert_eq!(allocator.counts(), (0, 0, 0));
    Ok(())
}

#[test]
fn native_zeroing_accepts_the_default_allocator() -> Result<(), &'static str> {
    // SAFETY: CRT's default allocator is process-global and the block is released below.
    unsafe {
        let allocator = ffi::rust_crt_allocator();
        let pointer = NonNull::new(c::zaws_allocate_zeroed(allocator, 4, 8))
            .ok_or("storage allocation failed")?;
        let bytes = std::slice::from_raw_parts(pointer.as_ptr().cast::<u8>(), 32);
        assert_eq!(bytes, &[0; 32]);
        c::aws_mem_release(allocator, pointer.as_ptr());
    }
    Ok(())
}

#[test]
#[cfg(target_os = "linux")]
fn native_factory_allocator_failures_roll_back() -> Result<(), Box<dyn std::error::Error>> {
    let config = FactoryConfig::new(Config::new(vec![0, 1, 2], 6)?);
    let crt_config = ffi::AwsS3BufferPoolConfig {
        client: ptr::null_mut(),
        part_size: 1,
        max_part_size: 1,
        memory_limit: 6,
    };
    for fail_at in 1..=5 {
        let allocator = Allocator::new(fail_at)?;
        // SAFETY: both the allocator and config outlive the returned pool, if any.
        let raw = unsafe {
            factory(
                allocator.as_ptr(),
                crt_config,
                (&raw const config).cast_mut().cast(),
            )
        };
        let pool = Pool::new(raw);
        assert!(pool.is_none());
        // SAFETY: this shim reads the calling thread's CRT error slot; AWS_ERROR_OOM is 1.
        assert_eq!(unsafe { ffi::rust_crt_last_error() }, 1);
        assert_eq!(allocator.counts(), (fail_at, fail_at - 1, 0));
    }
    let allocator = Allocator::new(0)?;
    // SAFETY: config and allocator remain live until this pool's final release.
    let raw = unsafe {
        factory(
            allocator.as_ptr(),
            crt_config,
            (&raw const config).cast_mut().cast(),
        )
    };
    let pool = Pool::new(raw).ok_or("pool construction failed")?;
    assert_eq!(allocator.counts(), (5, 0, 5));
    drop(pool);
    assert_eq!(allocator.counts(), (5, 5, 0));
    Ok(())
}
