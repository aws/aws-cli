# ------------------------------------------------------------------
# Copyright (c) 2020 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import is_module_satisfies

# netCDF4 (tested with v.1.1.9) has some hidden imports
hiddenimports = ['netCDF4.utils']

# Around netCDF4 1.4.0, netcdftime changed name to cftime
if is_module_satisfies("netCDF4 < 1.4.0"):
    hiddenimports += ['netcdftime']
else:
    hiddenimports += ['cftime']

# Starting with netCDF 1.6.4, certifi is a hidden import made in
# netCDF4/_netCDF4.pyx.
if is_module_satisfies("netCDF4 >= 1.6.4"):
    hiddenimports += ['certifi']

# netCDF 1.6.2 is the first version that uses `delvewheel` for bundling DLLs in Windows PyPI wheels. While contemporary
# PyInstaller versions automatically pick up DLLs from external `netCDF4.libs` directory, this does not work on Anaconda
# python 3.8 and 3.9 due to defunct `os.add_dll_directory`, which forces `delvewheel` to use the old load-order file
# approach. So we need to explicitly ensure that load-order file as well as DLLs are collected.
if is_win and is_module_satisfies("netCDF4 >= 1.6.2"):
    if is_module_satisfies("PyInstaller >= 5.6"):
        from PyInstaller.utils.hooks import collect_delvewheel_libs_directory
        datas, binaries = collect_delvewheel_libs_directory("netCDF4")
