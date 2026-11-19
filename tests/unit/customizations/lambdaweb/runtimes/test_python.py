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
from unittest import mock

import pytest

from awscli.customizations.lambdaweb.exceptions import (
    EntryPointNotFoundError,
    InvalidSourceError,
)
from awscli.customizations.lambdaweb.runtimes import python

RUNTIME = python.RUNTIME
ENV_VAR = python.ENTRYPOINT_ENV_VAR


def _write(directory, relpath, content=''):
    path = os.path.join(directory, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def _dist_info(directory, name, tag, purelib=False):
    lines = ['Wheel-Version: 1.0', f'Tag: {tag}']
    if purelib:
        lines.append('Root-Is-Purelib: true')
    _write(directory, f'{name}.dist-info/WHEEL', '\n'.join(lines) + '\n')


# --- entry grammar -----------------------------------------------------------


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('main:app', (None, 'main', 'app')),
        ('app.main:app', (None, 'app.main', 'app')),
        ('asgi:main:app', ('asgi', 'main', 'app')),
        (
            'wsgi:mysite.wsgi:application',
            ('wsgi', 'mysite.wsgi', 'application'),
        ),
        ('main:factory.application', (None, 'main', 'factory.application')),
        # a two-part value never selects an interface, matching the runtime.
        ('asgi:application', (None, 'asgi', 'application')),
    ],
)
def test_parse_entry(value, expected):
    assert python.parse_entry(value) == expected
    assert python.format_entry(*expected) == value


@pytest.mark.parametrize(
    'value',
    [
        'main',
        'main:',
        ':app',
        'http:main:app',
        'asgi:wsgi:main:app',
        ' main:app',
        'main:app ',
        'main:app()',
        'my-app:app',
        'class:app',
        'main:app.',
        '1main:app',
    ],
)
def test_parse_entry_rejects_invalid_values(value):
    with pytest.raises(InvalidSourceError) as excinfo:
        python.parse_entry(value)
    message = str(excinfo.value)
    assert repr(value) in message or f"'{value}'" in message
    assert 'uvicorn or gunicorn' in message
    assert 'asgi: or wsgi:' in message


# --- explicit --entry-point --------------------------------------------------


def test_explicit_module_object_is_verified_in_tree(tmp_path):
    src = str(tmp_path)
    _write(src, 'api/server.py', 'app = object()\n')
    selection = RUNTIME.resolve_entry(src, 'api.server:app')
    assert selection.display == 'api.server:app'
    assert selection.bundle_path == 'api/server.py'
    assert selection.wrapper is None
    assert selection.env == {ENV_VAR: 'api.server:app'}


def test_explicit_prefixed_entry_is_kept_verbatim(tmp_path):
    src = str(tmp_path)
    _write(src, 'main.py', 'application = object()\n')
    selection = RUNTIME.resolve_entry(src, 'wsgi:main:application')
    assert selection.display == 'wsgi:main:application'
    assert selection.env == {ENV_VAR: 'wsgi:main:application'}


def test_explicit_default_entry_sets_no_env(tmp_path):
    src = str(tmp_path)
    _write(src, 'main.py', 'app = object()\n')
    selection = RUNTIME.resolve_entry(src, 'main:app')
    assert selection.env is None
    assert selection.bundle_path == 'main.py'


def test_explicit_package_module_resolves_to_init(tmp_path):
    src = str(tmp_path)
    _write(src, 'api/__init__.py', 'app = object()\n')
    assert RUNTIME.resolve_entry(src, 'api:app').bundle_path == (
        'api/__init__.py'
    )


def test_explicit_namespace_package_is_rejected(tmp_path):
    src = str(tmp_path)
    _write(src, 'api/routes.py', '')
    with pytest.raises(InvalidSourceError) as excinfo:
        RUNTIME.resolve_entry(src, 'api:app')
    assert '__init__.py' in str(excinfo.value)


def test_explicit_missing_module_errors(tmp_path):
    with pytest.raises(EntryPointNotFoundError) as excinfo:
        RUNTIME.resolve_entry(str(tmp_path), 'missing.server:app')
    message = str(excinfo.value)
    assert "'missing.server'" in message
    assert 'missing/server.py' in message


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('src/server.py', 'src.server:app'),
        ('./src/server.py', 'src.server:app'),
        ('src/server.py:application', 'src.server:application'),
        ('server.py', 'server:app'),
        ('pkg/__init__.py', 'pkg:app'),
        ('main.py', 'main:app'),
    ],
)
def test_explicit_path_form(tmp_path, value, expected):
    src = str(tmp_path)
    _write(src, 'src/server.py', '')
    _write(src, 'server.py', '')
    _write(src, 'pkg/__init__.py', '')
    _write(src, 'main.py', '')
    selection = RUNTIME.resolve_entry(src, value)
    assert selection.display == expected
    if expected == 'main:app':
        assert selection.env is None
    else:
        assert selection.env == {ENV_VAR: expected}


def test_explicit_path_form_missing_file(tmp_path):
    with pytest.raises(EntryPointNotFoundError, match='not found'):
        RUNTIME.resolve_entry(str(tmp_path), 'src/server.py')


def test_explicit_path_form_rejects_non_identifier_segments(tmp_path):
    src = str(tmp_path)
    _write(src, 'my-app/server.py', '')
    with pytest.raises(InvalidSourceError) as excinfo:
        RUNTIME.resolve_entry(src, 'my-app/server.py')
    message = str(excinfo.value)
    assert 'not a valid identifier' in message
    assert 'module:object' in message


def test_explicit_path_form_rejects_escape_and_absolute(tmp_path):
    src = str(tmp_path)
    _write(src, 'server.py', '')
    with pytest.raises(InvalidSourceError, match='escapes'):
        RUNTIME.resolve_entry(src, '../server.py')
    with pytest.raises(InvalidSourceError, match='relative'):
        RUNTIME.resolve_entry(src, os.path.join(src, 'server.py'))


def test_explicit_path_form_with_bad_object(tmp_path):
    src = str(tmp_path)
    _write(src, 'server.py', '')
    with pytest.raises(InvalidSourceError):
        RUNTIME.resolve_entry(src, 'server.py:my app')


# --- automatic resolution ----------------------------------------------------


@pytest.mark.parametrize(
    ('files', 'expected'),
    [
        ({'main.py': 'app = 1\n'}, 'main:app'),
        ({'app.py': 'app = Flask(__name__)\n'}, 'app:app'),
        ({'application.py': 'application = 1\n'}, 'application:application'),
        (
            {'asgi.py': 'application = get_asgi_application()\n'},
            ('asgi:application'),
        ),
        ({'wsgi.py': 'application = 1\n'}, 'wsgi:application'),
        ({'server.py': ''}, 'server:app'),
        ({'src/main.py': 'app = 1\n'}, 'src.main:app'),
        (
            {'app/main.py': 'app = FastAPI()\n', 'app/__init__.py': ''},
            ('app.main:app'),
        ),
        # object sniffing: ``application`` only when ``app`` is absent.
        ({'main.py': 'application = 1\n'}, 'main:application'),
        ({'main.py': 'app: FastAPI = FastAPI()\n'}, 'main:app'),
        ({'main.py': 'application = 1\napp = 2\n'}, 'main:app'),
        ({'main.py': 'myapp = 1\n'}, 'main:app'),
        # order: main.py wins over app.py.
        ({'main.py': 'app = 1\n', 'app.py': 'app = 2\n'}, 'main:app'),
    ],
)
def test_resolve_entry_point_candidates(tmp_path, files, expected):
    src = str(tmp_path)
    for relpath, content in files.items():
        _write(src, relpath, content)
    assert python.resolve_entry_point(src) == expected


def test_resolve_entry_point_django_from_manage_py(tmp_path):
    src = str(tmp_path)
    _write(
        src,
        'manage.py',
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')\n",
    )
    _write(src, 'mysite/wsgi.py', 'application = get_wsgi_application()\n')
    assert python.resolve_entry_point(src) == 'mysite.wsgi:application'
    _write(src, 'mysite/asgi.py', 'application = get_asgi_application()\n')
    assert python.resolve_entry_point(src) == 'mysite.asgi:application'


def test_resolve_entry_point_django_without_settings_hint(tmp_path):
    src = str(tmp_path)
    _write(src, 'manage.py', 'print("custom")\n')
    _write(src, 'shop/asgi.py', '')
    _write(src, 'shop/settings.py', '')
    # A directory without Django settings never qualifies, so an installed
    # dependency such as asgiref is not chosen.
    _write(src, 'asgiref/wsgi.py', '')
    assert python.resolve_entry_point(src) == 'shop.asgi:application'


def test_resolve_entry_point_django_split_settings_package(tmp_path):
    src = str(tmp_path)
    _write(
        src,
        'manage.py',
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', "
        "'config.settings.local')\n",
    )
    _write(src, 'config/wsgi.py', '')
    _write(src, 'config/settings/base.py', '')
    _write(src, 'asgiref/wsgi.py', '')
    assert python.resolve_entry_point(src) == 'config.wsgi:application'


def test_resolve_entry_point_django_project_beats_dependency_asgi(tmp_path):
    src = str(tmp_path)
    _write(
        src,
        'manage.py',
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')\n",
    )
    _write(src, 'mysite/wsgi.py', '')
    _write(src, 'mysite/settings.py', '')
    _write(src, 'somedep/asgi.py', '')
    assert python.resolve_entry_point(src) == 'mysite.wsgi:application'


def test_resolve_entry_point_django_without_settings_anywhere_errors(tmp_path):
    src = str(tmp_path)
    _write(src, 'manage.py', 'print("custom")\n')
    _write(src, 'blog/wsgi.py', '')
    _write(src, 'shop/asgi.py', '')
    with pytest.raises(EntryPointNotFoundError):
        python.resolve_entry_point(src)


def test_resolve_entry_point_not_found(tmp_path):
    src = str(tmp_path)
    _write(src, 'requirements.txt', 'flask\n')
    with pytest.raises(EntryPointNotFoundError) as excinfo:
        python.resolve_entry_point(src)
    message = str(excinfo.value)
    assert 'main.py, app.py' in message
    assert 'manage.py' in message
    assert '--entry-point module:object' in message


def test_resolve_entry_sets_env_only_for_non_default(tmp_path):
    src = str(tmp_path)
    _write(src, 'app.py', 'app = 1\n')
    selection = RUNTIME.resolve_entry(src)
    assert selection.display == 'app:app'
    assert selection.bundle_path == 'app.py'
    assert selection.env == {ENV_VAR: 'app:app'}


# --- customer-set environment variable --------------------------------------


def test_customer_entry_verifies_module(tmp_path):
    src = str(tmp_path)
    _write(src, 'svc/api.py', '')
    selection = RUNTIME.customer_entry('asgi:svc.api:app', src)
    assert selection.display == 'asgi:svc.api:app'
    assert selection.bundle_path == 'svc/api.py'
    assert selection.env == {ENV_VAR: 'asgi:svc.api:app'}


def test_customer_entry_missing_module(tmp_path):
    with pytest.raises(EntryPointNotFoundError, match="'svc.api'"):
        RUNTIME.customer_entry('svc.api:app', str(tmp_path))


def test_customer_entry_invalid_value(tmp_path):
    with pytest.raises(InvalidSourceError) as excinfo:
        RUNTIME.customer_entry('main', str(tmp_path))
    assert ENV_VAR in str(excinfo.value)


# --- detection and exclusions -----------------------------------------------


def test_detect_markers(tmp_path):
    src = str(tmp_path)
    assert not RUNTIME.detect(src)
    _write(src, 'Pipfile', '')
    assert RUNTIME.detect(src)


def test_exclude_patterns_cover_virtualenvs_and_caches():
    patterns = RUNTIME.exclude_patterns
    for name in ('venv/', '.venv/', '*.egg-info/', '.pytest_cache/', '.tox/'):
        assert name in patterns
    assert '*.dist-info/' not in patterns
    assert 'build/' not in patterns
    assert 'tests/' not in patterns


# --- dependency inspection ---------------------------------------------------


def _warning(capsys):
    return capsys.readouterr().err


def test_inspect_dependencies_quiet_without_manifest(tmp_path, capsys):
    _write(str(tmp_path), 'main.py', 'app = 1\n')
    RUNTIME.inspect_dependencies(str(tmp_path), 'python3.14')
    assert _warning(capsys) == ''


def test_inspect_dependencies_quiet_for_comment_only_requirements(
    tmp_path, capsys
):
    _write(str(tmp_path), 'requirements.txt', '# none yet\n\n')
    RUNTIME.inspect_dependencies(str(tmp_path), 'python3.14')
    assert _warning(capsys) == ''


def test_inspect_dependencies_warns_when_not_installed_with_pip(
    tmp_path, capsys
):
    src = str(tmp_path)
    _write(src, 'requirements.txt', 'fastapi\n')
    with mock.patch.object(python.shutil, 'which', return_value=None):
        RUNTIME.inspect_dependencies(src, 'python3.14')
    warning = _warning(capsys)
    assert 'requirements.txt declares dependencies' in warning
    assert 'python3.14 runtime' in warning
    assert (
        'pip install -r requirements.txt --target . --only-binary=:all: '
        '--platform manylinux2014_aarch64 '
        '--platform manylinux_2_28_aarch64 '
        '--platform manylinux_2_34_aarch64 --implementation cp '
        '--python-version 3.14'
    ) in warning
    assert 'uv ' not in warning


def test_inspect_dependencies_prefers_uv_when_on_path(tmp_path, capsys):
    src = str(tmp_path)
    _write(src, 'requirements.txt', 'fastapi\n')
    with mock.patch.object(python.shutil, 'which', return_value='/bin/uv'):
        RUNTIME.inspect_dependencies(src, 'python3.14')
    assert (
        'uv pip install -r requirements.txt --target . --python-platform '
        'aarch64-manylinux_2_34 --python-version 3.14'
    ) in _warning(capsys)


def test_inspect_dependencies_prefers_uv_for_uv_lock(tmp_path, capsys):
    src = str(tmp_path)
    _write(src, 'pyproject.toml', '[project]\ndependencies = ["flask"]\n')
    _write(src, 'uv.lock', '')
    with mock.patch.object(python.shutil, 'which', return_value=None):
        RUNTIME.inspect_dependencies(src, 'python3.15')
    warning = _warning(capsys)
    assert 'uv.lock declares dependencies' in warning
    assert 'uv pip install -r pyproject.toml --target .' in warning
    assert '--python-version 3.15' in warning


def test_inspect_dependencies_pyproject_without_requirements_and_uv(
    tmp_path, capsys
):
    src = str(tmp_path)
    _write(
        src, 'pyproject.toml', '[project]\ndependencies = [\n  "flask",\n]\n'
    )
    with mock.patch.object(python.shutil, 'which', return_value=None):
        RUNTIME.inspect_dependencies(src, 'python3.14')
    warning = _warning(capsys)
    assert 'pyproject.toml declares dependencies' in warning
    assert 'export the dependencies to requirements.txt, then pip install' in (
        warning
    )


def test_inspect_dependencies_quiet_for_pyproject_without_dependencies(
    tmp_path, capsys
):
    _write(str(tmp_path), 'pyproject.toml', '[project]\nname = "x"\n')
    RUNTIME.inspect_dependencies(str(tmp_path), 'python3.14')
    assert _warning(capsys) == ''


def test_inspect_dependencies_quiet_when_installed_for_arm64(tmp_path, capsys):
    src = str(tmp_path)
    _write(src, 'requirements.txt', 'pydantic-core\nrequests\ncryptography\n')
    _dist_info(src, 'pydantic_core-2.0', 'cp314-cp314-manylinux_2_17_aarch64')
    _dist_info(src, 'requests-2.32', 'py3-none-any')
    _dist_info(src, 'cryptography-43', 'cp39-abi3-manylinux2014_aarch64')
    _dist_info(src, 'unknown-1.0', 'cp314-cp314-macosx_11_0_arm64', True)
    RUNTIME.inspect_dependencies(src, 'python3.14')
    assert _warning(capsys) == ''


def test_inspect_dependencies_warns_for_foreign_wheels(tmp_path, capsys):
    src = str(tmp_path)
    _write(src, 'requirements.txt', 'pydantic-core\n')
    _dist_info(src, 'pydantic_core-2.0', 'cp314-cp314-macosx_11_0_arm64')
    _dist_info(src, 'orjson-3.10', 'cp314-cp314-manylinux_2_17_x86_64')
    _dist_info(src, 'uvloop-0.21', 'cp314-cp314-musllinux_1_2_aarch64')
    _dist_info(src, 'requests-2.32', 'py3-none-any')
    with mock.patch.object(python.shutil, 'which', return_value=None):
        RUNTIME.inspect_dependencies(src, 'python3.14')
    warning = _warning(capsys)
    assert '3 installed package(s) were built for another platform' in warning
    assert 'orjson-3.10 (manylinux_2_17_x86_64)' in warning
    assert 'pydantic_core-2.0 (macosx_11_0_arm64)' in warning
    assert 'uvloop-0.21 (musllinux_1_2_aarch64)' in warning
    assert 'requests' not in warning
    assert 'arm64 Linux' in warning
    assert '--python-version 3.14' in warning


def test_inspect_dependencies_truncates_long_foreign_list(tmp_path, capsys):
    src = str(tmp_path)
    for index in range(7):
        _dist_info(src, f'pkg{index}-1.0', 'cp314-cp314-win_amd64')
    RUNTIME.inspect_dependencies(src, 'python3.14')
    warning = _warning(capsys)
    assert '7 installed package(s)' in warning
    assert 'and 2 more' in warning


# --- scaffold -----------------------------------------------------------------


def test_scaffold_files_and_entry():
    files = RUNTIME.scaffold_files('demo')
    assert list(files) == ['main.py']
    assert 'def app(environ, start_response):' in files['main.py']
    assert RUNTIME.scaffold_entry() == 'main:app'
    assert RUNTIME.docs.entry_file == 'main.py'


def test_explicit_root_file_with_object(tmp_path):
    src = str(tmp_path)
    _write(src, 'main.py', '')
    _write(src, 'server.py', '')
    selection = RUNTIME.resolve_entry(src, 'main.py:app')
    assert selection.display == 'main:app'
    assert selection.env is None
    selection = RUNTIME.resolve_entry(src, 'server.py:application')
    assert selection.display == 'server:application'
    assert selection.env == {ENV_VAR: 'server:application'}


def test_dist_info_scan_handles_glob_metacharacters(tmp_path, capsys):
    src = os.path.join(str(tmp_path), 'proj[2024]')
    _write(src, 'requirements.txt', 'pydantic-core\n')
    _dist_info(src, 'pydantic_core-2.0', 'cp315-cp315-macosx_11_0_arm64')
    with mock.patch.object(python.shutil, 'which', return_value=None):
        RUNTIME.inspect_dependencies(src, 'python3.15')
    assert 'built for another platform' in capsys.readouterr().err


def test_django_detection_handles_glob_metacharacters(tmp_path):
    src = os.path.join(str(tmp_path), 'proj[2024]')
    _write(src, 'manage.py', '')
    _write(src, 'shop/asgi.py', '')
    _write(src, 'shop/settings.py', '')
    assert python.resolve_entry_point(src) == 'shop.asgi:application'


def test_customer_entry_missing_module_names_the_variable(tmp_path):
    with pytest.raises(EntryPointNotFoundError) as excinfo:
        RUNTIME.customer_entry('svc.api:app', str(tmp_path))
    message = str(excinfo.value)
    assert ENV_VAR in message
    assert '--entry-point' not in message


def test_explicit_path_form_infers_object_name(tmp_path):
    src = str(tmp_path)
    _write(src, 'app.py', 'application = object()\n')
    selection = RUNTIME.resolve_entry(src, 'app.py')
    assert selection.display == 'app:application'
    # An explicit object always wins over the module's assignments.
    selection = RUNTIME.resolve_entry(src, 'app.py:app')
    assert selection.display == 'app:app'


def test_inspect_dependencies_quiet_for_option_only_requirements(
    tmp_path, capsys
):
    _write(
        str(tmp_path),
        'requirements.txt',
        '--index-url https://example.com/simple\n--pre\n',
    )
    RUNTIME.inspect_dependencies(str(tmp_path), 'python3.15')
    assert capsys.readouterr().err == ''


def test_inspect_dependencies_warns_for_requirements_reference(
    tmp_path, capsys
):
    _write(str(tmp_path), 'requirements.txt', '-r requirements/prod.txt\n')
    with mock.patch.object(python.shutil, 'which', return_value=None):
        RUNTIME.inspect_dependencies(str(tmp_path), 'python3.15')
    assert 'declares dependencies' in capsys.readouterr().err


def test_install_command_lock_file_without_installable_source(tmp_path):
    src = str(tmp_path)
    _write(src, 'Pipfile.lock', '')
    with mock.patch.object(python.shutil, 'which', return_value='/bin/uv'):
        command = python.install_command(src, 'python3.15')
    assert command.startswith('export the dependencies to requirements.txt')
    assert '-r requirements.txt' in command
    assert 'pyproject.toml' not in command


def test_inspect_dependencies_warns_for_wrong_python_version_wheel(
    tmp_path, capsys
):
    src = str(tmp_path)
    _write(src, 'requirements.txt', 'pkg\n')
    _dist_info(src, 'pkg-1.0', 'cp313-cp313-manylinux_2_17_aarch64')
    _dist_info(src, 'freethreaded-1.0', 'cp315-cp315t-manylinux_2_28_aarch64')
    _dist_info(src, 'futureabi-1.0', 'cp316-abi3-manylinux2014_aarch64')
    _dist_info(src, 'stable-1.0', 'cp39-abi3-manylinux2014_aarch64')
    _dist_info(src, 'current-1.0', 'cp315-cp315-manylinux_2_28_aarch64')
    with mock.patch.object(python.shutil, 'which', return_value=None):
        RUNTIME.inspect_dependencies(src, 'python3.15')
    warning = capsys.readouterr().err
    assert 'another platform or Python version' in warning
    assert 'pkg-1.0 (cp313-cp313)' in warning
    assert 'freethreaded-1.0 (cp315-cp315t)' in warning
    assert 'futureabi-1.0 (cp316-abi3)' in warning
    assert 'stable-1.0' not in warning
    assert 'current-1.0' not in warning


def test_factory_module_warns_about_unresolvable_object(tmp_path, capsys):
    src = str(tmp_path)
    _write(src, 'main.py', 'def create_app():\n    return object()\n')
    assert python.resolve_entry_point(src) == 'main:app'
    warning = capsys.readouterr().err
    assert "does not define 'app' or 'application'" in warning
    assert '--entry-point module:object' in warning


def test_reexported_object_counts_as_evidence(tmp_path, capsys):
    src = str(tmp_path)
    _write(src, 'main.py', 'from myproj.wsgi import application\n')
    assert python.resolve_entry_point(src) == 'main:application'
    assert capsys.readouterr().err == ''


def test_def_based_object_counts_as_evidence(tmp_path, capsys):
    src = str(tmp_path)
    _write(src, 'main.py', 'def app(environ, start_response):\n    pass\n')
    assert python.resolve_entry_point(src) == 'main:app'
    assert capsys.readouterr().err == ''


def test_runtime_symlink_hints_are_language_specific():
    from awscli.customizations.lambdaweb.runtimes import nodejs

    assert 'pip' in python.RUNTIME.symlink_hint
    assert 'npm' not in python.RUNTIME.symlink_hint
    assert 'npm install' in nodejs.RUNTIME.symlink_hint


def test_explicit_prefixed_path_form_errors_clearly(tmp_path):
    src = str(tmp_path)
    _write(src, 'main.py', 'app = 1\n')
    with pytest.raises(InvalidSourceError) as excinfo:
        RUNTIME.resolve_entry(src, 'wsgi:main.py')
    message = str(excinfo.value)
    assert 'interface prefix' in message
    assert 'wsgi:main:app' in message
    with pytest.raises(InvalidSourceError) as excinfo:
        RUNTIME.resolve_entry(src, 'asgi:main.py:app')
    assert 'asgi:main:app' in str(excinfo.value)


def test_explicit_path_not_found_names_the_flag(tmp_path):
    with pytest.raises(EntryPointNotFoundError) as excinfo:
        RUNTIME.resolve_entry(str(tmp_path), 'missing.py')
    assert "--entry-point 'missing.py'" in str(excinfo.value)


def test_declared_dependencies_pipfile_and_poetry(tmp_path):
    src = str(tmp_path)
    _write(src, 'Pipfile', '[packages]\nflask = "*"\n')
    assert python._declared_dependencies(src) == 'Pipfile'
    os.remove(os.path.join(src, 'Pipfile'))
    _write(
        src,
        'pyproject.toml',
        '[tool.poetry.dependencies]\npython = "^3.12"\nflask = "*"\n',
    )
    assert python._declared_dependencies(src) == 'pyproject.toml'
    _write(
        src,
        'pyproject.toml',
        '[tool.poetry.dependencies]\npython = "^3.12"\n',
    )
    assert python._declared_dependencies(src) is None


def test_inspect_dependencies_tolerates_unversioned_runtime_id(
    tmp_path, capsys
):
    src = str(tmp_path)
    _write(src, 'requirements.txt', 'cryptography\n')
    _dist_info(src, 'cryptography-43', 'cp39-abi3-manylinux2014_aarch64')
    _dist_info(src, 'pydantic_core-2.0', 'cp315-cp315-manylinux_2_28_aarch64')
    RUNTIME.inspect_dependencies(src, 'python3')
    assert capsys.readouterr().err == ''
