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

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# Collect default icon from `resources`.
datas = collect_data_files('toga_gtk')

# Collect metadata so that the backend can be discovered via `toga.backends` entry-point.
datas += copy_metadata("toga-gtk")
