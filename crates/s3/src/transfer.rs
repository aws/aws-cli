//! Filesystem preparation, temp-file ownership, timestamps, and transfer result lines.
use crate::sync::comparator::Modified;
use std::{
    collections::TryReserveError,
    fs, io,
    path::{Path, PathBuf},
    time::{Duration, SystemTime},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Direction {
    Download,
    Upload,
    /// `s3 rm`'s DeleteObject of each object it names.
    Delete,
}
impl std::fmt::Display for Direction {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Download => "download",
            Self::Upload => "upload",
            Self::Delete => "delete",
        })
    }
}

/// Who pays for the requests a command sends to a Requester Pays bucket.
///
/// `--request-payer` takes one value, which each request then sends as
/// `x-amz-request-payer`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RequestPayer {
    /// `requester`, the one value S3 accepts.
    Requester,
}
impl RequestPayer {
    /// The `x-amz-request-payer` header value.
    pub const fn header_value(self) -> &'static [u8] {
        match self {
            Self::Requester => b"requester",
        }
    }
}
impl TryFrom<&str> for RequestPayer {
    type Error = UnknownRequestPayer;
    /// The payer `value` names, as argparse stores `--request-payer`.
    fn try_from(value: &str) -> Result<Self, Self::Error> {
        match value {
            "requester" => Ok(Self::Requester),
            _ => Err(UnknownRequestPayer),
        }
    }
}

/// A `--request-payer` value other than `requester`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct UnknownRequestPayer;
impl std::fmt::Display for UnknownRequestPayer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("request payer is not requester")
    }
}
impl std::error::Error for UnknownRequestPayer {}

/// What becomes of each source once its transfer succeeded.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub enum SourceDisposition {
    /// A copy keeps every source.
    #[default]
    Keep,
    /// A move deletes each one, before its result is reported
    /// (the request submitters' `_add_additional_subscribers`): an upload
    /// removes its file, and a download deletes its object
    /// (`DeleteSourceFileSubscriber`, `DeleteSourceObjectSubscriber`).
    Delete {
        /// The `user-agent` each DeleteObject sends.
        user_agent: String,
    },
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum GlacierPolicy {
    #[default]
    Warn,
    Skip,
    Transfer,
}
impl GlacierPolicy {
    pub fn from_flags(force: bool, ignore_warnings: bool) -> Self {
        if force {
            Self::Transfer
        } else if ignore_warnings {
            Self::Skip
        } else {
            Self::Warn
        }
    }
}
pub fn glacier_warning(source: &[u8]) -> Vec<u8> {
    [
        b"warning: Skipping file ".as_slice(),
        source,
        b". Object is of storage class GLACIER. Unable to \
            perform download operations on GLACIER objects. You must restore the object to \
            be able to perform the operation. See aws s3 download help for additional \
            parameter options to ignore or force these transfers.",
    ]
    .concat()
}
pub fn parent_escape_warning(relative: &str) -> String {
    format!("warning: Skipping file {relative}. File references a parent directory.")
}
/// Upstream's `MAX_UPLOAD_SIZE` (customizations/s3/utils.py): 10,000 parts
/// of 5 GiB.
pub const MAX_UPLOAD_SIZE: u64 = 5 * (1 << 30) * 10_000;
/// The warning upstream's upload submitter gives a source past the limit.
///
/// `display` names the source as its result line does. The warning skips
/// nothing: the source is still uploaded, or reported by a dry run.
pub fn upload_size_warning(display: &Path) -> Vec<u8> {
    [
        b"warning: File ".as_slice(),
        display.as_os_str().as_encoded_bytes(),
        b" exceeds s3 upload limit of ",
        cli_core::output::format_size(MAX_UPLOAD_SIZE, true).as_bytes(),
        b".",
    ]
    .concat()
}
/// The warning upstream's file generator gives a local file whose mtime it
/// cannot read, which it lists with the epoch as its mtime
/// (`FileGenerator._validate_update_time`). It names no file and skips nothing.
pub const INVALID_TIMESTAMP_WARNING: &[u8] =
    b"warning: File has an invalid timestamp. Passing epoch time as timestamp.";
/// The warning upstream's `create_warning` builds for a committed download
/// whose modification time could not be set: the absolute destination
/// `path` twice, then the error.
pub fn mtime_warning(path: &Path, error: &str) -> Vec<u8> {
    let path = path.as_os_str().as_encoded_bytes();
    [
        b"warning: Skipping file ".as_slice(),
        path,
        b". Successfully Downloaded ",
        path,
        b" but was unable to update the last modified time. ",
        error.as_bytes(),
    ]
    .concat()
}
/// The native diagnostic for a download destination whose parent could not
/// be created, ahead of the destination and the error.
pub const PARENT_DIRECTORY_FAILURE: &str = "error: unable to create parent directory for";
/// The native diagnostic for a download whose temp path could not be built,
/// ahead of the destination and the error.
pub const TEMP_PATH_FAILURE: &str = "error: unable to prepare download destination";
/// Why upstream's file generator skips an upload source with a warning.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceSkip {
    /// `os.path.exists` denies the source.
    Missing,
    /// A character or block device, a FIFO, or a socket.
    Special,
    /// Opening it to read fails.
    UnreadableFile,
    /// Listing it fails.
    UnreadableDirectory,
    /// The recursive walk cannot open a directory below its root.
    UnreadableSubdirectory,
}
impl SourceSkip {
    /// The sentence upstream's `triggers_warning` gives `create_warning`.
    pub fn reason(self) -> &'static str {
        match self {
            Self::Missing => "File does not exist.",
            Self::Special => {
                "File is character special device, block special device, FIFO, or socket."
            }
            Self::UnreadableFile | Self::UnreadableDirectory | Self::UnreadableSubdirectory => {
                "File/Directory is not readable."
            }
        }
    }
    /// What follows the source's absolute path in the warning: upstream's
    /// `local_format` ends an existing directory's path with a separator. A
    /// subdirectory is warned about by its joined name, before the walk
    /// marks it as a directory.
    pub fn path_suffix(self) -> &'static str {
        match self {
            Self::UnreadableDirectory => std::path::MAIN_SEPARATOR_STR,
            Self::Missing | Self::Special | Self::UnreadableFile | Self::UnreadableSubdirectory => {
                ""
            }
        }
    }
    fn warning_with_suffix(self, path: &Path, suffix: &str) -> Vec<u8> {
        [
            b"warning: Skipping file ".as_slice(),
            path.as_os_str().as_encoded_bytes(),
            suffix.as_bytes(),
            b". ",
            self.reason().as_bytes(),
        ]
        .concat()
    }
}
/// The warning upstream's `create_warning` builds for `source`, a path the
/// producer named, resolved against `cwd`: abspath drops a trailing
/// separator, which the file generator's recursive root warning retains.
pub fn source_skip_warning(cwd: &Path, source: &Path, skip: SourceSkip) -> Vec<u8> {
    let absolute = crate::local_path::absolute_path(cwd, source);
    let suffix = if ends_in_separator(&absolute) {
        ""
    } else if ends_in_separator(source) {
        std::path::MAIN_SEPARATOR_STR
    } else {
        skip.path_suffix()
    };
    skip.warning_with_suffix(&absolute, suffix)
}
fn ends_in_separator(path: &Path) -> bool {
    path.as_os_str()
        .as_encoded_bytes()
        .last()
        .is_some_and(|byte| *byte == b'/' || (cfg!(windows) && *byte == b'\\'))
}
/// What upstream's file generator decides about an upload source before it
/// queues the upload.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceInspection {
    /// The source may be queued: its size in bytes, after following links.
    Size(u64),
    /// The source may be queued, with its size, but upstream cannot read
    /// its mtime: it warns with [`INVALID_TIMESTAMP_WARNING`] first.
    InvalidTimestamp(u64),
    /// The source is skipped with a warning, for this reason.
    Skipped(SourceSkip),
}
/// Upstream's `triggers_warning` for an upload source, following links as
/// its file generator does: why the source is skipped, or the size it is
/// queued with and whether `_safely_get_file_stats` then reads its mtime.
/// The kind is checked before anything opens the source, so a FIFO with no
/// writer cannot block the check.
pub fn inspect_upload_source(path: &Path) -> SourceInspection {
    let Ok(metadata) = fs::metadata(path) else {
        return SourceInspection::Skipped(SourceSkip::Missing);
    };
    #[cfg(unix)]
    {
        use std::os::unix::fs::FileTypeExt;
        let kind = metadata.file_type();
        if kind.is_char_device() || kind.is_block_device() || kind.is_fifo() || kind.is_socket() {
            return SourceInspection::Skipped(SourceSkip::Special);
        }
    }
    let readable = if metadata.is_dir() {
        // `is_readable` lists a directory, which reads its first entries.
        fs::read_dir(path).is_ok_and(|mut entries| entries.next().is_none_or(|e| e.is_ok()))
    } else {
        fs::File::open(path).is_ok()
    };
    match (readable, metadata.is_dir()) {
        (true, _) if Modified::from_metadata(&metadata).is_none() => {
            SourceInspection::InvalidTimestamp(metadata.len())
        }
        (true, _) => SourceInspection::Size(metadata.len()),
        (false, true) => SourceInspection::Skipped(SourceSkip::UnreadableDirectory),
        (false, false) => SourceInspection::Skipped(SourceSkip::UnreadableFile),
    }
}
/// `str()` of the OSError upstream raises when it opens a single upload's
/// source that is a directory to read the body, with the errno the host's
/// open of that path reports ([`directory_open`]). The message is the C
/// library's `strerror`, which the native path shares with the embedded
/// interpreter. The path is the one `local_format` spelled,
/// `os.path.abspath(source) + os.sep`, so the root is `//`. `source` is
/// absolute, as the command made the operand.
pub fn directory_source_failure(source: &Path) -> Vec<u8> {
    let mut path = crate::local_path::absolute_path(Path::new(""), source).into_os_string();
    path.push(std::path::MAIN_SEPARATOR_STR);
    let code = directory_open::open_errno(&path);
    errno_error_text(
        code,
        &directory_open::strerror(code),
        path.as_encoded_bytes(),
    )
}

/// `str()` of the OSError upstream's `os.remove` of a moved upload's source
/// raises (`DeleteSourceFileSubscriber`), for `error`, the failed removal of
/// `source`. The path is `source` made absolute, as upstream's file
/// generator made it. On Windows the error is the one `DeleteFileW`
/// reported, which CPython names with its system message.
pub fn source_removal_failure(cwd: &Path, source: &Path, error: &io::Error) -> Vec<u8> {
    let path = crate::local_path::absolute_path(cwd, source);
    let path = path.as_os_str().as_encoded_bytes();
    #[cfg(windows)]
    if let Some(code) = error.raw_os_error() {
        // std spells the system message `<message>. (os error N)`, which
        // CPython spells without the period or the code.
        let message = error.to_string();
        let message = message.split(" (os error ").next().unwrap_or(&message);
        let mut text = format!("[WinError {code}] ").into_bytes();
        text.extend_from_slice(message.trim_end_matches(['.', ' ']).as_bytes());
        text.extend_from_slice(b": ");
        text.extend(crate::mime::repr(path));
        return text;
    }
    let code = error.raw_os_error().unwrap_or(libc::EIO);
    errno_error_text(code, &directory_open::strerror(code), path)
}

fn errno_error_text(code: i32, message: &[u8], path: &[u8]) -> Vec<u8> {
    let mut text = format!("[Errno {code}] ").into_bytes();
    text.extend_from_slice(message);
    text.extend_from_slice(b": ");
    text.extend(crate::mime::repr(path));
    text
}

/// The local side of a result line, spelled as awscli's `relative_path`
/// spells the absolute path: `./foo.txt` beside the working directory,
/// `sub/foo.txt` beneath it, `../x/foo.txt` beyond it. Like upstream, only
/// the directory is resolved, so a final `..` or `.` stays as spelled.
pub fn display_local_path(cwd: &Path, path: &Path) -> PathBuf {
    // `os.path.split` leaves an empty name after a trailing separator, which
    // upstream gives a directory source, so the whole path is the directory.
    if path.as_os_str().len() > 1 && ends_in_separator(path) {
        let directory = crate::local_path::absolute_path(cwd, path);
        let mut relative = relative_directory(cwd, &directory).into_os_string();
        relative.push(std::path::MAIN_SEPARATOR_STR);
        return relative.into();
    }
    if let Some((directory, name)) = split_dot_name(path) {
        let directory = crate::local_path::absolute_path(cwd, directory);
        let mut relative = relative_directory(cwd, &directory);
        relative.push(name);
        return relative;
    }
    let absolute = crate::local_path::absolute_path(cwd, path);
    let mut relative = relative_directory(cwd, absolute.parent().unwrap_or(&absolute));
    relative.push(absolute.file_name().unwrap_or_default());
    relative
}
fn split_dot_name(path: &Path) -> Option<(&Path, &str)> {
    let bytes = path.as_os_str().as_encoded_bytes();
    let name = [".", ".."].into_iter().find(|name| {
        bytes.strip_suffix(name.as_bytes()).is_some_and(|rest| {
            rest.last()
                .is_none_or(|&byte| std::path::is_separator(char::from(byte)))
        })
    })?;
    let directory = if name == "." {
        path
    } else {
        path.parent().unwrap_or(path)
    };
    if directory.as_os_str().is_empty() {
        return Some((Path::new("."), name));
    }
    Some((directory, name))
}
fn relative_directory(cwd: &Path, directory: &Path) -> PathBuf {
    let base = crate::local_path::absolute_path(Path::new("/"), cwd);
    let from: Vec<_> = base.components().collect();
    let to: Vec<_> = directory.components().collect();
    let common = from.iter().zip(&to).take_while(|(a, b)| a == b).count();
    let mut relative = PathBuf::new();
    for _ in common..from.len() {
        relative.push("..");
    }
    for part in &to[common..] {
        relative.push(part.as_os_str());
    }
    if relative.as_os_str().is_empty() {
        relative.push(".");
    }
    relative
}
pub fn normalize_local_directory_root(path: &Path) -> PathBuf {
    let mut root = path.as_os_str().to_os_string();
    if root.is_empty() {
        root.push(".");
    }
    if !root
        .as_encoded_bytes()
        .ends_with(std::path::MAIN_SEPARATOR_STR.as_bytes())
    {
        root.push(std::path::MAIN_SEPARATOR_STR);
    }
    root.into()
}
/// What botocore raises for an upload's key before any request: an empty key
/// fails parameter validation, and a key that is not UTF-8 fails the
/// serializer's percent-encoding. None when the key is sendable.
pub fn upload_key_refusal(key: &[u8]) -> Option<String> {
    if key.is_empty() {
        return Some(EMPTY_KEY_MESSAGE.into());
    }
    key_encode_refusal(key)
}
/// What botocore's serializer raises for a key or listing prefix that is not
/// UTF-8, before any request: the request's percent-encoding cannot encode
/// the surrogate escapes Python decoded its bytes to. None when the value is
/// UTF-8; an empty listing prefix is one.
pub fn key_encode_refusal(key: &[u8]) -> Option<String> {
    key_encode_error(key)
}
fn key_encode_error(key: &[u8]) -> Option<String> {
    let mut position = 0;
    let mut first = None;
    let mut run = 0;
    for chunk in key.utf8_chunks() {
        if first.is_some() && !chunk.valid().is_empty() {
            break;
        }
        position += chunk.valid().chars().count();
        if let Some(&byte) = chunk.invalid().first() {
            first.get_or_insert(byte);
        }
        run += chunk.invalid().len();
    }
    let byte = first?;
    let reason = "surrogates not allowed";
    Some(if run == 1 {
        let character = format!("'\\udc{byte:02x}'");
        format!("'utf-8' codec can't encode character {character} in position {position}: {reason}")
    } else {
        format!(
            "'utf-8' codec can't encode characters in position {position}-{}: {reason}",
            position + run - 1
        )
    })
}
const EMPTY_KEY_MESSAGE: &str = "Parameter validation failed:\n\
    Invalid length for parameter Key, value: 0, valid min length: 1";
fn expect_directory(path: &Path) -> io::Result<()> {
    match fs::metadata(path) {
        Ok(metadata) if metadata.is_dir() => Ok(()),
        Ok(_) => Err(io::Error::from(io::ErrorKind::NotADirectory)),
        Err(error) if error.kind() == io::ErrorKind::NotFound => {
            Err(io::Error::from(io::ErrorKind::NotADirectory))
        }
        Err(error) => Err(error),
    }
}
/// Bounds retries by path length, including an unlinked working-directory ancestor.
pub fn create_local_dir_path(path: &Path) -> io::Result<()> {
    if path.as_os_str().is_empty() {
        return Err(io::Error::from(io::ErrorKind::InvalidInput));
    }
    let ancestors: Vec<_> = path
        .ancestors()
        .filter(|p| !p.as_os_str().is_empty())
        .collect();
    let mut index = 0usize;
    let mut unresolved = None;
    for _ in 0..path.as_os_str().len().max(1) {
        match fs::create_dir(ancestors[index]) {
            Ok(()) => unresolved = None,
            Err(e) if e.kind() == io::ErrorKind::AlreadyExists => {
                expect_directory(ancestors[index])?;
            }
            Err(e) if e.kind() == io::ErrorKind::NotFound => {
                if unresolved == Some(index) || index + 1 == ancestors.len() {
                    return Err(e);
                }
                unresolved = Some(index);
                index += 1;
                continue;
            }
            Err(e) => return Err(e),
        }
        if index == 0 {
            return Ok(());
        }
        index -= 1;
    }
    Err(io::Error::from(io::ErrorKind::NotFound))
}
/// The stable name of a `create_local_dir_path` failure, from what
/// `mkdirat` reports. The stat of a component that already exists reports a
/// subset of the same errnos. A path std refuses before any call, an empty
/// one or one holding a NUL, is a bad path name.
pub fn create_dir_error_name(error: &io::Error) -> &'static str {
    #[cfg(unix)]
    if let Some(errno) = error.raw_os_error() {
        return match errno {
            libc::EACCES => crate::local_error::ACCESS_DENIED,
            libc::EPERM => crate::local_error::PERMISSION_DENIED,
            libc::EDQUOT => crate::local_error::DISK_QUOTA,
            libc::EEXIST => crate::local_error::PATH_ALREADY_EXISTS,
            libc::ELOOP => crate::local_error::SYM_LINK_LOOP,
            libc::EMLINK => crate::local_error::LINK_QUOTA_EXCEEDED,
            libc::ENAMETOOLONG => crate::local_error::NAME_TOO_LONG,
            libc::ENOENT | libc::ENOTCONN => crate::local_error::FILE_NOT_FOUND,
            libc::ENOMEM => crate::local_error::SYSTEM_RESOURCES,
            libc::ENOSPC => crate::local_error::NO_SPACE_LEFT,
            libc::ENOTDIR => crate::local_error::NOT_DIR,
            libc::EROFS => crate::local_error::READ_ONLY_FILE_SYSTEM,
            libc::EILSEQ => crate::local_error::BAD_PATH_NAME,
            _ => crate::local_error::UNEXPECTED,
        };
    }
    if error.raw_os_error().is_none() && error.kind() == io::ErrorKind::InvalidInput {
        return crate::local_error::BAD_PATH_NAME;
    }
    crate::cp::io_error_name(error)
}
pub fn build_recursive_destination_path(root: &Path, relative: &str) -> PathBuf {
    let mut path = root.as_os_str().to_os_string();
    path.push(relative.replace('/', std::path::MAIN_SEPARATOR_STR));
    path.into()
}
pub fn build_recursive_source_path(root: &Path, relative: &Path) -> PathBuf {
    let mut path = root.as_os_str().to_os_string();
    path.push(relative);
    path.into()
}
pub fn build_recursive_upload_key(prefix: &[u8], relative: &Path) -> Vec<u8> {
    let mut key = prefix.to_vec();
    key.extend(relative.as_os_str().as_encoded_bytes().iter().map(|&byte| {
        if cfg!(windows) && byte == b'\\' {
            b'/'
        } else {
            byte
        }
    }));
    key
}
/// An entry a recursive upload's walk keeps for upstream's sorted pass over a
/// directory: its name, and whether it is listed as a directory.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ListedName<'a> {
    /// The entry's name within its directory, as the OS encodes it.
    pub name: &'a [u8],
    /// Whether upstream lists it with a separator after the name: a
    /// directory, or a link to one.
    pub directory: bool,
}
/// Whether upstream's file generator takes `a` before `b` from one directory
/// (filegenerator.py `list_files`).
pub fn lists_before(a: ListedName<'_>, b: ListedName<'_>) -> bool {
    listing_order(a, b).is_lt()
}
/// The order upstream's file generator takes two entries of one directory
/// in. It sorts the names, a directory's with a separator after it, by code
/// point once that separator is `/` (`normalize_sort`). Python decodes a
/// POSIX name with surrogate escapes, so each byte outside a valid UTF-8
/// sequence sorts as U+DC80 through U+DCFF. Decoding a Windows name's WTF-8
/// the same way keeps each lone surrogate's place among the code points
/// around it.
pub fn listing_order(a: ListedName<'_>, b: ListedName<'_>) -> std::cmp::Ordering {
    sort_points(a).cmp(sort_points(b))
}
fn sort_points(listed: ListedName<'_>) -> impl Iterator<Item = u32> + '_ {
    python_code_points(listed.name).chain(listed.directory.then_some(u32::from('/')))
}
/// The code points of `name` as Python decodes an OS name: UTF-8, with each
/// byte outside a valid sequence escaped to U+DC80 through U+DCFF.
pub fn python_code_points(name: &[u8]) -> impl Iterator<Item = u32> + '_ {
    let escaped = |byte: &u8| 0xDC00 + u32::from(*byte);
    name.utf8_chunks().flat_map(move |chunk| {
        let valid = chunk.valid().chars().map(u32::from);
        valid.chain(chunk.invalid().iter().map(escaped))
    })
}
/// What a recursive upload's walk does with one entry.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UploadWalkStep {
    /// Descend it: a directory, or a link to one.
    Descend,
    /// Hand it to source inspection by its full path.
    Inspect,
    /// Skip it with a warning: a directory whose full path reaches the OS's
    /// limit on a path's length only with the separator.
    SkipDirectory,
}
/// What a recursive upload's walk does with the entry at `path`, decided by a
/// stat of its full path, the source root then the entry's relative path, as
/// upstream's `os.path.isdir` decides, so a link to an ancestor reaches the
/// OS's limit on links in one path and the walk ends. Upstream appends a
/// separator to the name of a directory, or a link to one, and checks the
/// joined path again before it descends, so the stat includes that
/// separator. A directory whose full path fits the OS's limit on a path's
/// length only without it fails upstream's second check, which warns that
/// the path with the separator does not exist. An entry whose stat fails, one
/// removed after its directory was read or one whose path passes the limit,
/// is inspected rather than descended, so the walk warns about it once, as
/// upstream does.
pub fn recursive_upload_walk_step(path: &Path) -> io::Result<UploadWalkStep> {
    let mut separated = path.as_os_str().to_os_string();
    separated.push(std::path::MAIN_SEPARATOR_STR);
    let metadata = match fs::metadata(&separated) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == io::ErrorKind::InvalidFilename => {
            return Ok(if fs::metadata(path)?.is_dir() {
                UploadWalkStep::SkipDirectory
            } else {
                UploadWalkStep::Inspect
            });
        }
        Err(error) => return Err(error),
    };
    Ok(if metadata.is_dir() {
        UploadWalkStep::Descend
    } else {
        UploadWalkStep::Inspect
    })
}
/// Fills an array from the operating system's random source.
#[cfg(target_os = "linux")]
pub fn random_bytes<const N: usize>() -> io::Result<[u8; N]> {
    let mut bytes = [0; N];
    let mut filled = 0;
    while filled < N {
        let rest = &mut bytes[filled..];
        // SAFETY: the kernel writes at most `rest.len()` bytes to the live
        // slice `rest` points at.
        let written = unsafe { libc::getrandom(rest.as_mut_ptr().cast(), rest.len(), 0) };
        match usize::try_from(written) {
            Ok(written) => filled += written,
            Err(_) => {
                let error = io::Error::last_os_error();
                if error.kind() != io::ErrorKind::Interrupted {
                    return Err(error);
                }
            }
        }
    }
    Ok(bytes)
}
/// Fills an array from the operating system's random source.
#[cfg(target_vendor = "apple")]
pub fn random_bytes<const N: usize>() -> io::Result<[u8; N]> {
    let mut bytes = [0; N];
    // SAFETY: arc4random_buf writes exactly `N` bytes to the live array and
    // cannot fail.
    unsafe { libc::arc4random_buf(bytes.as_mut_ptr().cast(), N) };
    Ok(bytes)
}
/// Fills an array from the operating system's random source.
#[cfg(all(unix, not(target_os = "linux"), not(target_vendor = "apple")))]
pub fn random_bytes<const N: usize>() -> io::Result<[u8; N]> {
    use io::Read;
    let mut bytes = [0; N];
    fs::File::open("/dev/urandom")?.read_exact(&mut bytes)?;
    Ok(bytes)
}
/// Fills an array from the operating system's random source.
#[cfg(windows)]
pub fn random_bytes<const N: usize>() -> io::Result<[u8; N]> {
    #[link(name = "bcrypt")]
    unsafe extern "system" {
        fn BCryptGenRandom(
            algorithm: *mut std::ffi::c_void,
            output: *mut u8,
            size: u32,
            flags: u32,
        ) -> i32;
    }
    let size = u32::try_from(N).map_err(|_| io::Error::from(io::ErrorKind::InvalidInput))?;
    let mut bytes = [0; N];
    const BCRYPT_USE_SYSTEM_PREFERRED_RNG: u32 = 2;
    // SAFETY: the system-preferred provider writes exactly size bytes to the live array.
    let status = unsafe {
        BCryptGenRandom(
            std::ptr::null_mut(),
            bytes.as_mut_ptr(),
            size,
            BCRYPT_USE_SYSTEM_PREFERRED_RNG,
        )
    };
    if status != 0 {
        return Err(io::Error::other(format!(
            "random generator failed: {status:#x}"
        )));
    }
    Ok(bytes)
}
/// A fresh id for a download's temp name, drawn from the operating system's
/// random source through this thread's batch (see [`random`]): seeing one id
/// says nothing about the next.
///
/// # Errors
/// Fails when the random source does, which fails that download.
pub fn temp_name_id() -> io::Result<u64> {
    random::draw(random_bytes::<{ random::BATCH_BYTES }>)
}
const TEMP_NAME_BYTES_MAX: usize = 255;
const TEMP_NAME_SUFFIX_DIGITS: usize = u64::BITS as usize / 4;
const _: () = assert!(1 + TEMP_NAME_SUFFIX_DIGITS < TEMP_NAME_BYTES_MAX);
const TEMP_NAME_KEPT_BYTES_MAX: usize = TEMP_NAME_BYTES_MAX - 1 - TEMP_NAME_SUFFIX_DIGITS;

/// Builds a download's temp path: the destination, a dot, and `id` as 16
/// lowercase hex digits. Callers draw a fresh `id` for every name from
/// `temp_name_id`, so seeing one temp name says nothing about the next. Upstream's
/// `get_temp_filename` truncates the destination's name so that it and the
/// suffix fit 255 characters; this counts bytes, which is what the file
/// system limits, and cuts the name at a character boundary, so any
/// destination name the file system holds downloads. The parent path is kept
/// as it is. Fails only when the path cannot be allocated.
pub fn make_download_temp_path(destination: &Path, id: u64) -> Result<PathBuf, TryReserveError> {
    let suffix = format!(".{id:016x}");
    debug_assert_eq!(suffix.len(), 1 + TEMP_NAME_SUFFIX_DIGITS);
    #[cfg(unix)]
    let path = {
        use std::os::unix::ffi::OsStringExt;
        let destination = destination.as_os_str().as_encoded_bytes();
        std::ffi::OsString::from_vec(temp_path_bytes(destination, suffix.as_bytes())?)
    };
    #[cfg(windows)]
    let path = {
        use std::os::windows::ffi::{OsStrExt, OsStringExt};
        let destination: Vec<u16> = destination.as_os_str().encode_wide().collect();
        std::ffi::OsString::from_wide(&temp_path_wide(&destination, suffix.as_bytes())?)
    };
    Ok(path.into())
}
#[cfg(unix)]
fn temp_path_bytes(destination: &[u8], suffix: &[u8]) -> Result<Vec<u8>, TryReserveError> {
    let name_start = destination
        .iter()
        .rposition(|&byte| std::path::is_separator(char::from(byte)))
        .map_or(0, |separator| separator + 1);
    let name = &destination[name_start..];
    let mut kept = name.len().min(TEMP_NAME_KEPT_BYTES_MAX);
    while kept > 0 && kept < name.len() && name[kept] & 0xc0 == 0x80 {
        kept -= 1;
    }
    let mut path = Vec::new();
    path.try_reserve_exact(name_start + kept + suffix.len())?;
    path.extend_from_slice(&destination[..name_start + kept]);
    path.extend_from_slice(suffix);
    debug_assert!(path.len() - name_start <= TEMP_NAME_BYTES_MAX);
    Ok(path)
}
#[cfg(any(windows, test))]
fn temp_path_wide(destination: &[u16], suffix: &[u8]) -> Result<Vec<u16>, TryReserveError> {
    let name_start = destination
        .iter()
        .rposition(|&unit| unit == u16::from(b'/') || unit == u16::from(b'\\'))
        .map_or(0, |separator| separator + 1);
    let (mut bytes, mut kept) = (0, 0);
    for decoded in char::decode_utf16(destination[name_start..].iter().copied()) {
        // An unpaired surrogate is one unit, three bytes in WTF-8.
        let (wtf8, units) = decoded.map_or((3, 1), |c| (c.len_utf8(), c.len_utf16()));
        if bytes + wtf8 > TEMP_NAME_KEPT_BYTES_MAX {
            break;
        }
        bytes += wtf8;
        kept += units;
    }
    let mut path = Vec::new();
    path.try_reserve_exact(name_start + kept + suffix.len())?;
    path.extend_from_slice(&destination[..name_start + kept]);
    path.extend(suffix.iter().map(|&byte| u16::from(byte)));
    Ok(path)
}
/// Whether `path` holds a NUL, which no file system represents: a listed
/// key can name one. No file system call receives such a path; each guarded
/// site fails or skips instead.
pub fn path_holds_nul(path: &Path) -> bool {
    path.as_os_str().as_encoded_bytes().contains(&0)
}
pub fn delete_file_best_effort(path: &Path) {
    if path_holds_nul(path) {
        return;
    }
    let _ = fs::remove_file(path);
}
pub fn timestamp_from_epoch_seconds(seconds: i64) -> SystemTime {
    if seconds < 0 {
        SystemTime::UNIX_EPOCH - Duration::from_secs(seconds.unsigned_abs())
    } else {
        SystemTime::UNIX_EPOCH + Duration::from_secs(seconds as u64)
    }
}
/// A listed object's time, None only when the listing carried none; a
/// pre-epoch time is kept.
pub fn timestamp_from_list_entry(present: bool, seconds: i64) -> Option<SystemTime> {
    present.then(|| timestamp_from_epoch_seconds(seconds))
}
/// Sets both the access and modification times to `seconds` past the epoch,
/// as upstream's `os.utime(filename, (desired_time, desired_time))` does.
/// POSIX sets them by path: the owner may set times on a file it cannot open,
/// such as one a umask of 0222 created read-only. The error is its stable
/// filesystem name.
#[cfg(unix)]
pub fn set_destination_mtime(path: &Path, seconds: i64) -> Result<(), &'static str> {
    use std::os::unix::ffi::OsStrExt;
    let path = std::ffi::CString::new(path.as_os_str().as_bytes())
        .map_err(|_| crate::local_error::BAD_PATH_NAME)?;
    let time = libc::timespec {
        tv_sec: seconds as _,
        tv_nsec: 0,
    };
    let times = [time, time];
    loop {
        // SAFETY: the path is NUL-terminated and both timespecs outlive the call.
        if unsafe { libc::utimensat(libc::AT_FDCWD, path.as_ptr(), times.as_ptr(), 0) } == 0 {
            return Ok(());
        }
        let errno = io::Error::last_os_error().raw_os_error();
        if errno != Some(libc::EINTR) {
            return Err(match errno {
                Some(libc::EACCES) => crate::local_error::ACCESS_DENIED,
                Some(libc::EPERM) => crate::local_error::PERMISSION_DENIED,
                Some(libc::EROFS) => crate::local_error::READ_ONLY_FILE_SYSTEM,
                _ => crate::local_error::UNEXPECTED,
            });
        }
    }
}
/// Sets both the access and modification times to `seconds` past the epoch,
/// as upstream's `os.utime(filename, (desired_time, desired_time))` does,
/// through a handle opened for writing, which grants the right to set them.
/// The error is its stable filesystem name.
#[cfg(windows)]
pub fn set_destination_mtime(path: &Path, seconds: i64) -> Result<(), &'static str> {
    let timestamp = timestamp_from_epoch_seconds(seconds);
    fs::OpenOptions::new()
        .write(true)
        .open(path)
        .and_then(|file| {
            file.set_times(
                fs::FileTimes::new()
                    .set_accessed(timestamp)
                    .set_modified(timestamp),
            )
        })
        .map_err(|error| crate::cp::io_error_name(&error))
}
mod commit;
mod directory_open;
mod links;
mod random;
pub use commit::{CommitFailure, complete_downloaded_temp_file, rename_error_text};
pub use links::LinkPolicy;

#[cfg(test)]
mod tests;
