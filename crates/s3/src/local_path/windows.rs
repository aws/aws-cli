fn is_separator(byte: u8) -> bool {
    matches!(byte, b'/' | b'\\')
}

fn is_drive_absolute(path: &[u8]) -> bool {
    path.len() >= 3 && path[1] == b':' && is_separator(path[2])
}

fn is_unc(path: &[u8]) -> bool {
    path.len() >= 2 && is_separator(path[0]) && is_separator(path[1])
}

/// Only ordinary relative and drive-absolute operands stay native. CPython
/// uses `GetFullPathNameW` after `normpath`; device roots, drive-relative
/// paths, parent traversal, and Win32 name trimming need that API, not a
/// lexical resolver.
pub(super) fn supports(path: &[u8]) -> bool {
    let tail = if is_drive_absolute(path) {
        if !path[0].is_ascii_alphabetic() {
            return false;
        }
        &path[3..]
    } else if path.first().copied().is_some_and(is_separator) || path.get(1) == Some(&b':') {
        return false;
    } else {
        path
    };
    !tail.contains(&b':')
        && tail
            .split(|byte| is_separator(*byte))
            .filter(|part| !part.is_empty())
            .all(supports_component)
}

/// Whether a component needs neither Win32 trimming nor DOS-device rewriting.
fn supports_component(part: &[u8]) -> bool {
    if part == b"." {
        return true;
    }
    if part.ends_with(b".") || part.ends_with(b" ") {
        return false;
    }
    let name = part.split(|byte| *byte == b'.').next().unwrap_or_default();
    !name.ends_with(b" ") && !is_device(name)
}

fn is_device(name: &[u8]) -> bool {
    const DEVICES: [&str; 12] = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CONIN$",
        "CONOUT$",
        "COM\u{b9}",
        "COM\u{b2}",
        "COM\u{b3}",
        "LPT\u{b9}",
        "LPT\u{b2}",
        "LPT\u{b3}",
    ];
    if DEVICES
        .iter()
        .any(|device| name.eq_ignore_ascii_case(device.as_bytes()))
    {
        return true;
    }
    name.len() == 4
        && name[3].is_ascii_digit()
        && (name[..3].eq_ignore_ascii_case(b"COM") || name[..3].eq_ignore_ascii_case(b"LPT"))
}

/// Absolute spelling of an admitted operand: joined to `cwd` unless it names
/// a drive, with `.` and empty components dropped and every separator a
/// backslash. The drive keeps its case, as `ntpath.abspath` keeps it. The
/// command routes spellings needing `GetFullPathNameW` to Python first, so
/// only `cwd` can hold a `..`. A UNC path, which no operand is, is one this
/// made absolute already, and `ntpath.abspath` joins it to nothing either,
/// so a spelling this returns comes back unchanged.
pub(super) fn absolute_path(cwd: &[u8], path: &[u8]) -> Vec<u8> {
    let joined = if is_drive_absolute(path) || is_unc(path) {
        path.to_vec()
    } else {
        [cwd, b"\\", path].concat()
    };
    let (root, rest) = split_root(&joined);
    let mut components: Vec<&[u8]> = Vec::new();
    for component in rest.split(|byte| is_separator(*byte)) {
        match component {
            b"" | b"." => {}
            b".." => {
                components.pop();
            }
            _ => components.push(component),
        }
    }
    let mut absolute = root;
    absolute.extend_from_slice(&components.join(&b'\\'));
    absolute
}

/// `ntpath.dirname(path)` of an admitted operand: its drive's `X:\`, then
/// what precedes the last separator after it, less the separators that end
/// that.
pub(super) fn dir_name(path: &[u8]) -> &[u8] {
    let root = if is_drive_absolute(path) { 3 } else { 0 };
    let tail = &path[root..];
    let head = tail
        .iter()
        .rposition(|&byte| is_separator(byte))
        .map_or(0, |i| i + 1);
    let head = tail[..head]
        .iter()
        .rposition(|&byte| !is_separator(byte))
        .map_or(0, |i| i + 1);
    &path[..root + head]
}

/// The part of `path` `guess_type` takes an extension from: what follows
/// the last slash or backslash, once `ntpath.splitdrive` removes a drive.
/// That finds a drive's colon at the second UTF-16 unit, so a code point
/// past the BMP, the only one WTF-8 spells in four bytes, names no drive.
pub(super) fn file_name(path: &[u8]) -> &[u8] {
    let first = path.first().map_or(0, |byte| sequence_length(*byte));
    let name = if first < 4 && path.get(first) == Some(&b':') {
        &path[first + 1..]
    } else {
        path
    };
    name.rsplit(|byte| is_separator(*byte))
        .next()
        .unwrap_or_default()
}

/// The length a UTF-8 lead byte gives its sequence, or 1 for a byte that
/// leads none. A Windows path's encoded bytes are WTF-8, so this is the
/// width of the first code point, a lone surrogate included.
fn sequence_length(first: u8) -> usize {
    match first {
        0xc0..=0xdf => 2,
        0xe0..=0xef => 3,
        0xf0..=0xf7 => 4,
        _ => 1,
    }
}

fn split_root(path: &[u8]) -> (Vec<u8>, &[u8]) {
    if is_drive_absolute(path) {
        return ([&path[..2], b"\\"].concat(), &path[3..]);
    }
    if is_unc(path) {
        let mut parts = path[2..].splitn(3, |byte| is_separator(*byte));
        let server = parts.next().unwrap_or_default();
        let share = parts.next().unwrap_or_default();
        let rest = parts.next().unwrap_or_default();
        return ([b"\\\\", server, b"\\", share, b"\\"].concat(), rest);
    }
    let rest = path.strip_prefix(b"\\").or_else(|| path.strip_prefix(b"/"));
    (b"\\".to_vec(), rest.unwrap_or(path))
}

#[cfg(test)]
mod tests;
