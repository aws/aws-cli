//! Sample values that engage each setting, for the decision-table tests.

use super::*;

/// A value that engages `setting`: one its match accepts, and
/// one its consumer accepts for an honored row. A CA bundle row's value is a
/// relative path to a bundle of one certificate where the crate's tests run,
/// and the `services` row's names a section the caller must define.
pub(crate) fn sample_value(setting: &Setting) -> &'static str {
    if let Support::Honored(consumer) = setting.support
        && let Some(value) = sample_consumer_value(consumer, setting.source)
    {
        return value;
    }
    match setting.matching {
        Match::Present | Match::Nonempty => "value",
        Match::HistoryEnabled => "enabled",
        Match::StructuredErrorFormat => "json",
        Match::VariableReference => "$HOME/config",
    }
}
fn sample_consumer_value(consumer: Consumer, source: Source) -> Option<&'static str> {
    match consumer {
        Consumer::Record(field) => sample_record_value(field, source),
        Consumer::Endpoint => names_endpoint_url(source).then_some("http://localhost:4566"),
        Consumer::Credentials => sample_credentials_value(source),
        Consumer::Region | Consumer::SharedFiles => None,
    }
}
/// An expiry in the form the native chain reads, and instance metadata
/// settings in the forms botocore accepts.
fn sample_credentials_value(source: Source) -> Option<&'static str> {
    match source {
        Source::Env("AWS_CREDENTIAL_EXPIRATION") => Some("2037-10-21T07:28:00Z"),
        Source::Chain(_, "metadata_service_timeout" | "metadata_service_num_attempts") => Some("2"),
        Source::Chain(_, "ec2_metadata_service_endpoint") => Some("http://localhost:1338"),
        Source::Chain(_, "ec2_metadata_service_endpoint_mode") => Some("ipv6"),
        _ => None,
    }
}
fn names_endpoint_url(source: Source) -> bool {
    match source {
        Source::Env(name) => name.starts_with("AWS_ENDPOINT_URL"),
        Source::Chain(_, key) => key == "endpoint_url",
        Source::Profile(_) | Source::S3(_) | Source::ErrorFormat => false,
    }
}
fn sample_record_value(field: Field, source: Source) -> Option<&'static str> {
    let key = match source {
        Source::S3(key) => key,
        Source::Env(_) | Source::Profile(_) | Source::Chain(..) | Source::ErrorFormat => "",
    };
    Some(match field {
        Field::CaBundle => "testdata/ca.pem",
        Field::Proxy => "http://proxy.test:3128",
        Field::TcpKeepalive => "true",
        Field::MaxAttempts => "5",
        Field::RetryMode => "standard",
        Field::RequestChecksumCalculation | Field::ResponseChecksumValidation => "when_required",
        Field::Transfer => return sample_transfer_value(key),
        Field::MemoryLimit => "512",
        Field::S3Endpoint if key == "addressing_style" => "virtual",
        Field::S3Endpoint => "true",
        Field::AppId | Field::ExecutionEnv => "sample",
    })
}
const TRANSFER_SAMPLES: [(&str, &str); 11] = [
    ("target_bandwidth", "100MB/s"),
    ("preferred_transfer_client", "crt"),
    ("multipart_threshold", "16MB"),
    ("multipart_chunksize", "16MB"),
    ("max_concurrent_requests", "20"),
    ("max_queue_size", "100"),
    ("max_bandwidth", "10MB/s"),
    ("io_chunksize", "1MB"),
    ("should_stream", "true"),
    ("disk_throughput", "500MB/s"),
    ("direct_io", "true"),
];
pub(super) fn sample_transfer_value(key: &str) -> Option<&'static str> {
    TRANSFER_SAMPLES
        .iter()
        .find_map(|&(name, value)| (name == key).then_some(value))
}
