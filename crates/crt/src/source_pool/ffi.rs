use std::ffi::c_int;

pub(super) use crt_sys::{
    AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED, AWS_ERROR_S3_CANCELED,
    AWS_ERROR_S3_PART_SIZE_EXCEEDS_MEMORY_LIMIT, AWS_OP_SUCCESS, AwsAllocator, AwsByteBuf,
    AwsFutureS3BufferTicket, AwsS3BufferPool, AwsS3BufferPoolConfig, AwsS3BufferPoolReserveMeta,
    AwsS3BufferPoolVtable, AwsS3BufferTicket, AwsS3BufferTicketVtable,
};
pub(super) const AWS_ERROR_SUCCESS: i32 = 0;
pub(super) const AWS_ERROR_OOM: i32 = 1;
pub(super) const AWS_ERROR_INVALID_ARGUMENT: i32 = 34;

/// # Safety
/// Implementations keep aws-c-common's future rules: `new_future` returns one
/// reference, `acquire` adds one, and `release` drops one, freeing the future
/// and releasing its ticket with the last. The first completion wins; a
/// ticket moved into a future that is already done is released. Every
/// operation may be called from any CRT thread.
pub(super) unsafe trait FutureOps: Sync {
    /// # Safety
    /// `allocator` must outlive the future.
    unsafe fn new_future(&self, allocator: *mut AwsAllocator) -> *mut AwsFutureS3BufferTicket;
    /// # Safety
    /// The caller holds a live reference to `future`.
    unsafe fn acquire(&self, future: *mut AwsFutureS3BufferTicket) -> *mut AwsFutureS3BufferTicket;
    /// # Safety
    /// The caller transfers one live reference to `future`.
    unsafe fn release(&self, future: *mut AwsFutureS3BufferTicket) -> *mut AwsFutureS3BufferTicket;
    /// # Safety
    /// The caller holds a reference to `future` and owns the ticket reference.
    unsafe fn set_result_by_move(
        &self,
        future: *mut AwsFutureS3BufferTicket,
        ticket: *mut *mut AwsS3BufferTicket,
    );
    /// # Safety
    /// The caller holds a reference to `future`.
    unsafe fn set_error(&self, future: *mut AwsFutureS3BufferTicket, error: c_int);
    /// # Safety
    /// The caller holds a reference to `future`.
    unsafe fn is_done(&self, future: *const AwsFutureS3BufferTicket) -> bool;
    fn raise_error(&self, error: c_int);
}

#[derive(Debug)]
pub(super) struct CrtFutures;

// SAFETY: each operation is the aws-c-common function that defines the rules.
unsafe impl FutureOps for CrtFutures {
    unsafe fn new_future(&self, allocator: *mut AwsAllocator) -> *mut AwsFutureS3BufferTicket {
        // SAFETY: the caller guarantees the allocator outlives the future.
        unsafe { crt_sys::aws_future_s3_buffer_ticket_new(allocator) }
    }
    unsafe fn acquire(&self, future: *mut AwsFutureS3BufferTicket) -> *mut AwsFutureS3BufferTicket {
        // SAFETY: the caller holds a live reference.
        unsafe { crt_sys::aws_future_s3_buffer_ticket_acquire(future) }
    }
    unsafe fn release(&self, future: *mut AwsFutureS3BufferTicket) -> *mut AwsFutureS3BufferTicket {
        // SAFETY: the caller transfers one live reference.
        unsafe { crt_sys::aws_future_s3_buffer_ticket_release(future) }
    }
    unsafe fn set_result_by_move(
        &self,
        future: *mut AwsFutureS3BufferTicket,
        ticket: *mut *mut AwsS3BufferTicket,
    ) {
        // SAFETY: the caller holds the future and owns the moved ticket.
        unsafe { crt_sys::aws_future_s3_buffer_ticket_set_result_by_move(future, ticket) }
    }
    unsafe fn set_error(&self, future: *mut AwsFutureS3BufferTicket, error: c_int) {
        // SAFETY: the caller holds a reference to the future.
        unsafe { crt_sys::aws_future_s3_buffer_ticket_set_error(future, error) }
    }
    unsafe fn is_done(&self, future: *const AwsFutureS3BufferTicket) -> bool {
        // SAFETY: the caller holds a reference to the future.
        unsafe { crt_sys::aws_future_s3_buffer_ticket_is_done(future) }
    }
    fn raise_error(&self, error: c_int) {
        // SAFETY: this only sets the calling thread's CRT error.
        unsafe {
            crt_sys::aws_raise_error(error);
        }
    }
}

#[cfg(any(test, feature = "testing"))]
pub(crate) mod fake;
#[cfg(all(test, not(miri)))]
mod tests;
