import importlib.util
import json
import os
import pprint
import shlex
import subprocess
import sys
import sysconfig
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def producer() -> ModuleType:
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "payload_sysconfig", root / "deps/scripts/payload_sysconfig.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_payload_copies_are_relocation_invariant_and_leave_install_intact(
    producer: ModuleType, tmp_path: Path
) -> None:
    outputs: list[dict[str, bytes]] = []
    for location in ("first-checkout", "relocated checkout's tree"):
        tree = tmp_path / location
        cache = tree / "cache"
        prefix = cache / "install"
        source = cache / "packages/cpython"
        crt = tree / "crt"
        roots = [
            (cache, "/aws-cli-build/cpython-cache"),
            (cache / "build", "/aws-cli-build/cpython-build"),
            (prefix, "/aws-cli-python"),
            (source, "/aws-cli-build/cpython"),
            (crt, "/aws-cli-build/crt"),
        ]
        # Fields seen in real CPython 3.14 generated metadata: bare roots,
        # paths embedded in flags, shell-quoted CONFIG_ARGS, and snapshots
        # with runtime-computed prefixes and userbase.
        values = {
            "prefix": str(prefix),
            "exec_prefix": str(prefix),
            "abs_srcdir": str(source),
            "abs_builddir": str(cache / "build"),
            "LIBPL": f"{prefix}/lib/python3.14/config-3.14",
            "CONFIG_ARGS": shlex.join(
                [f"--prefix={prefix}", f"ZLIB_CFLAGS=-I{crt}/include"]
            ),
            "PY_CFLAGS_NODIST": f"-fprofile-instr-use={cache}/build/code.prof",
            "CPPFLAGS": f"-I{source}/Include -I{crt}/include",
            "CFLAGS": shlex.join(
                [f"-ffile-prefix-map={source}/=cpython/", "-O3"]
            ),
            "userbase": str(tree / "home/.local"),
            "TZPATH": "/usr/share/zoneinfo:/etc/zoneinfo",
            "SOABI": "cpython-314-x86_64-linux-gnu",
            "Py_GIL_DISABLED": 0,
            "SIZEOF_VOID_P": 8,
            "EMPTY": "",
        }
        stdlib = prefix / "lib/python3.14"
        stdlib.mkdir(parents=True)
        original = {
            "_sysconfigdata__linux_.py": (
                f"build_time_vars = {pprint.pformat(values)}\n"
            ).encode(),
            "_sysconfig_vars__linux_.json": json.dumps(values).encode(),
            "build-details.json": json.dumps(
                {
                    "schema_version": "1.0",
                    "libpython": {"static": f"{prefix}/lib/libpython3.14.a"},
                    "c_api": {"headers": f"{prefix}/include/python3.14"},
                }
            ).encode(),
        }
        for name, data in original.items():
            (stdlib / name).write_bytes(data)
        producer.write_payload_sysconfig(stdlib, prefix, roots, required=True)
        copies = prefix / "lib/payload-sysconfig"
        result = {path.name: path.read_bytes() for path in copies.iterdir()}
        assert {path.name: path.read_bytes() for path in stdlib.iterdir()} == (
            original
        )
        normalized = json.loads(result["_sysconfig_vars__linux_.json"])
        assert (
            producer.read_python_vars(copies / "_sysconfigdata__linux_.py")
            == normalized
        )
        assert normalized.keys() == values.keys()
        assert normalized["LIBPL"] == (
            "/aws-cli-python/lib/python3.14/config-3.14"
        )
        assert normalized["abs_srcdir"] == "/aws-cli-build/cpython"
        assert normalized["abs_builddir"] == "/aws-cli-build/cpython-build"
        details = json.loads(result["build-details.json"])
        assert details["schema_version"] == "1.0"
        assert details["libpython"]["static"] == (
            "/aws-cli-python/lib/libpython3.14.a"
        )
        for key in (
            "TZPATH",
            "SOABI",
            "Py_GIL_DISABLED",
            "SIZEOF_VOID_P",
            "EMPTY",
        ):
            assert normalized[key] == values[key]
        assert all(str(tree).encode() not in data for data in result.values())
        outputs.append(result)
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize("root", ["/build/python", r"C:\build\python"])
def test_normalization_does_not_match_siblings_or_unrelated_paths(
    producer: ModuleType, root: str
) -> None:
    values = {
        "root": root,
        "flags": f"-I{root}/include -L{root}/lib --prefix={root}",
        "sibling": f"{root}-other/include",
        "substring": f"/unrelated{root}/include",
        "identifier": f"identifier{root}/include",
        "embedded_flag": f"identifier-I{root}/include",
        root: "key is not a value",
        "number": 1,
    }
    result = producer.normalize_vars(values, [(Path(root), "/stable")])
    assert result["root"] == "/stable"
    assert (
        result["flags"] == "-I/stable/include -L/stable/lib --prefix=/stable"
    )
    for key in (
        "sibling",
        "substring",
        "identifier",
        "embedded_flag",
        root,
        "number",
    ):
        assert result[key] == values[key]


def test_missing_posix_metadata_fails_but_windows_publishes_empty_root(
    producer: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="missing installed sysconfig"):
        producer.write_payload_sysconfig(tmp_path, tmp_path, [], required=True)
    producer.write_payload_sysconfig(tmp_path, tmp_path, [], required=False)
    assert list((tmp_path / "lib/payload-sysconfig").iterdir()) == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX sysconfig data import")
def test_sysconfig_runtime_uses_payload_vars_and_recomputes_install_paths(
    producer: ModuleType, tmp_path: Path
) -> None:
    values = dict(sysconfig.get_config_vars())
    values |= {
        "prefix": str(tmp_path / "packing-install"),
        "exec_prefix": str(tmp_path / "packing-install"),
        "CC": f"{tmp_path}/tools/cc -target x86_64-linux-musl",
    }
    stdlib = tmp_path / "stdlib"
    stdlib.mkdir()
    name = "_sysconfigdata__payload"
    (stdlib / f"{name}.py").write_text(
        f"build_time_vars = {pprint.pformat(values)}\n"
    )
    (stdlib / "_sysconfig_vars__payload.json").write_text(json.dumps(values))
    producer.write_payload_sysconfig(
        stdlib,
        tmp_path,
        [
            (tmp_path / "packing-install", "/aws-cli-python"),
            (tmp_path / "tools", "/aws-cli-build/toolchain"),
        ],
        required=True,
    )
    payload_dir = str(tmp_path / "lib/payload-sysconfig")
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-B",
            "-c",
            (
                "import sys\n"
                f"sys.path.insert(0, {payload_dir!r})\n"
                "import sysconfig\n"
                "assert sysconfig.get_config_var('CC').startswith("
                "'/aws-cli-build/toolchain/cc')\n"
                "assert sysconfig.get_config_var('prefix') == sys.prefix\n"
                "assert sysconfig.get_config_var('SIZEOF_VOID_P') == "
                f"{values['SIZEOF_VOID_P']!r}\n"
                "assert sysconfig.get_path('purelib').startswith(sys.prefix)\n"
                "assert sysconfig.get_platform()\n"
                "assert not sysconfig.is_python_build()\n"
                "sys.prefix = sys.exec_prefix = '/runtime/venv'\n"
                "assert sysconfig.get_config_var('prefix') == "
                "'/runtime/venv'\n"
                "assert sysconfig.get_path('purelib').startswith("
                "'/runtime/venv')\n"
            ),
        ],
        env=os.environ | {"_PYTHON_SYSCONFIGDATA_NAME": name},
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert not result.stdout
