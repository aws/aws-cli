//! Shared S3 transfer budgets for the scheduler, submission queue, and finish
//! pool. These defaults bound command-wide concurrency; profile overrides are
//! resolved by `config`.
/// Scheduler transfer window when the profile does not set a concurrency
/// limit. The measured 12,000 objects/s listing rate at 28 ms per object
/// needs about 336 slots; 512 leaves headroom and bounds live object state to
/// 512 transfers.
pub const IN_FLIGHT_MAX_DEFAULT: u32 = 512;
/// Pending recursive download submissions buffered between listing and
/// scheduling. Eight default windows decouple listing bursts from submission.
/// Storage is 4096 pending entries plus owned keys; at 1 KiB per key, queued
/// key payloads occupy 4 MiB, excluding allocator overhead and the producer's
/// pending key. This is a tuning budget, not an optimum.
pub const SUBMIT_QUEUE_CAPACITY_DEFAULT: usize = 8 * IN_FLIGHT_MAX_DEFAULT as usize;
/// Destination entries a sync upload's listing holds ahead of its comparator:
/// one page at ListObjectsV2's default MaxKeys, so the next page is fetched
/// while the walk pairs files with this one. A full queue pauses the listing,
/// which bounds the keys held to about a page whatever the bucket holds.
pub const SYNC_DESTINATION_QUEUE_CAPACITY: usize = 1000;
/// Workers that finish recursive downloads off the CRT callback threads.
/// Four kept the measured median finish-queue high-water mark at five
/// entries; increasing the pool was unnecessary. Their 16-MiB stacks
/// (`cli_core::thread::THREAD_STACK_BYTES`) reserve 64 MiB of address space,
/// separate from the scheduler's completion state and object state.
pub const FINISH_WORKERS_DEFAULT: usize = 4;
/// Maximum workers overlapping native output preparation before GET
/// submission. Four bound default stack reservations to 64 MiB and
/// preparation parallelism to a small CPU budget; queued and running jobs
/// share the scheduler window.
pub const PREPARE_WORKERS_MAX: usize = 4;

const _: () = assert!(IN_FLIGHT_MAX_DEFAULT > 0);
const _: () = assert!(SUBMIT_QUEUE_CAPACITY_DEFAULT > 0);
const _: () = assert!(SUBMIT_QUEUE_CAPACITY_DEFAULT >= IN_FLIGHT_MAX_DEFAULT as usize);
const _: () = assert!(FINISH_WORKERS_DEFAULT > 0);
const _: () = assert!(SYNC_DESTINATION_QUEUE_CAPACITY > 0);
const _: () = assert!(FINISH_WORKERS_DEFAULT <= IN_FLIGHT_MAX_DEFAULT as usize);
const _: () = assert!(PREPARE_WORKERS_MAX > 0);
