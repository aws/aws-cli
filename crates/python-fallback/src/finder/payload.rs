use super::object::{self, Owned, PyResult};
use crate::ffi::{self as py, PyObject};
use pyload::{Entry, View};
use std::mem::MaybeUninit;
use std::ptr::NonNull;

pub(super) fn exists(args: *mut PyObject) -> PyResult<Owned> {
    let args = object::args(args, c"O")?;
    let name = args[0].unicode()?;
    let entry = object::payload_result(object::view()?.find(name))?;
    object::boolean(entry.is_some())
}

pub(super) fn is_bytecode(args: *mut PyObject) -> PyResult<Owned> {
    let args = object::args(args, c"O")?;
    let name = args[0].unicode()?;
    let entry = object::payload_result(object::view()?.find(name))?;
    object::boolean(entry.is_some_and(|entry| entry.entry.is_bytecode()))
}

pub(super) fn is_package(args: *mut PyObject) -> PyResult<Owned> {
    object::boolean(find_entry(args)?.is_package())
}

fn find_entry(args: *mut PyObject) -> PyResult<Entry<'static>> {
    let args = object::args(args, c"O")?;
    let name = args[0].unicode()?;
    let entry = object::payload_result(object::view()?.find(name))?;
    entry.map(|entry| entry.entry).or_else(|| {
        // SAFETY: callbacks hold the GIL and the exception class belongs to this interpreter.
        unsafe {
            py::PyErr_SetString(
                py::PyExc_FileNotFoundError,
                c"zippy: entry not found".as_ptr(),
            )
        };
        None
    })
}

pub(super) fn get_data(args: *mut PyObject) -> PyResult<Owned> {
    let entry = find_entry(args)?;
    let data = bytes(object::view()?, entry)?;
    let bytes = data.as_slice();
    let length = object::size(bytes.len())?;
    // SAFETY: CPython copies the live and length-checked buffer while holding the GIL.
    unsafe { Owned::new(py::PyBytes_FromStringAndSize(bytes.as_ptr().cast(), length)) }
}

pub(super) fn load_code(args: *mut PyObject) -> PyResult<Owned> {
    let entry = find_entry(args)?;
    if !entry.is_bytecode() {
        // SAFETY: callbacks hold the GIL and this exception class is initialized.
        unsafe {
            py::PyErr_SetString(
                py::PyExc_ImportError,
                c"zippy: entry is not bytecode".as_ptr(),
            )
        };
        return None;
    }
    read_code(object::view()?, entry)
}

pub(super) fn read_code(view: View<'static>, entry: Entry<'static>) -> PyResult<Owned> {
    let data = bytes(view, entry)?;
    let bytes = data.as_slice();
    let length = object::size(bytes.len())?;
    // SAFETY: marshal reads a live buffer; CPython validates the serialized object.
    unsafe {
        let code = Owned::new(py::PyMarshal_ReadObjectFromString(
            bytes.as_ptr().cast(),
            length,
        ))?;
        if py::aws_python_is_code(code.as_ptr()) == 0 {
            py::PyErr_SetString(py::PyExc_ImportError, c"zippy: invalid bytecode".as_ptr());
            return None;
        }
        Some(code)
    }
}

pub(super) fn stats() -> PyResult<Owned> {
    let view = object::view()?;
    let dictionary = object::dict()?;
    dictionary.dict_set(c"entry_count", &object::number(view.entry_count())?)?;
    // SAFETY: the main interpreter's GIL serializes the payload metadata.
    let blob_length = unsafe { super::STATE.blob_length };
    dictionary.dict_set(c"blob_length", &object::number(blob_length)?)?;
    Some(dictionary)
}

enum Bytes {
    Stored(&'static [u8]),
    Decoded(PythonBuffer),
}

impl Bytes {
    fn as_slice(&self) -> &[u8] {
        match self {
            Self::Stored(bytes) => bytes,
            Self::Decoded(buffer) => buffer.as_slice(),
        }
    }
}

struct PythonBuffer {
    pointer: NonNull<u8>,
    length: usize,
}

impl PythonBuffer {
    fn new(length: usize) -> PyResult<Self> {
        // SAFETY: called with the GIL; allocate one byte even for an empty output buffer.
        let pointer = unsafe { py::PyMem_Malloc(length.max(1)) }.cast::<u8>();
        let Some(pointer) = NonNull::new(pointer) else {
            // SAFETY: PyErr_NoMemory sets the current interpreter's exception under the GIL.
            unsafe { py::PyErr_NoMemory() };
            return None;
        };
        Some(Self { pointer, length })
    }

    fn as_slice(&self) -> &[u8] {
        // SAFETY: the initialized allocation belongs to self and survives this borrow.
        unsafe { std::slice::from_raw_parts(self.pointer.as_ptr(), self.length) }
    }

    fn as_mut_slice(&mut self) -> &mut [u8] {
        // SAFETY: the allocation belongs exclusively to self. Initialize before exposing a slice.
        unsafe {
            self.pointer.as_ptr().write_bytes(0, self.length);
            std::slice::from_raw_parts_mut(self.pointer.as_ptr(), self.length)
        }
    }

    fn as_uninit_mut_slice(&mut self) -> &mut [MaybeUninit<u8>] {
        // SAFETY: the allocation belongs exclusively to self, and uninitialized bytes are valid
        // `MaybeUninit<u8>` values.
        unsafe {
            std::slice::from_raw_parts_mut(
                self.pointer.as_ptr().cast::<MaybeUninit<u8>>(),
                self.length,
            )
        }
    }
}

impl Drop for PythonBuffer {
    fn drop(&mut self) {
        // SAFETY: this pointer was allocated by PyMem_Malloc and remains under the same GIL.
        unsafe { py::PyMem_Free(self.pointer.as_ptr().cast()) };
    }
}

fn bytes(view: View<'static>, entry: Entry<'static>) -> PyResult<Bytes> {
    let stored = object::payload_result(view.stored_bytes(entry))?;
    if !entry.is_compressed() {
        return Some(Bytes::Stored(stored));
    }
    let length = usize::try_from(entry.uncompressed_len)
        .ok()
        .or_else(|| object::overflow(c"zippy: integer overflow"))?;
    let mut output = PythonBuffer::new(length)?;
    let mut scratch = PythonBuffer::new(pyload::decompress::ZSTD_BUFFER_LEN)?;
    let decoded = pyload::decompress::decode_zstd(
        stored,
        output.as_mut_slice(),
        scratch.as_uninit_mut_slice(),
    );
    if decoded.is_err() {
        // SAFETY: callback holds the GIL and the OSError exception class is initialized.
        unsafe { py::PyErr_SetString(py::PyExc_OSError, c"zippy: payload read failed".as_ptr()) };
        return None;
    }
    Some(Bytes::Decoded(output))
}
