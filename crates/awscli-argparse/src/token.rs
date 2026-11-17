//! Original operating-system argument values and their invocation positions.
use crate::Value;
use std::ffi::{OsStr, OsString};

/// One argument, retaining its origin while parser stages select and reorder values.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token {
    pub value: OsString,
    pub original_index: usize,
}

impl Token {
    pub fn as_os_str(&self) -> &OsStr {
        &self.value
    }

    pub fn as_str(&self) -> Option<&str> {
        self.value.to_str()
    }

    pub(crate) fn is_text(&self, text: &str) -> bool {
        self.value == text
    }

    pub(crate) fn split_equal(&self) -> Option<(OsString, Self)> {
        #[cfg(unix)]
        let (prefix, value) = {
            use std::os::unix::ffi::{OsStrExt, OsStringExt};
            let bytes = self.value.as_bytes();
            let index = bytes.iter().position(|byte| *byte == b'=')?;
            (
                OsString::from_vec(bytes[..index].to_vec()),
                OsString::from_vec(bytes[index + 1..].to_vec()),
            )
        };
        #[cfg(windows)]
        let (prefix, value) = {
            use std::os::windows::ffi::{OsStrExt, OsStringExt};
            let wide: Vec<_> = self.value.encode_wide().collect();
            let index = wide.iter().position(|unit| *unit == u16::from(b'='))?;
            (
                OsString::from_wide(&wide[..index]),
                OsString::from_wide(&wide[index + 1..]),
            )
        };
        Some((
            prefix,
            Self {
                value,
                original_index: self.original_index,
            },
        ))
    }
}

pub(crate) fn from_os(arguments: &[OsString]) -> Vec<Token> {
    arguments
        .iter()
        .cloned()
        .enumerate()
        .map(|(original_index, value)| Token {
            value,
            original_index,
        })
        .collect()
}

impl From<Token> for Value {
    fn from(token: Token) -> Self {
        token.value.into()
    }
}

impl PartialEq<&str> for Token {
    fn eq(&self, other: &&str) -> bool {
        self.value == *other
    }
}
impl PartialEq<str> for Token {
    fn eq(&self, other: &str) -> bool {
        self.value == other
    }
}

impl PartialEq<String> for Token {
    fn eq(&self, other: &String) -> bool {
        self.value == other.as_str()
    }
}
