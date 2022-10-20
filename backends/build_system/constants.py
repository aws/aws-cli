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
import sys
from enum import Enum
from pathlib import Path


ROOT_DIR = Path(__file__).parents[2]
BUILD_DIR = ROOT_DIR / "build"

EXE_DIR = ROOT_DIR / "exe"
EXE_ASSETS_DIR = EXE_DIR / "assets"
PYINSTALLER_DIR = EXE_DIR / "pyinstaller"

# Platform specific values
IS_WINDOWS = sys.platform == "win32"
BIN_DIRNAME = "Scripts" if IS_WINDOWS else "bin"
PYTHON_EXE_NAME = "python.exe" if IS_WINDOWS else "python"
PYINSTALLER_EXE_NAME = "pyinstaller.exe" if IS_WINDOWS else "pyinstaller"
CLI_SCRIPTS = ["aws.cmd"] if IS_WINDOWS else ["aws", "aws_completer"]
LOCK_SUFFIX = "win-lock.txt" if IS_WINDOWS else "lock.txt"

# Requirements files
REQUIREMENTS_DIR = ROOT_DIR / "requirements"
BOOTSTRAP_REQUIREMENTS = REQUIREMENTS_DIR / "bootstrap.txt"
DOWNLOAD_DEPS_BOOTSTRAP = REQUIREMENTS_DIR / "download-deps" / "bootstrap.txt"
DOWNLOAD_DEPS_BOOTSTRAP_LOCK = REQUIREMENTS_DIR / "download-deps" / f"bootstrap-{LOCK_SUFFIX}"
PORTABLE_EXE_REQUIREMENTS = REQUIREMENTS_DIR / "portable-exe-extras.txt"
PORTABLE_EXE_REQUIREMENTS_LOCK = REQUIREMENTS_DIR / "download-deps" / f"portable-exe-{LOCK_SUFFIX}"
SYSTEM_SANDBOX_REQUIREMENTS_LOCK = REQUIREMENTS_DIR / "download-deps" / f"system-sandbox-{LOCK_SUFFIX}"

# Auto-complete index
AC_INDEX = ROOT_DIR / "awscli" / "data" / "ac.index"

INSTALL_DIRNAME = "aws-cli"


DISTRIBUTION_SOURCE = "exe"


class ArtifactType(Enum):
    PORTABLE_EXE = "portable-exe"
    SYSTEM_SANDBOX = "system-sandbox"
