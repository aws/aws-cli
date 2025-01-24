"""
tox uses `pluggy <https://pluggy.readthedocs.io/en/stable/>`_ to customize the default behaviour. For example the
following code snippet would define a new ``--magic`` command line interface flag the user can specify:

.. code-block:: python

    from tox.config.cli.parser import ToxParser
    from tox.plugin import impl


    @impl
    def tox_add_option(parser: ToxParser) -> None:
        parser.add_argument("--magic", action="store_true", help="magical flag")

You can define such hooks either in a package installed alongside tox or within a ``toxfile.py`` found alongside your
tox configuration file (root of your project).
"""
from __future__ import annotations

from typing import Any, Callable, TypeVar

import pluggy

NAME = "tox"  #: the name of the tox hook

_F = TypeVar("_F", bound=Callable[..., Any])
impl: Callable[[_F], _F] = pluggy.HookimplMarker(NAME)  #: decorator to mark tox plugin hooks


__all__ = (
    "NAME",
    "impl",
)
