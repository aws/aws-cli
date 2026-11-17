#include <Python.h>

/* Extensions that reach Python only through the linked table. On macOS
   that includes _scproxy, which reads SystemConfiguration.framework. */
static const char *const check =
    "import _bz2, _ctypes, _hashlib, _lzma, _sqlite3, _ssl, _zstd, zlib"
#ifdef __APPLE__
    "\nimport _scproxy\n"
    "assert isinstance(_scproxy._get_proxies(), dict)"
#endif
    ;

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <cpython-prefix>\n", argv[0]);
        return 2;
    }
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    PyStatus status = PyConfig_SetBytesString(&config, &config.home, argv[1]);
    if (!PyStatus_Exception(status)) {
        status = Py_InitializeFromConfig(&config);
    }
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
    }
    int failed = PyRun_SimpleString(check) != 0;
    if (Py_FinalizeEx() < 0) {
        failed = 1;
    }
    return failed;
}
