use super::{Database, GuessError};
use std::ffi::{OsString, c_void};
use std::os::windows::ffi::OsStringExt;
use std::ptr;

type Key = *mut c_void;
const KEY_READ: u32 = 0x20019;
const SUCCESS: i32 = 0;
const NOT_FOUND: i32 = 2;
const ACCESS_DENIED: i32 = 5;
const MORE_DATA: i32 = 234;
const NO_MORE_ITEMS: i32 = 259;
const REG_SZ: u32 = 1;
const EXTENSION_UNITS_MAX: usize = 128;
const TYPE_BYTES_MAX: usize = 510;
const CONTENT_TYPE: &[u16] = &[67, 111, 110, 116, 101, 110, 116, 32, 84, 121, 112, 101, 0];

#[link(name = "advapi32")]
unsafe extern "system" {
    fn RegOpenKeyExW(
        key: Key,
        subkey: *const u16,
        options: u32,
        desired: u32,
        result: *mut Key,
    ) -> i32;
    fn RegEnumKeyExW(
        key: Key,
        index: u32,
        name: *mut u16,
        units: *mut u32,
        reserved: *mut u32,
        class: *mut u16,
        class_units: *mut u32,
        last_write: *mut c_void,
    ) -> i32;
    fn RegQueryValueExW(
        key: Key,
        name: *const u16,
        reserved: *mut u32,
        kind: *mut u32,
        data: *mut u8,
        bytes: *mut u32,
    ) -> i32;
    fn RegCloseKey(key: Key) -> i32;
}

#[link(name = "kernel32")]
unsafe extern "system" {
    fn FormatMessageW(
        flags: u32,
        source: *const c_void,
        message: u32,
        language: u32,
        buffer: *mut u16,
        units: u32,
        arguments: *const c_void,
    ) -> u32;
}

struct OwnedKey(Key);
impl Drop for OwnedKey {
    fn drop(&mut self) {
        // SAFETY: every OwnedKey comes from a successful open and is closed exactly once.
        unsafe {
            RegCloseKey(self.0);
        }
    }
}

pub(super) fn read(database: &mut Database) {
    if let Err(status) = read_all(database) {
        database.failure = Some(GuessError(error_text(status)));
    }
}

fn read_all(database: &mut Database) -> Result<(), i32> {
    // HKEY_CLASSES_ROOT is the sign-extended predefined Win32 key, never dereferenced.
    let classes = ptr::without_provenance_mut((-2147483648_isize) as usize);
    let root = open(classes, ptr::null())?;
    for index in 0..=u32::MAX {
        match read_key(database, &root, index) {
            SUCCESS | MORE_DATA => {}
            NO_MORE_ITEMS => return Ok(()),
            status => return Err(status),
        }
    }
    Err(MORE_DATA)
}

fn open(parent: Key, name: *const u16) -> Result<OwnedKey, i32> {
    let mut key = ptr::null_mut();
    // SAFETY: callers pass a live key/predefined root and a NUL-terminated name or null.
    let status = unsafe { RegOpenKeyExW(parent, name, 0, KEY_READ, &mut key) };
    if status == SUCCESS {
        Ok(OwnedKey(key))
    } else {
        Err(status)
    }
}

fn read_key(database: &mut Database, root: &OwnedKey, index: u32) -> i32 {
    let mut name = [0u16; EXTENSION_UNITS_MAX];
    let mut units = name.len() as u32;
    // SAFETY: the buffer and its capacity remain live through the synchronous enumeration.
    let status = unsafe {
        RegEnumKeyExW(
            root.0,
            index,
            name.as_mut_ptr(),
            &mut units,
            ptr::null_mut(),
            ptr::null_mut(),
            ptr::null_mut(),
            ptr::null_mut(),
        )
    };
    if status != SUCCESS {
        return status;
    }
    if units as usize >= name.len() {
        return MORE_DATA;
    }
    if units != 0 && name[0] != u16::from(b'.') {
        return SUCCESS;
    }
    let key = match open(root.0, name.as_ptr()) {
        Ok(key) => key,
        Err(NOT_FOUND | ACCESS_DENIED) => return SUCCESS,
        Err(status) => return status,
    };
    let mut value = [0u16; TYPE_BYTES_MAX / 2 + 1];
    let mut value_bytes = TYPE_BYTES_MAX as u32;
    let mut kind = 0;
    // SAFETY: every pointer addresses a live output buffer or scalar of the declared capacity.
    let status = unsafe {
        RegQueryValueExW(
            key.0,
            CONTENT_TYPE.as_ptr(),
            ptr::null_mut(),
            &mut kind,
            value.as_mut_ptr().cast(),
            &mut value_bytes,
        )
    };
    if status == NOT_FOUND {
        return SUCCESS;
    }
    if status != SUCCESS {
        return status;
    }
    if kind != REG_SZ || value_bytes == 0 {
        return SUCCESS;
    }
    if value_bytes as usize > TYPE_BYTES_MAX {
        return MORE_DATA;
    }
    value[value_bytes as usize / 2] = 0;
    let length = value
        .iter()
        .position(|unit| *unit == 0)
        .unwrap_or(value.len());
    let extension = OsString::from_wide(&name[..units as usize]);
    let mime_type = OsString::from_wide(&value[..length]);
    database.add(extension.as_encoded_bytes(), mime_type.as_encoded_bytes());
    SUCCESS
}

fn error_text(status: i32) -> Vec<u8> {
    let code = status as u32;
    let mut buffer = [0u16; 2048];
    // SAFETY: no inserts are expanded and the supplied buffer has the advertised capacity.
    let count = unsafe {
        FormatMessageW(
            0x1000 | 0x200,
            ptr::null(),
            code,
            0x400,
            buffer.as_mut_ptr(),
            buffer.len() as u32,
            ptr::null(),
        )
    } as usize;
    if count == 0 || count > buffer.len() {
        return format!("[WinError {code}] Windows Error 0x{code:x}").into_bytes();
    }
    let end = buffer[..count]
        .iter()
        .rposition(|unit| *unit > u16::from(b' ') && *unit != u16::from(b'.'))
        .map_or(0, |index| index + 1);
    let mut result = format!("[WinError {code}] ").into_bytes();
    result.extend_from_slice(OsString::from_wide(&buffer[..end]).as_encoded_bytes());
    result
}

#[cfg(test)]
mod tests;
