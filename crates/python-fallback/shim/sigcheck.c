#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <marshal.h>

#define SIGNATURE(name, type) \
    _Static_assert(_Generic(&(name), type: 1, default: 0), #name " signature drift")

SIGNATURE(Py_IncRef, void (*)(PyObject *));
SIGNATURE(Py_DecRef, void (*)(PyObject *));
SIGNATURE(Py_IsInitialized, int (*)(void));
SIGNATURE(Py_FinalizeEx, int (*)(void));
SIGNATURE(PyArg_ParseTuple, int (*)(PyObject *, const char *, ...));
SIGNATURE(PyErr_Clear, void (*)(void));
SIGNATURE(PyErr_Print, void (*)(void));
SIGNATURE(PyErr_NoMemory, PyObject *(*)(void));
SIGNATURE(PyErr_Occurred, PyObject *(*)(void));
SIGNATURE(PyErr_ExceptionMatches, int (*)(PyObject *));
SIGNATURE(PyErr_SetString, void (*)(PyObject *, const char *));
SIGNATURE(PyLong_AsLongLong, long long (*)(PyObject *));
SIGNATURE(PyLong_FromUnsignedLong, PyObject *(*)(unsigned long));
SIGNATURE(PyLong_FromUnsignedLongLong, PyObject *(*)(unsigned long long));
SIGNATURE(PyBool_FromLong, PyObject *(*)(long));
SIGNATURE(PyUnicode_AsUTF8, const char *(*)(PyObject *));
SIGNATURE(PyUnicode_AsUTF8AndSize, const char *(*)(PyObject *, Py_ssize_t *));
SIGNATURE(PyUnicode_FromString, PyObject *(*)(const char *));
SIGNATURE(PyUnicode_FromStringAndSize, PyObject *(*)(const char *, Py_ssize_t));
SIGNATURE(PyBytes_FromStringAndSize, PyObject *(*)(const char *, Py_ssize_t));
SIGNATURE(PyBytes_AsString, char *(*)(PyObject *));
SIGNATURE(PyBytes_Size, Py_ssize_t (*)(PyObject *));
SIGNATURE(PyObject_Str, PyObject *(*)(PyObject *));
SIGNATURE(PyObject_GetAttrString, PyObject *(*)(PyObject *, const char *));
SIGNATURE(PyObject_SetAttrString, int (*)(PyObject *, const char *, PyObject *));
SIGNATURE(PyObject_Call, PyObject *(*)(PyObject *, PyObject *, PyObject *));
SIGNATURE(PyObject_CallObject, PyObject *(*)(PyObject *, PyObject *));
SIGNATURE(PyModule_GetDict, PyObject *(*)(PyObject *));
SIGNATURE(PyModule_AddObject, int (*)(PyObject *, const char *, PyObject *));
SIGNATURE(PyDict_New, PyObject *(*)(void));
SIGNATURE(PyDict_SetItemString, int (*)(PyObject *, const char *, PyObject *));
SIGNATURE(PyDict_GetItemString, PyObject *(*)(PyObject *, const char *));
SIGNATURE(PyTuple_Pack, PyObject *(*)(Py_ssize_t, ...));
SIGNATURE(PyList_New, PyObject *(*)(Py_ssize_t));
SIGNATURE(PyList_Append, int (*)(PyObject *, PyObject *));
SIGNATURE(PyList_Insert, int (*)(PyObject *, Py_ssize_t, PyObject *));
SIGNATURE(PyList_Size, Py_ssize_t (*)(PyObject *));
SIGNATURE(PyList_GetItem, PyObject *(*)(PyObject *, Py_ssize_t));
SIGNATURE(PySequence_Contains, int (*)(PyObject *, PyObject *));
SIGNATURE(PyImport_AddModule, PyObject *(*)(const char *));
SIGNATURE(PyImport_ImportModule, PyObject *(*)(const char *));
SIGNATURE(PyImport_GetMagicNumber, long (*)(void));
SIGNATURE(PyMarshal_ReadObjectFromString, PyObject *(*)(const char *, Py_ssize_t));
SIGNATURE(PyMarshal_WriteObjectToString, PyObject *(*)(PyObject *, int));
SIGNATURE(PyEval_GetBuiltins, PyObject *(*)(void));
SIGNATURE(PyEval_EvalCode, PyObject *(*)(PyObject *, PyObject *, PyObject *));
SIGNATURE(PyRun_StringFlags,
          PyObject *(*)(const char *, int, PyObject *, PyObject *, PyCompilerFlags *));
SIGNATURE(PySys_GetObject, PyObject *(*)(const char *));
SIGNATURE(PySys_SetObject, int (*)(const char *, PyObject *));
SIGNATURE(PySys_WriteStderr, void (*)(const char *, ...));
SIGNATURE(PyMem_Malloc, void *(*)(size_t));
SIGNATURE(PyMem_Free, void (*)(void *));

_Static_assert(sizeof(Py_ssize_t) == sizeof(void *), "Py_ssize_t must match Rust isize");
_Static_assert(sizeof(long long) == sizeof(int64_t), "exit conversion requires 64-bit C long long");
