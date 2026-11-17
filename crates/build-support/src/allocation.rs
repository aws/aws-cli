use std::{fs::File, io};

#[cfg(windows)]
#[allow(
    unsafe_code,
    reason = "the allocation query is the only syscall boundary and borrows an open File"
)]
mod windows;

/// Returns the allocated byte count used to detect holes in build artifacts.
///
/// On Windows, non-sparse files report their logical length: compression can
/// reduce physical allocation without introducing sparse holes. Sparse files
/// use the operating system's allocation size. Unix uses allocated disk blocks.
///
/// # Errors
/// Propagates metadata or allocation-query errors, including an invalid negative
/// allocation size returned by Windows.
///
/// # Examples
/// ```
/// let file = std::fs::File::open("Cargo.toml")?;
/// let _allocated = build_support::allocated_bytes(&file)?;
/// # Ok::<(), std::io::Error>(())
/// ```
pub fn allocated_bytes(file: &File) -> io::Result<u64> {
    let metadata = file.metadata()?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        Ok(metadata.blocks().saturating_mul(512))
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        windows_allocation(metadata.len(), metadata.file_attributes(), || {
            windows::query_allocation(file)
        })
    }
    #[cfg(not(any(unix, windows)))]
    {
        let _ = metadata;
        Err(io::Error::new(
            io::ErrorKind::Unsupported,
            "allocated storage is unavailable on this host",
        ))
    }
}

#[cfg(any(windows, test))]
fn windows_allocation(
    logical: u64,
    attributes: u32,
    query: impl FnOnce() -> io::Result<i64>,
) -> io::Result<u64> {
    const FILE_ATTRIBUTE_SPARSE_FILE: u32 = 0x200;
    if attributes & FILE_ATTRIBUTE_SPARSE_FILE == 0 {
        return Ok(logical);
    }
    u64::try_from(query()?).map_err(|_| {
        io::Error::new(
            io::ErrorKind::InvalidData,
            "negative Windows allocation size",
        )
    })
}

#[cfg(test)]
mod tests;
