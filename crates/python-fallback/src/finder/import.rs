use super::catalog::lookup_parts;
use super::object::{self, Owned, PyResult};
use super::payload;
use crate::ffi::{self as py, PyObject};
use pyload::Entry;

const VENDORED_MARKER: &[u8] = b"/<zippy>/__ZIPPY_VENDORED__/";

const _: () = {
    let mut index = 0;
    while index < object::SYNTHETIC_ROOT.len() {
        assert!(VENDORED_MARKER[index] == object::SYNTHETIC_ROOT[index]);
        index += 1;
    }
};

pub(super) fn find_spec(receiver: *mut PyObject, args: *mut PyObject) -> PyResult<Owned> {
    let args = object::args(args, c"O|OO")?;
    let fullname = args[0].unicode()?;
    let vendored = lookup_name(fullname, &args[1])?;
    let lookup = vendored.as_deref().unwrap_or(fullname);
    let view = object::view()?;
    let Some(entry) = object::payload_result(view.find(lookup))? else {
        return object::none();
    };
    if !entry.entry.is_bytecode() {
        return object::none();
    }
    let spec = create_spec(receiver, &args[0], entry.entry.is_package())?;
    configure_spec(&spec, entry.entry.is_package(), vendored.as_deref())?;
    Some(spec)
}

fn lookup_name(fullname: &[u8], path: &Owned) -> PyResult<Option<Vec<u8>>> {
    // SAFETY: the None singleton is live under the callback's GIL.
    if path.as_ptr() == unsafe { py::aws_python_none() } {
        return Some(None);
    }
    if let Some(lookup) = lookup_path(fullname, path)? {
        return Some(Some(lookup));
    }
    if fullname == b"botocore" || fullname == b"s3transfer" {
        return Some(Some(lookup_parts(&[b"awscli.", fullname])?));
    }
    Some(None)
}

fn lookup_path(fullname: &[u8], path: &Owned) -> PyResult<Option<Vec<u8>>> {
    // SAFETY: borrowed list elements remain live through path's owned reference.
    unsafe {
        if py::aws_python_is_list(path.as_ptr()) == 0 || py::PyList_Size(path.as_ptr()) <= 0 {
            return Some(None);
        }
        let first = py::PyList_GetItem(path.as_ptr(), 0);
        if first.is_null() || py::aws_python_is_unicode(first) == 0 {
            return Some(None);
        }
        let first = Owned::borrowed(first)?;
        if let Some(prefix) = first.unicode()?.strip_prefix(VENDORED_MARKER)
            && !prefix.is_empty()
        {
            let leaf = fullname
                .rsplit(|byte| *byte == b'.')
                .next()
                .unwrap_or(fullname);
            return Some(Some(lookup_parts(&[prefix, b".", leaf])?));
        }
    }
    Some(None)
}

fn create_spec(receiver: *mut PyObject, name: &Owned, package: bool) -> PyResult<Owned> {
    // SAFETY: GIL protects the cache, and the borrowed reference holds it across Python calls.
    let module_spec = unsafe { Owned::borrowed(super::STATE.module_spec) }
        .or_else(|| object::runtime_error(c"zippy: finder not initialized"))?;
    let origin = object::synthetic_file(name.unicode()?, package)?;
    let keywords = object::dict()?;
    keywords.dict_set(c"origin", &origin)?;
    keywords.dict_set(c"is_package", &object::boolean(package)?)?;
    // SAFETY: both positional objects remain live and all calls hold the interpreter's GIL.
    unsafe {
        let positional = Owned::new(py::PyTuple_Pack(2, name.as_ptr(), receiver))?;
        Owned::new(py::PyObject_Call(
            module_spec.as_ptr(),
            positional.as_ptr(),
            keywords.as_ptr(),
        ))
    }
}

fn configure_spec(spec: &Owned, package: bool, vendored: Option<&[u8]>) -> PyResult<()> {
    if let Some(lookup) = vendored {
        spec.set_attr(c"_zippy_lookup_name", &object::string(lookup)?)?;
    }
    if !package {
        return Some(());
    }
    let search = object::list()?;
    if let Some(lookup) = vendored {
        let marker = lookup_parts(&[VENDORED_MARKER, lookup])?;
        search.append(&object::string(&marker)?)?;
    }
    spec.set_attr(c"submodule_search_locations", &search)
}

pub(super) fn exec_module(args: *mut PyObject) -> PyResult<Owned> {
    let args = object::args(args, c"O")?;
    let module = &args[0];
    let name = module_name(module)?;
    let name = name.unicode()?;
    let view = object::view()?;
    let entry = object::payload_result(view.find(name))?;
    let Some(entry) = entry.filter(|entry| entry.entry.is_bytecode()) else {
        // SAFETY: callbacks hold the GIL and the exception class is initialized.
        unsafe {
            py::PyErr_SetString(py::PyExc_ImportError, c"zippy: module not in blob".as_ptr())
        };
        return None;
    };
    let code = payload::read_code(view, entry.entry)?;
    evaluate(module, entry.entry, &code)
}

fn module_name(module: &Owned) -> PyResult<Owned> {
    if let Some(spec) = module.attr(c"__spec__") {
        // SAFETY: the None singleton and references are live while the GIL is held.
        if spec.as_ptr() != unsafe { py::aws_python_none() }
            && let Some(name) = spec.attr(c"_zippy_lookup_name")
        {
            // SAFETY: the name owns a reference and the GIL protects the singleton.
            if name.as_ptr() != unsafe { py::aws_python_none() } {
                return Some(name);
            }
        }
    }
    // SAFETY: missing spec/stashed names deliberately fall back to the module's __name__.
    unsafe { py::PyErr_Clear() };
    module.attr(c"__name__")
}

fn evaluate(module: &Owned, entry: Entry<'_>, code: &Owned) -> PyResult<Owned> {
    // SAFETY: PyModule_GetDict validates module, whose owned reference holds the dict alive.
    unsafe {
        let dictionary = Owned::borrowed(py::PyModule_GetDict(module.as_ptr()))?;
        if py::PyDict_GetItemString(dictionary.as_ptr(), c"__builtins__".as_ptr()).is_null()
            && let Some(builtins) = Owned::borrowed(py::PyEval_GetBuiltins())
        {
            dictionary.dict_set(c"__builtins__", &builtins)?;
        }
        let origin = object::synthetic_file(entry.name, entry.is_package())?;
        dictionary.dict_set(c"__file__", &origin)?;
        let _result = Owned::new(py::PyEval_EvalCode(
            code.as_ptr(),
            dictionary.as_ptr(),
            dictionary.as_ptr(),
        ))?;
        object::none()
    }
}
