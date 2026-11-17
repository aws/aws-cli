//! Owned CRT runtime resources, requests, listing, and explicit diagnostics.

pub mod allocator;
pub mod credentials;
mod crt_error;
pub mod debug;
pub mod http;
pub mod page_mapping;
pub mod process_lock;
pub mod runtime;
pub mod s3;
mod sequential_parts;
pub mod shared_files;
pub mod signal;
pub mod source_pool;
#[cfg(any(test, feature = "testing"))]
pub mod testing;

#[doc(inline)]
pub use runtime::Runtime;
#[doc(inline)]
pub use runtime::{RuntimeLifecycleOps, RuntimeOptions};
#[doc(inline)]
pub use s3::{BodyTicketOps, MetaRequestOps};
#[doc(inline)]
pub use sequential_parts::request_sequential_parts;

#[doc(inline)]
pub use source_pool::AllocationOps;

/// Applies the platform CRT TLS default before any worker threads exist.
///
/// # Safety
/// On macOS the caller must invoke this before spawning any thread or making a
/// CRT call. The supplied value is from the entrypoint's environment snapshot.
pub unsafe fn prepare_process(non_fips_tls_13: Option<&str>) {
    #[cfg(target_os = "macos")]
    if non_fips_tls_13.is_none_or(str::is_empty) {
        unsafe extern "C" {
            fn setenv(
                name: *const std::ffi::c_char,
                value: *const std::ffi::c_char,
                overwrite: std::ffi::c_int,
            ) -> std::ffi::c_int;
        }
        // SAFETY: the caller guarantees process environment mutation precedes
        // every thread and CRT call; both strings are NUL terminated literals.
        unsafe {
            setenv(c"AWS_CRT_USE_NON_FIPS_TLS_13".as_ptr(), c"1".as_ptr(), 1);
        }
    }
    #[cfg(not(target_os = "macos"))]
    let _ = non_fips_tls_13;
}
pub mod endpoints;
pub mod redirect;
