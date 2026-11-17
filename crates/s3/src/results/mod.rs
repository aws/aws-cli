//! Ordered transfer results, coalesced live progress, and command-wide presentation.
mod printer;
mod processor;
mod recorder;
use crate::transfer::Direction;
pub use printer::{Flags, Mode, Printer, PrinterConfig, WriteErrors};
pub use processor::{Drain, DrainThread, Processor, Publisher, Running, spawn_drain};
pub use recorder::{CommandResult, Recorder};

pub type Key = u64;
/// The transfer a result line names, upstream's `transfer_type`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TransferType {
    Download,
    Upload,
    Delete,
    /// A transfer that deletes its source once it succeeded.
    Move,
}
impl From<Direction> for TransferType {
    fn from(direction: Direction) -> Self {
        match direction {
            Direction::Download => Self::Download,
            Direction::Upload => Self::Upload,
            Direction::Delete => Self::Delete,
        }
    }
}
impl std::fmt::Display for TransferType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Download => "download",
            Self::Upload => "upload",
            Self::Delete => "delete",
            Self::Move => "move",
        })
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Line {
    pub transfer_type: TransferType,
    pub source: Vec<u8>,
    pub destination: Option<Vec<u8>>,
}
impl Line {
    pub fn locations(&self) -> Vec<u8> {
        self.destination.as_ref().map_or_else(
            || self.source.clone(),
            |destination| [self.source.as_slice(), b" to ", destination.as_slice()].concat(),
        )
    }
}
#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    Queued {
        key: Key,
        size: Option<u64>,
    },
    Progress {
        key: Option<Key>,
        bytes: u64,
        total_size: Option<u64>,
        timestamp_ns: u64,
    },
    Success {
        key: Key,
        line: Line,
    },
    Failure {
        key: Key,
        line: Line,
        exception: Vec<u8>,
        transferred: Option<u64>,
        text: Option<Vec<u8>>,
    },
    Warning(Vec<u8>),
    Diagnostic(Vec<u8>),
    Skip {
        key: Key,
    },
    Fatal(Vec<u8>),
    CtrlC,
    DryRun(Line),
    FinalTotal(u64),
}
impl Event {
    fn redraws_progress(&self) -> bool {
        matches!(
            self,
            Self::Success { .. } | Self::Failure { .. } | Self::Skip { .. } | Self::Warning(_)
        )
    }
    fn ends_command(&self) -> bool {
        matches!(self, Self::Fatal(_) | Self::CtrlC)
    }
}
#[cfg(test)]
mod tests;
