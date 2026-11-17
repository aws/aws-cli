use super::super::{CONTENT_TYPE, KEY_READ, Key, NOT_FOUND, OwnedKey, REG_SZ, SUCCESS, open};
use std::ffi::c_void;
use std::io;
use std::ptr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

const KEY_WRITE: u32 = 0x20006;
const DELETE: u32 = 0x10000;
const VOLATILE: u32 = 1;
const CREATED_NEW_KEY: u32 = 1;
static NEXT: AtomicU64 = AtomicU64::new(0);

#[link(name = "advapi32")]
unsafe extern "system" {
    fn RegCreateKeyExW(
        parent: Key,
        name: *const u16,
        reserved: u32,
        class: *const u16,
        options: u32,
        desired: u32,
        attributes: *const c_void,
        result: *mut Key,
        disposition: *mut u32,
    ) -> i32;
    fn RegSetValueExW(
        key: Key,
        name: *const u16,
        reserved: u32,
        kind: u32,
        data: *const u8,
        bytes: u32,
    ) -> i32;
    fn RegDeleteTreeW(parent: Key, name: *const u16) -> i32;
}

pub(super) struct Fixture {
    name: Vec<u16>,
    key: Option<OwnedKey>,
    removed: bool,
}

impl std::fmt::Debug for Fixture {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("Fixture")
            .field("name", &self.name)
            .field("removed", &self.removed)
            .finish_non_exhaustive()
    }
}

impl Fixture {
    pub fn new() -> io::Result<Self> {
        let time = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(io::Error::other)?
            .as_nanos();
        let name = wide(&format!(
            "Software\\AwsCliNativeMimeTest-{}-{time}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        let (key, disposition) = create(current_user(), &name)?;
        if disposition != CREATED_NEW_KEY {
            return Err(io::Error::new(
                io::ErrorKind::AlreadyExists,
                "registry fixture name already exists; leaving it untouched",
            ));
        }
        Ok(Self {
            name,
            key: Some(key),
            removed: false,
        })
    }

    pub fn key(&self) -> io::Result<&OwnedKey> {
        self.key
            .as_ref()
            .ok_or_else(|| io::Error::other("registry fixture is closed"))
    }

    pub fn create_empty(&self, name: &str) -> io::Result<()> {
        let (key, _) = create(self.key()?.0, &wide(name))?;
        drop(key);
        Ok(())
    }

    pub fn set_value(&self, name: &str, kind: u32, value: &[u16]) -> io::Result<()> {
        let (key, _) = create(self.key()?.0, &wide(name))?;
        if kind == REG_SZ && !value.is_empty() && value.last() != Some(&0) {
            return Err(io::Error::other("string fixture must end with NUL"));
        }
        let bytes = u32::try_from(std::mem::size_of_val(value)).map_err(io::Error::other)?;
        let data = if value.is_empty() {
            ptr::null()
        } else {
            value.as_ptr().cast()
        };
        // SAFETY: key is owned; the fixed name and complete value buffer remain live for the call.
        status(unsafe { RegSetValueExW(key.0, CONTENT_TYPE.as_ptr(), 0, kind, data, bytes) })
    }

    pub fn finish(mut self) -> io::Result<()> {
        self.cleanup()?;
        match open(current_user(), self.name.as_ptr()) {
            Err(NOT_FOUND) => Ok(()),
            Err(code) => Err(io::Error::from_raw_os_error(code)),
            Ok(_) => Err(io::Error::other("registry fixture survived cleanup")),
        }
    }

    fn cleanup(&mut self) -> io::Result<()> {
        if self.removed {
            return Ok(());
        }
        drop(self.key.take());
        // SAFETY: this NUL-terminated path was newly created by this fixture; all keys are closed.
        status(unsafe { RegDeleteTreeW(current_user(), self.name.as_ptr()) })?;
        self.removed = true;
        Ok(())
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = self.cleanup();
    }
}

pub(super) fn wide(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(Some(0)).collect()
}

fn current_user() -> Key {
    // HKEY_CURRENT_USER is a sign-extended predefined handle, never dereferenced.
    ptr::without_provenance_mut((-2147483647_isize) as usize)
}

fn create(parent: Key, name: &[u16]) -> io::Result<(OwnedKey, u32)> {
    if name.last() != Some(&0) || name[..name.len() - 1].contains(&0) {
        return Err(io::Error::other(
            "registry fixture key must have one trailing NUL",
        ));
    }
    let mut key = ptr::null_mut();
    let mut disposition = 0;
    // SAFETY: parent is live, name is terminated, and both output pointers address local storage.
    status(unsafe {
        RegCreateKeyExW(
            parent,
            name.as_ptr(),
            0,
            ptr::null(),
            VOLATILE,
            KEY_READ | KEY_WRITE | DELETE,
            ptr::null(),
            &mut key,
            &mut disposition,
        )
    })?;
    Ok((OwnedKey(key), disposition))
}

fn status(code: i32) -> io::Result<()> {
    if code == SUCCESS {
        Ok(())
    } else {
        Err(io::Error::from_raw_os_error(code))
    }
}
