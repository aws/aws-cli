use super::Unit;

const SLASH: Unit = b'/' as Unit;

/// Appends `os.fsdecode(bytes)` to `units`: UTF-8, with each byte that is
/// not part of a UTF-8 sequence the surrogate escape U+DC80 to U+DCFF.
pub(super) fn decode_into(bytes: &[u8], units: &mut Vec<Unit>) {
    for chunk in bytes.utf8_chunks() {
        units.extend(chunk.valid().chars().map(Unit::from));
        units.extend(
            chunk
                .invalid()
                .iter()
                .map(|&byte| 0xdc00 | Unit::from(byte)),
        );
    }
}

/// `posixpath.join(root, pattern)`: an absolute pattern replaces the root,
/// and a slash separates them unless the root is empty or ends with one.
pub(super) fn join(root: &[Unit], pattern: &[Unit]) -> Vec<Unit> {
    if pattern.first() == Some(&SLASH) || root.is_empty() {
        return pattern.to_vec();
    }
    let separator: &[Unit] = if root.last() == Some(&SLASH) {
        &[]
    } else {
        &[SLASH]
    };
    [root, separator, pattern].concat()
}

#[cfg(test)]
mod tests;
