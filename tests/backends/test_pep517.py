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
import os
import re
import shutil

import pytest
import setuptools.config

import awscli
import backends.pep517


@pytest.fixture
def config_settings():
    return {}


@pytest.fixture
def repo_root():
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    )


@pytest.fixture(autouse=True)
def cd_to_repo_root(repo_root):
    # In general, we want to be at the root of the repository when running
    # PEP 517 hooks since setuptools generally expects you to be there when
    # running its hooks (which we use).
    original = os.getcwd()
    os.chdir(repo_root)
    yield
    os.chdir(original)


def assert_dist_info_correctness(dist_info_dir):
    # A helper utility to do sanity checks on the generated wheel .dist-info
    # directory. Right now we only look at the generated METADATA file,
    # but this could be expanded to other files that are expected to be in
    # the .dist-info directory
    metadata_file = dist_info_dir.join('METADATA')
    assert metadata_file.check()
    metadata_content = metadata_file.read()
    assert 'Metadata-Version: 2.1' in metadata_content
    assert 'Name: awscli' in metadata_content
    assert f'Version: {awscli.__version__}' in metadata_content


def assert_dependency_in_requirements(package_name, requirements):
    pattern = re.compile(rf'^{package_name}.*$')
    for req in requirements:
        if pattern.match(req):
            return
    raise AssertionError(
        f'Could not find package: "{package_name}" in '
        f'requirements: {requirements}')


def test_build_sdist(tmpdir, config_settings):
    sdist_name = backends.pep517.build_sdist(str(tmpdir), config_settings)
    expected_sdist_name = f'awscli-{awscli.__version__}.tar.gz'
    assert sdist_name == expected_sdist_name

    path_to_sdist = tmpdir.join(sdist_name)
    assert path_to_sdist.check()

    # Unpack the tarball and do some sanity checks to make sure the
    # sdist looks correct.
    shutil.unpack_archive(path_to_sdist, tmpdir)
    unpacked_sdist = tmpdir.join(f'awscli-{awscli.__version__}')
    assert unpacked_sdist.join('setup.cfg').check()
    assert unpacked_sdist.join('awscli', '__init__.py').check()

    # Make sure the backends package is in the sdist so users can build
    # a wheel from an sdist using PEP 517.
    assert unpacked_sdist.join('backends', 'pep517.py').check()

    # We do not build the ac.index in building the sdist. So we want to make
    # sure it is not being included.
    assert not unpacked_sdist.join('awscli', 'data', 'ac.index').check()


def test_build_wheel(tmpdir, config_settings):
    wheel_name = backends.pep517.build_wheel(str(tmpdir), config_settings)
    expected_wheel_name = f'awscli-{awscli.__version__}-py3-none-any.whl'
    assert wheel_name == expected_wheel_name

    path_to_wheel = tmpdir.join(wheel_name)
    assert path_to_wheel.check()

    # Unpack the wheel and do some sanity checks to make sure the
    # sdist looks correct.
    unpacked_wheel_dir = tmpdir.join('unpacked_wheel')
    unpacked_wheel_dist_info = unpacked_wheel_dir.join(
        f'awscli-{awscli.__version__}.dist-info')
    shutil.unpack_archive(path_to_wheel, unpacked_wheel_dir, 'zip')
    assert unpacked_wheel_dir.join('awscli', '__init__.py').check()
    assert_dist_info_correctness(unpacked_wheel_dist_info)

    # We do not want the backends package included as part of the
    # environment's site-packages so it should not exist in the wheel
    assert not unpacked_wheel_dir.join('backends', 'pep517.py').check()

    # The wheel should have built the auto-complete index and repacked it
    # into the wheel.
    assert unpacked_wheel_dir.join('awscli', 'data', 'ac.index').check()
    records_content = unpacked_wheel_dist_info.join('RECORD').read()
    assert '/'.join(['awscli', 'data', 'ac.index']) in records_content


def test_prepare_metadata_for_build_wheel(tmpdir, config_settings):
    dist_info_dirname = backends.pep517.prepare_metadata_for_build_wheel(
        str(tmpdir), config_settings)
    assert dist_info_dirname == 'awscli.dist-info'
    assert_dist_info_correctness(tmpdir.join(dist_info_dirname))


def test_get_requires_for_build_sdist(config_settings):
    requirements = backends.pep517.get_requires_for_build_sdist(
        config_settings)
    assert requirements == []


def test_get_requires_for_build_wheel(config_settings, repo_root):
    requirements = backends.pep517.get_requires_for_build_wheel(
        config_settings)
    expected_requirements = []
    # Setuptools relies on wheel under the hood to generate the wheel. So it
    # specifies wheel as a build requirement.
    expected_requirements += ['wheel']
    # Generation of the auto-complete index requires importing from the
    # awscli package and iterating over the commands from the clidriver. In
    # order to be able to do this, it requires all of the CLI's runtime
    # dependencies to be present to avoid import errors. So we want to make
    # sure whatever is being returned from the PEP 517 hook matches the runtime
    # dependencies declared in the setup.cfg
    expected_requirements += setuptools.config.read_configuration(
        os.path.join(repo_root, 'setup.cfg'))['options']['install_requires']

    assert requirements == expected_requirements
    # Also assert that some of the runtime dependencies we expect are actually
    # being from the setup.cfg
    assert_dependency_in_requirements('urllib3', requirements)
    assert_dependency_in_requirements('awscrt', requirements)
