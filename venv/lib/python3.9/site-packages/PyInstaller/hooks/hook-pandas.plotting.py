#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import is_module_satisfies

# Starting with pandas 1.3.0, pandas.plotting._matplotlib is imported via importlib.import_module() and needs to be
# added to hidden imports. But do this only if matplotlib is available in the first place (as it is soft dependency
# of pandas).
if is_module_satisfies('pandas >= 1.3.0') and is_module_satisfies('matplotlib'):
    hiddenimports = ['pandas.plotting._matplotlib']
