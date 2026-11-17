//! Typed S3 profile settings with explicit writer requirements, and the
//! client sizing they feed.
use crate::constants::IN_FLIGHT_MAX_DEFAULT;
use crate::download::WriterMode;
use crate::download::{
    COPY_FAST_MODES_AVAILABLE, CopyMode, NumaConfig, NumaMode, NumaPoolMode, PrefaultMode,
    Requirement, WriterConfig,
};
use awscli_config::{Nested, ParsedFiles};
use cli_core::{EnvMap, aws_profile};
use std::fmt;

mod parse;
mod sizing;
pub use parse::{InvalidValue, parse_node_selection};
pub use sizing::{
    ClientSizing, RECURSIVE_DOWNLOAD_CONNECTION_SLACK, Shape, SizingInputs, buffer_part_size,
    resolve_client_sizing,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Operation {
    SingleDownload,
    SingleUpload,
    RecursiveDownload,
    RecursiveUpload,
    Other,
}
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Settings {
    pub in_flight_max: Option<u32>,
    pub io_workers: Option<usize>,
    pub download_writer: Option<WriterMode>,
    pub download_writer_copy: Option<CopyMode>,
    pub download_writer_prefault: Option<PrefaultMode>,
    pub download_writer_numa: Option<NumaMode>,
    /// Empty vectors select automatic topology; None preserves absence.
    pub download_writer_node: Option<Vec<u32>>,
    /// Explicit NUMA source-pool setting; None keeps the pool tied to writer placement.
    pub download_numa_pool: Option<NumaPoolMode>,
}
#[derive(Debug, Clone, PartialEq)]
pub struct DownloadTuning {
    pub writer: WriterConfig,
    /// Recursive downloads keep `recv_filepath` for implicit small-object
    /// defaults; any explicit writer setting requires the native writer. An
    /// explicit `crt` writer overrides it: every object then takes
    /// `recv_filepath`.
    pub custom_writer_required: bool,
    /// The explicit NUMA source-pool setting; None installs the pool exactly
    /// when writer placement is active, on the placement's nodes.
    pub numa_pool: Option<NumaPoolMode>,
}
impl DownloadTuning {
    pub fn with_direct_io(mut self, direct_io: bool) -> Self {
        if direct_io && self.writer.requirement == Requirement::Preferred {
            self.writer.mode = WriterMode::Direct;
        }
        self
    }
}
impl Settings {
    pub fn resolve_in_flight_max(&self) -> u32 {
        self.in_flight_max.unwrap_or(IN_FLIGHT_MAX_DEFAULT)
    }
    pub fn resolve_download(&self) -> DownloadTuning {
        let required = self.download_writer.is_some() || self.download_writer_copy.is_some();
        DownloadTuning {
            writer: WriterConfig {
                mode: self.download_writer.unwrap_or(WriterMode::Mmap),
                requirement: requirement(required),
                copy_mode: self.download_writer_copy.unwrap_or_else(default_copy),
                prefault: self
                    .download_writer_prefault
                    .unwrap_or(PrefaultMode::Enabled),
                workers: self.io_workers,
                numa: NumaConfig {
                    mode: self.download_writer_numa.unwrap_or(NumaMode::SameNode),
                    nodes: self.download_writer_node.clone().unwrap_or_default(),
                    requirement: requirement(self.download_writer_numa.is_some()),
                },
            },
            custom_writer_required: self.requires_custom_writer(),
            numa_pool: self.download_numa_pool,
        }
    }
    /// The pool key alone selects no writer, so it never requires the native one.
    fn requires_custom_writer(&self) -> bool {
        self.io_workers.is_some()
            || self.download_writer.is_some()
            || self.download_writer_copy.is_some()
            || self.download_writer_prefault.is_some()
            || self.download_writer_numa.is_some()
            || self.download_writer_node.is_some()
    }
}
fn requirement(required: bool) -> Requirement {
    if required {
        Requirement::Required
    } else {
        Requirement::Preferred
    }
}
fn default_copy() -> CopyMode {
    if COPY_FAST_MODES_AVAILABLE {
        CopyMode::Nt
    } else {
        CopyMode::Memcpy
    }
}

/// Why an `s3` block fails for a download, one variant per failure the
/// diagnostic distinguishes. A value outside its key's grammar is an
/// `Invalid*` variant; the rest are relationships between keys or builds.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ParseError {
    InvalidMaxInFlight,
    InvalidIoWorkers,
    InvalidDownloadWriter,
    InvalidDownloadWriterCopy,
    UnsupportedDownloadWriterCopy,
    InvalidDownloadWriterPrefault,
    InvalidDownloadWriterNuma,
    InvalidDownloadWriterNode,
    InvalidDownloadNumaPool,
    UnsupportedDownloadNumaPool,
    DownloadWriterCopyRequiresMmap,
    DownloadWriterPrefaultRequiresMmap,
    DownloadWriterNodeRequiresNuma,
    SameNodeRequiresSingleNode,
    IoWorkersRequiresNativeWriter,
    DownloadWriterNumaRequiresNativeWriter,
}
impl ParseError {
    /// The `s3` key the diagnostic names.
    pub fn key(self) -> &'static str {
        match self {
            Self::InvalidMaxInFlight => "max_in_flight",
            Self::InvalidIoWorkers | Self::IoWorkersRequiresNativeWriter => "io_workers",
            Self::InvalidDownloadWriter => "download_writer",
            Self::InvalidDownloadWriterCopy
            | Self::UnsupportedDownloadWriterCopy
            | Self::DownloadWriterCopyRequiresMmap => "download_writer_copy",
            Self::InvalidDownloadWriterPrefault | Self::DownloadWriterPrefaultRequiresMmap => {
                "download_writer_prefault"
            }
            Self::InvalidDownloadWriterNuma | Self::DownloadWriterNumaRequiresNativeWriter => {
                "download_writer_numa"
            }
            Self::InvalidDownloadWriterNode
            | Self::DownloadWriterNodeRequiresNuma
            | Self::SameNodeRequiresSingleNode => "download_writer_node",
            Self::InvalidDownloadNumaPool | Self::UnsupportedDownloadNumaPool => {
                "download_numa_pool"
            }
        }
    }
    /// What the diagnostic says is wrong: the accepted values for an invalid
    /// value, else the constraint the settings break.
    pub fn message(self) -> &'static str {
        match self {
            Self::InvalidMaxInFlight | Self::InvalidIoWorkers => "expected a positive integer",
            Self::InvalidDownloadWriter => "expected 'pwrite', 'mmap', 'direct', or 'crt'",
            Self::InvalidDownloadWriterCopy => "expected 'memcpy', 'nt', or 'rep'",
            Self::InvalidDownloadWriterPrefault => "expected 'enabled' or 'disabled'",
            Self::InvalidDownloadWriterNuma => "expected 'disabled', 'same-node', or 'all-nodes'",
            Self::InvalidDownloadWriterNode => {
                "expected 'auto' or a node list like '0', '0,2', or '0-3'"
            }
            Self::InvalidDownloadNumaPool => "expected 'enabled' or 'disabled'",
            Self::UnsupportedDownloadWriterCopy => {
                "'nt' and 'rep' require an optimized x86_64 build"
            }
            Self::DownloadWriterCopyRequiresMmap | Self::DownloadWriterPrefaultRequiresMmap => {
                "requires s3.download_writer = mmap"
            }
            Self::DownloadWriterNodeRequiresNuma => {
                "requires s3.download_writer_numa = same-node or all-nodes"
            }
            Self::SameNodeRequiresSingleNode => "same-node mode accepts only one node id",
            Self::UnsupportedDownloadNumaPool => "'enabled' requires Linux NUMA support",
            Self::IoWorkersRequiresNativeWriter | Self::DownloadWriterNumaRequiresNativeWriter => {
                "requires s3.download_writer = mmap, pwrite, or direct"
            }
        }
    }
}
impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "invalid s3.{}: {}", self.key(), self.message())
    }
}
impl std::error::Error for ParseError {}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoadError {
    pub message: String,
}
impl fmt::Display for LoadError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}
impl std::error::Error for LoadError {}

/// The transfer settings for `operation` from the selected profile's `s3`
/// block. A missing, unreadable, or non-regular config file, such as
/// `/dev/null` or a directory, reads as empty, as botocore reads it. A file
/// that fails to parse never reaches this point: the router sends that
/// invocation to Python.
pub fn load(
    env: &impl EnvMap,
    files: &ParsedFiles,
    operation: Operation,
    profile: Option<&str>,
) -> Result<Settings, LoadError> {
    let profile = aws_profile::select_or_default(env, profile);
    let nested = files
        .profiles
        .as_ref()
        .and_then(|v| v.get(profile.to_str()?))
        .and_then(|v| v.get("s3"))
        .and_then(|v| v.value.as_nested());
    let Some(nested) = nested else {
        return Ok(Settings::default());
    };
    parse_settings(nested, operation).map_err(|e| LoadError {
        message: format!(
            "error: invalid s3.{} in AWS config profile \"{}\": {}\n",
            e.key(),
            profile.display(),
            e.message()
        ),
    })
}
/// Typed settings from the block, validated for `operation`. Unknown keys are
/// ignored so a newer setting does not fail an older binary. An operation that
/// downloads nothing reads only `max_in_flight` and ignores the download keys,
/// even malformed ones, as upstream ignores every key it doesn't know.
pub fn parse_settings(values: &Nested, operation: Operation) -> Result<Settings, ParseError> {
    match operation {
        Operation::SingleDownload | Operation::RecursiveDownload => {
            let settings = parse::download_settings(values)?;
            validate_download(&settings)?;
            Ok(settings)
        }
        Operation::SingleUpload | Operation::RecursiveUpload | Operation::Other => {
            parse::in_flight_settings(values)
        }
    }
}
fn validate_download(settings: &Settings) -> Result<(), ParseError> {
    validate_download_writer(settings)?;
    validate_numa(settings)?;
    validate_numa_pool(settings)
}
fn validate_download_writer(settings: &Settings) -> Result<(), ParseError> {
    let copy = settings.download_writer_copy;
    if copy.is_some_and(|v| v != CopyMode::Memcpy) && !COPY_FAST_MODES_AVAILABLE {
        return Err(ParseError::UnsupportedDownloadWriterCopy);
    }
    if copy.is_some()
        && settings
            .download_writer
            .is_some_and(|v| v != WriterMode::Mmap)
    {
        return Err(ParseError::DownloadWriterCopyRequiresMmap);
    }
    validate_download_writer_prefault(settings)?;
    validate_native_writer(settings)
}
fn validate_download_writer_prefault(settings: &Settings) -> Result<(), ParseError> {
    if settings.download_writer_prefault.is_some()
        && settings
            .download_writer
            .is_some_and(|v| v != WriterMode::Mmap)
    {
        return Err(ParseError::DownloadWriterPrefaultRequiresMmap);
    }
    Ok(())
}
/// The CRT writes the file itself, so it has no workers to size or place: an
/// explicit worker count or positive placement would be a requested behavior
/// silently ignored.
fn validate_native_writer(settings: &Settings) -> Result<(), ParseError> {
    if settings.download_writer != Some(WriterMode::Crt) {
        return Ok(());
    }
    if settings.io_workers.is_some() {
        return Err(ParseError::IoWorkersRequiresNativeWriter);
    }
    if settings.download_writer_numa.unwrap_or(NumaMode::Disabled) != NumaMode::Disabled {
        return Err(ParseError::DownloadWriterNumaRequiresNativeWriter);
    }
    Ok(())
}
fn validate_numa(settings: &Settings) -> Result<(), ParseError> {
    let mode = settings.download_writer_numa.unwrap_or(NumaMode::Disabled);
    if settings.download_writer_node.is_some() && mode == NumaMode::Disabled {
        return Err(ParseError::DownloadWriterNodeRequiresNuma);
    }
    if mode == NumaMode::SameNode
        && settings
            .download_writer_node
            .as_ref()
            .is_some_and(|v| v.len() > 1)
    {
        return Err(ParseError::SameNodeRequiresSingleNode);
    }
    Ok(())
}
/// Placing the pool needs NUMA discovery, which only Linux has; a disabled
/// pool is the default pool every platform has.
fn validate_numa_pool(settings: &Settings) -> Result<(), ParseError> {
    if settings.download_numa_pool == Some(NumaPoolMode::Enabled) && !cfg!(target_os = "linux") {
        return Err(ParseError::UnsupportedDownloadNumaPool);
    }
    Ok(())
}

#[cfg(test)]
mod tests;
