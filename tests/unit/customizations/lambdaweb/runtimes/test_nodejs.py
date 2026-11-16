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

import pytest

from awscli.customizations.lambdaweb.constants import ENTRY_POINT_CANDIDATES
from awscli.customizations.lambdaweb.exceptions import (
    EntryPointNotFoundError,
    InvalidSourceError,
    MalformedPackageJsonError,
)
from awscli.customizations.lambdaweb.runtimes import nodejs


def _write(path, content=''):
    with open(path, 'w') as f:
        f.write(content)


def test_resolve_explicit_entry_relative(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'app.js'), '// app')
    assert nodejs.resolve_entry_point(src, explicit='./app.js') == 'app.js'


def test_resolve_explicit_entry_absolute_rejected(tmp_path):
    src = str(tmp_path)
    abs_entry = os.path.join(src, 'app.js')
    _write(abs_entry, '// app')
    with pytest.raises(InvalidSourceError):
        nodejs.resolve_entry_point(src, explicit=abs_entry)


def test_resolve_explicit_entry_escape_rejected(tmp_path):
    src = str(tmp_path / 'inner')
    os.makedirs(src)
    _write(str(tmp_path / 'outside.js'), '// outside')
    with pytest.raises(InvalidSourceError):
        nodejs.resolve_entry_point(src, explicit='../outside.js')


def test_resolve_falls_back_to_package_main(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'server.js'), '// real')
    _write(
        os.path.join(src, 'package.json'),
        '{"main": "server.js"}',
    )
    assert nodejs.resolve_entry_point(src) == 'server.js'


def test_resolve_falls_back_to_index_js(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    assert nodejs.resolve_entry_point(src) == 'index.js'


def test_resolve_raises_when_no_candidate(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'README.md'), '# hi')
    with pytest.raises(EntryPointNotFoundError) as excinfo:
        nodejs.resolve_entry_point(src)
    message = str(excinfo.value)
    assert ', '.join(ENTRY_POINT_CANDIDATES) in message
    assert str(list(ENTRY_POINT_CANDIDATES)) not in message


def test_resolve_uses_exports_bare_string(tmp_path):
    # Modern packages may declare only "exports" (no "main"). A bare-string
    # "." export resolves to that file.
    src = str(tmp_path)
    os.makedirs(os.path.join(src, 'dist'))
    _write(os.path.join(src, 'dist', 'index.js'), '// built')
    _write(
        os.path.join(src, 'package.json'),
        '{"exports": "./dist/index.js"}',
    )
    assert nodejs.resolve_entry_point(src) == 'dist/index.js'


def test_resolve_exports_conditions_prefer_import(tmp_path):
    # The injected wrapper loads via dynamic import(), so the ESM ("import")
    # target is preferred over the CJS ("require") one for a dual package.
    src = str(tmp_path)
    os.makedirs(os.path.join(src, 'dist'))
    _write(os.path.join(src, 'dist', 'esm.js'), '// esm')
    _write(os.path.join(src, 'dist', 'cjs.js'), '// cjs')
    _write(
        os.path.join(src, 'package.json'),
        '{"exports": {".": {"require": "./dist/cjs.js", '
        '"import": "./dist/esm.js"}}}',
    )
    assert nodejs.resolve_entry_point(src) == 'dist/esm.js'


def test_resolve_exports_require_only(tmp_path):
    # A CJS-only package that still uses an exports map resolves via "require".
    src = str(tmp_path)
    os.makedirs(os.path.join(src, 'dist'))
    _write(os.path.join(src, 'dist', 'cjs.js'), '// cjs')
    _write(
        os.path.join(src, 'package.json'),
        '{"exports": {".": {"require": "./dist/cjs.js"}}}',
    )
    assert nodejs.resolve_entry_point(src) == 'dist/cjs.js'


def test_resolve_exports_bare_conditions_object(tmp_path):
    # "exports" may be a bare conditions object with no "." subpath key.
    src = str(tmp_path)
    os.makedirs(os.path.join(src, 'dist'))
    _write(os.path.join(src, 'dist', 'esm.js'), '// esm')
    _write(
        os.path.join(src, 'package.json'),
        '{"exports": {"import": "./dist/esm.js", '
        '"require": "./dist/cjs.js"}}',
    )
    assert nodejs.resolve_entry_point(src) == 'dist/esm.js'


@pytest.mark.parametrize(
    'exports',
    [
        [None, './dist/index.js'],
        {'.': {'import': [None, './dist/index.js']}},
    ],
)
def test_resolve_exports_array_fallback(tmp_path, exports):
    src = str(tmp_path)
    os.makedirs(os.path.join(src, 'dist'))
    _write(os.path.join(src, 'dist', 'index.js'), '// built')
    _write(
        os.path.join(src, 'package.json'),
        json.dumps({'exports': exports}),
    )

    assert nodejs.resolve_entry_point(src) == 'dist/index.js'


def test_resolve_main_wins_over_exports(tmp_path):
    # When both are present and "main" points at a real file, "main" wins
    # (it is the older, more specific field and existing behavior).
    src = str(tmp_path)
    os.makedirs(os.path.join(src, 'dist'))
    _write(os.path.join(src, 'main.js'), '// main')
    _write(os.path.join(src, 'dist', 'index.js'), '// built')
    _write(
        os.path.join(src, 'package.json'),
        '{"main": "main.js", "exports": "./dist/index.js"}',
    )
    assert nodejs.resolve_entry_point(src) == 'main.js'


def test_resolve_main_handles_utf8_bom_and_normalizes_dot_prefix(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'server.js'), '// server')
    with open(
        os.path.join(src, 'package.json'), 'w', encoding='utf-8-sig'
    ) as f:
        json.dump(
            {'name': 'café', 'main': './server.js'},
            f,
            ensure_ascii=False,
        )

    assert nodejs.resolve_entry_point(src) == 'server.js'


def test_resolve_exports_missing_file_falls_through(tmp_path):
    # "exports" is only a discovery heuristic: if it points at an unbuilt
    # output (file absent), fall through to candidate scanning rather than
    # resolve to a path that would not actually ship.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(
        os.path.join(src, 'package.json'),
        '{"exports": "./dist/index.js"}',
    )
    assert nodejs.resolve_entry_point(src) == 'index.js'


@pytest.mark.parametrize(
    'bad_target',
    [
        '../evil.js',
        '/etc/passwd',
        './../evil.js',
    ],
)
def test_resolve_exports_escape_ignored(tmp_path, bad_target):
    # An absolute path or parent-dir escape in "exports" is never honored;
    # resolution falls through to the safe candidate list.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(
        os.path.join(src, 'package.json'),
        f'{{"exports": "{bad_target}"}}',
    )
    assert nodejs.resolve_entry_point(src) == 'index.js'


def test_malformed_package_json_does_not_echo_contents(tmp_path):
    src = str(tmp_path)
    _write(
        os.path.join(src, 'package.json'),
        '{"secret":"AKIA1234567890","main":"index.js",,}',
    )
    _write(os.path.join(src, 'index.js'), '// idx')
    with pytest.raises(MalformedPackageJsonError) as excinfo:
        nodejs.resolve_entry_point(src)
    msg = str(excinfo.value)
    assert 'AKIA' not in msg
    assert 'AKIA1234567890' not in msg
    assert 'secret' not in msg


def test_unreadable_package_json_raises_friendly_error(tmp_path, monkeypatch):
    src = str(tmp_path)
    package_json = os.path.join(src, 'package.json')
    _write(package_json, '{}')

    def raise_permission_error(*args, **kwargs):
        raise PermissionError('permission denied')

    monkeypatch.setattr('builtins.open', raise_permission_error)
    with pytest.raises(InvalidSourceError) as excinfo:
        nodejs.resolve_entry_point(src)

    message = str(excinfo.value)
    assert package_json in message
    assert 'readable' in message


def test_verify_entrypoint_accepts_existing_file(tmp_path):
    entrypoint = tmp_path / 'server.js'
    entrypoint.write_text('export default {};\n')

    nodejs.verify_entrypoint_in_tree(str(tmp_path), 'server.js')


def test_verify_entrypoint_rejects_missing_file(tmp_path):
    with pytest.raises(InvalidSourceError, match='no such file'):
        nodejs.verify_entrypoint_in_tree(str(tmp_path), 'server.js')


def test_verify_entrypoint_warns_for_uncertain_path(tmp_path, capsys):
    nodejs.verify_entrypoint_in_tree(str(tmp_path), '../server.js')

    assert 'Warning:' in capsys.readouterr().err
