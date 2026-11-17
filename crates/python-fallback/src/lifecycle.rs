use std::sync::atomic::{AtomicBool, Ordering};

static STARTED: AtomicBool = AtomicBool::new(false);

pub(crate) fn claim() -> bool {
    !STARTED.swap(true, Ordering::AcqRel)
}
