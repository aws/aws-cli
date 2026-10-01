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
import json
import os
import zipfile
from unittest import mock

import pytest

from awscli.customizations.lambdaweb import bundle, constants, scaffold
from awscli.customizations.lambdaweb.exceptions import InvalidSourceError


def test_write_hello_world_into_new_dir(tmp_path):
    dest = str(tmp_path / 'my-app')
    entry = scaffold.write_hello_world(dest, 'my-app')
    assert entry == 'server.ts'
    assert sorted(os.listdir(dest)) == [
        'AGENTS.md',
        'README.md',
        'package.json',
        'server.ts',
    ]


def test_write_hello_world_into_empty_dir(tmp_path):
    dest = str(tmp_path / 'empty')
    os.makedirs(dest)
    scaffold.write_hello_world(dest, 'empty')
    assert os.path.isfile(os.path.join(dest, 'server.ts'))


def test_readme_is_human_facing_and_points_at_agents_md(tmp_path):
    dest = str(tmp_path / 'my-app')
    scaffold.write_hello_world(dest, 'my-app')
    with open(os.path.join(dest, 'README.md'), encoding='utf-8') as f:
        readme = f.read()
    assert readme.startswith('# my-app')
    # Human-facing overview, local verification, deploy, and agent setup.
    assert '## Why Lambda Web Functions' in readme
    assert '## Run locally' in readme
    assert '## Deploy' in readme
    assert 'curl http://localhost:3000' in readme
    assert '## Set up an AI coding agent' in readme
    assert 'AGENTS.md' in readme
    assert '## Clean up' not in readme
    assert '{function_name}' not in readme


def test_agents_md_has_agent_facing_reference(tmp_path):
    dest = str(tmp_path / 'my-app')
    scaffold.write_hello_world(dest, 'my-app')
    with open(os.path.join(dest, 'AGENTS.md'), encoding='utf-8') as f:
        agents = f.read()
    # Runtime, packaging, skill, and deployment facts use rendered values.
    assert constants.LOCAL_PORT_ENV_VAR in agents
    assert 'aws lambda-web deploy help' in agents
    assert 'build step' in agents
    assert constants.DEFAULT_RUNTIME in agents
    assert constants.RUNTIME_ARCHITECTURE in agents
    assert constants.CONFIRM_CREATE_FLAG in agents
    assert constants.ENTRYPOINT_ENV_VAR in agents
    assert 'aws-lambda-web-functions' in agents
    assert '--force-include' in agents
    assert 'aws logs tail /aws/lambda/web/my-app --follow' in agents
    assert 'The first invocation creates' in agents
    assert '{function_name}' not in agents
    # The guidance prevents agents from replacing the server with a handler.
    assert 'handler' in agents


def test_scaffold_server_listens_not_handler(tmp_path):
    # The starter listens for HTTP requests instead of exporting a handler.
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app')
    with open(os.path.join(dest, 'server.ts'), encoding='utf-8') as f:
        src = f.read()
    assert '.listen(' in src
    assert f'process.env.{constants.LOCAL_PORT_ENV_VAR}' in src
    assert f'?? {constants.RUNTIME_HTTP_PORT}' in src
    assert 'server.listen(port' in src
    assert 'AWS_LAMBDA_HTTP_ENDPOINT' not in src
    assert 'export const handler' not in src
    assert 'exports.handler' not in src


def test_scaffold_package_json_self_describes_entry(tmp_path):
    # package.json "main" must point at the scaffold entry so redeploys
    # auto-detect it, and it must be an ESM module with a deploy script.
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app')
    with open(os.path.join(dest, 'package.json'), encoding='utf-8') as f:
        pkg = json.load(f)
    assert pkg['main'] == 'server.ts'
    assert pkg['private'] is True
    assert pkg['type'] == 'module'
    assert 'description' not in pkg
    assert pkg['scripts']['start'] == 'node server.ts'
    assert pkg['scripts']['deploy'] == (
        'aws lambda-web deploy --name app --code .'
    )
    # resolve_entry_point (used on every redeploy) picks up server.ts via main.
    assert bundle.resolve_entry_point(dest) == 'server.ts'


def test_scaffold_bundles_with_import_wrapper(tmp_path):
    # server.ts is not index.js, so build_zip injects an index.js wrapper that
    # dynamically imports the TypeScript entry with the default runtime.
    dest = str(tmp_path / 'app')
    entry = scaffold.write_hello_world(dest, 'app')
    path, _ = bundle.build_zip(
        dest, entry, exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            wrapper = zf.read('index.js').decode()
        assert {'server.ts', 'package.json', 'index.js'} <= names
        assert 'const entryPoint = "./server.ts";' in wrapper
        assert 'import(entryPoint)' in wrapper
    finally:
        os.unlink(path)


def test_write_hello_world_refuses_non_empty_dir(tmp_path):
    dest = str(tmp_path / 'app')
    os.makedirs(dest)
    with open(os.path.join(dest, 'existing.js'), 'w', encoding='utf-8') as f:
        f.write('// pre-existing')
    with pytest.raises(InvalidSourceError) as excinfo:
        scaffold.write_hello_world(dest, 'app')
    assert 'does not overwrite files' in str(excinfo.value)
    # The pre-existing file is untouched.
    with open(os.path.join(dest, 'existing.js'), encoding='utf-8') as f:
        assert f.read() == '// pre-existing'


def test_write_hello_world_refuses_file_target(tmp_path):
    dest = str(tmp_path / 'afile')
    with open(dest, 'w', encoding='utf-8') as f:
        f.write('x')
    with pytest.raises(InvalidSourceError):
        scaffold.write_hello_world(dest, 'app')


def test_write_hello_world_wraps_write_error(tmp_path):
    dest = str(tmp_path / 'app')
    with (
        mock.patch.object(
            scaffold, '_write', side_effect=OSError('disk full')
        ),
        pytest.raises(InvalidSourceError, match='might contain files'),
    ):
        scaffold.write_hello_world(dest, 'app')


def test_is_empty_dir_wraps_inspection_error(tmp_path):
    dest = str(tmp_path / 'app')
    os.makedirs(dest)
    with (
        mock.patch.object(
            scaffold.os,
            'listdir',
            side_effect=OSError('permission denied'),
        ),
        pytest.raises(InvalidSourceError, match='Unable to inspect'),
    ):
        scaffold.is_empty_dir(dest)


def test_is_empty_dir(tmp_path):
    assert scaffold.is_empty_dir(str(tmp_path / 'missing')) is True
    empty = tmp_path / 'e'
    empty.mkdir()
    assert scaffold.is_empty_dir(str(empty)) is True
    (empty / 'f').write_text('x')
    assert scaffold.is_empty_dir(str(empty)) is False
