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

from PyInstaller.utils.hooks import is_module_satisfies

hiddenimports = []

if is_module_satisfies("scikit_learn > 1.0.1"):
    # 1.0.2 and later
    hiddenimports += [
        'sklearn.neighbors._quad_tree',
    ]
elif is_module_satisfies("scikit_learn < 0.22 "):
    # 0.21 and below
    hiddenimports += [
        'sklearn.neighbors.typedefs',
        'sklearn.neighbors.quad_tree',
    ]
else:
    # between and including 0.22 and 1.0.1
    hiddenimports += [
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._quad_tree',
    ]

# The following hidden import must be added here
# (as opposed to sklearn.tree)
hiddenimports += ['sklearn.tree._criterion']

# Additional hidden imports introduced in v1.0.0
if is_module_satisfies("scikit_learn >= 1.0.0"):
    hiddenimports += ["sklearn.neighbors._partition_nodes"]
