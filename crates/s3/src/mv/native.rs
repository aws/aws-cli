use super::Args;
use crate::{command, cp, transfer};
use cli_core::EnvMap;
use cli_core::cli_error::CommandFailure;
use cli_core::command::CommandContext;
use std::io::Write;

/// Runs `s3 mv` for an invocation the router admitted.
///
/// Each source is deleted after its transfer succeeded and before its
/// result line: an upload removes its file, and a download sends a
/// DeleteObject of its object. A source that cannot be deleted fails the
/// move, which keeps both copies. A recursive download under
/// `--case-conflict` checks each object as `s3 cp` does, and an object it
/// leaves is kept.
///
/// # Errors
/// Returns the [`CommandFailure`] the copy it runs returns.
pub fn run(
    context: &CommandContext<'_, impl EnvMap>,
    args: &Args,
    stdout: &mut (dyn Write + Send),
    stderr: &mut (dyn Write + Send),
) -> Result<u8, CommandFailure> {
    let copy = args.to_copy_args();
    let mode = cp::CopyMode {
        sources: transfer::SourceDisposition::Delete {
            user_agent: command::source_delete_user_agent(context.client),
        },
        sync: copy.case_conflict_strategies(),
    };
    cp::run_copy(context, &copy, mode, stdout, stderr)
}
