//! Standalone consumers of the prepared native dependency interfaces.

use crate::deps::{self, Pins, Toolchain};
use crate::python::{self, ProfileTools};
use crate::{TaskError, process};
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

mod options;
mod platform;
use options::Options;

/// The interpreter's static support archives, in the order
/// `build_python_deps.py` installs them.
const SUPPORT_LIBRARIES: &[&str] = &["sqlite3", "bz2", "ffi", "zstd"];

/// The define only the fallback's generated glue compiles with; every other
/// consumer embeds the public headers.
const BUILD_CORE_BUILTIN: &str = "-DPy_BUILD_CORE_BUILTIN=1";

/// Every consumer is optimized for size, with the sections the linker's
/// garbage collection removes.
const OPTIMIZE: &[&str] = &["-Os", "-ffunction-sections", "-fdata-sections"];

pub(super) fn run(root: &Path, args: &[String]) -> Result<(), TaskError> {
    deps::native_host()?;
    let options = Options::parse(root, args)?;
    let pins = Pins::load(root)?;
    deps::check_pins(root, &pins)?;
    let tools = deps::toolchain(root, &pins)?;
    // A prepared CRT prefix also supplies the OpenSSL, zlib, and xz CPython
    // links, as the consumers link them from it, and so keys the interpreter
    // stage apart from the product's.
    let (crt, libraries) = match &options.crt {
        Some(prefix) => (prefix.clone(), deps::CpythonLibraries::prepared(prefix)),
        None => (
            deps::crt(root, &pins, &tools)?,
            deps::CpythonLibraries::managed(root, &tools)?,
        ),
    };
    let crt_archives = deps::crt_archives(root, &crt)?;
    let pgo_tools = pgo_tools(root, &pins, &tools, &options)?;
    // A prepared PGO prefix also drives the CPython PGO build; the managed
    // tools leave the interpreter stage keyed as the product's.
    let cpython_tools = pgo_tools.as_ref().filter(|_| options.profile.is_some());
    let python = prepare_python(
        root,
        &pins,
        &tools,
        &crt,
        &libraries,
        &options,
        cpython_tools,
    )?;
    let output = root.join("target/package-consumers").join(deps::TARGET);
    let _lock = deps::lock_stage(&output)?;
    fs::create_dir_all(&output)?;
    let roots = serde_json::json!({
        "crt": crt, "cpython": python.cpython, "fallback": python.fallback,
        "toolchain": tools.prefix, "llvm_profdata": tools.llvm_profdata,
    });
    fs::write(
        output.join("roots.json"),
        serde_json::to_vec_pretty(&roots).map_err(|failure| deps::error(failure.to_string()))?,
    )?;
    let inputs = Inputs {
        root,
        crt: &crt,
        crt_archives: &crt_archives,
        python: &python,
        output: &output,
    };
    let crt_binary = compile(&inputs, &tools, &crt_consumer(&inputs))?;
    process::run(&mut Command::new(crt_binary))?;
    interpreter(&inputs, &tools)?;
    if let Some(pgo_tools) = &pgo_tools {
        profile(&inputs, &tools, pgo_tools)?;
    }
    fallback(&inputs, &tools)?;
    fs::write(
        output.join("passed.txt"),
        if cfg!(target_os = "linux") {
            "crt\ncpython\npgo\nfallback\n"
        } else {
            "crt\ncpython\nfallback\n"
        },
    )?;
    Ok(())
}

/// The Linux PGO tools, resolved before CPython: a prepared `--pgo-prefix`,
/// else the managed merger and profile runtime. Other hosts have no PGO
/// consumer.
fn pgo_tools(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    options: &Options,
) -> Result<Option<ProfileTools>, TaskError> {
    if !cfg!(target_os = "linux") {
        return Ok(None);
    }
    match &options.profile {
        Some(prefix) => prefix_tools(prefix).map(Some),
        None => ProfileTools::managed(root, pins, tools).map(Some),
    }
}

/// A prepared PGO prefix's tools; the runtime keeps compiler-rt's musl name.
fn prefix_tools(prefix: &Path) -> Result<ProfileTools, TaskError> {
    let profile_runtime = Some(prefix.join("lib/libclang_rt.profile-musl.a"))
        .filter(|path| path.is_file())
        .ok_or_else(|| deps::error("prepared PGO prefix has no profile runtime"))?;
    Ok(ProfileTools {
        llvm_profdata: prefix.join("bin/llvm-profdata"),
        profile_runtime,
    })
}

/// The interpreter and fallback the consumers read: the prepared prefixes
/// `options` names, else stages built against the CRT at `crt`, whose
/// headers the fallback compiles awscrt with, and the `libraries` CPython
/// links.
fn prepare_python(
    root: &Path,
    pins: &Pins,
    tools: &Toolchain,
    crt: &Path,
    libraries: &deps::CpythonLibraries,
    options: &Options,
    profile_tools: Option<&ProfileTools>,
) -> Result<python::PythonOutputs, TaskError> {
    let cpython = match &options.cpython {
        Some(prefix) => prefix.clone(),
        None => python::interpreter(root, pins, tools, libraries, options.pgo, profile_tools)?,
    };
    let fallback = match &options.fallback {
        Some(prefix) => prefix.clone(),
        None => python::fallback(
            root,
            pins,
            tools,
            &python::FallbackInputs {
                crt,
                cpython: &cpython,
                runtime_source: &root.join("tests/packages/runtime.txt"),
                pgo: options.pgo,
            },
        )?,
    };
    Ok(python::PythonOutputs { cpython, fallback })
}

/// The prepared prefixes every consumer reads and the directory it writes.
struct Inputs<'a> {
    root: &'a Path,
    crt: &'a Path,
    /// The CRT prefix's archives for this host, from deps/crt-libraries.txt.
    crt_archives: &'a [PathBuf],
    python: &'a python::PythonOutputs,
    output: &'a Path,
}

/// A C source and the defines only it compiles with.
#[derive(Debug)]
struct Source {
    path: PathBuf,
    defines: &'static [&'static str],
}

/// One consumer executable with only its own inputs: libc, then the package
/// interfaces it attaches.
#[derive(Debug)]
struct Consumer {
    name: &'static str,
    includes: Vec<PathBuf>,
    sources: Vec<Source>,
    archives: Vec<PathBuf>,
}

impl Consumer {
    /// A retained fixture linked with libc only.
    fn new(inputs: &Inputs<'_>, name: &'static str) -> Self {
        Self {
            name,
            includes: Vec::new(),
            sources: vec![Source {
                path: inputs.root.join(format!("tests/packages/{name}.c")),
                defines: &[],
            }],
            archives: Vec::new(),
        }
    }

    /// Attach CRT headers and archives.
    fn with_crt(mut self, inputs: &Inputs<'_>) -> Self {
        self.includes.push(inputs.crt.join("include"));
        self.archives.extend_from_slice(inputs.crt_archives);
        self
    }

    /// Attach CPython's public headers.
    fn with_cpython_headers(mut self, inputs: &Inputs<'_>) -> Self {
        self.includes.push(
            inputs
                .python
                .cpython
                .join("include")
                .join(python::PYTHON_ABI),
        );
        self
    }

    /// The executable, named `{name}-consumer`.
    fn binary(&self, output: &Path) -> PathBuf {
        output.join(format!(
            "{}-consumer{}",
            self.name,
            std::env::consts::EXE_SUFFIX
        ))
    }

    /// Optimization and include arguments shared by every compilation.
    fn compile_arguments(&self) -> Vec<OsString> {
        let mut arguments: Vec<OsString> = OPTIMIZE.iter().map(OsString::from).collect();
        for include in &self.includes {
            arguments.push("-I".into());
            arguments.push(include.into());
        }
        arguments
    }

    /// The object a source with its own defines compiles to, and its arguments.
    fn object(&self, source: &Source, output: &Path) -> (PathBuf, Vec<OsString>) {
        let stem = source
            .path
            .file_stem()
            .unwrap_or_default()
            .to_string_lossy();
        let object = output.join(format!("{}-consumer-{stem}.o", self.name));
        let mut arguments = self.compile_arguments();
        arguments.extend(source.defines.iter().map(OsString::from));
        arguments.extend(["-c".into(), source.path.clone().into_os_string()]);
        arguments.extend(["-o".into(), object.clone().into_os_string()]);
        (object, arguments)
    }
}

/// Compile a consumer's separately defined sources to objects, then link
/// them with its other sources and archives.
fn compile(
    inputs: &Inputs<'_>,
    tools: &Toolchain,
    consumer: &Consumer,
) -> Result<PathBuf, TaskError> {
    let mut command = tools.command(inputs.root, &tools.cc)?;
    platform::compile_flags(&mut command);
    platform::link_flags(&mut command);
    command.args(consumer.compile_arguments());
    for source in &consumer.sources {
        if source.defines.is_empty() {
            command.arg(&source.path);
            continue;
        }
        let (object, arguments) = consumer.object(source, inputs.output);
        let mut compile = tools.command(inputs.root, &tools.cc)?;
        platform::compile_flags(&mut compile);
        process::run(compile.args(arguments))?;
        command.arg(object);
    }
    platform::archives_begin(&mut command);
    command.args(&consumer.archives);
    platform::archives_end(&mut command);
    let binary = consumer.binary(inputs.output);
    command.arg("-o").arg(&binary);
    process::run(&mut command)?;
    Ok(binary)
}

/// The CRT consumer: CRT headers and archives only.
fn crt_consumer(inputs: &Inputs<'_>) -> Consumer {
    Consumer::new(inputs, "crt").with_crt(inputs)
}

/// The interpreter's support archives beside libpython.
fn support_archives(inputs: &Inputs<'_>) -> impl Iterator<Item = PathBuf> {
    let directory = inputs.python.cpython.join("lib");
    SUPPORT_LIBRARIES
        .iter()
        .map(move |name| directory.join(platform::archive(name)))
}

/// The embedding consumer: CPython's headers, extension table, archive and
/// support libraries, then the CRT.
fn cpython_consumer(inputs: &Inputs<'_>) -> Consumer {
    let directory = inputs.python.cpython.join("lib");
    let mut consumer = Consumer::new(inputs, "cpython").with_cpython_headers(inputs);
    consumer.sources.push(Source {
        path: directory.join(format!("{}-inittab.c", python::PYTHON_ABI)),
        defines: &[],
    });
    // CPython exports this archive name on every host; only its support
    // libraries and CRT libraries use native MSVC .lib aliases.
    consumer
        .archives
        .push(directory.join(format!("lib{}.a", python::PYTHON_ABI)));
    consumer.archives.extend(support_archives(inputs));
    consumer.with_crt(inputs)
}

/// The profile-runtime consumer: libc and the runtime archive only.
fn pgo_consumer(inputs: &Inputs<'_>, pgo_tools: &ProfileTools) -> Consumer {
    let mut consumer = Consumer::new(inputs, "pgo");
    consumer.archives.push(pgo_tools.profile_runtime.clone());
    consumer
}

/// The fallback consumer: CPython's headers, the generated glue built with
/// Py_BUILD_CORE_BUILTIN, the combined archive, support libraries and CRT.
fn fallback_consumer(inputs: &Inputs<'_>) -> Consumer {
    let prefix = &inputs.python.fallback;
    let mut consumer = Consumer::new(inputs, "fallback").with_cpython_headers(inputs);
    for name in ["inittab.c", "frozen_bootstrap.c"] {
        consumer.sources.push(Source {
            path: prefix.join(name),
            defines: &[BUILD_CORE_BUILTIN],
        });
    }
    consumer.archives.push(prefix.join("python-fallback.a"));
    consumer.archives.extend(support_archives(inputs));
    consumer.with_crt(inputs)
}

fn interpreter(inputs: &Inputs<'_>, tools: &Toolchain) -> Result<(), TaskError> {
    let prefix = &inputs.python.cpython;
    let binary = compile(inputs, tools, &cpython_consumer(inputs))?;
    process::run(Command::new(binary).arg(prefix))?;
    process::run(Command::new(platform::interpreter(prefix)).args([
        "-I",
        "-c",
        "import _ssl, zlib, _lzma, _sqlite3, _bz2, _ctypes, _zstd",
    ]))
}

fn profile(
    inputs: &Inputs<'_>,
    tools: &Toolchain,
    pgo_tools: &ProfileTools,
) -> Result<(), TaskError> {
    process::run(Command::new(&pgo_tools.llvm_profdata).arg("--version"))?;
    let binary = compile(inputs, tools, &pgo_consumer(inputs, pgo_tools))?;
    process::run(&mut Command::new(binary))
}

fn fallback(inputs: &Inputs<'_>, tools: &Toolchain) -> Result<(), TaskError> {
    let prefix = &inputs.python.fallback;
    let config = fs::read_to_string(prefix.join("python_config.rs"))?;
    if !config.contains("pub const DYNAMIC: bool = false;")
        || !config.contains("pub const EMBEDDED_PAYLOAD: bool = true;")
    {
        return Err(deps::error(
            "fallback consumer requires static embedded configuration",
        ));
    }
    let magic = config
        .lines()
        .find_map(|line| line.strip_prefix("pub const BYTECODE_MAGIC: u32 = "))
        .and_then(|value| value.trim_end_matches(';').parse::<u32>().ok())
        .filter(|value| *value != 0)
        .ok_or_else(|| deps::error("generated fallback bytecode magic is missing or zero"))?;
    process::run(
        Command::new(platform::interpreter(&inputs.python.cpython))
            .arg("-I")
            .arg(
                inputs
                    .root
                    .join("deps/scripts/validate_bytecode_metadata.py"),
            )
            .arg("--payload")
            .arg(prefix.join("awscli-v2.blob"))
            .arg("--runtime")
            .arg(prefix.join("runtime.pyc"))
            .arg("--metadata")
            .arg(prefix.join("python-bytecode-metadata.json"))
            .args(["--expected-magic", &magic.to_string()])
            .arg("--stamp")
            .arg(inputs.output.join("fallback-bytecode.stamp")),
    )?;
    let binary = compile(inputs, tools, &fallback_consumer(inputs))?;
    process::run(&mut Command::new(binary))
}

#[cfg(test)]
mod tests;
