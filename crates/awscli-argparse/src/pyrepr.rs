//! Python diagnostic string representation and code-point precision.
use crate::Value;
const HEX_DIGITS: &[u8; 16] = b"0123456789abcdef";
/// Quote strings with Python's ASCII escaping and printable Unicode policy.
pub fn repr(text: &str) -> String {
    let mut output = Vec::with_capacity(text.len() + 2);
    write(text.as_bytes(), &mut output);
    into_text(output)
}
/// Quote a string as Python does for ASCII, preserving non-ASCII UTF-8;
/// every repr in this module builds on it. Text reads as Python decodes
/// argv, so each byte outside a valid UTF-8 sequence is its lone
/// surrogate's `\udcXX` escape.
pub fn write(value: &[u8], output: &mut Vec<u8>) {
    let quote = choose_quote(value);
    output.push(quote);
    decode_bytes(value, |piece| match piece {
        Piece::Text(text) => write_escaped(text.as_bytes(), quote, output),
        Piece::Surrogate(unit) => output.extend_from_slice(escaped_surrogate(unit).as_bytes()),
    });
    output.push(quote);
}
/// The repr of an argv value as [`write`] spells it, from the value's
/// encoded bytes. On Windows those are WTF-8, so an unpaired UTF-16
/// surrogate there is three escapes, one per byte of its encoding, where
/// CPython writes one.
pub fn argv(value: &std::ffi::OsStr) -> String {
    let mut output = Vec::with_capacity(value.len() + 2);
    write(value.as_encoded_bytes(), &mut output);
    into_text(output)
}
/// `text` as Python's stderr writes it: UTF-8 under the `backslashreplace`
/// handler, which spells the surrogate a byte outside a valid sequence
/// decodes to as `\udcXX`. Callers pass an argv value's encoded bytes, as
/// for [`argv`].
pub fn backslash_replaced(text: &[u8]) -> String {
    let mut output = String::with_capacity(text.len());
    decode_bytes(text, |piece| match piece {
        Piece::Text(valid) => output.push_str(valid),
        Piece::Surrogate(unit) => output.push_str(&escaped_surrogate(unit)),
    });
    output
}
/// Python's `len()` of `text` as it decodes argv: each valid UTF-8 sequence
/// is one code point, and so is each byte outside one.
pub fn code_point_count(text: &[u8]) -> usize {
    let mut count = 0;
    decode_bytes(text, |piece| match piece {
        Piece::Text(valid) => count += valid.chars().count(),
        Piece::Surrogate(_) => count += 1,
    });
    count
}
fn write_escaped(value: &[u8], quote: u8, output: &mut Vec<u8>) {
    let mut buffer = [0; 4];
    for &byte in value {
        output.extend_from_slice(escape(&mut buffer, byte, quote));
    }
}
/// Python's quote selection: double quotes only when the string contains a
/// single quote and no double quote.
fn choose_quote(value: &[u8]) -> u8 {
    if value.contains(&b'\'') && !value.contains(&b'"') {
        b'"'
    } else {
        b'\''
    }
}
fn escape(buffer: &mut [u8; 4], byte: u8, quote: u8) -> &[u8] {
    if byte == quote || byte == b'\\' {
        *buffer = [b'\\', byte, 0, 0];
        return &buffer[..2];
    }
    match byte {
        b'\n' => b"\\n",
        b'\r' => b"\\r",
        b'\t' => b"\\t",
        0..=8 | 11 | 12 | 14..=31 | 127 => hex_escape(buffer, byte),
        _ => {
            buffer[0] = byte;
            &buffer[..1]
        }
    }
}
fn hex_escape(buffer: &mut [u8; 4], byte: u8) -> &[u8] {
    *buffer = [
        b'\\',
        b'x',
        HEX_DIGITS[usize::from(byte >> 4)],
        HEX_DIGITS[usize::from(byte & 0xf)],
    ];
    buffer
}
#[expect(
    clippy::expect_used,
    reason = "escapes are ASCII and every other byte is copied from UTF-8 text"
)]
fn into_text(output: Vec<u8>) -> String {
    String::from_utf8(output).expect("a repr of UTF-8 text is UTF-8")
}
/// One run of an operating-system string as CPython decodes it with the
/// surrogateescape error handler: decodable text, or the lone surrogate
/// code point that stands for one undecodable byte (on Windows, one
/// unpaired UTF-16 surrogate).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Piece<'a> {
    Text(&'a str),
    Surrogate(u16),
}
/// Visit `text` as CPython's surrogateescape decoding sees it, in order.
pub fn decode_os(text: &std::ffi::OsStr, mut each: impl FnMut(Piece<'_>)) {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        decode_bytes(text.as_bytes(), &mut each);
    }
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        for unit in char::decode_utf16(text.encode_wide()) {
            match unit {
                Ok(character) => {
                    let mut buffer = [0; 4];
                    each(Piece::Text(character.encode_utf8(&mut buffer)));
                }
                Err(error) => each(Piece::Surrogate(error.unpaired_surrogate())),
            }
        }
    }
}
/// Visit `bytes` as CPython's surrogateescape decoding of POSIX argv sees
/// them, in order: each run of valid UTF-8 is text, and each byte outside a
/// valid sequence is the lone surrogate `0xdc00` plus the byte.
#[expect(
    clippy::expect_used,
    reason = "UTF-8 validation guarantees the selected prefix"
)]
pub fn decode_bytes(mut bytes: &[u8], mut each: impl FnMut(Piece<'_>)) {
    while !bytes.is_empty() {
        let (valid, invalid) = match std::str::from_utf8(bytes) {
            Ok(valid) => (valid, 0),
            Err(error) => (
                std::str::from_utf8(&bytes[..error.valid_up_to()])
                    .expect("UTF-8 validator supplied the valid prefix"),
                error
                    .error_len()
                    .unwrap_or(bytes.len() - error.valid_up_to()),
            ),
        };
        if !valid.is_empty() {
            each(Piece::Text(valid));
        }
        bytes = &bytes[valid.len()..];
        for byte in &bytes[..invalid] {
            each(Piece::Surrogate(0xdc00 + u16::from(*byte)));
        }
        bytes = &bytes[invalid..];
    }
}
/// The `\uXXXX` text that both repr and a backslashreplace stream write for
/// a lone surrogate: `\udcff` for the escaped byte 0xFF.
pub fn escaped_surrogate(unit: u16) -> String {
    format!("\\u{unit:04x}")
}
/// Python's repr of an operating-system value that CPython decoded with
/// surrogateescape: each undecodable byte (on Windows, each unpaired UTF-16
/// surrogate) is its lone surrogate's `\udcXX` escape, which is the text
/// upstream prints for such a path. On Windows this decodes UTF-16, as
/// CPython does, where [`argv`] spells an argv value's WTF-8 bytes.
pub fn os(text: &std::ffi::OsStr) -> String {
    let quote = choose_quote(text.as_encoded_bytes());
    let mut output = vec![quote];
    decode_os(text, |piece| match piece {
        Piece::Text(valid) => write_escaped(valid.as_bytes(), quote, &mut output),
        Piece::Surrogate(unit) => output.extend_from_slice(escaped_surrogate(unit).as_bytes()),
    });
    output.push(quote);
    into_text(output)
}
/// Python's repr of a bytes object: `b` and the quoted value, with every
/// byte outside printable ASCII spelled `\xNN`.
pub fn bytes(value: &[u8]) -> String {
    let quote = choose_quote(value);
    let mut output = vec![b'b', quote];
    let mut buffer = [0; 4];
    for &byte in value {
        output.extend_from_slice(if byte.is_ascii() {
            escape(&mut buffer, byte, quote)
        } else {
            hex_escape(&mut buffer, byte)
        });
    }
    output.push(quote);
    into_text(output)
}
/// CPython precision applies to rendered code points, including escapes.
pub fn limited(text: impl AsRef<std::ffi::OsStr>, limit: usize) -> String {
    argv(text.as_ref()).chars().take(limit).collect()
}
/// Python representation of nested JSON, preserving insertion order.
pub fn value(value: &Value, ordered: bool) -> String {
    match value {
        Value::Null => "None".into(),
        Value::Bool(v) => if *v { "True" } else { "False" }.into(),
        Value::Number(v) => v.to_string(),
        Value::String(v) => repr(v),
        Value::OsString(v) => os(v),
        Value::Bytes(v) => bytes(v),
        Value::Array(v) => format!(
            "[{}]",
            v.iter()
                .map(|x| self::value(x, ordered))
                .collect::<Vec<_>>()
                .join(", ")
        ),
        Value::Object(v) => {
            let body = v
                .iter()
                .map(|(k, v)| format!("{}: {}", repr(k), self::value(v, ordered)))
                .collect::<Vec<_>>()
                .join(", ");
            if ordered {
                if v.is_empty() {
                    "OrderedDict()".into()
                } else {
                    format!("OrderedDict({{{body}}})")
                }
            } else {
                format!("{{{body}}}")
            }
        }
    }
}
#[cfg(test)]
mod tests;
