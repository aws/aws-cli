#!/usr/bin/env python3
"""Run the dependency drivers' self-tests, this directory's test modules.

`cargo xtask harness-test` runs this with the managed compiler their native
compiler probes use in AWS_NATIVE_TEST_CC. The tests run in a cached venv
holding this directory's hash-pinned pytest closure, configured by
tests/harness-pytest.ini. Arguments the runner does not recognize go to
pytest.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Final

# This runner is executed by path, so its only import path is its own
# directory. The venv helpers live one level up, in tests/; append rather
# than prepend, as tests/blackbox/run.py does.
sys.path.append(str(Path(__file__).resolve().parents[1]))

import harness_venv

VENV_DEPS_REVISION: Final = "1"
TEST_TIMEOUT_SECONDS: Final = 20 * 60


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument("--cache-dir", required=True, type=Path)
    args, pytest_args = parser.parse_known_args()
    harness_venv.validate_host_python("the dependency driver self-tests")
    tests_dir = Path(__file__).resolve().parent
    root = tests_dir.parents[1]
    cache_dir = args.cache_dir.resolve()
    python = harness_venv.ensure_venv(
        cache_dir / "venv",
        [tests_dir / "requirements.txt"],
        VENV_DEPS_REVISION,
    )
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        str(python),
        "-m",
        "pytest",
        "-q",
        "-c",
        str(root / "tests/harness-pytest.ini"),
        f"--rootdir={root}",
        "-p",
        "no:cacheprovider",
        f"--basetemp={cache_dir / 'pytest-temp'}",
        str(tests_dir),
        *pytest_args,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=root,
            env=env,
            check=False,
            timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit(
            f"dependency driver self-tests exceeded "
            f"{TEST_TIMEOUT_SECONDS} seconds"
        ) from error
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
