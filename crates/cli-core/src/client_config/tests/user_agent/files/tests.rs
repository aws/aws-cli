use crate::client_config::user_agent::{self, Distribution};
use std::path::Path;
use std::{fs, io, os::unix::fs::PermissionsExt, path::PathBuf};

struct Directory(PathBuf);
impl Directory {
    fn new() -> io::Result<Self> {
        static SEQUENCE: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        let sequence = SEQUENCE.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let path =
            std::env::temp_dir().join(format!("aws-cli-ua-{}-{sequence}", std::process::id()));
        fs::create_dir(&path)?;
        Ok(Self(path))
    }
}
impl Drop for Directory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn os_release_falls_back_skips_nonfiles_and_keeps_only_complete_bounded_lines() -> io::Result<()> {
    let directory = Directory::new()?;
    let first = directory.0.join("etc-os-release");
    let second = directory.0.join("lib-os-release");
    fs::write(&second, "ID=rhel\nVERSION_ID=9.4")?;
    let paths = [&first as &Path, &second];
    assert_eq!(
        user_agent::read_distribution(&paths),
        Distribution {
            id: "rhel".into(),
            version_major: "9".into()
        }
    );
    assert_eq!(
        user_agent::read_distribution(&paths[..1]),
        Distribution::default()
    );
    fs::write(
        &first,
        format!("ID=arch\nVERSION_ID={}\n", "7".repeat(4096)),
    )?;
    assert_eq!(
        user_agent::read_distribution(&paths),
        Distribution {
            id: "arch".into(),
            version_major: String::new()
        }
    );
    fs::remove_file(&first)?;
    fs::create_dir(&first)?;
    assert_eq!(user_agent::read_distribution(&paths).id, "rhel");
    fs::remove_dir(&first)?;
    let fifo = std::ffi::CString::new(first.as_os_str().as_encoded_bytes())?;
    // SAFETY: the owned CString is NUL-terminated and mkfifo only reads it during the call.
    assert_eq!(unsafe { libc::mkfifo(fifo.as_ptr(), 0o600) }, 0);
    assert_eq!(user_agent::read_distribution(&paths).id, "rhel");
    assert_eq!(
        user_agent::read_distribution(&[Path::new("/dev/null"), &first]),
        Distribution::default()
    );
    let _ = user_agent::distribution();
    Ok(())
}

#[test]
fn unreadable_os_release_reports_unknown_without_falling_back() -> io::Result<()> {
    let directory = Directory::new()?;
    let denied = directory.0.join("denied");
    let fallback = directory.0.join("fallback");
    fs::write(&denied, "ID=denied\n")?;
    fs::write(&fallback, "ID=fallback\n")?;
    fs::set_permissions(&denied, fs::Permissions::from_mode(0o000))?;
    if fs::File::open(&denied).is_err() {
        assert_eq!(
            user_agent::read_distribution(&[&denied, &fallback]).id,
            "unknown"
        );
    }
    fs::set_permissions(&denied, fs::Permissions::from_mode(0o600))?;
    Ok(())
}

#[test]
fn os_release_that_is_not_utf8_reports_unknown() -> io::Result<()> {
    let directory = Directory::new()?;
    let invalid = directory.0.join("os-release");
    let fallback = directory.0.join("fallback");
    fs::write(&invalid, b"ID=caf\xc3\nVERSION_ID=7\n")?;
    fs::write(&fallback, "ID=fallback\n")?;
    assert_eq!(
        user_agent::read_distribution(&[&invalid, &fallback]),
        Distribution {
            id: "unknown".into(),
            version_major: String::new()
        }
    );
    Ok(())
}

#[test]
fn os_release_cut_by_the_bounded_read_keeps_its_complete_assignments() -> io::Result<()> {
    let directory = Directory::new()?;
    let head = "ID=ubuntu\nVERSION_ID=\"22.04\"\nNAME=\"Ubuntu\n";
    let cut = directory.0.join("cut");
    fs::write(
        &cut,
        format!(
            "{head}{}\nLinux\"\n",
            "x".repeat(user_agent::OS_RELEASE_BYTES_MAX)
        ),
    )?;
    assert_eq!(
        user_agent::read_distribution(&[&cut]),
        Distribution {
            id: "ubuntu".into(),
            version_major: "22".into()
        }
    );
    let open = directory.0.join("open");
    fs::write(&open, head)?;
    assert_eq!(user_agent::read_distribution(&[&open]).id, "unknown");
    Ok(())
}
