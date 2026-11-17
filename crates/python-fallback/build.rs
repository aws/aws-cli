use build_support::NativeTarget;
use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

const PYTHON_ABI: &str = "python3.14";

const WINDOWS_SYSTEM_LIBRARIES: &[&str] = &[
    "advapi32", "bcrypt", "crypt32", "iphlpapi", "ole32", "oleaut32", "oldnames", "pathcch",
    "rpcrt4", "shlwapi", "user32", "version", "ws2_32", "ncrypt", "secur32", "userenv",
];

// The static archives the embedded interpreter's extensions link, in link
// order: dependents before their dependencies. Windows has no s2n.
const STATIC_LIBRARIES: [&str; 20] = [
    "sqlite3",
    "bz2",
    "ffi",
    "zstd",
    "aws-c-mqtt",
    "aws-c-s3",
    "aws-c-auth",
    "aws-c-http",
    "aws-c-io",
    "aws-c-event-stream",
    "aws-c-compression",
    "aws-checksums",
    "aws-c-cal",
    "aws-c-sdkutils",
    "aws-c-common",
    "s2n",
    "ssl",
    "crypto",
    "z",
    "lzma",
];

fn main() -> io::Result<()> {
    let mut out = io::stdout().lock();
    writeln!(out, "cargo:rustc-check-cfg=cfg(aws_python_static)")?;
    if !dynamic_python() {
        writeln!(out, "cargo:rustc-cfg=aws_python_static")?;
    }
    for key in [
        "AWS_NATIVE_CRT_PREFIX",
        "AWS_NATIVE_CPYTHON_PREFIX",
        "AWS_NATIVE_FALLBACK_PREFIX",
        "AWS_NATIVE_DEPS_OVERRIDE",
        "CC",
        "AR",
        "AWS_NATIVE_SANITIZE_C",
        "AWS_NATIVE_UBSAN_RUNTIME",
        "AWS_NATIVE_PYTHON_LINK",
        "AWS_NATIVE_PYTHON_PAYLOAD",
        "AWS_NATIVE_PYTHON_INCLUDE",
        "AWS_NATIVE_PYTHON_LIBRARY_DIR",
        "AWS_NATIVE_PYTHON_LIBRARY",
        "AWS_NATIVE_PYTHON_LIBRARIES",
        "AWS_NATIVE_AWSCRT_BUNDLED",
        "AWS_NATIVE_CRT_STATIC",
        "AWS_NATIVE_LINK_MODE",
        "AWS_NATIVE_RUNTIME_BYTECODE",
    ] {
        writeln!(out, "cargo:rerun-if-env-changed={key}")?;
    }
    let fallback = required_path("AWS_NATIVE_FALLBACK_PREFIX")?;
    let output = required_path("OUT_DIR")?;
    let runtime = env::var_os("AWS_NATIVE_RUNTIME_BYTECODE")
        .map_or_else(|| fallback.join("runtime.pyc"), PathBuf::from);
    for (source, name) in [
        (runtime, "runtime.pyc"),
        (fallback.join("python_config.rs"), "python_config.rs"),
    ] {
        fs::copy(&source, output.join(name))?;
        writeln!(out, "cargo:rerun-if-changed={}", source.display())?;
    }
    if !build_support::links_c() {
        return Ok(());
    }
    let target = NativeTarget::detect()?;
    let crt = required_path("AWS_NATIVE_CRT_PREFIX")?;
    let python = required_path(if dynamic_python() {
        "AWS_NATIVE_PYTHON_LIBRARY_DIR"
    } else {
        "AWS_NATIVE_CPYTHON_PREFIX"
    })?;
    compile_shim(&crt, &python, &fallback, &output, target, &mut out)?;
    emit_link(&crt, &python, &fallback, &output, target, &mut out)?;
    if target == NativeTarget::WindowsMsvc {
        link_test_payload(&output, target, &mut out)?;
    }
    link_sanitizer(&mut out)
}

fn link_test_payload(output: &Path, target: NativeTarget, out: &mut impl Write) -> io::Result<()> {
    let assembly = target.empty_payload_assembly(output)?;
    let object = output.join("empty-payload.o");
    let status = tool_command("CC")?
        .args(["-c", "-o"])
        .arg(&object)
        .arg(&assembly)
        .status()?;
    if !status.success() {
        return Err(io::Error::other("test payload assembly failed"));
    }
    writeln!(out, "cargo:rustc-link-arg-tests={}", object.display())
}

fn required_path(key: &str) -> io::Result<PathBuf> {
    env::var_os(key).map(PathBuf::from).ok_or_else(|| {
        io::Error::other(format!(
            "{key} is missing; run cargo xtask deps, then cargo xtask build"
        ))
    })
}

fn tool_command(key: &str) -> io::Result<Command> {
    tool(required_path(key)?)
}

fn tool(program: PathBuf) -> io::Result<Command> {
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
    command.env("LC_ALL", "C").env("ZERO_AR_DATE", "1");
    Ok(command)
}

fn compile_shim(
    crt: &Path,
    python: &Path,
    fallback: &Path,
    output: &Path,
    target: NativeTarget,
    out: &mut impl Write,
) -> io::Result<()> {
    let mut objects = Vec::new();
    for (index, source) in sources(fallback).iter().enumerate() {
        let object = output.join(format!("shim-{index}.o"));
        let mut compiler = tool_command("CC")?;
        if target == NativeTarget::WindowsMsvc {
            compiler.args(["--driver-mode=gcc", "-fms-runtime-lib=static"]);
        }
        compiler.args(["-std=c11", "-O2", "-ffunction-sections", "-fdata-sections"]);
        if target != NativeTarget::WindowsMsvc {
            compiler.arg("-fPIC");
        }
        compiler.args(build_support::python_linkage_c_flags(dynamic_python()));
        compiler.args(sanitizer_flags()?);
        compiler.arg("-I").arg(crt.join("include"));
        let include = env::var_os("AWS_NATIVE_PYTHON_INCLUDE").map_or_else(
            || python.join(format!("include/{PYTHON_ABI}")),
            PathBuf::from,
        );
        compiler.arg("-I").arg(include);
        compiler.arg("-c").arg(source).arg("-o").arg(&object);
        run(&mut compiler)?;
        writeln!(out, "cargo:rerun-if-changed={}", source.display())?;
        objects.push(object);
    }
    if target == NativeTarget::LinuxMusl
        && env::var("CARGO_CFG_TARGET_ARCH").as_deref() == Ok("aarch64")
    {
        objects.push(clear_cache_object(output)?);
    }
    let archive = output.join(if target == NativeTarget::WindowsMsvc {
        "awscli-python-shim.lib"
    } else {
        "libawscli-python-shim.a"
    });
    if archive.exists() {
        fs::remove_file(&archive)?;
    }
    let mut archiver = tool_command("AR")?;
    archiver.arg("crs").arg(archive);
    run(archiver.args(objects))
}

/// compiler-rt's `__clear_cache`, extracted from the C compiler's builtins
/// archive. On aarch64, libffi calls it after writing a closure trampoline,
/// and Rust's compiler_builtins does not define it for musl targets.
fn clear_cache_object(output: &Path) -> io::Result<PathBuf> {
    let printed = tool_command("CC")?
        .arg("--print-libgcc-file-name")
        .output()?;
    if !printed.status.success() {
        return Err(io::Error::other(
            "the C compiler could not name its builtins archive",
        ));
    }
    let builtins = PathBuf::from(
        String::from_utf8(printed.stdout)
            .map_err(io::Error::other)?
            .trim(),
    );
    let member = "clear_cache.c.o";
    let mut extract = tool_command("AR")?;
    extract
        .current_dir(output)
        .arg("x")
        .arg(&builtins)
        .arg(member);
    run(&mut extract)?;
    Ok(output.join(member))
}

fn sanitizer_flags() -> io::Result<&'static [&'static str]> {
    match env::var("AWS_NATIVE_SANITIZE_C").as_deref() {
        Err(env::VarError::NotPresent) => Ok(&[]),
        Ok("trap") => Ok(&["-fsanitize=undefined", "-fsanitize-trap=undefined"]),
        Ok("full") => Ok(&[
            "-fsanitize=undefined",
            "-fsanitize-minimal-runtime",
            "-fno-sanitize-recover=all",
        ]),
        _ => Err(io::Error::other(
            "AWS_NATIVE_SANITIZE_C must be trap or full",
        )),
    }
}

fn link_sanitizer(out: &mut impl Write) -> io::Result<()> {
    if env::var("AWS_NATIVE_SANITIZE_C").as_deref() != Ok("full") {
        return Ok(());
    }
    let runtime = required_path("AWS_NATIVE_UBSAN_RUNTIME")?;
    if !runtime.is_file() {
        return Err(io::Error::other(
            "the prepared musl UBSan runtime is missing",
        ));
    }
    let parent = runtime
        .parent()
        .ok_or_else(|| io::Error::other("missing runtime parent"))?;
    writeln!(out, "cargo:rustc-link-search=native={}", parent.display())?;
    writeln!(
        out,
        "cargo:rustc-link-lib=static=clang_rt.ubsan_minimal-musl"
    )
}

fn sources(fallback: &Path) -> Vec<PathBuf> {
    let mut sources = vec![fallback.join("inittab.c")];
    if !dynamic_python() {
        sources.push(fallback.join("frozen_bootstrap.c"));
    }
    sources.extend([
        "shim/python.c".into(),
        "shim/finder.c".into(),
        "shim/sigcheck.c".into(),
    ]);
    sources
}

fn emit_link(
    crt: &Path,
    python: &Path,
    fallback: &Path,
    output: &Path,
    target: NativeTarget,
    out: &mut impl Write,
) -> io::Result<()> {
    let mut directories = vec![output.to_owned(), fallback.to_owned(), crt.join("lib")];
    if !dynamic_python() {
        directories.push(python.join("lib"));
    }
    for directory in directories {
        writeln!(
            out,
            "cargo:rustc-link-search=native={}",
            directory.display()
        )?;
    }
    writeln!(out, "cargo:rustc-link-lib=static=awscli-python-shim")?;
    if dynamic_python() {
        return emit_dynamic_link(fallback, out);
    }
    let archive = match target {
        NativeTarget::LinuxMusl => {
            isolate_python_allocator(fallback, output, out)?;
            "static:+verbatim=python-fallback-private.a"
        }
        NativeTarget::Macos => {
            copy_to_conventional_archive_name(fallback, output, out)?;
            "static=python-fallback"
        }
        _ => "static:+verbatim=python-fallback.a",
    };
    writeln!(out, "cargo:rustc-link-lib={archive}")?;
    for library in STATIC_LIBRARIES {
        if library == "s2n" && target == NativeTarget::WindowsMsvc {
            continue;
        }
        writeln!(out, "cargo:rustc-link-lib=static={library}")?;
    }
    match target {
        NativeTarget::LinuxMusl | NativeTarget::LinuxGnu => {}
        NativeTarget::Macos => {
            for framework in ["SystemConfiguration", "CoreFoundation", "Security"] {
                writeln!(out, "cargo:rustc-link-lib=framework={framework}")?;
            }
        }
        NativeTarget::WindowsMsvc => {
            for library in WINDOWS_SYSTEM_LIBRARIES {
                writeln!(out, "cargo:rustc-link-lib={library}")?;
            }
        }
        _ => return Err(io::Error::other("unsupported native Python target")),
    }
    Ok(())
}

fn copy_to_conventional_archive_name(
    fallback: &Path,
    output: &Path,
    out: &mut impl Write,
) -> io::Result<()> {
    let input = fallback.join("python-fallback.a");
    writeln!(out, "cargo:rerun-if-changed={}", input.display())?;
    fs::copy(&input, output.join("libpython-fallback.a"))?;
    Ok(())
}

fn isolate_python_allocator(
    fallback: &Path,
    output: &Path,
    out: &mut impl Write,
) -> io::Result<()> {
    let tools = llvm_tools()?;
    let input = fallback.join("python-fallback.a");
    let private = output.join("python-fallback-private.a");
    writeln!(out, "cargo:rerun-if-changed={}", input.display())?;
    let mut objcopy = tool(tools.join("rust-objcopy"))?;
    objcopy
        .args([
            "--wildcard",
            "--localize-symbol=mi_*",
            "--localize-symbol=_mi_*",
        ])
        .arg(&input)
        .arg(&private);
    run_tool(
        &mut objcopy,
        "rust-objcopy could not localize CPython's mimalloc",
    )?;
    let mut nm = tool(tools.join("llvm-nm"))?;
    let listing = nm.args(["-A", "-P"]).arg(&private).output()?;
    if !listing.status.success() {
        return Err(io::Error::other(
            "llvm-nm could not list the localized CPython archive",
        ));
    }
    build_support::check_private_mimalloc(&String::from_utf8_lossy(&listing.stdout))?;
    let mut readobj = tool(tools.join("llvm-readobj"))?;
    let groups = readobj.arg("--section-groups").arg(&private).output()?;
    if !groups.status.success() {
        return Err(io::Error::other(
            "llvm-readobj could not list the localized CPython archive's section groups",
        ));
    }
    build_support::check_private_mimalloc_groups(&String::from_utf8_lossy(&groups.stdout))
}

fn llvm_tools() -> io::Result<PathBuf> {
    let sysroot = Command::new(required_path("RUSTC")?)
        .args(["--print", "sysroot"])
        .output()?;
    if !sysroot.status.success() {
        return Err(io::Error::other("rustc could not report its sysroot"));
    }
    let sysroot = String::from_utf8(sysroot.stdout).map_err(io::Error::other)?;
    let host = env::var("HOST").map_err(io::Error::other)?;
    let tools = Path::new(sysroot.trim())
        .join("lib/rustlib")
        .join(host)
        .join("bin");
    if !["llvm-nm", "llvm-readobj"]
        .iter()
        .all(|tool| tools.join(tool).is_file())
    {
        return Err(io::Error::other(format!(
            "{} lacks llvm-nm or llvm-readobj; install the llvm-tools component from \
             rust-toolchain.toml",
            tools.display()
        )));
    }
    Ok(tools)
}

fn dynamic_python() -> bool {
    env::var("AWS_NATIVE_PYTHON_LINK").as_deref() == Ok("dynamic")
}

fn emit_dynamic_link(fallback: &Path, out: &mut impl Write) -> io::Result<()> {
    if env::var("AWS_NATIVE_LINK_MODE").as_deref() != Ok("system") {
        return Err(io::Error::other(
            "dynamic Python requires explicit system link mode",
        ));
    }
    let library_dir = required_path("AWS_NATIVE_PYTHON_LIBRARY_DIR")?;
    let library = env::var("AWS_NATIVE_PYTHON_LIBRARY").map_err(io::Error::other)?;
    writeln!(
        out,
        "cargo:rustc-link-search=native={}",
        library_dir.display()
    )?;
    writeln!(out, "cargo:rustc-link-lib=dylib={library}")?;
    for library in env::var("AWS_NATIVE_PYTHON_LIBRARIES")
        .unwrap_or_default()
        .split(',')
        .filter(|name| !name.is_empty())
    {
        writeln!(out, "cargo:rustc-link-lib={library}")?;
    }
    if env::var("AWS_NATIVE_AWSCRT_BUNDLED").as_deref() == Ok("true") {
        if !fallback.join("python-fallback.a").is_file() {
            return Err(io::Error::other(
                "prepared bundled awscrt archive is missing",
            ));
        }
        writeln!(
            out,
            "cargo:rustc-link-lib=static:+verbatim=python-fallback.a"
        )?;
        let kind = if env::var("AWS_NATIVE_CRT_STATIC").as_deref() == Ok("true") {
            "static"
        } else {
            "dylib"
        };
        for library in [
            "aws-c-mqtt",
            "aws-c-s3",
            "aws-c-auth",
            "aws-c-http",
            "aws-c-io",
            "aws-c-event-stream",
            "aws-c-compression",
            "aws-checksums",
            "aws-c-cal",
            "aws-c-sdkutils",
            "aws-c-common",
        ] {
            writeln!(out, "cargo:rustc-link-lib={kind}={library}")?;
        }
        if kind == "static" {
            writeln!(out, "cargo:rustc-link-lib=static=s2n")?;
            for library in ["crypto", "gcc_s", "pthread", "dl", "m"] {
                writeln!(out, "cargo:rustc-link-lib=dylib={library}")?;
            }
        }
    }
    Ok(())
}

fn run(command: &mut Command) -> io::Result<()> {
    run_tool(command, "embedded Python C shim build failed")
}

fn run_tool(command: &mut Command, failure: &str) -> io::Result<()> {
    if command.status()?.success() {
        Ok(())
    } else {
        Err(io::Error::other(failure.to_owned()))
    }
}
