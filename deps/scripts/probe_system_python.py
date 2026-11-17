#!/usr/bin/env python3
"""Validate and describe the CPython used by a system-linked build."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import sysconfig


REQUIRED_STDLIB_MODULES = (
    "_ssl",
    "_hashlib",
    "_sqlite3",
    "_ctypes",
    "zlib",
    "_bz2",
    "_lzma",
    "pyexpat",
)


def is_native_loader_path(library: Path) -> bool:
    ldconfig = shutil.which("ldconfig")
    if ldconfig is None:
        for candidate in (Path("/sbin/ldconfig"), Path("/usr/sbin/ldconfig")):
            if candidate.is_file():
                ldconfig = str(candidate)
                break
    if ldconfig is None:
        return False

    try:
        result = subprocess.run(
            [ldconfig, "-p"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    expected = library.resolve()
    for line in result.stdout.splitlines():
        _, separator, resolved = line.partition(" => ")
        if separator and Path(resolved).resolve() == expected:
            return True
    return False


def fail(message: str) -> None:
    raise SystemExit(f"system Python validation failed: {message}")


def isolated_imports(
    modules: tuple[str, ...], *, platlib: str | None = None
) -> None:
    setup = ""
    if platlib is not None:
        setup = f"import sys; sys.path.append({platlib!r}); "
    command = setup + "; ".join(f"import {module}" for module in modules)
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        detail = (
            result.stderr.strip().splitlines()[-1]
            if result.stderr.strip()
            else "import failed"
        )
        fail(
            f"required isolated imports failed ({', '.join(modules)}): {detail}"
        )


def system_payload_imports() -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-c", "import awscli, awscrt, awscrt.io"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        detail = (
            result.stderr.strip().splitlines()[-1]
            if result.stderr.strip()
            else "import failed"
        )
        fail(
            f"system payload requires importable awscli and awscrt packages: {detail}"
        )


def embedded_payload_awscrt(platlib: str, expected_version: str) -> None:
    command = (
        f"import sys; sys.path.append({platlib!r}); import awscrt, awscrt.io; "
        "print(awscrt.__version__)"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        detail = (
            result.stderr.strip().splitlines()[-1]
            if result.stderr.strip()
            else "import failed"
        )
        fail(f"embedded payload requires awscrt in system platlib: {detail}")
    version = result.stdout.strip()
    if version != expected_version:
        fail(
            f"embedded payload requires awscrt {expected_version}, "
            f"found {version or 'unknown'}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--payload-mode", choices=("embedded", "system"), required=True
    )
    parser.add_argument("--expected-awscrt-version", required=True)
    # A bundled awscrt is compiled into the binary and packed with the
    # payload, so the interpreter's own awscrt, if any, is never imported.
    parser.add_argument(
        "--awscrt", choices=("platlib", "bundled"), default="platlib"
    )
    args = parser.parse_args()

    python_abi = f"python{sys.version_info.major}.{sys.version_info.minor}"

    if sys.implementation.name != "cpython":
        fail(f"expected CPython, found {sys.implementation.name}")
    if sys.version_info < (3, 9):
        fail(f"expected CPython 3.9 or newer, found {sys.version.split()[0]}")
    if sysconfig.get_config_var("Py_ENABLE_SHARED") != 1:
        fail("Py_ENABLE_SHARED is not 1")

    include = Path(sysconfig.get_path("include"))
    if not (include / "Python.h").is_file():
        fail(f"Python.h is missing from {include}")

    ldlibrary = sysconfig.get_config_var("LDLIBRARY")
    libdir = sysconfig.get_config_var("LIBDIR")
    if not isinstance(ldlibrary, str) or not ldlibrary.startswith(
        f"lib{python_abi}.so"
    ):
        fail(f"expected LDLIBRARY=lib{python_abi}.so*, found {ldlibrary!r}")
    if not isinstance(libdir, str) or not (Path(libdir) / ldlibrary).exists():
        fail(f"{ldlibrary!r} is not present in LIBDIR {libdir!r}")

    platlib = sysconfig.get_path("platlib")
    isolated_imports(REQUIRED_STDLIB_MODULES)
    if args.payload_mode == "embedded":
        if args.awscrt == "platlib":
            embedded_payload_awscrt(platlib, args.expected_awscrt_version)
    elif args.awscrt == "bundled":
        fail("a bundled awscrt requires the embedded payload")
    else:
        system_payload_imports()

    magic = importlib.util.MAGIC_NUMBER
    link_libraries: list[str] = []
    for variable in ("LIBS", "SYSLIBS"):
        for flag in shlex.split(sysconfig.get_config_var(variable) or ""):
            if flag.startswith("-l") and flag[2:] and flag[2:] != python_abi:
                library = flag[2:]
                if library not in link_libraries:
                    link_libraries.append(library)
    print(f"abi={python_abi}")
    print(f"include={include}")
    print(f"platlib={platlib}")
    print(f"libdir={libdir}")
    print(
        "libdir_is_loader_path="
        f"{'true' if is_native_loader_path(Path(libdir) / ldlibrary) else 'false'}"
    )
    print(f"ldlibrary={ldlibrary}")
    print(f"magic={int.from_bytes(magic, 'little')}")
    print(f"link_libraries={','.join(link_libraries)}")


if __name__ == "__main__":
    main()
