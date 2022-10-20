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
import re
import json
import shutil
import subprocess
import venv
import contextlib
from typing import List, Dict, Any, Optional, Callable

from constants import ROOT_DIR
from constants import IS_WINDOWS


PACKAGE_NAME = re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9_\.\-]+)(?P<rest>.+)")
CONSTRAINT = re.compile(r"(?P<comparison>[=\<\>]+)(?P<version>.+)")
COMPARISONS: Dict[str, Callable[[List[int], List[int]], bool]] = {
    '==': lambda a, b: a == b,
    '>':  lambda a, b: a > b,
    '>=':  lambda a, b: a >= b,
    '<':  lambda a, b: a < b,
    '<=':  lambda a, b: a <= b,
}


@contextlib.contextmanager
def cd(dirname):
    original = os.getcwd()
    os.chdir(dirname)
    try:
        yield
    finally:
        os.chdir(original)


class Requirement:
    def __init__(self, name: str, *constraints):
        self.name = name
        self.constraints = constraints

    def is_in_range(self, version: str) -> bool:
        return self._meets_constraints(version)

    def _meets_constraints(self, version):
        return all(
            self._meets_constraint(version, constraint)
            for constraint in self.constraints
        )

    def _meets_constraint(self, version, constraint) -> bool:
        match = CONSTRAINT.match(constraint)
        if not match:
            raise RuntimeError(f"Unknown version specifier {constraint}")
        comparison, constraint_version = match.group('comparison', 'version')
        version, constraint_version = self._normalize(version, constraint_version)

        compare_fn = COMPARISONS.get(comparison)
        if not compare_fn:
            raise RuntimeError(f"Unknown version range specifier {comparison}")
        return compare_fn(version, constraint_version)

    def _normalize(self, v1: str, v2: str):
        v1_parts = [int(v) for v in v1.split(".")]
        v2_parts = [int(v) for v in v2.split(".")]
        while (pad := len(v1_parts) - len(v2_parts)) != 0:
            if pad > 0:
                v2_parts.append(0)
            if pad < 0:
                v1_parts.append(0)
        return v1_parts, v2_parts

    def __eq__(self, other):
        if other is None:
            return False
        return (self.name == other.name and self.constraints == other.constraints)


class ParseError(Exception):
    pass


def parse_requirements(lines_list):
    lines = iter(lines_list)
    for line in lines:
        if ';' in line:
            raise ParseError('Parser does not support env markers')
        if line.startswith('#'):
            continue
        if ' #' in line:
            line = line[:line.find(' #')]
        if line.endswith('\\'):
            line = line[:-2].strip()
            try:
                line += next(lines)
            except StopIteration:
                return
        yield _parse_req_line(line)


def _parse_req_line(line: str):
    match = PACKAGE_NAME.search(line)
    if not match:
        raise RuntimeError(f"Unrecognized dependency {line}")

    name, rest = match.group('name', 'rest')
    return Requirement(name, *rest.split(','))


def get_install_requires():
    import flit_core.buildapi

    with cd(ROOT_DIR):
        requires = flit_core.buildapi.get_requires_for_build_wheel()
    # Generation of the auto-complete index requires importing from the
    # awscli package and iterating over the commands from the clidriver. In
    # order to be able to do this, it requires all of the CLI's runtime
    # dependencies to be present to avoid import errors.
    dependency_block_re = re.compile(
        r"dependencies = \[([\s\S]+?)\]", re.MULTILINE
    )
    extract_dependencies_re = re.compile(r'"(.+)"')
    with open(ROOT_DIR / "pyproject.toml", "r") as f:
        data = f.read()
    raw_dependencies = dependency_block_re.findall(data)[0]
    dependencies = extract_dependencies_re.findall(raw_dependencies)
    return dependencies


class Utils:
    def isdir(self, path: str) -> bool:
        return os.path.isdir(path)

    def islink(self, path: str) -> bool:
        return os.path.islink(path)

    def remove(self, path: str):
        os.remove(path)

    def makedirs(self, path: str):
        os.makedirs(path)

    def symlink(self, src: str, dst: str):
        os.symlink(src, dst)

    def read_file_lines(self, path: str) -> List[str]:
        return open(path, "r").readlines()

    def write_file(self, path: str, content: str):
        with open(path, "w") as f:
            f.write(content)

    def path_exists(self, path: str) -> bool:
        return os.path.exists(path)

    def rmtree(self, path: str) -> None:
        shutil.rmtree(path)

    def run(self, args: List[str], **kwargs: Dict[str, Any]):
        return subprocess.run(args, **kwargs)

    def copy_file(self, src: str, dst: str):
        print("Copying file %s -> %s" % (src, dst))
        shutil.copy2(src, dst)

    def copy_directory_contents_into(self, src: str, dst: str):
        print("Copying contents of %s into %s" % (src, dst))
        shutil.copytree(src, dst, dirs_exist_ok=True)

    def copy_directory(self, src: str, dst: str):
        print("Copying %s -> %s" % (src, dst))
        shutil.copytree(src, dst)

    def update_metadata(self, dirname, **kwargs):
        print("Update metadata values %s" % kwargs)
        metadata_file = os.path.join(dirname, "awscli", "data", "metadata.json")
        with open(metadata_file) as f:
            metadata = json.load(f)
        for key, value in kwargs.items():
            metadata[key] = value
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

    def create_venv(self, name: str, with_pip: bool = True):
        venv.create(name, with_pip=with_pip)

    def get_script_header(self, python_exe_path: str) -> str:
        if IS_WINDOWS:
            return f'@echo off & "{python_exe_path}" -x "%~f0" %* & goto :eof\n'
        return f"#!{python_exe_path}\n"
