import re
import sys
import os
from subprocess import run
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[4]
REQUIREMENTS_PATH = ROOT / "requirements"
REGENERATE_LOCK_FILE_SCRIPT_PATH = ROOT / "scripts" / "regenerate-lock-files"

# Lockfiles are generated on the CANNONICAL_PYTHON_VERSION
# These tests will be skipped on any other version of python.
CANNONICAL_PYTHON_VERSION = "3.9"
IS_CANNONICAL_PYTHON_VERSION = sys.version_info[0:2] == tuple(
    map(int, CANNONICAL_PYTHON_VERSION.split("."))
)
SKIP_REASON = f"Lock files are generated on Python {CANNONICAL_PYTHON_VERSION}"

IS_LINUX = sys.platform == "linux"


def should_read_line(line):
    line = line.strip()
    return not line.startswith("#")


def read_lock_file(path):
    with open(path, 'r') as f:
        lines = f.read().split('\n')

    # Find source files
    source_files = get_source_files(lines)
    dependencies = []
    for source_file in source_files:
        dependencies.extend(get_dependency_names(source_file))

    # Filter out comments
    lines = [
        line for line in lines
        if should_read_line(line)
    ]

    # Filter out transient dependencies, we only care about the ones explicitly
    # mentioned in the requirements files.
    reading = False
    relevant_lines = []
    for line in lines:
        if line and line[0] != ' ':
            dependency_name = get_name_component(line)
            if dependency_name in dependencies:
                reading = True
            else:
                reading = False
        if reading:
            relevant_lines.append(line)
    lockfile = "\n".join(relevant_lines)
    return lockfile


def get_name_component(dependency):
    return re.split(r'(>|<|>=|<=|==)', dependency)[0]


def get_requires_from_pyproject():
    dependency_block_re = re.compile(
        r"dependencies = \[([\s\S]+?)\]\s", re.MULTILINE
    )
    extract_dependencies_re = re.compile(r'"(.+)"')
    with open(ROOT / "pyproject.toml", "r") as f:
        data = f.read()
    raw_dependencies = dependency_block_re.findall(data)[0]
    dependencies = extract_dependencies_re.findall(raw_dependencies)
    return dependencies


def get_dependency_names(filename):
    if not filename.endswith('.txt'):
        return [get_name_component(dep) for dep in get_requires_from_pyproject()]

    dependencies = []
    filepath = ROOT / filename
    with open(filepath) as f:
        content = f.read()
        lines = content.split('\n')
        for line in lines:
            if not line:
                continue
            if line.startswith('-r'):
                directory = os.path.dirname(filepath)
                new_filename = line.split(' ')[1]
                new_full_filepath = os.path.abspath(os.path.join(directory, new_filename))
                dependencies.extend(get_dependency_names(new_full_filepath))
            else:
                dependencies.append(get_name_component(line))
    return dependencies



def get_source_files(lines):
    for line in lines:
        if 'pip-compile' and 'generate-hashes' in line:
            line = line[1:]
            files = [
                part for part in
                line.split(' ')
                if part and not part.startswith('--') and part != 'pip-compile'
            ]
            return files


def is_lockfile(path: str) -> bool:
    return path.endswith("-lock.txt")


def lockfile_paths(root):
    for base, _, filenames in os.walk(root):
        for filename in filenames:
            path = os.path.join(base, filename)
            if is_lockfile(path):
                yield path


@pytest.mark.skipif(
    not IS_CANNONICAL_PYTHON_VERSION,
    reason=SKIP_REASON,
)
def test_all_lock_files_are_generated_by_expected_python_version():
    for path in lockfile_paths(REQUIREMENTS_PATH):
        with open(path, "r") as f:
            content = f.read()
            assert f"python {CANNONICAL_PYTHON_VERSION}" in content


@pytest.mark.skipif(
    not IS_CANNONICAL_PYTHON_VERSION,
    reason=SKIP_REASON,
)
@pytest.mark.skipif(
    IS_LINUX,
    reason=(
        "The linux lock files are generated on mac. So the only "
        "platforms we need to test are mac and Windows."
    ),
)
def test_lock_files_are_up_to_date(tmpdir):
    reqs_dir = tmpdir / "requirements"
    reqs_dir.mkdir()
    download_deps_dir = reqs_dir / "download-deps"
    download_deps_dir.mkdir()
    command = [
        sys.executable,
        REGENERATE_LOCK_FILE_SCRIPT_PATH,
        "--output-directory",
        tmpdir,
    ]
    result = run(command, cwd=ROOT)
    assert result.returncode == 0

    lockfile_mapping = {
        path: path.replace(str(tmpdir), str(ROOT))
        for path in lockfile_paths(tmpdir)
    }

    for regenerated_file, original_file in lockfile_mapping.items():
        assert read_lock_file(regenerated_file) == read_lock_file(original_file)
