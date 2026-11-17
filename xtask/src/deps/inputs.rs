//! Explicit source inventories and pins consumed by native dependency cache keys.
//!
//! A stage keys only on the code that builds its output, the drivers that
//! code runs, and the pins it fetches. Orchestration that only sequences
//! stages, checks the pins, or downloads sources keys none: `deps/mod.rs`,
//! `python.rs`, and this inventory itself. Editing them changes no prefix, so
//! the tests check every file instead: each build module and driver belongs
//! to a stage or is named as unkeyed, the modules and drivers a listed file
//! uses are listed beside it, and every pin name a stage's code spells is one
//! of its pins.

use super::{Result, error};

/// The hosts whose build of a stage runs a group of inputs.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Hosts {
    All,
    Linux,
    LinuxX86_64,
    LinuxAarch64,
    NotLinux,
    Windows,
    NotWindows,
}

impl Hosts {
    fn includes(self, os: &str, arch: &str) -> bool {
        match self {
            Self::All => true,
            Self::Linux => os == "linux",
            Self::LinuxX86_64 => os == "linux" && arch == "x86_64",
            Self::LinuxAarch64 => os == "linux" && arch == "aarch64",
            Self::NotLinux => os != "linux",
            Self::Windows => os == "windows",
            Self::NotWindows => os != "windows",
        }
    }
}

/// A group of a stage's inputs and the hosts whose build uses it.
type Part = (Hosts, &'static [&'static str]);

/// The sanitized tool commands and wrappers, and the filesystem helpers they
/// and the native builders run through.
const COMMANDS: &[&str] = &[
    "xtask/src/deps/command.rs",
    "xtask/src/deps/files.rs",
    "deps/scripts/tool_environ.txt",
];
const TOOLCHAIN: &[&str] = &["xtask/src/deps/toolchain.rs"];
const LINUX_TOOLCHAIN: &[&str] = &[
    "xtask/src/deps/toolchain/compiler_runtime.rs",
    "xtask/src/deps/llvm.rs",
];
const NATIVE_TOOLCHAIN: &[&str] = &["xtask/src/deps/toolchain/native.rs"];
const MSVC: &[&str] = &["xtask/src/deps/msvc.rs", "xtask/src/deps/msvc/capture.rs"];
/// The source maps every CRT compiler carries and the host policy the
/// OpenSSL, zlib/xz, and CRT stages read.
const CRT_COMPILERS: &[&str] = &[
    "xtask/src/deps/crt/source_paths.rs",
    "xtask/src/deps/platform.rs",
];
const OPENSSL: &[&str] = &["xtask/src/deps/crt/openssl.rs"];
/// The CMake driver the zlib/xz and CRT stages build their projects with.
const CMAKE: &[&str] = &["xtask/src/deps/crt/cmake.rs"];
const ZLIB_XZ: &[&str] = &["xtask/src/deps/crt/zlib_xz.rs"];
const CRT: &[&str] = &["xtask/src/deps/crt.rs", "deps/crt-libraries.txt"];
/// The prefix and completion helpers of every Python stage.
const PYTHON_STAGE: &[&str] = &["xtask/src/python/stage.rs"];
/// The modules every driver imports, and the allowlist `build_environ.py`
/// reads to sanitize the environment of the tools they run.
const PYTHON_DRIVERS: &[&str] = &[
    "deps/scripts/build_environ.py",
    "deps/scripts/build_guard.py",
    "deps/scripts/native_target.py",
    "deps/scripts/tool_environ.txt",
];
const PROFILE: &[&str] = &[
    "xtask/src/python/profile.rs",
    "deps/scripts/build_pgo_tools.py",
];
const SUPPORT: &[&str] = &[
    "xtask/src/python/support.rs",
    "deps/scripts/build_python_deps.py",
];
const CPYTHON: &[&str] = &[
    "xtask/src/python/interpreter.rs",
    "xtask/src/deps/files.rs",
    "deps/scripts/build_cpython.py",
    "deps/scripts/build_cpython_windows.py",
    "deps/scripts/payload_sysconfig.py",
    "deps/scripts/profile_aws.py",
    "deps/cpython-linux-pyconfig.h",
];
const FALLBACK: &[&str] = &["xtask/src/python/fallback.rs"];
/// The driver every fallback phase runs.
const FALLBACK_DRIVER: &[&str] = &["deps/scripts/prepare_python_fallback.py"];
const FALLBACK_ARCHIVE: &[&str] = &[
    "deps/scripts/gen_inittab.py",
    "deps/scripts/gen_frozen_bootstrap.py",
];
const FALLBACK_PAYLOAD: &[&str] = &[
    "deps/scripts/gen_ac_index.py",
    "deps/scripts/pack.py",
    "aws-cli/requirements/download-deps/system-sandbox-lock.txt",
    "aws-cli/requirements/download-deps/system-sandbox-win-lock.txt",
];
const FALLBACK_RUNTIME: &[&str] = &["crates/python-fallback/python/runtime.py"];

/// The groups of a stage's file inventory.
///
/// The Linux toolchain's self-test builds the `profile` stage and installs
/// its runtime into compiler-rt's resource directory, which every automatic
/// `-fprofile-instr-generate` link, CPython's PGO build among them, reads.
/// The runtime is therefore part of the toolchain's output, and the Linux
/// toolchain keys on the profile stage's code and driver. The other
/// toolchains only discover the host's tools; Windows reads them from the
/// captured MSVC environment.
///
/// A stage built with another's output keys on that stage's prefix, key, or
/// the toolchain digest rather than on its code: OpenSSL and zlib/xz follow
/// the toolchain, the CRT them and the toolchain, CPython OpenSSL and
/// zlib/xz, and the fallback stages CPython. The fallback stages therefore
/// leave out the interpreter's drivers. A caller-supplied `--cpython` prefix
/// (`package consumers`) keys them by its path alone: this checkout's
/// drivers say nothing about how that prefix was built.
///
/// The CRT and CPython build the OpenSSL and zlib/xz stages they key on, and
/// leave out those stages' code all the same: an edit to it changes the
/// stage's key, which reaches the CRT's key and CPython's prefix paths.
fn parts(label: &str) -> Result<&'static [Part]> {
    use Hosts::{All, Linux, NotLinux, Windows};
    Ok(match label {
        "toolchain" => &[
            (All, COMMANDS),
            (All, TOOLCHAIN),
            (Linux, LINUX_TOOLCHAIN),
            (Linux, PYTHON_STAGE),
            (Linux, PYTHON_DRIVERS),
            (Linux, PROFILE),
            (NotLinux, NATIVE_TOOLCHAIN),
            (Windows, MSVC),
        ],
        "openssl" => &[(All, COMMANDS), (All, CRT_COMPILERS), (All, OPENSSL)],
        "zlib-xz" => &[
            (All, COMMANDS),
            (All, CRT_COMPILERS),
            (All, CMAKE),
            (All, ZLIB_XZ),
        ],
        "crt" => &[
            (All, COMMANDS),
            (All, CRT_COMPILERS),
            (All, CMAKE),
            (All, CRT),
        ],
        "profile" => &[(All, PYTHON_STAGE), (All, PYTHON_DRIVERS), (All, PROFILE)],
        "python-support" => &[(All, PYTHON_STAGE), (All, PYTHON_DRIVERS), (All, SUPPORT)],
        // The interpreter stage builds the support stage, and on Linux PGO
        // the managed profile runtime, before it runs its own driver.
        "cpython" => &[
            (All, PYTHON_STAGE),
            (All, PYTHON_DRIVERS),
            (All, SUPPORT),
            (Linux, PROFILE),
            (All, CPYTHON),
        ],
        "fallback-archive" => &[
            (All, PYTHON_STAGE),
            (All, PYTHON_DRIVERS),
            (All, FALLBACK),
            (All, FALLBACK_DRIVER),
            (All, FALLBACK_ARCHIVE),
        ],
        "fallback-payload" => &[
            (All, PYTHON_STAGE),
            (All, PYTHON_DRIVERS),
            (All, FALLBACK),
            (All, FALLBACK_DRIVER),
            (All, FALLBACK_PAYLOAD),
        ],
        "fallback-runtime" => &[
            (All, PYTHON_STAGE),
            (All, PYTHON_DRIVERS),
            (All, FALLBACK),
            (All, FALLBACK_DRIVER),
            (All, FALLBACK_RUNTIME),
        ],
        // The published prefix only links the other fallback stages'
        // outputs, whose prefixes key it.
        "fallback" => &[(All, PYTHON_STAGE), (All, FALLBACK)],
        _ => return Err(error(format!("unknown dependency input inventory {label}"))),
    })
}

/// The files whose contents key `label` on this host.
pub fn stage_files(label: &str) -> Result<Vec<&'static str>> {
    Ok(host_inputs(
        parts(label)?,
        std::env::consts::OS,
        std::env::consts::ARCH,
    ))
}

/// The inputs of `parts` that the build on `os` and `arch` uses, each once,
/// in inventory order.
fn host_inputs(parts: &[Part], os: &str, arch: &str) -> Vec<&'static str> {
    let mut inputs = Vec::new();
    for (hosts, group) in parts {
        if hosts.includes(os, arch) {
            for input in *group {
                if !inputs.contains(input) {
                    inputs.push(*input);
                }
            }
        }
    }
    inputs
}

/// The Linux toolchain's pins: the musl and kernel headers it installs, the
/// compiler-rt sources its builtins and profile runtime build from, the Rust
/// toolchain whose libunwind it copies and whose rustc its self-test links
/// with, and the LLVM version `llvm::release` requires of the official
/// release.
const TOOLCHAIN_PINS: &[&str] = &[
    "rust_version",
    "llvm_version",
    "musl",
    "linux_headers",
    "compiler_rt_source",
    "cmake_source",
    "third_party_source",
];
/// Each Linux toolchain uses its architecture's official LLVM release.
const X86_64_LLVM_PINS: &[&str] = &["llvm_binary"];
const AARCH64_LLVM_PINS: &[&str] = &["llvm_binary_aarch64"];
const OPENSSL_PINS: &[&str] = &["openssl"];
const ZLIB_XZ_PINS: &[&str] = &["zlib", "xz"];
const CRT_PINS: &[&str] = &[
    "aws_c_common",
    "aws_checksums",
    "aws_c_cal",
    "aws_c_io",
    "aws_c_compression",
    "aws_c_event_stream",
    "aws_c_http",
    "aws_c_mqtt",
    "aws_c_sdkutils",
    "aws_c_auth",
    "aws_c_s3",
];
/// The Windows CRT uses Schannel, so only the other hosts build s2n-tls.
const S2N_PINS: &[&str] = &["s2n_tls"];
const PROFILE_PINS: &[&str] = &["compiler_rt_source"];
const SUPPORT_PINS: &[&str] = &["sqlite", "bzip2", "libffi", "zstd"];
const CPYTHON_PINS: &[&str] = &["cpython", "python_version"];
/// The archive compiles, and the payload packs, the pinned aws-crt-python.
const AWSCRT_PINS: &[&str] = &["awscrt", "awscrt_version"];

/// The groups of a stage's pins, named as in deps/pins.toml `[sources]` or
/// `[versions]`. As with the files, the interpreter keys on the pins of the
/// stages it builds itself.
fn pin_parts(label: &str) -> Result<&'static [Part]> {
    use Hosts::{All, Linux, LinuxAarch64, LinuxX86_64, NotWindows};
    Ok(match label {
        "toolchain" => &[
            (Linux, TOOLCHAIN_PINS),
            (LinuxX86_64, X86_64_LLVM_PINS),
            (LinuxAarch64, AARCH64_LLVM_PINS),
        ],
        "openssl" => &[(All, OPENSSL_PINS)],
        "zlib-xz" => &[(All, ZLIB_XZ_PINS)],
        "crt" => &[(All, CRT_PINS), (NotWindows, S2N_PINS)],
        "profile" => &[(All, PROFILE_PINS)],
        "python-support" => &[(All, SUPPORT_PINS)],
        "cpython" => &[
            (All, SUPPORT_PINS),
            (Linux, PROFILE_PINS),
            (All, CPYTHON_PINS),
        ],
        "fallback-archive" | "fallback-payload" => &[(All, AWSCRT_PINS)],
        "fallback-runtime" | "fallback" => &[],
        _ => return Err(error(format!("unknown dependency pin inventory {label}"))),
    })
}

/// The deps/pins.toml entries that key `label` on this host. A source keys
/// it by URL, digest, and unpacking; a version by its value.
pub fn stage_pins(label: &str) -> Result<Vec<&'static str>> {
    Ok(host_inputs(
        pin_parts(label)?,
        std::env::consts::OS,
        std::env::consts::ARCH,
    ))
}

/// Host tools the Linux toolchain runs that can change what it builds: CMake
/// configures compiler-rt. The other toolchains only discover their tools.
const TOOLCHAIN_TOOLS: &[&str] = if cfg!(target_os = "linux") {
    &["cmake"]
} else {
    &[]
};
/// Perl generates OpenSSL's Makefile, configuration headers, and perlasm
/// assembly.
const OPENSSL_TOOLS: &[&str] = &["perl"];
/// CMake configures zlib, xz, and the AWS C libraries. None of them runs
/// perl; the CRT follows OpenSSL's through the OpenSSL key in its own.
const CMAKE_TOOLS: &[&str] = &["cmake"];

/// The host tools whose `--version` output keys a stage: those it runs that
/// can change what it builds. Ninja and make only run the commands they are
/// given, and the system Python only runs the drivers, whose bytecode and
/// generated sources come from the project-built interpreter, so none of
/// them keys a stage. A stage built with another's output follows that
/// stage's tools through the toolchain digest or prefix in its own key: the
/// CPython stage, for instance, keys on OpenSSL's prefix, the CRT on its
/// key, and the fallback stages on CPython's prefix, so they all rebuild
/// when OpenSSL's perl does.
///
/// Windows takes its tool identity from the captured MSVC environment in
/// `native::toolchain` instead, so no stage there probes the PATH.
pub fn stage_tools(label: &str) -> Result<&'static [&'static str]> {
    let tools = match label {
        "toolchain" => TOOLCHAIN_TOOLS,
        "openssl" => OPENSSL_TOOLS,
        "zlib-xz" | "crt" => CMAKE_TOOLS,
        "profile" | "python-support" | "cpython" | "fallback-archive" | "fallback-payload"
        | "fallback-runtime" | "fallback" => &[],
        _ => return Err(error(format!("unknown dependency tool inventory {label}"))),
    };
    Ok(if cfg!(windows) { &[] } else { tools })
}

#[cfg(test)]
mod tests;
