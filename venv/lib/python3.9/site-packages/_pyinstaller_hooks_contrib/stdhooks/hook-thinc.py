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
"""
Thinc contains data files and hidden imports. This hook was created to make spacy work correctly.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("thinc")
hiddenimports = collect_submodules("thinc")
