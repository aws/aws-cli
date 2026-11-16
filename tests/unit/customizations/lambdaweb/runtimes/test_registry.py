# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import pytest

from awscli.customizations.lambdaweb import constants, runtimes
from awscli.customizations.lambdaweb.exceptions import InvalidSourceError
from awscli.customizations.lambdaweb.runtimes import nodejs, python


def _touch(directory, *names):
    for name in names:
        path = os.path.join(directory, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write('')


def test_default_is_node_and_matches_constants():
    assert runtimes.DEFAULT is nodejs.RUNTIME
    assert nodejs.RUNTIME.latest == constants.DEFAULT_RUNTIME
    assert python.RUNTIME.latest == 'python3.15'


def test_resolve_requested_omitted():
    assert runtimes.resolve_requested(None) is None
    assert runtimes.resolve_requested('') is None


@pytest.mark.parametrize(
    ('value', 'expected_id', 'expected_runtime'),
    [
        ('node', constants.DEFAULT_RUNTIME, nodejs.RUNTIME),
        ('nodejs', constants.DEFAULT_RUNTIME, nodejs.RUNTIME),
        ('python', 'python3.15', python.RUNTIME),
        ('nodejs24.x', 'nodejs24.x', nodejs.RUNTIME),
        ('nodejs22.x', 'nodejs22.x', nodejs.RUNTIME),
        ('python3.14', 'python3.14', python.RUNTIME),
        ('python3.15', 'python3.15', python.RUNTIME),
    ],
)
def test_resolve_requested(value, expected_id, expected_runtime):
    assert runtimes.resolve_requested(value) == (
        expected_id,
        expected_runtime,
    )


def test_resolve_requested_passes_unknown_identifier_through():
    # A runtime newer than this CLI is sent as given and packaged with the
    # default family's rules; the service validates the identifier.
    assert runtimes.resolve_requested('ruby3.4') == ('ruby3.4', nodejs.RUNTIME)
    assert not nodejs.RUNTIME.matches('ruby3.4')


def test_for_identifier():
    assert runtimes.for_identifier('nodejs20.x') is nodejs.RUNTIME
    assert runtimes.for_identifier('python3.14') is python.RUNTIME
    # An unknown deployed runtime keeps the historical packaging behavior.
    assert runtimes.for_identifier('ruby3.4') is nodejs.RUNTIME


def test_hello_world_values():
    assert runtimes.hello_world_values() == [
        'nodejs24.x',
        'node',
        'nodejs',
        'python3.15',
        'python',
    ]
    assert nodejs.RUNTIME.accepts_hello_world('nodejs24.x')
    assert not nodejs.RUNTIME.accepts_hello_world('nodejs22.x')
    assert python.RUNTIME.accepts_hello_world('python3.15')
    assert not python.RUNTIME.accepts_hello_world('python3.14')


def test_entry_env_vars():
    assert runtimes.entry_env_vars() == (
        'AWS_LAMBDA_NODEJS_ENTRYPOINT',
        'AWS_LAMBDA_PYTHON_ENTRYPOINT',
    )


@pytest.mark.parametrize(
    ('files', 'expected'),
    [
        ((), None),
        (('package.json',), nodejs.RUNTIME),
        (('server.js',), nodejs.RUNTIME),
        (('requirements.txt',), python.RUNTIME),
        (('pyproject.toml',), python.RUNTIME),
        (('main.py',), python.RUNTIME),
        (('manage.py',), python.RUNTIME),
        (('src/main.py',), python.RUNTIME),
        (('README.md', 'lib/util.rb'), None),
    ],
)
def test_detect_single(tmp_path, files, expected):
    _touch(str(tmp_path), *files)
    assert runtimes.detect_single(str(tmp_path)) is expected


def test_detect_single_rejects_mixed_project(tmp_path):
    _touch(str(tmp_path), 'package.json', 'index.js', 'requirements.txt')
    with pytest.raises(InvalidSourceError) as excinfo:
        runtimes.detect_single(str(tmp_path))
    message = str(excinfo.value)
    assert 'both Node.js and Python' in message
    assert '--runtime node' in message
    assert '--runtime python' in message


def test_detect_returns_every_match(tmp_path):
    _touch(str(tmp_path), 'package.json', 'main.py')
    assert runtimes.detect(str(tmp_path)) == (nodejs.RUNTIME, python.RUNTIME)
