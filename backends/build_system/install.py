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
import os
import functools

from constants import CLI_SCRIPTS
from constants import IS_WINDOWS
from constants import BIN_DIRNAME
from constants import PYTHON_EXE_NAME
from constants import ArtifactType
from utils import Utils


WINDOWS_CMD_TEMPLATE = """@echo off
{path} %*
"""

class Uninstaller:
    def __init__(self, utils: Utils = None):
        if utils is None:
            utils = Utils()
        self._utils = utils

    def uninstall(self, install_dir: str, bin_dir: str):
        if self._utils.isdir(install_dir):
            self._utils.rmtree(install_dir)
        for exe in CLI_SCRIPTS:
            exe_path = os.path.join(bin_dir, exe)
            if self._utils.islink(exe_path) or self._utils.path_exists(exe_path):
                self._utils.remove(exe_path)


class Installer:
    def __init__(self, build_dir: str, utils: Utils = None):
        self._build_dir = build_dir
        if utils is None:
            utils = Utils()
        self._utils = utils

    def install(self, install_dir: str, bin_dir: str):
        self._copy_to_install_dir(install_dir)
        self._install_executables(install_dir, bin_dir)

    @functools.cached_property
    def artifact_type(self):
        if self._utils.isdir(os.path.join(self._build_dir, "exe")):
            return ArtifactType.PORTABLE_EXE
        return ArtifactType.SYSTEM_SANDBOX

    def _copy_to_install_dir(self, install_dir):
        build_lib = self._get_build_lib()
        if self._utils.isdir(install_dir):
            self._utils.rmtree(install_dir)
        self._utils.copy_directory(build_lib, install_dir)
        if self.artifact_type == ArtifactType.SYSTEM_SANDBOX:
            self._update_script_header(install_dir)

    def _get_build_lib(self):
        if self.artifact_type == ArtifactType.PORTABLE_EXE:
            return os.path.join(self._build_dir, "exe", "aws", "dist")
        return os.path.join(self._build_dir, "venv")

    def _install_executables(self, install_dir, bin_dir):
        if IS_WINDOWS and self.artifact_type == ArtifactType.PORTABLE_EXE:
            self._install_executables_on_windows(install_dir, bin_dir)
        else:
            self._symlink_executables(install_dir, bin_dir)

    def _install_executables_on_windows(self, install_dir, bin_dir):
        with open(os.path.join(bin_dir, "aws.cmd"), "w") as f:
            f.write(WINDOWS_CMD_TEMPLATE.format(path=os.path.join(install_dir, "aws.exe")))

    def _symlink_executables(self, install_dir, bin_dir):
        if not self._utils.path_exists(bin_dir):
            self._utils.makedirs(bin_dir)
        for exe in CLI_SCRIPTS:
            exe_path = os.path.join(bin_dir, exe)
            if self._utils.islink(exe_path):
                self._utils.remove(exe_path)
            self._utils.symlink(
                self._get_install_bin_exe(install_dir, exe), exe_path
            )

    def _get_install_bin_exe(self, install_dir, exe):
        install_bin_dir = install_dir
        if self.artifact_type == ArtifactType.SYSTEM_SANDBOX:
            install_bin_dir = os.path.join(install_dir, BIN_DIRNAME)
        return os.path.join(install_bin_dir, exe)

    def _update_script_header(self, install_dir):
        python_exe_path = self._get_install_bin_exe(
            install_dir, PYTHON_EXE_NAME
        )
        for exe in CLI_SCRIPTS:
            exe_path = self._get_install_bin_exe(install_dir, exe)
            lines = self._utils.read_file_lines(exe_path)
            lines[0] = self._utils.get_script_header(python_exe_path)
            self._utils.write_file(exe_path, "".join(lines))
