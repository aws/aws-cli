use crate::{OrderedMap, ReadError};
use std::path::Path;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Config,
    Credentials,
    Aliases,
}
pub type Nested = OrderedMap<String>;
pub type Entries = OrderedMap<Entry>;
pub type Sections = OrderedMap<Entries>;
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Value {
    String(String),
    Nested(Nested),
}
impl Value {
    pub fn as_str(&self) -> Option<&str> {
        if let Self::String(value) = self {
            Some(value)
        } else {
            None
        }
    }
    pub fn as_nested(&self) -> Option<&Nested> {
        if let Self::Nested(value) = self {
            Some(value)
        } else {
            None
        }
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Origin {
    pub source: String,
    pub section: String,
    pub key: String,
    pub line: usize,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Entry {
    pub value: Value,
    pub origin: Origin,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Syntax {
    Decoding,
    MissingSection,
    DuplicateSection,
    DuplicateOption,
    InvalidOption,
    InvalidNested,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Diagnostic {
    pub source: String,
    pub line: Option<usize>,
    pub syntax: Syntax,
}
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub enum Status {
    #[default]
    Omitted,
    Loaded,
    Missing,
    Directory,
    Unreadable(ReadError),
    ParseFailure(Diagnostic),
    ResourceLimit,
}
impl Status {
    pub fn name(&self) -> &'static str {
        match self {
            Self::Omitted => "omitted",
            Self::Loaded => "loaded",
            Self::Missing => "missing",
            Self::Directory => "directory",
            Self::Unreadable(_) => "unreadable",
            Self::ParseFailure(_) => "parse_failure",
            Self::ResourceLimit => "resource_limit",
        }
    }
}
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct File {
    pub source: String,
    pub status: Status,
    pub sections: Sections,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Contents<'a> {
    pub bytes: &'a [u8],
    pub source: &'a str,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Inputs<'a> {
    pub config: Option<Contents<'a>>,
    pub credentials: Option<Contents<'a>>,
    pub aliases: Option<Contents<'a>>,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Paths<'a> {
    pub config: Option<&'a Path>,
    pub credentials: Option<&'a Path>,
    pub aliases: Option<&'a Path>,
}
