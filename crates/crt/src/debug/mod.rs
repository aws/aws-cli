//! Native diagnostics using Python's logger names and record framing.
use std::{
    ffi::OsStr,
    io::{self, Write},
};

/// Writes the selected source's ASCII repr escapes while retaining native path bytes.
pub fn write_arguments(mut writer: impl Write, argv: &[impl AsRef<OsStr>]) -> io::Result<()> {
    writer.write_all(b"Arguments entered to CLI: [")?;
    for (index, arg) in argv.iter().enumerate() {
        if index != 0 {
            writer.write_all(b", ")?;
        }
        write_repr(&mut writer, arg.as_ref())?;
    }
    writer.write_all(b"]")
}
fn write_repr(writer: &mut impl Write, text: &OsStr) -> io::Result<()> {
    let bytes = text.as_encoded_bytes();
    let quote = if bytes.contains(&b'\'') && !bytes.contains(&b'"') {
        b'"'
    } else {
        b'\''
    };
    writer.write_all(&[quote])?;
    for &byte in bytes {
        match byte {
            b'\n' => writer.write_all(b"\\n")?,
            b'\r' => writer.write_all(b"\\r")?,
            b'\t' => writer.write_all(b"\\t")?,
            b'\\' => writer.write_all(b"\\\\")?,
            value if value == quote => writer.write_all(&[b'\\', value])?,
            value if value.is_ascii_control() => write!(writer, "\\x{value:02x}")?,
            value => writer.write_all(&[value])?,
        }
    }
    writer.write_all(&[quote])
}
mod native;
#[doc(inline)]
pub use native::Logger;
#[cfg(test)]
mod tests;
