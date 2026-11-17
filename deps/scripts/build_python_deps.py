#!/usr/bin/env python3
"""Build static sqlite3, bzip2, libffi, and zstd for the AWS CLI binary.

The embedded interpreter links these project-built static archives.
Linux uses the pinned clang wrappers; macOS uses native Apple tools.

sqlite is compiled directly from the amalgamation (sqlite3.c), bzip2 from its
seven library sources, and zstd with its upstream static-library Make target.
libffi needs its autoconf build for the per-architecture assembly and
generated headers.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from build_environ import tool_environ
from build_guard import guard
from native_target import require_native_target

# Bump to force a rebuild when the build flags below change.
BUILD_CONFIG_REVISION = "8"

# Feature defines for the sqlite amalgamation. CPython's _sqlite3 only hard
# requires the defaults; the ENABLE flags match what common sqlite
# distributions compile in.
SQLITE_CFLAGS = [
    "-DSQLITE_ENABLE_COLUMN_METADATA",
    "-DSQLITE_ENABLE_DBSTAT_VTAB",
    "-DSQLITE_ENABLE_FTS3",
    "-DSQLITE_ENABLE_FTS3_PARENTHESIS",
    "-DSQLITE_ENABLE_FTS4",
    "-DSQLITE_ENABLE_FTS5",
    "-DSQLITE_ENABLE_MATH_FUNCTIONS",
    "-DSQLITE_ENABLE_RTREE",
    "-DSQLITE_THREADSAFE=1",
]

# The seven sources that make up libbz2.a, per bzip2's Makefile.
BZIP2_SOURCES = [
    "blocksort.c",
    "huffman.c",
    "crctable.c",
    "randtable.c",
    "compress.c",
    "decompress.c",
    "bzlib.c",
]


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


def copy_source_tree(source_dir: Path, work_dir: Path) -> Path:
    destination = work_dir / "source"
    if destination.exists():
        shutil.rmtree(destination)
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, destination, symlinks=True)
    return destination


def deployment_target(target_triple: str) -> str:
    if target_triple.startswith("aarch64-macos"):
        return "11.0"
    if target_triple.startswith("x86_64-macos"):
        return "10.15"
    raise SystemExit(f"unsupported python deps build target: {target_triple}")


def is_linux_musl_target(target_triple: str) -> bool:
    return target_triple.startswith(
        (
            "x86_64-linux",
            "x86_64-unknown-linux",
            "aarch64-linux",
            "aarch64-unknown-linux",
        )
    ) and target_triple.endswith("-musl")


def is_macos_target(target_triple: str) -> bool:
    return target_triple.startswith(("aarch64-macos", "x86_64-macos"))


def require_supported_target(target_triple: str) -> None:
    require_native_target(target_triple)
    if (
        is_linux_musl_target(target_triple)
        or is_macos_target(target_triple)
        or target_triple in ("x86_64-windows-msvc", "x86_64-pc-windows-msvc")
    ):
        return
    raise SystemExit(f"unsupported python deps build target: {target_triple}")


def apple_tool(name: str, env: dict[str, str]) -> str:
    """The absolute path to `name` in the active Apple developer directory.

    xcrun resolves against DEVELOPER_DIR (allowlisted) or whatever
    xcode-select points at, and only falls back to PATH when the developer
    directory does not ship the tool. The reduced PATH keeps that fallback
    inside the Apple toolchain instead of the caller's shell.
    """
    path = command_output(
        ["/usr/bin/xcrun", "-f", name],
        cwd=Path.cwd(),
        env=env | {"PATH": "/usr/bin:/bin"},
    )
    if not Path(path).is_absolute() or not os.access(path, os.X_OK):
        raise SystemExit(
            f"xcrun did not resolve {name} to an executable: {path!r}"
        )
    return path


def toolchain_env(
    cc: str,
    ar: str,
    ranlib: str,
    target_triple: str,
    sdk_path: str | None,
    msvc_environ: Path | None = None,
) -> dict[str, str]:
    """Allowlisted environment with explicit compiler and archivers."""
    require_supported_target(target_triple)
    env = tool_environ(msvc_environ=msvc_environ)
    env.update({"CC": cc, "AR": ar, "RANLIB": ranlib})
    if target_triple in ("x86_64-windows-msvc", "x86_64-pc-windows-msvc"):
        env["CC"] = (
            f"{shlex.quote(cc)} --driver-mode=gcc -fms-runtime-lib=static"
        )
        # `tool_command` splits each tool as shell words, and a Windows
        # tool path holds spaces and backslashes.
        env["AR"] = shlex.quote(ar)
        env["RANLIB"] = shlex.quote(ranlib)
    if is_macos_target(target_triple):
        env["MACOSX_DEPLOYMENT_TARGET"] = deployment_target(target_triple)
        if sdk_path is not None:
            env["SDKROOT"] = sdk_path
    env["ZERO_AR_DATE"] = "1"
    return env


LIBFFI_WINDOWS_TARGET = "X86_WIN64"

LIBFFI_COMMON_SOURCES = [
    "src/prep_cif.c",
    "src/types.c",
    "src/raw_api.c",
    "src/java_raw_api.c",
    "src/closures.c",
    "src/tramp.c",
]

LIBFFI_WINDOWS_SOURCES = ["src/x86/ffiw64.c", "src/x86/win64.S"]

# fficonfig.h values for x86-64 Windows with a Clang-compatible compiler.
# Everything left as `#undef` in the template stays undefined: there is no
# alloca.h, unistd.h, strings.h, or dlfcn.h in the Microsoft C runtime, PE
# objects have no ELF visibility attribute, and closures.c configures its own
# executable-memory strategy from `_WIN32`.
#
# HAVE_AS_CFI_PSEUDO_OP stays undefined on purpose. Windows unwinds through
# SEH tables rather than DWARF, so the .cfi directives in win64.S would only
# add a .debug_frame section, whose name is longer than COFF allows and whose
# linker warning fails the build.
LIBFFI_WINDOWS_DEFINES = {
    "EH_FRAME_FLAGS": '"aw"',
    "HAVE_MEMCPY": "1",
    "HAVE_STDINT_H": "1",
    "HAVE_STDIO_H": "1",
    "HAVE_STDLIB_H": "1",
    "HAVE_STRING_H": "1",
    "HAVE_SYS_STAT_H": "1",
    "HAVE_SYS_TYPES_H": "1",
    "PACKAGE": '"libffi"',
    "PACKAGE_NAME": '"libffi"',
    "PACKAGE_TARNAME": '"libffi"',
    "SIZEOF_DOUBLE": "8",
    "SIZEOF_LONG_DOUBLE": "8",
    "SIZEOF_SIZE_T": "8",
    "STDC_HEADERS": "1",
}


def libffi_version(source_dir: Path) -> tuple[str, str]:
    """libffi's release version and packed version number from configure.ac."""
    configure_ac = (source_dir / "configure.ac").read_text(encoding="utf-8")
    version = re.search(
        r"^AC_INIT\(\[libffi\],\s*\[(\d+)\.(\d+)\.(\d+)\]",
        configure_ac,
        re.MULTILINE,
    )
    if not version:
        raise SystemExit("could not read the libffi version from configure.ac")
    # Match configure.ac's encoding; newer releases derive this in shell.
    major, minor, micro = map(int, version.groups())
    number = major * 10000 + minor * 100 + micro
    return ".".join(version.groups()), str(number)


def generate_libffi_headers(source_dir: Path, include_dir: Path) -> None:
    """Write the headers libffi's configure step would have generated.

    The Windows tool set has no autoconf, so `ffi.h` and `fficonfig.h` are
    produced from their templates with the values `configure.host` selects
    for a non-Microsoft compiler on x86-64 Windows. Substituting into the
    upstream templates keeps everything the templates carry, including the
    hand-written `FFI_HIDDEN` block at the end of `fficonfig.h.in`.
    """
    version, version_number = libffi_version(source_dir)
    include_dir.mkdir(parents=True, exist_ok=True)

    ffi_h = (source_dir / "include" / "ffi.h.in").read_text(encoding="utf-8")
    for placeholder, value in (
        ("@VERSION@", version),
        ("@FFI_VERSION_STRING@", version),
        ("@FFI_VERSION_NUMBER@", version_number),
        ("@TARGET@", LIBFFI_WINDOWS_TARGET),
        # `long double` is a plain double in the Microsoft C runtime, and
        # closures live in memory this build allocates itself.
        ("@HAVE_LONG_DOUBLE@", "0"),
        ("@FFI_EXEC_TRAMPOLINE_TABLE@", "0"),
    ):
        ffi_h = ffi_h.replace(placeholder, value)
    (include_dir / "ffi.h").write_text(ffi_h, encoding="utf-8")

    fficonfig = (source_dir / "fficonfig.h.in").read_text(encoding="utf-8")
    defines = dict(LIBFFI_WINDOWS_DEFINES)
    defines["PACKAGE_STRING"] = f'"libffi {version}"'
    defines["PACKAGE_VERSION"] = f'"{version}"'
    defines["VERSION"] = f'"{version}"'
    for name, value in defines.items():
        fficonfig = fficonfig.replace(
            f"#undef {name}\n", f"#define {name} {value}\n"
        )
    (include_dir / "fficonfig.h").write_text(fficonfig, encoding="utf-8")

    for header in ("ffi_cfi.h", "ffi_common.h", "tramp.h"):
        shutil.copy2(source_dir / "include" / header, include_dir / header)
    shutil.copy2(
        source_dir / "src" / "x86" / "ffitarget.h",
        include_dir / "ffitarget.h",
    )


def build_libffi_windows(
    prefix: Path,
    source_dir: Path,
    env: dict[str, str],
) -> None:
    """Compile libffi for x86-64 Windows without its autoconf build.

    `configure.host` selects `ffiw64.c` with the GNU-assembler `win64.S` for
    every compiler other than Microsoft's, which is what native Clang provides.
    """
    include_dir = source_dir / "native-include"
    generate_libffi_headers(source_dir, include_dir)

    objects: list[Path] = []
    for relative in LIBFFI_COMMON_SOURCES + LIBFFI_WINDOWS_SOURCES:
        source = source_dir / relative
        obj = source.with_suffix(".o")
        run(
            [
                *cc_command(env),
                "-O2",
                # Static use: without this the Microsoft-style declarations in
                # ffi.h would be dllimport.
                "-DFFI_STATIC_BUILD",
                f"-I{include_dir}",
                "-c",
                str(source),
                "-o",
                str(obj),
            ],
            cwd=source_dir,
            env=env,
        )
        objects.append(obj)

    install_archive(
        objects,
        prefix,
        "libffi.a",
        cwd=source_dir,
        env=env,
    )
    install_headers(
        [include_dir / "ffi.h", include_dir / "ffitarget.h"],
        prefix,
    )


def build_zstd_sources(
    prefix: Path,
    lib_dir: Path,
    env: dict[str, str],
) -> None:
    """Compile libzstd's static library without its Makefile.

    zstd's build is driven by GNU Make, which the Windows tool set does not
    include. The library is a plain list of C sources per component, so the
    archive is assembled directly. `ZSTD_DISABLE_ASM` selects the portable
    Huffman decoder in place of the x86-64 assembly source.
    """
    components = ("common", "compress", "decompress", "dictBuilder")
    objects: list[Path] = []
    for component in components:
        for source in sorted((lib_dir / component).glob("*.c")):
            obj = source.with_suffix(".o")
            run(
                [
                    *cc_command(env),
                    "-O2",
                    "-DZSTD_DISABLE_ASM",
                    "-DXXH_NAMESPACE=ZSTD_",
                    f"-I{lib_dir}",
                    f"-I{lib_dir / 'common'}",
                    "-c",
                    str(source),
                    "-o",
                    str(obj),
                ],
                cwd=lib_dir,
                env=env,
            )
            objects.append(obj)
    install_archive(
        objects,
        prefix,
        "libzstd.a",
        cwd=lib_dir,
        env=env,
    )


def build_stamp(prefix: Path) -> Path:
    return prefix / ".python-deps-build-version"


def stamp_text(source_dirs: list[Path]) -> str:
    return f"{BUILD_CONFIG_REVISION}\n" + "".join(
        f"{source.resolve()}\n" for source in source_dirs
    )


def tool_command(env: dict[str, str], name: str, fallback: str) -> list[str]:
    return shlex.split(env.get(name, fallback))


def cc_command(env: dict[str, str]) -> list[str]:
    return tool_command(env, "CC", "cc")


def install_archive(
    objects: list[Path],
    prefix: Path,
    name: str,
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    lib_dir = prefix / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    archive = lib_dir / name
    if archive.exists():
        archive.unlink()
    run(
        [
            *tool_command(env, "AR", "ar"),
            "rcs",
            str(archive),
            *[str(obj) for obj in objects],
        ],
        cwd=cwd,
        env=env,
    )
    run(
        [*tool_command(env, "RANLIB", "ranlib"), str(archive)],
        cwd=cwd,
        env=env,
    )


def install_headers(headers: list[Path], prefix: Path) -> None:
    include_dir = prefix / "include"
    include_dir.mkdir(parents=True, exist_ok=True)
    for header in headers:
        shutil.copy2(header, include_dir / header.name)


def build_sqlite(
    toolchain: dict[str, str],
    prefix: Path,
    dependency_source: Path,
    work_dir: Path,
) -> None:
    source_dir = copy_source_tree(dependency_source, work_dir)
    env = dict(toolchain)
    obj = source_dir / "sqlite3.o"
    run(
        [
            *cc_command(env),
            "-O2",
            *SQLITE_CFLAGS,
            "-c",
            "sqlite3.c",
            "-o",
            str(obj),
        ],
        cwd=source_dir,
        env=env,
    )
    install_archive([obj], prefix, "libsqlite3.a", cwd=source_dir, env=env)
    install_headers(
        [source_dir / "sqlite3.h", source_dir / "sqlite3ext.h"],
        prefix,
    )


def build_bzip2(
    toolchain: dict[str, str],
    prefix: Path,
    dependency_source: Path,
    work_dir: Path,
) -> None:
    source_dir = copy_source_tree(dependency_source, work_dir)
    env = dict(toolchain)
    objects: list[Path] = []
    for source_name in BZIP2_SOURCES:
        obj = source_dir / f"{source_name}.o"
        run(
            [
                *cc_command(env),
                "-O2",
                "-D_FILE_OFFSET_BITS=64",
                "-c",
                source_name,
                "-o",
                str(obj),
            ],
            cwd=source_dir,
            env=env,
        )
        objects.append(obj)
    install_archive(objects, prefix, "libbz2.a", cwd=source_dir, env=env)
    install_headers([source_dir / "bzlib.h"], prefix)


def build_libffi(
    toolchain: dict[str, str],
    prefix: Path,
    dependency_source: Path,
    work_dir: Path,
) -> None:
    source_dir = copy_source_tree(dependency_source, work_dir)
    env = dict(toolchain)
    if sys.platform == "win32":
        build_libffi_windows(prefix, source_dir, env)
        return
    env["CFLAGS"] = "-O2"
    run(
        [
            "./configure",
            f"--prefix={prefix}",
            "--disable-shared",
            "--enable-static",
            "--disable-docs",
            "--disable-multi-os-directory",
            "--libdir=" + str(prefix / "lib"),
        ],
        cwd=source_dir,
        env=env,
    )
    jobs = str(min(os.cpu_count() or 4, 16))
    run(["make", "-j", jobs], cwd=source_dir, env=env)
    run(["make", "install"], cwd=source_dir, env=env)


def build_zstd(
    toolchain: dict[str, str],
    prefix: Path,
    dependency_source: Path,
    work_dir: Path,
) -> None:
    source_dir = copy_source_tree(dependency_source, work_dir)
    lib_dir = source_dir / "lib"
    env = dict(toolchain)
    if sys.platform == "win32":
        build_zstd_sources(prefix, lib_dir, env)
        install_headers(
            [
                lib_dir / name
                for name in ("zstd.h", "zstd_errors.h", "zdict.h")
            ],
            prefix,
        )
        return
    jobs = str(min(os.cpu_count() or 4, 16))
    run(
        [
            "make",
            "-j",
            jobs,
            "libzstd.a-release",
            f"CC={env['CC']}",
            f"AR={env['AR']}",
            f"RANLIB={env['RANLIB']}",
            "CFLAGS=-O2",
        ],
        cwd=lib_dir,
        env=env,
    )

    install_archive = prefix / "lib" / "libzstd.a"
    install_archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(lib_dir / "libzstd.a", install_archive)
    install_headers(
        [
            lib_dir / "zstd.h",
            lib_dir / "zstd_errors.h",
            lib_dir / "zdict.h",
        ],
        prefix,
    )


def build_python_deps(
    cc: str,
    ar: str,
    ranlib: str,
    target_triple: str,
    prefix: Path,
    cache_dir: Path,
    sqlite_source: Path,
    bzip2_source: Path,
    libffi_source: Path,
    zstd_source: Path,
    sdk_path: str | None,
    msvc_environ: Path | None = None,
) -> None:
    require_supported_target(target_triple)
    guard("python-deps")
    toolchain = toolchain_env(
        cc, ar, ranlib, target_triple, sdk_path, msvc_environ
    )
    build_sqlite(toolchain, prefix, sqlite_source, cache_dir / "sqlite")
    build_bzip2(toolchain, prefix, bzip2_source, cache_dir / "bzip2")
    build_libffi(toolchain, prefix, libffi_source, cache_dir / "libffi")
    build_zstd(toolchain, prefix, zstd_source, cache_dir / "zstd")
    if sys.platform == "win32":
        for name in ("sqlite3", "bz2", "ffi", "zstd"):
            shutil.copy2(
                prefix / "lib" / f"lib{name}.a", prefix / "lib" / f"{name}.lib"
            )
    build_stamp(prefix).write_text(
        stamp_text([sqlite_source, bzip2_source, libffi_source, zstd_source])
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for tool in ("cc", "ar", "ranlib"):
        parser.add_argument(f"--{tool}", required=True)
    parser.add_argument("--target-triple", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--sqlite-source", required=True)
    parser.add_argument("--bzip2-source", required=True)
    parser.add_argument("--libffi-source", required=True)
    parser.add_argument("--zstd-source", required=True)
    parser.add_argument("--sdk-path")
    parser.add_argument("--msvc-environ", type=Path)
    parser.add_argument("--stamp", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_python_deps(
        args.cc,
        args.ar,
        args.ranlib,
        args.target_triple,
        Path(args.prefix),
        Path(args.cache_dir),
        Path(args.sqlite_source),
        Path(args.bzip2_source),
        Path(args.libffi_source),
        Path(args.zstd_source),
        args.sdk_path,
        args.msvc_environ,
    )

    stamp = Path(args.stamp)
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text("ok\n")


if __name__ == "__main__":
    main()
