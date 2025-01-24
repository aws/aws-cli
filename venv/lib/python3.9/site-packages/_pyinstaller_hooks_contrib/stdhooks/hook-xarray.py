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

from PyInstaller.utils.hooks import copy_metadata, collect_entry_point

datas = []
hiddenimports = []

# Collect additional backend plugins that are registered via `xarray.backends` entry-point.
ep_datas, ep_hiddenimports = collect_entry_point('xarray.backends')
datas += ep_datas
hiddenimports += ep_hiddenimports

# Similarly, collect chunk manager entry-points.
ep_datas, ep_hiddenimports = collect_entry_point('xarray.chunkmanagers')
datas += ep_datas
hiddenimports += ep_hiddenimports

# `xarray` requires `numpy` metadata due to several calls to its `xarray.core.utils.module_available` with specified
# `minversion` argument, which end up calling `importlib.metadata.version`.
datas += copy_metadata('numpy')
