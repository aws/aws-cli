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

from awscli.testutils import skip_if_windows
from tests.backends.build_system.integration import BaseArtifactTest
from tests.backends.build_system.integration import VEnvWorkspace


WINDOWS_SKIP_REASON = "./configure tests do not run nativly on windows"


class TestMakeInstall(BaseArtifactTest):
    def assert_venv_installed_correctly(self, bin_path, lib_path):
        venv_dir = lib_path / "aws-cli"
        self.assert_built_venv_is_correct(venv_dir)

        bins = set(os.listdir(bin_path))
        assert bins == {"aws", "aws_completer"}

        aws_exe = bin_path / "aws"
        self.assert_version_string_is_correct(aws_exe)

    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_install(self, workspace: VEnvWorkspace):
        workspace.configure(
            install_type="system-sandbox",
            download_deps=True,
        )
        workspace.make()
        workspace.make(
            [
                "install",
                f"libdir={workspace.lib_path}",
                f"bindir={workspace.bin_path}",
            ]
        )
        self.assert_venv_installed_correctly(
            workspace.bin_path, workspace.lib_path
        )

    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_install_prefix(self, workspace):
        workspace.configure(
            install_type="system-sandbox",
            download_deps=True,
        )

        workspace.make()
        workspace.make(
            [
                "install",
                f"prefix={workspace.install_path}",
            ]
        )

        self.assert_venv_installed_correctly(
            workspace.bin_path, workspace.lib_path
        )

    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_install_destdir(self, workspace):
        workspace.configure(
            install_type="system-sandbox",
            download_deps=True,
        )

        workspace.make()
        workspace.make(
            [
                "install",
                f"prefix=/install",
            ],
            env={"DESTDIR": str(workspace.path)},
        )

        self.assert_venv_installed_correctly(
            workspace.bin_path, workspace.lib_path
        )

    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_uninstall(self, workspace: VEnvWorkspace):
        workspace.configure(
            install_type="system-sandbox",
            download_deps=True,
        )
        workspace.make()
        workspace.make(
            [
                "install",
                f"libdir={workspace.lib_path}",
                f"bindir={workspace.bin_path}",
            ]
        )
        workspace.make(
            [
                "uninstall",
                f"libdir={workspace.lib_path}",
                f"bindir={workspace.bin_path}",
            ]
        )

        assert os.listdir(workspace.bin_path) == []
        assert os.listdir(workspace.lib_path) == []


class TestMake(BaseArtifactTest):
    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_exe_with_deps(self, workspace: VEnvWorkspace):
        workspace.configure(
            install_type="portable-exe",
            download_deps=True,
        )
        workspace.make()

        self.assert_built_exe_is_correct(workspace.cli_path)

    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_exe_without_deps(self, workspace: VEnvWorkspace):
        workspace.install_dependencies()
        workspace.install_pyinstaller()
        workspace.configure(install_type="portable-exe")
        workspace.make()

        self.assert_built_exe_is_correct(workspace.cli_path)

    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_venv_with_deps(self, workspace: VEnvWorkspace):
        workspace.configure(
            install_type="system-sandbox",
            download_deps=True,
        )
        workspace.make()

        self.assert_built_venv_is_correct(workspace.build_path)

    @skip_if_windows(WINDOWS_SKIP_REASON)
    def test_venv_without_deps(self, workspace: VEnvWorkspace):
        workspace.install_dependencies()
        workspace.configure(
            install_type="system-sandbox",
        )
        workspace.make()

        self.assert_built_venv_is_correct(workspace.build_path)
