use super::{INVALID_RESPONSE_STATUS_ERROR_CODE, TransferResult};
use std::time::Duration;

const NANOS_PER_MILLI: u64 = 1_000_000;
/// The longest backoff (standard.py `ExponentialBackoff._MAX_BACKOFF`).
const BACKOFF_NANOS_MAX: u64 = 20_000 * NANOS_PER_MILLI;
/// The first backoff's ceiling after a throttling error, and after any other
/// (standard.py `ExponentialBackoff._DEFAULT_BACKOFF_CONFIG`).
const THROTTLING_SCALE_NANOS: u64 = 1_000 * NANOS_PER_MILLI;
const TRANSIENT_SCALE_NANOS: u64 = 50 * NANOS_PER_MILLI;
const BACKOFF_EXPONENT_MAX: u64 = (BACKOFF_NANOS_MAX / TRANSIENT_SCALE_NANOS)
    .next_power_of_two()
    .ilog2() as u64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub(crate) enum ErrorKind {
    Throttling,
    Transient,
}

pub(crate) fn is_unmodeled_throttle(failure: &TransferResult, modeled: &[&[u8]]) -> bool {
    failure.error_code == INVALID_RESPONSE_STATUS_ERROR_CODE
        && failure.response_status == 429
        && !modeled.contains(&failure.service_error.code.as_bytes())
}

pub(crate) fn backoff_delay(
    random: &mut dyn FnMut() -> u64,
    attempt: u64,
    kind: ErrorKind,
) -> Duration {
    debug_assert!(attempt >= 1);
    let scale = match kind {
        ErrorKind::Throttling => THROTTLING_SCALE_NANOS,
        ErrorKind::Transient => TRANSIENT_SCALE_NANOS,
    };
    let exponent = attempt.saturating_sub(1).min(BACKOFF_EXPONENT_MAX);
    let ceiling = (scale << exponent).min(BACKOFF_NANOS_MAX);
    Duration::from_nanos(uint_less_than(random, ceiling))
}
pub(crate) fn random_word() -> u64 {
    use std::hash::{BuildHasher, Hasher};
    std::collections::hash_map::RandomState::new()
        .build_hasher()
        .finish()
}
fn uint_less_than(random: &mut dyn FnMut() -> u64, less_than: u64) -> u64 {
    debug_assert!(less_than > 0);
    let biased = less_than.wrapping_neg() % less_than;
    loop {
        let product = u128::from(random()) * u128::from(less_than);
        if product as u64 >= biased {
            return (product >> 64) as u64;
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Quota {
    pub available: u32,
}
impl Quota {
    /// The starting and largest capacity (quota.py `INITIAL_CAPACITY`).
    pub(crate) const CAPACITY_MAX: u32 = 500;
    /// What a retry takes (standard.py `_RETRY_COST`,
    /// `_THROTTLING_RETRY_COST`).
    pub(crate) const RETRY_COST: u32 = 14;
    pub(crate) const THROTTLING_RETRY_COST: u32 = 5;
    /// What a call that never retried gives back (`_NO_RETRY_INCREMENT`).
    const NO_RETRY_INCREMENT: u32 = 1;
    pub(crate) fn acquire(&mut self, kind: ErrorKind) -> Option<u32> {
        let cost = match kind {
            ErrorKind::Throttling => Self::THROTTLING_RETRY_COST,
            ErrorKind::Transient => Self::RETRY_COST,
        };
        self.available = self.available.checked_sub(cost)?;
        Some(cost)
    }
    pub(crate) fn release(&mut self, last_retry_cost: Option<u32>) {
        let amount = last_retry_cost.unwrap_or(Self::NO_RETRY_INCREMENT);
        self.available = (self.available + amount).min(Self::CAPACITY_MAX);
    }
}
impl Default for Quota {
    fn default() -> Self {
        Self {
            available: Self::CAPACITY_MAX,
        }
    }
}
const _: () = {
    assert!(Quota::THROTTLING_RETRY_COST > Quota::NO_RETRY_INCREMENT);
    assert!(Quota::RETRY_COST > Quota::THROTTLING_RETRY_COST);
};
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Attempts {
    pub count: u64,
    pub last_retry_cost: Option<u32>,
    pub redirected: bool,
}
impl Default for Attempts {
    fn default() -> Self {
        Self {
            count: 1,
            last_retry_cost: None,
            redirected: false,
        }
    }
}
impl Attempts {
    pub(crate) fn exhausted(self, limit: u64) -> Option<u64> {
        (self.count >= limit).then(|| self.count - 1)
    }
    pub(crate) fn admit_retry(&mut self, limit: u64, quota: &mut Quota, kind: ErrorKind) -> bool {
        if self.exhausted(limit).is_some() {
            return false;
        }
        let Some(cost) = quota.acquire(kind) else {
            return false;
        };
        self.last_retry_cost = Some(cost);
        true
    }
}

#[cfg(test)]
mod tests;
