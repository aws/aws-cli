//! Command-scoped MIME guessing with CPython's file and suffix policies.

mod defaults;
mod errors;
mod printable;
#[cfg(windows)]
mod registry;
mod text;

pub(crate) use text::repr;

use std::collections::HashMap;
use std::fmt;
use std::fs::{self, File};
use std::io::{self, Read};
use std::path::Path;

/// CPython's ordered list, including the repeated Apache entry.
pub const KNOWN_FILES: &[&str] = &[
    "/etc/mime.types",
    "/etc/httpd/mime.types",
    "/etc/httpd/conf/mime.types",
    "/etc/apache/mime.types",
    "/etc/apache2/mime.types",
    "/usr/local/etc/httpd/conf/mime.types",
    "/usr/local/lib/netscape/mime.types",
    "/usr/local/etc/httpd/conf/mime.types",
    "/usr/local/etc/mime.types",
];

const MIME_TYPES_BYTES_MAX: usize = 16 * 1024 * 1024;

/// The exception `mimetypes.init` raised, as `str()` renders it, with any
/// raw filename bytes kept. Upstream's `guess_content_type` does not catch
/// it, so every guess raises it again: `guess` returns it as the error of
/// its `Result<Option<&[u8]>, GuessError>`. An allocation failure is not a
/// `GuessError`; it aborts instead.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GuessError(Vec<u8>);

impl GuessError {
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
}

impl fmt::Display for GuessError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&String::from_utf8_lossy(&self.0))
    }
}

impl std::error::Error for GuessError {}

/// Immutable after loading; a recursive command shares it without a lookup lock.
#[derive(Debug, Default)]
pub struct Database {
    added: HashMap<Vec<u8>, Vec<u8>>,
    failure: Option<GuessError>,
}

impl Database {
    /// Load the native registry, then each of CPython's standard MIME files.
    pub fn load() -> Self {
        let mut database = Self::default();
        #[cfg(windows)]
        registry::read(&mut database);
        for file in KNOWN_FILES {
            database.add_file(Path::new(file));
        }
        database
    }

    /// Load an explicit ordered collection of MIME files without consulting the registry.
    pub fn from_files(files: impl IntoIterator<Item = impl AsRef<Path>>) -> Self {
        let mut database = Self::default();
        for file in files {
            database.add_file(file.as_ref());
        }
        database
    }

    /// The initial load error takes precedence over every later filename guess.
    pub fn upload_failure(&self) -> Option<&GuessError> {
        self.failure.as_ref()
    }

    /// `guess_content_type` for the source at `path`, spelled as the command
    /// was given it: what loading raised, or the type of the path's final
    /// component. Upstream's `guess_type` also parses a path that starts with
    /// exactly `//` as a URL and raises for a malformed netloc, such as
    /// `//[foo/x.txt`; native guesses that path's type instead.
    pub fn guess(&self, source: &Path) -> Result<Option<&[u8]>, GuessError> {
        if let Some(failure) = &self.failure {
            return Err(failure.clone());
        }
        Ok(self.name_type(crate::local_path::file_name(source.as_os_str())))
    }

    /// Add a case-preserving mapping; lookups lowercase as CPython's strict table does.
    pub fn add(&mut self, extension: &[u8], mime_type: &[u8]) {
        if !mime_type.is_empty() {
            self.added.insert(extension.to_vec(), mime_type.to_vec());
        }
    }

    fn add_file(&mut self, source: &Path) {
        if self.failure.is_some() || !fs::metadata(source).is_ok_and(|m| m.is_file()) {
            return;
        }
        let mut file = match File::open(source) {
            Ok(file) => file.take((MIME_TYPES_BYTES_MAX + 1) as u64),
            Err(error) => {
                self.failure = Some(os_error(&error, Some(source)));
                return;
            }
        };
        let mut bytes = Vec::new();
        if let Err(error) = file.read_to_end(&mut bytes) {
            self.failure = Some(os_error(&error, None));
        } else if bytes.len() > MIME_TYPES_BYTES_MAX {
            self.failure = Some(errors::from_errno(libc::EFBIG, None));
        } else {
            self.read_types(&bytes);
        }
    }

    fn read_types(&mut self, bytes: &[u8]) {
        for line in bytes.split(|byte| matches!(byte, b'\r' | b'\n')) {
            let mut words = text::Words::new(line);
            let Some(mime_type) = words.next().filter(|word| !word.starts_with(b"#")) else {
                continue;
            };
            for word in words.take_while(|word| !word.starts_with(b"#")) {
                let mut extension = Vec::with_capacity(word.len() + 1);
                extension.push(b'.');
                extension.extend_from_slice(word);
                self.add(&extension, mime_type);
            }
        }
    }

    fn name_type(&self, name: &[u8]) -> Option<&[u8]> {
        let (stem, extension) = split_extension(name);
        // `suffix_map` rewrites `.tgz` and its kin to the compound suffix they
        // abbreviate. Every rewrite ends in an encoding, which is not itself
        // rewritten (asserted in `defaults`), so upstream's loop runs at most
        // once.
        let suffix = text::lower(extension);
        let rewritten = defaults::SUFFIX_REWRITES
            .iter()
            .find(|(abbreviation, _)| *abbreviation == suffix.as_slice())
            .map(|&(_, replacement)| [stem, replacement].concat());
        let (stem, extension) = split_extension(rewritten.as_deref().unwrap_or(name));
        // `encodings_map` is matched case-sensitively and only strips.
        let extension = if defaults::ENCODINGS.contains(&extension) {
            split_extension(stem).1
        } else {
            extension
        };
        let key = text::lower(extension);
        self.added.get(&key).map(Vec::as_slice).or_else(|| {
            defaults::DEFAULT_TYPES
                .binary_search_by(|(extension, _)| extension.cmp(&key.as_slice()))
                .ok()
                .map(|index| defaults::DEFAULT_TYPES[index].1)
        })
    }
}

fn split_extension(name: &[u8]) -> (&[u8], &[u8]) {
    match name.iter().rposition(|byte| *byte == b'.') {
        Some(index) if name[..index].iter().any(|byte| *byte != b'.') => {
            (&name[..index], &name[index..])
        }
        _ => (name, &[]),
    }
}

fn os_error(error: &io::Error, source: Option<&Path>) -> GuessError {
    errors::from_errno(errors::errno(error), source)
}

/// `str()` of the OSError CPython raises: `[Errno N] message`, then
/// `: 'path'` when the error names a file. `source` is quoted as it is
/// because `load` reads only `KNOWN_FILES`, which need no escaping in
/// `repr` (asserted below).
fn error_text(number: i32, message: &str, source: Option<&Path>) -> GuessError {
    let mut result = format!("[Errno {number}] {message}").into_bytes();
    if let Some(source) = source {
        result.extend_from_slice(b": '");
        result.extend_from_slice(source.as_os_str().as_encoded_bytes());
        result.push(b'\'');
    }
    GuessError(result)
}

const _: () = {
    let mut file = 0;
    while file < KNOWN_FILES.len() {
        let path = KNOWN_FILES[file].as_bytes();
        let mut index = 0;
        while index < path.len() {
            let byte = path[index];
            assert!(matches!(byte, b' '..=b'~') && byte != b'\'' && byte != b'\\');
            index += 1;
        }
        file += 1;
    }
};

#[cfg(test)]
mod tests;
