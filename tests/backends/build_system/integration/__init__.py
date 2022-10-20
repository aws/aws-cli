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
import re
import sys
import shutil
import venv
import subprocess
import os

from pathlib import Path
from typing import Dict


IS_WINDOWS = sys.platform == "win32"
BIN_DIRNAME = "Scripts" if IS_WINDOWS else "bin"
PYTHON_EXE_NAME = "python.exe" if IS_WINDOWS else "python"
CLI_SCRIPT_NAME = "aws.cmd" if IS_WINDOWS else "aws"
LOCK_SUFFIX = "win-lock.txt" if IS_WINDOWS else "lock.txt"

ROOT = Path(__file__).parents[4]
BOOTSTRAP_REQUIREMENTS = (
    ROOT / "requirements" / "download-deps" / f"bootstrap-{LOCK_SUFFIX}"
)
PORTABLE_EXE_REQUIREMENTS = (
    ROOT / "requirements" / "download-deps" / f"portable-exe-{LOCK_SUFFIX}"
)
SYSTEM_SANDBOX_REQIREMENTS = (
    ROOT / "requirements" / "download-deps" / f"system-sandbox-{LOCK_SUFFIX}"
)


class BaseArtifactTest:
    def expected_cli_version(self):
        init_file_path = ROOT / "awscli" / "__init__.py"
        version_file = open(init_file_path, "r").read()
        version_match = re.search(
            r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M
        )
        if version_match:
            return version_match.group(1)
        raise RuntimeError("Unable to find version string.")

    def expected_python_version(self):
        python_info = sys.version_info
        return f"{python_info.major}.{python_info.minor}.{python_info.micro}"

    def assert_version_string_is_correct(self, exe_path):
        version_string = subprocess.check_output(
            [str(exe_path), "--version"]
        ).decode()

        assert f"aws-cli/{self.expected_cli_version()}" in version_string
        assert f"Python/{self.expected_python_version()}" in version_string
        assert "source/" in version_string

    def assert_built_venv_is_correct(self, venv_dir):
        self.assert_venv_is_correct(venv_dir)
        files = os.listdir(venv_dir)

        # The venv after building also includes the binary
        assert BIN_DIRNAME in files
        aws_exe = venv_dir / BIN_DIRNAME / CLI_SCRIPT_NAME
        self.assert_version_string_is_correct(aws_exe)

    def assert_venv_is_correct(self, venv_dir):
        files = os.listdir(venv_dir)
        assert "Include" in files or "include" in files
        assert "Lib" in files or "lib" in files or "lib64" in files
        assert "pyvenv.cfg" in files

    def assert_built_exe_is_correct(self, root_dir):
        aws_dir = root_dir / "build" / "exe" / "aws"
        files = os.listdir(aws_dir)

        assert set(files) == {
            "README.md",
            "THIRD_PARTY_LICENSES",
            "dist",
            "install",
        }

        aws_exe = aws_dir / "dist" / "aws"
        self.assert_version_string_is_correct(aws_exe)

    def assert_installed_exe_is_correct(self, exe_dir):
        self.assert_version_string_is_correct(exe_dir / CLI_SCRIPT_NAME)

    def assert_installed_venv_is_correct(self, exe_dir, lib_dir):
        self.assert_version_string_is_correct(exe_dir / CLI_SCRIPT_NAME)
        self.assert_venv_is_correct(lib_dir / "aws-cli")


class VEnvWorkspace:
    def __init__(self, path):
        self.path = path
        self.cli_path = path / "aws"
        self.venv_path = path / "venv"
        self.install_path = path / "install"
        self.bin_path = path / "install" / "bin"
        self.lib_path = path / "install" / "lib"

        self._init_cli_directory()
        self._init_venv_directory()
        self._init_install_path()

    def _init_cli_directory(self):
        shutil.copytree(
            ROOT,
            self.cli_path,
            ignore=shutil.ignore_patterns(".git", "build", ".tox"),
        )

    def _init_venv_directory(self):
        venv.create(self.venv_path, with_pip=True)

    def _init_install_path(self):
        self.install_path.mkdir()
        self.bin_path.mkdir()
        self.lib_path.mkdir()

    def install_bootstrap_dependencies(self):
        self._install_requirements_file(BOOTSTRAP_REQUIREMENTS)

    def install_dependencies(self):
        self.install_bootstrap_dependencies()
        self._install_requirements_file(SYSTEM_SANDBOX_REQIREMENTS)

    def install_pyinstaller(self):
        self._install_requirements_file(PORTABLE_EXE_REQUIREMENTS)

    def _install_requirements_file(self, path: Path):
        subprocess.check_call(
            [self.python_exe(), "-m", "pip", "install", "-r", path]
        )

    @property
    def build_path(self):
        return self.cli_path / "build" / "venv"

    def python_exe(self):
        return self.venv_path / BIN_DIRNAME / PYTHON_EXE_NAME

    def env(self, overrides: Dict[str, str] = None):
        env = os.environ.copy()
        if overrides:
            env.update(overrides)
        env["PYTHON"] = str(self.python_exe())
        return env

    def subprocess(self, args, env=None):
        return subprocess.check_output(
            args,
            stderr=subprocess.STDOUT,
            cwd=self.cli_path,
            env=self.env(env),
        )

    def configure(self, install_type: str, download_deps: bool = False):
        configure_path = self.cli_path / "configure"
        args = [
            configure_path,
            f"--with-install-type={install_type}",
        ]
        if download_deps:
            args.append("--with-download-deps")
        self.subprocess(args)

    def make(self, args=None, env=None):
        cmd = ["make"]
        if args:
            cmd += args
        return self.subprocess(cmd, env=env)

    def call_build_system(self, artifact_type: str, download_deps: bool):
        args = [
            self.python_exe(),
            os.path.join("backends", "build_system"),
            "build",
            "--artifact",
            artifact_type,
            "--build-dir",
            "build",
        ]
        if download_deps:
            args.append("--download-deps")
        return self.subprocess(args)

    def call_install(self, bin_path: str, lib_path: str):
        args = [
            self.python_exe(),
            os.path.join("backends", "build_system"),
            "install",
            "--bin-dir",
            bin_path,
            "--lib-dir",
            lib_path,
            "--build-dir",
            "build",
        ]
        return self.subprocess(args)

    def call_uninstall(self, bin_path: str, lib_path: str):
        args = [
            self.python_exe(),
            os.path.join("backends", "build_system"),
            "uninstall",
            "--bin-dir",
            bin_path,
            "--lib-dir",
            lib_path,
        ]
        return self.subprocess(args)
