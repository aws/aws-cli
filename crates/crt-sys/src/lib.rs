//! Narrow, checked-in declarations for the native CRT surface.

use std::ffi::{c_char, c_int, c_void};

#[cfg(all(target_os = "linux", target_env = "musl"))]
mod mimalloc;
#[cfg(all(target_os = "linux", target_env = "musl"))]
pub use mimalloc::Mimalloc;

#[cfg(all(test, target_os = "linux", target_env = "musl", not(miri)))]
mod tests;

#[derive(Debug)]
#[repr(C)]
pub struct AwsAllocator {
    _private: [u8; 0],
}

macro_rules! c_functions {
    ($(
        $(#[$attribute:meta])*
        pub fn $name:ident($($argument:ident: $type:ty),* $(,)?) $(-> $output:ty)?;
    )*) => {
        #[cfg(not(fuzzing))]
        unsafe extern "C" {
            $(
                $(#[$attribute])*
                pub fn $name($($argument: $type),*) $(-> $output)?;
            )*
        }
        $(
            #[cfg(fuzzing)]
            $(#[$attribute])*
            #[allow(
                clippy::missing_safety_doc,
                reason = "the C function documents the contract; this stub only aborts"
            )]
            #[unsafe(no_mangle)]
            pub unsafe extern "C" fn $name($(_: $type),*) $(-> $output)? {
                std::process::abort()
            }
        )*
    };
}

macro_rules! opaque {
    ($($name:ident),+ $(,)?) => {$(
        #[derive(Debug)]
#[repr(C)]
        pub struct $name { _private: [u8; 0] }
    )+};
}

opaque!(
    AwsEventLoopGroup,
    AwsHostResolver,
    AwsClientBootstrap,
    AwsTlsCtx,
    AwsTlsConnectionOptions,
    AwsCredentialsProvider,
    AwsCredentials,
    AwsS3Client,
    AwsS3MetaRequest,
    AwsHttpHeaders,
    AwsFutureS3BufferTicket,
    AwsCrossProcessLock,
);

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct AwsByteCursor {
    pub len: usize,
    pub ptr: *mut u8,
}

impl AwsByteCursor {
    pub fn from_bytes(bytes: &[u8]) -> Self {
        Self {
            len: bytes.len(),
            ptr: bytes.as_ptr().cast_mut(),
        }
    }
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct AwsByteBuf {
    pub len: usize,
    pub buffer: *mut u8,
    pub capacity: usize,
    pub allocator: *mut AwsAllocator,
}

#[derive(Debug)]
#[repr(C)]
pub struct AwsAtomicVar {
    value: *mut c_void,
}

#[derive(Debug)]
#[repr(C)]
pub struct AwsRefCount {
    ref_count: AwsAtomicVar,
    object: *mut c_void,
    on_zero_fn: Option<unsafe extern "C" fn(*mut c_void)>,
}

pub type TicketClaimFn = unsafe extern "C" fn(*mut AwsS3BufferTicket) -> AwsByteBuf;
pub type TicketRefFn = unsafe extern "C" fn(*mut AwsS3BufferTicket) -> *mut AwsS3BufferTicket;

#[derive(Debug)]
#[repr(C)]
pub struct AwsS3BufferTicketVtable {
    pub claim: Option<TicketClaimFn>,
    pub acquire: Option<TicketRefFn>,
    pub release: Option<TicketRefFn>,
}

#[derive(Debug)]
#[repr(C)]
pub struct AwsS3BufferTicket {
    pub vtable: *mut AwsS3BufferTicketVtable,
    pub ref_count: AwsRefCount,
    pub implementation: *mut c_void,
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct AwsS3BufferPoolReserveMeta {
    pub client: *mut AwsS3Client,
    pub meta_request: *mut AwsS3MetaRequest,
    pub size: usize,
    pub can_block: bool,
    pub local_offset: u64,
}

pub type PoolReserveFn = unsafe extern "C" fn(
    *mut AwsS3BufferPool,
    AwsS3BufferPoolReserveMeta,
) -> *mut AwsFutureS3BufferTicket;
pub type PoolVoidFn = unsafe extern "C" fn(*mut AwsS3BufferPool);
pub type PoolSpecialFn = unsafe extern "C" fn(*mut AwsS3BufferPool, usize) -> c_int;
pub type PoolReleaseSpecialFn = unsafe extern "C" fn(*mut AwsS3BufferPool, usize);
pub type PoolAlignFn = unsafe extern "C" fn(*mut AwsS3BufferPool, u64) -> u64;
pub type PoolRefFn = unsafe extern "C" fn(*mut AwsS3BufferPool) -> *mut AwsS3BufferPool;
pub type PoolAddPreallocatedFn =
    unsafe extern "C" fn(*mut AwsS3BufferPool, *mut AwsS3MetaRequest, *mut AwsByteBuf) -> c_int;
pub type PoolRemovePreallocatedFn =
    unsafe extern "C" fn(*mut AwsS3BufferPool, *mut AwsS3MetaRequest);

#[derive(Debug)]
#[repr(C)]
pub struct AwsS3BufferPoolVtable {
    pub reserve: Option<PoolReserveFn>,
    pub trim: Option<PoolVoidFn>,
    pub add_special_size: Option<PoolSpecialFn>,
    pub release_special_size: Option<PoolReleaseSpecialFn>,
    pub derive_aligned_buffer_size: Option<PoolAlignFn>,
    pub acquire: Option<PoolRefFn>,
    pub release: Option<PoolRefFn>,
    pub add_preallocated_buffer: Option<PoolAddPreallocatedFn>,
    pub remove_preallocated_buffer: Option<PoolRemovePreallocatedFn>,
}

const _: () = {
    assert!(std::mem::size_of::<AwsS3BufferPoolReserveMeta>() == 40);
    assert!(std::mem::size_of::<AwsS3BufferPoolVtable>() == 72);
};

#[derive(Debug)]
#[repr(C)]
pub struct AwsS3BufferPool {
    pub vtable: *mut AwsS3BufferPoolVtable,
    pub ref_count: AwsRefCount,
    pub implementation: *mut c_void,
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct AwsS3BufferPoolConfig {
    pub client: *mut AwsS3Client,
    pub part_size: usize,
    pub max_part_size: usize,
    pub memory_limit: usize,
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct AwsS3BodyExtraInfo {
    pub range_start: u64,
    pub ticket: *mut AwsS3BufferTicket,
}

#[derive(Debug)]
#[repr(C)]
pub struct AwsS3MetaRequestResult {
    pub error_response_headers: *mut AwsHttpHeaders,
    pub error_response_body: *mut AwsByteBuf,
    pub error_response_operation_name: *mut c_void,
    pub response_status: c_int,
    pub did_validate: bool,
    pub validation_algorithm: c_int,
    pub error_code: c_int,
}

pub type ShutdownFn = unsafe extern "C" fn(*mut c_void);
pub type CredentialsShutdownFn = unsafe extern "C" fn(*mut c_void);
pub type ClientShutdownFn = unsafe extern "C" fn(*mut c_void);
/// `aws_on_get_credentials_callback_fn`: a query's answer, which borrows the
/// credentials for the call.
pub type GetCredentialsCallback = unsafe extern "C" fn(*mut AwsCredentials, c_int, *mut c_void);
/// `aws_credentials_provider_delegate_get_credentials_fn`: the delegate's
/// data, then the query's callback and its data. Returning success promises
/// one call of the callback.
pub type CredentialsDelegateFn =
    unsafe extern "C" fn(*mut c_void, Option<GetCredentialsCallback>, *mut c_void) -> c_int;
pub type PoolFactoryFn = unsafe extern "C" fn(
    *mut AwsAllocator,
    AwsS3BufferPoolConfig,
    *mut c_void,
) -> *mut AwsS3BufferPool;
pub type HeadersFn =
    unsafe extern "C" fn(*mut AwsS3MetaRequest, *const AwsHttpHeaders, c_int, *mut c_void) -> c_int;
pub type BodyFn = unsafe extern "C" fn(
    *mut AwsS3MetaRequest,
    *const AwsByteCursor,
    AwsS3BodyExtraInfo,
    *mut c_void,
) -> c_int;
pub type PlainBodyFn =
    unsafe extern "C" fn(*mut AwsS3MetaRequest, *const AwsByteCursor, u64, *mut c_void) -> c_int;
pub type FinishFn =
    unsafe extern "C" fn(*mut AwsS3MetaRequest, *const AwsS3MetaRequestResult, *mut c_void);

pub const AWS_OP_SUCCESS: c_int = 0;
pub const AWS_ERROR_S3_SLOW_DOWN: c_int = 0x3806;
pub const AWS_ERROR_S3_INVALID_RESPONSE_STATUS: c_int = 0x3807;
pub const AWS_ERROR_S3_CANCELED: c_int = 0x380B;
pub const AWS_ERROR_S3_RESPONSE_CHECKSUM_MISMATCH: c_int = 0x380E;
/// The CRT's code for an object that changed while it was downloaded, which a
/// size-checked GET's headers callback raises too.
pub const AWS_ERROR_S3_OBJECT_MODIFIED: c_int = 0x3814;
pub const AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED: c_int = 0x3822;
pub const AWS_ERROR_S3_PART_SIZE_EXCEEDS_MEMORY_LIMIT: c_int = 0x3823;
pub const AWS_ERROR_FILE_INVALID_PATH: c_int = 44;
pub const AWS_AUTH_SIGNING_NO_CREDENTIALS: c_int = 6146;
pub const AWS_IO_TLS_ERROR_NEGOTIATION_FAILURE: c_int = 1029;
pub const AWS_IO_SOCKET_CONNECTION_REFUSED: c_int = 1047;
pub const AWS_IO_SOCKET_TIMEOUT: c_int = 1048;
pub const AWS_IO_SOCKET_NO_ROUTE_TO_HOST: c_int = 1049;
pub const AWS_IO_TLS_NEGOTIATION_TIMEOUT: c_int = 1067;
pub const AWS_IO_SOCKET_NETWORK_DOWN: c_int = 1050;
pub const AWS_IO_SOCKET_CONNECT_ABORTED: c_int = 1057;
pub const AWS_IO_DNS_QUERY_FAILED: c_int = 1058;
pub const AWS_IO_DNS_INVALID_NAME: c_int = 1059;
pub const AWS_IO_DNS_NO_ADDRESS_FOR_HOST: c_int = 1060;
/// `aws_tribool` values (sigcheck.c verifies them): a zeroed option is unset.
pub const AWS_TRIBOOL_UNSET: c_int = 0;
pub const AWS_TRIBOOL_TRUE: c_int = 2;

// SAFETY CONTRACT: declarations are restricted to the ABI surface checked by
// crt_shim.c against the pinned headers. Callers must supply live CRT objects,
// preserve cursor/user-data lifetimes, and honor each API's ownership transfer.
c_functions! {
    pub fn rust_crt_allocator() -> *mut AwsAllocator;
    pub fn rust_crt_library_init(allocator: *mut AwsAllocator);
    pub fn rust_crt_library_clean_up();
    pub fn rust_crt_event_loop_new(
        allocator: *mut AwsAllocator,
        loop_count: u16,
        shutdown_callback: Option<ShutdownFn>,
        shutdown_user_data: *mut c_void,
    ) -> *mut AwsEventLoopGroup;
    pub fn rust_crt_resolver_new(
        allocator: *mut AwsAllocator,
        group: *mut AwsEventLoopGroup,
        shutdown_callback: Option<ShutdownFn>,
        shutdown_user_data: *mut c_void,
    ) -> *mut AwsHostResolver;
    pub fn rust_crt_bootstrap_new(
        allocator: *mut AwsAllocator,
        group: *mut AwsEventLoopGroup,
        resolver: *mut AwsHostResolver,
        shutdown_callback: Option<ShutdownFn>,
        shutdown_user_data: *mut c_void,
    ) -> *mut AwsClientBootstrap;
    pub fn rust_crt_last_error() -> c_int;
    pub fn rust_crt_error_name(error_code: c_int) -> *const c_char;
    pub fn rust_crt_error_message(error_code: c_int) -> *const c_char;

    pub fn aws_event_loop_group_release(group: *mut AwsEventLoopGroup);
    pub fn aws_host_resolver_release(resolver: *mut AwsHostResolver);
    pub fn aws_client_bootstrap_release(bootstrap: *mut AwsClientBootstrap);
    pub fn aws_credentials_provider_release(
        provider: *mut AwsCredentialsProvider,
    ) -> *mut AwsCredentialsProvider;
    pub fn aws_s3_buffer_ticket_acquire(ticket: *mut AwsS3BufferTicket) -> *mut AwsS3BufferTicket;
    pub fn aws_s3_buffer_ticket_release(ticket: *mut AwsS3BufferTicket) -> *mut AwsS3BufferTicket;
    pub fn aws_future_s3_buffer_ticket_new(
        allocator: *mut AwsAllocator,
    ) -> *mut AwsFutureS3BufferTicket;
    pub fn aws_future_s3_buffer_ticket_acquire(
        future: *mut AwsFutureS3BufferTicket,
    ) -> *mut AwsFutureS3BufferTicket;
    pub fn aws_future_s3_buffer_ticket_release(
        future: *mut AwsFutureS3BufferTicket,
    ) -> *mut AwsFutureS3BufferTicket;
    pub fn aws_future_s3_buffer_ticket_set_result_by_move(
        future: *mut AwsFutureS3BufferTicket,
        ticket: *mut *mut AwsS3BufferTicket,
    );
    pub fn aws_future_s3_buffer_ticket_set_error(
        future: *mut AwsFutureS3BufferTicket,
        error_code: c_int,
    );
    pub fn aws_future_s3_buffer_ticket_is_done(future: *const AwsFutureS3BufferTicket) -> bool;
    pub fn aws_future_s3_buffer_ticket_get_error(future: *const AwsFutureS3BufferTicket) -> c_int;
    pub fn aws_s3_meta_request_cancel(request: *mut AwsS3MetaRequest);
    pub fn aws_s3_meta_request_release(request: *mut AwsS3MetaRequest) -> *mut AwsS3MetaRequest;
    pub fn aws_raise_error(error_code: c_int) -> c_int;
    /// The lock `instance_nonce` names, or null when another holder has it;
    /// the cursor is read only during the call.
    pub fn aws_cross_process_lock_try_acquire(
        allocator: *mut AwsAllocator,
        instance_nonce: AwsByteCursor,
    ) -> *mut AwsCrossProcessLock;
    pub fn aws_cross_process_lock_release(instance_lock: *mut AwsCrossProcessLock);
}

pub mod endpoints;
pub mod native;
