//! Endpoint-rule parameters and owned resolutions from the CRT engine.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Parameters<'a> {
    pub region: &'a str,
    pub bucket: Option<&'a str>,
    pub use_fips: bool,
    pub use_dual_stack: bool,
    pub endpoint: Option<&'a str>,
    pub force_path_style: Option<bool>,
    pub accelerate: Option<bool>,
    pub use_global_endpoint: Option<bool>,
    pub disable_multi_region_access_points: Option<bool>,
    pub use_arn_region: Option<bool>,
}
/// The two JSON documents a resolution evaluates, named because both are
/// byte slices that a positional call could swap unnoticed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Documents<'a> {
    /// The service's endpoint rule set.
    pub rules_json: &'a [u8],
    /// The partitions that the rule set's partition function reads.
    pub partitions_json: &'a [u8],
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Resolved {
    Endpoint { url: Vec<u8>, properties: Vec<u8> },
    RuleError(Vec<u8>),
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum ResolveError {
    OutOfMemory,
    InvalidRuleset,
    InvalidPartitions,
    ResolveFailed,
}
impl std::fmt::Display for ResolveError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::OutOfMemory => "endpoint allocation failed",
            Self::InvalidRuleset => "invalid endpoint ruleset",
            Self::InvalidPartitions => "invalid endpoint partitions",
            Self::ResolveFailed => "endpoint resolution failed",
        })
    }
}
impl std::error::Error for ResolveError {}
mod native;
#[doc(inline)]
pub use native::resolve;
