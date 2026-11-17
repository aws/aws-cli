//! Compiler-side source filenames independent of the source store and scratch tree.
//!
//! The maps belong to the compiler command, not to project flags a build
//! system can replace. POSIX builds keep them in per-project compiler
//! wrappers. Windows CMake builds receive them quoted as the initial
//! `CMAKE_C_FLAGS`/`CMAKE_CXX_FLAGS` cache values (`windows_flags`), and the
//! Windows OpenSSL build passes both separator spellings (`clang_cl_flags`)
//! to clang-cl through `_CL_` (`clang_cl_variable`).

use std::path::Path;

use super::super::{Result, error, shell_quote};

/// Physical roots the compiler reads for one package.
pub(super) struct Roots<'a> {
    /// Stable upstream package name, such as `aws-c-common`.
    pub name: &'a str,
    /// Source tree the compiler reads, which may be a patched or scratch copy.
    pub source: &'a Path,
    /// Generated sources and compiler scratch files for this package.
    pub build: &'a Path,
    /// Shared scratch tree, including other packages' generated files.
    pub work: &'a Path,
    /// Shared installed headers and libraries.
    pub install: &'a Path,
}

/// `-ffile-prefix-map` arguments for every root, broadest first.
///
/// The build and source trees can sit inside the work tree, so the roots are
/// ordered by length: GCC applies the last matching map, and Clang the longest.
/// Trailing separators keep a map from also matching a sibling directory.
pub(super) fn flags(roots: &Roots<'_>) -> Result<Vec<String>> {
    if cfg!(windows) {
        // CMake hands Clang forward-slash paths, even on Windows.
        mapped(roots, |root| vec![(root.replace('\\', "/"), '/')])
    } else {
        // A POSIX directory name may contain a backslash; keep it literal.
        mapped(roots, |root| vec![(root.to_owned(), '/')])
    }
}

/// Map arguments for clang-cl, which can see either separator spelling of a
/// root: nmake passes backslash paths, CMake forward slashes.
pub(super) fn clang_cl_flags(roots: &Roots<'_>) -> Result<Vec<String>> {
    mapped(roots, |root| {
        vec![
            (root.replace('/', "\\"), '\\'),
            (root.replace('\\', "/"), '/'),
        ]
    })
}

/// Maps for each root spelling, each ending in that spelling's separator.
fn mapped(
    roots: &Roots<'_>,
    spellings: impl Fn(&str) -> Vec<(String, char)>,
) -> Result<Vec<String>> {
    let mut mappings = Vec::new();
    for (root, logical) in [
        (roots.work, "crt-work".to_owned()),
        (roots.install, "crt-install".to_owned()),
        (roots.build, format!("crt-build/{}", roots.name)),
        (roots.source, roots.name.to_owned()),
    ] {
        let root = root
            .to_str()
            .ok_or_else(|| error("CRT build roots must be UTF-8"))?;
        for (spelling, separator) in spellings(root) {
            let spelling = spelling.trim_end_matches(separator);
            let mapping = (format!("{spelling}{separator}"), logical.clone());
            if !mappings.contains(&mapping) {
                mappings.push(mapping);
            }
        }
    }
    mappings.sort_by_key(|(root, _)| root.len());
    Ok(mappings
        .into_iter()
        .map(|(root, logical)| format!("-ffile-prefix-map={root}={logical}/"))
        .collect())
}

/// The maps double-quoted and space-joined for a Windows compiler command
/// line. Windows names cannot contain a double quote, so spaces and percent
/// signs stay verbatim.
pub(super) fn windows_flags(maps: &[String]) -> String {
    maps.iter()
        .map(|map| format!("\"{map}\""))
        .collect::<Vec<_>>()
        .join(" ")
}

/// The `_CL_` value that appends `flags` to every clang-cl invocation.
///
/// clang-cl reads `_CL_` as `cl` does, so the maps stay out of the CC and
/// CFLAGS strings OpenSSL records in its build information. Windows names
/// cannot contain a double quote and no argument ends in a backslash, so
/// quoting each argument preserves it, spaces included. The driver also
/// replaces the first `#` in each option with `=`, so each option's first
/// `=` is written as `#`; a `#` in a path then stays literal.
pub(super) fn clang_cl_variable(flags: &[String]) -> String {
    flags
        .iter()
        .map(|flag| format!("\"/clang:{}\"", flag.replacen('=', "#", 1)))
        .collect::<Vec<_>>()
        .join(" ")
}

/// A POSIX compiler wrapper that runs `compiler` with `flags` before the caller's arguments.
///
/// Keeping the maps in the wrapper also keeps them out of compiler strings
/// that builds such as OpenSSL embed in their version metadata.
pub(super) fn wrapper(compiler: &Path, flags: &[String]) -> Result<String> {
    let mut script = format!("#!/bin/sh\nexec {}", shell_quote(compiler)?);
    for flag in flags {
        script.push_str(" '");
        script.push_str(&flag.replace('\'', "'\\''"));
        script.push('\'');
    }
    script.push_str(" \"$@\"\n");
    Ok(script)
}

#[cfg(test)]
mod tests;
