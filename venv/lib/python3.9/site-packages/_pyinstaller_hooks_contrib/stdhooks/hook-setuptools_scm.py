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

from PyInstaller.utils.hooks import copy_metadata

# Ensure `metadata of setuptools` dist is collected, to avoid run-time warning about unknown/incompatible `setuptools`
# version.
datas = copy_metadata('setuptools')
