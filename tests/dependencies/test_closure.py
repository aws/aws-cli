# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import fnmatch
import functools
import importlib.metadata
import json
import os
import re
import site
from collections.abc import Iterator
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
from packaging.requirements import Requirement

_NESTED_STR_DICT = Dict[str, "_NESTED_STR_DICT"]
_ROOT_PATH = Path(__file__).parents[2]
_LOCKFILE_PATTERN = re.compile(r'^(?P<package>.+)==(?P<version>[^\s\\]+)')


@pytest.fixture()
def awscli_package():
    return Package(name="awscli")


def parse_lockfile(lockfile: Path):
    requirements = {}
    with open(lockfile) as f:
        for line in f.readlines():
            match = _LOCKFILE_PATTERN.match(line)
            if not match:
                continue
            package = match.group("package")
            version = match.group("version")
            requirements[package] = version
    return requirements


class Package:
    def __init__(self, name: str) -> None:
        self.name = name

    @functools.cached_property
    def runtime_dependencies(self) -> "DependencyClosure":
        return self._get_runtime_closure()

    def _get_runtime_closure(self) -> "DependencyClosure":
        closure = DependencyClosure()
        for requirement in self._get_runtime_requirements():
            if self._requirement_applies_to_environment(requirement):
                closure[requirement] = Package(name=requirement.name)
        return closure

    def _get_runtime_requirements(self) -> List[Requirement]:
        req_strings = self._get_distribution(self.name).requires
        if req_strings is None:
            return []
        return [Requirement(req_string) for req_string in req_strings]

    def _requirement_applies_to_environment(
        self, requirement: Requirement
    ) -> bool:
        # Do not include any requirements defined as extras as currently
        # our dependency closure does not use any extras
        if requirement.extras:
            return False
        # Only include requirements where the markers apply to the current
        # environment.
        if requirement.marker and not requirement.marker.evaluate():
            return False
        return True

    def _get_distribution(self, name: str) -> importlib.metadata.Distribution:
        # For v2, we inject our own MetaPathFinder to handle
        # botocore/s3transfer import aliases. However for the typical
        # importlib.metadata.distribution(), it extends the built-in
        # MetaPathFinder to include its own find_distributions() method
        # to search for distribution directories. Read more here:
        # https://docs.python.org/3/library/importlib.metadata.html#extending-the-search-algorithm
        #
        # Our MetaPathFinder class does not implement this method, which
        # causes importlib.metadata.distribution() to not find the "awscli"
        # package. So instead, this helper method is implemented to locate the
        # dist-info directories based off our current site-packages
        # and explicitly provide the directory to avoid needing to use
        # MetaPathFinders and thus avoid this issue.

        # Package names may have a "-". These get converted to "_" for
        # their respective directory names in the site packages directory.
        # Directory names may have a "_" in place of a "." if they were
        # built from source. If the initial normalization fails to match,
        # we try replacing "." with "_" in the package name.
        for c in ['-', '.']:
            snake_case_name = name.replace(c, "_")
            for sitepackages in site.getsitepackages():
                for filename in os.listdir(sitepackages):
                    if fnmatch.fnmatch(
                        filename, f"{snake_case_name}-*.dist-info"
                    ):
                        return importlib.metadata.Distribution.at(
                            os.path.join(sitepackages, filename)
                        )
        raise ValueError(
            f'Could not find .dist-info directory for {snake_case_name}'
        )


class DependencyClosure:
    def __init__(self) -> None:
        self._req_to_package: Dict[Requirement, Package] = {}

    def __setitem__(self, key: Requirement, value: Package) -> None:
        self._req_to_package[key] = value

    def __getitem__(self, key: Requirement) -> Package:
        return self._req_to_package[key]

    def __delitem__(self, key: Requirement) -> None:
        del self._req_to_package[key]

    def __iter__(self) -> Iterator[Requirement]:
        return iter(self._req_to_package)

    def __len__(self) -> int:
        return len(self._req_to_package)

    def walk(self) -> Iterator[Tuple[Requirement, Package]]:
        for req, package in self._req_to_package.items():
            yield req, package
            yield from package.runtime_dependencies.walk()

    def to_dict(self) -> _NESTED_STR_DICT:
        reqs = {}
        for req, package in self._req_to_package.items():
            reqs[str(req)] = package.runtime_dependencies.to_dict()
        return reqs


class TestDependencyClosure:
    def _is_bounded_version_requirement(
        self, requirement: Requirement
    ) -> bool:
        for specifier in requirement.specifier:
            if specifier.operator in ["==", "<=", "<"]:
                return True
        return False

    def _pformat_closure(self, closure: DependencyClosure) -> str:
        return json.dumps(closure.to_dict(), sort_keys=True, indent=2)

    def test_expected_runtime_dependencies(self, awscli_package):
        expected_dependencies = {
            "awscrt",
            "colorama",
            "distro",
            "docutils",
            "jmespath",
            "prompt-toolkit",
            "python-dateutil",
            "ruamel.yaml",
            "ruamel.yaml.clib",
            "six",
            "urllib3",
            "wcwidth",
        }
        actual_dependencies = set()
        for _, package in awscli_package.runtime_dependencies.walk():
            actual_dependencies.add(package.name)
        assert actual_dependencies == expected_dependencies, (
            f"Unexpected dependency found in runtime closure: "
            f"{self._pformat_closure(awscli_package.runtime_dependencies)}"
        )

    def test_expected_unbounded_runtime_dependencies(self, awscli_package):
        expected_unbounded_dependencies = {
            "six",  # Transitive dependency from python-dateutil
            "wcwidth",  # Transitive dependency from prompt-toolkit
        }
        all_dependencies = set()
        bounded_dependencies = set()
        for req, package in awscli_package.runtime_dependencies.walk():
            all_dependencies.add(package.name)
            if self._is_bounded_version_requirement(req):
                bounded_dependencies.add(package.name)
        actual_unbounded_dependencies = all_dependencies - bounded_dependencies
        assert (
            actual_unbounded_dependencies == expected_unbounded_dependencies
        ), (
            f"Unexpected unbounded dependency found in runtime closure: "
            f"{self._pformat_closure(awscli_package.runtime_dependencies)}"
        )

    # Test lockfiles generated with pyproject.toml as a source.
    @pytest.mark.parametrize("filename", ["requirements-docs-lock.txt"])
    def test_lockfile_pins_within_runtime_dependencies_bounds(
        self, filename, awscli_package
    ):
        lockfile = parse_lockfile(Path(_ROOT_PATH, filename))
        for req, _ in awscli_package.runtime_dependencies.walk():
            if req.name not in lockfile:
                continue
            assert req.specifier.contains(lockfile[req.name])
