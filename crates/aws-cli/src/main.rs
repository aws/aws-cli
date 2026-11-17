#![deny(unsafe_code)]
#[allow(
    unsafe_code,
    reason = "the entrypoint publishes its environment before any other thread starts"
)]
mod bootstrap;
use std::io;
use std::process::ExitCode;
mod invocation;
mod python;

#[cfg(all(target_os = "linux", target_env = "musl"))]
#[global_allocator]
static ALLOCATOR: crt_sys::Mimalloc = crt_sys::Mimalloc;

#[cfg(windows)]
type HostExitStatus = u32;
#[cfg(not(windows))]
type HostExitStatus = u8;

/// Records whether the process started without a stdout, from the C
/// runtime's initializer list: by `main`, the standard library's start code
/// has reopened a closed descriptor on `/dev/null`.
#[cfg(any(target_os = "linux", target_os = "macos"))]
#[allow(
    unsafe_code,
    reason = "link_section places the safe recorder in the C runtime's initializer list"
)]
#[used]
#[cfg_attr(target_os = "linux", unsafe(link_section = ".init_array"))]
#[cfg_attr(target_os = "macos", unsafe(link_section = "__DATA,__mod_init_func"))]
static RECORD_STDOUT_AT_START: extern "C" fn() = record_stdout_at_start;

#[cfg(any(target_os = "linux", target_os = "macos"))]
extern "C" fn record_stdout_at_start() {
    cli_core::startup::record_stdout_at_start();
}

fn main() -> ExitCode {
    #[cfg(target_os = "linux")]
    cli_core::startup::expand_stack_size();
    // Replace the start code's ignored SIGPIPE, which a `credential_process`
    // helper would inherit, with a handler `exec` resets. Should that fail,
    // SIGPIPE stays ignored and only the helpers' disposition differs.
    #[cfg(unix)]
    let _ = cli_core::startup::install_sigpipe_handler();
    let status = invocation::run().unwrap_or_else(|error| {
        use cli_core::cli_error::{Category, CommandFailure};
        let failure = CommandFailure {
            message: error.to_string().into_bytes(),
            ..CommandFailure::new(Category::General)
        };
        let _ = cli_core::cli_error::render_command_failure(
            &mut cli_core::output::TextStream::new(io::stderr().lock()),
            &failure,
            Default::default(),
        );
        1
    });
    exit_code(status)
}

fn exit_code(status: HostExitStatus) -> ExitCode {
    // A Windows parent sees all 32 bits of a status, but a stable
    // `ExitCode` holds a byte, so a wider status leaves through
    // `process::exit`, which flushes stdout first.
    #[cfg(windows)]
    {
        u8::try_from(status).map_or_else(
            |_| std::process::exit(i32::from_ne_bytes(status.to_ne_bytes())),
            ExitCode::from,
        )
    }
    #[cfg(not(windows))]
    {
        ExitCode::from(status)
    }
}
