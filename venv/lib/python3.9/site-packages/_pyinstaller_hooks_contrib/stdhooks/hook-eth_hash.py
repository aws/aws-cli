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

from PyInstaller.utils.hooks import collect_submodules, copy_metadata, is_module_satisfies

# The ``eth_hash.utils.load_backend`` function does a dynamic import.
hiddenimports = collect_submodules('eth_hash.backends')

# As of eth-hash 0.6.0, it uses importlib.metadata.version() set its __version__ attribute
if is_module_satisfies("eth-hash >= 0.6.0"):
    datas = copy_metadata("eth-hash")
