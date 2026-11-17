//! The CMake builds of the zlib/xz and CRT stages' projects.
//!
//! Each project configures with the managed compilers, wrapped with its
//! source maps, and installs into its stage's prefix, where a marker records
//! the install so an interrupted stage build resumes after it. What a project
//! needs beyond that, such as its own configure arguments or a patched
//! source, its stage supplies.

use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use super::super::toolchain::jobs;
use super::super::{Result, Toolchain, write_executable};
use super::source_paths;
use crate::process;

/// Where a stage's projects install, and the scratch directory they build in.
#[derive(Clone, Copy, Debug)]
pub(super) struct Build<'a> {
    pub(super) prefix: &'a Path,
    pub(super) work: &'a Path,
}

/// One CMake project of a stage.
#[derive(Clone, Copy, Debug)]
pub(super) struct Project<'a> {
    /// The stable upstream name, such as `aws-c-common`, which names the
    /// project's build tree, compiler wrapper, and installed marker.
    pub(super) name: &'a str,
    /// The source tree, which may be a patched copy in the scratch directory.
    pub(super) source: &'a Path,
    /// The target to build: `install`, unless the stage installs by hand.
    pub(super) target: &'a str,
}

impl Build<'_> {
    /// Configure `project` with its own `arguments` after the shared ones,
    /// build its target, and return its build tree.
    pub(super) fn run(
        &self,
        root: &Path,
        tools: &Toolchain,
        project: &Project<'_>,
        arguments: &[impl AsRef<OsStr>],
    ) -> Result<PathBuf> {
        let build = self.work.join("cmake").join(project.name);
        let mut configure = cmake_command(root, tools, self.prefix)?;
        configure_compiler(&mut configure, tools, self, project, &build)?;
        configure
            .arg("-S")
            .arg(project.source)
            .arg("-B")
            .arg(&build)
            .args(arguments);
        process::run(&mut configure)?;
        process::run(
            tools
                .command(root, "cmake")?
                .arg("--build")
                .arg(&build)
                .arg("--target")
                .arg(project.target)
                .arg("--")
                .arg(format!("-j{}", jobs()?)),
        )?;
        Ok(build)
    }
}

/// The directory of a prefix that holds its projects' installed markers.
pub(super) const MARKERS: &str = ".projects";

/// The marker that `name` is installed in `prefix`. It lives in the prefix,
/// not the shared work directory, so it is never read for another key's
/// prefix, and a removed prefix takes its markers with it.
pub(in crate::deps) fn installed_marker(prefix: &Path, name: &str) -> PathBuf {
    prefix.join(MARKERS).join(format!("{name}.complete"))
}

/// Record that `name` is installed in `prefix`.
pub(in crate::deps) fn mark_installed(prefix: &Path, name: &str) -> Result<()> {
    let marker = installed_marker(prefix, name);
    if let Some(parent) = marker.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(marker, "ok\n")?;
    Ok(())
}

/// Spell a path the way CMake reads it back.
/// CMake stores some cache values inside generated CMake code, where a
/// Windows path's backslashes are invalid string escapes; forward slashes
/// are accepted on every platform. A POSIX file name may contain a
/// backslash, so there the path is kept as it is.
fn cmake_path(path: &Path) -> String {
    let path = path.display().to_string();
    if cfg!(windows) {
        path.replace('\\', "/")
    } else {
        path
    }
}

fn cmake_command(root: &Path, tools: &Toolchain, prefix: &Path) -> Result<Command> {
    let ninja = tools.ninja()?;
    let mut configure = tools.command(root, "cmake")?;
    tools.apply_build_tools(&mut configure);
    configure
        .args([
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_TESTING=OFF",
            "-DCMAKE_FIND_USE_PACKAGE_REGISTRY=FALSE",
            "-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=FALSE",
            "-DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON",
            // Without this, every PATH entry seeds find_* with a prefix, so a
            // Homebrew or version-manager tree could supply headers and libraries.
            "-DCMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH=FALSE",
        ])
        .arg(format!("-DCMAKE_MAKE_PROGRAM={}", cmake_path(&ninja)))
        .arg(format!("-DCMAKE_INSTALL_PREFIX={}", cmake_path(prefix)))
        .arg(format!("-DCMAKE_PREFIX_PATH={}", cmake_path(prefix)))
        .arg(format!("-DCMAKE_AR={}", cmake_path(&tools.ar)))
        .arg(format!("-DCMAKE_RANLIB={}", cmake_path(&tools.ranlib)));
    if let Some((msvc, _)) = &tools.msvc {
        // Clang's GNU-style Windows driver needs a resource compiler, which
        // CMake would only look for on the PATH this configuration keeps
        // from it, so it is the selected LLVM's.
        let rc = msvc.find_tool("llvm-rc")?;
        configure
            .arg(format!("-DCMAKE_RC_COMPILER={}", cmake_path(&rc)))
            .arg("-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded");
    }
    if let Some(sdk) = &tools.sdk {
        configure.arg(format!("-DCMAKE_OSX_SYSROOT={}", sdk.display()));
        configure.arg(format!(
            "-DCMAKE_OSX_DEPLOYMENT_TARGET={}",
            if cfg!(target_arch = "aarch64") {
                "11.0"
            } else {
                "10.15"
            }
        ));
    }
    Ok(configure)
}

/// Point CMake at a compiler that carries this project's source maps.
///
/// POSIX wrappers keep the maps out of project flags a build can replace.
/// Windows passes them as the initial compiler flags instead.
fn configure_compiler(
    configure: &mut Command,
    tools: &Toolchain,
    stage: &Build<'_>,
    project: &Project<'_>,
    build: &Path,
) -> Result<()> {
    let maps = &source_paths::flags(&source_paths::Roots {
        name: project.name,
        source: project.source,
        build,
        work: stage.work,
        install: stage.prefix,
    })?;
    if cfg!(windows) {
        let flags = format!(
            "-fms-runtime-lib=static {}",
            source_paths::windows_flags(maps)
        );
        configure
            .arg(format!("-DCMAKE_C_COMPILER={}", cmake_path(&tools.cc)))
            .arg(format!("-DCMAKE_CXX_COMPILER={}", cmake_path(&tools.cc)))
            .arg(format!("-DCMAKE_C_FLAGS={flags}"))
            .arg(format!("-DCMAKE_CXX_FLAGS={flags}"));
        return Ok(());
    }
    let wrapper = stage.work.join("compilers").join(project.name).join("cc");
    write_executable(&wrapper, &source_paths::wrapper(&tools.cc, maps)?)?;
    configure
        .arg(format!("-DCMAKE_C_COMPILER={}", wrapper.display()))
        .arg(format!("-DCMAKE_CXX_COMPILER={}", wrapper.display()));
    Ok(())
}

#[cfg(test)]
mod tests;
