//! The text a local filesystem or system failure is reported by in a
//! transfer's result line or error. Errno-backed failures read as the
//! C library's `strerror` text, which is also what the Python CLI shows;
//! the rest are short descriptions. The values are distinct, because a
//! commit failure is mapped back to its errno by its text.

pub const ACCESS_DENIED: &str = "Permission denied";
pub const ADVISE_FAILED: &str = "madvise failed";
pub const BAD_PATH_NAME: &str = "Invalid path name";
pub const BROKEN_PIPE: &str = "Broken pipe";
pub const CONNECTION_RESET_BY_PEER: &str = "Connection reset by peer";
pub const CROSS_DEVICE: &str = "Invalid cross-device link";
pub const CURRENT_DIR_UNLINKED: &str = "Current directory was removed";
pub const DEVICE_BUSY: &str = "Device or resource busy";
pub const DIR_NOT_EMPTY: &str = "Directory not empty";
pub const DISK_QUOTA: &str = "Disk quota exceeded";
pub const FILE_BUSY: &str = "File is busy";
pub const FILE_LOCKS_UNSUPPORTED: &str = "File locking not supported";
pub const FILE_NOT_FOUND: &str = "No such file or directory";
pub const FILE_RESIZE_FAILED: &str = "Could not resize file";
pub const FILE_TOO_BIG: &str = "File too large";
pub const INPUT_OUTPUT: &str = "Input/output error";
pub const INTERRUPTED: &str = "Interrupted system call";
pub const INVALID_ARGUMENT: &str = "Invalid argument";
pub const IS_DIR: &str = "Is a directory";
pub const LINK_QUOTA_EXCEEDED: &str = "Too many links";
pub const LOCKED_MEMORY_LIMIT_EXCEEDED: &str = "Locked memory limit exceeded";
pub const MAPPING_ALREADY_EXISTS: &str = "Mapping already exists";
pub const MEMORY_MAPPING_NOT_SUPPORTED: &str = "Memory mapping not supported";
pub const NAME_TOO_LONG: &str = "File name too long";
pub const NOT_DIR: &str = "Not a directory";
pub const NOT_OPEN_FOR_READING: &str = "File not open for reading";
pub const NOT_OPEN_FOR_WRITING: &str = "File not open for writing";
pub const NO_DEVICE: &str = "No such device";
pub const NO_SPACE_LEFT: &str = "No space left on device";
pub const OUT_OF_MEMORY: &str = "Out of memory";
pub const OVERFLOW: &str = "Value too large";
pub const PATH_ALREADY_EXISTS: &str = "File exists";
pub const PERMISSION_DENIED: &str = "Operation not permitted";
pub const PROCESS_FD_QUOTA_EXCEEDED: &str = "Too many open files";
pub const RANDOM_UNAVAILABLE: &str = "No random source available";
pub const READ_ONLY_FILE_SYSTEM: &str = "Read-only file system";
pub const SOCKET_UNCONNECTED: &str = "Socket is not connected";
pub const STREAM_TOO_LONG: &str = "Input too long";
pub const SYM_LINK_LOOP: &str = "Too many levels of symbolic links";
pub const SYSTEM_FD_QUOTA_EXCEEDED: &str = "Too many open files in system";
pub const SYSTEM_RESOURCES: &str = "Insufficient system resources";
pub const UNEXPECTED: &str = "Unexpected error";
pub const UNSEEKABLE: &str = "File is not seekable";
pub const UNSUPPORTED: &str = "Operation not supported";
pub const WOULD_BLOCK: &str = "Resource temporarily unavailable";
pub const WRITE_ZERO: &str = "Write made no progress";
