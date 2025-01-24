from __future__ import annotations

from pathlib import Path
from shutil import rmtree


def ensure_empty_dir(path: Path, except_filename: str | None = None) -> None:
    if path.exists():
        if path.is_dir():
            for sub_path in path.iterdir():
                if sub_path.name == except_filename:
                    continue
                if sub_path.is_dir():
                    rmtree(sub_path, ignore_errors=True)
                else:
                    sub_path.unlink()
        else:
            path.unlink()
            path.mkdir()
    else:
        path.mkdir(parents=True)


__all__ = [
    "ensure_empty_dir",
]
