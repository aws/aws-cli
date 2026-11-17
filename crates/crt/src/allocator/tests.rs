use super::*;
#[test]
fn crt_calloc_release_round_trip() -> Result<(), Box<dyn std::error::Error>> {
    let adapter = Allocator::new().ok_or("allocation failed")?;
    // SAFETY: the adapter remains alive until this block is released.
    unsafe {
        let block = c::aws_mem_calloc(adapter.as_ptr(), 3, 40);
        assert!(!block.is_null());
        assert_eq!((block as usize) % 16, 0);
        let bytes = std::slice::from_raw_parts_mut(block.cast::<u8>(), 120);
        assert!(bytes.iter().all(|&byte| byte == 0));
        bytes.fill(0xff);
        assert_eq!(adapter.outstanding(), 1);
        c::aws_mem_release(adapter.as_ptr(), block);
    }
    assert_eq!(adapter.outstanding(), 0);
    Ok(())
}
