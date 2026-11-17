//! Embedded payload access and the `_zippy_finder` import hook.

mod catalog;
mod import;
mod object;
mod payload;

use crate::ffi::{self as py, PyObject};
use object::{Owned, PyResult};
use pyload::View;
use std::ptr;

#[derive(Clone, Copy)]
struct State {
    view: Option<View<'static>>,
    blob_length: usize,
    module_spec: *mut PyObject,
    finder_type: *mut PyObject,
    finder: *mut PyObject,
}

// Only the main interpreter's GIL protects these pointers. No Rust reference to STATE
// is retained across a Python call, which may reenter the finder on the same thread.
static mut STATE: State = State {
    view: None,
    blob_length: 0,
    module_spec: ptr::null_mut(),
    finder_type: ptr::null_mut(),
    finder: ptr::null_mut(),
};

unsafe extern "C" {
    fn aws_python_finder_module() -> *mut PyObject;
    fn aws_python_finder_type() -> *mut PyObject;
}

/// Retain the builtin initialization symbol when linking the interpreter.
pub fn force_link() {
    std::hint::black_box(PyInit__zippy_finder as unsafe extern "C" fn() -> *mut PyObject);
}

/// Install or transactionally replace the immutable embedded payload.
///
/// Returns false with a Python exception set if validation or finder setup fails.
///
/// # Safety
/// The main interpreter must be initialized and its GIL held. Lifecycle calls must
/// not run concurrently or recursively. This module does not support subinterpreters.
/// Bytecode entries must be trusted and compiled by a compatible CPython; format and
/// code-object checks cannot validate the safety of bytecode execution.
pub unsafe fn install_payload(bytes: &'static [u8]) -> bool {
    install(bytes).is_some()
}

fn install(bytes: &'static [u8]) -> PyResult<()> {
    let view = object::payload_result(View::new(bytes))?;
    // SAFETY: install_payload requires the initialized main interpreter's GIL.
    unsafe {
        let _module = Owned::new(py::PyImport_ImportModule(c"_zippy_finder".as_ptr()))?;
        if STATE.module_spec.is_null() {
            let machinery = Owned::new(py::PyImport_ImportModule(c"importlib.machinery".as_ptr()))?;
            let spec = machinery.attr(c"ModuleSpec")?;
            STATE.module_spec = spec.into_ptr();
        }
        install_finder()?;
        STATE.view = Some(view);
        STATE.blob_length = bytes.len();
    }
    Some(())
}

fn install_finder() -> PyResult<()> {
    // SAFETY: the caller holds the GIL; local owned references survive reentrant calls.
    unsafe {
        let state = ptr::addr_of!(STATE).read();
        if state.finder_type.is_null() {
            return object::runtime_error(c"zippy: finder not initialized");
        }
        let sys = Owned::new(py::PyImport_ImportModule(c"sys".as_ptr()))?;
        let meta_path = sys.attr(c"meta_path")?;
        if state.finder.is_null() {
            let finder = Owned::new(py::PyObject_CallObject(state.finder_type, ptr::null_mut()))?;
            object::check(py::PyList_Insert(meta_path.as_ptr(), 0, finder.as_ptr()))?;
            STATE.finder = finder.into_ptr();
        } else {
            let contains = py::PySequence_Contains(meta_path.as_ptr(), state.finder);
            if contains < 0 {
                return None;
            }
            if contains == 0 {
                object::check(py::PyList_Insert(meta_path.as_ptr(), 0, state.finder))?;
            }
        }
    }
    Some(())
}

/// Clear interpreter-owned caches while retaining payload access for atexit imports.
///
/// # Safety
/// The initialized main interpreter's GIL must be held; call once before finalization.
pub unsafe fn prepare_for_interpreter_shutdown() {
    // SAFETY: caller holds the GIL. Clear before decref because decref can run Python.
    unsafe {
        let state = ptr::addr_of!(STATE).read();
        STATE.finder = ptr::null_mut();
        STATE.module_spec = ptr::null_mut();
        STATE.finder_type = ptr::null_mut();
        for object in [state.finder, state.module_spec, state.finder_type] {
            if !object.is_null() {
                py::Py_DecRef(object);
            }
        }
    }
}

/// Forget the payload after Python has completed its atexit callbacks.
///
/// # Safety
/// Finalization must have returned and no interpreter may access this module.
pub unsafe fn release_payload_view() {
    // SAFETY: caller guarantees exclusive lifecycle access after finalization.
    unsafe {
        STATE.view = None;
        STATE.blob_length = 0;
    }
}

/// Initialize the builtin module for CPython.
///
/// # Safety
/// Only CPython may call this entry point, while holding the main interpreter's GIL.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn PyInit__zippy_finder() -> *mut PyObject {
    initialize_module().map_or(ptr::null_mut(), Owned::into_ptr)
}

fn initialize_module() -> PyResult<Owned> {
    // SAFETY: CPython invokes this initializer with the GIL held.
    unsafe {
        let module = Owned::new(aws_python_finder_module())?;
        if STATE.finder_type.is_null() {
            STATE.finder_type = Owned::new(aws_python_finder_type())?.into_ptr();
        }
        let finder_type = Owned::borrowed(STATE.finder_type)?;
        object::check(py::PyObject_SetAttrString(
            module.as_ptr(),
            c"Finder".as_ptr(),
            finder_type.as_ptr(),
        ))?;
        Some(module)
    }
}

/// Dispatch a callback from the C method definitions.
///
/// # Safety
/// CPython supplies live arguments and self while holding the main interpreter's GIL.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn aws_python_finder_call(
    operation: i32,
    receiver: *mut PyObject,
    args: *mut PyObject,
) -> *mut PyObject {
    dispatch(operation, receiver, args).map_or(ptr::null_mut(), Owned::into_ptr)
}

fn dispatch(operation: i32, receiver: *mut PyObject, args: *mut PyObject) -> PyResult<Owned> {
    match operation {
        0 => payload::exists(args),
        1 => catalog::has_prefix(args),
        2 => catalog::list_prefix(args),
        3 => catalog::list_dir(args),
        4 => catalog::list_services(args),
        5 => catalog::list_api_versions(args),
        6 => payload::get_data(args),
        7 => payload::load_code(args),
        8 => payload::is_package(args),
        9 => payload::is_bytecode(args),
        10 => payload::stats(),
        11 => import::find_spec(receiver, args),
        12 => object::none(),
        13 => import::exec_module(args),
        _ => object::runtime_error(c"zippy: invalid callback"),
    }
}
