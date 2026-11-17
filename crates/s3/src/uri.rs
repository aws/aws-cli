//! S3 URI parsing, bucket admission, and byte-preserving request paths.
//!
//! The parsers read an operand's bytes, so a key or prefix keeps bytes
//! that are not UTF-8: botocore cannot encode those into a request, which
//! the commands report natively (`transfer::key_encode_refusal`).
//! A bucket that is not UTF-8 is no bucket `supports_native_bucket` admits,
//! so its operand stays Python's.

/// Why `parse_s3_uri` refused a single-object `s3://bucket/key` URI.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum S3UriParseError {
    NotS3Uri,
    InvalidS3UriScheme,
    MissingS3Bucket,
    MissingS3ObjectKey,
    /// The bucket is not UTF-8, so no native request can name it.
    BucketNotUtf8,
}
impl From<S3PrefixUriParseError> for S3UriParseError {
    fn from(error: S3PrefixUriParseError) -> Self {
        match error {
            S3PrefixUriParseError::NotS3Uri => Self::NotS3Uri,
            S3PrefixUriParseError::InvalidS3UriScheme => Self::InvalidS3UriScheme,
            S3PrefixUriParseError::MissingS3Bucket => Self::MissingS3Bucket,
            S3PrefixUriParseError::BucketNotUtf8 => Self::BucketNotUtf8,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct S3Uri<'a> {
    pub bucket: &'a str,
    pub key: &'a [u8],
}
/// Why `parse_s3_prefix_uri` refused a recursive `s3://bucket[/prefix]` URI.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum S3PrefixUriParseError {
    NotS3Uri,
    InvalidS3UriScheme,
    MissingS3Bucket,
    /// The bucket is not UTF-8, so no native request can name it.
    BucketNotUtf8,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct S3PrefixUri<'a> {
    pub bucket: &'a str,
    pub prefix: &'a [u8],
}

/// Why `parse_s3_list_target` refused an `s3 ls` target. A value that is no
/// S3 URI is a plain `bucket[/prefix]` path there, so there is no `NotS3Uri`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum S3ListTargetParseError {
    InvalidS3UriScheme,
    MissingS3Bucket,
    /// The bucket is not UTF-8, so no native request can name it.
    BucketNotUtf8,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct S3ListTarget<'a> {
    pub original: &'a [u8],
    pub bucket: Option<&'a str>,
    pub prefix: &'a [u8],
    pub has_prefix: bool,
}

pub fn supports_native_bucket(bucket: &str) -> bool {
    const SUFFIXES: [&str; 6] = [
        "-s3alias",
        "--ol-s3",
        ".mrap",
        "--x-s3",
        "--table-s3",
        "--op-s3",
    ];
    !bucket.is_empty()
        && bucket.len() <= 255
        && bucket
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b".-_".contains(&b))
        && !SUFFIXES.iter().any(|suffix| bucket.ends_with(suffix))
}

/// A single-object URI is a prefix URI with a nonempty key.
pub fn parse_s3_uri(value: &[u8]) -> Result<S3Uri<'_>, S3UriParseError> {
    let parsed = parse_s3_prefix_uri(value)?;
    if parsed.prefix.is_empty() {
        return Err(S3UriParseError::MissingS3ObjectKey);
    }
    Ok(S3Uri {
        bucket: parsed.bucket,
        key: parsed.prefix,
    })
}

pub fn parse_s3_prefix_uri(value: &[u8]) -> Result<S3PrefixUri<'_>, S3PrefixUriParseError> {
    if !value.starts_with(b"s3:") {
        return Err(S3PrefixUriParseError::NotS3Uri);
    }
    let rest = value
        .strip_prefix(b"s3://")
        .ok_or(S3PrefixUriParseError::InvalidS3UriScheme)?;
    let (bucket, prefix) = split_bucket(rest);
    if bucket.is_empty() {
        return Err(S3PrefixUriParseError::MissingS3Bucket);
    }
    let bucket = std::str::from_utf8(bucket).map_err(|_| S3PrefixUriParseError::BucketNotUtf8)?;
    Ok(S3PrefixUri { bucket, prefix })
}

/// Parses the two target spellings `aws s3 ls` accepts: an S3 URI or a
/// plain `bucket[/prefix]` path. The bucket and prefix borrow the argument,
/// and `original` keeps its spelling.
pub fn parse_s3_list_target(
    value: Option<&[u8]>,
) -> Result<S3ListTarget<'_>, S3ListTargetParseError> {
    let original = value.unwrap_or(b"s3://");
    let rest = if let Some(rest) = original.strip_prefix(b"s3://") {
        rest
    } else {
        if original.starts_with(b"s3:") || original.windows(3).any(|v| v == b"://") {
            return Err(S3ListTargetParseError::InvalidS3UriScheme);
        }
        original
    };
    if rest.is_empty() {
        return Ok(S3ListTarget {
            original,
            bucket: None,
            prefix: b"",
            has_prefix: false,
        });
    }
    let (bucket, prefix) = split_bucket(rest);
    if bucket.is_empty() {
        return Err(S3ListTargetParseError::MissingS3Bucket);
    }
    let bucket = std::str::from_utf8(bucket).map_err(|_| S3ListTargetParseError::BucketNotUtf8)?;
    Ok(S3ListTarget {
        original,
        bucket: Some(bucket),
        prefix,
        has_prefix: !prefix.is_empty(),
    })
}

fn split_bucket(rest: &[u8]) -> (&[u8], &[u8]) {
    match rest.iter().position(|byte| *byte == b'/') {
        Some(slash) => (&rest[..slash], &rest[slash + 1..]),
        None => (rest, b""),
    }
}

pub fn normalize_recursive_s3_prefix(prefix: &[u8]) -> Vec<u8> {
    if prefix.is_empty() || prefix.ends_with(b"/") {
        prefix.into()
    } else {
        [prefix, b"/"].concat()
    }
}

pub fn encode_s3_request_path_key(key: &str) -> String {
    encode_s3_request_path_key_bytes(key.as_bytes())
}

pub(crate) fn encode_s3_request_path_key_bytes(key: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    let mut encoded = String::with_capacity(key.len());
    for &byte in key {
        if byte.is_ascii_alphanumeric() || b"-_.~/".contains(&byte) {
            encoded.push(char::from(byte));
        } else {
            encoded.push('%');
            encoded.push(char::from(HEX[usize::from(byte >> 4)]));
            encoded.push(char::from(HEX[usize::from(byte & 15)]));
        }
    }
    encoded
}

/// Whether a key's path, appended to a download root, resolves above that
/// root. AWS CLI v2 decides this with `os.path.normpath`, which follows the
/// host's separators, so a key such as `..\file.txt` escapes on Windows and
/// names an ordinary file on POSIX. Upstream flags only a normalized path
/// that starts with `..` and a separator, so a key that normalizes to a bare
/// `..` is not flagged; see `relative_key_names_root_parent`.
pub fn relative_key_escapes_root(relative_key: &str) -> bool {
    relative_key_escapes_root_with(relative_key, cfg!(windows))
}

/// Whether a key's path, appended to a download root, normalizes to the
/// root's parent itself: a bare `..`, which `relative_key_escapes_root`
/// leaves unflagged as upstream does. Upstream's download goes ahead and
/// fails on that destination after the GET.
pub fn relative_key_names_root_parent(relative_key: &str) -> bool {
    relative_key_names_root_parent_with(relative_key, cfg!(windows))
}

fn relative_key_escapes_root_with(relative_key: &str, windows: bool) -> bool {
    let normalized = NormalizedKey::new(relative_key, windows);
    normalized.parents > 0 && normalized.parents + normalized.depth > 1
}

fn relative_key_names_root_parent_with(relative_key: &str, windows: bool) -> bool {
    let normalized = NormalizedKey::new(relative_key, windows);
    normalized.parents == 1 && normalized.depth == 0
}

/// A relative key as `os.path.normpath` leaves it: `parents` `..`
/// components followed by `depth` named ones. Windows collapses only
/// segments that are exactly `.` or `..`, as POSIX does.
struct NormalizedKey {
    parents: usize,
    depth: usize,
}
impl NormalizedKey {
    fn new(relative_key: &str, windows: bool) -> Self {
        let mut normalized = Self {
            parents: 0,
            depth: 0,
        };
        for part in relative_key.split(|value| value == '/' || (windows && value == '\\')) {
            match part {
                "" | "." => {}
                ".." if normalized.depth == 0 => normalized.parents += 1,
                ".." => normalized.depth -= 1,
                _ => normalized.depth += 1,
            }
        }
        normalized
    }
}

#[cfg(test)]
mod tests;
