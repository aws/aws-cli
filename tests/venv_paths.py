"""Virtual environment layout shared by the harness runners under tests/.

`python -m venv` puts the interpreter in `bin/python` on POSIX and in
`Scripts\\python.exe` on Windows. Both tests/harness_venv.py, which the
other runners share, and tests/integ/run_integ_tests.py
provision a cached venv and then look for that interpreter, so the
convention lives here once instead of being spelled out - and drifting - in
each of them.

`ensure_venv` in deps/scripts/prepare_python_fallback.py is this
convention's other home, and the two must agree. They are separate on
purpose: that script is a declared cache input of the fallback stages,
while these runners are not cache inputs.
"""

from __future__ import annotations

import sys
from pathlib import Path


def venv_python_path(venv_dir: Path) -> Path:
    """Interpreter inside a virtual environment, per platform convention."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"
