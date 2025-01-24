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
#
# NumPy aware dynamic Python compiler using LLVM
# https://github.com/numba/numba
#
# Tested with:
# numba 0.26 (Anaconda 4.1.1, Windows), numba 0.28 (Linux)

from PyInstaller.utils.hooks import is_module_satisfies

excludedimports = ["IPython", "scipy"]
hiddenimports = ["llvmlite"]

# numba 0.59.0 updated its vendored version of cloudpickle to 3.0.0; this version keeps `cloudpickle_fast` module
# around for backward compatibility with existing pickled data, but does not import it directly anymore.
if is_module_satisfies("numba >= 0.59.0"):
    hiddenimports += ["numba.cloudpickle.cloudpickle_fast"]
