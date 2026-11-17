use crate::helpers::HostExitStatus;
use crate::{configuration as config, exit_status, ffi, finder, helpers, lifecycle};
use std::ffi::{CStr, CString, OsString, c_int};
use std::fmt;
#[cfg(unix)]
use std::os::unix::ffi::OsStrExt;
use std::ptr;

const RUNTIME_CODE: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/runtime.pyc"));

const FINALIZATION_FAILURE_STATUS: HostExitStatus = 120;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Ending {
    Exited(HostExitStatus),
    Failed,
}

fn status_after_finalization(ending: Ending, finalized: c_int) -> HostExitStatus {
    match ending {
        Ending::Exited(_) if finalized < 0 => FINALIZATION_FAILURE_STATUS,
        Ending::Exited(status) => status,
        Ending::Failed => 1,
    }
}

/// An interpreter startup failure before Python can print its own exception.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum RunError {
    AlreadyStarted,
    TooManyArguments,
    InvalidArgument,
    RegisterExtensions,
    ConfigureArguments,
    ConfigureExecutable,
    ConfigureStdioEncoding,
    ConfigureStdioErrors,
    Initialize,
}
impl fmt::Display for RunError {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        out.write_str(match self {
            Self::AlreadyStarted => "the Python interpreter has already run in this process",
            Self::TooManyArguments => "too many argv entries for CPython",
            Self::InvalidArgument => "an argv entry contains a NUL byte",
            Self::RegisterExtensions => "failed to register builtin extensions",
            Self::ConfigureArguments => "failed to set argv",
            Self::ConfigureExecutable => "failed to configure selected Python executable",
            Self::ConfigureStdioEncoding => "failed to configure Python standard stream encoding",
            Self::ConfigureStdioErrors => "failed to configure Python standard stream errors",
            Self::Initialize => "failed to initialize CPython",
        })
    }
}
impl std::error::Error for RunError {}
impl RunError {
    /// The stderr line that reports this failure.
    pub fn diagnostic_line(&self) -> String {
        match self {
            Self::ConfigureStdioEncoding => {
                "error: failed to configure Python stdio err=StdioEncodingFailed\n".into()
            }
            Self::ConfigureStdioErrors => {
                "error: failed to configure Python stdio err=StdioErrorHandlerFailed\n".into()
            }
            _ => format!("error(python_fallback): {self}\n"),
        }
    }
}

/// The sys attributes the bootstrap reads the User-Agent version and
/// metadata from, and deletes, before it hands control to the AWS CLI.
const USER_AGENT_VERSION: &CStr = c"_zippy_user_agent_version";
const USER_AGENT_METADATA: &CStr = c"_zippy_user_agent_metadata";

/// One run of the embedded AWS CLI: the argv it parses and what the host
/// changes in the User-Agent of every request it sends.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Invocation<'a> {
    argv: &'a [OsString],
    user_agent_version: Option<&'a str>,
    user_agent_metadata: Vec<(&'a str, &'a str)>,
}
impl<'a> Invocation<'a> {
    /// A run with the original argv, including the executable name.
    pub fn new(argv: &'a [OsString]) -> Self {
        Self {
            argv,
            user_agent_version: None,
            user_agent_metadata: Vec::new(),
        }
    }

    /// Names `aws-cli/<version>` in the User-Agent of every request, in place
    /// of upstream's `__version__`. `aws --version` and `--debug`'s
    /// `CLI version` line print the same version, since the AWS CLI builds
    /// them from the session's User-Agent version.
    #[must_use]
    pub fn user_agent_version(mut self, version: &'a str) -> Self {
        self.user_agent_version = Some(version);
        self
    }

    /// Adds `md/<name>#<value>` to the User-Agent of every request, after
    /// the metadata the AWS CLI adds when it sets up each session.
    #[must_use]
    pub fn user_agent_metadata(mut self, name: &'a str, value: &'a str) -> Self {
        self.user_agent_metadata.push((name, value));
        self
    }

    /// Runs the embedded CLI and returns the status it exits with.
    ///
    /// The build-pinned payload remains valid through Python's atexit handlers.
    /// The process can run this interpreter once.
    ///
    /// # Errors
    /// Returns a startup error for invalid argv or an already claimed interpreter.
    pub fn run(self) -> Result<HostExitStatus, RunError> {
        let payload = pyload::embedded();
        let argv = arguments(self.argv)?;
        let executable =
            CString::new(config::EXECUTABLE).map_err(|_| RunError::ConfigureExecutable)?;
        let platlib = CString::new(config::PLATLIB).map_err(|_| RunError::ConfigureExecutable)?;
        if !lifecycle::claim() {
            return Err(RunError::AlreadyStarted);
        }
        finder::force_link();
        // SAFETY: the process-once claim excludes every other safe initialization entrypoint.
        // Initialization and all Python operations/finalization stay on this thread with the GIL.
        // Payload bytecode is trusted: the build compiles it with the same pinned CPython.
        unsafe {
            if let Some(status) = initialize(&argv, &executable)? {
                return Ok(status);
            }
            let ending = evaluate_payload(payload, &platlib, &self);
            finder::prepare_for_interpreter_shutdown();
            let finalized = ffi::Py_FinalizeEx();
            finder::release_payload_view();
            Ok(status_after_finalization(ending, finalized))
        }
    }
}

#[cfg(unix)]
type Argument = CString;
#[cfg(windows)]
type Argument = Vec<u16>;

#[cfg(unix)]
fn arguments(argv: &[OsString]) -> Result<Vec<Argument>, RunError> {
    i32::try_from(argv.len()).map_err(|_| RunError::TooManyArguments)?;
    argv.iter()
        .map(|value| CString::new(value.as_bytes()).map_err(|_| RunError::InvalidArgument))
        .collect()
}

#[cfg(windows)]
fn arguments(argv: &[OsString]) -> Result<Vec<Argument>, RunError> {
    use std::os::windows::ffi::OsStrExt;
    i32::try_from(argv.len()).map_err(|_| RunError::TooManyArguments)?;
    argv.iter()
        .map(|value| {
            let mut wide: Vec<u16> = value.encode_wide().collect();
            if wide.contains(&0) {
                return Err(RunError::InvalidArgument);
            }
            wide.push(0);
            Ok(wide)
        })
        .collect()
}

unsafe fn initialize(
    argv: &[Argument],
    executable: &CString,
) -> Result<Option<HostExitStatus>, RunError> {
    let pointers: Vec<_> = argv.iter().map(|value| value.as_ptr()).collect();
    let mut exit_code = 0;
    // SAFETY: argv count was bounded before claiming the interpreter. The C shim copies
    // every argument/config string while their CString owners remain alive here.
    let status = unsafe {
        #[cfg(unix)]
        let initialize = ffi::aws_python_initialize;
        #[cfg(windows)]
        let initialize = ffi::aws_python_initialize_wide;
        initialize(
            pointers.len() as i32,
            pointers.as_ptr(),
            0,
            if config::DYNAMIC {
                executable.as_ptr()
            } else {
                ptr::null()
            },
            i32::from(config::EMBEDDED_PAYLOAD),
            helpers::STDIO_ENCODING.as_ptr(),
            helpers::STDIO_ERRORS.as_ptr(),
            &mut exit_code,
        )
    };
    match status {
        0 => Ok(None),
        1 => Err(RunError::RegisterExtensions),
        2 => Err(RunError::ConfigureArguments),
        4 => Ok(Some(exit_code as HostExitStatus)),
        5 => Err(RunError::ConfigureExecutable),
        6 => Err(RunError::ConfigureStdioEncoding),
        7 => Err(RunError::ConfigureStdioErrors),
        _ => Err(RunError::Initialize),
    }
}

unsafe fn evaluate_payload(
    payload: &'static [u8],
    platlib: &CString,
    invocation: &Invocation<'_>,
) -> Ending {
    // SAFETY: initialization succeeded and the calling thread holds the interpreter GIL.
    unsafe {
        let loaded_magic = ffi::PyImport_GetMagicNumber();
        if !helpers::bytecode_magic_is_compatible(
            config::DYNAMIC,
            i64::from(config::BYTECODE_MAGIC),
            loaded_magic as i64,
        ) {
            ffi::PySys_WriteStderr(
                c"error(python_fallback): embedded Python bytecode magic mismatch \
                payload=%lld libpython=%lld\n"
                    .as_ptr(),
                i64::from(config::BYTECODE_MAGIC),
                loaded_magic as i64,
            );
            return Ending::Failed;
        }
        if !remove_remote_exec()
            || !append_platlib(platlib)
            || !publish_user_agent_version(invocation.user_agent_version)
            || !publish_user_agent_metadata(&invocation.user_agent_metadata)
            || (config::EMBEDDED_PAYLOAD && !finder::install_payload(payload))
        {
            ffi::PyErr_Print();
            return Ending::Failed;
        }
        evaluate_runtime()
    }
}

/// Remove the `sys.remote_exec` stub before any CLI code loads.
///
/// CPython keeps the stub even when built without remote debugging, and older
/// system interpreters lack it entirely.
unsafe fn remove_remote_exec() -> bool {
    // SAFETY: the GIL is held; deleting a sys attribute takes no reference.
    unsafe {
        ffi::PySys_GetObject(c"remote_exec".as_ptr()).is_null()
            || ffi::PySys_SetObject(c"remote_exec".as_ptr(), std::ptr::null_mut()) == 0
    }
}

unsafe fn append_platlib(platlib: &CString) -> bool {
    if !config::DYNAMIC || !config::EMBEDDED_PAYLOAD || platlib.as_bytes().is_empty() {
        return true;
    }
    // SAFETY: the GIL protects the borrowed sys.path reference and newly owned Unicode.
    unsafe {
        let path = ffi::PySys_GetObject(c"path".as_ptr());
        if path.is_null() {
            return false;
        }
        let entry = ffi::PyUnicode_FromString(platlib.as_ptr());
        if entry.is_null() {
            return false;
        }
        let status = ffi::PyList_Append(path, entry);
        ffi::Py_DecRef(entry);
        status == 0
    }
}

/// Publish the User-Agent version as a sys string, which both bootstraps
/// read; an invocation without one publishes None, which keeps upstream's.
unsafe fn publish_user_agent_version(version: Option<&str>) -> bool {
    // SAFETY: the GIL is held. sys takes its own reference to the value, so
    // the new string's is released; None is borrowed.
    unsafe {
        let Some(version) = version else {
            return ffi::PySys_SetObject(USER_AGENT_VERSION.as_ptr(), ffi::aws_python_none()) == 0;
        };
        let value = unicode(version);
        let published =
            !value.is_null() && ffi::PySys_SetObject(USER_AGENT_VERSION.as_ptr(), value) == 0;
        ffi::Py_DecRef(value);
        published
    }
}

/// Publish the User-Agent metadata as a sys list of `(name, value)` pairs,
/// which both bootstraps read; an invocation without metadata publishes an
/// empty list.
unsafe fn publish_user_agent_metadata(metadata: &[(&str, &str)]) -> bool {
    // SAFETY: the GIL is held. The list holds its own reference to each pair
    // and sys to the list, so every reference created here is released.
    unsafe {
        let list = ffi::PyList_New(0);
        if list.is_null() {
            return false;
        }
        let published = metadata
            .iter()
            .all(|&(name, value)| append_pair(list, name, value))
            && ffi::PySys_SetObject(USER_AGENT_METADATA.as_ptr(), list) == 0;
        ffi::Py_DecRef(list);
        published
    }
}

unsafe fn append_pair(list: *mut ffi::PyObject, name: &str, value: &str) -> bool {
    // SAFETY: the GIL is held and `list` is live. `Py_DecRef` ignores the
    // null of a failed creation, and the pair holds its own references to
    // the strings.
    unsafe {
        let name = unicode(name);
        let value = unicode(value);
        let pair = if name.is_null() || value.is_null() {
            ptr::null_mut()
        } else {
            ffi::PyTuple_Pack(2, name, value)
        };
        let appended = !pair.is_null() && ffi::PyList_Append(list, pair) == 0;
        for object in [name, value, pair] {
            ffi::Py_DecRef(object);
        }
        appended
    }
}

/// A new Python string of `text`, or null with the exception set.
unsafe fn unicode(text: &str) -> *mut ffi::PyObject {
    // SAFETY: the GIL is held. CPython copies the live UTF-8 bytes, whose
    // length, like every Rust allocation's, is at most isize::MAX.
    unsafe { ffi::PyUnicode_FromStringAndSize(text.as_ptr().cast(), text.len() as isize) }
}

unsafe fn evaluate_runtime() -> Ending {
    // SAFETY: the build supplies the pinned interpreter's marshalled bootstrap, and
    // the caller holds its GIL. Every owned reference is dropped before finalization.
    unsafe {
        let code = ffi::PyMarshal_ReadObjectFromString(
            RUNTIME_CODE.as_ptr().cast(),
            RUNTIME_CODE.len() as isize,
        );
        if code.is_null() {
            ffi::PyErr_Print();
            return Ending::Failed;
        }
        let result = evaluate_code(code);
        ffi::Py_DecRef(code);
        result
    }
}

unsafe fn evaluate_code(code: *mut ffi::PyObject) -> Ending {
    // SAFETY: code is a live owned marshalled code object; __main__ and its dictionary
    // are borrowed from the interpreter. Eval's result is released before returning.
    unsafe {
        let module = ffi::PyImport_AddModule(c"__main__".as_ptr());
        let globals = if module.is_null() {
            ptr::null_mut()
        } else {
            ffi::PyModule_GetDict(module)
        };
        if globals.is_null() {
            ffi::PyErr_Print();
            return Ending::Failed;
        }
        let result = ffi::PyEval_EvalCode(code, globals, globals);
        if !result.is_null() {
            ffi::Py_DecRef(result);
            return Ending::Exited(0);
        }
        if ffi::PyErr_ExceptionMatches(ffi::PyExc_SystemExit) != 0 {
            return Ending::Exited(exit_status::from_raised_system_exit());
        }
        ffi::PyErr_Print();
        Ending::Failed
    }
}

#[cfg(test)]
mod tests;
