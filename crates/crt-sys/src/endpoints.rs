//! Narrow endpoint-rule declarations over opaque CRT-owned objects.
use crate::{AwsAllocator, AwsByteCursor};
use std::ffi::c_int;
macro_rules! opaque {
    ($($name:ident),+) => {
        $(
            #[repr(C)]
            #[derive(Debug)]
            pub struct $name {
                _private: [u8; 0],
            }
        )+
    };
}
opaque!(Ruleset, Partitions, Engine, Context, Resolved);
/// `AWS_ENDPOINTS_RESOLVED_ERROR`, the `aws_endpoints_resolved_endpoint_get_type`
/// value of a reached error rule (sigcheck.c static-asserts it).
pub const AWS_ENDPOINTS_RESOLVED_ERROR: c_int = 1;
// SAFETY: constructors return counted references; callers keep dependencies alive
// until release and copy result cursors before releasing the resolved endpoint.
c_functions! {
    /// Counted initialization of aws-c-sdkutils and the libraries it needs,
    /// without the I/O, TLS, and S3 layers.
    pub fn aws_sdkutils_library_init(allocator: *mut AwsAllocator);
    pub fn aws_sdkutils_library_clean_up();
    pub fn aws_endpoints_ruleset_new_from_string(
        allocator: *mut AwsAllocator,
        rules: AwsByteCursor,
    ) -> *mut Ruleset;
    pub fn aws_endpoints_ruleset_release(rules: *mut Ruleset) -> *mut Ruleset;
    pub fn aws_partitions_config_new_from_string(
        allocator: *mut AwsAllocator,
        partitions: AwsByteCursor,
    ) -> *mut Partitions;
    pub fn aws_partitions_config_release(partitions: *mut Partitions) -> *mut Partitions;
    pub fn aws_endpoints_rule_engine_new(
        allocator: *mut AwsAllocator,
        rules: *mut Ruleset,
        partitions: *mut Partitions,
    ) -> *mut Engine;
    pub fn aws_endpoints_rule_engine_release(engine: *mut Engine) -> *mut Engine;
    pub fn aws_endpoints_request_context_new(allocator: *mut AwsAllocator) -> *mut Context;
    pub fn aws_endpoints_request_context_release(context: *mut Context) -> *mut Context;
    pub fn aws_endpoints_request_context_add_string(
        allocator: *mut AwsAllocator,
        context: *mut Context,
        name: AwsByteCursor,
        value: AwsByteCursor,
    ) -> c_int;
    pub fn aws_endpoints_request_context_add_boolean(
        allocator: *mut AwsAllocator,
        context: *mut Context,
        name: AwsByteCursor,
        value: bool,
    ) -> c_int;
    pub fn aws_endpoints_rule_engine_resolve(
        engine: *mut Engine,
        context: *const Context,
        out: *mut *mut Resolved,
    ) -> c_int;
    pub fn aws_endpoints_resolved_endpoint_get_type(endpoint: *const Resolved) -> c_int;
    pub fn aws_endpoints_resolved_endpoint_get_url(
        endpoint: *const Resolved,
        out: *mut AwsByteCursor,
    ) -> c_int;
    pub fn aws_endpoints_resolved_endpoint_get_properties(
        endpoint: *const Resolved,
        out: *mut AwsByteCursor,
    ) -> c_int;
    pub fn aws_endpoints_resolved_endpoint_get_error(
        endpoint: *const Resolved,
        out: *mut AwsByteCursor,
    ) -> c_int;
    pub fn aws_endpoints_resolved_endpoint_release(endpoint: *mut Resolved) -> *mut Resolved;
}
