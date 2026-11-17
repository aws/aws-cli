use python_fallback::{configuration, ffi as py, finder, helpers};
use std::error::Error;
use std::ffi::{CStr, CString, c_char, c_int, c_void};
use std::ptr;
use std::sync::OnceLock;
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicUsize, Ordering};

type TestResult<T> = Result<T, Box<dyn Error>>;

pub struct Interpreter {
    active: bool,
}

impl Interpreter {
    pub fn new() -> TestResult<Self> {
        let argv = [c"python-module-harness".as_ptr()];
        let executable = CString::new(configuration::EXECUTABLE)?;
        let executable_pointer = if configuration::DYNAMIC {
            executable.as_ptr()
        } else {
            ptr::null()
        };
        let mut exit = 0;
        // SAFETY: this subprocess initializes CPython exactly once; all argument storage is live.
        let status = unsafe {
            py::aws_python_initialize(
                1,
                argv.as_ptr(),
                1,
                executable_pointer,
                1,
                helpers::STDIO_ENCODING.as_ptr(),
                helpers::STDIO_ERRORS.as_ptr(),
                &mut exit,
            )
        };
        if status != 0 {
            return Err(format!("initialization failed: {status}, exit {exit}").into());
        }
        let interpreter = Self { active: true };
        if configuration::DYNAMIC {
            set_text(c"EXPECTED_EXECUTABLE", &executable)?;
            run("import sys\nassert sys.executable == EXPECTED_EXECUTABLE\n\
                 assert sys.path\nassert '' not in sys.path")?;
        } else {
            run("import sys\nassert sys.path == []")?;
        }
        run("EXPECTED_SYS_PATH = list(sys.path)")?;
        Ok(interpreter)
    }

    pub fn finalize(&mut self) {
        assert!(self.active);
        // SAFETY: this harness still owns the main interpreter's GIL and all callbacks are idle.
        unsafe {
            finder::prepare_for_interpreter_shutdown();
            assert_eq!(py::Py_FinalizeEx(), 0);
            finder::release_payload_view();
        }
        self.active = false;
    }
}

impl Drop for Interpreter {
    fn drop(&mut self) {
        if self.active {
            self.finalize();
        }
    }
}

pub struct Object(*mut py::PyObject);

impl Object {
    pub unsafe fn new(pointer: *mut py::PyObject) -> TestResult<Self> {
        if pointer.is_null() {
            // SAFETY: callers own the interpreter's GIL and have just received an exception.
            unsafe { py::PyErr_Print() };
            Err("Python call failed".into())
        } else {
            Ok(Self(pointer))
        }
    }
}

impl Drop for Object {
    fn drop(&mut self) {
        // SAFETY: every object is destroyed before interpreter finalization with the GIL held.
        unsafe { py::Py_DecRef(self.0) };
    }
}

pub fn run(source: &str) -> TestResult<()> {
    let source = CString::new(source)?;
    // SAFETY: initialized main interpreter, GIL held, live source and module references.
    unsafe {
        let module = py::PyImport_AddModule(c"__main__".as_ptr());
        assert!(!module.is_null());
        let dictionary = py::PyModule_GetDict(module);
        let _result = Object::new(py::PyRun_StringFlags(
            source.as_ptr(),
            py::PY_FILE_INPUT,
            dictionary,
            dictionary,
            ptr::null_mut(),
        ))?;
    }
    expect_clear();
    Ok(())
}

unsafe extern "C" {
    fn Py_NewInterpreter() -> *mut c_void;
    fn Py_EndInterpreter(state: *mut c_void);
    fn PyThreadState_Get() -> *mut c_void;
    fn PyThreadState_Swap(state: *mut c_void) -> *mut c_void;
    fn PyRun_SimpleStringFlags(command: *const c_char, flags: *mut c_void) -> c_int;
}

pub fn run_in_subinterpreter(source: &str) -> TestResult<()> {
    let source = CString::new(source)?;
    // SAFETY: the main thread holds the GIL; the new thread state is current
    // until it ends, and the main thread state is restored afterward.
    let status = unsafe {
        let main = PyThreadState_Get();
        let state = Py_NewInterpreter();
        assert!(!state.is_null());
        let status = PyRun_SimpleStringFlags(source.as_ptr(), ptr::null_mut());
        Py_EndInterpreter(state);
        PyThreadState_Swap(main);
        status
    };
    expect_clear();
    if status == 0 {
        Ok(())
    } else {
        Err("subinterpreter source raised".into())
    }
}

pub fn expected(entries: usize, bytes: usize) -> TestResult<()> {
    run(&format!(
        "EXPECTED_ENTRY_COUNT = {entries}\nEXPECTED_BLOB_LENGTH = {bytes}"
    ))
}

pub fn set_text(name: &CStr, text: &CStr) -> TestResult<()> {
    // SAFETY: initialized interpreter, held GIL, and nul-terminated strings live through the calls.
    unsafe {
        let module = py::PyImport_AddModule(c"__main__".as_ptr());
        assert!(!module.is_null());
        let value = Object::new(py::PyUnicode_FromString(text.as_ptr()))?;
        let dictionary = py::PyModule_GetDict(module);
        assert_eq!(
            py::PyDict_SetItemString(dictionary, name.as_ptr(), value.0),
            0
        );
    }
    Ok(())
}

pub fn marshal_code(source: &CStr) -> TestResult<Vec<u8>> {
    // SAFETY: initialized interpreter, GIL held, and both source and filename are valid C strings.
    unsafe {
        let code = Object::new(py::aws_python_compile(
            source.as_ptr(),
            c"<python-module-harness>".as_ptr(),
            py::PY_FILE_INPUT,
        ))?;
        marshal(code.0)
    }
}

pub fn marshal_none() -> TestResult<Vec<u8>> {
    // SAFETY: the None singleton is live under the GIL throughout serialization.
    unsafe { marshal(py::aws_python_none()) }
}

unsafe fn marshal(object: *mut py::PyObject) -> TestResult<Vec<u8>> {
    // SAFETY: caller provides a live Python object and holds the initialized interpreter's GIL.
    unsafe {
        // CPython 3.14 uses marshal version 5, including support for slice objects.
        let bytes = Object::new(py::PyMarshal_WriteObjectToString(object, 5))?;
        let pointer = py::PyBytes_AsString(bytes.0);
        let length = py::PyBytes_Size(bytes.0);
        assert!(!pointer.is_null() && length >= 0);
        Ok(std::slice::from_raw_parts(pointer.cast(), length as usize).to_vec())
    }
}

pub unsafe fn expect_exception(exception: *mut py::PyObject) {
    // SAFETY: caller supplies an initialized exception class and holds the GIL.
    unsafe {
        assert!(!py::PyErr_Occurred().is_null());
        assert_ne!(py::PyErr_ExceptionMatches(exception), 0);
        py::PyErr_Clear();
    }
}

pub fn expect_clear() {
    // SAFETY: all callers hold the initialized interpreter's GIL.
    assert!(unsafe { py::PyErr_Occurred() }.is_null());
}

pub fn main_global(name: &CStr) -> TestResult<*mut py::PyObject> {
    // SAFETY: initialized interpreter, held GIL, and a nul-terminated name.
    let value = unsafe {
        let module = py::PyImport_AddModule(c"__main__".as_ptr());
        assert!(!module.is_null());
        py::PyDict_GetItemString(py::PyModule_GetDict(module), name.as_ptr())
    };
    if value.is_null() {
        return Err(format!("__main__ has no {name:?}").into());
    }
    Ok(value)
}

pub fn main_size(name: &CStr) -> TestResult<usize> {
    let value = main_global(name)?;
    // SAFETY: the borrowed integer lives in `__main__` and the harness holds the GIL.
    let value = unsafe { py::PyLong_AsLongLong(value) };
    expect_clear();
    Ok(usize::try_from(value)?)
}

/// CPython's `PyMemAllocatorEx`, laid out as `cpython/pymem.h` declares it.
#[repr(C)]
#[derive(Clone, Copy)]
struct Allocator {
    context: *mut c_void,
    malloc: Option<unsafe extern "C" fn(*mut c_void, usize) -> *mut c_void>,
    calloc: Option<unsafe extern "C" fn(*mut c_void, usize, usize) -> *mut c_void>,
    realloc: Option<unsafe extern "C" fn(*mut c_void, *mut c_void, usize) -> *mut c_void>,
    free: Option<unsafe extern "C" fn(*mut c_void, *mut c_void)>,
}

// SAFETY: the harness reads the wrapped allocator only on its one thread, under the GIL;
// CPython's allocator functions and context outlive the interpreter.
unsafe impl Send for Allocator {}
// SAFETY: as for `Send`; the stored allocator is never written after it is recorded.
unsafe impl Sync for Allocator {}

/// `PYMEM_DOMAIN_OBJ`, the domain `PyObject_Malloc` allocates from.
const OBJECT_DOMAIN: c_int = 2;

unsafe extern "C" {
    static mut PyExc_MemoryError: *mut py::PyObject;
    fn PyMem_GetAllocator(domain: c_int, allocator: *mut Allocator);
    fn PyMem_SetAllocator(domain: c_int, allocator: *mut Allocator);
}

static WRAPPED: OnceLock<Allocator> = OnceLock::new();
static FAIL_SIZE: AtomicUsize = AtomicUsize::new(0);
static FAILURES: AtomicU32 = AtomicU32::new(0);
static COUNTDOWN_ARMED: AtomicBool = AtomicBool::new(false);
static COUNTDOWN_REMAINING: AtomicUsize = AtomicUsize::new(0);

unsafe extern "C" fn sized_malloc(context: *mut c_void, size: usize) -> *mut c_void {
    let armed = FAIL_SIZE.compare_exchange(size, 0, Ordering::Relaxed, Ordering::Relaxed);
    if size != 0 && armed.is_ok() {
        FAILURES.fetch_add(1, Ordering::Relaxed);
        return ptr::null_mut();
    }
    // SAFETY: CPython calls the hook as its own malloc, with its own context.
    unsafe { forward_malloc(context, size) }
}

unsafe extern "C" fn countdown_malloc(context: *mut c_void, size: usize) -> *mut c_void {
    if COUNTDOWN_ARMED.load(Ordering::Relaxed) {
        let remaining = COUNTDOWN_REMAINING.load(Ordering::Relaxed);
        if remaining == 0 {
            COUNTDOWN_ARMED.store(false, Ordering::Relaxed);
            return ptr::null_mut();
        }
        COUNTDOWN_REMAINING.store(remaining - 1, Ordering::Relaxed);
    }
    // SAFETY: CPython calls the hook as its own malloc, with its own context.
    unsafe { forward_malloc(context, size) }
}

unsafe fn forward_malloc(context: *mut c_void, size: usize) -> *mut c_void {
    match WRAPPED.get().and_then(|allocator| allocator.malloc) {
        // SAFETY: the wrapped allocator is CPython's, called with the context it was given.
        Some(malloc) => unsafe { malloc(context, size) },
        None => ptr::null_mut(),
    }
}

fn with_object_malloc<T>(
    hook: unsafe extern "C" fn(*mut c_void, usize) -> *mut c_void,
    call: impl FnOnce() -> T,
) -> T {
    let wrapped = *WRAPPED.get_or_init(|| {
        let mut allocator = Allocator {
            context: ptr::null_mut(),
            malloc: None,
            calloc: None,
            realloc: None,
            free: None,
        };
        // SAFETY: the harness holds the GIL; CPython fills the live allocator record.
        unsafe { PyMem_GetAllocator(OBJECT_DOMAIN, &mut allocator) };
        allocator
    });
    let mut hooked = Allocator {
        malloc: Some(hook),
        ..wrapped
    };
    let mut restored = wrapped;
    // SAFETY: the hook forwards to the allocator it replaces, so every block it serves is one
    // CPython's own functions may free; the GIL is held while the domain is swapped.
    unsafe { PyMem_SetAllocator(OBJECT_DOMAIN, &mut hooked) };
    let result = call();
    // SAFETY: as above; this restores the allocator the domain had before.
    unsafe { PyMem_SetAllocator(OBJECT_DOMAIN, &mut restored) };
    result
}

pub fn fail_object_allocation_of_size<T>(size: usize, call: impl FnOnce() -> T) -> (T, u32) {
    FAILURES.store(0, Ordering::Relaxed);
    FAIL_SIZE.store(size, Ordering::Relaxed);
    let result = with_object_malloc(sized_malloc, call);
    FAIL_SIZE.store(0, Ordering::Relaxed);
    (result, FAILURES.load(Ordering::Relaxed))
}

pub fn fail_object_allocation_after<T>(served: usize, call: impl FnOnce() -> T) -> (T, bool) {
    COUNTDOWN_REMAINING.store(served, Ordering::Relaxed);
    COUNTDOWN_ARMED.store(true, Ordering::Relaxed);
    let result = with_object_malloc(countdown_malloc, call);
    let failed = !COUNTDOWN_ARMED.swap(false, Ordering::Relaxed);
    (result, failed)
}

pub fn expect_memory_error() {
    // SAFETY: the exception global belongs to the initialized interpreter; the GIL is held.
    unsafe { expect_exception(PyExc_MemoryError) };
}
