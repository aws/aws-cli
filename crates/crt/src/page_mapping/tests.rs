use super::*;

#[test]
fn a_mapping_is_writable_and_page_aligned() -> Result<(), MapError> {
    let mut mapping = AnonymousMapping::new(page_size())?;
    assert_eq!(mapping.as_ptr().addr() % page_size(), 0);
    let bytes = mapping.as_mut_slice();
    assert_eq!(bytes.len(), page_size());
    bytes[0] = 0x5a;
    bytes[page_size() - 1] = 0xa5;
    assert_eq!(bytes[0], 0x5a);
    assert_eq!(bytes[page_size() - 1], 0xa5);
    Ok(())
}

#[test]
#[cfg_attr(miri, ignore = "Miri does not support madvise with MADV_HUGEPAGE")]
fn native_mapping_is_aligned_writable_and_survives_hugepage_advice() -> Result<(), MapError> {
    let size = page_size() * 2;
    let pointer = map(size)?;
    assert_eq!(pointer.as_ptr().addr() % page_size(), 0);
    // SAFETY: map returned exclusive writable storage covering size bytes.
    let bytes = unsafe { std::slice::from_raw_parts_mut(pointer.as_ptr(), size) };
    bytes.fill(0x5a);
    // SAFETY: the mapping remains live and uniquely owned.
    let _ = unsafe { prefer_huge_pages(pointer, size) };
    assert!(bytes.iter().all(|byte| *byte == 0x5a));
    bytes[size - 1] = 0xa5;
    assert_eq!(bytes[size - 1], 0xa5);
    // SAFETY: the borrow is no longer used and pointer is the original live mapping.
    unsafe { unmap(pointer, size) };
    Ok(())
}

#[test]
fn a_refused_mapping_is_a_map_error() {
    let unmappable = usize::MAX & !(page_size() - 1);
    assert_eq!(AnonymousMapping::new(unmappable).map(|_| ()), Err(MapError));
}
