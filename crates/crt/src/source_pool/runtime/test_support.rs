#![expect(
    clippy::unwrap_used,
    clippy::panic,
    reason = "test fixtures require successful construction and invariant locks"
)]
use super::*;
use std::{
    alloc::Layout,
    ptr::NonNull,
    sync::{
        Mutex,
        atomic::{AtomicPtr, AtomicU32},
    },
};
#[derive(Default)]
pub(super) struct FakeOps {
    pub calls: AtomicUsize,
    pub live: AtomicUsize,
    pub mappings: AtomicUsize,
    pub huge_page_hints: AtomicUsize,
    pub fail_at: AtomicUsize,
    pub fail_kind: Mutex<Option<AllocationKind>>,
    pub fail_mmap: AtomicBool,
    pub fail_mbind: AtomicBool,
    pub node: AtomicU32,
    pub current_node_calls: AtomicUsize,
    pub lock_probe: AtomicPtr<AtomicBool>,
    pub probed: AtomicUsize,
    pub completions: AtomicUsize,
    pub released: AtomicUsize,
    pub on_complete: Mutex<Option<Box<dyn FnOnce() + Send>>>,
    pub on_map: Mutex<Option<Box<dyn FnOnce() + Send>>>,
    pub map_hook: Mutex<Option<Box<dyn FnMut() -> bool + Send>>>,
}
impl std::fmt::Debug for FakeOps {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.debug_struct("FakeOps").finish_non_exhaustive()
    }
}
impl FakeOps {
    pub fn outside_lock(&self) {
        let probe = self.lock_probe.load(Ordering::Acquire);
        // SAFETY: a non-null probe names the lock flag inside a pool's
        // storage, which destruction drops in place; `release` clears it
        // before that storage is freed.
        if let Some(held) = unsafe { probe.as_ref() } {
            assert!(
                !held.load(Ordering::Acquire),
                "external allocation operation ran under pool spin lock"
            );
            self.probed.fetch_add(1, Ordering::AcqRel);
        }
    }
    fn forget_probe_within(&self, pointer: NonNull<u8>, layout: Layout) {
        let start = pointer.as_ptr().addr();
        let probe = self.lock_probe.load(Ordering::Acquire);
        if (start..start + layout.size()).contains(&probe.addr()) {
            self.lock_probe.store(ptr::null_mut(), Ordering::Release);
        }
    }
}
// SAFETY: this backend uses matching std allocations and owns their complete writable storage.
unsafe impl AllocationOps for FakeOps {
    fn allocate(&self, kind: AllocationKind, layout: Layout) -> Option<NonNull<u8>> {
        self.outside_lock();
        let call = self.calls.fetch_add(1, Ordering::AcqRel) + 1;
        if self.fail_at.load(Ordering::Acquire) == call
            || *self.fail_kind.lock().unwrap() == Some(kind)
        {
            return None;
        }
        // SAFETY: layout is positive; the returned pointer is tracked until release.
        let pointer = NonNull::new(unsafe { std::alloc::alloc_zeroed(layout) })?;
        self.live.fetch_add(1, Ordering::AcqRel);
        Some(pointer)
    }
    unsafe fn release(&self, kind: AllocationKind, pointer: NonNull<u8>, layout: Layout) {
        self.outside_lock();
        if kind == AllocationKind::Pool {
            self.forget_probe_within(pointer, layout);
        }
        self.live.fetch_sub(1, Ordering::AcqRel);
        self.released.fetch_add(1, Ordering::AcqRel);
        // SAFETY: the AllocationOps caller supplies its matching live allocation and layout.
        unsafe {
            std::alloc::dealloc(pointer.as_ptr(), layout);
        }
    }
    fn mmap(&self, size: usize) -> Result<NonNull<u8>, super::super::allocation::MappingError> {
        self.outside_lock();
        let hook = self.on_map.lock().unwrap().take();
        if let Some(hook) = hook {
            hook();
        }
        let repeated = self.map_hook.lock().unwrap().take();
        if let Some(mut hook) = repeated {
            let allowed = hook();
            *self.map_hook.lock().unwrap() = Some(hook);
            if !allowed {
                return Err(super::super::allocation::MappingError);
            }
        }
        if self.fail_mmap.load(Ordering::Acquire) {
            return Err(super::super::allocation::MappingError);
        }
        let layout = Layout::from_size_align(size, 64).unwrap();
        // SAFETY: layout describes the entire writable fake mapping, released with the same layout.
        let pointer = NonNull::new(unsafe { std::alloc::alloc_zeroed(layout) })
            .ok_or(super::super::allocation::MappingError)?;
        self.mappings.fetch_add(1, Ordering::AcqRel);
        Ok(pointer)
    }
    unsafe fn mbind(
        &self,
        _: NonNull<u8>,
        _: usize,
        _: u32,
    ) -> Result<(), super::super::allocation::MappingError> {
        self.outside_lock();
        if self.fail_mbind.load(Ordering::Acquire) {
            Err(super::super::allocation::MappingError)
        } else {
            Ok(())
        }
    }
    unsafe fn munmap(&self, pointer: NonNull<u8>, size: usize) {
        self.outside_lock();
        self.mappings.fetch_sub(1, Ordering::AcqRel);
        // SAFETY: this uniquely owned fake mapping was allocated with the matching layout.
        unsafe {
            std::alloc::dealloc(pointer.as_ptr(), Layout::from_size_align(size, 64).unwrap());
        }
    }
    unsafe fn prefer_huge_pages(&self, _: NonNull<u8>, _: usize) {
        self.outside_lock();
        self.huge_page_hints.fetch_add(1, Ordering::AcqRel);
    }
    fn current_node(&self) -> Option<u32> {
        self.current_node_calls.fetch_add(1, Ordering::AcqRel);
        Some(self.node.load(Ordering::Acquire))
    }
    fn page_size(&self) -> usize {
        1
    }
    fn before_completion(&self) {
        self.outside_lock();
        self.completions.fetch_add(1, Ordering::AcqRel);
        let hook = self.on_complete.lock().unwrap().take();
        if let Some(hook) = hook {
            hook();
        }
    }
}
pub(super) struct TestPool {
    pub pointer: *mut Pool,
    pub ops: Arc<FakeOps>,
}
impl TestPool {
    pub fn new(nodes: &[u32], budget: usize, part: usize) -> Self {
        Self::with_ops(nodes, budget, part, Arc::new(FakeOps::default())).unwrap()
    }
    pub fn with_ops(nodes: &[u32], budget: usize, part: usize, ops: Arc<FakeOps>) -> Option<Self> {
        let factory = FactoryConfig::new(Config {
            nodes: nodes.to_vec(),
            budget_bytes: budget,
        });
        let config = ffi::AwsS3BufferPoolConfig {
            client: ptr::null_mut(),
            part_size: part,
            max_part_size: budget,
            memory_limit: 0,
        };
        let interface = factory_with_ops(
            NonNull::dangling().as_ptr(),
            config,
            &factory,
            ops.clone(),
            &FAKE_POOL_VTABLE,
        );
        let pointer = pool_from_interface(interface)?;
        // SAFETY: interface is a newly constructed live pool owned by this
        // wrapper; this only takes the address of its lock flag.
        let held = unsafe { &raw const (*pointer).state.held };
        ops.lock_probe.store(held.cast_mut(), Ordering::Release);
        Some(Self { pointer, ops })
    }
    pub fn pool(&self) -> &Pool {
        // SAFETY: the wrapper owns one live pool reference throughout this borrow.
        unsafe { &*self.pointer }
    }
    pub fn interface(&self) -> *mut ffi::AwsS3BufferPool {
        // SAFETY: the pool is live and pinned while the returned pointer is used.
        unsafe { &raw mut (*self.pointer).interface }
    }
    pub fn reserve(&self, size: usize, can_block: bool) -> Future {
        // SAFETY: this wrapper retains the pool and owns the returned future.
        let pointer = unsafe {
            pool_reserve(
                self.interface(),
                ffi::AwsS3BufferPoolReserveMeta {
                    size,
                    can_block,
                    local_offset: 0,
                    client: ptr::null_mut(),
                    meta_request: ptr::null_mut(),
                },
            )
        };
        assert!(!pointer.is_null());
        Future(pointer)
    }
    pub fn trim(&self) {
        // SAFETY: this wrapper retains the pool reference throughout the callback.
        unsafe {
            pool_trim(self.interface());
        }
    }
}
impl Drop for TestPool {
    fn drop(&mut self) {
        release_pool_reference(self.pointer);
    }
}
pub(super) struct Future(pub *mut ffi::AwsFutureS3BufferTicket);
impl Future {
    pub fn done(&self) -> bool {
        // SAFETY: this wrapper owns the queried future reference.
        unsafe { ffi::fake::FakeFutures.is_done(self.0) }
    }
    pub fn cancel(&self, error: i32) {
        // SAFETY: this wrapper owns the future during completion.
        unsafe {
            ffi::fake::FakeFutures.set_error(self.0, error);
        }
    }
    pub fn take(&self) -> Result<Ticket, i32> {
        // SAFETY: the future is live and transfers its owned result reference once.
        unsafe { ffi::fake::take_result(self.0) }.map(Ticket)
    }
}
impl Drop for Future {
    fn drop(&mut self) {
        // SAFETY: this wrapper transfers exactly one owned future reference.
        unsafe {
            ffi::fake::FakeFutures.release(self.0);
        }
    }
}
#[derive(Debug)]
pub(super) struct Ticket(pub *mut ffi::AwsS3BufferTicket);
impl Ticket {
    pub fn node(&self) -> u32 {
        // SAFETY: this wrapper retains the ticket through inspection.
        unsafe { ticket_node(self.0) }.unwrap()
    }
    pub fn buffer(&self) -> *mut u8 {
        // SAFETY: this wrapper retains the ticket through the claim callback.
        unsafe { ticket_claim(self.0) }.buffer
    }
    pub fn capacity(&self) -> usize {
        // SAFETY: this wrapper retains the ticket through its claim callback.
        unsafe { ticket_claim(self.0) }.capacity
    }
    pub fn acquire(&self) -> Self {
        // SAFETY: this live reference permits creating one more owned reference.
        Self(unsafe { ticket_acquire(self.0) })
    }
}
impl Drop for Ticket {
    fn drop(&mut self) {
        // SAFETY: this wrapper transfers one owned ticket reference.
        unsafe {
            ticket_release(self.0);
        }
    }
}

impl TestPool {
    pub fn queued(&self, size: usize, preferred: usize, allocating: bool) -> Future {
        // SAFETY: the test allocator is opaque to the injected future implementation.
        let future = unsafe { ffi::fake::FakeFutures.new_future(self.pool().allocator) };
        // SAFETY: the fresh future has one live caller reference.
        let owned = unsafe { ffi::fake::FakeFutures.acquire(future) };
        let pending = PendingReserve {
            future: owned,
            requested: size,
            preferred_shard: preferred,
            allocating,
            next: ptr::null_mut(),
            ticket: ptr::null_mut(),
            error_code: ffi::AWS_ERROR_SUCCESS,
            ops: Arc::clone(&self.pool().ops),
        };
        let pending = allocate_value(&self.pool().ops, AllocationKind::Pending, pending)
            .unwrap_or_else(|_| panic!("fixture pending allocation"));
        let mut state = self.pool().state.lock();
        // SAFETY: the fresh pending node becomes owned by the exclusively locked queue.
        unsafe {
            if state.pending_tail.is_null() {
                state.pending_head = pending;
            } else {
                (*state.pending_tail).next = pending;
            }
        }
        state.pending_tail = pending;
        state.pending_len += 1;
        Future(future)
    }
    pub fn seed_idle(&self, shard: usize, size: usize) -> *mut u8 {
        let node = self.pool().state.lock().shards[shard].node;
        let mapping = Mapping::allocate(&self.pool().ops, self.pool().futures, size, node).unwrap();
        let pointer = mapping.as_ptr();
        let mut state = self.pool().state.lock();
        let slot = find_free_buffer_slot_locked(&mut state, shard).unwrap();
        // SAFETY: this empty slot is exclusively held under the pool lock.
        unsafe {
            (*slot).mapping = Some(mapping);
            (*slot).state = BufferState::Idle;
        }
        state.allocated_bytes += size;
        pointer
    }
    pub fn accounting(&self) -> (usize, usize, usize) {
        let state = self.pool().state.lock();
        (
            state.allocated_bytes,
            state.reserved_bytes,
            state.forced_bytes,
        )
    }
    pub fn queue_len(&self) -> usize {
        let state = self.pool().state.lock();
        let mut cursor = state.pending_head;
        let mut count = 0;
        while !cursor.is_null() {
            count += 1;
            // SAFETY: every link remains owned by the locked queue.
            cursor = unsafe { (*cursor).next };
        }
        count
    }
    pub fn complete_any_pending(&self) {
        complete_any_pending(self.pointer);
    }
    pub fn claim_allocating(&self, future: &Future, shard: usize, size: usize) -> AllocationClaim {
        let mut state = self.pool().state.lock();
        let slot = find_free_buffer_slot_locked(&mut state, shard).unwrap();
        // SAFETY: the fixture claims this empty slot under the exclusive lock.
        unsafe {
            (*slot).state = BufferState::Allocating;
        }
        state.reserved_bytes += size;
        drop(state);
        AllocationClaim::new(self.pointer, future.0, slot, size, shard, size)
    }
}
pub(super) struct PoolAddress(pub *mut Pool);
// SAFETY: tests retain the pool and use its thread-safe state lock for all inspection.
unsafe impl Send for PoolAddress {}
impl PoolAddress {
    pub fn get(&self) -> &Pool {
        // SAFETY: each test retains its pool owner until the installed hook has run.
        unsafe { &*self.0 }
    }
}
pub(super) struct FutureAddress(pub *mut ffi::AwsFutureS3BufferTicket);
// SAFETY: futures are synchronized and the fixture retains a reference through the closure.
unsafe impl Send for FutureAddress {}
impl FutureAddress {
    pub fn done(&self) -> bool {
        // SAFETY: the fixture retains this borrowed future reference.
        unsafe { ffi::fake::FakeFutures.is_done(self.0) }
    }
    pub fn cancel(&self, error: i32) {
        // SAFETY: the fixture retains this borrowed future reference during completion.
        unsafe {
            ffi::fake::FakeFutures.set_error(self.0, error);
        }
    }
}
