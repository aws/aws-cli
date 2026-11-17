//! Bounded JSON scanner retaining every numeric token's original spelling.
use crate::pyrepr;
use std::collections::HashMap;
/// Decoded parameter JSON with ordered objects and lexical numbers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum JsonValue {
    Null,
    Bool(bool),
    Number(String),
    String(String),
    /// A raw operating-system argument; JSON and parameter-file parsers never create this.
    OsString(std::ffi::OsString),
    Bytes(Vec<u8>),
    Array(Vec<JsonValue>),
    Object(Object),
}
/// Syntax rejection at a byte boundary, or an unsupported nesting depth.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum JsonError {
    Syntax { offset: usize, incomplete: bool },
    TooDeep,
    TooLong,
}
impl JsonError {
    pub fn describe(&self, input: &str) -> String {
        match self {
            Self::Syntax { offset, incomplete } => {
                let before = &input.as_bytes()[..(*offset).min(input.len())];
                let line = before.iter().filter(|c| **c == b'\n').count() + 1;
                let column = before
                    .iter()
                    .rposition(|c| *c == b'\n')
                    .map_or(before.len() + 1, |i| before.len() - i);
                format!(
                    "{}: line {line} column {column} (byte {offset})",
                    if *incomplete {
                        "unexpected end of input"
                    } else {
                        "syntax error"
                    }
                )
            }
            Self::TooDeep => "JSON nesting limit exceeded".into(),
            Self::TooLong => "JSON input limit exceeded".into(),
        }
    }
}
/// Parse the entire JSON document; nonstandard numbers and lone surrogates fail.
pub fn parse(input: &[u8]) -> Result<JsonValue, JsonError> {
    parse_with_limit(input, crate::SHORTHAND_INPUT_BYTES_MAX)
}
/// Parse framing JSON with a caller-supplied inclusive byte budget.
pub fn parse_with_limit(input: &[u8], limit: usize) -> Result<JsonValue, JsonError> {
    if input.len() > limit {
        return Err(JsonError::TooLong);
    }
    let mut scanner = Scanner { input, index: 0 };
    let value = scanner.value(0)?;
    scanner.space();
    if scanner.index != input.len() {
        return Err(scanner.error());
    }
    Ok(value)
}
struct Scanner<'a> {
    input: &'a [u8],
    index: usize,
}
impl Scanner<'_> {
    fn error(&self) -> JsonError {
        JsonError::Syntax {
            offset: self.index,
            incomplete: self.index == self.input.len(),
        }
    }
    fn space(&mut self) {
        while self
            .input
            .get(self.index)
            .is_some_and(|c| matches!(c, b' ' | b'\t' | b'\n' | b'\r'))
        {
            self.index += 1;
        }
    }
    fn consume(&mut self, c: u8) -> Result<(), JsonError> {
        self.space();
        if self.input.get(self.index) != Some(&c) {
            return Err(self.error());
        }
        self.index += 1;
        Ok(())
    }
    fn value(&mut self, depth: usize) -> Result<JsonValue, JsonError> {
        self.space();
        match self.input.get(self.index).copied() {
            Some(b'"') => self.string().map(JsonValue::String),
            Some(b'{') => self.object(depth),
            Some(b'[') => self.array(depth),
            Some(b't') => self.literal(b"true", JsonValue::Bool(true)),
            Some(b'f') => self.literal(b"false", JsonValue::Bool(false)),
            Some(b'n') => self.literal(b"null", JsonValue::Null),
            Some(b'-' | b'0'..=b'9') => self.number(),
            _ => Err(self.error()),
        }
    }
    fn literal(&mut self, token: &[u8], value: JsonValue) -> Result<JsonValue, JsonError> {
        for c in token {
            if self.input.get(self.index) != Some(c) {
                return Err(self.error());
            }
            self.index += 1;
        }
        Ok(value)
    }
    fn number(&mut self) -> Result<JsonValue, JsonError> {
        let start = self.index;
        if self.input.get(self.index) == Some(&b'-') {
            self.index += 1;
        }
        match self.input.get(self.index) {
            Some(b'0') => self.index += 1,
            Some(b'1'..=b'9') => self.digits(),
            _ => return Err(self.error()),
        }
        if self.input.get(self.index) == Some(&b'.') {
            self.index += 1;
            let before = self.index;
            self.digits();
            if self.index == before {
                return Err(self.error());
            }
        }
        if self
            .input
            .get(self.index)
            .is_some_and(|c| matches!(c, b'e' | b'E'))
        {
            self.index += 1;
            if self
                .input
                .get(self.index)
                .is_some_and(|c| matches!(c, b'+' | b'-'))
            {
                self.index += 1;
            }
            let before = self.index;
            self.digits();
            if self.index == before {
                return Err(self.error());
            }
        }
        let text = std::str::from_utf8(&self.input[start..self.index]).map_err(|_| self.error())?;
        Ok(JsonValue::Number(text.to_owned()))
    }
    fn digits(&mut self) {
        while self.input.get(self.index).is_some_and(u8::is_ascii_digit) {
            self.index += 1;
        }
    }
    fn string(&mut self) -> Result<String, JsonError> {
        self.consume(b'"')?;
        let mut text = String::new();
        loop {
            let Some(c) = self.input.get(self.index).copied() else {
                return Err(self.error());
            };
            match c {
                b'"' => {
                    self.index += 1;
                    return Ok(text);
                }
                b'\\' => {
                    self.index += 1;
                    self.escape(&mut text)?;
                }
                0..=0x1f => return Err(self.error()),
                0x20..=0x7f => {
                    self.index += 1;
                    text.push(char::from(c));
                }
                _ => self.utf8(c, &mut text)?,
            }
        }
    }
    fn utf8(&mut self, lead: u8, text: &mut String) -> Result<(), JsonError> {
        const CONTINUATION: std::ops::RangeInclusive<u8> = 0x80..=0xbf;
        let (first, length) = match lead {
            0xc2..=0xdf => (CONTINUATION, 2),
            0xe0 => (0xa0..=0xbf, 3),
            0xe1..=0xec | 0xee..=0xef => (CONTINUATION, 3),
            0xed => (0x80..=0x9f, 3),
            0xf0 => (0x90..=0xbf, 4),
            0xf1..=0xf3 => (CONTINUATION, 4),
            0xf4 => (0x80..=0x8f, 4),
            _ => return Err(self.error()),
        };
        let start = self.index;
        self.index += 1;
        self.accept(|c| first.contains(&c))?;
        for _ in 2..length {
            self.accept(|c| CONTINUATION.contains(&c))?;
        }
        let sequence =
            std::str::from_utf8(&self.input[start..self.index]).map_err(|_| self.error())?;
        text.push_str(sequence);
        Ok(())
    }
    fn escape(&mut self, text: &mut String) -> Result<(), JsonError> {
        let Some(c) = self.input.get(self.index).copied() else {
            return Err(self.error());
        };
        let decoded = match c {
            b'"' | b'\\' | b'/' => char::from(c),
            b'b' => '\u{8}',
            b'f' => '\u{c}',
            b'n' => '\n',
            b'r' => '\r',
            b't' => '\t',
            b'u' => {
                self.index += 1;
                return self.unicode_escape(text);
            }
            _ => return Err(self.error()),
        };
        self.index += 1;
        text.push(decoded);
        Ok(())
    }
    fn unicode_escape(&mut self, text: &mut String) -> Result<(), JsonError> {
        let unit = self.hex(4)?;
        let code = if (0xd800..=0xdbff).contains(&unit) {
            let low = self.low_surrogate()?;
            0x10000 + ((unit - 0xd800) << 10) + (low - 0xdc00)
        } else if (0xdc00..=0xdfff).contains(&unit) {
            return Err(JsonError::Syntax {
                offset: self.index,
                incomplete: false,
            });
        } else {
            unit
        };
        text.push(char::from_u32(code).ok_or_else(|| self.error())?);
        Ok(())
    }
    fn low_surrogate(&mut self) -> Result<u32, JsonError> {
        self.accept(|c| c == b'\\')?;
        self.accept(|c| c == b'u')?;
        self.accept(|c| matches!(c, b'D' | b'd'))?;
        let third = self.hex_digit(|c| matches!(c, b'C'..=b'F' | b'c'..=b'f'))?;
        Ok(0xd000 | (third << 8) | self.hex(2)?)
    }
    fn hex(&mut self, digits: usize) -> Result<u32, JsonError> {
        let mut value = 0;
        for _ in 0..digits {
            value = value * 16 + self.hex_digit(|c| c.is_ascii_hexdigit())?;
        }
        Ok(value)
    }
    fn hex_digit(&mut self, allowed: impl Fn(u8) -> bool) -> Result<u32, JsonError> {
        let c = self.accept(allowed)?;
        char::from(c).to_digit(16).ok_or_else(|| self.error())
    }
    fn accept(&mut self, allowed: impl Fn(u8) -> bool) -> Result<u8, JsonError> {
        match self.input.get(self.index).copied() {
            Some(c) if allowed(c) => {
                self.index += 1;
                Ok(c)
            }
            _ => Err(self.error()),
        }
    }
    fn array(&mut self, depth: usize) -> Result<JsonValue, JsonError> {
        if depth > crate::NESTED_VALUE_DEPTH_MAX {
            return Err(JsonError::TooDeep);
        }
        self.consume(b'[')?;
        self.space();
        let mut items = Vec::new();
        if self.input.get(self.index) == Some(&b']') {
            self.index += 1;
            return Ok(JsonValue::Array(items));
        }
        loop {
            items.push(self.value(depth + 1)?);
            self.space();
            if self.input.get(self.index) == Some(&b']') {
                self.index += 1;
                break;
            }
            self.consume(b',')?;
        }
        Ok(JsonValue::Array(items))
    }
    fn object(&mut self, depth: usize) -> Result<JsonValue, JsonError> {
        if depth > crate::NESTED_VALUE_DEPTH_MAX {
            return Err(JsonError::TooDeep);
        }
        self.consume(b'{')?;
        self.space();
        let mut pairs = Object::new();
        if self.input.get(self.index) == Some(&b'}') {
            self.index += 1;
            return Ok(JsonValue::Object(pairs));
        }
        loop {
            let key = self.string()?;
            self.consume(b':')?;
            let value = self.value(depth + 1)?;
            pairs.insert(key, value);
            self.space();
            if self.input.get(self.index) == Some(&b'}') {
                self.index += 1;
                break;
            }
            self.consume(b',')?;
        }
        Ok(JsonValue::Object(pairs))
    }
}
impl JsonValue {
    /// Python's repr of the value json.loads builds: objects are OrderedDicts.
    pub fn repr(&self) -> String {
        pyrepr::value(self, true)
    }
    pub fn type_name(&self) -> &'static str {
        match self {
            Self::Null => "NoneType",
            Self::Bool(_) => "bool",
            Self::String(_) | Self::OsString(_) => "str",
            Self::Bytes(_) => "bytes",
            Self::Array(_) => "list",
            Self::Object(_) => "collections.OrderedDict",
            Self::Number(v) => {
                if v.contains(['.', 'e', 'E']) {
                    "float"
                } else {
                    "int"
                }
            }
        }
    }
}
#[cfg(test)]
mod tests;
/// Insertion-ordered JSON object; replacement retains the first key position.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Object {
    pairs: Vec<(String, JsonValue)>,
    indices: HashMap<String, usize>,
}
impl Object {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn insert(&mut self, key: String, value: JsonValue) {
        if let Some(&index) = self.indices.get(&key) {
            self.pairs[index].1 = value;
        } else {
            self.indices.insert(key.clone(), self.pairs.len());
            self.pairs.push((key, value));
        }
    }
    pub fn contains_key(&self, key: &str) -> bool {
        self.indices.contains_key(key)
    }
    pub fn get(&self, key: &str) -> Option<&JsonValue> {
        self.indices.get(key).map(|&index| &self.pairs[index].1)
    }
    pub fn len(&self) -> usize {
        self.pairs.len()
    }
    pub fn is_empty(&self) -> bool {
        self.pairs.is_empty()
    }
    pub fn iter(&self) -> std::slice::Iter<'_, (String, JsonValue)> {
        self.pairs.iter()
    }
}
impl From<Vec<(String, JsonValue)>> for Object {
    fn from(pairs: Vec<(String, JsonValue)>) -> Self {
        let mut indices = HashMap::with_capacity(pairs.len());
        for (index, (key, _)) in pairs.iter().enumerate() {
            indices.entry(key.clone()).or_insert(index);
        }
        Self { pairs, indices }
    }
}
impl FromIterator<(String, JsonValue)> for Object {
    fn from_iter<T: IntoIterator<Item = (String, JsonValue)>>(iter: T) -> Self {
        let mut result = Self::new();
        for (k, v) in iter {
            result.insert(k, v);
        }
        result
    }
}
impl IntoIterator for Object {
    type Item = (String, JsonValue);
    type IntoIter = std::vec::IntoIter<Self::Item>;
    fn into_iter(self) -> Self::IntoIter {
        self.pairs.into_iter()
    }
}
impl<'a> IntoIterator for &'a Object {
    type Item = &'a (String, JsonValue);
    type IntoIter = std::slice::Iter<'a, (String, JsonValue)>;
    fn into_iter(self) -> Self::IntoIter {
        self.pairs.iter()
    }
}

impl JsonValue {
    pub fn object<const N: usize>(pairs: [(&str, JsonValue); N]) -> Self {
        Self::Object(pairs.into_iter().map(|(k, v)| (k.to_owned(), v)).collect())
    }
    pub fn as_str(&self) -> Option<&str> {
        if let Self::String(v) = self {
            Some(v)
        } else {
            None
        }
    }
    pub fn as_os_str(&self) -> Option<&std::ffi::OsStr> {
        match self {
            Self::String(value) => Some(std::ffi::OsStr::new(value)),
            Self::OsString(value) => Some(value),
            _ => None,
        }
    }
    pub fn contains_os_string(&self) -> bool {
        match self {
            Self::OsString(_) => true,
            Self::Array(values) => values.iter().any(Self::contains_os_string),
            Self::Object(values) => values.iter().any(|(_, value)| value.contains_os_string()),
            _ => false,
        }
    }
    /// Nested array and object levels: zero for a scalar, and one more than
    /// the deepest element for a container. A raw namespace value stays
    /// within `VALUE_DEPTH_MAX`.
    pub fn depth(&self) -> usize {
        match self {
            Self::Array(values) => 1 + values.iter().map(Self::depth).max().unwrap_or(0),
            Self::Object(values) => {
                1 + values
                    .iter()
                    .map(|(_, value)| value.depth())
                    .max()
                    .unwrap_or(0)
            }
            _ => 0,
        }
    }
    pub fn as_bool(&self) -> Option<bool> {
        if let Self::Bool(v) = self {
            Some(*v)
        } else {
            None
        }
    }
    pub fn as_i64(&self) -> Option<i64> {
        if let Self::Number(v) = self {
            v.parse().ok()
        } else {
            None
        }
    }
    pub fn as_u64(&self) -> Option<u64> {
        if let Self::Number(v) = self {
            v.parse().ok()
        } else {
            None
        }
    }
    pub fn as_array(&self) -> Option<&Vec<Self>> {
        if let Self::Array(v) = self {
            Some(v)
        } else {
            None
        }
    }
    pub fn as_object(&self) -> Option<&Object> {
        if let Self::Object(v) = self {
            Some(v)
        } else {
            None
        }
    }
    pub fn is_array(&self) -> bool {
        matches!(self, Self::Array(_))
    }
    pub fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }
    pub fn is_string(&self) -> bool {
        matches!(self, Self::String(_))
    }
    pub fn get(&self, key: &str) -> Option<&Self> {
        self.as_object()?.get(key)
    }
    pub fn write_json(&self, writer: &mut impl std::io::Write) -> std::io::Result<()> {
        match self {
            Self::Null => writer.write_all(b"null"),
            Self::Bool(value) => writer.write_all(if *value { b"true" } else { b"false" }),
            Self::Number(value) => writer.write_all(value.as_bytes()),
            Self::String(value) => write_string(value, writer),
            Self::OsString(value) => {
                writer.write_all(b"{\"$os_bytes\":")?;
                write_string(&base64(value.as_encoded_bytes()), writer)?;
                writer.write_all(b"}")
            }
            Self::Bytes(value) => {
                writer.write_all(b"{\"$bytes\":")?;
                write_string(&base64(value), writer)?;
                writer.write_all(b"}")
            }
            Self::Array(values) => {
                writer.write_all(b"[")?;
                for (i, value) in values.iter().enumerate() {
                    if i > 0 {
                        writer.write_all(b",")?;
                    }
                    value.write_json(writer)?;
                }
                writer.write_all(b"]")
            }
            Self::Object(pairs) => {
                writer.write_all(b"{")?;
                for (i, (key, value)) in pairs.iter().enumerate() {
                    if i > 0 {
                        writer.write_all(b",")?;
                    }
                    write_string(key, writer)?;
                    writer.write_all(b":")?;
                    value.write_json(writer)?;
                }
                writer.write_all(b"}")
            }
        }
    }
}
fn write_string(text: &str, writer: &mut impl std::io::Write) -> std::io::Result<()> {
    writer.write_all(b"\"")?;
    for c in text.chars() {
        match c {
            '"' => writer.write_all(b"\\\"")?,
            '\\' => writer.write_all(b"\\\\")?,
            '\n' => writer.write_all(b"\\n")?,
            '\r' => writer.write_all(b"\\r")?,
            '\t' => writer.write_all(b"\\t")?,
            '\u{8}' => writer.write_all(b"\\b")?,
            '\u{c}' => writer.write_all(b"\\f")?,
            c if c < ' ' => write!(writer, "\\u{:04x}", u32::from(c))?,
            _ => {
                let mut buffer = [0; 4];
                writer.write_all(c.encode_utf8(&mut buffer).as_bytes())?;
            }
        }
    }
    writer.write_all(b"\"")
}
impl std::fmt::Display for JsonValue {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let mut bytes = Vec::new();
        self.write_json(&mut bytes).map_err(|_| std::fmt::Error)?;
        let text = std::str::from_utf8(&bytes).map_err(|_| std::fmt::Error)?;
        f.write_str(text)
    }
}
impl std::ops::Index<&str> for JsonValue {
    type Output = Self;
    fn index(&self, key: &str) -> &Self {
        static NULL: JsonValue = JsonValue::Null;
        self.get(key).unwrap_or(&NULL)
    }
}
impl std::ops::Index<usize> for JsonValue {
    type Output = Self;
    fn index(&self, index: usize) -> &Self {
        static NULL: JsonValue = JsonValue::Null;
        self.as_array().and_then(|v| v.get(index)).unwrap_or(&NULL)
    }
}
impl From<&str> for JsonValue {
    fn from(value: &str) -> Self {
        Self::String(value.to_owned())
    }
}
impl From<String> for JsonValue {
    fn from(value: String) -> Self {
        Self::String(value)
    }
}
impl From<std::ffi::OsString> for JsonValue {
    fn from(value: std::ffi::OsString) -> Self {
        match value.into_string() {
            Ok(value) => Self::String(value),
            Err(value) => Self::OsString(value),
        }
    }
}
impl From<bool> for JsonValue {
    fn from(value: bool) -> Self {
        Self::Bool(value)
    }
}
impl From<i64> for JsonValue {
    fn from(value: i64) -> Self {
        Self::Number(value.to_string())
    }
}
impl From<i32> for JsonValue {
    fn from(value: i32) -> Self {
        Self::Number(value.to_string())
    }
}
impl From<u8> for JsonValue {
    fn from(value: u8) -> Self {
        Self::Number(value.to_string())
    }
}
impl<T: Into<JsonValue>> From<Option<T>> for JsonValue {
    fn from(value: Option<T>) -> Self {
        value.map_or(Self::Null, Into::into)
    }
}
impl<T: Into<JsonValue>> From<Vec<T>> for JsonValue {
    fn from(value: Vec<T>) -> Self {
        Self::Array(value.into_iter().map(Into::into).collect())
    }
}
impl PartialEq<&str> for JsonValue {
    fn eq(&self, other: &&str) -> bool {
        self.as_str() == Some(*other)
    }
}
impl PartialEq<str> for JsonValue {
    fn eq(&self, other: &str) -> bool {
        self.as_str() == Some(other)
    }
}

fn base64(bytes: &[u8]) -> String {
    const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut text = String::new();
    for chunk in bytes.chunks(3) {
        let a = chunk[0];
        let b = chunk.get(1).copied().unwrap_or(0);
        let c = chunk.get(2).copied().unwrap_or(0);
        text.push(char::from(ALPHABET[usize::from(a >> 2)]));
        text.push(char::from(ALPHABET[usize::from((a & 3) << 4 | b >> 4)]));
        text.push(if chunk.len() > 1 {
            char::from(ALPHABET[usize::from((b & 15) << 2 | c >> 6)])
        } else {
            '='
        });
        text.push(if chunk.len() > 2 {
            char::from(ALPHABET[usize::from(c & 63)])
        } else {
            '='
        });
    }
    text
}
