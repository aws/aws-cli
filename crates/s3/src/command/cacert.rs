const ENTRY_NAME: &[u8] = cli_core::client_config::CACERT_ENTRY_NAME.as_bytes();

pub(super) fn find(payload: &[u8]) -> Option<&[u8]> {
    let view = pyload::View::new(payload).ok()?;
    let entry = view.find(ENTRY_NAME).ok()??.entry;
    debug_assert!(
        !entry.is_compressed(),
        "the packer stores the CA bundle uncompressed"
    );
    let pem = view.stored_bytes(entry).ok()?;
    debug_assert_eq!(
        pem.len() as u64,
        entry.uncompressed_len,
        "a raw entry stores its whole length"
    );
    Some(pem)
}

#[cfg(test)]
mod tests;
