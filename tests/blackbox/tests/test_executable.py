"""The built executable's own properties: not sparse, linked as its build
says, and, for the static build, self-contained and carrying the pinned
runtime.

These assert what only this repository's binary promises, so they are
`native_only`: another AWS CLI ships another layout and interpreter. A
system build (run.py's `--link-mode system`) loads the system's libraries
and runs the system's interpreter, so it is checked for those instead.
"""

import ctypes
import os
import struct
import subprocess
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer

from credhelpers import credential_runtime, run_command
from harness_plugin import BUILD

pytestmark = [pytest.mark.asyncio, pytest.mark.native_only]

STATIC_BUILD: Final = BUILD.link_mode == "static"
# The checkout the binary was built in, which no search path may name.
REPOSITORY: Final = Path(__file__).resolve().parents[3]

# Section alignment leaves some padding unbacked; a payload-sized hole is a
# build that wrote the payload sparsely.
HOLE_BYTES_MAX: Final = 2 * 1024 * 1024

# The ELF64 type of a position-independent executable, and program and
# dynamic entry tags (System V gABI).
ET_DYN: Final = 3
PT_LOAD: Final = 1
PT_DYNAMIC: Final = 2
PT_INTERP: Final = 3
DT_NULL: Final = 0
DT_NEEDED: Final = 1
DT_STRTAB: Final = 5
DT_RPATH: Final = 15
DT_RUNPATH: Final = 29
# A Windows import naming one of these is a runtime the build must embed.
WINDOWS_EMBEDDED_RUNTIMES: Final = (
    "python",
    "aws",
    "ssl",
    "crypto",
    "vcruntime",
    "msvcp",
)
# The only libraries a macOS build may name.
MACOS_SYSTEM_PREFIXES: Final = ("/usr/lib/", "/System/Library/Frameworks/")

# A CLI plugin that checks the embedded interpreter's pinned libraries and
# builtin policy before any command runs, then exits.
RUNTIME_PROBE: Final = '''\
import bz2
import ctypes
import importlib
import lzma
import sqlite3
import ssl
import sys
import zlib

from compression import zstd


def awscli_initialize(event_hooks):
    event_hooks.register("top-level-args-parsed", probe)


def probe(**kwargs):
    assert sys.version_info[:3] == (3, 14, 8), sys.version
    assert not sys.is_remote_debug_enabled()
    assert not hasattr(sys, "remote_exec")
    for name in (
        "_remote_debugging",
        "_interpreters",
        "_interpchannels",
        "_interpqueues",
        "_lsprof",
        "_suggestions",
        "_types",
        "cmath",
    ):
        assert name not in sys.builtin_module_names, name
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as error:
            assert error.name == name, error
        else:
            raise AssertionError(f"unapproved builtin is importable: {name}")
    assert ssl.OPENSSL_VERSION.split()[1] == "3.5.9", ssl.OPENSSL_VERSION
    assert sqlite3.sqlite_version == "3.53.4", sqlite3.sqlite_version
    assert zlib.ZLIB_RUNTIME_VERSION == "1.3.2", zlib.ZLIB_RUNTIME_VERSION
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    assert context.get_ciphers()
    data = bytes(range(256)) * 17 + b"runtime dependency probe"
    for codec in (zlib, lzma, bz2, zstd):
        assert codec.decompress(codec.compress(data)) == data
    with sqlite3.connect(":memory:") as db:
        db.execute("create table sample (value integer)")
        db.executemany("insert into sample values (?)", [(7,), (19,)])
        assert db.execute("select sum(value) from sample").fetchone() == (26,)
    if sys.platform == "linux":
        # The static musl payload ships a ctypes stub.
        try:
            ctypes.CDLL(None)
        except OSError as error:
            assert str(error) == "ctypes dynamic loading is not available"
        else:
            raise AssertionError("static ctypes unexpectedly loaded a DLL")
    else:
        # A round trip through ffi_call and a closure, with distinct
        # arguments, catches ABI marshalling errors.
        callback_type = ctypes.CFUNCTYPE(
            ctypes.c_double, ctypes.c_int, ctypes.c_double
        )
        callback = callback_type(lambda count, value: count * 2 + value)
        assert callback(7, 0.25) == 14.25
    print("runtime dependencies: versions and operations passed")
    sys.exit(0)
'''


@pytest_asyncio.fixture
async def offline_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test")
        yield server, env


def allocated_bytes(path: Path) -> int:
    """The storage the filesystem allocated for `path`."""
    if sys.platform == "win32":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCompressedFileSizeW.restype = ctypes.c_uint32
        high = ctypes.c_uint32()
        low = kernel32.GetCompressedFileSizeW(str(path), ctypes.byref(high))
        if low == 0xFFFFFFFF and ctypes.get_last_error() != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        return (high.value << 32) | low
    return os.stat(path).st_blocks * 512


@dataclass(frozen=True)
class ElfLinkage:
    """What an ELF executable asks of the loader: whether it names one, the
    libraries it needs, and its RPATH and RUNPATH search paths."""

    interpreter: bool
    needed: tuple[str, ...]
    search_paths: tuple[str, ...]


def elf_linkage(image: bytes) -> ElfLinkage:
    """The linkage of a 64-bit little-endian ELF image."""
    assert image[:4] == b"\x7fELF", "not an ELF image"
    assert image[4:6] == b"\x02\x01", "not a 64-bit little-endian ELF image"
    phoff, = struct.unpack_from("<Q", image, 0x20)
    phentsize, phnum = struct.unpack_from("<HH", image, 0x36)
    interpreter = False
    # Each loaded segment's address, file offset, and size in the file.
    segments: list[tuple[int, int, int]] = []
    entries: list[tuple[int, int]] = []
    for index in range(phnum):
        header = phoff + index * phentsize
        kind, = struct.unpack_from("<I", image, header)
        offset, address = struct.unpack_from("<QQ", image, header + 0x08)
        size, = struct.unpack_from("<Q", image, header + 0x20)
        if kind == PT_LOAD:
            segments.append((address, offset, size))
        elif kind == PT_INTERP:
            interpreter = True
        elif kind == PT_DYNAMIC:
            for entry in range(offset, offset + size, 16):
                tag, value = struct.unpack_from("<qQ", image, entry)
                if tag == DT_NULL:
                    break
                entries.append((tag, value))

    def strings(*tags: int) -> tuple[str, ...]:
        offsets = [value for tag, value in entries if tag in tags]
        if not offsets:
            return ()
        table = next(value for tag, value in entries if tag == DT_STRTAB)
        start = next(
            offset + table - address
            for address, offset, size in segments
            if address <= table < address + size
        )
        return tuple(
            image[start + name:image.index(b"\0", start + name)].decode()
            for name in offsets
        )

    return ElfLinkage(
        interpreter, strings(DT_NEEDED), strings(DT_RPATH, DT_RUNPATH)
    )


def pe_imports(image: bytes) -> list[str]:
    """The DLLs a PE32+ image imports, directly or delay-loaded."""
    pe, = struct.unpack_from("<I", image, 0x3C)
    assert image[pe:pe + 4] == b"PE\0\0", "not a PE image"
    sections, optional_size = struct.unpack_from("<H12xH", image, pe + 6)
    optional = pe + 24
    assert struct.unpack_from("<H", image, optional)[0] == 0x20B, "not PE32+"
    directories = optional + 112
    table = optional + optional_size
    # Each section header's virtual size and address, and where its raw
    # data starts in the file.
    mapping = [
        struct.unpack_from("<8xII4xI", image, table + index * 40)
        for index in range(sections)
    ]

    def offset(rva: int) -> int:
        for size, address, raw_offset in mapping:
            if address <= rva < address + size:
                return raw_offset + rva - address
        raise AssertionError(f"RVA {rva:#x} is in no section")

    def name(rva: int) -> str:
        start = offset(rva)
        return image[start:image.index(b"\0", start)].decode("ascii")

    names = []
    # The import directory's descriptors are 20 bytes, naming the DLL at
    # +12; the delay-load directory's are 32, naming it at +4.
    for directory, stride, field in ((1, 20, 12), (13, 32, 4)):
        rva, size = struct.unpack_from("<II", image, directories + directory * 8)
        if rva == 0 or size == 0:
            continue
        entry = offset(rva)
        while True:
            descriptor = image[entry:entry + stride]
            if not any(descriptor):
                break
            names.append(name(struct.unpack_from("<I", descriptor, field)[0]))
            entry += stride
    return names


async def test_the_executable_is_not_sparse(aws_cli: str) -> None:
    path = Path(aws_cli)
    holes = path.stat().st_size - allocated_bytes(path)
    assert holes <= HOLE_BYTES_MAX, (
        f"{holes} bytes of {path} are zero-filled holes"
    )


@pytest.mark.skipif(sys.platform != "linux", reason="an ELF check")
@pytest.mark.skipif(not STATIC_BUILD, reason="a system build uses the loader")
async def test_the_linux_executable_is_a_self_contained_static_pie(
    aws_cli: str,
) -> None:
    image = Path(aws_cli).read_bytes()
    linkage = elf_linkage(image)
    assert not linkage.interpreter, "the executable names an interpreter"
    assert not linkage.needed, f"the executable needs {linkage.needed}"
    assert not linkage.search_paths, (
        f"the executable searches {linkage.search_paths}"
    )
    # A static PIE, so every run loads at a random address.
    assert struct.unpack_from("<H", image, 0x10)[0] == ET_DYN, (
        "the executable loads at a fixed address"
    )


# A system build needs the system's libpython of the ABI it was built
# against, and either the shared CRT's libraries or, with the CRT linked
# statically, libcrypto and no CRT or s2n library at all. No search path
# may lead the loader to /usr/lib or the checkout instead of the system's
# own search.
@pytest.mark.skipif(sys.platform != "linux", reason="an ELF check")
@pytest.mark.skipif(STATIC_BUILD, reason="the static build needs no loader")
async def test_the_linux_system_executable_needs_the_system_libraries(
    aws_cli: str,
) -> None:
    linkage = elf_linkage(Path(aws_cli).read_bytes())
    assert linkage.interpreter, "a system build must use the loader"
    required = [f"lib{BUILD.python_abi}.so"]
    if BUILD.crt_link == "static":
        required.append("libcrypto.so")
        crt = [
            name for name in linkage.needed
            if name.startswith(("libaws-", "libs2n"))
        ]
        assert not crt, f"a static CRT must not need {crt}"
    else:
        required += ["libaws-c-s3.so", "libaws-c-common.so"]
    for library in required:
        assert any(library in name for name in linkage.needed), (
            f"the executable needs no {library}: {linkage.needed}"
        )
    for forbidden in ("/usr/lib", str(REPOSITORY)):
        assert not any(forbidden in path for path in linkage.search_paths), (
            f"the executable searches {linkage.search_paths}"
        )


@pytest.mark.skipif(sys.platform != "darwin", reason="a Mach-O check")
async def test_the_macos_executable_links_only_system_libraries(
    aws_cli: str,
) -> None:
    listing = subprocess.run(
        ["/usr/bin/otool", "-L", aws_cli],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for line in listing.splitlines()[1:]:
        library = line.split()[0]
        assert library.startswith(MACOS_SYSTEM_PREFIXES), library


@pytest.mark.skipif(sys.platform != "win32", reason="a PE check")
async def test_the_windows_executable_imports_no_runtime_it_embeds(
    aws_cli: str,
) -> None:
    imports = pe_imports(Path(aws_cli).read_bytes())
    assert imports, "the executable imports nothing"
    for library in imports:
        lowered = library.lower()
        assert not any(name in lowered for name in WINDOWS_EMBEDDED_RUNTIMES), (
            library
        )


# A system build runs the system's interpreter and libraries, whose
# versions are the system's.
@pytest.mark.skipif(
    not STATIC_BUILD, reason="a system build runs the system's interpreter"
)
async def test_the_embedded_interpreter_has_its_pinned_libraries(
    aws_cli: str,
    offline_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = offline_runtime
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "runtime_probe.py").write_text(RUNTIME_PROBE, encoding="utf-8")
    Path(env["AWS_CONFIG_FILE"]).write_text(
        "[plugins]\n"
        f"cli_legacy_plugin_path = {plugins}\n"
        "runtime_probe = runtime_probe\n",
        encoding="utf-8",
    )
    result = await run_command(
        [aws_cli, "iam", "list-users", "--generate-cli-skeleton"],
        env,
        cwd=tmp_path,
    )
    assert result == (
        b"runtime dependencies: versions and operations passed\n",
        b"",
        0,
    ), result[1].decode()
    assert not server.requests
