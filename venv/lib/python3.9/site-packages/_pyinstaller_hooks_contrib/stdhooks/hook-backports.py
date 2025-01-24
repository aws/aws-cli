# ------------------------------------------------------------------
# Copyright (c) 2024 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------

# Some of jaraco's backports packages (backports.functools-lru-cache, backports.tarfile) use pkgutil-style `backports`
# namespace package, with `__init__.py` file that contains:
#
# __path__ = __import__('pkgutil').extend_path(__path__, __name__)
#
# This import via `__import__` function slips past PyInstaller's modulegraph analysis; so add a hidden import, in case
# the user's program (and its dependencies) have no other direct imports of `pkgutil`.
hiddenimports = ['pkgutil']
