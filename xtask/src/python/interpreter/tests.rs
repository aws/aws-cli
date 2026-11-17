use super::*;

struct Prefix(PathBuf);

impl Prefix {
    fn new(name: &str) -> Result<Self, TaskError> {
        let path =
            std::env::temp_dir().join(format!("awscli-python-test-{}-{name}", std::process::id()));
        if path.exists() {
            fs::remove_dir_all(&path)?;
        }
        for output in CPYTHON_OUTPUTS {
            let output = path.join(output);
            if let Some(parent) = output.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(output, "built")?;
        }
        Ok(Self(path))
    }
}

impl Drop for Prefix {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn interpreter_prefix_without_payload_sysconfig_is_rebuilt() -> Result<(), TaskError> {
    let prefix = Prefix::new("missing-sysconfig")?;
    fs::write(prefix.0.join(".complete"), "ok\n")?;
    assert!(!interpreter_complete(&prefix.0));
    fs::create_dir_all(prefix.0.join(PAYLOAD_SYSCONFIG))?;
    assert!(interpreter_complete(&prefix.0));
    Ok(())
}

#[test]
fn interpreter_build_without_payload_sysconfig_is_not_recorded_complete() -> Result<(), TaskError> {
    let prefix = Prefix::new("unfinished-sysconfig")?;
    assert!(finish_interpreter(&prefix.0).is_err());
    assert!(!prefix.0.join(".complete").exists());
    fs::create_dir_all(prefix.0.join(PAYLOAD_SYSCONFIG))?;
    finish_interpreter(&prefix.0)?;
    assert!(interpreter_complete(&prefix.0));
    Ok(())
}

#[test]
fn only_linux_pgo_interpreters_train_on_the_cli() {
    // Training selects the profile tools; it never keys the stage on CLI contents.
    assert_eq!(trains_on_cli(true), cfg!(target_os = "linux"));
    assert!(!trains_on_cli(false));
}

#[test]
fn only_selected_profile_tools_extend_the_interpreter_key() {
    // The managed tools keep the key every other interpreter caller uses.
    let libraries = [Path::new("/deps/openssl-1"), Path::new("/deps/zlib-xz-1")];
    assert_eq!(
        interpreter_key(true, libraries, None),
        [b"pgo".as_slice(), b"/deps/openssl-1", b"/deps/zlib-xz-1"]
    );
    assert_eq!(
        interpreter_key(false, libraries, None),
        [b"no-pgo".as_slice(), b"/deps/openssl-1", b"/deps/zlib-xz-1"]
    );
    let tools = ProfileTools {
        llvm_profdata: PathBuf::from("/pgo/bin/llvm-profdata"),
        profile_runtime: PathBuf::from("/pgo/lib/libclang_rt.profile-musl.a"),
    };
    assert_eq!(
        interpreter_key(true, libraries, Some(&tools)),
        [
            b"pgo".as_slice(),
            b"/deps/openssl-1",
            b"/deps/zlib-xz-1",
            b"/pgo/bin/llvm-profdata",
            b"/pgo/lib/libclang_rt.profile-musl.a",
        ]
    );
}

#[test]
fn a_new_openssl_or_zlib_xz_prefix_changes_the_interpreter_key() {
    // Each is rebuilt into a new prefix; CPython links both, so the
    // interpreter must not be reused across either.
    let (openssl, zlib_xz) = (Path::new("/deps/openssl-1"), Path::new("/deps/zlib-xz-1"));
    for pgo in [true, false] {
        let key = interpreter_key(pgo, [openssl, zlib_xz], None);
        assert_ne!(
            interpreter_key(pgo, [Path::new("/deps/openssl-2"), zlib_xz], None),
            key
        );
        assert_ne!(
            interpreter_key(pgo, [openssl, Path::new("/deps/zlib-xz-2")], None),
            key
        );
    }
}
