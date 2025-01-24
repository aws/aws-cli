# ------------------------------------------------------------------
# Copyright (c) 2023 PyInstaller Development Team.
#
# This file is distributed under the terms of the GNU General Public
# License (version 2.0 or later).
#
# The full license is available in LICENSE, distributed with
# this software.
#
# SPDX-License-Identifier: GPL-2.0-or-later
# ------------------------------------------------------------------

# `moviepy.video.fx.all` programmatically imports and forwards all submodules of `moviepy.video.fx`, so we need to
# collect those as hidden imports.
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('moviepy.video.fx')
