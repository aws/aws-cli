//! Local operand normalization shared by copy execution and MIME guessing.
//! POSIX follows `posixpath.abspath`, including the special double-slash
//! root. Windows admits only spellings whose normalization needs no Win32
//! path API; other operands stay with the embedded Python implementation.
use std::ffi::OsStr;
use std::path::{Path, PathBuf};

#[cfg(any(not(windows), test))]
mod posix;
#[cfg(any(windows, test))]
mod windows;

/// Whether the native path can normalize `path` the way upstream's `abspath`
/// does. Every POSIX operand can be normalized lexically.
pub fn supports(path: &OsStr) -> bool {
    #[cfg(windows)]
    {
        windows::supports(path.as_encoded_bytes())
    }
    #[cfg(not(windows))]
    {
        let _ = path;
        true
    }
}

/// The part of `path` upstream's `guess_type` takes an extension from: its
/// final component, as the host's `os.path` splits it.
pub fn file_name(path: &OsStr) -> &[u8] {
    let path = path.as_encoded_bytes();
    #[cfg(windows)]
    {
        windows::file_name(path)
    }
    #[cfg(not(windows))]
    {
        posix::file_name(path)
    }
}

/// `os.path.dirname(path)` of an operand the native path admitted.
pub fn dir_name(path: &Path) -> &Path {
    let bytes = path.as_os_str().as_encoded_bytes();
    #[cfg(windows)]
    {
        let directory = windows::dir_name(bytes);
        // SAFETY: the bytes are a prefix of an `OsStr` encoding that is empty,
        // the whole encoding, or cut immediately before an ASCII separator or
        // after the one ending an `X:\` root. A separator is a nonempty UTF-8
        // substring, beside which `from_encoded_bytes_unchecked` admits a cut.
        Path::new(unsafe { OsStr::from_encoded_bytes_unchecked(directory) })
    }
    #[cfg(not(windows))]
    {
        use std::os::unix::ffi::OsStrExt;
        Path::new(OsStr::from_bytes(posix::dir_name(bytes)))
    }
}

/// `os.path.abspath(path)` with `cwd` as the working directory, resolved
/// lexically rather than through symlinks.
pub fn absolute_path(cwd: &Path, path: &Path) -> PathBuf {
    let cwd = cwd.as_os_str().as_encoded_bytes();
    let path = path.as_os_str().as_encoded_bytes();
    #[cfg(windows)]
    {
        let absolute = windows::absolute_path(cwd, path);
        // SAFETY: the bytes are the encodings of two `OsStr` values, cut only
        // at ASCII separators and drive colons and joined with ASCII
        // separators, so they remain a valid `OsStr` encoding.
        PathBuf::from(unsafe { std::ffi::OsString::from_encoded_bytes_unchecked(absolute) })
    }
    #[cfg(not(windows))]
    {
        use std::os::unix::ffi::OsStringExt;
        PathBuf::from(std::ffi::OsString::from_vec(posix::absolute_path(
            cwd, path,
        )))
    }
}
