unsafe extern "C" {
    static awscli_payload_start: u8;
    static awscli_payload_end: u8;
}

/// Returns the one immutable payload section retained for the process lifetime.
pub fn embedded() -> &'static [u8] {
    let start = std::ptr::addr_of!(awscli_payload_start);
    let end = std::ptr::addr_of!(awscli_payload_end);
    assert!(end as usize >= start as usize, "payload section order");
    let len = end as usize - start as usize;
    // SAFETY: the executable's assembly emits these symbols immediately before
    // and after the read-only payload bytes, retained for the process lifetime.
    unsafe { std::slice::from_raw_parts(start, len) }
}
