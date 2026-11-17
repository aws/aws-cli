use crate::output::*;
use std::io::{self, Write};
const TEXT_PAGE: usize = 4096;
#[test]
fn raw_sizes() {
    for (size, text) in [
        (0, "0"),
        (1, "1"),
        (1023, "1023"),
        (1024, "1024"),
        (u64::MAX, "18446744073709551615"),
    ] {
        assert_eq!(format_size(size, false), text);
    }
}
#[test]
fn human_readable_bytes_singular_and_plural() {
    for (size, text) in [
        (0, "0 Bytes"),
        (1, "1 Byte"),
        (2, "2 Bytes"),
        (1023, "1023 Bytes"),
        (1024, "1.0 KiB"),
        (u64::MAX, "16.0 EiB"),
    ] {
        assert_eq!(format_size(size, true), text);
    }
}
#[test]
fn suffix_transitions_round_at_boundaries() {
    for (power, suffix) in [
        (10, "KiB"),
        (20, "MiB"),
        (30, "GiB"),
        (40, "TiB"),
        (50, "PiB"),
        (60, "EiB"),
    ] {
        let boundary = 1_u64 << power;
        assert_eq!(
            format_size(boundary - 1, true),
            if power == 10 {
                "1023 Bytes".into()
            } else {
                format!("1.0 {suffix}")
            }
        );
        assert_eq!(format_size(boundary, true), format!("1.0 {suffix}"));
        assert_eq!(format_size(boundary + 1, true), format!("1.0 {suffix}"));
    }
}
#[test]
fn sizes_round_to_nearest_tenth() {
    for (power, suffix) in [
        (10, "KiB"),
        (20, "MiB"),
        (30, "GiB"),
        (40, "TiB"),
        (50, "PiB"),
        (60, "EiB"),
    ] {
        let unit = 1_u64 << power;
        assert_eq!(
            format_size(unit + unit / 20, true),
            format!("{} {suffix}", if power == 60 { "1.1" } else { "1.0" })
        );
        assert_eq!(
            format_size(unit + unit / 20 + 1, true),
            format!("1.1 {suffix}")
        );
    }
}
#[test]
fn sizes_match_awscli_at_ties_and_unit_boundaries() {
    for (size, expected) in [
        (1075, "1.0 KiB"),
        (1076, "1.1 KiB"),
        (1280, "1.2 KiB"),
        (1331, "1.3 KiB"),
        (1433, "1.4 KiB"),
        (7168, "7.0 KiB"),
        (1_048_063, "1023.5 KiB"),
        (1_048_064, "1.0 MiB"),
        (1_048_166, "1.0 MiB"),
        (1_310_720, "1.2 MiB"),
        (1_363_148, "1.3 MiB"),
        (20_971_520, "20.0 MiB"),
        (1_342_177_280, "1.2 GiB"),
        (1_098_974_756_863, "1023.5 GiB"),
        (1_098_974_756_864, "1.0 TiB"),
        (1_125_350_151_028_736, "1.0 PiB"),
        (1_151_796_154_455_818_240, "1023.0 PiB"),
        (9_007_199_254_740_993, "8.0 PiB"),
        (17_293_822_569_102_704_640, "15.0 EiB"),
    ] {
        assert_eq!(format_size(size, true), expected, "{size}");
    }
}
#[test]
fn rates_truncate_below_a_kib_and_round_the_exact_double_above() {
    for (rate, expected) in [
        (0.0, "0 Bytes"),
        (0.5, "0 Bytes"),
        (1.0, "1 Byte"),
        (1.5, "1 Bytes"),
        (2.5, "2 Bytes"),
        (5.9, "5 Bytes"),
        (1023.9, "1023 Bytes"),
        (1075.2, "1.1 KiB"),
        (1280.0, "1.2 KiB"),
        (1536.0, "1.5 KiB"),
        (1587.2, "1.6 KiB"),
        (1587.1999999999998, "1.5 KiB"),
        (7168.0, "7.0 KiB"),
        (1048063.9, "1023.5 KiB"),
        (1048063.99, "1023.5 KiB"),
    ] {
        assert_eq!(format_human_readable_rate(rate), expected, "{rate}");
    }
}
#[test]
fn summary_sizes_above_object_range() {
    assert_eq!(
        format_summary_size(u128::from(u64::MAX) + 1, false),
        "18446744073709551616"
    );
    assert_eq!(
        format_summary_size(u128::MAX, false),
        "340282366920938463463374607431768211455"
    );
    assert_eq!(
        format_summary_size(u128::from(u64::MAX) + 1, true),
        "16.0 EiB"
    );
    assert_eq!(format_summary_size(u128::MAX, true), "16.0 EiB");
}
#[test]
fn right_alignment_only_pads_short_values() {
    for (width, expected) in [(5, b"  abc".as_slice()), (3, b"abc"), (2, b"abc")] {
        let mut out = Vec::new();
        print_right_aligned(&mut out, width, b"abc").unwrap();
        assert_eq!(out, expected);
    }
}
#[test]
fn entry_dates_handle_present_missing_negative_wide_components() {
    for (date, expected) in [
        (
            EntryDate {
                present: true,
                year: 2026,
                month: 7,
                day: 2,
                hour: 3,
                minute: 4,
                second: 5,
            },
            "2026-07-02 03:04:05",
        ),
        (
            EntryDate {
                year: 9999,
                month: 99,
                ..EntryDate::default()
            },
            "0000-00-00 00:00:00",
        ),
        (
            EntryDate {
                present: true,
                year: -1,
                month: -2,
                day: -3,
                hour: -4,
                minute: -5,
                second: -6,
            },
            "0000-00-00 00:00:00",
        ),
        (
            EntryDate {
                present: true,
                year: 12345,
                month: 123,
                day: 456,
                hour: 78,
                minute: 901,
                second: 2345,
            },
            "12345-123-456 78:901:2345",
        ),
    ] {
        let mut out = Vec::new();
        print_entry_date(&mut out, date).unwrap();
        assert_eq!(out, expected.as_bytes());
    }
}
#[test]
fn object_and_prefix_basename_semantics() {
    for (input, expected) in [
        ("file.txt", "file.txt"),
        ("dir/file.txt", "file.txt"),
        ("dir///file.txt", "file.txt"),
        ("dir/", ""),
    ] {
        assert_eq!(basename_for_object(input.as_bytes()), expected.as_bytes());
    }
    for (input, expected) in [("dir/", "dir"), ("parent/dir////", ""), ("////", "")] {
        assert_eq!(
            basename_for_common_prefix(input.as_bytes()),
            expected.as_bytes()
        );
    }
}
#[test]
fn empty_and_nonempty_entry_names() {
    assert_eq!(entry_name(b""), b"");
    assert_eq!(entry_name(b"prefix/object.txt"), b"prefix/object.txt");
}

fn write_mixed_endings(out: &mut impl Write) -> io::Result<()> {
    out.write_all(b"progress\rdone\n")?;
    out.write_all(b"\n\n\n")?;
    out.write_all(b"tail")?;
    out.write_all("x\n".repeat(3000).as_bytes())?;
    out.flush()
}
fn mixed_endings_with_crlf() -> Vec<u8> {
    let mut expected = b"progress\rdone\r\n\r\n\r\n\r\ntail".to_vec();
    expected.extend_from_slice("x\r\n".repeat(3000).as_bytes());
    expected
}
#[derive(Default)]
struct OneByte {
    written: Vec<u8>,
    calls: usize,
}
impl Write for OneByte {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        let Some(&byte) = buf.first() else {
            return Ok(0);
        };
        self.written.push(byte);
        self.calls += 1;
        Ok(1)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
struct Failing {
    capacity: usize,
    written: Vec<u8>,
}
impl Write for Failing {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if self.written.len() == self.capacity {
            return Err(io::Error::new(io::ErrorKind::BrokenPipe, "reader closed"));
        }
        let count = buf.len().min(self.capacity - self.written.len());
        self.written.extend_from_slice(&buf[..count]);
        Ok(count)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
fn expect_cause(error: &io::Error) {
    assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
    assert_eq!(error.to_string(), "reader closed");
}

#[test]
fn crlf_writer_ends_each_line_with_crlf_and_keeps_bare_carriage_returns() {
    let expected = mixed_endings_with_crlf();
    for size in [1, 7, 4096, 16384] {
        let mut written = Vec::new();
        let stream = TextStream::with_translation(&mut written, true);
        write_mixed_endings(&mut io::BufWriter::with_capacity(size, stream)).unwrap();
        assert_eq!(written, expected, "buffer {size}");
    }
    let mut written = Vec::new();
    write_mixed_endings(&mut TextStream::with_translation(&mut written, true)).unwrap();
    assert_eq!(written, expected);
}
#[test]
fn crlf_writer_reports_whole_writes_over_a_short_writing_stream() {
    let mut inner = OneByte::default();
    let mut stream = TextStream::with_translation(&mut inner, true);
    assert_eq!(stream.write(b"a\rb\nc\n").unwrap(), 6);
    write_mixed_endings(&mut stream).unwrap();
    let mut expected = b"a\rb\r\nc\r\n".to_vec();
    expected.extend(mixed_endings_with_crlf());
    assert_eq!(inner.written, expected);
    assert_eq!(inner.calls, expected.len());
}
#[test]
fn untranslated_writer_is_the_inner_writer() {
    let mut inner = OneByte::default();
    let mut stream = TextStream::with_translation(&mut inner, false);
    assert_eq!(stream.write(b"a\rb\n").unwrap(), 1);
    write_mixed_endings(&mut stream).unwrap();
    let mut expected = b"a".to_vec();
    expected.extend_from_slice(b"progress\rdone\n\n\n\ntail");
    expected.extend_from_slice("x\n".repeat(3000).as_bytes());
    assert_eq!(inner.written, expected);
}
#[test]
fn stream_writer_translates_newlines_only_where_the_fallback_does() {
    let mut written = Vec::new();
    TextStream::new(&mut written)
        .write_all(b"a\rb\nc\n")
        .unwrap();
    let expected: &[u8] = if STREAMS_TRANSLATE_NEWLINES {
        b"a\rb\r\nc\r\n"
    } else {
        b"a\rb\nc\n"
    };
    assert_eq!(written, expected);
}
#[test]
fn crlf_writer_keeps_the_cause_of_a_failed_write() {
    for capacity in [0, 4, 5, TEXT_PAGE] {
        let mut inner = Failing {
            capacity,
            written: Vec::new(),
        };
        let mut stream = TextStream::with_translation(&mut inner, true);
        let line = "line\n".repeat(TEXT_PAGE);
        expect_cause(&stream.write(line.as_bytes()).unwrap_err());
        expect_cause(&stream.write_all(b"line\n").unwrap_err());
        let mut buffered = io::BufWriter::with_capacity(8, stream);
        buffered.write_all(b"line\n").unwrap();
        expect_cause(&buffered.flush().unwrap_err());
        drop(buffered);
        let mut prefix = "line\r\n".repeat(TEXT_PAGE).into_bytes();
        prefix.truncate(capacity);
        assert_eq!(inner.written, prefix);
    }
}
#[derive(Debug, Default)]
struct Descriptor {
    written: Vec<u8>,
    accepts: Option<usize>,
    writes_left: Option<usize>,
}
impl Write for Descriptor {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if self.writes_left == Some(0) {
            return Err(io::ErrorKind::BrokenPipe.into());
        }
        self.writes_left = self.writes_left.map(|left| left - 1);
        let count = self
            .accepts
            .map_or(buf.len(), |accepts| accepts.min(buf.len()));
        self.written.extend_from_slice(&buf[..count]);
        Ok(count)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[test]
fn buffered_stream_writes_only_when_flushed_or_full() {
    let mut stream = BufferedStream::new(Descriptor::default(), 8);
    stream.write_all(b"abc").unwrap();
    stream.write_all(b"defgh").unwrap();
    assert!(stream.get_ref().written.is_empty());
    assert_eq!(stream.buffered(), b"abcdefgh");
    stream.write_all(b"ij").unwrap();
    assert_eq!(stream.get_ref().written, b"abcdefgh");
    stream.flush().unwrap();
    assert_eq!(stream.get_ref().written, b"abcdefghij");
    assert!(stream.buffered().is_empty() && stream.last_error().is_none());
    stream.write_all(b"0123456789").unwrap();
    assert_eq!(stream.get_ref().written, b"abcdefghij01234567");
    assert_eq!(stream.buffered(), b"89");
}
#[test]
fn buffered_stream_keeps_a_full_buffer_of_a_refused_statement_longer_than_it() {
    let mut stream = BufferedStream::new(
        Descriptor {
            writes_left: Some(0),
            ..Descriptor::default()
        },
        8,
    );
    let error = stream.write_all(b"0123456789abcdef").unwrap_err();
    assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
    assert_eq!(stream.buffered(), b"01234567");
    assert!(stream.get_ref().written.is_empty());
    assert!(stream.flush().is_err());
    assert_eq!(stream.buffered(), b"01234567");
}
#[test]
fn buffered_stream_keeps_what_a_failed_flush_left() {
    let mut stream = BufferedStream::new(
        Descriptor {
            accepts: Some(2),
            writes_left: Some(1),
            ..Descriptor::default()
        },
        8,
    );
    stream.write_all(b"abcdef").unwrap();
    let error = stream.flush().unwrap_err();
    assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
    assert_eq!(
        stream.last_error().unwrap().kind(),
        io::ErrorKind::BrokenPipe
    );
    assert_eq!(stream.get_ref().written, b"ab");
    assert_eq!(stream.buffered(), b"cdef");
    stream.write_all(b"g").unwrap();
    assert_eq!(stream.buffered(), b"cdefg");
    assert!(stream.write_all(b"hijk").is_err());
    assert_eq!(stream.buffered(), b"cdefg");
    *stream.get_mut() = Descriptor::default();
    stream.flush().unwrap();
    assert_eq!(stream.get_ref().written, b"cdefg");
}
