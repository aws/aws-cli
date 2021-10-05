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
"""PEP 517 interface for building the AWS CLI

The interface for the public functions defined in this module are dictated by
PEP 517: https://www.python.org/dev/peps/pep-0517/#build-backend-interface.
Typically projects just rely directly on public build libraries (e.g.,
setuptools + wheel) in their pyproject.toml. However, the AWS CLI requires an
auto-complete index to function properly, and instead of directly committing
this index (which is MBs in size and changes with each API update) to the
repository, it is built as part of building the wheel. For the most part,
this in-tree backend just proxies to setuptools/wheel logic. The only exception
is that it builds the auto-complete index and injects it into the wheel
built by setuptools/wheel prior to returning.
"""
import contextlib
import os
import shutil
import subprocess
import sys
import zipfile

import setuptools.build_meta
import setuptools.config


ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


def build_sdist(sdist_directory, config_settings=None):
    return setuptools.build_meta.build_sdist(sdist_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None,
                metadata_directory=None):
    whl_filename = setuptools.build_meta.build_wheel(
            wheel_directory, config_settings, metadata_directory)
    _build_and_inject_ac_index(os.path.join(wheel_directory, whl_filename))
    return whl_filename


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return setuptools.build_meta.prepare_metadata_for_build_wheel(
        metadata_directory, config_settings)


def get_requires_for_build_sdist(config_settings=None):
    return setuptools.build_meta.get_requires_for_build_sdist(
        config_settings)


def get_requires_for_build_wheel(config_settings=None):
    requires = setuptools.build_meta.get_requires_for_build_wheel(
        config_settings)
    # Generation of the auto-complete index requires importing from the
    # awscli package and iterating over the commands from the clidriver. In
    # order to be able to do this, it requires all of the CLI's runtime
    # dependencies to be present to avoid import errors.
    requires += setuptools.config.read_configuration(
        os.path.join(ROOT_DIR, 'setup.cfg'))['options']['install_requires']
    return requires


def _build_and_inject_ac_index(whl_path):
    from awscli.autocomplete.generator import generate_index

    build_dir = os.path.join(ROOT_DIR, 'build')
    _create_dir_if_not_exists(build_dir)
    ac_index_build_name = os.path.join(build_dir, 'ac.index')
    _remove_file_if_exists(ac_index_build_name)
    print('Generating auto-complete index')
    generate_index(ac_index_build_name)
    unpack_wheel_dir = os.path.join(build_dir, 'unpacked_wheel')
    _remove_dir_if_exists(unpack_wheel_dir)
    print('Adding auto-complete index into wheel')
    with _open_wheel(whl_path, unpack_wheel_dir) as extracted_wheel_dir:
        os.rename(
            ac_index_build_name,
            os.path.join(extracted_wheel_dir, 'awscli', 'data', 'ac.index')
        )


@contextlib.contextmanager
def _open_wheel(whl_path, extract_dir='.'):
    _extract_zip(whl_path, extract_dir)
    yield extract_dir
    subprocess.run(
        [
            sys.executable, '-m', 'wheel', 'pack', '--dest',
            os.path.dirname(whl_path), extract_dir,
        ],
        check=True
    )


def _extract_zip(zipfile_name, target_dir):
    with zipfile.ZipFile(zipfile_name, 'r') as zf:
        for zf_info in zf.infolist():
            # Works around extractall not preserving file permissions:
            # https://bugs.python.org/issue15795
            extracted_path = zf.extract(zf_info, target_dir)
            os.chmod(extracted_path, zf_info.external_attr >> 16)


def _remove_file_if_exists(filename):
    if os.path.exists(filename):
        os.remove(filename)


def _remove_dir_if_exists(dirname):
    if os.path.isdir(dirname):
        shutil.rmtree(dirname)


def _create_dir_if_not_exists(dirname):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
