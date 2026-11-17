use std::{io, sync::Mutex};

#[derive(Debug)]
pub(super) struct Publication {
    complete: Mutex<bool>,
}

impl Publication {
    pub(super) const fn new() -> Self {
        Self {
            complete: Mutex::new(false),
        }
    }

    #[expect(
        clippy::expect_used,
        reason = "a panicked publisher invalidates startup state"
    )]
    pub(super) fn run(&self, publish: impl FnOnce() -> io::Result<()>) -> io::Result<()> {
        let mut complete = self
            .complete
            .lock()
            .expect("shared-file publication panicked");
        if !*complete {
            publish()?;
            *complete = true;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests;
