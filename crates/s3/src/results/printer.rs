use super::{Event, Recorder};
use std::borrow::Cow;
use std::io::{self, Write};
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum Mode {
    #[default]
    Full,
    NoProgress,
    OnlyErrors,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PrinterConfig {
    pub mode: Mode,
    pub frequency_s: i64,
    pub oneline: bool,
}
impl Default for PrinterConfig {
    fn default() -> Self {
        Self {
            mode: Mode::Full,
            frequency_s: 0,
            oneline: true,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Flags {
    pub quiet: bool,
    pub only_show_errors: bool,
    pub is_stream: bool,
    pub progress: bool,
    pub progress_frequency: i64,
    pub progress_multiline: bool,
}
impl Default for Flags {
    fn default() -> Self {
        Self {
            quiet: false,
            only_show_errors: false,
            is_stream: false,
            progress: true,
            progress_frequency: 0,
            progress_multiline: false,
        }
    }
}
impl Flags {
    pub fn select(self) -> Option<PrinterConfig> {
        if self.quiet {
            return None;
        }
        Some(if self.only_show_errors || self.is_stream {
            PrinterConfig {
                mode: Mode::OnlyErrors,
                ..Default::default()
            }
        } else if !self.progress {
            PrinterConfig {
                mode: Mode::NoProgress,
                ..Default::default()
            }
        } else {
            PrinterConfig {
                frequency_s: self.progress_frequency,
                oneline: !self.progress_multiline,
                ..Default::default()
            }
        })
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Stream {
    Out,
    Err,
}
impl Stream {
    fn index(self) -> usize {
        usize::from(self == Self::Err)
    }
}
const DRY_RUN_PREFIX: &str = "(dryrun) ";
const FATAL_PREFIX: &[u8] = b"fatal error: ";
const STILL_CALCULATING: &str = " (calculating...)";
/// The first write error on each stream. A stream whose write fails does
/// not stop the other, as upstream's result processor survives a failing
/// handler. A failed stream keeps taking whole statements into its buffer,
/// as CPython's buffered stdout and stderr do, for the flush at exit.
#[derive(Debug, Default)]
pub struct WriteErrors {
    pub stdout: Option<io::Error>,
    pub stderr: Option<io::Error>,
}
impl WriteErrors {
    pub fn is_empty(&self) -> bool {
        self.stdout.is_none() && self.stderr.is_none()
    }
    /// Each stream's error, `self`'s where both have one.
    pub fn or(self, other: Self) -> Self {
        Self {
            stdout: self.stdout.or(other.stdout),
            stderr: self.stderr.or(other.stderr),
        }
    }
}
impl std::fmt::Display for WriteErrors {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match (&self.stdout, &self.stderr) {
            (Some(error), _) => write!(f, "stdout: {error}"),
            (None, Some(error)) => write!(f, "stderr: {error}"),
            (None, None) => f.write_str("no write failed"),
        }
    }
}
impl std::error::Error for WriteErrors {}
impl From<WriteErrors> for io::Error {
    fn from(errors: WriteErrors) -> Self {
        errors
            .stdout
            .or(errors.stderr)
            .unwrap_or_else(|| io::Error::other("no write failed"))
    }
}
#[derive(Debug)]
pub struct Printer {
    config: PrinterConfig,
    progress_length: usize,
    last_progress_ns: Option<u64>,
    last_stream: Option<Stream>,
    failed_streams: [bool; 2],
    errors: [Option<io::Error>; 2],
}
impl Printer {
    pub fn new(config: PrinterConfig) -> Self {
        Self {
            config,
            progress_length: 0,
            last_progress_ns: None,
            last_stream: None,
            failed_streams: [false; 2],
            errors: [None, None],
        }
    }
    pub fn take_errors(&mut self) -> WriteErrors {
        let [stdout, stderr] = std::mem::take(&mut self.errors);
        WriteErrors { stdout, stderr }
    }
    /// Renders one event after `recorder` recorded it. A failed write keeps
    /// its stream's error, and the stream goes on taking statements.
    pub fn handle(
        &mut self,
        recorder: &Recorder,
        event: &Event,
        now_ns: u64,
        stdout: &mut dyn Write,
        stderr: &mut dyn Write,
    ) {
        let mut streams = Streams { stdout, stderr };
        let streams = &mut streams;
        match event {
            Event::Queued { .. } => {}
            Event::Progress { .. } => self.print_progress(recorder, now_ns, streams),
            Event::Success { line, .. } => self.print_success(recorder, line, now_ns, streams),
            Event::Failure {
                line,
                exception,
                text,
                ..
            } => self.print_failure(
                recorder,
                (line, exception, text.as_deref()),
                now_ns,
                streams,
            ),
            Event::Warning(text) => self.print_warning(recorder, text, now_ns, streams),
            Event::Skip { .. } => self.redisplay_progress(recorder, false, now_ns, streams),
            Event::Diagnostic(_) | Event::Fatal(_) | Event::CtrlC => {
                self.print_command_line(event, streams);
            }
            Event::DryRun(line) => self.print_dry_run(line, streams),
            Event::FinalTotal(_) => self.clear_progress_if_done(recorder, b'\n', streams),
        }
    }
    fn print_success(
        &mut self,
        recorder: &Recorder,
        line: &super::Line,
        now_ns: u64,
        streams: &mut Streams<'_>,
    ) {
        if self.config.mode == Mode::OnlyErrors {
            return;
        }
        let text = [
            format!("{}: ", line.transfer_type).as_bytes(),
            line.locations().as_slice(),
        ]
        .concat();
        let statement = self.write_statement(Stream::Out, text, b'\n', streams);
        self.redisplay_progress_after(Stream::Out, statement, recorder, now_ns, streams);
    }
    fn print_command_line(&mut self, event: &Event, streams: &mut Streams<'_>) {
        let text = match event {
            Event::Diagnostic(text) => Cow::Borrowed(text.as_slice()),
            Event::Fatal(text) => Cow::Owned([FATAL_PREFIX, text.as_slice()].concat()),
            Event::CtrlC => Cow::Borrowed(cli_core::interrupt::MESSAGE.as_bytes()),
            _ => return,
        };
        self.write_statement(Stream::Err, text, b'\n', streams);
    }
    fn print_warning(
        &mut self,
        recorder: &Recorder,
        text: &[u8],
        now_ns: u64,
        streams: &mut Streams<'_>,
    ) {
        let statement = self.write_statement(Stream::Err, text, b'\n', streams);
        self.redisplay_progress_after(Stream::Err, statement, recorder, now_ns, streams);
    }
    fn print_dry_run(&mut self, line: &super::Line, streams: &mut Streams<'_>) {
        let text = [
            format!("{DRY_RUN_PREFIX}{}: ", line.transfer_type).as_bytes(),
            line.locations().as_slice(),
        ]
        .concat();
        self.write_statement(Stream::Out, text, b'\n', streams);
    }
    fn print_failure(
        &mut self,
        recorder: &Recorder,
        (line, exception, text): (&super::Line, &[u8], Option<&[u8]>),
        now_ns: u64,
        streams: &mut Streams<'_>,
    ) {
        let text = text.map_or_else(
            || {
                [
                    format!("{} failed: ", line.transfer_type).as_bytes(),
                    line.locations().as_slice(),
                    b" ",
                    exception,
                ]
                .concat()
            },
            <[u8]>::to_vec,
        );
        let statement = self.write_statement(Stream::Err, text, b'\n', streams);
        self.redisplay_progress_after(Stream::Err, statement, recorder, now_ns, streams);
    }
    fn redisplay_progress_after(
        &mut self,
        stream: Stream,
        statement: Statement,
        recorder: &Recorder,
        now_ns: u64,
        streams: &mut Streams<'_>,
    ) {
        if self.config.mode != Mode::Full {
            return self.redisplay_progress(recorder, true, now_ns, streams);
        }
        if statement.failed {
            return;
        }
        if let Err(error) = streams.writer(stream).flush() {
            return self.mark_failed(stream, error);
        }
        self.redisplay_progress(recorder, true, now_ns, streams);
    }
    fn redisplay_progress(
        &mut self,
        recorder: &Recorder,
        reset: bool,
        now_ns: u64,
        streams: &mut Streams<'_>,
    ) {
        if reset {
            self.progress_length = 0;
        }
        if recorder.has_remaining_progress() {
            self.print_progress(recorder, now_ns, streams);
        } else {
            self.clear_progress_if_done(recorder, b'\r', streams);
        }
    }
    fn clear_progress_if_done(
        &mut self,
        recorder: &Recorder,
        ending: u8,
        streams: &mut Streams<'_>,
    ) {
        if self.progress_length > 0 && !recorder.has_remaining_progress() {
            self.write_statement(Stream::Out, "", ending, streams);
        }
    }
    fn print_progress(&mut self, recorder: &Recorder, now_ns: u64, streams: &mut Streams<'_>) {
        if self.config.mode != Mode::Full {
            return;
        }
        if !self.should_print_progress_now(now_ns) {
            return;
        }
        let text = progress_text(recorder);
        if self.config.oneline {
            self.progress_length = self
                .write_statement(Stream::Out, &text, b'\r', streams)
                .width;
        } else {
            self.write_statement(Stream::Out, &text, b'\n', streams);
        }
    }
    fn should_print_progress_now(&mut self, now_ns: u64) -> bool {
        if let Some(last) = self.last_progress_ns
            && self.config.frequency_s > 0
            && u128::from(now_ns.saturating_sub(last))
                < self.config.frequency_s as u128 * 1_000_000_000
        {
            return false;
        }
        self.last_progress_ns = Some(now_ns);
        true
    }
    fn write_statement(
        &mut self,
        stream: Stream,
        text: impl AsRef<[u8]>,
        ending: u8,
        streams: &mut Streams<'_>,
    ) -> Statement {
        self.switch_to(stream, streams);
        let text = text.as_ref();
        let width = code_point_count(text);
        let padding = self.progress_length.saturating_sub(width);
        let text = if stream == Stream::Err {
            backslash_replaced(text)
        } else {
            Cow::Borrowed(text)
        };
        // One write per statement, so the descriptor receives each line
        // whole: the CRT's debug log shares stderr from other threads, and
        // must not land inside a line. The stream's buffer takes the
        // statement whole, as CPython's buffered stdout and stderr do,
        // measured as written: one that fits joins it, and one that does not
        // first flushes it and is dropped when that fails.
        let mut line = Vec::with_capacity(text.len() + padding + 1);
        line.extend_from_slice(&text);
        line.resize(line.len() + padding, b' ');
        line.push(ending);
        let mut failed = false;
        if let Err(error) = streams.writer(stream).write_all(&line) {
            self.mark_failed(stream, error);
            failed = true;
        }
        if !failed && self.failed_streams[stream.index()] {
            failed = !self.retry_stream(stream, streams);
        }
        Statement {
            width: width + padding,
            failed,
        }
    }
    fn retry_stream(&mut self, stream: Stream, streams: &mut Streams<'_>) -> bool {
        if let Err(error) = streams.writer(stream).flush() {
            self.mark_failed(stream, error);
            return false;
        }
        self.failed_streams[stream.index()] = false;
        true
    }
    fn mark_failed(&mut self, stream: Stream, error: io::Error) {
        self.failed_streams[stream.index()] = true;
        self.errors[stream.index()].get_or_insert(error);
    }
    fn switch_to(&mut self, stream: Stream, streams: &mut Streams<'_>) {
        if let Some(previous) = self.last_stream.replace(stream)
            && previous != stream
        {
            self.flush_stream(previous, streams);
        }
    }
    fn flush_stream(&mut self, stream: Stream, streams: &mut Streams<'_>) {
        if self.failed_streams[stream.index()] {
            return;
        }
        if let Err(error) = streams.writer(stream).flush() {
            self.mark_failed(stream, error);
        }
    }
    /// Pushes both streams' written bytes out.
    pub fn flush(&mut self, stdout: &mut dyn Write, stderr: &mut dyn Write) {
        let streams = &mut Streams { stdout, stderr };
        self.flush_stream(Stream::Out, streams);
        self.flush_stream(Stream::Err, streams);
    }
}
#[derive(Debug, Clone, Copy)]
struct Statement {
    width: usize,
    failed: bool,
}
struct Streams<'a> {
    stdout: &'a mut dyn Write,
    stderr: &'a mut dyn Write,
}
impl Streams<'_> {
    fn writer(&mut self, stream: Stream) -> &mut dyn Write {
        match stream {
            Stream::Out => self.stdout,
            Stream::Err => self.stderr,
        }
    }
}
fn progress_text(r: &Recorder) -> String {
    let estimate = if r.expected_totals_are_final() {
        ""
    } else {
        "~"
    };
    let beginning = if r.expected_bytes_transferred > 0 {
        format!(
            "{}/{estimate}{} ({}/s) with ",
            cli_core::output::format_size(
                r.bytes_transferred
                    .saturating_add(r.bytes_failed_to_transfer),
                true
            ),
            cli_core::output::format_size(r.expected_bytes_transferred, true),
            cli_core::output::format_human_readable_rate(r.bytes_transfer_speed)
        )
    } else {
        format!("{} file(s) with ", r.files_transferred)
    };
    let remaining = i128::from(r.expected_files_transferred)
        - i128::from(r.files_transferred)
        - i128::from(r.files_skipped);
    format!(
        "Completed {beginning}{estimate}{remaining} file(s) remaining{}",
        if r.expected_totals_are_final() {
            ""
        } else {
            STILL_CALCULATING
        }
    )
}

/// Python's stderr encodes with `backslashreplace`, so each surrogate escape
/// a path decoded into prints as `\udcXX`; stdout keeps the raw byte.
fn backslash_replaced(bytes: &[u8]) -> Cow<'_, [u8]> {
    if std::str::from_utf8(bytes).is_ok() {
        return Cow::Borrowed(bytes);
    }
    let mut replaced = Vec::with_capacity(bytes.len());
    for chunk in bytes.utf8_chunks() {
        replaced.extend_from_slice(chunk.valid().as_bytes());
        for byte in chunk.invalid() {
            replaced.extend_from_slice(format!("\\udc{byte:02x}").as_bytes());
        }
    }
    Cow::Owned(replaced)
}
fn code_point_count(mut bytes: &[u8]) -> usize {
    let mut count = 0;
    while !bytes.is_empty() {
        match std::str::from_utf8(bytes) {
            Ok(text) => return count + text.chars().count(),
            Err(error) => {
                let valid = error.valid_up_to();
                count += bytes[..valid]
                    .iter()
                    .filter(|&&byte| byte & 0xc0 != 0x80)
                    .count()
                    + 1;
                bytes = &bytes[valid + 1..];
            }
        }
    }
    count
}
