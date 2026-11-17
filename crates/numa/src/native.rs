#[cfg(target_os = "linux")]
mod linux;
#[cfg(not(target_os = "linux"))]
use crate::{CurrentCpu, NodeInfo, NumaError, Topology};
#[cfg(target_os = "linux")]
pub use linux::{apply_current_thread, bind_memory_to_node, cpu_count, current_cpu, discover};
#[cfg(not(target_os = "linux"))]
pub fn discover() -> Result<Topology, NumaError> {
    Err(NumaError::Unsupported)
}
/// The CPUs the process may use: off Linux, `std::thread::available_parallelism`,
/// and one when it is unknown.
#[cfg(not(target_os = "linux"))]
pub fn cpu_count() -> usize {
    std::thread::available_parallelism().map_or(1, usize::from)
}
#[cfg(not(target_os = "linux"))]
pub fn current_cpu() -> Result<CurrentCpu, NumaError> {
    Err(NumaError::Unsupported)
}
#[cfg(not(target_os = "linux"))]
pub fn apply_current_thread(_: &NodeInfo) -> Result<(), NumaError> {
    Err(NumaError::Unsupported)
}
#[cfg(not(target_os = "linux"))]
pub fn bind_memory_to_node(_: &mut [u8], _: u32) -> Result<(), NumaError> {
    Err(NumaError::Unsupported)
}
