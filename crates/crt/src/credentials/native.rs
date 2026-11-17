//! aws-c-auth's delegate provider, answered by a [`Delegate`].
use super::{Delegate, Query, View};
use crt_sys::{self as ffi, native as c};
use std::ffi::{c_int, c_void};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

/// Where one query's answer goes: the signer's callback and its state.
struct Completion {
    callback: ffi::GetCredentialsCallback,
    data: *mut c_void,
}
// SAFETY: aws-c-auth's providers answer a query from whichever thread
// resolves it, so its callback and state accept a call from any one thread.
unsafe impl Send for Completion {}

impl Completion {
    fn answer(self, view: Option<View<'_>>) {
        let cursor =
            |text: Option<&str>| ffi::AwsByteCursor::from_bytes(text.unwrap_or("").as_bytes());
        let view = view.map(|view| c::CredentialsView {
            access_key_id: cursor(Some(view.access_key_id)),
            secret_access_key: cursor(Some(view.secret_access_key)),
            session_token: cursor(view.session_token),
            account_id: cursor(view.account_id),
            expiration_timepoint_seconds: view.expiration.map_or(u64::MAX, epoch_seconds),
        });
        // SAFETY: the query owns this callback's one call, and the shim
        // copies the borrowed credentials before it returns.
        unsafe {
            c::zaws_credentials_complete(
                Some(self.callback),
                self.data,
                view.as_ref().map_or(std::ptr::null(), std::ptr::from_ref),
            );
        }
    }
}

/// aws-c-auth's `expiration_timepoint_seconds` for an expiry: whole seconds
/// since the epoch, and zero for an instant before it.
fn epoch_seconds(expiration: SystemTime) -> u64 {
    expiration
        .duration_since(UNIX_EPOCH)
        .map_or(0, |since_epoch| since_epoch.as_secs())
}

/// The delegate a runtime's credentials stage hands the CRT. It is boxed so
/// the CRT's pointer to it stays valid while the runtime moves.
pub(crate) type Pinned = Box<Arc<dyn Delegate>>;

/// The shim's `credentials_delegate_data` for `delegate`.
pub(crate) fn data(delegate: &Pinned) -> *mut c_void {
    std::ptr::from_ref::<Arc<dyn Delegate>>(delegate)
        .cast_mut()
        .cast()
}

/// The shim's `credentials_delegate`.
///
/// # Safety
/// `delegate` is [`data`] of a delegate that outlives the provider, which
/// the credentials stage's shutdown callback ends.
pub(crate) unsafe extern "C" fn on_query(
    delegate: *mut c_void,
    callback: Option<ffi::GetCredentialsCallback>,
    data: *mut c_void,
) -> c_int {
    let Some(callback) = callback else {
        // SAFETY: raising an error has no pointer arguments.
        return unsafe { ffi::aws_raise_error(crate::s3::INVALID_ARGUMENT_ERROR_CODE) };
    };
    // SAFETY: the caller's contract; the delegate is shared, never mutated.
    let delegate = unsafe { &*delegate.cast::<Arc<dyn Delegate>>() };
    let completion = Completion { callback, data };
    delegate.credentials(Query::new(move |view| completion.answer(view)));
    ffi::AWS_OP_SUCCESS
}
