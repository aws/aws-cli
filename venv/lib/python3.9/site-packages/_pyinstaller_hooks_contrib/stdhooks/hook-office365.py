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
"""
Office365-REST-Python-Client contains xml templates that are needed by some methods
This hook ensures that all of the data used by the package is bundled
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("office365")
