use super::parse::ListingError;
use super::{PAGE_BODY_BYTES_MAX, ProbeState, TokenProbe, elapsed};
use crate::s3::{BoundedText, ENDPOINT_URL_MAX, REGION_MAX, TransferResult};
use crate::signal::lock;
use std::sync::{Condvar, Mutex};
use std::time::Instant;

#[derive(Debug)]
pub(super) struct Page {
    pub inner: Mutex<State>,
    changed: Condvar,
    pub body_bytes_max: usize,
}
#[derive(Debug)]
pub(super) struct State {
    pub body: Vec<u8>,
    pub probe: TokenProbe,
    pub result: Option<TransferResult>,
    pub body_error: Option<i32>,
    pub shutdown: bool,
    pub attempt_status: i32,
    pub submit: Instant,
    pub first_body: Option<Instant>,
    pub finish: Option<Instant>,
    pub shutdown_time: Option<Instant>,
    pub token_time: Option<Instant>,
    pub chunks: u64,
    pub first_chunk_bytes: u64,
    pub probe_chunk: u64,
    pub probe_ns: u64,
    pub request_region: BoundedText<REGION_MAX>,
    pub endpoint_url: BoundedText<ENDPOINT_URL_MAX>,
}
impl Page {
    #[cfg(test)]
    pub(super) fn finish_response(&self, code: i32, status: i32, body: &[u8], operation: &[u8]) {
        let mut result = crate::s3::transfer_result(code, status, body, operation, "");
        result.response_status = status;
        self.finish(result);
    }
    pub(super) fn record_provenance(&self, region: &[u8], endpoint_url: &[u8]) {
        let mut state = lock(&self.inner);
        state.request_region.set(region);
        state.endpoint_url.set(endpoint_url);
    }
    pub(super) fn new(body_bytes_max: usize) -> Self {
        debug_assert!(body_bytes_max > 0 && body_bytes_max <= PAGE_BODY_BYTES_MAX);
        Self {
            inner: Mutex::new(State {
                body: Vec::new(),
                probe: TokenProbe::default(),
                result: None,
                body_error: None,
                shutdown: false,
                attempt_status: 0,
                submit: Instant::now(),
                first_body: None,
                finish: None,
                shutdown_time: None,
                token_time: None,
                chunks: 0,
                first_chunk_bytes: 0,
                probe_chunk: 0,
                probe_ns: 0,
                request_region: BoundedText::default(),
                endpoint_url: BoundedText::default(),
            }),
            changed: Condvar::new(),
            body_bytes_max,
        }
    }
    pub(super) fn append_chunk(&self, chunk: &[u8]) -> Result<(), i32> {
        if chunk.is_empty() {
            return Ok(());
        }
        let mut state = lock(&self.inner);
        if let Some(code) = state.body_error {
            return Err(code);
        }
        if chunk.len() > self.body_bytes_max - state.body.len() {
            let code = ListingError::ExceedsMemoryLimit.code();
            state.body_error = Some(code);
            return Err(code);
        }
        let required = state.body.len() + chunk.len();
        if required > state.body.capacity() {
            let capacity = required
                .max(state.body.capacity().saturating_mul(2))
                .min(self.body_bytes_max);
            let additional = capacity - state.body.len();
            state.body.reserve_exact(additional);
        }
        state.chunks += 1;
        if state.chunks == 1 {
            state.first_body = Some(Instant::now());
            state.first_chunk_bytes = chunk.len() as u64;
        }
        state.body.extend_from_slice(chunk);
        if state.probe.state() == ProbeState::Scanning {
            let start = Instant::now();
            let State { body, probe, .. } = &mut *state;
            let resolved = probe.scan(body);
            state.probe_ns += elapsed(start);
            if resolved.is_resolved() {
                state.token_time = Some(Instant::now());
                state.probe_chunk = state.chunks;
            }
        }
        Ok(())
    }
    pub(super) fn finish(&self, mut result: TransferResult) {
        let mut state = lock(&self.inner);
        if let Some(code) = state.body_error {
            result = TransferResult::from_crt_error(code);
        }
        if result.response_status == 0
            && matches!(
                result.crt_name.as_bytes(),
                b"AWS_ERROR_S3_INTERNAL_ERROR"
                    | b"AWS_ERROR_S3_SLOW_DOWN"
                    | b"AWS_ERROR_S3_REQUEST_TIMEOUT"
                    | b"AWS_ERROR_S3_REQUEST_TIME_TOO_SKEWED"
            )
        {
            result.response_status = state.attempt_status;
        }
        result.request_region = state.request_region.clone();
        result.endpoint_url = state.endpoint_url.clone();
        state.finish = Some(Instant::now());
        state.result = Some(result);
        self.changed.notify_all();
    }
    pub(super) fn shutdown(&self) {
        let mut state = lock(&self.inner);
        state.shutdown_time = Some(Instant::now());
        state.shutdown = true;
        self.changed.notify_all();
    }
    pub(super) fn wait_complete(&self) {
        let mut state = lock(&self.inner);
        while state.result.is_none() {
            state = self
                .changed
                .wait(state)
                .unwrap_or_else(std::sync::PoisonError::into_inner);
        }
    }
    pub(super) fn wait_shutdown(&self) {
        let mut state = lock(&self.inner);
        while !state.shutdown {
            state = self
                .changed
                .wait(state)
                .unwrap_or_else(std::sync::PoisonError::into_inner);
        }
    }
}
