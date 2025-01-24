#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
#-----------------------------------------------------------------------------
"""
Fixes https://github.com/pyinstaller/pyinstaller/issues/4995

Modules under parsedatetime.pdt_locales.* are lazily loaded using __import__.
But they are conviniently listed in parsedatetime.pdt_locales.locales.

Tested on versions:

- 1.1.1
- 1.5
- 2.0
- 2.6 (latest)

"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("parsedatetime.pdt_locales")
