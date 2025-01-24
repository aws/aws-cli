# ------------------------------------------------------------------
# Copyright (c) 2021 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files, is_module_satisfies

# adb.exe is not automatically collected by collect_dynamic_libs()
datas = collect_data_files("adbutils", subdir="binaries", includes=["adb*"])

# adbutils v2.2.2 replaced `pkg_resources` with `importlib.resources`, and now uses the following code to determine the
# path to the `adbutils.binaries` sub-package directory:
# https://github.com/openatx/adbutils/blob/2.2.2/adbutils/_utils.py#L78-L87
# As `adbutils.binaries` is not directly imported anywhere, we need a hidden import.
if is_module_satisfies('adbutils >= 2.2.2'):
    hiddenimports = ['adbutils.binaries']
