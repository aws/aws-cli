use std::io::{self, Write};

pub fn run(invocation: python_fallback::Invocation<'_>) -> io::Result<crate::HostExitStatus> {
    // CPython sets `sys.stdout` to None for a closed descriptor, which
    // the start code's `/dev/null` would hide. Nothing writes through
    // `io::stdout()` after this point.
    #[cfg(unix)]
    cli_core::startup::close_stdout_closed_at_start()?;
    match invocation.run() {
        Ok(status) => Ok(status),
        Err(error) => {
            let _ = io::stderr()
                .lock()
                .write_all(error.diagnostic_line().as_bytes());
            Ok(1)
        }
    }
}
