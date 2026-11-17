//! Extract external modules and their explicit Rust path attributes.
use super::{TaskError, lexical_tokens};
use std::path::PathBuf;

#[derive(Debug, Eq, PartialEq)]
pub(super) struct Declaration<'a> {
    pub name: &'a str,
    pub path: Option<PathBuf>,
}

pub(super) fn declarations(source: &str) -> Result<Vec<Declaration<'_>>, TaskError> {
    let tokens = lexical_tokens(source);
    let mut result = Vec::new();
    let mut path = None;
    let mut index = 0;
    while index < tokens.len() {
        if tokens[index..].starts_with(&["#", "["]) {
            let start = index + 2;
            let mut depth = 1;
            index = start;
            while index < tokens.len() && depth != 0 {
                match tokens[index] {
                    "[" => depth += 1,
                    "]" => depth -= 1,
                    _ => {}
                }
                index += 1;
            }
            if depth != 0 {
                return Err(error("unterminated module attribute"));
            }
            let attribute = &tokens[start..index - 1];
            if attribute.first() == Some(&"path") {
                let ["path", "=", literal] = attribute else {
                    return Err(error("module path must be a string literal"));
                };
                path = Some(path_literal(literal)?);
            }
        } else if tokens[index] == "mod" && tokens.get(index + 2) == Some(&";") {
            result.push(Declaration {
                name: tokens[index + 1],
                path: path.take(),
            });
            index += 3;
        } else {
            if matches!(tokens[index], ";" | "{" | "}") {
                path = None;
            }
            index += 1;
        }
    }
    Ok(result)
}

fn path_literal(literal: &str) -> Result<PathBuf, TaskError> {
    if let Some(raw) = literal.strip_prefix('r') {
        let hashes = raw.bytes().take_while(|byte| *byte == b'#').count();
        let quoted = raw
            .get(hashes..raw.len().saturating_sub(hashes))
            .and_then(|value| value.strip_prefix('"'))
            .and_then(|value| value.strip_suffix('"'))
            .ok_or_else(|| error("invalid raw module path"))?;
        return Ok(PathBuf::from(quoted));
    }
    let quoted = literal
        .strip_prefix('"')
        .and_then(|value| value.strip_suffix('"'))
        .ok_or_else(|| error("module path must be a string literal"))?;
    let mut result = String::new();
    let mut characters = quoted.chars().peekable();
    while let Some(character) = characters.next() {
        if character != '\\' {
            result.push(character);
            continue;
        }
        let escaped = characters
            .next()
            .ok_or_else(|| error("unterminated module path escape"))?;
        match escaped {
            '\\' | '"' | '\'' => result.push(escaped),
            'n' => result.push('\n'),
            'r' => result.push('\r'),
            't' => result.push('\t'),
            '0' => result.push('\0'),
            'x' => {
                let digits: String = characters.by_ref().take(2).collect();
                let value = u8::from_str_radix(&digits, 16)
                    .ok()
                    .filter(|value| digits.len() == 2 && value.is_ascii())
                    .ok_or_else(|| error("invalid ASCII module path escape"))?;
                result.push(char::from(value));
            }
            'u' => result.push(unicode_escape(&mut characters)?),
            '\n' | '\r' => {
                while characters.peek().is_some_and(|next| next.is_whitespace()) {
                    characters.next();
                }
            }
            _ => return Err(error("invalid module path escape")),
        }
    }
    Ok(PathBuf::from(result))
}

fn unicode_escape(characters: &mut impl Iterator<Item = char>) -> Result<char, TaskError> {
    if characters.next() != Some('{') {
        return Err(error("invalid Unicode module path escape"));
    }
    let mut digits = String::new();
    for character in characters {
        if character == '}' {
            return u32::from_str_radix(&digits, 16)
                .ok()
                .filter(|_| (1..=6).contains(&digits.len()))
                .and_then(char::from_u32)
                .ok_or_else(|| error("invalid Unicode module path escape"));
        }
        if character != '_' {
            digits.push(character);
        }
    }
    Err(error("unterminated Unicode module path escape"))
}

fn error(message: &str) -> TaskError {
    TaskError::Message(message.into())
}

#[cfg(test)]
mod tests;
