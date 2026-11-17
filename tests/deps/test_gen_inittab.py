import re
import subprocess
import sys
from pathlib import Path

import pytest

# Deliberately independent of the generator's policy: additions need review.
COMMON = [
    "_abc",
    "_ast",
    "_asyncio",
    "_bisect",
    "_blake2",
    "_bz2",
    "_codecs",
    "_codecs_cn",
    "_codecs_hk",
    "_codecs_iso2022",
    "_codecs_jp",
    "_codecs_kr",
    "_codecs_tw",
    "_collections",
    "_contextvars",
    "_csv",
    "_ctypes",
    "_datetime",
    "_decimal",
    "_elementtree",
    "_functools",
    "_hashlib",
    "_heapq",
    "_hmac",
    "_imp",
    "_io",
    "_json",
    "_locale",
    "_lzma",
    "_md5",
    "_multibytecodec",
    "_opcode",
    "_operator",
    "_pickle",
    "_queue",
    "_random",
    "_sha1",
    "_sha2",
    "_sha3",
    "_signal",
    "_socket",
    "_sqlite3",
    "_sre",
    "_ssl",
    "_stat",
    "_statistics",
    "_string",
    "_struct",
    "_symtable",
    "_sysconfig",
    "_thread",
    "_tokenize",
    "_tracemalloc",
    "_typing",
    "_uuid",
    "_warnings",
    "_weakref",
    "_zoneinfo",
    "_zstd",
    "array",
    "atexit",
    "binascii",
    "builtins",
    "errno",
    "faulthandler",
    "gc",
    "itertools",
    "marshal",
    "math",
    "mmap",
    "pyexpat",
    "select",
    "sys",
    "time",
    "unicodedata",
    "zlib",
]
PLATFORM = {
    "linux": "fcntl grp posix pwd resource termios _posixsubprocess",
    "darwin": "fcntl grp posix pwd resource termios _posixsubprocess _scproxy",
    "win32": "_winapi msvcrt nt winreg _overlapped _multiprocessing",
}
UNAPPROVED = [
    "_interpchannels",
    "_interpqueues",
    "_interpreters",
    "_lsprof",
    "_remote_debugging",
    "_suggestions",
    "_types",
    "cmath",
    "_future_extension",
]


def generate(
    tmp_path: Path, names: set[str]
) -> subprocess.CompletedProcess[str]:
    config_dir = tmp_path / "lib/python3.14/config-test"
    config_dir.mkdir(parents=True)
    (tmp_path / "lib/python-support").mkdir()
    (tmp_path / "lib/libpython3.14.a").touch()
    (config_dir / "config.c").write_text(
        "\n".join(
            f'    {{"{name}", '
            + ("NULL" if name in {"sys", "builtins"} else f"PyInit_{name}")
            + "}, /* builtin */"
            for name in sorted(names)
        )
    )
    script = (
        Path(__file__).resolve().parents[2]
        / "deps/scripts/gen_inittab.py"
    )
    return subprocess.run(
        [
            sys.executable,
            str(script),
            str(tmp_path),
            str(tmp_path / "inittab.c"),
            str(tmp_path / "objects.txt"),
            str(tmp_path / "libs.txt"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_generated_inventory_excludes_unapproved_and_foreign_modules(
    tmp_path: Path,
) -> None:
    available = set(COMMON + UNAPPROVED)
    for modules in PLATFORM.values():
        available.update(modules.split())
    result = generate(tmp_path, available)
    assert result.returncode == 0, result.stderr
    source = (tmp_path / "inittab.c").read_text()
    emitted = re.findall(r'\{"([^"]+)",', source)
    assert sorted(emitted) == sorted(COMMON + PLATFORM[sys.platform].split())
    assert '{"sys", NULL}' in source
    assert 'PyImport_AppendInittab("_awscrt", PyInit__awscrt)' in source
    assert (
        'PyImport_AppendInittab("_zippy_finder", PyInit__zippy_finder)'
        in source
    )
    for name in UNAPPROVED:
        assert f"PyInit_{name}" not in source


@pytest.mark.parametrize("missing", ["_ssl", "_io", "sys", "platform"])
def test_missing_required_builtin_fails(tmp_path: Path, missing: str) -> None:
    if missing == "platform":
        missing = PLATFORM[sys.platform].split()[0]
    available = set(COMMON + PLATFORM[sys.platform].split()) - {missing}
    result = generate(tmp_path, available)
    assert result.returncode != 0
    assert "required builtin extensions missing" in result.stderr
    assert missing in result.stderr
    assert not (tmp_path / "inittab.c").exists()
