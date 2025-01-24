from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    import tomllib
else:  # pragma: no cover (py311+)
    import tomli as tomllib


from .ini import IniSource


class LegacyToml(IniSource):
    FILENAME = "pyproject.toml"

    def __init__(self, path: Path):
        if path.name != self.FILENAME or not path.exists():
            raise ValueError
        with path.open("rb") as file_handler:
            toml_content = tomllib.load(file_handler)
        try:
            content = toml_content["tool"]["tox"]["legacy_tox_ini"]
        except KeyError:
            raise ValueError
        super().__init__(path, content=content)


__all__ = ("LegacyToml",)
