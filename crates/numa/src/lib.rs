//! Linux NUMA discovery, node-wide CPU affinity, and bound memory policy.
//!
//! Pure parsing and discovery use injected node files. Native entry points return
//! [`NumaError::Unsupported`] on other operating systems; [`cpu_count`] counts
//! the CPUs there as the standard library does.
mod native;
mod parse;

#[doc(inline)]
pub use native::{apply_current_thread, bind_memory_to_node, cpu_count, current_cpu, discover};
#[doc(inline)]
pub use parse::{parse_allowed_node_mask, parse_cpu_list, parse_node_mask};

/// Linux nodemask storage covers 1024 nodes; `set_mempolicy` and `mbind` take
/// maxnode 1025.
pub const MAX_NODES: usize = 1024;
/// The fixed affinity storage covers 1024 Linux logical CPU identifiers.
pub const MAX_CPUS: usize = 1024;
const WORD_BITS: usize = usize::BITS as usize;
const WORDS: usize = MAX_CPUS / WORD_BITS;
const NODE_CPU_LIST_LIMIT: usize = 512;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CpuSet {
    words: [usize; WORDS],
}
impl Default for CpuSet {
    fn default() -> Self {
        Self { words: [0; WORDS] }
    }
}
impl CpuSet {
    /// Adds a CPU identifier within the fixed affinity mask.
    ///
    /// # Errors
    /// Returns `CpuOutsideAffinityMask` for identifiers at or beyond 1024.
    pub fn set(&mut self, cpu: usize) -> Result<(), NumaError> {
        if cpu >= MAX_CPUS {
            return Err(NumaError::CpuOutsideAffinityMask);
        }
        self.words[cpu / WORD_BITS] |= 1 << (cpu % WORD_BITS);
        Ok(())
    }
    pub fn contains(&self, cpu: usize) -> bool {
        cpu < MAX_CPUS && self.words[cpu / WORD_BITS] & (1 << (cpu % WORD_BITS)) != 0
    }
    pub fn is_empty(&self) -> bool {
        self.words.iter().all(|&word| word == 0)
    }
    pub fn count(&self) -> usize {
        self.words
            .iter()
            .map(|word| word.count_ones() as usize)
            .sum()
    }
    pub fn intersect_with(&mut self, allowed: &Self) {
        for (word, allowed) in self.words.iter_mut().zip(allowed.words) {
            *word &= allowed;
        }
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NodeInfo {
    pub id: u32,
    pub cpu_set: CpuSet,
    pub cpu_count: usize,
    cpu_list: String,
}
impl NodeInfo {
    /// A node holding `cpu_set`, spelled `cpu_list` as its sysfs file does.
    pub fn new(id: u32, cpu_set: CpuSet, cpu_list: &str) -> Self {
        Self {
            id,
            cpu_set,
            cpu_count: cpu_set.count(),
            cpu_list: cpu_list.chars().take(NODE_CPU_LIST_LIMIT).collect(),
        }
    }
    pub fn cpu_list(&self) -> &str {
        &self.cpu_list
    }
}
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Topology {
    pub nodes: Vec<NodeInfo>,
}
impl Topology {
    pub fn first_node(&self) -> Option<&NodeInfo> {
        self.nodes.first()
    }
    pub fn node_for_id(&self, id: u32) -> Option<&NodeInfo> {
        self.nodes.iter().find(|node| node.id == id)
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CurrentCpu {
    pub cpu: u32,
    pub node: u32,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct NodeMask {
    words: [usize; MAX_NODES / WORD_BITS],
}
impl Default for NodeMask {
    fn default() -> Self {
        Self {
            words: [0; MAX_NODES / WORD_BITS],
        }
    }
}
impl NodeMask {
    pub fn contains(&self, node: usize) -> bool {
        node < MAX_NODES && self.words[node / WORD_BITS] & (1 << (node % WORD_BITS)) != 0
    }
    fn set(&mut self, node: usize) {
        if node < MAX_NODES {
            self.words[node / WORD_BITS] |= 1 << (node % WORD_BITS);
        }
    }
}
/// The operating-system call a [`NumaError::Os`] failure came from. Each
/// names its errors its own way.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum NumaCall {
    /// Opening a `/proc` or sysfs topology file.
    Open,
    /// Reading an opened topology file.
    Read,
    /// `sched_getaffinity` for the calling thread.
    GetAffinity,
    /// `sched_setaffinity` for the calling thread.
    SetAffinity,
}
impl std::fmt::Display for NumaCall {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.write_str(match self {
            Self::Open => "opening a NUMA topology file",
            Self::Read => "reading a NUMA topology file",
            Self::GetAffinity => "sched_getaffinity",
            Self::SetAffinity => "sched_setaffinity",
        })
    }
}
/// NUMA failures retain filesystem and operating-system causes.
#[derive(Debug)]
#[non_exhaustive]
pub enum NumaError {
    Unsupported,
    InvalidList,
    AllowedListUnavailable,
    CpuOutsideAffinityMask,
    NoUsableNode,
    NodeOutsideMask,
    ThreadPlacementMismatch,
    AddressOverflow,
    /// A topology file is longer than its read limit.
    StreamTooLong,
    /// The page a placement probe binds could not be mapped.
    MappingFailed,
    /// A topology-file or affinity call failed.
    Os {
        call: NumaCall,
        error: std::io::Error,
    },
    /// A NUMA policy syscall (`getcpu`, `set_mempolicy`, `mbind`) or another
    /// operating-system operation failed.
    Io(std::io::Error),
}
impl std::fmt::Display for NumaError {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Unsupported => out.write_str("NUMA is unsupported"),
            Self::InvalidList => out.write_str("invalid NUMA list"),
            Self::AllowedListUnavailable => out.write_str("allowed NUMA node list is unavailable"),
            Self::CpuOutsideAffinityMask => out.write_str("CPU is outside the affinity mask"),
            Self::NoUsableNode => out.write_str("no usable NUMA node"),
            Self::NodeOutsideMask => out.write_str("NUMA node is outside the node mask"),
            Self::ThreadPlacementMismatch => out.write_str("NUMA thread placement mismatch"),
            Self::AddressOverflow => out.write_str("memory address overflow"),
            Self::StreamTooLong => out.write_str("NUMA topology file exceeds its read limit"),
            Self::MappingFailed => out.write_str("NUMA probe page mapping failed"),
            Self::Os { call, error } => write!(out, "{call} failed: {error}"),
            Self::Io(error) => write!(out, "NUMA system operation failed: {error}"),
        }
    }
}
impl std::error::Error for NumaError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Os { error, .. } | Self::Io(error) => Some(error),
            _ => None,
        }
    }
}
impl From<std::io::Error> for NumaError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error)
    }
}
/// Supplies one node's sysfs cpulist; failures skip only that node.
pub trait NodeReader {
    fn read(&self, node: u32) -> Result<String, NumaError>;
}
/// Discovers allowed nodes with the full intersection of each node's CPU mask.
///
/// # Errors
/// Returns malformed cpulists or no usable node. Only the native
/// [`discover`] is host-gated; injected node files parse on every host.
pub fn discover_from_node_reader(
    allowed_nodes: &NodeMask,
    allowed_cpus: &CpuSet,
    reader: &impl NodeReader,
) -> Result<Topology, NumaError> {
    let mut topology = Topology::default();
    for id in 0..MAX_NODES {
        if !allowed_nodes.contains(id) {
            continue;
        }
        let Ok(contents) = reader.read(id as u32) else {
            continue;
        };
        let cpu_list = contents.trim_matches([' ', '\t', '\r', '\n']);
        let mut cpu_set = parse_cpu_list(cpu_list)?;
        cpu_set.intersect_with(allowed_cpus);
        if cpu_set.is_empty() {
            continue;
        }
        topology
            .nodes
            .push(NodeInfo::new(id as u32, cpu_set, cpu_list));
    }
    if topology.nodes.is_empty() {
        return Err(NumaError::NoUsableNode);
    }
    Ok(topology)
}

#[cfg(test)]
mod tests;
