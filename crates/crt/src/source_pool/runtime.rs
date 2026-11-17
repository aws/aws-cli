use super::allocation::{AllocationKind, AllocationOps, Mapping};
use super::ffi::{self, FutureOps};
use super::heap::{HeapSlice, UninitValue, allocate_value, release_value};
use super::{Config, MAX_NODES};
use std::cell::UnsafeCell;
use std::ffi::{c_int, c_void};
use std::hint::spin_loop;
use std::mem::ManuallyDrop;
use std::ptr;
use std::sync::Arc;
#[cfg(any(test, feature = "testing"))]
use std::sync::atomic::AtomicU64;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

const SHARD_BUFFERS_MIN: usize = 2;
/// aws-c-s3's default memory limit for a 64-bit client at 200 Gbps or more,
/// its largest tier (s3_client.c `aws_s3_client_new`).
const CRT_MEMORY_LIMIT_BYTES_DEFAULT_MAX: u64 = 24 * 1024 * 1024 * 1024;
/// aws-c-s3's part size before it sizes parts for an object
/// (`g_default_part_size_fallback`, s3_util.c).
const CRT_PART_SIZE_BYTES_DEFAULT: u64 = 8 * 1024 * 1024;
const SOURCE_POOL_BUFFERS_MAX: usize = 4096;
const SOURCE_POOL_BUDGET_BYTES_DEFAULT: usize = 2 * 1024 * 1024 * 1024;
const SPECIAL_SIZES_MAX: usize = 32;
/// aws-c-s3's ceiling on a client's connections (`g_max_num_connections`).
const CRT_CONNECTIONS_MAX: usize = 10_000;
/// aws-c-s3's tracked requests per connection (`s_max_requests_multiplier`).
const CRT_REQUESTS_PER_CONNECTION_MAX: usize = 4;
const PENDING_RESERVES_MAX: usize = CRT_CONNECTIONS_MAX * CRT_REQUESTS_PER_CONNECTION_MAX;
const RESERVE_PASSES_MAX: usize = SOURCE_POOL_BUFFERS_MAX + 1;
const PENDING_DRIVE_STEPS_HANDOFF: usize = 2 * PENDING_RESERVES_MAX + SOURCE_POOL_BUFFERS_MAX + 1;
const PENDING_DRIVE_STEPS_MAX: usize = 2 * PENDING_DRIVE_STEPS_HANDOFF;

const _: () = {
    assert!(MAX_NODES * SHARD_BUFFERS_MIN <= SOURCE_POOL_BUFFERS_MAX);
    assert!(
        SOURCE_POOL_BUFFERS_MAX as u64 * CRT_PART_SIZE_BYTES_DEFAULT
            >= CRT_MEMORY_LIMIT_BYTES_DEFAULT_MAX
    );
    assert!(SOURCE_POOL_BUDGET_BYTES_DEFAULT as u64 <= CRT_MEMORY_LIMIT_BYTES_DEFAULT_MAX);
    assert!(SPECIAL_SIZES_MAX <= SOURCE_POOL_BUFFERS_MAX);
    assert!(PENDING_RESERVES_MAX >= SOURCE_POOL_BUFFERS_MAX);
    assert!(std::mem::size_of::<PendingReserve>() <= 64);
    assert!(RESERVE_PASSES_MAX > SOURCE_POOL_BUFFERS_MAX);
    assert!(PENDING_DRIVE_STEPS_HANDOFF > PENDING_RESERVES_MAX + SOURCE_POOL_BUFFERS_MAX);
    assert!(PENDING_DRIVE_STEPS_MAX >= 2 * PENDING_DRIVE_STEPS_HANDOFF);
};

#[cfg(any(test, feature = "testing"))]
#[derive(Debug, Default)]
pub struct Diagnostics {
    pub budget_bytes: AtomicUsize,
    pub reservations: AtomicU64,
    pub releases: AtomicU64,
    pub queued_grants: AtomicU64,
    pub forced_grants: AtomicU64,
    pub allocations: AtomicU64,
    pub trims: AtomicU64,
    pub peak_allocated_bytes: AtomicUsize,
    pub peak_reserved_bytes: AtomicUsize,
    pub peak_forced_bytes: AtomicUsize,
    node_mappings: Vec<AtomicU64>,
    node_bytes: Vec<AtomicU64>,
}

#[cfg(any(test, feature = "testing"))]
impl Diagnostics {
    fn for_nodes(count: usize) -> Self {
        Self {
            node_mappings: (0..count).map(|_| AtomicU64::new(0)).collect(),
            node_bytes: (0..count).map(|_| AtomicU64::new(0)).collect(),
            ..Self::default()
        }
    }

    pub fn node_snapshot(&self) -> Vec<(u64, u64)> {
        self.node_mappings
            .iter()
            .zip(&self.node_bytes)
            .map(|(mappings, bytes)| {
                (
                    mappings.load(Ordering::Relaxed),
                    bytes.load(Ordering::Relaxed),
                )
            })
            .collect()
    }

    fn record_mapping(&self, node_index: usize, size: usize) {
        self.allocations.fetch_add(1, Ordering::Relaxed);
        self.node_mappings[node_index].fetch_add(1, Ordering::Relaxed);
        self.node_bytes[node_index].fetch_add(size as u64, Ordering::Relaxed);
    }
}

#[derive(Debug)]
pub struct FactoryConfig {
    nodes: Vec<u32>,
    budget_bytes: usize,
    #[cfg(any(test, feature = "testing"))]
    diagnostics: Arc<Diagnostics>,
}

impl FactoryConfig {
    pub fn new(config: Config) -> Self {
        let Config {
            nodes,
            budget_bytes,
        } = config;
        Self {
            #[cfg(any(test, feature = "testing"))]
            diagnostics: Arc::new(Diagnostics::for_nodes(nodes.len())),
            nodes,
            budget_bytes,
        }
    }

    #[cfg(any(test, feature = "testing"))]
    pub fn diagnostics(&self) -> Arc<Diagnostics> {
        Arc::clone(&self.diagnostics)
    }
}

struct SpinLock<T> {
    held: AtomicBool,
    value: UnsafeCell<T>,
}

// SAFETY: access to value is only issued through the exclusive guard after a
// successful acquire swap. T never escapes the guard by reference.
unsafe impl<T: Send> Sync for SpinLock<T> {}

impl<T> SpinLock<T> {
    fn new(value: T) -> Self {
        Self {
            held: AtomicBool::new(false),
            value: UnsafeCell::new(value),
        }
    }

    fn lock(&self) -> SpinGuard<'_, T> {
        while self
            .held
            .compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed)
            .is_err()
        {
            spin_loop();
        }
        SpinGuard { lock: self }
    }
}

struct SpinGuard<'a, T> {
    lock: &'a SpinLock<T>,
}

impl<T> std::ops::Deref for SpinGuard<'_, T> {
    type Target = T;

    fn deref(&self) -> &T {
        unsafe {
            // SAFETY: this guard is created only after acquiring the lock and
            // remains the sole guard until Drop publishes the unlock.
            &*self.lock.value.get()
        }
    }
}

impl<T> std::ops::DerefMut for SpinGuard<'_, T> {
    fn deref_mut(&mut self) -> &mut T {
        unsafe {
            // SAFETY: the acquired guard has exclusive mutable access.
            &mut *self.lock.value.get()
        }
    }
}

impl<T> Drop for SpinGuard<'_, T> {
    fn drop(&mut self) {
        self.lock.held.store(false, Ordering::Release);
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum BufferState {
    Empty,
    Allocating,
    InUse,
    Idle,
}

struct Buffer {
    state: BufferState,
    mapping: Option<Mapping>,
    node: u32,
    node_index: usize,
}

struct Shard {
    node: u32,
    reserve_count: u64,
    pending_reserve_count: u64,
    current_node_hit_count: u64,
    fallback_reserve_count: u64,
    slots: Option<HeapSlice<UnsafeCell<Buffer>>>,
}

struct PendingReserve {
    future: *mut ffi::AwsFutureS3BufferTicket,
    requested: usize,
    preferred_shard: usize,
    allocating: bool,
    next: *mut PendingReserve,
    ticket: *mut ffi::AwsS3BufferTicket,
    error_code: c_int,
    ops: Arc<dyn AllocationOps>,
}

// SAFETY: PendingReserve's raw pointers are only inspected while the owning pool's
// spin lock is held, except for the future passed to CRT's thread-safe API.
unsafe impl Send for PendingReserve {}

/// Completions staged under the lock and delivered after it, because
/// completing a future runs CRT callbacks that may re-enter the pool.
struct PendingCompletionBatch {
    head: *mut PendingReserve,
    tail: *mut PendingReserve,
}

impl PendingCompletionBatch {
    fn new() -> Self {
        Self {
            head: ptr::null_mut(),
            tail: ptr::null_mut(),
        }
    }

    fn is_empty(&self) -> bool {
        self.head.is_null()
    }

    fn push_ticket(&mut self, pending: *mut PendingReserve, ticket: *mut ffi::AwsS3BufferTicket) {
        self.push(pending, ticket, ffi::AWS_ERROR_SUCCESS);
    }

    fn push_error(&mut self, pending: *mut PendingReserve, error_code: c_int) {
        self.push(pending, ptr::null_mut(), error_code);
    }

    fn push_done(&mut self, pending: *mut PendingReserve) {
        self.push(pending, ptr::null_mut(), ffi::AWS_ERROR_SUCCESS);
    }

    fn push(
        &mut self,
        pending: *mut PendingReserve,
        ticket: *mut ffi::AwsS3BufferTicket,
        code: c_int,
    ) {
        // SAFETY: the caller detached pending from the queue, so this batch owns it.
        unsafe {
            (*pending).next = ptr::null_mut();
            (*pending).ticket = ticket;
            (*pending).error_code = code;
            if self.tail.is_null() {
                self.head = pending;
            } else {
                (*self.tail).next = pending;
            }
        }
        self.tail = pending;
    }

    fn pop(&mut self) -> *mut PendingReserve {
        let pending = self.head;
        if pending.is_null() {
            return pending;
        }
        // SAFETY: every staged node is exclusively owned by this batch.
        unsafe {
            self.head = (*pending).next;
            (*pending).next = ptr::null_mut();
        }
        if self.head.is_null() {
            self.tail = ptr::null_mut();
        }
        pending
    }

    fn drain(&mut self, pool: &Pool) {
        while !self.is_empty() {
            let pending = self.pop();
            // SAFETY: the popped node and its future reference are owned here.
            let (future, ticket, code) =
                unsafe { ((*pending).future, (*pending).ticket, (*pending).error_code) };
            if !ticket.is_null() {
                complete_future(pool, future, ticket);
            } else if code != ffi::AWS_ERROR_SUCCESS
                // SAFETY: the staged node retains its future reference.
                && !unsafe { pool.futures.is_done(future) }
            {
                complete_error(pool, future, code);
            }
            finish_pending_node(pool.futures, pending);
        }
    }
}

struct State {
    reserve_count: u64,
    pending_reserve_count: u64,
    forced_reserve_count: u64,
    cross_shard_steal_count: u64,
    shards: HeapSlice<Shard>,
    pending_head: *mut PendingReserve,
    pending_tail: *mut PendingReserve,
    pending_len: usize,
    allocated_bytes: usize,
    reserved_bytes: usize,
    forced_bytes: usize,
    next_shard: usize,
    special_sizes: [usize; SPECIAL_SIZES_MAX],
    special_size_count: usize,
}

struct Pool {
    interface: ffi::AwsS3BufferPool,
    allocator: *mut ffi::AwsAllocator,
    ops: Arc<dyn AllocationOps>,
    futures: &'static dyn FutureOps,
    refs: AtomicUsize,
    state: SpinLock<State>,
    shard_count: usize,
    part_size: usize,
    page_size: usize,
    max_buffer_size: usize,
    budget_bytes: usize,
    #[cfg(any(test, feature = "testing"))]
    diagnostics: Arc<Diagnostics>,
}

// SAFETY: all mutable pool state is behind SpinLock, interface pointers are
// immutable after publication, and the CRT allocator is itself thread-safe.
unsafe impl Send for Pool {}
// SAFETY: same invariant as Send; concurrent callbacks synchronize via state.
unsafe impl Sync for Pool {}

enum TicketBacking {
    Pooled(*mut Buffer),
    Forced(Option<Mapping>),
}

struct Ticket {
    interface: ffi::AwsS3BufferTicket,
    refs: AtomicUsize,
    pool: *mut Pool,
    backing: TicketBacking,
    pointer: *mut u8,
    requested: usize,
    node: u32,
}

// SAFETY: the raw pointers identify pinned Pool/Buffer allocations whose
// lifetimes are held by this ticket's pool reference. Mutations are locked.
unsafe impl Send for Ticket {}
// SAFETY: claim reads immutable ticket fields and release uses atomics/lock.
unsafe impl Sync for Ticket {}

#[repr(C)]
pub(super) struct PoolVtable {
    crt: ffi::AwsS3BufferPoolVtable,
    futures: &'static dyn FutureOps,
}

const _: () = assert!(std::mem::offset_of!(PoolVtable, crt) == 0);

impl PoolVtable {
    const fn new(futures: &'static dyn FutureOps) -> Self {
        Self {
            crt: ffi::AwsS3BufferPoolVtable {
                reserve: Some(pool_reserve),
                trim: Some(pool_trim),
                add_special_size: Some(pool_add_special_size),
                release_special_size: Some(pool_release_special_size),
                derive_aligned_buffer_size: Some(pool_derive_aligned_buffer_size),
                acquire: Some(pool_acquire),
                release: Some(pool_release),
                add_preallocated_buffer: None,
                remove_preallocated_buffer: None,
            },
            futures,
        }
    }
}

static CRT_POOL_VTABLE: PoolVtable = PoolVtable::new(&ffi::CrtFutures);
#[cfg(any(test, feature = "testing"))]
static FAKE_POOL_VTABLE: PoolVtable = PoolVtable::new(&ffi::fake::FakeFutures);

static TICKET_VTABLE: ffi::AwsS3BufferTicketVtable = ffi::AwsS3BufferTicketVtable {
    claim: Some(ticket_claim),
    acquire: Some(ticket_acquire),
    release: Some(ticket_release),
};

fn align_up(value: usize, alignment: usize) -> Option<usize> {
    value
        .checked_add(alignment.checked_sub(1)?)
        .map(|rounded| rounded / alignment * alignment)
}

fn allocation_size(pool: &Pool, requested: usize) -> Option<usize> {
    if !supported_size(pool, requested) {
        return None;
    }
    let value = requested.max(pool.part_size);
    let limit = pool.max_buffer_size.min(pool.budget_bytes);
    if value > limit {
        return None;
    }
    let aligned = align_up(value, pool.page_size).unwrap_or(value);
    Some(if aligned <= limit { aligned } else { value })
}

fn supported_size(pool: &Pool, requested: usize) -> bool {
    requested != 0 && requested <= pool.max_buffer_size && requested <= pool.budget_bytes
}

fn effective_budget_bytes(override_bytes: usize, crt_memory_limit: usize) -> usize {
    if override_bytes != 0 {
        override_bytes
    } else if crt_memory_limit != 0 {
        crt_memory_limit
    } else {
        SOURCE_POOL_BUDGET_BYTES_DEFAULT
    }
}

fn effective_max_buffer_size(config: ffi::AwsS3BufferPoolConfig, budget: usize) -> usize {
    let mut maximum = if config.max_part_size == 0 {
        budget
    } else {
        config.max_part_size.min(budget)
    };
    if config.part_size <= budget {
        maximum = maximum.max(config.part_size);
    }
    maximum
}

fn total_source_buffer_count(budget: usize, part_size: usize, node_count: usize) -> usize {
    let by_budget = (budget / part_size).max(1);
    by_budget
        .max(node_count.saturating_mul(SHARD_BUFFERS_MIN))
        .min(SOURCE_POOL_BUFFERS_MAX)
}

#[cfg(any(test, feature = "testing"))]
fn update_peak(peak: &AtomicUsize, value: usize) {
    let mut current = peak.load(Ordering::Relaxed);
    while value > current {
        match peak.compare_exchange_weak(current, value, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return,
            Err(observed) => current = observed,
        }
    }
}

fn pool_from_interface(interface: *mut ffi::AwsS3BufferPool) -> Option<*mut Pool> {
    if interface.is_null() {
        return None;
    }
    let implementation = unsafe {
        // SAFETY: non-null interfaces passed to our vtable were initialized by
        // factory() and remain pinned for the duration of the callback.
        (*interface).implementation
    };
    (!implementation.is_null()).then_some(implementation.cast::<Pool>())
}

/// # Safety
/// A non-null `interface` was reached through its own vtable, so a non-null
/// vtable is a [`PoolVtable`].
unsafe fn raise_without_pool(interface: *mut ffi::AwsS3BufferPool, code: c_int) {
    if interface.is_null() {
        return;
    }
    // SAFETY: the caller guarantees the vtable, when set, is a `PoolVtable`,
    // whose first field is the C vtable the interface points at.
    let vtable = unsafe { (*interface).vtable.cast_const().cast::<PoolVtable>() };
    // SAFETY: as above; the vtables are statics.
    if let Some(vtable) = unsafe { vtable.as_ref() } {
        vtable.futures.raise_error(code);
    }
}

fn ticket_from_interface(interface: *mut ffi::AwsS3BufferTicket) -> Option<*mut Ticket> {
    if interface.is_null() {
        return None;
    }
    let implementation = unsafe {
        // SAFETY: the vtable callback proves this is an interface initialized
        // by new_ticket(), pinned until its final release.
        (*interface).implementation
    };
    (!implementation.is_null()).then_some(implementation.cast::<Ticket>())
}

/// CRT buffer-pool factory callback.
///
/// # Safety
/// `user_data` must identify the pinned `FactoryConfig` retained by `Runtime`,
/// and `allocator` must outlive the returned pool and every outstanding
/// ticket and future created from it. `config` is copied during this call.
/// The returned interface owns its lifetime through CRT references.
pub unsafe extern "C" fn factory(
    allocator: *mut ffi::AwsAllocator,
    config: ffi::AwsS3BufferPoolConfig,
    user_data: *mut c_void,
) -> *mut ffi::AwsS3BufferPool {
    if !cfg!(target_os = "linux") || allocator.is_null() || user_data.is_null() {
        CRT_POOL_VTABLE
            .futures
            .raise_error(ffi::AWS_ERROR_INVALID_ARGUMENT);
        return ptr::null_mut();
    }
    // SAFETY: the callback contract requires retained FactoryConfig storage.
    let factory_config = unsafe { &*user_data.cast::<FactoryConfig>() };
    let ops: Arc<dyn AllocationOps> = Arc::new(super::allocation::CrtAllocationOps::new(allocator));
    factory_with_ops(allocator, config, factory_config, ops, &CRT_POOL_VTABLE)
}
struct PoolParts<'a> {
    factory_config: &'a FactoryConfig,
    ops: Arc<dyn AllocationOps>,
    vtable: &'static PoolVtable,
}
fn factory_with_ops(
    allocator: *mut ffi::AwsAllocator,
    config: ffi::AwsS3BufferPoolConfig,
    factory_config: &FactoryConfig,
    ops: Arc<dyn AllocationOps>,
    vtable: &'static PoolVtable,
) -> *mut ffi::AwsS3BufferPool {
    if allocator.is_null()
        || config.part_size == 0
        || factory_config.nodes.is_empty()
        || factory_config.nodes.len() > MAX_NODES
    {
        vtable.futures.raise_error(ffi::AWS_ERROR_INVALID_ARGUMENT);
        return ptr::null_mut();
    }
    let budget = effective_budget_bytes(factory_config.budget_bytes, config.memory_limit);
    let maximum = effective_max_buffer_size(config, budget);
    if budget == 0 || maximum == 0 {
        vtable.futures.raise_error(ffi::AWS_ERROR_INVALID_ARGUMENT);
        return ptr::null_mut();
    }
    if config.part_size > budget {
        vtable
            .futures
            .raise_error(ffi::AWS_ERROR_S3_PART_SIZE_EXCEEDS_MEMORY_LIMIT);
        return ptr::null_mut();
    }
    let parts = PoolParts {
        factory_config,
        ops,
        vtable,
    };
    let Some(pool) = create_pool(allocator, config, parts, budget, maximum) else {
        vtable.futures.raise_error(ffi::AWS_ERROR_OOM);
        return ptr::null_mut();
    };
    // SAFETY: pool is pinned and private until its initialized interface is returned.
    unsafe {
        (*pool).interface.implementation = pool.cast();
        &mut (*pool).interface
    }
}
fn create_pool(
    allocator: *mut ffi::AwsAllocator,
    config: ffi::AwsS3BufferPoolConfig,
    parts: PoolParts<'_>,
    budget: usize,
    maximum: usize,
) -> Option<*mut Pool> {
    let PoolParts {
        factory_config,
        ops,
        vtable,
    } = parts;
    let allocation = UninitValue::<Pool>::new(&ops, AllocationKind::Pool)?;
    let shards = create_shards(factory_config, config, budget, &ops)?;
    #[cfg(any(test, feature = "testing"))]
    factory_config
        .diagnostics
        .budget_bytes
        .store(budget, Ordering::Relaxed);
    let page_size = ops.page_size().max(1);
    let shard_count = shards.len();
    let pool = Pool {
        // SAFETY: the custom vtable owns refcounting; the unused embedded CRT refcount is zeroed.
        interface: unsafe {
            ffi::AwsS3BufferPool {
                vtable: ptr::from_ref(vtable)
                    .cast::<ffi::AwsS3BufferPoolVtable>()
                    .cast_mut(),
                ref_count: std::mem::zeroed(),
                implementation: ptr::null_mut(),
            }
        },
        allocator,
        ops,
        futures: vtable.futures,
        refs: AtomicUsize::new(1),
        state: SpinLock::new(State {
            reserve_count: 0,
            pending_reserve_count: 0,
            forced_reserve_count: 0,
            cross_shard_steal_count: 0,
            shards,
            pending_head: ptr::null_mut(),
            pending_tail: ptr::null_mut(),
            pending_len: 0,
            allocated_bytes: 0,
            reserved_bytes: 0,
            forced_bytes: 0,
            next_shard: 0,
            special_sizes: [0; SPECIAL_SIZES_MAX],
            special_size_count: 0,
        }),
        shard_count,
        part_size: config.part_size,
        page_size,
        max_buffer_size: maximum,
        budget_bytes: budget,
        #[cfg(any(test, feature = "testing"))]
        diagnostics: Arc::clone(&factory_config.diagnostics),
    };
    Some(allocation.initialize(pool))
}
fn create_shards(
    factory_config: &FactoryConfig,
    config: ffi::AwsS3BufferPoolConfig,
    budget: usize,
    ops: &Arc<dyn AllocationOps>,
) -> Option<HeapSlice<Shard>> {
    let count = factory_config.nodes.len();
    let slots = total_source_buffer_count(budget, config.part_size, count);
    let mut shards = HeapSlice::new(ops, AllocationKind::Shards, count, |index| Shard {
        node: factory_config.nodes[index],
        reserve_count: 0,
        pending_reserve_count: 0,
        current_node_hit_count: 0,
        fallback_reserve_count: 0,
        slots: None,
    })?;
    for (index, shard) in shards.iter_mut().enumerate() {
        let count = slots / count + usize::from(index < slots % count);
        shard.slots = Some(HeapSlice::new(ops, AllocationKind::Slots, count, |_| {
            UnsafeCell::new(Buffer {
                state: BufferState::Empty,
                mapping: None,
                node: shard.node,
                node_index: index,
            })
        })?);
    }
    Some(shards)
}

// SAFETY CONTRACT: CRT invokes this through a live pool interface reference;
// the returned future transfers only the references documented by aws-c-s3.
unsafe extern "C" fn pool_reserve(
    interface: *mut ffi::AwsS3BufferPool,
    meta: ffi::AwsS3BufferPoolReserveMeta,
) -> *mut ffi::AwsFutureS3BufferTicket {
    let Some(pool_pointer) = pool_from_interface(interface) else {
        // SAFETY: the CRT called this through the interface's vtable.
        unsafe { raise_without_pool(interface, ffi::AWS_ERROR_INVALID_ARGUMENT) };
        return ptr::null_mut();
    };
    let pool = unsafe {
        // SAFETY: the CRT holds a pool interface reference for this callback.
        &*pool_pointer
    };
    let future = unsafe {
        // SAFETY: allocator remains valid for the complete CRT library lifetime.
        pool.futures.new_future(pool.allocator)
    };
    if future.is_null() {
        pool.futures.raise_error(ffi::AWS_ERROR_OOM);
        return ptr::null_mut();
    }
    #[cfg(any(test, feature = "testing"))]
    pool.diagnostics
        .reservations
        .fetch_add(1, Ordering::Relaxed);
    if !supported_size(pool, meta.size) {
        complete_error(pool, future, ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);

        return future;
    }

    let Some(pending) = new_pending(pool, future, meta.size) else {
        return future;
    };
    let mut spare = SparePending {
        node: pending,
        futures: pool.futures,
    };
    reserve_on_shard(pool_pointer, future, meta, &mut spare)
}

fn new_pending(
    pool: &Pool,
    future: *mut ffi::AwsFutureS3BufferTicket,
    size: usize,
) -> Option<*mut PendingReserve> {
    let queue_future = unsafe {
        // SAFETY: future is valid and queue ownership needs a distinct ref.
        pool.futures.acquire(future)
    };
    if queue_future.is_null() {
        complete_error(pool, future, ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);

        return None;
    }
    let pending = PendingReserve {
        future: queue_future,
        requested: size,
        preferred_shard: 0,
        allocating: false,
        next: ptr::null_mut(),
        ticket: ptr::null_mut(),
        error_code: ffi::AWS_ERROR_SUCCESS,
        ops: Arc::clone(&pool.ops),
    };
    match allocate_value(&pool.ops, AllocationKind::Pending, pending) {
        Ok(pending) => Some(pending),
        Err(_) => {
            unsafe {
                // SAFETY: queue_future is the distinct reference acquired
                // above; future remains owned by the caller.
                pool.futures.release(queue_future);
                complete_error(pool, future, ffi::AWS_ERROR_OOM);
            }
            None
        }
    }
}

fn current_node_for_shard_selection(pool: &Pool) -> Option<u32> {
    if pool.shard_count == 1 {
        return None;
    }
    pool.ops.current_node()
}

fn select_shard(state: &mut State, current_node: Option<u32>) -> usize {
    let selected = if state.shards.len() == 1 {
        0
    } else if let Some(index) =
        current_node.and_then(|node| state.shards.iter().position(|shard| shard.node == node))
    {
        state.shards[index].current_node_hit_count += 1;
        index
    } else {
        let selected = state.next_shard % state.shards.len();
        state.next_shard = (state.next_shard + 1) % state.shards.len();
        state.shards[selected].fallback_reserve_count += 1;
        selected
    };
    state.reserve_count += 1;
    state.shards[selected].reserve_count += 1;
    selected
}

enum ReserveAction {
    Deliver {
        slot: *mut Buffer,
        node: u32,
    },
    Allocate {
        slot: *mut Buffer,
        size: usize,
        node: u32,
        node_index: usize,
    },
    Forced {
        shard_index: usize,
    },
    Trim(Mapping),
    Queued,
    QueuedWithoutDrive,
    Full,
}

struct SparePending {
    node: *mut PendingReserve,
    futures: &'static dyn FutureOps,
}
impl Drop for SparePending {
    fn drop(&mut self) {
        finish_pending_node(self.futures, self.node);
    }
}

fn queue_or_force(
    state: &mut State,
    preferred: usize,
    can_block: bool,
    spare: &mut SparePending,
) -> ReserveAction {
    if can_block {
        return ReserveAction::Forced {
            shard_index: preferred,
        };
    }
    if state.pending_len == PENDING_RESERVES_MAX {
        return ReserveAction::Full;
    }
    let pending = std::mem::replace(&mut spare.node, ptr::null_mut());
    // SAFETY: spare owns this node until this locked append transfers it to the queue.
    unsafe {
        (*pending).preferred_shard = preferred;
        if state.pending_tail.is_null() {
            state.pending_head = pending;
        } else {
            (*state.pending_tail).next = pending;
        }
        state.pending_tail = pending;
    }
    state.pending_len += 1;
    state.pending_reserve_count += 1;
    state.shards[preferred].pending_reserve_count += 1;
    ReserveAction::Queued
}

fn reserve_action(
    pool: &Pool,
    state: &mut State,
    preferred: usize,
    meta: ffi::AwsS3BufferPoolReserveMeta,
    spare: &mut SparePending,
) -> ReserveAction {
    if !state.pending_head.is_null() {
        return queue_or_force(state, preferred, meta.can_block, spare);
    }
    match take_buffer_or_claim_locked(pool, state, preferred, meta.size) {
        TakeBufferAction::Allocate {
            slot,
            size,
            node,
            node_index,
        } => ReserveAction::Allocate {
            slot,
            size,
            node,
            node_index,
        },
        TakeBufferAction::Trim(mapping) => ReserveAction::Trim(mapping),
        TakeBufferAction::Deliver(slot) => reserve_deliver(slot),
        TakeBufferAction::None => {
            if let Some(slot) = steal_idle(pool, state, preferred, meta.size) {
                return reserve_deliver(slot);
            }
            debug_assert_eq!(state.pending_len, 0);
            match queue_or_force(state, preferred, meta.can_block, spare) {
                ReserveAction::Queued => ReserveAction::QueuedWithoutDrive,
                action => action,
            }
        }
    }
}

fn reserve_deliver(slot: *mut Buffer) -> ReserveAction {
    // SAFETY: only the holder of the pool state lock selects and marks this slot.
    let node = unsafe {
        (*slot).state = BufferState::InUse;
        (*slot).node
    };
    ReserveAction::Deliver { slot, node }
}

fn reserve_on_shard(
    pool_pointer: *mut Pool,
    future: *mut ffi::AwsFutureS3BufferTicket,
    meta: ffi::AwsS3BufferPoolReserveMeta,
    spare: &mut SparePending,
) -> *mut ffi::AwsFutureS3BufferTicket {
    // SAFETY: caller retains its live pool reference for the complete reservation.
    let pool = unsafe { &*pool_pointer };
    let current_node = current_node_for_shard_selection(pool);
    let mut selected = None;
    for _ in 0..RESERVE_PASSES_MAX {
        let action = {
            let mut state = pool.state.lock();
            let preferred = *selected.get_or_insert_with(|| select_shard(&mut state, current_node));
            reserve_action(pool, &mut state, preferred, meta, spare)
        };
        if let Some(future) = finish_reserve_action(pool_pointer, future, meta, action) {
            return future;
        }
    }
    let action = {
        let mut state = pool.state.lock();
        let preferred = *selected.get_or_insert_with(|| select_shard(&mut state, current_node));
        queue_or_force(&mut state, preferred, meta.can_block, spare)
    };
    finish_reserve_action(pool_pointer, future, meta, action).unwrap_or(future)
}

fn finish_reserve_action(
    pool_pointer: *mut Pool,
    future: *mut ffi::AwsFutureS3BufferTicket,
    meta: ffi::AwsS3BufferPoolReserveMeta,
    action: ReserveAction,
) -> Option<*mut ffi::AwsFutureS3BufferTicket> {
    // SAFETY: caller retains its live pool reference for the complete reservation.
    let pool = unsafe { &*pool_pointer };
    Some(match action {
        ReserveAction::Trim(mapping) => {
            #[cfg(any(test, feature = "testing"))]
            pool.diagnostics.trims.fetch_add(1, Ordering::Relaxed);
            drop(mapping);
            return None;
        }
        ReserveAction::Queued => {
            complete_any_pending(pool_pointer);
            future
        }
        ReserveAction::QueuedWithoutDrive => future,
        ReserveAction::Full => {
            complete_error(pool, future, ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
            future
        }
        ReserveAction::Deliver { slot, node } => {
            Claim::in_use(pool_pointer, future, slot, meta.size).into_ticket(node)
        }
        ReserveAction::Allocate {
            slot,
            size,
            node,
            node_index,
        } => pool_reserve_allocate(
            AllocationClaim::new(pool_pointer, future, slot, size, node_index, meta.size),
            node,
        ),
        ReserveAction::Forced { shard_index } => {
            reserve_forced_ticket(pool_pointer, future, shard_index, meta.size)
        }
    })
}

fn reserve_forced_ticket(
    pool_pointer: *mut Pool,
    future: *mut ffi::AwsFutureS3BufferTicket,
    shard_index: usize,
    requested: usize,
) -> *mut ffi::AwsFutureS3BufferTicket {
    let pool = unsafe {
        // SAFETY: caller holds the CRT pool callback reference.
        &*pool_pointer
    };
    let size = align_up(requested, pool.page_size)
        .filter(|aligned| *aligned <= pool.max_buffer_size)
        .unwrap_or(requested);
    let node = {
        let mut state = pool.state.lock();
        state.forced_reserve_count += 1;
        state.shards[shard_index].node
    };
    match Mapping::allocate(&pool.ops, pool.futures, size, node) {
        Ok(mapping) => {
            let pointer = mapping.as_ptr();
            {
                let mut state = pool.state.lock();
                state.forced_bytes += mapping.len();
                #[cfg(any(test, feature = "testing"))]
                update_peak(&pool.diagnostics.peak_forced_bytes, state.forced_bytes);
            }
            #[cfg(any(test, feature = "testing"))]
            pool.diagnostics.record_mapping(shard_index, size);
            match new_ticket(
                pool_pointer,
                TicketBacking::Forced(Some(mapping)),
                pointer,
                requested,
                node,
            ) {
                Ok(ticket) => {
                    #[cfg(any(test, feature = "testing"))]
                    pool.diagnostics
                        .forced_grants
                        .fetch_add(1, Ordering::Relaxed);
                    complete_future(pool, future, ticket);
                }
                Err(TicketBacking::Forced(mut mapping)) => {
                    let mapping = take_forced(&mut mapping);
                    {
                        let mut state = pool.state.lock();
                        state.forced_bytes -= mapping.len();
                    }
                    drop(mapping);
                    complete_error(pool, future, ffi::AWS_ERROR_OOM);
                }
                Err(TicketBacking::Pooled(_)) => invalid_backing(),
            }
        }
        Err(_) => complete_error(pool, future, ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED),
    }
    future
}

enum PendingAction {
    None,
    Deliver {
        pending: *mut PendingReserve,
        slot: *mut Buffer,
    },
    Allocate {
        pending: *mut PendingReserve,
        slot: *mut Buffer,
        size: usize,
        node: u32,
    },
    Trim(Mapping),
}

fn pop_head(state: &mut State) -> *mut PendingReserve {
    let head = state.pending_head;
    if head.is_null() {
        debug_assert_eq!(state.pending_len, 0);
        return head;
    }
    unsafe {
        // SAFETY: head belongs to this locked intrusive queue.
        state.pending_head = (*head).next;
        (*head).next = ptr::null_mut();
    }
    state.pending_len -= 1;
    if state.pending_head.is_null() {
        debug_assert_eq!(state.pending_len, 0);
        state.pending_tail = ptr::null_mut();
    }
    head
}

fn best_idle(state: &mut State, preferred: usize, requested: usize) -> Option<*mut Buffer> {
    reusable_slot(state, preferred, requested, None)
}

fn reusable_slot(
    state: &mut State,
    shard: usize,
    requested: usize,
    exact: Option<usize>,
) -> Option<*mut Buffer> {
    let slots = state.shards[shard].slots.as_ref()?;
    let mut best: Option<*mut Buffer> = None;
    let mut best_len = usize::MAX;
    for cell in slots.iter() {
        // SAFETY: caller holds the exclusive pool state lock.
        let slot = unsafe { &*cell.get() };
        let Some(mapping) = slot.mapping.as_ref() else {
            continue;
        };
        let length = mapping.len();
        if slot.state != BufferState::Idle || length < requested {
            continue;
        }
        if exact == Some(length) {
            return Some(cell.get());
        }
        if length < best_len {
            best = Some(cell.get());
            best_len = length;
        }
    }
    best
}

fn idle_for(pool: &Pool, state: &mut State, shard: usize, requested: usize) -> Option<*mut Buffer> {
    let size = allocation_size(pool, requested).unwrap_or(requested);
    let exact = state.special_sizes[..state.special_size_count]
        .contains(&size)
        .then_some(size);
    if exact.is_none() {
        return best_idle(state, shard, requested);
    }
    reusable_slot(state, shard, requested, exact)
}

fn steal_idle(
    pool: &Pool,
    state: &mut State,
    preferred: usize,
    size: usize,
) -> Option<*mut Buffer> {
    for shard in 0..state.shards.len() {
        if shard != preferred
            && let Some(slot) = idle_for(pool, state, shard, size)
        {
            state.cross_shard_steal_count += 1;
            return Some(slot);
        }
    }
    None
}

fn find_free_buffer_slot_locked(state: &mut State, preferred: usize) -> Option<*mut Buffer> {
    state.shards[preferred]
        .slots
        .as_ref()?
        .iter()
        .find(|cell| {
            // SAFETY: caller holds the exclusive pool state lock.
            unsafe { (*cell.get()).state == BufferState::Empty }
        })
        .map(UnsafeCell::get)
}

fn detach_trim_candidate_locked(
    state: &mut State,
    shard: usize,
    requested: usize,
) -> Option<Mapping> {
    let slots = state.shards[shard].slots.as_ref()?;
    let index = slots
        .iter()
        .enumerate()
        .filter_map(|(index, cell)| {
            // SAFETY: caller holds the exclusive pool state lock.
            let slot = unsafe { &*cell.get() };
            let size = slot.mapping.as_ref()?.len();
            (slot.state == BufferState::Idle).then_some((index, size))
        })
        .min_by_key(|(_, size)| (requested != 0 && *size >= requested, *size))?
        .0;
    // SAFETY: caller holds the exclusive pool state lock.
    let slot = unsafe { &mut *slots[index].get() };
    let mapping = slot.mapping.take()?;
    slot.state = BufferState::Empty;
    state.allocated_bytes -= mapping.len();
    Some(mapping)
}

fn detach_trim_candidate_from_pool_locked(state: &mut State, requested: usize) -> Option<Mapping> {
    for shard in 0..state.shards.len() {
        if let Some(mapping) = detach_trim_candidate_locked(state, shard, requested) {
            return Some(mapping);
        }
    }
    None
}

enum TakeBufferAction {
    None,
    Deliver(*mut Buffer),
    Allocate {
        slot: *mut Buffer,
        size: usize,
        node: u32,
        node_index: usize,
    },
    Trim(Mapping),
}

fn take_buffer_or_claim_locked(
    pool: &Pool,
    state: &mut State,
    preferred: usize,
    requested: usize,
) -> TakeBufferAction {
    let Some(size) = allocation_size(pool, requested) else {
        return TakeBufferAction::None;
    };
    if let Some(slot) = idle_for(pool, state, preferred, requested) {
        return TakeBufferAction::Deliver(slot);
    }
    let Some(slot) = find_free_buffer_slot_locked(state, preferred) else {
        return detach_trim_candidate_locked(state, preferred, size)
            .map_or(TakeBufferAction::None, TakeBufferAction::Trim);
    };
    if !can_allocate(
        state.allocated_bytes,
        state.reserved_bytes,
        size,
        pool.budget_bytes,
    ) {
        return detach_trim_candidate_from_pool_locked(state, size)
            .map_or(TakeBufferAction::None, TakeBufferAction::Trim);
    }
    // SAFETY: the stable slot belongs to this exclusively locked state.
    let (node, node_index) = unsafe {
        (*slot).state = BufferState::Allocating;
        ((*slot).node, (*slot).node_index)
    };
    state.reserved_bytes += size;
    #[cfg(any(test, feature = "testing"))]
    update_peak(&pool.diagnostics.peak_reserved_bytes, state.reserved_bytes);
    TakeBufferAction::Allocate {
        slot,
        size,
        node,
        node_index,
    }
}

fn deliver_pending(state: &mut State, slot: *mut Buffer) -> PendingAction {
    // SAFETY: slot was selected while this exclusive state lock was held.
    unsafe {
        (*slot).state = BufferState::InUse;
    }
    PendingAction::Deliver {
        pending: pop_head(state),
        slot,
    }
}

fn serve_pending_head_locked(
    pool: &Pool,
    state: &mut State,
    released_home: Option<usize>,
    completions: &mut PendingCompletionBatch,
) -> PendingAction {
    for _ in 0..=PENDING_RESERVES_MAX {
        let head = state.pending_head;
        if head.is_null() {
            return PendingAction::None;
        }
        // SAFETY: the queue owns this head until it is detached under this lock.
        if unsafe { (*head).allocating } {
            return PendingAction::None;
        }
        // SAFETY: the queued head owns a live future reference.
        if !unsafe { pool.futures.is_done((*head).future) } {
            return serve_live_head(pool, state, head, released_home);
        }
        completions.push_done(pop_head(state));
    }
    PendingAction::None
}

fn serve_live_head(
    pool: &Pool,
    state: &mut State,
    head: *mut PendingReserve,
    released_home: Option<usize>,
) -> PendingAction {
    // SAFETY: the queue owns this head until it is detached under this lock.
    let (requested, preferred) = unsafe { ((*head).requested, (*head).preferred_shard) };
    if let Some(slot) = idle_for(pool, state, preferred, requested) {
        return deliver_pending(state, slot);
    }
    if let Some(home) = released_home.filter(|home| *home != preferred)
        && let Some(slot) = idle_for(pool, state, home, requested)
    {
        state.cross_shard_steal_count += 1;
        return deliver_pending(state, slot);
    }
    match take_buffer_or_claim_locked(pool, state, preferred, requested) {
        TakeBufferAction::Deliver(slot) => deliver_pending(state, slot),
        TakeBufferAction::Allocate {
            slot, size, node, ..
        } => {
            // SAFETY: the queue owns its head; this claim prevents another driver detaching it.
            unsafe {
                (*head).allocating = true;
            }
            PendingAction::Allocate {
                pending: head,
                slot,
                size,
                node,
            }
        }
        TakeBufferAction::Trim(mapping) => PendingAction::Trim(mapping),
        TakeBufferAction::None => steal_idle(pool, state, preferred, requested)
            .map_or(PendingAction::None, |slot| deliver_pending(state, slot)),
    }
}

fn complete_any_pending(pool_pointer: *mut Pool) {
    complete_pending_or_free(pool_pointer, None, None);
}

fn complete_pending_or_free(
    pool_pointer: *mut Pool,
    released_home: Option<usize>,
    returned: Option<*mut Buffer>,
) {
    let pool = unsafe {
        // SAFETY: caller has a pool or ticket reference for the entire drive.
        &*pool_pointer
    };
    let mut completions = PendingCompletionBatch::new();
    complete_pending_queues(pool_pointer, released_home, returned, &mut completions);
    completions.drain(pool);
}

fn complete_pending_queues(
    pool_pointer: *mut Pool,
    released_home: Option<usize>,
    returned: Option<*mut Buffer>,
    completions: &mut PendingCompletionBatch,
) {
    let pool = unsafe {
        // SAFETY: caller has a pool or ticket reference for the entire drive.
        &*pool_pointer
    };
    let mut returned = returned;
    for step in 0..PENDING_DRIVE_STEPS_MAX {
        let action = {
            let mut state = pool.state.lock();
            if let Some(slot) = returned.take() {
                idle_returned_slot(slot);
            }
            if step >= PENDING_DRIVE_STEPS_HANDOFF && redrive_certain(&state) {
                return;
            }
            serve_pending_head_locked(pool, &mut state, released_home, completions)
        };
        returned = match action {
            PendingAction::None => return,
            PendingAction::Trim(mapping) => {
                #[cfg(any(test, feature = "testing"))]
                pool.diagnostics.trims.fetch_add(1, Ordering::Relaxed);
                drop(mapping);
                None
            }
            PendingAction::Deliver { pending, slot } => {
                fulfill_pending(pool_pointer, pending, slot, completions)
            }
            PendingAction::Allocate {
                pending,
                slot,
                size,
                node,
            } => allocate_pending_unlocked(pool_pointer, pending, slot, size, node, completions),
        };
    }
    fail_undriven_queue(pool, returned, completions);
}

fn idle_returned_slot(slot: *mut Buffer) {
    // SAFETY: the caller holds the pool lock; the slot is in use by a ticket
    // released or never issued, which owned it exclusively, so it is
    // returned once.
    unsafe {
        (*slot).state = BufferState::Idle;
    }
}

fn fulfill_pending(
    pool_pointer: *mut Pool,
    pending: *mut PendingReserve,
    slot: *mut Buffer,
    completions: &mut PendingCompletionBatch,
) -> Option<*mut Buffer> {
    // SAFETY: the caller retains its pool reference throughout the drive.
    #[cfg(any(test, feature = "testing"))]
    let pool = unsafe { &*pool_pointer };
    let (requested, pointer, node) = unsafe {
        // SAFETY: pending is a detached node exclusively owned by this action;
        // slot remains in use, with an immutable mapping, until it is returned.
        ((*pending).requested, slot_pointer(slot), (*slot).node)
    };
    match new_ticket(
        pool_pointer,
        TicketBacking::Pooled(slot),
        pointer,
        requested,
        node,
    ) {
        Ok(ticket) => {
            #[cfg(any(test, feature = "testing"))]
            pool.diagnostics
                .queued_grants
                .fetch_add(1, Ordering::Relaxed);
            completions.push_ticket(pending, ticket);
            None
        }
        Err(TicketBacking::Pooled(slot)) => {
            completions.push_error(pending, ffi::AWS_ERROR_OOM);
            Some(slot)
        }
        Err(TicketBacking::Forced(_)) => invalid_backing(),
    }
}

fn fail_undriven_queue(
    pool: &Pool,
    returned: Option<*mut Buffer>,
    completions: &mut PendingCompletionBatch,
) {
    let mut state = pool.state.lock();
    if let Some(slot) = returned {
        idle_returned_slot(slot);
    }
    if redrive_certain(&state) {
        return;
    }
    for _ in 0..PENDING_RESERVES_MAX {
        let pending = pop_head(&mut state);
        if pending.is_null() {
            break;
        }
        completions.push_error(pending, ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
    }
    debug_assert!(state.pending_head.is_null());
}

fn redrive_certain(state: &State) -> bool {
    if state.reserved_bytes != 0 {
        return true;
    }
    state.shards.iter().any(|shard| {
        shard.slots.as_ref().is_some_and(|slots| {
            slots.iter().any(|cell| {
                // SAFETY: caller holds the exclusive pool state lock.
                unsafe { (*cell.get()).state == BufferState::InUse }
            })
        })
    })
}

fn detach_queue(state: &mut State) -> *mut PendingReserve {
    let head = state.pending_head;
    state.pending_head = ptr::null_mut();
    state.pending_tail = ptr::null_mut();
    state.pending_len = 0;
    head
}

fn fail_detached(pool: &Pool, mut pending: *mut PendingReserve, code: c_int) {
    for _ in 0..PENDING_RESERVES_MAX {
        if pending.is_null() {
            return;
        }
        let node = pending;
        pending = unsafe {
            // SAFETY: the whole detached list is exclusively owned here.
            (*node).next
        };
        unsafe {
            // SAFETY: node is detached before future completion may run code.
            (*node).next = ptr::null_mut();
        }
        let future = unsafe {
            // SAFETY: detached pending node retains its future reference.
            (*node).future
        };
        complete_error(pool, future, code);
        finish_pending_node(pool.futures, node);
    }
    debug_assert!(pending.is_null());
}

fn complete_error(pool: &Pool, future: *mut ffi::AwsFutureS3BufferTicket, code: c_int) {
    pool.ops.before_completion();
    // SAFETY: the caller retains a future reference until this completion returns.
    unsafe {
        pool.futures.set_error(future, code);
    }
}

fn complete_future(
    pool: &Pool,
    future: *mut ffi::AwsFutureS3BufferTicket,
    ticket: *mut ffi::AwsS3BufferTicket,
) {
    pool.ops.before_completion();
    let mut ticket = ticket;
    unsafe {
        // SAFETY: future and ticket each carry one owned reference. The CRT
        // atomically consumes ticket on success or releases it if already done.
        pool.futures.set_result_by_move(future, &mut ticket);
    }
}

fn finish_pending_node(futures: &dyn FutureOps, pending: *mut PendingReserve) {
    if pending.is_null() {
        return;
    }
    let future = unsafe {
        // SAFETY: pending is detached and uniquely owned by this function.
        (*pending).future
    };
    unsafe {
        // SAFETY: this releases exactly the reference acquired for queue
        // ownership, then reconstructs exactly one Box allocation.
        futures.release(future);
        let ops = Arc::clone(&(*pending).ops);
        release_value(&ops, AllocationKind::Pending, pending);
    }
}

#[derive(Clone, Copy)]
struct ClaimedSlot {
    pool: *mut Pool,
    future: *mut ffi::AwsFutureS3BufferTicket,
    slot: *mut Buffer,
    shard_index: usize,
    requested: usize,
}

impl ClaimedSlot {
    fn fail_and_service_pending(
        self,
        returned: Option<*mut Buffer>,
        code: c_int,
    ) -> *mut ffi::AwsFutureS3BufferTicket {
        // SAFETY: the claim retains its pool reference until it is consumed.
        let pool = unsafe { &*self.pool };
        complete_error(pool, self.future, code);
        complete_pending_or_free(self.pool, Some(self.shard_index), returned);
        self.future
    }
}

#[must_use]
struct Claim {
    claimed: ClaimedSlot,
}

impl Claim {
    fn in_use(
        pool: *mut Pool,
        future: *mut ffi::AwsFutureS3BufferTicket,
        slot: *mut Buffer,
        requested: usize,
    ) -> Self {
        // SAFETY: this reservation owns the in-use slot; its shard never changes.
        let shard_index = unsafe { (*slot).node_index };
        Self {
            claimed: ClaimedSlot {
                pool,
                future,
                slot,
                shard_index,
                requested,
            },
        }
    }

    fn into_ticket(self, node: u32) -> *mut ffi::AwsFutureS3BufferTicket {
        match new_ticket(
            self.claimed.pool,
            TicketBacking::Pooled(self.claimed.slot),
            slot_pointer(self.claimed.slot),
            self.claimed.requested,
            node,
        ) {
            Ok(ticket) => {
                let claimed = ManuallyDrop::new(self).claimed;
                // SAFETY: the new ticket retains its pool for completion.
                let pool = unsafe { &*claimed.pool };
                complete_future(pool, claimed.future, ticket);
                claimed.future
            }
            Err(TicketBacking::Pooled(_)) => self.fail(ffi::AWS_ERROR_OOM),
            Err(TicketBacking::Forced(_)) => invalid_backing(),
        }
    }

    fn fail(self, code: c_int) -> *mut ffi::AwsFutureS3BufferTicket {
        ManuallyDrop::new(self).fail_and_service_pending(code)
    }

    fn fail_and_service_pending(&self, code: c_int) -> *mut ffi::AwsFutureS3BufferTicket {
        self.claimed
            .fail_and_service_pending(Some(self.claimed.slot), code)
    }
}

impl Drop for Claim {
    fn drop(&mut self) {
        self.fail_and_service_pending(ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
        debug_assert!(
            std::thread::panicking(),
            "reservation claim dropped without completing its future"
        );
    }
}

#[must_use]
struct AllocationClaim {
    claimed: ClaimedSlot,
    size: usize,
}

impl AllocationClaim {
    fn new(
        pool: *mut Pool,
        future: *mut ffi::AwsFutureS3BufferTicket,
        slot: *mut Buffer,
        size: usize,
        shard_index: usize,
        requested: usize,
    ) -> Self {
        Self {
            claimed: ClaimedSlot {
                pool,
                future,
                slot,
                shard_index,
                requested,
            },
            size,
        }
    }

    fn install(self, mapping: Mapping) -> Claim {
        // SAFETY: the claim retains its pool reference until it is consumed.
        let pool = unsafe { &*self.claimed.pool };
        {
            let mut state = pool.state.lock();
            state.reserved_bytes -= self.size;
            state.allocated_bytes += mapping.len();
            #[cfg(any(test, feature = "testing"))]
            update_peak(
                &pool.diagnostics.peak_allocated_bytes,
                state.allocated_bytes,
            );
            unsafe {
                // SAFETY: this reservation claimed the allocating slot
                // before dropping the lock and now installs it once.
                debug_assert!((*self.claimed.slot).state == BufferState::Allocating);
                debug_assert!((*self.claimed.slot).mapping.is_none());
                (*self.claimed.slot).mapping = Some(mapping);
                (*self.claimed.slot).state = BufferState::InUse;
            }
        }
        let allocation = ManuallyDrop::new(self);
        #[cfg(any(test, feature = "testing"))]
        pool.diagnostics
            .record_mapping(allocation.claimed.shard_index, allocation.size);
        Claim {
            claimed: allocation.claimed,
        }
    }

    fn fail(self, code: c_int) -> *mut ffi::AwsFutureS3BufferTicket {
        ManuallyDrop::new(self).fail_and_service_pending(code)
    }

    fn fail_and_service_pending(&self, code: c_int) -> *mut ffi::AwsFutureS3BufferTicket {
        // SAFETY: the claim retains its pool reference until it is consumed.
        let pool = unsafe { &*self.claimed.pool };
        {
            let mut state = pool.state.lock();
            abort_allocation(&mut state, self.claimed.slot, self.size);
        }
        self.claimed.fail_and_service_pending(None, code)
    }
}

impl Drop for AllocationClaim {
    fn drop(&mut self) {
        self.fail_and_service_pending(ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
        debug_assert!(
            std::thread::panicking(),
            "reservation claim dropped without completing its future"
        );
    }
}

fn new_ticket(
    pool_pointer: *mut Pool,
    backing: TicketBacking,
    pointer: *mut u8,
    requested: usize,
    node: u32,
) -> Result<*mut ffi::AwsS3BufferTicket, TicketBacking> {
    let pool = unsafe {
        // SAFETY: caller holds a pool reference while constructing the ticket.
        &*pool_pointer
    };
    let ticket = Ticket {
        interface: unsafe {
            // SAFETY: custom ticket ref callbacks make the embedded C refcount
            // intentionally unused and therefore zero-initialized.
            ffi::AwsS3BufferTicket {
                vtable: (&TICKET_VTABLE as *const ffi::AwsS3BufferTicketVtable).cast_mut(),
                ref_count: std::mem::zeroed(),
                implementation: ptr::null_mut(),
            }
        },
        refs: AtomicUsize::new(1),
        pool: pool_pointer,
        backing,
        pointer,
        requested,
        node,
    };
    let ticket = match allocate_value(&pool.ops, AllocationKind::Ticket, ticket) {
        Ok(ticket) => ticket,
        Err(ticket) => {
            pool.futures.raise_error(ffi::AWS_ERROR_OOM);
            return Err(ticket.backing);
        }
    };
    pool.refs.fetch_add(1, Ordering::AcqRel);
    unsafe {
        // SAFETY: ticket is pinned and not visible until implementation is set.
        (*ticket).interface.implementation = ticket.cast();
        Ok(&mut (*ticket).interface)
    }
}

// SAFETY CONTRACT: CRT calls through the ticket's vtable while holding a live
// ticket reference, which pins the immutable pointer and requested capacity.
unsafe extern "C" fn ticket_claim(interface: *mut ffi::AwsS3BufferTicket) -> ffi::AwsByteBuf {
    let Some(ticket) = ticket_from_interface(interface) else {
        return ffi::AwsByteBuf {
            len: 0,
            buffer: ptr::null_mut(),
            capacity: 0,
            allocator: ptr::null_mut(),
        };
    };
    let ticket = unsafe {
        // SAFETY: callback invocation holds a ticket reference.
        &*ticket
    };
    ffi::AwsByteBuf {
        len: 0,
        buffer: ticket.pointer,
        capacity: ticket.requested,
        allocator: ptr::null_mut(),
    }
}

// SAFETY CONTRACT: CRT supplies a live ticket interface and transfers one new
// reference to the caller when this callback returns the same interface.
unsafe extern "C" fn ticket_acquire(
    interface: *mut ffi::AwsS3BufferTicket,
) -> *mut ffi::AwsS3BufferTicket {
    let Some(ticket) = ticket_from_interface(interface) else {
        return ptr::null_mut();
    };
    unsafe {
        // SAFETY: callback entry guarantees a live ticket reference.
        (*ticket).refs.fetch_add(1, Ordering::AcqRel);
    }
    interface
}

// SAFETY CONTRACT: CRT supplies and transfers exactly one live ticket
// reference; final release uniquely owns the ticket allocation and backing.
unsafe extern "C" fn ticket_release(
    interface: *mut ffi::AwsS3BufferTicket,
) -> *mut ffi::AwsS3BufferTicket {
    let Some(ticket_pointer) = ticket_from_interface(interface) else {
        return ptr::null_mut();
    };
    let final_reference = unsafe {
        // SAFETY: each caller transfers one valid ticket reference.
        (*ticket_pointer).refs.fetch_sub(1, Ordering::AcqRel) == 1
    };
    if !final_reference {
        return ptr::null_mut();
    }
    let mut ticket = unsafe {
        // SAFETY: the final reference uniquely owns the original Box.
        std::ptr::read(ticket_pointer)
    };
    let pool_pointer = ticket.pool;
    let pool = unsafe {
        // SAFETY: every ticket holds one pool reference until this function's end.
        &*pool_pointer
    };
    match &mut ticket.backing {
        TicketBacking::Pooled(slot) => {
            // SAFETY: the pooled ticket uniquely owns this in-use slot, and a
            // slot's shard never changes.
            let owner = unsafe { (**slot).node_index };
            #[cfg(any(test, feature = "testing"))]
            pool.diagnostics.releases.fetch_add(1, Ordering::Relaxed);
            complete_pending_or_free(pool_pointer, Some(owner), Some(*slot));
        }
        TicketBacking::Forced(mapping) => {
            let mapping = take_forced(mapping);
            {
                let mut state = pool.state.lock();
                state.forced_bytes -= mapping.len();
            }
            #[cfg(any(test, feature = "testing"))]
            pool.diagnostics.releases.fetch_add(1, Ordering::Relaxed);
            drop(mapping);
        }
    }
    drop(ticket);
    // SAFETY: the final ticket value has dropped; release its matching storage.
    unsafe {
        pool.ops.release(
            AllocationKind::Ticket,
            std::ptr::NonNull::new_unchecked(ticket_pointer.cast()),
            std::alloc::Layout::new::<Ticket>(),
        );
    }
    release_pool_reference(pool_pointer);
    ptr::null_mut()
}

// SAFETY CONTRACT: CRT calls through a live pool reference. Only idle mappings
// are detached under the lock and unmapped after the lock is released.
unsafe extern "C" fn pool_trim(interface: *mut ffi::AwsS3BufferPool) {
    let Some(pool_pointer) = pool_from_interface(interface) else {
        return;
    };
    let pool = unsafe {
        // SAFETY: callback holds a pool reference.
        &*pool_pointer
    };
    for _ in 0..SOURCE_POOL_BUFFERS_MAX {
        let mapping = {
            let mut state = pool.state.lock();
            detach_trim_candidate_from_pool_locked(&mut state, 0)
        };
        let Some(mapping) = mapping else { break };
        #[cfg(any(test, feature = "testing"))]
        pool.diagnostics.trims.fetch_add(1, Ordering::Relaxed);
        drop(mapping);
    }
    complete_any_pending(pool_pointer);
}

// SAFETY CONTRACT: CRT calls through a live pool reference; `size` is a value,
// and all mutable special-size state remains protected by the pool lock.
unsafe extern "C" fn pool_add_special_size(
    interface: *mut ffi::AwsS3BufferPool,
    size: usize,
) -> c_int {
    let Some(pool_pointer) = pool_from_interface(interface) else {
        // SAFETY: the CRT called this through the interface's vtable.
        unsafe { raise_without_pool(interface, ffi::AWS_ERROR_INVALID_ARGUMENT) };
        return -1;
    };
    let pool = unsafe {
        // SAFETY: callback holds a pool reference.
        &*pool_pointer
    };
    if !supported_size(pool, size) {
        pool.futures
            .raise_error(ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
        return -1;
    }
    let size = allocation_size(pool, size).unwrap_or(size);
    let mut state = pool.state.lock();
    if state.special_sizes[..state.special_size_count].contains(&size) {
        return ffi::AWS_OP_SUCCESS;
    }
    if state.special_size_count < SPECIAL_SIZES_MAX {
        let index = state.special_size_count;
        state.special_sizes[index] = size;
        state.special_size_count += 1;
    }
    ffi::AWS_OP_SUCCESS
}

// SAFETY CONTRACT: CRT calls through a live pool reference; `size` is a value,
// and all mutable special-size state remains protected by the pool lock.
unsafe extern "C" fn pool_release_special_size(interface: *mut ffi::AwsS3BufferPool, size: usize) {
    let Some(pool_pointer) = pool_from_interface(interface) else {
        return;
    };
    let pool = unsafe {
        // SAFETY: callback holds a pool reference.
        &*pool_pointer
    };
    let size = allocation_size(pool, size).unwrap_or(size);
    let mut state = pool.state.lock();
    if let Some(index) = state.special_sizes[..state.special_size_count]
        .iter()
        .position(|candidate| *candidate == size)
    {
        state.special_size_count -= 1;
        let last = state.special_size_count;
        state.special_sizes[index] = state.special_sizes[last];
        state.special_sizes[last] = 0;
    }
}

// SAFETY CONTRACT: CRT calls through a live pool reference; the callback reads
// immutable sizing fields and returns no borrowed pool memory.
unsafe extern "C" fn pool_derive_aligned_buffer_size(
    interface: *mut ffi::AwsS3BufferPool,
    size: u64,
) -> u64 {
    if size == 0 {
        return 0;
    }
    let Some(pool_pointer) = pool_from_interface(interface) else {
        return size;
    };
    let pool = unsafe {
        // SAFETY: callback holds a pool reference.
        &*pool_pointer
    };
    let capped = usize::try_from(size)
        .unwrap_or(usize::MAX)
        .min(pool.max_buffer_size);
    allocation_size(pool, capped).unwrap_or(pool.max_buffer_size) as u64
}

// SAFETY CONTRACT: CRT supplies one live pool reference and this callback
// creates exactly one additional reference before returning the interface.
unsafe extern "C" fn pool_acquire(
    interface: *mut ffi::AwsS3BufferPool,
) -> *mut ffi::AwsS3BufferPool {
    let Some(pool) = pool_from_interface(interface) else {
        return ptr::null_mut();
    };
    unsafe {
        // SAFETY: callback entry holds one live pool reference.
        (*pool).refs.fetch_add(1, Ordering::AcqRel);
    }
    interface
}

// SAFETY CONTRACT: CRT transfers exactly one live pool reference; the final
// reference exclusively owns the pool allocation and detached pending list.
unsafe extern "C" fn pool_release(
    interface: *mut ffi::AwsS3BufferPool,
) -> *mut ffi::AwsS3BufferPool {
    if let Some(pool) = pool_from_interface(interface) {
        release_pool_reference(pool);
    }
    ptr::null_mut()
}

fn release_pool_reference(pool_pointer: *mut Pool) {
    let final_reference = unsafe {
        // SAFETY: caller transfers exactly one live pool reference.
        (*pool_pointer).refs.fetch_sub(1, Ordering::AcqRel) == 1
    };
    if !final_reference {
        return;
    }
    let pool = unsafe {
        // SAFETY: the final reference uniquely owns the pool until its drop.
        &*pool_pointer
    };
    let pending = detach_queue(&mut pool.state.lock());
    fail_detached(pool, pending, ffi::AWS_ERROR_S3_CANCELED);
    let ops = Arc::clone(&pool.ops);
    // SAFETY: the final reference owns the initialized pool, read out once
    // here; nothing reads it as a pool afterwards.
    drop(unsafe { ptr::read(pool_pointer) });
    // SAFETY: final pool value is dropped; release matching storage exactly once.
    unsafe {
        ops.release(
            AllocationKind::Pool,
            std::ptr::NonNull::new_unchecked(pool_pointer.cast()),
            std::alloc::Layout::new::<Pool>(),
        );
    }
}

/// Return the actual source mapping's NUMA node for one of this pool's
/// tickets. Unknown/default CRT tickets intentionally return `None`.
///
/// # Safety
/// A non-null interface must be a live CRT ticket retained for this call.
pub unsafe fn ticket_node(interface: *mut ffi::AwsS3BufferTicket) -> Option<u32> {
    if interface.is_null() {
        return None;
    }
    let ours = unsafe {
        // SAFETY: body callbacks hold the ticket alive while inspecting its
        // immutable interface pointer.
        ptr::eq(
            (*interface).vtable.cast_const(),
            &TICKET_VTABLE as *const ffi::AwsS3BufferTicketVtable,
        )
    };
    if !ours {
        return None;
    }
    ticket_from_interface(interface).map(|ticket| unsafe {
        // SAFETY: exact vtable identity proves the implementation is Ticket;
        // the callback's ticket reference pins it during this read.
        (*ticket).node
    })
}

fn abort_allocation(state: &mut State, slot: *mut Buffer, size: usize) {
    // SAFETY: the caller owns this in-flight claim under the exclusive state lock.
    unsafe {
        debug_assert!((*slot).state == BufferState::Allocating);
        debug_assert!((*slot).mapping.is_none());
        state.reserved_bytes -= size;
        (*slot).state = BufferState::Empty;
    }
}

fn can_allocate(allocated: usize, reserved: usize, size: usize, budget: usize) -> bool {
    allocated <= budget && reserved <= budget - allocated && size <= budget - allocated - reserved
}

#[cfg(test)]
mod test_support;
#[cfg(test)]
mod tests;

#[cfg(any(test, feature = "testing"))]
pub mod model;

#[expect(
    clippy::expect_used,
    reason = "only an in-use slot selected under the lock reaches this helper"
)]
fn slot_pointer(slot: *mut Buffer) -> *mut u8 {
    // SAFETY: the caller exclusively owns this in-use slot until ticket transfer.
    unsafe {
        (*slot)
            .mapping
            .as_ref()
            .expect("in-use slot has mapping")
            .as_ptr()
    }
}

#[expect(
    clippy::expect_used,
    reason = "forced ticket construction installs exactly one owned mapping"
)]
fn take_forced(mapping: &mut Option<Mapping>) -> Mapping {
    mapping.take().expect("forced ticket owns mapping")
}

#[expect(
    clippy::unreachable,
    reason = "new_ticket returns the same backing variant it received"
)]
fn invalid_backing() -> ! {
    unreachable!("internal pool action invariant violated")
}

fn pool_reserve_allocate(claim: AllocationClaim, node: u32) -> *mut ffi::AwsFutureS3BufferTicket {
    // SAFETY: the claim retains its pool reference across this allocation.
    let pool = unsafe { &*claim.claimed.pool };
    match Mapping::allocate(&pool.ops, pool.futures, claim.size, node) {
        Ok(mapping) => claim.install(mapping).into_ticket(node),
        Err(_) => claim.fail(ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED),
    }
}

fn allocate_pending_unlocked(
    pool_pointer: *mut Pool,
    pending: *mut PendingReserve,
    slot: *mut Buffer,
    size: usize,
    node: u32,
    completions: &mut PendingCompletionBatch,
) -> Option<*mut Buffer> {
    // SAFETY: caller retains its pool reference throughout queue driving.
    let pool = unsafe { &*pool_pointer };
    let Ok(mapping) = Mapping::allocate(&pool.ops, pool.futures, size, node) else {
        let mut state = pool.state.lock();
        abort_allocation(&mut state, slot, size);
        let detached = pop_head(&mut state);
        debug_assert_eq!(detached, pending);
        completions.push_error(pending, ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
        return None;
    };
    let completed = unsafe {
        // SAFETY: queue ownership retains the future while the allocation is in flight.
        pool.futures.is_done((*pending).future)
    };
    finish_pending_allocation_success_locked(pool, pending, slot, size, mapping, completed);
    if completed {
        completions.push_done(pending);
        return None;
    }
    fulfill_pending(pool_pointer, pending, slot, completions)
}

fn finish_pending_allocation_success_locked(
    pool: &Pool,
    pending: *mut PendingReserve,
    slot: *mut Buffer,
    size: usize,
    mapping: Mapping,
    completed: bool,
) {
    let mut state = pool.state.lock();
    state.reserved_bytes -= size;
    state.allocated_bytes += mapping.len();
    #[cfg(any(test, feature = "testing"))]
    update_peak(
        &pool.diagnostics.peak_allocated_bytes,
        state.allocated_bytes,
    );
    // SAFETY: slot was claimed for this allocation and cannot be selected by
    // another drive action.
    let slot_ref = unsafe { &mut *slot };
    debug_assert!(slot_ref.state == BufferState::Allocating);
    debug_assert!(slot_ref.mapping.is_none());
    #[cfg(any(test, feature = "testing"))]
    pool.diagnostics.record_mapping(slot_ref.node_index, size);
    slot_ref.mapping = Some(mapping);
    slot_ref.state = if completed {
        BufferState::Idle
    } else {
        BufferState::InUse
    };
    let detached = pop_head(&mut state);
    debug_assert_eq!(detached, pending);
}
