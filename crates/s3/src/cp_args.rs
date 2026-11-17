//! Checked copy arguments, operand admission, and pure transfer planning.
use crate::filter::{Filter, FilterKind, Roots};
use crate::object_settings::ObjectSettings;
use crate::sync::{BothSides, DestinationOnly, OnCaseConflict, SourceOnly, Strategies};
use crate::{AdmissionReason, uri};
use awscli_argparse::bind::{BindError, StringMap};
use awscli_argparse::{ParseResult, native_args, tables};
use std::ffi::{OsStr, OsString};
use std::path::Path;

native_args! {
    pub struct Args for tables::CP_ARGUMENTS {
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
        pub filters: Vec<(FilterKind, String)>,
        pub follow_symlinks: bool,
        pub content_type: Option<String>,
        pub cache_control: Option<String>,
        pub content_disposition: Option<String>,
        pub content_encoding: Option<String>,
        pub content_language: Option<String>,
        pub expires: Option<String>,
        pub website_redirect: Option<String>,
        pub metadata: StringMap,
        pub acl: Option<String>,
        pub storage_class: Option<String>,
        pub sse: Option<String>,
        pub sse_kms_key_id: Option<String>,
        pub sse_c: Option<String>,
        pub sse_c_key: Option<Vec<u8>>,
        pub request_payer: Option<String>,
        pub checksum_mode: Option<String>,
        pub checksum_algorithm: Option<String>,
        pub guess_mime_type: bool,
        pub grants: Vec<String>,
        pub case_conflict: OnCaseConflict,
    }
}
pub const DESTINATIONS: &[&str] = Args::FIELD_NAMES;
impl Args {
    pub fn printer(&self) -> Option<crate::results::PrinterConfig> {
        crate::results::Flags {
            quiet: self.quiet,
            only_show_errors: self.only_show_errors,
            is_stream: self.paths.iter().any(|p| p == "-"),
            progress: self.progress,
            progress_frequency: self.progress_frequency.unwrap_or(0),
            progress_multiline: self.progress_multiline,
        }
        .select()
    }
    pub fn from_result(result: &ParseResult) -> Result<Self, BindError> {
        Self::bind(&result.values)
    }
    /// The strategies a recursive download checks case conflicts by, if any.
    ///
    /// Upstream checks only a recursive download, under a `--case-conflict`
    /// other than `ignore`
    /// (`CommandArchitecture._should_handle_case_conflicts`), and runs it as a
    /// sync that replaces a file of the object's name, checks an object the
    /// destination lacks, and keeps a file only the destination holds
    /// (`CommandArchitecture._modify_instructions_for_case_conflicts`). None
    /// copies every source.
    pub fn case_conflict_strategies(&self) -> Option<Strategies> {
        let conflict = self.case_conflict.handling()?;
        matches!(
            copy_operation(&self.paths[0], &self.paths[1], self.dir_op),
            Some(Operation::RecursiveDownload(_))
        )
        .then_some(Strategies {
            both: BothSides::Always,
            source_only: SourceOnly::CaseConflict(conflict),
            destination_only: DestinationOnly::Keep,
        })
    }
}

/// Why a complete cp invocation stays with Python: a page size outside the
/// listing request's range, a setting value native does not know or
/// convert, an operand shape the native transfer path does not implement,
/// or object settings an upload could not send as upstream does. None
/// admits the invocation.
pub fn admit(args: &Args) -> Option<AdmissionReason> {
    let Ok(settings) = ObjectSettings::from_args(args) else {
        return Some(AdmissionReason::UnsupportedValue);
    };
    if args
        .page_size
        .is_some_and(|n| !(1..=i64::from(u32::MAX)).contains(&n))
    {
        return Some(AdmissionReason::UnsupportedValue);
    }
    let Some(operation) = copy_operation(&args.paths[0], &args.paths[1], args.dir_op) else {
        return Some(AdmissionReason::UnsupportedOperand);
    };
    if operation.uploads() {
        return settings.admit_upload();
    }
    None
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Operand<'a> {
    Local,
    Remote(uri::S3PrefixUri<'a>),
    Unsupported,
}

fn classify(value: &OsStr, allow_prefix: bool) -> Operand<'_> {
    let bytes = value.as_encoded_bytes();
    if value == "-" || bytes.starts_with(b"arn:") || bytes.contains(&0) {
        return Operand::Unsupported;
    }
    if !bytes.starts_with(b"s3:") {
        return Operand::Local;
    }
    let parsed = if allow_prefix {
        uri::parse_s3_prefix_uri(bytes).map_err(uri::S3UriParseError::from)
    } else {
        uri::parse_s3_uri(bytes).map(|v| uri::S3PrefixUri {
            bucket: v.bucket,
            prefix: v.key,
        })
    };
    match parsed {
        Ok(remote) if uri::supports_native_bucket(remote.bucket) => Operand::Remote(remote),
        Err(uri::S3UriParseError::NotS3Uri) => Operand::Local,
        _ => Operand::Unsupported,
    }
}

fn copy_operation<'a>(
    source: &'a OsStr,
    destination: &'a OsStr,
    recursive: bool,
) -> Option<Operation<'a>> {
    let single = |remote: uri::S3PrefixUri<'a>| uri::S3Uri {
        bucket: remote.bucket,
        key: remote.prefix,
    };
    match (classify(source, recursive), classify(destination, true)) {
        (Operand::Remote(remote), Operand::Local) if crate::local_path::supports(destination) => {
            Some(if recursive {
                Operation::RecursiveDownload(remote)
            } else {
                Operation::SingleDownload(single(remote))
            })
        }
        (Operand::Local, Operand::Remote(remote)) if crate::local_path::supports(source) => {
            Some(if recursive {
                Operation::RecursiveUpload(remote)
            } else {
                Operation::SingleUpload(single(remote))
            })
        }
        _ => None,
    }
}

/// The transfers the native path runs, each with its parsed S3 operand.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Operation<'a> {
    SingleDownload(uri::S3Uri<'a>),
    SingleUpload(uri::S3Uri<'a>),
    RecursiveDownload(uri::S3PrefixUri<'a>),
    RecursiveUpload(uri::S3PrefixUri<'a>),
}
impl Operation<'_> {
    /// Whether the transfer uploads local files.
    pub fn uploads(self) -> bool {
        matches!(self, Self::SingleUpload(_) | Self::RecursiveUpload(_))
    }
    /// The direction the transfer moves objects in.
    pub fn direction(self) -> crate::transfer::Direction {
        if self.uploads() {
            crate::transfer::Direction::Upload
        } else {
            crate::transfer::Direction::Download
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CopyPlan<'a> {
    pub source: &'a OsStr,
    pub destination: &'a OsStr,
    pub operation: Operation<'a>,
    pub quiet: bool,
    pub dryrun: bool,
    pub printer: Option<crate::results::PrinterConfig>,
    pub ignore_glacier_warnings: bool,
    pub force_glacier_transfer: bool,
    pub no_overwrite: bool,
    pub page_size: u32,
    /// The object settings each request of the transfer sends.
    pub settings: ObjectSettings<'a>,
    /// Whether an upload guesses each object's type from its source's name
    /// when `--content-type` gives none; `--no-guess-mime-type` turns it off.
    pub guess_mime_type: bool,
    pub selected_region: Option<&'a str>,
    pub selected_profile: Option<&'a str>,
    pub selected_endpoint_url: Option<&'a str>,
    /// Each `--include` and `--exclude` pattern, in command-line order.
    pub filters: &'a [(FilterKind, String)],
    /// Whether the local side's links are followed, which
    /// `--no-follow-symlinks` turns off.
    pub follow_symlinks: bool,
}

/// The plan of an invocation the router admitted.
///
/// # Panics
/// Panics when `admit` would have handed the invocation to Python.
#[expect(
    clippy::expect_used,
    reason = "router admission bounds the page size, settings, and operand shapes"
)]
pub fn make_copy_plan(args: &Args) -> CopyPlan<'_> {
    let operation = copy_operation(&args.paths[0], &args.paths[1], args.dir_op)
        .expect("admitted copy operands");
    CopyPlan {
        source: &args.paths[0],
        destination: &args.paths[1],
        operation,
        quiet: args.quiet,
        dryrun: args.dryrun,
        printer: args.printer(),
        ignore_glacier_warnings: args.ignore_glacier_warnings,
        force_glacier_transfer: args.force_glacier_transfer,
        no_overwrite: args.no_overwrite,
        page_size: args
            .page_size
            .map_or(0, |n| u32::try_from(n).expect("admitted page size")),
        settings: ObjectSettings::from_args(args).expect("admitted settings"),
        guess_mime_type: args.guess_mime_type,
        selected_region: None,
        selected_profile: None,
        selected_endpoint_url: None,
        filters: &args.filters,
        follow_symlinks: args.follow_symlinks,
    }
}
pub fn make_copy_plan_with_globals<'a>(
    args: &'a Args,
    globals: &'a cli_core::command::Globals,
) -> CopyPlan<'a> {
    let mut plan = make_copy_plan(args);
    plan.selected_region = globals.region.as_deref();
    plan.selected_profile = globals.profile.as_deref();
    plan.selected_endpoint_url = globals.endpoint_url.as_deref();
    plan
}

/// Upstream's `create_filter` for `plan`, run in the working directory `cwd`.
///
/// The plan's operands are as the command line spells them. A local root is
/// the operand's abspath, or for one file its directory's; an S3 root is the
/// bucket and the key as spelled, or for one object the key's parent prefix.
/// The file generator names a walked file after the abspath of its root and
/// a separator, an object after its bucket and a slash, and one file by its
/// path.
pub fn make_copy_filter(plan: &CopyPlan<'_>, cwd: &Path) -> Filter {
    make_filter(plan, cwd, Side::Source)
}

/// The filter a sync's destination entries pass, rooted as the source's is.
///
/// Upstream filters both of a sync's file generators with the same patterns
/// and roots (`CommandArchitecture.run`), each naming its entries as it lists
/// them: an object by its bucket and key, a file by its absolute path. A
/// sync is recursive, so a single object has no destination to filter.
pub fn make_sync_destination_filter(plan: &CopyPlan<'_>, cwd: &Path) -> Filter {
    make_filter(plan, cwd, Side::Destination)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Side {
    Source,
    Destination,
}

fn make_filter(plan: &CopyPlan<'_>, cwd: &Path, side: Side) -> Filter {
    if plan.filters.is_empty() {
        return Filter::default();
    }
    let local_root = |operand: &OsStr, recursive: bool| {
        let operand = Path::new(operand);
        let directory = if recursive {
            operand
        } else {
            crate::local_path::dir_name(operand)
        };
        crate::local_path::absolute_path(cwd, directory)
            .into_os_string()
            .into_encoded_bytes()
    };
    let bucket_prefix = |bucket: &str| [bucket.as_bytes(), b"/"].concat();
    let directory_prefix = |root: &[u8]| [root, std::path::MAIN_SEPARATOR_STR.as_bytes()].concat();
    let (source_root, destination_root, prefix) = match (plan.operation, side) {
        (Operation::RecursiveUpload(remote), side) => {
            let root = local_root(plan.source, true);
            let prefix = match side {
                Side::Source => directory_prefix(&root),
                Side::Destination => bucket_prefix(remote.bucket),
            };
            (
                root,
                s3_prefix_filter_root(remote.bucket, remote.prefix),
                prefix,
            )
        }
        (Operation::RecursiveDownload(remote), side) => {
            let root = local_root(plan.destination, true);
            let prefix = match side {
                Side::Source => bucket_prefix(remote.bucket),
                Side::Destination => directory_prefix(&root),
            };
            (
                s3_prefix_filter_root(remote.bucket, remote.prefix),
                root,
                prefix,
            )
        }
        (Operation::SingleUpload(_) | Operation::SingleDownload(_), Side::Destination) => {
            return Filter::default();
        }
        (Operation::SingleUpload(remote), Side::Source) => (
            local_root(plan.source, false),
            s3_object_filter_root(remote.bucket, remote.key),
            Vec::new(),
        ),
        (Operation::SingleDownload(remote), Side::Source) => (
            s3_object_filter_root(remote.bucket, remote.key),
            local_root(plan.destination, false),
            bucket_prefix(remote.bucket),
        ),
    };
    let roots = Roots {
        source: &source_root,
        destination: &destination_root,
    };
    Filter::new(plan.filters, roots, &prefix)
}

/// The root `create_filter` joins each pattern to for a recursive S3 operand.
///
/// That is the operand's `bucket` and `prefix` as spelled (`_get_s3_root`).
pub(crate) fn s3_prefix_filter_root(bucket: &str, prefix: &[u8]) -> Vec<u8> {
    [bucket.as_bytes(), b"/", prefix].concat()
}

/// The root `create_filter` joins each pattern to for a single S3 object.
///
/// That is the directory of `key` in `bucket`, or `key` itself when it ends
/// with `/` (`_get_s3_root`).
pub(crate) fn s3_object_filter_root(bucket: &str, key: &[u8]) -> Vec<u8> {
    let directory = if key.ends_with(b"/") {
        key
    } else {
        &key[..key.iter().rposition(|&byte| byte == b'/').unwrap_or(0)]
    };
    s3_prefix_filter_root(bucket, directory)
}

/// AWS CLI v2 uses the source basename as the object key when the single
/// upload destination is a bucket root or a prefix ending in '/'. The name
/// after a trailing separator, which a directory source carries, is empty.
pub fn resolve_single_upload_key(destination_key: &[u8], source: &std::path::Path) -> Vec<u8> {
    if !destination_key.is_empty() && !destination_key.ends_with(b"/") {
        return destination_key.into();
    }
    let trailing_separator = source
        .as_os_str()
        .as_encoded_bytes()
        .last()
        .is_some_and(|&byte| std::path::is_separator(char::from(byte)));
    let basename = if trailing_separator {
        &[]
    } else {
        source.file_name().unwrap_or_default().as_encoded_bytes()
    };
    [destination_key, basename].concat()
}

#[cfg(test)]
mod tests;
