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
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Dict, Iterator, List, Literal, Optional, Set, Tuple

import build
import pytest
from packaging.requirements import Requirement

IS_WINDOWS = sys.platform == "win32"
VENV_BIN_DIRNAME = "Scripts" if IS_WINDOWS else "bin"
PYTHON_EXE_NAME = "python.exe" if IS_WINDOWS else "python"

_DEPENDENCY_CLOSURE_TYPE = Literal["runtime", "build"]
_NESTED_STR_DICT = Dict[str, "_NESTED_STR_DICT"]


@pytest.fixture(scope="module")
def awscli_package(tmp_path_factory):
    yield Package(
        name="awscli",
        workdir_path=tmp_path_factory.mktemp("awscli_deps"),
        project_root=Path(__file__).parents[2],
    )


@pytest.fixture
def package(request, awscli_package):
    if request.param == "awscli":
        return awscli_package
    for _, package in awscli_package.runtime_dependencies.walk():
        if request.param == package.name:
            return package
    raise ValueError(f"Could not find package: {request.param}")


class Package:
    def __init__(
        self,
        name: str,
        workdir_path: Path,
        project_root: Optional[Path] = None,
        from_requirement: Optional[Requirement] = None,
    ):
        self.name = name
        self._workdir_path = workdir_path
        self._project_root = project_root
        self._from_requirement = from_requirement

    @functools.cached_property
    def runtime_dependencies(self) -> "DependencyClosure":
        return self._get_closure("runtime")

    @functools.cached_property
    def build_dependencies(self) -> "DependencyClosure":
        return self._get_closure("build")

    def _get_closure(
        self, closure_type: _DEPENDENCY_CLOSURE_TYPE
    ) -> "DependencyClosure":
        closure = DependencyClosure(closure_type)
        get_requirements = getattr(self, f"_get_{closure_type}_requirements")
        for requirement in get_requirements():
            if self._requirement_applies_to_environment(requirement):
                closure[requirement] = Package(
                    name=requirement.name,
                    workdir_path=self._workdir_path,
                    from_requirement=requirement,
                )
        return closure

    def _get_runtime_requirements(self) -> List[Requirement]:
        req_strings = importlib.metadata.distribution(self.name).requires
        if req_strings is None:
            return []
        return [Requirement(req_string) for req_string in req_strings]

    def _get_build_requirements(self) -> List[Requirement]:
        build_req_strings = set()
        venv = self._get_venv()
        project_root = self._get_project_root(venv)
        builder = build.ProjectBuilder(
            project_root, python_executable=str(venv.python_exe)
        )
        build_req_strings.update(builder.build_system_requires)
        if builder.build_system_requires:
            venv.pip(["install"] + list(builder.build_system_requires))
        build_req_strings.update(builder.get_requires_for_build("sdist"))
        build_req_strings.update(builder.get_requires_for_build("wheel"))
        return [
            Requirement(build_req_string)
            for build_req_string in build_req_strings
        ]

    def _get_venv(self) -> "Venv":
        dir_component = self.name
        if self._from_requirement:
            dir_component = str(self._from_requirement)
        venv_path = (
            self._workdir_path / "venv" / self._filesys_safe(dir_component)
        )
        venv_path.mkdir(parents=True, exist_ok=True)
        return Venv(venv_path)

    def _get_project_root(self, venv: "Venv") -> Path:
        if self._project_root:
            return self._project_root
        if self._from_requirement is None:
            raise ValueError(
                "Must either declare a project_root or from_requirement "
                "to download sdist"
            )
        return self._get_unpacked_sdist(venv, self._from_requirement)

    def _get_unpacked_sdist(
        self, venv: "Venv", requirement: Requirement
    ) -> Path:
        sdist_workdir = (
            self._workdir_path / "sdist" / self._filesys_safe(str(requirement))
        )
        sdist_workdir.mkdir(parents=True, exist_ok=True)
        for path in sdist_workdir.iterdir():
            if path.is_dir():
                return path
        return self._download_and_unpack_sdist(
            venv, requirement, sdist_workdir
        )

    def _download_and_unpack_sdist(
        self, venv: "Venv", requirement: Requirement, sdist_workdir: Path
    ) -> Path:
        venv.pip(
            [
                "download",
                str(requirement),
                "--no-binary",
                requirement.name,
                "--no-deps",
            ],
            cwd=sdist_workdir,
        )
        sdist_path = list(sdist_workdir.iterdir())[0]
        shutil.unpack_archive(sdist_path, extract_dir=sdist_workdir)
        # Strip off the .tar.gz from the downloaded sdist as that will
        # match the directory name when the sdist is unpacked
        unpacked_sdist_dirname = sdist_path.name[:-7]
        return sdist_workdir / unpacked_sdist_dirname

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

    def _filesys_safe(self, val: str) -> str:
        # Remove all non-alphanumeric characters (besides "-" and "_") to
        # avoid any issues with filepath names because of special characters
        return re.sub(r"[^\w-]", "", val)


class DependencyClosure:
    def __init__(self, closure_type: _DEPENDENCY_CLOSURE_TYPE):
        self._closure_type = closure_type
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
            subclosure = getattr(package, f"{self._closure_type}_dependencies")
            yield from subclosure.walk()

    def to_dict(self) -> _NESTED_STR_DICT:
        reqs = {}
        for req, package in self._req_to_package.items():
            subclosure = getattr(package, f"{self._closure_type}_dependencies")
            reqs[str(req)] = subclosure.to_dict()
        return reqs


class Venv:
    def __init__(self, root: Path, create: bool = True):
        self._root = root
        if create:
            venv.create(self._root, with_pip=True)

    @property
    def python_exe(self) -> Path:
        return self._root / VENV_BIN_DIRNAME / PYTHON_EXE_NAME

    def pip(self, args: List[str], cwd: Optional[Path] = None) -> None:
        subprocess.run(
            [str(self.python_exe), "-m", "pip"] + args, cwd=cwd, check=True
        )


class TestDependencyClosure:
    _EXPECTED_AWSCLI_RUNTIME_DEPENDENCIES = {
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

    def _get_expected_build_dependencies(self, package: Package) -> Set[str]:
        # Most packages depend either implicitly or explcitly on setuptools
        # and wheels to build. Declare this build closure here to cut down
        # verbosity of tests.
        default_build_dependencies = {
            "setuptools",
            "wheel",
            "flit_core",  # Build dependency of "wheel"
        }
        if package.name == "python-dateutil":
            extra_build_deps = {"setuptools_scm"}
            # tomli is a build dependency of "python-dateutil" for
            # Python versions < 3.11
            if sys.version_info.minor < 11:
                extra_build_deps.add("tomli")
            return default_build_dependencies | extra_build_deps
        if package.name == "PyYAML":
            return default_build_dependencies | {"Cython"}
        # For Python3.10+, the runtime closure defaults to urllib3 2.x.
        # In that major version, the library switched from setuptools/wheel
        # to hatchling.
        if package.name == "urllib3" and sys.version_info.minor >= 10:
            urllib3_2x_extra_build_deps = {
                "hatchling",
                # Build dependendencies of hatchling
                "editables",
                "packaging",
                "pathspec",
                "pluggy",
                "trove-classifiers",
                # Build dependency of "pluggy"
                "setuptools-scm",
                # Build dependency of "trove-classifers"
                "calver",
            }
            # tomli is a build dependency of "urllib3" 2.x for
            # Python versions < 3.11
            if sys.version_info.minor < 11:
                urllib3_2x_extra_build_deps.add('tomli')
            return default_build_dependencies | urllib3_2x_extra_build_deps
        return default_build_dependencies

    def _get_expected_unbounded_build_dependencies(
        self, package: Package
    ) -> Set[str]:
        # Most packages depend either implicitly or explcitly on setuptools
        # and wheels to build. And these dependencies are usually unbounded.
        default_unbounded_build_dependencies = {
            "setuptools",
            "wheel",
        }
        if package.name == "python-dateutil":
            extra_build_deps = {"setuptools_scm"}
            if sys.version_info.minor < 11:
                extra_build_deps.add("tomli")
            return default_unbounded_build_dependencies | extra_build_deps
        # For Python3.10+, the runtime closure defaults to urllib3 2.x.
        # In that major version, the library switched from setuptools/wheel
        # to hatchling.
        if package.name == "urllib3" and sys.version_info.minor >= 10:
            urllib3_2x_extra_build_deps = {
                # Build dependendencies of "hatchling"
                "editables",
                "packaging",
                "pathspec",
                "pluggy",
                "trove-classifiers",
                # Build dependency of "pluggy"
                "setuptools-scm",
                # Build dependency of "trove-classifers"
                "calver",
                # Unbounded build dependency of "packaging" and "editables"
                "flit_core",
            }
            # tomli is a build dependency of "urllib3" 2.x for
            # Python versions < 3.11
            if sys.version_info.minor < 11:
                urllib3_2x_extra_build_deps.add('tomli')
            return default_unbounded_build_dependencies | urllib3_2x_extra_build_deps
        return default_unbounded_build_dependencies

    def _is_bounded_version_requirement(
        self, requirement: Requirement
    ) -> bool:
        for specifier in requirement.specifier:
            if specifier.operator in ["==", "=<", "<"]:
                return True
        return False

    def _pformat_closure(self, closure: DependencyClosure) -> str:
        return json.dumps(closure.to_dict(), sort_keys=True, indent=2)

    def test_expected_runtime_dependencies(self, awscli_package):
        actual_dependencies = set()
        for _, package in awscli_package.runtime_dependencies.walk():
            actual_dependencies.add(package.name)
        assert (
            actual_dependencies == self._EXPECTED_AWSCLI_RUNTIME_DEPENDENCIES
        ), (
            f"Unexpected dependency found in awscli runtime closure: "
            f"{self._pformat_closure(awscli_package.runtime_dependencies)}"
        )

    def test_expected_unbounded_runtime_dependencies(self, awscli_package):
        expected_unbounded_dependencies = {
            "pyasn1",  # Transitive dependency from rsa
            "six",  # Transitive dependency from python-dateutil
        }
        actual_unbounded_dependencies = set()
        for req, package in awscli_package.runtime_dependencies.walk():
            if not self._is_bounded_version_requirement(req):
                actual_unbounded_dependencies.add(package.name)
        assert (
            actual_unbounded_dependencies == expected_unbounded_dependencies
        ), (
            f"Unexpected unbounded dependency found in awscli runtime closure: "
            f"{self._pformat_closure(awscli_package.runtime_dependencies)}"
        )

    @pytest.mark.parametrize(
        "package",
        {"awscli"} | _EXPECTED_AWSCLI_RUNTIME_DEPENDENCIES,
        indirect=["package"],
    )
    def test_expected_build_dependencies(self, package):
        expected_build_dependencies = self._get_expected_build_dependencies(
            package
        )
        actual_dependencies = set()
        for req, build_package in package.build_dependencies.walk():
            actual_dependencies.add(build_package.name)
        assert actual_dependencies == expected_build_dependencies, (
            f"Unexpected dependency found in {package.name} build closure: "
            f"{self._pformat_closure(package.build_dependencies)}"
        )

    @pytest.mark.parametrize(
        "package",
        {"awscli"} | _EXPECTED_AWSCLI_RUNTIME_DEPENDENCIES,
        indirect=["package"],
    )
    def test_expected_unbounded_build_dependencies(self, package):
        expected_unbounded_build_dependencies = (
            self._get_expected_unbounded_build_dependencies(package)
        )
        actual_dependencies = set()
        for req, build_package in package.build_dependencies.walk():
            if not self._is_bounded_version_requirement(req):
                actual_dependencies.add(build_package.name)
        assert actual_dependencies == expected_unbounded_build_dependencies, (
            f"Unexpected unbounded dependency found in {package.name} build closure: "
            f"{self._pformat_closure(package.build_dependencies)}"
        )
