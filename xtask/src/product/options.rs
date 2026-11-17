//! Validated build modes shared by build, run, and package preparation.

use crate::{TaskError, process};
use std::path::PathBuf;
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LinkMode {
    Static,
    System,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PythonLink {
    Static,
    Dynamic,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PythonPayload {
    Embedded,
    System,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Options {
    pub profile: String,
    pub python_pgo: bool,
    pub writer_debug: bool,
    pub link_mode: LinkMode,
    pub python_link: PythonLink,
    pub python_payload: PythonPayload,
    pub python_exe: PathBuf,
    pub awscrt_source: Option<PathBuf>,
    pub crt_static_prefix: Option<PathBuf>,
    pub target: String,
    pub cpu: Option<String>,
    pub strip: Option<bool>,
    pub frame_pointers: bool,
}

impl Options {
    /// The aws-cli features the options select, if any.
    pub fn features(&self) -> Option<&'static str> {
        if self.writer_debug {
            Some("download-writer-debug")
        } else {
            None
        }
    }

    pub fn cargo_profile(&self) -> &str {
        if self.profile == "dev" {
            "debug"
        } else {
            &self.profile
        }
    }
}

/// The profile a build uses unless `--profile` names another, and whose
/// artifact the CI lanes and the default harness runs consume: release with
/// debug assertions and overflow checks, optimized for size.
pub const DEFAULT_PROFILE: &str = "release-safe";

fn defaults() -> Options {
    Options {
        profile: DEFAULT_PROFILE.into(),
        python_pgo: !cfg!(windows),
        writer_debug: false,
        link_mode: LinkMode::Static,
        python_link: PythonLink::Static,
        python_payload: PythonPayload::Embedded,
        // The distro interpreter of the pinned ABI.
        python_exe: if cfg!(target_os = "linux") {
            PathBuf::from(format!("/usr/bin/{}", crate::python::PYTHON_ABI))
        } else {
            PathBuf::from("python3")
        },
        awscrt_source: None,
        crt_static_prefix: None,
        // The native target depends on the link mode, so parse resolves it.
        target: String::new(),
        cpu: None,
        strip: None,
        frame_pointers: false,
    }
}

pub fn parse(args: &[String]) -> Result<Options, TaskError> {
    let mut result = defaults();
    let mut args = args.iter();
    let mut explicit_python_link = false;
    let mut explicit_target = false;
    while let Some(argument) = args.next() {
        if argument == "--download-writer-debug" {
            result.writer_debug = true;
            continue;
        }
        let (flag, value) = if let Some(pair) = argument.split_once('=') {
            pair
        } else {
            (
                argument.as_str(),
                args.next()
                    .ok_or_else(|| error(format!("{argument} needs a value")))?
                    .as_str(),
            )
        };
        explicit_target |= flag == "--target";
        explicit_python_link |= flag == "--python-link";
        apply_option(&mut result, flag, value)?;
    }
    if !explicit_python_link && result.link_mode == LinkMode::System {
        result.python_link = PythonLink::Dynamic;
    }
    let native = default_target(result.link_mode)?;
    if !explicit_target {
        result.target.clone_from(&native);
    }
    // Only release-small strips by default. The default release-safe keeps
    // full debug info, so a backtrace names its frames and a debugger can step
    // through the shipped binary.
    if result.strip.is_none() {
        result.strip = Some(result.profile == "release-small");
    }
    validate(&result, &native)?;
    Ok(result)
}

fn apply_option(result: &mut Options, flag: &str, value: &str) -> Result<(), TaskError> {
    match flag {
        "--profile" if matches!(value, "dev" | "release" | "release-safe" | "release-small") => {
            result.profile = value.into()
        }
        "--python-pgo" => result.python_pgo = boolean(flag, value)?,
        "--download-writer-debug" => result.writer_debug = boolean(flag, value)?,
        "--strip" => result.strip = Some(boolean(flag, value)?),
        "--frame-pointers" => result.frame_pointers = boolean(flag, value)?,
        "--cpu"
            if !value.is_empty()
                && value
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || b"_-.".contains(&byte)) =>
        {
            result.cpu = Some(value.into())
        }
        "--target" => {
            result.target = value.into();
        }
        "--link-mode" => {
            result.link_mode = match value {
                "static" => LinkMode::Static,
                "system" => LinkMode::System,
                _ => return Err(error("--link-mode requires static or system")),
            }
        }
        "--python-link" => {
            result.python_link = match value {
                "static" => PythonLink::Static,
                "dynamic" => PythonLink::Dynamic,
                _ => return Err(error("--python-link requires static or dynamic")),
            };
        }
        "--python-payload" => {
            result.python_payload = match value {
                "embedded" => PythonPayload::Embedded,
                "system" => PythonPayload::System,
                _ => return Err(error("--python-payload requires embedded or system")),
            }
        }
        "--python-exe" => result.python_exe = PathBuf::from(value),
        "--awscrt-source" => result.awscrt_source = Some(PathBuf::from(value)),
        "--crt-static-prefix" => result.crt_static_prefix = Some(PathBuf::from(value)),
        _ => return Err(error(format!("invalid build option: {flag}={value}"))),
    }
    Ok(())
}

fn error(message: impl Into<String>) -> TaskError {
    TaskError::Message(message.into())
}
fn boolean(flag: &str, value: &str) -> Result<bool, TaskError> {
    match value {
        "true" => Ok(true),
        "false" => Ok(false),
        _ => Err(error(format!("{flag} requires true or false"))),
    }
}

/// The native target for a link mode.
///
/// Static builds keep the pinned x86_64/aarch64 host policy. System builds
/// take `system_target`: a native Linux/glibc host, restricted to the
/// 64-bit little-endian architectures `build_support::SYSTEM_ARCHITECTURES`
/// lists.
fn default_target(mode: LinkMode) -> Result<String, TaskError> {
    match mode {
        LinkMode::Static => {
            crate::deps::native_host()?;
            crate::deps::native_target(false)
        }
        LinkMode::System => system_target(),
    }
}

/// The glibc triple of the native rustc, whose host line already spells the
/// architecture as rustc does (`riscv64gc`, `powerpc64le`, ...).
///
/// This is the system-mode host check: every system-mode command (`build`,
/// `deps system-crt`, `package check`) takes it in place of the static host
/// gate.
pub(crate) fn system_target() -> Result<String, TaskError> {
    if !cfg!(target_os = "linux") {
        return Err(error("unsupported native host/build mode"));
    }
    let version = process::output(Command::new("rustc").arg("-vV"))?;
    system_target_from(&String::from_utf8_lossy(&version.stdout))
}

/// Map `rustc -vV` output to `<arch>-unknown-linux-gnu` for a Linux/glibc
/// host; other ABIs (musl, `gnueabihf`, ...) are refused. A 32-bit or
/// big-endian architecture is refused too, as the build scripts'
/// `NativeTarget` refuses it.
pub(super) fn system_target_from(rustc_version: &str) -> Result<String, TaskError> {
    let host = rustc_version
        .lines()
        .find_map(|line| line.strip_prefix("host: "))
        .ok_or_else(|| error("rustc -vV did not report its host triple"))?
        .trim();
    match host.split('-').collect::<Vec<_>>().as_slice() {
        [arch, _, "linux", "gnu"] if !arch.is_empty() => {
            let target = format!("{arch}-unknown-linux-gnu");
            build_support::require_system_architecture(&target)?;
            Ok(target)
        }
        _ => Err(error(format!(
            "system linking requires a native Linux/glibc host; rustc reports {host}"
        ))),
    }
}

fn validate(options: &Options, native: &str) -> Result<(), TaskError> {
    if options.target != native {
        return Err(error(format!(
            "target {} is not the native {:?} ABI; cross compilation is forbidden",
            options.target, options.link_mode
        )));
    }
    if options.link_mode == LinkMode::Static
        && (options.python_link != PythonLink::Static
            || options.python_payload != PythonPayload::Embedded)
    {
        return Err(error(
            "static linking requires static Python and the embedded payload",
        ));
    }
    if options.link_mode == LinkMode::System
        && (options.python_link != PythonLink::Dynamic || !cfg!(target_os = "linux"))
    {
        return Err(error(
            "system linking requires dynamic Python on native Linux/glibc",
        ));
    }
    if options.crt_static_prefix.is_some() && options.link_mode != LinkMode::System {
        return Err(error("--crt-static-prefix requires --link-mode=system"));
    }
    if options.awscrt_source.is_some()
        && (options.link_mode != LinkMode::System
            || options.python_payload != PythonPayload::Embedded)
    {
        return Err(error(
            "--awscrt-source requires system linking and the embedded payload",
        ));
    }
    if cfg!(windows) && options.python_pgo {
        return Err(error("CPython PGO is unsupported on Windows"));
    }
    Ok(())
}
