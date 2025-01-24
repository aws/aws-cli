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
Spacy contains hidden imports and data files which are needed to import it
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("spacy")
hiddenimports = collect_submodules("spacy")
