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
Collects in-repo dask.yaml and dask-schema.yaml data files.
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('dask', includes=['*.yml', '*.yaml'])
