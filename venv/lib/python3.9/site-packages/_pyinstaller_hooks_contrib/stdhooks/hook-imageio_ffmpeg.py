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

# Hook for imageio: http://imageio.github.io/

from PyInstaller.utils.hooks import collect_data_files, is_module_satisfies

datas = collect_data_files('imageio_ffmpeg', subdir="binaries")

# Starting with imageio_ffmpeg 0.5.0, `imageio_ffmpeg.binaries` is a package accessed via `importlib.resources`. Since
# it is not directly imported anywhere, we need to add it to hidden imports.
if is_module_satisfies('imageio_ffmpeg >= 0.5.0'):
    hiddenimports = ['imageio_ffmpeg.binaries']
