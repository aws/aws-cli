//! Native S3 listing argument binding, admission, streaming, and rendering.
use crate::{AdmissionReason, uri};
use awscli_argparse::{ParseResult, bind::BindError, native_args, tables};
use std::ffi::OsString;

native_args! {
    pub struct Args for tables::LS_ARGUMENTS {
        pub paths: OsString,
        pub dir_op: bool,
        pub page_size: Option<i64>,
        pub human_readable: bool,
        pub summarize: bool,
        pub request_payer: Option<String>,
        pub bucket_name_prefix: Option<OsString>,
        pub bucket_region: Option<OsString>,
    }
}
pub const DESTINATIONS: &[&str] = Args::FIELD_NAMES;
impl Args {
    pub fn from_result(result: &ParseResult) -> Result<Self, BindError> {
        Self::bind(&result.values)
    }
}
pub fn admit(args: &Args) -> Option<AdmissionReason> {
    if args
        .page_size
        .is_some_and(|n| !(1..=i64::from(u32::MAX)).contains(&n))
        || [&args.bucket_name_prefix, &args.bucket_region]
            .into_iter()
            .flatten()
            .any(|v| v.as_encoded_bytes().contains(&0))
    {
        return Some(AdmissionReason::UnsupportedValue);
    }
    let paths = args.paths.as_encoded_bytes();
    if paths.contains(&0) {
        return Some(AdmissionReason::UnsupportedOperand);
    }
    match uri::parse_s3_list_target(Some(paths)) {
        Ok(v) if v.bucket.is_none_or(uri::supports_native_bucket) => None,
        _ => Some(AdmissionReason::UnsupportedOperand),
    }
}

#[cfg(test)]
mod tests;

mod listing;
#[doc(inline)]
pub use listing::{
    Backend, Entry, EntryKind, Error, ListExecutionOptions, Request, execute, list_command_failure,
};
mod native;
pub use native::run;
