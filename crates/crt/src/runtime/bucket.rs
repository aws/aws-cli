use super::{Runtime, RuntimeOptions};
use crate::debug::Logger;
use crate::redirect::{self, Outcome, Resolver, Target};
use crate::s3::botocore_retry::{self, Attempts, ErrorKind, Quota};
use crate::s3::{
    CANCELED_ERROR_CODE, HeadObject, HeadObjectResult, RequestKind, RequestOptions, ServiceError,
    TransferResult,
};
use crate::signal::lock;
use cli_core::interrupt::State;
use std::sync::{Arc, Mutex, OnceLock};

/// Owns the original runtime and, once a redirect discovers the bucket's
/// region, one immutable regional runtime. Both live until this value drops,
/// which the command does only after scheduler drain and worker join.
#[derive(Debug)]
pub struct BucketRuntime {
    regional: OnceLock<Arc<Runtime>>,
    original: Arc<Runtime>,
    recovery: Option<Recovery>,
    quota: Mutex<Quota>,
}

#[derive(Debug)]
struct Recovery {
    options: RuntimeOptions,
    resolver: Arc<dyn Resolver>,
    logger: Option<Arc<Logger>>,
    lock: Mutex<()>,
}

impl BucketRuntime {
    /// Builds the bucket's client. With a resolver, the client's region
    /// identity is the resolver's normalized client region.
    pub fn new(
        mut options: RuntimeOptions,
        resolver: Option<Arc<dyn Resolver>>,
        logger: Option<Arc<Logger>>,
    ) -> Result<Self, Box<TransferResult>> {
        if let Some(resolver) = &resolver {
            resolver.client_region().clone_into(&mut options.region);
        }
        let original = Arc::new(build(options.clone(), logger.clone())?);
        Ok(Self {
            regional: OnceLock::new(),
            original,
            recovery: resolver.map(|resolver| Recovery {
                options,
                resolver,
                logger,
                lock: Mutex::new(()),
            }),
            quota: Mutex::new(Quota::default()),
        })
    }

    /// The published regional client, else the original; never blocks.
    pub fn selected(&self) -> &Arc<Runtime> {
        self.regional.get().unwrap_or(&self.original)
    }

    /// The client the command was built with, which sends every HeadBucket.
    pub fn original(&self) -> &Arc<Runtime> {
        &self.original
    }

    /// Heads `key` on the selected client, as the AWS CLI's botocore client
    /// sends a single download's HeadObject (`call`). A HEAD has no
    /// same-region veto.
    pub fn head_object(
        &self,
        head: HeadObject<'_>,
        interrupt: &State,
    ) -> Result<HeadObjectResult, Box<TransferResult>> {
        let modeled = modeled_errors(RequestKind::Head);
        self.call(modeled, false, interrupt, || {
            self.selected().head_object(head, interrupt)
        })
    }

    /// Sends one request on the selected client and waits for its result, as
    /// the AWS CLI's botocore client sends it (`call`): a move's source
    /// DeleteObject. As for a transfer, a request the regional client already
    /// sent is not replayed there. Runs on a request owner, never a CRT
    /// callback.
    pub fn send(
        &self,
        options: RequestOptions<'_>,
        interrupt: &State,
    ) -> Result<TransferResult, Box<TransferResult>> {
        self.call(modeled_errors(options.kind), true, interrupt, || {
            Ok(self.selected().submit(options, interrupt)?.wait().transfer)
        })
    }

    fn call<R: CallResult>(
        &self,
        modeled: &[&[u8]],
        transfer: bool,
        interrupt: &State,
        mut send: impl FnMut() -> Result<R, Box<TransferResult>>,
    ) -> Result<R, Box<TransferResult>> {
        let limit = self.original.options().botocore_attempts;
        let mut attempts = Attempts::default();
        loop {
            let mut result = send()?;
            let outcome = result.transfer_mut();
            if !attempts.redirected {
                match self.recover_region(outcome, transfer, interrupt) {
                    Outcome::Unavailable => {}
                    Outcome::Ready => {
                        attempts.redirected = true;
                        attempts.count += 1;
                        continue;
                    }
                    Outcome::Canceled => {
                        cancel(outcome);
                        return Ok(result);
                    }
                }
            }
            if outcome.error_code == 0 {
                lock(&self.quota).release(attempts.last_retry_cost);
                return Ok(result);
            }
            let kind = ErrorKind::Throttling;
            if !botocore_retry::is_unmodeled_throttle(outcome, modeled)
                || !attempts.admit_retry(limit, &mut lock(&self.quota), kind)
            {
                outcome.retries_exhausted = attempts.exhausted(limit);
                return Ok(result);
            }
            let delay = botocore_retry::backoff_delay(
                &mut botocore_retry::random_word,
                attempts.count,
                kind,
            );
            if interrupt.sleep(delay).is_err() {
                cancel(outcome);
                return Ok(result);
            }
            attempts.count += 1;
        }
    }

    /// Runs on a request owner, never a CRT callback. A published client is
    /// shared by stale failures without another lookup; a failed lookup
    /// leaves later discovery possible. `transfer` vetoes a replay into the
    /// region the failed request already used.
    pub fn recover_region(
        &self,
        result: &TransferResult,
        transfer: bool,
        interrupt: &State,
    ) -> Outcome {
        let Some(recovery) = &self.recovery else {
            return Outcome::Unavailable;
        };
        if !redirect::is_candidate(recovery.resolver.bucket(), result, transfer) {
            return Outcome::Unavailable;
        }
        if interrupt.is_requested() {
            return Outcome::Canceled;
        }
        let _serialized = lock(&recovery.lock);
        if interrupt.is_requested() {
            return Outcome::Canceled;
        }
        self.recover_locked(recovery, result, transfer, interrupt)
    }

    fn recover_locked(
        &self,
        recovery: &Recovery,
        result: &TransferResult,
        transfer: bool,
        interrupt: &State,
    ) -> Outcome {
        let request_region = result.request_region.as_bytes();
        if let Some(regional) = self.regional.get() {
            let same_region = request_region == regional.client_region().as_bytes();
            return if transfer && same_region {
                Outcome::Unavailable
            } else {
                Outcome::Ready
            };
        }
        let discovered = self.discover_region(&result.service_error, interrupt);
        if interrupt.is_requested() {
            return Outcome::Canceled;
        }
        let Some(region) = discovered else {
            return Outcome::Unavailable;
        };
        if transfer && region.as_bytes() == request_region {
            return Outcome::Unavailable;
        }
        self.publish(recovery, &region, interrupt)
    }

    fn discover_region(&self, error: &ServiceError, interrupt: &State) -> Option<String> {
        match redirect::target_region(error) {
            Target::Invalid => return None,
            Target::Region(region) => return Some(region.to_owned()),
            Target::Missing => {}
        }
        let head = self.original.head_bucket(interrupt).ok()?;
        match redirect::target_region(&head.transfer.service_error) {
            Target::Region(region) => Some(region.to_owned()),
            Target::Missing | Target::Invalid => None,
        }
    }

    fn publish(&self, recovery: &Recovery, region: &str, interrupt: &State) -> Outcome {
        let Ok(endpoint) = recovery.resolver.resolve(region) else {
            return Outcome::Unavailable;
        };
        let options = RuntimeOptions {
            region: region.to_owned(),
            endpoint_url: endpoint.url,
            signing_region: endpoint.signing_region,
            ..recovery.options.clone()
        };
        if interrupt.is_requested() {
            return Outcome::Canceled;
        }
        let Ok(runtime) = build(options, recovery.logger.clone()) else {
            return Outcome::Unavailable;
        };
        let _ = self.regional.set(Arc::new(runtime));
        if interrupt.is_requested() {
            Outcome::Canceled
        } else {
            Outcome::Ready
        }
    }
}

trait CallResult {
    fn transfer_mut(&mut self) -> &mut TransferResult;
}
impl CallResult for TransferResult {
    fn transfer_mut(&mut self) -> &mut TransferResult {
        self
    }
}
impl CallResult for HeadObjectResult {
    fn transfer_mut(&mut self) -> &mut TransferResult {
        &mut self.transfer
    }
}
fn cancel(outcome: &mut TransferResult) {
    outcome.error_code = CANCELED_ERROR_CODE;
    outcome.canceled_by_interrupt = true;
}
/// The error codes the model names for the operation a request of `kind`
/// sends (s3 service-2.json), which botocore's retries leave to the model.
fn modeled_errors(kind: RequestKind) -> &'static [&'static [u8]] {
    match kind {
        RequestKind::Get => &[b"NoSuchKey", b"InvalidObjectState"],
        RequestKind::Head => &[b"NoSuchKey"],
        RequestKind::Put => &[
            b"InvalidRequest",
            b"InvalidWriteOffset",
            b"TooManyParts",
            b"EncryptionTypeMismatch",
        ],
        RequestKind::HeadBucket => &[b"NoSuchBucket"],
        RequestKind::Delete => &[],
    }
}

fn build(
    options: RuntimeOptions,
    logger: Option<Arc<Logger>>,
) -> Result<Runtime, Box<TransferResult>> {
    match logger {
        Some(logger) => Runtime::new_with_logger(options, logger),
        None => Runtime::new(options),
    }
}

#[cfg(test)]
mod tests;
