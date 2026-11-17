//! Build pinned compiler builtins and CRT startup objects for the native musl sysroot.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use super::super::{
    CopyMode, Pins, Result, TARGET, copy_tree, llvm, shell_quote, source, tool_command,
};
use super::{Toolchain, jobs};
use crate::process;

const BOOTSTRAP_FILES: &[&str] = &[
    "libclang_rt.builtins.a",
    "clang_rt.crtbegin.o",
    "clang_rt.crtend.o",
];

pub(super) fn resource_directory(prefix: &Path) -> PathBuf {
    prefix.join("compiler-rt")
}

pub(super) fn validate(prefix: &Path) -> Result<()> {
    validate_bootstrap(prefix)?;
    llvm::check_runtime_path(prefix, &profile_path(prefix))
}

fn validate_bootstrap(prefix: &Path) -> Result<()> {
    let directory = resource_directory(prefix).join("lib").join(TARGET);
    for name in BOOTSTRAP_FILES {
        llvm::check_runtime_path(prefix, &directory.join(name))?;
    }
    Ok(())
}

fn profile_path(prefix: &Path) -> PathBuf {
    resource_directory(prefix)
        .join("lib")
        .join(TARGET)
        .join("libclang_rt.profile.a")
}

pub(super) fn install_profile(prefix: &Path, archive: &Path) -> Result<()> {
    // Keep Clang's automatic instrumentation link on the same pinned archive
    // used by explicit profile-runtime links in the interpreter build.
    fs::copy(archive, profile_path(prefix))?;
    validate(prefix)
}

pub(super) fn build(root: &Path, pins: &Pins, tools: &Toolchain, work: &Path) -> Result<()> {
    let sources = work.join("compiler-rt-source");
    // Upstream uses sibling paths for its CMake helpers and SipHash headers.
    // Real copied directories preserve those paths without patching upstream.
    for (pin, directory) in [
        ("compiler_rt_source", "compiler-rt"),
        ("cmake_source", "cmake"),
        ("third_party_source", "third-party"),
    ] {
        copy_tree(
            &source(root, pins, pin)?,
            &sources.join(directory),
            CopyMode::Replace,
        )?;
    }
    let build = work.join("compiler-rt-build");
    process::run(&mut configure(root, tools, &sources, &build)?)?;
    process::run(
        tool_command(root, "cmake")?
            .arg("--build")
            .arg(&build)
            .arg("--parallel")
            .arg(jobs()?.to_string()),
    )?;
    process::run(tool_command(root, "cmake")?.arg("--install").arg(&build))?;
    validate_bootstrap(&tools.prefix)
}

fn compiler_flags(root: &Path, tools: &Toolchain) -> Result<String> {
    let output = process::output(tool_command(root, &tools.clang)?.arg("-print-resource-dir"))?;
    let headers = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim()).join("include");
    Ok(format!(
        "-nostdinc -isystem {} -isystem {} -fPIC -fno-stack-protector -march={}",
        shell_quote(&tools.sysroot.join("include"))?,
        shell_quote(&headers)?,
        if cfg!(target_arch = "aarch64") {
            "armv8-a"
        } else {
            "x86-64"
        },
    ))
}

fn configure(root: &Path, tools: &Toolchain, sources: &Path, build: &Path) -> Result<Command> {
    let flags = compiler_flags(root, tools)?;
    let mut configure = tool_command(root, "cmake")?;
    configure
        .arg("-S")
        .arg(sources.join("compiler-rt/lib/builtins"))
        .arg("-B")
        .arg(build)
        .args([
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON",
            "-DCOMPILER_RT_BUILD_CRT=ON",
            "-DCOMPILER_RT_INCLUDE_TESTS=OFF",
            "-DLLVM_RUNTIMES_BUILD=ON",
            "-DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON",
        ])
        .arg(format!("-DCMAKE_MAKE_PROGRAM={}", tools.ninja()?.display()))
        .arg(format!("-DCMAKE_SYSROOT={}", tools.sysroot.display()))
        .arg(format!(
            "-DCMAKE_INSTALL_PREFIX={}",
            resource_directory(&tools.prefix).display()
        ));
    for (language, compiler, flags) in [
        ("C", tools.clang.clone(), flags.clone()),
        (
            "CXX",
            tools.clang.with_file_name("clang++"),
            format!("{flags} -nostdinc++"),
        ),
        ("ASM", tools.clang.clone(), flags),
    ] {
        configure
            .arg(format!(
                "-DCMAKE_{language}_COMPILER={}",
                compiler.display()
            ))
            .arg(format!("-DCMAKE_{language}_COMPILER_TARGET={TARGET}"))
            .arg(format!("-DCMAKE_{language}_FLAGS={flags}"));
    }
    for (name, tool) in [
        ("AR", "llvm-ar"),
        ("RANLIB", "llvm-ranlib"),
        ("NM", "llvm-nm"),
        ("OBJDUMP", "llvm-objdump"),
    ] {
        configure.arg(format!(
            "-DCMAKE_{name}={}",
            tools.clang.with_file_name(tool).display()
        ));
    }
    Ok(configure)
}

pub(super) fn self_test(root: &Path, tools: &Toolchain, work: &Path) -> Result<()> {
    let source = work.join("compiler-runtime.c");
    let binary = work.join("compiler-runtime");
    fs::write(
        &source,
        concat!(
            "static int initialized;\n",
            "__attribute__((constructor)) static void initialize(void) { initialized = 19; }\n",
            "int main(void) {\n",
            "volatile unsigned __int128 numerator = ((unsigned __int128)1 << 100) + 7;\n",
            "volatile unsigned __int128 denominator = 3;\n",
            "unsigned __int128 n = numerator, d = denominator;\n",
            "unsigned __int128 quotient = n / d, remainder = n % d;\n",
            "return initialized != 19 || quotient * d + remainder != n || remainder >= d;\n",
            "}\n",
        ),
    )?;
    process::run(
        tool_command(root, &tools.cc)?
            .arg(&source)
            .arg("-o")
            .arg(&binary),
    )?;
    process::run(&mut tool_command(root, &binary)?)?;
    super::assert_static_elf(&binary)?;
    // The builtins `bin/cc` links are this prefix's, not the LLVM release's.
    let printed = process::output(tool_command(root, &tools.cc)?.arg("--print-libgcc-file-name"))?;
    let builtins = PathBuf::from(String::from_utf8_lossy(&printed.stdout).trim());
    llvm::check_runtime_path(&tools.prefix, &builtins)
}
