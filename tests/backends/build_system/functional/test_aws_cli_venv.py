# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import contextlib
import json
import re
import os
import sys
import pathlib
import subprocess

import pytest
import flit_core.buildapi

from build_system.awscli_venv import AwsCliVenv
from build_system.constants import ArtifactType

from awscli.testutils import skip_if_windows
from awscli.testutils import if_windows
from backends.build_system.constants import BIN_DIRNAME, PYTHON_EXE_NAME

ROOT_DIR = pathlib.Path(__file__).parents[4]


@contextlib.contextmanager
def cd(dirname):
    original = os.getcwd()
    os.chdir(dirname)
    try:
        yield
    finally:
        os.chdir(original)


@pytest.fixture(scope="session")
def venv_path(tmp_path_factory):
    return tmp_path_factory.mktemp("venv")


@pytest.fixture(scope="session")
def cli_venv(venv_path):
    venv = AwsCliVenv(venv_path)
    venv.create()
    return venv


class TestAwsCliVenv:
    def _normalize_dependency_entry(self, dep: str) -> str:
        dep = re.split("[<=>]", dep)[0]
        dep = dep.rstrip("<=>")
        dep = dep.lower()
        dep = dep.replace("-", "_")
        return dep

    def _normalize_dist_info_name(self, name: str) -> str:
        name = name.split("-")[0]
        name = name.lower()
        return name

    def _get_install_requires(self):
        with cd(ROOT_DIR):
            requires = flit_core.buildapi.get_requires_for_build_wheel()
        # Generation of the auto-complete index requires importing from the
        # awscli package and iterating over the commands from the clidriver. In
        # order to be able to do this, it requires all of the CLI's runtime
        # dependencies to be present to avoid import errors.
        dependency_block_re = re.compile(
            r"dependencies = \[([\s\S]+?)\]", re.MULTILINE
        )
        extract_dependencies_re = re.compile(r'"(.+)"')
        with open(ROOT_DIR / "pyproject.toml", "r") as f:
            data = f.read()
        raw_dependencies = dependency_block_re.findall(data)[0]
        dependencies = extract_dependencies_re.findall(raw_dependencies)
        return dependencies + requires

    def _python_version(self) -> str:
        info = sys.version_info
        return f"python{info[0]}.{info[1]}"

    def _site_packages_dir(self, venv_path: pathlib.PurePath) -> str:
        site_path = [path for path in json.loads(
            subprocess.check_output(
                [
                    venv_path / BIN_DIRNAME / PYTHON_EXE_NAME,
                    "-c",
                    "import site, json; print(json.dumps(site.getsitepackages()))",
                ]
            )
            .decode()
            .strip()
        ) if "site-packages" in path][0]
        return site_path

    @skip_if_windows("Posix virtualenv")
    def test_create(self, tmp_path_factory):
        path = tmp_path_factory.mktemp("test_create")
        venv = AwsCliVenv(path)
        venv.create()

        venv_dirs = set(os.listdir(path))
        required_files = [
            "bin",
            "include",
            "pyvenv.cfg",
        ]
        for required_file in required_files:
            assert required_file in venv_dirs

    @if_windows("Windows virtualenv")
    def test_create_windows(self, tmp_path_factory):
        path = tmp_path_factory.mktemp("test_create")
        venv = AwsCliVenv(path)
        venv.create()

        venv_dirs = set(os.listdir(path))
        required_files = [
            "Scripts",
            "Include",
            "Lib",
            "pyvenv.cfg",
        ]
        for required_file in required_files:
            assert required_file in venv_dirs

    @skip_if_windows("Posix bootstrap")
    def test_bootstrap(self, cli_venv, venv_path):
        site_package_path = self._site_packages_dir(venv_path)

        prior_site_dir = set(os.listdir(site_package_path))
        cli_venv.bootstrap(
            ArtifactType.SYSTEM_SANDBOX.value, download_deps=False
        )
        post_site_dir = set(os.listdir(site_package_path))

        # Check that parent packages were installed
        added_packages = {
            self._normalize_dist_info_name(p)
            for p in post_site_dir - prior_site_dir
            if "dist-info" in p or "egg-info" in p
        }

        expected_packages = {
            self._normalize_dependency_entry(r)
            for r in self._get_install_requires()
        }
        missing_packages = expected_packages - added_packages

        assert missing_packages == set()

        # Check that the CLI is installed
        cli_path = (
            venv_path
            / "lib"
            / self._python_version()
            / "site-packages"
            / "awscli"
        )
        assert os.path.isdir(cli_path) is True

        # Make sure the ac.index got generated and injected correctly.
        ac_index_path = cli_path / "data" / "ac.index"
        assert os.path.exists(ac_index_path) is True

    @if_windows("Windows bootstrap")
    def test_bootstrap_windows(self, cli_venv, venv_path):
        site_package_path = self._site_packages_dir(venv_path)

        prior_site_dir = set(os.listdir(site_package_path))
        cli_venv.bootstrap(
            ArtifactType.SYSTEM_SANDBOX.value, download_deps=False
        )
        post_site_dir = set(os.listdir(site_package_path))

        # Check that parent packages were installed
        added_packages = {
            self._normalize_dist_info_name(p)
            for p in post_site_dir - prior_site_dir
            if "dist-info" in p
        }

        expected_packages = {
            self._normalize_dependency_entry(r)
            for r in self._get_install_requires()
        }
        missing_packages = expected_packages - added_packages

        assert missing_packages == set()

        # Check that the CLI is installed
        cli_path = venv_path / "Lib" / "site-packages" / "awscli"
        assert os.path.isdir(cli_path) is True

        # Make sure the ac.index got generated and injected correctly.
        ac_index_path = cli_path / "data" / "ac.index"
        assert os.path.exists(ac_index_path) is True

    @skip_if_windows("No bin dir on windows")
    def test_bin_dir(self, cli_venv, venv_path):
        assert cli_venv.bin_dir == os.path.join(venv_path, "bin")

    @if_windows("Scripts dir is only on windows")
    def test_scripts_dir(self, cli_venv, venv_path):
        assert cli_venv.bin_dir == os.path.join(venv_path, "Scripts")

    @skip_if_windows("Python binary location on posix")
    def test_python_exe(self, cli_venv, venv_path):
        assert cli_venv.python_exe == os.path.join(venv_path, "bin", "python")

    @if_windows("Python binary location on win")
    def test_python_exe_windows(self, cli_venv, venv_path):
        assert cli_venv.python_exe == os.path.join(
            venv_path, "Scripts", "python.exe"
        )
