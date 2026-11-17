use super::*;
use crate::crt_error::last_raised;
use crate::runtime::RuntimeOptions;
use std::sync::atomic::AtomicUsize;

type TestResult = Result<(), Box<dyn std::error::Error>>;

#[derive(Debug, Default)]
struct Capture {
    ui_hook: bool,
    progress: Mutex<u64>,
    finished: Mutex<Vec<TransferResult>>,
}
impl RequestCallbacks for Capture {
    fn finish(&self, result: TransferResult) {
        lock(&self.finished).push(result);
    }
    fn shutdown(&self) {}
    fn progress(&self, bytes: u64) {
        if self.ui_hook {
            *lock(&self.progress) += bytes;
        }
    }
}

fn runtime() -> Result<Arc<Runtime>, Box<TransferResult>> {
    Ok(Arc::new(Runtime::new(RuntimeOptions {
        region: "us-east-1".into(),
        endpoint_url: "http://127.0.0.1:1/bucket".into(),
        event_loop_count: 1,
        no_sign_request: true,
        ..RuntimeOptions::default()
    })?))
}

fn state(runtime: &Arc<Runtime>, callbacks: &Arc<Capture>) -> Arc<CallbackState> {
    let body: CallbackBodyFn = Box::new(|_| Err(INVALID_ARGUMENT_ERROR_CODE));
    Arc::new(CallbackState {
        runtime: Arc::clone(runtime),
        callbacks: Arc::clone(callbacks) as Arc<dyn RequestCallbacks>,
        body: Mutex::new(Some(body)),
        single_request: false,
        bytes_transferred: AtomicU64::new(0),
        body_delivered: AtomicBool::new(false),
        expected_size: None,
        size_changed: AtomicBool::new(false),
    })
}

fn data(state: &Arc<CallbackState>) -> *mut c_void {
    Arc::as_ptr(state).cast_mut().cast()
}

static TICKET_VTABLE: ffi::AwsS3BufferTicketVtable = ffi::AwsS3BufferTicketVtable {
    claim: None,
    acquire: Some(acquire),
    release: Some(release),
};
unsafe extern "C" fn acquire(ticket: *mut ffi::AwsS3BufferTicket) -> *mut ffi::AwsS3BufferTicket {
    // SAFETY: each test ticket points to its live counter throughout every callback and drop.
    let references = unsafe { &*(*ticket).implementation.cast::<AtomicUsize>() };
    references.fetch_add(1, Ordering::SeqCst);
    ticket
}
unsafe extern "C" fn release(ticket: *mut ffi::AwsS3BufferTicket) -> *mut ffi::AwsS3BufferTicket {
    // SAFETY: each test ticket points to its live counter throughout every callback and drop.
    let references = unsafe { &*(*ticket).implementation.cast::<AtomicUsize>() };
    references.fetch_sub(1, Ordering::SeqCst);
    std::ptr::null_mut()
}
fn ticket(references: &AtomicUsize) -> ffi::AwsS3BufferTicket {
    ffi::AwsS3BufferTicket {
        vtable: std::ptr::from_ref(&TICKET_VTABLE).cast_mut(),
        // SAFETY: all fields are nullable pointers/nullable function pointers. The custom
        // vtable handles references, so CRT never reads this unused zeroed counter.
        ref_count: unsafe { std::mem::zeroed() },
        implementation: std::ptr::from_ref(references).cast_mut().cast(),
    }
}
fn deliver(
    state: &Arc<CallbackState>,
    body: ffi::AwsByteCursor,
    ticket: *mut ffi::AwsS3BufferTicket,
) -> i32 {
    // SAFETY: the cursor, the ticket and the state outlive the synchronous
    // callback, which retains only the references it acquires.
    unsafe { body_callback(std::ptr::null_mut(), body, 9, ticket, data(state)) }
}
type Received = Arc<Mutex<Vec<(Vec<u8>, u64, bool)>>>;
fn recording_state(
    runtime: &Arc<Runtime>,
    single_request: bool,
    result: Result<(), i32>,
) -> (Arc<CallbackState>, Received) {
    let seen = Arc::new(Mutex::new(Vec::new()));
    let record = Arc::clone(&seen);
    let body: CallbackBodyFn = Box::new(move |body| {
        let entry = match body {
            CallbackBody::Ticketed(chunk) => (chunk.as_bytes().to_vec(), chunk.range_start, true),
            CallbackBody::Transient { bytes, range_start } => (bytes.to_vec(), range_start, false),
            CallbackBody::Missing => (Vec::new(), u64::MAX, false),
        };
        lock(&record).push(entry);
        result
    });
    let state = Arc::new(CallbackState {
        runtime: Arc::clone(runtime),
        callbacks: Arc::new(Capture::default()),
        body: Mutex::new(Some(body)),
        single_request,
        bytes_transferred: AtomicU64::new(0),
        body_delivered: AtomicBool::new(false),
        expected_size: None,
        size_changed: AtomicBool::new(false),
    });
    (state, seen)
}

fn finish_success(state: &Arc<CallbackState>) {
    let view = c::ResultView {
        error_code: 0,
        response_status: 200,
        body: cursor(&[]),
        operation: cursor(&[]),
        region_header: cursor(&[]),
        region_header_present: false,
    };
    // SAFETY: the view and the state outlive the call, which retains neither.
    unsafe { finish_callback(&view, data(state)) };
}

#[test]
fn progress_is_captured_with_and_without_a_ui_hook() -> TestResult {
    const MIB: u64 = 1024 * 1024;
    let runtime = runtime()?;
    let hooked = Arc::new(Capture {
        ui_hook: true,
        ..Capture::default()
    });
    let hooked_state = state(&runtime, &hooked);
    // SAFETY: the state outlives these calls, which retain nothing.
    unsafe {
        progress_callback(8 * MIB, data(&hooked_state));
        progress_callback(2 * MIB, data(&hooked_state));
    }
    assert_eq!(*lock(&hooked.progress), 10 * MIB);
    assert!(lock(&hooked.finished).is_empty());
    let unhooked = Arc::new(Capture::default());
    let unhooked_state = state(&runtime, &unhooked);
    for bytes in [8 * MIB, 2 * MIB, 2 * MIB] {
        // SAFETY: as above.
        unsafe { progress_callback(bytes, data(&unhooked_state)) };
    }
    finish_success(&unhooked_state);
    let finished = lock(&unhooked.finished);
    assert_eq!(*lock(&unhooked.progress), 0);
    assert_eq!(finished[0].bytes_transferred, 12 * MIB);
    assert!(!finished[0].body_delivered);
    assert_eq!(finished[0].request_region.as_bytes(), b"us-east-1");
    assert_eq!(
        finished[0].endpoint_url.as_bytes(),
        b"http://127.0.0.1:1/bucket"
    );
    Ok(())
}

#[test]
fn a_rejected_body_was_still_delivered() -> TestResult {
    let runtime = runtime()?;
    let capture = Arc::new(Capture::default());
    let state = state(&runtime, &capture);
    // SAFETY: an empty body borrows nothing; the state outlives the call.
    let rc = unsafe {
        body_callback(
            std::ptr::null_mut(),
            cursor(&[]),
            0,
            std::ptr::null_mut(),
            data(&state),
        )
    };
    assert_ne!(rc, 0);
    finish_success(&state);
    assert!(lock(&capture.finished)[0].body_delivered);
    Ok(())
}

#[test]
fn a_body_without_storage_reaches_the_consumer_as_missing() -> TestResult {
    let runtime = runtime()?;
    let capture = Arc::new(Capture::default());
    let state = state(&runtime, &capture);
    let seen = Arc::new(Mutex::new(Vec::new()));
    let record = Arc::clone(&seen);
    let consumer: CallbackBodyFn = Box::new(move |body| {
        lock(&record).push(matches!(body, CallbackBody::Missing));
        Err(CANCELED_ERROR_CODE)
    });
    *lock(&state.body) = Some(consumer);
    let missing = ffi::AwsByteCursor {
        ptr: std::ptr::null_mut(),
        len: 4,
    };
    // SAFETY: the null cursor borrows nothing; the state outlives the call.
    let rc = unsafe {
        body_callback(
            std::ptr::null_mut(),
            missing,
            0,
            std::ptr::null_mut(),
            data(&state),
        )
    };
    assert_ne!(rc, 0);
    assert_eq!(last_raised(), CANCELED_ERROR_CODE);
    assert_eq!(*lock(&seen), [true]);
    finish_success(&state);
    assert!(lock(&capture.finished)[0].body_delivered);
    Ok(())
}

#[test]
fn failures_own_the_error_response_region_header() -> TestResult {
    let _library = Library::acquire();
    let runtime = runtime()?;
    let capture = Arc::new(Capture::default());
    let state = state(&runtime, &capture);
    let names = [cursor(b"x-amz-bucket-region")];
    let values = [cursor(b"eu-west-1")];
    // SAFETY: the cursors and the state outlive the synchronous capture,
    // which releases its headers before returning and retains nothing.
    let rc = unsafe {
        c::zaws_callback_capture(
            names.as_ptr(),
            values.as_ptr(),
            1,
            301,
            1,
            None,
            Some(finish_callback),
            data(&state),
        )
    };
    assert_eq!(rc, 0);
    let finished = lock(&capture.finished);
    let error = &finished[0].service_error;
    assert!(error.region_header.is_present());
    assert_eq!(error.region_header.as_bytes(), b"eu-west-1");
    assert_eq!(finished[0].request_region.as_bytes(), b"us-east-1");
    Ok(())
}

#[test]
fn a_failed_get_hands_its_whole_message_to_the_receiver() -> TestResult {
    let runtime = runtime()?;
    let capture = Arc::new(Capture::default());
    let state = state(&runtime, &capture);
    let message = format!("{}\u{e9} tail", "a".repeat(1023));
    let xml = format!("<Error><Code>AccessDenied</Code><Message>{message}</Message></Error>");
    let view = c::ResultView {
        error_code: UNKNOWN_ERROR_CODE,
        response_status: 403,
        body: cursor(xml.as_bytes()),
        operation: cursor(b"GetObject"),
        region_header: cursor(&[]),
        region_header_present: false,
    };
    // SAFETY: the view and the state outlive the call, which retains neither.
    unsafe { finish_callback(&view, data(&state)) };
    let finished = lock(&capture.finished);
    assert_eq!(finished.len(), 1);
    let error = &finished[0].service_error;
    assert_eq!(error.code.as_bytes(), b"AccessDenied");
    assert_eq!(error.message, message.as_bytes());
    Ok(())
}

#[derive(Debug)]
struct ShutdownProbe {
    output: std::sync::Weak<()>,
    output_alive: Mutex<Option<bool>>,
}
impl RequestCallbacks for ShutdownProbe {
    fn finish(&self, _: TransferResult) {}
    fn shutdown(&self) {
        *lock(&self.output_alive) = Some(self.output.upgrade().is_some());
    }
}

#[test]
fn shutdown_releases_the_body_consumer_before_its_owner_hears() -> TestResult {
    let runtime = runtime()?;
    let output = Arc::new(());
    let probe = Arc::new(ShutdownProbe {
        output: Arc::downgrade(&output),
        output_alive: Mutex::new(None),
    });
    let body: CallbackBodyFn = Box::new(move |_| {
        let _held = &output;
        Ok(())
    });
    let state = Arc::new(CallbackState {
        runtime,
        callbacks: Arc::clone(&probe) as Arc<dyn RequestCallbacks>,
        body: Mutex::new(Some(body)),
        single_request: false,
        bytes_transferred: AtomicU64::new(0),
        body_delivered: AtomicBool::new(false),
        expected_size: None,
        size_changed: AtomicBool::new(false),
    });
    // SAFETY: the shutdown consumes the one reference this pointer carries.
    unsafe { shutdown_callback(Arc::into_raw(state).cast_mut().cast()) };
    assert_eq!(*lock(&probe.output_alive), Some(false));
    Ok(())
}

#[derive(Debug)]
struct RuntimeProbe {
    runtime: std::sync::Weak<Runtime>,
    counts: Arc<Mutex<Vec<usize>>>,
}
impl RequestCallbacks for RuntimeProbe {
    fn finish(&self, _: TransferResult) {}
    fn shutdown(&self) {
        lock(&self.counts).push(self.runtime.strong_count());
    }
}
impl Drop for RuntimeProbe {
    fn drop(&mut self) {
        lock(&self.counts).push(self.runtime.strong_count());
    }
}

#[test]
fn shutdown_releases_the_runtime_before_its_callbacks() -> TestResult {
    let runtime = runtime()?;
    let counts = Arc::new(Mutex::new(Vec::new()));
    let probe = RuntimeProbe {
        runtime: Arc::downgrade(&runtime),
        counts: Arc::clone(&counts),
    };
    let state = Arc::new(CallbackState {
        runtime: Arc::clone(&runtime),
        callbacks: Arc::new(probe),
        body: Mutex::new(None),
        single_request: false,
        bytes_transferred: AtomicU64::new(0),
        body_delivered: AtomicBool::new(false),
        expected_size: None,
        size_changed: AtomicBool::new(false),
    });
    // SAFETY: the shutdown consumes the one reference this pointer carries.
    unsafe { shutdown_callback(Arc::into_raw(state).cast_mut().cast()) };
    assert_eq!(*lock(&counts), [2, 1]);
    Ok(())
}

#[test]
fn the_body_callback_refuses_a_ranged_part_without_a_ticket() -> TestResult {
    let _library = Library::acquire();
    let runtime = runtime()?;
    let (state, seen) = recording_state(&runtime, false, Ok(()));
    let references = AtomicUsize::new(1);
    let mut ticket = ticket(&references);
    assert_eq!(deliver(&state, cursor(b"part"), std::ptr::null_mut()), -1);
    assert_eq!(last_raised(), INVALID_ARGUMENT_ERROR_CODE);
    assert!(lock(&seen).is_empty());
    assert!(!state.body_delivered.load(Ordering::Acquire));
    assert_eq!(deliver(&state, cursor(&[]), std::ptr::null_mut()), 0);
    let missing = ffi::AwsByteCursor {
        ptr: std::ptr::null_mut(),
        len: 1,
    };
    assert_eq!(deliver(&state, missing, &mut ticket), 0);
    assert_eq!(
        *lock(&seen),
        [(vec![], 9, false), (vec![], u64::MAX, false)]
    );
    assert!(state.body_delivered.load(Ordering::Acquire));
    assert_eq!(references.load(Ordering::SeqCst), 1);
    Ok(())
}

#[test]
fn the_body_callback_lends_single_request_bytes_and_acquires_only_tickets() -> TestResult {
    let _library = Library::acquire();
    let runtime = runtime()?;
    let lent = Arc::new(Mutex::new(None));
    let pointer = Arc::clone(&lent);
    let held = Arc::new(Mutex::new(Vec::new()));
    let chunks = Arc::clone(&held);
    let body: CallbackBodyFn = Box::new(move |body| {
        match body {
            CallbackBody::Transient { bytes, .. } => *lock(&pointer) = Some(bytes.as_ptr().addr()),
            CallbackBody::Ticketed(chunk) => lock(&chunks).push(chunk),
            CallbackBody::Missing => return Err(INVALID_ARGUMENT_ERROR_CODE),
        }
        Ok(())
    });
    let (state, _) = recording_state(&runtime, true, Ok(()));
    *lock(&state.body) = Some(body);
    let bytes = b"payload";
    assert_eq!(deliver(&state, cursor(bytes), std::ptr::null_mut()), 0);
    assert_eq!(*lock(&lent), Some(bytes.as_ptr().addr()));
    let references = AtomicUsize::new(1);
    let mut ticket = ticket(&references);
    assert_eq!(deliver(&state, cursor(bytes), &mut ticket), 0);
    assert_eq!(references.load(Ordering::SeqCst), 2);
    let chunk = lock(&held).pop().ok_or("a ticketed part")?;
    assert_eq!((chunk.as_bytes(), chunk.range_start), (&bytes[..], 9));
    drop(chunk);
    assert_eq!(references.load(Ordering::SeqCst), 1);
    Ok(())
}

#[test]
fn a_rejected_part_releases_its_ticket_and_raises_the_consumer_error() -> TestResult {
    let _library = Library::acquire();
    let runtime = runtime()?;
    let (state, seen) = recording_state(&runtime, false, Err(UNKNOWN_ERROR_CODE));
    let references = AtomicUsize::new(1);
    let mut ticket = ticket(&references);
    assert_eq!(deliver(&state, cursor(&[4, 5, 6, 7]), &mut ticket), -1);
    assert_eq!(last_raised(), UNKNOWN_ERROR_CODE);
    assert_eq!(*lock(&seen), [(vec![4, 5, 6, 7], 9, true)]);
    assert!(state.body_delivered.load(Ordering::Acquire));
    assert_eq!(references.load(Ordering::SeqCst), 1);
    Ok(())
}

fn checked_state(
    runtime: &Arc<Runtime>,
    callbacks: &Arc<Capture>,
    expected: u64,
) -> Arc<CallbackState> {
    let body: CallbackBodyFn = Box::new(|_| Ok(()));
    Arc::new(CallbackState {
        runtime: Arc::clone(runtime),
        callbacks: Arc::clone(callbacks) as Arc<dyn RequestCallbacks>,
        body: Mutex::new(Some(body)),
        single_request: false,
        bytes_transferred: AtomicU64::new(0),
        body_delivered: AtomicBool::new(false),
        expected_size: Some(expected),
        size_changed: AtomicBool::new(false),
    })
}
std::thread_local! {
    static RAISED: std::cell::Cell<i32> = const { std::cell::Cell::new(0) };
}
unsafe extern "C" fn raising_headers(
    headers: *const c::HeadHeaders,
    status: i32,
    data: *mut c_void,
) -> i32 {
    // SAFETY: the capture passes its live header view and the test's state.
    let rc = unsafe { headers_callback(headers, status, data) };
    if rc != 0 {
        RAISED.with(|raised| raised.set(last_raised()));
    }
    rc
}
fn check_response(
    state: &Arc<CallbackState>,
    capture: &Capture,
    status: i32,
    length: Option<&[u8]>,
) -> Result<(i32, TransferResult), Box<dyn std::error::Error>> {
    let names = [cursor(b"content-length")];
    let values = [cursor(length.unwrap_or_default())];
    // SAFETY: the cursors and the state outlive the synchronous capture,
    // which releases its headers before returning and retains nothing.
    let rc = unsafe {
        c::zaws_callback_capture(
            names.as_ptr(),
            values.as_ptr(),
            usize::from(length.is_some()),
            status,
            0,
            Some(raising_headers),
            None,
            data(state),
        )
    };
    let view = c::ResultView {
        error_code: if rc == 0 {
            0
        } else {
            RAISED.with(std::cell::Cell::get)
        },
        response_status: status,
        body: cursor(&[]),
        operation: cursor(&[]),
        region_header: cursor(&[]),
        region_header_present: false,
    };
    // SAFETY: the view and the state outlive the call, which retains neither.
    unsafe { finish_callback(&view, data(state)) };
    let result = lock(&capture.finished).pop().ok_or("a finished result")?;
    Ok((rc, result))
}

#[test]
fn a_get_checking_its_size_fails_on_a_response_of_another_or_no_length() -> TestResult {
    let _library = Library::acquire();
    let runtime = runtime()?;
    let cases: [(i32, Option<&[u8]>, bool); 8] = [
        (200, Some(b"7"), false),
        (200, Some(b"5"), true),
        (206, Some(b"9"), true),
        (404, Some(b"5"), false),
        (200, None, true),
        (206, None, true),
        (404, None, false),
        (200, Some(b"-1"), false),
    ];
    for (status, length, changed) in cases {
        let capture = Arc::new(Capture::default());
        let state = checked_state(&runtime, &capture, 7);
        let (rc, result) = check_response(&state, &capture, status, length)?;
        let case = format!("{status} {length:?}");
        assert_eq!(rc != 0, changed, "{case}");
        assert_eq!(result.size_changed, changed, "{case}");
        if changed {
            assert_eq!(result.error_code, SIZE_CHANGED_ERROR_CODE, "{case}");
            assert_eq!(result.crt_name.as_bytes(), b"AWS_ERROR_S3_OBJECT_MODIFIED");
        }
    }
    Ok(())
}

#[test]
fn a_size_change_only_describes_the_failure_it_caused() -> TestResult {
    let runtime = runtime()?;
    for (flagged, error_code) in [
        (true, CANCELED_ERROR_CODE),
        (false, SIZE_CHANGED_ERROR_CODE),
    ] {
        let capture = Arc::new(Capture::default());
        let state = checked_state(&runtime, &capture, 7);
        state.size_changed.store(flagged, Ordering::Release);
        let view = c::ResultView {
            error_code,
            response_status: 200,
            body: cursor(&[]),
            operation: cursor(&[]),
            region_header: cursor(&[]),
            region_header_present: false,
        };
        // SAFETY: the view and the state outlive the call, which retains neither.
        unsafe { finish_callback(&view, data(&state)) };
        let finished = lock(&capture.finished);
        assert!(!finished[0].size_changed, "{error_code}");
        assert_eq!(finished[0].error_code, error_code);
    }
    Ok(())
}

#[test]
fn an_unchecked_get_accepts_a_response_of_any_length() -> TestResult {
    let _library = Library::acquire();
    let runtime = runtime()?;
    let capture = Arc::new(Capture::default());
    let state = state(&runtime, &capture);
    let (rc, result) = check_response(&state, &capture, 200, Some(b"5"))?;
    assert_eq!(rc, 0);
    assert!(!result.size_changed);
    assert_eq!(result.error_code, 0);
    Ok(())
}
