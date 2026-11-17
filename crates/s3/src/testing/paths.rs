//! A recursive download's local path for any listing key stays under its
//! destination root.
//!
//! The input builds a key from pieces and picks a root from a fixed set. When
//! the scheduler's escape checks pass the key, the destination path must
//! normalize, lexically, to the root or a path below it, and a key naming the
//! root's parent must map to that parent. The normalizer here applies the
//! host's separators and drive prefixes itself, rather than the key
//! normalization the escape checks use, so the check does not grade itself.
//! The same destination then checks its temp path and its absolute path.
#![expect(
    clippy::expect_used,
    reason = "the model's paths are built from UTF-8 strings"
)]
use crate::testing::Choices;
use crate::{local_path, transfer, uri};
use std::path::Path;

/// The pieces a key concatenates. The non-ASCII piece repeats a chosen
/// number of times, so a name can pass the temp name limit.
const PIECES: [&str; 9] = ["", ".", "..", "a", "bc", "/", "\\", "C:", "é名"];
const NON_ASCII: usize = 8;
/// The most repetitions of the non-ASCII piece: 60 of its 5 bytes pass the
/// 255-byte file name limit.
const REPEATS_MAX: usize = 60;
const PIECES_MAX: usize = 12;
/// An absolute root and one ending in a separator, as the host spells them.
#[cfg(windows)]
const HOST_ROOTS: [&str; 2] = [r"C:\srv\dl", r"out\dl\"];
#[cfg(not(windows))]
const HOST_ROOTS: [&str; 2] = ["/srv/dl", "/srv/dl/"];
/// Destination operands before the scheduler normalizes them as roots; the
/// empty one becomes the current directory.
const ROOTS: [&str; 7] = [
    "dl",
    "out/dl/",
    ".",
    "",
    "../dl",
    HOST_ROOTS[0],
    HOST_ROOTS[1],
];
#[cfg(windows)]
const CWD: &str = r"C:\work";
#[cfg(not(windows))]
const CWD: &str = "/home/user/work";
#[cfg(windows)]
const SEPARATORS: &[char] = &['/', '\\'];
#[cfg(not(windows))]
const SEPARATORS: &[char] = &['/'];
const TEMP_ID: u64 = 0x0123_4567_89ab_cdef;
/// The file name limit temp names keep to.
const NAME_BYTES_MAX: usize = 255;

/// Checks the destination, temp and absolute paths of one key under one root.
pub fn path_containment(bytes: &[u8]) {
    path_containment_from(&mut Choices::new(bytes));
}
fn path_containment_from(input: &mut Choices<'_>) -> Destination {
    let root = transfer::normalize_local_directory_root(Path::new(ROOTS[input.index(ROOTS.len())]));
    let key = key(input);
    let destination = transfer::build_recursive_destination_path(&root, &key);
    let path = destination.to_str().expect("a UTF-8 destination");
    let taken = assert_contained(root.to_str().expect("a UTF-8 root"), &key, path);
    assert_temp_name(path);
    assert_absolute(&destination);
    taken
}

fn key(input: &mut Choices<'_>) -> String {
    let mut key = String::new();
    for _ in 0..input.range(0, PIECES_MAX) {
        let piece = input.index(PIECES.len());
        let repeats = if piece == NON_ASCII {
            input.range(1, REPEATS_MAX)
        } else {
            1
        };
        key.push_str(&PIECES[piece].repeat(repeats));
    }
    key
}

/// Which of the scheduler's local destinations a key takes.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Destination {
    Escapes,
    RootParent,
    Resolved,
}
fn assert_contained(root: &str, key: &str, path: &str) -> Destination {
    if uri::relative_key_escapes_root(key) {
        return Destination::Escapes;
    }
    let built = lexical(path);
    if uri::relative_key_names_root_parent(key) {
        // The root ends in a separator.
        let parent = [root, ".."].concat();
        assert_eq!(
            built,
            lexical(&parent),
            "{key:?} in {root:?} is not its parent"
        );
        return Destination::RootParent;
    }
    let root_path = lexical(root);
    let below = built.parts.get(root_path.parts.len()..).unwrap_or_default();
    assert!(
        built.drive == root_path.drive
            && built.rooted == root_path.rooted
            && built.parts.starts_with(&root_path.parts)
            && !below.contains(&".."),
        "{key:?} in {root:?} escapes to {path:?}"
    );
    Destination::Resolved
}

/// A path as lexical normalization leaves it: its drive, whether it starts
/// at a root, and its components without `.`, each `..` removing the name
/// before it; a `..` at a root stays there.
#[derive(Debug, PartialEq, Eq)]
struct Lexical<'a> {
    drive: &'a str,
    rooted: bool,
    parts: Vec<&'a str>,
}
fn lexical(path: &str) -> Lexical<'_> {
    let (drive, rest) = drive(path);
    let rooted = rest.starts_with(SEPARATORS);
    let mut parts: Vec<&str> = Vec::new();
    for part in rest.split(SEPARATORS) {
        match part {
            "" | "." => {}
            ".." if parts.last().is_some_and(|last| *last != "..") => {
                parts.pop();
            }
            ".." if rooted => {}
            _ => parts.push(part),
        }
    }
    Lexical {
        drive,
        rooted,
        parts,
    }
}
/// A Windows path's drive prefix, such as `C:`, and the rest; POSIX paths
/// have none.
fn drive(path: &str) -> (&str, &str) {
    match path.as_bytes() {
        [letter, b':', ..] if cfg!(windows) && letter.is_ascii_alphabetic() => path.split_at(2),
        _ => ("", path),
    }
}
/// A path's bytes through its last separator, and its name after it.
fn split_name(path: &str) -> (&str, &str) {
    path.rfind(SEPARATORS)
        .map_or(("", path), |separator| path.split_at(separator + 1))
}

/// The temp path keeps the destination's parent, and its name is the
/// longest prefix of the destination's name, cut at a character, that fits
/// the name limit with the suffix.
fn assert_temp_name(destination: &str) {
    let temp = transfer::make_download_temp_path(Path::new(destination), TEMP_ID)
        .expect("a temp path allocates");
    let temp = temp.to_str().expect("a temp name cut at a character");
    let (parent, name) = split_name(destination);
    let (temp_parent, temp_name) = split_name(temp);
    assert_eq!(
        temp_parent, parent,
        "{temp:?} left {destination:?}'s parent"
    );
    assert!(temp_name.len() <= NAME_BYTES_MAX, "{temp:?} is too long");
    let kept = temp_name
        .strip_suffix(&format!(".{TEMP_ID:016x}"))
        .expect("the temp suffix");
    let cut = name.strip_prefix(kept).expect("a prefix of the name");
    let next = cut.chars().next();
    assert!(
        next.is_none_or(|next| temp_name.len() + next.len_utf8() > NAME_BYTES_MAX),
        "{temp:?} cuts {destination:?} short"
    );
}

/// The absolute path of a destination the native path admits is absolute,
/// UTF-8, free of `.` and `..` components, and its own absolute path.
fn assert_absolute(destination: &Path) {
    if !local_path::supports(destination.as_os_str()) {
        return;
    }
    let cwd = Path::new(CWD);
    let absolute = local_path::absolute_path(cwd, destination);
    let spelled = absolute.to_str().expect("an absolute path of UTF-8 paths");
    assert!(absolute.is_absolute(), "{spelled:?} is relative");
    assert!(
        drive(spelled)
            .1
            .split(SEPARATORS)
            .all(|part| part != "." && part != ".."),
        "{spelled:?} keeps a dot component"
    );
    assert_eq!(local_path::absolute_path(cwd, &absolute), absolute);
}

#[cfg(test)]
mod tests;
