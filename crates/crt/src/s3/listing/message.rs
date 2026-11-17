use crate::crt_error::{check, check_pointer};
use crate::s3::TransferResult;
use crt_sys::{self as ffi, native as c};
use std::ptr::NonNull;
pub(super) struct Message(NonNull<c::HttpMessage>);
impl Message {
    pub(super) fn new(
        host: &[u8],
        path: &[u8],
        payer: &[u8],
        user_agent: &[u8],
    ) -> Result<Self, Box<TransferResult>> {
        // SAFETY: allocator is valid while the runtime holds its library guard.
        let message = Self(
            check_pointer(unsafe { c::aws_http_message_new_request(ffi::rust_crt_allocator()) })
                .map_err(TransferResult::from_crt_error)?,
        );
        let raw = message.pointer();
        for (name, value) in [
            (b"host".as_slice(), host),
            (b"accept", b"application/xml"),
            (b"user-agent", user_agent),
        ] {
            message.header(name, value)?;
        }
        let crt_failure = |code| Box::new(TransferResult::from_crt_error(code));
        // SAFETY: CRT synchronously copies the method into the owned message.
        check(unsafe {
            c::aws_http_message_set_request_method(raw, ffi::AwsByteCursor::from_bytes(b"GET"))
        })
        .map_err(crt_failure)?;
        // SAFETY: CRT synchronously copies the path into the owned message.
        check(unsafe {
            c::aws_http_message_set_request_path(raw, ffi::AwsByteCursor::from_bytes(path))
        })
        .map_err(crt_failure)?;
        if !payer.is_empty() {
            message.header(b"x-amz-request-payer", payer)?;
        }
        Ok(message)
    }
    fn header(&self, name: &[u8], value: &[u8]) -> Result<(), Box<TransferResult>> {
        // SAFETY: C copies header cursors into the live message.
        check(unsafe {
            c::zaws_message_add_header(
                self.0.as_ptr(),
                ffi::AwsByteCursor::from_bytes(name),
                ffi::AwsByteCursor::from_bytes(value),
            )
        })
        .map_err(|code| Box::new(TransferResult::from_crt_error(code)))
    }
    pub(super) fn pointer(&self) -> *mut c::HttpMessage {
        self.0.as_ptr()
    }
}
impl Drop for Message {
    fn drop(&mut self) {
        // SAFETY: this owner releases its initial reference; submitted requests retain their own.
        unsafe {
            c::aws_http_message_release(self.0.as_ptr());
        }
    }
}
