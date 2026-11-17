//! Standard text streams and byte-preserving S3 listing names, dates, sizes,
//! and alignment.
#![forbid(unsafe_code)]
use std::io::{self, Write};

/// Whether the standard streams write each `\n` as CRLF. CPython opens
/// `sys.stdout` and `sys.stderr` with `newline=None` on Windows, so every line
/// the Python fallback prints there ends in CRLF, and the native path writes
/// the same bytes.
pub const STREAMS_TRANSLATE_NEWLINES: bool = cfg!(windows);
const TEXT_PAGE_BYTES: usize = 4096;

/// A standard stream with the line endings of `STREAMS_TRANSLATE_NEWLINES`.
///
/// Translation is stateless, as in a text-mode CPython stream: every `\n`
/// becomes `\r\n`, even one a `\r` precedes, and a bare `\r`, such as a
/// progress redraw, is left alone. The native path writes no binary payload to
/// either stream; `s3 cp` to or from `-` routes to Python.
pub struct TextStream<W: Write> {
    inner: W,
    translate: bool,
    page: [u8; TEXT_PAGE_BYTES],
    end: usize,
}
impl<W: Write> TextStream<W> {
    /// Wraps a standard stream with the host's line endings.
    pub fn new(inner: W) -> Self {
        Self::with_translation(inner, STREAMS_TRANSLATE_NEWLINES)
    }
    /// Wraps `inner`, writing each `\n` as CRLF only when `translate` is set.
    pub fn with_translation(inner: W, translate: bool) -> Self {
        Self {
            inner,
            translate,
            page: [0; TEXT_PAGE_BYTES],
            end: 0,
        }
    }
    fn append(&mut self, mut bytes: &[u8]) -> io::Result<()> {
        while !bytes.is_empty() {
            if self.end == self.page.len() {
                self.drain()?;
            }
            let count = bytes.len().min(self.page.len() - self.end);
            self.page[self.end..self.end + count].copy_from_slice(&bytes[..count]);
            self.end += count;
            bytes = &bytes[count..];
        }
        Ok(())
    }
    fn drain(&mut self) -> io::Result<()> {
        let end = std::mem::take(&mut self.end);
        self.inner.write_all(&self.page[..end])
    }
    fn translate_all(&mut self, buf: &[u8]) -> io::Result<()> {
        let mut lines = buf.split(|&byte| byte == b'\n');
        if let Some(first) = lines.next() {
            self.append(first)?;
        }
        for line in lines {
            self.append(b"\r\n")?;
            self.append(line)?;
        }
        self.drain()
    }
}
impl<W: Write + std::fmt::Debug> std::fmt::Debug for TextStream<W> {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.debug_struct("TextStream")
            .field("inner", &self.inner)
            .field("translate", &self.translate)
            .finish_non_exhaustive()
    }
}
impl<W: Write> Write for TextStream<W> {
    /// Without translation this is the inner writer's own write. With it, all
    /// of `buf` is written or the call fails with the inner writer's error: a
    /// partial count could separate an inserted `\r` from its `\n`.
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if !self.translate {
            return self.inner.write(buf);
        }
        self.translate_all(buf).map(|()| buf.len())
    }
    fn write_vectored(&mut self, bufs: &[io::IoSlice<'_>]) -> io::Result<usize> {
        if !self.translate {
            return self.inner.write_vectored(bufs);
        }
        let buf = bufs
            .iter()
            .find(|buf| !buf.is_empty())
            .map_or(&[][..], |buf| &**buf);
        self.write(buf)
    }
    fn write_all(&mut self, buf: &[u8]) -> io::Result<()> {
        if !self.translate {
            return self.inner.write_all(buf);
        }
        self.translate_all(buf)
    }
    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}
/// A standard stream as CPython buffers it, `io.BufferedWriter` over the
/// descriptor: a write that fits joins the buffer, and one that does not
/// first flushes the buffer and is dropped when that fails. A flush that
/// fails keeps the bytes the descriptor did not take, so they wait for a
/// later flush, as the output a failed write leaves waits for the flush of
/// `sys.stdout` at exit. Dropping the stream writes nothing; the caller
/// decides whether what it kept is written again.
pub struct BufferedStream<W: Write> {
    inner: W,
    buffer: Vec<u8>,
    capacity: usize,
    error: Option<io::Error>,
}
impl<W: Write> BufferedStream<W> {
    /// Buffers up to `capacity` bytes for `inner`.
    pub fn new(inner: W, capacity: usize) -> Self {
        Self {
            inner,
            buffer: Vec::with_capacity(capacity),
            capacity,
            error: None,
        }
    }
    /// The bytes buffered and not yet written.
    pub fn buffered(&self) -> &[u8] {
        &self.buffer
    }
    /// The error of the last write or flush that failed, if any did.
    pub fn last_error(&self) -> Option<&io::Error> {
        self.error.as_ref()
    }
    pub fn get_ref(&self) -> &W {
        &self.inner
    }
    /// Drops what the buffer holds and the last error, leaving the stream as
    /// a new one over `inner`.
    pub fn discard(&mut self) {
        self.buffer.clear();
        self.error = None;
    }
    pub fn get_mut(&mut self) -> &mut W {
        &mut self.inner
    }
    fn flush_buffer(&mut self) -> io::Result<()> {
        let mut written = 0;
        let mut result = Ok(());
        while written < self.buffer.len() {
            match self.inner.write(&self.buffer[written..]) {
                Ok(0) => {
                    result = Err(io::ErrorKind::WriteZero.into());
                    break;
                }
                Ok(count) => written += count,
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(error) => {
                    result = Err(error);
                    break;
                }
            }
        }
        self.buffer.drain(..written);
        result.map_err(|error| self.record(error))
    }
    fn record(&mut self, error: io::Error) -> io::Error {
        self.error = Some(error.raw_os_error().map_or_else(
            || io::Error::from(error.kind()),
            io::Error::from_raw_os_error,
        ));
        error
    }
}
impl<W: Write> std::fmt::Debug for BufferedStream<W> {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.debug_struct("BufferedStream")
            .field("buffered", &self.buffer.len())
            .field("capacity", &self.capacity)
            .field("error", &self.error)
            .finish_non_exhaustive()
    }
}
impl<W: Write> Write for BufferedStream<W> {
    /// Takes all of `buf` into the buffer when it fits, flushing first when
    /// it does not. A `buf` larger than the whole buffer fills it and drains
    /// it, so a drain that fails keeps the bytes it could not write for the
    /// flush at exit; the rest of `buf` is not taken.
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if buf.len() > self.capacity - self.buffer.len() {
            self.flush_buffer()?;
        }
        if buf.len() > self.capacity {
            if self.capacity == 0 {
                return self.inner.write(buf).map_err(|error| self.record(error));
            }
            self.buffer.extend_from_slice(&buf[..self.capacity]);
            self.flush_buffer()?;
            return Ok(self.capacity);
        }
        self.buffer.extend_from_slice(buf);
        Ok(buf.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        self.flush_buffer()?;
        self.inner.flush().map_err(|error| self.record(error))
    }
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct EntryDate {
    pub present: bool,
    pub year: i32,
    pub month: i32,
    pub day: i32,
    pub hour: i32,
    pub minute: i32,
    pub second: i32,
}
/// Flushes diagnostic output through the injected destination.
///
/// # Errors
/// Propagates write and flush failures.
pub fn print_stderr(out: &mut impl Write, args: std::fmt::Arguments<'_>) -> io::Result<()> {
    out.write_fmt(args)?;
    out.flush()
}
pub fn entry_name(name: &[u8]) -> &[u8] {
    name
}
/// Writes `YYYY-MM-DD HH:MM:SS`, keeping a wide component whole and clamping a
/// negative one to zero; an absent date is all zeros.
///
/// # Errors
/// Propagates destination write failures.
pub fn print_entry_date(out: &mut impl Write, date: EntryDate) -> io::Result<()> {
    if !date.present {
        return out.write_all(b"0000-00-00 00:00:00");
    }
    write!(
        out,
        "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
        date.year.max(0),
        date.month.max(0),
        date.day.max(0),
        date.hour.max(0),
        date.minute.max(0),
        date.second.max(0)
    )
}
/// Right-aligns by byte length.
///
/// # Errors
/// Propagates destination write failures.
pub fn print_right_aligned(out: &mut impl Write, width: usize, value: &[u8]) -> io::Result<()> {
    for _ in value.len()..width {
        out.write_all(b" ")?;
    }
    out.write_all(value)
}
pub fn basename_for_object(key: &[u8]) -> &[u8] {
    key.iter()
        .rposition(|&byte| byte == b'/')
        .map_or(key, |index| &key[index + 1..])
}
pub fn basename_for_common_prefix(prefix: &[u8]) -> &[u8] {
    let Some(index) = prefix.iter().rposition(|&byte| byte == b'/') else {
        return prefix;
    };
    let preceding = &prefix[..index];
    preceding
        .iter()
        .rposition(|&byte| byte == b'/')
        .map_or(preceding, |index| &preceding[index + 1..])
}
pub fn format_size(size: u64, human_readable: bool) -> String {
    if human_readable {
        human_size(size)
    } else {
        size.to_string()
    }
}
pub fn format_summary_size(size: u128, human_readable: bool) -> String {
    if human_readable {
        human_size(size.min(u128::from(u64::MAX)) as u64)
    } else {
        size.to_string()
    }
}
fn human_size(size: u64) -> String {
    format_human_readable_rate(size as f64)
}
/// The Python CLI formats a byte rate and a human-readable size alike.
pub fn format_human_readable_rate(mut value: f64) -> String {
    if value == 1.0 {
        return "1 Byte".to_owned();
    }
    if value < 1024.0 {
        return format!("{} Bytes", value as u64);
    }
    let suffixes = ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB"];
    let mut index = 0;
    value /= 1024.0;
    while value.round_ties_even() >= 1024.0 && index + 1 < suffixes.len() {
        index += 1;
        value /= 1024.0;
    }
    format!("{value:.1} {}", suffixes[index])
}
