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
import hashlib
import base64
from pathlib import Path

import pytest
import py

import awscli
import backends.pep517


@pytest.fixture
def config_settings():
    return {}


@pytest.fixture
def repo_root():
    return str(Path(__file__).parents[2])


@pytest.fixture
def preserve_ac_index(repo_root, tmpdir):
    # Some functional tests will build the ac.index in-place.
    # In case there was an existing one we will need to move it out of the
    # way and then back once the test is complete.
    # If thre is no ac.index file, we need to clean up the one generated
    # by the tests.
    ac_index_path = os.path.join(repo_root, "awscli", "data", "ac.index")
    save_location = tmpdir.join("ac.index")
    if os.path.isfile(ac_index_path):
        os.rename(ac_index_path, save_location)
    yield
    if os.path.isfile(save_location):
        os.rename(save_location, ac_index_path)
    else:
        os.remove(ac_index_path)


@pytest.fixture(autouse=True)
def cd_to_repo_root(repo_root):
    # In general, we want to be at the root of the repository when running
    # PEP 517 hooks.
    original = os.getcwd()
    os.chdir(repo_root)
    yield
    os.chdir(original)


def assert_dist_info_correctness(dist_info_dir):
    # A helper utility to do sanity checks on the generated wheel .dist-info
    # directory. Right now we only look at the generated METADATA file,
    # but this could be expanded to other files that are expected to be in
    # the .dist-info directory
    metadata_file = dist_info_dir.join("METADATA")
    assert metadata_file.check()
    metadata_content = metadata_file.read()
    assert "Metadata-Version: 2.1" in metadata_content
    assert "Name: awscli" in metadata_content
    assert f"Version: {awscli.__version__}" in metadata_content


def assert_dependency_in_requirements(package_name, requirements):
    pattern = re.compile(rf"^{package_name}.*$")
    for req in requirements:
        if pattern.match(req):
            return
    raise AssertionError(
        f'Could not find package: "{package_name}" in '
        f"requirements: {requirements}"
    )


def test_build_sdist(tmpdir, config_settings):
    sdist_name = backends.pep517.build_sdist(str(tmpdir), config_settings)
    expected_sdist_name = f"awscli-{awscli.__version__}.tar.gz"
    assert sdist_name == expected_sdist_name

    path_to_sdist = tmpdir.join(sdist_name)
    assert path_to_sdist.check()

    # Unpack the tarball and do some sanity checks to make sure the
    # sdist looks correct.
    shutil.unpack_archive(path_to_sdist, tmpdir)
    unpacked_sdist = tmpdir.join(f"awscli-{awscli.__version__}")

    assert unpacked_sdist.join("pyproject.toml").check()
    assert unpacked_sdist.join("awscli", "__init__.py").check()
    assert unpacked_sdist.join("CHANGELOG.rst").check()

    # Make sure the backends package is in the sdist so users can build
    # a wheel from an sdist using PEP 517.
    assert unpacked_sdist.join("backends", "pep517.py").check()

    # Make sure the bin directory is included.
    assert unpacked_sdist.join("bin", "aws").check()

    # We do not build the ac.index in building the sdist. So we want to make
    # sure it is not being included.
    assert not unpacked_sdist.join("awscli", "data", "ac.index").check()


def test_build_wheel(tmpdir, config_settings, repo_root):
    wheel_name = backends.pep517.build_wheel(str(tmpdir), config_settings)
    expected_wheel_name = f"awscli-{awscli.__version__}-py3-none-any.whl"
    assert wheel_name == expected_wheel_name

    path_to_wheel = tmpdir.join(wheel_name)
    assert path_to_wheel.check()

    # Unpack the wheel and do some sanity checks to make sure the
    # sdist looks correct.
    unpacked_wheel_dir = tmpdir.join("unpacked_wheel")
    unpacked_wheel_dist_info = unpacked_wheel_dir.join(
        f"awscli-{awscli.__version__}.dist-info"
    )
    shutil.unpack_archive(path_to_wheel, unpacked_wheel_dir, "zip")
    assert unpacked_wheel_dir.join("awscli", "__init__.py").check()
    assert_dist_info_correctness(unpacked_wheel_dist_info)

    # Make sure scripts were included and the shebang got re-written
    # correctly.
    unpacked_wheel_data = unpacked_wheel_dir.join(
        f"awscli-{awscli.__version__}.data"
    )
    assert unpacked_wheel_data.join("scripts", "aws").check()
    assert "#!python" in unpacked_wheel_data.join("scripts", "aws").read()

    # We do not want the backends package included as part of the
    # environment's site-packages so it should not exist in the wheel
    assert not unpacked_wheel_dir.join("backends", "pep517.py").check()

    # The wheel should have built the auto-complete index and repacked it
    # into the wheel.
    assert unpacked_wheel_dir.join("awscli", "data", "ac.index").check()
    records_content = unpacked_wheel_dist_info.join("RECORD").read()
    assert "/".join(["awscli", "data", "ac.index"]) in records_content

    _create_record_file(
        unpacked_wheel_dir, os.path.split(unpacked_wheel_dist_info)[-1]
    )
    expected_records_content = unpacked_wheel_dist_info.join("RECORD").read()
    assert records_content == expected_records_content


def test_build_editable(tmpdir, config_settings, repo_root, preserve_ac_index):
    wheel_name = backends.pep517.build_editable(str(tmpdir), config_settings)
    path_to_wheel = tmpdir.join(wheel_name)

    unpacked_wheel_dir = tmpdir.join("unpacked_wheel")
    unpacked_wheel_dist_info = unpacked_wheel_dir.join(
        f"awscli-{awscli.__version__}.dist-info"
    )
    unpacked_wheel_data = unpacked_wheel_dir.join(
        f"awscli-{awscli.__version__}.data"
    )
    shutil.unpack_archive(path_to_wheel, unpacked_wheel_dir, "zip")

    assert unpacked_wheel_dist_info.check()
    assert unpacked_wheel_data.check()
    assert unpacked_wheel_data.join("scripts").join("aws").check()
    assert unpacked_wheel_data.join("scripts").join("aws_completer").check()

    # Check that the ac.index got created in the base repo. The
    # relocate_ac_index fixture moves the existing one out of the repo before
    # this tests runs so if the file exists it is because it was generated by
    # backends.pep517.build_editable.
    assert (
        py.path.local(repo_root)
        .join("awscli")
        .join("data")
        .join("ac.index")
        .check()
    )

    pth_file = unpacked_wheel_dir.join("awscli.pth")
    assert pth_file.check()
    assert pth_file.read() == repo_root


def test_prepare_metadata_for_build_wheel(tmpdir, config_settings):
    dist_info_dirname = backends.pep517.prepare_metadata_for_build_wheel(
        str(tmpdir), config_settings
    )
    assert dist_info_dirname.startswith("awscli")
    assert dist_info_dirname.endswith(".dist-info")
    assert_dist_info_correctness(tmpdir.join(dist_info_dirname))


def test_prepare_metadata_for_build_editable(tmpdir, config_settings):
    dist_info_dirname = backends.pep517.prepare_metadata_for_build_editable(
        str(tmpdir), config_settings
    )
    assert dist_info_dirname.startswith("awscli")
    assert dist_info_dirname.endswith(".dist-info")
    assert_dist_info_correctness(tmpdir.join(dist_info_dirname))


def test_get_requires_for_build_sdist(config_settings):
    requirements = backends.pep517.get_requires_for_build_sdist(
        config_settings
    )
    assert requirements == []


def test_get_requires_for_build_wheel(config_settings, repo_root):
    requirements = backends.pep517.get_requires_for_build_wheel(
        config_settings
    )
    expected_requirements = [
        "colorama",
        "docutils",
        "cryptography",
        "ruamel.yaml",
        "prompt-toolkit",
        "distro",
        "awscrt",
        "python-dateutil",
        "jmespath",
        "urllib3",
    ]
    assert len(expected_requirements) == len(requirements)
    for expected_requirement in expected_requirements:
        assert_dependency_in_requirements(expected_requirement, requirements)


def test_read_sdist_extras():
    expected_extras = {
        "backends/**/*.py",
        "bin/*",
        "CHANGELOG.rst",
    }
    extras = set(backends.pep517.read_sdist_extras())

    assert extras == expected_extras


# Since we regenerate the RECORD file in the wheel directory this is a
# duplicate of the logic from that file. At the time of writing the
# RECORD file in the wheel is the same as the originally generated one
# using setuptools sans the metadata file.
# Comparing the generated wheel RECORD file to one generated by this
# snippet should alert us if we break anything in the pep517 module.
def _create_record_file(base_dir, dist_info_dir):
    entries = []
    for base, dirs, files in os.walk(base_dir):
        dirs.sort()
        for filename in sorted(files):
            # Record file has its own special entry at the end
            if filename == "RECORD":
                continue
            target = os.path.join(base, filename)
            # Path entries in record file are unix style
            path = os.path.relpath(target, base_dir).replace(os.sep, "/")
            digest = _get_b64_sha256(target)
            size = os.path.getsize(target)
            record_entry = f"{path},sha256={digest},{size}"
            entries.append(record_entry)
    entries.append(f"{dist_info_dir}/RECORD,,")
    record_path = os.path.join(base_dir, dist_info_dir, "RECORD")
    with open(record_path, "w") as f:
        f.write("\n".join(entries) + "\n")


def _get_b64_sha256(path):
    with open(path, "rb") as f:
        file_bytes = f.read()
        digest_bytes = hashlib.sha256(file_bytes).digest()
    encoded = base64.urlsafe_b64encode(digest_bytes).rstrip(b"=")
    return encoded.decode("utf-8")
