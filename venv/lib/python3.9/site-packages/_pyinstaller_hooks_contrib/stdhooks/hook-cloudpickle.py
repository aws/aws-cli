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

from PyInstaller.utils.hooks import is_module_satisfies

# cloudpickle to 3.0.0 keeps `cloudpickle_fast` module around for backward compatibility with existing pickled data,
# but does not import it directly anymore. Ensure it is collected nevertheless.
if is_module_satisfies("cloudpickle >= 3.0.0"):
    hiddenimports = ["cloudpickle.cloudpickle_fast"]
