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

# https://github.com/enthought/comtypes/blob/1.4.5/comtypes/client/_generate.py#L271-L280
hiddenimports = [
    "comtypes.persist",
    "comtypes.typeinfo",
    "comtypes.automation",
    "comtypes.stream",
    "comtypes",
    "ctypes.wintypes",
    "ctypes",
]
