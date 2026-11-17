#!/usr/bin/env python3
"""
Generate the C glue that registers builtin Python extensions in our binary.

Emits:

  - inittab.c    — defines CPython's in-core builtin table and
                    register_builtin_extensions(), which calls
                    PyImport_AppendInittab() for each chosen extension.
  - objects.txt  — currently empty for the self-built CPython layout.
  - libs.txt     — one absolute path per line for every static archive (.a)
                    that needs to be linked.

The interpreter comes from deps/scripts/build_cpython.py, which compiles
every enabled stdlib extension into the static libpython archive
(MODULE_BUILDTYPE=static) and installs the generated Modules/config.c next to
the stdlib. We parse that config.c for the complete {name, PyInit_*} table
and filter it into our own _PyImport_Inittab. Defining the table ourselves
keeps config.o out of the link and adds register_builtin_extensions(). On
macOS the table includes _scproxy, so urllib.request reads system proxy
settings through SystemConfiguration.framework as in AWS CLI v2.

<python_root> is the self-built CPython install prefix (bin/, lib/, include/).

Usage:
    gen_inittab.py <python_root> <out.c> <objects.txt> <libs.txt>
"""

import glob
import os
import re
import sys

# Extensions to register in PyImport_Inittab. Anything not listed isn't
# accessible by name from Python (though its symbols may still be linked
# in if libpython.a references them). The set covers what awscli and
# botocore exercise during --version, sts get-caller-identity, and s3 ls.
KEEP = {
    # Required by CPython at startup.
    "_codecs",
    "_io",
    "_signal",
    "_thread",
    "_tracemalloc",
    "_weakref",
    "faulthandler",
    # No external static-archive dependencies — safe to add.
    "_abc",
    "_bisect",
    "_collections",
    "_elementtree",
    "_functools",
    "_opcode",
    "_operator",
    "_sqlite3",
    "_sre",
    "_stat",
    "_statistics",
    "_sysconfig",
    "_symtable",
    "_typing",
    "_uuid",
    "errno",
    "itertools",
    "mmap",
    "time",
    "atexit",
    "_locale",
    # urllib3's HTTPS path requires _ssl; awscli + boto exercise the rest.
    "_ssl",
    "_hashlib",
    "_md5",
    "_sha1",
    "_sha2",
    "_sha3",
    "_blake2",
    "_hmac",
    "_socket",
    "_ctypes",
    "_struct",
    "_random",
    "_pickle",
    "_json",
    "_datetime",
    "math",
    "array",
    "binascii",
    "select",
    "zlib",
    "_bz2",
    "_lzma",
    "_zstd",
    "_decimal",
    "_queue",
    "_asyncio",
    "_multibytecodec",
    "_codecs_cn",
    "_codecs_hk",
    "_codecs_iso2022",
    "_codecs_jp",
    "_codecs_kr",
    "_codecs_tw",
    "unicodedata",
    "_csv",
    "_heapq",
    "_zoneinfo",
    "pyexpat",
    # In-core entries, including the NULL initializers for sys and builtins.
    "_ast",
    "_contextvars",
    "_imp",
    "_string",
    "_tokenize",
    "_warnings",
    "builtins",
    "gc",
    "marshal",
    "sys",
}


# Native builds only: the generator runs on the interpreter's host platform.
# POSIX process support is used by subprocess and the CLI's pager. macOS
# urllib.request needs _scproxy to read system proxy settings. Windows S3
# imports multiprocessing.managers through s3transfer.compat.
POSIX_BUILTINS = {
    "fcntl",
    "grp",
    "posix",
    "pwd",
    "resource",
    "termios",
    "_posixsubprocess",
}
PLATFORM_BUILTINS = {
    "linux": POSIX_BUILTINS,
    "darwin": POSIX_BUILTINS | {"_scproxy"},
    "win32": {
        "nt",
        "msvcrt",
        "winreg",
        "_winapi",
        "_overlapped",
        "_multiprocessing",
    },
}


# These are not merely opportunistic modules. If any are absent from
# CPython's generated static inittab, the final embedded runtime cannot satisfy
# its expected AWS CLI fallback surface.
REQUIRED_RUNTIME_BUILTINS = {
    "_codecs",
    "_io",
    "_signal",
    "_thread",
    "_weakref",
    "builtins",
    "sys",
    "_bz2",
    "_ctypes",
    "_hashlib",
    "_lzma",
    "_socket",
    "_sqlite3",
    "_ssl",
    "_zstd",
    "pyexpat",
    "zlib",
}


def find_libpython_a(python_root: str) -> str:
    """Locate libpython3.x.a in the self-built CPython layout."""
    lib_dir = os.path.join(python_root, "lib")
    if os.path.isdir(lib_dir):
        for fname in sorted(os.listdir(lib_dir)):
            if fname.startswith("libpython3.") and fname.endswith(".a"):
                return os.path.join(lib_dir, fname)

        for dirname in sorted(os.listdir(lib_dir)):
            if not dirname.startswith("python3."):
                continue
            cfg_dir = os.path.join(lib_dir, dirname)
            if not os.path.isdir(cfg_dir):
                continue
            for child in sorted(os.listdir(cfg_dir)):
                if not child.startswith("config-"):
                    continue
                child_dir = os.path.join(cfg_dir, child)
                if not os.path.isdir(child_dir):
                    continue
                for fname in sorted(os.listdir(child_dir)):
                    if fname.startswith("libpython3.") and fname.endswith(
                        ".a"
                    ):
                        return os.path.join(child_dir, fname)

    raise SystemExit(f"libpython3.x.a not found near {python_root}")


def parse_config_c_inittab(python_root: str) -> list[tuple[str, str]]:
    """Read the {name, init_fn} table from the installed Modules/config.c."""
    pattern = os.path.join(
        python_root, "lib", "python3.*", "config-*", "config.c"
    )
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise SystemExit(f"generated config.c not found under {python_root}")

    # A table entry may carry a trailing comment: PC/config.c annotates its
    # "nt" line, and dropping that entry leaves the interpreter without the
    # os module's platform implementation.
    entry_re = re.compile(
        r'^\s*\{"([A-Za-z0-9_]+)",\s*([A-Za-z0-9_]+|NULL)\},?'
        r"\s*(?:/\*.*\*/)?\s*$"
    )
    entries: list[tuple[str, str]] = []
    with open(matches[0]) as f:
        for line in f:
            m = entry_re.match(line)
            if m:
                entries.append((m.group(1), m.group(2)))
    if not entries:
        raise SystemExit(f"no inittab entries parsed from {matches[0]}")
    return entries


def collect_self_built(
    python_root: str,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[str], list[str]]:
    """Inittab entries and link inputs for a self-built static CPython.

    Every extension already lives inside libpython3.x.a, so there are no
    loose objects and no bundled support archives. Re-emitting config.c's
    table keeps the real config.o out of the link and makes the table the
    single point of control over which extension objects the linker pulls in.
    """
    core_inittab_entries = parse_config_c_inittab(python_root)

    platform_builtins = PLATFORM_BUILTINS[sys.platform]
    approved = KEEP | platform_builtins
    available = {name for name, _ in core_inittab_entries}
    missing_required = sorted(
        (REQUIRED_RUNTIME_BUILTINS | platform_builtins) - available
    )
    if missing_required:
        raise SystemExit(
            "required builtin extensions missing from generated config.c: "
            + ", ".join(missing_required)
        )

    core_inittab_entries = [
        (name, init_fn)
        for name, init_fn in core_inittab_entries
        if name in approved
    ]
    lib_paths = [find_libpython_a(python_root)]

    # deps/scripts/build_cpython.py creates this directory for the self-built
    # layout.
    # Current PGO/ThinLTO builds materialize bundled support archives
    # (libmpdec, libexpat, libHacl_*) into libpython3.x.a, so this directory
    # is usually empty. Older/plain builds may still stage separate archives.
    support_dir = os.path.join(python_root, "lib", "python-support")
    if not os.path.isdir(support_dir):
        raise SystemExit(f"support archive directory missing: {support_dir}")
    lib_paths.extend(
        os.path.join(support_dir, fname)
        for fname in sorted(os.listdir(support_dir))
        if fname.endswith(".a")
    )

    return core_inittab_entries, [], [], lib_paths


def main() -> None:
    if len(sys.argv) != 5:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    python_root, out_c, out_objs, out_libs = sys.argv[1:]

    collected = collect_self_built(python_root)
    core_inittab_entries, append_inittab_entries, obj_paths, lib_paths = (
        collected
    )

    # Our own builtin extensions, statically linked separately.
    append_inittab_entries.append(("_zippy_finder", "PyInit__zippy_finder"))
    append_inittab_entries.append(("_awscrt", "PyInit__awscrt"))

    # Emit inittab.c.
    with open(out_c, "w") as f:
        f.write(
            "// Generated by deps/scripts/gen_inittab.py; "
            "do not edit.\n"
        )
        f.write("#include <Python.h>\n\n")
        for _, init_fn in core_inittab_entries + append_inittab_entries:
            if init_fn != "NULL":
                f.write(f"PyMODINIT_FUNC {init_fn}(void);\n")
        f.write("\nstruct _inittab _PyImport_Inittab[] = {\n")
        for name, init_fn in core_inittab_entries:
            f.write(f'    {{"{name}", {init_fn}}},\n')
        f.write("    {NULL, NULL},\n")
        f.write("};\n")
        f.write("\nint register_builtin_extensions(void) {\n")
        for name, init_fn in append_inittab_entries:
            f.write(
                f'    if (PyImport_AppendInittab("{name}", {init_fn}) != 0) '
                "return -1;\n"
            )
        f.write("    return 0;\n")
        f.write("}\n")

    with open(out_objs, "w") as f:
        for p in obj_paths:
            f.write(p + "\n")

    with open(out_libs, "w") as f:
        for p in lib_paths:
            f.write(p + "\n")

    entry_count = len(core_inittab_entries) + len(append_inittab_entries)
    print(f"wrote {out_c}: {entry_count} extensions", file=sys.stderr)
    print(f"wrote {out_objs}: {len(obj_paths)} objects", file=sys.stderr)
    print(f"wrote {out_libs}: {len(lib_paths)} archives", file=sys.stderr)


if __name__ == "__main__":
    main()
