# ------------------------------------------------------------------
# Copyright (c) 2022 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------

from PyInstaller.compat import is_py310
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, is_module_satisfies

# Collect core plugins.
hiddenimports = collect_submodules('hydra._internal.core_plugins')

# Hydra's plugin manager (`hydra.core.plugins.Plugins`) uses PEP-302 `find_module` / `load_module`, which has been
# deprecated since python 3.4, and has been removed from PyInstaller's frozen importer in PyInstaller 5.8. For python
# 3.10 and newer, they implemented new codepath that uses `find_spec`, but for earlier python versions, they opted to
# keep using the old codepath.
#
# See: https://github.com/facebookresearch/hydra/pull/2531
#
# To work around the incompatibility with PyInstaller >= 5.8 when using python < 3.10, force collection of plugins as
# source .py files. This way, they end up handled by python's built-in finder/importer instead of PyInstaller's
# frozen importer.
if not is_py310 and is_module_satisfies("PyInstaller >= 5.8"):
    module_collection_mode = {
        'hydra._internal.core_plugins': 'py',
        'hydra_plugins': 'py',
    }

# Collect package's data files, such as default configuration files.
datas = collect_data_files('hydra')
