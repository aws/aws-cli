use super::Args;
use crate::{list_stats, request_failure, uri};
use cli_core::{
    cli_error::{Category, CommandFailure},
    output,
};
use crt::s3::{ListResult, ListStats};
use std::ffi::OsStr;
use std::io::{self, Write};

pub use crt::s3::EntryKind;
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub kind: EntryKind,
    pub name: Vec<u8>,
    pub size: u64,
    pub date: output::EntryDate,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Request<'a> {
    pub target: uri::S3ListTarget<'a>,
    pub recursive: bool,
    pub page_size: u32,
    pub request_payer: Option<&'a str>,
    pub bucket_name_prefix: Option<&'a str>,
    pub bucket_region: Option<&'a str>,
}
/// A synchronous pager must stop on nonzero callback return and drain before returning.
pub trait Backend {
    fn list(
        &mut self,
        request: Request<'_>,
        callback: &mut dyn FnMut(Entry) -> i32,
        stats: Option<&mut ListStats>,
    ) -> ListResult;
}
/// What `execute` lists and prints: the parsed target and the bound values
/// the listing reads. The runtime the listing runs on stays with its
/// backend.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ListExecutionOptions<'a> {
    pub target: uri::S3ListTarget<'a>,
    pub recursive: bool,
    pub human_readable: bool,
    pub summarize: bool,
    pub bucket_name_prefix: Option<&'a str>,
    pub bucket_region: Option<&'a str>,
    /// Zero leaves the page size to the service default.
    pub page_size: u32,
    pub request_payer: Option<&'a str>,
    /// Whether an object listing collects and prints its statistics; see
    /// `list_stats::enabled`.
    pub collect_stats: bool,
}
impl<'a> ListExecutionOptions<'a> {
    /// The options of the admitted `args`, whose `paths` parsed as `target`.
    #[expect(clippy::expect_used, reason = "router admission bounds the page size")]
    pub fn new(args: &'a Args, target: uri::S3ListTarget<'a>, collect_stats: bool) -> Self {
        Self {
            target,
            recursive: args.dir_op,
            human_readable: args.human_readable,
            summarize: args.summarize,
            bucket_name_prefix: args.bucket_name_prefix.as_deref().and_then(OsStr::to_str),
            bucket_region: args.bucket_region.as_deref().and_then(OsStr::to_str),
            page_size: args
                .page_size
                .map_or(0, |v| u32::try_from(v).expect("admitted page size")),
            request_payer: args.request_payer.as_deref(),
            collect_stats,
        }
    }
    fn request(&self) -> Request<'a> {
        Request {
            target: self.target,
            recursive: self.recursive,
            page_size: self.page_size,
            request_payer: self.request_payer,
            bucket_name_prefix: self.bucket_name_prefix,
            bucket_region: self.bucket_region,
        }
    }
}
#[derive(Debug)]
pub enum Error {
    Request(Box<ListResult>),
    Local(crt::s3::ListLocalError),
    /// A write to the listing's stdout failed.
    Stdout(io::Error),
    /// A write of a diagnostic to stderr failed.
    Stderr(io::Error),
}
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Request(v) => std::fmt::Display::fmt(&v.transfer, f),
            Self::Local(v) => write!(f, "{v:?}"),
            Self::Stdout(v) | Self::Stderr(v) => std::fmt::Display::fmt(v, f),
        }
    }
}
impl std::error::Error for Error {}
pub(super) fn invalid_target_failure(error: uri::S3ListTargetParseError) -> CommandFailure {
    let message = format!(
        "error: invalid S3 URI for ls: {}",
        s3_list_target_error_message(error)
    );
    CommandFailure {
        message: message.into_bytes(),
        ..CommandFailure::new(Category::General)
    }
}
pub(super) fn s3_list_target_error_message(error: uri::S3ListTargetParseError) -> &'static str {
    match error {
        uri::S3ListTargetParseError::InvalidS3UriScheme => {
            "expected s3://bucket[/prefix] or bucket[/prefix]"
        }
        uri::S3ListTargetParseError::MissingS3Bucket => "missing bucket name",
        uri::S3ListTargetParseError::BucketNotUtf8 => "bucket name is not UTF-8",
    }
}
pub fn execute_to_file(
    backend: &mut impl Backend,
    options: ListExecutionOptions<'_>,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
    endpoint_url: &str,
) -> Result<u8, CommandFailure> {
    execute(backend, options, stdout, stderr).map_err(|error| listing_failure(error, endpoint_url))
}
pub fn listing_failure(error: Error, endpoint: &str) -> CommandFailure {
    let message = match error {
        Error::Request(result) => return list_command_failure(&result, endpoint),
        Error::Stdout(error) => cli_core::cli_error::stdout_write_failure_message(&error),
        Error::Stderr(_) => cli_core::cli_error::WRITE_FAILED_MESSAGE.to_owned(),
        error @ Error::Local(_) => error.to_string(),
    };
    CommandFailure {
        message: message.into_bytes(),
        ..CommandFailure::new(Category::General)
    }
}
/// Lists and prints. Whether a request or an error ends it early, what the
/// earlier pages printed is flushed and no summary is printed. A listing that
/// matched nothing under a prefix is the command's own failure with status 1,
/// as upstream's; so is a callback error the backend reports without a failed
/// stdout write, after the line `error: failed to write S3 listing output`.
/// Each row, and each of the summary's two statements, is flushed as it is
/// printed, as upstream's `uni_print` flushes each line, so a row reaches a
/// pipe while a later page is still on its way. A stdout write that fails
/// returns `Error::Stdout`, which `execute_to_file` reports through the general
/// handler: the exception CPython raises for it, its broken pipe among them,
/// whose output then waits for the flush of `sys.stdout` at exit.
pub fn execute(
    backend: &mut impl Backend,
    options: ListExecutionOptions<'_>,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
) -> Result<u8, Error> {
    let mut output_context = ListOutputContext::new(stdout, &options);
    let mut collected_stats = ListStats::default();
    let mut stats = stats_sink(&options, &mut collected_stats);
    let mut write_error = None;
    let result = backend.list(
        options.request(),
        &mut |entry| match output_context.on_entry(entry) {
            Ok(()) => 0,
            Err(e) => {
                write_error = Some(e);
                -1
            }
        },
        stats.as_deref_mut(),
    );
    write_stats(stderr, stats.as_deref())?;
    if let Some(error) = write_error {
        let _ = output_context.stdout.flush();
        return Err(Error::Stdout(error));
    }
    if let Some(error) = result.local_error {
        let _ = output_context.stdout.flush();
        return Err(Error::Local(error));
    }
    if result.callback_error != 0 {
        writeln!(stderr, "error: failed to write S3 listing output").map_err(Error::Stderr)?;
        stderr.flush().map_err(Error::Stderr)?;
        return Ok(1);
    }
    if list_result_failed(&result) {
        output_context.stdout.flush().map_err(Error::Stdout)?;
        return Err(Error::Request(Box::new(result)));
    }
    if options.summarize {
        output_context.print_summary().map_err(Error::Stdout)?;
    }
    output_context.stdout.flush().map_err(Error::Stdout)?;
    Ok(u8::from(
        options.target.has_prefix && output_context.entry_count == 0,
    ))
}
fn stats_sink<'s>(
    options: &ListExecutionOptions<'_>,
    collected: &'s mut ListStats,
) -> Option<&'s mut ListStats> {
    (options.collect_stats && options.target.bucket.is_some()).then_some(collected)
}
fn write_stats(mut stderr: &mut dyn Write, stats: Option<&ListStats>) -> Result<(), Error> {
    let Some(collected) = stats else {
        return Ok(());
    };
    if collected.pages == 0 {
        return Ok(());
    }
    list_stats::write(&mut stderr, collected).map_err(Error::Stderr)?;
    stderr.flush().map_err(Error::Stderr)
}
fn list_result_failed(result: &ListResult) -> bool {
    result.repeated_token.is_some()
        || result.transfer.error_code != 0
        || !matches!(result.transfer.response_status, 0 | 200)
}
fn saturated_retries(retries: u64) -> u32 {
    u32::try_from(retries).unwrap_or(u32::MAX)
}
struct ListOutputContext<'a> {
    stdout: &'a mut dyn Write,
    recursive: bool,
    human_readable: bool,
    total_objects: u64,
    total_size: u128,
    entry_count: u64,
}
impl<'a> ListOutputContext<'a> {
    fn new(stdout: &'a mut dyn Write, options: &ListExecutionOptions<'_>) -> Self {
        Self {
            stdout,
            recursive: options.recursive,
            human_readable: options.human_readable,
            total_objects: 0,
            total_size: 0,
            entry_count: 0,
        }
    }
    fn on_entry(&mut self, entry: Entry) -> io::Result<()> {
        match entry.kind {
            EntryKind::Object => self.emit_object(&entry),
            EntryKind::CommonPrefix => self.emit_common_prefix(&entry.name),
            EntryKind::Bucket => self.emit_bucket(&entry),
        }?;
        self.stdout.flush()
    }
    fn emit_object(&mut self, entry: &Entry) -> io::Result<()> {
        self.entry_count += 1;
        self.total_objects += 1;
        self.total_size += u128::from(entry.size);
        output::print_entry_date(&mut self.stdout, entry.date)?;
        self.stdout.write_all(b" ")?;
        let size = output::format_size(entry.size, self.human_readable);
        output::print_right_aligned(&mut self.stdout, 10, size.as_bytes())?;
        self.stdout.write_all(b" ")?;
        self.stdout.write_all(if self.recursive {
            &entry.name
        } else {
            output::basename_for_object(&entry.name)
        })?;
        self.stdout.write_all(b"\n")
    }
    fn emit_common_prefix(&mut self, prefix: &[u8]) -> io::Result<()> {
        self.entry_count += 1;
        output::print_right_aligned(&mut self.stdout, 30, b"PRE")?;
        self.stdout.write_all(b" ")?;
        self.stdout
            .write_all(output::basename_for_common_prefix(prefix))?;
        self.stdout.write_all(b"/\n")
    }
    fn emit_bucket(&mut self, entry: &Entry) -> io::Result<()> {
        self.entry_count += 1;
        output::print_entry_date(&mut self.stdout, entry.date)?;
        self.stdout.write_all(b" ")?;
        self.stdout.write_all(&entry.name)?;
        self.stdout.write_all(b"\n")
    }
    fn print_summary(&mut self) -> io::Result<()> {
        writeln!(self.stdout, "\nTotal Objects: {}", self.total_objects)?;
        self.stdout.flush()?;
        let size = output::format_summary_size(self.total_size, self.human_readable);
        writeln!(self.stdout, "   Total Size: {size}")?;
        self.stdout.flush()
    }
}
/// The failure the handler chain frames for a listing request that failed, as
/// botocore would have raised it: a ClientError for an error response,
/// NoCredentialsError when the signer had none, and the general handler's
/// sentence for a request that never got an answer. The base failure carries
/// the result's CRT code, CRT name and HTTP status whatever the kind, a
/// repeated token's 200 among them.
pub fn list_command_failure(result: &ListResult, endpoint: &str) -> CommandFailure {
    let transfer = &result.transfer;
    let mut failure = CommandFailure {
        crt_code: transfer.error_code,
        crt_name: String::from_utf8_lossy(transfer.crt_name.as_bytes()).into_owned(),
        http_status: transfer.response_status,
        ..CommandFailure::new(Category::General)
    };
    if let Some(token) = &result.repeated_token {
        failure.message = request_failure::RepeatedToken { token }.to_vec();
        return failure;
    }
    match request_failure::classify(transfer) {
        request_failure::Kind::ServiceError {
            code,
            message,
            operation,
            retries_exhausted,
        } => {
            failure.category = Category::ClientError;
            failure.code = String::from_utf8_lossy(code).into_owned();
            failure.message = message.to_vec();
            failure.operation =
                String::from_utf8_lossy(request_failure::operation_name(operation)).into_owned();
            failure.retries_exhausted = retries_exhausted.map(saturated_retries);
        }
        request_failure::Kind::HttpStatus {
            status,
            operation,
            retries_exhausted,
        } => {
            failure.category = Category::ClientError;
            failure.code = status.to_string();
            failure.message = request_failure::http_reason_phrase(status).into();
            failure.operation =
                String::from_utf8_lossy(request_failure::operation_name(operation)).into_owned();
            failure.retries_exhausted = retries_exhausted.map(saturated_retries);
        }
        request_failure::Kind::NoCredentials => {
            failure.category = Category::NoCredentials;
            failure.message = request_failure::NO_CREDENTIALS_MESSAGE.into();
        }
        _ => {
            let reason = request_failure::Reason {
                result: transfer,
                url: request_failure::RequestUrl::Listing {
                    endpoint_url: endpoint,
                    request_path: &String::from_utf8_lossy(&result.request_path),
                },
                missing_key: None,
            };
            failure.message = request_failure::sentence_bytes(reason);
        }
    }
    failure
}
