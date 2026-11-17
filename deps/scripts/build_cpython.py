#!/usr/bin/env python3
"""Build a static CPython.

The fallback uses a project-managed CPython source build on every supported
target instead of consuming python-build-standalone assets. That keeps Linux
and macOS on the same maintenance path and gives the project one place to
control CPython's static extension set and link inputs.

The build is configured so the result matches what the embedding pipeline
needs:

- static libpython, no shared libpython, empty lib-dynload
- MODULE_BUILDTYPE=static: every enabled stdlib extension is compiled into
  libpython and listed in the generated config.c inittab
- --enable-optimizations and --with-lto=thin by default, followed by a partial
  native link that turns CPython and its bundled support archives into a
  standard relocatable object wrapped in a normal static archive
- _ssl/_hashlib link the project-built OpenSSL from the CRT install prefix,
  zlib/_lzma link the project-built libz.a/liblzma.a from the same prefix
- _bz2/_sqlite3/_ctypes/_zstd link the project-built
  libbz2.a/libsqlite3.a/libffi.a/libzstd.a from the python-deps prefix
  (deps/scripts/build_python_deps.py)
- on macOS, _scproxy stays enabled in the runnable build interpreter so
  urllib/pip behavior remains normal; it remains in the materialized
  libpython and consumers link SystemConfiguration.framework
- the materialized libpython omits config.o, so its _PyImport_Inittab is
  undefined until a consumer supplies one: lib/<abi>-inittab.c exports the
  archive's own table for consumers that want every extension it carries,
  while the fallback generates a table that also registers its extensions

Linux uses the pinned clang wrappers and a project-built musl sysroot.
The profile merger comes from the same LLVM release; compiler-rt supplies
the project-built profile runtime. macOS uses the native Apple toolchain.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import build_cpython_windows
from build_environ import tool_environ
from build_guard import guard
from native_target import require_native_target
from payload_sysconfig import (
    PAYLOAD_DIRECTORY,
    RUNTIME_PREFIX,
    write_payload_sysconfig,
)

# Bump to force a rebuild when the configure or materialization flags below
# change.
BUILD_CONFIG_REVISION = "36"
BUILD_SRCDIR = "../source"

PROFILE_TASK = (
    '-c "'
    "import argparse, bz2, ctypes, hashlib, json, lzma, sqlite3, ssl, sys, "
    "urllib.request, xml.etree.ElementTree; "
    "[str(i) for i in range(20000)]"
    '"'
)

LINUX_PROFILE_TASK = (
    '-c "'
    "import argparse, bz2, hashlib, json, lzma, sqlite3, ssl, sys, "
    "urllib.request, xml.etree.ElementTree; "
    "[str(i) for i in range(20000)]"
    '"'
)

# Stdlib extensions excluded from the build entirely. Everything here is
# either absent from the Linux fallback's registered extension set or pulls
# in toolkit dependencies (ncurses, tcl/tk, gdbm) the project does not ship.
DISABLED_MODULES = [
    "_tkinter",
    "_curses",
    "_curses_panel",
    "_gdbm",
    "_dbm",
    "syslog",
    "_multiprocessing",
    "_posixshmem",
]

# Extension objects dropped from the materialized archive, and therefore
# from its exported table. Every enabled extension ships.
EXCLUDED_EXTENSIONS: list[str] = []

# One `{"name", PyInit_name},` line of CPython's generated Modules/config.c.
INITTAB_ENTRY = re.compile(
    r'^\s*\{"([A-Za-z0-9_]+)",\s*([A-Za-z0-9_]+)\},?\s*(?:/\*.*\*/)?\s*$'
)


@dataclass(frozen=True)
class LinuxPgoTools:
    llvm_profdata: Path
    profile_runtime: Path


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path | None = None,
) -> None:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            check=True,
        )
        if log_path is not None:
            log_path.write_bytes(result.stdout + result.stderr)
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


def deployment_target(target_triple: str) -> str:
    if target_triple.startswith("aarch64-macos"):
        return "11.0"
    if target_triple.startswith("x86_64-macos"):
        return "10.15"
    raise SystemExit(f"unsupported CPython build target: {target_triple}")


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


def is_windows_target(target_triple: str) -> bool:
    return target_triple in ("x86_64-windows-msvc", "x86_64-pc-windows-msvc")


def require_supported_target(target_triple: str) -> None:
    require_native_target(target_triple)
    if (
        is_linux_musl_target(target_triple)
        or is_macos_target(target_triple)
        or is_windows_target(target_triple)
    ):
        return
    raise SystemExit(f"unsupported CPython build target: {target_triple}")


def build_stamp(prefix: Path) -> Path:
    return prefix / ".cpython-build-version"


def source_identity(source_dir: Path) -> str:
    return str(source_dir.resolve())


def stamp_text(
    source_dir: Path,
    target_triple: str,
    cc_build_identity: str,
    pgo: bool,
    llvm_profdata: Path | None,
    profile_runtime: Path | None,
    aws_cli_source: Path | None = None,
) -> str:
    llvm_profdata_identity = (
        source_identity(llvm_profdata) if llvm_profdata is not None else "none"
    )
    profile_runtime_identity = (
        source_identity(profile_runtime)
        if profile_runtime is not None
        else "none"
    )
    training_identity = "stdlib"
    if pgo and aws_cli_source is not None:
        digest = hashlib.sha256(
            Path(__file__).with_name("profile_aws.py").read_bytes()
        )
        for source in sorted((aws_cli_source / "awscli").rglob("*")):
            if "__pycache__" in source.parts or source.suffix == ".pyc":
                continue
            if source.is_file():
                digest.update(str(source.relative_to(aws_cli_source)).encode())
                digest.update(source.read_bytes())
        training_identity = digest.hexdigest()
    return (
        f"{BUILD_CONFIG_REVISION}\n"
        f"{target_triple}\n"
        f"{cc_build_identity}\n"
        f"pgo={pgo}\n"
        f"{source_identity(source_dir)}\n"
        f"{llvm_profdata_identity}\n"
        f"{profile_runtime_identity}\n"
        f"{training_identity}\n"
    )


def python_abi_name(python_version: str) -> str:
    """ABI name ("python3.14") from a full version ("3.14.5")."""
    major_minor = python_version.rpartition(".")[0]
    if not major_minor:
        raise SystemExit(
            f"--python-version must be MAJOR.MINOR.MICRO, got {python_version!r}"
        )
    return f"python{major_minor}"


def is_built(
    prefix: Path,
    python_abi: str,
    source_dir: Path,
    target_triple: str,
    cc_build_identity: str,
    pgo: bool,
    llvm_profdata: Path | None,
    profile_runtime: Path | None,
    aws_cli_source: Path | None = None,
) -> bool:
    return (
        (prefix / "lib" / f"lib{python_abi}.a").exists()
        and inittab_source_path(prefix, python_abi).exists()
        and (
            prefix
            / "bin"
            / f"{python_abi}{'.exe' if is_windows_target(target_triple) else ''}"
        ).exists()
        and (prefix / PAYLOAD_DIRECTORY).is_dir()
        and build_stamp(prefix).exists()
        and build_stamp(prefix).read_text()
        == stamp_text(
            source_dir,
            target_triple,
            cc_build_identity,
            pgo,
            llvm_profdata,
            profile_runtime,
            aws_cli_source,
        )
    )


def configure_args(
    prefix: Path,
    openssl_prefix: Path,
    zlib_xz_prefix: Path,
    deps_prefix: Path,
    target_triple: str,
    pgo: bool,
    aws_cli_source: Path | None = None,
) -> list[str]:
    args = [
        f"--prefix={prefix}",
        # These feed getpath.c, not make install. Executable landmarks find
        # the physical installation; build-tree freezing needs a real,
        # stable relative VPATH through the scratch source symlink.
        f"host_prefix={RUNTIME_PREFIX}",
        f"host_exec_prefix={RUNTIME_PREFIX}",
        f"--srcdir={BUILD_SRCDIR}",
        "--disable-test-modules",
        "--without-remote-debug",
        "--with-lto=thin",
        f"--with-openssl={openssl_prefix}",
        "--with-openssl-rpath=no",
        "--with-system-libmpdec=no",
        "--without-readline",
        "MODULE_BUILDTYPE=static",
        # Block pkg-config so system packages can never leak in; every
        # external dependency is a project-built static archive from the
        # OpenSSL, zlib/xz, or python-deps prefix, passed explicitly below.
        "PKG_CONFIG=/usr/bin/false",
        f"ZLIB_CFLAGS=-I{zlib_xz_prefix}/include",
        f"ZLIB_LIBS={zlib_xz_prefix}/lib/libz.a",
        f"LIBLZMA_CFLAGS=-I{zlib_xz_prefix}/include",
        f"LIBLZMA_LIBS={zlib_xz_prefix}/lib/liblzma.a",
        f"BZIP2_CFLAGS=-I{deps_prefix}/include",
        f"BZIP2_LIBS={deps_prefix}/lib/libbz2.a",
        f"LIBSQLITE3_CFLAGS=-I{deps_prefix}/include",
        f"LIBSQLITE3_LIBS={deps_prefix}/lib/libsqlite3.a",
        f"LIBFFI_CFLAGS=-I{deps_prefix}/include",
        f"LIBFFI_LIBS={deps_prefix}/lib/libffi.a",
        f"LIBZSTD_CFLAGS=-I{deps_prefix}/include",
        f"LIBZSTD_LIBS={deps_prefix}/lib/libzstd.a",
    ]
    if pgo:
        profile_task = (
            LINUX_PROFILE_TASK
            if is_linux_musl_target(target_triple)
            else PROFILE_TASK
        )
        if aws_cli_source is not None:
            profile_task = shlex.join(
                [
                    "-B",
                    str(Path(__file__).with_name("profile_aws.py")),
                    str(aws_cli_source),
                ]
            )
        args.extend(
            [
                "--enable-optimizations",
                f"PROFILE_TASK={profile_task}",
            ]
        )
    if is_linux_musl_target(target_triple):
        # Select FNV hashing, as deps/cpython-linux-pyconfig.h records with
        # HAVE_ALIGNED_REQUIRED. Configure's alignment probe intentionally
        # reads misaligned integers; an explicit answer gives that result
        # without requiring undefined behavior in configure.
        args.extend(["--with-ensurepip=no", "ac_cv_aligned_required=yes"])
    args.extend(f"py_cv_module_{name}=n/a" for name in DISABLED_MODULES)
    return args


def support_archive_dir(prefix: Path) -> Path:
    return prefix / "lib" / "python-support"


def preserve_linux_metadata(
    build_dir: Path, python_abi: str, env: dict[str, str]
) -> None:
    """Keep the target triplet out of the static interpreter's metadata paths.

    Configure derives these values directly from compiler probes, ignoring
    command-line assignments. Change its generated substitutions and rerun
    config.status so Makefile and python-config agree on every ABI name.
    This does not change the compiler target or the configured features.
    """
    abi_tag = "cpython-" + python_abi.removeprefix("python").replace(".", "")
    substitutions = {
        "MULTIARCH": "",
        "MULTIARCH_CPPFLAGS": "",
        "PLATFORM_TRIPLET": "",
        "SOABI": abi_tag,
        "EXT_SUFFIX": f".{abi_tag}.so",
        "LIBPL": f"$(prefix)/lib/{python_abi}/config-$(VERSION)$(ABIFLAGS)",
    }
    status = build_dir / "config.status"
    contents = status.read_text()
    for name, value in substitutions.items():
        pattern = rf'^S\["{name}"\]=.*$'
        contents, count = re.subn(
            pattern,
            f'S["{name}"]="{value}"',
            contents,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise SystemExit(f"expected one config.status field: {name}")
    status.write_text(contents)
    run([str(status)], cwd=build_dir, env=env)


def verify_linux_configuration(build_dir: Path, target_triple: str) -> None:
    """Reject unreviewed feature drift from the recorded Linux configuration."""
    expected = (
        Path(__file__).resolve().parents[1] / "cpython-linux-pyconfig.h"
    ).read_text()
    actual = (build_dir / "pyconfig.h").read_text()
    changes = linux_configuration_changes(expected, actual, target_triple)
    if changes:
        raise SystemExit(
            "CPython pyconfig.h has unreviewed feature differences: "
            f"{changes}; configuration: {build_dir / 'pyconfig.h'}"
        )


def linux_configuration_changes(
    recorded: str,
    current: str,
    target_triple: str = "x86_64-unknown-linux-musl",
) -> dict[str, tuple[str | None, str | None]]:
    """Compare features, accounting for reviewed CPython 3.14.8 additions."""
    pattern = r"^#define\s+(\S+)(?:[^\S\n]+(.*))?$"
    expected = dict(re.findall(pattern, recorded, re.MULTILINE))
    actual = dict(re.findall(pattern, current, re.MULTILINE))
    # Clang identifies musl as tier 0. CPython 3.14.8 additionally probes
    # musl's dl_iterate_phdr and declares the linker's 1 MiB stack default;
    # its new curses/sysctl probes remain undefined on this static host.
    expected.update(
        PY_SUPPORT_TIER="0",
        HAVE_DL_ITERATE_PHDR="1",
        _Py_LINKER_THREAD_STACK_SIZE="1048576",
    )
    # The embedded runtime is built without remote debugging, so the
    # recorded configuration's remote-debug support must now be absent.
    expected.pop("Py_REMOTE_DEBUG", None)
    if target_triple.startswith("aarch64"):
        # The recorded configuration was x86_64; these probes name x86
        # assembly and must be absent in an otherwise equivalent ARM build.
        expected.pop("HAVE_GCC_ASM_FOR_X64", None)
        expected.pop("HAVE_GCC_ASM_FOR_X87", None)
        # HACL*'s SIMD probes accept only the x86 -msse and -mavx2 flags.
        expected.pop("_Py_HACL_CAN_COMPILE_VEC128", None)
        expected.pop("_Py_HACL_CAN_COMPILE_VEC256", None)
        # CPython uses wchar_t only when it is unsigned, as it is on ARM
        # Linux and is not on x86_64 Linux.
        expected["HAVE_USABLE_WCHAR_T"] = "1"
    return {
        name: (expected.get(name), actual.get(name))
        for name in sorted(expected.keys() | actual.keys())
        if expected.get(name) != actual.get(name)
    }


def inittab_source_path(prefix: Path, python_abi: str) -> Path:
    return prefix / "lib" / f"{python_abi}-inittab.c"


def write_inittab_source(
    build_dir: Path, prefix: Path, python_abi: str
) -> None:
    """Export the materialized archive's extension table as C source.

    A normal static build defines _PyImport_Inittab in config.o. The
    materialized archive leaves config.o out so a consumer's own table can
    exclude extensions, which makes Py_Initialize() an undefined reference
    until some table is linked. This source is that table for consumers
    that want every extension the archive carries: CPython's generated
    Modules/config.c minus the members removed from the archive. Consumers
    compile it against the installed headers; it needs no core defines.
    """
    config_c = (
        build_dir
        if build_dir.is_file()
        else build_dir / "Modules" / "config.c"
    )
    entries: list[tuple[str, str]] = []
    for line in config_c.read_text().splitlines():
        match = INITTAB_ENTRY.match(line)
        if match is None:
            continue
        name, init_fn = match.groups()
        if name not in EXCLUDED_EXTENSIONS:
            entries.append((name, init_fn))
    if not entries:
        raise SystemExit(f"no inittab entries parsed from {config_c}")
    lines = [
        "// Generated by deps/scripts/build_cpython.py from CPython's",
        "// Modules/config.c: the extension table of the libpython archive",
        "// installed beside it. Do not edit.",
        "#include <Python.h>",
        "",
        *(
            f"PyMODINIT_FUNC {init_fn}(void);"
            for _, init_fn in entries
            # In-core modules such as sys and builtins list no init function.
            if init_fn != "NULL"
        ),
        "",
        "struct _inittab _PyImport_Inittab[] = {",
        *(f'    {{"{name}", {init_fn}}},' for name, init_fn in entries),
        "    {NULL, NULL},",
        "};",
        "",
    ]
    inittab_source_path(prefix, python_abi).write_text("\n".join(lines))


def collect_support_archives(build_dir: Path) -> list[Path]:
    """Return bundled extension support archives from CPython's build tree."""
    return [
        archive
        for archive in sorted(build_dir.rglob("lib*.a"))
        if not archive.name.startswith("libpython")
    ]


def patch_linux_pgo_makefile(
    build_dir: Path,
    pgo_tools: LinuxPgoTools,
) -> None:
    old = 'LDFLAGS_NODIST="$(LDFLAGS_NODIST) $(PGO_PROF_GEN_FLAG)" LIBS="$(LIBS)"'
    new = (
        'LDFLAGS_NODIST="$(LDFLAGS_NODIST) $(PGO_PROF_GEN_FLAG) '
        f'-Wl,-u,__llvm_profile_runtime {pgo_tools.profile_runtime}" '
        'LIBS="$(LIBS)"'
    )
    # makesetup may regenerate Makefile after config.status updates the
    # generated module lists. Preserve the profile runtime in its input too.
    for name in ["Makefile.pre", "Makefile"]:
        makefile = build_dir / name
        text = makefile.read_text()
        flag = "PGO_PROF_GEN_FLAG=-fprofile-instr-generate\n"
        if text.count(flag) != 1 or text.count(old) != 1:
            raise SystemExit(f"could not find CPython PGO rules in {name}")
        text = text.replace(
            flag,
            "PGO_PROF_GEN_FLAG=-fprofile-instr-generate "
            "-mllvm -enable-name-compression=false\n",
        )
        text = text.replace(old, new, 1)
        makefile.write_text(text)


def reset_support_archive_dir(prefix: Path) -> None:
    """Create the support archive directory expected by gen_inittab.py.

    The PGO/ThinLTO build materializes CPython's bundled support archives
    directly into libpython, so there are no separate support libraries
    left for the executable to link. The empty directory keeps the downstream self-built
    CPython layout explicit.
    """
    support_dir = support_archive_dir(prefix)
    if support_dir.exists():
        shutil.rmtree(support_dir)
    support_dir.mkdir(parents=True)


def archive_members(archive: Path, env: dict[str, str]) -> set[str]:
    result = subprocess.run(
        [*tool_command(env, "AR", "ar"), "-t", str(archive)],
        env=env,
        capture_output=True,
        check=True,
    )
    return set(result.stdout.decode("utf-8").splitlines())


def tool_command(env: dict[str, str], name: str, fallback: str) -> list[str]:
    return shlex.split(env.get(name, fallback))


def remove_archive_members(
    archive: Path,
    members: list[str],
    env: dict[str, str],
) -> None:
    existing = sorted(archive_members(archive, env).intersection(members))
    if existing:
        run(
            [*tool_command(env, "AR", "ar"), "-d", str(archive), *existing],
            cwd=archive.parent,
            env=env,
        )


def materialize_command(
    ld: str,
    target_triple: str,
    input_libpython: Path,
    materialized_obj: Path,
    support_archives: list[Path],
    sdk_path: str | None,
) -> list[str]:
    if is_macos_target(target_triple):
        if sdk_path is None:
            raise SystemExit("--sdk-path is required for macOS CPython builds")
        return [
            ld,
            "-r",
            "-flto=thin",
            "-isysroot",
            sdk_path,
            f"-mmacosx-version-min={deployment_target(target_triple)}",
            "-o",
            str(materialized_obj),
            f"-Wl,-force_load,{input_libpython}",
            *[str(archive) for archive in support_archives],
        ]
    if is_linux_musl_target(target_triple):
        return [
            ld,
            "-m",
            "aarch64linux"
            if target_triple.startswith("aarch64")
            else "elf_x86_64",
            "-r",
            # Keep the optimized frontend's O3 level through LTO codegen.
            "--lto-O3",
            "-o",
            str(materialized_obj),
            "--whole-archive",
            str(input_libpython),
            "--no-whole-archive",
            *[str(archive) for archive in support_archives],
        ]
    require_supported_target(target_triple)
    raise AssertionError("unreachable")


def materialize_lto_archive(
    ld: str,
    target_triple: str,
    build_dir: Path,
    prefix: Path,
    python_abi: str,
    sdk_path: str | None,
    env: dict[str, str],
) -> None:
    """Replace installed libpython with a native archive materialized from LTO.

    CPython's PGO/ThinLTO build leaves libpython and bundled support archives
    as bitcode wrapper objects. Consumers need native objects. This function performs
    the LTO link first, producing one native relocatable object, then wraps
    that object in a standard archive.

    config.o is intentionally left out so the linked table is the
    consumer's choice: write_inittab_source() exports the archive's complete
    table, and deps/scripts/gen_inittab.py emits the fallback's own.
    EXCLUDED_EXTENSIONS are also left out; on macOS that keeps
    SystemConfiguration.framework out of every consumer's link.
    """
    libpython = prefix / "lib" / f"lib{python_abi}.a"
    work_dir = build_dir / "zippy-materialized"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    input_libpython = work_dir / f"lib{python_abi}-lto-input.a"
    shutil.copy2(libpython, input_libpython)
    remove_archive_members(
        input_libpython,
        ["config.o", *(f"{name}.o" for name in EXCLUDED_EXTENSIONS)],
        env,
    )

    materialized_obj = work_dir / f"lib{python_abi}-materialized.o"
    materialized_archive = work_dir / f"lib{python_abi}-materialized.a"
    support_archives = collect_support_archives(build_dir)
    run(
        materialize_command(
            ld,
            target_triple,
            input_libpython,
            materialized_obj,
            support_archives,
            sdk_path,
        ),
        cwd=build_dir,
        env=env,
    )
    run(
        [
            *tool_command(env, "AR", "ar"),
            "rc",
            str(materialized_archive),
            str(materialized_obj),
        ],
        cwd=build_dir,
        env=env,
    )
    run(
        [*tool_command(env, "RANLIB", "ranlib"), str(materialized_archive)],
        cwd=build_dir,
        env=env,
    )
    shutil.copy2(materialized_archive, libpython)
    reset_support_archive_dir(prefix)


def verify_static_build(
    prefix: Path,
    python_abi: str,
    target_triple: str,
    env: dict[str, str],
) -> None:
    dynload = prefix / "lib" / python_abi / "lib-dynload"
    if dynload.is_dir():
        shared = sorted(p.name for p in dynload.iterdir() if p.suffix == ".so")
        if shared:
            raise SystemExit(
                f"CPython build produced shared extensions: {shared}; "
                "expected a fully static build"
            )

    python = prefix / "bin" / python_abi
    if not python.is_file():
        raise SystemExit(f"CPython executable is missing: {python}")

    check = (
        "import sys\n"
        "required = ['_ssl', '_hashlib', 'zlib', '_bz2', '_lzma', '_sqlite3',"
        " '_ctypes', '_zstd', '_decimal', 'pyexpat', '_socket']\n"
        "missing = [m for m in required if m not in "
        "sys.builtin_module_names]\n"
        "assert not missing, f'not built into libpython: {missing}'\n"
        "import ssl\n"
        "assert ssl.OPENSSL_VERSION.startswith('OpenSSL 3.'), "
        "ssl.OPENSSL_VERSION\n"
        "import sqlite3\n"
        "sqlite3.connect(':memory:').execute('create table t (x)')\n"
        "import bz2\n"
        "assert bz2.decompress(bz2.compress(b'zippy')) == b'zippy'\n"
        "import compression.zstd as zstd\n"
        "assert zstd.decompress(zstd.compress(b'zippy')) == b'zippy'\n"
    )
    if is_macos_target(target_triple):
        check += "import ctypes\nassert ctypes.c_int(7).value == 7\n"
    elif is_linux_musl_target(target_triple):
        check += "assert sys.hash_info.algorithm == 'fnv', sys.hash_info\n"
    run([str(python), "-c", check], cwd=prefix, env=env)

    if is_macos_target(target_triple):
        # The SDK's dylib stubs for these must never reach the link; the
        # project builds static archives for them
        # (deps/scripts/build_python_deps.py).
        otool = subprocess.run(
            ["otool", "-L", str(python)],
            env=env,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
        leaked = [
            name
            for name in ("libsqlite3", "libbz2", "libffi", "libzstd")
            if name in otool
        ]
        if leaked:
            raise SystemExit(
                f"{python_abi} dynamically links {leaked}; "
                f"expected static archives from the CRT prefix:\n{otool}"
            )
    elif is_linux_musl_target(target_triple):
        ldd = subprocess.run(
            ["ldd", str(python)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        ).stdout.decode("utf-8")
        if (
            "not a dynamic executable" not in ldd
            and "statically linked" not in ldd
        ):
            raise SystemExit(f"{python_abi} is not statically linked:\n{ldd}")


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


def build_env(
    cc: str,
    ar: str,
    ranlib: str,
    ld: str,
    target_triple: str,
    openssl_prefix: Path,
    zlib_xz_prefix: Path,
    deps_prefix: Path | None,
    sdk_path: str | None,
    msvc_environ: Path | None = None,
    *,
    source_dir: Path,
    cache_dir: Path,
) -> dict[str, str]:
    require_supported_target(target_triple)
    env = tool_environ(msvc_environ=msvc_environ)
    # Configure, make, and tool_command split these as shell words, so a
    # checkout path with spaces or quotes must stay one argument.
    env.update(
        {
            "CC": shlex.quote(cc),
            "AR": shlex.quote(ar),
            "LLVM_AR": shlex.quote(ar),
            "RANLIB": shlex.quote(ranlib),
            "LD": shlex.quote(ld),
            "PKG_CONFIG": "/usr/bin/false",
            "ZERO_AR_DATE": "1",
            # Match the CRT's reproducibility epoch. getbuildinfo.c uses
            # __DATE__ and __TIME__; relocation checks must not differ just
            # by build time.
            "SOURCE_DATE_EPOCH": "946684800",
        }
    )
    if is_windows_target(target_triple):
        # The Windows builder passes its own prefix maps to the compiler and
        # reads no autoconf environment.
        return env
    cflags = build_cpython_windows.file_prefix_map_flags(
        source_dir, cache_dir, openssl_prefix, zlib_xz_prefix, deps_prefix
    )
    if is_macos_target(target_triple):
        if sdk_path is None:
            raise SystemExit("--sdk-path is required for macOS CPython builds")
        env["SDKROOT"] = sdk_path
        env["LLVM_PROFDATA"] = apple_tool("llvm-profdata", env)
        env["MACOSX_DEPLOYMENT_TARGET"] = deployment_target(target_triple)
        if deps_prefix is not None:
            env["LDFLAGS"] = f"-L{deps_prefix}/lib"
    elif is_linux_musl_target(target_triple):
        cflags.insert(0, "-Wno-error=date-time")
        env["LDFLAGS"] = (
            f"-static -L{openssl_prefix}/lib -L{zlib_xz_prefix}/lib"
        )
        if deps_prefix is not None:
            env["LDFLAGS"] += f" -L{deps_prefix}/lib"
    env["CFLAGS"] = shlex.join(cflags)
    return env


def configured_variable(build_dir: Path, name: str) -> str:
    """The value configure wrote for `name` in the generated Makefile."""
    makefile = build_dir / "Makefile"
    pattern = re.compile(rf"^{name}=[ \t]*(.*?)[ \t]*$", re.MULTILINE)
    match = pattern.search(makefile.read_text())
    if match is None:
        raise SystemExit(f"could not find {name} in {makefile}")
    return match.group(1)


def verify_macos_toolchain(
    build_dir: Path,
    env: dict[str, str],
    pgo: bool,
) -> None:
    """Check that configure kept the pinned Apple archiver and profile merger.

    Without this the leak is silent until make hands Apple clang's bitcode to
    a foreign llvm-ar, hundreds of lines into the build.
    """
    archiver = configured_variable(build_dir, "AR")
    if archiver != env["AR"]:
        raise SystemExit(
            f"configure chose AR={archiver!r}, expected {env['AR']!r}; "
            "another toolchain's archiver is ahead of the Apple toolchain "
            "on PATH"
        )
    if not pgo:
        return
    merger = configured_variable(build_dir, "LLVM_PROF_MERGER")
    if env["LLVM_PROFDATA"] not in merger:
        raise SystemExit(
            f"configure chose {merger!r}, expected the profile merger to use "
            f"{env['LLVM_PROFDATA']!r}; another toolchain's llvm-profdata is "
            "ahead of the Apple toolchain on PATH"
        )


def verify_pgo_build(build_dir: Path) -> None:
    profile = build_dir / "code.profclangd"
    if not profile.is_file() or profile.stat().st_size == 0:
        raise SystemExit(f"CPython PGO profile is missing or empty: {profile}")


def require_linux_pgo_tools(
    llvm_profdata: Path | None,
    profile_runtime: Path | None,
) -> LinuxPgoTools:
    if llvm_profdata is None:
        raise SystemExit("--llvm-profdata is required for Linux PGO")
    if profile_runtime is None:
        raise SystemExit("--profile-runtime is required for Linux PGO")
    if not llvm_profdata.is_file():
        raise SystemExit(f"llvm-profdata does not exist: {llvm_profdata}")
    if not os.access(llvm_profdata, os.X_OK):
        raise SystemExit(f"llvm-profdata is not executable: {llvm_profdata}")
    if not profile_runtime.is_file():
        raise SystemExit(
            f"profiling runtime does not exist: {profile_runtime}"
        )
    return LinuxPgoTools(
        llvm_profdata=llvm_profdata,
        profile_runtime=profile_runtime,
    )


def prepare_source_link(source_dir: Path, cache_dir: Path) -> None:
    """Expose the immutable source package at the stable build-tree VPATH."""
    link = cache_dir / "source"
    if link.is_symlink():
        link.unlink()
    link.symlink_to(source_dir.resolve(), target_is_directory=True)


def payload_sysconfig_roots(
    tools: Sequence[str],
    prefix: Path,
    source_dir: Path,
    cache_dir: Path,
    openssl_prefix: Path,
    zlib_xz_prefix: Path,
    deps_prefix: Path,
    llvm_profdata: Path | None,
    profile_runtime: Path | None,
    sdk_path: str | None,
    aws_cli_source: Path | None,
    env: dict[str, str],
) -> list[tuple[Path, str]]:
    """Inventory physical roots here, where all producer inputs are known."""
    roots = [
        (prefix, RUNTIME_PREFIX),
        (source_dir, "/aws-cli-build/cpython"),
        (cache_dir / "source", "/aws-cli-build/cpython"),
        (cache_dir, "/aws-cli-build/cpython-cache"),
        (cache_dir / "build", "/aws-cli-build/cpython-build"),
        (openssl_prefix, "/aws-cli-build/openssl"),
        (zlib_xz_prefix, "/aws-cli-build/zlib-xz"),
        (deps_prefix, "/aws-cli-build/python-deps"),
        (Path(__file__).resolve().parent, "/aws-cli-build/cpython-driver"),
    ]
    # Configure records the compiler, archiver, and linker paths. Each sits
    # in the native toolchain's own tree, or is a wrapper script there.
    for tool in tools:
        tool_path = Path(shutil.which(tool) or tool).absolute()
        roots.append((tool_path.parent, "/aws-cli-build/toolchain"))
        roots.append((tool_path.resolve().parent, "/aws-cli-build/toolchain"))
    for path, logical in (
        (llvm_profdata, "/aws-cli-build/pgo/llvm-profdata"),
        (profile_runtime, "/aws-cli-build/pgo/libclang_rt.profile.a"),
        (Path(sdk_path) if sdk_path else None, "/aws-cli-build/sdk"),
        (aws_cli_source, "/aws-cli-build/aws-cli"),
    ):
        if path is not None:
            roots.append((path, logical))
    # Apple configure records absolute tool paths resolved by xcrun.
    if sys.platform == "darwin":
        for name in ("AR", "RANLIB", "LLVM_PROFDATA"):
            if name in env:
                roots.append((Path(env[name]), f"/aws-cli-build/tools/{name}"))
    # Configure may record lexical paths or their resolved symlink targets.
    return [
        (variant, logical)
        for path, logical in roots
        for variant in dict.fromkeys((path.absolute(), path.resolve()))
    ]


def build_cpython(
    cc: str,
    ar: str,
    ranlib: str,
    ld: str,
    target_triple: str,
    python_version: str,
    prefix: Path,
    openssl_prefix: Path,
    zlib_xz_prefix: Path,
    deps_prefix: Path,
    cache_dir: Path,
    source_dir: Path,
    pgo: bool,
    llvm_profdata: Path | None,
    profile_runtime: Path | None,
    sdk_path: str | None,
    aws_cli_source: Path | None = None,
    msvc_environ: Path | None = None,
) -> None:
    python_abi = python_abi_name(python_version)
    env = build_env(
        cc,
        ar,
        ranlib,
        ld,
        target_triple,
        openssl_prefix,
        zlib_xz_prefix,
        deps_prefix,
        sdk_path,
        msvc_environ,
        source_dir=source_dir,
        cache_dir=cache_dir,
    )
    cc_build_identity = compiler_identity(cc, env)
    if is_built(
        prefix,
        python_abi,
        source_dir,
        target_triple,
        cc_build_identity,
        pgo,
        llvm_profdata,
        profile_runtime,
        aws_cli_source,
    ):
        return

    guard("cpython")
    cache_dir.mkdir(parents=True, exist_ok=True)
    build_dir = cache_dir / "build"

    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    if is_windows_target(target_triple):
        if pgo:
            raise SystemExit("CPython PGO is unsupported on Windows")
        config_c = build_cpython_windows.build_static_cpython(
            cc,
            ar,
            python_version,
            prefix,
            openssl_prefix,
            zlib_xz_prefix,
            deps_prefix,
            cache_dir,
            source_dir,
            env,
            min(os.cpu_count() or 4, 16),
        )
        write_inittab_source(config_c, prefix, python_abi)
        write_payload_sysconfig(
            prefix / "bin" / "Lib", prefix, [], required=False
        )
        build_stamp(prefix).write_text(
            stamp_text(
                source_dir,
                target_triple,
                cc_build_identity,
                pgo,
                llvm_profdata,
                profile_runtime,
                aws_cli_source,
            )
        )
        return
    linux_pgo_tools: LinuxPgoTools | None = None
    if is_linux_musl_target(target_triple) and pgo:
        linux_pgo_tools = require_linux_pgo_tools(
            llvm_profdata,
            profile_runtime,
        )
        env["LLVM_PROFDATA"] = str(linux_pgo_tools.llvm_profdata)

    prepare_source_link(source_dir, cache_dir)
    run(
        [
            f"{BUILD_SRCDIR}/configure",
            *configure_args(
                prefix,
                openssl_prefix,
                zlib_xz_prefix,
                deps_prefix,
                target_triple,
                pgo,
                aws_cli_source,
            ),
        ],
        cwd=build_dir,
        env=env,
    )
    for name, expected in (
        ("host_prefix", RUNTIME_PREFIX),
        ("host_exec_prefix", RUNTIME_PREFIX),
        ("VPATH", BUILD_SRCDIR),
    ):
        if configured_variable(build_dir, name) != expected:
            raise SystemExit(f"configure did not retain stable {name}")
    if is_linux_musl_target(target_triple):
        preserve_linux_metadata(build_dir, python_abi, env)
        verify_linux_configuration(build_dir, target_triple)
    if linux_pgo_tools is not None:
        patch_linux_pgo_makefile(build_dir, linux_pgo_tools)
    if is_macos_target(target_triple):
        verify_macos_toolchain(build_dir, env, pgo)
    jobs = str(min(os.cpu_count() or 4, 16))
    run(
        ["make", "-j", jobs],
        cwd=build_dir,
        env=env,
        log_path=build_dir / "build.log",
    )
    run(["make", "install"], cwd=build_dir, env=env)

    if pgo:
        verify_pgo_build(build_dir)
    if linux_pgo_tools is not None:
        contents = (build_dir / "Makefile").read_text()
        if (
            "-enable-name-compression=false" not in contents
            or str(linux_pgo_tools.profile_runtime) not in contents
        ):
            raise SystemExit("CPython regenerated its musl PGO runtime rules")
    verify_static_build(prefix, python_abi, target_triple, env)
    materialize_lto_archive(
        ld, target_triple, build_dir, prefix, python_abi, sdk_path, env
    )
    write_inittab_source(build_dir, prefix, python_abi)
    write_payload_sysconfig(
        prefix / "lib" / python_abi,
        prefix,
        payload_sysconfig_roots(
            (cc, ar, ranlib, ld),
            prefix,
            source_dir,
            cache_dir,
            openssl_prefix,
            zlib_xz_prefix,
            deps_prefix,
            llvm_profdata,
            profile_runtime,
            sdk_path,
            aws_cli_source,
            env,
        ),
        required=True,
    )
    build_stamp(prefix).write_text(
        stamp_text(
            source_dir,
            target_triple,
            cc_build_identity,
            pgo,
            llvm_profdata,
            profile_runtime,
            aws_cli_source,
        )
    )


def absolute_path(argument: str) -> Path:
    """Anchor paths before configure and make change directories."""
    return Path(argument).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for tool in ("cc", "ar", "ranlib", "ld"):
        parser.add_argument(f"--{tool}", required=True)
    parser.add_argument("--target-triple", required=True)
    parser.add_argument(
        "--python-version",
        required=True,
        help="CPython version being built (MAJOR.MINOR.MICRO)",
    )
    parser.add_argument("--prefix", required=True, type=absolute_path)
    parser.add_argument("--openssl-prefix", required=True, type=absolute_path)
    parser.add_argument("--zlib-xz-prefix", required=True, type=absolute_path)
    parser.add_argument("--deps-prefix", required=True, type=absolute_path)
    parser.add_argument("--cache-dir", required=True, type=absolute_path)
    parser.add_argument("--source-dir", required=True, type=absolute_path)
    parser.add_argument(
        "--pgo",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--llvm-profdata", type=absolute_path)
    parser.add_argument("--profile-runtime", type=absolute_path)
    parser.add_argument("--aws-cli-source", type=absolute_path)
    parser.add_argument("--sdk-path")
    parser.add_argument("--msvc-environ", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_cpython(
        args.cc,
        args.ar,
        args.ranlib,
        args.ld,
        args.target_triple,
        args.python_version,
        args.prefix,
        args.openssl_prefix,
        args.zlib_xz_prefix,
        args.deps_prefix,
        args.cache_dir,
        args.source_dir,
        args.pgo,
        args.llvm_profdata,
        args.profile_runtime,
        args.sdk_path,
        args.aws_cli_source,
        args.msvc_environ,
    )


if __name__ == "__main__":
    main()
