//! NUMA source buffers with one FIFO across all locality shards.
mod allocation;
mod ffi;
mod heap;
mod runtime;

#[doc(inline)]
pub use allocation::{AllocationKind, AllocationOps, Mapping, MappingError};
#[cfg(any(feature = "testing", test))]
#[doc(inline)]
pub use runtime::Diagnostics;
#[doc(inline)]
pub use runtime::factory;
#[doc(inline)]
pub use runtime::{FactoryConfig, ticket_node};
/// Maximum source-pool NUMA shards, independent of the kernel nodemask size.
pub const MAX_NODES: usize = 16;
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Config {
    pub nodes: Vec<u32>,
    pub budget_bytes: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ConfigError;
impl std::fmt::Display for ConfigError {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.write_str("source pool requires between one and sixteen NUMA nodes")
    }
}
impl std::error::Error for ConfigError {}
impl Config {
    /// Copies node identifiers in order and checks the shard count.
    ///
    /// # Errors
    /// Returns [`ConfigError`] when the node count is outside 1 through 16.
    pub fn new(nodes: Vec<u32>, budget_bytes: usize) -> Result<Self, ConfigError> {
        if nodes.is_empty() || nodes.len() > MAX_NODES {
            return Err(ConfigError);
        }
        Ok(Self {
            nodes,
            budget_bytes,
        })
    }
}

#[cfg(any(test, feature = "testing"))]
pub use runtime::model;
