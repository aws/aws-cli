//! Ordered parameter loading and modeled scalar conversion.
use crate::failure::{Failure, FailureKind};
use crate::{Argument, CliType, Namespace, Value};
use crate::{pyrepr, shorthand};
use std::collections::HashMap;
use std::ffi::{OsStr, OsString};
use std::io::Read;
use std::path::{Path, PathBuf};
/// Exclusive parameter-file byte bound: eight maximum-size argv strings
/// (8 * 128 KiB) give file inputs more room than argv while keeping each read
/// within 1 MiB. A file of this size or larger goes to Python.
pub const PARAMFILE_BYTES_MAX: usize = 1024 * 1024;
/// Expanded paths are bounded by two maximum-size arguments.
pub const EXPANDED_PATH_BYTES_MAX: usize = 2 * crate::ARG_LEN_MAX;
const INT_TEXT_LEN_MAX: usize = if crate::ARG_LEN_MAX > PARAMFILE_BYTES_MAX {
    crate::ARG_LEN_MAX
} else {
    PARAMFILE_BYTES_MAX
};
const CODEC_NAME_LEN_MAX: usize = 32;
const CODE_PAGE_UTF8: u32 = 65001;
/// The spellings `codecs.lookup` resolves to the utf_8 codec.
const UTF8_CODEC_NAMES: [&str; 7] = [
    "utf_8",
    "utf8",
    "u8",
    "utf",
    "utf8_ucs2",
    "utf8_ucs4",
    "cp65001",
];
const _: () = {
    assert!(PARAMFILE_BYTES_MAX == 8 * crate::ARG_LEN_MAX);
    assert!(EXPANDED_PATH_BYTES_MAX >= crate::ARG_LEN_MAX);
    assert!(EXPANDED_PATH_BYTES_MAX < PARAMFILE_BYTES_MAX);
    assert!(INT_TEXT_LEN_MAX >= crate::ARG_LEN_MAX);
    assert!(INT_TEXT_LEN_MAX >= PARAMFILE_BYTES_MAX);
    assert!(crate::SHORTHAND_INPUT_BYTES_MAX == PARAMFILE_BYTES_MAX);
    let mut i = 0;
    while i < UTF8_CODEC_NAMES.len() {
        assert!(2 * UTF8_CODEC_NAMES[i].len() <= CODEC_NAME_LEN_MAX);
        i += 1;
    }
};
/// CPython's `sys.int_info.default_max_str_digits`
/// (`_PY_LONG_DEFAULT_MAX_STR_DIGITS` in `Include/internal/pycore_long.h`).
/// `int()` rejects a valid decimal literal with more digits than this,
/// counting neither the sign, the surrounding whitespace nor underscores,
/// however small the value: `int("0" * 4300 + "5")` fails while
/// `int("0" * 4299 + "5")` is 5.
pub const PYTHON_INT_MAX_STR_DIGITS: usize = 4300;
/// Integer parsing failure preserves the native signed 64-bit policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ParseIntError {
    InvalidLiteral,
    /// A valid literal with more than `PYTHON_INT_MAX_STR_DIGITS` digits;
    /// the payload is its digit count.
    DigitLimit(usize),
    OutOfRange,
}
/// Python int syntax with the declared ASCII-only policy.
///
/// `int()` strips C's six whitespace characters from ASCII text, the
/// vertical tab among them, but not the separators U+001C to U+001F that
/// `str.strip()` also removes. Like CPython, it checks the whole literal's
/// syntax, then the digit limit, and only then converts, so an invalid
/// literal is reported as one however many digits it has, and the 64-bit
/// range applies only to a literal within the limit.
pub fn parse_int(text: &str) -> Result<i64, ParseIntError> {
    assert!(text.len() <= INT_TEXT_LEN_MAX);
    let body = text.trim_matches([' ', '\t', '\n', '\u{b}', '\u{c}', '\r']);
    let (negative, digits) = if let Some(v) = body.strip_prefix('-') {
        (true, v)
    } else {
        (false, body.strip_prefix('+').unwrap_or(body))
    };
    let count = literal_digits(digits).ok_or(ParseIntError::InvalidLiteral)?;
    if count > PYTHON_INT_MAX_STR_DIGITS {
        return Err(ParseIntError::DigitLimit(count));
    }
    let mut value = 0i64;
    for c in digits.bytes().filter(u8::is_ascii_digit) {
        value = value
            .checked_mul(10)
            .and_then(|v| v.checked_sub(i64::from(c - b'0')))
            .ok_or(ParseIntError::OutOfRange)?;
    }
    if negative {
        Ok(value)
    } else {
        value.checked_neg().ok_or(ParseIntError::OutOfRange)
    }
}
/// `int()` of an argv value, as a failure when it fails. A value that is not
/// Unicode decodes to surrogates, which are neither digits nor whitespace,
/// so it is an invalid literal however long it is.
pub fn parse_int_os(text: &OsStr) -> Result<i64, Failure> {
    match text.to_str() {
        Some(text) => parse_int(text).map_err(|error| Failure::integer(text, error)),
        None => Err(Failure::new(FailureKind::InvalidInteger(
            text.to_os_string(),
        ))),
    }
}
fn literal_digits(digits: &str) -> Option<usize> {
    if digits.is_empty() || digits.starts_with('_') || digits.ends_with('_') {
        return None;
    }
    let mut count = 0;
    let mut underscore = false;
    for c in digits.bytes() {
        if c == b'_' {
            if underscore {
                return None;
            }
            underscore = true;
            continue;
        }
        underscore = false;
        if !c.is_ascii_digit() {
            return None;
        }
        count += 1;
    }
    Some(count)
}
/// File classification obtained before any content read.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FileKind {
    File,
    Directory,
    Stream,
}
/// Parameter-file I/O seam; stream detection must never open a file.
pub trait Paramfiles {
    fn kind(&self, path: &Path) -> std::io::Result<FileKind>;
    fn read(&self, path: &Path, limit: usize) -> std::io::Result<Vec<u8>>;
}
/// Filesystem-backed parameter reads.
#[derive(Debug, Default, Clone, Copy)]
pub struct FsParamfiles;
impl Paramfiles for FsParamfiles {
    fn kind(&self, path: &Path) -> std::io::Result<FileKind> {
        let m = std::fs::metadata(path)?;
        Ok(if m.is_file() {
            FileKind::File
        } else if m.is_dir() {
            FileKind::Directory
        } else {
            FileKind::Stream
        })
    }
    fn read(&self, path: &Path, limit: usize) -> std::io::Result<Vec<u8>> {
        let file = std::fs::File::open(path)?;
        let mut bytes = Vec::new();
        file.take(limit as u64 + 1).read_to_end(&mut bytes)?;
        Ok(bytes)
    }
}
/// Inputs are injected; parsing never reads process-global environment variables.
pub struct Environment<'a> {
    pub directory: &'a Path,
    /// Operating-system values: a value that is not Unicode still expands
    /// into a path.
    pub variables: &'a HashMap<String, OsString>,
    pub files: &'a dyn Paramfiles,
    pub preferred_encoding: PreferredEncoding,
}

/// The source Python consults when no explicit file codec is configured.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PreferredEncoding {
    Locale,
    AnsiCodePage(u32),
}

/// Read host codec policy once when constructing the invocation environment.
pub fn host_preferred_encoding() -> PreferredEncoding {
    host_encoding::preferred()
}
impl std::fmt::Debug for Environment<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Environment")
            .field("directory", &self.directory)
            .field("variables", &self.variables)
            .finish_non_exhaustive()
    }
}
/// A value stopped conversion, retaining its namespace destination.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnpackError {
    pub dest: String,
    pub failure: Option<Failure>,
}
/// Convert in namespace order; raw values remain untouched.
pub fn unpack(
    table: &[Argument],
    namespace: &Namespace,
    environment: &Environment<'_>,
) -> Result<Namespace, UnpackError> {
    let mut values = Namespace::default();
    for entry in &namespace.entries {
        let arg = table
            .iter()
            .find(|a| Argument::new(a.name).matches_dest(&entry.dest));
        let mut value = entry.value.clone();
        if value.contains_os_string()
            && !arg.is_some_and(|argument| {
                argument.positional
                    && argument.name == "paths"
                    && argument.nargs == Some(crate::Nargs::Count(2))
                    && argument.cli_type.is_none()
            })
            && !os_integer_fails_as_int_does(arg, &value)
            && !os_listing_value_keeps_its_bytes(arg, &value)
        {
            return Err(UnpackError {
                dest: entry.dest.clone(),
                failure: None,
            });
        }
        let loaded = if let Some(uri) = paramfile_uri(&value) {
            load(arg, uri, environment)
        } else {
            Ok(value.clone())
        };
        value = loaded.map_err(|failure| UnpackError {
            dest: entry.dest.clone(),
            failure,
        })?;
        value = convert(arg, value).map_err(|failure| UnpackError {
            dest: entry.dest.clone(),
            failure,
        })?;
        values.put(&entry.dest, value, entry.explicit);
    }
    Ok(values)
}
fn os_integer_fails_as_int_does(argument: Option<&Argument>, value: &Value) -> bool {
    let Value::OsString(text) = value else {
        return false;
    };
    let bytes = text.as_encoded_bytes();
    argument.is_some_and(|a| a.cli_type == Some(CliType::Integer) && a.nargs.is_none())
        && !bytes.starts_with(b"file://")
        && !bytes.starts_with(b"fileb://")
}
fn os_listing_value_keeps_its_bytes(argument: Option<&Argument>, value: &Value) -> bool {
    let Value::OsString(text) = value else {
        return false;
    };
    let bytes = text.as_encoded_bytes();
    argument.is_some_and(|a| {
        a.cli_type.is_none()
            && match (a.positional, a.name) {
                (true, "paths") => a.nargs == Some(crate::Nargs::Optional),
                (false, "bucket-name-prefix" | "bucket-region") => a.nargs.is_none(),
                _ => false,
            }
    }) && !bytes.starts_with(b"file://")
        && !bytes.starts_with(b"fileb://")
}
fn paramfile_uri(value: &Value) -> Option<&str> {
    let text = match value {
        Value::String(s) => s.as_str(),
        Value::Array(v) if v.len() == 1 => v[0].as_str()?,
        _ => return None,
    };
    if text.starts_with("file://") || text.starts_with("fileb://") {
        Some(text)
    } else {
        None
    }
}
fn convert(argument: Option<&Argument>, value: Value) -> Result<Value, Option<Failure>> {
    let bytes = matches!(value, Value::Bytes(_));
    if bytes && !argument.is_some_and(|a| a.cli_type == Some(CliType::Blob) && a.nargs.is_none()) {
        return Err(None);
    }
    let Some(arg) = argument else {
        return Ok(value);
    };
    if arg.nargs.is_some() || value.is_null() {
        return Ok(value);
    }
    if let (Some(CliType::Integer), Value::OsString(text)) = (arg.cli_type, &value) {
        return parse_int_os(text).map(Value::from).map_err(Some);
    }
    let Value::String(text) = &value else {
        return Ok(value);
    };
    match arg.cli_type {
        Some(CliType::Integer) => parse_int(text)
            .map(Value::from)
            .map_err(|e| Some(Failure::integer(text, e))),
        Some(CliType::Map) => convert_map(arg, text),
        _ => Ok(value),
    }
}
fn convert_map(arg: &Argument, text: &str) -> Result<Value, Option<Failure>> {
    let body = shorthand::lstrip(text);
    if body.starts_with('{') {
        return convert_json(arg, text);
    }
    if body.starts_with('[') {
        return Err(Some(Failure::new(FailureKind::NotJsonObject {
            name: arg.spelling(),
            value: text.into(),
        })));
    }
    convert_shorthand(arg, text)
}
fn convert_shorthand(arg: &Argument, text: &str) -> Result<Value, Option<Failure>> {
    let parsed = shorthand::parse(text.as_bytes()).map_err(|e| match e {
        shorthand::ParseError::Syntax(message) => Some(Failure::new(FailureKind::Shorthand {
            name: arg.spelling(),
            text: message,
        })),
        _ => None,
    })?;
    let mut report = String::new();
    if let Value::Object(pairs) = &parsed {
        for (key, value) in pairs {
            if !value.is_string() {
                let repr = pyrepr::value(value, false);
                write_schema_line(&mut report, key, &repr, type_name(value));
            }
        }
    }
    finish_map(report, parsed)
}
fn convert_json(arg: &Argument, text: &str) -> Result<Value, Option<Failure>> {
    let parsed = crate::json::parse(text.as_bytes()).map_err(|e| match e {
        crate::json::JsonError::TooDeep | crate::json::JsonError::TooLong => None,
        _ => Some(Failure::new(FailureKind::InvalidJson {
            name: arg.spelling(),
            decoder_text: e.describe(text),
            value: text.into(),
        })),
    })?;
    let crate::json::JsonValue::Object(pairs) = parsed else {
        return Err(None);
    };
    let mut out = crate::json::Object::new();
    let mut report = String::new();
    for (key, value) in pairs {
        if let crate::json::JsonValue::String(value) = value {
            out.insert(key, Value::String(value));
        } else {
            write_schema_line(&mut report, &key, &value.repr(), value.type_name());
        }
    }
    finish_map(report, Value::Object(out))
}
fn finish_map(report: String, pairs: Value) -> Result<Value, Option<Failure>> {
    if report.is_empty() {
        return Ok(pairs);
    }
    Err(Some(Failure::new(FailureKind::SchemaValidation { report })))
}
fn write_schema_line(report: &mut String, key: &str, repr: &str, type_name: &str) {
    if !report.is_empty() {
        report.push('\n');
    }
    report.push_str(&format!(
        "Invalid type for parameter {key}, value: {repr}, type: <class '{type_name}'>, valid \
         types: <class 'str'>"
    ));
}
fn type_name(value: &Value) -> &'static str {
    match value {
        Value::Null => "NoneType",
        Value::Bool(_) => "bool",
        Value::String(_) | Value::OsString(_) => "str",
        Value::Bytes(_) => "bytes",
        Value::Array(_) => "list",
        Value::Object(_) => "dict",
        Value::Number(n) => {
            if n.to_string().contains(['.', 'e', 'E']) {
                "float"
            } else {
                "int"
            }
        }
    }
}
#[derive(Debug, Clone, Copy)]
struct ParamfileScheme<'a> {
    binary: bool,
    path: &'a str,
}
fn paramfile_scheme(uri: &str) -> ParamfileScheme<'_> {
    if let Some(path) = uri.strip_prefix("fileb://") {
        return ParamfileScheme { binary: true, path };
    }
    assert!(uri.starts_with("file://"));
    ParamfileScheme {
        binary: false,
        path: &uri["file://".len()..],
    }
}
fn load(
    argument: Option<&Argument>,
    uri: &str,
    env: &Environment<'_>,
) -> Result<Value, Option<Failure>> {
    let Some(arg) = argument else {
        return Err(None);
    };
    let scheme = paramfile_scheme(uri);
    let path = expand_path(scheme.path, env.variables).ok_or(None)?;
    if !scheme.binary && !text_encoding_is_utf8_with(env.variables, env.preferred_encoding) {
        return Err(None);
    }
    if path.is_empty() {
        return Err(read_failure(
            arg,
            uri,
            &path,
            std::io::Error::from_raw_os_error(2),
        ));
    }
    let full = env.directory.join(&path);
    if paramfile_is_stream(env, &full) {
        return Err(None);
    }
    let bytes = env
        .files
        .read(&full, PARAMFILE_BYTES_MAX)
        .map_err(|e| read_failure(arg, uri, &path, e))?;
    if bytes.len() >= PARAMFILE_BYTES_MAX {
        return Err(None);
    }
    if scheme.binary {
        return Ok(Value::Bytes(bytes));
    }
    let text = String::from_utf8(bytes).map_err(|_| {
        Some(Failure::new(FailureKind::ParamfileDecode {
            name: arg.spelling(),
            path: python_text(&path),
        }))
    })?;
    Ok(translate_newlines(&text).into())
}
fn paramfile_is_stream(env: &Environment<'_>, path: &Path) -> bool {
    env.files.kind(path).ok() == Some(FileKind::Stream)
}
/// Text mode's universal newlines on read: `\r\n` and a lone `\r` become
/// `\n`.
fn translate_newlines(text: &str) -> String {
    assert!(text.len() <= PARAMFILE_BYTES_MAX);
    text.replace("\r\n", "\n").replace('\r', "\n")
}
fn read_failure(arg: &Argument, uri: &str, path: &OsStr, error: std::io::Error) -> Option<Failure> {
    #[cfg(not(windows))]
    let errno = error.raw_os_error()?;
    #[cfg(windows)]
    let errno = windows::errno(&error)?;
    let text = match errno {
        1 => "Operation not permitted",
        2 => "No such file or directory",
        11 => "Resource temporarily unavailable",
        13 => "Permission denied",
        20 => "Not a directory",
        21 => "Is a directory",
        23 => "Too many open files in system",
        26 => "Text file busy",
        _ => return None,
    };
    Some(Failure::new(FailureKind::ParamfileLoad {
        name: arg.spelling(),
        uri: uri.into(),
        errno_text: format!("[Errno {errno}] {text}: {}", pyrepr::os(path)),
    }))
}
/// The path as Python's stderr writes the str it decoded with surrogate
/// escapes: each undecodable byte becomes its `\udcXX` backslash escape.
fn python_text(path: &OsStr) -> String {
    if let Some(text) = path.to_str() {
        return text.into();
    }
    let mut output = String::new();
    for chunk in path.as_encoded_bytes().utf8_chunks() {
        output.push_str(chunk.valid());
        for byte in chunk.invalid() {
            output.push_str(&format!("\\u{:04x}", 0xdc00 + u16::from(*byte)));
        }
    }
    output
}

fn expand_path(path: &str, env: &HashMap<String, OsString>) -> Option<OsString> {
    #[cfg(windows)]
    return windows::expand(path, env).map(OsString::from);
    #[cfg(not(windows))]
    {
        use std::os::unix::ffi::OsStringExt;
        let expanded = expand_vars(&expand_user(path.as_bytes(), env)?, env)?;
        Some(OsString::from_vec(expanded))
    }
}
/// posixpath.expanduser over the path's bytes, without consulting the
/// password database: HOME's bytes replace a leading `~`.
pub fn expand_user(path: &[u8], env: &HashMap<String, OsString>) -> Option<Vec<u8>> {
    if path.len() > EXPANDED_PATH_BYTES_MAX {
        return None;
    }
    if !path.starts_with(b"~") {
        return Some(path.to_vec());
    }
    let end = path.iter().position(|c| *c == b'/').unwrap_or(path.len());
    if end != 1 {
        return None;
    }
    let mut base = env.get("HOME")?.as_encoded_bytes();
    while let [rest @ .., b'/'] = base {
        base = rest;
    }
    let joined = [base, &path[end..]].concat();
    if joined.len() > EXPANDED_PATH_BYTES_MAX {
        None
    } else if joined.is_empty() {
        Some(b"/".to_vec())
    } else {
        Some(joined)
    }
}
/// Expand ASCII variables once over the path's bytes, preserving references
/// to unset variables; a value is substituted as its operating-system bytes.
pub fn expand_vars(path: &[u8], env: &HashMap<String, OsString>) -> Option<Vec<u8>> {
    if path.len() > EXPANDED_PATH_BYTES_MAX {
        return None;
    }
    let mut output = Vec::new();
    let mut index = 0;
    while index < path.len() {
        let rest = &path[index..];
        let variable = if let Some(tail) = rest.strip_prefix(b"${") {
            tail.iter()
                .position(|c| *c == b'}')
                .map(|end| (&tail[..end], end + 3))
        } else if let Some(tail) = rest.strip_prefix(b"$") {
            let len = tail
                .iter()
                .take_while(|c| c.is_ascii_alphanumeric() || **c == b'_')
                .count();
            (len != 0).then(|| (&tail[..len], len + 1))
        } else {
            None
        };
        if let Some((name, len)) = variable {
            let value = std::str::from_utf8(name)
                .ok()
                .and_then(|name| env.get(name));
            output.extend_from_slice(value.map_or(&rest[..len], |v| v.as_encoded_bytes()));
            index += len;
        } else {
            output.push(rest[0]);
            index += 1;
        }
        if output.len() > EXPANDED_PATH_BYTES_MAX {
            return None;
        }
    }
    Some(output)
}
/// Whether compat.getpreferredencoding selects a supported UTF-8 alias.
pub fn text_encoding_is_utf8(env: &HashMap<String, OsString>) -> bool {
    text_encoding_is_utf8_with(env, PreferredEncoding::Locale)
}

/// The gate reads Unicode views. A codec name that is not Unicode is one
/// Python's codec lookup cannot encode, so its failure is Python's to
/// report. A locale value that is not Unicode is skipped: no such locale
/// loads, so the real CLI keeps the C locale and decodes UTF-8.
pub fn text_encoding_is_utf8_with(
    env: &HashMap<String, OsString>,
    preferred: PreferredEncoding,
) -> bool {
    if let Some(name) = env.get("AWS_CLI_FILE_ENCODING") {
        return name.to_str().is_some_and(utf8_codec);
    }
    if let PreferredEncoding::AnsiCodePage(page) = preferred {
        return page == CODE_PAGE_UTF8;
    }
    let locale = ["LC_ALL", "LC_CTYPE", "LANG"]
        .into_iter()
        .filter_map(|k| env.get(k)?.to_str())
        .find(|v| !v.is_empty())
        .unwrap_or("C");
    if matches!(locale, "C" | "POSIX") {
        return true;
    }
    let Some((_, codeset)) = locale.split_once('.') else {
        return false;
    };
    utf8_codec(codeset.split('@').next().unwrap_or(codeset))
}
fn utf8_codec(name: &str) -> bool {
    let mut normalized = String::new();
    let mut pending = false;
    for c in name.bytes() {
        if !c.is_ascii_alphanumeric() && c != b'.' {
            pending = true;
            continue;
        }
        if pending && !normalized.is_empty() {
            normalized.push('_');
        }
        pending = false;
        normalized.push(char::from(c.to_ascii_lowercase()));
        if normalized.len() > CODEC_NAME_LEN_MAX {
            return false;
        }
    }
    UTF8_CODEC_NAMES.contains(&normalized.as_str())
}
/// Build a process-backed environment without changing any variables. Values
/// keep their operating-system form; a name that is not Unicode is skipped,
/// as the CLI's environment snapshot skips it.
pub fn process_variables() -> HashMap<String, OsString> {
    std::env::vars_os()
        .filter_map(|(name, value)| Some((name.into_string().ok()?, value)))
        .collect()
}
/// Current directory resolution for tools using the filesystem adapter.
pub fn current_directory() -> std::io::Result<PathBuf> {
    std::env::current_dir()
}
#[cfg(test)]
mod tests;

#[cfg(any(windows, test))]
mod windows;

#[allow(
    unsafe_code,
    reason = "GetACP is the sole host probe and takes no pointers"
)]
mod host_encoding;
