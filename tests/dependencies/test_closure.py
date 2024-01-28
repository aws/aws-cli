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
import functools
import importlib.metadata
import json
from typing import Dict, Iterator, List, Tuple

import pytest
from packaging.requirements import Requirement

_NESTED_STR_DICT = Dict[str, "_NESTED_STR_DICT"]


@pytest.fixture()
def awscli_package():
    return Package(name="awscli")


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
        req_strings = importlib.metadata.distribution(self.name).requires
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
            "botocore",
            "colorama",
            "docutils",
            "jmespath",
            "pyasn1",
            "python-dateutil",
            "PyYAML",
            "rsa",
            "s3transfer",
            "six",
            "urllib3",
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
            "pyasn1",  # Transitive dependency from rsa
            "six",  # Transitive dependency from python-dateutil
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
