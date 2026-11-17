//! LLVM and musl bootstrap, including executable isolation and ABI checks.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use super::command::tool_allowlist;
use super::{
    Pins, Result, TARGET, claim_work, digest, error, files, guard, native_host, shell_quote,
    source, tool_command, work_dir, write_executable,
};
use crate::process;

mod compiler_runtime;
mod native;

#[derive(Debug, Clone)]
pub struct Toolchain {
    pub prefix: PathBuf,
    pub cc: PathBuf,
    pub ar: PathBuf,
    pub ranlib: PathBuf,
    pub clang: PathBuf,
    pub llvm_ar: PathBuf,
    pub ld_lld: PathBuf,
    pub llvm_profdata: PathBuf,
    pub sysroot: PathBuf,
    /// The driver that links Rust executables against `sysroot`'s musl when
    /// rustc passes `RUST_LINK_FLAGS`; only the Linux toolchain has one.
    pub link: Option<PathBuf>,
    pub digest: String,
    pub version: String,
    pub sdk: Option<PathBuf>,
    /// The captured MSVC environment and the file it is saved in for the
    /// drivers and build scripts that read it.
    pub msvc: Option<(super::msvc::Environment, PathBuf)>,
    pub perl: Option<PathBuf>,
    /// The pinned mimalloc source crt-sys compiles into the static musl
    /// executable; other hosts keep their allocator.
    pub mimalloc: Option<PathBuf>,
}

impl Toolchain {
    pub fn ninja(&self) -> Result<PathBuf> {
        if let Some((environment, _)) = &self.msvc {
            environment.find_tools(&["ninja-build", "ninja", "samu"])
        } else {
            super::ninja_program()
        }
    }

    pub fn apply_environment(&self, command: &mut Command) {
        if let Some((environment, file)) = &self.msvc {
            environment.apply(command);
            command.env("AWS_NATIVE_MSVC_ENV_FILE", file);
        }
    }

    /// Name the managed compilers and archivers, as every native library
    /// stage's build runs them, in the captured MSVC environment if any.
    pub fn apply_build_tools(&self, command: &mut Command) {
        self.apply_environment(command);
        command
            .env("CC", &self.cc)
            .env("CXX", &self.cc)
            .env("AR", &self.ar)
            .env("RANLIB", &self.ranlib)
            .env("ZERO_AR_DATE", "1");
    }

    /// Link a Cargo `command`'s musl executables through `bin/link`.
    ///
    /// It names the linker and appends `RUST_LINK_FLAGS` to the rustflags
    /// and rustdocflags Cargo would read; doctests link with the latter.
    /// Call it after the command sets its own flags. The link flags cannot
    /// live only in the Cargo configuration, which those variables
    /// override. A toolchain without `link`, as on macOS and Windows,
    /// leaves the command alone.
    pub fn apply_link(&self, command: &mut Command) {
        link_through(self.link.as_deref(), command);
    }

    /// Name the managed C tools, and the mimalloc source where the build
    /// links it, for a Cargo command whose build scripts compile C.
    pub fn apply_c_tools(&self, command: &mut Command) {
        command
            .env("CC", &self.cc)
            .env("AR", &self.ar)
            .env("RANLIB", &self.ranlib);
        if let Some(source) = &self.mimalloc {
            command.env("AWS_NATIVE_MIMALLOC_SOURCE", source);
        }
    }

    pub fn command(&self, root: &Path, program: impl AsRef<std::ffi::OsStr>) -> Result<Command> {
        let program = Path::new(program.as_ref());
        let resolved = if let Some((environment, _)) = &self.msvc {
            if program.components().count() == 1 {
                environment.find_tool(
                    program
                        .to_str()
                        .ok_or_else(|| error("tool name is not UTF-8"))?,
                )?
            } else {
                program.to_owned()
            }
        } else {
            program.to_owned()
        };
        let mut command = tool_command(root, resolved)?;
        self.apply_environment(&mut command);
        Ok(command)
    }
}

// Linker options must not break compile-only CMake probes that use -Werror.
// Every C dependency gets the stack protector Linux distributions default
// to; musl sets the canary before any constructor or `main` runs.
const WRAPPER_FLAGS: &str = concat!(
    "--target=x86_64-linux-musl -nostdinc ",
    "--start-no-unused-arguments -fuse-ld=lld --rtlib=compiler-rt ",
    "--end-no-unused-arguments -static -fPIC -march=x86-64 ",
    "-fno-omit-frame-pointer -fstack-protector-strong",
);

fn wrapper_flags() -> String {
    if cfg!(target_arch = "aarch64") {
        WRAPPER_FLAGS
            .replace("x86_64", "aarch64")
            .replace("-march=x86-64", "-march=armv8-a")
    } else {
        WRAPPER_FLAGS.to_owned()
    }
}

/// The rustc flags of a link through `bin/link`.
///
/// Rust's musl target links its bundled musl and startup objects unless
/// self-contained linking is off, and `bin/link` refuses them. rustc guesses
/// a linker's flavor from its file name and reads `link` as a bare linker,
/// so the flags name the compiler-driver flavor.
pub const RUST_LINK_FLAGS: [&str; 3] = [
    "-Ctarget-feature=+crt-static",
    "-Clink-self-contained=no",
    "-Clinker-flavor=gcc",
];

/// The prefix directory of the Rust runtime library `bin/link` searches:
/// the `libunwind.a` Rust's std links, which the Rust toolchain ships only
/// beside its bundled musl. The name must not contain `self-contained`,
/// which `bin/link` refuses.
const RUST_RUNTIME: &str = "rust-runtime";

/// The Linux toolchain's link driver.
fn link_driver(prefix: &Path) -> PathBuf {
    prefix.join("bin/link")
}

/// The Cargo variable that names the musl target's linker.
fn linker_variable() -> String {
    format!(
        "CARGO_TARGET_{}_LINKER",
        TARGET.to_uppercase().replace('-', "_")
    )
}

/// [`Toolchain::apply_link`] with the toolchain's `link` alone, for callers
/// that keep the driver's path but not the toolchain.
pub(super) fn link_through(link: Option<&Path>, command: &mut Command) {
    let Some(link) = link else {
        return;
    };
    command.env(linker_variable(), link);
    for (encoded, plain) in [
        ("CARGO_ENCODED_RUSTFLAGS", "RUSTFLAGS"),
        ("CARGO_ENCODED_RUSTDOCFLAGS", "RUSTDOCFLAGS"),
    ] {
        let mut flags = cargo_flags(command, encoded, plain);
        for flag in RUST_LINK_FLAGS {
            if !flags.is_empty() {
                flags.push('\x1f');
            }
            flags.push_str(flag);
        }
        command.env(encoded, flags);
    }
}

/// The `\x1f`-separated flags of one kind that Cargo reads for `command`.
///
/// They are its `encoded` variable, such as `CARGO_ENCODED_RUSTFLAGS`, else
/// its whitespace-split `plain` one, such as `RUSTFLAGS`, each as the
/// command sets or inherits it.
fn cargo_flags(command: &Command, encoded: &str, plain: &str) -> String {
    let variable = |name: &str| match command.get_envs().find(|(key, _)| *key == name) {
        Some((_, value)) => value.map(|value| value.to_string_lossy().into_owned()),
        None => std::env::var(name).ok(),
    };
    variable(encoded).unwrap_or_else(|| {
        variable(plain)
            .unwrap_or_default()
            .split_whitespace()
            .collect::<Vec<_>>()
            .join("\x1f")
    })
}

pub fn toolchain(root: &Path, pins: &Pins) -> Result<Toolchain> {
    native_host()?;
    if !cfg!(target_os = "linux") {
        return native::toolchain(root);
    }
    let rust_version = pins.version("rust_version")?;
    let rust_root = rust_sysroot(root, rust_version)?;
    let llvm = &super::llvm::release(root, pins)?;
    let llvm_version = pins.version("llvm_version")?;
    // The Rust sysroot's location stays out of the key: CI and containers
    // install rustup in fresh directories, and the `rust_version` pin
    // already keys its contents. The LLVM release needs no extra input: its
    // pin keys it.
    let hash = digest(root, "toolchain", &[wrapper_flags().as_bytes()])?;
    let prefix = super::store(root)
        .join("deps")
        .join(TARGET)
        .join(format!("toolchain-{hash}"));
    let tools = Toolchain {
        cc: prefix.join("bin/cc"),
        ar: prefix.join("bin/ar"),
        ranlib: prefix.join("bin/ranlib"),
        clang: llvm.join("bin/clang"),
        llvm_ar: llvm.join("bin/llvm-ar"),
        ld_lld: llvm.join("bin/ld.lld"),
        llvm_profdata: llvm.join("bin/llvm-profdata"),
        sysroot: prefix.join("sysroot"),
        link: Some(link_driver(&prefix)),
        prefix,
        digest: hash,
        version: llvm_version.to_owned(),
        sdk: None,
        msvc: None,
        perl: None,
        mimalloc: Some(source(root, pins, "mimalloc_source")?),
    };
    let _lock = super::lock_stage(&tools.prefix)?;
    if cached(&tools)? {
        return Ok(tools);
    }
    guard("toolchain")?;
    fs::create_dir_all(&tools.prefix)?;
    {
        // musl's make and compiler-rt's CMake tree keep objects built with
        // this key's compiler and sysroot, so they stay apart from its prefix
        // and are emptied when the key changes.
        let work = scratch(root);
        let _work_lock = claim_work(&work, &tools.prefix)?;
        build_musl(root, pins, &tools, &work)?;
        build_headers(root, pins, &tools, &work)?;
        compiler_runtime::build(root, pins, &tools, &work)?;
    }
    copy_rust_runtime(&rust_root, rust_version, &tools.prefix)?;
    wrappers(root, &tools)?;
    self_test(root, pins, &tools, &rust_root)?;
    fs::write(
        tools.prefix.join("selection.txt"),
        format!("official LLVM {}", tools.version),
    )?;
    fs::write(
        tools.prefix.join(".complete"),
        format!("{}\n{}\n", tools.digest, wrapper_flags()),
    )?;
    Ok(tools)
}

/// The Linux toolchain's scratch directory: musl's make tree, compiler-rt's
/// CMake tree, and the self-test's programs.
pub(super) fn scratch(root: &Path) -> PathBuf {
    work_dir(root, TARGET, "toolchain")
}

fn cached(tools: &Toolchain) -> Result<bool> {
    if tools.prefix.join(".complete").is_file() {
        for file in [
            &tools.cc,
            &tools.ar,
            &tools.ranlib,
            &tools.clang,
            &tools.sysroot.join("lib/libc.a"),
            &link_driver(&tools.prefix),
            &tools.prefix.join(RUST_RUNTIME).join("libunwind.a"),
        ] {
            if !file.is_file() {
                return Err(error(format!(
                    "incomplete cached toolchain: {}",
                    file.display()
                )));
            }
        }
        compiler_runtime::validate(&tools.prefix)?;
        return Ok(true);
    }
    Ok(false)
}

/// The sysroot of the pinned Rust toolchain. It is named explicitly, so a
/// caller's RUSTUP_TOOLCHAIN or toolchain override cannot select another.
pub fn rust_sysroot(root: &Path, version: &str) -> Result<PathBuf> {
    let mut command = tool_command(root, "rustup")?;
    if let Some(home) = std::env::var_os("RUSTUP_HOME") {
        command.env("RUSTUP_HOME", home);
    }
    let output = process::output(command.args(["run", version, "rustc", "--print", "sysroot"]))?;
    Ok(PathBuf::from(
        String::from_utf8_lossy(&output.stdout).trim(),
    ))
}

/// Copy the pinned Rust toolchain's `libunwind.a` into `RUST_RUNTIME`, out
/// of the directory that also holds Rust's bundled musl.
fn copy_rust_runtime(rust_root: &Path, rust_version: &str, prefix: &Path) -> Result<()> {
    let library = rust_root
        .join("lib/rustlib")
        .join(TARGET)
        .join("lib/self-contained/libunwind.a");
    let directory = prefix.join(RUST_RUNTIME);
    fs::create_dir_all(&directory)?;
    fs::copy(&library, directory.join("libunwind.a")).map_err(|failure| {
        error(format!(
            "cannot copy Rust {rust_version} libunwind {}: {failure}; install its {TARGET} target",
            library.display()
        ))
    })?;
    Ok(())
}

fn build_musl(root: &Path, pins: &Pins, tools: &Toolchain, work: &Path) -> Result<()> {
    let musl = source(root, pins, "musl")?;
    let build = work.join("musl");
    fs::create_dir_all(&build)?;
    let mut configure = tool_command(root, musl.join("configure"))?;
    configure
        .current_dir(&build)
        .args([
            &format!("--target={}-linux-musl", std::env::consts::ARCH),
            "--prefix=/",
            "--disable-shared",
            "--enable-wrapper=no",
            // musl still compiles its early startup code, which runs
            // before the canary is set, without the protector (`NOSSP_OBJS`).
            "CFLAGS=-fstack-protector-strong",
        ])
        .env(
            "CC",
            format!(
                "{} --target={}-linux-musl -fuse-ld=lld --rtlib=compiler-rt -fPIC",
                tools.clang.display(),
                std::env::consts::ARCH
            ),
        )
        .env("AR", &tools.llvm_ar)
        .env("RANLIB", tools.llvm_ar.with_file_name("llvm-ranlib"));
    process::run(&mut configure)?;
    process::run(
        tool_command(root, "make")?
            .current_dir(&build)
            .arg(format!("-j{}", jobs()?)),
    )?;
    process::run(
        tool_command(root, "make")?
            .current_dir(&build)
            .arg("install")
            .arg(format!("DESTDIR={}", tools.sysroot.display())),
    )?;
    Ok(())
}

fn build_headers(root: &Path, pins: &Pins, tools: &Toolchain, work: &Path) -> Result<()> {
    let linux = source(root, pins, "linux_headers")?;
    let build = work.join("linux-headers");
    fs::create_dir_all(&build)?;
    process::run(
        tool_command(root, "make")?
            .arg("-C")
            .arg(linux)
            .arg(format!("O={}", build.display()))
            .arg(if cfg!(target_arch = "aarch64") {
                "ARCH=arm64"
            } else {
                "ARCH=x86"
            })
            .arg("headers_install")
            .arg(format!("INSTALL_HDR_PATH={}", tools.sysroot.display()))
            .arg(format!("HOSTCC={}", tools.clang.display()))
            .arg(format!("-j{}", jobs()?)),
    )?;
    Ok(())
}

fn wrappers(root: &Path, tools: &Toolchain) -> Result<()> {
    let output = process::output(tool_command(root, &tools.clang)?.arg("-print-resource-dir"))?;
    let resource = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim());
    let cc = format!(
        "#!/bin/sh\nexec {} {} --sysroot={} -resource-dir {} -isystem {} -isystem {} \"$@\"\n",
        shell_quote(&tools.clang)?,
        wrapper_flags(),
        shell_quote(&tools.sysroot)?,
        shell_quote(&compiler_runtime::resource_directory(&tools.prefix))?,
        shell_quote(&tools.sysroot.join("include"))?,
        shell_quote(&resource.join("include"))?
    );
    write_executable(&tools.cc, &cc)?;
    write_executable(
        &link_driver(&tools.prefix),
        &link_script(tools, &tool_allowlist(root)?)?,
    )?;
    write_executable(
        &tools.ar,
        &format!("#!/bin/sh\nexec {} \"$@\"\n", shell_quote(&tools.llvm_ar)?),
    )?;
    write_executable(
        &tools.ranlib,
        &format!(
            "#!/bin/sh\nexec {} \"$@\"\n",
            shell_quote(&tools.llvm_ar.with_file_name("llvm-ranlib"))?
        ),
    )?;
    Ok(())
}

/// `bin/link`: clang links with the LLVM release's `ld.lld`, the sysroot's
/// musl and startup objects, compiler-rt's CRT objects, and Rust's libunwind.
///
/// It leaves out `bin/cc`'s compile-only flags. It refuses any argument, or
/// line of an `@file` argument, that names a `self-contained` directory:
/// rustc passes Rust's bundled musl from one without `RUST_LINK_FLAGS`, and
/// moves its arguments into an `@file` when they exceed the system's limit.
///
/// It links every executable as a static PIE, so each run loads at a random
/// address. Rust's aarch64 musl target doesn't enable static PIE, so rustc
/// asks for a fixed-address link there with `-no-pie`, which the driver
/// replaces with `-static-pie`. Every object is position-independent already,
/// and `ld.lld` rejects one that isn't. An `@file` is rewritten into a copy
/// beside it, which rustc's temporary directory then removes with the rest.
///
/// It runs clang with only the variables of the tool `allowlist`, and
/// `LC_ALL=C`, as `tool_command` runs every other tool. Cargo hands rustc,
/// and so the driver, the caller's whole environment, and clang would take
/// its linker from a caller's `COMPILER_PATH` and search a caller's
/// `LIBRARY_PATH` for libraries.
fn link_script(tools: &Toolchain, allowlist: &str) -> Result<String> {
    // `${NAME+"NAME=$NAME"}` passes a variable on only where the caller sets
    // it. A name sh can't read, such as Windows' `ProgramFiles(x86)`, is
    // never set on Linux.
    let kept: String = files::allowed_names(allowlist)
        .filter(|name| {
            let mut characters = name.chars();
            characters
                .next()
                .is_some_and(|first| first.is_ascii_alphabetic() || first == '_')
                && characters.all(|character| character.is_ascii_alphanumeric() || character == '_')
        })
        .map(|name| format!("    ${{{name}+\"{name}=${name}\"}} \\\n"))
        .collect();
    Ok(format!(
        r#"#!/bin/sh
refuse() {{
    echo "link: $1 names Rust's bundled musl; rustc needs -Clink-self-contained=no" >&2
    exit 1
}}
for argument do
    shift
    case $argument in
    */self-contained/*) refuse "$argument" ;;
    -no-pie) argument=-static-pie ;;
    @*)
        file=${{argument#@}}
        while IFS= read -r line || [ -n "$line" ]; do
            case $line in
            */self-contained/*) refuse "$argument" ;;
            -no-pie) line=-static-pie ;;
            esac
            printf '%s\n' "$line"
        done <"$file" >"$file.static-pie"
        argument=@$file.static-pie
        ;;
    esac
    set -- "$@" "$argument"
done
exec env -i \
{kept}    LC_ALL=C \
    {clang} --target={arch}-linux-musl -fuse-ld=lld --rtlib=compiler-rt \
    --sysroot={sysroot} -resource-dir {resource} -L{runtime} "$@"
"#,
        clang = shell_quote(&tools.clang)?,
        arch = std::env::consts::ARCH,
        sysroot = shell_quote(&tools.sysroot)?,
        resource = shell_quote(&compiler_runtime::resource_directory(&tools.prefix))?,
        runtime = shell_quote(&tools.prefix.join(RUST_RUNTIME))?,
    ))
}

fn self_test(root: &Path, pins: &Pins, tools: &Toolchain, rust_root: &Path) -> Result<()> {
    let work = tools.prefix.join("self-test");
    fs::create_dir_all(&work)?;
    let hello = work.join("hello.c");
    let binary = work.join("hello");
    fs::write(
        &hello,
        "#include <stdio.h>\nint main(void) { puts(\"musl toolchain ready\"); return 0; }\n",
    )?;
    process::run(
        tool_command(root, &tools.cc)?
            .arg(&hello)
            .arg("-o")
            .arg(&binary),
    )?;
    process::run(&mut tool_command(root, &binary)?)?;
    assert_static_elf(&binary)?;

    compiler_runtime::self_test(root, tools, &work)?;
    test_rust_link(root, tools, rust_root, &work)?;
    test_threads(root, tools, &work)?;
    test_configuration(root, tools, &work)?;
    test_profile(root, pins, tools, &work, &hello)?;
    fs::write(
        work.join("results.txt"),
        concat!(
            "PASS: static hello; compiler builtins/CRT constructors; ",
            "Rust static PIE through bin/link; pthread/TLS; ",
            "CMake try-compile/run; host-header rejection; ",
            "explicit/automatic instrument/run/merge/profile-use\n",
        ),
    )?;
    Ok(())
}

/// Link a Rust program through `bin/link` with `RUST_LINK_FLAGS`, as the
/// product's musl builds do, then run it and check it is a static PIE. On
/// aarch64 this covers `bin/link` replacing rustc's `-no-pie`.
fn test_rust_link(root: &Path, tools: &Toolchain, rust_root: &Path, work: &Path) -> Result<()> {
    let source = work.join("hello.rs");
    let binary = work.join("rust-hello");
    fs::write(
        &source,
        "fn main() {\n    println!(\"musl link ready\");\n}\n",
    )?;
    let mut linker = std::ffi::OsString::from("-Clinker=");
    linker.push(link_driver(&tools.prefix));
    process::run(
        tool_command(root, rust_root.join("bin/rustc"))?
            .args(["--edition=2024", "--target", TARGET])
            .arg(linker)
            .args(RUST_LINK_FLAGS)
            .arg(&source)
            .arg("-o")
            .arg(&binary),
    )?;
    process::run(&mut tool_command(root, &binary)?)?;
    assert_static_pie(&binary)
}

fn test_threads(root: &Path, tools: &Toolchain, work: &Path) -> Result<()> {
    let threads = work.join("threads.c");
    let thread_binary = work.join("threads");
    fs::write(
        &threads,
        concat!(
            "#include <pthread.h>\nstatic _Thread_local int value = 7;\n",
            "static void *worker(void *unused) { (void)unused; value = 11; ",
            "return (void *)(long)value; }\n",
            "int main(void) { pthread_t thread; void *result; ",
            "if (pthread_create(&thread, 0, worker, 0)) return 1; ",
            "if (pthread_join(thread, &result)) return 2; ",
            "return value != 7 || (long)result != 11; }\n",
        ),
    )?;
    process::run(
        tool_command(root, &tools.cc)?
            .arg(&threads)
            .arg("-pthread")
            .arg("-o")
            .arg(&thread_binary),
    )?;
    process::run(&mut tool_command(root, &thread_binary)?)?;

    Ok(())
}

fn test_configuration(root: &Path, tools: &Toolchain, work: &Path) -> Result<()> {
    let cmake_source = work.join("cmake-source");
    fs::create_dir_all(&cmake_source)?;
    fs::write(
        cmake_source.join("CMakeLists.txt"),
        concat!(
            "cmake_minimum_required(VERSION 3.20)\nproject(toolchain_probe C)\n",
            "include(CheckCSourceRuns)\ncheck_c_source_runs(\"#include <pthread.h>",
            "\\nint main(void){ return 0; }\" NATIVE_MUSL_RUNS)\n",
            "if(NOT NATIVE_MUSL_RUNS)\n",
            "message(FATAL_ERROR \"native musl try-compile did not run\")\nendif()\n",
        ),
    )?;
    process::run(
        tool_command(root, "cmake")?
            .arg("-S")
            .arg(cmake_source)
            .arg("-B")
            .arg(work.join("cmake-build"))
            .arg(format!("-DCMAKE_C_COMPILER={}", tools.cc.display())),
    )?;

    // glibc installs gnu-versions.h directly in /usr/include. Debian and
    // Ubuntu move gnu/ into the multiarch include directory, so a header
    // under gnu/ is not there.
    let absent_header = "gnu-versions.h";
    if !Path::new("/usr/include").join(absent_header).is_file()
        || tools.sysroot.join("include").join(absent_header).exists()
    {
        return Err(error(
            "header isolation probe needs host gnu-versions.h absent from musl",
        ));
    }
    let leak_probe = work.join("host-header.c");
    fs::write(&leak_probe, format!("#include <{absent_header}>\n"))?;
    let failed = tool_command(root, &tools.cc)?
        .arg("-c")
        .arg(&leak_probe)
        .arg("-o")
        .arg(work.join("host-header.o"))
        .output()?;
    if failed.status.success()
        || !String::from_utf8_lossy(&failed.stderr).contains("file not found")
    {
        return Err(error(
            "host header isolation probe did not fail as expected",
        ));
    }

    Ok(())
}

fn test_profile(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    work: &Path,
    hello: &Path,
) -> Result<()> {
    let profile = crate::python::profile(root, pins, tools)?;
    compiler_runtime::install_profile(&tools.prefix, &profile)?;
    let instrumented_object = work.join("instrumented.o");
    let instrumented = work.join("instrumented");
    let raw = work.join("hello.profraw");
    let merged = work.join("hello.profdata");
    process::run(
        tool_command(root, &tools.cc)?
            .args(["-fprofile-instr-generate", "-c"])
            .arg(hello)
            .arg("-o")
            .arg(&instrumented_object),
    )?;
    process::run(
        tool_command(root, &tools.cc)?
            .arg(&instrumented_object)
            .arg(profile)
            .args(["-Wl,-u,__llvm_profile_runtime", "-pthread", "-o"])
            .arg(&instrumented),
    )?;
    process::run(tool_command(root, &instrumented)?.env("LLVM_PROFILE_FILE", raw.as_os_str()))?;
    let automatic_raw = test_automatic_profile(root, tools, work, hello)?;
    process::run(
        tool_command(root, &tools.llvm_profdata)?
            .arg("merge")
            .arg(&raw)
            .arg(automatic_raw)
            .arg("-o")
            .arg(&merged),
    )?;
    process::run(
        tool_command(root, &tools.cc)?
            .arg(format!("-fprofile-instr-use={}", merged.display()))
            .arg(hello)
            .arg("-o")
            .arg(work.join("profile-used")),
    )?;
    process::run(&mut tool_command(root, work.join("profile-used"))?)?;
    Ok(())
}

fn test_automatic_profile(
    root: &Path,
    tools: &Toolchain,
    work: &Path,
    hello: &Path,
) -> Result<PathBuf> {
    let binary = work.join("automatic-profile");
    let raw = work.join("automatic.profraw");
    process::run(
        tool_command(root, &tools.cc)?
            .arg("-fprofile-instr-generate")
            .arg(hello)
            .arg("-o")
            .arg(&binary),
    )?;
    process::run(tool_command(root, &binary)?.env("LLVM_PROFILE_FILE", &raw))?;
    assert_static_elf(&binary)?;
    Ok(raw)
}

/// ELF's `PT_DYNAMIC` program header type: the dynamic section.
const PT_DYNAMIC: u32 = 2;
/// ELF's `PT_INTERP` program header type: the dynamic loader's path.
const PT_INTERP: u32 = 3;
/// ELF's `DT_NULL` dynamic tag, which ends the dynamic section.
const DT_NULL: u64 = 0;
/// ELF's `DT_NEEDED` dynamic tag: a shared library the executable loads.
const DT_NEEDED: u64 = 1;
/// ELF's `ET_DYN` file type, which a position-independent executable has.
const ET_DYN: u16 = 3;

/// Check that a probe is an ELF64 executable with no dynamic loader and no
/// needed shared library.
fn assert_static_elf(path: &Path) -> Result<()> {
    let bytes = fs::read(path)?;
    if bytes.len() < 64 || &bytes[..4] != b"\x7fELF" || bytes[4] != 2 || bytes[5] != 1 {
        return Err(error("toolchain probe is not ELF64 little-endian"));
    }
    let offset = usize::try_from(u64::from_le_bytes(field(&bytes, 32)?))
        .map_err(|_| error("ELF offset exceeds host size"))?;
    let size = usize::from(u16::from_le_bytes(field(&bytes, 54)?));
    let count = usize::from(u16::from_le_bytes(field(&bytes, 56)?));
    for index in 0..count {
        let start = index
            .checked_mul(size)
            .and_then(|position| offset.checked_add(position))
            .ok_or_else(|| error("invalid ELF program table"))?;
        match u32::from_le_bytes(field(&bytes, start)?) {
            PT_INTERP => return Err(error("toolchain probe has a dynamic interpreter")),
            PT_DYNAMIC => assert_no_needed(
                &bytes,
                u64::from_le_bytes(field(&bytes, start.saturating_add(8))?),
                u64::from_le_bytes(field(&bytes, start.saturating_add(32))?),
            )?,
            _ => {}
        }
    }
    Ok(())
}

/// Check that the dynamic section at file `offset`, `size` bytes long, names
/// no needed shared library.
fn assert_no_needed(bytes: &[u8], offset: u64, size: u64) -> Result<()> {
    // Each ELF64 dynamic entry is a 64-bit tag and a 64-bit value.
    const ENTRY_BYTES: u64 = 16;
    for index in 0..size / ENTRY_BYTES {
        let start = (index * ENTRY_BYTES)
            .checked_add(offset)
            .and_then(|start| usize::try_from(start).ok())
            .ok_or_else(|| error("invalid ELF dynamic section"))?;
        match u64::from_le_bytes(field(bytes, start)?) {
            DT_NULL => break,
            DT_NEEDED => return Err(error("toolchain probe needs a shared library")),
            _ => {}
        }
    }
    Ok(())
}

/// Check that a probe is a static PIE: a position-independent executable
/// with no dynamic loader and no needed shared library.
fn assert_static_pie(path: &Path) -> Result<()> {
    assert_static_elf(path)?;
    if u16::from_le_bytes(field(&fs::read(path)?, 16)?) != ET_DYN {
        return Err(error("toolchain probe is not position-independent"));
    }
    Ok(())
}

/// The `N` bytes of an ELF field at `offset` in `bytes`.
fn field<const N: usize>(bytes: &[u8], offset: usize) -> Result<[u8; N]> {
    offset
        .checked_add(N)
        .and_then(|end| bytes.get(offset..end))
        .and_then(|field| field.try_into().ok())
        .ok_or_else(|| error("truncated ELF probe"))
}

/// The dependency-build parallelism when no limit is set.
const DEFAULT_JOBS_MAX: usize = 16;

/// The parallelism of every dependency build. Cargo's own `CARGO_BUILD_JOBS`
/// sets it. Without it, builds use the available parallelism capped at
/// `DEFAULT_JOBS_MAX`. The job count is never part of a stage key.
pub fn jobs() -> Result<usize> {
    jobs_from(
        std::env::var_os("CARGO_BUILD_JOBS").as_deref(),
        std::thread::available_parallelism().map_or(4, std::num::NonZeroUsize::get),
    )
}

/// Interpret a `CARGO_BUILD_JOBS` value as Cargo does: unset or `default`
/// selects the default, a positive count is used as given, a negative count
/// leaves that many of the `available` processors idle (keeping at least one
/// job), and zero or any other text is an error.
fn jobs_from(value: Option<&std::ffi::OsStr>, available: usize) -> Result<usize> {
    let default = available.min(DEFAULT_JOBS_MAX);
    let Some(value) = value else {
        return Ok(default);
    };
    let text = value.to_str().unwrap_or_default();
    if text == "default" {
        return Ok(default);
    }
    match text.parse::<isize>() {
        Ok(0) => Err(error("CARGO_BUILD_JOBS may not be 0")),
        Ok(count) if count > 0 => Ok(count.unsigned_abs()),
        Ok(count) => Ok(available.saturating_sub(count.unsigned_abs()).max(1)),
        Err(_) => Err(error(format!(
            "could not parse CARGO_BUILD_JOBS `{}`; use `default` or a number of jobs",
            value.to_string_lossy()
        ))),
    }
}

#[cfg(test)]
mod tests;
