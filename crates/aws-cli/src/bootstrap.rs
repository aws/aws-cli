use cli_core::{EnvMap, SnapshotEnv};

mod sequence;
pub use sequence::run_after_preparation;

pub fn prepare(environment: &SnapshotEnv) -> std::io::Result<()> {
    // SAFETY: called once at the beginning of invocation::run, before CRT, Python,
    // interrupt watchers, or worker threads are initialized. The process owns this
    // startup boundary; library entrypoints never mutate the parent environment.
    unsafe {
        crt::prepare_process(environment.var("AWS_CRT_USE_NON_FIPS_TLS_13"));
        #[cfg(not(windows))]
        crt::shared_files::prepare_process(environment)
    }
    #[cfg(windows)]
    Ok(())
}

pub fn prepare_native(environment: &SnapshotEnv) -> std::io::Result<()> {
    // SAFETY: only the native route calls this, after every Python fallback decision
    // and before installing the interrupt watcher or starting any runtime. The
    // router's synchronous platform probe has dropped its sole Library reference:
    // pinned aws_s3_library_clean_up joins every managed CRT thread before returning,
    // including resolver and event-loop cleanup threads. No join timeout is set.
    // Python has not started, and this process owns the native invocation boundary.
    unsafe {
        crt::request_sequential_parts();
        #[cfg(windows)]
        crt::shared_files::prepare_process(environment)?;
    }
    #[cfg(not(windows))]
    let _ = environment;
    Ok(())
}
