//! Checked `s3 sync` arguments, their operand admission, and its strategies.
//!
//! Upstream's `sync` is a recursive copy of each source file or object the
//! destination lacks or holds in another version (`SyncCommand`,
//! `CommandArchitecture.run`). The router binds [`Args`] from a completed parse
//! and asks [`admit`] whether the native path takes them: one local directory
//! and one supported S3 prefix, in either order, with the options its recursive
//! copy takes and every strategy's. The options no native copy takes, such
//! as `--no-follow-symlinks`, are Python's. The transfer pairs each source
//! with the destination's entry of the same name ([`comparator`]) and
//! decides each name by the [`Strategies`] its options choose.
//!
//! ```
//! use s3::sync::{Args, admit};
//! use std::ffi::OsString;
//!
//! // `s3 sync site s3://bucket/www/`
//! let args = Args {
//!     paths: [OsString::from("site"), OsString::from("s3://bucket/www/")],
//!     ..Args::default()
//! };
//! assert_eq!(admit(&args), None);
//! // A sync between two buckets is Python's, as such a copy is.
//! let args = Args {
//!     paths: [OsString::from("s3://a/www/"), OsString::from("s3://b/www/")],
//!     ..Args::default()
//! };
//! assert!(admit(&args).is_some());
//! ```
use crate::filter::FilterKind;
use crate::{AdmissionReason, cp_args};
use awscli_argparse::bind::{BindError, BindField, Shape, StringMap};
use awscli_argparse::{Namespace, ParseResult, native_args, tables};
use std::ffi::OsString;

pub mod comparator;
mod native;
pub use native::run;

native_args! {
    pub struct Args for tables::SYNC_ARGUMENTS {
        pub paths: [OsString; 2],
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
        pub size_only: bool,
        pub exact_timestamps: bool,
        pub delete: bool,
    }
}
/// The destinations [`Args`] binds; any other destination is Python's.
pub const DESTINATIONS: &[&str] = Args::FIELD_NAMES;
/// A sync given no option: every argument at the default its parse stores.
impl Default for Args {
    fn default() -> Self {
        Self {
            paths: Default::default(),
            dryrun: false,
            quiet: false,
            no_overwrite: false,
            page_size: None,
            only_show_errors: false,
            progress: true,
            progress_frequency: None,
            progress_multiline: false,
            ignore_glacier_warnings: false,
            force_glacier_transfer: false,
            filters: Vec::new(),
            follow_symlinks: true,
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
            case_conflict: OnCaseConflict::Ignore,
            size_only: false,
            exact_timestamps: false,
            delete: false,
        }
    }
}
impl Args {
    /// Binds the arguments a completed parse stored.
    ///
    /// # Errors
    /// Returns [`BindError`] when a destination's value lacks the shape its
    /// field binds.
    pub fn from_result(result: &ParseResult) -> Result<Self, BindError> {
        Self::bind(&result.values)
    }
    /// The recursive copy whose sources the sync compares.
    ///
    /// Upstream sets `dir_op` for every sync (`CommandParameters.__init__`) and
    /// hands the transfer every option but `--no-overwrite`, which only its
    /// strategy reads (`CommandArchitecture._get_s3_handler_params`).
    pub fn to_copy_args(&self) -> cp_args::Args {
        cp_args::Args {
            paths: self.paths.clone(),
            dir_op: true,
            dryrun: self.dryrun,
            quiet: self.quiet,
            no_overwrite: false,
            page_size: self.page_size,
            only_show_errors: self.only_show_errors,
            progress: self.progress,
            progress_frequency: self.progress_frequency,
            progress_multiline: self.progress_multiline,
            ignore_glacier_warnings: self.ignore_glacier_warnings,
            force_glacier_transfer: self.force_glacier_transfer,
            filters: self.filters.clone(),
            follow_symlinks: self.follow_symlinks,
            content_type: self.content_type.clone(),
            cache_control: self.cache_control.clone(),
            content_disposition: self.content_disposition.clone(),
            content_encoding: self.content_encoding.clone(),
            content_language: self.content_language.clone(),
            expires: self.expires.clone(),
            website_redirect: self.website_redirect.clone(),
            metadata: self.metadata.clone(),
            acl: self.acl.clone(),
            storage_class: self.storage_class.clone(),
            sse: self.sse.clone(),
            sse_kms_key_id: self.sse_kms_key_id.clone(),
            sse_c: self.sse_c.clone(),
            sse_c_key: self.sse_c_key.clone(),
            request_payer: self.request_payer.clone(),
            checksum_mode: self.checksum_mode.clone(),
            checksum_algorithm: self.checksum_algorithm.clone(),
            guess_mime_type: self.guess_mime_type,
            grants: self.grants.clone(),
            case_conflict: self.case_conflict,
        }
    }
    /// The strategies the options choose, as upstream chooses them
    /// (`CommandArchitecture.choose_sync_strategies`).
    ///
    /// Each strategy's option replaces the default of its case, and the
    /// strategies upstream registers later win (`register_sync_strategies`):
    /// `--no-overwrite` over `--exact-timestamps` over `--size-only`.
    /// `--case-conflict` other than `ignore` replaces the strategy for a name
    /// only the source holds, which only a download consults.
    pub fn strategies(&self) -> Strategies {
        let both = if self.no_overwrite {
            BothSides::Never
        } else if self.exact_timestamps {
            BothSides::ExactTimestamps
        } else if self.size_only {
            BothSides::SizeOnly
        } else {
            BothSides::SizeAndLastModified
        };
        let source_only = self
            .case_conflict
            .handling()
            .map_or(SourceOnly::Transfer, SourceOnly::CaseConflict);
        let destination_only = if self.delete {
            DestinationOnly::Delete
        } else {
            DestinationOnly::Keep
        };
        Strategies {
            both,
            source_only,
            destination_only,
        }
    }
}

/// What a sync adds to its recursive copy.
#[derive(Debug, Clone, Default, PartialEq, Eq, Hash)]
pub struct Plan {
    /// How each name is decided.
    pub strategies: Strategies,
    /// The `--include` and `--exclude` patterns each destination entry must
    /// pass before it is paired, as upstream filters both of its file
    /// generators (`CommandArchitecture.run`).
    pub destination_filter: crate::filter::Filter,
}

/// How a sync decides each name, one strategy per case upstream registers.
///
/// Upstream's defaults (`CommandArchitecture.choose_sync_strategies`) are what
/// an invocation with no option gets: a name both sides hold is transferred
/// when the sizes differ or the local side is newer, one only the source holds
/// is transferred, and one only the destination holds is kept.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub struct Strategies {
    pub both: BothSides,
    pub source_only: SourceOnly,
    pub destination_only: DestinationOnly,
}
/// What decides a name both sides hold, upstream's `file_at_src_and_dest`.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub enum BothSides {
    /// Transfer when the sizes differ or the local side is newer
    /// (`SizeAndLastModifiedSync`).
    #[default]
    SizeAndLastModified,
    /// `--size-only`: transfer when the sizes differ
    /// (`SizeOnlySync`).
    SizeOnly,
    /// `--exact-timestamps`: a download also transfers when the times differ
    /// at all; an upload compares as the default does
    /// (`ExactTimestampsSync`).
    ExactTimestamps,
    /// `--no-overwrite`: never replace the destination's entry
    /// (`NoOverwriteSync`).
    Never,
    /// `cp` or `mv` under `--case-conflict`: always replace the
    /// destination's entry (`AlwaysSync`).
    Always,
}
/// What decides a name only the source holds, upstream's `file_not_at_dest`.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub enum SourceOnly {
    /// Transfer it (`MissingFileSync`).
    #[default]
    Transfer,
    /// `--case-conflict`: a download first checks for a file whose name
    /// differs only by case (`CaseConflictSync`). An upload transfers it, as
    /// upstream handles case conflicts only for downloads
    /// (`CommandArchitecture._should_handle_case_conflicts`).
    CaseConflict(CaseConflict),
}
/// What a download does with a name that differs only by case from a file
/// it holds or is downloading.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CaseConflict {
    /// Warn and leave the object.
    Skip,
    /// Warn and download it anyway.
    Warn,
    /// End the command with the conflict as its fatal error.
    Error,
}
/// The `--case-conflict` choice, upstream's `on_case_conflict`.
///
/// `sync`, `cp`, and `mv` take it, and each checks for case conflicts only
/// in a recursive download
/// (`CommandArchitecture._should_handle_case_conflicts`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub enum OnCaseConflict {
    /// Download without checking, the option's default.
    #[default]
    Ignore,
    /// Check, and leave an object that conflicts.
    Skip,
    /// Check, and download an object that conflicts after a warning.
    Warn,
    /// Check, and end the command on the first conflict.
    Error,
}
impl OnCaseConflict {
    /// What a download does on a case conflict; None when it does not check.
    pub fn handling(self) -> Option<CaseConflict> {
        match self {
            Self::Ignore => None,
            Self::Skip => Some(CaseConflict::Skip),
            Self::Warn => Some(CaseConflict::Warn),
            Self::Error => Some(CaseConflict::Error),
        }
    }
}
/// The choice argparse stored. Its choices are the variants', so any other
/// value fails the binding.
impl BindField for OnCaseConflict {
    const SHAPE: Shape = Shape::StringDefault;
    fn bind(ns: &Namespace, dest: &str) -> Result<Self, BindError> {
        match ns.string(dest) {
            Some("ignore") => Ok(Self::Ignore),
            Some("skip") => Ok(Self::Skip),
            Some("warn") => Ok(Self::Warn),
            Some("error") => Ok(Self::Error),
            _ => Err(BindError {
                destination: dest.into(),
                shape: Self::SHAPE,
            }),
        }
    }
}
/// What becomes of a name only the destination holds, upstream's
/// `file_not_at_src`.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash)]
pub enum DestinationOnly {
    /// Leave it alone (`NeverSync`).
    #[default]
    Keep,
    /// `--delete`: remove it (`DeleteSync`).
    Delete,
}

/// Why a complete sync invocation stays with Python; None admits it.
///
/// A sync admits what its recursive copy does: one local operand and one
/// supported S3 URI. A sync between two S3 paths, streams, aliases, ARNs and
/// directory buckets, which upstream refuses for a sync
/// (`CommandParameters.add_paths`), are Python's.
pub fn admit(args: &Args) -> Option<AdmissionReason> {
    cp_args::admit(&args.to_copy_args())
}

#[cfg(test)]
mod tests;
