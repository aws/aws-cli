use super::page::Page;
use super::request::{Operation, Query};
use super::{
    ListEntry, ListStats, PAGE_BODY_BYTES_MAX, PAGE_COUNT_MAX, ProbeState, elapsed, nanos, parse,
};
use crate::runtime::BOTOCORE_ATTEMPTS_DEFAULT;
use crate::s3::botocore_retry::{self, Attempts, ErrorKind, Quota};
use crate::s3::{ListLocalError, ListResult, TransferResult};
use crate::signal::lock;
use cli_core::interrupt::Canceled;
use std::sync::Arc;
use std::time::Instant;

pub(super) enum Submit<H> {
    Submitted(H),
    Failed(i32),
}
pub(super) trait PageOps {
    type Handle;
    fn endpoint_path(&mut self, fallback: &[u8]) -> Vec<u8> {
        fallback.to_vec()
    }
    fn submit(
        &mut self,
        page: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>>;
    fn recover_region(&mut self, _failed: &ListResult) -> bool {
        false
    }
    fn cancel(&mut self, handle: &Self::Handle);
    fn release(&mut self, handle: Self::Handle);
    fn backoff(&mut self, attempt: u64, kind: ErrorKind) -> Result<(), Canceled>;
}
pub(super) struct Options<'a> {
    pub endpoint_path: &'a [u8],
    pub query: Query<'a>,
    pub prefetch: bool,
    pub page_attempts: u64,
    pub page_count_max: usize,
    pub page_body_bytes_max: usize,
    pub object_conditions: bool,
}
impl<'a> Options<'a> {
    pub(super) fn new(endpoint_path: &'a [u8], query: Query<'a>, prefetch: bool) -> Self {
        Self {
            endpoint_path,
            query,
            prefetch,
            page_attempts: BOTOCORE_ATTEMPTS_DEFAULT,
            page_count_max: PAGE_COUNT_MAX,
            page_body_bytes_max: PAGE_BODY_BYTES_MAX,
            object_conditions: false,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Action {
    Done,
    Advance,
    SubmitSerial,
    CancelAndDone,
    CancelAndSubmit,
}
#[derive(Debug, Clone, Copy)]
pub(crate) struct NextActionInputs {
    pub page_ok: bool,
    pub should_continue: bool,
    pub prefetch_in_flight: bool,
    pub prefetch_token_matches: bool,
}
pub(crate) fn next_action(inputs: NextActionInputs) -> Action {
    let stop = if inputs.prefetch_in_flight {
        Action::CancelAndDone
    } else {
        Action::Done
    };
    if !inputs.page_ok || !inputs.should_continue {
        return stop;
    }
    if !inputs.prefetch_in_flight {
        return Action::SubmitSerial;
    }
    if inputs.prefetch_token_matches {
        Action::Advance
    } else {
        Action::CancelAndSubmit
    }
}
struct Slot<H> {
    page: Arc<Page>,
    handle: Option<H>,
    shutdown_pending: bool,
    folded: bool,
    path: Vec<u8>,
}
impl<H> Slot<H> {
    fn new(limit: usize) -> Self {
        Self {
            page: Arc::new(Page::new(limit)),
            handle: None,
            shutdown_pending: false,
            folded: false,
            path: Vec::new(),
        }
    }
    fn cancel(&self, ops: &mut impl PageOps<Handle = H>) {
        if let Some(handle) = &self.handle {
            ops.cancel(handle);
        }
    }
    fn await_finish(&mut self, ops: &mut impl PageOps<Handle = H>) {
        if let Some(handle) = self.handle.take() {
            self.page.wait_complete();
            ops.release(handle);
        }
    }
    fn await_shutdown(&mut self, stats: &mut Option<&mut ListStats>) {
        if !self.shutdown_pending {
            return;
        }
        self.page.wait_shutdown();
        self.shutdown_pending = false;
        if self.folded
            && let Some(stats) = stats
        {
            let state = lock(&self.page.inner);
            if let (Some(finish), Some(shutdown)) = (state.finish, state.shutdown_time) {
                stats
                    .shutdown_wait
                    .add(nanos(shutdown.saturating_duration_since(finish)));
            }
        }
    }
    fn prepare(&mut self, stats: &mut Option<&mut ListStats>, limit: usize) {
        debug_assert!(self.handle.is_none());
        self.await_shutdown(stats);
        *self = Self::new(limit);
    }
    fn drain(&mut self, ops: &mut impl PageOps<Handle = H>, stats: &mut Option<&mut ListStats>) {
        self.cancel(ops);
        self.await_finish(ops);
        self.await_shutdown(stats);
    }
}
#[derive(Default)]
struct Tokens {
    parse: Option<Vec<u8>>,
    prefetch: Option<Vec<u8>>,
}
impl Tokens {
    fn parse_non_empty(&self) -> bool {
        self.parse.as_ref().is_some_and(|token| !token.is_empty())
    }
    fn parse_equals(&self, token: Option<&[u8]>) -> bool {
        self.parse.is_some() && self.parse.as_deref() == token
    }
    fn prefetch_matches_parse(&self) -> bool {
        self.prefetch.is_some() && self.prefetch == self.parse
    }
}
struct ReadPage {
    result: TransferResult,
    prefetched: bool,
    parsed: parse::State,
}
enum Parsed {
    Page(parse::State),
    Rejected,
    Failed(Box<ListResult>),
}
struct Driver<'r, 'o, O: PageOps> {
    options: &'r Options<'o>,
    ops: &'r mut O,
    stats: Option<&'r mut ListStats>,
    prev_parse_done: Option<Instant>,
    quota: &'r mut Quota,
}
pub(super) fn run<O: PageOps>(
    options: Options<'_>,
    ops: &mut O,
    stats: Option<&mut ListStats>,
    sink: &mut dyn FnMut(ListEntry) -> i32,
) -> ListResult {
    run_with_quota(options, ops, stats, sink, &mut Quota::default())
}
pub(super) fn run_with_quota<O: PageOps>(
    options: Options<'_>,
    ops: &mut O,
    stats: Option<&mut ListStats>,
    sink: &mut dyn FnMut(ListEntry) -> i32,
    quota: &mut Quota,
) -> ListResult {
    let start = Instant::now();
    let mut driver = Driver {
        options: &options,
        ops,
        stats,
        prev_parse_done: None,
        quota,
    };
    if let Some(stats) = &mut driver.stats {
        **stats = ListStats::default();
    }
    let limit = options.page_body_bytes_max;
    let mut slots = [Slot::new(limit), Slot::new(limit)];
    let result = driver.run_pages(&mut slots, sink);
    for slot in &mut slots {
        slot.drain(driver.ops, &mut driver.stats);
    }
    if let Some(stats) = driver.stats {
        stats.total_ns = elapsed(start);
    }
    result
}
impl<O: PageOps> Driver<'_, '_, O> {
    fn run_pages(
        &mut self,
        slots: &mut [Slot<O::Handle>; 2],
        sink: &mut dyn FnMut(ListEntry) -> i32,
    ) -> ListResult {
        if let Err(result) = self.slot_submit(&mut slots[0], None) {
            return *result;
        }
        let mut tokens = Tokens::default();
        let mut current = 0;
        let page_count_max = self.options.page_count_max;
        for page_index in 0..page_count_max {
            let allow_next = page_index + 1 < page_count_max;
            current = match self.run_page(slots, current, &mut tokens, allow_next, sink) {
                Ok(next) => next,
                Err(result) => return *result,
            };
        }
        page_limit_exceeded()
    }
    fn run_page(
        &mut self,
        slots: &mut [Slot<O::Handle>; 2],
        current: usize,
        tokens: &mut Tokens,
        allow_next: bool,
        sink: &mut dyn FnMut(ListEntry) -> i32,
    ) -> Result<usize, Box<ListResult>> {
        let [first, second] = slots;
        let (slot, other) = if current == 0 {
            (first, second)
        } else {
            (second, first)
        };
        let ReadPage {
            result,
            prefetched,
            parsed,
        } = self.read_page(slot, other, tokens, allow_next, sink)?;
        // Botocore's paginator stops, after yielding the page, when a page
        // names the token it was requested with.
        let repeated = tokens.parse_equals(parsed.next_token.as_deref());
        tokens.parse = parsed.next_token;
        let mut should_continue = parsed.has_more_results && tokens.parse_non_empty();
        let mut finished = ListResult {
            transfer: result,
            ..ListResult::default()
        };
        if should_continue && repeated {
            finished.repeated_token = tokens.parse.clone();
            should_continue = false;
        }
        if should_continue && !allow_next {
            return Err(Box::new(page_limit_exceeded()));
        }
        let prefetch_token_matches = prefetched && tokens.prefetch_matches_parse();
        tokens.prefetch = None;
        let action = next_action(NextActionInputs {
            page_ok: true,
            should_continue,
            prefetch_in_flight: prefetched,
            prefetch_token_matches,
        });
        self.advance(other, current, action, tokens, finished)
    }
    fn read_page(
        &mut self,
        slot: &mut Slot<O::Handle>,
        other: &mut Slot<O::Handle>,
        tokens: &mut Tokens,
        allow_next: bool,
        sink: &mut dyn FnMut(ListEntry) -> i32,
    ) -> Result<ReadPage, Box<ListResult>> {
        let mut attempts = Attempts::default();
        loop {
            let result = self.await_page(slot, tokens.parse.as_deref(), &mut attempts)?;
            let body = std::mem::take(&mut lock(&slot.page.inner).body);
            let prefetched = allow_next
                && self.options.prefetch
                && self.prefetch(&slot.page, &body, other, tokens);
            match self.parse_page(slot, &body, sink) {
                Parsed::Page(parsed) => {
                    self.quota.release(attempts.last_retry_cost);
                    return Ok(ReadPage {
                        result,
                        prefetched,
                        parsed,
                    });
                }
                Parsed::Failed(failure) => return Err(failure),
                Parsed::Rejected => {}
            }
            if prefetched {
                other.cancel(self.ops);
                other.await_finish(self.ops);
            }
            tokens.prefetch = None;
            if !self.retry_page(
                slot,
                tokens.parse.as_deref(),
                &mut attempts,
                ErrorKind::Transient,
            )? {
                // botocore reports the 500 it made of the page.
                let retries = attempts.exhausted(self.options.page_attempts);
                let operation = self.options.query.operation;
                return Err(Box::new(malformed_failure(slot, operation, retries)));
            }
        }
    }
    fn retry_page(
        &mut self,
        slot: &mut Slot<O::Handle>,
        token: Option<&[u8]>,
        attempts: &mut Attempts,
        kind: ErrorKind,
    ) -> Result<bool, Box<ListResult>> {
        debug_assert!(attempts.count >= 1);
        if !attempts.admit_retry(self.options.page_attempts, self.quota, kind) {
            return Ok(false);
        }
        if self.ops.backoff(attempts.count, kind).is_err() {
            return Err(Box::new(ListResult {
                local_error: Some(ListLocalError::Canceled),
                ..ListResult::default()
            }));
        }
        attempts.count += 1;
        self.slot_submit(slot, token)?;
        Ok(true)
    }
    fn advance(
        &mut self,
        other: &mut Slot<O::Handle>,
        current: usize,
        action: Action,
        tokens: &Tokens,
        finished: ListResult,
    ) -> Result<usize, Box<ListResult>> {
        match action {
            Action::Done | Action::CancelAndDone => return Err(Box::new(finished)),
            Action::Advance => return Ok(1 - current),
            Action::CancelAndSubmit => {
                other.cancel(self.ops);
                other.await_finish(self.ops);
            }
            Action::SubmitSerial => {}
        }
        self.slot_submit(other, tokens.parse.as_deref())?;
        Ok(1 - current)
    }
    fn prefetch(
        &mut self,
        current: &Page,
        body: &[u8],
        next: &mut Slot<O::Handle>,
        tokens: &mut Tokens,
    ) -> bool {
        let token = {
            let mut state = lock(&current.inner);
            state.probe.finish();
            if state.probe.state() != ProbeState::Token {
                return false;
            }
            state.probe.token(body).to_vec()
        };
        if tokens.parse_equals(Some(&token)) {
            return false;
        }
        debug_assert!(tokens.prefetch.is_none());
        let submitted = self.slot_submit(next, Some(&token)).is_ok();
        tokens.prefetch = Some(token);
        submitted
    }
    fn slot_submit(
        &mut self,
        slot: &mut Slot<O::Handle>,
        token: Option<&[u8]>,
    ) -> Result<(), Box<ListResult>> {
        slot.prepare(&mut self.stats, self.options.page_body_bytes_max);
        let endpoint_path = self.ops.endpoint_path(self.options.endpoint_path);
        slot.path = self.options.query.build_path(&endpoint_path, token);
        match self.ops.submit(&slot.page, &slot.path) {
            Ok(Submit::Submitted(handle)) => {
                slot.handle = Some(handle);
                slot.shutdown_pending = true;
                Ok(())
            }
            Ok(Submit::Failed(code)) => Err(Box::new(submit_failure(code))),
            Err(transfer) => Err(Box::new(ListResult {
                transfer: *transfer,
                request_path: slot.path.clone(),
                local_error: Some(ListLocalError::CrtFailure),
                ..ListResult::default()
            })),
        }
    }
    fn await_page(
        &mut self,
        slot: &mut Slot<O::Handle>,
        token: Option<&[u8]>,
        attempts: &mut Attempts,
    ) -> Result<TransferResult, Box<ListResult>> {
        let page_attempts = self.options.page_attempts;
        loop {
            let failure = match finished(self.ops, slot) {
                Ok(result) => return Ok(result),
                Err(failure) => named_retries(failure, *attempts, page_attempts),
            };
            if failure.local_error.is_some() {
                return Err(failure);
            }
            if !attempts.redirected && self.ops.recover_region(&failure) {
                attempts.redirected = true;
                attempts.count += 1;
                self.slot_submit(slot, token)?;
                continue;
            }
            let modeled = self.options.query.operation.modeled_errors();
            if !botocore_retry::is_unmodeled_throttle(&failure.transfer, modeled)
                || !self.retry_page(slot, token, attempts, ErrorKind::Throttling)?
            {
                return Err(failure);
            }
        }
    }
    fn parse_page(
        &mut self,
        slot: &mut Slot<O::Handle>,
        body: &[u8],
        sink: &mut dyn FnMut(ListEntry) -> i32,
    ) -> Parsed {
        let start = Instant::now();
        let mut parsed = parse::State {
            object_conditions: self.options.object_conditions,
            ..parse::State::default()
        };
        let result = parse::parse_page(body, self.options.query.operation, &mut parsed, sink);
        let done = Instant::now();
        if let Some(stats) = &mut self.stats {
            let times = ParseTimes {
                start,
                done,
                previous: self.prev_parse_done,
            };
            fold_page_stats(stats, &slot.page, body, &parsed, times);
            slot.folded = true;
        }
        self.prev_parse_done = Some(done);
        match result {
            Ok(()) => Parsed::Page(parsed),
            Err(_) if parsed.document_malformed() => Parsed::Rejected,
            Err(code) => Parsed::Failed(Box::new(ListResult {
                transfer: TransferResult::from_crt_error(code),
                callback_error: parsed.callback_error,
                request_path: slot.path.clone(),
                local_error: parsed.local_error,
                ..ListResult::default()
            })),
        }
    }
}
fn named_retries(
    mut failure: Box<ListResult>,
    attempts: Attempts,
    page_attempts: u64,
) -> Box<ListResult> {
    if failure.local_error.is_none() {
        failure.transfer.retries_exhausted = attempts.exhausted(page_attempts);
    }
    failure
}
fn malformed_failure<H>(slot: &Slot<H>, operation: Operation, retries: Option<u64>) -> ListResult {
    let state = lock(&slot.page.inner);
    let mut transfer = TransferResult {
        response_status: 500,
        request_region: state.request_region.clone(),
        endpoint_url: state.endpoint_url.clone(),
        retries_exhausted: retries,
        ..TransferResult::default()
    };
    transfer.service_error.operation.set(operation.name());
    ListResult {
        transfer,
        request_path: slot.path.clone(),
        ..ListResult::default()
    }
}
fn submit_failure(code: i32) -> ListResult {
    ListResult {
        transfer: TransferResult::from_crt_error(code),
        ..ListResult::default()
    }
}
fn finished<O: PageOps>(
    ops: &mut O,
    slot: &mut Slot<O::Handle>,
) -> Result<TransferResult, Box<ListResult>> {
    slot.await_finish(ops);
    let state = lock(&slot.page.inner);
    let result = state
        .result
        .clone()
        .unwrap_or_else(|| TransferResult::from_crt_error(crate::s3::UNKNOWN_ERROR_CODE));
    if result.error_code == 0 && result.response_status == 200 {
        return Ok(result);
    }
    Err(Box::new(ListResult {
        transfer: result,
        request_path: slot.path.clone(),
        local_error: state.body_error.map(|_| ListLocalError::PageBodyTooLarge),
        ..ListResult::default()
    }))
}
fn page_limit_exceeded() -> ListResult {
    ListResult {
        local_error: Some(ListLocalError::PageLimitExceeded),
        ..ListResult::default()
    }
}
struct ParseTimes {
    start: Instant,
    done: Instant,
    previous: Option<Instant>,
}
fn fold_page_stats(
    stats: &mut ListStats,
    page: &Page,
    body: &[u8],
    parsed: &parse::State,
    times: ParseTimes,
) {
    let mut state = lock(&page.inner);
    stats.pages += 1;
    stats.entries += parsed.entries_emitted;
    stats.ttfb.add(state.first_body.map_or(0, |first| {
        nanos(first.saturating_duration_since(state.submit))
    }));
    stats.transfer.add(
        state
            .first_body
            .zip(state.finish)
            .map_or(0, |(first, finish)| {
                nanos(finish.saturating_duration_since(first))
            }),
    );
    stats
        .parse_emit
        .add(nanos(times.done.saturating_duration_since(times.start)));
    stats.on_entry.add(parsed.on_entry_ns);
    if let Some(previous) = times.previous {
        stats
            .gap
            .add(nanos(state.submit.saturating_duration_since(previous)));
    }
    stats.body_bytes += body.len() as u64;
    stats.chunks += state.chunks;
    stats.first_chunk_bytes += state.first_chunk_bytes;
    stats.probe_ns += state.probe_ns;
    state.probe.finish();
    fold_probe_stats(stats, &state, body, parsed);
}
fn fold_probe_stats(
    stats: &mut ListStats,
    state: &super::page::State,
    body: &[u8],
    parsed: &parse::State,
) {
    let probe_state = state.probe.state();
    debug_assert_ne!(probe_state, ProbeState::Scanning);
    if probe_state.is_resolved() {
        if state.probe_chunk == 1 {
            stats.resolved_chunk1 += 1;
        }
        stats.token_latency.add(state.token_time.map_or(0, |time| {
            nanos(time.saturating_duration_since(state.submit))
        }));
    }
    match probe_state {
        ProbeState::Token => {
            stats.token_pages += 1;
            stats.token_offset_sum += state.probe.match_offset() as u64;
            if Some(state.probe.token(body)) != parsed.next_token.as_deref() {
                stats.token_mismatch += 1;
            }
        }
        ProbeState::FinalPage => {
            stats.final_pages += 1;
            if parsed.has_more_results {
                stats.token_mismatch += 1;
            }
        }
        ProbeState::Unresolved | ProbeState::Scanning => stats.token_unresolved += 1,
    }
}
