use super::*;
use std::{fs, io::Write, os::windows::fs::MetadataExt, time::SystemTime};

const FILE_ATTRIBUTE_SPARSE_FILE: u32 = 0x200;
const FILE_ATTRIBUTE_COMPRESSED: u32 = 0x800;
const FSCTL_SET_SPARSE: u32 = 0x0009_00c4;
const FSCTL_SET_COMPRESSION: u32 = 0x0009_c040;

#[link(name = "kernel32")]
unsafe extern "system" {
    fn DeviceIoControl(
        file: *mut c_void,
        control: u32,
        input: *const c_void,
        input_size: u32,
        output: *mut c_void,
        output_size: u32,
        returned: *mut u32,
        overlapped: *mut c_void,
    ) -> i32;
}

#[test]
fn sparse_flag_without_holes_reports_zero_allocated_and_logical_bytes() -> io::Result<()> {
    with_file(|file| {
        control(file, FSCTL_SET_SPARSE, &[])?;
        assert_ne!(
            file.metadata()?.file_attributes() & FILE_ATTRIBUTE_SPARSE_FILE,
            0
        );
        assert_eq!(file.metadata()?.len(), 0);
        assert_eq!(crate::allocated_bytes(file)?, 0);
        Ok(())
    })
}

#[test]
fn sparse_file_reports_the_backed_extent_below_logical_length() -> io::Result<()> {
    with_file(|file| {
        control(file, FSCTL_SET_SPARSE, &[])?;
        file.set_len(8 * 1024 * 1024)?;
        file.write_all(&[0x5a; 8192])?;
        file.sync_all()?;
        let allocated = crate::allocated_bytes(file)?;
        assert!(allocated >= 8192);
        assert!(allocated < file.metadata()?.len());
        assert_eq!(
            i64::try_from(allocated).map_err(io::Error::other)?,
            query_allocation(file)?
        );
        Ok(())
    })
}

#[test]
fn dense_compressed_file_reports_logical_length_despite_smaller_allocation() -> io::Result<()> {
    with_file(|file| {
        control(file, FSCTL_SET_COMPRESSION, &1_u16.to_ne_bytes())?;
        for _ in 0..128 {
            file.write_all(&[0; 32768])?;
        }
        file.sync_all()?;
        let metadata = file.metadata()?;
        assert_ne!(metadata.file_attributes() & FILE_ATTRIBUTE_COMPRESSED, 0);
        assert_eq!(metadata.file_attributes() & FILE_ATTRIBUTE_SPARSE_FILE, 0);
        assert!(query_allocation(file)? < metadata.len() as i64);
        assert_eq!(crate::allocated_bytes(file)?, metadata.len());
        Ok(())
    })
}

fn control(file: &File, code: u32, input: &[u8]) -> io::Result<()> {
    let mut returned = 0;
    let input_size = u32::try_from(input.len()).map_err(io::Error::other)?;
    // SAFETY: the fixture owns a synchronous file handle. These two control codes
    // only read the live input buffer, write returned, and require no output or
    // OVERLAPPED buffer. A null sparse buffer requests the documented true value.
    let success = unsafe {
        DeviceIoControl(
            file.as_raw_handle(),
            code,
            if input.is_empty() {
                std::ptr::null()
            } else {
                input.as_ptr().cast()
            },
            input_size,
            std::ptr::null_mut(),
            0,
            &mut returned,
            std::ptr::null_mut(),
        )
    };
    if success == 0 {
        Err(io::Error::last_os_error())
    } else {
        Ok(())
    }
}

fn with_file(check: impl FnOnce(&mut File) -> io::Result<()>) -> io::Result<()> {
    let stamp = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map_err(io::Error::other)?
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "awscli-allocated-storage-{}-{stamp}",
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
