"""Reject mixed interpreter identities and stale system payload artifacts."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def artifacts(tmp_path: Path) -> Path:
    (tmp_path / "payload").write_bytes(b"payload")
    (tmp_path / "runtime").write_bytes(b"runtime")
    metadata = {
        "implementation": sys.implementation.name,
        "cache_tag": sys.implementation.cache_tag,
        "magic_number": importlib.util.MAGIC_NUMBER.hex(),
        "payload_sha256": hashlib.sha256(b"payload").hexdigest(),
        "runtime_sha256": hashlib.sha256(b"runtime").hexdigest(),
    }
    (tmp_path / "metadata").write_text(json.dumps(metadata))
    return tmp_path


def validate(artifacts: Path, magic: int) -> subprocess.CompletedProcess[str]:
    validator = (
        Path(__file__).resolve().parents[2]
        / "deps/scripts/validate_bytecode_metadata.py"
    )
    return subprocess.run(
        [
            sys.executable, "-E", "-s", "-B", str(validator),
            "--payload", str(artifacts / "payload"),
            "--runtime", str(artifacts / "runtime"),
            "--metadata", str(artifacts / "metadata"),
            "--expected-magic", str(magic),
            "--stamp", str(artifacts / "stamp"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_consistent_artifacts_write_validation_stamp(artifacts: Path) -> None:
    result = validate(
        artifacts, int.from_bytes(importlib.util.MAGIC_NUMBER, "little"),
    )
    assert result.returncode == 0, result.stderr
    assert (artifacts / "stamp").read_text() == "validated\n"


@pytest.mark.parametrize(
    "field",
    [
        "implementation", "cache_tag", "magic_number",
        "payload_sha256", "runtime_sha256",
    ],
)
def test_stale_metadata_is_rejected_without_stamp(
    artifacts: Path, field: str,
) -> None:
    metadata_path = artifacts / "metadata"
    metadata = json.loads(metadata_path.read_text())
    metadata[field] = "stale"
    metadata_path.write_text(json.dumps(metadata))
    result = validate(
        artifacts, int.from_bytes(importlib.util.MAGIC_NUMBER, "little"),
    )
    assert result.returncode != 0
    assert f"{field}: expected" in result.stderr
    assert not (artifacts / "stamp").exists()


def test_changed_interpreter_magic_is_rejected_without_stamp(artifacts: Path) -> None:
    magic = int.from_bytes(importlib.util.MAGIC_NUMBER, "little")
    result = validate(artifacts, magic ^ 1)
    assert result.returncode != 0
    assert "selected Python magic changed during validation" in result.stderr
    assert not (artifacts / "stamp").exists()
