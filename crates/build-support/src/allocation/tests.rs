use super::*;
use std::cell::Cell;

#[test]
fn non_sparse_and_compressed_files_skip_the_allocation_query() -> io::Result<()> {
    for attributes in [0, 0x800, 0x800 | 0x20] {
        let queried = Cell::new(false);
        let allocated = windows_allocation(4 * 1024 * 1024, attributes, || {
            queried.set(true);
            Ok(4096)
        })?;
        assert_eq!(allocated, 4 * 1024 * 1024);
        assert!(!queried.get());
    }
    Ok(())
}

#[test]
fn sparse_files_use_the_reported_allocation_even_when_compressed() -> io::Result<()> {
    for attributes in [0x200, 0x200 | 0x800] {
        assert_eq!(windows_allocation(8192, attributes, || Ok(4096))?, 4096);
        assert_eq!(windows_allocation(8192, attributes, || Ok(0))?, 0);
        assert_eq!(windows_allocation(8192, attributes, || Ok(16384))?, 16384);
    }
    Ok(())
}

#[test]
fn sparse_allocation_errors_and_negative_sizes_are_preserved() {
    let query_error = windows_allocation(8192, 0x200, || Err(io::Error::from_raw_os_error(5)));
    assert_eq!(
        query_error.err().and_then(|error| error.raw_os_error()),
        Some(5)
    );
    for size in [-1, i64::MIN] {
        assert_eq!(
            windows_allocation(8192, 0x200, || Ok(size))
                .err()
                .map(|error| error.kind()),
            Some(io::ErrorKind::InvalidData)
        );
    }
}
