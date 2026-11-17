use super::super::*;
use std::{alloc::Layout, ptr::NonNull, sync::atomic::AtomicPtr};
/// A backend call the pool makes, which must run outside its lock.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Call {
    Allocate,
    Release,
    Mmap,
    Mbind,
    Munmap,
    Completion,
}
#[derive(Default)]
pub(super) struct ModelOps {
    pub live: AtomicUsize,
    pub mappings: AtomicUsize,
    pub fail_mapping: AtomicBool,
    pub fail_ticket: AtomicBool,
    /// One-shot failures of the next queue node allocation, mapping, and
    /// placement, which the operation model arms.
    pub fail_pending: AtomicBool,
    pub fail_next_mapping: AtomicBool,
    pub fail_placement: AtomicBool,
    /// The page size the pool reads once at creation; zero reads as one.
    pub page: AtomicUsize,
    /// The node `current_node` reports, or none.
    pub node: std::sync::Mutex<Option<u32>>,
    /// The node each mapping, by address, was last placed on.
    pub placed: std::sync::Mutex<std::collections::HashMap<usize, u32>>,
    /// The pool's lock flag, or null for no probe. It points into the
    /// pool's storage, so `release` clears it with the pool.
    pub lock_probe: AtomicPtr<AtomicBool>,
    /// Runs at every backend call, once the probe finds the lock free.
    pub reentry: Option<fn(Call)>,
    #[cfg(test)]
    pub on_map: std::sync::Mutex<Option<Box<dyn FnOnce() + Send>>>,
}
impl std::fmt::Debug for ModelOps {
    fn fmt(&self, out: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        out.debug_struct("ModelOps").finish_non_exhaustive()
    }
}
impl ModelOps {
    fn outside_lock(&self, call: Call) {
        let probe = self.lock_probe.load(Ordering::Acquire);
        // SAFETY: a non-null probe names the lock flag inside the pool's
        // storage, and `release` clears it before that storage is freed.
        if let Some(held) = unsafe { probe.as_ref() } {
            assert!(
                !held.load(Ordering::Acquire),
                "{call:?} ran under the pool lock"
            );
        }
        if let Some(reentry) = self.reentry {
            reentry(call);
        }
    }
}
// SAFETY: storage comes from Rust's matching allocation/deallocation API and is uniquely owned.
unsafe impl AllocationOps for ModelOps {
    fn allocate(&self, kind: AllocationKind, layout: Layout) -> Option<NonNull<u8>> {
        self.outside_lock(Call::Allocate);
        if kind == AllocationKind::Ticket && self.fail_ticket.swap(false, Ordering::SeqCst) {
            return None;
        }
        if kind == AllocationKind::Pending && self.fail_pending.swap(false, Ordering::SeqCst) {
            return None;
        }
        // SAFETY: the caller supplies a nonzero valid layout.
        let pointer = NonNull::new(unsafe { std::alloc::alloc_zeroed(layout) })?;
        self.live.fetch_add(1, Ordering::SeqCst);
        Some(pointer)
    }
    unsafe fn release(&self, kind: AllocationKind, pointer: NonNull<u8>, layout: Layout) {
        self.outside_lock(Call::Release);
        let start = pointer.as_ptr().addr();
        let probe = self.lock_probe.load(Ordering::Acquire).addr();
        if kind == AllocationKind::Pool && (start..start + layout.size()).contains(&probe) {
            self.lock_probe.store(ptr::null_mut(), Ordering::Release);
        }
        self.live.fetch_sub(1, Ordering::SeqCst);
        // SAFETY: caller transfers matching, uniquely owned storage.
        unsafe { std::alloc::dealloc(pointer.as_ptr(), layout) };
    }
    fn mmap(&self, size: usize) -> Result<NonNull<u8>, super::super::super::MappingError> {
        self.outside_lock(Call::Mmap);
        #[cfg(test)]
        {
            let hook = self
                .on_map
                .lock()
                .map_err(|_| super::super::super::MappingError)?
                .take();
            if let Some(hook) = hook {
                hook();
            }
        }
        if self.fail_mapping.load(Ordering::SeqCst)
            || self.fail_next_mapping.swap(false, Ordering::SeqCst)
        {
            return Err(super::super::super::MappingError);
        }
        let layout = Layout::array::<u8>(size).map_err(|_| super::super::super::MappingError)?;
        // SAFETY: model mappings are nonzero and at most a few pages.
        let pointer = NonNull::new(unsafe { std::alloc::alloc_zeroed(layout) })
            .ok_or(super::super::super::MappingError)?;
        self.mappings.fetch_add(1, Ordering::SeqCst);
        Ok(pointer)
    }
    unsafe fn mbind(
        &self,
        pointer: NonNull<u8>,
        _: usize,
        node: u32,
    ) -> Result<(), super::super::super::MappingError> {
        self.outside_lock(Call::Mbind);
        if self.fail_placement.swap(false, Ordering::SeqCst) {
            return Err(super::super::super::MappingError);
        }
        if let Ok(mut placed) = self.placed.lock() {
            placed.insert(pointer.as_ptr().addr(), node);
        }
        Ok(())
    }
    unsafe fn munmap(&self, pointer: NonNull<u8>, size: usize) {
        self.outside_lock(Call::Munmap);
        let Ok(layout) = Layout::array::<u8>(size) else {
            return;
        };
        self.mappings.fetch_sub(1, Ordering::SeqCst);
        // SAFETY: caller transfers this live modeled mapping and its original length.
        unsafe { std::alloc::dealloc(pointer.as_ptr(), layout) };
    }
    fn current_node(&self) -> Option<u32> {
        self.node.lock().ok().and_then(|node| *node)
    }
    fn page_size(&self) -> usize {
        self.page.load(Ordering::SeqCst).max(1)
    }
    fn before_completion(&self) {
        self.outside_lock(Call::Completion);
    }
}

pub(super) struct Harness {
    pub pointer: *mut Pool,
    pub ops: Arc<ModelOps>,
}
// SAFETY: all pool mutations synchronize on its lock; reference drops are atomic.
unsafe impl Send for Harness {}
// SAFETY: shared methods retain the harness-owned pool reference for each callback.
unsafe impl Sync for Harness {}
impl Harness {
    pub fn new(nodes: Vec<u32>, budget: usize, part: usize) -> Self {
        Self::configured(ModelOps::default(), nodes, [part, budget, budget])
    }
    /// A pool over `ops` whose part size, maximum part size and budget are
    /// `sizes`, in that order.
    pub fn configured(ops: ModelOps, nodes: Vec<u32>, sizes: [usize; 3]) -> Self {
        let [part, maximum, budget] = sizes;
        let ops = Arc::new(ops);
        let erased: Arc<dyn AllocationOps> = ops.clone();
        let factory_config = FactoryConfig::new(Config {
            nodes,
            budget_bytes: budget,
        });
        let config = ffi::AwsS3BufferPoolConfig {
            client: ptr::null_mut(),
            part_size: part,
            max_part_size: maximum,
            memory_limit: budget,
        };
        let interface = factory_with_ops(
            NonNull::dangling().as_ptr(),
            config,
            &factory_config,
            erased,
            &FAKE_POOL_VTABLE,
        );
        assert!(!interface.is_null());
        // SAFETY: a successful factory owns a initialized pinned interface.
        let pointer = unsafe { (*interface).implementation.cast() };
        Self { pointer, ops }
    }
    pub fn pool(&self) -> &Pool {
        // SAFETY: this harness retains a pool reference until Drop.
        unsafe { &*self.pointer }
    }
    pub fn reserve(&self, size: usize, can_block: bool) -> Future {
        // SAFETY: this harness retains the interface throughout reserve.
        Future(unsafe {
            pool_reserve(
                ptr::addr_of_mut!((*self.pointer).interface),
                ffi::AwsS3BufferPoolReserveMeta {
                    client: ptr::null_mut(),
                    meta_request: ptr::null_mut(),
                    size,
                    can_block,
                    local_offset: 0,
                },
            )
        })
    }
    /// Releases the harness's pool reference before the harness drops.
    pub fn release_reference(&mut self) {
        release_pool_reference(std::mem::replace(&mut self.pointer, ptr::null_mut()));
    }
    pub fn trim(&self) {
        // SAFETY: this harness retains the interface throughout trim.
        unsafe {
            pool_trim(ptr::addr_of_mut!((*self.pointer).interface));
        }
    }
}
impl Drop for Harness {
    fn drop(&mut self) {
        if !self.pointer.is_null() {
            release_pool_reference(self.pointer);
        }
    }
}

pub(super) struct Future(pub *mut ffi::AwsFutureS3BufferTicket);
impl Future {
    pub fn done(&self) -> bool {
        // SAFETY: this wrapper owns one future reference.
        unsafe { ffi::fake::FakeFutures.is_done(self.0) }
    }
    pub fn cancel(&self, code: i32) {
        // SAFETY: this wrapper owns one future reference.
        unsafe {
            ffi::fake::FakeFutures.set_error(self.0, code);
        }
    }
    pub fn sequence(&self) -> u64 {
        // SAFETY: this wrapper owns one future reference.
        unsafe { ffi::fake::sequence(self.0) }
    }
    pub fn completions(&self) -> usize {
        // SAFETY: this wrapper owns one future reference.
        unsafe { ffi::fake::completions(self.0) }
    }
    pub fn take(&self) -> Result<Ticket, i32> {
        // SAFETY: this wrapper owns a future reference; take moves its result out once.
        unsafe { ffi::fake::take_result(self.0) }.map(Ticket)
    }
}
impl Drop for Future {
    fn drop(&mut self) {
        // SAFETY: this wrapper transfers its sole reference to CRT.
        unsafe {
            ffi::fake::FakeFutures.release(self.0);
        }
    }
}
#[derive(Debug)]
pub(super) struct Ticket(pub *mut ffi::AwsS3BufferTicket);
impl Ticket {
    pub fn acquire(&self) -> Self {
        // SAFETY: this wrapper owns a live reference throughout acquire.
        Self(unsafe { ticket_acquire(self.0) })
    }
    pub fn refs(&self) -> usize {
        // SAFETY: this wrapper retains the live ticket whose count is inspected.
        unsafe {
            (*(*self.0).implementation.cast::<super::super::Ticket>())
                .refs
                .load(Ordering::Acquire)
        }
    }
    pub fn capacity(&self) -> usize {
        // SAFETY: this wrapper owns a live reference throughout claim.
        unsafe { ticket_claim(self.0) }.capacity
    }
    pub fn buffer(&self) -> *mut u8 {
        // SAFETY: this wrapper owns a live reference throughout claim.
        unsafe { ticket_claim(self.0) }.buffer
    }
}
impl Drop for Ticket {
    fn drop(&mut self) {
        // SAFETY: this wrapper transfers its owned reference exactly once.
        unsafe {
            ticket_release(self.0);
        }
    }
}
