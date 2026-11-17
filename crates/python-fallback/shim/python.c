#define PY_SSIZE_T_CLEAN
#include <Python.h>
#ifndef _WIN32
#include <locale.h>
#include <stdlib.h>
#include <string.h>
#endif

extern int register_builtin_extensions(void);
extern void install_frozen_bootstrap(void);

#ifndef _WIN32
extern int aws_python_locale_name_is_decodable(const char *name);

/* Whether Python can decode the LC_CTYPE locale name the environment selects.
   glibc's setlocale rejects a name that no locale has, so the real CLI keeps
   the C locale. musl's accepts any name, and `locale.setlocale(LC_CTYPE)`
   then fails to decode one that is not UTF-8, which awscli reads before every
   file:// parameter (helpers::locale_name_is_decodable). The probe restores
   the process locale, which is still C here. */
static int environment_locale_is_decodable(void) {
    const char *current = setlocale(LC_CTYPE, NULL);
    char *saved = current != NULL ? strdup(current) : NULL;
    if (saved == NULL) return 1;
    const char *selected = setlocale(LC_CTYPE, "");
    int decodable = selected == NULL || aws_python_locale_name_is_decodable(selected);
    setlocale(LC_CTYPE, saved);
    free(saved);
    return decodable;
}

/* Preinitialize as the first PyConfig_SetBytes* call would, except that the
   process keeps the C locale, as on glibc, where CPython then enables UTF-8
   mode. That call parses argv only when it is the one that sets argv. */
static PyStatus preinitialize_in_c_locale(int argc, const char *const *argv,
                                          const char *executable) {
    PyPreConfig preconfig;
    PyPreConfig_InitPythonConfig(&preconfig);
    preconfig.configure_locale = 0;
    if (executable != NULL) return Py_PreInitialize(&preconfig);
    return Py_PreInitializeFromBytesArgs(&preconfig, argc, (char **)argv);
}
#endif

static int initialize(int argc, const char *const *argv, const wchar_t *const *wide_argv,
                      int harness, const char *executable, int embedded_payload,
                      const char *stdio_encoding, const char *stdio_errors, int *exit_code) {
    if (register_builtin_extensions() != 0) return 1;
    install_frozen_bootstrap();
#ifndef _WIN32
    if (!harness && !environment_locale_is_decodable()
        && PyStatus_Exception(preinitialize_in_c_locale(argc, argv, executable))) {
        return executable != NULL ? 5 : 2;
    }
#endif
    PyConfig config;
    if (harness) PyConfig_InitIsolatedConfig(&config);
    else PyConfig_InitPythonConfig(&config);
    if (executable != NULL) {
        PyStatus selected = PyConfig_SetBytesString(&config, &config.executable, executable);
        if (PyStatus_Exception(selected)) {
            PyConfig_Clear(&config);
            return 5;
        }
    }
    PyStatus status = wide_argv != NULL
        ? PyConfig_SetArgv(&config, argc, (wchar_t *const *)wide_argv)
        : PyConfig_SetBytesArgv(&config, argc, (char *const *)argv);
    if (PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        return 2;
    }
    /* Resolve both fields explicitly: config_init_stdio_encoding fills them
       independently, so a half left unset still comes from the locale. The
       values are helpers::STDIO_ENCODING and helpers::STDIO_ERRORS. */
    status = PyConfig_SetBytesString(&config, &config.stdio_encoding, stdio_encoding);
    if (PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        return 6;
    }
    status = PyConfig_SetBytesString(&config, &config.stdio_errors, stdio_errors);
    if (PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        return 7;
    }
    config.isolated = 1;
    config.use_environment = 0;
    config.user_site_directory = 0;
#if PY_VERSION_HEX >= 0x030E0000
    config.remote_debug = 0;
#endif
    config.site_import = executable != NULL && !embedded_payload;
    config.parse_argv = 0;
    config.pathconfig_warnings = 0;
    config.module_search_paths_set = executable == NULL;
    if (harness) {
        config.install_signal_handlers = 0;
        config.write_bytecode = 0;
#if PY_VERSION_HEX >= 0x030B0000
        config.safe_path = 1;
#endif
    }
    status = Py_InitializeFromConfig(&config);
    if (PyStatus_IsExit(status)) {
        *exit_code = status.exitcode;
        PyConfig_Clear(&config);
        return 4;
    }
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
        return 3;
    }
    PyConfig_Clear(&config);
    return 0;
}

int aws_python_initialize(int argc, const char *const *argv, int harness,
                          const char *executable, int embedded_payload,
                          const char *stdio_encoding, const char *stdio_errors, int *exit_code) {
    return initialize(argc, argv, NULL, harness, executable, embedded_payload, stdio_encoding,
                      stdio_errors, exit_code);
}

#ifdef _WIN32
int aws_python_initialize_wide(int argc, const wchar_t *const *argv, int harness,
                               const char *executable, int embedded_payload,
                               const char *stdio_encoding, const char *stdio_errors,
                               int *exit_code) {
    return initialize(argc, NULL, argv, harness, executable, embedded_payload, stdio_encoding,
                      stdio_errors, exit_code);
}
#endif

PyObject *aws_python_none(void) { return Py_None; }
int aws_python_is_long(PyObject *object) { return PyLong_Check(object); }
int aws_python_is_list(PyObject *object) { return PyList_Check(object); }
int aws_python_is_unicode(PyObject *object) { return PyUnicode_Check(object); }
int aws_python_is_code(PyObject *object) { return PyCode_Check(object); }

PyObject *aws_python_take_raised_exception(void) {
#if PY_VERSION_HEX >= 0x030C0000
    return PyErr_GetRaisedException();
#else
    PyObject *type = NULL;
    PyObject *value = NULL;
    PyObject *traceback = NULL;
    PyErr_Fetch(&type, &value, &traceback);
    PyErr_NormalizeException(&type, &value, &traceback);
    Py_XDECREF(type);
    Py_XDECREF(traceback);
    return value;
#endif
}
PyObject *aws_python_compile(const char *source, const char *filename, int start) {
    return Py_CompileString(source, filename, start);
}
