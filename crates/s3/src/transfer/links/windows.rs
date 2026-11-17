use std::ffi::c_void;
use std::os::windows::ffi::OsStrExt;
use std::os::windows::fs::OpenOptionsExt;
use std::os::windows::io::AsRawHandle;
use std::path::Path;

/// A symbolic link's tag, the one `os.path.islink` reports.
pub(super) const IO_REPARSE_TAG_SYMLINK: u32 = 0xA000_000C;
/// A junction's tag, which s3handler's `is_link` adds.
pub(super) const IO_REPARSE_TAG_MOUNT_POINT: u32 = 0xA000_0003;

/// The right to read a file's attributes, all the query needs.
const FILE_READ_ATTRIBUTES: u32 = 0x80;
/// Opens a directory as well as a file.
const FILE_FLAG_BACKUP_SEMANTICS: u32 = 0x0200_0000;
/// Opens a reparse point itself rather than what it redirects to.
const FILE_FLAG_OPEN_REPARSE_POINT: u32 = 0x0020_0000;
const FILE_ATTRIBUTE_REPARSE_POINT: u32 = 0x400;
/// `FILE_INFO_BY_HANDLE_CLASS::FileAttributeTagInfo`.
const FILE_ATTRIBUTE_TAG_INFO: i32 = 9;
/// The open failures after which CPython reads the tag from the parent
/// directory's listing instead.
const ERROR_ACCESS_DENIED: i32 = 5;
const ERROR_SHARING_VIOLATION: i32 = 32;
/// `MAX_PATH`, the length of a find record's name.
const MAX_PATH: usize = 260;

/// `FILE_ATTRIBUTE_TAG_INFO`.
#[repr(C)]
#[derive(Default)]
struct AttributeTagInfo {
    file_attributes: u32,
    reparse_tag: u32,
}

/// `WIN32_FIND_DATAW`, whose `dwReserved0` holds a reparse point's tag.
/// Only the attributes and the tag are read.
#[repr(C)]
struct FindData {
    file_attributes: u32,
    /// The creation, access, and write `FILETIME`s.
    _times: [u32; 6],
    _size: [u32; 2],
    reparse_tag: u32,
    _reserved: u32,
    _file_name: [u16; MAX_PATH],
    _alternate_file_name: [u16; 14],
}

#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetFileInformationByHandleEx(
        file: *mut c_void,
        class: i32,
        information: *mut c_void,
        size: u32,
    ) -> i32;
    fn FindFirstFileW(name: *const u16, data: *mut FindData) -> *mut c_void;
    fn FindClose(find: *mut c_void) -> i32;
}

/// The reparse tag of the reparse point at `path`, as `os.lstat` reads it.
///
/// The path is opened without following it. One the process may not open
/// is looked up in its directory's listing, as CPython looks it up. None
/// for a path that is no reparse point, or that neither finds, which
/// CPython's link tests report as no link.
pub(super) fn reparse_tag(path: &Path) -> Option<u32> {
    let file = match std::fs::OpenOptions::new()
        .access_mode(FILE_READ_ATTRIBUTES)
        .custom_flags(FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT)
        .open(path)
    {
        Ok(file) => file,
        Err(error)
            if matches!(
                error.raw_os_error(),
                Some(ERROR_ACCESS_DENIED | ERROR_SHARING_VIOLATION)
            ) =>
        {
            return listed_reparse_tag(path);
        }
        Err(_) => return None,
    };
    let mut info = AttributeTagInfo::default();
    let size = u32::try_from(size_of::<AttributeTagInfo>()).ok()?;
    // SAFETY: the handle stays open for the call, which writes at most `size`
    // bytes to `info`, a live `FILE_ATTRIBUTE_TAG_INFO` of that size.
    let queried = unsafe {
        GetFileInformationByHandleEx(
            file.as_raw_handle(),
            FILE_ATTRIBUTE_TAG_INFO,
            (&raw mut info).cast(),
            size,
        )
    };
    (queried != 0 && info.file_attributes & FILE_ATTRIBUTE_REPARSE_POINT != 0)
        .then_some(info.reparse_tag)
}

/// The reparse tag the directory listing of `path` reports, CPython's
/// `attributes_from_dir`. The link checks never pass a path ending in a
/// separator, which CPython would drop first.
fn listed_reparse_tag(path: &Path) -> Option<u32> {
    let name: Vec<u16> = path.as_os_str().encode_wide().chain([0]).collect();
    // SAFETY: an all-zero `WIN32_FIND_DATAW` is valid: integers and arrays
    // of them.
    let mut data: FindData = unsafe { std::mem::zeroed() };
    // SAFETY: `name` is NUL-terminated and outlives the call, which fills
    // `data`, a live `WIN32_FIND_DATAW`.
    let find = unsafe { FindFirstFileW(name.as_ptr(), &raw mut data) };
    // INVALID_HANDLE_VALUE, the all-ones handle.
    if find.addr() == usize::MAX {
        return None;
    }
    // SAFETY: `find` is the search handle the call just opened.
    unsafe { FindClose(find) };
    (data.file_attributes & FILE_ATTRIBUTE_REPARSE_POINT != 0).then_some(data.reparse_tag)
}
