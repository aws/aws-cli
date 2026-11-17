"""Hash-pinned venvs shared by the harness runners under tests/.

tests/blackbox/run.py, tests/deps/run.py, and tests/argparse/argtables.py
each provision a cached venv from hash-pinned lock files, reuse it while the
locks and the host
interpreter are unchanged, and run setup commands under one time limit. The
first provision downloads wheels; nothing here touches the network after
that.
"""

from __future__ import annotations

import hashlib
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from venv_paths import venv_python_path

SETUP_TIMEOUT_SECONDS: Final = 20 * 60
MINIMUM_PYTHON: Final = (3, 12)
MAXIMUM_PYTHON: Final = (3, 14)
_MARKER_NAME: Final = ".zippy-harness-deps"


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            check=False,
            timeout=SETUP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        command = shlex.join(args)
        raise SystemExit(
            f"command exceeded {SETUP_TIMEOUT_SECONDS} seconds: {command}"
        ) from error
    if result.returncode != 0:
        command = shlex.join(args)
        raise SystemExit(
            f"command failed with exit code {result.returncode}: {command}"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def host_python_id() -> str:
    version = sys.version_info
    return (
        f"{sys.implementation.name} "
        f"{version.major}.{version.minor}.{version.micro}"
    )


def validate_host_python(suite: str) -> None:
    major_minor = sys.version_info[:2]
    if MINIMUM_PYTHON <= major_minor <= MAXIMUM_PYTHON:
        return
    raise SystemExit(
        f"{suite} require Python 3.12 through 3.14; found "
        f"{sys.version_info.major}.{sys.version_info.minor}"
    )


def ensure_venv(
    venv_dir: Path,
    requirements: Sequence[Path],
    revision: str,
) -> Path:
    """Provision and return the cached venv interpreter.

    The venv is rebuilt from scratch when `revision`, any lock file, or the
    host interpreter changes.
    """
    marker = venv_dir / _MARKER_NAME
    python = venv_python_path(venv_dir)
    marker_text = "".join(
        [
            f"{revision}\n",
            *(f"{sha256(path)}\n" for path in requirements),
            f"{host_python_id()}\n",
        ]
    )
    if (
        python.exists()
        and marker.exists()
        and marker.read_text(encoding="utf-8") == marker_text
    ):
        return python
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    print(
        f"harness: provisioning the test harness venv under {venv_dir}",
        file=sys.stderr,
        flush=True,
    )
    run([sys.executable, "-m", "venv", str(venv_dir)])
    install = [
        str(python),
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--only-binary=:all:",
        "--require-hashes",
    ]
    for path in requirements:
        install.extend(["--requirement", str(path)])
    run(install)
    marker.write_text(marker_text, encoding="utf-8")
    return python
