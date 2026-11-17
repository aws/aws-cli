use super::*;
use std::{
    fs,
    io::{Read, Seek},
    time::SystemTime,
};

#[test]
fn positional_write_retains_exact_offset_bytes_and_file_length() -> io::Result<()> {
    with_file(|file| {
        let platform = NativePlatform;
        platform.set_length(file, 8)?;
        assert_eq!(platform.write_at(file, b"ab", 4)?, 2);
        assert_eq!(file.metadata()?.len(), 8);
        file.rewind()?;
        let mut contents = [0; 8];
        file.read_exact(&mut contents)?;
        assert_eq!(contents, [0, 0, 0, 0, b'a', b'b', 0, 0]);
        Ok(())
    })
}

#[test]
fn file_mapping_is_unsupported_before_any_mapping_advice_is_available() -> io::Result<()> {
    with_file(|file| {
        let platform = NativePlatform;
        assert!(!platform.mmap_available());
        for length in [0, platform.page_size()] {
            let error = platform
                .mmap_file(file, length)
                .err()
                .ok_or_else(|| io::Error::other("Windows file mapping unexpectedly succeeded"))?;
            assert_eq!(error.kind(), io::ErrorKind::Unsupported);
        }
        Ok(())
    })
}

fn with_file(check: impl FnOnce(&mut File) -> io::Result<()>) -> io::Result<()> {
    let stamp = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map_err(io::Error::other)?
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "awscli-windows-positional-{}-{stamp}",
        std::process::id()
    ));
    let mut file = File::options()
        .read(true)
        .write(true)
        .create_new(true)
        .open(&path)?;
    let result = check(&mut file);
    drop(file);
    let cleanup = fs::remove_file(path);
    result.and(cleanup)
}
