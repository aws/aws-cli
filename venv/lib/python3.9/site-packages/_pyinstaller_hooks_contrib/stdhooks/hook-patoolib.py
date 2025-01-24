#-----------------------------------------------------------------------------
# Copyright (c) 2017-2024, PyInstaller Development Team.
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
patoolib uses importlib and pyinstaller doesn't find it and add it to the list of needed modules
"""

from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('patoolib.programs')
