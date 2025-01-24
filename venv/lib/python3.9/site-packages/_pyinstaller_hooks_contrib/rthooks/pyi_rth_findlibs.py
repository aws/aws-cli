#-----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

# Override the findlibs.find() function to give precedence to sys._MEIPASS, followed by `ctypes.util.find_library`,
# and only then the hard-coded paths from the original implementation. The main aim here is to avoid loading libraries
# from Homebrew environment on macOS when it happens to be present at run-time and we have a bundled copy collected from
# the build system. This happens because we (try not to) modify `DYLD_LIBRARY_PATH`, and the original `findlibs.find()`
# implementation gives precedence to environment variables and several fixed/hard-coded locations, and uses
# `ctypes.util.find_library` as the final fallback...
def _pyi_rthook():
    import sys
    import os
    import ctypes.util

    import findlibs

    _orig_find = getattr(findlibs, 'find', None)

    def _pyi_find(lib_name, pkg_name=None):
        pkg_name = pkg_name or lib_name
        extension = findlibs.EXTENSIONS.get(sys.platform, ".so")

        # First check sys._MEIPASS
        fullname = os.path.join(sys._MEIPASS, "lib{}{}".format(lib_name, extension))
        if os.path.isfile(fullname):
            return fullname

        # Fall back to `ctypes.util.find_library` (to give it precedence over hard-coded paths from original
        # implementation).
        lib = ctypes.util.find_library(lib_name)
        if lib is not None:
            return lib

        # Finally, fall back to original implementation
        if _orig_find is not None:
            return _orig_find(lib_name, pkg_name)

        return None

    findlibs.find = _pyi_find


_pyi_rthook()
del _pyi_rthook
