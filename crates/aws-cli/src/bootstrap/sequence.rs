use std::io;

pub fn run_after_preparation<T>(
    prepare: impl FnOnce() -> io::Result<()>,
    run: impl FnOnce() -> io::Result<T>,
) -> io::Result<T> {
    prepare()?;
    run()
}

#[cfg(test)]
#[path = "sequence/tests.rs"]
mod tests;
