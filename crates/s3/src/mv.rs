//! Checked `s3 mv` arguments and their operand admission.
//!
//! Upstream's `mv` is `cp` that deletes each source once its transfer
//! succeeded (the request submitters' `_add_additional_subscribers`). The
//! router binds [`Args`] from a completed parse and asks [`admit`] whether the
//! native path takes them; it takes the operand shapes and options a native
//! copy takes.
//!
//! ```
//! use s3::mv::{Args, admit};
//! use s3::sync::OnCaseConflict;
//! use std::ffi::OsString;
//!
//! // `s3 mv report.txt s3://bucket/reports/`
//! let args = Args {
//!     paths: [OsString::from("report.txt"), OsString::from("s3://bucket/reports/")],
//!     dir_op: false,
//!     dryrun: false,
//!     quiet: false,
//!     no_overwrite: false,
//!     page_size: None,
//!     only_show_errors: false,
//!     progress: true,
//!     progress_frequency: None,
//!     progress_multiline: false,
//!     ignore_glacier_warnings: false,
//!     force_glacier_transfer: false,
//!     validate_same_s3_paths: false,
//!     filters: Vec::new(),
//!     follow_symlinks: true,
//!     case_conflict: OnCaseConflict::Ignore,
//! };
//! assert_eq!(admit(&args), None);
//! // A move between two buckets is Python's, as such a copy is.
//! let args = Args {
//!     paths: [OsString::from("s3://a/key"), OsString::from("s3://b/key")],
//!     ..args
//! };
//! assert!(admit(&args).is_some());
//! ```
use crate::filter::FilterKind;
use crate::sync::OnCaseConflict;
use crate::{AdmissionReason, cp_args};
use awscli_argparse::bind::{BindError, StringMap};
use awscli_argparse::{ParseResult, native_args, tables};
use std::ffi::OsString;

mod native;
pub use native::run;

native_args! {
    pub struct Args for tables::MV_ARGUMENTS {
        pub paths: [OsString; 2],
        pub dir_op: bool,
        pub dryrun: bool,
        pub quiet: bool,
        pub no_overwrite: bool,
        pub page_size: Option<i64>,
        pub only_show_errors: bool,
        pub progress: bool,
        pub progress_frequency: Option<i64>,
        pub progress_multiline: bool,
        pub ignore_glacier_warnings: bool,
        pub force_glacier_transfer: bool,
        pub validate_same_s3_paths: bool,
        pub filters: Vec<(FilterKind, String)>,
        pub follow_symlinks: bool,
        pub case_conflict: OnCaseConflict,
    }
}
/// The destinations [`Args`] binds; any other destination is Python's.
pub const DESTINATIONS: &[&str] = Args::FIELD_NAMES;
impl Args {
    /// Binds the arguments a completed parse stored.
    ///
    /// # Errors
    /// Returns [`BindError`] when a destination's value lacks the shape its
    /// field binds.
    pub fn from_result(result: &ParseResult) -> Result<Self, BindError> {
        Self::bind(&result.values)
    }
    /// The copy the move runs before it deletes each source.
    ///
    /// `--validate-same-s3-paths` is dropped: upstream reads it only for a
    /// move between two S3 paths (`CommandParameters._validate_path_args`),
    /// which is Python's. The copy names no object setting: [`Args`] binds
    /// none, so a move that gives one is Python's.
    pub fn to_copy_args(&self) -> cp_args::Args {
        cp_args::Args {
            paths: self.paths.clone(),
            dir_op: self.dir_op,
            dryrun: self.dryrun,
            quiet: self.quiet,
            no_overwrite: self.no_overwrite,
            page_size: self.page_size,
            only_show_errors: self.only_show_errors,
            progress: self.progress,
            progress_frequency: self.progress_frequency,
            progress_multiline: self.progress_multiline,
            ignore_glacier_warnings: self.ignore_glacier_warnings,
            force_glacier_transfer: self.force_glacier_transfer,
            filters: self.filters.clone(),
            follow_symlinks: self.follow_symlinks,
            content_type: None,
            cache_control: None,
            content_disposition: None,
            content_encoding: None,
            content_language: None,
            expires: None,
            website_redirect: None,
            metadata: StringMap::default(),
            acl: None,
            storage_class: None,
            sse: None,
            sse_kms_key_id: None,
            sse_c: None,
            sse_c_key: None,
            request_payer: None,
            checksum_mode: None,
            checksum_algorithm: None,
            guess_mime_type: true,
            grants: Vec::new(),
            case_conflict: self.case_conflict,
        }
    }
}

/// Why a complete mv invocation stays with Python; None admits it.
///
/// A move admits what its copy does: a page size the listing request takes,
/// and one local operand and one supported S3 URI. A move between two S3
/// paths, and with it the same-path validation, is Python's, as are streams,
/// which upstream refuses for every command but `cp`.
pub fn admit(args: &Args) -> Option<AdmissionReason> {
    cp_args::admit(&args.to_copy_args())
}

#[cfg(test)]
mod tests;
