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
from pathlib import Path
import importlib.metadata

from constants import (
    BOOTSTRAP_REQUIREMENTS,
    PORTABLE_EXE_REQUIREMENTS,
)
from utils import get_install_requires, parse_requirements
from utils import UnmetDependenciesException


ROOT = Path(__file__).parents[2]
PYPROJECT = ROOT / "pyproject.toml"
BUILD_REQS_RE = re.compile(
    r"requires = \[([\s\S]+?)\]\s", re.MULTILINE
)
EXTRACT_DEPENDENCIES_RE = re.compile(r'"(.+)"')


def validate_env(target_artifact):
    requirements = _get_requires_list(target_artifact)
    unmet_deps = _get_unmet_dependencies(requirements)
    if unmet_deps:
        in_venv = sys.prefix != sys.base_prefix
        raise UnmetDependenciesException(unmet_deps, in_venv)


def _get_requires_list(target_artifact):
    requires_list = _parse_pyproject_requirements()
    requires_list += _parse_requirements(BOOTSTRAP_REQUIREMENTS)
    requires_list += get_install_requires()
    if target_artifact == "portable-exe":
        requires_list += _parse_requirements(PORTABLE_EXE_REQUIREMENTS)
    return parse_requirements(requires_list)


def _parse_pyproject_requirements():
    with open(PYPROJECT, 'r') as f:
        data = f.read()
    raw_dependencies = BUILD_REQS_RE.findall(data)[0]
    dependencies = EXTRACT_DEPENDENCIES_RE.findall(raw_dependencies)
    return list(dependencies)


def _parse_requirements(requirements_file):
    requirements = []
    with open(requirements_file, "r") as f:
        for line in f.readlines():
            if not line.startswith(("-r", "#")):
                requirements.append(line.strip())
    return requirements


def _get_unmet_dependencies(requirements):
    unmet = []
    checked = set()
    for requirement in requirements:
        project_name = requirement.name
        if project_name in checked:
            continue
        checked.add(project_name)
        try:
            actual_version = importlib.metadata.version(project_name)
        except importlib.metadata.PackageNotFoundError:
            unmet.append((project_name, None, requirement))
            continue
        if not requirement.is_in_range(actual_version):
            unmet.append((project_name, actual_version, requirement))
    return unmet
