use crate::{
    CpuSet, CurrentCpu, MAX_CPUS, MAX_NODES, NODE_CPU_LIST_LIMIT, NodeInfo, NodeMask, NodeReader,
    NumaCall, NumaError, Topology, discover_from_node_reader, parse_allowed_node_mask,
};
use std::io::Read;
const MPOL_BIND: libc::c_int = 2;
const MPOL_MF_MOVE: libc::c_int = 1 << 1;
const MAXNODE: usize = MAX_NODES + 1;
#[derive(Debug)]
struct NativeNodeReader;
impl NodeReader for NativeNodeReader {
    fn read(&self, node: u32) -> Result<String, NumaError> {
        let contents = read_virtual(
            &format!("/sys/devices/system/node/node{node}/cpulist"),
            NODE_CPU_LIST_LIMIT,
        )?;
        String::from_utf8(contents).map_err(|_| NumaError::InvalidList)
    }
}
fn read_virtual(path: &str, limit: usize) -> Result<Vec<u8>, NumaError> {
    let mut contents = Vec::new();
    std::fs::File::open(path)
        .map_err(|error| NumaError::Os {
            call: NumaCall::Open,
            error,
        })?
        .take(limit as u64 + 1)
        .read_to_end(&mut contents)
        .map_err(|error| NumaError::Os {
            call: NumaCall::Read,
            error,
        })?;
    if contents.len() > limit {
        return Err(NumaError::StreamTooLong);
    }
    Ok(contents)
}
/// Discovers memory nodes permitted by the process memory and CPU masks.
///
/// # Errors
/// Propagates filesystem, kernel, and malformed topology errors.
pub fn discover() -> Result<Topology, NumaError> {
    let allowed = parse_allowed_node_mask(&read_virtual("/proc/self/status", 64 * 1024)?)?;
    let affinity = current_affinity()?;
    discover_from_node_reader(&allowed, &affinity, &NativeNodeReader)
}
/// The CPUs the calling thread may run on: the size of its `sched_getaffinity`
/// mask, and one when the mask cannot be read. Unlike
/// `std::thread::available_parallelism`, a cgroup CPU quota does not lower it.
pub fn cpu_count() -> usize {
    current_affinity().map_or(1, |set| set.count())
}
fn current_affinity() -> Result<CpuSet, NumaError> {
    // SAFETY: zero initialization is valid for cpu_set_t's integer storage.
    let mut raw: libc::cpu_set_t = unsafe { std::mem::zeroed() };
    read_affinity(&mut raw, std::mem::size_of::<libc::cpu_set_t>())?;
    let mut set = CpuSet::default();
    for cpu in 0..MAX_CPUS {
        // SAFETY: cpu is bounded by CPU_SETSIZE and raw is initialized.
        if unsafe { libc::CPU_ISSET(cpu, &raw) } {
            set.set(cpu)?;
        }
    }
    Ok(set)
}
/// Fills the first `size` bytes of `mask` with the calling thread's CPU
/// affinity. The kernel returns EINVAL when `size` holds fewer bits than its
/// CPU ids; that fails as a node CPU beyond `CpuSet` does, so the placement
/// requirement decides whether to fall back.
fn read_affinity(mask: &mut libc::cpu_set_t, size: usize) -> Result<(), NumaError> {
    assert!(size <= std::mem::size_of_val(mask));
    // SAFETY: mask is writable storage of at least `size` bytes, and the
    // wrapper clears the bytes past the kernel's own mask.
    if unsafe { libc::sched_getaffinity(0, size, mask) } == 0 {
        return Ok(());
    }
    let error = std::io::Error::last_os_error();
    if error.raw_os_error() == Some(libc::EINVAL) {
        return Err(NumaError::CpuOutsideAffinityMask);
    }
    Err(NumaError::Os {
        call: NumaCall::GetAffinity,
        error,
    })
}
/// Queries the calling thread's current CPU and NUMA node.
///
/// # Errors
/// Propagates kernel query failures.
pub fn current_cpu() -> Result<CurrentCpu, NumaError> {
    let mut current = CurrentCpu { cpu: 0, node: 0 };
    // SAFETY: the kernel writes one u32 to each valid output pointer.
    let result = unsafe {
        libc::syscall(
            libc::SYS_getcpu,
            &mut current.cpu,
            &mut current.node,
            std::ptr::null_mut::<libc::c_void>(),
        )
    };
    if result != 0 {
        return Err(std::io::Error::last_os_error().into());
    }
    Ok(current)
}
fn node_mask(node: u32) -> Result<NodeMask, NumaError> {
    if node as usize >= MAX_NODES {
        return Err(NumaError::NodeOutsideMask);
    }
    let mut mask = NodeMask::default();
    mask.set(node as usize);
    Ok(mask)
}
/// Applies node-wide affinity and memory binding, then verifies placement.
///
/// # Errors
/// Propagates affinity, memory policy, and placement failures.
pub fn apply_current_thread(node: &NodeInfo) -> Result<(), NumaError> {
    let mask = node_mask(node.id)?;
    // SAFETY: zero initialization is valid for cpu_set_t's integer storage.
    let mut cpus: libc::cpu_set_t = unsafe { std::mem::zeroed() };
    for cpu in 0..MAX_CPUS {
        if node.cpu_set.contains(cpu) {
            // SAFETY: cpu is bounded by CPU_SETSIZE and cpus is initialized.
            unsafe {
                libc::CPU_SET(cpu, &mut cpus);
            }
        }
    }
    // SAFETY: cpus is fully initialized; pid zero changes only this thread.
    if unsafe { libc::sched_setaffinity(0, std::mem::size_of_val(&cpus), &cpus) } != 0 {
        return Err(NumaError::Os {
            call: NumaCall::SetAffinity,
            error: std::io::Error::last_os_error(),
        });
    }
    // SAFETY: the nodemask has 1024 valid bits; maxnode follows the Linux ABI's trailing-bit
    // convention.
    if unsafe {
        libc::syscall(
            libc::SYS_set_mempolicy,
            MPOL_BIND,
            mask.words.as_ptr(),
            MAXNODE,
        )
    } != 0
    {
        return Err(std::io::Error::last_os_error().into());
    }
    let current = current_cpu()?;
    if current.node != node.id || !node.cpu_set.contains(current.cpu as usize) {
        return Err(NumaError::ThreadPlacementMismatch);
    }
    Ok(())
}
/// Binds all pages overlapping an exclusively borrowed region to one node.
///
/// # Errors
/// Reports invalid nodes, address overflow, and kernel binding failures.
pub fn bind_memory_to_node(memory: &mut [u8], node: u32) -> Result<(), NumaError> {
    if memory.is_empty() {
        return Ok(());
    }
    let mask = node_mask(node)?;
    // SAFETY: sysconf accepts this constant and requires no pointers.
    let page = usize::try_from(unsafe { libc::sysconf(libc::_SC_PAGESIZE) })
        .map_err(|_| NumaError::AddressOverflow)?;
    if !page.is_power_of_two() {
        return Err(NumaError::AddressOverflow);
    }
    let address = memory.as_mut_ptr() as usize;
    let end = address
        .checked_add(memory.len())
        .and_then(|end| end.checked_add(page - 1))
        .ok_or(NumaError::AddressOverflow)?
        & !(page - 1);
    let start = address & !(page - 1);
    // SAFETY: start..end is the page range overlapping the live memory slice; mbind changes policy
    // without dereferencing Rust references. The nodemask has the ABI-required 1024 bits.
    let result = unsafe {
        libc::syscall(
            libc::SYS_mbind,
            start,
            end - start,
            MPOL_BIND,
            mask.words.as_ptr(),
            MAXNODE,
            MPOL_MF_MOVE,
        )
    };
    if result != 0 {
        return Err(std::io::Error::last_os_error().into());
    }
    Ok(())
}
#[cfg(test)]
mod tests;
