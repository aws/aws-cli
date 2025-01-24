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

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("itk.Configuration")

# `itk` requires `itk/Configuration` directory to exist on filesystem; collect source .py files from `itk.Configuration`
# as a work-around that ensures the existence of this directory.
module_collection_mode = {
    "itk.Configuration": "pyz+py",
}
