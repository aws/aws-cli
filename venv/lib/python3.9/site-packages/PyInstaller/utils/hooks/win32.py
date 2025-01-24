# ----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# ----------------------------------------------------------------------------

from PyInstaller import isolated


@isolated.decorate
def get_pywin32_module_file_attribute(module_name):
    """
    Get the absolute path of the PyWin32 DLL specific to the PyWin32 module with the passed name.

    On import, each PyWin32 module:

    * Imports a DLL specific to that module.
    * Overwrites the values of all module attributes with values specific to that DLL. This includes that module's
      `__file__` attribute, which then provides the absolute path of that DLL.

    This function safely imports that module in a PyWin32-aware subprocess and returns the value of that module's
    `__file__` attribute.

    Parameters
    ----------
    module_name : str
        Fully-qualified name of that module.

    Returns
    ----------
    str
        Absolute path of that DLL.

    See Also
    ----------
    `PyInstaller.utils.win32.winutils.import_pywin32_module()`
        For further details.
    """
    from PyInstaller.utils.win32 import winutils
    module = winutils.import_pywin32_module(module_name)
    return module.__file__
