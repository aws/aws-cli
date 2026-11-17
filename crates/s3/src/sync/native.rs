use super::Args;
use crate::cp;
use cli_core::EnvMap;
use cli_core::cli_error::CommandFailure;
use cli_core::command::CommandContext;
use std::io::Write;

/// Runs `s3 sync` for an invocation the router admitted.
///
/// An upload lists the objects under its destination prefix, and a download
/// walks its destination directory, which it creates first if it is
/// missing. Each source is paired with the destination's entry of the same
/// name and decided by the strategies the options choose; an entry only the
/// destination holds is kept, or removed under `--delete`.
///
/// # Errors
/// Returns the [`CommandFailure`] the transfer returns.
pub fn run(
    context: &CommandContext<'_, impl EnvMap>,
    args: &Args,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let mode = cp::CopyMode {
        sync: Some(args.strategies()),
        ..cp::CopyMode::default()
    };
    cp::run_copy(context, &args.to_copy_args(), mode, stdout, stderr)
}
