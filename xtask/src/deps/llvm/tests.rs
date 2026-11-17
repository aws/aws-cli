use super::check_runtime_path;
use crate::TaskError;
use crate::deps::tests::Directory;
use std::fs;
use std::path::Path;

#[test]
fn runtime_must_exist_inside_the_selected_toolchain() -> Result<(), TaskError> {
    let root = Directory::new()?;
    let prefix = root.0.join("managed");
    fs::create_dir(&prefix)?;
    let runtime = prefix.join("libclang_rt.builtins.a");
    assert!(check_runtime_path(&prefix, &runtime).is_err());
    assert!(check_runtime_path(&prefix, Path::new("libclang_rt.builtins.a")).is_err());
    fs::write(&runtime, b"archive fixture")?;
    check_runtime_path(&prefix, &runtime)?;
    let external = root.0.join("system-builtins.a");
    fs::write(&external, b"external fixture")?;
    assert!(check_runtime_path(&prefix, &external).is_err());
    Ok(())
}

#[cfg(unix)]
#[test]
fn runtime_symlink_cannot_select_an_external_archive() -> Result<(), TaskError> {
    use std::os::unix::fs::symlink;

    let root = Directory::new()?;
    let prefix = root.0.join("managed");
    fs::create_dir(&prefix)?;
    let external = root.0.join("system-builtins.a");
    fs::write(&external, b"external fixture")?;
    let runtime = prefix.join("libclang_rt.builtins.a");
    symlink(&external, &runtime)?;
    assert!(check_runtime_path(&prefix, &runtime).is_err());
    Ok(())
}

#[test]
fn release_members_include_every_checked_tool() {
    for name in super::TOOLS {
        let member = format!("bin/{name}");
        assert!(
            super::RELEASE_MEMBERS.contains(&member.as_str()),
            "{member}"
        );
    }
    assert_eq!(
        super::archive_members("llvm_binary"),
        super::RELEASE_MEMBERS
    );
    assert_eq!(
        super::archive_members("llvm_binary_aarch64"),
        super::RELEASE_MEMBERS
    );
    assert!(super::archive_members("cpython_source").is_empty());
}
