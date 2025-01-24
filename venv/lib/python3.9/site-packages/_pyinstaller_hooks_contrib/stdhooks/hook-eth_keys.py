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

from PyInstaller.utils.hooks import copy_metadata, is_module_satisfies

# As of eth-keys 0.5.0, it uses importlib.metadata.version() set its __version__ attribute
if is_module_satisfies("eth-keys >= 0.5.0"):
    datas = copy_metadata("eth-keys")
