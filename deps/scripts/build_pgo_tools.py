#!/usr/bin/env python3
"""Build the musl profile runtime from pinned compiler-rt sources.

The matching LLVM release supplies llvm-profdata. This script builds only
its target runtime, without a C++ library dependency.
"""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from build_environ import tool_environ
from build_guard import guard
from native_target import require_native_target

# Escape hatch for PGO-tools changes their stamps cannot see; the stamps
# already cover the sources, the compiler version, and the full flag lists.
LLVM_PGO_TOOLS_REVISION = "2"


def run(args: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    try:
        subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as err:
        if err.stdout:
            sys.stdout.buffer.write(err.stdout)
        if err.stderr:
            sys.stderr.buffer.write(err.stderr)
        raise


def command_output(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as err:
        if err.stdout:
            sys.stdout.buffer.write(err.stdout)
        if err.stderr:
            sys.stderr.buffer.write(err.stderr)
        raise
    return result.stdout.decode("utf-8").strip()


def compiler_identity(cc: str, env: dict[str, str]) -> str:
    return command_output([cc, "--version"], cwd=Path.cwd(), env=env)


def is_linux_musl_target(target_triple: str) -> bool:
    return target_triple.startswith(
        (
            "x86_64-linux",
            "x86_64-unknown-linux",
            "aarch64-linux",
            "aarch64-unknown-linux",
        )
    ) and target_triple.endswith("-musl")


def source_identity(source_dir: Path) -> str:
    return str(source_dir.resolve())


def profile_runtime_sources(source_dir: Path) -> list[Path]:
    profile_dir = source_dir / "lib" / "profile"
    names = [
        "GCDAProfiling.c",
        "InstrProfiling.c",
        "InstrProfilingInternal.c",
        "InstrProfilingValue.c",
        "InstrProfilingBuffer.c",
        "InstrProfilingFile.c",
        "InstrProfilingMerge.c",
        "InstrProfilingMergeFile.c",
        "InstrProfilingNameVar.c",
        "InstrProfilingVersionVar.c",
        "InstrProfilingWriter.c",
        "InstrProfilingPlatformAIX.c",
        "InstrProfilingPlatformDarwin.c",
        "InstrProfilingPlatformFuchsia.c",
        "InstrProfilingPlatformLinux.c",
        "InstrProfilingPlatformOther.c",
        "InstrProfilingPlatformWindows.c",
        "InstrProfilingUtil.c",
    ]
    return [profile_dir / name for name in names]


def profile_runtime_flags(
    source_dir: Path,
    target_triple: str,
) -> list[str]:
    return [
        "-O2",
        f"-I{source_dir / 'lib'}",
        f"-I{source_dir / 'include'}",
        f"-I{source_dir / 'lib' / 'profile'}",
        "-fPIC",
        "-Wno-pedantic",
        "-DCOMPILER_RT_HAS_ATOMICS=1",
        "-DCOMPILER_RT_HAS_FCNTL_LCK=1",
        "-DCOMPILER_RT_HAS_FLOCK=1",
        "-DCOMPILER_RT_HAS_UNAME=1",
    ]


# Extra flags for InstrProfilingRuntime.cpp; the static musl link provides
# no C++ runtime for it to use.
PROFILE_RUNTIME_CXX_FLAGS = [
    "-fno-exceptions",
    "-fno-rtti",
    "-nostdinc++",
]


def build_profile_runtime(
    cc: str,
    ar: str,
    ranlib: str,
    target_triple: str,
    source_dir: Path,
    cache_dir: Path,
    env: dict[str, str],
) -> Path:
    source_dir = source_dir.resolve()
    build_dir = cache_dir / "profile-runtime"
    archive = build_dir / "libclang_rt.profile-musl.a"
    stamp = build_dir / ".profile-runtime-version"
    flags = profile_runtime_flags(source_dir, target_triple)
    sources = profile_runtime_sources(source_dir)
    # The stamp embeds every compile input so a flag or source-list edit
    # rebuilds the archive without a manual revision bump.
    expected_stamp = (
        f"{source_identity(source_dir)}\n"
        f"{LLVM_PGO_TOOLS_REVISION}\n"
        f"{target_triple}\n"
        f"{compiler_identity(cc, env)}\n"
        f"{shlex.join(flags)}\n"
        f"{shlex.join(PROFILE_RUNTIME_CXX_FLAGS)}\n"
        f"{shlex.join(source.name for source in sources)}\n"
    )
    if archive.exists() and stamp.exists() and stamp.read_text() == expected_stamp:
        return archive

    guard("linux-pgo-tools")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    object_dir = build_dir / "obj"
    object_dir.mkdir(parents=True)

    objects: list[Path] = []
    for source in sources:
        obj = object_dir / f"{source.stem}.o"
        run(
            [cc, *flags, "-c", str(source), "-o", str(obj)],
            cwd=build_dir,
            env=env,
        )
        objects.append(obj)

    cxx_source = source_dir / "lib" / "profile" / "InstrProfilingRuntime.cpp"
    cxx_obj = object_dir / "InstrProfilingRuntime.o"
    run(
        [
            cc,
            "-x",
            "c++",
            *flags,
            *PROFILE_RUNTIME_CXX_FLAGS,
            "-c",
            str(cxx_source),
            "-o",
            str(cxx_obj),
        ],
        cwd=build_dir,
        env=env,
    )
    objects.append(cxx_obj)

    run(
        [ar, "rcs", str(archive), *[str(obj) for obj in objects]],
        cwd=build_dir,
        env=env,
    )
    run([ranlib, str(archive)], cwd=build_dir, env=env)
    stamp.write_text(expected_stamp)
    return archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for tool in ("cc", "ar", "ranlib", "llvm-profdata"):
        parser.add_argument(f"--{tool}", required=True)
    parser.add_argument("--llvm-version", required=True)
    parser.add_argument("--target-triple", required=True)
    parser.add_argument("--compiler-rt-source", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--profile-runtime-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_native_target(args.target_triple)
    if not is_linux_musl_target(args.target_triple):
        raise SystemExit("the profile runtime requires native Linux musl")
    env = tool_environ()
    merger_version = command_output(
        [args.llvm_profdata, "--version"], cwd=Path.cwd(), env=env
    )
    compiler_version = compiler_identity(args.cc, env)
    expected = args.llvm_version
    if re.fullmatch(r"21\.[0-9]+\.[0-9]+", expected) is None:
        raise SystemExit(f"the profile runtime requires LLVM 21: {expected}")
    version_pattern = rf"\bversion\s+{re.escape(expected)}\b"
    for name, found in (
        ("profile merger", merger_version),
        ("compiler", compiler_version),
    ):
        if re.search(version_pattern, found) is None:
            raise SystemExit(f"{name} must be LLVM {expected}: {found}")
    runtime = build_profile_runtime(
        args.cc,
        args.ar,
        args.ranlib,
        args.target_triple,
        args.compiler_rt_source,
        args.cache_dir,
        env,
    )
    args.profile_runtime_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runtime, args.profile_runtime_output)


if __name__ == "__main__":
    main()
