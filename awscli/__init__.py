# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""
AWSCLI
----
A Universal Command Line Environment for Amazon Web Services.
"""
import os
import importlib.abc
import sys

__version__ = '2.13.21'

#
# Get our data path to be added to botocore's search path
#
_awscli_data_path = []
if 'AWS_DATA_PATH' in os.environ:
    for path in os.environ['AWS_DATA_PATH'].split(os.pathsep):
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        _awscli_data_path.append(path)
_awscli_data_path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
)
os.environ['AWS_DATA_PATH'] = os.pathsep.join(_awscli_data_path)


SCALAR_TYPES = set([
    'string', 'float', 'integer', 'long', 'boolean', 'double',
    'blob', 'timestamp'
])
COMPLEX_TYPES = set(['structure', 'map', 'list'])


class TopLevelImportAliasFinder(importlib.abc.MetaPathFinder):
    """Finder to allow missing awscli namespace in package imports

    This allows packages that used to be dependencies of the AWS CLI and are
    now maintained in the AWS CLI codebase to still be importable as a
    top-level import and minimize churn on the codebase. For example, both of
    these import statements result in the import of the same module on disk::

        >> import awscli.botocore
        >> import botocore

    Note: That this import alias only comes into affect if anything is
    imported from the awscli package.
    """
    _PACKAGES = [
        'botocore',
        's3transfer',
    ]
    _TARGET_FINDERS = [
        'pyimod02_importers.PyiFrozenImporter',  # Pyinstaller injected finder
        '_frozen_importlib_external.PathFinder'  # Built-in path finder
    ]

    def __init__(self, underlying_finder):
        self._underlying_finder = underlying_finder
        self._parent_path = [os.path.dirname(__file__)]

    @classmethod
    def add_alias_finder(cls, meta_path):
        """Wrap known MetaPathFinders that search for aliased packages"""
        for i, finder in enumerate(meta_path):
            # We are searching by module + name because the meta path finders
            # that we want to add the alias shim for either cannot be imported
            # (e.g. the PyInstaller meta path finder) or is recommended against
            # being directly imported (e.g. the standard library path finder).
            if isinstance(finder, type):
                finder_name = finder.__name__
            else:
                finder_name = finder.__class__.__name__
            full_cls_name = f'{finder.__module__}.{finder_name}'
            if full_cls_name in cls._TARGET_FINDERS:
                meta_path[i] = cls(finder)
                return

    def find_spec(self, fullname, path, target=None):
        if fullname in self._PACKAGES:
            path = self._parent_path
        return self._underlying_finder.find_spec(fullname, path, target)


TopLevelImportAliasFinder.add_alias_finder(sys.meta_path)
