use build_support::NativeTarget;
use std::env;
use std::error::Error;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

fn emit(value: impl std::fmt::Display) -> io::Result<()> {
    writeln!(io::stdout().lock(), "cargo::{value}")
}

fn required(name: &str) -> Result<PathBuf, Box<dyn Error>> {
    env::var_os(name).map(PathBuf::from).ok_or_else(|| {
        format!(
            "{name} is required; run cargo xtask deps crt, then supply its com\
            pleted prefix and CC/AR wrappers"
        )
        .into()
    })
}

fn run(program: &Path, args: &[std::ffi::OsString]) -> Result<(), Box<dyn Error>> {
    let mut command = Command::new(program);
    command
        .args(args)
        .env("LC_ALL", "C")
        .env("ZERO_AR_DATE", "1");
    let allowed = include_str!("../../deps/scripts/tool_environ.txt");
    for (key, _) in env::vars_os() {
        let key_text = key.to_string_lossy();
        if key_text != "HOME"
            && !allowed.lines().any(|line| {
                line == key_text || (cfg!(windows) && line.eq_ignore_ascii_case(&key_text))
            })
        {
            command.env_remove(key);
        }
    }
    build_support::apply_captured_msvc_environment(&mut command, &mut io::stdout().lock())?;
    #[cfg(windows)]
    command.env("LC_ALL", "C").env("ZERO_AR_DATE", "1");
    if !command.status()?.success() {
        return Err(format!(
            "{} failed compiling the CRT consumer shim",
            program.display()
        )
        .into());
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    for key in [
        "AWS_NATIVE_CRT_PREFIX",
        "AWS_NATIVE_LINK_MODE",
        "AWS_NATIVE_CRT_STATIC",
        "AWS_NATIVE_CRT_INCLUDE",
        "AWS_NATIVE_CRT_LIBRARY_DIR",
        "CC",
        "AR",
        "AWS_NATIVE_CRT_INJECT_SIGNATURE_MISMATCH",
        "AWS_NATIVE_CRT_INJECT_LAYOUT_MISMATCH",
        "AWS_NATIVE_SANITIZE_C",
        "AWS_NATIVE_UBSAN_RUNTIME",
        "AWS_NATIVE_MIMALLOC_SOURCE",
    ] {
        emit(format!("rerun-if-env-changed={key}"))?;
    }
    emit("rustc-check-cfg=cfg(fuzzing)")?;
    if !build_support::links_c() {
        return Ok(());
    }
    let target = NativeTarget::detect()?;
    let system = env::var("AWS_NATIVE_LINK_MODE").as_deref() == Ok("system");
    if system != (target == NativeTarget::LinuxGnu) {
        return Err(
            "system linking requires native Linux/glibc; static Linux requires musl".into(),
        );
    }
    let prefix = required("AWS_NATIVE_CRT_PREFIX")?;
    let cc = required("CC")?;
    let ar = required("AR")?;
    let out = required("OUT_DIR")?;
    let include = system
        .then(|| env::var_os("AWS_NATIVE_CRT_INCLUDE"))
        .flatten()
        .map(PathBuf::from)
        .unwrap_or_else(|| prefix.join("include"));
    let library_dir = system
        .then(|| env::var_os("AWS_NATIVE_CRT_LIBRARY_DIR"))
        .flatten()
        .map(PathBuf::from)
        .unwrap_or_else(|| prefix.join("lib"));
    let crt_static = !system || env::var("AWS_NATIVE_CRT_STATIC").as_deref() == Ok("true");
    let archive = if target == NativeTarget::WindowsMsvc {
        "aws-c-s3.lib"
    } else if crt_static {
        "libaws-c-s3.a"
    } else {
        "libaws-c-s3.so"
    };
    if !include.join("aws/s3/s3_client.h").is_file() || !library_dir.join(archive).is_file() {
        return Err(
            "CRT dependency output is incomplete; prepare the selected native link mode".into(),
        );
    }
    compile_shim(&include, &cc, &ar, &out, target)?;
    link_libraries(&library_dir, &out, target, system, crt_static)?;
    link_sanitizer()
}

fn compile_shim(
    include: &Path,
    cc: &Path,
    ar: &Path,
    out: &Path,
    target: NativeTarget,
) -> Result<(), Box<dyn Error>> {
    let sources = [
        "shim/allocator.c",
        "shim/crt_shim.c",
        "shim/native.c",
        "shim/sigcheck.c",
    ];
    let mut objects = Vec::new();
    emit("rerun-if-changed=shim")?;
    for (index, source) in sources.iter().enumerate() {
        let object = out.join(format!("crt-{index}.o"));
        run(cc, &shim_arguments(source, &object, include, target)?)?;
        objects.push(object.into_os_string());
    }
    if target == NativeTarget::LinuxMusl {
        objects.push(compile_mimalloc(cc, out)?);
    }
    let archive_path = out.join(if target == NativeTarget::WindowsMsvc {
        "zaws-crt-shim.lib"
    } else {
        "libzaws-crt-shim.a"
    });
    // Replacing an archive preserves obsolete members; recreate it when sources retire.
    match std::fs::remove_file(&archive_path) {
        Ok(()) => {}
        Err(error) if error.kind() == io::ErrorKind::NotFound => {}
        Err(error) => return Err(error.into()),
    }
    let mut archive = vec!["rcs".into(), archive_path.into_os_string()];
    archive.extend(objects);
    run(ar, &archive)
}

fn shim_arguments(
    source: &str,
    object: &Path,
    include: &Path,
    target: NativeTarget,
) -> Result<Vec<std::ffi::OsString>, Box<dyn Error>> {
    let mut args = vec![
        "-c".into(),
        source.into(),
        "-o".into(),
        object.as_os_str().to_owned(),
        "-std=c11".into(),
        "-O2".into(),
        "-ffunction-sections".into(),
        "-fdata-sections".into(),
        "-Werror=incompatible-pointer-types".into(),
        "-I".into(),
        include.as_os_str().to_owned(),
        "-Ishim".into(),
    ];
    // Clang refuses `-fPIC` for an MSVC target, as the Python shims know.
    if target != NativeTarget::WindowsMsvc {
        args.push("-fPIC".into());
    }
    if target == NativeTarget::LinuxMusl {
        args.extend([
            "-DAWS_CLI_USE_MIMALLOC=1".into(),
            "-I".into(),
            required("AWS_NATIVE_MIMALLOC_SOURCE")?
                .join("include")
                .into_os_string(),
        ]);
    }
    args.extend(sanitizer_flags()?.iter().map(std::ffi::OsString::from));
    if target == NativeTarget::WindowsMsvc {
        args.extend(["--driver-mode=gcc".into(), "-fms-runtime-lib=static".into()]);
    }
    for define in ["SIGNATURE", "LAYOUT"] {
        if env::var_os(format!("AWS_NATIVE_CRT_INJECT_{define}_MISMATCH")).is_some() {
            args.push(format!("-DZAWS_INJECT_{define}_MISMATCH=1").into());
        }
    }
    Ok(args)
}

/// The preprocessor definitions upstream's CMake passes for a static Release
/// library on musl Linux, plus `MI_NO_GETENV`, so no `MIMALLOC_*` variable
/// can change options or print. `MI_MALLOC_OVERRIDE` stays undefined:
/// `shim/mimalloc.c` supplies the overrides.
const MIMALLOC_DEFINES: [&str; 5] = [
    "-DMI_STATIC_LIB",
    "-DMI_BUILD_RELEASE",
    "-DNDEBUG",
    "-DMI_LIBC_MUSL=1",
    "-DMI_NO_GETENV",
];

/// `mi_options_print` stamps the build date into its banner; pin it to the
/// epoch the CRT and CPython builds use as `SOURCE_DATE_EPOCH` (946684800).
const MIMALLOC_DATE_DEFINES: [&str; 3] = [
    "-Wno-builtin-macro-redefined",
    "-D__DATE__=\"Jan  1 2000\"",
    "-D__TIME__=\"00:00:00\"",
];

/// Upstream's Release compile options for Clang, then the section flags.
/// `-fno-builtin-malloc` keeps the compiler from turning a call inside the
/// allocator back into a call to the override it implements. Upstream picks
/// local-dynamic TLS for a static musl library so it stays usable in a
/// shared object; this object only links into the static executable, where
/// initial-exec is always valid.
const MIMALLOC_FLAGS: [&str; 7] = [
    "-O3",
    "-Wno-unknown-pragmas",
    "-fvisibility=hidden",
    "-ftls-model=initial-exec",
    "-fno-builtin-malloc",
    "-ffunction-sections",
    "-fdata-sections",
];

fn compile_mimalloc(cc: &Path, out: &Path) -> Result<std::ffi::OsString, Box<dyn Error>> {
    let source = required("AWS_NATIVE_MIMALLOC_SOURCE")?;
    if !source.join("src/static.c").is_file() {
        return Err("AWS_NATIVE_MIMALLOC_SOURCE is not the pinned mimalloc source".into());
    }
    emit(format!("rerun-if-changed={}", source.display()))?;
    let object = out.join("crt-mimalloc.o");
    let mut args: Vec<std::ffi::OsString> = vec![
        "-c".into(),
        "shim/mimalloc.c".into(),
        "-o".into(),
        object.as_os_str().to_owned(),
        "-fPIC".into(),
        "-I".into(),
        source.join("include").into_os_string(),
        "-I".into(),
        source.join("src").into_os_string(),
    ];
    args.extend(
        MIMALLOC_DEFINES
            .iter()
            .chain(&MIMALLOC_DATE_DEFINES)
            .chain(&MIMALLOC_FLAGS)
            .map(std::ffi::OsString::from),
    );
    let mut prefix_map = std::ffi::OsString::from("-ffile-prefix-map=");
    prefix_map.push(source.as_os_str());
    prefix_map.push("/=mimalloc/");
    args.push(prefix_map);
    run(cc, &args)?;
    Ok(object.into_os_string())
}

fn sanitizer_flags() -> Result<&'static [&'static str], Box<dyn Error>> {
    match env::var("AWS_NATIVE_SANITIZE_C").as_deref() {
        Err(env::VarError::NotPresent) => Ok(&[]),
        Ok("trap") => Ok(&["-fsanitize=undefined", "-fsanitize-trap=undefined"]),
        Ok("full") => Ok(&[
            "-fsanitize=undefined",
            "-fsanitize-minimal-runtime",
            "-fno-sanitize-recover=all",
        ]),
        _ => Err("AWS_NATIVE_SANITIZE_C must be trap or full".into()),
    }
}

fn link_sanitizer() -> Result<(), Box<dyn Error>> {
    if env::var("AWS_NATIVE_SANITIZE_C").as_deref() != Ok("full") {
        return Ok(());
    }
    let runtime = required("AWS_NATIVE_UBSAN_RUNTIME")?;
    if !runtime.is_file() {
        return Err("the prepared musl UBSan runtime is missing".into());
    }
    let parent = runtime.parent().ok_or("UBSan runtime has no parent")?;
    emit(format!("rustc-link-search=native={}", parent.display()))?;
    emit("rustc-link-lib=static=clang_rt.ubsan_minimal-musl").map_err(Into::into)
}

fn link_libraries(
    library_dir: &Path,
    out: &Path,
    target: NativeTarget,
    system: bool,
    crt_static: bool,
) -> Result<(), Box<dyn Error>> {
    emit(format!("rustc-link-search=native={}", out.display()))?;
    emit(format!(
        "rustc-link-search=native={}",
        library_dir.display()
    ))?;
    emit("rustc-link-lib=static=zaws-crt-shim")?;
    let linkage = if crt_static { "static" } else { "dylib" };
    for library in build_support::CRT_LIBRARIES {
        emit(format!("rustc-link-lib={linkage}={library}"))?;
    }
    if system {
        link_system_crt(crt_static)?;
    } else {
        link_static_crt(target)?;
    }
    Ok(())
}

fn link_system_crt(crt_static: bool) -> Result<(), Box<dyn Error>> {
    if crt_static {
        emit("rustc-link-lib=static=s2n")?;
        for library in ["crypto", "gcc_s", "pthread", "dl", "m"] {
            emit(format!("rustc-link-lib=dylib={library}"))?;
        }
    }
    Ok(())
}

fn link_static_crt(target: NativeTarget) -> Result<(), Box<dyn Error>> {
    if target == NativeTarget::LinuxMusl || target == NativeTarget::Macos {
        emit("rustc-link-lib=static=s2n")?;
    }
    for library in ["ssl", "crypto", "z", "lzma"] {
        emit(format!("rustc-link-lib=static={library}"))?;
    }
    if target == NativeTarget::Macos {
        for framework in ["CoreFoundation", "Security"] {
            emit(format!("rustc-link-lib=framework={framework}"))?;
        }
    }
    if target == NativeTarget::WindowsMsvc {
        // The Windows system libraries the CRT needs: aws-c-common's path
        // helpers need shlwapi and its process helpers psapi.
        for library in [
            "advapi32", "bcrypt", "crypt32", "iphlpapi", "kernel32", "ncrypt", "psapi", "secur32",
            "shlwapi", "ws2_32", "userenv",
        ] {
            emit(format!("rustc-link-lib={library}"))?;
        }
    }
    Ok(())
}
