//! Pure S3 bucket-region redirect policy, mirroring botocore's
//! `S3RegionRedirectorv2` with replay-safety checks ahead of classification.
use crate::s3::{CANCELED_ERROR_CODE, REGION_MAX, ServiceError, TransferResult};
use std::fmt;

/// What a recovery attempt decided. A failed recovery keeps the original
/// failure; only `Ready` selects a new attempt.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Unavailable,
    Ready,
    Canceled,
}

/// The region a failure names. `Missing` permits a HeadBucket lookup;
/// `Invalid` forbids routing altogether.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Target<'a> {
    Missing,
    Invalid,
    Region(&'a str),
}

/// Why a discovered region has no endpoint. Recovery keeps the original
/// failure in every case.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ResolveError {
    /// The rules reached an error, or an endpoint the client refuses.
    InvalidEndpoint,
    /// The rules could not be evaluated, or their result did not parse.
    RulesUnavailable,
}

/// A re-resolved bucket endpoint for a discovered region.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolvedEndpoint {
    /// Bucket endpoint including any base path.
    pub url: String,
    /// Rule-selected signing region; the client region when absent.
    pub signing_region: Option<String>,
}

/// Command-owned inputs that re-evaluate one bucket's endpoint rules for a
/// discovered region without re-reading configuration.
pub trait Resolver: Send + Sync + fmt::Debug {
    /// The bucket the runtime was built for.
    fn bucket(&self) -> &str;
    /// The normalized client-region identity, distinct from a signing region:
    /// FIPS aliases stripped, `aws-global` when no region is configured.
    fn client_region(&self) -> &str;
    fn resolve(&self, region: &str) -> Result<ResolvedEndpoint, ResolveError>;
}

/// A present header wins, even an empty, malformed, or truncated one; then
/// malformed XML is invalid; then a present, nonempty XML `<Region>`.
pub fn target_region(error: &ServiceError) -> Target<'_> {
    let text = if error.region_header.is_present() {
        &error.region_header
    } else if error.region_body_invalid {
        return Target::Invalid;
    } else if error.region_body.is_present() && !error.region_body.is_empty() {
        &error.region_body
    } else {
        return Target::Missing;
    };
    if text.is_truncated() || !valid_region(text.as_bytes()) {
        return Target::Invalid;
    }
    std::str::from_utf8(text.as_bytes()).map_or(Target::Invalid, Target::Region)
}

/// Whether a failed request may recover through a discovered region. Missing
/// region metadata may still be discovered; invalid metadata may not.
pub fn is_candidate(bucket: &str, result: &TransferResult, transfer: bool) -> bool {
    if !supports_bucket(bucket) {
        return false;
    }
    if result.error_code == 0 || result.response_status < 300 {
        return false;
    }
    if result.canceled_by_interrupt || result.error_code == CANCELED_ERROR_CODE {
        return false;
    }
    if transfer && (result.bytes_transferred != 0 || result.body_delivered) {
        return false;
    }
    if target_region(&result.service_error) == Target::Invalid {
        return false;
    }
    is_redirect_response(result)
}

/// Only ordinary bucket endpoints can be re-resolved for another region.
pub fn supports_bucket(bucket: &str) -> bool {
    !bucket.is_empty() && !bucket.starts_with("arn:") && !bucket.ends_with("--x-s3")
}

fn is_redirect_response(result: &TransferResult) -> bool {
    let error = &result.service_error;
    let operation = error.operation.as_bytes();
    if operation == b"ListBuckets" {
        return false;
    }
    if matches!(result.response_status, 301 | 302 | 307) {
        return true;
    }
    match error.code.as_bytes() {
        b"PermanentRedirect" => return true,
        b"AuthorizationHeaderMalformed" => return error.region_body.is_present(),
        b"IllegalLocationConstraintException" => return operation != b"CreateBucket",
        _ => {}
    }
    result.response_status == 400
        && match operation {
            b"HeadObject" => true,
            b"HeadBucket" => error.region_header.is_present(),
            _ => false,
        }
}

fn valid_region(region: &[u8]) -> bool {
    let (Some(first), Some(last)) = (region.first(), region.last()) else {
        return false;
    };
    region.len() <= REGION_MAX
        && first.is_ascii_alphanumeric()
        && last.is_ascii_alphanumeric()
        && region
            .iter()
            .all(|byte| byte.is_ascii_alphanumeric() || *byte == b'-')
        && !region.iter().all(u8::is_ascii_digit)
}

#[cfg(test)]
mod tests;
