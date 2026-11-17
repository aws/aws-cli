//! The cp transfer request, completion precedence, and parseable statistics.
use crate::request_failure::{self, Reason, RequestUrl};
use crate::{config, list_stats, results, transfer};
use crt::runtime::RuntimeOptions;
use crt::s3::{ListLocalError, ListResult, TransferResult};
use std::ffi::OsStr;
use std::io;
use std::path::PathBuf;

/// What a transfer of any shape runs with.
#[derive(Debug, Clone)]
pub struct TransferRequest {
    pub direction: transfer::Direction,
    pub bucket: String,
    /// The listing's or walk's key prefix, as the operand's bytes: an upload
    /// prefix that is not UTF-8 makes keys botocore cannot encode, which
    /// each upload reports.
    pub prefix: Vec<u8>,
    pub local_root: PathBuf,
    pub runtime: RuntimeOptions,
    pub quiet: bool,
    /// `--dryrun`: each object every rule passes is reported in place of its
    /// transfer.
    pub dryrun: bool,
    pub no_overwrite: bool,
    pub glacier: transfer::GlacierPolicy,
    pub content_types: Option<std::sync::Arc<crate::mime::Database>>,
    pub refusal: Option<String>,
    pub page_size: u32,
    pub max_in_flight: u32,
    pub collect_stats: bool,
    pub prefetch: bool,
    /// The client sizing of the command's shape. `runtime` is the record's
    /// client; the runner builds it with this sizing's target, pool, and
    /// connection cap.
    pub sizing: config::ClientSizing,
    pub download: Option<config::DownloadTuning>,
    /// The one object a command without `--recursive` names, which its
    /// producer hands to the engine; None for a listing or a walk.
    pub object: Option<SingleObject>,
    /// The `--include` and `--exclude` patterns each source must pass.
    pub filter: crate::filter::Filter,
    /// What the transfer's requests send besides their own fields.
    pub headers: RequestHeaders,
    /// What the transfer's object requests compute or check of each
    /// object's checksum beyond what the runtime's checksum modes ask.
    pub checksums: ChecksumSettings,
    /// What only a delete sets; a copy keeps the default.
    pub delete: DeleteOptions,
    /// What becomes of each source a copy transferred: a move deletes it.
    pub sources: transfer::SourceDisposition,
    /// How `s3 sync` pairs each source with the destination's entry of the
    /// same name, which it lists or walks too, and which entries it pairs;
    /// None transfers every source.
    pub sync: Option<crate::sync::Plan>,
    /// The `user-agent` each listing's pages send, None for the client's.
    /// Upstream lists through a botocore client's paginator, which adds its
    /// feature id, and transfers through the CRT client, which does not
    /// (`S3TransferCommand._get_source_and_transfer_clients`).
    pub listing_user_agent: Option<String>,
    /// What the transfer does with the links its local side meets.
    pub links: transfer::LinkPolicy,
}
/// What a transfer's requests send besides their own fields.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub struct RequestHeaders {
    /// `--request-payer`, which the listing and every object request send.
    pub request_payer: Option<transfer::RequestPayer>,
    /// The headers every object request sends after its own: an upload's
    /// object settings, or a download's customer key.
    pub object: Vec<crt::s3::Header>,
}
impl RequestHeaders {
    /// The `x-amz-request-payer` value, if any.
    pub fn request_payer_value(&self) -> Option<&'static [u8]> {
        self.request_payer.map(transfer::RequestPayer::header_value)
    }
}
/// The checksum settings of a transfer, which the CRT applies in place of
/// headers (s3transfer's `S3ClientArgsCreator`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub struct ChecksumSettings {
    /// `--checksum-algorithm`: the algorithm of the checksum each upload's
    /// PUT sends in a trailer, whatever `request_checksum_calculation` says.
    pub upload_algorithm: Option<crt::s3::ChecksumAlgorithm>,
    /// `--checksum-mode`: each download checks the object's checksum,
    /// whatever `response_checksum_validation` says.
    pub validate_downloads: bool,
}
/// What `s3 rm` adds to the request it deletes with.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub struct DeleteOptions {
    /// Whether the listing names only folder markers: a bucket `s3 rm`
    /// names without `--recursive`, whose listing upstream's file generator
    /// still yields every folder marker of (`FileGenerator.list_objects`).
    pub folder_markers_only: bool,
}
impl TransferRequest {
    /// Whether the endpoint's rule error is fatal before the transfer starts.
    pub fn refusal_is_fatal(&self) -> bool {
        match self.direction {
            transfer::Direction::Download => true,
            transfer::Direction::Upload => self.sync.is_some(),
            transfer::Direction::Delete => self.object.is_none(),
        }
    }
    /// The engine's window, which follows the shape: one slot for one
    /// object, whatever `max_in_flight` the settings configured.
    pub fn engine_window(&self) -> u32 {
        if self.object.is_some() {
            1
        } else {
            self.max_in_flight
        }
    }
    /// The workers that finish transfers off the CRT's threads: one for one
    /// object.
    pub fn finish_workers(&self) -> usize {
        if self.object.is_some() {
            1
        } else {
            crate::constants::FINISH_WORKERS_DEFAULT
        }
    }
    /// The workers that prepare native outputs and send their GETs off the
    /// submitting thread, given `cpus`: only a download of many objects whose
    /// explicit settings give every object a native writer has them, up to
    /// one per CPU and per engine slot. One object is prepared on the
    /// submitting thread, and a `crt` writer prepares nothing.
    pub fn prepare_workers(&self, cpus: usize) -> Option<usize> {
        let tuning = self.download.as_ref()?;
        let pooled = self.direction == transfer::Direction::Download
            && self.object.is_none()
            && tuning.custom_writer_required
            && tuning.writer.mode != crate::download::WriterMode::Crt;
        pooled.then(|| {
            crate::constants::PREPARE_WORKERS_MAX
                .min(cpus.max(1))
                .min(self.engine_window() as usize)
        })
    }
}
/// The object of a command that names one, as its producer hands it over.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SingleObject {
    /// The object key, as result lines spell it.
    pub key: Vec<u8>,
    /// The upload source, normalized as the command's local operand is, or
    /// the download destination the operand resolved to. A destination its
    /// name ruled out is named as the operand resolved.
    pub local_path: PathBuf,
    /// What the command found at a download's destination.
    pub local: crate::scheduler::EntryLocal,
    /// How result lines name the remote side: the destination operand as
    /// spelled, unless the key took the source's basename. None names it
    /// `s3://bucket/key`.
    pub remote: Option<std::ffi::OsString>,
}
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Stats {
    pub submitted: u64,
    pub succeeded: u64,
    pub failed: u64,
    pub skipped: u64,
    pub elapsed_ns: u64,
    pub stall_ns: u64,
    pub stall_count: u64,
    pub size_le_4_kib: u64,
    pub size_le_64_kib: u64,
    pub size_le_1_mib: u64,
    pub size_gt_1_mib: u64,
    pub producer_wait_ns: u64,
    pub producer_wait_count: u64,
    pub queue_hwm: u64,
    pub in_flight_hwm: u64,
    /// Download requests the CRT accepted with a native writer receiving the
    /// body. Acceptance, not completed data: an accepted request can still
    /// fail or be cancelled before any byte arrives.
    pub custom_writer_requests: u64,
    /// Download requests the CRT accepted to write through `recv_filepath`,
    /// counted as `custom_writer_requests` is.
    pub recv_file_requests: u64,
    pub write_queue_hwm: u64,
    pub writes_completed: u64,
    pub write_ns: u64,
}
impl Stats {
    pub fn files_per_second(&self) -> f64 {
        if self.elapsed_ns == 0 {
            0.0
        } else {
            self.succeeded as f64 * 1_000_000_000.0 / self.elapsed_ns as f64
        }
    }
    pub fn record_size(&mut self, size: u64) {
        match size {
            0..=4096 => self.size_le_4_kib += 1,
            4097..=65536 => self.size_le_64_kib += 1,
            65537..=1048576 => self.size_le_1_mib += 1,
            _ => self.size_gt_1_mib += 1,
        }
    }
}
/// The opt-in statistics line, one diagnostic. `source_pool` names the pool
/// installed on the client, not proof that body bytes passed through it, and
/// the request counters count accepted requests, not completed data.
pub fn write_transfer_stats(
    report: CommandReport<'_>,
    direction: transfer::Direction,
    stats: &Stats,
    throughput: f64,
    memory_bytes: u64,
    numa_source_pool: bool,
) {
    let source_pool = if numa_source_pool { "numa" } else { "crt" };
    let throughput = list_stats::format_shortest_half_up(throughput, 3);
    report.diagnostic(format!(
        "zs3_transfer_stats direction={direction} submitted={} succeeded={} failed={} skipped={} \
        elapsed_ns={} files_per_second={} stall_ns={} stall_count={} \
        size_le_4_kib={} size_le_64_kib={} size_le_1_mib={} size_gt_1_mib={} \
        producer_wait_ns={} producer_wait_count={} queue_hwm={} in_flight_hwm={} \
        write_queue_hwm={} writes_completed={} write_ns={} \
        crt_target_gbps={throughput} memory_limit_bytes={memory_bytes} \
        source_pool={source_pool} custom_writer_requests={} recv_file_requests={}",
        stats.submitted,
        stats.succeeded,
        stats.failed,
        stats.skipped,
        stats.elapsed_ns,
        list_stats::format_shortest_half_up(stats.files_per_second(), 3),
        stats.stall_ns,
        stats.stall_count,
        stats.size_le_4_kib,
        stats.size_le_64_kib,
        stats.size_le_1_mib,
        stats.size_gt_1_mib,
        stats.producer_wait_ns,
        stats.producer_wait_count,
        stats.queue_hwm,
        stats.in_flight_hwm,
        stats.write_queue_hwm,
        stats.writes_completed,
        stats.write_ns,
        stats.custom_writer_requests,
        stats.recv_file_requests
    ));
}
/// Why a producer stopped, retained until the engine has drained.
#[derive(Debug, Clone, Default)]
pub enum ProducerOutcome {
    /// The listing ran to its last page, or to the page that failed. A
    /// local error rides in its `local_error`.
    ListCompleted(Box<ListResult>),
    /// The walk named every entry under its root, or warned about a root
    /// upstream's file generator skips.
    #[default]
    WalkCompleted,
    /// The walk could not go on: the directory or an entry's submission
    /// failed.
    WalkFailed(String),
    /// The engine could not take an entry the producer named outside the
    /// walk; the command returns the error to the general handler.
    SubmitFailed(String),
    /// The one-object producer handed its entry to the engine.
    ObjectCompleted,
    /// The one-object download's HeadObject failed. Upstream's file generator
    /// raises before any transfer exists, so the command reports a fatal
    /// error naming the key, and no submission total.
    HeadFailed(Box<TransferResult>),
    /// Ctrl-C canceled the one-object download's HeadObject; the command
    /// reports the cancellation.
    HeadCanceled,
    /// The one-object download's HeadObject response had a Content-Length
    /// but no Last-Modified. Upstream's file generator raises the KeyError
    /// before any transfer exists, and the command reports it as a fatal
    /// error.
    HeadMissingLastModified,
    /// A sync download's comparator raised: the walk of its destination
    /// could not go on, which raises out of upstream's file generator, or
    /// `--case-conflict error` found a conflict. The producer canceled the
    /// transfers on this error, and the command reports it as its fatal
    /// error.
    ComparatorRaised(String),
}
impl ProducerOutcome {
    /// Whether the producer named every object, which is when upstream's
    /// file generator is exhausted and reports its submission total. A
    /// listing, walk, or HeadObject that failed raised instead, and so did an
    /// entry the engine could not take; Ctrl-C stops the generator too.
    pub fn exhausted(&self, interrupted: bool) -> bool {
        if interrupted {
            return false;
        }
        match self {
            Self::WalkCompleted | Self::ObjectCompleted => true,
            Self::WalkFailed(_)
            | Self::SubmitFailed(_)
            | Self::HeadFailed(_)
            | Self::HeadCanceled
            | Self::HeadMissingLastModified
            | Self::ComparatorRaised(_) => false,
            Self::ListCompleted(list) => list_completed(list),
        }
    }
}
/// Whether a listing named every object: no page failed, and nothing
/// stopped it before its last.
pub fn list_completed(list: &ListResult) -> bool {
    list.local_error.is_none()
        && list.callback_error == 0
        && list.repeated_token.is_none()
        && list.transfer.error_code == 0
        && matches!(list.transfer.response_status, 0 | 200)
}
/// What a producer leaves for the command once the engine has drained.
#[derive(Debug, Clone, Default)]
pub struct ProducerResult {
    /// Why the producer stopped. A producer that never ran, because the
    /// finish pool could not start, leaves the default.
    pub outcome: ProducerOutcome,
    /// The download submitter stopped on an entry's error after the listing
    /// handed it over, so a listing that succeeded still named objects that
    /// were never submitted. The scheduler holds the error itself.
    pub submit_queue_failed: bool,
    /// The listing's statistics, when they were collected.
    pub list_stats: Option<crt::s3::ListStats>,
}
impl ProducerResult {
    /// Whether the producer named and submitted every object, so the
    /// submission total is final.
    pub fn exhausted(&self, interrupted: bool) -> bool {
        !self.submit_queue_failed && self.outcome.exhausted(interrupted)
    }
}
#[derive(Debug, Clone, Default)]
pub struct Finished {
    /// The working directory one object's result lines needed could not be
    /// looked up. Its transfer ran unrendered, and the command reports this
    /// instead.
    pub display_failure: Option<super::backstop::SetupError>,
    pub fatal: Option<String>,
    pub producer: ProducerOutcome,
    pub canceled: bool,
    pub failed: u64,
    pub warned: u64,
    pub stats: Option<Stats>,
    pub list_stats: Option<crt::s3::ListStats>,
    /// Whether the NUMA source pool was installed on the download client;
    /// otherwise the CRT's default pool served it.
    pub numa_source_pool: bool,
    /// The throughput target the client was built with.
    pub crt_target_gbps: f64,
    /// The memory limit the client was built with.
    pub memory_limit_bytes: u64,
}
#[derive(Debug, Clone)]
pub enum Completion {
    /// The CRT client could not be built; named while the library was live.
    ClientFailed(Box<TransferResult>),
    SourceOpenFailed(String),
    Finished(Box<Finished>),
}
/// Where a cp transfer's command-level lines go. They queue on the command's
/// processor behind the transfer lines, and its printer pads them over
/// progress. Under `--quiet` the processor has no printer: the lines the result
/// printer owns are dropped, and a native diagnostic goes to stderr as written
/// (`results::Processor::with_diagnostics`).
#[derive(Debug, Clone, Copy)]
pub struct CommandReport<'a> {
    publisher: &'a results::Publisher,
    printing: bool,
}
impl<'a> CommandReport<'a> {
    pub fn new(publisher: &'a results::Publisher, quiet: bool) -> Self {
        Self {
            publisher,
            printing: !quiet,
        }
    }
    /// Ctrl-C, which the printer reports once.
    pub fn cancel(self) {
        if self.printing {
            self.publisher.publish(results::Event::CtrlC);
        }
    }
    /// `fatal error: ` and `text`, one statement whatever lines it holds.
    pub fn fatal(self, text: impl Into<Vec<u8>>) {
        if self.printing {
            self.publisher.publish(results::Event::Fatal(text.into()));
        }
    }
    /// `fatal error: ` and the botocore sentence for `reason`, whole: a key
    /// it names keeps its newlines. The request is one upstream's botocore
    /// client sends, which `credentials` signed.
    pub fn fatal_reason(self, reason: Reason<'_>, credentials: &crt::credentials::Source) {
        if !self.printing {
            return;
        }
        self.fatal(request_failure::client_sentence_bytes(reason, credentials));
    }
    /// A native diagnostic every mode prints, `--quiet` included.
    pub fn diagnostic(self, line: impl Into<Vec<u8>>) {
        self.publisher
            .publish(results::Event::Diagnostic(line.into()));
    }
}
/// Reports a transfer's completion as the command's result, in one
/// precedence: a client that could not be built is the general handler's
/// failure, as upstream's factory raises it before any transfer; then one
/// object's working directory that could not be looked up; then the
/// statistics; then a Ctrl-C, which supersedes the errors it caused; then an
/// internal error the transfer recorded; then the producer's own failure;
/// then any failed transfer (1), then any warned transfer (2).
pub fn finish_transfer(
    report: CommandReport<'_>,
    source: &OsStr,
    request: &TransferRequest,
    completion: &Completion,
) -> Result<u8, RenderError> {
    match completion {
        Completion::ClientFailed(result) => Err(RenderError::ClientFailed(result.clone())),
        Completion::SourceOpenFailed(error) => {
            report.diagnostic(source_diagnostic("open", source, error));
            Ok(1)
        }
        Completion::Finished(result) => finish_transfer_result(report, source, request, result),
    }
}
fn source_diagnostic(action: &str, source: &OsStr, error: &str) -> Vec<u8> {
    [
        format!("error: unable to {action} recursive upload source ").as_bytes(),
        source.as_encoded_bytes(),
        b": ",
        error.as_bytes(),
    ]
    .concat()
}
fn finish_transfer_result(
    report: CommandReport<'_>,
    source: &OsStr,
    request: &TransferRequest,
    result: &Finished,
) -> Result<u8, RenderError> {
    if let (
        Some(failure),
        ProducerOutcome::ObjectCompleted
        | ProducerOutcome::HeadFailed(_)
        | ProducerOutcome::HeadCanceled
        | ProducerOutcome::HeadMissingLastModified,
    ) = (&result.display_failure, &result.producer)
    {
        return Err(RenderError::Fatal(failure.name().to_owned()));
    }
    finish_transfer_stats(report, request.direction, result)?;
    if let ProducerOutcome::HeadFailed(head) = &result.producer {
        finish_head_failure(report, request, head, result.canceled);
        return Ok(1);
    }
    if result.canceled {
        report.cancel();
        return Ok(1);
    }
    if let Some(fatal) = &result.fatal {
        return Err(RenderError::Fatal(fatal.clone()));
    }
    if finish_transfer_result_producer(report, source, request, &result.producer)? {
        return Ok(1);
    }
    Ok(if result.failed > 0 {
        1
    } else if result.warned > 0 {
        2
    } else {
        0
    })
}
fn finish_transfer_stats(
    report: CommandReport<'_>,
    direction: transfer::Direction,
    finished: &Finished,
) -> io::Result<()> {
    if let Some(stats) = &finished.stats {
        write_transfer_stats(
            report,
            direction,
            stats,
            finished.crt_target_gbps,
            finished.memory_limit_bytes,
            finished.numa_source_pool,
        );
    }
    if let Some(stats) = &finished.list_stats
        && stats.pages > 0
    {
        let mut line = Vec::new();
        list_stats::write(&mut line, stats)?;
        line.pop_if(|byte| *byte == b'\n');
        report.diagnostic(line);
    }
    Ok(())
}
fn finish_transfer_result_producer(
    report: CommandReport<'_>,
    source: &OsStr,
    request: &TransferRequest,
    outcome: &ProducerOutcome,
) -> Result<bool, RenderError> {
    match outcome {
        ProducerOutcome::WalkCompleted | ProducerOutcome::ObjectCompleted => Ok(false),
        ProducerOutcome::SubmitFailed(error) => Err(RenderError::Fatal(error.clone())),
        ProducerOutcome::HeadFailed(_) => Ok(true),
        ProducerOutcome::HeadCanceled => {
            report.cancel();
            Ok(true)
        }
        // `str(KeyError('LastModified'))`.
        ProducerOutcome::HeadMissingLastModified => {
            report.fatal(b"'LastModified'".as_slice());
            Ok(true)
        }
        ProducerOutcome::WalkFailed(error) => {
            report.diagnostic(source_diagnostic("enumerate", source, error));
            Ok(true)
        }
        ProducerOutcome::ComparatorRaised(error) => {
            report.fatal(error.as_bytes());
            Ok(true)
        }
        ProducerOutcome::ListCompleted(list) => finish_recursive_list(report, request, list),
    }
}
fn finish_head_failure(
    report: CommandReport<'_>,
    request: &TransferRequest,
    head: &TransferResult,
    canceled: bool,
) {
    let key = request
        .object
        .as_ref()
        .map_or(&[][..], |object| &object.key);
    let request_key = crate::uri::encode_s3_request_path_key_bytes(key);
    let key = String::from_utf8_lossy(key);
    let reason = Reason {
        result: head,
        missing_key: Some(&key),
        url: RequestUrl::Object {
            endpoint_url: &request.runtime.endpoint_url,
            request_key: &request_key,
        },
    };
    report.fatal_reason(reason, &request.runtime.credentials);
    if canceled {
        report.cancel();
    }
}
fn finish_recursive_list(
    report: CommandReport<'_>,
    request: &TransferRequest,
    list: &ListResult,
) -> Result<bool, RenderError> {
    if let Some(exception) = listing_exception(request, list) {
        report.fatal(exception);
        return Ok(true);
    }
    if let Some(error) = list.local_error {
        return Err(RenderError::Fatal(format!("{error:?}")));
    }
    if list.callback_error != 0 {
        return Ok(finish_recursive_listing_sink_failure(
            report,
            request.direction,
        ));
    }
    Ok(false)
}
/// `str()` of the exception upstream's file generator raises for a listing
/// that stopped before its last object: a page that failed, a 200 response
/// whose document botocore's parser could not read, or a repeated
/// continuation token. Upstream's transfer manager cancels its outstanding
/// transfers on it (`CRTTransferManager.__exit__`).
///
/// A page request the CRT refused, or a page botocore's parser rejected on
/// every attempt, ends the listing as a failed page. None for a listing that
/// named every object, and for one the sink, Ctrl-C, or a local error with
/// no upstream exception stopped.
pub fn listing_exception(request: &TransferRequest, list: &ListResult) -> Option<Vec<u8>> {
    if let Some(error) = list.local_error {
        let cause = match error {
            ListLocalError::UnexpectedRoot => "unexpected root element",
            ListLocalError::InvalidNumber => "invalid numeric value",
            _ => return None,
        };
        let message = format!("Unable to parse response ({cause}), invalid XML received");
        return Some(message.into_bytes());
    }
    if list.callback_error != 0 {
        return None;
    }
    if let Some(token) = &list.repeated_token {
        return Some(request_failure::RepeatedToken { token }.to_vec());
    }
    let result = &list.transfer;
    if result.error_code == 0 && matches!(result.response_status, 0 | 200) {
        return None;
    }
    let reason = Reason {
        result,
        missing_key: None,
        url: RequestUrl::Listing {
            endpoint_url: &request.runtime.endpoint_url,
            request_path: std::str::from_utf8(&list.request_path).unwrap_or(""),
        },
    };
    Some(request_failure::client_sentence_bytes(
        reason,
        &request.runtime.credentials,
    ))
}
fn finish_recursive_listing_sink_failure(
    report: CommandReport<'_>,
    direction: transfer::Direction,
) -> bool {
    report.diagnostic(format!(
        "error: recursive S3 {direction} failed while processing listing output"
    ));
    true
}
#[derive(Debug)]
pub enum RenderError {
    Io(io::Error),
    /// An internal error, which escapes to the general handler by its name.
    Fatal(String),
    /// The client could not be built, which the general handler reports.
    ClientFailed(Box<TransferResult>),
}
impl From<io::Error> for RenderError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}
impl std::fmt::Display for RenderError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(e) => e.fmt(f),
            Self::Fatal(e) => f.write_str(e),
            Self::ClientFailed(result) => {
                f.write_str(&super::backstop::client_failure_message(result))
            }
        }
    }
}
impl std::error::Error for RenderError {}

#[cfg(test)]
mod tests;
