use std::{ffi::c_void, fs::File, io, mem::MaybeUninit, os::windows::io::AsRawHandle};

// FILE_STANDARD_INFO from winbase.h. BOOLEAN fields are bytes, not Win32 BOOLs.
#[repr(C)]
struct FileStandardInfo {
    allocation_size: i64,
    end_of_file: i64,
    number_of_links: u32,
    delete_pending: u8,
    directory: u8,
}

const _: () = {
    assert!(size_of::<FileStandardInfo>() == 24);
    assert!(align_of::<FileStandardInfo>() == 8);
    assert!(std::mem::offset_of!(FileStandardInfo, allocation_size) == 0);
    assert!(std::mem::offset_of!(FileStandardInfo, end_of_file) == 8);
    assert!(std::mem::offset_of!(FileStandardInfo, number_of_links) == 16);
    assert!(std::mem::offset_of!(FileStandardInfo, delete_pending) == 20);
    assert!(std::mem::offset_of!(FileStandardInfo, directory) == 21);
};

#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetFileInformationByHandleEx(
        file: *mut c_void,
        class: i32,
        information: *mut c_void,
        size: u32,
    ) -> i32;
}

pub(super) fn query_allocation(file: &File) -> io::Result<i64> {
    const FILE_STANDARD_INFO: i32 = 1;
    let mut information = MaybeUninit::<FileStandardInfo>::uninit();
    // SAFETY: File retains the borrowed handle for the complete synchronous call.
    // The class matches the repr(C) output type and its full writable buffer size.
    let success = unsafe {
        GetFileInformationByHandleEx(
            file.as_raw_handle(),
            FILE_STANDARD_INFO,
            information.as_mut_ptr().cast(),
            size_of::<FileStandardInfo>() as u32,
        )
    };
    if success == 0 {
        return Err(io::Error::last_os_error());
    }
    // SAFETY: successful GetFileInformationByHandleEx initialized the full output.
    Ok(unsafe { information.assume_init() }.allocation_size)
}

#[cfg(test)]
mod tests;
