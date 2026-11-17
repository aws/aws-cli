//! Port of awscli/shorthand.py's ShorthandParser: the `key=value,...`
//! grammar the AWS CLI accepts for structured arguments, with the text of
//! ShorthandParseSyntaxError and DuplicateKeyInObjectError including their
//! caret blocks. Only what a map-typed argument needs is ported: the
//! grammar and its diagnostics. Upstream's `key@=value` production resolves
//! file://, fileb://, and http(s):// parameter files inside values while
//! parsing; it is not ported, and a value using it is refused with
//! `ParseError::Paramfile` for the caller to hand to Python. Message indices
//! count code points, as Python's str indices do, so the caret sits under
//! the same column for non-ASCII input. Results are the crate's shared
//! `JsonValue`: a word is a string, `a,b` and `[a,b]` are arrays, and
//! `{k=v}` and the top-level parameter are objects.
use crate::json::Object as Map;
use crate::{NESTED_VALUE_DEPTH_MAX, SHORTHAND_INPUT_BYTES_MAX, Value};
/// Grammar rejection or an explicitly unsupported input.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    Syntax(String),
    Paramfile,
    TooDeep,
    TooLong,
    InvalidUtf8,
}
/// Python str.isspace, including the four ASCII information separators.
pub fn is_python_space(c: char) -> bool {
    matches!(u32::from(c),
        0x09..=0x0d | 0x1c..=0x20 | 0x85 | 0xa0 | 0x1680 | 0x2000..=0x200a |
        0x2028 | 0x2029 | 0x202f | 0x205f | 0x3000
    )
}
/// Python's `str.lstrip()` with no argument: leading `str.isspace` code
/// points removed.
pub fn lstrip(text: &str) -> &str {
    text.trim_start_matches(is_python_space)
}
/// Python's `str.rstrip()` with no argument.
pub fn rstrip(text: &str) -> &str {
    text.trim_end_matches(is_python_space)
}
/// `ShorthandParser.parse`: one shorthand parameter, without resolving
/// nested parameter files.
pub fn parse(input: &[u8]) -> Result<Value, ParseError> {
    if input.len() > SHORTHAND_INPUT_BYTES_MAX {
        return Err(ParseError::TooLong);
    }
    let input = std::str::from_utf8(input).map_err(|_| ParseError::InvalidUtf8)?;
    let mut parser = Parser {
        input,
        index: 0,
        depth: 0,
    };
    let value = parser
        .parse_parameter()
        .map_err(|error| error.render_diagnostic(input))?;
    assert_eq!(parser.index, input.len());
    assert_eq!(parser.depth, 0);
    Ok(value)
}
#[derive(Debug)]
enum GrammarError {
    Syntax {
        expected: String,
        actual: String,
        index: usize,
    },
    Duplicate {
        key: String,
        index: usize,
    },
    Paramfile,
    TooDeep,
}
impl GrammarError {
    fn render_diagnostic(self, input: &str) -> ParseError {
        match self {
            Self::Syntax {
                expected,
                actual,
                index,
            } => ParseError::Syntax(format!(
                "Expected: '{expected}', received: '{actual}' for input:\n {}",
                error_location(input, index)
            )),
            Self::Duplicate { key, index } => ParseError::Syntax(format!(
                "Second instance of key \"{key}\" encountered for input:\n{}\nThis is \
    often because there is a preceding \",\" instead of a space.",
                error_location(input, index)
            )),
            Self::Paramfile => ParseError::Paramfile,
            Self::TooDeep => ParseError::TooDeep,
        }
    }
}
struct Parser<'a> {
    input: &'a str,
    index: usize,
    depth: usize,
}
impl Parser<'_> {
    fn peek(&self) -> Option<char> {
        self.input[self.index..].chars().next()
    }
    fn consume_whitespace(&mut self) {
        while self
            .peek()
            .is_some_and(|c| matches!(c, ' ' | '\t' | '\n' | '\r' | '\u{b}' | '\u{c}'))
        {
            self.index += 1;
        }
    }
    /// `_expect` without raising: whether `c` is next, consuming it. With
    /// `whitespace`, whitespace before it is consumed even on a mismatch, and
    /// whitespace after it on a match.
    fn accept(&mut self, c: char, whitespace: bool) -> bool {
        if whitespace {
            self.consume_whitespace();
        }
        if self.peek() != Some(c) {
            return false;
        }
        self.index += 1;
        if whitespace {
            self.consume_whitespace();
        }
        true
    }
    fn expect(&mut self, c: char, whitespace: bool) -> Result<(), GrammarError> {
        if self.accept(c, whitespace) {
            Ok(())
        } else {
            Err(self.fail(
                &c.to_string(),
                &self
                    .peek()
                    .map(|c| c.to_string())
                    .unwrap_or_else(|| "EOF".into()),
                self.index,
            ))
        }
    }
    fn fail(&self, expected: &str, actual: &str, index: usize) -> GrammarError {
        GrammarError::Syntax {
            expected: expected.into(),
            actual: actual.into(),
            index,
        }
    }
    fn parse_parameter(&mut self) -> Result<Value, GrammarError> {
        let mut pairs = Map::new();
        let (key, value) = self.parse_key_value()?;
        pairs.insert(key, value);
        let mut last = self.index;
        while self.index < self.input.len() {
            self.expect(',', true)?;
            let (key, value) = self.parse_key_value()?;
            if pairs.contains_key(&key) {
                return Err(GrammarError::Duplicate {
                    key,
                    index: last + 1,
                });
            }
            pairs.insert(key, value);
            last = self.index;
        }
        Ok(Value::Object(pairs))
    }
    fn parse_key(&mut self) -> String {
        let start = self.index;
        while self
            .peek()
            .is_some_and(|c| c.is_ascii_alphanumeric() || "-_.#/:".contains(c))
        {
            self.index += 1;
        }
        self.input[start..self.index].into()
    }
    fn parse_key_value(&mut self) -> Result<(String, Value), GrammarError> {
        let key = self.parse_key();
        if self.accept('@', true) {
            return Err(GrammarError::Paramfile);
        }
        self.expect('=', true)?;
        Ok((key, self.parse_values()?))
    }
    fn parse_values(&mut self) -> Result<Value, GrammarError> {
        match self.peek() {
            None => Ok("".into()),
            Some('[') => self.parse_explicit_list(),
            Some('{') => self.parse_hash_literal(),
            _ => self.parse_csv_value(),
        }
    }
    fn parse_first_value(&mut self) -> Result<String, GrammarError> {
        match self.peek() {
            Some(c @ ('\'' | '"')) => self.parse_quoted(c),
            _ => Ok(self.parse_word(false).unwrap_or_default()),
        }
    }
    fn parse_second_value(&mut self) -> Result<String, GrammarError> {
        match self.peek() {
            Some(c @ ('\'' | '"')) => self.parse_quoted(c),
            _ => self
                .parse_word(true)
                .ok_or_else(|| self.fail("<second>", "<none>", self.index)),
        }
    }
    /// `_csv_value`: a first value, then second values separated by commas
    /// until one fails to parse, which backtracks to the comma before it so
    /// `a=b,c=d` reads as two keyvals rather than a list.
    fn parse_csv_value(&mut self) -> Result<Value, GrammarError> {
        let first = self.parse_first_value()?;
        self.consume_whitespace();
        if self.peek() != Some(',') {
            return Ok(first.into());
        }
        self.expect(',', true)?;
        let mut list = vec![Value::String(first.clone())];
        loop {
            let item = match self.parse_second_value() {
                Ok(v) => v,
                Err(GrammarError::Syntax { .. }) if self.index < self.input.len() => {
                    self.backtrack_to_comma();
                    break;
                }
                Err(e) => return Err(e),
            };
            self.consume_whitespace();
            if self.index == self.input.len() {
                list.push(item.into());
                break;
            }
            if self.expect(',', true).is_err() {
                self.backtrack_to_comma();
                break;
            }
            list.push(item.into());
        }
        if list.len() == 1 {
            Ok(first.into())
        } else {
            Ok(Value::Array(list))
        }
    }
    fn backtrack_to_comma(&mut self) {
        while self.index > 0 && self.input.as_bytes()[self.index] != b',' {
            self.index -= 1;
        }
    }
    /// `_FIRST_VALUE`, or with `second` `_SECOND_VALUE`: an escaped comma or
    /// start-word character, then escaped commas and follow characters. None
    /// when nothing matched; otherwise the text with `\,` unescaped and
    /// trailing whitespace stripped, as `_value` and `_second_value` process it.
    fn parse_word(&mut self, second: bool) -> Option<String> {
        let start = self.index;
        while self.index < self.input.len() {
            if self.input[self.index..].starts_with("\\,") {
                self.index += 2;
                continue;
            }
            let Some(c) = self.peek() else {
                break;
            };
            let allowed = if self.index == start {
                is_start_word(c)
            } else if second {
                is_second_follow(c)
            } else {
                is_first_follow(c)
            };
            if !allowed {
                break;
            }
            self.index += c.len_utf8();
        }
        if self.index == start {
            None
        } else {
            Some(rstrip(&self.input[start..self.index].replace("\\,", ",")).to_owned())
        }
    }
    /// `_SINGLE_QUOTED` and `_DOUBLE_QUOTED`, `q(?:\\q|[^q])*q`, matched as
    /// Python's regex does: the body runs to the first unescaped quote, or
    /// with none, backtracks to the last escaped quote. The body then has
    /// `\q` and `\\` unescaped, in that order, as `_consume_quoted` does.
    fn parse_quoted(&mut self, quote: char) -> Result<String, GrammarError> {
        let start = self.index;
        let mut index = start + 1;
        let mut last_escaped = None;
        let bytes = self.input.as_bytes();
        let quote = quote as u8;
        let mut end = None;
        while index < bytes.len() {
            if bytes[index] == b'\\' && bytes.get(index + 1) == Some(&quote) {
                last_escaped = Some(index + 1);
                index += 2;
                continue;
            }
            if bytes[index] == quote {
                end = Some(index);
                break;
            }
            index += 1;
        }
        let end = end.or(last_escaped).ok_or_else(|| {
            self.fail(
                if quote == b'\'' {
                    "<singled quoted>"
                } else {
                    "<double quoted>"
                },
                "<none>",
                start,
            )
        })?;
        self.index = end + 1;
        Ok(self.input[start + 1..end]
            .replace(
                &format!("\\{}", char::from(quote)),
                &char::from(quote).to_string(),
            )
            .replace("\\\\", "\\"))
    }
    fn enter(&mut self) -> Result<(), GrammarError> {
        if self.depth == NESTED_VALUE_DEPTH_MAX {
            return Err(GrammarError::TooDeep);
        }
        self.depth += 1;
        Ok(())
    }
    fn parse_explicit_values(&mut self) -> Result<Value, GrammarError> {
        match self.peek() {
            Some('[') => self.parse_explicit_list(),
            Some('{') => self.parse_hash_literal(),
            _ => self.parse_first_value().map(Value::String),
        }
    }
    fn parse_explicit_list(&mut self) -> Result<Value, GrammarError> {
        self.enter()?;
        self.expect('[', true)?;
        let mut items = Vec::new();
        while self.peek() != Some(']') {
            items.push(self.parse_explicit_values()?);
            self.consume_whitespace();
            if self.peek() != Some(']') {
                self.expect(',', false)?;
                self.consume_whitespace();
            }
        }
        self.expect(']', false)?;
        self.depth -= 1;
        Ok(Value::Array(items))
    }
    /// `_hash_literal`: "{" keyvals separated by commas "}", a repeated key
    /// keeping its last value in its first position, as a dict does.
    fn parse_hash_literal(&mut self) -> Result<Value, GrammarError> {
        self.enter()?;
        self.expect('{', true)?;
        let mut pairs = Map::new();
        while self.peek() != Some('}') {
            let key = self.parse_key();
            if self.accept('@', true) {
                return Err(GrammarError::Paramfile);
            }
            self.expect('=', true)?;
            let value = self.parse_explicit_values()?;
            self.consume_whitespace();
            if self.peek() != Some('}') {
                self.expect(',', false)?;
                self.consume_whitespace();
            }
            pairs.insert(key, value);
        }
        self.expect('}', false)?;
        self.depth -= 1;
        Ok(Value::Object(pairs))
    }
}
/// `_error_location`: the input with a caret under `index`. The column
/// counts code points from the last newline before the index, and text
/// from the next newline on moves below the caret line.
fn error_location(input: &str, index: usize) -> String {
    let before = &input[..index];
    let start = before.rfind('\n').map_or(0, |i| i + 1);
    let column = input[start..index].chars().count();
    let end = input[index..].find('\n').map_or(input.len(), |i| index + i);
    format!(
        "{}\n{}^{}",
        &input[..end],
        " ".repeat(column),
        &input[end..]
    )
}
/// `_START_WORD`: printable BMP code points other than space, quotes,
/// comma, equals, and the two openers.
fn is_start_word(c: char) -> bool {
    matches!(u32::from(c),
        0x21 | 0x23..=0x26 | 0x28..=0x2b | 0x2d..=0x3c | 0x3e..=0x5a |
        0x5c..=0x7a | 0x7c..=0xffff
    )
}
/// `_FIRST_FOLLOW_CHARS`: `\s` and the BMP other than quotes, comma, and
/// the two closers.
fn is_first_follow(c: char) -> bool {
    is_python_space(c)
        || matches!(u32::from(c),0x21|0x23..=0x26|0x28..=0x2b|0x2d..=0x5c|0x5e..=0x7c|0x7e..=0xffff)
}
/// `_SECOND_FOLLOW_CHARS`: `\s` and the BMP other than quotes, comma, and
/// equals.
fn is_second_follow(c: char) -> bool {
    is_python_space(c)
        || matches!(u32::from(c),0x21|0x23..=0x26|0x28..=0x2b|0x2d..=0x3c|0x3e..=0xffff)
}
#[cfg(test)]
mod tests;
