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
import subprocess
import sys
import zipfile
from unittest import mock

import pytest

from awscli.customizations.lambdaweb import bundle, constants, scaffold
from awscli.customizations.lambdaweb.exceptions import InvalidSourceError
from awscli.customizations.lambdaweb.runtimes import nodejs, python

NODE = nodejs.RUNTIME
PYTHON = python.RUNTIME
RUNTIMES = [
    pytest.param(NODE, id='nodejs'),
    pytest.param(PYTHON, id='python'),
]


def _read(dest, name):
    with open(os.path.join(dest, name), encoding='utf-8') as f:
        return f.read()


def test_write_hello_world_into_new_dir(tmp_path):
    dest = str(tmp_path / 'my-app')
    entry = scaffold.write_hello_world(dest, 'my-app', NODE)
    assert entry == 'server.ts'
    assert sorted(os.listdir(dest)) == [
        'AGENTS.md',
        'README.md',
        'package.json',
        'server.ts',
    ]


def test_write_python_hello_world(tmp_path):
    dest = str(tmp_path / 'my-app')
    entry = scaffold.write_hello_world(dest, 'my-app', PYTHON)
    assert entry == 'main:app'
    assert sorted(os.listdir(dest)) == ['AGENTS.md', 'README.md', 'main.py']


def test_write_hello_world_into_empty_dir(tmp_path):
    dest = str(tmp_path / 'empty')
    os.makedirs(dest)
    scaffold.write_hello_world(dest, 'empty', NODE)
    assert os.path.isfile(os.path.join(dest, 'server.ts'))


@pytest.mark.parametrize('runtime', RUNTIMES)
def test_readme_is_human_facing_and_points_at_agents_md(tmp_path, runtime):
    dest = str(tmp_path / 'my-app')
    scaffold.write_hello_world(dest, 'my-app', runtime)
    readme = _read(dest, 'README.md')
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
    assert runtime.docs.start_command in readme
    assert f'edit `{runtime.docs.entry_file}`' in readme


@pytest.mark.parametrize('runtime', RUNTIMES)
def test_agents_md_has_agent_facing_reference(tmp_path, runtime):
    dest = str(tmp_path / 'my-app')
    scaffold.write_hello_world(dest, 'my-app', runtime)
    agents = _read(dest, 'AGENTS.md')
    # Runtime, packaging, skill, and deployment facts use rendered values.
    assert constants.LOCAL_PORT_ENV_VAR in agents
    assert 'aws lambda-web deploy help' in agents
    assert 'build step' in agents
    assert runtime.latest in agents
    assert constants.RUNTIME_ARCHITECTURE in agents
    assert constants.CONFIRM_CREATE_FLAG in agents
    assert runtime.entry_env_var in agents
    assert 'aws-lambda-web-functions' in agents
    assert '--force-include' in agents
    assert 'aws logs tail /aws/lambda/web/my-app --follow' in agents
    assert 'The first invocation creates' in agents
    assert '{function_name}' not in agents
    # The guidance prevents agents from replacing the server with a handler.
    assert 'handler' in agents


def test_node_docs_do_not_mention_python_and_vice_versa(tmp_path):
    node_dest = str(tmp_path / 'node')
    python_dest = str(tmp_path / 'python')
    scaffold.write_hello_world(node_dest, 'node', NODE)
    scaffold.write_hello_world(python_dest, 'python', PYTHON)
    node_docs = _read(node_dest, 'AGENTS.md') + _read(node_dest, 'README.md')
    python_docs = _read(python_dest, 'AGENTS.md') + _read(
        python_dest, 'README.md'
    )
    assert python.ENTRYPOINT_ENV_VAR not in node_docs
    assert 'pip install' not in node_docs
    assert constants.ENTRYPOINT_ENV_VAR not in python_docs
    assert 'npm' not in python_docs
    assert 'node_modules' not in python_docs


def test_python_agents_md_documents_the_app_object_contract(tmp_path):
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', PYTHON)
    agents = _read(dest, 'AGENTS.md')
    assert 'main:app' in agents
    assert 'WSGI or ASGI application object' in agents
    assert '--entry-point module:object' in agents
    assert 'uv pip install -r requirements.txt --target .' in agents
    assert (
        'pip install -r requirements.txt --target . --only-binary=:all:'
        in (agents)
    )
    assert '--python-version 3.15' in agents
    assert 'aarch64' in agents
    assert 'does not run `pip` or `uv`' in agents
    assert '__pycache__' in agents
    assert 'python main.py   # run locally on port 3000' in agents


def test_python_readme_explains_frameworks(tmp_path):
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', PYTHON)
    readme = _read(dest, 'README.md')
    assert 'app = FastAPI()' in readme
    assert 'app = Flask(__name__)' in readme
    assert 'mysite.asgi:application' in readme
    assert '```bash\npython main.py\n```' in readme
    assert '```bash\naws lambda-web deploy --name app --code .\n```' in readme


def test_scaffold_server_listens_not_handler(tmp_path):
    # The starter listens for HTTP requests instead of exporting a handler.
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', NODE)
    src = _read(dest, 'server.ts')
    assert '.listen(' in src
    assert f'process.env.{constants.LOCAL_PORT_ENV_VAR}' in src
    assert f'?? {constants.RUNTIME_HTTP_PORT}' in src
    assert 'server.listen(port' in src
    assert 'AWS_LAMBDA_HTTP_ENDPOINT' not in src
    assert 'export const handler' not in src
    assert 'exports.handler' not in src


def test_python_scaffold_exposes_wsgi_app_without_server_at_import(tmp_path):
    # The starter is a WSGI callable; the local server lives under __main__.
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', PYTHON)
    src = _read(dest, 'main.py')
    assert 'def app(environ, start_response):' in src
    assert 'if __name__ == "__main__":' in src
    assert src.index('def app(') < src.index('if __name__')
    assert 'wsgiref' in src
    assert (
        f'"{constants.LOCAL_PORT_ENV_VAR}", {constants.RUNTIME_HTTP_PORT}'
        in (src)
    )
    assert 'AWS_LAMBDA_HTTP_ENDPOINT' not in src
    assert 'handler' not in src
    assert 'import uvicorn' not in src


def test_python_scaffold_serves_hello_world(tmp_path):
    # Import the module without starting the server and exercise ``app`` the
    # way a WSGI server would.
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', PYTHON)
    script = (
        'import json, os, sys\n'
        'sys.path.insert(0, os.getcwd())\n'
        'import main\n'
        'status = []\n'
        'def start_response(code, headers):\n'
        '    status.append((code, dict(headers)))\n'
        'body = b"".join(main.app({"PATH_INFO": "/x"}, start_response))\n'
        'print(json.dumps([status, body.decode()]))\n'
    )
    result = subprocess.run(
        [sys.executable, '-I', '-c', script],
        cwd=dest,
        capture_output=True,
        text=True,
        check=True,
    )
    status, body = json.loads(result.stdout)
    assert status == [['200 OK', {'content-type': 'application/json'}]]
    assert json.loads(body) == {
        'message': 'Hello from Lambda Web!',
        'path': '/x',
    }


def test_scaffold_package_json_self_describes_entry(tmp_path):
    # package.json "main" must point at the scaffold entry so redeploys
    # auto-detect it, and it must be an ESM module with a deploy script.
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', NODE)
    pkg = json.loads(_read(dest, 'package.json'))
    assert pkg['main'] == 'server.ts'
    assert pkg['private'] is True
    assert pkg['type'] == 'module'
    assert 'description' not in pkg
    assert pkg['scripts']['start'] == 'node server.ts'
    assert pkg['scripts']['deploy'] == (
        'aws lambda-web deploy --name app --code .'
    )
    # resolve_entry_point (used on every redeploy) picks up server.ts via main.
    assert nodejs.resolve_entry_point(dest) == 'server.ts'


@pytest.mark.parametrize('runtime', RUNTIMES)
def test_scaffold_is_detected_and_resolves_its_own_entry(tmp_path, runtime):
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', runtime)
    assert runtime.detect(dest)
    assert runtime.resolve_entry(dest).display == runtime.scaffold_entry()


def test_scaffold_bundles_with_import_wrapper(tmp_path):
    # server.ts is not index.js, so build_zip injects an index.js wrapper that
    # dynamically imports the TypeScript entry with the default runtime.
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', NODE)
    path, _ = bundle.build_zip(
        dest,
        NODE.resolve_entry(dest),
        exclude_patterns=(),
        include_hidden=False,
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


def test_python_scaffold_bundles_without_wrapper_or_env(tmp_path):
    dest = str(tmp_path / 'app')
    scaffold.write_hello_world(dest, 'app', PYTHON)
    selection = PYTHON.resolve_entry(dest)
    assert selection.env is None
    assert selection.wrapper is None
    path, _ = bundle.build_zip(
        dest, selection, exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            assert set(zf.namelist()) == {'main.py', 'README.md', 'AGENTS.md'}
    finally:
        os.unlink(path)


def test_write_hello_world_refuses_non_empty_dir(tmp_path):
    dest = str(tmp_path / 'app')
    os.makedirs(dest)
    with open(os.path.join(dest, 'existing.js'), 'w', encoding='utf-8') as f:
        f.write('// pre-existing')
    with pytest.raises(InvalidSourceError) as excinfo:
        scaffold.write_hello_world(dest, 'app', NODE)
    assert 'does not overwrite files' in str(excinfo.value)
    # The pre-existing file is untouched.
    assert _read(dest, 'existing.js') == '// pre-existing'


def test_write_hello_world_refuses_file_target(tmp_path):
    dest = str(tmp_path / 'afile')
    with open(dest, 'w', encoding='utf-8') as f:
        f.write('x')
    with pytest.raises(InvalidSourceError):
        scaffold.write_hello_world(dest, 'app', NODE)


def test_write_hello_world_wraps_write_error(tmp_path):
    dest = str(tmp_path / 'app')
    with (
        mock.patch.object(
            scaffold, '_write', side_effect=OSError('disk full')
        ),
        pytest.raises(InvalidSourceError, match='might contain files'),
    ):
        scaffold.write_hello_world(dest, 'app', NODE)


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
