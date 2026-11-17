use crate::ffi::{self as py, PyObject};
use std::ffi::CStr;
use std::marker::PhantomData;
use std::ptr::NonNull;

pub(super) type PyResult<T> = Option<T>;

pub(super) struct Owned {
    pointer: NonNull<PyObject>,
    _thread_bound: PhantomData<*mut ()>,
}

impl Owned {
    pub(super) unsafe fn new(pointer: *mut PyObject) -> PyResult<Self> {
        Some(Self {
            pointer: NonNull::new(pointer)?,
            _thread_bound: PhantomData,
        })
    }

    pub(super) unsafe fn borrowed(pointer: *mut PyObject) -> PyResult<Self> {
        // SAFETY: caller guarantees a live borrowed reference and the GIL.
        let object = unsafe { Self::new(pointer) }?;
        // SAFETY: new validated that the borrowed object is non-null.
        unsafe { py::Py_IncRef(pointer) };
        Some(object)
    }

    pub(super) fn as_ptr(&self) -> *mut PyObject {
        self.pointer.as_ptr()
    }

    pub(super) fn into_ptr(self) -> *mut PyObject {
        let pointer = self.as_ptr();
        std::mem::forget(self);
        pointer
    }

    pub(super) fn attr(&self, name: &CStr) -> PyResult<Self> {
        // SAFETY: owned object remains live and every caller holds the GIL.
        unsafe { Self::new(py::PyObject_GetAttrString(self.as_ptr(), name.as_ptr())) }
    }

    pub(super) fn set_attr(&self, name: &CStr, value: &Self) -> PyResult<()> {
        // SAFETY: both owned references and the nul-terminated name are live.
        check(unsafe { py::PyObject_SetAttrString(self.as_ptr(), name.as_ptr(), value.as_ptr()) })
    }

    pub(super) fn unicode(&self) -> PyResult<&[u8]> {
        let mut length = 0;
        // SAFETY: CPython checks the type and owns the UTF-8 buffer for this object's lifetime.
        let pointer = unsafe { py::PyUnicode_AsUTF8AndSize(self.as_ptr(), &mut length) };
        if pointer.is_null() {
            return None;
        }
        // SAFETY: successful CPython conversion returns a live buffer and nonnegative length.
        Some(unsafe { std::slice::from_raw_parts(pointer.cast(), length as usize) })
    }

    pub(super) fn append(&self, value: &Self) -> PyResult<()> {
        // SAFETY: CPython validates the list, and both objects remain live.
        check(unsafe { py::PyList_Append(self.as_ptr(), value.as_ptr()) })
    }

    pub(super) fn dict_set(&self, key: &CStr, value: &Self) -> PyResult<()> {
        // SAFETY: CPython validates the dict; key and value remain live through the call.
        check(unsafe { py::PyDict_SetItemString(self.as_ptr(), key.as_ptr(), value.as_ptr()) })
    }
}

impl Drop for Owned {
    fn drop(&mut self) {
        // SAFETY: owned references are confined to initialized interpreter calls with the GIL.
        unsafe { py::Py_DecRef(self.as_ptr()) };
    }
}

pub(super) fn check(status: i32) -> PyResult<()> {
    (status == 0).then_some(())
}

pub(super) fn none() -> PyResult<Owned> {
    // SAFETY: called only with the GIL; the interpreter owns its None singleton.
    unsafe { Owned::borrowed(py::aws_python_none()) }
}

pub(super) fn boolean(value: bool) -> PyResult<Owned> {
    // SAFETY: every entrypoint holds the initialized interpreter's GIL.
    unsafe { Owned::new(py::PyBool_FromLong(value.into())) }
}

pub(super) fn string(value: &[u8]) -> PyResult<Owned> {
    let length = size(value.len())?;
    // SAFETY: CPython copies the live, length-checked bytes while the GIL is held.
    unsafe {
        Owned::new(py::PyUnicode_FromStringAndSize(
            value.as_ptr().cast(),
            length,
        ))
    }
}

pub(super) fn list() -> PyResult<Owned> {
    // SAFETY: every entrypoint holds the initialized interpreter's GIL.
    unsafe { Owned::new(py::PyList_New(0)) }
}

pub(super) fn dict() -> PyResult<Owned> {
    // SAFETY: every entrypoint holds the initialized interpreter's GIL.
    unsafe { Owned::new(py::PyDict_New()) }
}

pub(super) fn number(value: usize) -> PyResult<Owned> {
    // SAFETY: every entrypoint holds the initialized interpreter's GIL.
    unsafe { Owned::new(py::PyLong_FromUnsignedLongLong(value as u64)) }
}

pub(super) fn size(length: usize) -> PyResult<isize> {
    crate::helpers::checked_python_size(length).or_else(|| overflow(c"zippy: integer overflow"))
}

pub(super) fn runtime_error<T>(message: &CStr) -> PyResult<T> {
    // SAFETY: exception globals belong to the initialized interpreter, with the GIL held.
    unsafe { py::PyErr_SetString(py::PyExc_RuntimeError, message.as_ptr()) };
    None
}

pub(super) fn overflow<T>(message: &CStr) -> PyResult<T> {
    // SAFETY: exception globals belong to the initialized interpreter, with the GIL held.
    unsafe { py::PyErr_SetString(py::PyExc_OverflowError, message.as_ptr()) };
    None
}

pub(super) fn payload_result<T>(result: Result<T, pyload::Error>) -> PyResult<T> {
    result
        .ok()
        .or_else(|| runtime_error(c"zippy: invalid payload"))
}

pub(super) fn args(args: *mut PyObject, format: &CStr) -> PyResult<[Owned; 3]> {
    // SAFETY: callback args is a live tuple; ParseTuple writes only these three pointers.
    unsafe {
        let mut values = [py::aws_python_none(); 3];
        let [first, second, third] = &mut values;
        let status = py::PyArg_ParseTuple(args, format.as_ptr(), first, second, third);
        if status == 0 {
            return None;
        }
        Some([
            Owned::borrowed(values[0])?,
            Owned::borrowed(values[1])?,
            Owned::borrowed(values[2])?,
        ])
    }
}

pub(super) fn view() -> PyResult<pyload::View<'static>> {
    // SAFETY: every entrypoint holds the GIL and the view borrows static immutable bytes.
    unsafe { super::STATE.view }.or_else(|| runtime_error(c"zippy: payload not loaded"))
}

/// The root of every synthetic module filename and vendored package search location.
///
/// The AWS CLI derives data, metadata, and package paths from `__file__`, so
/// the root is absolute, keeping every derived path out of the working
/// directory, and holds no `os.pathsep` character, so a derived search path
/// never splits into extra entries. Nothing can exist under it: creating
/// `/<zippy>` takes root on POSIX, and Windows names cannot hold `<` or `>`.
pub(super) const SYNTHETIC_ROOT: &[u8] = b"/<zippy>";

const _: () = {
    assert!(SYNTHETIC_ROOT[0] == b'/');
    let mut index = 0;
    while index < SYNTHETIC_ROOT.len() {
        assert!(SYNTHETIC_ROOT[index] != b':' && SYNTHETIC_ROOT[index] != b';');
        index += 1;
    }
};

const SYNTHETIC_PATH_MAX: usize = 1024;

pub(super) fn synthetic_file(name: &[u8], package: bool) -> PyResult<Owned> {
    let bytes = synthetic_path(name, package).or_else(|| overflow(c"module name too long"))?;
    string(&bytes)
}

fn synthetic_path(name: &[u8], package: bool) -> Option<Vec<u8>> {
    let suffix: &[u8] = if package { b"/__init__.py" } else { b".py" };
    let mut bytes = joined::<SYNTHETIC_PATH_MAX>(&[SYNTHETIC_ROOT, b"/", name, suffix])?;
    let start = SYNTHETIC_ROOT.len() + 1;
    for byte in &mut bytes[start..start + name.len()] {
        if *byte == b'.' {
            *byte = b'/';
        }
    }
    Some(bytes)
}

pub(super) fn bounded<const LIMIT: usize>(parts: &[&[u8]], message: &CStr) -> PyResult<Vec<u8>> {
    joined::<LIMIT>(parts).or_else(|| overflow(message))
}

fn joined<const LIMIT: usize>(parts: &[&[u8]]) -> Option<Vec<u8>> {
    let length = parts
        .iter()
        .try_fold(0_usize, |length, part| length.checked_add(part.len()))
        .filter(|length| *length <= LIMIT)?;
    let mut output = Vec::with_capacity(length);
    for part in parts {
        output.extend_from_slice(part);
    }
    Some(output)
}

#[cfg(test)]
mod tests;
