"""Exercise the system-Python outputs without external services or compilers."""

import importlib.util
import marshal
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

import pytest
from payload import read_payload_entries


@pytest.fixture
def staged_driver(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[2] / "deps/scripts"
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, tmp_path / path.name)
    return tmp_path


@pytest.mark.parametrize("bundled", [True, False])
def test_embedded_config_and_extension_registration_agree(
    staged_driver: Path, bundled: bool,
) -> None:
    subprocess.run(
        [
            sys.executable, "-E", "-s", "-B", "-c",
            "from pathlib import Path; import prepare_system_python as p; "
            f"p.write_glue(Path('inittab.c'), True, {bundled!r}); "
            f"p.write_config(Path('config.rs'), True, {bundled!r}, "
            "'/python/site-packages', '/usr/bin/python3')",
        ],
        cwd=staged_driver, check=True, capture_output=True,
    )
    glue = (staged_driver / "inittab.c").read_text()
    config = (staged_driver / "config.rs").read_text()
    assert ('PyImport_AppendInittab("_awscrt"' in glue) == bundled
    assert 'PyImport_AppendInittab("_zippy_finder"' in glue
    assert "pub const DYNAMIC: bool = true;" in config
    assert "pub const EMBEDDED_PAYLOAD: bool = true;" in config
    platlib = "" if bundled else "/python/site-packages"
    assert f'pub const PLATLIB: &str = "{platlib}";' in config


def test_system_payload_contains_only_native_models_and_rust_config(
    staged_driver: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    output = staged_driver / "output"
    digest = staged_driver / "aws-cli.digest"
    digest.write_text("source identity is checked by xtask")
    arguments = [
        sys.executable, "-E", "-s", "-B",
        str(staged_driver / "prepare_system_python.py"),
        "--payload-mode", "system", "--cache-dir", str(output / "cache"),
        "--aws-cli-source", str(root / "aws-cli"),
        "--aws-cli-digest", str(digest),
        "--pack-tool", str(staged_driver / "pack.py"),
        "--native-service", "s3",
        "--runtime-source", str(root / "crates/python-fallback/python/runtime_system.py"),
        "--expected-magic",
        str(int.from_bytes(importlib.util.MAGIC_NUMBER, "little")),
        "--platlib", sysconfig.get_path("platlib"),
        "--cc", "unused", "--ar", "unused",
        "--crt-include", str(output),
        "--target-triple", "x86_64-unknown-linux-gnu",
        "--object-file", str(output / "python-fallback.a"),
    ]
    for option in (
        "inittab", "blob", "runtime-bytecode", "metadata", "python-config",
    ):
        arguments.extend([f"--{option}", str(output / option)])
    subprocess.run(
        arguments, cwd=staged_driver, check=True, capture_output=True,
    )
    # The in-tree upstream resources are the contents oracle. Exact equality
    # also excludes Python modules, other services, and unused S3 resources.
    expected_paths = (
        "awscli/botocore/data/s3/2006-03-01/service-2.json",
        "awscli/botocore/data/s3/2006-03-01/endpoint-rule-set-1.json",
        "awscli/botocore/data/partitions.json",
    )
    assert read_payload_entries(output / "blob") == {
        name: (4, (root / "aws-cli" / name).read_bytes())
        for name in expected_paths
    }
    config = (output / "python-config").read_text()
    assert "pub const DYNAMIC: bool = true;" in config
    assert "pub const EMBEDDED_PAYLOAD: bool = false;" in config
    assert not (output / "python-fallback.a").exists()
    runtime = marshal.loads((output / "runtime-bytecode").read_bytes())
    assert runtime.co_filename == "src/runtime_system.py"


def test_runtime_bytecode_survives_source_relocation(
    staged_driver: Path, tmp_path: Path
) -> None:
    outputs: list[bytes] = []
    for location in ("checkout", "other tree"):
        source = tmp_path / location / "runtime.py"
        source.parent.mkdir()
        source.write_text("def entry():\n    return 42\n")
        output = source.with_suffix(".bin")
        subprocess.run(
            [
                sys.executable, "-E", "-s", "-B", "-c",
                "import os, sys; from pathlib import Path; "
                "import prepare_python_fallback as f; "
                "f.compile_runtime_bytecode(Path(sys.executable), "
                "Path(sys.argv[1]), Path(sys.argv[2]), dict(os.environ))",
                str(source), str(output),
            ],
            cwd=staged_driver, check=True, capture_output=True,
        )
        outputs.append(output.read_bytes())
    assert outputs[0] == outputs[1]
    code = marshal.loads(outputs[0])
    assert code.co_filename == "src/runtime.py"
