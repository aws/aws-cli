use super::Publication;
use std::io;

#[test]
fn failed_publication_remains_retryable_and_success_is_published_once() -> io::Result<()> {
    let publication = Publication::new();
    let mut attempts = Vec::new();
    let failed = publication.run(|| {
        attempts.push("failed");
        Err(io::ErrorKind::OutOfMemory.into())
    });
    let error = failed
        .err()
        .ok_or_else(|| io::Error::other("publication must fail"))?;
    assert_eq!(error.kind(), io::ErrorKind::OutOfMemory);

    publication.run(|| {
        attempts.push("successful");
        Ok(())
    })?;
    publication.run(|| {
        attempts.push("repeated");
        Err(io::ErrorKind::PermissionDenied.into())
    })?;
    assert_eq!(attempts, ["failed", "successful"]);
    Ok(())
}
