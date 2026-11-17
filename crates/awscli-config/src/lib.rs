//! Standalone AWS shared-file parsing with retained declaration origins.
//!
//! Parsing is independent of the environment and C libraries. Paths are literal;
//! callers choose paths and inject filesystem access through [`Fs`].
#![forbid(unsafe_code)]

mod ini;
mod merge;
mod ordered_map;
mod profile_map;
mod read;
mod text;
mod types;

#[doc(inline)]
pub use ordered_map::OrderedMap;
#[doc(inline)]
pub use profile_map::Organized;
#[doc(inline)]
pub use read::{FileKind, Fs, Metadata, ReadError, ReadHandle, StdFs};
#[doc(inline)]
pub use text::is_space;
#[doc(inline)]
pub use types::{
    Contents, Diagnostic, Entries, Entry, File, Inputs, Kind, Nested, Origin, Paths, Sections,
    Status, Syntax, Value,
};

/// Inclusive byte limit for each input, before UTF-8 decoding. Upstream imposes
/// no limit, so this bounds memory growth: a profile is roughly 200 bytes, so
/// 8 MiB holds about 40,000 profiles.
pub const INPUT_SIZE_MAX: usize = 8 * 1024 * 1024;

/// Owned, immutable parsing results and organized profile views.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ParsedFiles {
    pub config: File,
    pub credentials: File,
    pub aliases: File,
    pub organized: Organized,
    pub profiles: Option<Sections>,
}

impl ParsedFiles {
    /// Parses caller-supplied bytes, copying all retained values and labels.
    /// No I/O or environment access occurs.
    pub fn parse(inputs: Inputs<'_>) -> Self {
        Self::build_views(
            parse_file(inputs.config, Kind::Config),
            parse_file(inputs.credentials, Kind::Credentials),
            parse_file(inputs.aliases, Kind::Aliases),
        )
    }

    /// Loads each distinct literal path once and parses it with each selected grammar.
    ///
    /// # Errors
    /// Propagates cancellation and filesystem resource exhaustion.
    pub fn load(fs: &impl Fs, paths: Paths<'_>) -> Result<Self, ReadError> {
        let mut reads = std::collections::HashMap::new();
        let mut load = |path: Option<&std::path::Path>, kind| -> Result<File, ReadError> {
            let Some(path) = path else {
                return Ok(File::default());
            };
            // Key by the path as written: `Path` equality ignores a trailing
            // separator, yet `c/` cannot open the regular file `c`.
            let key = path.as_os_str();
            if !reads.contains_key(key) {
                reads.insert(key.to_os_string(), read::file(fs, path)?);
            }
            let source = path.to_string_lossy();
            match &reads[key] {
                read::ReadResult::Bytes(bytes) => Ok(parse_file(
                    Some(Contents {
                        bytes,
                        source: &source,
                    }),
                    kind,
                )),
                read::ReadResult::Status(status) => Ok(File {
                    source: source.into_owned(),
                    status: status.clone(),
                    sections: Sections::default(),
                }),
            }
        };
        Ok(Self::build_views(
            load(paths.config, Kind::Config)?,
            load(paths.credentials, Kind::Credentials)?,
            load(paths.aliases, Kind::Aliases)?,
        ))
    }

    fn build_views(config: File, credentials: File, aliases: File) -> Self {
        let organized = profile_map::organize(&config.sections);
        let profiles = if [&config.status, &credentials.status]
            .iter()
            .any(|status| matches!(status, Status::ParseFailure(_) | Status::ResourceLimit))
        {
            None
        } else {
            Some(merge::profiles(&organized.profiles, &credentials.sections))
        };
        Self {
            config,
            credentials,
            aliases,
            organized,
            profiles,
        }
    }
}

fn parse_file(input: Option<Contents<'_>>, kind: Kind) -> File {
    let Some(input) = input else {
        return File::default();
    };
    let source = input.source.to_owned();
    if input.bytes.len() > INPUT_SIZE_MAX {
        return File {
            source,
            status: Status::ResourceLimit,
            sections: Sections::default(),
        };
    }
    let parsed = match std::str::from_utf8(input.bytes) {
        Ok(text) => ini::parse(text, input.source, kind),
        Err(_) => Err(Diagnostic {
            source: source.clone(),
            line: None,
            syntax: Syntax::Decoding,
        }),
    };
    match parsed {
        Ok(sections) => File {
            source,
            status: Status::Loaded,
            sections,
        },
        Err(diagnostic) => File {
            source,
            status: Status::ParseFailure(diagnostic),
            sections: Sections::default(),
        },
    }
}

#[cfg(test)]
mod tests;
