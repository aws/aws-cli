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

import pytest

from build_system.constants import PYINSTALLER_DIR
from build_system.constants import EXE_ASSETS_DIR
from build_system.constants import BIN_DIRNAME
from build_system.constants import PYINSTALLER_EXE_NAME
from build_system.exe import ExeBuilder


class FakeUtils:
    def __init__(self, prior_build_dir=False):
        self._prior_build_dir = prior_build_dir
        self.calls = []

    def isdir(self, path: str) -> bool:
        self.calls.append(("isdir", path))
        return self._prior_build_dir

    def run(self, command, **kwargs):
        self.calls.append(("run", command, kwargs))

    def copy_directory(self, src, dst):
        self.calls.append(("copy_directory", src, dst))

    def copy_directory_contents_into(self, src, dst):
        self.calls.append(("copy_directory_contents_into", src, dst))

    def update_metadata(self, dirname, **kwargs):
        self.calls.append(("update_metadata", dirname, kwargs))

    def rmtree(self, path):
        self.calls.append(("rmtree", path))


class FakeAwsCliVenv:
    @property
    def bin_dir(self) -> str:
        return BIN_DIRNAME

    @property
    def python_exe(self) -> str:
        return "python"


@pytest.fixture
def fake_aws_cli_venv():
    return FakeAwsCliVenv()


class TestExe:
    def _expected_build_tasks(self):
        return [
            # Check if build dir is present
            ("isdir", os.path.join("workspace", "dist")),
            # Build aws and copy into final directory
            (
                "run",
                [
                    "python",
                    os.path.join(BIN_DIRNAME, PYINSTALLER_EXE_NAME),
                    os.path.join(PYINSTALLER_DIR, "aws.spec"),
                    "--distpath",
                    os.path.join("workspace", "dist"),
                    "--workpath",
                    os.path.join("workspace", "build"),
                ],
                {"cwd": PYINSTALLER_DIR, "check": True},
            ),
            (
                "copy_directory",
                os.path.join("workspace", "dist", "aws"),
                os.path.join("workspace", "aws", "dist"),
            ),
            # build aws_completer and copy into final directory
            (
                "run",
                [
                    "python",
                    os.path.join(BIN_DIRNAME, PYINSTALLER_EXE_NAME),
                    os.path.join(PYINSTALLER_DIR, "aws_completer.spec"),
                    "--distpath",
                    os.path.join("workspace", "dist"),
                    "--workpath",
                    os.path.join("workspace", "build"),
                ],
                {"cwd": PYINSTALLER_DIR, "check": True},
            ),
            (
                "copy_directory_contents_into",
                os.path.join("workspace", "dist", "aws_completer"),
                os.path.join("workspace", "aws", "dist"),
            ),
            # Copy exe assets
            (
                "copy_directory_contents_into",
                EXE_ASSETS_DIR,
                os.path.join("workspace", "aws"),
            ),
            # Update metadata
            (
                "update_metadata",
                os.path.join("workspace", "aws", "dist"),
                {"distribution_source": "source-exe"},
            ),

        ]

    def test_build(self, fake_aws_cli_venv):
        fake_utils = FakeUtils()
        builder = ExeBuilder("workspace", fake_aws_cli_venv, _utils=fake_utils)
        builder.build()

        assert fake_utils.calls == self._expected_build_tasks() + [
            # Cleanup
            ("rmtree", os.path.join("workspace", "build")),
            ("rmtree", os.path.join("workspace", "dist")),
        ]

    def test_build_no_cleanup(self, fake_aws_cli_venv):
        fake_utils = FakeUtils()
        builder = ExeBuilder("workspace", fake_aws_cli_venv, _utils=fake_utils)
        builder.build(cleanup=False)

        assert fake_utils.calls == self._expected_build_tasks()

    def test_build_does_delete_prior_workspace(self, fake_aws_cli_venv):
        fake_utils = FakeUtils(prior_build_dir=True)

        builder = ExeBuilder("workspace", fake_aws_cli_venv, _utils=fake_utils)
        builder.build()

        assert fake_utils.calls[0:2] == [
            ("isdir", os.path.join("workspace", "dist")),
            ("rmtree", os.path.join("workspace", "dist")),
        ]
