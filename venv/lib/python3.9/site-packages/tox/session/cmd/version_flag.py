"""
Display the version information about tox.
"""
from __future__ import annotations

import sys
from argparse import SUPPRESS, Action, ArgumentParser, Namespace
from pathlib import Path
from typing import Any, Sequence, cast

import tox
from tox.config.cli.parser import HelpFormatter, ToxParser
from tox.plugin import impl
from tox.plugin.manager import MANAGER
from tox.version import version


@impl
def tox_add_option(parser: ToxParser) -> None:
    class _V(Action):
        def __init__(self, option_strings: Sequence[str], dest: str = SUPPRESS) -> None:
            help_msg = "show program's and plugins version number and exit"
            super().__init__(option_strings=option_strings, dest=dest, nargs=0, help=help_msg, default=SUPPRESS)

        def __call__(
            self,
            parser: ArgumentParser,
            namespace: Namespace,  # noqa: U100
            values: str | Sequence[Any] | None,  # noqa: U100
            option_string: str | None = None,  # noqa: U100
        ) -> None:
            formatter = cast(HelpFormatter, parser._get_formatter())
            formatter.add_raw_text(get_version_info())
            parser._print_message(formatter.format_help(), sys.stdout)
            parser.exit()

    parser.add_argument("--version", action=_V)


def get_version_info() -> str:
    out = [f"{version} from {Path(tox.__file__).absolute()}"]
    plugin_info = MANAGER.manager.list_plugin_distinfo()
    if plugin_info:
        out.append("registered plugins:")
        for module, egg_info in plugin_info:
            source = getattr(module, "__file__", repr(module))
            out.append(f"    {egg_info.project_name}-{egg_info.version} at {source}")
    return "\n".join(out)
