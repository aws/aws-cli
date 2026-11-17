use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Counts {
    pub(crate) allocations: usize,
    pub(crate) requested: usize,
    pub(crate) live: isize,
    pub(crate) peak: isize,
}

impl Counts {
    pub(crate) const ZERO: Self = Self {
        allocations: 0,
        requested: 0,
        live: 0,
        peak: 0,
    };
}

thread_local! {
    // A `const` thread local of a `Copy` value registers no destructor, so
    // reaching it never allocates.
    static COUNTS: Cell<Counts> = const { Cell::new(Counts::ZERO) };
}

fn record(allocated: Option<usize>, freed: usize) {
    let _ = COUNTS.try_with(|counts| {
        let mut next = counts.get();
        if let Some(size) = allocated {
            next.allocations += 1;
            next.requested += size;
            next.live += size as isize;
        }
        next.live -= freed as isize;
        next.peak = next.peak.max(next.live);
        counts.set(next);
    });
}

pub(crate) fn counted<T>(run: impl FnOnce() -> T) -> (T, Counts) {
    let _ = COUNTS.try_with(|counts| counts.set(Counts::ZERO));
    let value = run();
    let counts = COUNTS.try_with(Cell::get).unwrap_or(Counts::ZERO);
    (value, counts)
}

#[derive(Debug)]
struct Counting;

// SAFETY: every method forwards its arguments unchanged to `System`, which
// upholds the `GlobalAlloc` contract; the bookkeeping only updates a
// thread-local `Cell` and never allocates.
unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        record(Some(layout.size()), 0);
        // SAFETY: the caller meets `GlobalAlloc::alloc`'s requirements.
        unsafe { System.alloc(layout) }
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        record(Some(layout.size()), 0);
        // SAFETY: the caller meets `GlobalAlloc::alloc_zeroed`'s requirements.
        unsafe { System.alloc_zeroed(layout) }
    }

    unsafe fn dealloc(&self, block: *mut u8, layout: Layout) {
        record(None, layout.size());
        // SAFETY: `block` came from this allocator, which is `System`, with `layout`.
        unsafe { System.dealloc(block, layout) }
    }

    unsafe fn realloc(&self, block: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        record(Some(size), layout.size());
        // SAFETY: the caller meets `GlobalAlloc::realloc`'s requirements for
        // a block this allocator, which is `System`, returned.
        unsafe { System.realloc(block, layout, size) }
    }
}

#[global_allocator]
static ALLOCATOR: Counting = Counting;
