use super::{
    ListEntry, ListOptions, ListStats,
    driver::{self, Submit},
    page::Page,
    request::{Operation, Query},
};
use crate::crt_error::check_pointer;
use crate::{
    Runtime,
    redirect::Outcome,
    runtime::BucketRuntime,
    s3::{
        ListResult, TransferResult,
        botocore_retry::{self, ErrorKind},
        result_from_view,
    },
    signal::lock,
};
use cli_core::interrupt::{Canceled, State};
use crt_sys::{self as ffi, native as c};
use std::{ffi::c_void, ptr::NonNull, sync::Arc};

#[derive(Clone, Copy)]
enum Client<'a> {
    Runtime(&'a Runtime),
    Bucket(&'a BucketRuntime, &'a State),
}
impl<'a> Client<'a> {
    fn current(self) -> &'a Runtime {
        match self {
            Self::Runtime(runtime) => runtime,
            Self::Bucket(bucket, _) => bucket.selected(),
        }
    }
    fn interrupt(self) -> &'a State {
        match self {
            Self::Runtime(_) => cli_core::interrupt::process_state(),
            Self::Bucket(_, interrupt) => interrupt,
        }
    }
}
fn endpoint(runtime: &Runtime) -> (&[u8], &[u8]) {
    let mut authority = ffi::AwsByteCursor::from_bytes(&[]);
    let mut path = authority;
    // SAFETY: the returned cursors borrow the parsed endpoint the live runtime owns.
    unsafe { c::zaws_runtime_endpoint(runtime.pointer(), &mut authority, &mut path) };
    let bytes = |cursor: ffi::AwsByteCursor| {
        if cursor.len == 0 {
            &[][..]
        } else {
            // SAFETY: endpoint storage lives as long as the borrowed runtime.
            unsafe { std::slice::from_raw_parts(cursor.ptr, cursor.len) }
        }
    };
    (bytes(authority), bytes(path))
}

struct NativeOps<'a> {
    client: Client<'a>,
    runtime: &'a Runtime,
    operation: Operation,
    payer: &'a [u8],
    user_agent: Option<&'a [u8]>,
}
impl driver::PageOps for NativeOps<'_> {
    type Handle = NonNull<ffi::AwsS3MetaRequest>;
    fn endpoint_path(&mut self, _fallback: &[u8]) -> Vec<u8> {
        self.runtime = self.client.current();
        endpoint(self.runtime).1.to_vec()
    }
    fn recover_region(&mut self, failed: &ListResult) -> bool {
        let Client::Bucket(bucket, interrupt) = self.client else {
            return false;
        };
        let mut failure = failed.transfer.clone();
        if failure.service_error.operation.is_empty() {
            failure.service_error.operation.set(self.operation.name());
        }
        bucket.recover_region(&failure, false, interrupt) == Outcome::Ready
    }
    fn submit(
        &mut self,
        page: &Arc<Page>,
        path: &[u8],
    ) -> Result<Submit<Self::Handle>, Box<TransferResult>> {
        let cursor = ffi::AwsByteCursor::from_bytes;
        let (authority, _) = endpoint(self.runtime);
        let message = super::message::Message::new(
            authority,
            path,
            self.payer,
            self.user_agent
                .unwrap_or(self.runtime.options().user_agent.as_bytes()),
        )?;
        page.record_provenance(
            self.runtime.client_region().as_bytes(),
            self.runtime.options().endpoint_url.as_bytes(),
        );
        let data = Arc::into_raw(Arc::clone(page)).cast_mut().cast();
        // SAFETY: C acquires the message; the callback Arc remains owned until shutdown.
        let submitted = check_pointer(unsafe {
            c::zaws_submit_message(
                self.runtime.pointer(),
                message.pointer(),
                cursor(self.operation.name()),
                Some(body),
                Some(finish),
                Some(telemetry),
                Some(shutdown),
                data,
            )
        });
        match submitted {
            Ok(meta) => Ok(Submit::Submitted(meta)),
            Err(code) => {
                // SAFETY: rejected submission retains no callbacks.
                drop(unsafe { Arc::from_raw(data.cast::<Page>()) });
                Ok(Submit::Failed(code))
            }
        }
    }
    fn cancel(&mut self, handle: &Self::Handle) {
        // SAFETY: the driver retains a live counted request until release.
        unsafe { ffi::aws_s3_meta_request_cancel(handle.as_ptr()) };
    }
    fn release(&mut self, handle: Self::Handle) {
        // SAFETY: finish has run; release transfers the driver's one counted reference.
        unsafe { ffi::aws_s3_meta_request_release(handle.as_ptr()) };
    }
    fn backoff(&mut self, attempt: u64, kind: ErrorKind) -> Result<(), Canceled> {
        let delay = botocore_retry::backoff_delay(&mut botocore_retry::random_word, attempt, kind);
        self.client.interrupt().sleep(delay)
    }
}
unsafe extern "C" fn body(
    _: *mut ffi::AwsS3MetaRequest,
    bytes: ffi::AwsByteCursor,
    _: u64,
    _: *mut ffi::AwsS3BufferTicket,
    data: *mut c_void,
) -> i32 {
    // SAFETY: CRT retains this page and the cursor for the callback duration.
    let page = unsafe { &*data.cast::<Page>() };
    // SAFETY: a nonempty CRT cursor points to its callback-lifetime body buffer.
    let bytes = if bytes.len == 0 {
        &[]
    } else {
        // SAFETY: the nonempty body cursor belongs to the current callback.
        unsafe { std::slice::from_raw_parts(bytes.ptr, bytes.len) }
    };
    match page.append_chunk(bytes) {
        Ok(()) => 0,
        // SAFETY: only records the calling thread's callback error.
        Err(code) => unsafe { ffi::aws_raise_error(code) },
    }
}
unsafe extern "C" fn finish(raw: *const c::ResultView, data: *mut c_void) {
    // SAFETY: result and page are live throughout this callback.
    let (raw, page) = unsafe { (&*raw, &*data.cast::<Page>()) };
    // SAFETY: the shim's view and its cursors are live for this callback; the
    // whole error response is parsed and copied before it returns.
    let mut result = unsafe { result_from_view(raw, "") };
    // A page keeps the status it received: only object transfers and HeadObject
    // read a PreconditionFailed as HTTP 412.
    result.response_status = raw.response_status;
    page.finish(result);
}
unsafe extern "C" fn telemetry(status: i32, data: *mut c_void) {
    // SAFETY: the page's callback reference lives through shutdown.
    let page = unsafe { &*data.cast::<Page>() };
    lock(&page.inner).attempt_status = status;
}
unsafe extern "C" fn shutdown(data: *mut c_void) {
    // SAFETY: the final callback consumes exactly the reference created at submit.
    let page = unsafe { Arc::from_raw(data.cast::<Page>()) };
    page.shutdown();
}
impl BucketRuntime {
    /// Lists on the selected client. A failed page that redirects replays
    /// once on the regional client, and later pages follow it; `interrupt`
    /// cancels the region lookup.
    pub fn list_objects(
        &self,
        options: ListOptions<'_>,
        stats: Option<&mut ListStats>,
        callback: &mut dyn FnMut(ListEntry) -> i32,
        interrupt: &State,
    ) -> ListResult {
        list_objects(Client::Bucket(self, interrupt), options, stats, callback)
    }
}
fn list_objects(
    client: Client<'_>,
    options: ListOptions<'_>,
    stats: Option<&mut ListStats>,
    callback: &mut dyn FnMut(ListEntry) -> i32,
) -> ListResult {
    if options.bucket.is_empty() {
        return ListResult {
            transfer: TransferResult::invalid_argument(),
            ..ListResult::default()
        };
    }
    list(
        client,
        Query {
            operation: Operation::ListObjectsV2,
            prefix: options.prefix,
            delimiter: if options.recursive { b"" } else { b"/" },
            region: b"",
            page_size: options.page_size,
        },
        Headers {
            payer: options.request_payer,
            user_agent: options.user_agent,
        },
        options.prefetch,
        options.object_conditions,
        stats,
        callback,
    )
}
impl Runtime {
    pub fn list_objects(
        &self,
        options: ListOptions<'_>,
        stats: Option<&mut ListStats>,
        callback: &mut dyn FnMut(ListEntry) -> i32,
    ) -> ListResult {
        list_objects(Client::Runtime(self), options, stats, callback)
    }
    pub fn list_buckets(
        &self,
        prefix: &[u8],
        region: &[u8],
        page_size: u32,
        callback: &mut dyn FnMut(ListEntry) -> i32,
    ) -> ListResult {
        list(
            Client::Runtime(self),
            Query {
                operation: Operation::ListBuckets,
                prefix,
                delimiter: b"",
                region,
                page_size,
            },
            Headers::default(),
            false,
            false,
            None,
            callback,
        )
    }
}
#[derive(Debug, Clone, Copy, Default)]
struct Headers<'a> {
    payer: &'a [u8],
    user_agent: Option<&'a [u8]>,
}
fn list(
    client: Client<'_>,
    query: Query<'_>,
    headers: Headers<'_>,
    prefetch: bool,
    object_conditions: bool,
    stats: Option<&mut ListStats>,
    callback: &mut dyn FnMut(ListEntry) -> i32,
) -> ListResult {
    let runtime = client.current();
    let mut ops = NativeOps {
        client,
        runtime,
        operation: query.operation,
        payer: headers.payer,
        user_agent: headers.user_agent,
    };
    let mut options = driver::Options::new(endpoint(runtime).1, query, prefetch);
    options.page_attempts = runtime.options().botocore_attempts;
    options.object_conditions = object_conditions;
    let mut result = driver::run(options, &mut ops, stats, callback);
    let operation = &mut result.transfer.service_error.operation;
    if result.transfer.error_code != 0 && operation.is_empty() {
        operation.set(query.operation.name());
    }
    let runtime = ops.runtime;
    if result.transfer.error_code != 0 {
        result.transfer.proxy_url =
            crate::s3::masked_proxy(runtime.options().proxy_url.as_deref().unwrap_or(""));
    }
    // Only a run that returned a result records its outcome; a local failure
    // escapes the run before it, so it records none.
    if result.local_error.is_none() {
        runtime.record_outcome(result.transfer.error_code, result.transfer.response_status);
    }
    result
}
