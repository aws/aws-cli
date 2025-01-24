from __future__ import annotations

from pathlib import Path

from .ini import IniSource
from .ini_section import IniSection


class SetupCfg(IniSource):
    """Configuration sourced from a tox.ini file"""

    CORE_SECTION = IniSection("tox", "tox")
    FILENAME = "setup.cfg"

    def __init__(self, path: Path):
        super().__init__(path)
        if not self._parser.has_section(self.CORE_SECTION.key):
            raise ValueError


__all__ = ("SetupCfg",)
