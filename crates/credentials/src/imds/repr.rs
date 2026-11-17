//! CPython's `repr` of ASCII `str`, for the message of its own that
//! botocore lets through with a value in it.

/// `repr(value)` of a `str`, exact while `value` is ASCII. CPython decides
/// which other characters to escape from the Unicode database, which is
/// not read here: they are left as they are.
pub(crate) fn text(value: &str) -> String {
    let quote = quote(value.as_bytes());
    let mut out = String::from(quote);
    for character in value.chars() {
        match u8::try_from(character) {
            Ok(byte) if byte.is_ascii() => escape(&mut out, byte, quote),
            _ => out.push(character),
        }
    }
    out.push(quote);
    out
}

/// A single quote, unless the value has one and no double quote.
fn quote(value: &[u8]) -> char {
    if value.contains(&b'\'') && !value.contains(&b'"') {
        '"'
    } else {
        '\''
    }
}

fn escape(out: &mut String, byte: u8, quote: char) {
    match byte {
        b'\\' => out.push_str("\\\\"),
        b'\t' => out.push_str("\\t"),
        b'\n' => out.push_str("\\n"),
        b'\r' => out.push_str("\\r"),
        b' '..=b'~' => {
            let character = char::from(byte);
            if character == quote {
                out.push('\\');
            }
            out.push(character);
        }
        _ => out.push_str(&format!("\\x{byte:02x}")),
    }
}

#[cfg(test)]
mod tests;
