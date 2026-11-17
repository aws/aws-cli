#define PY_SSIZE_T_CLEAN
#include <Python.h>

extern PyObject *aws_python_finder_call(int operation, PyObject *self, PyObject *args);

/* CPython can reuse a single-phase module in a legacy subinterpreter without
 * calling its initializer. Check every callback before Rust accesses GIL-owned
 * main-interpreter state, even when the import machinery reused a cached module. */
static int require_main_interpreter(void) {
    if (PyInterpreterState_Get() == PyInterpreterState_Main()) return 1;
    PyErr_SetString(PyExc_ImportError,
                    "zippy: finder is only available in the main interpreter");
    return 0;
}

#define CALLBACK(name, operation) \
    static PyObject *name(PyObject *self, PyObject *args) { \
        if (!require_main_interpreter()) return NULL; \
        return aws_python_finder_call(operation, self, args); \
    }

CALLBACK(zippy_exists, 0)
CALLBACK(zippy_has_prefix, 1)
CALLBACK(zippy_list_prefix, 2)
CALLBACK(zippy_list_dir, 3)
CALLBACK(zippy_list_services, 4)
CALLBACK(zippy_list_api_versions, 5)
CALLBACK(zippy_get_data, 6)
CALLBACK(zippy_load_code, 7)
CALLBACK(zippy_is_package, 8)
CALLBACK(zippy_is_bytecode, 9)
CALLBACK(zippy_stats, 10)
CALLBACK(finder_find_spec, 11)
CALLBACK(finder_create_module, 12)
CALLBACK(finder_exec_module, 13)

static PyMethodDef finder_methods[] = {
    {"find_spec", finder_find_spec, METH_VARARGS, "Find a module spec for the given name."},
    {"create_module", finder_create_module, METH_VARARGS, "Use default module creation."},
    {"exec_module", finder_exec_module, METH_VARARGS,
     "Execute the module's bytecode in its namespace."},
    {"get_data", zippy_get_data, METH_VARARGS, "get_data(name: str) -> bytes"},
    {NULL, NULL, 0, NULL}
};

static PyType_Slot finder_slots[] = {
    {Py_tp_methods, finder_methods},
    {Py_tp_new, PyType_GenericNew},
    {0, NULL}
};

static PyType_Spec finder_spec = {
    "_zippy_finder.Finder", sizeof(PyObject), 0, Py_TPFLAGS_DEFAULT, finder_slots
};

static PyMethodDef module_methods[] = {
    {"exists", zippy_exists, METH_VARARGS, "exists(name: str) -> bool"},
    {"has_prefix", zippy_has_prefix, METH_VARARGS, "has_prefix(prefix: str) -> bool"},
    {"list_prefix", zippy_list_prefix, METH_VARARGS, "list_prefix(prefix: str) -> list[str]"},
    {"list_dir", zippy_list_dir, METH_VARARGS, "list_dir(prefix: str) -> list[str]"},
    {"list_services", zippy_list_services, METH_VARARGS,
     "list_services(prefix: str, type_name: str) -> list[str]"},
    {"list_api_versions", zippy_list_api_versions, METH_VARARGS,
     "list_api_versions(prefix: str, service_name: str, type_name: str) -> list[str]"},
    {"get_data", zippy_get_data, METH_VARARGS, "get_data(name: str) -> bytes"},
    {"load_code", zippy_load_code, METH_VARARGS, "load_code(name: str) -> code"},
    {"is_package", zippy_is_package, METH_VARARGS, "is_package(name: str) -> bool"},
    {"is_bytecode", zippy_is_bytecode, METH_VARARGS, "is_bytecode(name: str) -> bool"},
    {"stats", zippy_stats, METH_NOARGS, "stats() -> dict"},
    {NULL, NULL, 0, NULL}
};

static PyModuleDef module_def = {
    PyModuleDef_HEAD_INIT,
    "_zippy_finder", "ZIPPY003 embedded payload access", -1, module_methods,
    NULL, NULL, NULL, NULL
};

PyObject *aws_python_finder_module(void) {
    if (!require_main_interpreter()) return NULL;
    return PyModule_Create(&module_def);
}

PyObject *aws_python_finder_type(void) {
    if (!require_main_interpreter()) return NULL;
    return PyType_FromSpec(&finder_spec);
}
