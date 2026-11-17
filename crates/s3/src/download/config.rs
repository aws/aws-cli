use super::stream_copy::CopyMode;

pub const CHUNK_BYTES: u64 = 8 * 1024 * 1024;
/// Bytes assigned to one locality shard before offsets rotate to the next.
pub const STRIPE_BYTES: u64 = 64 * 1024 * 1024;
pub const EVICTION_BYTES: usize = 512 * 1024 * 1024;
/// Fault one nominal chunk per operation, allowing eight windows in each
/// locality stripe.
pub const PREFAULT_WINDOW: usize = 8 * 1024 * 1024;
/// Permit 32 prefault windows ahead of copying before waiting for completion.
pub const PREFAULT_LOOKAHEAD: usize = 256 * 1024 * 1024;
/// The prefault workers each locality shard runs, for one mapping of its own
/// or for the command's pool.
pub const PREFAULT_THREADS_PER_SHARD: usize = 2;
/// Maximum NUMA nodes representable by the CRT source-pool configuration;
/// each selected node owns one locality shard.
pub const MAX_NODES: usize = crt::source_pool::MAX_NODES;

const _: () = assert!(PREFAULT_LOOKAHEAD.is_multiple_of(PREFAULT_WINDOW));
const _: () = assert!(STRIPE_BYTES.is_multiple_of(PREFAULT_WINDOW as u64));

/// Who writes a downloaded object: one of the native outputs, or `Crt`, where
/// the CRT writes the file itself through `recv_filepath` and no native output
/// exists.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum WriterMode {
    Pwrite,
    #[default]
    Mmap,
    Direct,
    Crt,
}
/// Whether the NUMA source-buffer pool serves the download client: `Enabled`
/// requires it, `Disabled` keeps the CRT's default pool.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NumaPoolMode {
    Enabled,
    Disabled,
}
/// Whether an unavailable requested optimization may fall back.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Requirement {
    Preferred,
    Required,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum PrefaultMode {
    #[default]
    Enabled,
    Disabled,
}
/// NUMA placement policy for writer threads and output memory.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NumaMode {
    Disabled,
    SameNode,
    AllNodes,
}
/// NUMA policy requested for a download writer. The default places nothing;
/// a command's settings resolve same-node placement, preferred, unless the
/// profile chooses otherwise.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NumaConfig {
    pub mode: NumaMode,
    /// Empty selects nodes automatically; explicit lists retain their order.
    pub nodes: Vec<u32>,
    /// Whether placement failures permit fallback.
    pub requirement: Requirement,
}
impl Default for NumaConfig {
    fn default() -> Self {
        Self {
            mode: NumaMode::Disabled,
            nodes: Vec::new(),
            requirement: Requirement::Required,
        }
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WriterConfig {
    pub mode: WriterMode,
    pub requirement: Requirement,
    pub copy_mode: CopyMode,
    pub prefault: PrefaultMode,
    pub workers: Option<usize>,
    pub numa: NumaConfig,
}
impl Default for WriterConfig {
    fn default() -> Self {
        Self {
            mode: WriterMode::Mmap,
            requirement: Requirement::Preferred,
            copy_mode: CopyMode::Memcpy,
            prefault: PrefaultMode::Enabled,
            workers: None,
            numa: NumaConfig::default(),
        }
    }
}
