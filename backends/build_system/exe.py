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
from dataclasses import dataclass, field

from constants import EXE_ASSETS_DIR, PYINSTALLER_DIR, DISTRIBUTION_SOURCE, PYINSTALLER_EXE_NAME
from utils import Utils
from awscli_venv import AwsCliVenv


@dataclass
class ExeBuilder:
    workspace: str
    venv: AwsCliVenv

    _exe_dir: str = field(init=False)
    _final_dist_dir: str = field(init=False)
    _dist_dir: str = field(init=False)
    _build_dir: str = field(init=False)

    _utils: Utils = field(default_factory=lambda: Utils())

    def __post_init__(self):
        self._exe_dir = os.path.join(self.workspace, "aws")
        self._final_dist_dir = os.path.join(self._exe_dir, "dist")
        self._dist_dir = os.path.join(self.workspace, "dist")
        self._build_dir = os.path.join(self.workspace, "build")

    def build(self, cleanup=True):
        self._ensure_no_existing_build_dir()
        self._build_aws()
        self._build_aws_completer()
        self._utils.copy_directory_contents_into(EXE_ASSETS_DIR, self._exe_dir)
        if cleanup:
            self._cleanup()
        print(f"Built exe at {self._exe_dir}")

    def _ensure_no_existing_build_dir(self):
        if self._utils.isdir(self._dist_dir):
            self._utils.rmtree(self._dist_dir)

    def _build_aws(self):
        aws_exe_build_dir = self._run_pyinstaller("aws.spec")
        self._utils.update_metadata(
            aws_exe_build_dir,
            distribution_source=DISTRIBUTION_SOURCE,
        )
        self._utils.copy_directory(aws_exe_build_dir, self._final_dist_dir)

    def _build_aws_completer(self):
        aws_completer_exe_build_dir = self._run_pyinstaller(
            "aws_completer.spec"
        )
        self._utils.copy_directory_contents_into(
            aws_completer_exe_build_dir, self._final_dist_dir
        )

    def _run_pyinstaller(self, specfile: str):
        aws_spec_path = os.path.join(PYINSTALLER_DIR, specfile)
        self._utils.run(
            [
                self.venv.python_exe,
                os.path.join(self.venv.bin_dir, PYINSTALLER_EXE_NAME),
                aws_spec_path,
                "--distpath",
                self._dist_dir,
                "--workpath",
                self._build_dir,
            ],
            cwd=PYINSTALLER_DIR,
            check=True,
        )
        return os.path.join(
            self.workspace, "dist", os.path.splitext(specfile)[0]
        )

    def _cleanup(self):
        locations = [
            self._build_dir,
            self._dist_dir,
        ]
        for location in locations:
            self._utils.rmtree(location)
            print("Deleted build directory: %s" % location)
