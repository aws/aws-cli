//! CPython-independent readers for the embedded ZIPPY003 payload.

pub mod catalog;
pub mod container;
#[cfg(test)]
#[path = "../tests/allocation_limits/counting.rs"]
mod counting;
pub mod decompress;
#[cfg(feature = "embedded")]
mod embedded;
pub mod format;
pub mod inspect;
pub mod runtime;
pub mod swiss_group;
#[cfg(feature = "embedded")]
pub use embedded::embedded;

pub use container::{
    ARTIFACT_BYTES_MAX, Error as ContainerError, LocateFileError, Located, Location,
    PAYLOAD_SECTION_DESCRIPTION, PAYLOAD_SECTION_NAME, locate, locate_file,
};

pub use format::{Entry, Error, MAGIC, PAYLOAD_BYTES_MAX, Payload, Summary, parse, payload_extent};

pub use runtime::{View, ViewEntry};

pub use decompress::{Error as DecompressError, ZSTD_BUFFER_LEN, decode_zstd};

pub use catalog::{immediate_child, is_model_file, prefix_upper_bound};
