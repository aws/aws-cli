#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------
#
# This rthook overrides pkgutil.iter_modules with custom implementation that uses PyInstaller's PyiFrozenImporter to
# list sub-modules embedded in the PYZ archive. The non-embedded modules (binary extensions, or .pyc modules in
# noarchive build) are handled by original pkgutil iter_modules implementation (and consequently, python's FileFinder).
#
# The preferred way of adding support for iter_modules would be adding non-standard iter_modules() method to
# PyiFrozenImporter itself. However, that seems to work only for path entry finders (for use with sys.path_hooks), while
# PyInstaller's PyiFrozenImporter is registered as meta path finders (for use with sys.meta_path). Turning
# PyiFrozenImporter into path entry finder, would seemingly require the latter to support on-filesystem resources
# (e.g., extension modules) in addition to PYZ-embedded ones.
#
# Therefore, we instead opt for overriding pkgutil.iter_modules with custom implementation that augments the output of
# original implementation with contents of PYZ archive from PyiFrozenImporter's TOC.


def _pyi_rthook():
    import os
    import pkgutil
    import sys

    from pyimod02_importers import PyiFrozenImporter

    _orig_pkgutil_iter_modules = pkgutil.iter_modules

    def _pyi_pkgutil_iter_modules(path=None, prefix=''):
        # Use original implementation to discover on-filesystem modules (binary extensions in regular builds, or both
        # binary extensions and compiled pyc modules in noarchive debug builds).
        yield from _orig_pkgutil_iter_modules(path, prefix)

        # Find the instance of PyInstaller's PyiFrozenImporter.
        for importer in pkgutil.iter_importers():
            if isinstance(importer, PyiFrozenImporter):
                break
        else:
            return

        if path is None:
            # Search for all top-level packages/modules. These will have no dots in their entry names.
            for entry in importer.toc:
                if "." in entry:
                    continue
                is_pkg = importer.is_package(entry)
                yield pkgutil.ModuleInfo(importer, prefix + entry, is_pkg)
        else:
            # Use os.path.realpath() to fully resolve any symbolic links in sys._MEIPASS, in order to avoid path
            # mis-matches when the given search paths also contain symbolic links and are already fully resolved.
            # See #6537 for an example of such a problem with onefile build on macOS, where the temporary directory
            # is placed under /var, which is actually a symbolic link to /private/var.
            MEIPASS = os.path.realpath(sys._MEIPASS)

            for pkg_path in path:
                # Fully resolve the given path, in case it contains symbolic links.
                pkg_path = os.path.realpath(pkg_path)
                # Ensure it ends with os.path.sep (so we can directly filter out the package itself).
                if not pkg_path.endswith(os.path.sep):
                    pkg_path += os.path.sep

                for entry in importer.toc:
                    # Get the path to the module, and resolve symbolic links. This implicitly solves the problem with
                    # macOS .app bundles and packages that contain data files, where package directory is fully
                    # collected into Contents/Resources, and symbolic link to directory is created in sys._MEIPASS
                    # (Contents/Frameworks). See #7884.
                    module_path = os.path.realpath(os.path.join(MEIPASS, entry.replace(".", os.path.sep)))

                    # If the module is not in the requested path, skip it.
                    if not module_path.startswith(pkg_path):
                        continue

                    name = module_path[len(pkg_path):]

                    if os.path.sep in name:
                        # Not a direct child
                        continue
                    is_pkg = importer.is_package(entry)
                    yield pkgutil.ModuleInfo(importer, prefix + name, is_pkg)

    pkgutil.iter_modules = _pyi_pkgutil_iter_modules


_pyi_rthook()
del _pyi_rthook
