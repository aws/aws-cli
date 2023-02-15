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
import argparse
import os
import shutil
from awscli_venv import AwsCliVenv
from constants import (
    ArtifactType,
    BUILD_DIR,
    INSTALL_DIRNAME,
)
from exe import ExeBuilder
from install import (
    Installer,
    Uninstaller,
)
from validate_env import validate_env


def create_exe(aws_venv, build_dir):
    exe_workspace = os.path.join(build_dir, "exe")
    if os.path.exists(exe_workspace):
        shutil.rmtree(exe_workspace)
    builder = ExeBuilder(exe_workspace, aws_venv)
    builder.build()


def build(parsed_args):
    aws_venv = _bootstap_venv(
        parsed_args.build_dir,
        parsed_args.artifact,
        parsed_args.download_deps,
    )
    if parsed_args.artifact == ArtifactType.PORTABLE_EXE.value:
        create_exe(aws_venv, parsed_args.build_dir)


def validate(parsed_args):
    validate_env(parsed_args.artifact)


def install(parsed_args):
    build_dir = parsed_args.build_dir
    install_dir = os.path.join(parsed_args.lib_dir, INSTALL_DIRNAME)
    bin_dir = parsed_args.bin_dir
    installer = Installer(build_dir)
    installer.install(install_dir, bin_dir)


def uninstall(parsed_args):
    install_dir = os.path.join(parsed_args.lib_dir, INSTALL_DIRNAME)
    bin_dir = parsed_args.bin_dir
    uninstaller = Uninstaller()
    uninstaller.uninstall(install_dir, bin_dir)


def _bootstap_venv(build_dir: str, artifact_type: str, download_deps: bool):
    venv_path = os.path.join(build_dir, "venv")
    if os.path.exists(venv_path):
        shutil.rmtree(venv_path)
    os.makedirs(venv_path)
    aws_venv = AwsCliVenv(venv_path)
    aws_venv.create()
    aws_venv.bootstrap(artifact_type, download_deps)
    return aws_venv


def main():
    parser = argparse.ArgumentParser()

    subparser = parser.add_subparsers()

    validate_env_parser = subparser.add_parser("validate-env")
    validate_env_parser.add_argument(
        "--artifact", choices=[e.value for e in ArtifactType], required=True
    )
    validate_env_parser.set_defaults(func=validate)

    build_parser = subparser.add_parser("build")
    build_parser.add_argument(
        "--artifact", choices=[e.value for e in ArtifactType], required=True
    )
    build_parser.add_argument(
        "--build-dir", default=BUILD_DIR, type=os.path.abspath
    )
    build_parser.add_argument("--download-deps", action="store_true")
    build_parser.set_defaults(func=build)

    install_parser = subparser.add_parser("install")
    install_parser.add_argument(
        "--build-dir", default=BUILD_DIR, type=os.path.abspath
    )
    install_parser.add_argument(
        "--lib-dir", required=True, type=os.path.abspath
    )
    install_parser.add_argument(
        "--bin-dir", required=True, type=os.path.abspath
    )
    install_parser.set_defaults(func=install)

    uninstall_parser = subparser.add_parser("uninstall")
    uninstall_parser.add_argument(
        "--lib-dir", required=True, type=os.path.abspath
    )
    uninstall_parser.add_argument(
        "--bin-dir", required=True, type=os.path.abspath
    )
    uninstall_parser.set_defaults(func=uninstall)

    parsed_args = parser.parse_args()
    parsed_args.func(parsed_args)


if __name__ == "__main__":
    main()
