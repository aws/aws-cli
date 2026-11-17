use super::*;

fn state() -> RequestState {
    RequestState {
        inner: Mutex::new(RequestInner::default()),
        submission: Arc::new(Submission::new(CrtMetaRequestOps)),
        proxy: String::new(),
        logger: None,
        progress: None,
        operation: b"HeadObject",
        bytes_transferred: AtomicU64::new(0),
    }
}
#[test]
fn head_archive_matrix_preserves_exact_classes_and_restore_completion() {
    let _library = Library::acquire();
    let state = state();
    for (storage, restore, readable) in [
        ("", "", true),
        ("STANDARD", "", true),
        ("GLACIER_IR", "", true),
        ("GLACIER", "", false),
        ("DEEP_ARCHIVE", "", false),
        ("GLACIER", "ongoing-request=\"true\"", false),
        ("DEEP_ARCHIVE", "ongoing-request=\"true\"", false),
        (
            "GLACIER",
            "ongoing-request=\"false\", expiry-date=\"later\"",
            true,
        ),
        (
            "DEEP_ARCHIVE",
            "ongoing-request=\"false\", expiry-date=\"later\"",
            true,
        ),
        ("glacier", "", true),
    ] {
        let headers = c::HeadHeaders {
            length: cursor(b"0"),
            modified: cursor(b""),
            storage_class: cursor(storage.as_bytes()),
            restore: cursor(restore.as_bytes()),
            etag: cursor(b""),
            region: cursor(b""),
            checksum_type: cursor(b""),
            checksum_crc32: cursor(b""),
            checksum_crc32c: cursor(b""),
            checksum_crc64nvme: cursor(b""),
            region_present: false,
            checksum_type_present: false,
            checksum_reported: false,
        };
        // SAFETY: the stack state and borrowed headers remain live for this call.
        let status =
            unsafe { on_headers(&headers, 200, std::ptr::from_ref(&state).cast_mut().cast()) };
        assert_eq!(status, 0);
        let inner = lock(&state.inner);
        assert_eq!(inner.head.archive.readable(), readable);
        assert_eq!(inner.head.content_length, Some(0));
    }
}
#[test]
fn progress_forwarding_preserves_each_parts_bytes_without_finishing() {
    let values = Arc::new(Mutex::new(Vec::new()));
    let captured = Arc::clone(&values);
    let mut state = state();
    state.progress = Some(Arc::new(move |bytes| lock(&captured).push(bytes)));
    for bytes in [8 * 1024 * 1024, 2 * 1024 * 1024] {
        // SAFETY: the stack state is live throughout the synchronous callback.
        unsafe { on_progress(bytes, std::ptr::from_ref(&state).cast_mut().cast()) };
    }
    assert_eq!(*lock(&values), [8 * 1024 * 1024, 2 * 1024 * 1024]);
    assert_eq!(lock(&state.inner).head.content_length, None);
}
