// The integration target exercises these dependencies through the spawned CLI.
#[cfg(all(target_os = "linux", target_env = "musl"))]
use crt_sys as _;
use {awscli_argparse as _, awscli_config as _, cli_core as _, cli_router as _};
use {crt as _, pyload as _, python_fallback as _, s3 as _};

#[cfg(unix)]
mod tests;

#[path = "../../src/bootstrap/sequence.rs"]
mod startup;
