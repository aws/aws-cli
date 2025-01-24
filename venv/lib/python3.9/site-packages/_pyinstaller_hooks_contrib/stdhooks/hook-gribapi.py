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

import os
import pathlib

from PyInstaller import isolated
from PyInstaller.utils.hooks import collect_data_files, logger

# Collect the headers (eccodes.h, gribapi.h) that are bundled with the package.
datas = collect_data_files('gribapi')

# Collect the eccodes shared library. Starting with eccodes 2.37.0, binary wheels with bundled shared library are
# provided for linux and macOS.


# NOTE: custom isolated function is used here instead of `get_module_attribute('gribapi.bindings', 'library_path')`
# hook utility function because with eccodes 2.37.0, `eccodes` needs to be imported before `gribapi` to avoid circular
# imports... Also, this way, we can obtain the root directory of eccodes package at the same time.
@isolated.decorate
def get_eccodes_library_path():
    import eccodes
    import gribapi.bindings

    return (
        # Path to eccodes shared library used by the gribapi bindings.
        str(gribapi.bindings.library_path),
        # Path to eccodes package (implicitly assumed to be next to the gribapi package, since they are part of the
        # same eccodes dist).
        str(eccodes.__path__[0]),
    )


binaries = []

try:
    library_path, package_path = get_eccodes_library_path()
except Exception:
    logger.warning("hook-gribapi: failed to query gribapi.bindings.library_path!", exc_info=True)
    library_path = None

if library_path:
    if not os.path.isabs(library_path):
        from PyInstaller.depend.utils import _resolveCtypesImports
        resolved_binary = _resolveCtypesImports([os.path.basename(library_path)])
        if resolved_binary:
            library_path = resolved_binary[0][1]
        else:
            logger.warning("hook-gribapi: failed to resolve shared library name %r!", library_path)
            library_path = None
else:
    logger.warning("hook-gribapi: could not determine path to eccodes shared library!")

if library_path:
    # If we are collecting eccodes shared library that is bundled with eccodes >= 2.37.0 binary wheel, attempt to
    # preserve its parent directory layout. This ensures that the library is found at run-time, but implicitly requires
    # PyInstaller 6.x, whose binary dependency analysis (that might also pick up this shared library) also preserves the
    # parent directory layout of discovered shared libraries. With PyInstaller 5.x, this will result in duplication
    # because binary dependency analysis collects into top-level application directory, but that copy will not be
    # discovered at run-time, so duplication is unavoidable.
    library_parent_path = pathlib.PurePath(library_path).parent
    package_parent_path = pathlib.PurePath(package_path).parent

    if package_parent_path in library_parent_path.parents:
        # Should end up being `eccodes.libs` on Linux, and `eccodes/.dylib` on macOS).
        dest_dir = str(library_parent_path.relative_to(package_parent_path))
    else:
        # External copy; collect into top-level application directory.
        dest_dir = '.'

    logger.info(
        "hook-gribapi: collecting eccodes shared library %r to destination directory %r", library_path, dest_dir
    )
    binaries.append((library_path, dest_dir))
