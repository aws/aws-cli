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
from PyInstaller.utils.hooks import collect_dynamic_libs, is_module_satisfies

# PyTables is a package for managing hierarchical datasets
hiddenimports = ["tables._comp_lzo", "tables._comp_bzip2"]

# Collect the bundled copy of blosc2 shared library.
binaries = collect_dynamic_libs('tables')
datas = []

# tables 3.7.0 started using `delvewheel` for its Windows PyPI wheels. While contemporary PyInstaller versions
# automatically pick up DLLs from external `pyproj.libs` directory, this does not work on Anaconda python 3.8 and 3.9
# due to defunct `os.add_dll_directory`, which forces `delvewheel` to use the old load-order file approach. So we need
# to explicitly ensure that load-order file as well as DLLs are collected.
if is_win and is_module_satisfies("tables >= 3.7.0"):
    if is_module_satisfies("PyInstaller >= 5.6"):
        from PyInstaller.utils.hooks import collect_delvewheel_libs_directory
        datas, binaries = collect_delvewheel_libs_directory("tables", datas=datas, binaries=binaries)
