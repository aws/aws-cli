# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import importlib
import os

import pytest

import awscli
from awscli import TopLevelImportAliasFinder

AWSCLI_ROOT_DIR = os.path.dirname(awscli.__file__)


@pytest.fixture()
def fake_builtin_path_finder():
    class PathFinder(type):
        __module__ = '_frozen_importlib_external'
    return PathFinder


@pytest.fixture()
def fake_pyinstaller_finder():
    class FrozenImporter:
        __module__ = 'pyimod02_importers'
    return FrozenImporter()


class RecordingMetaPathFinder(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.find_spec_calls = []

    def find_spec(self, fullname, path, target=None):
        self.find_spec_calls.append((fullname, path, target))
        return None


@pytest.mark.parametrize(
    'fullname,provided_path,expected_path',
    [
        ('botocore', None, [AWSCLI_ROOT_DIR]),
        ('s3transfer', None, [AWSCLI_ROOT_DIR]),
        ('awscli', None, None),
        ('awscli.utils', [AWSCLI_ROOT_DIR], [AWSCLI_ROOT_DIR]),
        ('logging', None, None),
    ]
)
def test_find_spec(fullname, provided_path, expected_path):
    underlying_finder = RecordingMetaPathFinder()
    alias_finder = TopLevelImportAliasFinder(underlying_finder)
    alias_finder.find_spec(fullname, provided_path, target=None)
    assert underlying_finder.find_spec_calls == [
        (fullname, expected_path, None)
    ]


def test_add_alias_finder_wraps_builtin_finder(fake_builtin_path_finder):
    sys_meta = [fake_builtin_path_finder]
    TopLevelImportAliasFinder.add_alias_finder(sys_meta)
    _assert_classes(sys_meta, [TopLevelImportAliasFinder])


def test_add_alias_finder_wraps_pyinstaller_finder(fake_pyinstaller_finder):
    sys_meta = [fake_pyinstaller_finder]
    TopLevelImportAliasFinder.add_alias_finder(sys_meta)
    _assert_classes(sys_meta, [TopLevelImportAliasFinder])


def test_add_alias_finder_does_not_wrap_other_finders():
    do_not_wrap_this_finder = RecordingMetaPathFinder()
    sys_meta = [do_not_wrap_this_finder]
    TopLevelImportAliasFinder.add_alias_finder(sys_meta)
    assert sys_meta == [do_not_wrap_this_finder]


def test_add_alias_finder_wraps_only_first_matching_finder(
        fake_pyinstaller_finder):
    sys_meta = [
        RecordingMetaPathFinder(),
        fake_pyinstaller_finder,
        fake_pyinstaller_finder
    ]
    TopLevelImportAliasFinder.add_alias_finder(sys_meta)
    _assert_classes(
        sys_meta,
        [
            RecordingMetaPathFinder,
            TopLevelImportAliasFinder,
            fake_pyinstaller_finder.__class__,
        ]
    )


def _assert_classes(sys_meta, expected_classes):
    assert [finder.__class__ for finder in sys_meta] == expected_classes
