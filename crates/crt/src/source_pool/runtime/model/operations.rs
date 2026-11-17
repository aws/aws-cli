//! A pool configuration and an operation sequence the input chooses, driven
//! through the pool's C entry points and checked against the pool's
//! invariants after every operation.
//!
//! The checks are safety properties, not predictions: which buffer a grant
//! reuses or which mapping a trim retires is the pool's choice, but every
//! byte is counted once, no two live tickets share memory, grants that are
//! not forced keep reservation order, and no waiter is left without a ticket
//! whose release drives the queue.
//!
//! The pool calls its backend and completes futures only with its lock free,
//! so any schedule in which another CRT thread runs a whole operation inside
//! one of those gaps runs here on one thread: an armed re-entry lets the
//! input nest one operation into a backend call. What holds mid-operation is
//! checked after the nested one, and what needs the pool at rest when the
//! step returns.
#![expect(
    clippy::expect_used,
    reason = "fuzz assertions stop at the first violated invariant"
)]
use super::super::*;
use super::support::{self, Call, Harness, ModelOps};
use crate::testing::Choices;
use std::cell::{Cell, RefCell};
#[cfg(test)]
mod tests;

/// The size step: part size, maximum part size and budget are one to
/// `UNITS_MAX` of it. It is no multiple of the largest page, so rounding a
/// size up to 4096 bytes can pass the pool's limit and fall back.
const UNIT: usize = 1024;
const UNITS_MAX: usize = 8;
/// The node ids shards draw from. None is below four, the most shards, so
/// no shard's node is a shard index.
const NODES: [u32; 5] = [4, 5, 7, 8, 10];
/// A node no shard has, one of the gaps.
const ABSENT_NODE: u32 = 6;
const PAGE_SIZES: [usize; 3] = [1, 8, 4096];
/// Operations per input, before the drain or destroy that ends it.
const STEPS_MAX: usize = 64;
/// The operations a step chooses among, by index.
const RESERVE: usize = 0;
const CANCEL: usize = 1;
const ACQUIRE: usize = 2;
const RELEASE: usize = 3;
const TRIM: usize = 4;
const ARM: usize = 5;
const SPECIAL_SIZE: usize = 6;
const OPERATIONS: usize = 7;
/// What a nested operation may be: any but `arm`, which sets up the model's
/// backend rather than calling the pool.
const NESTED: [usize; 6] = [RESERVE, CANCEL, ACQUIRE, RELEASE, TRIM, SPECIAL_SIZE];
/// How deep operations nest: a nested operation's backend calls nest none.
const NESTING_DEPTH: usize = 1;
const FAILURES: [Failure; 4] = [
    Failure::Pending,
    Failure::Ticket,
    Failure::Mapping,
    Failure::Placement,
];

/// Drives one pool configuration through an operation sequence and ends it
/// with a drain or a destroy, checking the pool's invariants throughout.
pub fn operations(bytes: &[u8]) {
    operations_from(&mut Choices::new(bytes));
}
fn operations_from(input: &mut Choices<'_>) -> Reached {
    let input = Input(RefCell::new(input));
    let model = Model::new(&input);
    let destroy = input.flag();
    model.check();
    for _ in 0..STEPS_MAX {
        if input.is_empty() {
            break;
        }
        model.step(&input);
    }
    let reached = model.reached();
    if destroy {
        model.destroy(&input);
    } else {
        model.drain(&input);
    }
    reached
}

/// The input behind a shared reference, so a nested operation reads it while
/// the step it nests in runs.
struct Input<'r, 'b>(RefCell<&'r mut Choices<'b>>);
impl Input<'_, '_> {
    fn range(&self, minimum: usize, maximum: usize) -> usize {
        self.0.borrow_mut().range(minimum, maximum)
    }
    fn index(&self, len: usize) -> usize {
        self.0.borrow_mut().index(len)
    }
    fn flag(&self) -> bool {
        self.0.borrow_mut().flag()
    }
    fn is_empty(&self) -> bool {
        self.0.borrow().is_empty()
    }
}

/// The step running, which an armed re-entry nests an operation into. It
/// holds its model and input by shared reference; both change only through
/// cells, so a nested operation may reach them through these pointers.
struct InFlight {
    model: *const Model,
    input: *const Input<'static, 'static>,
    /// The step's operation, which limits what a nested one may be.
    operation: usize,
    depth: Cell<usize>,
}
thread_local! {
    static IN_FLIGHT: Cell<*const InFlight> = const { Cell::new(ptr::null()) };
}
impl Drop for InFlight {
    fn drop(&mut self) {
        IN_FLIGHT.set(ptr::null());
    }
}

/// The model backend's hook: while a re-entry is armed, the input chooses at
/// each backend call of a step whether to nest an operation there.
fn reenter(call: Call) {
    // SAFETY: a non-null pointer names the step running on this thread,
    // which clears it before its frame ends.
    let Some(in_flight) = (unsafe { IN_FLIGHT.get().as_ref() }) else {
        return;
    };
    // SAFETY: the step borrows both for its whole frame, which outlives this
    // call; their lifetimes are erased only for the duration of the step.
    let (model, input) = unsafe { (&*in_flight.model, &*in_flight.input) };
    let depth = in_flight.depth.get();
    if depth >= NESTING_DEPTH || !model.reentry.get() || !input.flag() {
        return;
    }
    model.reentry.set(false);
    in_flight.depth.set(depth + 1);
    model.nest(call, in_flight.operation, input);
    in_flight.depth.set(depth);
}

/// What an input reached before its end, which named scripts assert.
#[derive(Debug, PartialEq, Eq)]
struct Reached {
    nested: Vec<Nested>,
    trims: u64,
    steals: u64,
    forced: u64,
    queued: u64,
    mappings: u64,
    grants: u64,
    failures: usize,
}

/// A nested operation: the backend call it ran in, which operation it was,
/// and whether the queue head's mapping was in flight.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Nested {
    call: Call,
    operation: usize,
    head_allocating: bool,
}

/// One backend call the model can fail once.
#[derive(Clone, Copy)]
enum Failure {
    Pending,
    Ticket,
    Mapping,
    Placement,
}
fn failure_flag(ops: &ModelOps, failure: Failure) -> &AtomicBool {
    match failure {
        Failure::Pending => &ops.fail_pending,
        Failure::Ticket => &ops.fail_ticket,
        Failure::Mapping => &ops.fail_next_mapping,
        Failure::Placement => &ops.fail_placement,
    }
}

struct Model {
    harness: Harness,
    ops: Arc<ModelOps>,
    /// Backend allocations of the pool, its shard table and its slot tables.
    storage: usize,
    nodes: Vec<u32>,
    /// The configured part size, and the largest size the configuration
    /// supports: the maximum part size capped at the budget, raised to the
    /// part size.
    part: usize,
    limit: usize,
    budget: usize,
    book: RefCell<Book>,
    /// Whether a re-entry is armed and no operation has nested yet.
    reentry: Cell<bool>,
}

/// The model's futures and ticket references.
struct Book {
    /// The pool, alive while the harness or a held ticket has a reference.
    pool: *mut Pool,
    reservations: Vec<Reservation>,
    held: Vec<Held>,
    serial: u64,
    /// The failure armed and not yet consumed.
    armed: Option<Failure>,
    failures: usize,
    nested: Vec<Nested>,
}

struct Reservation {
    future: support::Future,
    size: usize,
    can_block: bool,
    supported: bool,
    /// The node a forced ticket must carry, when the reservation fixes one.
    forced_node: Option<u32>,
    canceled: Option<i32>,
    collected: bool,
    /// The book positions of the waiters the queue held when the
    /// reservation was made, which a pooled grant may not pass.
    ahead: Vec<usize>,
    /// When a pooled grant to it was done.
    pooled: Option<u64>,
    /// Canceled while the pool may have been delivering it, which leaves the
    /// pool's completion to the future to ignore.
    raced: bool,
}

/// One ticket reference, with the serial its buffer is stamped with.
struct Held {
    ticket: support::Ticket,
    serial: u64,
}

impl Model {
    fn new(input: &Input<'_, '_>) -> Self {
        let mut free = NODES.to_vec();
        let shards = input.range(1, 4);
        let nodes: Vec<u32> = (0..shards)
            .map(|_| free.remove(input.index(free.len())))
            .collect();
        let budget = input.range(1, UNITS_MAX);
        // A part above the budget is ruled out of the model.
        let part = input.range(1, budget);
        let maximum = input.range(1, UNITS_MAX);
        let ops = ModelOps {
            page: AtomicUsize::new(PAGE_SIZES[input.index(PAGE_SIZES.len())]),
            reentry: Some(reenter),
            ..ModelOps::default()
        };
        let sizes = [part * UNIT, maximum * UNIT, budget * UNIT];
        let harness = Harness::configured(ops, nodes.clone(), sizes);
        let ops = Arc::clone(&harness.ops);
        // SAFETY: the new pool is live; this takes only its lock flag's address.
        let held = unsafe { &raw const (*harness.pointer).state.held };
        ops.lock_probe.store(held.cast_mut(), Ordering::Release);
        let storage = ops.live.load(Ordering::SeqCst);
        let book = Book {
            pool: harness.pointer,
            reservations: Vec::new(),
            held: Vec::new(),
            serial: 0,
            armed: None,
            failures: 0,
            nested: Vec::new(),
        };
        Self {
            harness,
            ops,
            storage,
            nodes,
            part: sizes[0],
            limit: sizes[1].min(sizes[2]).max(sizes[0]),
            budget: sizes[2],
            book: RefCell::new(book),
            reentry: Cell::new(false),
        }
    }

    fn pool(&self) -> &Pool {
        // SAFETY: the harness or a held ticket keeps a pool reference
        // whenever the model checks the pool.
        unsafe { &*self.book.borrow().pool }
    }

    fn supported(&self, size: usize) -> bool {
        (1..=self.limit).contains(&size)
    }

    fn step(&self, input: &Input<'_, '_>) {
        let operation = input.index(OPERATIONS);
        let in_flight = InFlight {
            model: self,
            input: ptr::from_ref(input).cast(),
            operation,
            depth: Cell::new(0),
        };
        IN_FLIGHT.set(&raw const in_flight);
        self.operate(operation, input);
        drop(in_flight);
        self.settle();
    }

    fn operate(&self, operation: usize, input: &Input<'_, '_>) {
        match operation {
            RESERVE => self.reserve(input),
            CANCEL => drop(self.book.borrow_mut().cancel(input)),
            ACQUIRE => self.book.borrow_mut().acquire(input),
            RELEASE => self.release(input),
            TRIM => self.harness.trim(),
            ARM => self.arm(input),
            _ => self.special_size(input),
        }
    }

    /// Runs one nested operation, as another thread could, in a backend call
    /// of a step running `outer`, then checks what holds mid-operation.
    fn nest(&self, call: Call, outer: usize, input: &Input<'_, '_>) {
        let operation = NESTED[input.index(NESTED.len())];
        // The book orders reservations as their reserve calls return, so it
        // cannot order one reservation nested in another.
        if operation == RESERVE && outer == RESERVE {
            return;
        }
        let head_allocating = {
            let head = self.pool().state.lock().pending_head;
            // SAFETY: the queue head is live while the queue holds it, and
            // only the lock holder writes `allocating`, whose lock is free.
            !head.is_null() && unsafe { (*head).allocating }
        };
        // The current node is the outer thread's again once it resumes.
        let node = *self.ops.node.lock().expect("model node");
        match operation {
            CANCEL => {
                if let Some(canceled) = self.book.borrow_mut().cancel(input) {
                    canceled.raced = true;
                }
            }
            _ => self.operate(operation, input),
        }
        *self.ops.node.lock().expect("model node") = node;
        let pool = self.pool();
        let mut book = self.book.borrow_mut();
        book.nested.push(Nested {
            call,
            operation,
            head_allocating,
        });
        book.collect(&self.ops);
        book.ticket_totals(&pool.state.lock(), &self.nodes, &self.ops);
        book.assert_completions();
    }

    fn settle(&self) {
        self.book.borrow_mut().collect(&self.ops);
        self.check();
    }

    /// Arms one failure, or past the failures a re-entry, in place of what
    /// was armed.
    fn arm(&self, input: &Input<'_, '_>) {
        let mut book = self.book.borrow_mut();
        if let Some(armed) = book.armed.take() {
            failure_flag(&self.ops, armed).store(false, Ordering::SeqCst);
        }
        let failure = FAILURES.get(input.index(FAILURES.len() + 1)).copied();
        if let Some(failure) = failure {
            failure_flag(&self.ops, failure).store(true, Ordering::SeqCst);
        }
        book.armed = failure;
        self.reentry.set(failure.is_none());
    }

    /// Releases a ticket reference outside the book's borrow, since the
    /// release may call the backend, which a nested operation can enter.
    fn release(&self, input: &Input<'_, '_>) {
        let held = self.book.borrow_mut().release(input);
        drop(held);
    }

    /// Request sizes at the pool's edges: one byte, either side of the part
    /// size, and the maximum buffer size and one past it.
    fn edges(&self) -> [usize; 6] {
        let (part, limit) = (self.part, self.limit);
        [1, part - 1, part, part + 1, limit, limit + 1]
    }

    fn interface(&self) -> *mut ffi::AwsS3BufferPool {
        // SAFETY: the harness retains its pool reference.
        unsafe { ptr::addr_of_mut!((*self.harness.pointer).interface) }
    }

    fn reserve(&self, input: &Input<'_, '_>) {
        let edges = self.edges();
        let size = match edges.get(input.index(edges.len() + 1)) {
            Some(size) => *size,
            None => self.derived(edges[input.index(edges.len())]),
        };
        let can_block = input.flag();
        let node = match input.index(3) {
            0 => None,
            1 => Some(self.nodes[input.index(self.nodes.len())]),
            _ => Some(ABSENT_NODE),
        };
        *self.ops.node.lock().expect("model node") = node;
        let ahead = queue(&self.pool().state.lock(), &self.book.borrow().reservations).0;
        let future = self.harness.reserve(size, can_block);
        assert!(!can_block || future.done(), "a blocking reservation waited");
        // A pool of several shards prefers the current node's, if it has one.
        let forced_node = match self.nodes[..] {
            [only] => Some(only),
            _ => node.filter(|node| self.nodes.contains(node)),
        };
        let supported = self.supported(size);
        self.book.borrow_mut().reservations.push(Reservation {
            future,
            size,
            can_block,
            supported,
            forced_node,
            canceled: None,
            collected: false,
            ahead,
            pooled: None,
            raced: false,
        });
    }

    /// The size `pool_derive_aligned_buffer_size` gives `size`, which the
    /// pool must accept.
    fn derived(&self, size: usize) -> usize {
        // SAFETY: the harness retains the interface for this call.
        let derived = unsafe { pool_derive_aligned_buffer_size(self.interface(), size as u64) };
        let derived = usize::try_from(derived).expect("derived size fits a usize");
        assert!(self.supported(derived));
        derived
    }

    fn special_size(&self, input: &Input<'_, '_>) {
        let size = self.edges()[input.index(6)];
        let interface = self.interface();
        if input.flag() {
            // SAFETY: the harness retains the interface for this call.
            let code = unsafe { pool_add_special_size(interface, size) };
            assert_eq!(code == ffi::AWS_OP_SUCCESS, self.supported(size));
        } else {
            // SAFETY: the harness retains the interface for this call.
            unsafe { pool_release_special_size(interface, size) };
        }
    }

    fn reached(&self) -> Reached {
        let pool = self.pool();
        let diagnostics = &pool.diagnostics;
        let book = self.book.borrow();
        Reached {
            nested: book.nested.clone(),
            trims: diagnostics.trims.load(Ordering::Relaxed),
            steals: pool.state.lock().cross_shard_steal_count,
            forced: diagnostics.forced_grants.load(Ordering::Relaxed),
            queued: diagnostics.queued_grants.load(Ordering::Relaxed),
            mappings: diagnostics.allocations.load(Ordering::Relaxed),
            grants: book.serial,
            failures: book.failures,
        }
    }

    /// Releases every ticket reference, and those the releases grant, then
    /// checks the idle pool trims to nothing and frees all it took.
    fn drain(self, input: &Input<'_, '_>) {
        while !self.book.borrow().held.is_empty() {
            self.release(input);
            self.settle();
        }
        self.harness.trim();
        self.settle();
        self.book.borrow().assert_completed();
        assert_eq!(self.ops.mappings.load(Ordering::SeqCst), 0);
        assert_eq!(self.ops.live.load(Ordering::SeqCst), self.storage);
        let ops = Arc::clone(&self.ops);
        drop(self);
        assert_eq!(ops.live.load(Ordering::SeqCst), 0);
    }

    /// Releases the model's pool reference first, so the pool lives on in
    /// its tickets, then releases them; the last release destroys the pool.
    /// Every ticket holds a pool reference, so the pool is checked after
    /// each release that leaves the model a ticket.
    fn destroy(mut self, input: &Input<'_, '_>) {
        self.harness.release_reference();
        while !self.book.borrow().held.is_empty() {
            self.release(input);
            self.book.borrow_mut().collect(&self.ops);
            if !self.book.borrow().held.is_empty() {
                self.check();
            }
        }
        self.book.borrow().assert_completed();
        assert_eq!(self.ops.live.load(Ordering::SeqCst), 0);
        assert_eq!(self.ops.mappings.load(Ordering::SeqCst), 0);
    }

    /// The invariants of a pool at rest.
    fn check(&self) {
        let state = self.pool().state.lock();
        let book = self.book.borrow();
        assert_eq!(state.reserved_bytes, 0, "a claim is in flight at rest");
        let queued = check_queue(&state, &book.reservations);
        let slots = slot_totals(&state, &self.ops);
        let tickets = book.ticket_totals(&state, &self.nodes, &self.ops);
        assert_eq!(state.allocated_bytes, slots.bytes);
        // Mapped and claimed bytes stay within the budget; forced ones do not count.
        assert!(
            slots.bytes + state.reserved_bytes <= self.budget,
            "over budget"
        );
        assert_eq!(state.forced_bytes, tickets.forced_bytes);
        assert_eq!(
            slots.in_use, tickets.pooled,
            "an in-use slot without its ticket"
        );
        let live = self.ops.live.load(Ordering::SeqCst);
        assert_eq!(live, self.storage + queued + tickets.distinct);
        let mappings = self.ops.mappings.load(Ordering::SeqCst);
        assert_eq!(mappings, slots.mapped + tickets.forced);
        book.assert_completions();
        let waiting = book.reservations.iter().any(|r| !r.future.done());
        assert!(
            !waiting || tickets.pooled != 0,
            "a waiter no release will drive"
        );
    }
}

/// The book positions of the futures the FIFO holds, in its order, and its
/// last node.
fn queue(state: &State, reservations: &[Reservation]) -> (Vec<usize>, *mut PendingReserve) {
    let mut positions = Vec::new();
    let (mut node, mut last) = (state.pending_head, ptr::null_mut());
    while !node.is_null() {
        assert!(
            positions.len() < reservations.len(),
            "the queue repeats a node"
        );
        // SAFETY: the caller holds the pool lock, under which the queue owns its nodes.
        let pending = unsafe { &*node };
        let position = reservations
            .iter()
            .position(|r| r.future.0 == pending.future);
        positions.push(position.expect("a queued future is a reservation"));
        (last, node) = (node, pending.next);
    }
    (positions, last)
}
/// Whether the FIFO holds `future`.
fn queued(state: &State, future: *mut ffi::AwsFutureS3BufferTicket) -> bool {
    let mut node = state.pending_head;
    while !node.is_null() {
        // SAFETY: the caller holds the pool lock, under which the queue owns its nodes.
        let pending = unsafe { &*node };
        if pending.future == future {
            return true;
        }
        node = pending.next;
    }
    false
}
/// Walks the FIFO and returns its length. It holds every waiting
/// reservation, in the order the model made them.
fn check_queue(state: &State, reservations: &[Reservation]) -> usize {
    let (positions, last) = queue(state, reservations);
    assert_eq!(last, state.pending_tail);
    assert_eq!(positions.len(), state.pending_len);
    assert!(positions.is_sorted_by(|older, younger| older < younger));
    for (index, reservation) in reservations.iter().enumerate() {
        assert!(reservation.future.done() || positions.contains(&index));
    }
    positions.len()
}

/// What the slot tables hold.
#[derive(Default)]
struct Slots {
    mapped: usize,
    bytes: usize,
    in_use: usize,
}
fn slot_totals(state: &State, ops: &ModelOps) -> Slots {
    let mut totals = Slots::default();
    for (index, shard) in state.shards.iter().enumerate() {
        for cell in shard.slots.as_ref().expect("slot table").iter() {
            // SAFETY: the caller holds the pool lock.
            let slot = unsafe { &*cell.get() };
            assert_eq!((slot.node, slot.node_index), (shard.node, index));
            assert!(slot.state != BufferState::Allocating);
            assert_eq!(slot.mapping.is_some(), slot.state != BufferState::Empty);
            if let Some(mapping) = &slot.mapping {
                assert_eq!(placement(ops, mapping), Some(shard.node));
            }
            totals.mapped += usize::from(slot.mapping.is_some());
            totals.bytes += slot.mapping.as_ref().map_or(0, Mapping::len);
            totals.in_use += usize::from(slot.state == BufferState::InUse);
        }
    }
    totals
}

/// What the model's live tickets hold, each ticket counted once.
#[derive(Default)]
struct Tickets {
    distinct: usize,
    pooled: usize,
    forced: usize,
    forced_bytes: usize,
}

/// The node the backend placed `mapping` on.
fn placement(ops: &ModelOps, mapping: &Mapping) -> Option<u32> {
    let placed = ops.placed.lock().expect("model placements");
    placed.get(&mapping.as_ptr().addr()).copied()
}

/// The mapping behind a live ticket's buffer, which the buffer lies in.
fn buffer_mapping<'a>(state: &'a State, ticket: &'a Ticket) -> &'a Mapping {
    let mapping = match &ticket.backing {
        TicketBacking::Pooled(slot) => pooled_mapping(state, *slot, ticket.node),
        TicketBacking::Forced(mapping) => mapping.as_ref().expect("forced mapping"),
    };
    assert_eq!(ticket.pointer, mapping.as_ptr());
    assert!(ticket.requested <= mapping.len());
    mapping
}

/// The pool's ticket behind a held reference.
fn inner(ticket: &support::Ticket) -> &Ticket {
    // SAFETY: the held reference keeps the ticket alive; its fields other
    // than the count are fixed once it is issued.
    unsafe { &*(*ticket.0).implementation.cast::<Ticket>() }
}

/// The in-use slot of one of `state`'s tables that backs a pooled ticket.
fn pooled_mapping(state: &State, slot: *mut Buffer, node: u32) -> &Mapping {
    let owned = state.shards.iter().any(|shard| {
        let cells = shard.slots.as_ref().expect("slot table");
        cells.iter().any(|cell| cell.get() == slot)
    });
    assert!(owned, "a pooled ticket's slot is not the pool's");
    // SAFETY: the slot is in one of `state`'s tables, under the caller's lock.
    let slot = unsafe { &*slot };
    assert!(slot.state == BufferState::InUse);
    assert_eq!(slot.node, node);
    slot.mapping.as_ref().expect("in-use slot mapping")
}

/// The bytes a stamp covers: a buffer's first eight and its last.
fn stamp_offsets(capacity: usize) -> impl Iterator<Item = usize> {
    (0..capacity.min(8)).chain([capacity - 1])
}
fn stamp(ticket: &support::Ticket, serial: u64) {
    let (buffer, bytes) = (ticket.buffer(), serial.to_le_bytes());
    for offset in stamp_offsets(ticket.capacity()) {
        // SAFETY: a live ticket's holder owns `capacity` bytes at its buffer.
        unsafe { buffer.add(offset).write(bytes[offset % 8]) };
    }
}
fn assert_stamped(held: &Held) {
    let (buffer, bytes) = (held.ticket.buffer(), held.serial.to_le_bytes());
    for offset in stamp_offsets(held.ticket.capacity()) {
        // SAFETY: the ticket is live, so its buffer stays readable.
        let byte = unsafe { buffer.add(offset).read() };
        assert_eq!(
            byte,
            bytes[offset % 8],
            "another ticket wrote ticket {}",
            held.serial
        );
    }
}

/// No two live buffers overlap.
fn assert_disjoint(mut buffers: Vec<(usize, usize)>) {
    buffers.sort_unstable();
    for pair in buffers.windows(2) {
        assert!(
            pair[0].0 + pair[0].1 <= pair[1].0,
            "two live tickets share bytes"
        );
    }
}

impl Book {
    fn cancel(&mut self, input: &Input<'_, '_>) -> Option<&mut Reservation> {
        let waiting: Vec<_> = (0..self.reservations.len())
            .filter(|index| !self.reservations[*index].future.done())
            .collect();
        if waiting.is_empty() {
            return None;
        }
        let reservation = &mut self.reservations[waiting[input.index(waiting.len())]];
        let code = if input.flag() {
            ffi::AWS_ERROR_OOM
        } else {
            ffi::AWS_ERROR_S3_CANCELED
        };
        reservation.future.cancel(code);
        reservation.canceled = Some(code);
        Some(reservation)
    }

    fn acquire(&mut self, input: &Input<'_, '_>) {
        if self.held.is_empty() {
            return;
        }
        let held = &self.held[input.index(self.held.len())];
        let copy = Held {
            ticket: held.ticket.acquire(),
            serial: held.serial,
        };
        self.held.push(copy);
    }

    /// Takes a ticket reference out of the book for the caller to release.
    fn release(&mut self, input: &Input<'_, '_>) -> Option<Held> {
        if self.held.is_empty() {
            return None;
        }
        let held = self.held.remove(input.index(self.held.len()));
        if held.ticket.refs() == 1 {
            assert_stamped(&held);
        }
        Some(held)
    }

    /// Takes each newly completed future's result. An armed failure the
    /// operation consumed fails exactly one reservation; nothing else fails
    /// a reservation the model did not cancel and the pool supports.
    fn collect(&mut self, ops: &ModelOps) {
        let consumed = self
            .armed
            .take_if(|armed| !failure_flag(ops, *armed).load(Ordering::SeqCst));
        let mut unexplained = 0;
        for index in 0..self.reservations.len() {
            let reservation = &self.reservations[index];
            if reservation.collected || !reservation.future.done() {
                continue;
            }
            match reservation.future.take() {
                Ok(ticket) => self.issue(index, ticket),
                Err(code) => unexplained += usize::from(self.unexplained(index, code)),
            }
            self.reservations[index].collected = true;
        }
        assert_eq!(unexplained, usize::from(consumed.is_some()));
        self.failures += unexplained;
    }

    fn issue(&mut self, index: usize, ticket: support::Ticket) {
        let reservation = &self.reservations[index];
        assert!(reservation.supported, "a ticket for an unsupported size");
        assert_eq!(ticket.capacity(), reservation.size);
        let issued = inner(&ticket);
        // SAFETY: the new ticket holds a pool reference.
        let state = unsafe { &*self.pool }.state.lock();
        buffer_mapping(&state, issued);
        if matches!(issued.backing, TicketBacking::Pooled(_)) {
            self.reservations[index].pooled = Some(self.assert_grant_order(&state, index));
        } else {
            assert!(reservation.can_block, "a forced ticket without can_block");
            if let Some(node) = reservation.forced_node {
                assert_eq!(issued.node, node, "a forced ticket left the current node");
            }
        }
        drop(state);
        self.serial += 1;
        stamp(&ticket, self.serial);
        self.held.push(Held {
            ticket,
            serial: self.serial,
        });
    }

    /// A pooled grant passes no waiter the queue held when the reservation
    /// was made: at rest every older one still waiting, mid-operation not
    /// those being delivered. Each must be done, or out of the queue: one
    /// another operation is still delivering was granted first. Returns when
    /// the grant was done.
    fn assert_grant_order(&self, state: &State, index: usize) -> u64 {
        let sequence = self.reservations[index].future.sequence();
        for waiter in &self.reservations[index].ahead {
            let waiter = &self.reservations[*waiter];
            let delivering = !queued(state, waiter.future.0);
            assert!(
                waiter.future.done() || delivering,
                "a grant passed a waiter"
            );
            assert!(
                waiter.pooled.is_none_or(|done| done < sequence),
                "pooled grants out of order"
            );
        }
        sequence
    }

    /// Whether an error has no cause the model knows of: a cancel, or a
    /// size the pool does not support.
    fn unexplained(&self, index: usize, code: i32) -> bool {
        let reservation = &self.reservations[index];
        if let Some(canceled) = reservation.canceled {
            assert_eq!(code, canceled);
            return false;
        }
        if !reservation.supported {
            assert_eq!(code, ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED);
            return false;
        }
        let failure = [
            ffi::AWS_ERROR_OOM,
            ffi::AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED,
        ];
        assert!(failure.contains(&code), "unexpected error {code}");
        true
    }

    /// A done future was completed once, and a waiting one never, besides
    /// the pool's completion of one canceled as it was delivered.
    fn assert_completions(&self) {
        for reservation in &self.reservations {
            let done = usize::from(reservation.future.done());
            let completions = reservation.future.completions();
            let raced = usize::from(reservation.raced && completions == 2);
            assert_eq!(completions, done + raced, "a second completion");
        }
    }

    /// Every future was completed exactly once, as `assert_completions` counts.
    fn assert_completed(&self) {
        assert!(self.reservations.iter().all(|r| r.future.done()));
        self.assert_completions();
    }

    /// Checks every live ticket's buffer, its backing, and its reference
    /// count, and totals what the tickets hold.
    fn ticket_totals(&self, state: &State, nodes: &[u32], ops: &ModelOps) -> Tickets {
        let mut totals = Tickets::default();
        let (mut buffers, mut slots) = (Vec::new(), Vec::new());
        for (index, held) in self.held.iter().enumerate() {
            let same = |other: &&Held| other.ticket.0 == held.ticket.0;
            if self.held[..index].iter().any(|other| same(&other)) {
                continue;
            }
            assert_eq!(held.ticket.refs(), self.held.iter().filter(same).count());
            let ticket = inner(&held.ticket);
            let mapping = buffer_mapping(state, ticket);
            match ticket.backing {
                TicketBacking::Pooled(slot) => slots.push(slot),
                TicketBacking::Forced(_) => {
                    totals.forced_bytes += mapping.len();
                    assert!(nodes.contains(&ticket.node));
                    assert_eq!(placement(ops, mapping), Some(ticket.node));
                }
            }
            assert_stamped(held);
            buffers.push((ticket.pointer.addr(), ticket.requested));
        }
        totals.distinct = buffers.len();
        totals.pooled = slots.len();
        totals.forced = totals.distinct - totals.pooled;
        slots.sort_unstable();
        slots.dedup();
        assert_eq!(slots.len(), totals.pooled, "two tickets own one slot");
        assert_disjoint(buffers);
        totals
    }
}
