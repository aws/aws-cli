"""Run the guard and tool-environment checks staged as drivers run."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "deps/scripts"
# Every dependency driver runs beside these files. Staging only them proves
# each check needs nothing else from deps/scripts.
SHARED_FILES = ("build_guard.py", "build_environ.py", "tool_environ.txt")


@pytest.mark.parametrize("check", ["check_build_guard.py", "check_build_environ.py"])
def test_staged_check_passes_under_the_driver_interpreter(
    tmp_path: Path, check: str
) -> None:
    staged = tmp_path / "staged"
    staged.mkdir()
    for name in (check, *SHARED_FILES):
        shutil.copy2(SCRIPTS / name, staged / name)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    result = subprocess.run(
        [sys.executable, "-E", "-s", "-B", str(staged / check)],
        cwd=scratch,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
