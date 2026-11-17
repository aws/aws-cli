use build_support::NativeTarget;
use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::Command;

fn main() -> io::Result<()> {
    let mut out = io::stdout().lock();
    for key in ["AWS_NATIVE_FALLBACK_PREFIX", "AWS_NATIVE_PYTHON_LINK", "CC"] {
        writeln!(out, "cargo:rerun-if-env-changed={key}")?;
    }
    if !build_support::links_c() {
        return Ok(());
    }
    let target = NativeTarget::detect()?;
    let prefix = required_path("AWS_NATIVE_FALLBACK_PREFIX")?;
    let blob = prefix.join("awscli-v2.blob").canonicalize()?;
    let output = required_path("OUT_DIR")?;
    let assembly = output.join("payload.S");
    let object = output.join("payload.o");
    fs::write(&assembly, target.payload_assembly(&blob)?)?;
    let status = compiler()?
        .args(["-c", "-o"])
        .arg(&object)
        .arg(&assembly)
        .status()?;
    if !status.success() {
        return Err(io::Error::other("payload assembly failed"));
    }
    writeln!(out, "cargo:rerun-if-changed={}", blob.display())?;
    writeln!(out, "cargo:rustc-link-arg-bin=aws={}", object.display())?;
    if target == NativeTarget::WindowsMsvc {
        link_test_payload(target, &output, &mut out)?;
    }
    writeln!(
        out,
        "cargo:rustc-link-arg-bin=aws={}",
        target.payload_retention_flag()
    )?;
    if let Some(flag) = stack_size_flag(target) {
        writeln!(out, "cargo:rustc-link-arg-bin=aws={flag}")?;
    }
    if target == NativeTarget::LinuxMusl {
        let script = output.join("allocator.ld");
        fs::write(&script, build_support::ALLOCATOR_ASSERTIONS)?;
        writeln!(out, "cargo:rustc-link-arg-bin=aws={}", script.display())?;
    }
    if env::var_os("AWS_NATIVE_PYTHON_LINK").is_none_or(|link| link == "static") {
        for symbol in PYTHON_API_LOOKUP_SYMBOLS {
            writeln!(
                out,
                "cargo:rustc-link-arg-bin=aws={}",
                target.undefined_symbol_flag(symbol)
            )?;
        }
    }
    keep_needed_libraries(&mut out)
}

fn link_test_payload(
    target: NativeTarget,
    output: &std::path::Path,
    out: &mut impl Write,
) -> io::Result<()> {
    let assembly = target.empty_payload_assembly(output)?;
    let object = output.join("empty-payload.o");
    let status = compiler()?
        .args(["-c", "-o"])
        .arg(&object)
        .arg(&assembly)
        .status()?;
    if !status.success() {
        return Err(io::Error::other("empty payload assembly failed"));
    }
    writeln!(out, "cargo:rustc-link-arg-tests={}", object.display())
}

/// Keep the shared system CRT and Python ABI libraries in DT_NEEDED. crt-sys
/// and python-fallback name them for rustc, which links GNU targets with
/// `--as-needed`; only the binary's own build script can add the link
/// argument that keeps them.
fn keep_needed_libraries(out: &mut impl Write) -> io::Result<()> {
    for key in [
        "AWS_NATIVE_LINK_MODE",
        "AWS_NATIVE_CRT_STATIC",
        "AWS_NATIVE_PYTHON_LIBRARY",
    ] {
        writeln!(out, "cargo:rerun-if-env-changed={key}")?;
    }
    if env::var("AWS_NATIVE_LINK_MODE").as_deref() != Ok("system") {
        return Ok(());
    }
    let mut libraries = Vec::new();
    if env::var("AWS_NATIVE_CRT_STATIC").as_deref() != Ok("true") {
        libraries.extend(build_support::CRT_LIBRARIES);
    }
    let python = env::var("AWS_NATIVE_PYTHON_LIBRARY").map_err(io::Error::other)?;
    libraries.push(&python);
    writeln!(
        out,
        "cargo:rustc-link-arg-bin=aws={}",
        build_support::needed_libraries_link_arg(libraries)?
    )
}

/// The stack size the executable's `PT_GNU_STACK` header records, 16 MiB.
/// musl sizes every thread created without an explicit stack size from it,
/// capped at 8 MiB: the CRT's threads and CPython's, whose
/// `THREAD_STACK_SIZE` is 0 on Linux and so takes the default. Without the
/// header musl gives them 128 KiB, which the CRT raises to its 1 MiB minimum.
/// The threads the Rust code spawns set `cli_core::thread::THREAD_STACK_BYTES`
/// themselves.
const STACK_SIZE_BYTES: u64 = 16 * 1024 * 1024;

fn stack_size_flag(target: NativeTarget) -> Option<String> {
    match target {
        NativeTarget::LinuxMusl | NativeTarget::LinuxGnu => {
            Some(format!("-Wl,-z,stack-size={STACK_SIZE_BYTES}"))
        }
        _ => None,
    }
}

/// C API functions Python code resolves by name at run time through
/// `ctypes.pythonapi` rather than through a link-time reference.
/// prompt_toolkit's `Application.run()` saves the SIGINT handler with
/// `PyOS_getsig` and restores it with `PyOS_setsig`. Nothing in a static
/// interpreter calls `PyOS_getsig`, so section garbage collection drops it
/// and the lookup fails before the first prompt renders. `PyOS_setsig`
/// survives only because the signal module calls it, so it is listed too. A
/// dynamic interpreter's shared library already exports its whole API.
const PYTHON_API_LOOKUP_SYMBOLS: [&str; 2] = ["PyOS_getsig", "PyOS_setsig"];

fn required_path(key: &str) -> io::Result<PathBuf> {
    env::var_os(key).map(PathBuf::from).ok_or_else(|| {
        io::Error::other(format!(
            "{key} is missing; run cargo xtask deps, then cargo xtask build"
        ))
    })
}

fn compiler() -> io::Result<Command> {
    let program = required_path("CC")?;
    let mut command = Command::new(program);
    let allowlist = include_str!("../../deps/scripts/tool_environ.txt");
    for (name, _) in env::vars_os() {
        if name != "HOME"
            && !allowlist.lines().any(|allowed| {
                name == allowed.trim()
                    || (cfg!(windows)
                        && name
                            .to_str()
                            .is_some_and(|name| name.eq_ignore_ascii_case(allowed.trim())))
            })
        {
            command.env_remove(name);
        }
    }
    build_support::apply_captured_msvc_environment(&mut command, &mut io::stdout().lock())?;
    command.env("LC_ALL", "C");
    Ok(command)
}
