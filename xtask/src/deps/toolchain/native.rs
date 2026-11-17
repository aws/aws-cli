//! Native Apple and Windows compiler discovery; these paths never emulate a host.

use std::fs;
use std::path::{Path, PathBuf};

use super::Toolchain;
use crate::deps::{
    Result, TARGET, digest, error, msvc, shell_quote, tool_command, write_executable,
};
use crate::process;

fn apple(root: &Path, name: &str) -> Result<PathBuf> {
    let output = process::output(tool_command(root, "/usr/bin/xcrun")?.args(["-f", name]))?;
    let path = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim());
    if !path.is_absolute() || !path.is_file() {
        return Err(error(format!("xcrun did not resolve {name}")));
    }
    Ok(path)
}

pub(super) fn toolchain(root: &Path) -> Result<Toolchain> {
    let msvc = cfg!(windows).then(|| msvc::discover(root)).transpose()?;
    let NativeTools {
        clang,
        ar,
        ranlib,
        ld,
        profdata,
        sdk,
    } = discover(root, msvc.as_ref())?;
    let perl = msvc
        .as_ref()
        .map(|environment| msvc::native_perl(root, environment))
        .transpose()?;
    let mut probe = tool_command(root, &clang)?;
    if let Some(environment) = &msvc {
        environment.apply(&mut probe);
    }
    let identity = process::output(probe.arg("--version"))?.stdout;
    let sdk_text = sdk
        .as_ref()
        .map_or_else(String::new, |sdk| sdk.display().to_string());
    let native_identity = native_identity(
        root,
        msvc.as_ref(),
        &[&clang, &ar, &ranlib, &ld, &profdata],
        perl.as_deref(),
    )?;
    let hash = digest(
        root,
        "toolchain",
        &[&identity, sdk_text.as_bytes(), &native_identity],
    )?;
    let prefix = crate::deps::store(root)
        .join("deps")
        .join(TARGET)
        .join(format!("toolchain-{hash}"));
    let cc = publish(&prefix, &clang, sdk.as_deref(), &identity, &hash)?;
    // The captured prompt also carries PATH, TEMP, and TMP, which the key
    // leaves out, so each command saves its own in its checkout.
    let msvc = msvc
        .map(|environment| {
            let file = environment.save(&root.join("target/msvc-environment"))?;
            Ok::<_, crate::TaskError>((environment, file))
        })
        .transpose()?;
    Ok(Toolchain {
        prefix,
        cc,
        ar: ar.clone(),
        ranlib,
        clang,
        llvm_ar: ar,
        ld_lld: ld,
        llvm_profdata: profdata,
        sysroot: sdk.clone().unwrap_or_default(),
        link: None,
        digest: hash,
        version: String::from_utf8_lossy(&identity).into_owned(),
        sdk,
        msvc,
        perl,
        mimalloc: None,
    })
}

/// Complete the toolchain prefix `prefix` under its lock, unless a build
/// already has, and return its C compiler.
///
/// A complete prefix is never rewritten: another build may be running its
/// wrapper, and the key covers everything in it.
fn publish(
    prefix: &Path,
    clang: &Path,
    sdk: Option<&Path>,
    identity: &[u8],
    hash: &str,
) -> Result<PathBuf> {
    let _lock = crate::deps::lock_stage(prefix)?;
    let cc = compiler(prefix, clang, sdk);
    if !prefix.join(".complete").is_file() {
        if let Some(sdk) = sdk {
            write_wrapper(&cc, clang, sdk)?;
        }
        fs::create_dir_all(prefix)?;
        fs::write(prefix.join("selection.txt"), identity)?;
        fs::write(prefix.join(".complete"), hash)?;
    }
    Ok(cc)
}

/// The C compiler of the toolchain at `prefix`: with an Apple SDK, the
/// wrapper `write_wrapper` writes there, and otherwise `clang` itself.
fn compiler(prefix: &Path, clang: &Path, sdk: Option<&Path>) -> PathBuf {
    if sdk.is_some() {
        prefix.join("bin/cc")
    } else {
        clang.to_owned()
    }
}

/// Write the wrapper at `wrapper` that runs `clang` against the Apple `sdk`.
fn write_wrapper(wrapper: &Path, clang: &Path, sdk: &Path) -> Result<()> {
    let minimum = if cfg!(target_arch = "aarch64") {
        "11.0"
    } else {
        "10.15"
    };
    write_executable(
        wrapper,
        &format!(
            "#!/bin/sh\nexec {} -isysroot {} -mmacosx-version-min={minimum} -fPIC \"$@\"\n",
            shell_quote(clang)?,
            shell_quote(sdk)?,
        ),
    )
}

struct NativeTools {
    clang: PathBuf,
    ar: PathBuf,
    ranlib: PathBuf,
    ld: PathBuf,
    profdata: PathBuf,
    sdk: Option<PathBuf>,
}

fn discover(root: &Path, msvc: Option<&msvc::Environment>) -> Result<NativeTools> {
    let (clang, ar, ranlib, ld, profdata, sdk) = if cfg!(target_os = "macos") {
        let output = process::output(tool_command(root, "/usr/bin/xcrun")?.args([
            "--sdk",
            "macosx",
            "--show-sdk-path",
        ]))?;
        let sdk = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim());
        (
            apple(root, "clang")?,
            apple(root, "ar")?,
            apple(root, "ranlib")?,
            apple(root, "clang")?,
            apple(root, "llvm-profdata")?,
            Some(sdk),
        )
    } else {
        let environment = msvc.ok_or_else(|| error("missing native MSVC environment"))?;
        (
            environment.find_tool("clang")?,
            environment.find_tool("llvm-ar")?,
            environment.find_tool("llvm-ranlib")?,
            environment.find_tool("lld-link")?,
            environment.find_tool("llvm-profdata")?,
            None,
        )
    };
    Ok(NativeTools {
        clang,
        ar,
        ranlib,
        ld,
        profdata,
        sdk,
    })
}

fn native_identity(
    root: &Path,
    msvc: Option<&msvc::Environment>,
    programs: &[&PathBuf],
    perl: Option<&Path>,
) -> Result<Vec<u8>> {
    let mut identity = Vec::new();
    if let Some(environment) = msvc {
        identity.extend(environment.identity()?);
        identity.extend(windows_build_identity(root, environment)?);
    }
    for program in programs.iter().map(|path| path.as_path()).chain(perl) {
        identity.extend(program.as_os_str().as_encoded_bytes());
        identity.push(0);
        if let Some(environment) = msvc {
            let mut command = tool_command(root, program)?;
            environment.apply(&mut command);
            identity.extend(process::output(command.arg("--version"))?.stdout);
        }
    }
    Ok(identity)
}

fn windows_build_identity(root: &Path, environment: &msvc::Environment) -> Result<Vec<u8>> {
    let mut identity = Vec::new();
    let cmake = environment.find_tool("cmake")?;
    let ninja = environment.find_tools(&["ninja-build", "ninja", "samu"])?;
    for program in [cmake, ninja] {
        identity.extend(program.as_os_str().as_encoded_bytes());
        identity.push(0);
        let mut command = tool_command(root, program)?;
        environment.apply(&mut command);
        let output = process::output(command.arg("--version"))?;
        identity.extend(output.stdout);
        identity.extend(output.stderr);
    }
    // nmake has no GNU-style version switch. Its complete binary identity
    // detects a changed tool even when the SDK reports the same version.
    let nmake = environment.find_tool("nmake")?;
    identity.extend(nmake.as_os_str().as_encoded_bytes());
    identity.push(0);
    identity.extend(fs::read(nmake)?);
    Ok(identity)
}
