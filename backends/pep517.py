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
flit_core) in their pyproject.toml. However, the AWS CLI requires an
auto-complete index to function properly, and instead of directly committing
this index (which is MBs in size and changes with each API update) to the
repository, it is built as part of building the wheel. For the most part,
this in-tree backend just proxies to flit logic. The only exception
is that it builds the auto-complete index and injects it into the wheel
built by flit prior to returning.
"""
import re
import contextlib
import hashlib
import base64
import os
import glob
import tarfile
import shutil
import sys
import zipfile
from pathlib import Path

import flit_core.buildapi

ROOT_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT_DIR))
BIN_DIR = ROOT_DIR / "bin"
BUILD_DIR = ROOT_DIR / "build"
SCRIPTS = os.listdir(BIN_DIR)
AC_INDEX_REL_PATH = os.path.join("awscli", "data", "ac.index")


def build_sdist(sdist_directory, config_settings=None):
    sdist_filename = flit_core.buildapi.build_sdist(
        sdist_directory, config_settings
    )
    _update_sdist(os.path.join(sdist_directory, sdist_filename))
    return sdist_filename


def build_wheel(
    wheel_directory,
    config_settings=None,
    metadata_directory=None,
):
    whl_filename = flit_core.buildapi.build_wheel(
        wheel_directory, config_settings, metadata_directory
    )
    _inject_wheel_extras(os.path.join(wheel_directory, whl_filename))
    return whl_filename


def build_editable(
    wheel_directory,
    config_settings=None,
    metadata_directory=None,
):
    whl_filename = flit_core.buildapi.build_editable(
        wheel_directory, config_settings, metadata_directory
    )
    _inject_editable_wheel_extras(os.path.join(wheel_directory, whl_filename))
    _build_ac_index(ROOT_DIR / "awscli" / "data", rebuild=False)
    return whl_filename


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return flit_core.buildapi.prepare_metadata_for_build_wheel(
        metadata_directory, config_settings
    )


def prepare_metadata_for_build_editable(
    metadata_directory, config_settings=None
):
    return flit_core.buildapi.prepare_metadata_for_build_editable(
        metadata_directory, config_settings
    )


def get_requires_for_build_sdist(config_settings=None):
    return flit_core.buildapi.get_requires_for_build_sdist(config_settings)


def get_requires_for_build_wheel(config_settings=None):
    requires = flit_core.buildapi.get_requires_for_build_wheel(config_settings)
    # Generation of the auto-complete index requires importing from the
    # awscli package and iterating over the commands from the clidriver. In
    # order to be able to do this, it requires all of the CLI's runtime
    # dependencies to be present to avoid import errors.
    dependency_block_re = re.compile(
        r"dependencies = \[([\s\S]+?)\]\s", re.MULTILINE
    )
    extract_dependencies_re = re.compile(r'"(.+)"')
    with open(ROOT_DIR / "pyproject.toml", "r") as f:
        data = f.read()
    raw_dependencies = dependency_block_re.findall(data)[0]
    dependencies = extract_dependencies_re.findall(raw_dependencies)
    return dependencies + requires


get_requires_for_build_editable = get_requires_for_build_wheel


def _update_sdist(sdist_path):
    with _extracted_sdist_dir(sdist_path) as extracted_sdist_dir:
        # Remove the ac.index if it exists. flit backend includes all data
        # files so we need to remove it if it happens to have been built.
        _remove_file_if_exists(
            os.path.join(extracted_sdist_dir, AC_INDEX_REL_PATH)
        )
        _inject_extra_sdist_files(extracted_sdist_dir)


def _inject_extra_sdist_files(tar_root):
    # Flit backend has no way of including extra data files that are not a part
    # of the base package. This adds additional data files that are needed into
    # the sdist.
    for pattern in read_sdist_extras():
        pattern = pattern.replace("/", os.sep)
        pattern = os.path.join(ROOT_DIR, pattern)
        for filename in glob.glob(pattern, recursive=True):
            filename = os.path.relpath(filename, ROOT_DIR)
            path_to_add = os.path.join(ROOT_DIR, filename)
            target_path = os.path.join(tar_root, filename)
            _create_dir_if_not_exists(os.path.dirname(target_path))
            shutil.copy2(path_to_add, target_path)


def read_sdist_extras():
    with open(ROOT_DIR / "pyproject.toml", "r") as f:
        data = f.read()
    # This regex searches for the list content of sdist_extra_files
    # in the tool.awscli table within pyproject.toml.
    # We do this to avoid a dependency on tomli until it settles into
    # the stdlib.
    # "# end of cli tool section comment" is to ensure we don't parse
    # something with a similar name elsewhere.
    sdist_extra_block_re = re.compile(
        (
            r"[tool.awscli.sdist].*?"
            r"include = \[([\s\S]+?)\].*?"
            r"# end of cli sdist tool section"
        ),
        re.MULTILINE | re.DOTALL,
    )
    extract_dependencies_re = re.compile(r'"(.+)"')

    raw_extras = sdist_extra_block_re.findall(data)[0]
    extras = extract_dependencies_re.findall(raw_extras)
    return extras


def _rewrite_shebang(path):
    with open(path, "r") as f:
        lines = f.read().split("\n")
    # Rewrite shebang lines to be #!python to conform with PEP 427.
    if lines[0] == "#!/usr/bin/env python":
        lines[0] = "#!python"
    with open(path, "w") as f:
        f.write("\n".join(lines))


def _inject_wheel_extras(whl_path):
    with _extracted_wheel_dir(whl_path) as extracted_wheel_dir:
        _build_and_inject_ac_index(BUILD_DIR, extracted_wheel_dir)
        _inject_scripts(extracted_wheel_dir)


def _inject_editable_wheel_extras(whl_path):
    with _extracted_wheel_dir(whl_path) as extracted_wheel_dir:
        _inject_scripts(extracted_wheel_dir)


@contextlib.contextmanager
def _extracted_wheel_dir(whl_path):
    _create_dir_if_not_exists(BUILD_DIR)
    unpack_wheel_dir = os.path.join(BUILD_DIR, "unpacked_wheel")
    _remove_dir_if_exists(unpack_wheel_dir)
    with _open_wheel(whl_path, unpack_wheel_dir) as extracted_wheel_dir:
        yield extracted_wheel_dir


@contextlib.contextmanager
def _extracted_sdist_dir(sdist_path):
    _create_dir_if_not_exists(BUILD_DIR)
    unpack_sdist_dir = os.path.join(BUILD_DIR, "unpacked_sdist")
    _remove_dir_if_exists(unpack_sdist_dir)
    with _open_sdist(sdist_path, unpack_sdist_dir) as extracted_sdist_dir:
        yield extracted_sdist_dir


def _build_and_inject_ac_index(build_dir, extracted_wheel_dir):
    ac_index_build_name = _build_ac_index(build_dir)
    print("Adding auto-complete index into wheel")
    os.rename(
        ac_index_build_name,
        os.path.join(extracted_wheel_dir, AC_INDEX_REL_PATH),
    )


def _build_ac_index(build_dir, rebuild=True):
    from awscli.autocomplete.generator import generate_index

    ac_index_build_name = os.path.join(build_dir, "ac.index")
    if rebuild:
        _remove_file_if_exists(ac_index_build_name)
    elif os.path.exists(ac_index_build_name):
        return ac_index_build_name

    print("Generating auto-complete index")
    generate_index(ac_index_build_name)
    return ac_index_build_name


def _inject_scripts(extracted_wheel_dir):
    # There are two directories generated by flit:
    # 1) awscli/
    # 2) awscli-version.dist-info/
    # The easiest way to generate a data directory is to
    # find the dist-info directory and replace dist-info with
    # data.
    # There shold be exactly one, if not then something has gone horribly wrong
    # and crashing here is appropriate.
    dist_info_dir = [
        d for d in os.listdir(extracted_wheel_dir) if "dist-info" in d
    ][0]
    data_dir = os.path.join(
        extracted_wheel_dir,
        dist_info_dir.replace("dist-info", "data"),
    )
    _create_dir_if_not_exists(data_dir)
    scripts_dir = os.path.join(data_dir, "scripts")
    _create_dir_if_not_exists(scripts_dir)
    for script in SCRIPTS:
        target = os.path.join(scripts_dir, script)
        print(f"Injecting script {script} -> {target}")
        shutil.copy2(
            os.path.join(BIN_DIR, script),
            target,
        )
        _rewrite_shebang(target)
    _create_record_file(extracted_wheel_dir, dist_info_dir)


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


@contextlib.contextmanager
def _open_wheel(whl_path, extract_dir="."):
    _extract_zip(whl_path, extract_dir)
    yield extract_dir
    _compress_whl(whl_path, extract_dir)


@contextlib.contextmanager
def _open_sdist(sdist_path, extract_dir="."):
    _extract_sdist(sdist_path, extract_dir)
    basename = os.listdir(extract_dir)[0]
    tar_root = os.path.join(extract_dir, basename)
    yield tar_root
    _compress_sdist(sdist_path, tar_root)


def _extract_sdist(sdist_path, target_dir):
    sdist = tarfile.open(sdist_path)
    sdist.extractall(target_dir)
    sdist.close()


def _compress_sdist(sdist_path, target_dir):
    with tarfile.open(sdist_path, "w:gz") as tar:
        tar.add(target_dir, arcname=os.path.basename(target_dir))


def _extract_zip(zipfile_name, target_dir):
    with zipfile.ZipFile(zipfile_name, "r") as zf:
        for zf_info in zf.infolist():
            # Works around extractall not preserving file permissions:
            # https://bugs.python.org/issue15795
            extracted_path = zf.extract(zf_info, target_dir)
            os.chmod(extracted_path, zf_info.external_attr >> 16)


def _compress_whl(whl_file_path, target_dir):
    _remove_file_if_exists(whl_file_path)
    shutil.make_archive(whl_file_path, "zip", target_dir)
    os.rename(whl_file_path + ".zip", whl_file_path)


def _remove_file_if_exists(filename):
    if os.path.exists(filename):
        os.remove(filename)


def _remove_dir_if_exists(dirname):
    if os.path.isdir(dirname):
        shutil.rmtree(dirname)


def _create_dir_if_not_exists(dirname):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
