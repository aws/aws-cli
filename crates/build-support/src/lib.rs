//! Native-host validation and executable-format policy for Cargo build scripts.
#![deny(unsafe_code)]

mod allocation;
pub use allocation::allocated_bytes;
mod msvc_environment;
pub use msvc_environment::apply_captured_msvc_environment;
mod private_mimalloc;
pub use private_mimalloc::{
    ALLOCATOR_ASSERTIONS, MIMALLOC_LOCALIZE_ARGUMENTS, check_private_mimalloc,
    check_private_mimalloc_groups,
};

use std::io;
use std::path::Path;

/// Supported native ABI; validation always compares the host and requested target first.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum NativeTarget {
    LinuxMusl,
    LinuxGnu,
    Macos,
    WindowsMsvc,
}

impl NativeTarget {
    /// Resolve Cargo's target variables, rejecting cross-platform or cross-architecture work.
    pub fn detect() -> io::Result<Self> {
        let host = std::env::var("HOST").map_err(io::Error::other)?;
        let target = std::env::var("TARGET").map_err(io::Error::other)?;
        Self::from_triples(&host, &target)
    }

    /// Permit an ABI change only on the same native architecture and operating system.
    pub fn from_triples(host: &str, target: &str) -> io::Result<Self> {
        let host_arch = architecture(host)?;
        let target_arch = architecture(target)?;
        let host_os = operating_system(host)?;
        let target_os = operating_system(target)?;
        if host_arch != target_arch || host_os != target_os {
            return Err(io::Error::other(format!(
                "cross compilation is forbidden: host {host}, target {target}"
            )));
        }
        if target_os == "linux" && target.ends_with("-gnu") {
            require_system_architecture(target)?;
            return Ok(Self::LinuxGnu);
        }
        if !matches!(target_arch, "x86_64" | "aarch64") {
            return Err(io::Error::other(format!(
                "unsupported architecture: {target}"
            )));
        }
        match target_os {
            "linux" if target.ends_with("-musl") => Ok(Self::LinuxMusl),
            "darwin" => Ok(Self::Macos),
            "windows" if target_arch == "x86_64" && target.ends_with("-msvc") => {
                Ok(Self::WindowsMsvc)
            }
            _ => Err(io::Error::other(format!(
                "unsupported native target: {target}"
            ))),
        }
    }

    /// Assembly which embeds one read-only payload without a Rust compiler copy.
    pub fn payload_assembly(self, path: &Path) -> io::Result<String> {
        let path = path
            .to_str()
            .ok_or_else(|| io::Error::other("payload assembly path must be UTF-8"))?
            .replace('\\', "/");
        if path.contains(['\n', '\r', '"', '\0']) {
            return Err(io::Error::other(
                "payload path cannot be represented in assembly",
            ));
        }
        let (section, prefix, trailer) = match self {
            Self::LinuxMusl | Self::LinuxGnu => (
                ".section .pyload,\"a\",@progbits",
                "",
                ".section .note.GNU-stack,\"\",@progbits\n",
            ),
            Self::Macos => (
                ".section __DATA_CONST,__pyload,regular,no_dead_strip",
                "_",
                "",
            ),
            Self::WindowsMsvc => (".section .pyload,\"dr\"", "", ""),
        };
        Ok(format!(
            "{section}\n.balign 16\n.global {prefix}awscli_payload_start\n\
             {prefix}awscli_payload_start:\n.incbin \"{path}\"\n\
             .global {prefix}awscli_payload_end\n{prefix}awscli_payload_end:\n{trailer}"
        ))
    }

    /// Write an empty payload and the assembly that embeds it into
    /// `directory`, returning the assembly, for test binaries that link the
    /// payload reader without the executable's payload. ELF and Mach-O links
    /// drop the reader's unused reference with its section, but link.exe
    /// resolves every symbol a linked object names.
    pub fn empty_payload_assembly(self, directory: &Path) -> io::Result<std::path::PathBuf> {
        let payload = directory.join("empty-payload.bin");
        let assembly = directory.join("empty-payload.S");
        std::fs::write(&payload, [])?;
        std::fs::write(&assembly, self.payload_assembly(&payload)?)?;
        Ok(assembly)
    }

    /// Linker argument that retains the payload even when all other references are stripped.
    pub fn payload_retention_flag(self) -> String {
        self.undefined_symbol_flag("awscli_payload_start")
    }

    /// Linker argument that keeps a C symbol through section garbage collection.
    ///
    /// The linker takes the object-file spelling: Mach-O prefixes every C
    /// symbol with an underscore, while ELF and 64-bit COFF use the bare name.
    pub fn undefined_symbol_flag(self, symbol: &str) -> String {
        match self {
            Self::LinuxMusl | Self::LinuxGnu => format!("-Wl,--undefined={symbol}"),
            Self::Macos => format!("-Wl,-u,_{symbol}"),
            Self::WindowsMsvc => format!("/INCLUDE:{symbol}"),
        }
    }
}

/// The architectures a native Linux/glibc system build admits, as rustc's
/// triples spell them, each with its ELF `e_machine`.
pub const SYSTEM_ARCHITECTURES: [(&str, u16); 5] = [
    ("x86_64", EM_X86_64),
    ("aarch64", EM_AARCH64),
    ("riscv64gc", EM_RISCV),
    ("powerpc64le", EM_PPC64),
    ("loongarch64", EM_LOONGARCH),
];
const EM_PPC64: u16 = 21;
const EM_X86_64: u16 = 62;
const EM_AARCH64: u16 = 183;
const EM_RISCV: u16 = 243;
const EM_LOONGARCH: u16 = 258;

/// The ELF `e_machine` of an architecture [`SYSTEM_ARCHITECTURES`] lists,
/// under rustc's triple spelling.
pub fn system_elf_machine(arch: &str) -> Option<u16> {
    SYSTEM_ARCHITECTURES
        .iter()
        .find(|(name, _)| *name == arch)
        .map(|&(_, machine)| machine)
}

/// Reject a Linux/glibc triple whose architecture [`SYSTEM_ARCHITECTURES`]
/// does not list, naming the ones it does.
pub fn require_system_architecture(triple: &str) -> io::Result<()> {
    if system_elf_machine(architecture(triple)?).is_some() {
        return Ok(());
    }
    let [names @ .., last] = SYSTEM_ARCHITECTURES.map(|(name, _)| name);
    Err(io::Error::other(format!(
        "unsupported architecture: {triple}; Linux/glibc builds support only \
         the 64-bit little-endian {} and {last}",
        names.join(", ")
    )))
}

/// The CRT libraries every native link takes, in link order: the `aws-*`
/// group of `deps/crt-libraries.txt`, which a system build links as shared
/// libraries unless `AWS_NATIVE_CRT_STATIC` is `true`.
pub const CRT_LIBRARIES: [&str; 11] = [
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
];

/// Compiler flags that tell CPython's headers how the glue is linked.
///
/// Only the static interpreter compiles the glue as a builtin core module; a
/// distro shared libpython is consumed like any extension.
pub fn python_linkage_c_flags(dynamic_python: bool) -> &'static [&'static str] {
    if dynamic_python {
        &[]
    } else {
        &["-DPy_BUILD_CORE_BUILTIN=1"]
    }
}

/// GNU linker argument that keeps each shared library in `DT_NEEDED`.
///
/// rustc links GNU targets with `--as-needed`, so a library the binary never
/// references would leave `DT_NEEDED`, and stable rustc rejects the
/// `-as-needed` link modifier. Naming the libraries again under
/// `--no-as-needed` keeps them: both GNU ld and LLD record a shared library as
/// needed when any of its mentions is.
pub fn needed_libraries_link_arg<'a>(
    libraries: impl IntoIterator<Item = &'a str>,
) -> io::Result<String> {
    let mut argument = String::from("-Wl,--push-state,--no-as-needed");
    for library in libraries {
        if library.is_empty() || library.contains(',') {
            return Err(io::Error::other(format!(
                "library name cannot be passed through -Wl: {library:?}"
            )));
        }
        argument.push_str(",-l");
        argument.push_str(library);
    }
    argument.push_str(",--pop-state");
    Ok(argument)
}

fn architecture(triple: &str) -> io::Result<&str> {
    match triple.split('-').next() {
        Some(arch) if !arch.is_empty() => Ok(arch),
        _ => Err(io::Error::other(format!(
            "unsupported architecture: {triple}"
        ))),
    }
}

fn operating_system(triple: &str) -> io::Result<&str> {
    triple
        .split('-')
        .find(|part| matches!(*part, "linux" | "darwin" | "windows"))
        .ok_or_else(|| io::Error::other(format!("unsupported operating system: {triple}")))
}

/// Whether the build script's crate compiles and links its C code.
///
/// Miri interprets Rust and cannot call into C, and cargo-fuzz builds for
/// the host's glibc target with instrumentation the prepared C dependencies
/// lack, so both build the Rust code alone; the code they run never reaches
/// C. Every other build links the C its crate calls, from the dependency
/// environment xtask prepares.
pub fn links_c() -> bool {
    std::env::var_os("CARGO_CFG_MIRI").is_none() && std::env::var_os("CARGO_CFG_FUZZING").is_none()
}

#[cfg(test)]
mod tests;
