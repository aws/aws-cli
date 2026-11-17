use super::printable::is_printable;

pub(super) fn lower(bytes: &[u8]) -> Vec<u8> {
    let mut result = Vec::with_capacity(bytes.len());
    for (code, encoded) in CodePoints(bytes) {
        if code == 0x212a {
            result.push(b'k');
        } else {
            result.extend(encoded.iter().map(u8::to_ascii_lowercase));
        }
    }
    result
}

struct CodePoints<'a>(&'a [u8]);

impl<'a> Iterator for CodePoints<'a> {
    type Item = (u32, &'a [u8]);

    fn next(&mut self) -> Option<Self::Item> {
        let first = *self.0.first()?;
        let width = match first {
            0xc2..=0xdf => 2,
            0xe0..=0xef => 3,
            0xf0..=0xf4 => 4,
            _ => 1,
        };
        if let Some(encoded) = self.0.get(..width)
            && let Ok(decoded) = std::str::from_utf8(encoded)
            && let Some(character) = decoded.chars().next()
        {
            self.0 = &self.0[width..];
            return Some((character as u32, encoded));
        }
        let encoded = &self.0[..1];
        self.0 = &self.0[1..];
        Some((0xdc00 + u32::from(first), encoded))
    }
}

pub(super) struct Words<'a> {
    remaining: &'a [u8],
}

impl<'a> Words<'a> {
    pub(super) fn new(bytes: &'a [u8]) -> Self {
        Self { remaining: bytes }
    }
}

impl<'a> Iterator for Words<'a> {
    type Item = &'a [u8];

    fn next(&mut self) -> Option<Self::Item> {
        while let Some(width) = whitespace_width(self.remaining) {
            self.remaining = &self.remaining[width..];
        }
        if self.remaining.is_empty() {
            return None;
        }
        let mut length = 0;
        while length < self.remaining.len() && whitespace_width(&self.remaining[length..]).is_none()
        {
            length += 1;
        }
        let (word, rest) = self.remaining.split_at(length);
        self.remaining = rest;
        Some(word)
    }
}

fn whitespace_width(bytes: &[u8]) -> Option<usize> {
    let (code, encoded) = CodePoints(bytes).next()?;
    matches!(code,
        0x09..=0x0d | 0x1c..=0x20 | 0x85 | 0xa0 | 0x1680 | 0x2000..=0x200a |
        0x2028 | 0x2029 | 0x202f | 0x205f | 0x3000
    )
    .then_some(encoded.len())
}

/// `repr()` of a str as CPython spells it, the bytes decoded as CPython
/// decodes a path: UTF-8, with each byte of an invalid sequence its own lone
/// surrogate. It quotes with `"` when only `'` occurs and with `'` otherwise,
/// escaping that quote, backslashes, and what `str.isprintable` rejects.
pub(crate) fn repr(bytes: &[u8]) -> Vec<u8> {
    let quote = if bytes.contains(&b'\'') && !bytes.contains(&b'"') {
        b'"'
    } else {
        b'\''
    };
    let mut result = vec![quote];
    for (code, encoded) in CodePoints(bytes) {
        write_escaped(&mut result, quote, code, encoded);
    }
    result.push(quote);
    result
}

fn write_escaped(result: &mut Vec<u8>, quote: u8, code: u32, encoded: &[u8]) {
    let byte = match u8::try_from(code) {
        Ok(byte) if byte.is_ascii() => byte,
        _ => return write_escaped_wide(result, code, encoded),
    };
    match byte {
        _ if byte == quote || byte == b'\\' => result.extend_from_slice(&[b'\\', byte]),
        b'\t' => result.extend_from_slice(b"\\t"),
        b'\n' => result.extend_from_slice(b"\\n"),
        b'\r' => result.extend_from_slice(b"\\r"),
        ..b' ' | 0x7f => result.extend_from_slice(format!("\\x{byte:02x}").as_bytes()),
        _ => result.push(byte),
    }
}

/// One code point past ASCII of a `repr`: itself when printable, else the
/// shortest of the `\x`, `\u` and `\U` escapes that holds it.
fn write_escaped_wide(result: &mut Vec<u8>, code: u32, encoded: &[u8]) {
    if is_printable(code) {
        result.extend_from_slice(encoded);
        return;
    }
    let escape = if code <= 0xff {
        format!("\\x{code:02x}")
    } else if code <= 0xffff {
        format!("\\u{code:04x}")
    } else {
        format!("\\U{code:08x}")
    };
    result.extend_from_slice(escape.as_bytes());
}

#[cfg(test)]
mod tests;
