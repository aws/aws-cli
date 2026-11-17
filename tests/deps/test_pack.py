import marshal
import subprocess
import sys
from pathlib import Path
from types import CodeType

import pytest

try:
    from compression import zstd
except ImportError:
    zstd = None

from payload import read_payload_entries


def test_help_resources_round_trip_with_available_compression(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    resources = {
        "example.rst": b"Example\n=======\n\n" + b"Help text.\n" * 100,
        "settings.json": b'{"region": "us-west-2"}',
    }
    for name, data in resources.items():
        (source / name).write_bytes(data)
    blob = tmp_path / "payload.blob"
    packer = Path(__file__).resolve().parents[2] / "deps/scripts/pack.py"
    subprocess.run(
        [sys.executable, str(packer), str(blob), f"{source}:"],
        check=True,
        capture_output=True,
    )
    rst_flags = 4 | 8 if zstd is not None else 4
    assert read_payload_entries(blob) == {
        "example.rst": (rst_flags, resources["example.rst"]),
        "settings.json": (4, resources["settings.json"]),
    }


@pytest.mark.parametrize("prefix", ["", "awscli", "vendor.package"])
def test_bytecode_is_independent_of_source_root(
    tmp_path: Path, prefix: str
) -> None:
    packer = Path(__file__).resolve().parents[2] / "deps/scripts/pack.py"
    blobs: list[bytes] = []
    for location in ("checkout", "different cache/source"):
        source = tmp_path / location
        (source / "nested").mkdir(parents=True)
        (source / "nested/__init__.py").write_text(
            "def fail():\n    raise ValueError('example')\n"
        )
        blob = source / "payload.blob"
        subprocess.run(
            [sys.executable, str(packer), str(blob), f"{source}:{prefix}"],
            check=True,
            capture_output=True,
        )
        entries = read_payload_entries(blob)
        module = f"{prefix}.nested" if prefix else "nested"
        code = marshal.loads(entries[module][1])
        filename = "nested/__init__.py"
        if prefix:
            filename = f"{prefix.replace('.', '/')}/{filename}"
        assert code.co_filename == filename
        nested = [c for c in code.co_consts if isinstance(c, CodeType)]
        assert len(nested) == 1
        assert nested[0].co_filename == filename
        blobs.append(blob.read_bytes())
    assert blobs[0] == blobs[1]


def test_wheel_records_exclude_unbundled_script_hashes(tmp_path: Path) -> None:
    packer = Path(__file__).resolve().parents[2] / "deps/scripts/pack.py"
    outputs: list[bytes] = []
    retained = (
        '"example/data,one.json",sha256=unchanged,2\r\n'
        "example-1.dist-info/RECORD,,\r\n"
    )
    for name in ("first", "relocated"):
        source = tmp_path / name
        metadata = source / "example-1.dist-info"
        metadata.mkdir(parents=True)
        # pip hashes generated console scripts with a venv-specific shebang.
        # Those scripts are outside the root and never enter this payload.
        (metadata / "RECORD").write_bytes(
            (
                f"../../../bin/example,sha256={name}-script-hash,80\r\n"
                + retained
            ).encode()
        )
        blob = source / "payload.blob"
        subprocess.run(
            [sys.executable, str(packer), str(blob), f"{source}:"],
            check=True,
            capture_output=True,
        )
        entries = read_payload_entries(blob)
        assert entries["example-1.dist-info/RECORD"] == (4, retained.encode())
        outputs.append(blob.read_bytes())
    assert outputs[0] == outputs[1]
