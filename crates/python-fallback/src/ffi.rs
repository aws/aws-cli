//! Raw CPython 3.14 calls. Object, configuration, and type layouts remain in C.

use std::ffi::{c_char, c_int, c_long, c_longlong, c_ulong, c_ulonglong, c_void};
use std::marker::{PhantomData, PhantomPinned};

/// Opaque interpreter-owned object; usable only while its interpreter and GIL are held.
#[derive(Debug)]
#[repr(C)]
pub struct PyObject {
    _opaque: [u8; 0],
    _marker: PhantomData<(*mut u8, PhantomPinned)>,
}

/// CPython's statement-suite input selector, defined in `compile.h`.
pub const PY_FILE_INPUT: c_int = 257;
/// CPython's expression input selector, defined in `compile.h`.
pub const PY_EVAL_INPUT: c_int = 258;

unsafe extern "C" {
    #[cfg(windows)]
    pub fn aws_python_initialize_wide(
        argc: c_int,
        argv: *const *const u16,
        harness: c_int,
        executable: *const c_char,
        embedded_payload: c_int,
        stdio_encoding: *const c_char,
        stdio_errors: *const c_char,
        exit_code: *mut c_int,
    ) -> c_int;
    pub fn aws_python_initialize(
        argc: c_int,
        argv: *const *const c_char,
        harness: c_int,
        executable: *const c_char,
        embedded_payload: c_int,
        stdio_encoding: *const c_char,
        stdio_errors: *const c_char,
        exit_code: *mut c_int,
    ) -> c_int;
    pub fn aws_python_none() -> *mut PyObject;
    pub fn aws_python_is_long(object: *mut PyObject) -> c_int;
    pub fn aws_python_is_list(object: *mut PyObject) -> c_int;
    pub fn aws_python_is_unicode(object: *mut PyObject) -> c_int;
    pub fn aws_python_is_code(object: *mut PyObject) -> c_int;
    pub fn aws_python_compile(
        source: *const c_char,
        filename: *const c_char,
        start: c_int,
    ) -> *mut PyObject;

    pub fn Py_IncRef(object: *mut PyObject);
    pub fn Py_DecRef(object: *mut PyObject);
    pub fn Py_IsInitialized() -> c_int;
    pub fn Py_FinalizeEx() -> c_int;
    pub fn PyArg_ParseTuple(args: *mut PyObject, format: *const c_char, ...) -> c_int;
    pub fn PyErr_Clear();
    pub fn PyErr_Print();
    pub fn PyErr_NoMemory() -> *mut PyObject;
    pub fn PyErr_Occurred() -> *mut PyObject;
    pub fn aws_python_take_raised_exception() -> *mut PyObject;
    pub fn PyErr_ExceptionMatches(exception: *mut PyObject) -> c_int;
    pub fn PyErr_SetString(exception: *mut PyObject, message: *const c_char);
    pub static mut PyExc_SystemExit: *mut PyObject;
    pub static mut PyExc_RuntimeError: *mut PyObject;
    pub static mut PyExc_OverflowError: *mut PyObject;
    pub static mut PyExc_FileNotFoundError: *mut PyObject;
    pub static mut PyExc_ImportError: *mut PyObject;
    pub static mut PyExc_OSError: *mut PyObject;
    pub fn PyLong_AsLongLong(object: *mut PyObject) -> c_longlong;
    pub fn PyLong_FromUnsignedLong(value: c_ulong) -> *mut PyObject;
    pub fn PyLong_FromUnsignedLongLong(value: c_ulonglong) -> *mut PyObject;
    pub fn PyBool_FromLong(value: c_long) -> *mut PyObject;
    pub fn PyUnicode_AsUTF8(object: *mut PyObject) -> *const c_char;
    pub fn PyUnicode_AsUTF8AndSize(object: *mut PyObject, length: *mut isize) -> *const c_char;
    pub fn PyUnicode_FromString(string: *const c_char) -> *mut PyObject;
    pub fn PyUnicode_FromStringAndSize(string: *const c_char, length: isize) -> *mut PyObject;
    pub fn PyBytes_FromStringAndSize(bytes: *const c_char, length: isize) -> *mut PyObject;
    pub fn PyBytes_AsString(object: *mut PyObject) -> *mut c_char;
    pub fn PyBytes_Size(object: *mut PyObject) -> isize;
    pub fn PyObject_Str(object: *mut PyObject) -> *mut PyObject;
    pub fn PyObject_GetAttrString(object: *mut PyObject, name: *const c_char) -> *mut PyObject;
    pub fn PyObject_SetAttrString(
        object: *mut PyObject,
        name: *const c_char,
        value: *mut PyObject,
    ) -> c_int;
    pub fn PyObject_Call(
        callable: *mut PyObject,
        args: *mut PyObject,
        keywords: *mut PyObject,
    ) -> *mut PyObject;
    pub fn PyObject_CallObject(callable: *mut PyObject, args: *mut PyObject) -> *mut PyObject;
    pub fn PyModule_GetDict(module: *mut PyObject) -> *mut PyObject;
    pub fn PyModule_AddObject(
        module: *mut PyObject,
        name: *const c_char,
        value: *mut PyObject,
    ) -> c_int;
    pub fn PyDict_New() -> *mut PyObject;
    pub fn PyDict_SetItemString(
        dictionary: *mut PyObject,
        key: *const c_char,
        value: *mut PyObject,
    ) -> c_int;
    pub fn PyDict_GetItemString(dictionary: *mut PyObject, key: *const c_char) -> *mut PyObject;
    pub fn PyTuple_Pack(count: isize, ...) -> *mut PyObject;
    pub fn PyList_New(length: isize) -> *mut PyObject;
    pub fn PyList_Append(list: *mut PyObject, item: *mut PyObject) -> c_int;
    pub fn PyList_Insert(list: *mut PyObject, index: isize, item: *mut PyObject) -> c_int;
    pub fn PyList_Size(list: *mut PyObject) -> isize;
    pub fn PyList_GetItem(list: *mut PyObject, index: isize) -> *mut PyObject;
    pub fn PySequence_Contains(sequence: *mut PyObject, item: *mut PyObject) -> c_int;
    pub fn PyImport_AddModule(name: *const c_char) -> *mut PyObject;
    pub fn PyImport_ImportModule(name: *const c_char) -> *mut PyObject;
    pub fn PyImport_GetMagicNumber() -> c_long;
    pub fn PyMarshal_ReadObjectFromString(data: *const c_char, length: isize) -> *mut PyObject;
    pub fn PyMarshal_WriteObjectToString(object: *mut PyObject, version: c_int) -> *mut PyObject;
    pub fn PyEval_GetBuiltins() -> *mut PyObject;
    pub fn PyEval_EvalCode(
        code: *mut PyObject,
        globals: *mut PyObject,
        locals: *mut PyObject,
    ) -> *mut PyObject;
    pub fn PyRun_StringFlags(
        source: *const c_char,
        start: c_int,
        globals: *mut PyObject,
        locals: *mut PyObject,
        flags: *mut c_void,
    ) -> *mut PyObject;
    pub fn PySys_GetObject(name: *const c_char) -> *mut PyObject;
    pub fn PySys_SetObject(name: *const c_char, value: *mut PyObject) -> c_int;
    pub fn PySys_WriteStderr(format: *const c_char, ...);
    pub fn PyMem_Malloc(size: usize) -> *mut c_void;
    pub fn PyMem_Free(pointer: *mut c_void);
}
