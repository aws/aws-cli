use super::fake::{self, FakeFutures};
use super::{
    AwsAllocator, AwsFutureS3BufferTicket, AwsS3BufferTicket, AwsS3BufferTicketVtable, CrtFutures,
    FutureOps,
};
use std::ffi::c_int;
use std::ptr;
use std::sync::atomic::{AtomicUsize, Ordering};

const ERROR: c_int = crt_sys::AWS_ERROR_S3_CANCELED;

#[repr(C)]
struct Counted {
    interface: AwsS3BufferTicket,
    releases: AtomicUsize,
}

static COUNTED: AwsS3BufferTicketVtable = AwsS3BufferTicketVtable {
    claim: None,
    acquire: None,
    release: Some(release_counted),
};

unsafe extern "C" fn release_counted(ticket: *mut AwsS3BufferTicket) -> *mut AwsS3BufferTicket {
    // SAFETY: a ticket with this vtable is the first field of a live
    // `Counted`, and its pointer covers the whole `Counted`.
    unsafe {
        (*ticket.cast::<Counted>())
            .releases
            .fetch_add(1, Ordering::SeqCst);
    }
    ptr::null_mut()
}

impl Counted {
    fn new() -> Box<Self> {
        Box::new(Self {
            interface: AwsS3BufferTicket {
                vtable: ptr::from_ref(&COUNTED).cast_mut(),
                // SAFETY: an all-zero reference count is a valid C value; the
                // vtable's release means nothing reads it.
                ref_count: unsafe { std::mem::zeroed() },
                implementation: ptr::null_mut(),
            },
            releases: AtomicUsize::new(0),
        })
    }

    fn ticket(self: &mut Box<Self>) -> *mut AwsS3BufferTicket {
        ptr::from_mut(&mut **self).cast()
    }
}

#[derive(Clone, Copy, Debug)]
enum Step {
    Acquire,
    Release,
    Result(usize),
    Error,
}

struct Implementation<'a> {
    futures: &'a dyn FutureOps,
    allocator: *mut AwsAllocator,
    error: unsafe fn(*const AwsFutureS3BufferTicket) -> c_int,
}

fn observe(implementation: &Implementation<'_>, steps: &[Step]) -> Vec<String> {
    let futures = implementation.futures;
    let mut tickets = [Counted::new(), Counted::new()];
    // SAFETY: the allocator outlives the future, which the steps release.
    let future = unsafe { futures.new_future(implementation.allocator) };
    assert!(!future.is_null());
    let mut references = 1;
    let mut seen = Vec::new();
    let mut error = None;
    for step in steps {
        // SAFETY: each step holds a reference to the future, the moved
        // ticket is the step's own, and a release gives one reference back.
        unsafe {
            match *step {
                Step::Acquire => {
                    assert_eq!(futures.acquire(future), future);
                    references += 1;
                }
                Step::Release => {
                    assert!(futures.release(future).is_null());
                    references -= 1;
                }
                Step::Result(index) => {
                    let mut ticket = tickets[index].ticket();
                    futures.set_result_by_move(future, &mut ticket);
                    assert!(ticket.is_null(), "the move takes the ticket");
                }
                Step::Error => futures.set_error(future, ERROR),
            }
            if references > 0 && futures.is_done(future) {
                error = Some((implementation.error)(future));
            }
        }
        let releases: Vec<_> = tickets
            .iter()
            .map(|ticket| ticket.releases.load(Ordering::SeqCst))
            .collect();
        seen.push(format!("{step:?}: releases {releases:?}"));
    }
    assert_eq!(references, 0, "every sequence releases the future");
    seen.push(format!("error {error:?}"));
    seen
}

/// # Safety
/// `future` is a live, completed CRT future the caller holds a reference to.
unsafe fn crt_error(future: *const AwsFutureS3BufferTicket) -> c_int {
    // SAFETY: as the caller guarantees.
    unsafe { crt_sys::aws_future_s3_buffer_ticket_get_error(future) }
}

fn crt() -> (crate::runtime::Library, Implementation<'static>) {
    let library = crate::runtime::Library::acquire();
    let implementation = Implementation {
        futures: &CrtFutures,
        // SAFETY: the CRT's allocator is process-global.
        allocator: unsafe { crt_sys::rust_crt_allocator() },
        error: crt_error,
    };
    (library, implementation)
}

#[test]
fn fake_futures_follow_the_crts_completion_and_release_rules() {
    let (_library, crt) = crt();
    let fake = Implementation {
        futures: &FakeFutures,
        allocator: ptr::null_mut(),
        error: fake::error,
    };
    for steps in [
        &[Step::Result(0), Step::Release][..],
        &[Step::Error, Step::Result(0), Step::Release],
        &[Step::Result(0), Step::Result(1), Step::Release],
        &[Step::Result(0), Step::Error, Step::Release],
        &[Step::Acquire, Step::Result(0), Step::Release, Step::Release],
        &[Step::Acquire, Step::Release, Step::Error, Step::Release],
    ] {
        assert_eq!(observe(&fake, steps), observe(&crt, steps), "{steps:?}");
    }
}

#[test]
fn fake_futures_raise_the_error_the_crt_reports_last() {
    let _library = crate::runtime::Library::acquire();
    CrtFutures.raise_error(ERROR);
    FakeFutures.raise_error(ERROR);
    // SAFETY: this reads only the calling thread's CRT error.
    assert_eq!(unsafe { crt_sys::rust_crt_last_error() }, ERROR);
    assert_eq!(fake::last_error(), ERROR);
}
