use super::Unit;

const SLASH: Unit = b'/' as Unit;
const BACKSLASH: Unit = b'\\' as Unit;
const COLON: Unit = b':' as Unit;

fn is_separator(unit: Unit) -> bool {
    unit == SLASH || unit == BACKSLASH
}

/// Appends the code points of `bytes` to `units`, WTF-8 as a Windows OS
/// string encodes them: UTF-8 that also spells an unpaired surrogate.
pub(super) fn decode_into(bytes: &[u8], units: &mut Vec<Unit>) {
    let mut rest = bytes;
    while let Some((&lead, tail)) = rest.split_first() {
        let (continuations, bits) = match lead {
            0x00..=0x7f => (0, lead),
            0xc0..=0xdf => (1, lead & 0x1f),
            0xe0..=0xef => (2, lead & 0x0f),
            _ => (3, lead & 0x07),
        };
        let (sequence, next) = tail.split_at(continuations.min(tail.len()));
        units.push(sequence.iter().fold(Unit::from(bits), |unit, &byte| {
            unit << 6 | Unit::from(byte & 0x3f)
        }));
        rest = next;
    }
}

/// `ntpath.splitroot(path)`, as CPython's `_Py_skiproot` splits it: the
/// lengths of the drive and of the root the tail follows. A drive is a
/// UNC share, `\\server\share` or `\\?\UNC\server\share`, a device such as
/// `\\.\device`, or a code point and a colon; the root is one separator.
/// `_Py_skiproot` looks for that colon at the second of the path's UTF-16
/// units, so a code point past the BMP, which takes two, names no drive.
fn split_root(path: &[Unit]) -> (usize, usize) {
    let separator = |index: usize| path.get(index).copied().is_some_and(is_separator);
    if separator(0) {
        if !separator(1) {
            return (0, 1);
        }
        let unc = path.get(2) == Some(&Unit::from(b'?'))
            && separator(3)
            && path.get(4..7).is_some_and(|name| {
                name.iter().zip(b"UNC").all(|(&unit, &upper)| {
                    unit == Unit::from(upper) || unit == Unit::from(upper.to_ascii_lowercase())
                })
            })
            && separator(7);
        let next_separator = |from: usize| {
            path.get(from..)?
                .iter()
                .position(|&unit| is_separator(unit))
                .map(|found| from + found)
        };
        let Some(server) = next_separator(if unc { 8 } else { 2 }) else {
            return (path.len(), 0);
        };
        return match next_separator(server + 1) {
            Some(share) => (share, 1),
            None => (path.len(), 0),
        };
    }
    if path.first().is_some_and(|&unit| unit <= 0xffff) && path.get(1) == Some(&COLON) {
        return (2, usize::from(separator(2)));
    }
    (0, 0)
}

/// `ntpath.join(path, other)`: a rooted `other` replaces the path, keeping
/// its drive unless `other` names one; a drive-relative `other` replaces a
/// path on another drive, and joins one on its drive under its spelling;
/// otherwise a backslash separates them unless the path ends with a
/// separator. A UNC drive followed only by a tail gains a backslash.
pub(super) fn join(path: &[Unit], other: &[Unit]) -> Vec<Unit> {
    let parts = |path: &[Unit]| {
        let (drive, root) = split_root(path);
        let (drive, rest) = path.split_at(drive);
        let (root, tail) = rest.split_at(root);
        (drive.to_vec(), root.to_vec(), tail.to_vec())
    };
    let (mut drive, mut root, mut tail) = parts(path);
    let (other_drive, other_root, other_tail) = parts(other);
    if !other_root.is_empty() {
        if !other_drive.is_empty() || drive.is_empty() {
            drive = other_drive;
        }
        root = other_root;
        tail = other_tail;
    } else if !other_drive.is_empty()
        && other_drive != drive
        && lower(&other_drive) != lower(&drive)
    {
        drive = other_drive;
        root = other_root;
        tail = other_tail;
    } else {
        if !other_drive.is_empty() {
            drive = other_drive;
        }
        if tail.last().is_some_and(|&unit| !is_separator(unit)) {
            tail.push(BACKSLASH);
        }
        tail.extend(other_tail);
    }
    let unc_tail = !tail.is_empty()
        && root.is_empty()
        && drive
            .last()
            .is_some_and(|&unit| unit != COLON && !is_separator(unit));
    if unc_tail {
        root = vec![BACKSLASH];
    }
    [drive, root, tail].concat()
}

/// `str.lower()` of each code point; a surrogate is itself.
fn lower(units: &[Unit]) -> Vec<Unit> {
    units
        .iter()
        .flat_map(|&unit| match char::from_u32(unit) {
            Some(character) => character.to_lowercase().map(Unit::from).collect(),
            None => vec![unit],
        })
        .collect()
}

/// `ntpath.normcase(path)`: every slash a backslash, then lowercased as
/// `LCMapStringEx` maps the invariant locale's lowercase, which CPython
/// calls on its UTF-16.
#[cfg(windows)]
pub(super) fn normcase(path: &[Unit]) -> Vec<Unit> {
    let utf16: Vec<u16> = path
        .iter()
        .flat_map(|&unit| {
            let unit = if unit == SLASH { BACKSLASH } else { unit };
            match char::from_u32(unit) {
                Some(character) => character.encode_utf16(&mut [0; 2]).to_vec(),
                None => vec![unit as u16],
            }
        })
        .collect();
    char::decode_utf16(lowercase(&utf16))
        .map(|unit| unit.map_or_else(|error| error.unpaired_surrogate().into(), Unit::from))
        .collect()
}

// The prototype winnls.h declares, with `LPNLSVERSIONINFO`, `LPVOID`, and
// `LPARAM` as the pointers and the pointer-sized integer they are.
#[cfg(windows)]
#[link(name = "kernel32")]
unsafe extern "system" {
    fn LCMapStringEx(
        locale_name: *const u16,
        map_flags: u32,
        source: *const u16,
        source_len: i32,
        destination: *mut u16,
        destination_len: i32,
        version_information: *mut std::ffi::c_void,
        reserved: *mut std::ffi::c_void,
        sort_handle: isize,
    ) -> i32;
}

/// `_winapi.LCMapStringEx(LOCALE_NAME_INVARIANT, LCMAP_LOWERCASE, text)`.
/// An empty text is itself, as `normcase` returns it; a text the call
/// cannot map, which CPython raises for, is left as it is.
#[cfg(windows)]
fn lowercase(text: &[u16]) -> Vec<u16> {
    use std::ptr;
    const LCMAP_LOWERCASE: u32 = 0x0000_0100;
    // LOCALE_NAME_INVARIANT, the empty locale name.
    let invariant: [u16; 1] = [0];
    let Ok(length) = i32::try_from(text.len()) else {
        return text.to_vec();
    };
    if length == 0 {
        return Vec::new();
    }
    // SAFETY: the locale name is NUL-terminated, the source holds `length`
    // units, and a null destination of length zero asks only for the size.
    let size = unsafe {
        LCMapStringEx(
            invariant.as_ptr(),
            LCMAP_LOWERCASE,
            text.as_ptr(),
            length,
            ptr::null_mut(),
            0,
            ptr::null_mut(),
            ptr::null_mut(),
            0,
        )
    };
    let Ok(capacity) = usize::try_from(size) else {
        return text.to_vec();
    };
    if capacity == 0 {
        return text.to_vec();
    }
    let mut mapped = vec![0; capacity];
    // SAFETY: as above, with a destination of `size` writable units.
    let written = unsafe {
        LCMapStringEx(
            invariant.as_ptr(),
            LCMAP_LOWERCASE,
            text.as_ptr(),
            length,
            mapped.as_mut_ptr(),
            size,
            ptr::null_mut(),
            ptr::null_mut(),
            0,
        )
    };
    match usize::try_from(written) {
        Ok(written) if written > 0 => {
            mapped.truncate(written);
            mapped
        }
        _ => text.to_vec(),
    }
}

#[cfg(test)]
mod tests;
