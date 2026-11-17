"""Relocation independence of the static fallback payload and awscrt objects."""

import importlib.util
import json
import marshal
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from payload import read_payload_entries

SCRIPTS = Path(__file__).resolve().parents[2] / "deps/scripts"


@pytest.fixture
def driver(tmp_path: Path) -> ModuleType:
    staged = tmp_path / "driver"
    staged.mkdir()
    for source in SCRIPTS.iterdir():
        if source.is_file():
            shutil.copy2(source, staged / source.name)
    sys.path.insert(0, str(staged))
    try:
        spec = importlib.util.spec_from_file_location(
            "packing_driver", staged / "prepare_python_fallback.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(staged))
    return module


def stdlib_dir(prefix: Path) -> Path:
    if sys.platform == "win32":
        return prefix / "bin" / "Lib"
    return prefix / "lib" / "python3.14"


def test_pack_blob_prefers_payload_sysconfig_without_mutating_stdlib(
    driver: ModuleType, tmp_path: Path
) -> None:
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)],
        check=True,
        capture_output=True,
    )
    venv_python = (
        venv / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else venv / "bin" / "python"
    )
    module_name = "_sysconfigdata__linux_"
    resource_name = "_sysconfig_vars__linux_.json"
    blobs: list[bytes] = []
    for location in ("install", "relocated install"):
        prefix = tmp_path / location
        stdlib = stdlib_dir(prefix)
        copies = prefix / "lib/payload-sysconfig"
        stubs = prefix / "stubs"
        aws_cli = prefix / "aws-cli"
        awscrt = prefix / "crt-python"
        autocomplete_index = prefix / "autocomplete-index"
        for directory in (
            stdlib,
            copies,
            stubs,
            aws_cli / "awscli",
            awscrt / "awscrt",
            autocomplete_index,
        ):
            directory.mkdir(parents=True)
        original = f"build_time_vars = {{'prefix': {str(prefix)!r}}}\n"
        (stdlib / f"{module_name}.py").write_text(original)
        (stdlib / resource_name).write_text(
            json.dumps({"prefix": str(prefix)})
        )
        payload_source = (
            "build_time_vars = {'prefix': '/aws-cli-python', "
            "'SIZEOF_VOID_P': 8}\n"
        )
        (copies / f"{module_name}.py").write_text(payload_source)
        (copies / resource_name).write_text('{"prefix": "/aws-cli-python"}')
        blob = prefix / "payload.blob"
        driver.pack_blob(
            Path(sys.executable),
            SCRIPTS / "pack.py",
            prefix,
            "python3.14",
            aws_cli,
            awscrt,
            venv_python,
            stubs,
            autocomplete_index,
            blob,
            dict(os.environ),
        )
        entries = read_payload_entries(blob)
        assert marshal.loads(entries[module_name][1]) == compile(
            payload_source,
            f"{module_name}.py",
            "exec",
            dont_inherit=True,
            optimize=2,
        )
        assert json.loads(entries[resource_name][1]) == {
            "prefix": "/aws-cli-python"
        }
        assert (stdlib / f"{module_name}.py").read_text() == original
        assert json.loads((stdlib / resource_name).read_text()) == {
            "prefix": str(prefix)
        }
        blobs.append(blob.read_bytes())
    assert blobs[0] == blobs[1]


def test_pack_blob_rejects_unprepared_cpython_prefix(
    driver: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(SystemExit, match="missing CPython payload sysconfig"):
        driver.pack_blob(
            Path(sys.executable),
            tmp_path / "pack.py",
            tmp_path,
            "python3.14",
            tmp_path,
            tmp_path,
            Path(sys.executable),
            tmp_path,
            tmp_path / "autocomplete-index",
            tmp_path / "blob",
            dict(os.environ),
        )


def test_awscrt_compilation_normalizes_source_filenames(
    driver: ModuleType, tmp_path: Path
) -> None:
    if sys.platform != "linux":
        pytest.skip("native Linux compiler fixture")
    # The harness supplies the managed toolchain's compiler; a run that
    # omits it must fail rather than lose the filename assertion.
    compiler = os.environ.get("AWS_NATIVE_TEST_CC")
    assert compiler, "AWS_NATIVE_TEST_CC must name the managed compiler"
    source = tmp_path / "package store" / "source"
    source.mkdir(parents=True)
    (source / "module.c").write_text('const char *filename = __FILE__;\n')
    objects = driver.compile_awscrt_sources(
        compiler,
        "x86_64-unknown-linux-musl",
        tmp_path / "python-include",
        tmp_path / "crt-include",
        source.parent,
        tmp_path / "objects",
        None,
        dict(os.environ),
    )
    assert len(objects) == 1
    data = objects[0].read_bytes()
    assert b"aws-crt-python/source/module.c\0" in data
    assert str(tmp_path).encode() not in data
