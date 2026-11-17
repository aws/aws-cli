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
import sys
import zipfile

import pytest

from awscli.customizations.lambdaweb import bundle
from awscli.customizations.lambdaweb.constants import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_INCLUDED_HIDDEN_DIRECTORIES,
    DEFAULT_INCLUDED_HIDDEN_FILES,
    ENTRY_POINT_CANDIDATES,
)
from awscli.customizations.lambdaweb.exceptions import (
    EntryPointNotFoundError,
    InvalidFunctionNameError,
    InvalidSourceError,
    MalformedPackageJsonError,
    WrapperConflictError,
)


def _write(path, content=''):
    with open(path, 'w') as f:
        f.write(content)


def test_resolve_explicit_entry_relative(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'app.js'), '// app')
    assert bundle.resolve_entry_point(src, explicit='./app.js') == 'app.js'


def test_resolve_explicit_entry_absolute_rejected(tmp_path):
    src = str(tmp_path)
    abs_entry = os.path.join(src, 'app.js')
    _write(abs_entry, '// app')
    with pytest.raises(InvalidSourceError):
        bundle.resolve_entry_point(src, explicit=abs_entry)


def test_resolve_explicit_entry_escape_rejected(tmp_path):
    src = str(tmp_path / 'inner')
    os.makedirs(src)
    _write(str(tmp_path / 'outside.js'), '// outside')
    with pytest.raises(InvalidSourceError):
        bundle.resolve_entry_point(src, explicit='../outside.js')


def test_resolve_falls_back_to_package_main(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'server.js'), '// real')
    _write(
        os.path.join(src, 'package.json'),
        '{"main": "server.js"}',
    )
    assert bundle.resolve_entry_point(src) == 'server.js'


def test_resolve_falls_back_to_index_js(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    assert bundle.resolve_entry_point(src) == 'index.js'


def test_resolve_raises_when_no_candidate(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'README.md'), '# hi')
    with pytest.raises(EntryPointNotFoundError) as excinfo:
        bundle.resolve_entry_point(src)
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
    assert bundle.resolve_entry_point(src) == 'dist/index.js'


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
    assert bundle.resolve_entry_point(src) == 'dist/esm.js'


def test_resolve_exports_require_only(tmp_path):
    # A CJS-only package that still uses an exports map resolves via "require".
    src = str(tmp_path)
    os.makedirs(os.path.join(src, 'dist'))
    _write(os.path.join(src, 'dist', 'cjs.js'), '// cjs')
    _write(
        os.path.join(src, 'package.json'),
        '{"exports": {".": {"require": "./dist/cjs.js"}}}',
    )
    assert bundle.resolve_entry_point(src) == 'dist/cjs.js'


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
    assert bundle.resolve_entry_point(src) == 'dist/esm.js'


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

    assert bundle.resolve_entry_point(src) == 'dist/index.js'


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
    assert bundle.resolve_entry_point(src) == 'main.js'


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

    assert bundle.resolve_entry_point(src) == 'server.js'


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
    assert bundle.resolve_entry_point(src) == 'index.js'


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
    assert bundle.resolve_entry_point(src) == 'index.js'


def test_malformed_package_json_does_not_echo_contents(tmp_path):
    src = str(tmp_path)
    _write(
        os.path.join(src, 'package.json'),
        '{"secret":"AKIA1234567890","main":"index.js",,}',
    )
    _write(os.path.join(src, 'index.js'), '// idx')
    with pytest.raises(MalformedPackageJsonError) as excinfo:
        bundle.resolve_entry_point(src)
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
        bundle.resolve_entry_point(src)

    message = str(excinfo.value)
    assert package_json in message
    assert 'readable' in message


def test_build_zip_arcnames_forward_slash_on_all_platforms(tmp_path):
    src = str(tmp_path)
    nested = os.path.join(src, 'lib', 'inner')
    os.makedirs(nested)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(nested, 'mod.js'), '// mod')
    path, _ = bundle.build_zip(
        src, 'index.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        assert 'lib/inner/mod.js' in names
        for n in names:
            assert '\\' not in n, n
    finally:
        os.unlink(path)


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='symlinks need elevation on Windows',
)
def test_build_zip_skips_symlinks(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    target = os.path.join(src, 'real.js')
    _write(target, '// target')
    os.symlink(target, os.path.join(src, 'link.js'))
    path, _ = bundle.build_zip(
        src, 'index.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert 'link.js' not in names
        assert 'real.js' in names
        assert 'index.js' in names
    finally:
        os.unlink(path)


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='symlinks need elevation on Windows',
)
def test_build_zip_skips_symlinked_directory(tmp_path):
    # A symlinked directory (the pnpm / workspace node_modules layout) must
    # not be descended into or bundled -- os.walk lists it under ``dirs`` even
    # with followlinks=False, so it has to be pruned explicitly.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    real_dep = os.path.join(src, 'store', 'dep')
    os.makedirs(real_dep)
    _write(os.path.join(real_dep, 'dep.js'), '// dep')
    nm = os.path.join(src, 'node_modules')
    os.makedirs(nm)
    os.symlink(real_dep, os.path.join(nm, 'dep'))
    path, _ = bundle.build_zip(
        src, 'index.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        # The symlinked dep must not appear under node_modules...
        assert not any(n.startswith('node_modules/dep/') for n in names)
        # ...though the real file under its true location still ships.
        assert 'store/dep/dep.js' in names
        assert 'index.js' in names
    finally:
        os.unlink(path)


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='symlinks need elevation on Windows',
)
def test_build_zip_warns_once_on_skipped_symlinks(tmp_path, capsys):
    # Skipping a symlink is silent-failure-prone (missing deps only surface at
    # runtime), so build_zip emits exactly one consolidated warning that names
    # the skipped links and calls out node_modules.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, 'real.js'), '// target')
    os.symlink(os.path.join(src, 'real.js'), os.path.join(src, 'link.js'))
    nm = os.path.join(src, 'node_modules')
    os.makedirs(os.path.join(src, 'store', 'dep'))
    os.makedirs(nm)
    os.symlink(os.path.join(src, 'store', 'dep'), os.path.join(nm, 'dep'))
    path, _ = bundle.build_zip(
        src, 'index.js', exclude_patterns=(), include_hidden=False
    )
    os.unlink(path)
    err = capsys.readouterr().err
    assert err.count('Warning: skipped') == 1
    assert 'link.js' in err
    assert 'node_modules/dep' in err
    assert 'node_modules' in err


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='symlinks need elevation on Windows',
)
def test_build_zip_no_symlink_warning_when_none_skipped(tmp_path, capsys):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    path, _ = bundle.build_zip(
        src, 'index.js', exclude_patterns=(), include_hidden=False
    )
    os.unlink(path)
    assert 'Warning: skipped' not in capsys.readouterr().err


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='symlinks need elevation on Windows',
)
def test_build_zip_excluded_symlink_does_not_warn(tmp_path, capsys):
    # A symlink the user already excludes (matches an exclude pattern) is
    # dropped silently -- no spurious "missing dependency" warning.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, 'real.pem'), 'secret')
    os.symlink(os.path.join(src, 'real.pem'), os.path.join(src, 'link.pem'))
    path, _ = bundle.build_zip(
        src, 'index.js', exclude_patterns=('*.pem',), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert 'link.pem' not in names
        assert 'real.pem' not in names
    finally:
        os.unlink(path)
    assert 'Warning: skipped' not in capsys.readouterr().err


def test_build_zip_excludes_dotenv_by_default(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, '.env'), 'SECRET=1')
    _write(os.path.join(src, '.env.production'), 'SECRET=2')
    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert '.env' not in names
        assert '.env.production' not in names
        assert 'index.js' in names
    finally:
        os.unlink(path)


def test_build_zip_force_includes_exact_excluded_files(tmp_path, capsys):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, '.env'), 'PUBLIC_SETTING=on')
    cert_dir = os.path.join(src, 'certs')
    os.makedirs(cert_dir)
    _write(os.path.join(cert_dir, 'public.pem'), 'public certificate')
    _write(os.path.join(src, 'private.key'), 'private key')

    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
        force_include=['./.env', 'certs/public.pem'],
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert '.env' in names
        assert 'certs/public.pem' in names
        assert 'private.key' not in names
    finally:
        os.unlink(path)

    warning = capsys.readouterr().err
    assert '--force-include' in warning
    assert '.env' in warning
    assert 'certs/public.pem' in warning
    assert 'PUBLIC_SETTING' not in warning
    assert 'AWS Secrets Manager' in warning


def test_build_zip_force_include_rejects_source_escape(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    _write(str(src / 'index.js'), '// idx')
    _write(str(tmp_path / 'outside.env'), 'PUBLIC_SETTING=on')

    with pytest.raises(InvalidSourceError, match='remain inside'):
        bundle.build_zip(
            str(src),
            'index.js',
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
            include_hidden=False,
            force_include=['../outside.env'],
        )


@pytest.mark.parametrize('file_type', ['directory', 'symlink'])
def test_build_zip_force_include_rejects_non_regular_file(tmp_path, file_type):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    target = os.path.join(src, 'forced')
    if file_type == 'directory':
        os.makedirs(target)
    else:
        real_file = os.path.join(src, 'real.env')
        _write(real_file, 'PUBLIC_SETTING=on')
        os.symlink(real_file, target)

    with pytest.raises(InvalidSourceError, match='regular file'):
        bundle.build_zip(
            src,
            'index.js',
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
            include_hidden=False,
            force_include=['forced'],
        )


def test_build_zip_force_include_does_not_override_excluded_directory(
    tmp_path,
):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    ssh_dir = os.path.join(src, '.ssh')
    os.makedirs(ssh_dir)
    _write(os.path.join(ssh_dir, 'known_hosts'), 'example.com ssh-ed25519 key')

    with pytest.raises(
        InvalidSourceError, match='excluded or symlinked directories'
    ):
        bundle.build_zip(
            src,
            'index.js',
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
            include_hidden=True,
            force_include=['.ssh/known_hosts'],
        )


@pytest.mark.parametrize(
    'hidden_directory', DEFAULT_INCLUDED_HIDDEN_DIRECTORIES
)
def test_build_zip_includes_runtime_hidden_directories_by_default(
    tmp_path, capsys, hidden_directory
):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    generated_dir = os.path.join(
        src, 'apps', 'web', hidden_directory, 'server', '.runtime'
    )
    os.makedirs(generated_dir)
    _write(os.path.join(generated_dir, 'entry.js'), '// generated')
    _write(os.path.join(generated_dir, '.env'), 'SECRET=1')

    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        expected = f'apps/web/{hidden_directory}/server/.runtime/entry.js'
        excluded = f'apps/web/{hidden_directory}/server/.runtime/.env'
        assert expected in names
        assert excluded not in names
    finally:
        os.unlink(path)
    assert '--include-hidden-files' not in capsys.readouterr().err


@pytest.mark.parametrize('hidden_file', DEFAULT_INCLUDED_HIDDEN_FILES)
def test_build_zip_includes_runtime_hidden_files_by_default(
    tmp_path, capsys, hidden_file
):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, hidden_file), '// generated')

    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert hidden_file in names
    finally:
        os.unlink(path)
    assert '--include-hidden-files' not in capsys.readouterr().err


def test_build_zip_accepts_entry_in_included_hidden_directory(tmp_path):
    src = str(tmp_path)
    entry = '.next/server/index.js'
    os.makedirs(os.path.dirname(os.path.join(src, entry)))
    _write(os.path.join(src, entry), '// server')

    path, _ = bundle.build_zip(
        src,
        entry,
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            wrapper = zf.read('index.js').decode('utf-8')
        assert entry in names
        assert 'const entryPoint = "./.next/server/index.js";' in wrapper
    finally:
        os.unlink(path)


def test_build_zip_warns_once_for_skipped_hidden_paths(tmp_path, capsys):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, '.editorconfig'), 'root = true')
    config_dir = os.path.join(src, '.config')
    os.makedirs(config_dir)
    _write(os.path.join(config_dir, 'settings.json'), '{}')

    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert '.editorconfig' not in names
        assert '.config/settings.json' not in names
    finally:
        os.unlink(path)

    err = capsys.readouterr().err
    assert err.count('Warning: skipped') == 1
    assert '.editorconfig' in err
    assert '.config' in err
    assert '--include-hidden-files' in err


def test_build_zip_excluded_hidden_paths_do_not_warn(tmp_path, capsys):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, '.env'), 'SECRET=1')
    git_dir = os.path.join(src, '.git')
    os.makedirs(git_dir)
    _write(os.path.join(git_dir, 'config'), 'ignored')

    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
    )
    os.unlink(path)

    assert 'Warning: skipped' not in capsys.readouterr().err


def test_build_zip_includes_nonsecret_hidden_when_opted_in(tmp_path):
    # --include-hidden-files ships ordinary dotfiles that are not excluded.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, '.editorconfig'), 'root = true')
    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=True,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert '.editorconfig' in names
    finally:
        os.unlink(path)


def test_build_zip_include_hidden_still_excludes_secrets(tmp_path):
    # Hidden-file opt-in must not disable secret exclusions. Environment
    # files, private keys, and SSH credentials stay out of the bundle.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, '.env'), 'DB_PASSWORD=hunter2')
    _write(os.path.join(src, '.env.production'), 'DB_PASSWORD=prod')
    _write(os.path.join(src, 'key.pem'), '-----BEGIN KEY-----')
    _write(os.path.join(src, 'server.key'), 'secret')
    _write(os.path.join(src, 'id_rsa'), 'secret')
    _write(os.path.join(src, '.npmrc'), '//registry.example.com/:_authToken=x')
    _write(os.path.join(src, '.netrc'), 'password secret')
    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=True,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert '.env' not in names
        assert '.env.production' not in names
        assert 'key.pem' not in names
        assert 'server.key' not in names
        assert 'id_rsa' not in names
        assert '.npmrc' not in names
        assert '.netrc' not in names
        assert 'index.js' in names
    finally:
        os.unlink(path)


def test_build_zip_excludes_nested_cache_dir(tmp_path):
    # Multi-segment patterns match the full path while ordinary dependencies
    # under node_modules remain in the bundle.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    cache_dir = os.path.join(src, 'node_modules', '.cache')
    os.makedirs(cache_dir)
    _write(os.path.join(cache_dir, 'blob'), 'x' * 1000)
    keep_dir = os.path.join(src, 'node_modules', 'left-pad')
    os.makedirs(keep_dir)
    _write(os.path.join(keep_dir, 'index.js'), '// dep')
    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert 'node_modules/.cache/blob' not in names
        # A normal dependency under node_modules is still bundled.
        assert 'node_modules/left-pad/index.js' in names
    finally:
        os.unlink(path)


def test_build_zip_excludes_monorepo_cache_dir_with_hidden_opt_in(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    app_dir = os.path.join(src, 'packages', 'app', 'node_modules')
    cache_dir = os.path.join(app_dir, '.cache')
    os.makedirs(cache_dir)
    _write(os.path.join(cache_dir, 'blob'), 'cached')
    keep_dir = os.path.join(app_dir, 'left-pad')
    os.makedirs(keep_dir)
    _write(os.path.join(keep_dir, 'index.js'), '// dep')

    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=True,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert 'packages/app/node_modules/.cache/blob' not in names
        assert 'packages/app/node_modules/left-pad/index.js' in names
    finally:
        os.unlink(path)


def test_no_wrapper_injected_when_entry_is_none(tmp_path):
    # entry=None means the caller selected the entry out of band (a
    # customer-set AWS_LAMBDA_NODEJS_ENTRYPOINT), so build_zip must ship the
    # tree
    # AS-IS with no generated index.js.
    src = str(tmp_path)
    _write(os.path.join(src, 'server.mjs'), "console.log('hi')")
    _write(os.path.join(src, 'package.json'), '{"type": "module"}')
    path, _ = bundle.build_zip(
        src, None, exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert names == {'server.mjs', 'package.json'}
        assert 'index.js' not in names
    finally:
        os.unlink(path)


def test_no_wrapper_when_entry_none_even_with_existing_index_js(tmp_path):
    # A tree that HAS its own index.js is shipped verbatim under entry=None --
    # no WrapperConflictError, and the customer's index.js is untouched.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// customer index')
    _write(os.path.join(src, 'server.mjs'), '// real server')
    path, _ = bundle.build_zip(
        src, None, exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            assert zf.read('index.js').decode() == '// customer index'
    finally:
        os.unlink(path)


def test_wrapper_injected_when_entry_is_server_js(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'server.js'), "console.log('hi')")
    _write(os.path.join(src, 'package.json'), '{"type": "module"}')
    path, _ = bundle.build_zip(
        src, 'server.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            wrapper = zf.read('index.js').decode('utf-8')
        assert 'index.js' in names
        assert 'server.js' in names
        # A dynamic import works in both CommonJS and ESM and can load a target
        # from either module system, so the wrapper does not need to infer the
        # module system.
        assert 'const entryPoint = "./server.js";' in wrapper
        assert 'import(entryPoint)' in wrapper
    finally:
        os.unlink(path)


def test_build_zip_normalizes_dot_prefixed_entry(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'server.js'), "console.log('hi')")

    path, _ = bundle.build_zip(
        src, './server.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            wrapper = zf.read('index.js').decode('utf-8')
        assert 'const entryPoint = "./server.js";' in wrapper
        assert '././server.js' not in wrapper
    finally:
        os.unlink(path)


def test_build_zip_dot_prefixed_index_does_not_inject_wrapper(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// customer index')

    path, _ = bundle.build_zip(
        src, './index.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            assert zf.read('index.js').decode('utf-8') == '// customer index'
    finally:
        os.unlink(path)


@pytest.mark.parametrize(
    'entry,exclude_patterns',
    [
        ('.config/server.js', ()),
        ('private/server.pem', ('*.pem',)),
    ],
)
def test_build_zip_rejects_entry_excluded_from_bundle(
    tmp_path, entry, exclude_patterns
):
    src = str(tmp_path)
    os.makedirs(os.path.dirname(os.path.join(src, entry)), exist_ok=True)
    _write(os.path.join(src, entry), "console.log('hi')")

    with pytest.raises(InvalidSourceError, match='not included'):
        bundle.build_zip(
            src,
            entry,
            exclude_patterns=exclude_patterns,
            include_hidden=False,
        )


def test_wrapper_escapes_entry_point_for_javascript(tmp_path):
    src = str(tmp_path)
    entry = "server's.js"
    _write(os.path.join(src, entry), "console.log('hi')")
    path, _ = bundle.build_zip(
        src, entry, exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            wrapper = zf.read('index.js').decode('utf-8')
        assert "const entryPoint = \"./server's.js\";" in wrapper
        assert 'import(entryPoint)' in wrapper
    finally:
        os.unlink(path)


@pytest.mark.parametrize(
    'pkg_json',
    [
        '{"type": "module"}',
        '{"type": "commonjs"}',
        '{}',
        None,
    ],
)
def test_wrapper_uses_dynamic_import_regardless_of_module_system(
    tmp_path, pkg_json
):
    # Dynamic import works whether Node interprets index.js as CommonJS or ESM
    # and can load a target using either module system.
    src = str(tmp_path)
    _write(os.path.join(src, 'server.cjs'), "console.log('hi')")
    if pkg_json is not None:
        _write(os.path.join(src, 'package.json'), pkg_json)
    path, _ = bundle.build_zip(
        src, 'server.cjs', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            wrapper = zf.read('index.js').decode('utf-8')
        assert 'const entryPoint = "./server.cjs";' in wrapper
        assert 'import(entryPoint)' in wrapper
        # Never emit a bare require()/static import that would break under
        # the opposite module system.
        assert 'require(' not in wrapper
    finally:
        os.unlink(path)


def test_wrapper_refuses_to_overwrite_existing_index_js(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// existing')
    _write(os.path.join(src, 'server.js'), '// real')
    with pytest.raises(WrapperConflictError) as excinfo:
        bundle.build_zip(
            src, 'server.js', exclude_patterns=(), include_hidden=False
        )
    assert 'index.js' in str(excinfo.value)


def test_wrapper_replaces_excluded_index_js(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// excluded')
    _write(os.path.join(src, 'server.js'), '// real')

    path, _ = bundle.build_zip(
        src,
        'server.js',
        exclude_patterns=('index.js',),
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            wrapper = zf.read('index.js').decode('utf-8')
        assert 'const entryPoint = "./server.js";' in wrapper
    finally:
        os.unlink(path)


def test_wrapper_replaces_symlinked_index_js(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'linked-index.js'), '// linked')
    _write(os.path.join(src, 'server.js'), '// real')
    os.symlink(
        os.path.join(src, 'linked-index.js'),
        os.path.join(src, 'index.js'),
    )

    path, _ = bundle.build_zip(
        src,
        'server.js',
        exclude_patterns=(),
        include_hidden=False,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            wrapper = zf.read('index.js').decode('utf-8')
        assert 'linked-index.js' in names
        assert 'const entryPoint = "./server.js";' in wrapper
    finally:
        os.unlink(path)


@pytest.mark.parametrize('name', ['', 'foo bar', 'foo/bar', 'a' * 65])
def test_validate_function_name_rejects_special_chars(name):
    with pytest.raises(InvalidFunctionNameError):
        bundle.validate_function_name(name)


@pytest.mark.parametrize('name', ['a', '-ab', 'ab_', '_cd', 'ef-'])
def test_validate_function_name_rejects_short_or_leading_trailing(name):
    with pytest.raises(InvalidFunctionNameError):
        bundle.validate_function_name(name)


def test_validate_function_name_accepts_valid():
    # Should not raise
    bundle.validate_function_name('my-fn_1')


@pytest.mark.skipif(
    not hasattr(os, 'mkfifo'), reason='mkfifo not available on this platform'
)
def test_build_zip_skips_fifo(tmp_path, capsys):
    # A FIFO in the tree must be skipped: zipfile would block forever
    # trying to read it.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    os.mkfifo(os.path.join(src, 'pipe'))
    path, _ = bundle.build_zip(
        src, 'index.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert 'pipe' not in names
        assert 'index.js' in names
        assert 'not a regular file' in capsys.readouterr().err
    finally:
        os.unlink(path)


def test_build_zip_wrapper_entry_is_world_readable(tmp_path):
    src = str(tmp_path)
    _write(os.path.join(src, 'server.js'), '// real')
    path, _ = bundle.build_zip(
        src, 'server.js', exclude_patterns=(), include_hidden=False
    )
    try:
        with zipfile.ZipFile(path) as zf:
            info = zf.getinfo('index.js')
        assert (info.external_attr >> 16) & 0o777 == 0o644
    finally:
        os.unlink(path)


def test_build_zip_excludes_secrets_case_insensitively(tmp_path):
    # .ENV / SERVER.PEM / ID_RSA must not bypass the exclusions on
    # case-sensitive filesystems.
    src = str(tmp_path)
    _write(os.path.join(src, 'index.js'), '// idx')
    _write(os.path.join(src, '.ENV'), 'SECRET=1')
    _write(os.path.join(src, 'SERVER.PEM'), '-----BEGIN KEY-----')
    _write(os.path.join(src, 'ID_RSA'), 'secret')
    path, _ = bundle.build_zip(
        src,
        'index.js',
        exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
        include_hidden=True,
    )
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
        assert '.ENV' not in names
        assert 'SERVER.PEM' not in names
        assert 'ID_RSA' not in names
        assert 'index.js' in names
    finally:
        os.unlink(path)


def test_build_zip_removes_temp_file_on_failure(tmp_path, monkeypatch):
    src = str(tmp_path / 'src')
    os.makedirs(src)
    _write(os.path.join(src, 'index.js'), '// existing')
    _write(os.path.join(src, 'server.js'), '// real')
    tmpdir = tmp_path / 'tmpdir'
    tmpdir.mkdir()
    monkeypatch.setattr(bundle.tempfile, 'tempdir', str(tmpdir))
    with pytest.raises(WrapperConflictError):
        bundle.build_zip(
            src, 'server.js', exclude_patterns=(), include_hidden=False
        )
    assert list(tmpdir.iterdir()) == []


def test_remove_bundle_missing_file_is_quiet(tmp_path):
    bundle.remove_bundle(str(tmp_path / 'nope.zip'))
