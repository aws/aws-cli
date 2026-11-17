//! Build compiler-rt's minimal UBSan runtime without host C++ dependencies.

use crate::{TaskError, deps, process};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};

const FLAGS: &[&str] = &[
    "-std=c++17",
    "-O2",
    "-fPIC",
    "-fno-exceptions",
    "-fno-rtti",
    "-nostdinc++",
    "-DSANITIZER_COMMON_NO_REDEFINE_BUILTINS=1",
    "-fvisibility=hidden",
];

pub(super) fn build(
    root: &Path,
    pins: &deps::Pins,
    tools: &deps::Toolchain,
) -> Result<PathBuf, TaskError> {
    let pin = pins
        .sources
        .get("compiler_rt_source")
        .ok_or_else(|| deps::error("compiler-rt source pin is missing"))?;
    let mut digest = Sha256::new();
    digest.update(pin.sha256.as_bytes());
    digest.update(tools.digest.as_bytes());
    digest.update(include_bytes!("runtime.rs"));
    let prefix = deps::store(root)
        .join("deps")
        .join(deps::TARGET)
        .join(format!("ubsan-minimal-{:x}", digest.finalize()));
    let archive = prefix.join("lib/libclang_rt.ubsan_minimal-musl.a");
    let _lock = deps::lock_stage(&prefix)?;
    if prefix.join(".complete").is_file() && archive.is_file() {
        return Ok(archive);
    }
    deps::guard("ubsan-minimal")?;
    let source = deps::source(root, pins, "compiler_rt_source")?;
    fs::create_dir_all(prefix.join("lib"))?;
    let object = prefix.join("ubsan_minimal_handlers.o");
    process::run(
        deps::tool_command(root, &tools.cc)?
            .args(FLAGS)
            .arg("-I")
            .arg(source.join("lib"))
            .arg("-c")
            .arg(source.join("lib/ubsan_minimal/ubsan_minimal_handlers.cpp"))
            .arg("-o")
            .arg(&object),
    )?;
    if archive.exists() {
        fs::remove_file(&archive)?;
    }
    process::run(
        deps::tool_command(root, &tools.ar)?
            .arg("rcsD")
            .arg(&archive)
            .arg(object),
    )?;
    probe(root, tools, &prefix, &archive)?;
    fs::write(
        prefix.join(".complete"),
        format!("compiler-rt {}\n", pin.sha256),
    )?;
    Ok(archive)
}

fn probe(
    root: &Path,
    tools: &deps::Toolchain,
    prefix: &Path,
    archive: &Path,
) -> Result<(), TaskError> {
    let source = prefix.join("overflow.c");
    let object = prefix.join("overflow.o");
    let binary = prefix.join("overflow");
    fs::write(
        &source,
        "#include <limits.h>\nint main(void) { volatile int x = INT_MAX; return x + 1; }\n",
    )?;
    process::run(
        deps::tool_command(root, &tools.cc)?
            .args([
                "-fsanitize=undefined",
                "-fsanitize-minimal-runtime",
                "-fno-sanitize-recover=all",
                "-c",
            ])
            .arg(source)
            .arg("-o")
            .arg(&object),
    )?;
    process::run(
        deps::tool_command(root, &tools.cc)?
            .arg(object)
            .arg(archive)
            .arg("-o")
            .arg(&binary),
    )?;
    let output = deps::tool_command(root, &binary)?.output()?;
    if output.status.success()
        || !String::from_utf8_lossy(&output.stderr).contains("ubsan: add-overflow")
    {
        return Err(deps::error(
            "native musl UBSan overflow probe did not diagnose and abort",
        ));
    }
    fs::write(prefix.join("probe-stderr.txt"), output.stderr)?;
    Ok(())
}
