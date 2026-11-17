use super::*;
use std::cell::RefCell;

#[test]
fn publication_failure_prevents_native_resource_creation() -> io::Result<()> {
    let events = RefCell::new(Vec::new());
    let result = run_after_preparation(
        || {
            events.borrow_mut().push("export shared files");
            Err(io::Error::other("publisher failed"))
        },
        || {
            events.borrow_mut().extend(["watcher", "runtime"]);
            Ok(0)
        },
    );
    let error = result
        .err()
        .ok_or_else(|| io::Error::other("publication unexpectedly succeeded"))?;
    assert_eq!(error.to_string(), "publisher failed");
    assert_eq!(*events.borrow(), ["export shared files"]);
    Ok(())
}

#[test]
fn successful_publication_precedes_native_resources_and_preserves_the_result() -> io::Result<()> {
    let events = RefCell::new(Vec::new());
    let result = run_after_preparation(
        || {
            events.borrow_mut().push("export shared files");
            Ok(())
        },
        || {
            events.borrow_mut().extend(["watcher", "runtime"]);
            Ok(255)
        },
    )?;
    assert_eq!(result, 255);
    assert_eq!(
        *events.borrow(),
        ["export shared files", "watcher", "runtime"]
    );
    Ok(())
}
