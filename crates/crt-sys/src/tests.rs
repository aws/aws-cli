use super::{AwsAllocator, native, rust_crt_allocator};
use std::ffi::{c_int, c_void};
use std::hint::black_box;

unsafe extern "C" {
    fn aws_default_allocator() -> *mut AwsAllocator;
    fn aws_mem_acquire(allocator: *mut AwsAllocator, size: usize) -> *mut c_void;
    fn aws_mem_realloc(
        allocator: *mut AwsAllocator,
        ptr: *mut *mut c_void,
        oldsize: usize,
        newsize: usize,
    ) -> c_int;
    fn mi_is_in_heap_region(ptr: *const c_void) -> bool;
    fn mi_usable_size(ptr: *const c_void) -> usize;
    fn malloc(size: usize) -> *mut c_void;
    fn calloc(count: usize, size: usize) -> *mut c_void;
    fn realloc(ptr: *mut c_void, size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn posix_memalign(ptr: *mut *mut c_void, alignment: usize, size: usize) -> c_int;
    fn malloc_usable_size(ptr: *mut c_void) -> usize;
    fn reallocarray(ptr: *mut c_void, count: usize, size: usize) -> *mut c_void;
    fn aligned_alloc(alignment: usize, size: usize) -> *mut c_void;
    fn memalign(alignment: usize, size: usize) -> *mut c_void;
    fn valloc(size: usize) -> *mut c_void;
    fn __errno_location() -> *mut c_int;
}

const ENOMEM: c_int = 12;
const EBADF: c_int = 9;
const EINVAL: c_int = 22;

fn probe<T>(call: impl FnOnce() -> T) -> (T, c_int) {
    // SAFETY: __errno_location returns this thread's live errno slot.
    unsafe {
        *__errno_location() = EBADF;
        let result = black_box(call());
        (result, *__errno_location())
    }
}

#[track_caller]
fn assert_failure((result, errno): (*mut c_void, c_int), expected: c_int) {
    assert!(result.is_null());
    assert_eq!(errno, expected);
}

#[repr(C)]
struct AllocatorTable {
    _mem_acquire: unsafe extern "C" fn(*mut AwsAllocator, usize) -> *mut c_void,
    _mem_release: unsafe extern "C" fn(*mut AwsAllocator, *mut c_void),
    _mem_realloc: unsafe extern "C" fn(*mut AwsAllocator, *mut c_void, usize, usize) -> *mut c_void,
    mem_calloc: unsafe extern "C" fn(*mut AwsAllocator, usize, usize) -> *mut c_void,
    implementation: *mut c_void,
}

#[test]
fn crt_calloc_and_realloc_use_mimalloc_and_preserve_contents() {
    // SAFETY: the process-lifetime allocator owns every block below. Each
    // slice is bounded by the requested size and ends before realloc/free.
    unsafe {
        let allocator = rust_crt_allocator();
        let mut block = native::aws_mem_calloc(allocator, 3, 40);
        assert!(!block.is_null());
        assert!(mi_is_in_heap_region(block));
        assert_eq!((block as usize) % 16, 0);
        let bytes = std::slice::from_raw_parts_mut(block.cast::<u8>(), 120);
        assert!(bytes.iter().all(|&byte| byte == 0));
        bytes.fill(0xa5);

        assert_eq!(aws_mem_realloc(allocator, &mut block, 120, 131_072), 0);
        assert!(mi_is_in_heap_region(block));
        assert_eq!(
            std::slice::from_raw_parts(block.cast::<u8>(), 120),
            &[0xa5; 120]
        );
        assert_eq!(aws_mem_realloc(allocator, &mut block, 131_072, 32), 0);
        assert_eq!(
            std::slice::from_raw_parts(block.cast::<u8>(), 32),
            &[0xa5; 32]
        );
        native::aws_mem_release(allocator, block);
    }
}

#[test]
fn crt_allocator_is_the_mimalloc_table_rather_than_the_crt_default() {
    // SAFETY: the block is live from acquisition to release, and growth stays
    // within the usable size mimalloc reports for it.
    unsafe {
        let allocator = rust_crt_allocator();
        assert_ne!(allocator, aws_default_allocator());
        let mut block = aws_mem_acquire(allocator, 100);
        let original = block;
        let usable = mi_usable_size(block);
        assert!(usable > 100);
        // The CRT default always allocates a new block before releasing the
        // old one when a buffer grows. mi_realloc grows within the block.
        assert_eq!(aws_mem_realloc(allocator, &mut block, 100, usable), 0);
        assert_eq!(block, original);
        native::aws_mem_release(allocator, block);
    }
}

#[test]
fn crt_allocator_calloc_rejects_multiplication_overflow() {
    // SAFETY: rust_crt_allocator returns a static aws_allocator whose fields
    // match AllocatorTable. The overflowing request returns no block, while the
    // CRT default would abort on its out-of-memory panic.
    unsafe {
        let allocator = rust_crt_allocator();
        let table = &*allocator.cast::<AllocatorTable>();
        assert!(table.implementation.is_null());
        assert!((table.mem_calloc)(allocator, usize::MAX, 2).is_null());
    }
}

#[test]
fn crt_workers_can_free_blocks_after_the_allocating_thread_exits() {
    let (sender, receiver) = std::sync::mpsc::channel();
    let producer = std::thread::spawn(move || {
        for size in [8, 64, 4096, 131_072, 2_097_152] {
            // SAFETY: each allocation is initialized within its bounds and
            // remains live until the receiver releases it after this thread exits.
            let address = unsafe {
                let block = aws_mem_acquire(rust_crt_allocator(), size);
                assert!(!block.is_null());
                assert!(mi_is_in_heap_region(block));
                block.cast::<u8>().write_bytes(0x5a, size);
                block as usize
            };
            assert!(sender.send((address, size)).is_ok());
        }
    });
    assert!(producer.join().is_ok());
    for (address, size) in receiver {
        // SAFETY: ownership arrived through the channel after the producer
        // exited; no other thread accesses this still-live allocation.
        unsafe {
            let block = address as *mut c_void;
            assert!(
                std::slice::from_raw_parts(block.cast::<u8>(), size)
                    .iter()
                    .all(|&byte| byte == 0x5a)
            );
            native::aws_mem_release(rust_crt_allocator(), block);
        }
    }
}

#[test]
fn runtime_allocation_uses_mimalloc() {
    // SAFETY: allocate/destroy pair owns an otherwise zeroed runtime, and
    // releasing a null block is a no-op.
    unsafe {
        let runtime = native::zaws_runtime_allocate();
        assert!(!runtime.is_null());
        assert!(mi_is_in_heap_region(runtime.cast()));
        native::zaws_runtime_destroy(runtime);
        native::aws_mem_release(rust_crt_allocator(), std::ptr::null_mut());
    }
}

#[test]
fn static_musl_c_allocations_use_mimalloc() {
    // SAFETY: each successful allocation is accessed within its requested
    // bounds and freed exactly once through the matching C allocation family.
    unsafe {
        let block = malloc(37);
        assert!(!block.is_null());
        assert!(mi_is_in_heap_region(block));
        block.cast::<u8>().write_bytes(0xc3, 37);
        let grown = realloc(block, 65_536);
        assert!(!grown.is_null());
        assert!(mi_is_in_heap_region(grown));
        assert_eq!(
            std::slice::from_raw_parts(grown.cast::<u8>(), 37),
            &[0xc3; 37]
        );
        free(grown);

        let zeroed = calloc(3, 40);
        assert!(!zeroed.is_null());
        assert!(mi_is_in_heap_region(zeroed));
        assert_eq!(
            std::slice::from_raw_parts(zeroed.cast::<u8>(), 120),
            &[0; 120]
        );
        free(zeroed);
    }
}

#[test]
fn static_musl_aligned_allocations_use_mimalloc() {
    // SAFETY: the successful POSIX allocation spans 8192 bytes and is freed
    // exactly once through the same C allocation family.
    unsafe {
        let mut aligned = std::ptr::null_mut();
        assert_eq!(posix_memalign(&mut aligned, 4096, 8192), 0);
        assert!(!aligned.is_null());
        assert!(mi_is_in_heap_region(aligned));
        assert_eq!((aligned as usize) % 4096, 0);
        assert!(malloc_usable_size(aligned) >= 8192);
        aligned.cast::<u8>().write_bytes(0x7e, 8192);
        free(aligned);
        free(std::ptr::null_mut());
    }
}

#[test]
fn mimalloc_ignores_its_environment_options() -> std::io::Result<()> {
    // mimalloc reads options as the process starts, so only a fresh process
    // shows whether MIMALLOC_* variables reach it. Unless built with
    // MI_NO_GETENV, these report every option and the statistics on stderr.
    let output = std::process::Command::new(std::env::current_exe()?)
        .args([
            "--exact",
            "tests::static_musl_c_allocations_use_mimalloc",
            "--test-threads=1",
        ])
        .env("MIMALLOC_VERBOSE", "1")
        .env("MIMALLOC_SHOW_STATS", "1")
        .env("MIMALLOC_SHOW_ERRORS", "1")
        .output()?;
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("1 passed"), "{stdout}");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(!stderr.contains("mimalloc"), "{stderr}");
    Ok(())
}

#[test]
fn overflowing_calloc_and_reallocarray_fail_with_enomem() {
    // SAFETY: the overflowing calls allocate nothing. The one block is
    // written within its 16 bytes, survives the failed reallocarray as the
    // C contract requires, and is freed once.
    unsafe {
        assert_failure(probe(|| calloc(usize::MAX, 2)), ENOMEM);
        assert_failure(probe(|| calloc(2, usize::MAX)), ENOMEM);
        assert_failure(
            probe(|| reallocarray(std::ptr::null_mut(), usize::MAX, 2)),
            ENOMEM,
        );
        let block = malloc(16);
        assert!(!block.is_null());
        block.cast::<u8>().write_bytes(0x5a, 16);
        assert_failure(probe(|| reallocarray(block, usize::MAX / 4, 8)), ENOMEM);
        assert_eq!(
            std::slice::from_raw_parts(block.cast::<u8>(), 16),
            &[0x5a; 16]
        );
        assert!(mi_usable_size(block) >= 16);
        free(block);
    }
}

#[test]
fn every_failed_c_allocation_sets_errno() {
    // SAFETY: every call fails and so returns no block to free.
    unsafe {
        assert_failure(probe(|| malloc(usize::MAX)), ENOMEM);
        assert_failure(probe(|| realloc(std::ptr::null_mut(), usize::MAX)), ENOMEM);
        assert_failure(probe(|| valloc(usize::MAX)), ENOMEM);
        assert_failure(probe(|| aligned_alloc(64, usize::MAX)), ENOMEM);
        assert_failure(probe(|| memalign(64, usize::MAX)), ENOMEM);
        assert_failure(probe(|| aligned_alloc(24, 48)), EINVAL);
        assert_failure(probe(|| memalign(0, 16)), EINVAL);
    }
}

#[test]
fn posix_memalign_reports_failure_in_its_result_alone() {
    // SAFETY: failed calls leave `block` null; the successful one returns a
    // block of at least 100 bytes that is freed once.
    unsafe {
        for (alignment, size, expected) in
            [(64, usize::MAX, ENOMEM), (4, 16, EINVAL), (24, 16, EINVAL)]
        {
            let mut block = std::ptr::null_mut();
            let (code, errno) = probe(|| posix_memalign(&mut block, alignment, size));
            assert_eq!(code, expected);
            assert_eq!(errno, EBADF);
            assert!(block.is_null());
        }
        let mut block = std::ptr::null_mut();
        assert_eq!(probe(|| posix_memalign(&mut block, 4096, 100)), (0, EBADF));
        assert_eq!((block as usize) % 4096, 0);
        assert!(mi_usable_size(block) >= 100);
        free(block);
    }
}

const TEST_ALIGNMENTS: [usize; 10] = [1, 2, 4, 8, 16, 32, 64, 4096, 64 * 1024, 1024 * 1024];

const TEST_LENGTHS: [usize; 9] = [
    1,
    7,
    16,
    100,
    1024,
    4097,
    65_536,
    300 * 1024,
    5 * 1024 * 1024,
];

const REMAP_BYTES: usize = 2 * 1024 * 1024;

/// # Safety
/// `block` is a live block from mimalloc.
unsafe fn assert_freeable(block: *mut u8, len: usize, align: usize) {
    assert!(!block.is_null(), "{len} {align}");
    assert_eq!(block as usize % align, 0, "{len} {align}");
    // SAFETY: the caller passes a live mimalloc block.
    unsafe {
        assert!(mi_is_in_heap_region(block.cast()));
        assert!(mi_usable_size(block.cast()) >= len, "{len} {align}");
    }
}

/// # Safety
/// `block` is valid for reads of `len` bytes.
unsafe fn holds(block: *const u8, len: usize, byte: u8) -> bool {
    // SAFETY: the caller guarantees `len` readable bytes.
    unsafe { std::slice::from_raw_parts(block, len) }
        .iter()
        .all(|&b| b == byte)
}

/// # Safety
/// `block` is a live block of this allocator described by `layout`, and is
/// released by this call in favor of the returned block.
unsafe fn grow(
    block: *mut u8,
    layout: std::alloc::Layout,
) -> Result<(*mut u8, std::alloc::Layout), std::alloc::LayoutError> {
    use std::alloc::{GlobalAlloc, Layout};
    let allocator = super::Mimalloc;
    let align = layout.align();
    // SAFETY: the caller passes a live block with its layout; each realloc
    // receives the layout that last described the block.
    unsafe {
        let usable = mi_usable_size(block.cast());
        let same = allocator.realloc(block, layout, usable);
        assert_eq!(same, block, "{layout:?}");
        let usable_layout = Layout::from_size_align(usable, align)?;
        let grown_layout = Layout::from_size_align(usable * 4, align)?;
        let grown = allocator.realloc(same, usable_layout, grown_layout.size());
        assert_freeable(grown, grown_layout.size(), align);
        assert!(holds(grown, layout.size(), 0x3c), "{layout:?}");
        Ok((grown, grown_layout))
    }
}

#[test]
fn global_allocator_meets_alignment_and_keeps_contents_across_realloc()
-> Result<(), std::alloc::LayoutError> {
    use std::alloc::{GlobalAlloc, Layout};
    let allocator = super::Mimalloc;
    for align in TEST_ALIGNMENTS {
        for size in TEST_LENGTHS {
            let layout = Layout::from_size_align(size, align)?;
            // SAFETY: each block is used within its layout and released once
            // with the layout that last described it.
            unsafe {
                let block = allocator.alloc(layout);
                assert_freeable(block, size, align);
                block.write_bytes(0x3c, size);
                let (grown, grown_layout) = grow(block, layout)?;
                let shrunk = allocator.realloc(grown, grown_layout, 1);
                assert_freeable(shrunk, 1, align);
                assert_eq!(*shrunk, 0x3c);
                allocator.dealloc(shrunk, Layout::from_size_align(1, align)?);

                let zeroed = allocator.alloc_zeroed(layout);
                assert_freeable(zeroed, size, align);
                assert!(holds(zeroed, size, 0), "{size} {align}");
                allocator.dealloc(zeroed, layout);
            }
        }
    }
    Ok(())
}

fn pattern_byte(index: usize) -> u8 {
    (index % 256) as u8
}

/// # Safety
/// `block` is valid for reads of `len` bytes.
unsafe fn holds_pattern(block: *const u8, len: usize) -> bool {
    // SAFETY: the caller guarantees `len` readable bytes.
    let bytes = unsafe { std::slice::from_raw_parts(block, len) };
    bytes
        .iter()
        .enumerate()
        .all(|(index, &byte)| byte == pattern_byte(index))
}

#[test]
fn global_allocator_remaps_to_2_mib_and_back_keeping_contents_and_alignment()
-> Result<(), std::alloc::LayoutError> {
    use std::alloc::{GlobalAlloc, Layout};
    let allocator = super::Mimalloc;
    for align in TEST_ALIGNMENTS {
        let small = Layout::from_size_align(64, align)?;
        let large = Layout::from_size_align(REMAP_BYTES, align)?;
        // SAFETY: each block is used within its layout and released once
        // with the layout that last described it.
        unsafe {
            let block = allocator.alloc(small);
            assert_freeable(block, 64, align);
            for index in 0..64 {
                block.add(index).write(pattern_byte(index));
            }
            let grown = allocator.realloc(block, small, REMAP_BYTES);
            assert_freeable(grown, REMAP_BYTES, align);
            assert!(holds_pattern(grown, 64), "{align}");
            grown.add(64).write_bytes(0x5a, REMAP_BYTES - 64);
            let shrunk = allocator.realloc(grown, large, 32);
            assert_freeable(shrunk, 32, align);
            assert!(holds_pattern(shrunk, 32), "{align}");
            allocator.dealloc(shrunk, Layout::from_size_align(32, align)?);
        }
    }
    Ok(())
}
