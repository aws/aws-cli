use super::diagnostics::{self, LocalityInactiveReason as Inactive};
use super::platform::Platform;
use super::{
    MAX_NODES, NumaConfig, NumaMode, NumaPoolMode, Requirement, STRIPE_BYTES, WriteError,
    WriterMode,
};
use crate::cp::backstop::SetupError;
use std::sync::Arc;

/// Writer placement and the source-pool nodes one download's client is built with.
#[derive(Clone, Debug, Default)]
pub struct DownloadLocality {
    /// Writer placement; inactive for a `crt` download.
    pub locality: LocalityContext,
    /// The NUMA source pool's nodes; None keeps the CRT's default pool.
    pub source_pool: Option<Vec<u32>>,
}

#[derive(Clone, Debug, Default)]
pub struct LocalityContext {
    pub nodes: Vec<numa::NodeInfo>,
}
impl LocalityContext {
    pub fn resolve(config: &NumaConfig, platform: Arc<dyn Platform>) -> Result<Self, WriteError> {
        if config.mode == NumaMode::Disabled {
            diagnostics::log_locality_inactive(Inactive::Disabled);
            return Ok(Self::default());
        }
        match Self::resolve_enabled(config, platform) {
            Err(error) if config.requirement == Requirement::Preferred => {
                let name = SetupError::write(&error);
                diagnostics::log_locality_inactive(Inactive::Unavailable(name.name()));
                Ok(Self::default())
            }
            result => result,
        }
    }
    fn resolve_enabled(
        config: &NumaConfig,
        platform: Arc<dyn Platform>,
    ) -> Result<Self, WriteError> {
        let topology = platform.discover_numa().map_err(|error| {
            if matches!(error, numa::NumaError::Unsupported) {
                diagnostics::log_locality_inactive(Inactive::Os(super::platform::NAME));
            }
            numa_error(error)
        })?;
        if config.requirement == Requirement::Preferred && topology.nodes.len() < 2 {
            diagnostics::log_locality_inactive(Inactive::SingleNode);
            return Ok(Self::default());
        }
        let nodes = selected_nodes(config, &topology)?;
        if config.requirement == Requirement::Preferred {
            for node in nodes.clone() {
                let ops = Arc::clone(&platform);
                let result = cli_core::thread::builder()
                    .name("download-numa-probe".into())
                    .spawn(move || ops.probe_numa(&node))?
                    .join();
                assert!(result.is_ok(), "NUMA probe panicked");
                if let Ok(result) = result {
                    result.map_err(numa_error)?;
                }
            }
        }
        diagnostics::log_locality_active(config.mode, &nodes);
        Ok(Self { nodes })
    }
    /// Resolves placement and the source pool for one download. A `crt`
    /// download is written by the CRT, so there are no writer threads to
    /// place: placement is never resolved, and the pool follows only
    /// `pool_mode`.
    pub fn resolve_download(
        config: &NumaConfig,
        writer: WriterMode,
        pool_mode: Option<NumaPoolMode>,
        platform: Arc<dyn Platform>,
    ) -> Result<DownloadLocality, WriteError> {
        let locality = if writer == WriterMode::Crt {
            Self::default()
        } else {
            Self::resolve(config, Arc::clone(&platform))?
        };
        let source_pool = locality.resolve_source_pool(pool_mode, platform.as_ref())?;
        Ok(DownloadLocality {
            locality,
            source_pool,
        })
    }
    /// The source pool's nodes under `mode`, resolved apart from writer
    /// placement so neither setting changes the other. Unset follows
    /// placement; `Disabled` keeps the CRT's default pool; `Enabled` takes
    /// placement's nodes, or the node the same-node automatic selection picks
    /// when placement is inactive, and proves every node can bind memory
    /// before any client exists.
    pub fn resolve_source_pool(
        &self,
        mode: Option<NumaPoolMode>,
        platform: &dyn Platform,
    ) -> Result<Option<Vec<u32>>, WriteError> {
        let placed = || self.nodes.iter().map(|node| node.id).collect::<Vec<_>>();
        match mode {
            None => return Ok((!self.nodes.is_empty()).then(placed)),
            Some(NumaPoolMode::Disabled) => return Ok(None),
            Some(NumaPoolMode::Enabled) => {}
        }
        let nodes = if self.nodes.is_empty() {
            let topology = platform.discover_numa().map_err(numa_error)?;
            vec![same_node_auto(&topology)?.id]
        } else {
            placed()
        };
        for node in &nodes {
            platform.probe_numa_memory(*node).map_err(numa_error)?;
        }
        Ok(Some(nodes))
    }
    pub fn shard_count(&self) -> usize {
        self.nodes.len().max(1)
    }
    pub fn shard_for_offset(&self, offset: u64) -> usize {
        (offset / STRIPE_BYTES % self.shard_count() as u64) as usize
    }
    pub fn shard_index_for_node(&self, node: u32) -> Option<usize> {
        self.nodes.iter().position(|candidate| candidate.id == node)
    }
    pub fn shard_for_body(&self, offset: u64, node: Option<u32>) -> usize {
        node.and_then(|id| self.shard_index_for_node(id))
            .unwrap_or_else(|| self.shard_for_offset(offset))
    }
    pub(crate) fn apply_to_shard(
        &self,
        shard: usize,
        platform: &dyn Platform,
    ) -> Result<(), WriteError> {
        if self.nodes.is_empty() {
            return Ok(());
        }
        let node = self
            .nodes
            .get(shard)
            .ok_or_else(|| WriteError::Numa("NumaInvalidShard".into()))?;
        platform.apply_numa(node).map_err(numa_error)
    }
}
fn selected_nodes(
    config: &NumaConfig,
    topology: &numa::Topology,
) -> Result<Vec<numa::NodeInfo>, WriteError> {
    debug_assert!(config.nodes.len() <= MAX_NODES);
    debug_assert!(
        (1..config.nodes.len()).all(|index| !config.nodes[..index].contains(&config.nodes[index]))
    );
    match config.mode {
        NumaMode::SameNode => Ok(vec![select_same_node(config, topology)?]),
        NumaMode::Disabled | NumaMode::AllNodes => {
            debug_assert_eq!(config.mode, NumaMode::AllNodes);
            select_all_nodes(config, topology)
        }
    }
}
fn select_same_node(
    config: &NumaConfig,
    topology: &numa::Topology,
) -> Result<numa::NodeInfo, WriteError> {
    match config.nodes.as_slice() {
        [] => same_node_auto(topology).cloned(),
        [id] => requested_node(topology, *id),
        _ => Err(WriteError::Numa("NumaInvalidNodeSelection".into())),
    }
}
fn select_all_nodes(
    config: &NumaConfig,
    topology: &numa::Topology,
) -> Result<Vec<numa::NodeInfo>, WriteError> {
    let nodes: Vec<_> = if config.nodes.is_empty() {
        if topology.nodes.len() > MAX_NODES {
            diagnostics::log_locality_truncated(MAX_NODES, topology.nodes.len());
        }
        topology.nodes.iter().take(MAX_NODES).cloned().collect()
    } else {
        config
            .nodes
            .iter()
            .map(|id| requested_node(topology, *id))
            .collect::<Result<_, _>>()?
    };
    if nodes.is_empty() {
        return Err(WriteError::Numa("NumaNoUsableNode".into()));
    }
    Ok(nodes)
}
fn requested_node(topology: &numa::Topology, id: u32) -> Result<numa::NodeInfo, WriteError> {
    topology
        .node_for_id(id)
        .cloned()
        .ok_or_else(|| WriteError::Numa("NumaRequestedNodeUnavailable".into()))
}
fn same_node_auto(topology: &numa::Topology) -> Result<&numa::NodeInfo, WriteError> {
    numa::current_cpu()
        .ok()
        .and_then(|cpu| topology.node_for_id(cpu.node))
        .or_else(|| topology.first_node())
        .ok_or_else(|| WriteError::Numa("NumaNoUsableNode".into()))
}
#[cfg(test)]
mod tests;

fn numa_error(error: numa::NumaError) -> WriteError {
    use numa::NumaError;
    let name = match error {
        NumaError::Unsupported => "NumaUnsupported",
        NumaError::InvalidList => "NumaInvalidList",
        NumaError::AllowedListUnavailable => "NumaAllowedListUnavailable",
        NumaError::CpuOutsideAffinityMask => "NumaCpuOutsideAffinityMask",
        NumaError::NoUsableNode => "NumaNoUsableNode",
        NumaError::NodeOutsideMask => "NumaInvalidNodeSelection",
        NumaError::ThreadPlacementMismatch => "NumaThreadPlacementMismatch",
        NumaError::AddressOverflow => crate::local_error::OVERFLOW,
        NumaError::StreamTooLong => crate::local_error::STREAM_TOO_LONG,
        NumaError::MappingFailed => "MappingFailed",
        NumaError::Os { call, error } => os_error_name(call, &error),
        NumaError::Io(_) => "NumaSystemCallFailed",
        _ => "NumaSystemCallFailed",
    };
    WriteError::Numa(name.into())
}
#[cfg_attr(
    not(unix),
    expect(unused_variables, reason = "only unix names errnos per call")
)]
fn os_error_name(call: numa::NumaCall, error: &std::io::Error) -> &'static str {
    #[cfg(unix)]
    if let Some(errno) = error.raw_os_error() {
        return errno_name(call, errno);
    }
    crate::cp::io_error_name(error)
}
#[cfg(unix)]
fn errno_name(call: numa::NumaCall, errno: i32) -> &'static str {
    use numa::NumaCall::{GetAffinity, Open, Read};
    match (call, errno) {
        (Open, libc::EINVAL | libc::EILSEQ) => crate::local_error::BAD_PATH_NAME,
        (Open, libc::EACCES) => crate::local_error::ACCESS_DENIED,
        (Open, libc::EFBIG | libc::EOVERFLOW) => crate::local_error::FILE_TOO_BIG,
        (Open, libc::EISDIR) => crate::local_error::IS_DIR,
        (Open, libc::ELOOP) => crate::local_error::SYM_LINK_LOOP,
        (Open, libc::EMFILE) => crate::local_error::PROCESS_FD_QUOTA_EXCEEDED,
        (Open, libc::ENAMETOOLONG) => crate::local_error::NAME_TOO_LONG,
        (Open, libc::ENFILE) => crate::local_error::SYSTEM_FD_QUOTA_EXCEEDED,
        (Open, libc::ENODEV | libc::ENXIO) => crate::local_error::NO_DEVICE,
        (Open, libc::ENOENT | libc::ESRCH) => crate::local_error::FILE_NOT_FOUND,
        (Open, libc::ENOMEM) => crate::local_error::SYSTEM_RESOURCES,
        (Open, libc::ENOSPC) => crate::local_error::NO_SPACE_LEFT,
        (Open, libc::ENOTDIR) => crate::local_error::NOT_DIR,
        (Open, libc::EPERM) => crate::local_error::PERMISSION_DENIED,
        (Open, libc::EEXIST) => crate::local_error::PATH_ALREADY_EXISTS,
        (Open, libc::EBUSY) => crate::local_error::DEVICE_BUSY,
        (Open, libc::EOPNOTSUPP) => crate::local_error::FILE_LOCKS_UNSUPPORTED,
        (Open, libc::EAGAIN) => crate::local_error::WOULD_BLOCK,
        (Open, libc::ETXTBSY) => crate::local_error::FILE_BUSY,
        (Open, libc::EROFS) => crate::local_error::READ_ONLY_FILE_SYSTEM,
        (Read, libc::EBADF) => crate::local_error::NOT_OPEN_FOR_READING,
        (Read, libc::EAGAIN) => crate::local_error::WOULD_BLOCK,
        (Read, libc::EIO) => crate::local_error::INPUT_OUTPUT,
        (Read, libc::EISDIR) => crate::local_error::IS_DIR,
        (Read, libc::ENOBUFS | libc::ENOMEM) => crate::local_error::SYSTEM_RESOURCES,
        (Read, libc::ENOTCONN) => crate::local_error::SOCKET_UNCONNECTED,
        (Read, libc::ECONNRESET) => crate::local_error::CONNECTION_RESET_BY_PEER,
        (GetAffinity, libc::EPERM) => crate::local_error::PERMISSION_DENIED,
        _ => crate::local_error::UNEXPECTED,
    }
}
