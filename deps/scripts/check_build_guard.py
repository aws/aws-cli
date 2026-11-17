#!/usr/bin/env python3
"""Check the CI guard from a staged directory.

tests/deps/test_build_checks.py copies this script beside the shared driver
modules into an otherwise empty directory and runs it, from an unrelated
working directory, under the interpreter flags every driver runs under,
which ignore PYTHONPATH and the user site. Importing the guard therefore
proves the staging contract, and the calls below prove the guard's own: a
plain call returns, the forbid variable exits with a loud message before
any work, and the marker directory receives one marker line per
invocation.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from build_guard import FORBID_ENV, MARKER_DIR_ENV, guard

BUILDER = "buildkit-check"


def check_plain_call_returns() -> None:
    guard(BUILDER)


def check_forbid_exits() -> None:
    os.environ[FORBID_ENV] = "1"
    try:
        guard(BUILDER)
    except SystemExit as exit_request:
        if "forbidden" not in str(exit_request.code):
            raise SystemExit(
                f"guard exited without the forbid message: "
                f"{exit_request.code!r}"
            ) from exit_request
    else:
        raise SystemExit(
            "guard returned although expensive builds are forbidden"
        )
    finally:
        del os.environ[FORBID_ENV]


def check_marker_written() -> None:
    with tempfile.TemporaryDirectory(prefix="buildkit-markers-") as marker_dir:
        os.environ[MARKER_DIR_ENV] = marker_dir
        try:
            guard(BUILDER)
            guard(BUILDER)
        finally:
            del os.environ[MARKER_DIR_ENV]
        marker = Path(marker_dir) / BUILDER
        contents = marker.read_text(encoding="utf-8")
        if contents != "ran\nran\n":
            raise SystemExit(
                f"unexpected marker contents in {marker}: {contents!r}"
            )


def main() -> None:
    # The caller's CI phase must not leak into the checks: each contract is
    # exercised with its variable set explicitly.
    os.environ.pop(FORBID_ENV, None)
    os.environ.pop(MARKER_DIR_ENV, None)
    check_plain_call_returns()
    check_forbid_exits()
    check_marker_written()
    print("build_guard: staged import and environment contract checked")


if __name__ == "__main__":
    main()
