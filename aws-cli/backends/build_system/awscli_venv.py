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
import json
import os
import pathlib
import site
import subprocess
import sys

from constants import (
    BIN_DIRNAME,
    CLI_SCRIPTS,
    DISTRIBUTION_SOURCE_SANDBOX,
    DOWNLOAD_DEPS_BOOTSTRAP_LOCK,
    IS_WINDOWS,
    PORTABLE_EXE_REQUIREMENTS_LOCK,
    PYTHON_EXE_NAME,
    ROOT_DIR,
    SYSTEM_SANDBOX_REQUIREMENTS_LOCK,
    ArtifactType,
)
from utils import Utils


class AwsCliVenv:
    _PARENT_SCRIPTS_TO_COPY = [
        "pyinstaller",
        "pyinstaller.exe",
    ]

    def __init__(self, venv_dir: str, utils: Utils = None):
        self._venv_dir = venv_dir
        if utils is None:
            utils = Utils()
        self._utils = utils

    def create(self):
        self._utils.create_venv(self._venv_dir, with_pip=True)

    def bootstrap(
        self, artifact_type: ArtifactType, download_deps: bool = False
    ):
        if download_deps:
            self._install_requirements(DOWNLOAD_DEPS_BOOTSTRAP_LOCK)
            if artifact_type == ArtifactType.PORTABLE_EXE.value:
                self._install_requirements(PORTABLE_EXE_REQUIREMENTS_LOCK)
            else:
                self._install_requirements(SYSTEM_SANDBOX_REQUIREMENTS_LOCK)
        else:
            self._copy_parent_packages()
        self._install_awscli()
        self._update_metadata()
        self._update_windows_script_header()

    def _copy_parent_packages(self):
        for site_package in site.getsitepackages():
            self._remove_packages_being_replaced(site_package)
            self._utils.copy_directory_contents_into(
                site_package, self._site_packages()
            )
        parent_scripts = pathlib.Path(sys.executable).parents[0]
        for script in self._PARENT_SCRIPTS_TO_COPY:
            source = os.path.join(parent_scripts, script)
            if self._utils.path_exists(source):
                self._utils.copy_file(
                    source, os.path.join(self.bin_dir, script)
                )

    def _remove_packages_being_replaced(self, source_site_packages):
        # Remove packages in the new venv that we're about to replace.
        # The venv already contains the user's pip from when it was created,
        # matching their interpreter's version. We then copy packages in to
        # the venv during 'bootstrap' above when download_deps=False. The pip
        # we copy in is our pinned pip if the parent environment has our
        # bootstrap requirements installed, and otherwise the user's own.
        # copy_directory_contents_into doesn't delete existing content first,
        # which can lead to a non-functional mix of files from different pip
        # versions.
        destination = self._site_packages()
        replaced = {
            self._distribution_key(name)
            for name in self._utils.listdir(source_site_packages)
        }
        for name in self._utils.listdir(destination):
            if self._distribution_key(name) not in replaced:
                continue
            path = os.path.join(destination, name)
            if self._utils.isdir(path) and not self._utils.islink(path):
                self._utils.rmtree(path)
            else:
                self._utils.remove(path)

    def _distribution_key(self, name):
        # Metadata directory names include the version, so they need to be
        # matched on the distribution name alone in order to remove metadata
        # belonging to a different version of the same distribution.
        if name.endswith((".dist-info", ".egg-info")):
            return name.split("-")[0]
        return name

    def _install_requirements(self, requirements_file, cwd=None):
        self._pip_install(
            ["--no-build-isolation", "-r", requirements_file],
            cwd=cwd,
        )

    def _install_awscli(self):
        self._pip_install(
            [
                ROOT_DIR,
                "--no-build-isolation",
                "--no-cache-dir",
                "--no-index",
            ]
        )

    def _update_windows_script_header(self):
        # When installing to a venv pip will rewrite shebang lines
        # to reference the relevant virutalenv directly. This is not
        # the case for aws.cmd which is our own windows cmd file
        # and does not have a shebang that is re-writable.
        # We need to manually overwrite the header line in this script
        # to reference the current virtualenv.
        # If we are not on Windows then this is not relevant.
        if not IS_WINDOWS:
            return
        python_exe_path = os.path.join(self.bin_dir, "python.exe")
        exe_path = os.path.join(self.bin_dir, "aws.cmd")
        lines = self._utils.read_file_lines(exe_path)
        lines[0] = self._utils.get_script_header(python_exe_path)
        self._utils.write_file(exe_path, "".join(lines))

    def _update_metadata(self):
        self._utils.update_metadata(
            self._site_packages(),
            distribution_source=DISTRIBUTION_SOURCE_SANDBOX,
        )

    @property
    def bin_dir(self):
        return os.path.join(self._venv_dir, BIN_DIRNAME)

    @property
    def python_exe(self):
        return os.path.join(self.bin_dir, PYTHON_EXE_NAME)

    def _pip_install(self, args, cwd=None):
        args = [self.python_exe, "-m", "pip", "install"] + args
        run_kwargs = {"check": True}
        if IS_WINDOWS:
            args = " ".join([str(a) for a in args])
            # The tests on windows will fail when executed with
            # the wrapper test runner script in scripts/ci if this
            # is not executed from shell.
            run_kwargs["shell"] = True
        if cwd is not None:
            run_kwargs["cwd"] = cwd
        self._utils.run(args, **run_kwargs)

    def _site_packages(self) -> str:
        # On windows the getsitepackages can return the root venv dir.
        # So instead of just taking the first entry, we need to take the
        # first entry that contains the string "site-packages" in the path.
        site_path = [
            path
            for path in json.loads(
                subprocess.check_output(
                    [
                        self.python_exe,
                        "-c",
                        "import site, json; print(json.dumps(site.getsitepackages()))",
                    ]
                )
                .decode()
                .strip()
            )
            if "site-packages" in path
        ][0]
        return site_path
