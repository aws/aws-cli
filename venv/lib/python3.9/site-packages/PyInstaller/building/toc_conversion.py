# -----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

import os
import zipfile

import pkg_resources

from PyInstaller import log as logging
from PyInstaller.building.datastruct import Tree, normalize_toc
from PyInstaller.compat import ALL_SUFFIXES
from PyInstaller.depend.utils import get_path_to_egg

logger = logging.getLogger(__name__)

# create a list of excludes suitable for Tree.
PY_IGNORE_EXTENSIONS = {
    *('*' + x for x in ALL_SUFFIXES),
    # Exclude EGG-INFO, too, as long as we do not have a way to hold several in one archive.
    'EGG-INFO',
}


class DependencyProcessor:
    """
    Class to convert final module dependency graph into TOC data structures.
    TOC data structures are suitable for creating the final executable.
    """
    def __init__(self, graph, additional_files):
        self._binaries = set()
        self._datas = set()
        self._distributions = set()
        self.__seen_distribution_paths = set()
        # Include files that were found by hooks. graph.iter_graph() should include only those modules that are
        # reachable from the top-level script.
        for node in graph.iter_graph(start=graph._top_script_node):
            # Update 'binaries', 'datas'
            name = node.identifier
            if name in additional_files:
                self._binaries.update(additional_files.binaries(name))
                self._datas.update(additional_files.datas(name))
            # Any module can belong to a single distribution
            self._distributions.update(self._get_distribution_for_node(node))

    def _get_distribution_for_node(self, node):
        """
        Get the distribution a module belongs to.

        Bug: This currently only handles packages in eggs.
        """
        # TODO: Modulegraph could flag a module as residing in a zip file
        # TODO add support for single modules in eggs (e.g. mock-1.0.1)
        # TODO add support for egg-info:
        # TODO add support for wheels (dist-info)
        #
        # TODO add support for unpacked eggs and for new .whl packages.
        # Wheels:
        #  .../site-packages/pip/  # It seams this has to be a package
        #  .../site-packages/pip-6.1.1.dist-info
        # Unzipped Eggs:
        #  .../site-packages/mock.py   # this may be a single module, too!
        #  .../site-packages/mock-1.0.1-py2.7.egg-info
        # Unzipped Eggs (I assume: multiple-versions externally managed):
        #  .../site-packages/pyPdf-1.13-py2.6.egg/pyPdf/
        #  .../site-packages/pyPdf-1.13-py2.6.egg/EGG_INFO
        # Zipped Egg:
        #  .../site-packages/zipped.egg/zipped_egg/
        #  .../site-packages/zipped.egg/EGG_INFO
        modpath = node.filename
        if not modpath:
            # e.g. namespace-package
            return []
        # TODO: add other ways to get a distribution path
        distpath = get_path_to_egg(modpath)
        if not distpath or distpath in self.__seen_distribution_paths:
            # no egg or already handled
            return []
        self.__seen_distribution_paths.add(distpath)
        dists = list(pkg_resources.find_distributions(distpath))
        assert len(dists) == 1
        dist = dists[0]
        dist._pyinstaller_info = {
            'zipped': zipfile.is_zipfile(dist.location),
            'egg': True,  # TODO when supporting other types
            'zip-safe': dist.has_metadata('zip-safe'),
        }
        return dists

    # Public methods.

    def make_binaries_toc(self):
        toc = [(x, y, 'BINARY') for x, y in self._binaries]
        return normalize_toc(toc)

    def make_datas_toc(self):
        toc = [(x, y, 'DATA') for x, y in self._datas]
        for dist in self._distributions:
            if (
                dist._pyinstaller_info['egg'] and not dist._pyinstaller_info['zipped']
                and not dist._pyinstaller_info['zip-safe']
            ):
                # this is a un-zipped, not-zip-safe egg
                tree = Tree(dist.location, excludes=PY_IGNORE_EXTENSIONS)
                toc.extend(tree)
        return normalize_toc(toc)

    def make_zipfiles_toc(self):
        # TODO create a real TOC when handling of more files is added.
        toc = []
        for dist in self._distributions:
            if dist._pyinstaller_info['zipped'] and not dist._pyinstaller_info['egg']:
                # Hmm, this should never happen as normal zip-files are not associated with a distribution, are they?
                toc.append(("eggs/" + os.path.basename(dist.location), dist.location, 'ZIPFILE'))
        return normalize_toc(toc)

    @staticmethod
    def __collect_data_files_from_zip(zipfilename):
        # 'PyInstaller.config' cannot be imported as other top-level modules.
        from PyInstaller.config import CONF
        workpath = os.path.join(CONF['workpath'], os.path.basename(zipfilename))
        try:
            os.makedirs(workpath)
        except OSError as e:
            import errno
            if e.errno != errno.EEXIST:
                raise
        # TODO: extract only those file which would then be included
        with zipfile.ZipFile(zipfilename) as zfh:
            zfh.extractall(workpath)
        return Tree(workpath, excludes=PY_IGNORE_EXTENSIONS)

    def make_zipped_data_toc(self):
        toc = []
        logger.debug('Looking for egg data files...')
        for dist in self._distributions:
            if dist._pyinstaller_info['egg']:
                if dist._pyinstaller_info['zipped']:
                    # this is a zipped egg
                    tree = self.__collect_data_files_from_zip(dist.location)
                    toc.extend(tree)
                elif dist._pyinstaller_info['zip-safe']:
                    # this is an un-zipped, zip-safe egg
                    tree = Tree(dist.location, excludes=PY_IGNORE_EXTENSIONS)
                    toc.extend(tree)
                else:
                    # this is an un-zipped, not-zip-safe egg, handled in make_datas_toc()
                    pass
        return normalize_toc(toc)
