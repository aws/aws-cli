//! Checked `s3 rm` arguments, operand admission, and the plan of each delete.
//!
//! The router binds [`Args`] from a completed parse and asks [`admit`]
//! whether the native path takes them. An admitted invocation's
//! [`DeletePlan`] says which objects it deletes, as upstream's file
//! generator lists them for a delete.
//!
//! ```
//! use s3::rm::{Args, Selection, admit, make_delete_plan};
//! use std::ffi::OsString;
//!
//! // `s3 rm s3://bucket/tree --recursive`
//! let args = Args {
//!     paths: [OsString::from("s3://bucket/tree")],
//!     dir_op: true,
//!     dryrun: false,
//!     quiet: false,
//!     only_show_errors: false,
//!     page_size: None,
//!     request_payer: None,
//!     filters: Vec::new(),
//! };
//! assert_eq!(admit(&args), None);
//! let plan = make_delete_plan(&args);
//! assert_eq!(plan.selection, Selection::Prefix);
//! // The listing takes the operand as a directory.
//! assert_eq!(plan.listing_prefix(), b"tree/");
//! ```
use crate::filter::{Filter, FilterKind, Roots};
use crate::transfer::RequestPayer;
use crate::{AdmissionReason, cp_args, uri};
use awscli_argparse::{ParseResult, Value, bind::BindError, native_args, tables};
use std::ffi::{OsStr, OsString};

mod native;
pub use native::run;

native_args! {
    pub struct Args for tables::RM_ARGUMENTS {
        pub paths: [OsString; 1],
        pub dir_op: bool,
        pub dryrun: bool,
        pub quiet: bool,
        pub only_show_errors: bool,
        pub page_size: Option<i64>,
        pub request_payer: Option<String>,
        pub filters: Vec<(FilterKind, String)>,
    }
}
/// The destinations [`Args`] binds; any other destination is Python's.
pub const DESTINATIONS: &[&str] = Args::FIELD_NAMES;
impl Args {
    /// Binds the arguments a completed parse stored.
    ///
    /// A parameter file loads the one operand as a scalar, which upstream
    /// wraps back into a list before reading it
    /// (`S3TransferCommand._convert_path_args`), so the binding takes either.
    ///
    /// # Errors
    /// Returns [`BindError`] when a destination's value lacks the shape its
    /// field binds.
    pub fn from_result(result: &ParseResult) -> Result<Self, BindError> {
        let Some(operand @ (Value::String(_) | Value::OsString(_))) = result.values.value("paths")
        else {
            return Self::bind(&result.values);
        };
        let mut values = result.values.clone();
        values.put("paths", Value::Array(vec![operand.clone()]), true);
        Self::bind(&values)
    }
}

/// Why a complete rm invocation stays with Python; None admits it.
///
/// Python keeps a page size outside the listing request's range, a request
/// payer native does not know, and an operand the native path does not
/// take.
pub fn admit(args: &Args) -> Option<AdmissionReason> {
    if args
        .page_size
        .is_some_and(|n| !(1..=i64::from(u32::MAX)).contains(&n))
        || request_payer(args).is_err()
    {
        return Some(AdmissionReason::UnsupportedValue);
    }
    if target(&args.paths[0]).is_none() {
        return Some(AdmissionReason::UnsupportedOperand);
    }
    None
}

fn request_payer(
    args: &Args,
) -> Result<Option<RequestPayer>, crate::transfer::UnknownRequestPayer> {
    args.request_payer
        .as_deref()
        .map(RequestPayer::try_from)
        .transpose()
}

fn target(operand: &OsStr) -> Option<uri::S3PrefixUri<'_>> {
    let text = operand.to_str()?;
    if text.contains('\0') {
        return None;
    }
    uri::parse_s3_prefix_uri(text.as_bytes())
        .ok()
        .filter(|remote| uri::supports_native_bucket(remote.bucket))
}

/// What an admitted `s3 rm` deletes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct DeletePlan<'a> {
    /// The operand's bucket.
    pub bucket: &'a str,
    /// The operand's key or prefix, as spelled.
    pub key: &'a [u8],
    /// Which objects under `key` the command deletes.
    pub selection: Selection,
    /// The listing's `--page-size`; zero leaves the request's default.
    pub page_size: u32,
    /// `--request-payer`, which the listing and every DeleteObject send.
    pub request_payer: Option<RequestPayer>,
}
impl DeletePlan<'_> {
    /// The prefix a listing selection lists: `key` as a directory.
    ///
    /// A nonempty prefix ends with `/` (`FileFormat.s3_format`).
    pub fn listing_prefix(&self) -> Vec<u8> {
        uri::normalize_recursive_s3_prefix(self.key)
    }
}
/// Which objects an `s3 rm` names.
///
/// Each is a shape upstream's file generator lists for a delete
/// (`FileGenerator.list_objects`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Selection {
    /// The key a command without `--recursive` names, a folder marker's
    /// included, deleted without a HeadObject or a listing.
    Object,
    /// Every object `--recursive` lists under the key.
    Prefix,
    /// A bucket named without `--recursive`: upstream lists all of it and
    /// still yields each folder marker, a zero-size key ending in `/`, for a
    /// delete, and nothing else.
    FolderMarkers,
}

/// The plan of an invocation the router admitted.
///
/// # Panics
/// Panics when `admit` would have handed the invocation to Python.
#[expect(
    clippy::expect_used,
    reason = "router admission bounds the page size, the request payer, and the operand"
)]
pub fn make_delete_plan(args: &Args) -> DeletePlan<'_> {
    let remote = target(&args.paths[0]).expect("admitted operand");
    let selection = if args.dir_op {
        Selection::Prefix
    } else if remote.prefix.is_empty() {
        Selection::FolderMarkers
    } else {
        Selection::Object
    };
    DeletePlan {
        bucket: remote.bucket,
        key: remote.prefix,
        selection,
        page_size: args
            .page_size
            .map_or(0, |n| u32::try_from(n).expect("admitted page size")),
        request_payer: request_payer(args).expect("admitted request payer"),
    }
}

/// The `--include` and `--exclude` filter of an admitted invocation.
///
/// Upstream roots each pattern at the operand for both its source and its
/// destination, which an `s3 rm` names alike, and its file generator names
/// each object after its bucket and a slash (`create_filter`).
pub fn make_delete_filter(args: &Args, plan: &DeletePlan<'_>) -> Filter {
    if args.filters.is_empty() {
        return Filter::default();
    }
    let root = match plan.selection {
        Selection::Prefix => cp_args::s3_prefix_filter_root(plan.bucket, plan.key),
        Selection::Object | Selection::FolderMarkers => {
            cp_args::s3_object_filter_root(plan.bucket, plan.key)
        }
    };
    let roots = Roots {
        source: &root,
        destination: &root,
    };
    Filter::new(
        &args.filters,
        roots,
        &[plan.bucket.as_bytes(), b"/"].concat(),
    )
}

#[cfg(test)]
mod tests;
