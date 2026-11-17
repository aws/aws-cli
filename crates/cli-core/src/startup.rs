//! Process state the standard library's start code replaces before `main`.
//!
//! On Unix the start code ignores SIGPIPE, and it reopens on `/dev/null` a
//! standard descriptor the process started without. A child keeps an ignored
//! SIGPIPE across `exec`, so a pipeline in a `credential_process` helper can
//! loop forever, where the Python CLI starts the helper with the default
//! action. And writes to the reopened stdout succeed, where the Python CLI
//! starts with `sys.stdout` set to None.
//! Windows has neither change: its start code leaves both alone.
use std::io::{self, Write};
#[cfg(unix)]
use std::sync::atomic::{AtomicBool, Ordering};

#[cfg(unix)]
static STDOUT_CLOSED_AT_START: AtomicBool = AtomicBool::new(false);

/// Replaces the start code's ignored SIGPIPE with a handler that does
/// nothing. A write to a closed pipe still fails with EPIPE instead of
/// killing the process, and `exec` resets a handled signal to its default
/// action, so every child starts with it.
///
/// # Errors
/// Returns the `sigaction` failure; SIGPIPE then stays ignored.
#[cfg(unix)]
pub fn install_sigpipe_handler() -> io::Result<()> {
    // SAFETY: all-zero sigaction is valid storage; sigemptyset initializes its mask.
    let mut action: libc::sigaction = unsafe { std::mem::zeroed() };
    action.sa_sigaction = on_sigpipe as *const () as usize;
    action.sa_flags = libc::SA_RESTART;
    // SAFETY: action and its mask are valid local writable storage, and the
    // handler touches no state.
    let result = unsafe {
        libc::sigemptyset(&mut action.sa_mask);
        libc::sigaction(libc::SIGPIPE, &action, std::ptr::null_mut())
    };
    if result != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}
#[cfg(unix)]
extern "C" fn on_sigpipe(_: libc::c_int) {}

#[cfg(target_os = "linux")]
type ProgramHeader = libc::Elf64_Phdr;
#[cfg(target_os = "linux")]
const _: () = assert!(usize::BITS == 64, "AT_PHDR holds ELF64 program headers");

#[cfg(target_os = "linux")]
const PAGE_SIZE_MIN: u64 = 4096;

/// Raises the soft RLIMIT_STACK to the stack size the executable's
/// `PT_GNU_STACK` header records, clamped to the hard limit. The kernel
/// ignores the header and gives the main thread the soft limit, so under a
/// small one the native commands, which run on the main thread, would
/// overflow it. Every route gets the raised limit, and so does every child
/// the process starts.
///
/// It fails silently: with the limit unread or unraised, a deeper stack
/// faults with SIGSEGV, as it would have anyway.
#[cfg(target_os = "linux")]
pub fn expand_stack_size() {
    expand_stack_size_from(program_headers(), &mut ProcessStackLimit);
}

#[cfg(target_os = "linux")]
fn program_headers() -> &'static [ProgramHeader] {
    // SAFETY: getauxval only reads the auxiliary vector the kernel passed.
    let (address, count) = unsafe {
        (
            libc::getauxval(libc::AT_PHDR),
            libc::getauxval(libc::AT_PHNUM),
        )
    };
    if address == 0 {
        return &[];
    }
    // SAFETY: the kernel points AT_PHDR at the executable's AT_PHNUM program
    // headers, which stay mapped and unchanged for the process's lifetime.
    unsafe { std::slice::from_raw_parts(address as *const ProgramHeader, count as usize) }
}

#[cfg(target_os = "linux")]
trait StackLimit {
    fn get(&mut self) -> io::Result<libc::rlimit>;
    fn set(&mut self, limit: &libc::rlimit) -> io::Result<()>;
}

#[cfg(target_os = "linux")]
struct ProcessStackLimit;

#[cfg(target_os = "linux")]
impl StackLimit for ProcessStackLimit {
    fn get(&mut self) -> io::Result<libc::rlimit> {
        let mut limit = libc::rlimit {
            rlim_cur: 0,
            rlim_max: 0,
        };
        // SAFETY: limit is writable storage for the result.
        if unsafe { libc::getrlimit(libc::RLIMIT_STACK, &mut limit) } != 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(limit)
    }
    fn set(&mut self, limit: &libc::rlimit) -> io::Result<()> {
        // SAFETY: limit is a valid rlimit, which setrlimit only reads.
        if unsafe { libc::setrlimit(libc::RLIMIT_STACK, limit) } != 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(())
    }
}

#[cfg(target_os = "linux")]
fn expand_stack_size_from(headers: &[ProgramHeader], limit: &mut impl StackLimit) {
    let Some(header) = headers
        .iter()
        .find(|header| header.p_type == libc::PT_GNU_STACK)
    else {
        return;
    };
    if header.p_memsz == 0 {
        return;
    }
    debug_assert!(header.p_memsz.is_multiple_of(PAGE_SIZE_MIN));
    let Ok(limits) = limit.get() else {
        return;
    };
    let wanted = header.p_memsz.min(limits.rlim_max);
    if wanted > limits.rlim_cur {
        let _ = limit.set(&libc::rlimit {
            rlim_cur: wanted,
            rlim_max: limits.rlim_max,
        });
    }
}

/// Records whether the process started without a stdout. The executable
/// calls this from its initializer list, which runs before the start code
/// reopens a closed descriptor; from `main` on, descriptor 1 is always open.
///
/// It allocates nothing and touches no standard library state the start code
/// has yet to initialize.
#[cfg(unix)]
pub fn record_stdout_at_start() {
    STDOUT_CLOSED_AT_START.store(descriptor_closed(libc::STDOUT_FILENO), Ordering::Relaxed);
}

#[cfg(unix)]
fn descriptor_closed(fd: libc::c_int) -> bool {
    // SAFETY: F_GETFD only reads the descriptor table.
    let flags = unsafe { libc::fcntl(fd, libc::F_GETFD) };
    flags == -1 && io::Error::last_os_error().raw_os_error() == Some(libc::EBADF)
}

/// Whether the process started without a stdout. Only an executable that
/// calls [`record_stdout_at_start`] before `main` can learn so.
pub fn stdout_closed_at_start() -> bool {
    #[cfg(unix)]
    {
        STDOUT_CLOSED_AT_START.load(Ordering::Relaxed)
    }
    #[cfg(windows)]
    {
        false
    }
}

/// Closes the `/dev/null` the start code opened in place of a stdout the
/// process started without, so an embedded interpreter starts without one,
/// as the Python CLI does: CPython then sets `sys.stdout` to None.
///
/// Afterwards nothing may write through `io::stdout()`, since a later open
/// can reuse the descriptor.
///
/// # Errors
/// Returns the `close` failure.
#[cfg(unix)]
pub fn close_stdout_closed_at_start() -> io::Result<()> {
    if !stdout_closed_at_start() {
        return Ok(());
    }
    // SAFETY: descriptor 1 is the start code's `/dev/null`; nothing in the
    // process closes or replaces it, and no Rust object owns it.
    if unsafe { libc::close(libc::STDOUT_FILENO) } != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}

/// The stdout a native command writes to: descriptor 1 itself, unbuffered,
/// or for a listing in a process that started without a stdout, one whose
/// every write fails with EBADF, as a write to the closed descriptor does.
/// The command buffers it as CPython buffers `sys.stdout`, so it must know
/// what each write left: the standard library's `io::Stdout` keeps its own
/// buffer, flushes it again as the process exits, and reports a write to a
/// descriptor open without write access as a success.
#[derive(Debug)]
pub enum CommandStdout {
    Open(Descriptor),
    #[cfg(unix)]
    Closed,
}
impl CommandStdout {
    /// The process's standard output, or the closed one when the process
    /// started without one.
    pub fn unlocked() -> Self {
        #[cfg(unix)]
        if stdout_closed_at_start() {
            return Self::Closed;
        }
        Self::open()
    }
    /// The process's standard output whatever it started with: the start
    /// code's `/dev/null` in place of a stdout the process started without.
    pub fn open() -> Self {
        Self::Open(Descriptor::stdout())
    }
}
#[cfg(unix)]
fn closed() -> io::Error {
    io::Error::from_raw_os_error(libc::EBADF)
}
impl Write for CommandStdout {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        match self {
            Self::Open(stdout) => stdout.write(buf),
            #[cfg(unix)]
            Self::Closed => Err(closed()),
        }
    }
    fn write_vectored(&mut self, bufs: &[io::IoSlice<'_>]) -> io::Result<usize> {
        match self {
            Self::Open(stdout) => stdout.write_vectored(bufs),
            #[cfg(unix)]
            Self::Closed => Err(closed()),
        }
    }
    fn write_all(&mut self, buf: &[u8]) -> io::Result<()> {
        match self {
            Self::Open(stdout) => stdout.write_all(buf),
            #[cfg(unix)]
            Self::Closed if buf.is_empty() => Ok(()),
            #[cfg(unix)]
            Self::Closed => Err(closed()),
        }
    }
    fn flush(&mut self) -> io::Result<()> {
        match self {
            Self::Open(stdout) => stdout.flush(),
            #[cfg(unix)]
            Self::Closed => Ok(()),
        }
    }
}

/// Descriptor 1 or 2, written with `write(2)` and never closed: each write
/// is one system call whose failure, EBADF included, is the caller's. The
/// standard library's `io::Stderr` reports a write to a descriptor open
/// without write access as a success too.
#[cfg(unix)]
#[derive(Debug)]
pub struct Descriptor(std::mem::ManuallyDrop<std::fs::File>);
#[cfg(unix)]
impl Descriptor {
    fn stdout() -> Self {
        Self::standard(libc::STDOUT_FILENO)
    }
    /// The process's standard error.
    pub fn stderr() -> Self {
        Self::standard(libc::STDERR_FILENO)
    }
    fn standard(fd: libc::c_int) -> Self {
        use std::os::fd::FromRawFd;
        // SAFETY: descriptors 1 and 2 stay open for the life of the process;
        // the start code reopens one the process started without, and
        // `ManuallyDrop` keeps this handle from ever closing it.
        Self(std::mem::ManuallyDrop::new(unsafe {
            std::fs::File::from_raw_fd(fd)
        }))
    }
}
#[cfg(unix)]
impl Write for Descriptor {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        self.0.write(buf)
    }
    fn write_vectored(&mut self, bufs: &[io::IoSlice<'_>]) -> io::Result<usize> {
        self.0.write_vectored(bufs)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
/// A standard output or error handle, through the standard library, which
/// converts console output as the Python CLI's does. No Windows write error
/// leaves output for a flush at exit, so its buffer changes nothing written.
#[cfg(windows)]
#[derive(Debug)]
pub enum Descriptor {
    Stdout(io::Stdout),
    Stderr(io::Stderr),
}
#[cfg(windows)]
impl Descriptor {
    fn stdout() -> Self {
        Self::Stdout(io::stdout())
    }
    /// The process's standard error.
    pub fn stderr() -> Self {
        Self::Stderr(io::stderr())
    }
}
#[cfg(windows)]
impl Write for Descriptor {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        match self {
            Self::Stdout(stdout) => stdout.write(buf),
            Self::Stderr(stderr) => stderr.write(buf),
        }
    }
    fn write_vectored(&mut self, bufs: &[io::IoSlice<'_>]) -> io::Result<usize> {
        match self {
            Self::Stdout(stdout) => stdout.write_vectored(bufs),
            Self::Stderr(stderr) => stderr.write_vectored(bufs),
        }
    }
    fn flush(&mut self) -> io::Result<()> {
        match self {
            Self::Stdout(stdout) => stdout.flush(),
            Self::Stderr(stderr) => stderr.flush(),
        }
    }
}

#[cfg(test)]
mod tests;
